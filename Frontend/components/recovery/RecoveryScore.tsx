'use client';

import React from 'react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Sparkles, ShieldCheck, TrendingUp } from 'lucide-react';

export interface RecoveryScoreProps {
  score?: number; // 0-100
  factors?: {
    customerHistory: number;
    failurePattern: number;
    paymentMethod: number;
    timing: number;
    amountRisk: number;
  };
  compact?: boolean;
}

export function RecoveryScore({
  score = 91,
  factors = {
    customerHistory: 94,
    failurePattern: 92,
    paymentMethod: 88,
    timing: 95,
    amountRisk: 81,
  },
  compact = false,
}: RecoveryScoreProps) {
  if (compact) {
    return (
      <div className="inline-flex items-center gap-1.5 font-mono text-xs">
        <span className="font-bold text-success text-sm">{score}</span>
        <span className="text-[10px] text-mutedText">/ 100</span>
        <Badge variant={score >= 85 ? 'success' : score >= 70 ? 'warning' : 'danger'} size="sm">
          {score >= 85 ? 'HIGH RECOVERY' : 'MEDIUM'}
        </Badge>
      </div>
    );
  }

  return (
    <Card className="p-4 border-ai-border/40 bg-surface-elevated/60 space-y-3">
      <div className="flex items-center justify-between border-b border-border/60 pb-2">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-ai" />
          <h4 className="text-xs font-bold text-primaryText">RECOVERY SCORE</h4>
        </div>
        <div className="flex items-baseline gap-1 font-mono">
          <span className="text-xl font-bold text-success">{score}</span>
          <span className="text-xs text-mutedText">/ 100</span>
        </div>
      </div>

      <div className="space-y-2 text-xs font-mono">
        <div className="space-y-1">
          <div className="flex justify-between text-[11px]">
            <span className="text-secondaryText">Customer History</span>
            <span className="text-success font-semibold">{factors.customerHistory}%</span>
          </div>
          <div className="h-1.5 w-full bg-surface rounded-full overflow-hidden">
            <div className="h-full bg-success rounded-full" style={{ width: `${factors.customerHistory}%` }} />
          </div>
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-[11px]">
            <span className="text-secondaryText">Failure Pattern</span>
            <span className="text-success font-semibold">{factors.failurePattern}%</span>
          </div>
          <div className="h-1.5 w-full bg-surface rounded-full overflow-hidden">
            <div className="h-full bg-success rounded-full" style={{ width: `${factors.failurePattern}%` }} />
          </div>
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-[11px]">
            <span className="text-secondaryText">Payment Method Yield</span>
            <span className="text-ai-light font-semibold">{factors.paymentMethod}%</span>
          </div>
          <div className="h-1.5 w-full bg-surface rounded-full overflow-hidden">
            <div className="h-full bg-ai rounded-full" style={{ width: `${factors.paymentMethod}%` }} />
          </div>
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-[11px]">
            <span className="text-secondaryText">Optimal Timing</span>
            <span className="text-success font-semibold">{factors.timing}%</span>
          </div>
          <div className="h-1.5 w-full bg-surface rounded-full overflow-hidden">
            <div className="h-full bg-success rounded-full" style={{ width: `${factors.timing}%` }} />
          </div>
        </div>
      </div>
    </Card>
  );
}
