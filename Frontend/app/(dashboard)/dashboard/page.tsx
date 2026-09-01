'use client';

import React from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { MetricsGrid } from '@/components/dashboard/MetricsGrid';
import { RevenueOverview } from '@/components/dashboard/RevenueOverview';
import { RevenueLeakRadar } from '@/components/dashboard/RevenueLeakRadar';
import { AgentStatusSummary } from '@/components/dashboard/AgentStatusSummary';
import { RecoveryOpportunitiesTable } from '@/components/dashboard/RecoveryOpportunitiesTable';
import { RecentRecoveriesTimeline } from '@/components/dashboard/RecentRecoveriesTimeline';
import { RecoveryEngine } from '@/components/recovery-engine/RecoveryEngine';
import { OllamaStatusCard } from '@/components/ai/OllamaStatusCard';
import { DecisionExplanation } from '@/components/recovery/DecisionExplanation';
import { SlideUp, StaggerContainer } from '@/components/motion/Motion';
import { useRecoveryEngine } from '@/context/RecoveryEngineContext';
import { PlayCircle, Sparkles, ArrowRight, XCircle, CheckCircle2 } from 'lucide-react';

export default function DashboardPage() {
  const { metrics, startDemo, stage } = useRecoveryEngine();

  return (
    <StaggerContainer className="space-y-6">
      {/* Page Header */}
      <SlideUp className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/60 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-primaryText">
              Revenue Command Center
            </h1>
            <span className="rounded-full bg-ai/15 px-2.5 py-0.5 text-xs text-ai-light font-medium border border-ai/30 flex items-center gap-1">
              <Sparkles className="h-3 w-3" />
              Ollama Llama 3.1 8B Active
            </span>
          </div>
          <p className="text-xs sm:text-sm text-secondaryText mt-1">
            AI-powered autonomous recovery intelligence for your Razorpay payments.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ai"
            size="sm"
            onClick={startDemo}
          >
            <PlayCircle className="h-3.5 w-3.5" />
            <span>Run Autonomous Demo (~12s)</span>
          </Button>
        </div>
      </SlideUp>

      {/* KPI Metrics Cards */}
      <SlideUp delay={0.1}>
        <MetricsGrid metrics={metrics} />
      </SlideUp>

      {/* SIGNATURE AUTONOMOUS RECOVERY ENGINE VISUAL COMPONENT */}
      <SlideUp delay={0.2}>
        <RecoveryEngine />
      </SlideUp>

      {/* WHY THIS MATTERS: Traditional vs RecoverAI Comparison Card */}
      <SlideUp delay={0.25}>
        <Card className="p-5 border-ai-border/40 bg-gradient-to-r from-surface to-ai-bg/10">
          <div className="flex items-center justify-between border-b border-border/60 pb-3 mb-4">
            <div className="flex items-center gap-2">
              <Badge variant="ai">THE RECOVERAI ADVANTAGE</Badge>
              <h3 className="text-xs font-bold text-primaryText uppercase tracking-wider">
                Why Autonomous Payment Intelligence Matters
              </h3>
            </div>
            <span className="text-[11px] font-mono text-success">
              +67.4% Recovery Yield vs 18% Generic Retry
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
            {/* Traditional Legacy System */}
            <div className="rounded-lg bg-surface/60 border border-border/80 p-3.5 space-y-2">
              <span className="text-[10px] font-bold text-danger uppercase flex items-center gap-1">
                <XCircle className="h-3.5 w-3.5" />
                TRADITIONAL PAYMENT SYSTEM
              </span>
              <div className="flex items-center justify-between text-[11px] text-mutedText pt-1">
                <span>Failed Payment</span>
                <ArrowRight className="h-3 w-3 text-mutedText" />
                <span>Blind Retry</span>
                <ArrowRight className="h-3 w-3 text-mutedText" />
                <span>Repeated Failure</span>
                <ArrowRight className="h-3 w-3 text-danger" />
                <span className="text-danger font-bold">Lost Revenue</span>
              </div>
            </div>

            {/* RecoverAI Autonomous Infrastructure */}
            <div className="rounded-lg bg-ai-bg/20 border border-ai-border/60 p-3.5 space-y-2">
              <span className="text-[10px] font-bold text-success uppercase flex items-center gap-1">
                <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                RECOVERAI AUTONOMOUS ENGINE
              </span>
              <div className="flex items-center justify-between text-[10px] text-ai-light pt-1 overflow-x-auto">
                <span>Detect</span>
                <span>→</span>
                <span>Analyze</span>
                <span>→</span>
                <span>Predict</span>
                <span>→</span>
                <span>Simulate</span>
                <span>→</span>
                <span>Validate</span>
                <span>→</span>
                <span>Recover</span>
                <span>→</span>
                <span className="text-success font-bold">Prove & Learn</span>
              </div>
            </div>
          </div>
        </Card>
      </SlideUp>

      {/* Revenue Performance Chart & Explainable AI Card */}
      <SlideUp delay={0.3} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RevenueOverview />
        </div>
        <div>
          <DecisionExplanation
            strategy="Retry + Payment Link"
            probability={91}
            confidence={93}
            expectedRecovery={17800}
          />
        </div>
      </SlideUp>

      {/* Anomaly Radar & Ollama Local AI Engine Grid */}
      <SlideUp delay={0.4} className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RevenueLeakRadar />
        <OllamaStatusCard isAnalyzing={stage === 'analyzing'} />
      </SlideUp>

      {/* Recovery Opportunities Table */}
      <SlideUp delay={0.5}>
        <RecoveryOpportunitiesTable />
      </SlideUp>

      {/* Agent Status & Recent Recoveries Timeline */}
      <SlideUp delay={0.6} className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <AgentStatusSummary />
        <RecentRecoveriesTimeline />
      </SlideUp>
    </StaggerContainer>
  );
}
