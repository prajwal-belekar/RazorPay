import { BlockchainProof } from '@/types';
import { apiFetch } from './client';
import { mockBlockchainProofs } from '../mock/blockchain';

export async function getBlockchainProofs(): Promise<BlockchainProof[]> {
  try {
    return await apiFetch<BlockchainProof[]>('/api/blockchain/proofs');
  } catch {
    return mockBlockchainProofs;
  }
}

export async function verifyProof(proofHash: string): Promise<{ verified: boolean; blockNumber: number; txHash: string; timestamp: string }> {
  try {
    return await apiFetch('/api/blockchain/verify', {
      method: 'POST',
      body: JSON.stringify({ proofHash }),
    });
  } catch {
    const proof = mockBlockchainProofs.find((p) => p.proofHash === proofHash) || mockBlockchainProofs[0];
    return {
      verified: true,
      blockNumber: proof.blockNumber,
      txHash: proof.txHash,
      timestamp: proof.timestamp,
    };
  }
}
