import { SimulationConfig, SimulationResult } from '@/types';
import { apiFetch } from './client';

export interface SimulationActual {
  status: string;
  action: string;
  amount: number | null;
  timestamp: string | null;
  execution_id: number;
  proof_status: string | null;
  predicted: false;
}

export async function runSimulation(config: SimulationConfig): Promise<{ predictions: SimulationResult[]; actual: SimulationActual | null }> {
  const response = await apiFetch<{ predictions: Array<{
    strategy: string;
    probability: number;
    expected_value: number;
    roi: number;
    risk: string;
    required_action: string;
    reason: string;
    predicted: boolean;
  }>; recommended_strategy: string | null; actual: SimulationActual | null }>('/api/simulator/run', {
    method: 'POST',
    body: JSON.stringify({
      payment_id: config.paymentId,
      horizon_days: config.horizonDays,
      retry_count: config.retryCount,
      selected_strategies: config.selectedStrategies.map((strategy) => {
        if (strategy === 'Retry') return 'DELAYED_RETRY';
        if (strategy === 'Payment Link') return 'PAYMENT_LINK';
        if (strategy === 'Reminder') return 'SOFT_PUSH_REMINDER';
        return 'HYBRID_RECOVERY_CASCADE';
      }),
    }),
  });
  const labels: Record<string, SimulationResult['strategy']> = {
    DELAYED_RETRY: 'Retry',
    PAYMENT_LINK: 'Payment Link',
    SOFT_PUSH_REMINDER: 'Reminder',
    HYBRID_RECOVERY_CASCADE: 'Retry + Payment Link',
  };
  const predictions = response.predictions.map((result) => ({
    strategy: labels[result.strategy] || result.strategy as SimulationResult['strategy'],
    expectedRecovery: result.expected_value,
    probability: result.probability * 100,
    expectedRoi: result.roi,
    timeToRecoverHours: 0,
    successRateByMethod: {} as SimulationResult['successRateByMethod'],
    risk: result.risk,
    requiredAction: result.required_action,
    reason: result.reason,
    predicted: result.predicted,
    isRecommended: result.strategy === response.recommended_strategy,
  }));
  return { predictions, actual: response.actual };
}
