import {
  AlertTriangle,
  Search,
  Brain,
  Cpu,
  ShieldCheck,
  Zap,
  CheckCircle2,
  Lock,
  Sparkles,
  XCircle,
  LucideIcon,
} from 'lucide-react';

export type RecoveryStage =
  | 'idle'
  | 'detecting'
  | 'analyzing'
  | 'predicting'
  | 'simulating'
  | 'validating'
  | 'executing'
  | 'recovered'
  | 'verified'
  | 'learning'
  | 'failed';

export interface StageMetadata {
  stage: RecoveryStage;
  visualIndex: number; // 0-8 visual step mapping
  label: string;
  title: string;
  description: string;
  detail: string;
  icon: LucideIcon;
  durationMs: number;
  activeAgentRole: 'Detection' | 'Prediction' | 'Recovery' | 'Simulation' | 'Policy' | 'Learning';
  activeAgentName: string;
  orbMode: 'idle' | 'detecting' | 'analyzing' | 'predicting' | 'simulating' | 'validating' | 'executing' | 'recovered' | 'verified' | 'learning' | 'failed';
  colorToken: string;
  accentHex: string;
}

export const CANONICAL_STAGES: RecoveryStage[] = [
  'idle',
  'detecting',
  'analyzing',
  'predicting',
  'simulating',
  'validating',
  'executing',
  'recovered',
  'verified',
  'learning',
  'failed',
];

export const VISUAL_LIFECYCLE_STEPS = [
  { id: 'detect', label: 'DETECT', stage: 'detecting' as RecoveryStage, icon: AlertTriangle },
  { id: 'analyze', label: 'ANALYZE', stage: 'analyzing' as RecoveryStage, icon: Search },
  { id: 'predict', label: 'PREDICT', stage: 'predicting' as RecoveryStage, icon: Brain },
  { id: 'simulate', label: 'SIMULATE', stage: 'simulating' as RecoveryStage, icon: Cpu },
  { id: 'validate', label: 'VALIDATE', stage: 'validating' as RecoveryStage, icon: ShieldCheck },
  { id: 'execute', label: 'EXECUTE', stage: 'executing' as RecoveryStage, icon: Zap },
  { id: 'recover', label: 'RECOVER', stage: 'recovered' as RecoveryStage, icon: CheckCircle2 },
  { id: 'prove', label: 'PROVE', stage: 'verified' as RecoveryStage, icon: Lock },
  { id: 'learn', label: 'LEARN', stage: 'learning' as RecoveryStage, icon: Sparkles },
];

