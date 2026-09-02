'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { AIDecisionCard } from '@/components/recovery/AIDecisionCard';
import { StrategyComparison } from '@/components/recovery/StrategyComparison';
import { RecoveryTimeline } from '@/components/recovery/RecoveryTimeline';
import { ActionFirewallCard } from '@/components/recovery/ActionFirewallCard';
import { RecoveryPassportCard } from '@/components/recovery/RecoveryPassportCard';
import { RecoveryScore } from '@/components/recovery/RecoveryScore';
import { ConfidenceMatrix } from '@/components/recovery/ConfidenceMatrix';
import { RevenuePipeline3D } from '@/components/3d/RevenuePipeline';
import { useRecoveryEngine } from '@/context/RecoveryEngineContext';
import { RecoveryCase, StrategyType } from '@/types';
import { formatCurrency, formatDate } from '@/lib/formatters';
import { ArrowLeft, RotateCcw, Cpu, CloudOff } from 'lucide-react';

export default function RecoveryDetailPage() {
  const params = useParams();
  const router = useRouter();
  const caseId = (params?.id as string) || 'REC-18291';

  const { cases, executeRecoveryCase, isLoading, backendError, dataSource } = useRecoveryEngine();
  const [recoveryCase, setRecoveryCase] = useState<RecoveryCase | null>(null);
  const [selectedStrategy, setSelectedStrategy] = useState<StrategyType>('Retry');
  const [isExecuting, setIsExecuting] = useState(false);
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState(false);

  useEffect(() => {
    const found = cases.find((c) => c.id === caseId || c.transactionId === caseId);
    if (found) {
      setRecoveryCase(found);
      setSelectedStrategy(found.strategy);
    } else if (!isLoading && cases.length > 0) {
      setRecoveryCase(null);
    }
  }, [caseId, cases, isLoading]);

  if (isLoading) {
    return (
      <div className="p-8 text-center text-xs text-secondaryText animate-pulse">
        Loading payments...
      </div>
    );
  }

  if (backendError) {
    return (
      <div className="p-8 border border-danger-border/60 bg-danger-bg/10 rounded-lg text-center space-y-2">
        <CloudOff className="h-6 w-6 mx-auto text-danger" />
        <p className="text-xs font-medium text-primaryText">Unable to connect to RecoverAI backend.</p>
        <p className="text-[11px] text-secondaryText">Payment #{caseId} cannot be loaded. Please ensure the FastAPI backend is running.</p>
        <button
          onClick={() => router.push('/dashboard')}
          className="mt-2 text-xs text-ai-light hover:underline"
        >
          Back to Dashboard
        </button>
      </div>
    );
  }

  if (!recoveryCase) {
    return (
      <div className="p-8 text-center text-xs text-secondaryText">
        No payment recovery case found.
      </div>
    );
  }

  const handleExecute = async () => {
    setIsExecuting(true);
    setIsConfirmModalOpen(false);
    try {
      await executeRecoveryCase(recoveryCase.id, selectedStrategy);
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Back Button & Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/60 pb-4">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push('/recovery')}
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl sm:text-2xl font-bold font-mono text-primaryText">
                {recoveryCase.transactionId}
              </h1>
              <Badge
                variant={
                  recoveryCase.status === 'Recovered'
                    ? 'success'
                    : recoveryCase.status === 'At Risk'
                    ? 'warning'
                    : 'info'
                }
              >
                {recoveryCase.status}
              </Badge>
            </div>
            <p className="text-xs text-secondaryText">Recovery Case #{recoveryCase.id}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ai"
            size="sm"
            onClick={() => router.push(`/simulator?tx=${recoveryCase.transactionId}`)}
          >
            <Cpu className="h-3.5 w-3.5" />
            Simulate Strategy
          </Button>

          {recoveryCase.status !== 'Recovered' && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsConfirmModalOpen(true)}
              isLoading={isExecuting}
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Execute Recovery
            </Button>
          )}
        </div>
      </div>

      {/* 3D Recovery Pipeline Visual */}
      <Card className="p-3 border-ai-border/40 bg-surface-elevated/40">
        <span className="text-[10px] font-mono text-mutedText uppercase px-2">3D Autonomous Recovery Pipeline</span>
        <RevenuePipeline3D activeStep={recoveryCase.status === 'Recovered' ? 5 : 3} className="h-28 w-full" />
      </Card>

      {/* 1. Transaction Summary Card */}
      <Card className="p-4">
        <div className="grid grid-cols-2 sm:grid-cols-6 gap-4 text-xs font-mono">
          <div>
            <span className="text-[10px] text-mutedText block">Amount</span>
            <span className="text-base font-bold text-primaryText">{formatCurrency(recoveryCase.amount)}</span>
          </div>

          <div>
            <span className="text-[10px] text-mutedText block">Customer</span>
            <span className="text-primaryText font-semibold">{recoveryCase.customer.name}</span>
            <span className="text-[10px] text-mutedText block">{recoveryCase.customer.tier}</span>
          </div>

          <div>
            <span className="text-[10px] text-mutedText block">Payment Method</span>
            <span className="text-primaryText font-semibold">{recoveryCase.paymentMethod === 'N/A' ? 'N/A' : recoveryCase.paymentMethod}</span>
          </div>

          <div>
            <span className="text-[10px] text-mutedText block">Failure Reason</span>
            <span className="text-danger font-semibold">{recoveryCase.failureReason}</span>
          </div>

          <div>
            <span className="text-[10px] text-mutedText block">Created Date</span>
            <span className="text-secondaryText">{formatDate(recoveryCase.createdAt, { includeTime: true })}</span>
          </div>

          <div>
            <span className="text-[10px] text-mutedText block">Decision Source</span>
            <span className="text-ai-light font-semibold">{recoveryCase.decisionSource || 'N/A'}</span>
            <span className="text-[10px] text-mutedText block">Retries: {recoveryCase.retryCount ?? 'N/A'}</span>
          </div>
        </div>
      </Card>

      {/* Recovery Score & Governance Matrix Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <RecoveryScore score={recoveryCase.recoveryProbability} />
        <ConfidenceMatrix confidence={recoveryCase.aiConfidence} impactAmount={recoveryCase.amount} />
      </div>

      {/* 2. AI Decision Card */}
      <AIDecisionCard recoveryCase={recoveryCase} />

      {/* 3. Strategy Comparison */}
      <StrategyComparison
        strategies={recoveryCase.strategies}
        selectedStrategy={selectedStrategy}
        onSelectStrategy={setSelectedStrategy}
      />

      {/* 4. Action Firewall Safety Card */}
      <ActionFirewallCard firewall={recoveryCase.firewallResult} />

      {/* 5. Autonomous Recovery Timeline */}
      <RecoveryTimeline timeline={recoveryCase.timeline} />

      {/* 6. Recovery Passport & Blockchain Proof */}
      <RecoveryPassportCard recoveryCase={recoveryCase} />

      {/* Execution Confirmation Modal */}
      <Modal
        isOpen={isConfirmModalOpen}
        onClose={() => setIsConfirmModalOpen(false)}
        title="Confirm Recovery Strategy Execution"
        subtitle="Trigger autonomous gateway recovery flow"
        maxWidth="md"
      >
        <div className="space-y-4 text-xs">
          <div className="rounded-lg bg-surface border border-border p-3.5 space-y-2 font-mono">
            <div className="flex justify-between">
              <span className="text-secondaryText">Transaction:</span>
              <span className="font-bold text-primaryText">{recoveryCase.transactionId}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-secondaryText">Selected Strategy:</span>
              <span className="font-bold text-ai-light">{selectedStrategy}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-secondaryText">Expected Recovery:</span>
              <span className="text-success font-bold">
                {formatCurrency(recoveryCase.expectedRecovery)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-secondaryText">Policy Version:</span>
              <span>{recoveryCase.firewallResult.policyVersion}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-secondaryText">AI Confidence:</span>
              <span className="text-ai-light font-bold">{recoveryCase.aiConfidence}%</span>
            </div>
          </div>

          <p className="text-[11px] text-secondaryText leading-relaxed">
            Executing this strategy will invoke the Razorpay recovery API and generate a cryptographic decision proof on the Polygon Devnet.
          </p>

          <div className="flex justify-end gap-2 pt-2 border-t border-border/60">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsConfirmModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleExecute}
              isLoading={isExecuting}
            >
              Execute Now
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
