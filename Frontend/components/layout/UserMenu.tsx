'use client';

import React, { useState } from 'react';
import { User, LogOut, Settings, HelpCircle, ShieldCheck } from 'lucide-react';
import Link from 'next/link';

export function UserMenu() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 rounded-full p-1 hover:bg-surface-elevated transition-colors"
      >
        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-ai/20 border border-ai/40 text-ai-light font-semibold text-xs">
          PB
        </div>
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 top-full mt-2 z-50 w-56 rounded-lg border border-border bg-surface-elevated p-2 shadow-card animate-in fade-in slide-in-from-top-2 duration-150 text-xs">
            <div className="px-3 py-2 border-b border-border/60 mb-1">
              <p className="font-semibold text-primaryText text-xs">Merchant Account</p>
              <p className="text-[11px] text-secondaryText truncate">merchant@payrecover.ai</p>
              <div className="flex items-center gap-1 text-[10px] text-ai-light mt-1">
                <ShieldCheck className="h-3 w-3" />
                <span>Enterprise Autonomous</span>
              </div>
            </div>

            <Link
              href="/settings"
              onClick={() => setIsOpen(false)}
              className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-surface text-secondaryText hover:text-primaryText transition-colors"
            >
              <Settings className="h-3.5 w-3.5" />
              <span>Settings</span>
            </Link>

            <Link
              href="/policies"
              onClick={() => setIsOpen(false)}
              className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-surface text-secondaryText hover:text-primaryText transition-colors"
            >
              <ShieldCheck className="h-3.5 w-3.5" />
              <span>AI Policies</span>
            </Link>

            <a
              href="https://docs.recoverai.io"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-surface text-secondaryText hover:text-primaryText transition-colors"
            >
              <HelpCircle className="h-3.5 w-3.5" />
              <span>Documentation</span>
            </a>

            <div className="border-t border-border/60 my-1 pt-1">
              <Link
                href="/login"
                onClick={() => setIsOpen(false)}
                className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-danger-bg text-danger hover:text-danger-light transition-colors"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span>Sign Out</span>
              </Link>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
