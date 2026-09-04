export interface Payment {
  id: number;
  amount: number;
  failure_reason: string;
  customer_type: string;
  recommended_action: string | null;
  reason: string | null;
  confidence: number | null;
  decision_source: string | null;
  recovery_status: string | null;
  payment_status?: string | null;
  retry_count: number;
  previous_recovery_attempts?: number;
  created_at: string | null;
  payment_method?: string | null;
  razorpay_payment_id?: string | null;
  razorpay_order_id?: string | null;
  currency?: string | null;
  error_code?: string | null;
  gateway?: string | null;
  payment_timestamp?: string | null;
  // AI Action Firewall / Merchant Governance Guard fields
  firewall_decision?: string | null;
  firewall_reason?: string | null;
  firewall_policy_version?: string | null;
  firewall_checks?: ActionFirewallCheck[];
  firewall_evaluated_at?: string | null;
  proof?: {
    proof_id: string;
    transaction_id: string;
    razorpay_payment_id?: string | null;
    recovery_action: string;
    recovery_timestamp: string | null;
    recovered_amount: number;
    ai_confidence: number | null;
    policy_version: string | null;
    firewall_decision: string | null;
    execution_id: number;
    proof_payload: Record<string, unknown>;
    proof_hash: string;
    proof_status: 'VERIFIED' | 'NOT_VERIFIED';
    tx_hash?: string | null;
    block_number?: number | null;
    network?: string | null;
  } | null;
}

export type PaymentMethod = 'UPI' | 'Cards' | 'Net Banking' | 'Wallet' | 'N/A';

export type FailureReason = 'Bank Timeout' | string;

export type StrategyType = 
  | 'Retry' 
  | 'Payment Link' 
  | 'Reminder' 
  | 'Retry + Payment Link'
  | 'Smart Schedule';

export type RecoveryStatus = 
  | 'At Risk' 
  | 'Analyzing' 
  | 'Simulating' 
  | 'Approved' 
  | 'Recovered' 
  | 'Failed' 
  | 'Blocked' 
  | 'Pending Approval';

export interface Customer {
  id: string;
  name: string;
  email: string;
  phone: string;
  tier: 'VIP' | 'Returning' | 'New' | 'Regular';
  historicalSuccessRate: number;
}

export interface Transaction {
  id: string;
  customerId: string;
  customerName: string;
  amount: number;
  currency: string;
  paymentMethod: PaymentMethod;
  status: 'Success' | 'Failed' | 'Recovered' | 'Pending';
  failureReason?: FailureReason;
  failureCode?: string;
  createdAt: string;
  updatedAt: string;
  gateway: string;
  recoveryId?: string;
}

export interface StrategyOption {
  type: StrategyType;
  title: string;
  probability: number; // 0-100
  expectedRecovery: number;
  confidence: number; // 0-100
  recommendedDelayMinutes?: number;
  isAiRecommended?: boolean;
  explanation: string;
  roi: number; // multiplier e.g. 4.2x
}

export interface ActionFirewallCheck {
  id: string;
  name: string;
  description: string;
  status: 'PASSED' | 'FAILED' | 'WARNING';
  policyValue: string;
  actualValue: string;
}

export interface FirewallResult {
  approved: boolean;
  statusMessage: string;
  checks: ActionFirewallCheck[];
  evaluatedAt: string;
  policyVersion: string;
}

export interface TimelineEvent {
  id: string;
  timestamp: string;
  component: 'Detection Agent' | 'Prediction Engine' | 'Ollama AI' | 'Policy Firewall' | 'Razorpay Engine' | 'Blockchain Vault' | 'Learning Agent';
  status: 'info' | 'success' | 'warning' | 'error';
  title: string;
  description: string;
  metadata?: Record<string, string | number>;
}

export interface BlockchainProof {
  proofId: string;
  transactionId: string;
  amount: number;
  strategy: StrategyType;
  policyVersion: string;
  proofHash: string;
  policyHash?: string;
  timestamp: string;
  blockNumber?: number | null;
  verified: boolean;
  txHash?: string | null;
  network?: string | null;
  razorpayPaymentId?: string | null;
  recoveryAction?: string;
  recoveryTimestamp?: string | null;
  aiConfidence?: number | null;
  firewallDecision?: string | null;
  executionId?: number;
  proofPayload?: Record<string, unknown> | null;
  proofStatus?: 'VERIFIED' | 'NOT_VERIFIED' | 'ON_CHAIN';
}

export interface RecoveryCase {
  id: string;
  transactionId: string;
  customer: Customer;
  amount: number;
  paymentMethod: PaymentMethod;
  failureReason: FailureReason;
  recoveryProbability: number;
  expectedRecovery: number;
  strategy: StrategyType;
  aiConfidence: number;
  status: RecoveryStatus;
  createdAt: string;
  strategies: StrategyOption[];
  explanation: string;
  firewallResult: FirewallResult;
  timeline: TimelineEvent[];
  proof?: BlockchainProof;
  decisionSource?: string | null;
  retryCount?: number;
  reason?: string | null;
}

