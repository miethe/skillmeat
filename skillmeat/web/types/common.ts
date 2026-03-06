/**
 * Shared common types used across multiple domains
 */

/**
 * Response shape returned by batch delete endpoints.
 *
 * POST /context-entities/batch/delete
 * POST /workflows/batch/delete
 * POST /project-templates/batch/delete
 */
export interface BatchDeleteResponse {
  results: Array<{ id: string; success: boolean; error?: string }>;
  succeeded: number;
  failed: number;
}
