import { SimulationResult } from '@/types';

export const mockDefaultSimulationResults: SimulationResult[] = [
  {
    strategy: 'Retry',
    expectedRecovery: 1420000, // ₹14.2L
    probability: 62.5,
    expectedRoi: 3.4,
    timeToRecoverHours: 0.5,
    successRateByMethod: {
      UPI: 74,
      Cards: 48,
      'Net Banking': 60,
      Wallet: 68,
      'N/A': 0,
    },
  },
  {
    strategy: 'Payment Link',
    expectedRecovery: 1180000, // ₹11.8L
    probability: 58.0,
    expectedRoi: 2.8,
    timeToRecoverHours: 4.2,
    successRateByMethod: {
      UPI: 65,
      Cards: 55,
      'Net Banking': 52,
      Wallet: 60,
      'N/A': 0,
    },
  },
  {
    strategy: 'Reminder',
    expectedRecovery: 1290000, // ₹12.9L
    probability: 54.2,
    expectedRoi: 2.5,
    timeToRecoverHours: 12.0,
    successRateByMethod: {
      UPI: 58,
      Cards: 50,
      'Net Banking': 48,
      Wallet: 52,
      'N/A': 0,
    },
  },
  {
    strategy: 'Retry + Payment Link',
    expectedRecovery: 1870000, // ₹18.7L
    probability: 82.4,
    expectedRoi: 5.6,
    timeToRecoverHours: 1.5,
    successRateByMethod: {
      UPI: 88,
      Cards: 78,
      'Net Banking': 80,
      Wallet: 82,
      'N/A': 0,
    },
    isRecommended: true,
  },
];
