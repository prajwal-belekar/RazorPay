import React from 'react';
import { cn } from '@/lib/utils';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'glass' | 'interactive' | 'ai';
}

export function Card({ className, variant = 'default', children, ...props }: CardProps) {
  const baseStyles = "rounded-lg border text-primaryText transition-colors";
  
  const variants = {
    default: "bg-surface border-border",
    elevated: "bg-surface-elevated border-border/80 shadow-card",
    glass: "glass-card border-border/60",
    interactive: "bg-surface border-border hover:border-border/80 hover:bg-surface-elevated cursor-pointer",
    ai: "bg-surface border-ai-border/40 bg-gradient-to-br from-surface to-ai-bg/20",
  };

  return (
    <div className={cn(baseStyles, variants[variant], className)} {...props}>
      {children}
    </div>
  );
}

export function CardHeader({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-5 pb-3 flex flex-col gap-1.5", className)} {...props}>{children}</div>;
}

export function CardTitle({ className, children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn("text-sm font-semibold tracking-tight text-primaryText flex items-center gap-2", className)} {...props}>{children}</h3>;
}

export function CardDescription({ className, children, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-xs text-secondaryText", className)} {...props}>{children}</p>;
}

export function CardContent({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-5 pt-0", className)} {...props}>{children}</div>;
}

export function CardFooter({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-5 pt-0 flex items-center border-t border-border/40 mt-4", className)} {...props}>{children}</div>;
}
