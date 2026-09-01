'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { RecoveryTwin3D } from '@/components/3d/RecoveryTwin';
import { CounterfactualView } from '@/components/simulator/CounterfactualView';
import { formatCurrency } from '@/lib/formatters';
import { runSimulation } from '@/lib/api/simulator';
import { SimulationResult, StrategyType } from '@/types';
import { mockDefaultSimulationResults } from '@/lib/mock/simulator';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell
} from 'recharts';
import { Cpu, Sparkles, Sliders, ArrowRight, GitFork } from 'lucide-react';

export default function SimulatorPage() {
  const [revenueAtRisk, setRevenueAtRisk] = useState<number>(2840000);
  const [horizonDays, setHorizonDays] = useState<number>(7);
  const [retryCount, setRetryCount] = useState<number>(2);
  const [selectedStrategies, setSelectedStrategies] = useState<StrategyType[]>([
    'Retry',
    'Payment Link',
    'Reminder',
    'Retry + Payment Link',
  ]);

  const [results, setResults] = useState<SimulationResult[]>(mockDefaultSimulationResults);
  const [isSimulating, setIsSimulating] = useState(false);
  const [isExecuteModalOpen, setIsExecuteModalOpen] = useState(false);
  const [executingStrategy, setExecutingStrategy] = useState<SimulationResult | null>(null);

  const handleRunSimulation = async () => {
    setIsSimulating(true);
    try {
      const res = await runSimulation({
        revenueAtRisk,
        horizonDays,
        retryCount,
        selectedStrategies,
      });
      setResults(res);
    } finally {
      setIsSimulating(false);
    }
  };

  useEffect(() => {
    handleRunSimulation();
  }, [revenueAtRisk, horizonDays, retryCount]);

  const recommendedResult = results.find((r) => r.isRecommended) || results[3] || results[0];

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload as SimulationResult;
      return (
        <div className="rounded-lg border border-border bg-surface-elevated p-3 shadow-card text-xs space-y-1 font-sans">
          <p className="font-bold text-primaryText">{data.strategy}</p>
          <div className="flex justify-between gap-4">
            <span className="text-secondaryText">Expected Recovery:</span>
            <span className="font-mono text-success font-bold">{formatCurrency(data.expectedRecovery)}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-secondaryText">Probability:</span>
            <span className="font-mono text-ai-light font-bold">{data.probability}%</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-secondaryText">ROI:</span>
            <span className="font-mono text-primaryText font-bold">{data.expectedRoi}x</span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/60 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-primaryText">
              Recovery Digital Twin
            </h1>
            <Badge variant="ai">3D Monte Carlo Twin</Badge>
          </div>
          <p className="text-xs sm:text-sm text-secondaryText mt-1">
            Simulate recovery strategies before taking action using Monte Carlo payment twin models.
          </p>
        </div>

        <Button
          variant="ai"
          size="sm"
          onClick={handleRunSimulation}
          isLoading={isSimulating}
        >
          <Cpu className="h-3.5 w-3.5" />
          <span>Run Simulation</span>
        </Button>
      </div>

      {/* Main Grid: Left Configuration, Right Predicted Outcomes */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Controls */}
        <Card className="lg:col-span-4 p-5 space-y-5 h-fit">
          <div className="flex items-center gap-2 border-b border-border/60 pb-3">
            <Sliders className="h-4 w-4 text-ai" />
            <h3 className="text-sm font-bold text-primaryText">Simulation Configuration</h3>
          </div>

          <div className="space-y-4">
            {/* Revenue Input */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-secondaryText">Revenue At Risk (₹)</label>
              <input
                type="number"
                value={revenueAtRisk}
                onChange={(e) => setRevenueAtRisk(Number(e.target.value))}
                className="w-full rounded-md border border-border bg-surface px-3 py-1.5 text-xs text-primaryText font-mono focus:outline-none focus:border-ai"
              />
              <span className="text-[10px] text-mutedText font-mono">
                {formatCurrency(revenueAtRisk, { compact: true })} exposed revenue
              </span>
            </div>

            {/* Recovery Horizon Slider */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-secondaryText">Recovery Horizon</span>
                <span className="font-mono text-primaryText font-semibold">{horizonDays} Days</span>
              </div>
              <input
                type="range"
                min={1}
                max={30}
                value={horizonDays}
                onChange={(e) => setHorizonDays(Number(e.target.value))}
                className="w-full accent-ai cursor-pointer"
              />
            </div>

            {/* Retry Count Slider */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-secondaryText">Retry Attempts</span>
                <span className="font-mono text-primaryText font-semibold">{retryCount} Retries</span>
              </div>
              <input
                type="range"
                min={1}
                max={5}
                value={retryCount}
                onChange={(e) => setRetryCount(Number(e.target.value))}
                className="w-full accent-ai cursor-pointer"
              />
            </div>

            {/* Strategy Toggles */}
            <div className="space-y-2 pt-2 border-t border-border/40">
              <span className="text-xs font-semibold text-secondaryText">Included Strategies</span>
              <div className="space-y-1.5 text-xs">
                {(['Retry', 'Payment Link', 'Reminder', 'Retry + Payment Link'] as StrategyType[]).map((strat) => (
                  <label key={strat} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedStrategies.includes(strat)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedStrategies([...selectedStrategies, strat]);
                        } else {
                          setSelectedStrategies(selectedStrategies.filter((s) => s !== strat));
                        }
                      }}
                      className="rounded border-border accent-ai"
                    />
                    <span className="text-primaryText">{strat}</span>
                  </label>
                ))}
              </div>
            </div>

            <Button
              variant="ai"
              size="md"
              className="w-full mt-4"
              onClick={handleRunSimulation}
              isLoading={isSimulating}
            >
              <Cpu className="h-4 w-4" />
              Re-Run Digital Twin
            </Button>
          </div>
        </Card>

        {/* Right: Predicted Outcomes & Visual Comparison */}
        <div className="lg:col-span-8 space-y-6">
          {/* Highlight Recommended Outcome Card */}
          {recommendedResult && (
            <Card className="border-ai-border/80 bg-gradient-to-r from-surface to-ai-bg/20 p-5 shadow-glow">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge variant="ai" size="sm">
                      <Sparkles className="h-3 w-3" />
                      RECOMMENDED STRATEGY
                    </Badge>
                    <span className="text-xs font-mono text-success font-bold">+₹4.5L Expected Uplift</span>
                  </div>
                  <h3 className="text-lg font-bold text-primaryText">{recommendedResult.strategy}</h3>
                  <p className="text-xs text-secondaryText">
                    Expected Recovery: <strong className="text-success font-mono text-sm">{formatCurrency(recommendedResult.expectedRecovery)}</strong> ({recommendedResult.probability}% probability)
                  </p>
                </div>

                <Button
                  variant="primary"
                  size="md"
                  onClick={() => {
                    setExecutingStrategy(recommendedResult);
                    setIsExecuteModalOpen(true);
                  }}
                >
                  Execute Strategy
                  <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </div>
            </Card>
          )}

          {/* Counterfactual "What-If" Analysis View */}
          <CounterfactualView />

          {/* 3D Strategy Twin Constellation Card */}
          <Card className="p-4 border-ai-border/40 bg-surface-elevated/40">
            <span className="text-[10px] font-mono text-mutedText uppercase px-2">3D Digital Twin Constellation</span>
            <RecoveryTwin3D selectedStrategy={recommendedResult?.strategy} className="h-48 w-full" />
          </Card>

          {/* Strategy Outcome Grid Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {results.map((res, idx) => (
              <Card
                key={idx}
                className={`p-3.5 space-y-1 border ${
                  res.isRecommended
                    ? 'border-ai bg-ai-bg/15 shadow-subtle'
                    : 'border-border bg-surface-elevated/40'
                }`}
              >
                <span className="text-[11px] font-semibold text-secondaryText truncate block">{res.strategy}</span>
                <div className="text-base font-bold font-mono text-primaryText">
                  {formatCurrency(res.expectedRecovery, { compact: true })}
                </div>
                <div className="flex justify-between items-center text-[10px] text-mutedText font-mono pt-1">
                  <span>Probability: <strong className="text-success">{res.probability}%</strong></span>
                  <span>{res.expectedRoi}x ROI</span>
                </div>
              </Card>
            ))}
          </div>

          {/* Recharts Bar Comparison Chart */}
          <Card className="p-5">
            <CardHeader className="p-0 pb-4 border-b border-border/60">
              <CardTitle className="text-sm">Strategy Recovery Comparison</CardTitle>
            </CardHeader>
            <CardContent className="p-0 pt-6">
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={results} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#26262B" vertical={false} />
                    <XAxis dataKey="strategy" stroke="#A1A1AA" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis
                      stroke="#A1A1AA"
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(val) => `₹${(val / 100000).toFixed(1)}L`}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="expectedRecovery" radius={[6, 6, 0, 0]}>
                      {results.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={entry.isRecommended ? '#8B5CF6' : '#3B82F6'}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Execution Confirmation Modal */}
      <Modal
        isOpen={isExecuteModalOpen}
        onClose={() => setIsExecuteModalOpen(false)}
        title="Confirm Autonomous Strategy Execution"
        subtitle="Execute simulated strategy across affected merchant payments"
        maxWidth="md"
      >
        {executingStrategy && (
          <div className="space-y-4 text-xs font-mono">
            <div className="rounded-lg bg-surface border border-border p-4 space-y-2">
              <div className="flex justify-between">
                <span className="text-secondaryText">Strategy:</span>
                <span className="font-bold text-ai-light">{executingStrategy.strategy}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondaryText">Expected Recovery:</span>
                <span className="font-bold text-success text-sm">
                  {formatCurrency(executingStrategy.expectedRecovery)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondaryText">Affected Transactions:</span>
                <span className="text-primaryText">1,284 Transactions</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondaryText">Policy Check:</span>
                <span className="text-success font-bold">✓ Policy v2.4 Compliant</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondaryText">AI Confidence:</span>
                <span className="text-ai-light font-bold">93%</span>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsExecuteModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setIsExecuteModalOpen(false);
                  alert("Sent strategy execution for human approval.");
                }}
              >
                Send for Approval
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setIsExecuteModalOpen(false);
                }}
              >
                Execute
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
