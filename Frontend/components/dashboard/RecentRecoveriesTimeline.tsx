'use client';

import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { formatCurrency } from '@/lib/formatters';
import { CheckCircle2, ShieldCheck, ArrowRight } from 'lucide-react';

export function RecentRecoveriesTimeline() {
  const recentItems = [
    {
      amount: 18500,
      strategy: 'Retry after 15 minutes',
      timeAgo: '2 minutes ago',
      txId: 'TXN-82931',
      hash: '0x8a91...72fc',
    },
    {
      amount: 42000,
      strategy: 'Payment Link',
      timeAgo: '8 minutes ago',
      txId: 'TXN-82932',
      hash: '0x4b12...4e10',
    },
    {
      amount: 7200,
      strategy: 'Soft Push Reminder',
      timeAgo: '12 minutes ago',
      txId: 'TXN-82933',
      hash: '0x718a...203a',
    },
    {
      amount: 24500,
      strategy: 'Retry + Payment Link',
      timeAgo: '25 minutes ago',
      txId: 'TXN-82935',
      hash: '0x1029...3810',
    },
  ];

  return (
    <Card className="p-0">
      <CardHeader className="flex flex-row items-center justify-between border-b border-border/60 pb-3">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-success" />
          <CardTitle>Recent Autonomous Recoveries</CardTitle>
        </div>
        <span className="text-xs text-mutedText font-mono">Live Activity Stream</span>
      </CardHeader>

      <CardContent className="p-4 space-y-3">
        {recentItems.map((item, idx) => (
          <div
            key={idx}
            className="flex items-start justify-between p-3 rounded-lg border border-border/60 bg-surface-elevated/40 text-xs hover:border-border/90 transition-colors"
          >
            <div className="flex items-start gap-3">
              <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-success-bg border border-success-border text-success">
                ✓
              </div>
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-success font-mono text-sm">
                    {formatCurrency(item.amount)} recovered
                  </span>
                  <span className="font-mono text-[10px] text-mutedText">({item.txId})</span>
                </div>
                <p className="text-[11px] text-secondaryText">{item.strategy}</p>
                <div className="flex items-center gap-1.5 text-[10px] text-ai-light font-mono pt-0.5">
                  <ShieldCheck className="h-3 w-3" />
                  <span>Proof: {item.hash}</span>
                </div>
              </div>
            </div>

            <span className="text-[10px] text-mutedText whitespace-nowrap">{item.timeAgo}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
