import { MerchantDNA } from '@/types';
import { apiFetch } from './client';
import { mockMerchantDNA, mockStrategyPerformance, mockFailureAnalysis } from '../mock/analytics';

export async function getMerchantDNA(): Promise<MerchantDNA> {
  try {
    return await apiFetch<MerchantDNA>('/api/analytics/dna');
  } catch {
    return mockMerchantDNA;
  }
}

export async function getStrategyPerformance() {
  try {
    return await apiFetch('/api/analytics/strategies');
  } catch {
    return mockStrategyPerformance;
  }
}

export async function getFailureAnalysis() {
  try {
    return await apiFetch('/api/analytics/failures');
  } catch {
    return mockFailureAnalysis;
  }
}
