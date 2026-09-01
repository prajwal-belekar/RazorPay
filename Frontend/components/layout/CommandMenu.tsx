'use client';

import React, { useState, useEffect } from 'react';
import { Search, Command, ArrowRight } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { mockTransactions } from '@/lib/mock/transactions';
import { mockRecoveryCases } from '@/lib/mock/recovery';
import { mockBlockchainProofs } from '@/lib/mock/blockchain';
import { formatCurrency } from '@/lib/formatters';

export function CommandMenu() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const router = useRouter();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const navigateTo = (path: string) => {
    setIsOpen(false);
    setQuery('');
    router.push(path);
  };

  if (!isOpen) return null;

  const filteredTxns = mockTransactions.filter(
    (t) =>
      t.id.toLowerCase().includes(query.toLowerCase()) ||
      t.customerName.toLowerCase().includes(query.toLowerCase()) ||
      t.amount.toString().includes(query)
  );

  const filteredRecoveries = mockRecoveryCases.filter(
    (r) =>
      r.id.toLowerCase().includes(query.toLowerCase()) ||
      r.transactionId.toLowerCase().includes(query.toLowerCase()) ||
      r.customer.name.toLowerCase().includes(query.toLowerCase())
  );

  const filteredProofs = mockBlockchainProofs.filter(
    (p) =>
      p.proofHash.toLowerCase().includes(query.toLowerCase()) ||
      p.transactionId.toLowerCase().includes(query.toLowerCase())
  );

  const navigationCommands = [
    { label: 'Go to Dashboard', path: '/dashboard' },
    { label: 'Go to Recovery Opportunities', path: '/recovery' },
    { label: 'Go to Transaction Explorer', path: '/transactions' },
    { label: 'Go to Digital Twin Simulator', path: '/simulator' },
    { label: 'Go to AI Agents Center', path: '/agents' },
    { label: 'Go to Revenue Radar', path: '/revenue-radar' },
    { label: 'Go to Analytics & DNA', path: '/analytics' },
    { label: 'Go to Blockchain Trust Vault', path: '/blockchain' },
    { label: 'Go to Policies & Safety Firewall', path: '/policies' },
    { label: 'Open AI Copilot Assistant', path: '/copilot' },
    { label: 'Open Settings', path: '/settings' },
  ].filter((cmd) => cmd.label.toLowerCase().includes(query.toLowerCase()));

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="fixed inset-0" onClick={() => setIsOpen(false)} />
      <div className="relative z-10 w-full max-w-xl overflow-hidden rounded-xl bg-surface-elevated border border-border shadow-card">
        {/* Search Input Bar */}
        <div className="flex items-center border-b border-border/80 px-4 py-3">
          <Search className="h-4 w-4 text-secondaryText mr-2" />
          <input
            type="text"
            placeholder="Search transactions, customers, recovery cases, proofs..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
            className="w-full bg-transparent text-sm text-primaryText placeholder:text-mutedText focus:outline-none"
          />
          <kbd className="hidden sm:inline-flex items-center gap-1 rounded bg-surface px-2 py-0.5 text-[10px] font-mono text-secondaryText border border-border">
            ESC
          </kbd>
        </div>

        {/* Results list */}
        <div className="max-h-96 overflow-y-auto p-2 divide-y divide-border/40 text-xs">
          {/* Quick Navigation Commands */}
          {navigationCommands.length > 0 && (
            <div className="py-2">
              <div className="px-3 text-[10px] font-semibold text-mutedText uppercase tracking-wider mb-1">
                Navigation Commands
              </div>
              {navigationCommands.slice(0, 5).map((cmd, idx) => (
                <button
                  key={idx}
                  onClick={() => navigateTo(cmd.path)}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-md hover:bg-surface text-secondaryText hover:text-primaryText transition-colors text-left"
                >
                  <span>{cmd.label}</span>
                  <ArrowRight className="h-3 w-3" />
                </button>
              ))}
            </div>
          )}

          {/* Recoveries */}
          {filteredRecoveries.length > 0 && (
            <div className="py-2">
              <div className="px-3 text-[10px] font-semibold text-mutedText uppercase tracking-wider mb-1">
                Recovery Cases
              </div>
              {filteredRecoveries.map((r) => (
                <button
                  key={r.id}
                  onClick={() => navigateTo(`/recovery/${r.id}`)}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-md hover:bg-surface text-secondaryText hover:text-primaryText transition-colors text-left"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-primaryText">{r.transactionId}</span>
                    <span className="text-secondaryText">• {r.customer.name}</span>
                  </div>
                  <span className="font-mono text-success font-medium">{formatCurrency(r.amount)}</span>
                </button>
              ))}
            </div>
          )}

          {/* Transactions */}
          {filteredTxns.length > 0 && (
            <div className="py-2">
              <div className="px-3 text-[10px] font-semibold text-mutedText uppercase tracking-wider mb-1">
                Transactions
              </div>
              {filteredTxns.map((t) => (
                <button
                  key={t.id}
                  onClick={() => navigateTo('/transactions')}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-md hover:bg-surface text-secondaryText hover:text-primaryText transition-colors text-left"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-primaryText">{t.id}</span>
                    <span className="text-secondaryText">• {t.paymentMethod}</span>
                  </div>
                  <span className="font-mono">{formatCurrency(t.amount)}</span>
                </button>
              ))}
            </div>
          )}

          {/* Blockchain proofs */}
          {filteredProofs.length > 0 && (
            <div className="py-2">
              <div className="px-3 text-[10px] font-semibold text-mutedText uppercase tracking-wider mb-1">
                Blockchain Proofs
              </div>
              {filteredProofs.map((p) => (
                <button
                  key={p.proofId}
                  onClick={() => navigateTo('/blockchain')}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-md hover:bg-surface text-secondaryText hover:text-primaryText transition-colors text-left font-mono text-[11px]"
                >
                  <span className="text-ai-light">{p.proofHash}</span>
                  <span className="text-secondaryText">{p.transactionId}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function GlobalSearchButton() {
  return (
    <button
      onClick={() => {
        window.dispatchEvent(
          new KeyboardEvent('keydown', { key: 'k', metaKey: true, ctrlKey: true })
        );
      }}
      className="flex items-center gap-2 rounded-md border border-border/80 bg-surface/80 px-3 py-1.5 text-xs text-secondaryText hover:border-border hover:bg-surface-elevated hover:text-primaryText transition-all w-48 sm:w-64"
    >
      <Search className="h-3.5 w-3.5 text-mutedText" />
      <span className="flex-1 text-left truncate text-[11px]">Search cases, TXNs, proofs...</span>
      <kbd className="hidden sm:inline-flex items-center gap-0.5 rounded bg-surface-elevated px-1.5 py-0.5 text-[10px] font-mono text-mutedText border border-border/80">
        <Command className="h-2.5 w-2.5" />K
      </kbd>
    </button>
  );
}
