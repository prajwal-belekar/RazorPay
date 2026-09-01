'use client';

import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { mockAgents } from '@/lib/mock/agents';
import { useRecoveryEngine } from '@/context/RecoveryEngineContext';
import { getStageMetadata } from '@/lib/recoveryStages';
import { Bot } from 'lucide-react';
import Link from 'next/link';

export function AgentStatusSummary() {
  const { stage } = useRecoveryEngine();
  const stageMeta = getStageMetadata(stage);

  return (
    <Card className="p-0">
      <CardHeader className="flex flex-row items-center justify-between border-b border-border/60 pb-3">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-ai" />
          <CardTitle>Autonomous AI Swarm Telemetry</CardTitle>
        </div>
        <Link
          href="/agents"
          className="text-xs text-ai-light hover:underline font-medium"
        >
          View Swarm Center →
        </Link>
      </CardHeader>

      <CardContent className="p-4 space-y-3">
        {mockAgents.slice(0, 4).map((agent) => {
          const isActiveForStage = agent.role.toLowerCase() === stageMeta.activeAgentRole.toLowerCase();

          return (
            <div
              key={agent.id}
              className={`rounded-lg border p-3 text-xs space-y-2 transition-all ${
                isActiveForStage
                  ? 'border-ai bg-ai-bg/20 shadow-subtle'
                  : 'border-border/60 bg-surface-elevated/60 hover:border-border/90'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-primaryText">{agent.name}</span>
                  <span className="text-[10px] font-mono text-mutedText">({agent.model})</span>
                </div>
                <Badge
                  variant={isActiveForStage ? 'ai' : agent.status === 'ACTIVE' ? 'success' : 'info'}
                  size="sm"
                >
                  ● {isActiveForStage ? 'EXECUTING TASK' : agent.status}
                </Badge>
              </div>

              <p className="text-[11px] text-secondaryText truncate">
                {isActiveForStage ? stageMeta.detail : agent.currentTask}
              </p>

              <div className="flex items-center justify-between pt-1 border-t border-border/40 text-[11px] font-mono text-mutedText">
                <span>Processed: <strong className="text-primaryText">{agent.processedCount.toLocaleString('en-IN')}</strong></span>
                <span>Success: <strong className="text-success">{agent.successRate}%</strong></span>
                <span>Latency: <strong className="text-ai-light">{agent.avgLatencyMs}ms</strong></span>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
