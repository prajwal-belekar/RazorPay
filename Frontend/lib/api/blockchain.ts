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

export async function verifyProof(proofHash: string): Promise<{ verified: boolean; blockNumber: number | null; txHash: string | null; timestamp: string | null }> {
  try {
    return await apiFetch('/api/blockchain/verify', {
      method: 'POST',
      body: JSON.stringify({ proofHash }),
    });
  } catch {
    return {
      verified: false,
      blockNumber: null,
      txHash: null,
      timestamp: null,
    };
  }
}
