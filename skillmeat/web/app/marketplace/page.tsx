import type { Metadata } from "next";
import { MarketplaceListingCatalog } from "@/components/marketplace/MarketplaceListingCatalog";

export const metadata: Metadata = {
  title: "Marketplace",
  description: "Browse and install artifacts from the SkillMeat marketplace",
};

export default function MarketplacePage() {
  return (
    <div className="container mx-auto">
      <div className="mb-8">
        <h1 className="text-4xl font-bold">Marketplace</h1>
        <p className="mt-2 text-lg text-muted-foreground">
          Discover and install skills, commands, agents, and more from the community
        </p>
      </div>

      <MarketplaceListingCatalog />
    </div>
  );
}
