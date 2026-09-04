'use client';

import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import {
  RecoveryCase,
  Transaction,
  BlockchainProof,
  DashboardMetrics,
  Anomaly,
  MerchantDNA,
  Payment,
  PaymentMethod,
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
import { mockMerchantDNA } from '@/lib/mock/analytics';
import { getPayments, paymentsToRecoveryCases, computeMetrics, executeRecovery, syncRazorpayPayments } from '@/lib/api/payments';
import confetti from 'canvas-confetti';

export type ConnectionStatus = 'live' | 'offline' | 'loading';

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
  dataSource: 'live' | 'mock';
  isLoading: boolean;
  backendError: string | null;
  connectionStatus: ConnectionStatus;
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
  syncRazorpay: () => Promise<boolean>;
}

const RecoveryEngineContext = createContext<RecoveryEngineContextType | undefined>(undefined);

function getWebSocketUrl(): string {
  if (process.env.NEXT_PUBLIC_WS_URL) {
    return process.env.NEXT_PUBLIC_WS_URL;
  }
  if (typeof window !== 'undefined') {
    const host = window.location.hostname || '127.0.0.1';
    return `ws://${host}:8000/ws/dashboard`;
  }
  return 'ws://127.0.0.1:8000/ws/dashboard';
}

const RECONNECT_INTERVAL = 5000;
const MAX_RECONNECT_ATTEMPTS = 10;

