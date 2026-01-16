/**
 * Group API service functions
 */
import type {
  Group,
  GroupWithArtifacts,
  CreateGroupRequest,
  UpdateGroupRequest,
  GroupArtifact,
} from '@/types/groups';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

/**
 * Build API URL with versioned path
 */
function buildUrl(path: string): string {
  return `${API_BASE}/api/${API_VERSION}${path}`;
}

/**
 * Fetch groups for a collection
 */
export async function fetchGroups(collectionId: string): Promise<Group[]> {
  const response = await fetch(buildUrl(`/groups?collection_id=${collectionId}`));
  if (!response.ok) {
    throw new Error(`Failed to fetch groups: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Fetch single group by ID
 */
export async function fetchGroup(id: string): Promise<Group> {
  const response = await fetch(buildUrl(`/groups/${id}`));
  if (!response.ok) {
    throw new Error(`Failed to fetch group: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Create new group
 */
export async function createGroup(data: CreateGroupRequest): Promise<Group> {
  const response = await fetch(buildUrl('/groups'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error(`Failed to create group: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Update existing group
 */
export async function updateGroup(id: string, data: UpdateGroupRequest): Promise<Group> {
  const response = await fetch(buildUrl(`/groups/${id}`), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error(`Failed to update group: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Delete group
 */
export async function deleteGroup(id: string): Promise<void> {
  const response = await fetch(buildUrl(`/groups/${id}`), {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`Failed to delete group: ${response.statusText}`);
  }
}

/**
 * Add artifact(s) to group
 * @param groupId - Group ID
 * @param artifactIds - Artifact ID(s) to add (single string or array)
 * @param position - Optional position in the group (default: append)
 */
export async function addArtifactToGroup(
  groupId: string,
  artifactIds: string | string[],
  position?: number
): Promise<GroupWithArtifacts> {
  const ids = Array.isArray(artifactIds) ? artifactIds : [artifactIds];
  const response = await fetch(buildUrl(`/groups/${groupId}/artifacts`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ artifact_ids: ids, position }),
  });
  if (!response.ok) {
    throw new Error(`Failed to add artifact to group: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Remove artifact from group
 */
export async function removeArtifactFromGroup(groupId: string, artifactId: string): Promise<void> {
  const response = await fetch(buildUrl(`/groups/${groupId}/artifacts/${artifactId}`), {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`Failed to remove artifact from group: ${response.statusText}`);
  }
}

/**
 * Reorder artifacts within group
 * @param groupId - Group ID
 * @param artifactIds - Ordered list of artifact IDs
 */
export async function reorderArtifactsInGroup(
  groupId: string,
  artifactIds: string[]
): Promise<GroupArtifact[]> {
  const response = await fetch(buildUrl(`/groups/${groupId}/artifacts/reorder`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ artifact_ids: artifactIds }),
  });
  if (!response.ok) {
    throw new Error(`Failed to reorder artifacts: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Move artifact to another group
 * @param sourceGroupId - Source group ID
 * @param artifactId - Artifact ID to move
 * @param targetGroupId - Target group ID
 * @param position - Optional position in target group (default: append)
 */
export async function moveArtifactToGroup(
  sourceGroupId: string,
  artifactId: string,
  targetGroupId: string,
  position?: number
): Promise<GroupArtifact> {
  const response = await fetch(buildUrl(`/groups/${sourceGroupId}/artifacts/${artifactId}/move`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_group_id: targetGroupId, position }),
  });
  if (!response.ok) {
    throw new Error(`Failed to move artifact: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Reorder groups within a collection
 * @param collectionId - Collection ID
 * @param groupIds - Ordered list of group IDs
 */
export async function reorderGroups(collectionId: string, groupIds: string[]): Promise<Group[]> {
  const response = await fetch(buildUrl(`/collections/${collectionId}/groups/reorder`), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ group_ids: groupIds }),
  });
  if (!response.ok) {
    throw new Error(`Failed to reorder groups: ${response.statusText}`);
  }
  return response.json();
}
