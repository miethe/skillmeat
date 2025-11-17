"use client";

import Link from "next/link";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Listing } from "@/types/marketplace";
import { Download, Shield, Package, Terminal, Bot, Webhook, Database } from "lucide-react";
import { cn } from "@/lib/utils";

interface MarketplaceListingCardProps {
  listing: Listing;
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

export function MarketplaceListingCard({ listing }: MarketplaceListingCardProps) {
  const Icon = ARTIFACT_ICONS[listing.category];
  const iconColor = ARTIFACT_COLORS[listing.category];

  // Format download count
  const formatDownloads = (count: number): string => {
    if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
    if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
    return count.toString();
  };

  // Format date
  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
    return `${Math.floor(diffDays / 365)} years ago`;
  };

  return (
    <Link href={`/marketplace/${listing.listing_id}`} className="block">
      <Card className="h-full transition-all hover:shadow-lg hover:border-primary/50">
        <CardHeader>
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-3">
              <div className={cn("rounded-lg bg-secondary p-2", iconColor)}>
                <Icon className="h-5 w-5" />
              </div>
              <div className="flex-1">
                <CardTitle className="text-lg font-semibold leading-tight">
                  {listing.name}
                </CardTitle>
                <div className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
                  <span>{listing.publisher.name}</span>
                  {listing.publisher.verified && (
                    <Shield className="h-3 w-3 text-blue-600" aria-label="Verified publisher" />
                  )}
                </div>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="line-clamp-2 text-sm text-muted-foreground">{listing.description}</p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {listing.tags.slice(0, 3).map((tag) => (
              <Badge key={tag} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))}
            {listing.tags.length > 3 && (
              <Badge variant="secondary" className="text-xs">
                +{listing.tags.length - 3}
              </Badge>
            )}
          </div>
        </CardContent>
        <CardFooter className="flex items-center justify-between border-t pt-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <Download className="h-3 w-3" />
            <span>{formatDownloads(listing.downloads)}</span>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
              {listing.license}
            </Badge>
            <span>v{listing.version}</span>
          </div>
          <span>Updated {formatDate(listing.updated_at)}</span>
        </CardFooter>
      </Card>
    </Link>
  );
}
