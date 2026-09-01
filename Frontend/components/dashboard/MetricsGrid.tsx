'use client';

import React from 'react';
import { Card } from '../ui/Card';
import { AnimatedNumber } from '../motion/AnimatedNumber';
import { formatCurrency, formatPercent } from '@/lib/formatters';
import { DashboardMetrics } from '@/types';
import { TrendingUp, ShieldCheck, Zap, RotateCcw, AlertTriangle } from 'lucide-react';

export function MetricsGrid({ metrics }: { metrics: DashboardMetrics }) {
  const cards = [
    {
      title: 'Revenue At Risk',
      numericValue: metrics.revenueAtRisk,
      isCurrency: true,
      change: `↑ ${metrics.revenueAtRiskChange}%`,
      changeType: 'warning' as const,
      meaning: 'Revenue exposed to failed payments',
      icon: AlertTriangle,
      color: 'text-warning',
      bgColor: 'bg-warning-bg',
    },
    {
      title: 'Revenue Recovered',
      numericValue: metrics.revenueRecovered,
      isCurrency: true,
      change: `↑ ${metrics.revenueRecoveredChange}%`,
      changeType: 'success' as const,
      meaning: 'Primary business recovered revenue',
      icon: RotateCcw,
      color: 'text-success',
      bgColor: 'bg-success-bg',
      hero: true,
    },
    {
      title: 'Recovery Rate',
      numericValue: metrics.recoveryRate,
      isPercent: true,
      change: `↑ ${metrics.recoveryRateChange}%`,
      changeType: 'success' as const,
      meaning: 'Successful recovery percentage',
      icon: TrendingUp,
      color: 'text-ai-light',
      bgColor: 'bg-ai-bg',
      circularPercent: metrics.recoveryRate,
    },
    {
      title: 'Recovery Opportunities',
      numericValue: metrics.opportunitiesCount,
      change: `↑ ${metrics.opportunitiesChange}%`,
      changeType: 'info' as const,
      meaning: 'Identified recoverable transactions',
      icon: Zap,
      color: 'text-info-light',
      bgColor: 'bg-info-bg',
    },
    {
      title: 'AI Actions',
      numericValue: metrics.aiActionsCount,
      subValue: `${metrics.policyComplianceRate}% policy compliant`,
      change: '98.4% safe',
      changeType: 'success' as const,
      meaning: 'Autonomous actions executed',
      icon: ShieldCheck,
      color: 'text-ai-light',
      bgColor: 'bg-ai-bg',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <Card
            key={idx}
            className={`p-4 transition-all hover:border-border/90 ${
              card.hero ? 'border-success-border/70 bg-surface-elevated/90 shadow-glow' : ''
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-secondaryText truncate">{card.title}</span>
              <div className={`p-1.5 rounded-md ${card.bgColor} ${card.color}`}>
                <Icon className="h-4 w-4" />
              </div>
            </div>

            <div className="flex items-baseline justify-between">
              <div className="text-2xl font-bold font-mono tracking-tight text-primaryText tabular-nums">
                {card.isCurrency ? (
                  <AnimatedNumber
                    value={card.numericValue}
                    formatter={(val) => formatCurrency(val, { compact: true })}
                  />
                ) : card.isPercent ? (
                  <AnimatedNumber
                    value={card.numericValue}
                    formatter={(val) => formatPercent(val, 1)}
                  />
                ) : (
                  <AnimatedNumber
                    value={card.numericValue}
                    formatter={(val) => Math.round(val).toLocaleString('en-IN')}
                  />
                )}
              </div>

              {/* Circular Progress for Recovery Rate */}
              {card.circularPercent !== undefined ? (
                <div className="relative h-9 w-9 flex items-center justify-center">
                  <svg className="h-full w-full -rotate-90 transform" viewBox="0 0 36 36">
                    <path
                      className="text-surface-elevated"
                      strokeWidth="3.5"
                      stroke="currentColor"
                      fill="none"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                    <path
                      className="text-ai stroke-current"
                      strokeDasharray={`${card.circularPercent}, 100`}
                      strokeWidth="3.5"
                      strokeLinecap="round"
                      fill="none"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                  </svg>
                  <span className="absolute text-[9px] font-bold text-primaryText font-mono">
                    {Math.round(card.circularPercent)}%
                  </span>
                </div>
              ) : (
                <span
                  className={`text-[11px] font-medium font-mono px-1.5 py-0.5 rounded ${
                    card.changeType === 'success'
                      ? 'bg-success-bg text-success'
                      : card.changeType === 'warning'
                      ? 'bg-warning-bg text-warning'
                      : 'bg-info-bg text-info-light'
                  }`}
                >
                  {card.change}
                </span>
              )}
            </div>

            {card.subValue && (
              <p className="text-[11px] text-mutedText mt-1 font-mono">{card.subValue}</p>
            )}
            <p className="text-[10px] text-secondaryText/80 mt-1.5 line-clamp-1">{card.meaning}</p>
          </Card>
        );
      })}
    </div>
  );
}
