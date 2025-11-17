"use client";

import { Input } from "@/components/ui/input";
import { Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface MarketplaceSearchProps {
  value: string;
  onChange: (value: string) => void;
  onClear?: () => void;
}

export function MarketplaceSearch({ value, onChange, onClear }: MarketplaceSearchProps) {
  return (
    <div className="relative flex items-center">
      <Search className="absolute left-3 h-4 w-4 text-muted-foreground" />
      <Input
        type="text"
        placeholder="Search listings..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="pl-10 pr-10"
        aria-label="Search marketplace listings"
      />
      {value && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onClear}
          className="absolute right-1 h-7 w-7 p-0"
          aria-label="Clear search"
        >
          <X className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}
