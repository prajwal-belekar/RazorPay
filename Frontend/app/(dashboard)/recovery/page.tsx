'use client';

import React, { useMemo } from 'react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { RecoveryOpportunitiesTable } from '@/components/dashboard/RecoveryOpportunitiesTable';
import { useRecoveryEngine } from '@/context/RecoveryEngineContext';
import { formatCurrency, formatPercent } from '@/lib/formatters';
import { RotateCcw } from 'lucide-react';
import { useLiveDemo } from '@/hooks/use-live-demo';

export default function RecoveryPage() {
  const demoState = useLiveDemo();
  const { cases, isLoading } = useRecoveryEngine();

  const stats = useMemo(() => {
    const atRisk = cases.filter((c) => c.status !== 'Recovered');
    const recoveredAmount = cases
      .filter((c) => c.status === 'Recovered')
      .reduce((acc, c) => acc + c.amount, 0);
    const totalAmount = cases.reduce((acc, c) => acc + c.amount, 0);
    const avgRate = cases.length > 0
      ? cases.reduce((acc, c) => acc + c.recoveryProbability, 0) / cases.length
      : 0;
    return { opportunities: atRisk.length, totalAmount, recoveredAmount, avgRate, total: cases.length };
  }, [cases]);

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
          <span className="text-xs text-secondaryText font-medium">Recovery Opportunities</span>
          <div className="text-xl font-bold font-mono text-primaryText mt-1">
            {isLoading ? '...' : stats.opportunities}
          </div>
          <span className="text-[10px] text-mutedText">From backend payment records</span>
        </Card>

        <Card className="p-4">
          <span className="text-xs text-secondaryText font-medium">Total At Risk Value</span>
          <div className="text-xl font-bold font-mono text-primaryText mt-1">
            {isLoading ? '...' : formatCurrency(stats.totalAmount - stats.recoveredAmount)}
          </div>
          <span className="text-[10px] text-mutedText">Across {isLoading ? '...' : stats.total} case(s)</span>
        </Card>

        <Card className="p-4">
          <span className="text-xs text-secondaryText font-medium">Total Recovered</span>
          <div className="text-xl font-bold font-mono text-success mt-1">
            {isLoading ? '...' : formatCurrency(stats.recoveredAmount)}
          </div>
          <span className="text-[10px] text-success">From SUCCESS recoveries</span>
        </Card>

        <Card className="p-4">
          <span className="text-xs text-secondaryText font-medium">Avg AI Confidence</span>
          <div className="text-xl font-bold font-mono text-ai-light mt-1">
            {isLoading ? '...' : formatPercent(stats.avgRate, 1)}
          </div>
          <span className="text-[10px] text-ai-light">From AI decision records</span>
        </Card>
      </div>

      {/* Main Table */}
      <RecoveryOpportunitiesTable />
    </div>
  );
}
