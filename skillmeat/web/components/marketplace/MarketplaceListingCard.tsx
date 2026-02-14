'use client';

import { Download, ExternalLink, Package, Star, Tag } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { MarketplaceListing } from '@/types/marketplace';

interface MarketplaceListingCardProps {
  listing: MarketplaceListing;
  onClick?: (listing: MarketplaceListing) => void;
}

export function MarketplaceListingCard({ listing, onClick }: MarketplaceListingCardProps) {
  const handleClick = () => {
    if (onClick) {
      onClick(listing);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  };

  return (
    <Card
      className="cursor-pointer p-4 transition-shadow focus-within:ring-2 focus-within:ring-ring hover:shadow-lg"
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
      aria-label={`View listing: ${listing.name}`}
    >
      {/* Header */}
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-lg font-semibold" title={listing.name}>
            {listing.name}
          </h3>
          <p className="truncate text-sm text-muted-foreground">by {listing.publisher}</p>
        </div>
        {listing.price === 0 ? (
          <Badge variant="secondary" className="shrink-0">
            Free
          </Badge>
        ) : (
          <Badge variant="outline" className="shrink-0">
            ${(listing.price / 100).toFixed(2)}
          </Badge>
        )}
      </div>

      {/* Description */}
      {listing.description && (
        <p className="mb-3 line-clamp-2 text-sm text-muted-foreground">{listing.description}</p>
      )}

      {/* Metadata */}
      <div className="mb-3 flex items-center gap-4 text-sm text-muted-foreground">
        <div className="flex items-center gap-1" title="Number of artifacts">
          <Package className="h-4 w-4" />
          <span>{listing.artifact_count}</span>
        </div>

        {listing.downloads !== undefined && (
          <div className="flex items-center gap-1" title="Download count">
            <Download className="h-4 w-4" />
            <span>{listing.downloads}</span>
          </div>
        )}

        {listing.rating !== undefined && (
          <div className="flex items-center gap-1" title="Rating">
            <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
            <span>{listing.rating.toFixed(1)}</span>
          </div>
        )}

        <Badge variant="outline" className="ml-auto">
          {listing.license}
        </Badge>
      </div>

      {/* Tags */}
      {listing.tags.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-1.5">
          {[...listing.tags].sort((a, b) => a.localeCompare(b)).slice(0, 3).map((tag) => (
            <Badge key={tag} variant="secondary" className="text-xs">
              <Tag className="mr-1 h-3 w-3" />
              {tag}
            </Badge>
          ))}
          {listing.tags.length > 3 && (
            <Badge variant="secondary" className="text-xs">
              +{listing.tags.length - 3} more
            </Badge>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          className="flex-1"
          onClick={(e) => {
            e.stopPropagation();
            handleClick();
          }}
        >
          View Details
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={(e) => {
            e.stopPropagation();
            window.open(listing.source_url, '_blank', 'noopener,noreferrer');
          }}
          aria-label="Open listing in new tab"
        >
          <ExternalLink className="h-4 w-4" />
        </Button>
      </div>
    </Card>
  );
}
