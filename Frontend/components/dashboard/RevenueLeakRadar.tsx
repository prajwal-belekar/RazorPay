'use client';

import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { formatCurrency } from '@/lib/formatters';
import { mockRevenueLeakAnomaly } from '@/lib/mock/dashboard';
import { Radar, AlertTriangle, ArrowUpRight, Cpu, Search } from 'lucide-react';
import { useRouter } from 'next/navigation';

export function RevenueLeakRadar() {
  const router = useRouter();
  const anomaly = mockRevenueLeakAnomaly;

  return (
    <Card className="border-warning-border/60 bg-gradient-to-br from-surface to-warning-bg/10 relative overflow-hidden">
      <div className="absolute top-0 right-0 p-3 opacity-10 pointer-events-none">
        <Radar className="h-32 w-32 text-warning animate-pulse-glow" />
      </div>

      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-warning/20 border border-warning/40 text-warning">
            <AlertTriangle className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <CardTitle className="text-warning text-sm font-bold">REVENUE LEAK DETECTED</CardTitle>
              <Badge variant="warning" size="sm">
                HIGH SEVERITY
              </Badge>
            </div>
            <p className="text-xs text-secondaryText">AI Anomaly Radar Engine Alert</p>
          </div>
        </div>

        <span className="font-mono text-xs text-mutedText">Detected 10m ago</span>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 rounded-lg bg-surface-elevated/80 border border-border/80 p-3.5 text-xs">
          <div>
            <span className="text-secondaryText text-[11px]">UPI Failure Spike</span>
            <div className="flex items-baseline gap-1.5 mt-0.5">
              <span className="text-lg font-bold font-mono text-primaryText">
                {anomaly.previousRate}% → {anomaly.currentRate}%
              </span>
              <span className="text-xs font-bold text-danger font-mono">
                +{anomaly.percentageChange}%
              </span>
            </div>
          </div>

          <div>
            <span className="text-secondaryText text-[11px]">Estimated Revenue At Risk</span>
            <div className="text-lg font-bold font-mono text-warning mt-0.5">
              {formatCurrency(anomaly.revenueAtRisk)}
            </div>
          </div>

          <div>
            <span className="text-secondaryText text-[11px]">AI Confidence</span>
            <div className="text-lg font-bold font-mono text-ai-light mt-0.5">
              {anomaly.confidence}%
            </div>
          </div>
        </div>

        <p className="text-xs text-secondaryText leading-relaxed">
          <strong>Recommended AI Action:</strong> {anomaly.recommendedAction}
        </p>

        <div className="flex items-center gap-3 pt-1">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => router.push('/revenue-radar')}
            className="flex-1 sm:flex-none"
          >
            <Search className="h-3.5 w-3.5" />
            Analyze Anomaly
          </Button>

          <Button
            variant="ai"
            size="sm"
            onClick={() => router.push(`/simulator?risk=${anomaly.revenueAtRisk}`)}
            className="flex-1 sm:flex-none"
          >
            <Cpu className="h-3.5 w-3.5" />
            Simulate Strategy
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
