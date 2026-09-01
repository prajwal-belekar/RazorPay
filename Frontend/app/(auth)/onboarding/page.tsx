'use client';

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { ShieldAlert, CheckCircle2, ArrowRight, ArrowLeft } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);

  const steps = [
    'Merchant Information',
    'Razorpay Connection',
    'Recovery Policies',
    'AI Configuration',
    'Blockchain Configuration',
    'Finish',
  ];

  return (
    <div className="min-h-screen bg-bg text-primaryText flex items-center justify-center p-4">
      <div className="w-full max-w-xl space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-1">
          <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-ai/20 border border-ai/50 text-ai-light shadow-glow mb-1">
            <ShieldAlert className="h-5 w-5" />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-primaryText">Merchant Onboarding Wizard</h1>
          <p className="text-xs text-secondaryText">Setup RecoverAI autonomous payment recovery engine</p>
        </div>

        {/* Progress Indicator */}
        <div className="flex items-center justify-between px-4 text-xs font-mono">
          {steps.map((name, idx) => {
            const num = idx + 1;
            const isDone = num < step;
            const isCurrent = num === step;
            return (
              <div key={num} className="flex items-center gap-1">
                <div
                  className={`h-6 w-6 rounded-full flex items-center justify-center text-[10px] font-bold ${
                    isDone
                      ? 'bg-success text-black'
                      : isCurrent
                      ? 'bg-ai text-white'
                      : 'bg-surface-elevated text-mutedText border border-border'
                  }`}
                >
                  {isDone ? '✓' : num}
                </div>
                {idx < steps.length - 1 && (
                  <div className={`h-0.5 w-6 sm:w-10 ${isDone ? 'bg-success' : 'bg-border'}`} />
                )}
              </div>
            );
          })}
        </div>

        {/* Main Step Card */}
        <Card className="p-6 border-border/80 bg-surface-elevated/90 shadow-card">
          <CardHeader className="p-0 pb-4 border-b border-border/60">
            <CardTitle className="text-base font-bold">
              Step {step}: {steps[step - 1]}
            </CardTitle>
          </CardHeader>

          <CardContent className="p-0 pt-4 space-y-4 text-xs">
            {step === 1 && (
              <div className="space-y-3">
                <Input label="Company / Merchant Name" defaultValue="Acme FinTech Systems" />
                <Input label="Support Email" defaultValue="payments@acmefintech.io" />
                <Input label="Estimated Monthly Failed Revenue" defaultValue="₹50,000,000" />
              </div>
            )}

            {step === 2 && (
              <div className="space-y-3">
                <Input label="Razorpay Key ID" defaultValue="rzp_live_9821491024" />
                <Input label="Razorpay Secret" type="password" defaultValue="••••••••••••••••" />
                <div className="rounded bg-surface p-2 text-success text-[11px]">
                  ✓ Razorpay sandbox webhooks connected successfully.
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-3">
                <Input label="Autonomous Transaction Cap" defaultValue="₹50,000" />
                <Input label="Maximum Retries Per Payment" defaultValue="2" />
                <Input label="Default Cooldown Interval" defaultValue="15 minutes" />
              </div>
            )}

            {step === 4 && (
              <div className="space-y-3">
                <div className="p-3 rounded bg-surface border border-border">
                  <span className="font-bold text-primaryText block">AI Engine Selection</span>
                  <span className="text-secondaryText text-[11px]">Local Ollama Llama3.1-8B initialized.</span>
                </div>
                <Input label="Minimum AI Confidence" defaultValue="85%" />
              </div>
            )}

            {step === 5 && (
              <div className="space-y-3">
                <div className="p-3 rounded bg-surface border border-border">
                  <span className="font-bold text-success block">Polygon Devnet Wallet Connected</span>
                  <span className="text-secondaryText font-mono text-[10px]">0x91ac82de941038bc72ef41029481bc91a4729103</span>
                </div>
              </div>
            )}

            {step === 6 && (
              <div className="text-center py-6 space-y-3">
                <CheckCircle2 className="h-12 w-12 text-success mx-auto" />
                <h3 className="text-lg font-bold text-primaryText">Setup Complete!</h3>
                <p className="text-xs text-secondaryText max-w-sm mx-auto">
                  RecoverAI autonomous recovery engine is ready to protect your revenue stream.
                </p>
              </div>
            )}

            <div className="flex justify-between items-center pt-4 border-t border-border/60">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setStep((s) => Math.max(s - 1, 1))}
                disabled={step === 1}
              >
                <ArrowLeft className="h-3.5 w-3.5 mr-1" />
                Back
              </Button>

              {step < 6 ? (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => setStep((s) => Math.min(s + 1, 6))}
                >
                  Continue
                  <ArrowRight className="h-3.5 w-3.5 ml-1" />
                </Button>
              ) : (
                <Button
                  variant="ai"
                  size="sm"
                  onClick={() => router.push('/dashboard')}
                >
                  Go to Command Center
                  <ArrowRight className="h-3.5 w-3.5 ml-1" />
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
