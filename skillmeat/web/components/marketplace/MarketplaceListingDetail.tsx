"use client";

import { ExternalLink, Package, Download, Star, Calendar, Shield, Home, Code } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { MarketplaceListingDetail } from "@/types/marketplace";

interface MarketplaceListingDetailProps {
  listing: MarketplaceListingDetail | null;
  isLoading?: boolean;
  onInstall?: () => void;
}

export function MarketplaceListingDetail({
  listing,
  isLoading,
  onInstall,
}: MarketplaceListingDetailProps) {
  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="h-32 w-full" />
        <div className="grid grid-cols-2 gap-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      </div>
    );
  }

  if (!listing) {
    return (
      <Card className="p-6">
        <p className="text-center text-muted-foreground">
          Listing not found or failed to load.
        </p>
      </Card>
    );
  }

  const createdDate = new Date(listing.created_at);
  const formattedDate = createdDate.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-start justify-between gap-4 mb-2">
          <div className="flex-1 min-w-0">
            <h1 className="text-3xl font-bold tracking-tight mb-2">
              {listing.name}
            </h1>
            <p className="text-lg text-muted-foreground">
              by {listing.publisher}
            </p>
          </div>
          {listing.price === 0 ? (
            <Badge variant="secondary" className="text-lg px-3 py-1">
              Free
            </Badge>
          ) : (
            <Badge variant="outline" className="text-lg px-3 py-1">
              ${(listing.price / 100).toFixed(2)}
            </Badge>
          )}
        </div>

        {listing.version && (
          <p className="text-sm text-muted-foreground">
            Version {listing.version}
          </p>
        )}
      </div>

      {/* Description */}
      {listing.description && (
        <Card className="p-4">
          <p className="text-base leading-relaxed">{listing.description}</p>
        </Card>
      )}

      {/* Metadata Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <Package className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Artifacts</span>
          </div>
          <p className="text-2xl font-bold">{listing.artifact_count}</p>
        </Card>

        {listing.downloads !== undefined && (
          <Card className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Download className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Downloads</span>
            </div>
            <p className="text-2xl font-bold">{listing.downloads}</p>
          </Card>
        )}

        {listing.rating !== undefined && (
          <Card className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Star className="h-4 w-4 text-yellow-400 fill-yellow-400" />
              <span className="text-sm font-medium">Rating</span>
            </div>
            <p className="text-2xl font-bold">{listing.rating.toFixed(1)}</p>
          </Card>
        )}

        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Published</span>
          </div>
          <p className="text-sm">{formattedDate}</p>
        </Card>
      </div>

      {/* License & Signature */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <Shield className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">License</span>
          </div>
          <Badge variant="outline" className="mt-1">
            {listing.license}
          </Badge>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <Shield className="h-4 w-4 text-green-600" />
            <span className="text-sm font-medium">Signature</span>
          </div>
          <p className="text-xs text-muted-foreground font-mono truncate" title={listing.signature}>
            {listing.signature.slice(0, 32)}...
          </p>
          <p className="text-xs text-green-600 mt-1">Verified</p>
        </Card>
      </div>

      {/* Tags */}
      {listing.tags.length > 0 && (
        <Card className="p-4">
          <h3 className="text-sm font-medium mb-3">Tags</h3>
          <div className="flex flex-wrap gap-2">
            {listing.tags.map((tag) => (
              <Badge key={tag} variant="secondary">
                {tag}
              </Badge>
            ))}
          </div>
        </Card>
      )}

      {/* Links */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {listing.homepage && (
          <Button
            variant="outline"
            className="justify-start"
            onClick={() => window.open(listing.homepage, "_blank", "noopener,noreferrer")}
          >
            <Home className="h-4 w-4 mr-2" />
            Homepage
            <ExternalLink className="h-3 w-3 ml-auto" />
          </Button>
        )}

        {listing.repository && (
          <Button
            variant="outline"
            className="justify-start"
            onClick={() => window.open(listing.repository, "_blank", "noopener,noreferrer")}
          >
            <Code className="h-4 w-4 mr-2" />
            Repository
            <ExternalLink className="h-3 w-3 ml-auto" />
          </Button>
        )}

        <Button
          variant="outline"
          className="justify-start"
          onClick={() => window.open(listing.source_url, "_blank", "noopener,noreferrer")}
        >
          <ExternalLink className="h-4 w-4 mr-2" />
          View on Marketplace
        </Button>
      </div>

      {/* Install Button */}
      {onInstall && (
        <Card className="p-4 bg-secondary/50">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h3 className="font-medium mb-1">Ready to install?</h3>
              <p className="text-sm text-muted-foreground">
                This will download and import {listing.artifact_count} artifacts
                into your collection.
              </p>
            </div>
            <Button size="lg" onClick={onInstall}>
              <Download className="h-4 w-4 mr-2" />
              Install Bundle
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