export const STAGE_METADATA_MAP: Record<RecoveryStage, StageMetadata> = {
  idle: {
    stage: 'idle',
    visualIndex: 0,
    label: 'Ready',
    title: 'Engine Idle',
    description: 'Autonomous Recovery Engine active and monitoring Razorpay webhooks.',
    detail: 'Standing by for incoming payment failure signals.',
    icon: Search,
    durationMs: 1000,
    activeAgentRole: 'Detection',
    activeAgentName: 'Detection Agent',
    orbMode: 'idle',
    colorToken: 'text-mutedText',
    accentHex: '#3F3F46',
  },
  detecting: {
    stage: 'detecting',
    visualIndex: 0,
    label: 'Detecting Risk',
    title: 'Payment Failure Detected',
    description: 'Razorpay webhook received: TXN-82931 failed (UPI Bank Timeout).',
    detail: '₹18,500 exposed revenue at risk across merchant checkout.',
    icon: AlertTriangle,
    durationMs: 800,
    activeAgentRole: 'Detection',
    activeAgentName: 'Detection Agent',
    orbMode: 'detecting',
    colorToken: 'text-warning',
    accentHex: '#F59E0B',
  },
  analyzing: {
    stage: 'analyzing',
    visualIndex: 1,
    label: 'LLM Context Analysis',
    title: 'Local Ollama LLM Reasoning',
    description: 'Analyzing failure code (UPI_TIMEOUT) and customer tier history.',
    detail: 'Llama 3.1 8B inspecting customer VIP status and retry velocity.',
    icon: Search,
    durationMs: 1200,
    activeAgentRole: 'Recovery',
    activeAgentName: 'Recovery Agent (Ollama)',
    orbMode: 'analyzing',
    colorToken: 'text-ai-light',
    accentHex: '#8B5CF6',
  },
  predicting: {
    stage: 'predicting',
    visualIndex: 2,
    label: 'Predicting Yield',
    title: 'Recovery Yield Prediction',
    description: 'ML model predicting high recoverability probability.',
    detail: 'Yield score 91/100 calculated for instant delayed retry + payment link.',
    icon: Brain,
    durationMs: 1000,
    activeAgentRole: 'Prediction',
    activeAgentName: 'Prediction Engine',
    orbMode: 'predicting',
    colorToken: 'text-info-light',
    accentHex: '#3B82F6',
  },
  simulating: {
    stage: 'simulating',
    visualIndex: 3,
    label: 'Digital Twin Monte Carlo',
    title: 'Simulating Recovery Twins',
    description: 'Running Monte Carlo scenarios for Retry vs Payment Link vs Hybrid.',
    detail: 'Hybrid strategy predicted: ₹17,800 expected recovery @ 91% success.',
    icon: Cpu,
    durationMs: 1500,
    activeAgentRole: 'Simulation',
    activeAgentName: 'Digital Twin Agent',
    orbMode: 'simulating',
    colorToken: 'text-ai-light',
    accentHex: '#A855F7',
  },
  validating: {
    stage: 'validating',
    visualIndex: 4,
    label: 'AI Action Firewall',
    title: 'Validating Governance Policy',
    description: 'Evaluating Policy v2.4 (Limits, Retry cooldown, Risk cap).',
    detail: 'Auto-recovery approved: ₹18,500 <= ₹25,000 limit, 93% confidence >= 85%.',
    icon: ShieldCheck,
    durationMs: 1200,
    activeAgentRole: 'Policy',
    activeAgentName: 'AI Action Firewall',
    orbMode: 'validating',
    colorToken: 'text-success',
    accentHex: '#10B981',
  },
  executing: {
    stage: 'executing',
    visualIndex: 5,
    label: 'Gateway Execution',
    title: 'Executing Razorpay Smart Recovery',
    description: 'Triggering Razorpay delayed retry API with dynamic UPI route.',
    detail: 'Simulated API response 200 OK from Razorpay gateway.',
    icon: Zap,
    durationMs: 1200,
    activeAgentRole: 'Recovery',
    activeAgentName: 'Recovery Agent',
    orbMode: 'executing',
    colorToken: 'text-warning',
    accentHex: '#F59E0B',
  },
  recovered: {
    stage: 'recovered',
    visualIndex: 6,
    label: 'Revenue Recovered',
    title: 'Payment Successfully Recovered',
    description: '₹18,500 successfully settled to merchant account!',
    detail: 'Funds recovered in 4.2 seconds without customer drop-off.',
    icon: CheckCircle2,
    durationMs: 1000,
    activeAgentRole: 'Recovery',
    activeAgentName: 'Recovery Agent',
    orbMode: 'recovered',
    colorToken: 'text-success',
    accentHex: '#10B981',
  },
  verified: {
    stage: 'verified',
    visualIndex: 7,
    label: 'Trust Center Proof',
    title: 'Cryptographic Proof Generated',
    description: 'Decision proof recorded on Polygon Devnet (Hash: 0x8a91...72fc).',
    detail: 'Immutable verification receipt ready for audit in Trust Center.',
    icon: Lock,
    durationMs: 1200,
    activeAgentRole: 'Policy',
    activeAgentName: 'Policy Firewall Agent',
    orbMode: 'verified',
    colorToken: 'text-ai-light',
    accentHex: '#6366F1',
  },
  learning: {
    stage: 'learning',
    visualIndex: 8,
    label: 'Merchant DNA Updated',
    title: 'Updating Merchant Recovery DNA',
    description: 'Feeding recovery outcome back into XGBoost feature store.',
    detail: 'UPI success rate model updated (+1.4% confidence uplift).',
    icon: Sparkles,
    durationMs: 1000,
    activeAgentRole: 'Learning',
    activeAgentName: 'Learning Agent',
    orbMode: 'learning',
    colorToken: 'text-success',
    accentHex: '#10B981',
  },
  failed: {
    stage: 'failed',
    visualIndex: 0,
    label: 'Recovery Blocked',
    title: 'Human Review Required',
    description: 'Action Firewall flagged transaction for manual merchant review.',
    detail: 'Exceeds policy threshold or insufficient AI confidence.',
    icon: XCircle,
    durationMs: 1000,
    activeAgentRole: 'Policy',
    activeAgentName: 'AI Action Firewall',
    orbMode: 'failed',
    colorToken: 'text-danger',
    accentHex: '#EF4444',
  },
};

export const DEMO_STAGE_SEQUENCE: RecoveryStage[] = [
  'detecting',
  'analyzing',
  'predicting',
  'simulating',
  'validating',
  'executing',
  'recovered',
  'verified',
  'learning',
];

export function getStageMetadata(stage: RecoveryStage): StageMetadata {
  return STAGE_METADATA_MAP[stage] || STAGE_METADATA_MAP.idle;
}

export function getVisualStageIndex(stage: RecoveryStage): number {
  return STAGE_METADATA_MAP[stage]?.visualIndex ?? 0;
}
