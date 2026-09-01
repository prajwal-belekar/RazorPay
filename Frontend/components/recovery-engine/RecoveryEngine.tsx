'use client';

import React from 'react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { AIOrb } from '../3d/AIOrb';
import { RevenuePipeline3D } from '../3d/RevenuePipeline';
import { useRecoveryEngine } from '@/context/RecoveryEngineContext';
import {
  VISUAL_LIFECYCLE_STEPS,
  DEMO_STAGE_SEQUENCE,
  getStageMetadata,
} from '@/lib/recoveryStages';
import {
  Play,
  Pause,
  SkipForward,
  RotateCw,
} from 'lucide-react';

export function RecoveryEngine() {
  const {
    stage,
    currentStepIndex,
    isDemoRunning,
    isPaused,
    startDemo,
    pauseDemo,
    resumeDemo,
    stopDemo,
    nextStep,
    goToStep,
  } = useRecoveryEngine();

  const currentStageKey = DEMO_STAGE_SEQUENCE[currentStepIndex] || 'detecting';
  const meta = getStageMetadata(stage !== 'idle' ? stage : currentStageKey);

  return (
    <Card className="border-ai-border/80 bg-gradient-to-r from-surface via-surface-elevated to-ai-bg/10 p-6 shadow-glow relative overflow-hidden">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 border-b border-border/60 pb-5">
        {/* Left: 3D AI Orb & Status */}
        <div className="flex items-center gap-4">
          <div className="shrink-0">
            <AIOrb stage={stage !== 'idle' ? stage : currentStageKey} className="h-16 w-16 sm:h-20 sm:w-20" />
          </div>

          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h2 className="text-lg sm:text-xl font-bold tracking-tight text-primaryText">
                AUTONOMOUS RECOVERY ENGINE
              </h2>
              <Badge variant={isDemoRunning ? 'ai' : 'success'} size="sm">
                ● {isDemoRunning ? `STAGE: ${meta.label.toUpperCase()}` : 'ENGINE OPERATIONAL'}
              </Badge>
            </div>
            <p className="text-xs text-secondaryText">
              {isDemoRunning ? meta.detail : 'Real-time Razorpay payment risk detection & Ollama autonomous resolution'}
            </p>
          </div>
        </div>

        {/* Right: Engine Demo Controls */}
        <div className="flex items-center gap-2">
          {!isDemoRunning ? (
            <Button variant="ai" size="sm" onClick={startDemo}>
              <Play className="h-3.5 w-3.5" />
              <span>Run Autonomous Demo (~12s)</span>
            </Button>
          ) : (
            <>
              {isPaused ? (
                <Button variant="secondary" size="sm" onClick={resumeDemo}>
                  <Play className="h-3.5 w-3.5" />
                  <span>Resume</span>
                </Button>
              ) : (
                <Button variant="outline" size="sm" onClick={pauseDemo}>
                  <Pause className="h-3.5 w-3.5" />
                  <span>Pause</span>
                </Button>
              )}

              <Button
                variant="ghost"
                size="sm"
                onClick={nextStep}
              >
                <SkipForward className="h-3.5 w-3.5" />
                <span>Skip</span>
              </Button>

              <Button variant="danger" size="sm" onClick={stopDemo}>
                <RotateCw className="h-3.5 w-3.5" />
                <span>Reset</span>
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Signature Pipeline Flow Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-9 gap-2 pt-5 text-xs font-mono">
        {VISUAL_LIFECYCLE_STEPS.map((st, idx) => {
          const Icon = st.icon;
          const isCurrent = isDemoRunning && currentStepIndex === idx;
          const isCompleted = isDemoRunning ? idx < currentStepIndex : false;

          return (
            <div
              key={st.id}
              onClick={() => goToStep(idx)}
              className={`p-2 rounded-lg border flex flex-col justify-between transition-all cursor-pointer ${
                isCurrent
                  ? 'border-ai bg-ai-bg/30 text-ai-light shadow-glow ring-1 ring-ai/50 font-bold scale-[1.02]'
                  : isCompleted
                  ? 'border-success-border/60 bg-success-bg/20 text-success font-medium'
                  : 'border-border/60 bg-surface/60 text-secondaryText hover:bg-surface-elevated'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] text-mutedText">{idx + 1}</span>
                <Icon className={`h-3 w-3 ${isCurrent ? 'animate-pulse text-ai-light' : 'text-secondaryText'}`} />
              </div>
              <span className="text-[10px] font-bold text-primaryText truncate">{st.label}</span>
            </div>
          );
        })}
      </div>

      {/* 3D Flow Line Representation */}
      <div className="mt-4 pt-2 border-t border-border/40">
        <RevenuePipeline3D stage={stage !== 'idle' ? stage : currentStageKey} className="h-20 w-full" />
      </div>
    </Card>
  );
}
