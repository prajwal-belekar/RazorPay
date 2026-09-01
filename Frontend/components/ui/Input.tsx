import React from 'react';
import { cn } from '@/lib/utils';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, label, error, icon, ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1.5 w-full">
        {label && <label className="text-xs font-medium text-secondaryText">{label}</label>}
        <div className="relative flex items-center">
          {icon && <div className="absolute left-3 text-secondaryText pointer-events-none">{icon}</div>}
          <input
            type={type}
            ref={ref}
            className={cn(
              "w-full rounded-md border border-border bg-surface px-3 py-1.5 text-xs text-primaryText placeholder:text-mutedText focus:outline-none focus:border-ai focus:ring-1 focus:ring-ai/50 transition-colors",
              icon && "pl-9",
              error && "border-danger focus:border-danger focus:ring-danger/50",
              className
            )}
            {...props}
          />
        </div>
        {error && <span className="text-[11px] text-danger">{error}</span>}
      </div>
    );
  }
);
Input.displayName = 'Input';
