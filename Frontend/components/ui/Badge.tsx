import React from 'react';
import { cn } from '@/lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'ai' | 'info' | 'outline';
  size?: 'sm' | 'md';
}

export function Badge({ className, variant = 'default', size = 'md', children, ...props }: BadgeProps) {
  const base = "inline-flex items-center font-medium rounded-full tracking-wide";
  
  const variants = {
    default: "bg-surface-elevated text-secondaryText border border-border/80",
    success: "bg-success-bg text-success border border-success-border",
    warning: "bg-warning-bg text-warning border border-warning-border",
    danger: "bg-danger-bg text-danger border border-danger-border",
    ai: "bg-ai-bg text-ai-light border border-ai-border",
    info: "bg-info-bg text-info-light border border-info-border",
    outline: "bg-transparent text-secondaryText border border-border",
  };

  const sizes = {
    sm: "px-2 py-0.5 text-[10px] gap-1",
    md: "px-2.5 py-0.5 text-xs gap-1.5",
  };

  return (
    <span className={cn(base, variants[variant], sizes[size], className)} {...props}>
      {children}
    </span>
  );
}
