'use client';

import React, { useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { Menu, ChevronRight, PlayCircle, Keyboard, Code, FileText, HelpCircle, Activity } from 'lucide-react';
import { GlobalSearchButton, CommandMenu } from './CommandMenu';
import { AIStatusIndicator } from './AIStatusIndicator';
import { NotificationCenter } from './NotificationCenter';
import { UserMenu } from './UserMenu';
import { Button } from '../ui/Button';
import { DropdownMenu } from '../ui/Dropdown';
import { ShortcutsModal } from '../ui/ShortcutsModal';
import { RawWebhookModal } from '../ui/RawWebhookModal';

export function Topbar({
  onMenuClick,
  onRunDemo,
}: {
  onMenuClick?: () => void;
  onRunDemo?: () => void;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [isShortcutsOpen, setIsShortcutsOpen] = useState(false);
  const [isWebhookOpen, setIsWebhookOpen] = useState(false);

  const getBreadcrumbs = () => {
    const parts = pathname.split('/').filter(Boolean);
    if (parts.length === 0) return [{ label: 'Dashboard', href: '/dashboard' }];

    return parts.map((part, index) => {
      const href = '/' + parts.slice(0, index + 1).join('/');
      let label = part.charAt(0).toUpperCase() + part.slice(1).replace('-', ' ');
      if (part.startsWith('REC-') || part.startsWith('TXN-')) {
        label = part.toUpperCase();
      }
      return { label, href };
    });
  };

  const breadcrumbs = getBreadcrumbs();

  return (
    <>
      <CommandMenu />
      <header className="sticky top-0 z-30 flex h-14 w-full items-center justify-between border-b border-border bg-bg/90 backdrop-blur-md px-4 sm:px-6">
        {/* Left: Mobile menu button & Breadcrumbs */}
        <div className="flex items-center gap-3">
          <button
            onClick={onMenuClick}
            className="rounded-md p-1.5 text-secondaryText hover:bg-surface-elevated hover:text-primaryText lg:hidden"
            aria-label="Open sidebar menu"
          >
            <Menu className="h-5 w-5" />
          </button>

          <nav className="flex items-center gap-1.5 text-xs text-secondaryText font-medium">
            {breadcrumbs.map((crumb, idx) => (
              <React.Fragment key={crumb.href}>
                {idx > 0 && <ChevronRight className="h-3.5 w-3.5 text-mutedText" />}
                <span
                  className={
                    idx === breadcrumbs.length - 1
                      ? 'font-semibold text-primaryText'
                      : 'hover:text-primaryText transition-colors'
                  }
                >
                  {crumb.label}
                </span>
              </React.Fragment>
            ))}
          </nav>
        </div>

        {/* Center: Global Search */}
        <div className="hidden md:flex items-center justify-center flex-1 max-w-xs mx-4">
          <GlobalSearchButton />
        </div>

        {/* Right: AI Status, Live Demo, Notifications, More Options, User */}
        <div className="flex items-center gap-2 sm:gap-3">
          <AIStatusIndicator />

          <Button
            variant="ai"
            size="sm"
            onClick={onRunDemo}
            className="hidden sm:inline-flex"
          >
            <PlayCircle className="h-3.5 w-3.5" />
            <span>Run Live Demo</span>
          </Button>

          <NotificationCenter />

          {/* More Options Overflow Menu */}
          <DropdownMenu
            align="right"
            triggerIcon="horizontal"
            items={[
              {
                id: 'shortcuts',
                label: 'Keyboard Shortcuts',
                icon: <Keyboard className="h-3.5 w-3.5" />,
                onClick: () => setIsShortcutsOpen(true),
              },
              {
                id: 'webhook',
                label: 'View Raw Webhook Payload',
                icon: <Code className="h-3.5 w-3.5" />,
                onClick: () => setIsWebhookOpen(true),
              },
              {
                id: 'telemetry',
                label: 'System Telemetry & Logs',
                icon: <Activity className="h-3.5 w-3.5" />,
                onClick: () => router.push('/agents'),
              },
              {
                id: 'docs',
                label: 'Documentation & API Docs',
                icon: <FileText className="h-3.5 w-3.5" />,
                onClick: () => window.open('https://docs.recoverai.io', '_blank'),
              },
            ]}
          />

          <UserMenu />
        </div>
      </header>

      <ShortcutsModal
        isOpen={isShortcutsOpen}
        onClose={() => setIsShortcutsOpen(false)}
      />

      <RawWebhookModal
        isOpen={isWebhookOpen}
        onClose={() => setIsWebhookOpen(false)}
        transactionId="TXN-82931"
      />
    </>
  );
}
