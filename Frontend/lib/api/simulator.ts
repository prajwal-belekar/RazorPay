import { SimulationConfig, SimulationResult } from '@/types';
import { apiFetch } from './client';
import { mockDefaultSimulationResults } from '../mock/simulator';

export async function runSimulation(config: SimulationConfig): Promise<SimulationResult[]> {
  try {
    return await apiFetch<SimulationResult[]>('/api/simulator/run', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  } catch {
    const scale = config.revenueAtRisk / 2840000;
    return mockDefaultSimulationResults.map((r) => ({
      ...r,
      expectedRecovery: Math.round(r.expectedRecovery * scale),
    }));
  }
}
