'use client';

import { Search } from 'lucide-react';
import { Input } from '@/components/ui/input';

interface ArtifactFilterBarProps {
  searchValue: string;
  onSearchChange: (value: string) => void;
  searchPlaceholder?: string;
  searchAriaLabel?: string;
  children?: React.ReactNode;
  className?: string;
}

export function ArtifactFilterBar({
  searchValue,
  onSearchChange,
  searchPlaceholder = 'Search artifacts...',
  searchAriaLabel = 'Search artifacts',
  children,
  className = '',
}: ArtifactFilterBarProps) {
  return (
    <div className={`space-y-3 border-b bg-muted/20 p-4 ${className}`} role="search" aria-label="Filter artifacts">
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-[200px] flex-1">
          <Search
            className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            placeholder={searchPlaceholder}
            value={searchValue}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-9"
            aria-label={searchAriaLabel}
          />
        </div>
        {children}
      </div>
    </div>
  );
}
