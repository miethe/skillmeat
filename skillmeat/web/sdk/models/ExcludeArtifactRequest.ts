/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Request body for excluding or restoring a catalog entry.
 *
 * Used to mark artifacts as excluded from the catalog (e.g., false positives,
 * documentation files, non-Claude artifacts) or to restore previously excluded
 * entries.
 *
 * When `excluded=True`: Marks the entry as excluded with optional reason.
 * Excluded artifacts are hidden from default catalog views but can be restored.
 *
 * When `excluded=False`: Removes exclusion status and restores entry to default
 * view (status changes to "new" or "imported" depending on history).
 *
 * Both operations are idempotent - calling multiple times succeeds.
 */
export type ExcludeArtifactRequest = {
    /**
     * True to mark as excluded, False to restore
     */
    excluded: boolean;
    /**
     * User-provided reason for exclusion (max 500 chars, optional)
     */
    reason?: (string | null);
};

