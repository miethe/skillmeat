"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { MarketplaceListingDetail, MarketplaceListingDetailSkeleton } from "@/components/marketplace/MarketplaceListingDetail";
import { useMarketplaceListing } from "@/hooks/useMarketplace";
import { ChevronLeft } from "lucide-react";

export default function MarketplaceListingPage() {
  const params = useParams();
  const listingId = params.id as string;

  const { data: listing, isLoading, error } = useMarketplaceListing(listingId);

  return (
    <div className="container mx-auto">
      {/* Back Button */}
      <div className="mb-6">
        <Link href="/marketplace">
          <Button variant="ghost" size="sm">
            <ChevronLeft className="mr-2 h-4 w-4" />
            Back to Marketplace
          </Button>
        </Link>
      </div>

      {/* Loading State */}
      {isLoading && <MarketplaceListingDetailSkeleton />}

      {/* Error State */}
      {error && (
        <div className="flex flex-col items-center justify-center rounded-lg border border-destructive/50 bg-destructive/10 p-12 text-center">
          <p className="text-lg font-semibold text-destructive">Failed to load listing</p>
          <p className="mt-2 text-sm text-muted-foreground">{error.message}</p>
          <div className="mt-4 flex gap-2">
            <Link href="/marketplace">
              <Button variant="outline">Back to Marketplace</Button>
            </Link>
            <Button onClick={() => window.location.reload()}>Retry</Button>
          </div>
        </div>
      )}

      {/* Content */}
      {!isLoading && !error && listing && <MarketplaceListingDetail listing={listing} />}
    </div>
  );
}
