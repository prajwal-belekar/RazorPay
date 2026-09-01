'use client';

import React, { useState } from 'react';
import { CheckCircle2, ShieldCheck, Sparkles, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

export function AIStatusIndicator() {
  const [isOpen, setIsOpen] = useState(false);

  const services = [
    { name: 'Ollama LLM (Llama3.1-8B)', status: 'Connected', isHealthy: true },
    { name: 'Prediction Engine', status: 'Healthy (94.2%)', isHealthy: true },
    { name: 'Recovery Agent', status: 'Healthy', isHealthy: true },
    { name: 'Blockchain Vault', status: 'Polygon Devnet Connected', isHealthy: true },
    { name: 'Razorpay Sandbox', status: 'Active Sandbox', isHealthy: true },
  ];

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 rounded-full border border-ai-border/60 bg-ai-bg/30 px-3 py-1 text-xs text-ai-light hover:bg-ai-bg/60 transition-colors"
      >
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-ai opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-ai"></span>
        </span>
        <span className="font-medium text-[11px] hidden sm:inline">AI Operational</span>
        <ChevronDown className={cn("h-3 w-3 text-ai-light transition-transform", isOpen && "rotate-180")} />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 top-full mt-2 z-50 w-72 rounded-lg border border-border bg-surface-elevated p-4 shadow-card animate-in fade-in slide-in-from-top-2 duration-150">
            <div className="flex items-center justify-between border-b border-border/60 pb-2.5 mb-3">
              <div className="flex items-center gap-1.5">
                <Sparkles className="h-4 w-4 text-ai" />
                <span className="text-xs font-semibold text-primaryText">RecoverAI AI Systems</span>
              </div>
              <span className="inline-flex items-center gap-1 rounded-full bg-success-bg px-2 py-0.5 text-[10px] text-success border border-success-border font-medium">
                <span className="h-1.5 w-1.5 rounded-full bg-success"></span>
                Operational
              </span>
            </div>

            <div className="space-y-2 text-xs">
              {services.map((svc, idx) => (
                <div key={idx} className="flex items-center justify-between py-1">
                  <span className="text-secondaryText text-[11px]">{svc.name}</span>
                  <div className="flex items-center gap-1 text-[11px] text-success">
                    <CheckCircle2 className="h-3 w-3" />
                    <span>{svc.status}</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-3 pt-2.5 border-t border-border/60 flex items-center justify-between text-[10px] text-mutedText">
              <span className="flex items-center gap-1">
                <ShieldCheck className="h-3 w-3 text-ai" />
                Firewall Guard Active
              </span>
              <span>Latency: 120ms</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
