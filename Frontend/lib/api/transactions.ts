import { Transaction } from '@/types';
import { apiFetch } from './client';
import { mockTransactions } from '../mock/transactions';

export async function getTransactions(): Promise<Transaction[]> {
  try {
    return await apiFetch<Transaction[]>('/api/transactions');
  } catch {
    return mockTransactions;
  }
}
