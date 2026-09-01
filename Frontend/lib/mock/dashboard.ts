import { DashboardMetrics, Anomaly } from '@/types';

export const mockDashboardMetrics: DashboardMetrics = {
  revenueAtRisk: 2840000, // ₹28.4L
  revenueAtRiskChange: 12.4,
  revenueRecovered: 1870000, // ₹18.7L
  revenueRecoveredChange: 24.8,
  recoveryRate: 65.8,
  recoveryRateChange: 8.2,
  opportunitiesCount: 1284,
  opportunitiesChange: 14.3,
  aiActionsCount: 3821,
  policyComplianceRate: 98.4,
};

export const mockRevenueOverviewData = [
  { date: 'Aug 27', revenueAtRisk: 210000, revenueRecovered: 130000, totalFailed: 340000 },
  { date: 'Aug 28', revenueAtRisk: 240000, revenueRecovered: 155000, totalFailed: 395000 },
  { date: 'Aug 29', revenueAtRisk: 190000, revenueRecovered: 142000, totalFailed: 332000 },
  { date: 'Aug 30', revenueAtRisk: 280000, revenueRecovered: 198000, totalFailed: 478000 },
  { date: 'Aug 31', revenueAtRisk: 310000, revenueRecovered: 220000, totalFailed: 530000 },
  { date: 'Sep 01', revenueAtRisk: 260000, revenueRecovered: 180000, totalFailed: 440000 },
  { date: 'Sep 02', revenueAtRisk: 240000, revenueRecovered: 170000, totalFailed: 410000 },
];

export const mockRevenueLeakAnomaly: Anomaly = {
  id: 'ANOMALY-104',
  title: 'UPI Payment Failure Rate Spike',
  paymentMethod: 'UPI',
  previousRate: 8.0,
  currentRate: 19.0,
  percentageChange: 137.5,
  revenueAtRisk: 320000, // ₹3.2L
  confidence: 94,
  detectedAt: '2026-09-02T08:15:00Z',
  severity: 'HIGH',
  recommendedAction: 'Apply 15-min delayed retry with dynamic fallback payment link',
  affectedCount: 142,
};
