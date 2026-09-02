'use client';

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { DataTable, Column } from '../ui/DataTable';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { DropdownMenu } from '../ui/Dropdown';
import { RawWebhookModal } from '../ui/RawWebhookModal';
import { RecoveryScore } from '../recovery/RecoveryScore';
import { formatCurrency, formatPercent } from '@/lib/formatters';
import { useRecoveryEngine } from '@/context/RecoveryEngineContext';
import { RecoveryCase } from '@/types';
import { useRouter } from 'next/navigation';
import { Search, RotateCcw, Cpu, ChevronRight, Code, Copy, Download, ShieldAlert } from 'lucide-react';

export function RecoveryOpportunitiesTable() {
  const router = useRouter();
  const { cases, isLoading, backendError } = useRecoveryEngine();
  const [filterMethod, setFilterMethod] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [webhookTxnId, setWebhookTxnId] = useState<string | null>(null);

  const filteredCases = cases.filter((c) => {
    const matchesMethod = filterMethod === 'ALL' || c.paymentMethod === filterMethod;
    const matchesSearch =
      c.transactionId.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.customer.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.failureReason.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesMethod && matchesSearch;
  });

  const columns: Column<RecoveryCase>[] = [
    {
      header: 'Transaction',
      cell: (row) => (
        <div>
          <span className="font-semibold font-mono text-primaryText block">{row.transactionId}</span>
          <span className="text-[10px] text-mutedText">{row.paymentMethod}</span>
        </div>
      ),
    },
    {
      header: 'Customer',
      cell: (row) => (
        <div>
          <span className="font-medium text-primaryText block">{row.customer.name}</span>
          <span className="text-[10px] text-mutedText">{row.customer.tier}</span>
        </div>
      ),
    },
    {
      header: 'Amount',
      cell: (row) => (
        <span className="font-mono font-semibold text-primaryText">{formatCurrency(row.amount)}</span>
      ),
    },
    {
      header: 'Recovery Score',
      cell: (row) => (
        <RecoveryScore score={row.recoveryProbability} compact />
      ),
    },
    {
      header: 'Expected Value',
      cell: (row) => (
        <span className="font-mono text-success font-semibold">{formatCurrency(row.expectedRecovery)}</span>
      ),
    },
    {
      header: 'Strategy',
      cell: (row) => (
        <Badge variant="ai" size="sm">
          {row.strategy}
        </Badge>
      ),
    },
    {
      header: 'Confidence',
      cell: (row) => <span className="font-mono text-xs text-ai-light">{row.aiConfidence}%</span>,
    },
    {
      header: 'Status',
      cell: (row) => {
        const variant =
          row.status === 'Recovered'
            ? 'success'
            : row.status === 'At Risk'
            ? 'warning'
            : row.status === 'Approved'
            ? 'info'
            : 'danger';
        return <Badge variant={variant}>{row.status}</Badge>;
      },
    },
    {
      header: 'Actions',
      cell: (row) => (
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              router.push(`/recovery/${row.id}`);
            }}
          >
            Analyze
          </Button>

          {/* More Row Options Dropdown */}
          <DropdownMenu
            align="right"
            items={[
              {
                id: 'analyze',
                label: 'Analyze Recovery Case',
                icon: <RotateCcw className="h-3.5 w-3.5" />,
                onClick: () => router.push(`/recovery/${row.id}`),
              },
              {
                id: 'simulate',
                label: 'Simulate Digital Twin',
                icon: <Cpu className="h-3.5 w-3.5" />,
                onClick: () => router.push(`/simulator?tx=${row.transactionId}`),
              },
              {
                id: 'webhook',
                label: 'View Raw Razorpay Webhook',
                icon: <Code className="h-3.5 w-3.5" />,
                onClick: () => setWebhookTxnId(row.transactionId),
              },
              {
                id: 'copy',
                label: 'Copy Transaction ID',
                icon: <Copy className="h-3.5 w-3.5" />,
                onClick: () => navigator.clipboard.writeText(row.transactionId),
              },
              {
                id: 'export',
                label: 'Export Case JSON',
                icon: <Download className="h-3.5 w-3.5" />,
                onClick: () => {
                  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(row, null, 2));
                  const dlAnchorElem = document.createElement('a');
                  dlAnchorElem.setAttribute("href", dataStr);
                  dlAnchorElem.setAttribute("download", `${row.transactionId}_case.json`);
                  dlAnchorElem.click();
                },
              },
              {
                id: 'override',
                label: 'Override Policy & Force Execution',
                icon: <ShieldAlert className="h-3.5 w-3.5" />,
                danger: true,
                onClick: () => alert(`Force execution override requested for ${row.transactionId}`),
              },
            ]}
          />
        </div>
      ),
    },
  ];

  return (
    <>
      <Card className="p-0">
        <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border/60 pb-4">
          <div>
            <CardTitle className="text-base">Recovery Opportunities</CardTitle>
            <p className="text-xs text-secondaryText mt-0.5">
              Failed payments prioritized by AI expected recovery value & Recovery Score
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* Search Bar */}
            <div className="relative">
              <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-mutedText" />
              <input
                type="text"
                placeholder="Filter opportunities..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="rounded-md border border-border bg-surface px-8 py-1 text-xs text-primaryText placeholder:text-mutedText focus:outline-none focus:border-ai w-36 sm:w-48"
              />
            </div>

            {/* Payment Method Selector */}
            <select
              value={filterMethod}
              onChange={(e) => setFilterMethod(e.target.value)}
              className="rounded-md border border-border bg-surface px-2 py-1 text-xs text-secondaryText focus:outline-none focus:border-ai"
            >
              <option value="ALL">All Methods</option>
              <option value="UPI">UPI</option>
              <option value="Cards">Cards</option>
              <option value="Net Banking">Net Banking</option>
              <option value="Wallet">Wallet</option>
            </select>

            <Button
              variant="secondary"
              size="sm"
              onClick={() => router.push('/recovery')}
            >
              View All
              <ChevronRight className="h-3.5 w-3.5 ml-1" />
            </Button>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-xs text-secondaryText animate-pulse">
              Loading payments...
            </div>
          ) : backendError ? (
            <div className="p-8 text-center text-xs text-secondaryText space-y-1">
              <p>Unable to connect to RecoverAI backend.</p>
              <p className="text-[10px] text-mutedText">Showing dashboard data from local snapshot.</p>
            </div>
          ) : filteredCases.length === 0 ? (
            <div className="p-8 text-center text-xs text-secondaryText">
              No payment recovery cases found.
            </div>
          ) : (
            <DataTable
              columns={columns}
              data={filteredCases}
              onRowClick={(row) => router.push(`/recovery/${row.id}`)}
            />
          )}
        </CardContent>
      </Card>

      <RawWebhookModal
        isOpen={Boolean(webhookTxnId)}
        onClose={() => setWebhookTxnId(null)}
        transactionId={webhookTxnId || undefined}
      />
    </>
  );
}
