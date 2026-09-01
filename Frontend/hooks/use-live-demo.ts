import { useRecoveryEngine } from '@/context/RecoveryEngineContext';
import { DEMO_STAGE_SEQUENCE } from '@/lib/recoveryStages';

export function useLiveDemo() {
  const engine = useRecoveryEngine();

  return {
    isOpen: engine.isDemoOpen,
    currentStepIndex: engine.currentStepIndex,
    isAutoRunning: engine.isDemoRunning && !engine.isPaused,
    setIsAutoRunning: (val: boolean) => {
      if (val) {
        engine.resumeDemo();
      } else {
        engine.pauseDemo();
      }
    },
    totalSteps: DEMO_STAGE_SEQUENCE.length,
    startDemo: engine.startDemo,
    closeDemo: engine.closeDemo,
    nextStep: engine.nextStep,
    prevStep: engine.prevStep,
    setCurrentStepIndex: engine.goToStep,
  };
}
