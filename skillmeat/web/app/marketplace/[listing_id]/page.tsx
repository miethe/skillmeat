"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { MarketplaceListingDetail } from "@/components/marketplace/MarketplaceListingDetail";
import { MarketplaceInstallDialog } from "@/components/marketplace/MarketplaceInstallDialog";
import { useListing, useInstallListing } from "@/hooks/useMarketplace";

export default function ListingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const listingId = params.listing_id as string;

  const [isInstallDialogOpen, setIsInstallDialogOpen] = useState(false);

  // Fetch listing detail
  const { data: listing, isLoading, error } = useListing(listingId);
  const installMutation = useInstallListing();

  const handleInstallClick = () => {
    setIsInstallDialogOpen(true);
  };

  const handleInstallConfirm = async (strategy: "merge" | "fork" | "skip") => {
    if (!listing) return;

    await installMutation.mutateAsync({
      listing_id: listing.listing_id,
      strategy,
    });

    setIsInstallDialogOpen(false);
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumb / Back Navigation */}
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push("/marketplace")}
        >
          <ChevronLeft className="h-4 w-4 mr-1" />
          Back to Marketplace
        </Button>
      </div>

      {/* Error State */}
      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6">
          <h2 className="text-lg font-semibold text-destructive mb-2">
            Failed to Load Listing
          </h2>
          <p className="text-sm text-destructive">
            {error instanceof Error ? error.message : "Unknown error occurred"}
          </p>
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => router.push("/marketplace")}
          >
            Return to Marketplace
          </Button>
        </div>
      )}

      {/* Listing Detail */}
      {!error && (
        <MarketplaceListingDetail
          listing={listing || null}
          isLoading={isLoading}
          onInstall={handleInstallClick}
        />
      )}

      {/* Install Dialog */}
      {listing && (
        <MarketplaceInstallDialog
          listing={listing}
          isOpen={isInstallDialogOpen}
          onClose={() => setIsInstallDialogOpen(false)}
          onConfirm={handleInstallConfirm}
          isInstalling={installMutation.isPending}
        />
      )}
    </div>
  );
}
