/**
 * React Query hooks for bundle management
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type {
  BundleListItem,
  BundleAnalytics,
  ShareLink,
} from "@/types/bundle";

// Mock data generator
const generateMockBundles = (): BundleListItem[] => {
  return [
    {
      id: "bundle-1",
      metadata: {
        name: "Web Development Skills",
        description: "Essential skills for modern web development",
        tags: ["web", "frontend", "development"],
        author: "Current User",
        version: "1.0.0",
        createdAt: new Date(Date.now() - 7 * 86400000).toISOString(),
      },
      artifactCount: 5,
      size: 2.5 * 1024 * 1024,
      format: "zip",
      exportedAt: new Date(Date.now() - 7 * 86400000).toISOString(),
      shareLink: {
        url: "https://skillmeat.example.com/share/bundle-1",
        shortUrl: "https://sm.example.com/abc123",
        permissionLevel: "importer",
        downloadCount: 42,
        createdAt: new Date(Date.now() - 7 * 86400000).toISOString(),
      },
      downloadCount: 42,
      isImported: false,
    },
    {
      id: "bundle-2",
      metadata: {
        name: "Database Tools",
        description: "MCP servers and commands for database management",
        tags: ["database", "mcp", "sql"],
        author: "Team Member",
        version: "2.1.0",
        createdAt: new Date(Date.now() - 14 * 86400000).toISOString(),
      },
      artifactCount: 3,
      size: 1.8 * 1024 * 1024,
      format: "tar.gz",
      exportedAt: new Date(Date.now() - 14 * 86400000).toISOString(),
      downloadCount: 0,
      isImported: true,
    },
  ];
};

/**
 * Hook to fetch all bundles
 */
export function useBundles(filter?: "created" | "imported" | "all") {
  return useQuery({
    queryKey: ["bundles", filter],
    queryFn: async (): Promise<BundleListItem[]> => {
      // TODO: Replace with actual API call when P2-001 is complete
      // const bundles = await apiClient.bundles.listBundles({ filter });

      await new Promise((resolve) => setTimeout(resolve, 500));

      let bundles = generateMockBundles();

      if (filter === "created") {
        bundles = bundles.filter((b) => !b.isImported);
      } else if (filter === "imported") {
        bundles = bundles.filter((b) => b.isImported);
      }

      return bundles;
    },
    staleTime: 30000,
  });
}

/**
 * Hook to fetch bundle analytics
 */
export function useBundleAnalytics(bundleId: string | null) {
  return useQuery({
    queryKey: ["bundle-analytics", bundleId],
    queryFn: async (): Promise<BundleAnalytics | null> => {
      if (!bundleId) return null;

      // TODO: Replace with actual API call
      await new Promise((resolve) => setTimeout(resolve, 300));

      return {
        bundleId,
        downloads: 42,
        uniqueDownloaders: 15,
        lastDownloaded: new Date(Date.now() - 3600000).toISOString(),
        popularArtifacts: [
          {
            artifactId: "1",
            artifactName: "canvas-design",
            downloads: 25,
          },
          {
            artifactId: "2",
            artifactName: "docx-processor",
            downloads: 17,
          },
        ],
      };
    },
    enabled: !!bundleId,
  });
}

/**
 * Hook to delete a bundle
 */
export function useDeleteBundle() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (bundleId: string) => {
      // TODO: Replace with actual API call
      await new Promise((resolve) => setTimeout(resolve, 500));
      return bundleId;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bundles"] });
    },
  });
}

/**
 * Hook to update share link settings
 */
export function useUpdateShareLink() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      bundleId,
      updates,
    }: {
      bundleId: string;
      updates: Partial<ShareLink>;
    }) => {
      // TODO: Replace with actual API call
      await new Promise((resolve) => setTimeout(resolve, 500));
      return { bundleId, updates };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bundles"] });
    },
  });
}

/**
 * Hook to revoke a share link
 */
export function useRevokeShareLink() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (bundleId: string) => {
      // TODO: Replace with actual API call
      await new Promise((resolve) => setTimeout(resolve, 500));
      return bundleId;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bundles"] });
    },
  });
}
