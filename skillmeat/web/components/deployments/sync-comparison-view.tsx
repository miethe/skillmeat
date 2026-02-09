'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { ArtifactDeploymentInfo } from '@/types/deployments';

export interface SyncComparisonViewProps {
  deploymentsByProfile?: Record<string, ArtifactDeploymentInfo[]>;
}

function shortSha(value?: string): string {
  if (!value) return 'none';
  return value.slice(0, 7);
}

export function SyncComparisonView({ deploymentsByProfile = {} }: SyncComparisonViewProps) {
  const profileIds = Object.keys(deploymentsByProfile);
  if (profileIds.length < 2) {
    return null;
  }

  const artifactMap = new Map<string, Record<string, ArtifactDeploymentInfo | undefined>>();
  for (const [profileId, deployments] of Object.entries(deploymentsByProfile)) {
    for (const deployment of deployments) {
      const key = `${deployment.artifact_type}:${deployment.artifact_name}`;
      const row = artifactMap.get(key) || {};
      row[profileId] = deployment;
      artifactMap.set(key, row);
    }
  }

  const outOfSync = Array.from(artifactMap.entries()).filter(([, row]) => {
    const shas = profileIds.map((profileId) => row[profileId]?.collection_sha || '');
    const nonEmpty = shas.filter(Boolean);
    if (nonEmpty.length !== profileIds.length) return true;
    return new Set(nonEmpty).size > 1;
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Cross-Platform Sync Comparison</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {outOfSync.length === 0 ? (
          <p className="text-sm text-muted-foreground">All compared profiles are in sync.</p>
        ) : (
          outOfSync.map(([artifactId, row]) => (
            <div key={artifactId} className="rounded-md border p-3">
              <div className="mb-2 text-sm font-medium">{artifactId}</div>
              <div className="flex flex-wrap gap-2">
                {profileIds.map((profileId) => {
                  const deployment = row[profileId];
                  return (
                    <Badge key={`${artifactId}-${profileId}`} variant="outline">
                      {profileId}: {shortSha(deployment?.collection_sha)}
                    </Badge>
                  );
                })}
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
