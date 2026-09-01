'use client';

import React, { useState, useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { MoreVertical, MoreHorizontal } from 'lucide-react';

export interface DropdownItem {
  id: string;
  label: React.ReactNode;
  icon?: React.ReactNode;
  onClick: () => void;
  danger?: boolean;
  disabled?: boolean;
}

export function DropdownMenu({
  items,
  triggerIcon = 'vertical',
  align = 'right',
  className,
}: {
  items: DropdownItem[];
  triggerIcon?: 'vertical' | 'horizontal';
  align?: 'left' | 'right';
  className?: string;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const TriggerIcon = triggerIcon === 'vertical' ? MoreVertical : MoreHorizontal;

  return (
    <div className="relative inline-block text-left" ref={menuRef}>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setIsOpen(!isOpen);
        }}
        className={cn(
          "rounded-md p-1 text-secondaryText hover:bg-surface-elevated hover:text-primaryText transition-colors focus:outline-none",
          isOpen && "bg-surface-elevated text-primaryText",
          className
        )}
        aria-label="More options"
      >
        <TriggerIcon className="h-4 w-4" />
      </button>

      {isOpen && (
        <div
          className={cn(
            "absolute z-50 mt-1 w-48 rounded-lg border border-border bg-surface-elevated p-1 shadow-card animate-in fade-in slide-in-from-top-1 duration-150 text-xs",
            align === 'right' ? 'right-0' : 'left-0'
          )}
          onClick={(e) => e.stopPropagation()}
        >
          {items.map((item) => (
            <button
              key={item.id}
              disabled={item.disabled}
              onClick={() => {
                setIsOpen(false);
                item.onClick();
              }}
              className={cn(
                "w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md transition-colors text-left font-medium cursor-pointer",
                item.danger
                  ? "text-danger hover:bg-danger-bg hover:text-danger-light"
                  : "text-secondaryText hover:bg-surface hover:text-primaryText",
                item.disabled && "opacity-50 cursor-not-allowed"
              )}
            >
              {item.icon && <span className="h-3.5 w-3.5 shrink-0">{item.icon}</span>}
              <span className="truncate">{item.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
