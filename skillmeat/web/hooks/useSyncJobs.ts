import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";

type SyncDirection =
  | "upstream_to_collection"
  | "collection_to_project"
  | "project_to_collection"
  | "resolve";

interface CreateJobRequest {
  direction: SyncDirection;
  artifacts?: string[];
  artifactType?: string;
  projectPath?: string;
  collection?: string;
  strategy?: string;
  resolution?: string;
  dryRun?: boolean;
}

interface JobStatus {
  job_id: string;
  direction: string;
  state: string;
  pct_complete: number;
  duration_ms?: number;
  log_excerpt?: string;
  conflicts?: any[];
  artifacts: string[];
  artifact_type?: string;
  project_path?: string;
  collection?: string;
  strategy?: string;
  resolution?: string;
  unresolved_files?: string[];
}

export function useCreateSyncJob() {
  return useMutation({
    mutationFn: async (payload: CreateJobRequest): Promise<JobStatus> => {
      const res = await fetch("/api/v1/sync/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to create job");
      }
      return res.json();
    },
    onSuccess: (data) => {
      toast.success("Sync job created", {
        description: `Job ${data.job_id} (${data.direction})`,
      });
    },
    onError: (err: any) => {
      toast.error("Sync job failed", { description: err.message });
    },
  });
}

export function useSyncJobStatus(jobId: string | null) {
  return useQuery<JobStatus>({
    queryKey: ["sync-job", jobId],
    enabled: !!jobId,
    refetchInterval: 2000,
    queryFn: async () => {
      const res = await fetch(`/api/v1/sync/jobs/${jobId}`);
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to fetch job status");
      }
      return res.json();
    },
  });
}
