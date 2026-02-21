/**
 * Composite artifact API client functions.
 *
 * Wraps the /api/v1/composites REST endpoints.  All transport concerns live
 * here; business logic lives in the hook layer.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

function buildUrl(path: string): string {
  return `${API_BASE}/api/${API_VERSION}${path}`;
}

// ---------------------------------------------------------------------------
// TypeScript types matching backend schemas/composites.py
// ---------------------------------------------------------------------------

export type CompositeType = 'plugin' | 'stack' | 'suite';

/** Lightweight child artifact summary embedded in MembershipResponse. */
export interface ChildArtifactSummary {
  id: string;
  uuid: string;
  name: string;
  type: string;
}

/** A single membership edge between a composite and a child artifact. */
export interface MembershipResponse {
  collection_id: string;
  composite_id: string;
  child_artifact_uuid: string;
  relationship_type: string;
  pinned_version_hash: string | null;
  position: number | null;
  created_at: string;
  child_artifact: ChildArtifactSummary | null;
}

/** Full composite artifact with memberships. */
export interface CompositeResponse {
  id: string;
  collection_id: string;
  composite_type: CompositeType;
  display_name: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
  memberships: MembershipResponse[];
  member_count: number;
}

/** Paginated list of composites. */
export interface CompositeListResponse {
  items: CompositeResponse[];
  total: number;
}

// ---------------------------------------------------------------------------
// Request payload types
// ---------------------------------------------------------------------------

export interface CompositeCreatePayload {
  composite_id: string;
  collection_id: string;
  composite_type?: CompositeType;
  display_name?: string | null;
  description?: string | null;
  initial_members?: string[];
  pinned_version_hash?: string | null;
}

export interface CompositeUpdatePayload {
  display_name?: string | null;
  description?: string | null;
  composite_type?: CompositeType | null;
}

export interface MembershipCreatePayload {
  artifact_id: string;
  relationship_type?: string;
  pinned_version_hash?: string | null;
  position?: number | null;
}

export interface MemberPositionUpdate {
  artifact_id: string;
  position: number;
}

export interface MembershipReorderPayload {
  members: MemberPositionUpdate[];
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

/**
 * List composites for a given collection.
 */
export async function fetchComposites(collectionId: string): Promise<CompositeListResponse> {
  const url = buildUrl(`/composites?collection_id=${encodeURIComponent(collectionId)}`);
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch composites: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Fetch a single composite by its type:name id.
 */
export async function fetchComposite(compositeId: string): Promise<CompositeResponse> {
  const url = buildUrl(`/composites/${encodeURIComponent(compositeId)}`);
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch composite '${compositeId}': ${response.statusText}`);
  }
  return response.json();
}

/**
 * Create a new composite artifact.  Returns the created composite (HTTP 201).
 */
export async function createComposite(payload: CompositeCreatePayload): Promise<CompositeResponse> {
  const response = await fetch(buildUrl('/composites'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await extractErrorDetail(response);
    throw new Error(detail ?? `Failed to create composite: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Update mutable fields of an existing composite (display_name, description, composite_type).
 */
export async function updateComposite(
  compositeId: string,
  payload: CompositeUpdatePayload
): Promise<CompositeResponse> {
  const response = await fetch(buildUrl(`/composites/${encodeURIComponent(compositeId)}`), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await extractErrorDetail(response);
    throw new Error(detail ?? `Failed to update composite: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Delete a composite.  Set cascadeDeleteChildren=true to also remove child
 * Artifact rows (not just the membership edges).
 */
export async function deleteComposite(
  compositeId: string,
  cascadeDeleteChildren = false
): Promise<void> {
  const params = cascadeDeleteChildren ? '?cascade_delete_children=true' : '';
  const response = await fetch(
    buildUrl(`/composites/${encodeURIComponent(compositeId)}${params}`),
    { method: 'DELETE' }
  );
  if (!response.ok) {
    const detail = await extractErrorDetail(response);
    throw new Error(detail ?? `Failed to delete composite: ${response.statusText}`);
  }
}

/**
 * Add a child artifact (by type:name id) to a composite.
 */
export async function addCompositeMember(
  compositeId: string,
  collectionId: string,
  payload: MembershipCreatePayload
): Promise<MembershipResponse> {
  const url = buildUrl(
    `/composites/${encodeURIComponent(compositeId)}/members?collection_id=${encodeURIComponent(collectionId)}`
  );
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await extractErrorDetail(response);
    throw new Error(detail ?? `Failed to add member: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Remove a child artifact membership by its stable UUID.
 */
export async function removeCompositeMember(
  compositeId: string,
  memberUuid: string
): Promise<void> {
  const response = await fetch(
    buildUrl(
      `/composites/${encodeURIComponent(compositeId)}/members/${encodeURIComponent(memberUuid)}`
    ),
    { method: 'DELETE' }
  );
  if (!response.ok) {
    const detail = await extractErrorDetail(response);
    throw new Error(detail ?? `Failed to remove member: ${response.statusText}`);
  }
}

/**
 * Bulk-update the display positions of members within a composite.
 */
export async function reorderCompositeMembers(
  compositeId: string,
  payload: MembershipReorderPayload
): Promise<MembershipResponse[]> {
  const response = await fetch(
    buildUrl(`/composites/${encodeURIComponent(compositeId)}/members`),
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }
  );
  if (!response.ok) {
    const detail = await extractErrorDetail(response);
    throw new Error(detail ?? `Failed to reorder members: ${response.statusText}`);
  }
  return response.json();
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function extractErrorDetail(response: Response): Promise<string | null> {
  try {
    const body = await response.json();
    return typeof body.detail === 'string' ? body.detail : null;
  } catch {
    return null;
  }
}