function processPaymentsData(payments: Payment[]) {
  const realCases = paymentsToRecoveryCases(payments);
  const computed = computeMetrics(payments);
  const transactions = payments.map((p) => {
    const paymentMethod = p.payment_method 
      ? (p.payment_method === 'upi' ? 'UPI' : 
         p.payment_method === 'card' ? 'Cards' :
         p.payment_method === 'netbanking' ? 'Net Banking' :
         p.payment_method === 'wallet' ? 'Wallet' : 'N/A')
      : 'N/A';
    
    return {
      id: p.razorpay_payment_id || `Payment #${p.id}`,
      customerId: `PAY-${p.id}`,
      customerName: p.customer_type || 'N/A',
      amount: p.amount,
      currency: p.currency || 'INR',
      paymentMethod: paymentMethod as PaymentMethod,
      status: (p.recovery_status || '').toUpperCase() === 'SUCCESS' ? ('Recovered' as const) : ('Pending' as const),
      failureReason: p.failure_reason as any,
      failureCode: p.error_code || undefined,
      createdAt: p.payment_timestamp || p.created_at || '',
      updatedAt: p.created_at || '',
      gateway: p.gateway || 'Razorpay',
      recoveryId: `Payment #${p.id}`,
    };
  });
  const metrics: DashboardMetrics = {
    revenueAtRisk: computed.revenueAtRisk,
    revenueAtRiskChange: 0,
    revenueRecovered: computed.revenueRecovered,
    revenueRecoveredChange: 0,
    recoveryRate: computed.recoveryRate,
    recoveryRateChange: 0,
    opportunitiesCount: computed.opportunitiesCount,
    opportunitiesChange: 0,
    aiActionsCount: computed.aiActionsCount,
    policyComplianceRate: mockDashboardMetrics.policyComplianceRate,
  };
  return { realCases, transactions, metrics };
}

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
  const [proofs, setProofs] = useState<BlockchainProof[]>([]);
  const [merchantDNA, setMerchantDNA] = useState<MerchantDNA>(mockMerchantDNA);
  const [dataSource, setDataSource] = useState<'live' | 'mock'>('mock');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [backendError, setBackendError] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('loading');

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef(true);

  // Fetch real payment records from the FastAPI backend on mount.
  // Real PostgreSQL -> FastAPI -> Next.js is the single source of truth.
  // Mock data is only used as a fallback when the backend is unreachable.
  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const payments = await getPayments();
        if (cancelled) return;

        if (Array.isArray(payments) && payments.length > 0) {
          const { realCases, transactions: txns, metrics: computedMetrics } = processPaymentsData(payments);
          setCases(realCases);
          setTransactions(txns);
          setMetrics(computedMetrics);
          setDataSource('live');
          setBackendError(null);
        } else if (cancelled) {
          return;
        } else {
          setDataSource('mock');
        }
      } catch (e: any) {
        if (cancelled) return;
        setDataSource('mock');
        setBackendError('Unable to connect to RecoverAI backend.');
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  // WebSocket connection for real-time updates
  useEffect(() => {
    isMountedRef.current = true;
    reconnectAttemptsRef.current = 0;

    const connect = () => {
      if (!isMountedRef.current) return;

      try {
        const wsUrl = getWebSocketUrl();
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          if (!isMountedRef.current) {
            ws.close();
            return;
          }
          setConnectionStatus('live');
          reconnectAttemptsRef.current = 0;
          setBackendError(null);
        };

        ws.onmessage = (event) => {
          if (!isMountedRef.current) return;

          try {
            const message = JSON.parse(event.data);
            
            if (message.type === 'dashboard_update' && message.data) {
              const { payments, ...metricsData } = message.data;
              
              // Update metrics directly from backend
              setMetrics((prev) => ({
                ...prev,
                ...metricsData,
              }));

              // Update cases and transactions from payments
              if (Array.isArray(payments)) {
                const { realCases, transactions: txns } = processPaymentsData(payments);
                setCases(realCases);
                setTransactions(txns);
                
                // If we have live data, update dataSource
                if (payments.length > 0) {
                  setDataSource('live');
                  setBackendError(null);
                }
              }
            } else if (message.type === 'pong') {
              // Heartbeat response
            }
          } catch (e) {
            console.error('Failed to parse WebSocket message:', e);
          }
        };

        ws.onerror = (event) => {
          // Standard browser WebSocket error events are generic Event instances without diagnostic payload (W3C spec).
          // Connection teardown and auto-reconnection are handled in ws.onclose.
          // Only log if an explicit message string or error details are present.
          const errorMsg = (event as any)?.message || (typeof event === 'string' ? event : null);
          if (errorMsg) {
            console.warn('WebSocket warning:', errorMsg);
          }
        };

        ws.onclose = () => {
          if (!isMountedRef.current) return;
          
          setConnectionStatus('offline');
          wsRef.current = null;

          // Attempt reconnection
          if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
            reconnectAttemptsRef.current++;
            reconnectTimeoutRef.current = setTimeout(() => {
              connect();
            }, RECONNECT_INTERVAL);
          } else {
            setBackendError('WebSocket connection lost. Unable to reconnect after multiple attempts.');
          }
        };
      } catch (e) {
        console.error('Failed to create WebSocket connection:', e);
        setConnectionStatus('offline');
        
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current++;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, RECONNECT_INTERVAL);
        }
      }
    };

    connect();

    // Heartbeat to keep connection alive
    const heartbeatInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);

    return () => {
      isMountedRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      clearInterval(heartbeatInterval);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

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
    if (dataSource === 'live') {
      const action = strategy.toUpperCase().includes('RETRY + PAYMENT')
        ? 'HYBRID'
        : strategy.toUpperCase().replaceAll(' + ', '_');
      const result = await executeRecovery(id, action);
      if (result.outcome === 'SUCCESS' || result.outcome === 'DUPLICATE') {
        const payments = await getPayments();
        const { realCases, transactions: txns, metrics: computedMetrics } = processPaymentsData(payments);
        setCases(realCases);
        setTransactions(txns);
        setMetrics(computedMetrics);
        return result.outcome === 'SUCCESS';
      }
      return false;
    }

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

    setTimeout(() => setStage('verified'), 1200);

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
  }, [dataSource]);

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

  const syncRazorpay = useCallback(async (): Promise<boolean> => {
    try {
      const result = await syncRazorpayPayments();
      if (result && result.success) {
        const payments = await getPayments();
        if (Array.isArray(payments) && payments.length > 0) {
          const { realCases, transactions: txns, metrics: computedMetrics } = processPaymentsData(payments);
          setCases(realCases);
          setTransactions(txns);
          setMetrics(computedMetrics);
          setDataSource('live');
        }
        return true;
      }
      return false;
    } catch {
      return false;
    }
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
        dataSource,
        isLoading,
        backendError,
        connectionStatus,
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
        syncRazorpay,
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