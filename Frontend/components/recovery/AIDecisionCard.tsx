'use client';

import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { formatCurrency } from '@/lib/formatters';
import { RecoveryCase } from '@/types';
import { Sparkles, Brain, CheckCircle2, TrendingUp } from 'lucide-react';

export function AIDecisionCard({ recoveryCase }: { recoveryCase: RecoveryCase }) {
  return (
    <Card className="border-ai-border/60 bg-gradient-to-br from-surface to-ai-bg/15 relative overflow-hidden shadow-glow">
      <CardHeader className="flex flex-row items-center justify-between border-b border-border/60 pb-3">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-ai/20 text-ai-light border border-ai/40">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <CardTitle className="text-ai-light font-bold">AI Recovery Decision</CardTitle>
            <p className="text-xs text-secondaryText">Ollama LLM & Risk Engine Inference</p>
          </div>
        </div>

        <Badge variant="ai" size="sm">
          Ollama Llama3.1-8B
        </Badge>
      </CardHeader>

      <CardContent className="pt-4 space-y-4">
        {/* Main Key Metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 rounded-lg bg-surface-elevated/80 border border-border/80 p-3.5 text-xs">
          <div>
            <span className="text-secondaryText text-[11px]">Recommended Strategy</span>
            <div className="font-bold text-sm text-primaryText mt-0.5 flex items-center gap-1">
              <span>{recoveryCase.strategy}</span>
              <CheckCircle2 className="h-3.5 w-3.5 text-success" />
            </div>
          </div>

          <div>
            <span className="text-secondaryText text-[11px]">Recovery Probability</span>
            <div className="font-bold font-mono text-sm text-success mt-0.5">
              {recoveryCase.recoveryProbability}%
            </div>
          </div>

          <div>
            <span className="text-secondaryText text-[11px]">AI Confidence</span>
            <div className="font-bold font-mono text-sm text-ai-light mt-0.5">
              {recoveryCase.aiConfidence}%
            </div>
          </div>

          <div>
            <span className="text-secondaryText text-[11px]">Expected Recovery</span>
            <div className="font-bold font-mono text-sm text-success mt-0.5">
              {formatCurrency(recoveryCase.expectedRecovery)}
            </div>
          </div>
        </div>

        {/* Short User-Facing Explanation */}
        <div className="rounded-lg bg-surface/80 border border-border/60 p-3 text-xs space-y-1">
          <div className="flex items-center gap-1.5 text-secondaryText text-[11px] font-semibold">
            <Brain className="h-3.5 w-3.5 text-ai" />
            <span>AI Reasoning Explanation</span>
          </div>
          <p className="text-primaryText text-xs leading-relaxed italic">
            &quot;{recoveryCase.explanation}&quot;
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
