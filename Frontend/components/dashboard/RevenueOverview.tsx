'use client';

import React, { useState, useMemo } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { formatCurrency } from '@/lib/formatters';
import { useRecoveryEngine } from '@/context/RecoveryEngineContext';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';

export function RevenueOverview() {
  const { cases, isLoading, dataSource } = useRecoveryEngine();
  const [period, setPeriod] = useState<'7D' | '30D' | '90D'>('7D');

  const chartData = useMemo(() => {
    const days = period === '7D' ? 7 : period === '30D' ? 30 : 90;
    const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;

    const byDay = new Map<string, { revenueAtRisk: number; revenueRecovered: number }>();

    cases.forEach((c) => {
      const ts = c.createdAt ? new Date(c.createdAt).getTime() : NaN;
      if (isNaN(ts) || ts < cutoff) return;
      const dateKey = new Date(ts).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
      const bucket = byDay.get(dateKey) || { revenueAtRisk: 0, revenueRecovered: 0 };
      if (c.status === 'Recovered') {
        bucket.revenueRecovered += c.amount;
      } else {
        bucket.revenueAtRisk += c.amount;
      }
      byDay.set(dateKey, bucket);
    });

    return Array.from(byDay.entries())
      .sort((a, b) => (a[0] < b[0] ? -1 : 1))
      .map(([date, v]) => ({
        date,
        revenueAtRisk: v.revenueAtRisk,
        revenueRecovered: v.revenueRecovered,
      }));
  }, [cases, period]);

  const totals = useMemo(() => {
    return chartData.reduce(
      (acc, d) => ({
        revenueAtRisk: acc.revenueAtRisk + d.revenueAtRisk,
        revenueRecovered: acc.revenueRecovered + d.revenueRecovered,
      }),
      { revenueAtRisk: 0, revenueRecovered: 0 }
    );
  }, [chartData]);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="rounded-lg border border-border bg-surface-elevated p-3 shadow-card text-xs space-y-1.5 font-sans">
          <p className="font-semibold text-primaryText border-b border-border/60 pb-1">{label}</p>
          <div className="flex items-center justify-between gap-4">
            <span className="text-warning flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-warning"></span>
              Revenue At Risk
            </span>
            <span className="font-mono font-semibold text-primaryText">
              {formatCurrency(payload[0]?.value || 0, { compact: true })}
            </span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span className="text-success flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-success"></span>
              Revenue Recovered
            </span>
            <span className="font-mono font-semibold text-primaryText">
              {formatCurrency(payload[1]?.value || 0, { compact: true })}
            </span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <Card className="p-0">
      <CardHeader className="flex flex-row items-center justify-between border-b border-border/60 pb-4">
        <div>
          <CardTitle>Revenue Recovery Performance</CardTitle>
          <p className="text-xs text-secondaryText mt-0.5">
            Comparison of exposed revenue vs AI recovered revenue over time
            {dataSource === 'live' ? ' (live backend data)' : ''}
          </p>
        </div>

        <div className="flex items-center gap-1 rounded-md bg-surface-elevated p-1 border border-border/80">
          {(['7D', '30D', '90D'] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-2.5 py-1 text-xs font-semibold rounded transition-colors ${
                period === p
                  ? 'bg-ai text-white shadow-subtle'
                  : 'text-secondaryText hover:text-primaryText'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </CardHeader>

      <CardContent className="pt-6 pb-4">
        <div className="h-72 w-full">
          {isLoading ? (
            <div className="h-full flex items-center justify-center text-xs text-secondaryText animate-pulse">
              Loading payments...
            </div>
          ) : chartData.length === 0 ? (
            <div className="h-full flex items-center justify-center text-xs text-secondaryText">
              No historical payment data available for this period.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={chartData}
                margin={{ top: 10, right: 10, left: 10, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="colorRisk" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#F59E0B" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorRecovered" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#26262B" vertical={false} />
                <XAxis
                  dataKey="date"
                  stroke="#A1A1AA"
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  stroke="#A1A1AA"
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value) => `₹${(value / 100000).toFixed(1)}L`}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="revenueAtRisk"
                  name="Revenue At Risk"
                  stroke="#F59E0B"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorRisk)"
                />
                <Area
                  type="monotone"
                  dataKey="revenueRecovered"
                  name="Revenue Recovered"
                  stroke="#10B981"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorRecovered)"
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="flex items-center justify-center gap-6 mt-2 pt-3 border-t border-border/40 text-xs">
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-warning"></span>
            <span className="text-secondaryText">Revenue At Risk</span>
            <span className="font-mono font-semibold text-primaryText">
              {formatCurrency(totals.revenueAtRisk, { compact: true })} Total
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-success"></span>
            <span className="text-secondaryText">Revenue Recovered</span>
            <span className="font-mono font-semibold text-primaryText">
              {formatCurrency(totals.revenueRecovered, { compact: true })} Total
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
