"use client";

import { useState } from "react";
import { AlertTriangle, Download, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import type { MarketplaceListing } from "@/types/marketplace";

interface MarketplaceInstallDialogProps {
  listing: MarketplaceListing | null;
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (strategy: "merge" | "fork" | "skip") => void;
  isInstalling?: boolean;
}

export function MarketplaceInstallDialog({
  listing,
  isOpen,
  onClose,
  onConfirm,
  isInstalling = false,
}: MarketplaceInstallDialogProps) {
  const [strategy, setStrategy] = useState<"merge" | "fork" | "skip">("merge");

  const handleConfirm = () => {
    onConfirm(strategy);
  };

  if (!listing) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Install Bundle</DialogTitle>
          <DialogDescription>
            Install {listing.name} from {listing.publisher}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Bundle Info */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Artifacts:</span>
              <span className="text-sm">{listing.artifact_count} items</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Publisher:</span>
              <span className="text-sm">{listing.publisher}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">License:</span>
              <Badge variant="outline" className="text-xs">
                {listing.license}
              </Badge>
            </div>
          </div>

          {/* Conflict Strategy */}
          <div className="space-y-2">
            <label
              htmlFor="strategy-select"
              className="text-sm font-medium"
            >
              Conflict Resolution Strategy
            </label>
            <Select
              id="strategy-select"
              value={strategy}
              onChange={(e) => setStrategy(e.target.value as "merge" | "fork" | "skip")}
              disabled={isInstalling}
            >
              <option value="merge">
                Merge - Update existing artifacts
              </option>
              <option value="fork">
                Fork - Create copies with new names
              </option>
              <option value="skip">
                Skip - Only install new artifacts
              </option>
            </Select>
            <p className="text-xs text-muted-foreground">
              {strategy === "merge" &&
                "Existing artifacts will be updated with new versions."}
              {strategy === "fork" &&
                "Conflicts will be resolved by creating renamed copies."}
              {strategy === "skip" &&
                "Existing artifacts will be left unchanged."}
            </p>
          </div>

          {/* Trust Warning */}
          <div className="flex gap-2 p-3 rounded-lg bg-yellow-50 dark:bg-yellow-950/20 border border-yellow-200 dark:border-yellow-800">
            <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-500 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="text-sm font-medium text-yellow-900 dark:text-yellow-100">
                Trust Verification
              </p>
              <p className="text-xs text-yellow-800 dark:text-yellow-200">
                This bundle is signed and verified. However, always review
                artifacts before use as they may access system resources.
              </p>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={onClose}
            disabled={isInstalling}
          >
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={isInstalling}
          >
            {isInstalling ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Installing...
              </>
            ) : (
              <>
                <Download className="h-4 w-4 mr-2" />
                Install Bundle
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
