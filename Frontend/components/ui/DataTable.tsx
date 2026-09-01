import React from 'react';
import { cn } from '@/lib/utils';

export interface Column<T> {
  header: string;
  accessorKey?: keyof T;
  cell?: (row: T) => React.ReactNode;
  className?: string;
  align?: 'left' | 'center' | 'right';
}

export function DataTable<T extends Record<string, any>>({
  columns,
  data,
  onRowClick,
  emptyText = "No records found",
  isLoading = false,
}: {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (row: T) => void;
  emptyText?: string;
  isLoading?: boolean;
}) {
  return (
    <div className="w-full overflow-x-auto rounded-lg border border-border/80 bg-surface">
      <table className="w-full text-left text-xs text-primaryText border-collapse">
        <thead className="bg-surface-elevated/60 text-secondaryText border-b border-border/80 font-medium">
          <tr>
            {columns.map((col, idx) => (
              <th
                key={idx}
                className={cn(
                  "px-4 py-3 text-xs tracking-wider uppercase font-semibold text-secondaryText/80",
                  col.align === 'center' && "text-center",
                  col.align === 'right' && "text-right",
                  col.className
                )}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border/40">
          {isLoading ? (
            Array.from({ length: 5 }).map((_, rIdx) => (
              <tr key={rIdx} className="animate-pulse">
                {columns.map((_, cIdx) => (
                  <td key={cIdx} className="px-4 py-3.5">
                    <div className="h-3.5 bg-surface-elevated/80 rounded w-3/4" />
                  </td>
                ))}
              </tr>
            ))
          ) : data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-secondaryText">
                {emptyText}
              </td>
            </tr>
          ) : (
            data.map((row, rowIdx) => (
              <tr
                key={row.id || row.proofId || row.transactionId || rowIdx}
                onClick={() => onRowClick?.(row)}
                className={cn(
                  "transition-colors hover:bg-surface-elevated/50",
                  onRowClick && "cursor-pointer"
                )}
              >
                {columns.map((col, cIdx) => (
                  <td
                    key={cIdx}
                    className={cn(
                      "px-4 py-3 text-xs font-normal text-primaryText whitespace-nowrap",
                      col.align === 'center' && "text-center",
                      col.align === 'right' && "text-right",
                      col.className
                    )}
                  >
                    {col.cell
                      ? col.cell(row)
                      : col.accessorKey
                      ? String(row[col.accessorKey] ?? '')
                      : null}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
