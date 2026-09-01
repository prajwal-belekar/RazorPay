'use client';

import React from 'react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Sparkles, Cpu, CheckCircle2, RefreshCw } from 'lucide-react';

export function OllamaStatusCard({
  isAnalyzing = false,
}: {
  isAnalyzing?: boolean;
}) {
  const steps = [
    { label: 'Failure pattern context analyzed', done: true },
    { label: 'Customer transaction history evaluated', done: true },
    { label: 'Gateway timeout recovery window calculated', done: true },
    { label: 'Merchant Recovery DNA policy matched', done: true },
    { label: 'Strategy recommendation ready', done: !isAnalyzing },
  ];

  return (
    <Card className="p-4 border-ai-border/60 bg-gradient-to-br from-surface to-ai-bg/20 space-y-3">
      <div className="flex items-center justify-between border-b border-border/60 pb-2">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-ai/20 text-ai-light border border-ai/40">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-primaryText uppercase tracking-wider">LOCAL AI ENGINE</h4>
            <p className="text-[10px] text-secondaryText font-mono">Ollama Local Inference Service</p>
          </div>
        </div>

        <Badge variant="ai" size="sm">
          ● Connected
        </Badge>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono bg-surface-elevated/80 p-2.5 rounded-lg border border-border">
        <div>
          <span className="text-[10px] text-mutedText block">Model</span>
          <span className="font-bold text-primaryText">Llama 3.1 8B</span>
        </div>
        <div>
          <span className="text-[10px] text-mutedText block">Mode</span>
          <span className="font-bold text-ai-light">Local On-Prem</span>
        </div>
        <div>
          <span className="text-[10px] text-mutedText block">Latency</span>
          <span className="font-bold text-success">840ms</span>
        </div>
        <div>
          <span className="text-[10px] text-mutedText block">Status</span>
          <span className="font-bold text-success">Operational</span>
        </div>
      </div>

      <div className="space-y-1.5 pt-1 text-xs">
        <span className="text-[10px] font-mono text-mutedText uppercase tracking-wider block">
          High-Level Execution Pipeline
        </span>
        <div className="space-y-1 font-mono text-[11px]">
          {steps.map((step, idx) => (
            <div key={idx} className="flex items-center gap-2">
              {step.done ? (
                <CheckCircle2 className="h-3.5 w-3.5 text-success shrink-0" />
              ) : (
                <RefreshCw className="h-3.5 w-3.5 text-ai animate-spin shrink-0" />
              )}
              <span className={step.done ? 'text-secondaryText' : 'text-ai-light font-bold'}>
                {step.label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}
