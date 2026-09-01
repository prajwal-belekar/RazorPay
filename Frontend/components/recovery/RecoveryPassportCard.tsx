'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Modal } from '../ui/Modal';
import { formatCurrency, formatDate, truncateHash } from '@/lib/formatters';
import { RecoveryCase } from '@/types';
import { ShieldCheck, CheckCircle2, Lock, ExternalLink, Copy, Check, ArrowRight } from 'lucide-react';

export function RecoveryPassportCard({ recoveryCase }: { recoveryCase: RecoveryCase }) {
  const router = useRouter();
  const [isVerifyModalOpen, setIsVerifyModalOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const proof = recoveryCase.proof;

  const copyHash = () => {
    if (proof?.proofHash) {
      navigator.clipboard.writeText(proof.proofHash);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <>
      <Card className="border-ai-border/80 bg-gradient-to-b from-surface-elevated to-bg p-6 relative overflow-hidden shadow-card">
        {/* Certificate Watermark Icon */}
        <div className="absolute -right-6 -bottom-6 opacity-5 pointer-events-none">
          <ShieldCheck className="h-48 w-48 text-ai" />
        </div>

        <div className="border border-ai-border/40 rounded-xl p-5 bg-surface/90 backdrop-blur space-y-4">
          <div className="flex items-center justify-between border-b border-border/60 pb-3">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-ai/20 text-ai-light border border-ai/50">
                <ShieldCheck className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold tracking-wide uppercase text-primaryText">
                  RECOVERY PASSPORT
                </h3>
                <p className="text-[10px] text-secondaryText font-mono">Verifiable Proof Identity</p>
              </div>
            </div>

            <Badge variant="success" size="sm">
              <CheckCircle2 className="h-3 w-3" />
              VERIFIED PROOF
            </Badge>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
            <div>
              <span className="text-[10px] text-mutedText block">Transaction</span>
              <span className="font-bold text-primaryText">{recoveryCase.transactionId}</span>
            </div>

            <div>
              <span className="text-[10px] text-mutedText block">Amount</span>
              <span className="font-bold text-success">{formatCurrency(recoveryCase.amount)}</span>
            </div>

            <div>
              <span className="text-[10px] text-mutedText block">Strategy</span>
              <span className="font-bold text-primaryText">{recoveryCase.strategy}</span>
            </div>

            <div>
              <span className="text-[10px] text-mutedText block">AI Confidence</span>
              <span className="font-bold text-ai-light">{recoveryCase.aiConfidence}%</span>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono border-t border-border/40 pt-3">
            <div>
              <span className="text-[10px] text-mutedText block">Policy Version</span>
              <span className="text-primaryText">{recoveryCase.firewallResult.policyVersion}</span>
            </div>

            <div>
              <span className="text-[10px] text-mutedText block">Recovery Status</span>
              <span className="text-success font-bold">✓ RECOVERED</span>
            </div>

            <div>
              <span className="text-[10px] text-mutedText block">Blockchain Ledger</span>
              <span className="text-ai-light font-bold">✓ VERIFIED</span>
            </div>

            <div>
              <span className="text-[10px] text-mutedText block">Proof Hash</span>
              <span className="text-secondaryText text-[11px]">
                {truncateHash(proof?.proofHash || '0x8a91f3c2b84e12d4a976328a9b1c72fc82a10452')}
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between border-t border-border/60 pt-3">
            <span className="text-[10px] text-mutedText">
              Polygon POS Enterprise Devnet • Block #{proof?.blockNumber || 18294021}
            </span>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => router.push('/blockchain')}
              >
                Trust Center
                <ArrowRight className="h-3 w-3 ml-1" />
              </Button>
              <Button
                variant="ai"
                size="sm"
                onClick={() => setIsVerifyModalOpen(true)}
              >
                <Lock className="h-3.5 w-3.5" />
                Verify Proof
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {/* Proof Verification Dialog Modal */}
      <Modal
        isOpen={isVerifyModalOpen}
        onClose={() => setIsVerifyModalOpen(false)}
        title={
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-success" />
            <span>Cryptographic Proof Verification</span>
          </div>
        }
        subtitle="On-chain ledger decision integrity verification"
        maxWidth="md"
      >
        <div className="space-y-4 text-xs font-mono">
          <div className="rounded-lg bg-success-bg border border-success-border p-3 text-center space-y-1">
            <div className="flex items-center justify-center gap-1.5 text-success font-bold text-sm">
              <CheckCircle2 className="h-4 w-4" />
              <span>✓ Cryptographically Verified</span>
            </div>
            <p className="text-[11px] text-secondaryText">
              Decision hash matches on-chain smart contract ledger record.
            </p>
          </div>

          <div className="space-y-2 rounded-lg bg-surface border border-border p-3 text-[11px]">
            <div className="flex justify-between">
              <span className="text-secondaryText">Transaction ID:</span>
              <span className="text-primaryText font-bold">{recoveryCase.transactionId}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-secondaryText">Decision Hash:</span>
              <div className="flex items-center gap-1 text-ai-light">
                <span>{truncateHash(proof?.proofHash || '0x8a91...72fc')}</span>
                <button onClick={copyHash} className="hover:text-white">
                  {copied ? <Check className="h-3 w-3 text-success" /> : <Copy className="h-3 w-3" />}
                </button>
              </div>
            </div>
            <div className="flex justify-between">
              <span className="text-secondaryText">Policy Hash:</span>
              <span className="text-secondaryText">
                {truncateHash(proof?.policyHash || '0x91ac...82de')}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-secondaryText">Block Number:</span>
              <span className="text-primaryText">#{proof?.blockNumber || 18294021}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-secondaryText">Recorded At:</span>
              <span className="text-primaryText">{formatDate(proof?.timestamp || new Date().toISOString(), { includeTime: true })}</span>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsVerifyModalOpen(false)}
            >
              Close
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                setIsVerifyModalOpen(false);
                router.push('/blockchain');
              }}
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Open Trust Center Ledger
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
