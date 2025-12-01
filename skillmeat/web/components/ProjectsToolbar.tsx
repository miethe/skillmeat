"use client";

import { useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";
import { useCacheRefresh } from "@/hooks/useCacheRefresh";
import { CacheFreshnessIndicator } from "./CacheFreshnessIndicator";
import { toast } from "sonner";

interface ProjectsToolbarProps {
  lastFetched: Date | null;
  isStale: boolean;
  cacheHit: boolean;
  onRefreshComplete?: () => void;
}

export function ProjectsToolbar({
  lastFetched,
  isStale,
  cacheHit,
  onRefreshComplete,
}: ProjectsToolbarProps) {
  const { refresh, isRefreshing } = useCacheRefresh();

  const handleRefresh = useCallback(async () => {
    toast.loading("Syncing projects...", { id: "cache-refresh" });
    try {
      await refresh();
      toast.success("Projects updated", { id: "cache-refresh" });
      onRefreshComplete?.();
    } catch (err) {
      toast.error("Failed to refresh projects", { id: "cache-refresh" });
    }
  }, [refresh, onRefreshComplete]);

  // Handle keyboard shortcut (Cmd/Ctrl + Shift + R)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "r") {
        e.preventDefault();
        handleRefresh();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleRefresh]);

  return (
    <div className="flex items-center justify-between">
      <CacheFreshnessIndicator
        lastFetched={lastFetched}
        isStale={isStale}
        cacheHit={cacheHit}
      />
      <Button
        variant="outline"
        size="sm"
        onClick={handleRefresh}
        disabled={isRefreshing}
        className="gap-2"
      >
        <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
        {isRefreshing ? "Refreshing..." : "Refresh"}
      </Button>
    </div>
  );
}
