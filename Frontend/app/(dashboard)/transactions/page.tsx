'use client';

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { DataTable, Column } from '@/components/ui/DataTable';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { DropdownMenu } from '@/components/ui/Dropdown';
import { RawWebhookModal } from '@/components/ui/RawWebhookModal';
import { formatCurrency, formatDate } from '@/lib/formatters';
import { mockTransactions } from '@/lib/mock/transactions';
import { Transaction } from '@/types';
import { Search, RotateCcw, Cpu, Code, Copy, Download, ExternalLink } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function TransactionsPage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [methodFilter, setMethodFilter] = useState('ALL');
  const [selectedTxn, setSelectedTxn] = useState<Transaction | null>(null);
  const [webhookTxnId, setWebhookTxnId] = useState<string | null>(null);

  const filteredTxns = mockTransactions.filter((t) => {
    const matchesStatus = statusFilter === 'ALL' || t.status === statusFilter;
    const matchesMethod = methodFilter === 'ALL' || t.paymentMethod === methodFilter;
    const matchesQuery =
      t.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.customerName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (t.failureReason && t.failureReason.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesStatus && matchesMethod && matchesQuery;
  });

  const columns: Column<Transaction>[] = [
    {
      header: 'Transaction ID',
      cell: (row) => (
        <div>
          <span className="font-mono font-bold text-primaryText block">{row.id}</span>
          <span className="text-[10px] text-mutedText">{row.gateway}</span>
        </div>
      ),
    },
    {
      header: 'Customer',
      cell: (row) => (
        <div>
          <span className="font-medium text-primaryText block">{row.customerName}</span>
          <span className="text-[10px] text-mutedText">{row.customerId}</span>
        </div>
      ),
    },
    {
      header: 'Amount',
      cell: (row) => (
        <span className="font-mono font-bold text-primaryText">{formatCurrency(row.amount)}</span>
      ),
    },
    {
      header: 'Payment Method',
      cell: (row) => <Badge variant="outline">{row.paymentMethod}</Badge>,
    },
    {
      header: 'Status',
      cell: (row) => {
        const variant =
          row.status === 'Recovered'
            ? 'success'
            : row.status === 'Success'
            ? 'success'
            : row.status === 'Pending'
            ? 'warning'
            : 'danger';
        return <Badge variant={variant}>{row.status}</Badge>;
      },
    },
    {
      header: 'Failure Reason',
      cell: (row) => (
        <span className="text-secondaryText text-xs">
          {row.failureReason || '—'}
        </span>
      ),
    },
    {
      header: 'Date',
      cell: (row) => (
        <span className="font-mono text-xs text-mutedText">
          {formatDate(row.createdAt, { includeTime: true })}
        </span>
      ),
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
              setSelectedTxn(row);
            }}
          >
            View
          </Button>

          <DropdownMenu
            align="right"
            items={[
              {
                id: 'detail',
                label: 'View Transaction Audit',
                icon: <ExternalLink className="h-3.5 w-3.5" />,
                onClick: () => setSelectedTxn(row),
              },
              {
                id: 'webhook',
                label: 'View Raw Webhook Payload',
                icon: <Code className="h-3.5 w-3.5" />,
                onClick: () => setWebhookTxnId(row.id),
              },
              {
                id: 'copy',
                label: 'Copy Transaction ID',
                icon: <Copy className="h-3.5 w-3.5" />,
                onClick: () => navigator.clipboard.writeText(row.id),
              },
              {
                id: 'simulate',
                label: 'Simulate Strategy',
                icon: <Cpu className="h-3.5 w-3.5" />,
                onClick: () => router.push(`/simulator?tx=${row.id}`),
              },
              ...(row.recoveryId
                ? [
                    {
                      id: 'case',
                      label: 'Inspect Recovery Case',
                      icon: <RotateCcw className="h-3.5 w-3.5" />,
                      onClick: () => router.push(`/recovery/${row.recoveryId}`),
                    },
                  ]
                : []),
            ]}
          />
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/60 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-primaryText">
            Transaction Explorer
          </h1>
          <p className="text-xs sm:text-sm text-secondaryText mt-1">
            Real-time audit log of all payment attempts, failures, and recovery states.
          </p>
        </div>

        <span className="font-mono text-xs text-mutedText">
          {filteredTxns.length} Transactions Found
        </span>
      </div>

      {/* Filter Bar */}
      <Card className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-mutedText" />
          <input
            type="text"
            placeholder="Search transaction ID, customer..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-md border border-border bg-surface px-8 py-1.5 text-xs text-primaryText placeholder:text-mutedText focus:outline-none focus:border-ai"
          />
        </div>

        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-md border border-border bg-surface px-3 py-1.5 text-xs text-secondaryText focus:outline-none focus:border-ai"
          >
            <option value="ALL">All Statuses</option>
            <option value="Recovered">Recovered</option>
            <option value="Failed">Failed</option>
            <option value="Pending">Pending</option>
            <option value="Success">Success</option>
          </select>

          <select
            value={methodFilter}
            onChange={(e) => setMethodFilter(e.target.value)}
            className="rounded-md border border-border bg-surface px-3 py-1.5 text-xs text-secondaryText focus:outline-none focus:border-ai"
          >
            <option value="ALL">All Methods</option>
            <option value="UPI">UPI</option>
            <option value="Cards">Cards</option>
            <option value="Net Banking">Net Banking</option>
            <option value="Wallet">Wallet</option>
          </select>
        </div>
      </Card>

      {/* DataTable */}
      <Card className="p-0">
        <DataTable
          columns={columns}
          data={filteredTxns}
          onRowClick={(row) => setSelectedTxn(row)}
        />
      </Card>

      {/* Detail Modal */}
      <Modal
        isOpen={Boolean(selectedTxn)}
        onClose={() => setSelectedTxn(null)}
        title={selectedTxn ? `Transaction ${selectedTxn.id}` : ''}
        subtitle="Gateway & Recovery Audit Details"
        maxWidth="md"
      >
        {selectedTxn && (
          <div className="space-y-4 text-xs font-mono">
            <div className="rounded-lg bg-surface border border-border p-4 space-y-2">
              <div className="flex justify-between">
                <span className="text-secondaryText">Amount:</span>
                <span className="font-bold text-primaryText text-sm">
                  {formatCurrency(selectedTxn.amount)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondaryText">Customer:</span>
                <span className="text-primaryText">{selectedTxn.customerName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondaryText">Status:</span>
                <Badge
                  variant={
                    selectedTxn.status === 'Recovered'
                      ? 'success'
                      : selectedTxn.status === 'Success'
                      ? 'success'
                      : 'danger'
                  }
                >
                  {selectedTxn.status}
                </Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-secondaryText">Failure Reason:</span>
                <span className="text-danger">{selectedTxn.failureReason || 'None'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondaryText">Failure Code:</span>
                <span className="text-secondaryText">{selectedTxn.failureCode || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondaryText">Created At:</span>
                <span className="text-secondaryText">{formatDate(selectedTxn.createdAt, { includeTime: true })}</span>
              </div>
            </div>

            {selectedTxn.recoveryId && (
              <Button
                variant="ai"
                size="sm"
                className="w-full"
                onClick={() => {
                  setSelectedTxn(null);
                  router.push(`/recovery/${selectedTxn.recoveryId}`);
                }}
              >
                Inspect Recovery Case →
              </Button>
            )}
          </div>
        )}
      </Modal>

      <RawWebhookModal
        isOpen={Boolean(webhookTxnId)}
        onClose={() => setWebhookTxnId(null)}
        transactionId={webhookTxnId || 'TXN-82931'}
      />
    </div>
  );
}
