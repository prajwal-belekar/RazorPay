'use client';

import React, { useMemo } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { formatCurrency, formatDate } from '@/lib/formatters';
import { useRecoveryEngine } from '@/context/RecoveryEngineContext';
import { CheckCircle2, ShieldCheck } from 'lucide-react';

export function RecentRecoveriesTimeline() {
  const { cases, isLoading } = useRecoveryEngine();

  const recentItems = useMemo(() => {
    const recovered = cases
      .filter((c) => c.status === 'Recovered')
      .sort((a, b) => (b.createdAt || '').localeCompare(a.createdAt || ''));
    return recovered.slice(0, 5);
  }, [cases]);

  return (
    <Card className="p-0">
      <CardHeader className="flex flex-row items-center justify-between border-b border-border/60 pb-3">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-success" />
          <CardTitle>Recent Autonomous Recoveries</CardTitle>
        </div>
        <span className="text-xs text-mutedText font-mono">From Backend Records</span>
      </CardHeader>

      <CardContent className="p-4 space-y-3">
        {isLoading ? (
          <div className="p-4 text-center text-xs text-secondaryText animate-pulse">
            Loading payments...
          </div>
        ) : recentItems.length === 0 ? (
          <div className="p-4 text-center text-xs text-secondaryText">
            No recovered payments yet.
          </div>
        ) : (
          recentItems.map((item, idx) => (
            <div
              key={item.id || idx}
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
                    <span className="font-mono text-[10px] text-mutedText">({item.id})</span>
                  </div>
                  <p className="text-[11px] text-secondaryText">
                    Action: {item.strategy || 'N/A'} • Status: {item.status || 'N/A'}
                  </p>
                  <div className="flex items-center gap-1.5 text-[10px] text-mutedText font-mono pt-0.5">
                    <ShieldCheck className="h-3 w-3 text-mutedText" />
                    <span>Proof: Not available</span>
                    {item.createdAt && (
                      <span className="text-mutedText">• {formatDate(item.createdAt)}</span>
                    )}
                  </div>
                </div>
              </div>

              {item.createdAt && (
                <span className="text-[10px] text-mutedText whitespace-nowrap">
                  {formatDate(item.createdAt, { includeTime: true })}
                </span>
              )}
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
