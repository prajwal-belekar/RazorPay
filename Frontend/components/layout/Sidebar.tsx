'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { NAV_ITEMS, APP_NAME } from '@/lib/constants';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  RotateCcw,
  Receipt,
  Radar,
  Cpu,
  Bot,
  BarChart3,
  ShieldCheck,
  Sliders,
  Sparkles,
  Settings,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
  PlayCircle
} from 'lucide-react';

const iconMap: Record<string, React.ElementType> = {
  LayoutDashboard,
  RotateCcw,
  Receipt,
  Radar,
  Cpu,
  Bot,
  BarChart3,
  ShieldCheck,
  Sliders,
  Sparkles,
  Settings,
};

const LinkComponent = Link as React.ComponentType<any>;

export function Sidebar({
  isMobileOpen,
  setIsMobileOpen,
  onRunDemo,
}: {
  isMobileOpen?: boolean;
  setIsMobileOpen?: (open: boolean) => void;
  onRunDemo?: () => void;
}) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const pathname = usePathname();

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/80 backdrop-blur-sm lg:hidden"
          onClick={() => setIsMobileOpen?.(false)}
        />
      )}

      <aside
        className={cn(
          "fixed top-0 bottom-0 left-0 z-40 flex flex-col border-r border-border bg-bg-dark transition-all duration-300 ease-in-out",
          isCollapsed ? "w-16" : "w-64",
          isMobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {/* Brand Header */}
        <div className="flex h-14 items-center justify-between border-b border-border/80 px-4">
          <Link href="/dashboard" className="flex items-center gap-2.5 overflow-hidden">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-ai/20 border border-ai/50 text-ai-light shadow-glow">
              <ShieldAlert className="h-4 w-4" />
            </div>
            {!isCollapsed && (
              <div className="flex flex-col">
                <span className="font-bold tracking-tight text-primaryText text-sm flex items-center gap-1">
                  {APP_NAME}
                  <span className="rounded bg-ai/20 px-1 py-0.2 text-[9px] font-mono text-ai-light border border-ai-border/40">
                    PRO
                  </span>
                </span>
                <span className="text-[10px] text-mutedText truncate">Payment Recovery</span>
              </div>
            )}
          </Link>

          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="hidden lg:flex h-6 w-6 items-center justify-center rounded border border-border bg-surface text-secondaryText hover:text-primaryText transition-colors"
            title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? <ChevronRight className="h-3.5 w-3.5" /> : <ChevronLeft className="h-3.5 w-3.5" />}
          </button>
        </div>

        {/* Navigation Categories */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6 no-scrollbar">
          {NAV_ITEMS.map((section, idx) => (
            <div key={idx} className="space-y-1">
              {!isCollapsed && (
                <h4 className="px-2 text-[10px] font-semibold text-mutedText uppercase tracking-wider mb-2">
                  {section.category}
                </h4>
              )}
              {section.items.map((item) => {
                const IconComponent = (iconMap[item.icon] || LayoutDashboard) as React.ComponentType<{ className?: string }>;
                const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);

                return (
                  // @ts-ignore Next typed routes
                  <LinkComponent key={item.href} href={item.href as any} onClick={() => setIsMobileOpen?.(false)} className={cn("group relative flex items-center gap-3 rounded-md px-2.5 py-2 text-xs font-medium transition-all", isActive ? "bg-surface-elevated text-primaryText border border-border/80 shadow-subtle" : "text-secondaryText hover:bg-surface/60 hover:text-primaryText")} title={isCollapsed ? item.label : undefined}>
                    <IconComponent
                      className={cn(
                        "h-4 w-4 shrink-0 transition-colors",
                        isActive ? "text-ai-light" : "text-secondaryText group-hover:text-primaryText"
                      )}
                    />
                    {!isCollapsed && <span className="truncate">{item.label}</span>}
                    {!isCollapsed && Boolean(item.badge) && (
                      <span className="ml-auto rounded-full bg-ai/15 px-1.5 py-0.2 text-[10px] text-ai-light border border-ai/30 font-medium">
                        {item.badge}
                      </span>
                    )}

                    {/* Active Pip */}
                    {isActive && (
                      <span className="absolute left-0 top-1/2 -translate-y-1/2 h-4 w-1 rounded-r bg-ai" />
                    )}
                  </LinkComponent>
                );
              })}
            </div>
          ))}
        </div>

        {/* Live Demo Quick Action */}
        <div className="p-3 border-t border-border/80">
          <button
            onClick={() => {
              setIsMobileOpen?.(false);
              onRunDemo?.();
            }}
            className={cn(
              "w-full flex items-center justify-center gap-2 rounded-md bg-ai-bg/40 text-ai-light border border-ai-border/60 hover:bg-ai-bg/80 py-2 transition-all font-medium text-xs shadow-glow",
              isCollapsed && "px-0"
            )}
            title="Run Live Demo Mode"
          >
            <PlayCircle className="h-4 w-4 animate-pulse text-ai-light" />
            {!isCollapsed && <span>Run Live Demo</span>}
          </button>
        </div>
      </aside>
    </>
  );
}
