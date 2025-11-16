"use client";

/**
 * Share Link Component
 *
 * Display and manage shareable links with QR codes and clipboard functionality
 */

import { useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import {
  Copy,
  Check,
  ExternalLink,
  QrCode,
  Calendar,
  Download,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PermissionBadge } from "./permission-badge";
import type { ShareLink as ShareLinkType } from "@/types/bundle";

export interface ShareLinkProps {
  shareLink: ShareLinkType;
  onRevoke?: () => void;
  onUpdate?: (updates: Partial<ShareLinkType>) => void;
  showAnalytics?: boolean;
}

export function ShareLink({
  shareLink,
  onRevoke,
  showAnalytics = true,
}: ShareLinkProps) {
  const [copied, setCopied] = useState(false);
  const [showQR, setShowQR] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(shareLink.url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error("Failed to copy:", error);
    }
  };

  const isExpired =
    shareLink.expiresAt && new Date(shareLink.expiresAt) < new Date();

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Share Link</CardTitle>
          <div className="flex items-center gap-2">
            <PermissionBadge level={shareLink.permissionLevel} />
            {onRevoke && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onRevoke}
                title="Revoke link"
              >
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Link Input */}
        <div className="space-y-2">
          <Label htmlFor="share-url">Share URL</Label>
          <div className="flex gap-2">
            <Input
              id="share-url"
              value={shareLink.shortUrl || shareLink.url}
              readOnly
              className="font-mono text-sm"
            />
            <Button
              variant="outline"
              size="icon"
              onClick={handleCopy}
              title="Copy to clipboard"
            >
              {copied ? (
                <Check className="h-4 w-4 text-green-600" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
            </Button>
            <Button
              variant="outline"
              size="icon"
              onClick={() => window.open(shareLink.url, "_blank")}
              title="Open in new tab"
            >
              <ExternalLink className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              onClick={() => setShowQR(!showQR)}
              title="Show QR code"
            >
              <QrCode className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* QR Code */}
        {showQR && (
          <div className="flex justify-center p-4 bg-white rounded-lg border">
            <QRCodeSVG value={shareLink.url} size={200} level="H" />
          </div>
        )}

        {/* Link Info */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          {shareLink.expiresAt && (
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-muted-foreground">
                <Calendar className="h-3 w-3" />
                <span>Expires</span>
              </div>
              <p className={isExpired ? "text-destructive font-medium" : ""}>
                {isExpired ? "Expired" : new Date(shareLink.expiresAt).toLocaleDateString()}
              </p>
            </div>
          )}
          {showAnalytics && (
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-muted-foreground">
                <Download className="h-3 w-3" />
                <span>Downloads</span>
              </div>
              <p className="font-medium">{shareLink.downloadCount}</p>
            </div>
          )}
        </div>

        {/* Expiration Warning */}
        {isExpired && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
            This link has expired and can no longer be used.
          </div>
        )}
      </CardContent>
    </Card>
  );
}
