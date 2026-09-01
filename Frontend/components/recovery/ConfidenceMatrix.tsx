'use client';

import React from 'react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { ShieldCheck, AlertTriangle, CheckCircle2, Lock } from 'lucide-react';

export function ConfidenceMatrix({
  confidence = 93,
  impactAmount = 18500,
}: {
  confidence?: number;
  impactAmount?: number;
}) {
  const isHighConfidence = confidence >= 85;
  const isHighImpact = impactAmount >= 50000;

  return (
    <Card className="p-4 space-y-3">
      <div className="flex items-center justify-between border-b border-border/60 pb-2">
        <h4 className="text-xs font-bold text-primaryText uppercase tracking-wider">
          AI Confidence vs Business Impact Governance
        </h4>
        <span className="text-[10px] font-mono text-mutedText">Policy Matrix</span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs font-mono relative p-1 bg-surface-elevated/40 rounded-lg border border-border">
        {/* Quadrant 1: High Impact / Low Confidence -> REVIEW */}
        <div
          className={`p-3 rounded-md border flex flex-col justify-between ${
            !isHighConfidence && isHighImpact
              ? 'border-warning bg-warning-bg/40 text-warning font-bold shadow-glow'
              : 'border-border/40 bg-surface/40 text-secondaryText'
          }`}
        >
          <div className="flex justify-between items-center text-[10px]">
            <span>HIGH IMPACT</span>
            <span>LOW CONF</span>
          </div>
          <div className="text-sm font-bold text-warning mt-2">HUMAN REVIEW</div>
          <span className="text-[10px] text-mutedText">Manual Sign-off Required</span>
        </div>

        {/* Quadrant 2: High Impact / High Confidence -> AUTONOMOUS */}
        <div
          className={`p-3 rounded-md border flex flex-col justify-between ${
            isHighConfidence && isHighImpact
              ? 'border-ai bg-ai-bg/40 text-ai-light font-bold shadow-glow'
              : 'border-border/40 bg-surface/40 text-secondaryText'
          }`}
        >
          <div className="flex justify-between items-center text-[10px]">
            <span>HIGH IMPACT</span>
            <span>HIGH CONF</span>
          </div>
          <div className="text-sm font-bold text-ai-light mt-2">AUTONOMOUS</div>
          <span className="text-[10px] text-mutedText">Policy Cap Verified</span>
        </div>

        {/* Quadrant 3: Low Impact / Low Confidence -> BLOCK */}
        <div
          className={`p-3 rounded-md border flex flex-col justify-between ${
            !isHighConfidence && !isHighImpact
              ? 'border-danger bg-danger-bg/40 text-danger font-bold shadow-glow'
              : 'border-border/40 bg-surface/40 text-secondaryText'
          }`}
        >
          <div className="flex justify-between items-center text-[10px]">
            <span>LOW IMPACT</span>
            <span>LOW CONF</span>
          </div>
          <div className="text-sm font-bold text-danger mt-2">ACTION BLOCKED</div>
          <span className="text-[10px] text-mutedText">Unsafe Recovery Option</span>
        </div>

        {/* Quadrant 4: Low Impact / High Confidence -> APPROVE */}
        <div
          className={`p-3 rounded-md border flex flex-col justify-between ${
            isHighConfidence && !isHighImpact
              ? 'border-success bg-success-bg/40 text-success font-bold shadow-glow'
              : 'border-border/40 bg-surface/40 text-secondaryText'
          }`}
        >
          <div className="flex justify-between items-center text-[10px]">
            <span>LOW IMPACT</span>
            <span>HIGH CONF</span>
          </div>
          <div className="text-sm font-bold text-success mt-2">AUTONOMOUS APPROVE</div>
          <span className="text-[10px] text-mutedText">Auto Gateway Retry</span>
        </div>
      </div>
    </Card>
  );
}
