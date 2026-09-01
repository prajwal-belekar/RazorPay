'use client';

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { formatCurrency } from '@/lib/formatters';
import { StrategyOption, StrategyType } from '@/types';
import { Check, Sparkles, TrendingUp, HelpCircle } from 'lucide-react';

export function StrategyComparison({
  strategies,
  selectedStrategy,
  onSelectStrategy,
}: {
  strategies: StrategyOption[];
  selectedStrategy: StrategyType;
  onSelectStrategy: (strat: StrategyType) => void;
}) {
  return (
    <Card className="p-0">
      <CardHeader className="flex flex-row items-center justify-between border-b border-border/60 pb-3">
        <div>
          <CardTitle>Strategy Comparison</CardTitle>
          <p className="text-xs text-secondaryText mt-0.5">
            Simulated strategy options & predicted financial returns
          </p>
        </div>
        <span className="text-xs text-mutedText font-mono">4 Evaluated</span>
      </CardHeader>

      <CardContent className="p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {strategies.map((option, idx) => {
            const isSelected = selectedStrategy === option.type;
            return (
              <div
                key={idx}
                onClick={() => onSelectStrategy(option.type)}
                className={`relative rounded-xl border p-4 text-xs transition-all cursor-pointer flex flex-col justify-between ${
                  isSelected
                    ? 'border-ai bg-ai-bg/20 shadow-glow'
                    : 'border-border bg-surface-elevated/40 hover:border-border/90 hover:bg-surface-elevated/80'
                }`}
              >
                {option.isAiRecommended && (
                  <div className="absolute -top-2.5 right-3">
                    <Badge variant="ai" size="sm">
                      <Sparkles className="h-3 w-3" />
                      AI Recommended
                    </Badge>
                  </div>
                )}

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-sm text-primaryText">{option.title}</h4>
                    {isSelected && (
                      <div className="flex h-5 w-5 items-center justify-center rounded-full bg-ai text-white">
                        <Check className="h-3 w-3" />
                      </div>
                    )}
                  </div>

                  <div className="space-y-1 py-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-secondaryText">Probability:</span>
                      <span className="font-mono font-bold text-success">{option.probability}%</span>
                    </div>

                    <div className="flex justify-between text-xs">
                      <span className="text-secondaryText">Expected Value:</span>
                      <span className="font-mono font-bold text-primaryText">
                        {formatCurrency(option.expectedRecovery)}
                      </span>
                    </div>

                    <div className="flex justify-between text-xs">
                      <span className="text-secondaryText">Expected ROI:</span>
                      <span className="font-mono text-ai-light font-semibold">{option.roi}x</span>
                    </div>
                  </div>

                  <p className="text-[11px] text-secondaryText/90 border-t border-border/40 pt-2 leading-relaxed">
                    {option.explanation}
                  </p>
                </div>

                <div className="mt-4 pt-2">
                  <Button
                    variant={isSelected ? 'ai' : 'outline'}
                    size="sm"
                    className="w-full text-xs"
                  >
                    {isSelected ? 'Selected Strategy' : 'Select Strategy'}
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
