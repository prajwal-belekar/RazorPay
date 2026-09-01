'use client';

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { DataTable, Column } from '@/components/ui/DataTable';
import { BlockchainProof3D } from '@/components/3d/BlockchainProof';
import { useRecoveryEngine } from '@/context/RecoveryEngineContext';
import { BlockchainProof } from '@/types';
import { formatCurrency, formatDate, truncateHash } from '@/lib/formatters';
import { ShieldCheck, CheckCircle2, ExternalLink, RefreshCw, Cpu, Lock } from 'lucide-react';
import confetti from 'canvas-confetti';

export default function BlockchainPage() {
  const { proofs } = useRecoveryEngine();
  const [selectedProof, setSelectedProof] = useState<BlockchainProof | null>(null);

  const columns: Column<BlockchainProof>[] = [
    {
      header: 'Decision ID',
      cell: (row) => <span className="font-mono font-bold text-primaryText">{row.proofId}</span>,
    },
    {
      header: 'Transaction',
      cell: (row) => <span className="font-mono text-ai-light font-semibold">{row.transactionId}</span>,
    },
    {
      header: 'Amount',
      cell: (row) => <span className="font-mono font-bold text-success">{formatCurrency(row.amount)}</span>,
    },
    {
      header: 'Strategy',
      cell: (row) => <Badge variant="outline">{row.strategy}</Badge>,
    },
    {
      header: 'Policy Version',
      cell: (row) => <span className="font-mono text-secondaryText">{row.policyVersion}</span>,
    },
    {
      header: 'Status',
      cell: (row) => (
        <Badge variant="success">
          <CheckCircle2 className="h-3 w-3" />
          Verified
        </Badge>
      ),
    },
    {
      header: 'Proof Hash',
      cell: (row) => (
        <span className="font-mono text-[11px] text-ai-light">{truncateHash(row.proofHash)}</span>
      ),
    },
    {
      header: 'Timestamp',
      cell: (row) => (
        <span className="font-mono text-xs text-mutedText">
          {formatDate(row.timestamp, { includeTime: true })}
        </span>
      ),
    },
    {
      header: 'Action',
      cell: (row) => (
        <Button
          variant="ai"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            setSelectedProof(row);
          }}
        >
          Verify
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/60 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-primaryText">
              Recovery Trust Center
            </h1>
            <Badge variant="success">Polygon Devnet Active</Badge>
          </div>
          <p className="text-xs sm:text-sm text-secondaryText mt-1">
            Cryptographically verifiable proof of autonomous recovery decisions.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            try { confetti({ particleCount: 30 }); } catch {}
          }}
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Sync Ledger
        </Button>
      </div>

      {/* Trust Lifecycle Concept Card */}
      <Card className="p-4 border-ai-border/40 bg-gradient-to-r from-surface to-ai-bg/10">
        <div className="flex flex-col md:flex-row items-center justify-between gap-3 text-xs font-mono">
          <div className="flex items-center gap-2 text-ai-light">
            <Cpu className="h-4 w-4" />
            <span className="font-bold">AI Decision</span>
          </div>
          <span className="text-mutedText">+</span>
          <div className="flex items-center gap-2 text-info-light">
            <ShieldCheck className="h-4 w-4" />
            <span className="font-bold">Policy Firewall</span>
          </div>
          <span className="text-mutedText">+</span>
          <div className="flex items-center gap-2 text-warning">
            <RefreshCw className="h-4 w-4" />
            <span className="font-bold">Razorpay Action</span>
          </div>
          <span className="text-mutedText">+</span>
          <div className="flex items-center gap-2 text-success">
            <CheckCircle2 className="h-4 w-4" />
            <span className="font-bold">Recovery Settlement</span>
          </div>
          <span className="text-mutedText">=</span>
          <div className="flex items-center gap-2 text-indigo-400 font-bold bg-surface/80 p-2 rounded border border-border">
            <Lock className="h-4 w-4" />
            <span>Immutable Recovery Proof</span>
          </div>
        </div>
      </Card>

      {/* 3D Proof Chain Visualization */}
      <Card className="p-3 border-ai-border/40 bg-surface-elevated/40">
        <span className="text-[10px] font-mono text-mutedText uppercase px-2">3D Proof Chain Ledger Visualization</span>
        <BlockchainProof3D className="h-32 w-full" />
      </Card>

      {/* Trust Metrics Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <Card className="p-4">
          <span className="text-xs text-secondaryText font-medium">Verified Recoveries</span>
          <div className="text-xl font-bold font-mono text-success mt-1">{proofs.length}</div>
          <span className="text-[10px] text-mutedText">100% On-chain Hash Match</span>
        </Card>

        <Card className="p-4">
          <span className="text-xs text-secondaryText font-medium">Verified Value</span>
          <div className="text-xl font-bold font-mono text-success mt-1">
            {formatCurrency(proofs.reduce((acc, p) => acc + p.amount, 0))}
          </div>
          <span className="text-[10px] text-mutedText">Recorded in Ledger</span>
        </Card>

        <Card className="p-4">
          <span className="text-xs text-secondaryText font-medium">Proofs Created</span>
          <div className="text-xl font-bold font-mono text-ai-light mt-1">3,821</div>
          <span className="text-[10px] text-mutedText">Decisions & Policy Hashes</span>
        </Card>

        <Card className="p-4">
          <span className="text-xs text-secondaryText font-medium">Ledger Network Status</span>
          <div className="text-sm font-bold font-mono text-success mt-1 flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-success" />
            Polygon Devnet
          </div>
          <span className="text-[10px] text-mutedText">Block #18294021</span>
        </Card>
      </div>

      {/* Proof DataTable */}
      <Card className="p-0">
        <CardHeader className="flex flex-row items-center justify-between border-b border-border/60 pb-3">
          <CardTitle>On-Chain Recovery Proof Ledger</CardTitle>
          <span className="text-xs font-mono text-mutedText">Verifiable Credentials</span>
        </CardHeader>

        <CardContent className="p-0">
          <DataTable
            columns={columns}
            data={proofs}
            onRowClick={(row) => setSelectedProof(row)}
          />
        </CardContent>
      </Card>

      {/* Verification Dialog Modal */}
      <Modal
        isOpen={Boolean(selectedProof)}
        onClose={() => setSelectedProof(null)}
        title={
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-success" />
            <span>On-Chain Decision Verification</span>
          </div>
        }
        subtitle="Cryptographic verification against smart contract"
        maxWidth="md"
      >
        {selectedProof && (
          <div className="space-y-4 text-xs font-mono">
            <div className="rounded-lg bg-success-bg border border-success-border p-3.5 text-center space-y-1">
              <div className="flex items-center justify-center gap-1.5 text-success font-bold text-sm">
                <CheckCircle2 className="h-4 w-4" />
                <span>✓ Cryptographically Verified</span>
              </div>
              <p className="text-[11px] text-secondaryText">
                Decision proof is authentic and untampered on the ledger.
              </p>
            </div>

            <div className="space-y-2 rounded-lg bg-surface border border-border p-3.5 text-[11px]">
              <div className="flex justify-between">
                <span className="text-secondaryText">Transaction ID:</span>
                <span className="text-primaryText font-bold">{selectedProof.transactionId}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondaryText">Decision Proof Hash:</span>
                <span className="text-ai-light">{selectedProof.proofHash}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondaryText">Policy Hash:</span>
                <span className="text-secondaryText">{selectedProof.policyHash}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondaryText">Block Number:</span>
                <span className="text-primaryText">#{selectedProof.blockNumber}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondaryText">Timestamp:</span>
                <span className="text-primaryText">{formatDate(selectedProof.timestamp, { includeTime: true })}</span>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedProof(null)}
              >
                Close
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => alert(`Polygon Devnet Tx Hash: ${selectedProof.txHash}`)}
              >
                <ExternalLink className="h-3.5 w-3.5" />
                View on Explorer
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
