"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { ListingDetail } from "@/types/marketplace";
import {
  Download,
  Shield,
  Package,
  Terminal,
  Bot,
  Webhook,
  Database,
  ExternalLink,
  Calendar,
  Tag,
  Scale,
  Globe,
  GitBranch,
  DollarSign,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { MarketplaceTrustPrompt } from "./MarketplaceTrustPrompt";
import { useInstallListing } from "@/hooks/useMarketplace";
import { useToast } from "@/hooks/use-toast";

interface MarketplaceListingDetailProps {
  listing: ListingDetail;
}

const ARTIFACT_ICONS = {
  skill: Package,
  command: Terminal,
  agent: Bot,
  hook: Webhook,
  "mcp-server": Database,
  bundle: Package,
};

const ARTIFACT_COLORS = {
  skill: "text-blue-600",
  command: "text-green-600",
  agent: "text-purple-600",
  hook: "text-orange-600",
  "mcp-server": "text-cyan-600",
  bundle: "text-indigo-600",
};

export function MarketplaceListingDetail({ listing }: MarketplaceListingDetailProps) {
  const [showTrustPrompt, setShowTrustPrompt] = useState(false);
  const { mutate: installListing, isPending: isInstalling } = useInstallListing();
  const { toast } = useToast();

  const Icon = ARTIFACT_ICONS[listing.category];
  const iconColor = ARTIFACT_COLORS[listing.category];

  const handleInstall = () => {
    setShowTrustPrompt(true);
  };

  const handleConfirmInstall = (verifySignature: boolean) => {
    installListing(
      {
        listing_id: listing.listing_id,
        verify_signature: verifySignature,
      },
      {
        onSuccess: (data) => {
          setShowTrustPrompt(false);
          toast({
            title: "Installation successful",
            description: data.message,
          });
        },
        onError: (error) => {
          toast({
            title: "Installation failed",
            description: error.message,
            variant: "destructive",
          });
        },
      }
    );
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  const formatDownloads = (count: number): string => {
    if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
    if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
    return count.toString();
  };

  return (
    <>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className={cn("rounded-lg bg-secondary p-3", iconColor)}>
              <Icon className="h-8 w-8" />
            </div>
            <div>
              <h1 className="text-3xl font-bold">{listing.name}</h1>
              <div className="mt-2 flex items-center gap-3 text-muted-foreground">
                <span>{listing.publisher.name}</span>
                {listing.publisher.verified && (
                  <div className="flex items-center gap-1 text-blue-600">
                    <Shield className="h-4 w-4" />
                    <span className="text-xs font-medium">Verified</span>
                  </div>
                )}
                <span>•</span>
                <span>v{listing.version}</span>
              </div>
            </div>
          </div>
          <div className="flex gap-2">
            <Button onClick={handleInstall} size="lg" disabled={isInstalling}>
              <Download className="mr-2 h-4 w-4" />
              {isInstalling ? "Installing..." : "Install"}
            </Button>
          </div>
        </div>

        {/* Description */}
        <Card>
          <CardHeader>
            <CardTitle>Description</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">{listing.description}</p>
          </CardContent>
        </Card>

        {/* Stats Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardContent className="flex items-center gap-3 pt-6">
              <Download className="h-5 w-5 text-muted-foreground" />
              <div>
                <div className="text-2xl font-bold">{formatDownloads(listing.downloads)}</div>
                <p className="text-xs text-muted-foreground">Downloads</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-3 pt-6">
              <Package className="h-5 w-5 text-muted-foreground" />
              <div>
                <div className="text-2xl font-bold">{listing.artifact_count}</div>
                <p className="text-xs text-muted-foreground">Artifacts</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-3 pt-6">
              <Scale className="h-5 w-5 text-muted-foreground" />
              <div>
                <div className="text-lg font-bold">{listing.license}</div>
                <p className="text-xs text-muted-foreground">License</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-3 pt-6">
              {listing.price === 0 ? (
                <>
                  <DollarSign className="h-5 w-5 text-green-600" />
                  <div>
                    <div className="text-lg font-bold text-green-600">Free</div>
                    <p className="text-xs text-muted-foreground">Price</p>
                  </div>
                </>
              ) : (
                <>
                  <DollarSign className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <div className="text-lg font-bold">${listing.price}</div>
                    <p className="text-xs text-muted-foreground">Price</p>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Details Grid */}
        <div className="grid gap-4 md:grid-cols-2">
          {/* Metadata */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Metadata</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2 text-muted-foreground">
                  <Calendar className="h-4 w-4" />
                  Created
                </span>
                <span className="font-medium">{formatDate(listing.created_at)}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2 text-muted-foreground">
                  <Calendar className="h-4 w-4" />
                  Updated
                </span>
                <span className="font-medium">{formatDate(listing.updated_at)}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2 text-muted-foreground">
                  <Tag className="h-4 w-4" />
                  Category
                </span>
                <Badge variant="secondary">{listing.category}</Badge>
              </div>
            </CardContent>
          </Card>

          {/* Links */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Links</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {listing.homepage && (
                <a
                  href={listing.homepage}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between text-sm hover:text-primary"
                >
                  <span className="flex items-center gap-2 text-muted-foreground">
                    <Globe className="h-4 w-4" />
                    Homepage
                  </span>
                  <ExternalLink className="h-4 w-4" />
                </a>
              )}
              {listing.repository && (
                <a
                  href={listing.repository}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between text-sm hover:text-primary"
                >
                  <span className="flex items-center gap-2 text-muted-foreground">
                    <GitBranch className="h-4 w-4" />
                    Repository
                  </span>
                  <ExternalLink className="h-4 w-4" />
                </a>
              )}
              <a
                href={listing.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between text-sm hover:text-primary"
              >
                <span className="flex items-center gap-2 text-muted-foreground">
                  <Package className="h-4 w-4" />
                  Marketplace Page
                </span>
                <ExternalLink className="h-4 w-4" />
              </a>
            </CardContent>
          </Card>
        </div>

        {/* Tags */}
        {listing.tags.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Tags</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {listing.tags.map((tag) => (
                  <Badge key={tag} variant="secondary">
                    {tag}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Trust Prompt Dialog */}
      <MarketplaceTrustPrompt
        listing={listing}
        open={showTrustPrompt}
        onOpenChange={setShowTrustPrompt}
        onConfirm={handleConfirmInstall}
        isInstalling={isInstalling}
      />
    </>
  );
}

export function MarketplaceListingDetailSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <Skeleton className="h-16 w-16 rounded-lg" />
          <div className="space-y-2">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-4 w-40" />
          </div>
        </div>
        <Skeleton className="h-10 w-32" />
      </div>
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-32" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i}>
            <CardContent className="pt-6">
              <Skeleton className="h-12 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
