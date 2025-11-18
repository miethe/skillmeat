/**
 * React Query hooks for bundle management
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type {
  BundleListItem,
  BundleAnalytics,
  ShareLink,
} from "@/types/bundle";
import { apiConfig, apiRequest } from "@/lib/api";

const USE_MOCKS = apiConfig.useMocks;

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
      try {
        const params = new URLSearchParams();
        if (filter && filter !== "all") {
          params.set("filter", filter);
        }

        const response = await apiRequest<{ items: BundleListItem[] }>(
          `/bundles${params.toString() ? `?${params.toString()}` : ""}`
        );

        return response.items || [];
      } catch (error) {
        if (USE_MOCKS) {
          console.warn("[bundles] API failed, falling back to mock data", error);
          let bundles = generateMockBundles();

          if (filter === "created") {
            bundles = bundles.filter((b) => !b.isImported);
          } else if (filter === "imported") {
            bundles = bundles.filter((b) => b.isImported);
          }

          return bundles;
        }
        throw error;
      }
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

      try {
        const analytics = await apiRequest<BundleAnalytics>(
          `/bundles/${bundleId}/analytics`
        );
        return analytics;
      } catch (error) {
        if (USE_MOCKS) {
          console.warn("[bundles] Analytics API failed, falling back to mock data", error);
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
        }
        throw error;
      }
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
      try {
        await apiRequest<void>(`/bundles/${bundleId}`, {
          method: "DELETE",
        });
        return bundleId;
      } catch (error) {
        if (USE_MOCKS) {
          console.warn("[bundles] Delete API failed, falling back to mock", error);
          return bundleId;
        }
        throw error;
      }
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
      try {
        const response = await apiRequest<ShareLink>(`/bundles/${bundleId}/share`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(updates),
        });
        return { bundleId, updates: response };
      } catch (error) {
        if (USE_MOCKS) {
          console.warn("[bundles] Update share link API failed, falling back to mock", error);
          return { bundleId, updates };
        }
        throw error;
      }
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
      try {
        await apiRequest<void>(`/bundles/${bundleId}/share`, {
          method: "DELETE",
        });
        return bundleId;
      } catch (error) {
        if (USE_MOCKS) {
          console.warn("[bundles] Revoke share link API failed, falling back to mock", error);
          return bundleId;
        }
        throw error;
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bundles"] });
    },
  });
}
