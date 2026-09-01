'use client';

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import {
  RecoveryCase,
  Transaction,
  BlockchainProof,
  DashboardMetrics,
  Anomaly,
  MerchantDNA,
} from '@/types';
import {
  RecoveryStage,
  STAGE_METADATA_MAP,
  DEMO_STAGE_SEQUENCE,
  getStageMetadata,
} from '@/lib/recoveryStages';
import { mockRecoveryCases } from '@/lib/mock/recovery';
import { mockTransactions } from '@/lib/mock/transactions';
import { mockDashboardMetrics, mockRevenueLeakAnomaly } from '@/lib/mock/dashboard';
import { mockBlockchainProofs } from '@/lib/mock/blockchain';
import { mockMerchantDNA } from '@/lib/mock/analytics';
import confetti from 'canvas-confetti';

interface RecoveryEngineContextType {
  stage: RecoveryStage;
  setStage: (stage: RecoveryStage) => void;
  currentStepIndex: number;
  isDemoOpen: boolean;
  isDemoRunning: boolean;
  isPaused: boolean;
  activeCase: RecoveryCase;
  metrics: DashboardMetrics;
  anomaly: Anomaly;
  cases: RecoveryCase[];
  transactions: Transaction[];
  proofs: BlockchainProof[];
  merchantDNA: MerchantDNA;
  openDemo: () => void;
  closeDemo: () => void;
  startDemo: () => void;
  pauseDemo: () => void;
  resumeDemo: () => void;
  stopDemo: () => void;
  nextStep: () => void;
  prevStep: () => void;
  goToStep: (index: number) => void;
  executeRecoveryCase: (id: string, strategy: string) => Promise<boolean>;
  updatePolicyThresholds: (maxRetries: number, minConfidence: number, autoCap: number) => void;
}

const RecoveryEngineContext = createContext<RecoveryEngineContextType | undefined>(undefined);

