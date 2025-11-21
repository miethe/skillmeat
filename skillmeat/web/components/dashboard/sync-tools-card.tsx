"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useCreateSyncJob, useSyncJobStatus } from "@/hooks/useSyncJobs";
import { useArtifactVersions } from "@/hooks/useArtifactVersions";
import { useArtifactDiff } from "@/hooks/useArtifactDiff";
import { toast } from "sonner";

export function SyncToolsCard() {
  const [artifactId, setArtifactId] = useState("");
  const [collection, setCollection] = useState("default");
  const [projectPath, setProjectPath] = useState("");
  const [diffPair, setDiffPair] = useState<"collection-project" | "project-collection">("collection-project");
  const [jobId, setJobId] = useState<string | null>(null);
  const [patchUrl, setPatchUrl] = useState<string | null>(null);
  const [resolveStrategy, setResolveStrategy] = useState<"ours" | "theirs">("ours");

  const createJob = useCreateSyncJob();
  const jobStatus = useSyncJobStatus(jobId);
  const versions = useArtifactVersions(artifactId || null, {
    collection,
    projectPath: projectPath || undefined,
  });
  const diffMutation = useArtifactDiff();

  const lhs = diffPair === "collection-project" ? "collection" : "project";
  const rhs = diffPair === "collection-project" ? "project" : "collection";

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sync Ops</CardTitle>
        <CardDescription>Start jobs, view versions, fetch diffs, export patch.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 md:grid-cols-3">
          <div className="space-y-2">
            <label className="text-sm font-medium">Artifact ID (type:name)</label>
            <Input
              placeholder="skill:pdf-processor"
              value={artifactId}
              onChange={(e) => setArtifactId(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Collection</label>
            <Input value={collection} onChange={(e) => setCollection(e.target.value)} />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Project Path</label>
            <Input
              placeholder="/path/to/project"
              value={projectPath}
              onChange={(e) => setProjectPath(e.target.value)}
            />
          </div>
        </div>

        <Separator />

        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-medium">Create Sync Job</span>
            </div>
            <Select
              defaultValue="collection_to_project"
              onValueChange={(v) =>
                createJob.mutateAsync({
                  direction: v as any,
                  artifacts: artifactId ? [artifactId.split(":")[1]] : undefined,
                  artifactType: artifactId.includes(":") ? artifactId.split(":")[0] : undefined,
                  projectPath: projectPath || undefined,
                  collection: collection || undefined,
                }).then((res) => setJobId(res.job_id))
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Pick direction" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="upstream_to_collection">Upstream → Collection</SelectItem>
                <SelectItem value="collection_to_project">Collection → Project</SelectItem>
                <SelectItem value="project_to_collection">Project → Collection</SelectItem>
              </SelectContent>
            </Select>
            {jobId ? (
              <div className="text-sm text-muted-foreground">
                Job {jobId} ({jobStatus.data?.state || "pending"})
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">Submit to start job</div>
            )}
          </div>

          <div className="space-y-2">
            <div className="font-medium">Job Status</div>
            <Input
              placeholder="Job ID"
              value={jobId || ""}
              onChange={(e) => setJobId(e.target.value || null)}
            />
            {jobStatus.data && (
              <div className="text-sm text-muted-foreground space-y-1">
                <div>State: {jobStatus.data.state}</div>
                <div>Progress: {(jobStatus.data.pct_complete * 100).toFixed(0)}%</div>
                {jobStatus.data.log_excerpt && <div>Log: {jobStatus.data.log_excerpt}</div>}
                {jobStatus.data.unresolved_files?.length ? (
                  <div>Unresolved: {jobStatus.data.unresolved_files.length}</div>
                ) : null}
              </div>
            )}
          </div>
        </div>

        <Separator />

        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <div className="font-medium">Versions</div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => versions.refetch()}
              disabled={!artifactId}
            >
              Refresh Versions
            </Button>
            <div className="text-sm text-muted-foreground space-y-1">
              {versions.data ? (
                <>
                  <div>Collection: {versions.data.collection.hash}</div>
                  <div>Project: {versions.data.project.hash || "n/a"}</div>
                  <div>Status: {versions.data.project.sync_status || versions.data.collection.sync_status}</div>
                </>
              ) : (
                <div>Enter artifact details to fetch.</div>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <div className="font-medium">Diff</div>
            <Select value={diffPair} onValueChange={(v) => setDiffPair(v as any)}>
              <SelectTrigger>
                <SelectValue placeholder="Pick diff pair" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="collection-project">Collection ↔ Project</SelectItem>
                <SelectItem value="project-collection">Project ↔ Collection</SelectItem>
              </SelectContent>
            </Select>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                if (!artifactId) {
                  toast.error("Artifact ID required");
                  return;
                }
                diffMutation.mutate({
                  artifactId,
                  lhs,
                  rhs,
                  collection: collection || undefined,
                  projectPath: projectPath || undefined,
                });
              }}
            >
              Fetch Diff
            </Button>
            {diffMutation.data && (
              <div className="text-sm text-muted-foreground space-y-1">
                <div>
                  Files changed: {diffMutation.data.files_added + diffMutation.data.files_removed + diffMutation.data.files_modified}
                </div>
                {diffMutation.data.truncated && (
                  <div>Diff truncated. Download: {diffMutation.data.download_path}</div>
                )}
              </div>
            )}
          </div>

          <div className="space-y-2">
            <div className="font-medium">Patch Export (Project → Upstream)</div>
            <Button
              variant="outline"
              size="sm"
              onClick={async () => {
                if (!artifactId || !projectPath) {
                  toast.error("Artifact ID and project path required");
                  return;
                }
                const [artifactType, artifactName] = artifactId.split(":");
                try {
                  const res = await fetch("/api/v1/sync/patch", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      artifact_name: artifactName,
                      artifact_type: artifactType,
                      project_path: projectPath,
                      collection,
                    }),
                  });
                  if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    throw new Error(data.detail || "Failed to export patch");
                  }
                  const data = await res.json();
                  setPatchUrl(data.download_path || null);
                  toast.success("Patch ready", { description: data.download_path });
                } catch (err: any) {
                  toast.error("Patch export failed", { description: err.message });
                }
              }}
            >
              Generate Patch
            </Button>
            {patchUrl && (
              <div className="text-sm text-muted-foreground">
                Download: <span className="font-medium break-all">{patchUrl}</span>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <div className="font-medium">Resolve Conflicts</div>
            <div className="grid grid-cols-2 gap-2">
              <Button
                variant={resolveStrategy === "ours" ? "default" : "outline"}
                onClick={() => setResolveStrategy("ours")}
              >
                Use Ours (Collection)
              </Button>
              <Button
                variant={resolveStrategy === "theirs" ? "default" : "outline"}
                onClick={() => setResolveStrategy("theirs")}
              >
                Use Theirs (Project)
              </Button>
            </div>
            <Button
              size="sm"
              onClick={async () => {
                if (!artifactId || !projectPath) {
                  toast.error("Artifact ID and project path required");
                  return;
                }
                const [artifactType, artifactName] = artifactId.split(":");
                try {
                  const res = await createJob.mutateAsync({
                    direction: "resolve",
                    artifacts: [artifactName],
                    artifactType,
                    projectPath,
                    collection,
                    resolution: resolveStrategy,
                    strategy: resolveStrategy,
                  });
                  setJobId(res.job_id);
                } catch (err: any) {
                  toast.error("Failed to queue resolve", { description: err.message });
                }
              }}
            >
              Apply Resolution
            </Button>
            {jobStatus.data?.unresolved_files?.length ? (
              <div className="text-sm text-muted-foreground space-y-1">
                <div className="font-semibold">Unresolved Files</div>
                <ul className="list-disc list-inside space-y-1">
                  {jobStatus.data.unresolved_files.map((f) => (
                    <li key={f} className="break-all">{f}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
