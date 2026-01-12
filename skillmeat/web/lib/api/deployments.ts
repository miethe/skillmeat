/**
 * Deployment API service functions
 *
 * Provides functions for deploying artifacts to projects and managing deployments
 */
import type {
  ArtifactDeployRequest,
  ArtifactUndeployRequest,
  ArtifactDeploymentResponse,
  ArtifactUndeployResponse,
  ArtifactDeploymentListResponse,
  ArtifactDeploymentInfo,
  ProjectDeploymentRemovalRequest,
  ProjectDeploymentRemovalResponse,
} from '@/types/deployments';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

/**
 * Build API URL with versioned path
 */
function buildUrl(path: string): string {
  return `${API_BASE}/api/${API_VERSION}${path}`;
}

/**
 * Deploy an artifact to a project
 *
 * Copies an artifact from the collection to the project's .claude directory
 *
 * @param data - Deployment request details
 * @returns Deployment response with details
 * @throws Error if deployment fails
 */
export async function deployArtifact(
  data: ArtifactDeployRequest
): Promise<ArtifactDeploymentResponse> {
  const response = await fetch(buildUrl('/deploy'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => response.statusText);
    throw new Error(`Failed to deploy artifact: ${errorText}`);
  }

  return response.json();
}

/**
 * Undeploy (remove) an artifact from a project
 *
 * Removes the artifact from the project's .claude directory
 *
 * @param data - Undeploy request details
 * @returns Undeploy response with confirmation
 * @throws Error if undeploy fails
 */
export async function undeployArtifact(
  data: ArtifactUndeployRequest
): Promise<ArtifactUndeployResponse> {
  const response = await fetch(buildUrl('/deploy/undeploy'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => response.statusText);
    throw new Error(`Failed to undeploy artifact: ${errorText}`);
  }

  return response.json();
}

/**
 * List all deployed artifacts in a project
 *
 * Retrieves deployment metadata for all artifacts in the project's .claude directory
 *
 * @param projectPath - Optional project path (uses CWD if not specified)
 * @returns List of deployments with sync status
 * @throws Error if list operation fails
 */
export async function listDeployments(
  projectPath?: string
): Promise<ArtifactDeploymentListResponse> {
  const params = new URLSearchParams();
  if (projectPath) {
    params.append('project_path', projectPath);
  }

  const url = buildUrl(`/deploy${params.toString() ? `?${params.toString()}` : ''}`);
  const response = await fetch(url);

  if (!response.ok) {
    const errorText = await response.text().catch(() => response.statusText);
    throw new Error(`Failed to list deployments: ${errorText}`);
  }

  return response.json();
}

/**
 * Get deployment summary statistics
 *
 * Calculates summary stats from deployment list response
 *
 * @param projectPath - Optional project path
 * @returns Deployment summary with counts by type and status
 */
export async function getDeploymentSummary(
  projectPath?: string
): Promise<DeploymentSummary> {
  const listResponse = await listDeployments(projectPath);
  const { deployments } = listResponse;

  // Count by artifact type
  const byType: Record<string, number> = {};
  deployments.forEach((deployment) => {
    const type = deployment.artifact_type;
    byType[type] = (byType[type] || 0) + 1;
  });

  // Count by sync status
  const byStatus = {
    synced: 0,
    modified: 0,
    outdated: 0,
    unknown: 0,
  };

  deployments.forEach((deployment) => {
    const status = deployment.sync_status || 'unknown';
    if (status in byStatus) {
      byStatus[status as keyof typeof byStatus]++;
    } else {
      byStatus.unknown++;
    }
  });

  // Find most recent deployment
  const lastUpdated = deployments.length > 0
    ? deployments.reduce((latest, current) => {
        return new Date(current.deployed_at) > new Date(latest.deployed_at)
          ? current
          : latest;
      }).deployed_at
    : new Date().toISOString();

  return {
    total: listResponse.total,
    byType,
    byStatus,
    lastUpdated,
  };
}

/**
 * Deployment summary statistics
 */
export interface DeploymentSummary {
  /** Total number of deployments */
  total: number;
  /** Deployments grouped by artifact type */
  byType: Record<string, number>;
  /** Deployments grouped by sync status */
  byStatus: {
    synced: number;
    modified: number;
    outdated: number;
    unknown: number;
  };
  /** Timestamp of most recent deployment (ISO 8601) */
  lastUpdated: string;
}

/**
 * Parameters for querying deployments
 */
export interface DeploymentQueryParams {
  /** Project path to query */
  projectPath?: string;
  /** Filter by artifact type */
  artifactType?: string;
  /** Filter by sync status */
  syncStatus?: string;
}

/**
 * Get deployments with optional filtering
 *
 * @param params - Query parameters
 * @returns Filtered deployment list
 */
export async function getDeployments(
  params?: DeploymentQueryParams
): Promise<ArtifactDeploymentInfo[]> {
  const listResponse = await listDeployments(params?.projectPath);
  let deployments = listResponse.deployments;

  // Apply client-side filtering if needed
  if (params?.artifactType) {
    deployments = deployments.filter(
      (d) => d.artifact_type === params.artifactType
    );
  }

  if (params?.syncStatus) {
    deployments = deployments.filter(
      (d) => d.sync_status === params.syncStatus
    );
  }

  return deployments;
}

/**
 * Remove a deployed artifact from a specific project
 *
 * This function removes an artifact deployment from a specific project.
 * Unlike the general undeployArtifact function, this targets a specific project
 * and supports optional filesystem file removal.
 *
 * @param projectId - Base64-encoded project path
 * @param artifactName - Name of the artifact to remove
 * @param artifactType - Type of the artifact to remove
 * @param removeFiles - Whether to remove files from filesystem (default: true)
 * @returns Removal response with confirmation
 * @throws Error if removal fails
 */
export async function removeProjectDeployment(
  projectId: string,
  artifactName: string,
  artifactType: string,
  removeFiles: boolean = true
): Promise<ProjectDeploymentRemovalResponse> {
  const params = new URLSearchParams({
    artifact_type: artifactType,
    remove_files: String(removeFiles),
  });

  const url = buildUrl(`/projects/${projectId}/deployments/${artifactName}?${params.toString()}`);
  const response = await fetch(url, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => response.statusText);
    throw new Error(`Failed to remove project deployment: ${errorText}`);
  }

  return response.json();
}
