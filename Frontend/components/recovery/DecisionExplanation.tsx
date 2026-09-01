'use client';

import React from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { formatCurrency } from '@/lib/formatters';
import { Sparkles, CheckCircle2, ShieldCheck, Cpu } from 'lucide-react';

export interface DecisionExplanationProps {
  strategy?: string;
  probability?: number;
  confidence?: number;
  expectedRecovery?: number;
  reasons?: string[];
  className?: string;
}

export const DEFAULT_EXPLANATION_REASONS = [
  'Temporary gateway timeout detected (high retry success pattern)',
  'Returning customer with 94% historical payment completion rate',
  'Amount ₹18,500 is within merchant auto-recovery policy threshold (₹25,000 cap)',
  'Monte Carlo simulation verified Retry + Payment Link yields +₹3,700 vs retry alone',
  'AI confidence (93%) exceeds policy firewall minimum threshold (85%)',
];

export function DecisionExplanation({
  strategy = 'Retry + Payment Link',
  probability = 91,
  confidence = 93,
  expectedRecovery = 17800,
  reasons = DEFAULT_EXPLANATION_REASONS,
  className = '',
}: DecisionExplanationProps) {
  return (
    <Card className={`p-5 border-ai-border/60 bg-gradient-to-br from-surface to-ai-bg/15 shadow-glow space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/60 pb-3">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-ai/20 text-ai-light border border-ai/40">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold font-mono text-ai-light uppercase tracking-wider">
              AI Recovery Decision
            </h3>
            <p className="text-xs font-bold text-primaryText">{strategy}</p>
          </div>
        </div>

        <Badge variant="ai" size="sm" className="w-fit">
          <Cpu className="h-3 w-3 mr-1" />
          Ollama Llama 3.1 8B Verified
        </Badge>
      </div>

      {/* Primary Decision Metrics */}
      <div className="grid grid-cols-3 gap-3 text-xs font-mono bg-surface-elevated/60 p-3 rounded-lg border border-border/60">
        <div>
          <span className="text-[10px] text-mutedText block uppercase">Probability</span>
          <span className="text-sm font-bold text-success">{probability}%</span>
        </div>
        <div>
          <span className="text-[10px] text-mutedText block uppercase">AI Confidence</span>
          <span className="text-sm font-bold text-ai-light">{confidence}%</span>
        </div>
        <div>
          <span className="text-[10px] text-mutedText block uppercase">Expected Recovery</span>
          <span className="text-sm font-bold text-primaryText">{formatCurrency(expectedRecovery)}</span>
        </div>
      </div>

      {/* WHY Section */}
      <div className="space-y-2 pt-1">
        <div className="flex items-center gap-1.5 text-xs font-bold text-primaryText">
          <ShieldCheck className="h-3.5 w-3.5 text-success" />
          <span>WHY DID RECOVERAI CHOOSE THIS?</span>
        </div>

        <ul className="space-y-1.5 text-xs text-secondaryText font-sans">
          {reasons.map((reason, idx) => (
            <li key={idx} className="flex items-start gap-2 bg-surface/40 p-2 rounded border border-border/40">
              <CheckCircle2 className="h-3.5 w-3.5 text-success shrink-0 mt-0.5" />
              <span className="leading-snug">{reason}</span>
            </li>
          ))}
        </ul>
      </div>
    </Card>
  );
}
