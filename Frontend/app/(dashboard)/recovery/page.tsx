'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { RecoveryOpportunitiesTable } from '@/components/dashboard/RecoveryOpportunitiesTable';
import { mockRecoveryCases } from '@/lib/mock/recovery';
import { formatCurrency, formatPercent } from '@/lib/formatters';
import { RotateCcw, TrendingUp, Zap, ShieldCheck } from 'lucide-react';
import { useLiveDemo } from '@/hooks/use-live-demo';

export default function RecoveryPage() {
  const demoState = useLiveDemo();

  const totalCases = mockRecoveryCases.length;
  const totalAmount = mockRecoveryCases.reduce((acc, c) => acc + c.amount, 0);
  const totalRecoverable = mockRecoveryCases.reduce((acc, c) => acc + c.expectedRecovery, 0);
  const avgRate = mockRecoveryCases.reduce((acc, c) => acc + c.recoveryProbability, 0) / totalCases;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/60 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-primaryText">
            Recovery Opportunities
          </h1>
          <p className="text-xs sm:text-sm text-secondaryText mt-1">
            Convert failed payments into recovered revenue using AI decisioning.
          </p>
        </div>

        <Button
          variant="ai"
          size="sm"
          onClick={demoState.startDemo}
        >
          <RotateCcw className="h-3.5 w-3.5" />
          <span>Run Recovery Demo</span>
        </Button>
      </div>

      {/* Summary KPI Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <Card className="p-4">
          <span className="text-xs text-secondaryText font-medium">Total Opportunities</span>
          <div className="text-xl font-bold font-mono text-primaryText mt-1">
            1,284
          </div>
          <span className="text-[10px] text-mutedText">From live Razorpay webhooks</span>
        </Card>

        <Card className="p-4">
          <span className="text-xs text-secondaryText font-medium">Potentially Recoverable</span>
          <div className="text-xl font-bold font-mono text-success mt-1">
            {formatCurrency(totalRecoverable)}
          </div>
          <span className="text-[10px] text-mutedText">88.4% projected yield</span>
        </Card>

        <Card className="p-4">
          <span className="text-xs text-secondaryText font-medium">Total Recovered YTD</span>
          <div className="text-xl font-bold font-mono text-success mt-1">
            {formatCurrency(1870000)}
          </div>
          <span className="text-[10px] text-success">↑ 24.8% vs last month</span>
        </Card>

        <Card className="p-4">
          <span className="text-xs text-secondaryText font-medium">Avg Recovery Rate</span>
          <div className="text-xl font-bold font-mono text-ai-light mt-1">
            {formatPercent(avgRate, 1)}
          </div>
          <span className="text-[10px] text-ai-light">High AI confidence</span>
        </Card>
      </div>

      {/* Main Table */}
      <RecoveryOpportunitiesTable />
    </div>
  );
}