export interface Agent {
  id: string;
  name: string;
  role: 'Detection' | 'Prediction' | 'Recovery' | 'Simulation' | 'Policy' | 'Learning';
  status: 'ACTIVE' | 'LEARNING' | 'IDLE' | 'BUSY';
  currentTask: string;
  processedCount: number;
  successRate: number;
  avgLatencyMs: number;
  lastAction: string;
  lastActionTime: string;
  model: string;
}

export interface AgentActivityLog {
  id: string;
  timestamp: string;
  agentName: string;
  agentRole: string;
  message: string;
  status: 'success' | 'info' | 'warning' | 'error';
  metadata?: Record<string, unknown>;
}

export interface Anomaly {
  id: string;
  title: string;
  paymentMethod: PaymentMethod;
  previousRate: number;
  currentRate: number;
  percentageChange: number;
  revenueAtRisk: number;
  confidence: number;
  detectedAt: string;
  severity: 'HIGH' | 'CRITICAL' | 'MEDIUM';
  recommendedAction: string;
  affectedCount: number;
}

export interface SimulationConfig {
  paymentId: number;
  horizonDays: number;
  retryCount: number;
  selectedStrategies: StrategyType[];
}

export interface SimulationResult {
  strategy: StrategyType;
  expectedRecovery: number;
  probability: number;
  expectedRoi: number;
  timeToRecoverHours: number;
  successRateByMethod: Record<PaymentMethod, number>;
  isRecommended?: boolean;
  risk?: string;
  requiredAction?: string;
  reason?: string;
  predicted?: boolean;
}

export interface PolicyRule {
  id: string;
  key: string;
  title: string;
  description: string;
  value: number | string | boolean;
  type: 'number' | 'currency' | 'boolean' | 'select' | 'minutes';
  unit?: string;
  category: 'Autonomous' | 'Risk' | 'Timing' | 'Limits';
}

export interface PolicySet {
  version: string;
  status: 'Active' | 'Draft' | 'Archived';
  lastUpdated: string;
  hash: string;
  rules: PolicyRule[];
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  timestamp: string;
  type: 'anomaly' | 'recovery' | 'blockchain' | 'policy' | 'system';
  read: boolean;
  actionUrl?: string;
  actionText?: string;
}

export interface MerchantDNA {
  bestStrategy: StrategyType;
  bestRetryWindow: string;
  bestCustomerSegment: string;
  bestPaymentMethod: PaymentMethod;
  methodRates: Record<PaymentMethod, number>;
  topFactors: { factor: string; impact: number }[];
  learningDataPoints: number;
  modelAccuracy: number;
  lastTrainedAt: string;
}

export interface DashboardMetrics {
  revenueAtRisk: number;
  revenueAtRiskChange: number;
  revenueRecovered: number;
  revenueRecoveredChange: number;
  recoveryRate: number;
  recoveryRateChange: number;
  opportunitiesCount: number;
  opportunitiesChange: number;
  aiActionsCount: number;
  policyComplianceRate: number;
}

export interface CopilotMessage {
  id: string;
  sender: 'user' | 'assistant';
  timestamp: string;
  text: string;
  metricCard?: {
    value: string;
    label: string;
    change?: string;
  };
  chartData?: { name: string; value: number; benchmark?: number }[];
  tableData?: {
    headers: string[];
    rows: (string | number)[][];
  };
  actions?: { label: string; action: string }[];
}

export interface AIResponse<T = unknown> {
  success: boolean;
  data: T;
  latencyMs: number;
  model: string;
  timestamp: string;
}

export interface PassportAIDecision {
  action: string;
  confidence: number;
  recovery_probability: number;
  expected_recovery: number;
  risk_level: string;
  reason: string;
  decision_source: string;
  ai_decision_at: string;
}

export interface PassportFirewallCheck {
  name: string;
  passed: boolean;
}

export interface PassportFirewall {
  approved: boolean;
  action: string;
  risk_level: string;
  policy_version: string;
  reason: string;
  checks: PassportFirewallCheck[];
  evaluated_at: string;
}

export interface PassportRecovery {
  execution_id: number;
  action: string;
  execution_mode: string;
  status: string;
  simulated: boolean;
  provider: string | null;
  provider_reference_id: string | null;
  result_message: string;
  error: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface PassportHybridStep {
  action: string;
  status: string;
  recovered: boolean;
  passed_firewall: boolean;
  reason: string;
}

export interface PaymentPassport {
  payment: {
    payment_id: number;
    failure_reason: string;
    payment_status: string;
    recovery_status: string;
    ai_decision: PassportAIDecision;
    firewall: PassportFirewall;
    recovery: PassportRecovery;
    hybrid_steps: PassportHybridStep[];
    timestamp: string;
  };
}

export interface SyncRazorpayResult {
  success: boolean;
  source: string;
  fetched: number;
  created: number;
  updated: number;
  skipped: number;
  failed: number;
}
