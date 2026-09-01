import React from 'react';
import { Button } from './Button';
import { AlertTriangle, Inbox, RefreshCw } from 'lucide-react';

export function EmptyState({
  title = "No data found",
  description = "There are currently no items to display.",
  actionLabel,
  onAction,
  icon: Icon = Inbox,
}: {
  title?: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center rounded-lg border border-border/60 bg-surface/50 my-4">
      <div className="rounded-full bg-surface-elevated p-3 border border-border/80 mb-3 text-secondaryText">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="text-sm font-semibold text-primaryText mb-1">{title}</h3>
      <p className="text-xs text-secondaryText max-w-sm mb-4">{description}</p>
      {actionLabel && onAction && (
        <Button variant="secondary" size="sm" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
}

export function ErrorState({
  title = "Unable to load data",
  description = "Something went wrong while fetching data. Please try again.",
  onRetry,
}: {
  title?: string;
  description?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center rounded-lg border border-danger-border/50 bg-danger-bg/20 my-4">
      <div className="rounded-full bg-danger-bg p-3 border border-danger-border mb-3 text-danger">
        <AlertTriangle className="h-6 w-6" />
      </div>
      <h3 className="text-sm font-semibold text-primaryText mb-1">{title}</h3>
      <p className="text-xs text-secondaryText max-w-sm mb-4">{description}</p>
      {onRetry && (
        <Button variant="danger" size="sm" onClick={onRetry}>
          <RefreshCw className="h-3.5 w-3.5 mr-1" />
          Retry
        </Button>
      )}
    </div>
  );
}

export function LoadingState({ message = "Loading financial telemetry..." }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center my-4">
      <div className="relative mb-3">
        <div className="h-8 w-8 rounded-full border-2 border-ai/20 border-t-ai animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="h-2 w-2 rounded-full bg-ai animate-ping" />
        </div>
      </div>
      <p className="text-xs text-secondaryText font-medium">{message}</p>
    </div>
  );
}
