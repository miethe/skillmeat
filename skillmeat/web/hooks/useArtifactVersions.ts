import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";

export interface TierVersion {
  tier: string;
  hash?: string;
  timestamp?: string;
  source?: string;
  sync_status?: string;
}

export interface ArtifactVersions {
  artifact_name: string;
  artifact_type: string;
  upstream: TierVersion;
  collection: TierVersion;
  project: TierVersion;
}

export function useArtifactVersions(
  artifactId: string | null,
  opts: { collection?: string; projectPath?: string } = {}
) {
  return useQuery<ArtifactVersions>({
    queryKey: ["artifact-versions", artifactId, opts.collection, opts.projectPath],
    enabled: !!artifactId,
    queryFn: async () => {
      const params = new URLSearchParams();
      if (opts.collection) params.append("collection", opts.collection);
      if (opts.projectPath) params.append("project_path", opts.projectPath);
      const res = await fetch(`/api/v1/artifacts/${artifactId}/versions?${params.toString()}`);
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to load versions");
      }
      return res.json();
    },
    onError: (err: any) => {
      toast.error("Failed to load versions", { description: err.message });
    },
  });
}
