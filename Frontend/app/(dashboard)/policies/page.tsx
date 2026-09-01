'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Switch } from '@/components/ui/Skeleton';
import { mockPolicySet } from '@/lib/mock/policies';
import { getPolicies, updatePolicies } from '@/lib/api/policies';
import { useRecoveryEngine } from '@/context/RecoveryEngineContext';
import { PolicySet, PolicyRule } from '@/types';
import { formatDate, formatCurrency } from '@/lib/formatters';
import { ShieldCheck, Save } from 'lucide-react';
import confetti from 'canvas-confetti';

export default function PoliciesPage() {
  const { updatePolicyThresholds } = useRecoveryEngine();
  const [policySet, setPolicySet] = useState<PolicySet>(mockPolicySet);
  const [rules, setRules] = useState<PolicyRule[]>(mockPolicySet.rules);
  const [isSaving, setIsSaving] = useState(false);
  const [isDirty, setIsDirty] = useState(false);

  useEffect(() => {
    getPolicies().then((res) => {
      setPolicySet(res);
      setRules(res.rules);
    });
  }, []);

  const handleRuleChange = (id: string, newValue: any) => {
    setRules((prev) =>
      prev.map((r) => (r.id === id ? { ...r, value: newValue } : r))
    );
    setIsDirty(true);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const updated = await updatePolicies(rules);
      setPolicySet(updated);
      setRules(updated.rules);
      setIsDirty(false);

      // Extract values to sync with central Action Firewall state
      const minConfidence = Number(rules.find((r) => r.key === 'min_confidence')?.value ?? 85);
      const autoCap = Number(rules.find((r) => r.key === 'max_auto_amount')?.value ?? 25000);
      const maxRetries = Number(rules.find((r) => r.key === 'max_retries')?.value ?? 2);

      updatePolicyThresholds(maxRetries, minConfidence, autoCap);

      try { confetti({ particleCount: 30 }); } catch {}
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/60 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-primaryText">
              AI Policies & Safety Firewall
            </h1>
            <Badge variant="ai">{policySet.version}</Badge>
          </div>
          <p className="text-xs sm:text-sm text-secondaryText mt-1">
            Configure safety thresholds, autonomous retry limits, and human approval rules.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {isDirty && (
            <span className="text-xs text-warning font-mono animate-pulse">
              Unsaved policy changes
            </span>
          )}
          <Button
            variant="primary"
            size="sm"
            onClick={handleSave}
            isLoading={isSaving}
            disabled={!isDirty}
          >
            <Save className="h-3.5 w-3.5" />
            Save & Publish {policySet.version}
          </Button>
        </div>
      </div>

      {/* Active Version Metadata Header */}
      <Card className="p-4 border-ai-border/40 bg-surface-elevated/80 flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs font-mono">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-success-bg text-success border border-success-border">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <div>
            <span className="font-bold text-primaryText text-sm block">Active Policy Version {policySet.version}</span>
            <span className="text-secondaryText text-[11px]">Status: ● Active & Enforced</span>
          </div>
        </div>

        <div className="flex flex-col sm:items-end text-[11px] text-mutedText">
          <span>Policy Hash: <strong className="text-ai-light">{policySet.hash}</strong></span>
          <span>Last Published: {formatDate(policySet.lastUpdated, { includeTime: true })}</span>
        </div>
      </Card>

      {/* Rules Form Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Autonomous Limits */}
        <Card className="p-5 space-y-4">
          <CardHeader className="p-0 pb-3 border-b border-border/60">
            <CardTitle className="text-sm">Autonomous Execution Caps</CardTitle>
          </CardHeader>
          <CardContent className="p-0 space-y-4">
            {rules.filter((r) => r.category === 'Autonomous' || r.category === 'Limits').map((rule) => (
              <div key={rule.id} className="space-y-1.5 text-xs">
                <div className="flex justify-between items-center">
                  <label className="font-semibold text-primaryText">{rule.title}</label>
                  <span className="font-mono text-ai-light font-bold">
                    {rule.type === 'currency' ? formatCurrency(Number(rule.value)) : `${rule.value} ${rule.unit || ''}`}
                  </span>
                </div>
                <p className="text-[11px] text-secondaryText">{rule.description}</p>
                <input
                  type="number"
                  value={Number(rule.value)}
                  onChange={(e) => handleRuleChange(rule.id, Number(e.target.value))}
                  className="w-full rounded-md border border-border bg-surface px-3 py-1.5 text-xs text-primaryText font-mono focus:outline-none focus:border-ai"
                />
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Timing & Risk Rules */}
        <Card className="p-5 space-y-4">
          <CardHeader className="p-0 pb-3 border-b border-border/60">
            <CardTitle className="text-sm">Timing & Risk Governance</CardTitle>
          </CardHeader>
          <CardContent className="p-0 space-y-4">
            {rules.filter((r) => r.category === 'Timing' || r.category === 'Risk').map((rule) => (
              <div key={rule.id} className="space-y-1.5 text-xs">
                {rule.type === 'boolean' ? (
                  <div className="flex items-center justify-between py-2 border-b border-border/40">
                    <div>
                      <label className="font-semibold text-primaryText block">{rule.title}</label>
                      <p className="text-[11px] text-secondaryText">{rule.description}</p>
                    </div>
                    <Switch
                      checked={Boolean(rule.value)}
                      onChange={(val) => handleRuleChange(rule.id, val)}
                    />
                  </div>
                ) : (
                  <div>
                    <div className="flex justify-between items-center">
                      <label className="font-semibold text-primaryText">{rule.title}</label>
                      <span className="font-mono text-ai-light font-bold">
                        {rule.value} {rule.unit || ''}
                      </span>
                    </div>
                    <p className="text-[11px] text-secondaryText mb-1">{rule.description}</p>
                    <input
                      type="number"
                      value={Number(rule.value)}
                      onChange={(e) => handleRuleChange(rule.id, Number(e.target.value))}
                      className="w-full rounded-md border border-border bg-surface px-3 py-1.5 text-xs text-primaryText font-mono focus:outline-none focus:border-ai"
                    />
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
