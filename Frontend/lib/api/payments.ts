import { Payment, RecoveryCase, PaymentMethod, RecoveryStatus, StrategyType } from '@/types';
import { apiFetch } from './client';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

const STATUS_MAP: Record<string, RecoveryStatus> = {
  SUCCESS: 'Recovered',
  PENDING: 'At Risk',
  FAILED: 'Failed',
  AT_RISK: 'At Risk',
  RECOVERED: 'Recovered',
};

const STRATEGY_MAP: Record<string, StrategyType> = {
  RETRY: 'Retry',
  PAYMENT_LINK: 'Payment Link',
  REMINDER: 'Reminder',
  'RETRY + PAYMENT LINK': 'Retry + Payment Link',
  SMART_SCHEDULE: 'Smart Schedule',
  'RETRY + PAYMENT_LINK': 'Retry + Payment Link',
};

function mapStrategy(action: string | null): StrategyType {
  if (!action) return 'Retry';
  return STRATEGY_MAP[action.toUpperCase()] || STRATEGY_MAP[action] || ('Retry' as StrategyType);
}

function mapStatus(status: string | null): RecoveryStatus {
  if (!status) return 'At Risk';
  const key = status.toUpperCase();
  return STATUS_MAP[key] || 'At Risk';
}

function mapCustomerType(customerType: string): { name: string; tier: string } {
  const lower = customerType.toLowerCase();
  if (lower.includes('returning')) return { name: customerType, tier: 'Returning' };
  if (lower.includes('vip')) return { name: customerType, tier: 'VIP' };
  if (lower.includes('regular')) return { name: customerType, tier: 'Regular' };
  if (lower.includes('new')) return { name: customerType, tier: 'New' };
  return { name: customerType, tier: 'Regular' };
}

function toPercent(value: number | null | undefined): number {
  if (value === null || value === undefined) return 0;
  return Math.round(value * 100);
}

export function paymentToRecoveryCase(payment: Payment): RecoveryCase {
  const tier = mapCustomerType(payment.customer_type);
  const confidence = toPercent(payment.confidence);
  const probability = confidence;
  const expectedRecovery = confidence > 0 ? Math.round(payment.amount * (confidence / 100)) : 0;

  return {
    id: String(payment.id),
    transactionId: `Payment #${payment.id}`,
    customer: {
      id: `PAY-${payment.id}`,
      name: payment.customer_type || 'N/A',
      email: 'N/A',
      phone: 'N/A',
      tier: tier.tier as 'VIP' | 'Returning' | 'New' | 'Regular',
      historicalSuccessRate: confidence,
    },
    amount: payment.amount,
    paymentMethod: 'N/A',
    failureReason: payment.failure_reason || 'Unknown',
    recoveryProbability: probability,
    expectedRecovery,
    strategy: mapStrategy(payment.recommended_action),
    aiConfidence: confidence,
    status: mapStatus(payment.recovery_status),
    createdAt: payment.created_at || '',
    explanation: payment.reason || 'N/A',
    strategies: [
      {
        type: mapStrategy(payment.recommended_action),
        title: payment.recommended_action || 'Retry',
        probability: probability,
        expectedRecovery,
        confidence,
        isAiRecommended: true,
        explanation: payment.reason || 'N/A',
        roi: 0,
      },
    ],
    firewallResult: {
      approved: true,
      statusMessage: 'Encoded from backend decision record',
      evaluatedAt: payment.created_at || '',
      policyVersion: 'N/A',
      checks: [],
    },
    timeline: [
      {
        id: `ev-created-${payment.id}`,
        timestamp: payment.created_at || '',
        component: 'Detection Agent',
        status: 'info',
        title: 'Payment Failure Recorded',
        description: `Payment #${payment.id} of ₹${payment.amount.toLocaleString('en-IN')} failed (${payment.failure_reason}).`,
      },
      {
        id: `ev-decision-${payment.id}`,
        timestamp: payment.created_at || '',
        component: 'Prediction Engine',
        status: 'info',
        title: 'AI Decision Generated',
        description: `${payment.decision_source || 'N/A'} recommended "${payment.recommended_action || 'N/A'}" with ${confidence}% confidence.`,
      },
    ],
    proof: undefined,
    decisionSource: payment.decision_source,
    retryCount: payment.retry_count,
    reason: payment.reason,
  };
}

export function paymentsToRecoveryCases(payments: Payment[]): RecoveryCase[] {
  return payments.map(paymentToRecoveryCase);
}

export async function getPayments(): Promise<Payment[]> {
  const payments = await apiFetch<Payment[]>('/api/payments');
  return payments || [];
}

export async function getPayment(id: string | number): Promise<Payment | null> {
  const payments = await getPayments();
  const numeric = typeof id === 'number' ? id : Number(id);
  return payments.find((p) => p.id === numeric) || null;
}

export function computeMetrics(payments: Payment[]) {
  const recovered = payments.filter((p) => (p.recovery_status || '').toUpperCase() === 'SUCCESS');
  const atRisk = payments.filter((p) => (p.recovery_status || '').toUpperCase() !== 'SUCCESS');
  const recoveredAmount = recovered.reduce((sum, p) => sum + p.amount, 0);
  const atRiskAmount = atRisk.reduce((sum, p) => sum + p.amount, 0);
  const totalFailed = recovered.length + atRisk.length;
  const recoveryRate = totalFailed > 0 ? (recovered.length / totalFailed) * 100 : 0;
  const aiActions = payments.filter((p) => p.decision_source).length;

  return {
    revenueAtRisk: atRiskAmount,
    revenueRecovered: recoveredAmount,
    recoveryRate,
    opportunitiesCount: atRisk.length,
    aiActionsCount: aiActions,
    totalFailed,
  };
}

export async function isBackendAvailable(): Promise<boolean> {
  if (!API_BASE_URL) return false;
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 4000);
    const res = await fetch(`${API_BASE_URL}/health`, { signal: controller.signal });
    clearTimeout(timeout);
    return res.ok;
  } catch {
    return false;
  }
}
