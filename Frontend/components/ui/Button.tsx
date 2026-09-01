import React from 'react';
import { cn } from '@/lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'ai';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', isLoading, children, disabled, ...props }, ref) => {
    const baseStyles = "inline-flex items-center justify-center font-medium transition-all focus:outline-none focus:ring-2 focus:ring-ai/50 disabled:opacity-50 disabled:pointer-events-none rounded-md select-none active:scale-[0.98]";

    const variants = {
      primary: "bg-primaryText text-bg hover:bg-white border border-transparent shadow-subtle",
      secondary: "bg-surface-elevated text-primaryText hover:bg-surface-hover border border-border/80",
      outline: "bg-transparent text-primaryText border border-border hover:bg-surface-elevated hover:border-border/80",
      ghost: "bg-transparent text-secondaryText hover:text-primaryText hover:bg-surface-elevated",
      danger: "bg-danger-bg text-danger hover:bg-danger/20 border border-danger-border",
      ai: "bg-ai/15 text-ai-light hover:bg-ai/25 border border-ai-border shadow-glow",
    };

    const sizes = {
      sm: "h-8 px-3 text-xs gap-1.5",
      md: "h-9 px-4 text-sm gap-2",
      lg: "h-11 px-6 text-base gap-2.5",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {isLoading && (
          <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-current" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        )}
        {children}
      </button>
    );
  }
);
Button.displayName = 'Button';
