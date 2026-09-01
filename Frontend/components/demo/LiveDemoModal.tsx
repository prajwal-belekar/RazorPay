'use client';

import React from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { Progress } from '../ui/Skeleton';
import { AIOrb } from '../3d/AIOrb';
import { RevenuePipeline3D } from '../3d/RevenuePipeline';
import { DecisionExplanation } from '../recovery/DecisionExplanation';
import { useRecoveryEngine } from '@/context/RecoveryEngineContext';
import {
  VISUAL_LIFECYCLE_STEPS,
  DEMO_STAGE_SEQUENCE,
  getStageMetadata,
} from '@/lib/recoveryStages';
import { formatCurrency } from '@/lib/formatters';
import {
  Play,
  Pause,
  ChevronRight,
  ChevronLeft,
  CheckCircle2,
  ShieldCheck,
  Zap,
  Lock,
  Sparkles,
  RotateCcw,
} from 'lucide-react';

export function LiveDemoModal() {
  const {
    stage,
    currentStepIndex,
    isDemoOpen,
    isDemoRunning,
    isPaused,
    closeDemo,
    startDemo,
    pauseDemo,
    resumeDemo,
    nextStep,
    prevStep,
    goToStep,
  } = useRecoveryEngine();

  if (!isDemoOpen) return null;

  const currentStageKey = DEMO_STAGE_SEQUENCE[currentStepIndex] || 'detecting';
  const meta = getStageMetadata(currentStageKey);
  const totalSteps = DEMO_STAGE_SEQUENCE.length;
  const progressPercent = ((currentStepIndex + 1) / totalSteps) * 100;

  return (
    <Modal
      isOpen={isDemoOpen}
      onClose={closeDemo}
      title={
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-ai/20 border border-ai/40 text-ai-light">
            <Zap className="h-3.5 w-3.5" />
          </div>
          <span className="text-base font-bold text-primaryText tracking-tight">
            RECOVERAI AUTONOMOUS RECOVERY DEMO
          </span>
          <Badge variant="ai" size="sm">
            ~12s Guided Flow
          </Badge>
        </div>
      }
      subtitle="Watch RecoverAI detect, analyze, predict, simulate, validate, execute, recover, prove, and learn in real time."
      maxWidth="3xl"
    >
      <div className="space-y-5">
        {/* Stage Progress Bar */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs font-semibold text-secondaryText">
            <span>
              Stage {currentStepIndex + 1} of {totalSteps}:{' '}
              <span className="text-ai-light font-bold">{meta.label}</span>
            </span>
            <span className="font-mono text-[11px] text-mutedText">
              {Math.round(progressPercent)}% Complete
            </span>
          </div>
          <Progress value={progressPercent} colorClass="bg-gradient-to-r from-ai via-info to-success" />
        </div>

        {/* 3D Revenue Flow Pipeline Visualization */}
        <div className="rounded-xl border border-border bg-surface-elevated/40 p-2 overflow-hidden">
          <div className="text-[10px] font-mono text-mutedText uppercase px-2 pt-1 flex justify-between">
            <span>3D Autonomous Pipeline Telemetry</span>
            <span className="text-ai-light font-bold">Stage: {currentStageKey.toUpperCase()}</span>
          </div>
          <RevenuePipeline3D stage={currentStageKey} className="h-28 w-full" />
        </div>

        {/* Live Step Visual Cards Grid with 3D Core */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Step Main Hero Card */}
          <div className="md:col-span-2 rounded-xl border border-ai-border/40 bg-surface-elevated/90 p-4 shadow-glow space-y-3">
            <div className="flex items-center justify-between border-b border-border/60 pb-3">
              <div className="flex items-center gap-3">
                {/* Embedded 3D AI Core Sphere */}
                <div className="shrink-0">
                  <AIOrb stage={currentStageKey} className="h-12 w-12" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-primaryText">{meta.title}</h3>
                  <p className="text-xs text-secondaryText">{meta.description}</p>
                </div>
              </div>
              <Badge variant={currentStepIndex >= 6 ? 'success' : 'ai'}>
                {currentStepIndex >= 6 ? 'RECOVERED' : 'ACTIVE'}
              </Badge>
            </div>

            {/* Stage-Specific Content Views */}
            <div className="py-1 space-y-3">
              {currentStageKey === 'detecting' && (
                <div className="rounded-lg bg-danger-bg/30 border border-danger-border p-3.5 text-xs space-y-2">
                  <div className="flex justify-between items-center font-bold text-danger">
                    <span>UPI Bank Timeout Detected</span>
                    <span className="font-mono text-sm">₹18,500</span>
                  </div>
                  <div className="text-secondaryText grid grid-cols-2 gap-2 text-[11px] font-mono">
                    <div><strong>Transaction:</strong> TXN-82931</div>
                    <div><strong>Gateway:</strong> Razorpay</div>
                    <div><strong>Bank:</strong> HDFC UPI</div>
                    <div><strong>Customer:</strong> Priya Sharma (VIP)</div>
                  </div>
                </div>
              )}

              {currentStageKey === 'analyzing' && (
                <div className="rounded-lg bg-ai-bg/30 border border-ai-border/60 p-3.5 text-xs space-y-2">
                  <div className="flex items-center gap-2 text-ai-light font-bold">
                    <Sparkles className="h-4 w-4 animate-spin" />
                    <span>Ollama Llama 3.1 8B Context Reasoning</span>
                  </div>
                  <p className="text-primaryText text-[11px] font-mono bg-surface/80 p-2 rounded border border-border/80">
                    &quot;Analyzing failure code UPI_TIMEOUT for customer Priya Sharma. VIP tier with 94% historical completion. Recommending delayed retry + payment link fallback.&quot;
                  </p>
                </div>
              )}

              {currentStageKey === 'predicting' && (
                <div className="rounded-lg bg-info-bg/30 border border-info-border p-3.5 text-xs space-y-2">
                  <div className="flex justify-between items-center font-bold text-info-light">
                    <span>XGBoost Yield Prediction</span>
                    <span className="font-mono text-sm text-success">91% Probability</span>
                  </div>
                  <p className="text-secondaryText text-[11px]">
                    Expected Recovery: <strong className="text-success font-mono">₹17,800</strong> out of ₹18,500 exposed revenue.
                  </p>
                </div>
              )}

              {currentStageKey === 'simulating' && (
                <div className="rounded-lg bg-surface border border-border p-3.5 text-xs space-y-2 font-mono">
                  <span className="font-semibold text-primaryText block">Digital Twin Strategy Monte Carlo</span>
                  <div className="space-y-1 text-[11px]">
                    <div className="flex justify-between bg-surface-elevated p-1.5 rounded">
                      <span>Retry Only:</span>
                      <span>₹14,200 (76%)</span>
                    </div>
                    <div className="flex justify-between bg-surface-elevated p-1.5 rounded">
                      <span>Payment Link Only:</span>
                      <span>₹12,600 (68%)</span>
                    </div>
                    <div className="flex justify-between bg-ai/20 p-1.5 rounded border border-ai/40 font-bold text-ai-light">
                      <span>Hybrid (Retry + Link):</span>
                      <span className="text-success">₹17,800 (91%) [+₹3,700 Uplift]</span>
                    </div>
                  </div>
                </div>
              )}

              {currentStageKey === 'validating' && (
                <div className="rounded-lg bg-surface border border-success-border/60 p-3.5 text-xs space-y-2 font-mono">
                  <div className="flex items-center justify-between text-success font-bold">
                    <span className="flex items-center gap-1.5">
                      <ShieldCheck className="h-4 w-4" />
                      AI Action Firewall Checks Passed
                    </span>
                    <Badge variant="success">APPROVED</Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-1.5 text-[11px] text-secondaryText pt-1">
                    <div className="text-success">✓ Limit Check (₹18.5k &lt; ₹25k)</div>
                    <div className="text-success">✓ Retry Limit (0 &lt; 2)</div>
                    <div className="text-success">✓ AI Confidence (93% &gt; 85%)</div>
                    <div className="text-success">✓ Policy Version v2.4</div>
                  </div>
                </div>
              )}

              {currentStageKey === 'executing' && (
                <div className="rounded-lg bg-surface border border-ai-border p-4 text-xs text-center py-5 space-y-2">
                  <RotateCcw className="h-7 w-7 text-ai animate-spin mx-auto" />
                  <p className="font-bold text-primaryText text-sm">Executing Razorpay Recovery API</p>
                  <p className="text-secondaryText text-[11px]">Triggering delayed retry token via Razorpay gateway webhook...</p>
                </div>
              )}

              {currentStageKey === 'recovered' && (
                <div className="rounded-lg bg-success-bg border border-success-border p-3.5 text-xs space-y-2">
                  <div className="flex items-center justify-between font-bold text-success text-sm">
                    <span className="flex items-center gap-2">
                      <CheckCircle2 className="h-5 w-5" />
                      ₹18,500 Successfully Recovered!
                    </span>
                    <Badge variant="success">SETTLED</Badge>
                  </div>
                  <p className="text-secondaryText text-[11px]">
                    Funds settled to merchant account in 4.2 seconds without customer drop-off.
                  </p>
                </div>
              )}

              {currentStageKey === 'verified' && (
                <div className="rounded-lg bg-surface border border-indigo-500/40 p-3.5 text-xs space-y-2 font-mono">
                  <div className="flex items-center justify-between font-bold text-indigo-400">
                    <span className="flex items-center gap-1.5">
                      <Lock className="h-4 w-4" />
                      Polygon POS Devnet Proof Recorded
                    </span>
                    <Badge variant="ai">0x8a91...72fc</Badge>
                  </div>
                  <p className="text-secondaryText text-[11px]">
                    Cryptographic decision proof anchored to block #18294021 in Recovery Trust Center.
                  </p>
                </div>
              )}

              {currentStageKey === 'learning' && (
                <div className="rounded-lg bg-surface border border-success-border/60 p-3.5 text-xs space-y-2 font-mono">
                  <div className="flex items-center justify-between text-success font-bold">
                    <span className="flex items-center gap-1.5">
                      <Sparkles className="h-4 w-4" />
                      Merchant Recovery DNA Updated
                    </span>
                    <span className="text-success">+1.4% UPI Uplift</span>
                  </div>
                  <p className="text-secondaryText text-[11px]">
                    UPI recovery rate updated to 83.4%. Machine learning feature store updated with 1,285 data points.
                  </p>
                </div>
              )}
            </div>

            {/* Explainable AI Decision Card inside Demo */}
            {currentStepIndex >= 2 && currentStepIndex <= 6 && (
              <DecisionExplanation
                strategy="Retry + Payment Link"
                probability={91}
                confidence={93}
                expectedRecovery={17800}
              />
            )}
          </div>

          {/* Steps Side Tracker */}
          <div className="rounded-xl border border-border bg-surface p-3.5 space-y-2">
            <h4 className="text-[11px] font-semibold text-secondaryText uppercase tracking-wider mb-2">
              Lifecycle Steps
            </h4>
            <div className="space-y-1 text-xs">
              {VISUAL_LIFECYCLE_STEPS.map((s, idx) => {
                const isPast = idx < currentStepIndex;
                const isCurrent = idx === currentStepIndex;
                const Icon = s.icon;
                return (
                  <div
                    key={s.id}
                    onClick={() => goToStep(idx)}
                    className={`flex items-center gap-2 p-1.5 rounded-md transition-colors cursor-pointer text-xs ${
                      isCurrent
                        ? 'bg-ai/20 text-ai-light border border-ai/40 font-bold'
                        : isPast
                        ? 'text-success font-medium'
                        : 'text-mutedText'
                    }`}
                  >
                    <div
                      className={`flex h-4 w-4 items-center justify-center rounded-full text-[9px] font-mono ${
                        isCurrent
                          ? 'bg-ai text-white'
                          : isPast
                          ? 'bg-success/20 text-success'
                          : 'bg-surface-elevated text-mutedText'
                      }`}
                    >
                      {isPast ? '✓' : idx + 1}
                    </div>
                    <span className="truncate flex-1">{s.label}</span>
                    <Icon className="h-3 w-3 shrink-0" />
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Controls Bar */}
        <div className="flex items-center justify-between border-t border-border/60 pt-3">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                if (isDemoRunning && !isPaused) {
                  pauseDemo();
                } else {
                  resumeDemo();
                }
              }}
            >
              {isDemoRunning && !isPaused ? (
                <>
                  <Pause className="h-3.5 w-3.5 mr-1" />
                  Pause
                </>
              ) : (
                <>
                  <Play className="h-3.5 w-3.5 mr-1" />
                  {isPaused ? 'Resume' : 'Play'}
                </>
              )}
            </Button>
            <span className="text-xs text-mutedText hidden sm:inline">
              {isDemoRunning && !isPaused ? 'Auto-advancing lifecycle...' : 'Paused'}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={prevStep}
              disabled={currentStepIndex === 0}
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              Prev
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={nextStep}
              disabled={currentStepIndex === totalSteps - 1}
            >
              Next
              <ChevronRight className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
