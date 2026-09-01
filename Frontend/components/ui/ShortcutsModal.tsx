'use client';

import React from 'react';
import { Modal } from './Modal';
import { Button } from './Button';
import { Command, Keyboard } from 'lucide-react';

export function ShortcutsModal({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const shortcuts = [
    { key: 'Ctrl + K', description: 'Open Global Command Menu & Search' },
    { key: 'Esc', description: 'Close active modal, drawer, or dropdown' },
    { key: 'Tab', description: 'Focus next interactive element' },
    { key: 'Ctrl + D', description: 'Run Guided Autonomous Recovery Demo' },
    { key: 'Ctrl + /', description: 'Toggle AI Copilot Assistant' },
  ];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2">
          <Keyboard className="h-4 w-4 text-ai" />
          <span>RecoverAI Keyboard Shortcuts</span>
        </div>
      }
      subtitle="Quick navigation commands"
      maxWidth="md"
    >
      <div className="space-y-4">
        <div className="space-y-2 rounded-lg border border-border bg-surface p-3 text-xs">
          {shortcuts.map((sc, idx) => (
            <div key={idx} className="flex items-center justify-between py-1.5 border-b border-border/40 last:border-0">
              <span className="text-secondaryText">{sc.description}</span>
              <kbd className="rounded bg-surface-elevated px-2 py-0.5 font-mono text-[11px] text-primaryText border border-border">
                {sc.key}
              </kbd>
            </div>
          ))}
        </div>

        <div className="flex justify-end">
          <Button variant="outline" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  );
}
