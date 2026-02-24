/**
 * Deployment Sets API service functions
 *
 * Covers all 11 endpoints under /api/v1/deployment-sets
 */
import type {
  DeploymentSet,
  DeploymentSetCreate,
  DeploymentSetUpdate,
  DeploymentSetListResponse,
  DeploymentSetListParams,
  DeploymentSetMember,
  DeploymentSetMemberCreate,
  MemberUpdatePosition,
  DeploymentSetResolution,
  BatchDeployRequest,
  BatchDeployResponse,
} from '@/types/deployment-sets';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

/**
 * Build a versioned API URL
 */
function buildUrl(path: string): string {
  return `${API_BASE}/api/${API_VERSION}${path}`;
}

// =============================================================================
// Deployment Set CRUD
// =============================================================================

/**
 * List deployment sets with optional filtering and pagination
 */
export async function fetchDeploymentSets(
  params?: DeploymentSetListParams
): Promise<DeploymentSetListResponse> {
  const searchParams = new URLSearchParams();

  if (params?.name) searchParams.set('name', params.name);
  if (params?.tag) searchParams.set('tag', params.tag);
  if (params?.limit !== undefined) searchParams.set('limit', params.limit.toString());
  if (params?.offset !== undefined) searchParams.set('offset', params.offset.toString());

  const query = searchParams.toString();
  const url = buildUrl(`/deployment-sets${query ? `?${query}` : ''}`);
  const response = await fetch(url);

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch deployment sets: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch a single deployment set by ID
 */
export async function fetchDeploymentSet(id: string): Promise<DeploymentSet> {
  const response = await fetch(buildUrl(`/deployment-sets/${id}`));

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch deployment set: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Create a new deployment set
 */
export async function createDeploymentSet(data: DeploymentSetCreate): Promise<DeploymentSet> {
  const response = await fetch(buildUrl('/deployment-sets'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to create deployment set: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Update an existing deployment set (partial update — only provided fields applied)
 */
export async function updateDeploymentSet(
  id: string,
  data: DeploymentSetUpdate
): Promise<DeploymentSet> {
  const response = await fetch(buildUrl(`/deployment-sets/${id}`), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to update deployment set: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Delete a deployment set (cascade-deletes member rows)
 */
export async function deleteDeploymentSet(id: string): Promise<void> {
  const response = await fetch(buildUrl(`/deployment-sets/${id}`), {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to delete deployment set: ${response.statusText}`);
  }
}

/**
 * Clone a deployment set and all its members.
 * The clone receives a name of "<original name> (copy)".
 */
export async function cloneDeploymentSet(id: string): Promise<DeploymentSet> {
  const response = await fetch(buildUrl(`/deployment-sets/${id}/clone`), {
    method: 'POST',
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to clone deployment set: ${response.statusText}`);
  }

  return response.json();
}

// =============================================================================
// Member Management
// =============================================================================

/**
 * List all members of a deployment set, ordered by position.
 */
export async function fetchDeploymentSetMembers(setId: string): Promise<DeploymentSetMember[]> {
  const response = await fetch(buildUrl(`/deployment-sets/${setId}/members`));

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch members: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Add an artifact, group, or nested deployment set as a member.
 * Exactly one of artifact_uuid, group_id, or nested_set_id must be set.
 */
export async function addDeploymentSetMember(
  setId: string,
  data: DeploymentSetMemberCreate
): Promise<DeploymentSetMember> {
  const response = await fetch(buildUrl(`/deployment-sets/${setId}/members`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to add member to deployment set: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Remove a member from a deployment set
 */
export async function removeDeploymentSetMember(
  setId: string,
  memberId: string
): Promise<void> {
  const response = await fetch(buildUrl(`/deployment-sets/${setId}/members/${memberId}`), {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Failed to remove member from deployment set: ${response.statusText}`
    );
  }
}

/**
 * Update the ordering position of a member within a deployment set
 */
export async function updateDeploymentSetMemberPosition(
  setId: string,
  memberId: string,
  data: MemberUpdatePosition
): Promise<DeploymentSetMember> {
  const response = await fetch(buildUrl(`/deployment-sets/${setId}/members/${memberId}`), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Failed to update member position: ${response.statusText}`
    );
  }

  return response.json();
}

// =============================================================================
// Resolution & Deployment
// =============================================================================

/**
 * Recursively resolve a deployment set into an ordered, deduplicated list of artifacts
 */
export async function resolveDeploymentSet(id: string): Promise<DeploymentSetResolution> {
  const response = await fetch(buildUrl(`/deployment-sets/${id}/resolve`));

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Failed to resolve deployment set: ${response.statusText}`
    );
  }

  return response.json();
}

/**
 * Batch-deploy all artifacts in a deployment set to a target project
 */
export async function batchDeployDeploymentSet(
  id: string,
  data: BatchDeployRequest
): Promise<BatchDeployResponse> {
  const response = await fetch(buildUrl(`/deployment-sets/${id}/deploy`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(
      errorBody.detail || `Failed to batch deploy deployment set: ${response.statusText}`
    );
  }

  return response.json();
}
