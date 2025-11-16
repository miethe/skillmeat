"use client";

import { useState } from "react";
import { GitBranch } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { ConflictInfo } from "@/hooks/useSync";

export interface ConflictResolverProps {
  conflicts: ConflictInfo[];
  onResolve: (strategy: "ours" | "theirs" | "manual") => void;
  onCancel: () => void;
}

export function ConflictResolver({
  conflicts,
  onResolve,
  onCancel,
}: ConflictResolverProps) {
  const [selectedStrategy, setSelectedStrategy] = useState<
    "ours" | "theirs" | null
  >(null);

  const handleResolve = () => {
    if (selectedStrategy) {
      onResolve(selectedStrategy);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-yellow-500/10">
          <GitBranch className="h-5 w-5 text-yellow-600" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold">Conflicts Detected</h3>
          <p className="text-sm text-muted-foreground mt-1">
            {conflicts.length} file{conflicts.length !== 1 ? "s" : ""} have
            conflicts that need to be resolved before syncing.
          </p>
        </div>
      </div>

      {/* Conflicts List */}
      <div className="space-y-2 max-h-60 overflow-y-auto">
        {conflicts.map((conflict, index) => (
          <ConflictItem key={index} conflict={conflict} />
        ))}
      </div>

      {/* Resolution Strategy */}
      <div className="space-y-3 pt-4 border-t">
        <h4 className="text-sm font-medium">Choose Resolution Strategy</h4>

        <div className="space-y-2">
          {/* Keep Local (Ours) */}
          <button
            onClick={() => setSelectedStrategy("ours")}
            className={`w-full text-left rounded-lg border p-3 transition-colors ${
              selectedStrategy === "ours"
                ? "border-primary bg-primary/5"
                : "hover:border-primary/50"
            }`}
          >
            <div className="flex items-start gap-3">
              <div
                className={`h-5 w-5 rounded-full border-2 flex items-center justify-center mt-0.5 ${
                  selectedStrategy === "ours"
                    ? "border-primary bg-primary"
                    : "border-muted-foreground"
                }`}
              >
                {selectedStrategy === "ours" && (
                  <div className="h-2 w-2 rounded-full bg-primary-foreground" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium">Keep Local Version</span>
                  <Badge variant="outline" className="text-xs">
                    Ours
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Keep your local changes and discard upstream changes
                </p>
              </div>
            </div>
          </button>

          {/* Use Upstream (Theirs) */}
          <button
            onClick={() => setSelectedStrategy("theirs")}
            className={`w-full text-left rounded-lg border p-3 transition-colors ${
              selectedStrategy === "theirs"
                ? "border-primary bg-primary/5"
                : "hover:border-primary/50"
            }`}
          >
            <div className="flex items-start gap-3">
              <div
                className={`h-5 w-5 rounded-full border-2 flex items-center justify-center mt-0.5 ${
                  selectedStrategy === "theirs"
                    ? "border-primary bg-primary"
                    : "border-muted-foreground"
                }`}
              >
                {selectedStrategy === "theirs" && (
                  <div className="h-2 w-2 rounded-full bg-primary-foreground" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium">Use Upstream Version</span>
                  <Badge variant="outline" className="text-xs">
                    Theirs
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Overwrite local changes with upstream version
                </p>
              </div>
            </div>
          </button>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-2 pt-4 border-t">
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button
          onClick={handleResolve}
          disabled={!selectedStrategy}
        >
          Resolve Conflicts
        </Button>
      </div>
    </div>
  );
}

function ConflictItem({ conflict }: { conflict: ConflictInfo }) {
  const typeColors = {
    modified: "text-yellow-600",
    deleted: "text-red-600",
    added: "text-green-600",
  };

  const typeLabels = {
    modified: "Modified",
    deleted: "Deleted",
    added: "Added",
  };

  return (
    <div className="rounded-lg border p-3 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <code className="text-xs font-mono bg-muted px-2 py-1 rounded">
              {conflict.filePath}
            </code>
            <Badge
              variant="outline"
              className={`text-xs ${typeColors[conflict.conflictType]}`}
            >
              {typeLabels[conflict.conflictType]}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            {conflict.description}
          </p>
        </div>
      </div>

      {/* Version Comparison */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="space-y-1">
          <span className="text-muted-foreground">Local</span>
          <code className="block bg-muted px-2 py-1 rounded">
            {conflict.currentVersion}
          </code>
        </div>
        <div className="space-y-1">
          <span className="text-muted-foreground">Upstream</span>
          <code className="block bg-muted px-2 py-1 rounded">
            {conflict.upstreamVersion}
          </code>
        </div>
      </div>
    </div>
  );
}
