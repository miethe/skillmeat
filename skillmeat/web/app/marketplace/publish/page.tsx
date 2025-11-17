"use client";

import { useRouter } from "next/navigation";
import { ChevronLeft, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { MarketplacePublishWizard } from "@/components/marketplace/MarketplacePublishWizard";
import { useBrokers, usePublishBundle } from "@/hooks/useMarketplace";
import { Skeleton } from "@/components/ui/skeleton";
import type { PublishFormData, PublishResponse } from "@/types/marketplace";
import { useState } from "react";

export default function PublishPage() {
  const router = useRouter();
  const [publishResult, setPublishResult] = useState<PublishResponse | null>(null);

  // Fetch brokers
  const { data: brokersData, isLoading: brokersLoading, error: brokersError } = useBrokers();
  const publishMutation = usePublishBundle();

  const brokers = brokersData || [];

  const handlePublish = async (formData: PublishFormData) => {
    if (!formData.bundle_path || !formData.broker) {
      throw new Error("Missing required fields");
    }

    const result = await publishMutation.mutateAsync({
      bundle_path: formData.bundle_path,
      broker: formData.broker,
      metadata: {
        description: formData.description,
        tags: formData.tags,
        homepage: formData.homepage,
        repository: formData.repository,
      },
    });

    setPublishResult(result);
  };

  const handleCancel = () => {
    if (confirm("Are you sure you want to cancel? All progress will be lost.")) {
      router.push("/marketplace");
    }
  };

  const handleDone = () => {
    if (publishResult?.listing_url) {
      window.open(publishResult.listing_url, "_blank", "noopener,noreferrer");
    }
    router.push("/marketplace");
  };

  // Show success state if published
  if (publishResult) {
    return (
      <div className="space-y-6">
        {/* Header */}
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

        {/* Success Card */}
        <Card className="p-8 text-center max-w-2xl mx-auto">
          <CheckCircle className="h-16 w-16 text-green-600 mx-auto mb-4" />
          <h2 className="text-2xl font-bold mb-2">
            {publishResult.status === "approved"
              ? "Bundle Published!"
              : "Bundle Submitted!"}
          </h2>
          <p className="text-muted-foreground mb-6">{publishResult.message}</p>

          <div className="space-y-3 mb-6">
            <div className="flex justify-between items-center py-2 border-b">
              <span className="text-sm font-medium">Submission ID:</span>
              <span className="text-sm font-mono text-muted-foreground">
                {publishResult.submission_id}
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b">
              <span className="text-sm font-medium">Status:</span>
              <span className="text-sm capitalize">{publishResult.status}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b">
              <span className="text-sm font-medium">Broker:</span>
              <span className="text-sm capitalize">{publishResult.broker}</span>
            </div>
          </div>

          {publishResult.status === "pending" && (
            <p className="text-sm text-muted-foreground mb-6">
              Your bundle is pending review. You'll be notified once it's approved
              and published to the marketplace.
            </p>
          )}

          <div className="flex gap-3 justify-center">
            {publishResult.listing_url && (
              <Button
                variant="outline"
                onClick={() =>
                  window.open(publishResult.listing_url, "_blank", "noopener,noreferrer")
                }
              >
                View Listing
              </Button>
            )}
            <Button onClick={handleDone}>Return to Marketplace</Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
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

      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight mb-2">
          Publish Bundle
        </h1>
        <p className="text-muted-foreground">
          Share your artifacts with the community by publishing to the marketplace
        </p>
      </div>

      {/* Loading State */}
      {brokersLoading && (
        <Card className="p-6">
          <div className="space-y-4">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        </Card>
      )}

      {/* Error State */}
      {brokersError && (
        <Card className="p-6">
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
            <p className="text-sm text-destructive">
              Failed to load marketplace brokers. Please try again later.
            </p>
          </div>
        </Card>
      )}

      {/* Publish Wizard */}
      {!brokersLoading && !brokersError && (
        <MarketplacePublishWizard
          brokers={brokers}
          onPublish={handlePublish}
          onCancel={handleCancel}
        />
      )}
    </div>
  );
}
