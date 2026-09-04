// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title RecoveryProof
/// @notice On-chain receipt for RecoverAI recovery-action proofs.
/// @dev Deployed on Polygon Amoy testnet (chain 80002) ONLY.
///      Stores deterministic SHA-256 proof hashes keyed by Razorpay payment ID.
///      The contract owner is the only address allowed to record proofs.
contract RecoveryProof {
    address public owner;

    struct Proof {
        bytes32 proofHash;
        string  paymentId;
        uint256 timestamp;
        address recorder;
    }

    // paymentId string => Proof
    mapping(string => Proof) private proofs;

    // All recorded payment IDs (for enumeration)
    string[] private recordedPaymentIds;

    event ProofRecorded(
        string indexed paymentId,
        bytes32 indexed proofHash,
        uint256 timestamp,
        address recorder
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "RecoveryProof: caller is not the owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /// @notice Record a recovery proof hash for a given payment ID.
    /// @param paymentId  Razorpay payment ID string (e.g. "pay_XXXX").
    /// @param proofHash  Deterministic SHA-256 proof hash (bytes32).
    function recordRecoveryProof(
        string calldata paymentId,
        bytes32 proofHash
    ) external onlyOwner {
        require(bytes(paymentId).length > 0, "RecoveryProof: empty paymentId");
        require(proofHash != bytes32(0), "RecoveryProof: zero proofHash");
        require(
            bytes(proofs[paymentId].paymentId).length == 0,
            "RecoveryProof: proof already recorded for this paymentId"
        );

        proofs[paymentId] = Proof({
            proofHash: proofHash,
            paymentId: paymentId,
            timestamp: block.timestamp,
            recorder: msg.sender
        });

        recordedPaymentIds.push(paymentId);

        emit ProofRecorded(paymentId, proofHash, block.timestamp, msg.sender);
    }

    /// @notice Retrieve a proof by its Razorpay payment ID.
    /// @param paymentId  The Razorpay payment ID to look up.
    /// @return proofHash  The stored proof hash.
    /// @return timestamp  Block timestamp when the proof was recorded.
    /// @return recorder   Address that recorded the proof.
    function getProofByPaymentId(
        string calldata paymentId
    ) external view returns (
        bytes32 proofHash,
        uint256 timestamp,
        address recorder
    ) {
        Proof storage p = proofs[paymentId];
        require(bytes(p.paymentId).length > 0, "RecoveryProof: no proof found");
        return (p.proofHash, p.timestamp, p.recorder);
    }

    /// @notice Check if a proof has been recorded for a payment ID.
    function hasProof(string calldata paymentId) external view returns (bool) {
        return bytes(proofs[paymentId].paymentId).length > 0;
    }

    /// @notice Return the total number of recorded proofs.
    function getProofCount() external view returns (uint256) {
        return recordedPaymentIds.length;
    }
}
