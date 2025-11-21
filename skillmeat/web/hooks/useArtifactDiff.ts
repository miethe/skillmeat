import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";

export interface ArtifactDiffRequest {
  artifactId: string;
  lhs: "collection" | "project";
  rhs: "collection" | "project";
  collection?: string;
  projectPath?: string;
}

export interface ArtifactDiffResponse {
  artifact_name: string;
  artifact_type: string;
  lhs: string;
  rhs: string;
  files_added: number;
  files_removed: number;
  files_modified: number;
  total_lines_added: number;
  total_lines_removed: number;
  truncated: boolean;
  download_path?: string;
  files: {
    path: string;
    status: string;
    lines_added: number;
    lines_removed: number;
    unified_diff?: string | null;
  }[];
}

export function useArtifactDiff() {
  return useMutation({
    mutationFn: async (req: ArtifactDiffRequest): Promise<ArtifactDiffResponse> => {
      const params = new URLSearchParams({
        lhs: req.lhs,
        rhs: req.rhs,
      });
      if (req.collection) params.append("collection", req.collection);
      if (req.projectPath) params.append("project_path", req.projectPath);
      const res = await fetch(`/api/v1/artifacts/${req.artifactId}/diff?${params.toString()}`);
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to load diff");
      }
      return res.json();
    },
    onError: (err: any) => {
      toast.error("Failed to fetch diff", { description: err.message });
    },
  });
}
