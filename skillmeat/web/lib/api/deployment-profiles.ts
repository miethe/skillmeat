/**
 * Deployment profile API service functions
 */
import { apiRequest } from '@/lib/api';
import type {
  CreateDeploymentProfileRequest,
  DeploymentProfile,
  UpdateDeploymentProfileRequest,
} from '@/types/deployments';

export async function listDeploymentProfiles(projectId: string): Promise<DeploymentProfile[]> {
  return apiRequest<DeploymentProfile[]>(`/projects/${projectId}/profiles`);
}

export async function createDeploymentProfile(
  projectId: string,
  data: CreateDeploymentProfileRequest
): Promise<DeploymentProfile> {
  return apiRequest<DeploymentProfile>(`/projects/${projectId}/profiles`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateDeploymentProfile(
  projectId: string,
  profileId: string,
  data: UpdateDeploymentProfileRequest
): Promise<DeploymentProfile> {
  return apiRequest<DeploymentProfile>(`/projects/${projectId}/profiles/${profileId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteDeploymentProfile(
  projectId: string,
  profileId: string
): Promise<void> {
  await apiRequest<void>(`/projects/${projectId}/profiles/${profileId}`, {
    method: 'DELETE',
  });
}
