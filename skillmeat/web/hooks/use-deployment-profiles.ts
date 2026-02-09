import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createDeploymentProfile,
  deleteDeploymentProfile,
  listDeploymentProfiles,
  updateDeploymentProfile,
} from '@/lib/api/deployment-profiles';
import { listDeployments } from '@/lib/api/deployments';
import { useProject } from './useProjects';
import type {
  ArtifactDeploymentInfo,
  CreateDeploymentProfileRequest,
  DeploymentStatus,
  DeploymentProfile,
  ProfileDeploymentStatus,
  UpdateDeploymentProfileRequest,
} from '@/types/deployments';

export const deploymentProfileKeys = {
  all: ['deployment-profiles'] as const,
  list: (projectId?: string) => [...deploymentProfileKeys.all, projectId] as const,
  status: (projectId?: string, artifactId?: string) =>
    [...deploymentProfileKeys.all, 'status', projectId, artifactId] as const,
};

function artifactKey(deployment: ArtifactDeploymentInfo): string {
  return `${deployment.artifact_type}:${deployment.artifact_name}`;
}

function toProfileStatus(
  deployment: ArtifactDeploymentInfo | undefined,
  profileId: string
): ProfileDeploymentStatus {
  if (!deployment) {
    return {
      profile_id: profileId,
      sync_status: 'missing',
    };
  }
  return {
    profile_id: profileId,
    platform: deployment.platform,
    sync_status: deployment.sync_status || 'unknown',
    deployed_at: deployment.deployed_at,
    collection_sha: deployment.collection_sha,
    deployment,
  };
}

export function useDeploymentProfiles(projectId: string | undefined) {
  return useQuery<DeploymentProfile[], Error>({
    queryKey: deploymentProfileKeys.list(projectId),
    queryFn: () => listDeploymentProfiles(projectId!),
    enabled: Boolean(projectId),
    staleTime: 60 * 1000,
  });
}

export function useCreateDeploymentProfile(projectId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateDeploymentProfileRequest) =>
      createDeploymentProfile(projectId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: deploymentProfileKeys.list(projectId) });
    },
  });
}

export function useUpdateDeploymentProfile(projectId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ profileId, data }: { profileId: string; data: UpdateDeploymentProfileRequest }) =>
      updateDeploymentProfile(projectId!, profileId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: deploymentProfileKeys.list(projectId) });
    },
  });
}

export function useDeleteDeploymentProfile(projectId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (profileId: string) => deleteDeploymentProfile(projectId!, profileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: deploymentProfileKeys.list(projectId) });
    },
  });
}

export function useDeploymentStatus(artifactId: string | undefined, projectId: string | undefined) {
  const projectQuery = useProject(projectId || '');

  const statusQuery = useQuery<DeploymentStatus | null, Error>({
    queryKey: deploymentProfileKeys.status(projectId, artifactId),
    enabled: Boolean(artifactId && projectQuery.data?.path),
    queryFn: async () => {
      const projectPath = projectQuery.data?.path;
      if (!projectPath || !artifactId) {
        return null;
      }

      const listResponse = await listDeployments(projectPath);
      const byProfile: Record<string, ProfileDeploymentStatus> = {};
      const grouped = listResponse.deployments_by_profile || {};

      for (const [profileId, deployments] of Object.entries(grouped)) {
        const matched = deployments.find((d) => artifactKey(d) === artifactId);
        byProfile[profileId] = toProfileStatus(matched, profileId);
      }

      if (Object.keys(byProfile).length === 0) {
        // Backward-compatible fallback for payloads without deployments_by_profile.
        for (const deployment of listResponse.deployments) {
          if (artifactKey(deployment) !== artifactId) continue;
          const profileId = deployment.deployment_profile_id || 'claude_code';
          byProfile[profileId] = toProfileStatus(deployment, profileId);
        }
      }

      const syncStates = Object.values(byProfile).map((state) => state.collection_sha || '');
      const distinctSyncStates = new Set(syncStates.filter(Boolean));

      return {
        artifact_id: artifactId,
        project_path: projectPath,
        by_profile: byProfile,
        is_synced_across_profiles: distinctSyncStates.size <= 1,
      };
    },
  });

  return {
    data: statusQuery.data,
    isLoading: projectQuery.isLoading || statusQuery.isLoading,
    error: statusQuery.error || projectQuery.error,
    refetch: statusQuery.refetch,
  };
}

export function useProfileSelector(initialProfileId?: string) {
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(
    initialProfileId || null
  );
  const [allProfiles, setAllProfiles] = useState(false);

  const deploymentParams = useMemo(
    () =>
      allProfiles
        ? { all_profiles: true, deployment_profile_id: undefined }
        : { all_profiles: false, deployment_profile_id: selectedProfileId || undefined },
    [allProfiles, selectedProfileId]
  );

  return {
    selectedProfileId,
    setSelectedProfileId,
    allProfiles,
    setAllProfiles,
    deploymentParams,
  };
}
