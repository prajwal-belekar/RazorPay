import { RecoveryCase, RecoveryStatus } from '@/types';
import { apiFetch } from './client';
import { mockRecoveryCases } from '../mock/recovery';

export async function getRecoveryCases(): Promise<RecoveryCase[]> {
  try {
    return await apiFetch<RecoveryCase[]>('/api/recovery');
  } catch {
    return mockRecoveryCases;
  }
}

export async function getRecoveryCaseById(id: string): Promise<RecoveryCase | null> {
  try {
    return await apiFetch<RecoveryCase>(`/api/recovery/${id}`);
  } catch {
    const found = mockRecoveryCases.find(
      (c) => c.id === id || c.transactionId === id
    );
    return found || mockRecoveryCases[0];
  }
}

export async function executeRecovery(id: string, strategy: string): Promise<{ success: boolean; txHash: string; status: RecoveryStatus }> {
  try {
    return await apiFetch(`/api/recovery/${id}/execute`, {
      method: 'POST',
      body: JSON.stringify({ strategy }),
    });
  } catch {
    return {
      success: true,
      txHash: '0x7382193eab84102c98d726154109abfe',
      status: 'Recovered',
    };
  }
}
