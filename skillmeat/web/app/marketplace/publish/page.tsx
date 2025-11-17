"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MarketplacePublishDialog } from "@/components/marketplace/MarketplacePublishDialog";
import { ChevronLeft, Upload, Info } from "lucide-react";

export default function MarketplacePublishPage() {
  const [bundlePath, setBundlePath] = useState("");
  const [showPublishDialog, setShowPublishDialog] = useState(false);

  const handlePublishClick = () => {
    if (!bundlePath.trim()) {
      return;
    }
    setShowPublishDialog(true);
  };

  const handlePublishSuccess = () => {
    setBundlePath("");
  };

  return (
    <div className="container mx-auto max-w-3xl">
      {/* Back Button */}
      <div className="mb-6">
        <Link href="/marketplace">
          <Button variant="ghost" size="sm">
            <ChevronLeft className="mr-2 h-4 w-4" />
            Back to Marketplace
          </Button>
        </Link>
      </div>

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold">Publish to Marketplace</h1>
        <p className="mt-2 text-lg text-muted-foreground">
          Share your bundles with the SkillMeat community
        </p>
      </div>

      {/* Info Cards */}
      <div className="mb-6 space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Info className="h-5 w-5" />
              Before You Publish
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>Please ensure your bundle meets the following requirements:</p>
            <ul className="ml-6 list-disc space-y-1">
              <li>All artifacts are properly documented with clear descriptions</li>
              <li>Source code is clean and follows best practices</li>
              <li>No malicious code or security vulnerabilities</li>
              <li>Appropriate license is included</li>
              <li>Version number follows semantic versioning (e.g., 1.0.0)</li>
              <li>Bundle has been tested and works as expected</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Review Process</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>All marketplace submissions undergo a review process:</p>
            <ul className="ml-6 list-disc space-y-1">
              <li>Automated security scanning for common vulnerabilities</li>
              <li>Manual review by SkillMeat moderators (1-2 business days)</li>
              <li>Verification of bundle integrity and metadata</li>
              <li>You'll receive an email when the review is complete</li>
            </ul>
          </CardContent>
        </Card>
      </div>

      {/* Bundle Selection */}
      <Card>
        <CardHeader>
          <CardTitle>Select Bundle</CardTitle>
          <CardDescription>
            Choose the bundle file you want to publish to the marketplace
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="bundle-path">Bundle Path</Label>
            <div className="flex gap-2">
              <Input
                id="bundle-path"
                value={bundlePath}
                onChange={(e) => setBundlePath(e.target.value)}
                placeholder="/path/to/bundle.tar.gz"
              />
              <Button
                onClick={handlePublishClick}
                disabled={!bundlePath.trim()}
                className="whitespace-nowrap"
              >
                <Upload className="mr-2 h-4 w-4" />
                Publish
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Enter the full path to your bundle file (must be a .tar.gz archive)
            </p>
          </div>

          {/* Alternative: Create Bundle First */}
          <div className="rounded-lg border border-dashed bg-muted/50 p-4">
            <p className="text-sm font-medium">Don't have a bundle yet?</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Use the <Link href="/collection" className="text-primary hover:underline">Collection</Link> page to create a bundle from your artifacts first.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Publish Dialog */}
      <MarketplacePublishDialog
        bundlePath={bundlePath}
        open={showPublishDialog}
        onOpenChange={setShowPublishDialog}
        onSuccess={handlePublishSuccess}
      />
    </div>
  );
}
