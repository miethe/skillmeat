"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { AlertTriangle, Shield, ShieldAlert, Info } from "lucide-react";
import { useState } from "react";
import type { ListingDetail } from "@/types/marketplace";

interface MarketplaceTrustPromptProps {
  listing: ListingDetail;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (verifySignature: boolean) => void;
  isInstalling?: boolean;
}

export function MarketplaceTrustPrompt({
  listing,
  open,
  onOpenChange,
  onConfirm,
  isInstalling = false,
}: MarketplaceTrustPromptProps) {
  const [verifySignature, setVerifySignature] = useState(true);
  const [understood, setUnderstood] = useState(false);

  const hasSignature = !!listing.signature;
  const isVerifiedPublisher = listing.publisher.verified;
  const isFree = listing.price === 0;

  // Calculate trust level
  const getTrustLevel = (): "high" | "medium" | "low" => {
    if (isVerifiedPublisher && hasSignature) return "high";
    if (isVerifiedPublisher || hasSignature) return "medium";
    return "low";
  };

  const trustLevel = getTrustLevel();

  const handleConfirm = () => {
    onConfirm(verifySignature);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[550px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {trustLevel === "high" && <Shield className="h-5 w-5 text-green-600" />}
            {trustLevel === "medium" && <AlertTriangle className="h-5 w-5 text-yellow-600" />}
            {trustLevel === "low" && <ShieldAlert className="h-5 w-5 text-red-600" />}
            Install from Marketplace
          </DialogTitle>
          <DialogDescription>
            Review security information before installing <strong>{listing.name}</strong>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Trust Level Indicator */}
          <div
            className={`rounded-lg border p-4 ${
              trustLevel === "high"
                ? "border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950"
                : trustLevel === "medium"
                  ? "border-yellow-200 bg-yellow-50 dark:border-yellow-900 dark:bg-yellow-950"
                  : "border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950"
            }`}
          >
            <div className="flex items-start gap-3">
              {trustLevel === "high" && <Shield className="mt-0.5 h-5 w-5 text-green-600" />}
              {trustLevel === "medium" && (
                <AlertTriangle className="mt-0.5 h-5 w-5 text-yellow-600" />
              )}
              {trustLevel === "low" && <ShieldAlert className="mt-0.5 h-5 w-5 text-red-600" />}
              <div className="flex-1 space-y-1">
                <p
                  className={`text-sm font-semibold ${
                    trustLevel === "high"
                      ? "text-green-900 dark:text-green-100"
                      : trustLevel === "medium"
                        ? "text-yellow-900 dark:text-yellow-100"
                        : "text-red-900 dark:text-red-100"
                  }`}
                >
                  {trustLevel === "high" && "High Trust Level"}
                  {trustLevel === "medium" && "Medium Trust Level"}
                  {trustLevel === "low" && "Low Trust Level"}
                </p>
                <ul
                  className={`space-y-1 text-xs ${
                    trustLevel === "high"
                      ? "text-green-800 dark:text-green-200"
                      : trustLevel === "medium"
                        ? "text-yellow-800 dark:text-yellow-200"
                        : "text-red-800 dark:text-red-200"
                  }`}
                >
                  <li className="flex items-center gap-2">
                    <span>{isVerifiedPublisher ? "✓" : "✗"}</span>
                    <span>Verified publisher</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <span>{hasSignature ? "✓" : "✗"}</span>
                    <span>Cryptographically signed</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <span>{isFree ? "✓" : "✗"}</span>
                    <span>Free (no payment required)</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          {/* Publisher Information */}
          <div className="space-y-2 rounded-lg border bg-card p-4">
            <h4 className="text-sm font-semibold">Publisher Information</h4>
            <div className="space-y-1 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Name:</span>
                <span className="font-medium">{listing.publisher.name}</span>
              </div>
              {listing.publisher.website && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Website:</span>
                  <a
                    href={listing.publisher.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium text-blue-600 hover:underline"
                  >
                    {new URL(listing.publisher.website).hostname}
                  </a>
                </div>
              )}
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">License:</span>
                <span className="font-medium">{listing.license}</span>
              </div>
            </div>
          </div>

          {/* Security Options */}
          {hasSignature && (
            <div className="flex items-start space-x-2">
              <Checkbox
                id="verify-signature"
                checked={verifySignature}
                onCheckedChange={(checked) => setVerifySignature(checked as boolean)}
              />
              <div className="grid gap-1.5 leading-none">
                <Label
                  htmlFor="verify-signature"
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                >
                  Verify cryptographic signature
                </Label>
                <p className="text-xs text-muted-foreground">
                  Ensures the bundle hasn't been tampered with (recommended)
                </p>
              </div>
            </div>
          )}

          {/* Warning Message */}
          <div className="flex items-start gap-3 rounded-lg border border-orange-200 bg-orange-50 p-3 dark:border-orange-900 dark:bg-orange-950">
            <Info className="mt-0.5 h-4 w-4 text-orange-600" />
            <div className="flex-1 space-y-1 text-xs text-orange-900 dark:text-orange-100">
              <p className="font-semibold">Important Security Notice:</p>
              <ul className="ml-4 list-disc space-y-0.5">
                <li>Artifacts can execute code and access system resources</li>
                <li>Only install from publishers you trust</li>
                <li>Review the source code if possible before installation</li>
                <li>Installation is at your own risk</li>
              </ul>
            </div>
          </div>

          {/* Acknowledgment Checkbox */}
          <div className="flex items-start space-x-2">
            <Checkbox
              id="understood"
              checked={understood}
              onCheckedChange={(checked) => setUnderstood(checked as boolean)}
            />
            <Label
              htmlFor="understood"
              className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
            >
              I understand the risks and wish to proceed with installation
            </Label>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isInstalling}>
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={!understood || isInstalling}>
            {isInstalling ? "Installing..." : "Install"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
