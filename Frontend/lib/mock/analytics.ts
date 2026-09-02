import { MerchantDNA } from '@/types';

export const mockMerchantDNA: MerchantDNA = {
  bestStrategy: 'Retry + Payment Link',
  bestRetryWindow: '15 minutes',
  bestCustomerSegment: 'Returning Customers',
  bestPaymentMethod: 'UPI',
  methodRates: {
    UPI: 82,
    Cards: 63,
    'Net Banking': 71,
    Wallet: 76,
    'N/A': 0,
  },
  topFactors: [
    { factor: 'Customer Transaction History', impact: 38 },
    { factor: 'Gateway Failure Subtype (Timeout vs Limits)', impact: 29 },
    { factor: 'Optimal Retry Cooldown Window', impact: 21 },
    { factor: 'Time of Day & Channel Multi-touch', impact: 12 },
  ],
  learningDataPoints: 12840,
  modelAccuracy: 94.2,
  lastTrainedAt: '2026-09-02T04:00:00Z',
};

export const mockStrategyPerformance = [
  { strategy: 'Retry', attempts: 1840, success: 1150, successRate: 62.5, recoveredAmount: 920000, avgRecovery: 800 },
  { strategy: 'Payment Link', attempts: 920, success: 533, successRate: 58.0, recoveredAmount: 480000, avgRecovery: 900 },
  { strategy: 'Reminder', attempts: 640, success: 346, successRate: 54.1, recoveredAmount: 240000, avgRecovery: 693 },
  { strategy: 'Retry + Payment Link', attempts: 421, success: 347, successRate: 82.4, recoveredAmount: 230000, avgRecovery: 662 },
];

export const mockFailureAnalysis = [
  { reason: 'Bank Timeout', count: 482, percent: 37.5, primaryMethod: 'UPI' },
  { reason: 'Insufficient Funds', count: 320, percent: 24.9, primaryMethod: 'Cards' },
  { reason: 'Authentication Failed', count: 240, percent: 18.7, primaryMethod: 'Net Banking' },
  { reason: 'Network Drop', count: 142, percent: 11.1, primaryMethod: 'UPI' },
  { reason: 'Limit Exceeded', count: 100, percent: 7.8, primaryMethod: 'Cards' },
];
