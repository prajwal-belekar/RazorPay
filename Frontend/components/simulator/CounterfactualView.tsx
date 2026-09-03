'use client';

import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { formatCurrency } from '@/lib/formatters';
import { SimulationResult } from '@/types';
import { Sparkles, ArrowRight, XCircle, CheckCircle2 } from 'lucide-react';

export function CounterfactualView({
  amount = 18500,
  results,
  onSelectStrategy,
}: {
  amount?: number;
  results?: SimulationResult[];
  onSelectStrategy?: (strat: string) => void;
}) {
  const retry = results?.find((result) => result.strategy === 'Retry');
  const hybrid = results?.find((result) => result.strategy === 'Retry + Payment Link');
  const scenarios = [
    {
      title: 'WHAT IF WE DO NOTHING?',
      recovery: 0,
      loss: amount,
      probability: 0,
      status: 'EXPECTED LOSS',
      variant: 'danger' as const,
      color: 'text-danger',
    },
    {
      title: 'WHAT IF WE RETRY ONLY?',
      recovery: retry?.expectedRecovery ?? 0,
      loss: Math.max(0, amount - (retry?.expectedRecovery ?? 0)),
      probability: retry?.probability ?? 0,
      status: 'PARTIAL RECOVERY',
      variant: 'warning' as const,
      color: 'text-warning',
    },
    {
      title: 'WHAT IF WE USE HYBRID CASCADE?',
      recovery: hybrid?.expectedRecovery ?? 0,
      loss: Math.max(0, amount - (hybrid?.expectedRecovery ?? 0)),
      probability: hybrid?.probability ?? 0,
      status: 'OPTIMAL RECOVERY',
      variant: 'ai' as const,
      color: 'text-ai-light',
      isRecommended: true,
    },
  ];

  return (
    <Card className="p-5 border-ai-border/60 bg-surface-elevated/40 space-y-4">
      <div className="flex items-center justify-between border-b border-border/60 pb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-ai" />
          <h3 className="text-sm font-bold text-primaryText uppercase tracking-wider">
            Counterfactual &quot;What If?&quot; Analysis
          </h3>
        </div>
        <Badge variant="ai">Decision Tree Twin</Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono">
        {scenarios.map((sc, idx) => (
          <div
            key={idx}
            onClick={() => sc.isRecommended && onSelectStrategy?.('Retry + Payment Link')}
            className={`p-4 rounded-xl border space-y-3 transition-all cursor-pointer ${
              sc.isRecommended
                ? 'border-ai bg-ai-bg/20 shadow-glow hover:bg-ai-bg/30'
                : 'border-border bg-surface/60 hover:bg-surface-elevated'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-[11px] text-secondaryText">{sc.title}</span>
              <Badge variant={sc.variant} size="sm">{sc.status}</Badge>
            </div>

            <div className="space-y-1 py-1">
              <div className="flex justify-between">
                <span className="text-secondaryText">Expected Recovery:</span>
                <span className={`font-bold font-mono text-sm ${sc.color}`}>
                  {formatCurrency(sc.recovery)}
                </span>
              </div>
              <div className="flex justify-between text-[11px]">
                <span className="text-secondaryText">Probability:</span>
                <span className="text-primaryText font-semibold">{sc.probability}%</span>
              </div>
            </div>

            {sc.isRecommended && (
              <div className="pt-2 border-t border-border/40 text-[11px] text-ai-light font-bold flex items-center justify-between">
                <span>Expected Net Uplift: +{formatCurrency(sc.recovery)}</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </div>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}
