"use client";

import { Badge } from "@/components/ui/badge";
import { Clock, AlertCircle } from "lucide-react";

interface CacheFreshnessIndicatorProps {
  lastFetched: Date | null;
  isStale: boolean;
  cacheHit: boolean;
}

function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function CacheFreshnessIndicator({
  lastFetched,
  isStale,
  cacheHit,
}: CacheFreshnessIndicatorProps) {
  if (!lastFetched) {
    return (
      <Badge variant="secondary" className="gap-1">
        <Clock className="h-3 w-3" />
        Loading...
      </Badge>
    );
  }

  if (isStale) {
    return (
      <Badge variant="destructive" className="gap-1">
        <AlertCircle className="h-3 w-3" />
        Stale data
      </Badge>
    );
  }

  return (
    <Badge variant="secondary" className="gap-1">
      <Clock className="h-3 w-3" />
      Updated {formatTimeAgo(lastFetched)}
      {cacheHit && " (cached)"}
    </Badge>
  );
}
