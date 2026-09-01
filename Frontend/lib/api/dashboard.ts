import { DashboardMetrics, Anomaly } from '@/types';
import { apiFetch } from './client';
import { mockDashboardMetrics, mockRevenueOverviewData, mockRevenueLeakAnomaly } from '../mock/dashboard';

export async function getDashboardSummary(): Promise<DashboardMetrics> {
  try {
    return await apiFetch<DashboardMetrics>('/api/dashboard/summary');
  } catch {
    return mockDashboardMetrics;
  }
}

export async function getRevenueOverviewData() {
  try {
    return await apiFetch('/api/dashboard/revenue');
  } catch {
    return mockRevenueOverviewData;
  }
}

export async function getRevenueLeakAnomaly(): Promise<Anomaly> {
  try {
    return await apiFetch<Anomaly>('/api/dashboard/anomaly');
  } catch {
    return mockRevenueLeakAnomaly;
  }
}
