'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, CircleOff } from 'lucide-react';
import type { ArtifactDeploymentInfo } from '@/types/deployments';
import { PlatformBadge } from '@/components/platform-badge';

export interface DeploymentStatusProfileViewProps {
  deploymentsByProfile?: Record<string, ArtifactDeploymentInfo[]>;
}

export function DeploymentStatusProfileView({
  deploymentsByProfile = {},
}: DeploymentStatusProfileViewProps) {
  const profileIds = Object.keys(deploymentsByProfile);
  if (profileIds.length === 0) {
    return null;
  }

  const artifactRows = new Map<
    string,
    {
      artifactName: string;
      artifactType: string;
      byProfile: Record<string, ArtifactDeploymentInfo | undefined>;
    }
  >();

  for (const [profileId, deployments] of Object.entries(deploymentsByProfile)) {
    for (const deployment of deployments) {
      const key = `${deployment.artifact_type}:${deployment.artifact_name}`;
      const row = artifactRows.get(key) || {
        artifactName: deployment.artifact_name,
        artifactType: deployment.artifact_type,
        byProfile: {},
      };
      row.byProfile[profileId] = deployment;
      artifactRows.set(key, row);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Deployment Status by Profile</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {Array.from(artifactRows.values()).map((row) => (
          <div key={`${row.artifactType}:${row.artifactName}`} className="rounded-md border p-3">
            <div className="mb-2 flex items-center justify-between">
              <div className="font-medium">
                {row.artifactName}
                <span className="ml-2 text-xs text-muted-foreground">({row.artifactType})</span>
              </div>
            </div>
            <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
              {profileIds.map((profileId) => {
                const deployment = row.byProfile[profileId];
                return (
                  <div
                    key={`${row.artifactName}-${profileId}`}
                    className="flex items-center justify-between rounded border bg-muted/20 px-2 py-1.5"
                  >
                    <div className="flex items-center gap-2">
                      {deployment ? (
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                      ) : (
                        <CircleOff className="h-4 w-4 text-muted-foreground" />
                      )}
                      <span className="text-xs font-medium">{profileId}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      {deployment?.platform && <PlatformBadge platform={deployment.platform} compact />}
                      <Badge variant="outline" className="text-[10px]">
                        {deployment?.sync_status || 'missing'}
                      </Badge>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
