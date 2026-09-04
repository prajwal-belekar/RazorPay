"""Blockchain Proof Layer service for RecoverAI.

Submits and verifies deterministic SHA-256 proof hashes on the Polygon Amoy
testnet (chain ID 80002) via the RecoveryProof smart contract.

Guarantees:
  - Only Polygon Amoy testnet is ever used (chain ID 80002).
  - The BLOCKCHAIN_PRIVATE_KEY is never logged, returned, or exposed.
  - Blockchain failures never corrupt PostgreSQL records.
  - Idempotent: if a proof is already recorded, the transaction is skipped.
"""

import logging
from typing import Any, Optional

from web3 import Web3
from web3.exceptions import ContractLogicError

from app.config import (
    BLOCKCHAIN_PRIVATE_KEY,
    POLYGON_AMOY_RPC_URL,
    POLYGON_CHAIN_ID,
    RECOVERY_PROOF_CONTRACT_ADDRESS,
)

logger = logging.getLogger(__name__)

# Minimal ABI for the RecoveryProof contract
_RECOVERY_PROOF_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "paymentId", "type": "string"},
            {"internalType": "bytes32", "name": "proofHash", "type": "bytes32"},
        ],
        "name": "recordRecoveryProof",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "string", "name": "paymentId", "type": "string"},
        ],
        "name": "getProofByPaymentId",
        "outputs": [
            {"internalType": "bytes32", "name": "proofHash", "type": "bytes32"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "address", "name": "recorder", "type": "address"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "string", "name": "paymentId", "type": "string"},
        ],
        "name": "hasProof",
        "outputs": [
            {"internalType": "bool", "name": "", "type": "bool"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "getProofCount",
        "outputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]


def _redact_key(key: str | None) -> str:
    """Return a safe preview of a private key without exposing it."""
    if not key or len(key) < 12:
        return "<not set>"
    return f"{key[:6]}...{key[-4:]}"


class BlockchainService:
    """Service for interacting with the RecoveryProof smart contract on Polygon Amoy."""

    def __init__(self) -> None:
        self._w3: Optional[Web3] = None
        self._contract = None
        self._account = None
        self._configured = False

    def _ensure_connected(self) -> None:
        """Lazy-connect to Polygon Amoy and instantiate the contract."""
        if self._configured:
            return

        rpc_url = POLYGON_AMOY_RPC_URL
        private_key = BLOCKCHAIN_PRIVATE_KEY
        contract_addr = RECOVERY_PROOF_CONTRACT_ADDRESS

        if not rpc_url or not private_key or not contract_addr:
            logger.warning(
                "Blockchain not configured. Set POLYGON_AMOY_RPC_URL, "
                "BLOCKCHAIN_PRIVATE_KEY, and RECOVERY_PROOF_CONTRACT_ADDRESS "
                "in Backend/.env. Proof submission will return NOT_SUBMITTED."
            )
            return

        try:
            self._w3 = Web3(Web3.HTTPProvider(rpc_url))
            if not self._w3.is_connected():
                logger.error("Cannot connect to Polygon Amoy RPC at %s", rpc_url[:30] + "...")
                return

            chain_id = self._w3.eth.chain_id
            if chain_id != POLYGON_CHAIN_ID:
                logger.error(
                    "Connected chain ID %d does not match expected %d (Polygon Amoy). "
                    "Proof submission refused.",
                    chain_id,
                    POLYGON_CHAIN_ID,
                )
                self._w3 = None
                return

            self._account = self._w3.eth.account.from_key(private_key)
            checksum_addr = self._w3.to_checksum_address(contract_addr)
            self._contract = self._w3.eth.contract(
                address=checksum_addr,
                abi=_RECOVERY_PROOF_ABI,
            )
            self._configured = True
            logger.info(
                "Blockchain connected: Polygon Amoy (chain %d), "
                "contract %s, recorder %s",
                chain_id,
                checksum_addr[:10] + "...",
                _redact_key(None),  # Don't log the key
            )
        except Exception as exc:
            logger.error("Blockchain initialization failed: %s", exc)
            self._w3 = None
            self._configured = False

    @property
    def is_configured(self) -> bool:
        """Return True when the blockchain connection is ready."""
        self._ensure_connected()
        return self._configured

    def submit_proof(
        self,
        payment_id: str,
        proof_hash: str,
    ) -> dict[str, Any]:
        """Submit a SHA-256 proof hash to the RecoveryProof smart contract.

        Parameters:
            payment_id: The Razorpay payment ID string.
            proof_hash: The full proof hash, e.g. "sha256:abcdef...".

        Returns:
            A structured dict with submission result and chain details.
        """
        if not self.is_configured:
            return {
                "submitted": False,
                "status": "NOT_SUBMITTED",
                "reason": "Blockchain not configured. Proof stored locally only.",
                "chain_network": None,
                "chain_tx_hash": None,
                "chain_block_number": None,
            }

        try:
            # Convert the proof hash string to bytes32
            # Strip the "sha256:" prefix and decode hex
            hex_str = proof_hash.replace("sha256:", "")
            if hex_str.startswith("0x"):
                hex_str = hex_str[2:]
            proof_bytes = bytes.fromhex(hex_str)
            if len(proof_bytes) != 32:
                return {
                    "submitted": False,
                    "status": "INVALID_HASH",
                    "reason": f"Proof hash must be 32 bytes, got {len(proof_bytes)}.",
                    "chain_network": f"polygon-amoy ({POLYGON_CHAIN_ID})",
                    "chain_tx_hash": None,
                    "chain_block_number": None,
                }

            # Check if already recorded (idempotent)
            try:
                existing = self._contract.functions.hasProof(payment_id).call()
                if existing:
                    logger.info("Proof already recorded on-chain for payment %s", payment_id[:8] + "...")
                    return {
                        "submitted": True,
                        "status": "ALREADY_RECORDED",
                        "reason": "Proof was already recorded on-chain for this payment.",
                        "chain_network": f"polygon-amoy ({POLYGON_CHAIN_ID})",
                        "chain_tx_hash": None,
                        "chain_block_number": None,
                    }
            except ContractLogicError:
                pass  # Contract reverts if no proof exists; treat as not recorded

            # Build and send the transaction
            nonce = self._w3.eth.get_transaction_count(self._account.address)
            gas_price = self._w3.eth.gas_price

            tx = self._contract.functions.recordRecoveryProof(
                payment_id,
                proof_bytes,
            ).build_transaction({
                "chainId": POLYGON_CHAIN_ID,
                "from": self._account.address,
                "nonce": nonce,
                "gasPrice": int(gas_price * 1.2),  # 20% buffer
                "gas": 200000,
            })

            signed_tx = self._w3.eth.account.sign_transaction(tx, private_key=BLOCKCHAIN_PRIVATE_KEY)
            tx_hash = self._w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            success = receipt.status == 1
            return {
                "submitted": success,
                "status": "CONFIRMED" if success else "FAILED",
                "reason": None if success else "Transaction reverted on-chain.",
                "chain_network": f"polygon-amoy ({POLYGON_CHAIN_ID})",
                "chain_tx_hash": receipt.transactionHash.hex(),
                "chain_block_number": receipt.blockNumber,
            }

        except Exception as exc:
            logger.error("Blockchain proof submission failed: %s", exc)
            return {
                "submitted": False,
                "status": "SUBMISSION_FAILED",
                "reason": f"Blockchain transaction failed: {type(exc).__name__}",
                "chain_network": f"polygon-amoy ({POLYGON_CHAIN_ID})",
                "chain_tx_hash": None,
                "chain_block_number": None,
            }

    def retrieve_proof(self, payment_id: str) -> dict[str, Any]:
        """Retrieve a proof from the RecoveryProof smart contract.

        Returns:
            A dict with on-chain proof details or an error status.
        """
        if not self.is_configured:
            return {
                "found": False,
                "status": "NOT_CONFIGURED",
                "reason": "Blockchain not configured.",
            }

        try:
            proof_hash_bytes, timestamp, recorder = (
                self._contract.functions.getProofByPaymentId(payment_id).call()
            )
            hex_hash = "0x" + proof_hash_bytes.hex()
            return {
                "found": True,
                "status": "ON_CHAIN",
                "proof_hash": hex_hash,
                "timestamp": timestamp,
                "recorder": recorder,
                "chain_network": f"polygon-amoy ({POLYGON_CHAIN_ID})",
            }
        except ContractLogicError:
            return {
                "found": False,
                "status": "NOT_FOUND",
                "reason": "No proof recorded on-chain for this payment ID.",
            }
        except Exception as exc:
            logger.error("Blockchain proof retrieval failed: %s", exc)
            return {
                "found": False,
                "status": "RETRIEVAL_FAILED",
                "reason": f"Blockchain query failed: {type(exc).__name__}",
            }

    def verify_proof_on_chain(
        self,
        payment_id: str,
        expected_hash: str,
    ) -> dict[str, Any]:
        """Verify that the on-chain proof hash matches the expected local hash.

        Returns:
            A dict indicating whether the hashes match.
        """
        on_chain = self.retrieve_proof(payment_id)
        if not on_chain.get("found"):
            return {
                "verified": False,
                "status": on_chain.get("status", "UNKNOWN"),
                "reason": on_chain.get("reason", "Could not retrieve on-chain proof."),
                "chain_network": f"polygon-amoy ({POLYGON_CHAIN_ID})",
            }

        on_chain_hash = on_chain["proof_hash"]
        # Normalize the expected hash for comparison
        expected_hex = expected_hash.replace("sha256:", "")
        if not expected_hex.startswith("0x"):
            expected_hex = "0x" + expected_hex

        matched = on_chain_hash.lower() == expected_hex.lower()
        return {
            "verified": matched,
            "status": "VERIFIED" if matched else "MISMATCH",
            "on_chain_hash": on_chain_hash,
            "expected_hash": expected_hex,
            "chain_network": f"polygon-amoy ({POLYGON_CHAIN_ID})",
        }


# Module-level singleton
blockchain_service = BlockchainService()
