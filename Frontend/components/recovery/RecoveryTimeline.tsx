'use client';

import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { TimelineEvent } from '@/types';
import { CheckCircle2, AlertTriangle, Info, Clock, ShieldCheck, Zap } from 'lucide-react';

export function RecoveryTimeline({ timeline }: { timeline: TimelineEvent[] }) {
  const getStatusIcon = (status: TimelineEvent['status']) => {
    switch (status) {
      case 'success':
        return <CheckCircle2 className="h-4 w-4 text-success" />;
      case 'error':
        return <AlertTriangle className="h-4 w-4 text-danger" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-warning" />;
      default:
        return <Info className="h-4 w-4 text-ai-light" />;
    }
  };

  return (
    <Card className="p-0">
      <CardHeader className="flex flex-row items-center justify-between border-b border-border/60 pb-3">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-ai" />
          <CardTitle>Autonomous Recovery Audit Trail</CardTitle>
        </div>
        <span className="text-xs text-mutedText font-mono">Real-time Telemetry</span>
      </CardHeader>

      <CardContent className="p-5">
        <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-border">
          {timeline.map((event, idx) => (
            <div key={event.id || idx} className="relative flex items-start gap-4 text-xs group">
              {/* Timeline Icon Node */}
              <div className="absolute -left-6 top-0 flex h-5 w-5 items-center justify-center rounded-full bg-surface-elevated border border-border shadow-subtle">
                {getStatusIcon(event.status)}
              </div>

              <div className="flex-1 rounded-lg border border-border/60 bg-surface-elevated/40 p-3 hover:border-border/90 transition-colors">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-primaryText text-xs">{event.title}</span>
                    <span className="rounded bg-surface px-1.5 py-0.2 text-[10px] text-ai-light font-mono border border-border">
                      {event.component}
                    </span>
                  </div>
                  <span className="font-mono text-[10px] text-mutedText">{event.timestamp}</span>
                </div>
                <p className="text-[11px] text-secondaryText leading-relaxed">{event.description}</p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
