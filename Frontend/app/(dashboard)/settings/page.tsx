'use client';

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Switch } from '@/components/ui/Skeleton';
import { Tabs } from '@/components/ui/Tabs';
import { Sliders, ShieldCheck, Sparkles, Save, User, Building, Bell, Lock, Cpu } from 'lucide-react';
import confetti from 'canvas-confetti';

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('ai');
  const [aiMode, setAiMode] = useState('Local Ollama');
  const [confidenceThreshold, setConfidenceThreshold] = useState(85);
  const [autonomousMode, setAutonomousMode] = useState(true);
  const [razorpayKey, setRazorpayKey] = useState('rzp_test_98124901234');
  const [isSaved, setIsSaved] = useState(false);

  const handleSave = () => {
    setIsSaved(true);
    try { confetti({ particleCount: 30 }); } catch {}
    setTimeout(() => setIsSaved(false), 2500);
  };

  const tabs = [
    { id: 'ai', label: 'AI & Ollama Settings', icon: <Sparkles className="h-3.5 w-3.5" /> },
    { id: 'merchant', label: 'Merchant Gateway', icon: <Building className="h-3.5 w-3.5" /> },
    { id: 'notifications', label: 'Notifications', icon: <Bell className="h-3.5 w-3.5" /> },
    { id: 'security', label: 'Security & Blockchain', icon: <Lock className="h-3.5 w-3.5" /> },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/60 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-primaryText">
            Settings & Configuration
          </h1>
          <p className="text-xs sm:text-sm text-secondaryText mt-1">
            Manage your AI models, Razorpay sandbox credentials, and autonomous recovery rules.
          </p>
        </div>

        <Button variant="primary" size="sm" onClick={handleSave}>
          <Save className="h-3.5 w-3.5" />
          {isSaved ? 'Saved!' : 'Save Settings'}
        </Button>
      </div>

      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {activeTab === 'ai' && (
        <Card className="p-6 space-y-6">
          <CardHeader className="p-0 pb-3 border-b border-border/60">
            <CardTitle className="text-sm">AI Engine & Local Ollama Configuration</CardTitle>
          </CardHeader>
          <CardContent className="p-0 space-y-5 text-xs">
            <div className="space-y-2">
              <label className="font-semibold text-primaryText">AI Execution Mode</label>
              <div className="grid grid-cols-3 gap-3">
                {['Local Ollama', 'Cloud AI', 'Hybrid'].map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setAiMode(mode)}
                    className={`p-3 rounded-lg border text-left font-mono transition-colors ${
                      aiMode === mode
                        ? 'border-ai bg-ai-bg/20 text-ai-light font-bold'
                        : 'border-border bg-surface-elevated text-secondaryText'
                    }`}
                  >
                    {mode}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between">
                <label className="font-semibold text-primaryText">Minimum AI Confidence Threshold</label>
                <span className="font-mono text-ai-light font-bold">{confidenceThreshold}%</span>
              </div>
              <input
                type="range"
                min={60}
                max={95}
                value={confidenceThreshold}
                onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
                className="w-full accent-ai cursor-pointer"
              />
              <span className="text-[11px] text-mutedText">
                AI will only execute retries when model confidence equals or exceeds {confidenceThreshold}%.
              </span>
            </div>

            <div className="flex items-center justify-between py-2 border-t border-border/40">
              <div>
                <label className="font-semibold text-primaryText block">Autonomous Action Mode</label>
                <span className="text-[11px] text-secondaryText">Allow AI to trigger Razorpay retries automatically within policy limits</span>
              </div>
              <Switch checked={autonomousMode} onChange={setAutonomousMode} />
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'merchant' && (
        <Card className="p-6 space-y-4">
          <CardHeader className="p-0 pb-3 border-b border-border/60">
            <CardTitle className="text-sm">Razorpay Integration Sandbox</CardTitle>
          </CardHeader>
          <CardContent className="p-0 space-y-4 text-xs">
            <Input
              label="Razorpay Key ID"
              value={razorpayKey}
              onChange={(e) => setRazorpayKey(e.target.value)}
            />
            <div className="space-y-1">
              <label className="text-xs font-medium text-secondaryText">Webhook Signing Secret</label>
              <Input type="password" value="whsec_mock_981240129840192" readOnly />
            </div>
            <div className="rounded-lg bg-surface border border-border p-3 text-[11px] text-secondaryText">
              <strong>Connected Sandbox:</strong> HDFC UPI & ICICI Card Test Gateways active.
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'notifications' && (
        <Card className="p-6 space-y-4">
          <CardHeader className="p-0 pb-3 border-b border-border/60">
            <CardTitle className="text-sm">Notification Channels</CardTitle>
          </CardHeader>
          <CardContent className="p-0 space-y-3 text-xs">
            <div className="flex items-center justify-between py-2 border-b border-border/40">
              <div>
                <label className="font-semibold text-primaryText block">Revenue Leak Spike Alerts</label>
                <span className="text-[11px] text-secondaryText">Receive instant notification when payment failure rate spikes &gt; 20%</span>
              </div>
              <Switch checked={true} />
            </div>

            <div className="flex items-center justify-between py-2 border-b border-border/40">
              <div>
                <label className="font-semibold text-primaryText block">High-Value Recovery Sign-Off</label>
                <span className="text-[11px] text-secondaryText">Notify when a transaction &gt; ₹50,000 requires human authorization</span>
              </div>
              <Switch checked={true} />
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'security' && (
        <Card className="p-6 space-y-4">
          <CardHeader className="p-0 pb-3 border-b border-border/60">
            <CardTitle className="text-sm">Security & Blockchain Ledger Settings</CardTitle>
          </CardHeader>
          <CardContent className="p-0 space-y-3 text-xs">
            <div className="space-y-1 font-mono">
              <label className="text-secondaryText block">Blockchain Ledger Network</label>
              <div className="p-2.5 rounded bg-surface border border-border text-primaryText font-bold">
                Polygon POS Enterprise Devnet (Chain ID 1370)
              </div>
            </div>
            <div className="space-y-1 font-mono">
              <label className="text-secondaryText block">Smart Contract Address</label>
              <div className="p-2.5 rounded bg-surface border border-border text-ai-light truncate">
                0x91ac82de941038bc72ef41029481bc91a4729103
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