export function RecoveryEngineProvider({ children }: { children: React.ReactNode }) {
  const [stage, setStage] = useState<RecoveryStage>('idle');
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0);
  const [isDemoOpen, setIsDemoOpen] = useState<boolean>(false);
  const [isDemoRunning, setIsDemoRunning] = useState<boolean>(false);
  const [isPaused, setIsPaused] = useState<boolean>(false);

  const [metrics, setMetrics] = useState<DashboardMetrics>(mockDashboardMetrics);
  const [anomaly, setAnomaly] = useState<Anomaly>(mockRevenueLeakAnomaly);
  const [cases, setCases] = useState<RecoveryCase[]>(mockRecoveryCases);
  const [transactions, setTransactions] = useState<Transaction[]>(mockTransactions);
  const [proofs, setProofs] = useState<BlockchainProof[]>(mockBlockchainProofs);
  const [merchantDNA, setMerchantDNA] = useState<MerchantDNA>(mockMerchantDNA);

  const activeCase = cases[0];

  const openDemo = useCallback(() => {
    setIsDemoOpen(true);
    setIsDemoRunning(true);
    setIsPaused(false);
    setCurrentStepIndex(0);
    setStage(DEMO_STAGE_SEQUENCE[0]);
  }, []);

  const closeDemo = useCallback(() => {
    setIsDemoOpen(false);
    setIsDemoRunning(false);
    setIsPaused(false);
  }, []);

  const startDemo = useCallback(() => {
    openDemo();
  }, [openDemo]);

  const pauseDemo = useCallback(() => {
    setIsPaused(true);
  }, []);

  const resumeDemo = useCallback(() => {
    setIsPaused(false);
  }, []);

  const stopDemo = useCallback(() => {
    setIsDemoRunning(false);
    setIsPaused(false);
    setStage('idle');
    setCurrentStepIndex(0);
  }, []);

  const goToStep = useCallback((index: number) => {
    if (index >= 0 && index < DEMO_STAGE_SEQUENCE.length) {
      setCurrentStepIndex(index);
      setStage(DEMO_STAGE_SEQUENCE[index]);
    }
  }, []);

  const nextStep = useCallback(() => {
    setCurrentStepIndex((prev) => {
      const nextIdx = Math.min(prev + 1, DEMO_STAGE_SEQUENCE.length - 1);
      setStage(DEMO_STAGE_SEQUENCE[nextIdx]);
      return nextIdx;
    });
  }, []);

  const prevStep = useCallback(() => {
    setCurrentStepIndex((prev) => {
      const nextIdx = Math.max(prev - 1, 0);
      setStage(DEMO_STAGE_SEQUENCE[nextIdx]);
      return nextIdx;
    });
  }, []);

  // Timer driven demo step transitions matching Prompt item 24 durations
  useEffect(() => {
    let timer: NodeJS.Timeout;

    if (isDemoRunning && !isPaused && currentStepIndex < DEMO_STAGE_SEQUENCE.length) {
      const currentStageKey = DEMO_STAGE_SEQUENCE[currentStepIndex];
      const meta = getStageMetadata(currentStageKey);

      timer = setTimeout(() => {
        // Trigger state updates at specific key stages
        if (currentStageKey === 'recovered') {
          try {
            confetti({ particleCount: 50, spread: 70, origin: { y: 0.6 } });
          } catch {}

          setMetrics((prev) => ({
            ...prev,
            revenueRecovered: prev.revenueRecovered + 18500,
            revenueAtRisk: Math.max(0, prev.revenueAtRisk - 18500),
            recoveryRate: 67.4,
            opportunitiesCount: Math.max(0, prev.opportunitiesCount - 1),
          }));

          setCases((prev) =>
            prev.map((c, i) =>
              i === 0 ? { ...c, status: 'Recovered' } : c
            )
          );

          setTransactions((prev) =>
            prev.map((t, i) =>
              i === 0 ? { ...t, status: 'Recovered' } : t
            )
          );
        }

        if (currentStageKey === 'verified') {
          const newProof: BlockchainProof = {
            proofId: `PRF-${Date.now().toString().slice(-6)}`,
            transactionId: 'TXN-82931',
            amount: 18500,
            strategy: 'Retry + Payment Link',
            policyVersion: 'v2.4',
            proofHash: '0x8a91f3c2b84e12d4a976328a9b1c72fc82a10452',
            policyHash: '0x91ac82de941038bc72ef41029481bc91a4729103',
            timestamp: new Date().toISOString(),
            blockNumber: 18294021,
            verified: true,
            txHash: '0x7a31b294c8e102f4a19028e3b1c28f9104820921',
            network: 'Polygon Devnet',
          };

          setProofs((prev) => [newProof, ...prev]);
        }

        if (currentStageKey === 'learning') {
          setMerchantDNA((prev) => ({
            ...prev,
            methodRates: { ...prev.methodRates, UPI: 83.4 },
            learningDataPoints: prev.learningDataPoints + 1,
            modelAccuracy: 94.8,
            lastTrainedAt: 'Just now',
          }));
        }

        if (currentStepIndex < DEMO_STAGE_SEQUENCE.length - 1) {
          const nextIdx = currentStepIndex + 1;
          setCurrentStepIndex(nextIdx);
          setStage(DEMO_STAGE_SEQUENCE[nextIdx]);
        } else {
          // Finished demo
          setIsDemoRunning(false);
          setStage('idle');
        }
      }, meta.durationMs);
    }

    return () => clearTimeout(timer);
  }, [isDemoRunning, isPaused, currentStepIndex]);

  const executeRecoveryCase = useCallback(async (id: string, strategy: string): Promise<boolean> => {
    setStage('executing');
    await new Promise((r) => setTimeout(r, 1200));

    setCases((prev) =>
      prev.map((c) =>
        c.id === id || c.transactionId === id
          ? { ...c, status: 'Recovered', strategy: strategy as any }
          : c
      )
    );

    setTransactions((prev) =>
      prev.map((t) =>
        t.id === id || t.recoveryId === id ? { ...t, status: 'Recovered' } : t
      )
    );

    setMetrics((prev) => ({
      ...prev,
      revenueRecovered: prev.revenueRecovered + 18500,
      revenueAtRisk: Math.max(0, prev.revenueAtRisk - 18500),
      recoveryRate: 67.4,
    }));

    setStage('recovered');
    try { confetti({ particleCount: 50, spread: 70, origin: { y: 0.6 } }); } catch {}

    setTimeout(() => {
      setStage('verified');
      const newProof: BlockchainProof = {
        proofId: `PRF-${Date.now().toString().slice(-6)}`,
        transactionId: id,
        amount: 18500,
        strategy: strategy as any,
        policyVersion: 'v2.4',
        proofHash: '0x8a91f3c2b84e12d4a976328a9b1c72fc82a10452',
        policyHash: '0x91ac82de941038bc72ef41029481bc91a4729103',
        timestamp: new Date().toISOString(),
        blockNumber: 18294022,
        verified: true,
        txHash: '0x7a31b294c8e102f4a19028e3b1c28f9104820921',
        network: 'Polygon Devnet',
      };
      setProofs((prev) => [newProof, ...prev]);
    }, 1200);

    setTimeout(() => {
      setStage('learning');
      setMerchantDNA((prev) => ({
        ...prev,
        methodRates: { ...prev.methodRates, UPI: 83.4 },
        learningDataPoints: prev.learningDataPoints + 1,
      }));
    }, 2400);

    setTimeout(() => {
      setStage('idle');
    }, 3600);

    return true;
  }, []);

  const updatePolicyThresholds = useCallback((maxRetries: number, minConfidence: number, autoCap: number) => {
    setCases((prev) =>
      prev.map((c) => {
        const approved = c.amount <= autoCap && c.aiConfidence >= minConfidence;
        return {
          ...c,
          firewallResult: {
            ...c.firewallResult,
            approved,
            statusMessage: approved
              ? 'ACTION APPROVED - Policy checks passed'
              : 'ACTION BLOCKED - Human Approval Required (Exceeds Policy Limits)',
          },
        };
      })
    );
  }, []);

  return (
    <RecoveryEngineContext.Provider
      value={{
        stage,
        setStage,
        currentStepIndex,
        isDemoOpen,
        isDemoRunning,
        isPaused,
        activeCase,
        metrics,
        anomaly,
        cases,
        transactions,
        proofs,
        merchantDNA,
        openDemo,
        closeDemo,
        startDemo,
        pauseDemo,
        resumeDemo,
        stopDemo,
        nextStep,
        prevStep,
        goToStep,
        executeRecoveryCase,
        updatePolicyThresholds,
      }}
    >
      {children}
    </RecoveryEngineContext.Provider>
  );
}

export function useRecoveryEngine() {
  const context = useContext(RecoveryEngineContext);
  if (!context) {
    throw new Error('useRecoveryEngine must be used within a RecoveryEngineProvider');
  }
  return context;
}
