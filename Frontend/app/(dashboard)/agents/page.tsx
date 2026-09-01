'use client';

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { OllamaStatusCard } from '@/components/ai/OllamaStatusCard';
import { mockAgents, mockAgentActivityStream } from '@/lib/mock/agents';
import { Bot, Activity } from 'lucide-react';

export default function AgentsPage() {
  const [agents] = useState(mockAgents);
  const [logs] = useState(mockAgentActivityStream);

  const orchestrationFlow = [
    { name: 'Detection Agent', role: 'Detect', color: 'text-warning' },
    { name: 'Prediction Engine', role: 'Predict', color: 'text-info-light' },
    { name: 'Recovery Agent', role: 'Reason (Ollama)', color: 'text-ai-light' },
    { name: 'Digital Twin', role: 'Simulate', color: 'text-ai-light' },
    { name: 'AI Action Firewall', role: 'Validate', color: 'text-success' },
    { name: 'Learning Agent', role: 'Learn', color: 'text-success' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/60 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-primaryText">
              AI Operations Center
            </h1>
            <Badge variant="ai">Multi-Agent Swarm</Badge>
          </div>
          <p className="text-xs sm:text-sm text-secondaryText mt-1">
            Real-time telemetry and task orchestration for autonomous recovery agents.
          </p>
        </div>

        <span className="font-mono text-xs text-success flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-success animate-pulse" />
          6 Swarm Agents Synchronized
        </span>
      </div>

      {/* Ollama Local AI Engine Card */}
      <OllamaStatusCard />

      {/* Multi-Agent Orchestration Flow Visualization */}
      <Card className="p-5 border-ai-border/40 bg-gradient-to-r from-surface to-ai-bg/10 shadow-glow">
        <h3 className="text-xs font-semibold text-secondaryText uppercase tracking-wider mb-4">
          Multi-Agent Workflow Pipeline
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 text-xs">
          {orchestrationFlow.map((step, idx) => (
            <div
              key={idx}
              className="flex flex-col items-center text-center p-3 rounded-lg border border-border/80 bg-surface-elevated/80 relative"
            >
              <div className="h-6 w-6 rounded-full bg-ai/20 border border-ai/40 flex items-center justify-center font-bold font-mono text-[10px] text-ai-light mb-1.5">
                {idx + 1}
              </div>
              <span className="font-bold text-primaryText text-[11px] truncate w-full">{step.name}</span>
              <span className={`text-[10px] font-mono mt-0.5 ${step.color}`}>{step.role}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Grid of All Agents */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {agents.map((agent) => (
          <Card key={agent.id} className="p-4 space-y-3 hover:border-border/90 transition-colors">
            <div className="flex items-center justify-between border-b border-border/60 pb-3">
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-ai/20 text-ai-light border border-ai/40">
                  <Bot className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="font-bold text-sm text-primaryText">{agent.name}</h3>
                  <span className="text-[10px] font-mono text-mutedText">{agent.model}</span>
                </div>
              </div>
              <Badge variant={agent.status === 'ACTIVE' ? 'success' : 'ai'} size="sm">
                ● {agent.status}
              </Badge>
            </div>

            <p className="text-xs text-secondaryText leading-relaxed min-h-[36px]">
              <strong>Current Task:</strong> {agent.currentTask}
            </p>

            <div className="space-y-1.5 text-xs font-mono bg-surface-elevated/50 p-2.5 rounded border border-border/40">
              <div className="flex justify-between">
                <span className="text-secondaryText">Processed:</span>
                <span className="text-primaryText font-bold">{agent.processedCount.toLocaleString('en-IN')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondaryText">Success Rate:</span>
                <span className="text-success font-bold">{agent.successRate}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondaryText">Avg Latency:</span>
                <span className="text-ai-light font-bold">{agent.avgLatencyMs}ms</span>
              </div>
            </div>

            <div className="text-[11px] text-mutedText border-t border-border/40 pt-2 truncate">
              <strong>Last Action ({agent.lastActionTime}):</strong> {agent.lastAction}
            </div>
          </Card>
        ))}
      </div>

      {/* Agent Activity Stream */}
      <Card className="p-0">
        <CardHeader className="flex flex-row items-center justify-between border-b border-border/60 pb-3">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-ai" />
            <CardTitle>Real-Time Agent Activity Log</CardTitle>
          </div>
          <span className="text-xs font-mono text-mutedText">Live Feed</span>
        </CardHeader>

        <CardContent className="p-4 space-y-2 font-mono text-xs max-h-80 overflow-y-auto">
          {logs.map((log) => (
            <div
              key={log.id}
              className="flex items-center justify-between p-2.5 rounded border border-border/40 bg-surface-elevated/40 text-xs"
            >
              <div className="flex items-center gap-3">
                <span className="text-[10px] text-mutedText">{log.timestamp}</span>
                <span className="font-bold text-ai-light text-[11px]">{log.agentName}</span>
                <span className="text-secondaryText">{log.message}</span>
              </div>
              <Badge variant={log.status === 'success' ? 'success' : 'info'} size="sm">
                {log.status}
              </Badge>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
