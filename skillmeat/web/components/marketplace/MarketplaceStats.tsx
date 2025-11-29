'use client';

import { Download, Star, TrendingUp, Package } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import type { MarketplaceListing } from '@/types/marketplace';

interface MarketplaceStatsProps {
  listings: MarketplaceListing[];
  isLoading?: boolean;
}

export function MarketplaceStats({ listings, isLoading }: MarketplaceStatsProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="p-4">
            <Skeleton className="mb-2 h-4 w-20" />
            <Skeleton className="h-8 w-16" />
          </Card>
        ))}
      </div>
    );
  }

  const totalListings = listings.length;
  const totalArtifacts = listings.reduce((sum, listing) => sum + listing.artifact_count, 0);
  const totalDownloads = listings.reduce((sum, listing) => sum + (listing.downloads || 0), 0);
  const avgRating =
    listings
      .filter((l) => l.rating !== undefined)
      .reduce((sum, listing) => sum + (listing.rating || 0), 0) /
      listings.filter((l) => l.rating !== undefined).length || 0;

  const stats = [
    {
      label: 'Total Listings',
      value: totalListings.toLocaleString(),
      icon: Package,
      color: 'text-blue-600',
    },
    {
      label: 'Total Artifacts',
      value: totalArtifacts.toLocaleString(),
      icon: TrendingUp,
      color: 'text-green-600',
    },
    {
      label: 'Total Downloads',
      value: totalDownloads.toLocaleString(),
      icon: Download,
      color: 'text-purple-600',
    },
    {
      label: 'Average Rating',
      value: avgRating > 0 ? avgRating.toFixed(1) : 'N/A',
      icon: Star,
      color: 'text-yellow-600',
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat) => {
        const Icon = stat.icon;
        return (
          <Card key={stat.label} className="p-4">
            <div className="mb-2 flex items-center gap-2">
              <Icon className={`h-4 w-4 ${stat.color}`} />
              <span className="text-sm font-medium text-muted-foreground">{stat.label}</span>
            </div>
            <p className="text-2xl font-bold">{stat.value}</p>
          </Card>
        );
      })}
    </div>
  );
}
