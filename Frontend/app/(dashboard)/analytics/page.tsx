'use client';

import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { mockMerchantDNA, mockStrategyPerformance, mockFailureAnalysis } from '@/lib/mock/analytics';
import { formatCurrency, formatPercent } from '@/lib/formatters';
import { Brain, Sparkles, Dna, TrendingUp, CheckCircle2, ShieldCheck, Zap } from 'lucide-react';

export default function AnalyticsPage() {
  const dna = mockMerchantDNA;
  const strategies = mockStrategyPerformance;
  const failures = mockFailureAnalysis;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/60 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-primaryText">
              Recovery Analytics & DNA
            </h1>
            <Badge variant="ai">Merchant Intelligence</Badge>
          </div>
          <p className="text-xs sm:text-sm text-secondaryText mt-1">
            Deep financial intelligence and merchant-specific AI learning profiles.
          </p>
        </div>

        <span className="font-mono text-xs text-ai-light flex items-center gap-1.5">
          <Brain className="h-4 w-4 text-ai" />
          Model Trained on {dna.learningDataPoints.toLocaleString('en-IN')} Data Points
        </span>
      </div>

      {/* MERCHANT RECOVERY DNA - Hero Component */}
      <Card className="border-ai-border/80 bg-gradient-to-br from-surface to-ai-bg/20 p-6 shadow-glow relative overflow-hidden">
        <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none">
          <Dna className="h-48 w-48 text-ai" />
        </div>

        <div className="space-y-6 relative z-10">
          <div className="flex items-center justify-between border-b border-border/60 pb-3">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-ai/20 text-ai-light border border-ai/50">
                <Dna className="h-4 w-4" />
              </div>
              <div>
                <h2 className="text-base font-bold text-primaryText uppercase tracking-wider">
                  MERCHANT RECOVERY DNA
                </h2>
                <p className="text-xs text-secondaryText">Learned optimal payment recovery parameters</p>
              </div>
            </div>

            <Badge variant="ai">Accuracy: {dna.modelAccuracy}%</Badge>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
            <div className="p-3 rounded-lg bg-surface-elevated/80 border border-border/80">
              <span className="text-[10px] text-mutedText block">Best Performing Strategy</span>
              <span className="text-sm font-bold text-ai-light">{dna.bestStrategy}</span>
            </div>

            <div className="p-3 rounded-lg bg-surface-elevated/80 border border-border/80">
              <span className="text-[10px] text-mutedText block">Optimal Retry Window</span>
              <span className="text-sm font-bold text-success">{dna.bestRetryWindow}</span>
            </div>

            <div className="p-3 rounded-lg bg-surface-elevated/80 border border-border/80">
              <span className="text-[10px] text-mutedText block">Top Customer Segment</span>
              <span className="text-sm font-bold text-primaryText">{dna.bestCustomerSegment}</span>
            </div>

            <div className="p-3 rounded-lg bg-surface-elevated/80 border border-border/80">
              <span className="text-[10px] text-mutedText block">Best Payment Method</span>
              <span className="text-sm font-bold text-success">{dna.bestPaymentMethod}</span>
            </div>
          </div>

          {/* Payment Method Yield Radar Profiles */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
            <div className="p-3 rounded-lg bg-surface/80 border border-border/60 space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-secondaryText">UPI Recovery</span>
                <span className="font-mono font-bold text-success">{dna.methodRates.UPI}%</span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-surface-elevated">
                <div className="h-full bg-success rounded-full" style={{ width: `${dna.methodRates.UPI}%` }} />
              </div>
            </div>

            <div className="p-3 rounded-lg bg-surface/80 border border-border/60 space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-secondaryText">Card Recovery</span>
                <span className="font-mono font-bold text-ai-light">{dna.methodRates.Cards}%</span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-surface-elevated">
                <div className="h-full bg-ai rounded-full" style={{ width: `${dna.methodRates.Cards}%` }} />
              </div>
            </div>

            <div className="p-3 rounded-lg bg-surface/80 border border-border/60 space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-secondaryText">NetBanking Recovery</span>
                <span className="font-mono font-bold text-info-light">{dna.methodRates['Net Banking']}%</span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-surface-elevated">
                <div className="h-full bg-info rounded-full" style={{ width: `${dna.methodRates['Net Banking']}%` }} />
              </div>
            </div>

            <div className="p-3 rounded-lg bg-surface/80 border border-border/60 space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-secondaryText">Wallet Recovery</span>
                <span className="font-mono font-bold text-warning">{dna.methodRates.Wallet}%</span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-surface-elevated">
                <div className="h-full bg-warning rounded-full" style={{ width: `${dna.methodRates.Wallet}%` }} />
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Strategy Performance Table */}
      <Card className="p-0">
        <CardHeader className="flex flex-row items-center justify-between border-b border-border/60 pb-3">
          <CardTitle>Strategy Performance Matrix</CardTitle>
          <span className="text-xs font-mono text-mutedText">Aggregated Results</span>
        </CardHeader>
        <CardContent className="p-0 overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-surface-elevated/60 text-secondaryText font-mono border-b border-border">
              <tr>
                <th className="py-3 px-4">Strategy</th>
                <th className="py-3 px-4">Attempts</th>
                <th className="py-3 px-4">Success</th>
                <th className="py-3 px-4">Success Rate</th>
                <th className="py-3 px-4">Recovered Amount</th>
                <th className="py-3 px-4">Avg Recovery</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/40 font-mono">
              {strategies.map((s, idx) => (
                <tr key={idx} className="hover:bg-surface-elevated/40">
                  <td className="py-3.5 px-4 font-bold text-primaryText font-sans">{s.strategy}</td>
                  <td className="py-3.5 px-4 text-secondaryText">{s.attempts.toLocaleString('en-IN')}</td>
                  <td className="py-3.5 px-4 text-success">{s.success.toLocaleString('en-IN')}</td>
                  <td className="py-3.5 px-4 text-success font-bold">{s.successRate}%</td>
                  <td className="py-3.5 px-4 text-primaryText font-bold">{formatCurrency(s.recoveredAmount)}</td>
                  <td className="py-3.5 px-4 text-secondaryText">{formatCurrency(s.avgRecovery)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Failure Analysis breakdown */}
      <Card className="p-5">
        <CardHeader className="p-0 pb-4 border-b border-border/60">
          <CardTitle className="text-sm">Payment Failure Root Cause Analysis</CardTitle>
        </CardHeader>
        <CardContent className="p-0 pt-4 space-y-3">
          {failures.map((f, idx) => (
            <div key={idx} className="space-y-1 text-xs">
              <div className="flex justify-between font-mono">
                <span className="text-primaryText font-bold">{f.reason} ({f.count} cases)</span>
                <span className="text-secondaryText">{f.percent}% of all failures</span>
              </div>
              <div className="h-2 w-full rounded-full bg-surface-elevated">
                <div
                  className="h-full rounded-full bg-ai"
                  style={{ width: `${f.percent}%` }}
                />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
