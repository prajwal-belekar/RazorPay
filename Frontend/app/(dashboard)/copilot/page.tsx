'use client';

import React, { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { askCopilot } from '@/lib/api/ai';
import { CopilotMessage } from '@/types';
import { Sparkles, Send, Bot, User, ArrowRight } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function CopilotPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<CopilotMessage[]>([
    {
      id: 'msg-1',
      sender: 'assistant',
      timestamp: '09:00 AM',
      text: "Hello! I am your Recovery Intelligence Copilot. You can ask me questions about your revenue at risk, payment failure telemetry, optimal recovery strategies, or run custom scenario simulations.",
      actions: [
        { label: 'View Revenue Radar', action: '/revenue-radar' },
        { label: 'Simulate Strategy', action: '/simulator' },
        { label: 'View Transactions', action: '/transactions' },
      ],
    },
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const suggestedQuestions = [
    "How much revenue is currently at risk?",
    "Why did recovery rate decrease?",
    "Which strategy performs best?",
    "Show high-value failed payments.",
    "What if retry cooldown increases?",
    "Which payment method has the highest failure rate?",
  ];

  const handleSend = async (queryText?: string) => {
    const textToSend = queryText || inputQuery;
    if (!textToSend.trim()) return;

    const userMsg: CopilotMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      text: textToSend,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery('');
    setIsLoading(true);

    try {
      const res = await askCopilot(textToSend);
      if (res.success && res.data) {
        setMessages((prev) => [...prev, res.data]);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border/60 pb-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-ai/20 text-ai-light border border-ai/50 shadow-glow">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-primaryText">Recovery Intelligence Copilot</h1>
              <Badge variant="ai">Ollama Llama 3.1 8B</Badge>
            </div>
            <p className="text-xs text-secondaryText">Query financial telemetry, anomaly root causes & strategy ROI</p>
          </div>
        </div>

        <span className="text-xs text-success font-mono hidden sm:flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-success animate-pulse" />
          Synchronized
        </span>
      </div>

      {/* Suggested Questions Pills */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar text-xs">
        <span className="text-mutedText text-[11px] font-semibold whitespace-nowrap">Suggested Queries:</span>
        {suggestedQuestions.map((q, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(q)}
            className="rounded-full border border-border bg-surface-elevated px-3 py-1 text-secondaryText hover:text-primaryText hover:border-ai/50 hover:bg-ai/10 transition-colors whitespace-nowrap cursor-pointer"
          >
            {q}
          </button>
        ))}
      </div>

      {/* Main Conversation Box */}
      <Card className="p-4 sm:p-6 space-y-4 min-h-[420px] flex flex-col justify-between">
        <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 text-xs ${
                msg.sender === 'user' ? 'flex-row-reverse' : ''
              }`}
            >
              <div
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                  msg.sender === 'user'
                    ? 'bg-surface-elevated text-primaryText border border-border'
                    : 'bg-ai/20 text-ai-light border border-ai/40'
                }`}
              >
                {msg.sender === 'user' ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
              </div>

              <div
                className={`space-y-3 rounded-xl p-4 max-w-xl ${
                  msg.sender === 'user'
                    ? 'bg-surface-elevated text-primaryText border border-border'
                    : 'bg-surface text-primaryText border border-border/80 shadow-subtle'
                }`}
              >
                <div className="flex justify-between items-center text-[10px] text-mutedText border-b border-border/40 pb-1">
                  <span className="font-bold">{msg.sender === 'user' ? 'Merchant Operator' : 'Recovery Copilot'}</span>
                  <span className="font-mono">{msg.timestamp}</span>
                </div>

                <p className="leading-relaxed text-xs font-sans">{msg.text}</p>

                {/* Metric Card */}
                {msg.metricCard && (
                  <div className="rounded-lg bg-surface-elevated border border-border/80 p-3 flex items-center justify-between font-mono">
                    <div>
                      <span className="text-[10px] text-secondaryText block">{msg.metricCard.label}</span>
                      <span className="text-lg font-bold text-primaryText">{msg.metricCard.value}</span>
                    </div>
                    {msg.metricCard.change && (
                      <span className="text-xs text-success font-semibold">{msg.metricCard.change}</span>
                    )}
                  </div>
                )}

                {/* Mini Chart Data */}
                {msg.chartData && (
                  <div className="rounded-lg bg-surface-elevated border border-border/80 p-3 space-y-2">
                    <span className="text-[10px] text-mutedText font-semibold uppercase tracking-wider block">
                      Strategy Success Rates (%)
                    </span>
                    <div className="space-y-1.5 text-[11px] font-mono">
                      {msg.chartData.map((d, i) => (
                        <div key={i} className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className="text-secondaryText">{d.name}</span>
                            <span className="text-success font-bold">{d.value}%</span>
                          </div>
                          <div className="h-1.5 w-full bg-surface rounded-full overflow-hidden">
                            <div className="h-full bg-ai rounded-full" style={{ width: `${d.value}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Mini Table Data */}
                {msg.tableData && (
                  <div className="rounded-lg bg-surface-elevated border border-border/80 p-2 overflow-x-auto">
                    <table className="w-full text-left text-[11px] font-mono">
                      <thead className="border-b border-border text-secondaryText">
                        <tr>
                          {msg.tableData.headers.map((h, i) => (
                            <th key={i} className="py-1 px-2">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {msg.tableData.rows.map((row, rIdx) => (
                          <tr key={rIdx} className="border-b border-border/40">
                            {row.map((cell, cIdx) => (
                              <td key={cIdx} className="py-1 px-2 text-primaryText">{cell}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Action buttons */}
                {msg.actions && (
                  <div className="flex items-center gap-2 pt-1 flex-wrap">
                    {msg.actions.map((act, i) => (
                      <Button
                        key={i}
                        variant="ai"
                        size="sm"
                        onClick={() => router.push(act.action)}
                      >
                        {act.label}
                        <ArrowRight className="h-3 w-3 ml-1" />
                      </Button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex items-center gap-2 text-xs text-ai-light font-mono animate-pulse p-2">
              <Sparkles className="h-4 w-4 animate-spin" />
              <span>Recovery Intelligence Copilot reasoning over financial telemetry...</span>
            </div>
          )}
        </div>

        {/* Input Bar */}
        <div className="flex items-center gap-2 border-t border-border/60 pt-3">
          <input
            type="text"
            placeholder="Ask Copilot about payment failures, recovery probabilities, or ROI..."
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            className="flex-1 rounded-md border border-border bg-surface px-3.5 py-2 text-xs text-primaryText placeholder:text-mutedText focus:outline-none focus:border-ai"
          />
          <Button
            variant="ai"
            size="md"
            onClick={() => handleSend()}
            isLoading={isLoading}
          >
            <Send className="h-3.5 w-3.5" />
            <span>Ask Copilot</span>
          </Button>
        </div>
      </Card>
    </div>
  );
}
