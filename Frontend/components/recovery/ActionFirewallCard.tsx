'use client';

import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { FirewallResult } from '@/types';
import { ShieldCheck, ShieldAlert, CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';

export function ActionFirewallCard({ firewall }: { firewall: FirewallResult }) {
  return (
    <Card className={`border ${firewall.approved ? 'border-success-border/60 bg-success-bg/10' : 'border-danger-border/60 bg-danger-bg/10'}`}>
      <CardHeader className="flex flex-row items-center justify-between border-b border-border/60 pb-3">
        <div className="flex items-center gap-2">
          <div className={`flex h-7 w-7 items-center justify-center rounded-lg border ${
            firewall.approved
              ? 'bg-success-bg text-success border-success-border'
              : 'bg-danger-bg text-danger border-danger-border'
          }`}>
            {firewall.approved ? <ShieldCheck className="h-4 w-4" /> : <ShieldAlert className="h-4 w-4" />}
          </div>
          <div>
            <CardTitle className="text-base font-bold text-primaryText">AI Action Firewall</CardTitle>
            <p className="text-xs text-secondaryText">Safety & Merchant Governance Guard</p>
          </div>
        </div>

        <Badge variant={firewall.approved ? 'success' : 'danger'}>
          {firewall.approved ? '✓ ACTION APPROVED' : '× ACTION BLOCKED'}
        </Badge>
      </CardHeader>

      <CardContent className="pt-4 space-y-4">
        <div className="rounded-md bg-surface/80 border border-border/60 p-3 flex items-center justify-between text-xs">
          <span className="font-semibold text-primaryText">{firewall.statusMessage}</span>
          <span className="font-mono text-[10px] text-mutedText">Policy {firewall.policyVersion}</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
          {firewall.checks.map((check, index) => {
            const isPassed = check.status === 'PASSED';
            const key = check.id ?? `${check.name}-${index}`;
            return (
              <div
                key={key}
                className={`flex items-start gap-2.5 p-2.5 rounded-lg border text-xs ${
                  isPassed
                    ? 'border-success-border/40 bg-surface/40 text-primaryText'
                    : 'border-danger-border/50 bg-danger-bg/20 text-danger'
                }`}
              >
                {isPassed ? (
                  <CheckCircle2 className="h-4 w-4 text-success shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="h-4 w-4 text-danger shrink-0 mt-0.5" />
                )}
                <div className="space-y-0.5 flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-[11px]">{check.name}</span>
                    <span className={`text-[10px] font-mono font-medium ${isPassed ? 'text-success' : 'text-danger'}`}>
                      {check.status}
                    </span>
                  </div>
                  <p className="text-[10px] text-secondaryText">{check.description}</p>
                  <div className="flex justify-between text-[10px] font-mono text-mutedText pt-1 border-t border-border/40">
                    <span>Limit: {check.policyValue}</span>
                    <span>Actual: {check.actualValue}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
