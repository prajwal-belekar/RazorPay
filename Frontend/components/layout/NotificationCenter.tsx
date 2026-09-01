'use client';

import React, { useState } from 'react';
import { Bell, Check, ExternalLink } from 'lucide-react';
import { mockNotifications } from '@/lib/mock/notifications';
import { NotificationItem } from '@/types';
import Link from 'next/link';

export function NotificationCenter() {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>(mockNotifications);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const markAsRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative rounded-md p-2 text-secondaryText hover:bg-surface-elevated hover:text-primaryText transition-colors"
        aria-label="Notifications"
      >
        <Bell className="h-4 w-4" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-ai opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-ai"></span>
          </span>
        )}
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 top-full mt-2 z-50 w-80 sm:w-96 rounded-lg border border-border bg-surface-elevated p-4 shadow-card animate-in fade-in slide-in-from-top-2 duration-150">
            <div className="flex items-center justify-between border-b border-border/60 pb-3 mb-3">
              <div className="flex items-center gap-2">
                <h3 className="text-xs font-semibold text-primaryText">Notifications</h3>
                {unreadCount > 0 && (
                  <span className="rounded-full bg-ai/20 px-2 py-0.5 text-[10px] text-ai-light font-medium border border-ai-border/40">
                    {unreadCount} new
                  </span>
                )}
              </div>
              {unreadCount > 0 && (
                <button
                  onClick={markAllAsRead}
                  className="flex items-center gap-1 text-[11px] text-secondaryText hover:text-primaryText transition-colors"
                >
                  <Check className="h-3 w-3" />
                  Mark all read
                </button>
              )}
            </div>

            <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
              {notifications.map((item) => (
                <div
                  key={item.id}
                  onClick={() => markAsRead(item.id)}
                  className={`p-3 rounded-md border text-xs transition-colors cursor-pointer ${
                    item.read
                      ? 'bg-surface/40 border-border/40 text-secondaryText'
                      : 'bg-surface border-border text-primaryText shadow-subtle'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <span className="font-semibold text-[12px]">{item.title}</span>
                    <span className="text-[10px] text-mutedText whitespace-nowrap">{item.timestamp}</span>
                  </div>
                  <p className="text-[11px] text-secondaryText mb-2 leading-relaxed">{item.message}</p>
                  {item.actionUrl && (
                    <Link
                      href={item.actionUrl}
                      onClick={() => setIsOpen(false)}
                      className="inline-flex items-center gap-1 text-[11px] text-ai-light hover:underline font-medium"
                    >
                      {item.actionText || 'View detail'}
                      <ExternalLink className="h-3 w-3" />
                    </Link>
                  )}
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
