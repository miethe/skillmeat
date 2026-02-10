'use client';

import { X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

export interface ActiveFilterItem {
  id: string;
  label: string;
  onRemove: () => void;
  ariaLabel?: string;
}

interface ActiveFilterRowProps {
  items: ActiveFilterItem[];
  prefixLabel?: string;
  ariaLabel?: string;
}

export function ActiveFilterRow({
  items,
  prefixLabel = 'Active filters:',
  ariaLabel = 'Active filters',
}: ActiveFilterRowProps) {
  if (items.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2" role="status" aria-live="polite" aria-label={ariaLabel}>
      <span className="text-sm text-muted-foreground">{prefixLabel}</span>
      {items.map((item) => (
        <Badge key={item.id} variant="secondary" className="gap-1">
          {item.label}
          <button
            type="button"
            className="ml-1 rounded-full p-0.5 hover:bg-muted-foreground/20 focus:outline-none focus:ring-2 focus:ring-ring"
            onClick={item.onRemove}
            aria-label={item.ariaLabel ?? `Remove filter: ${item.label}`}
          >
            <X className="h-3 w-3" aria-hidden="true" />
          </button>
        </Badge>
      ))}
    </div>
  );
}
