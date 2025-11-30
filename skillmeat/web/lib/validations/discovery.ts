/**
 * Zod validation schemas for discovery feature
 *
 * Client-side validation for artifact discovery, bulk import,
 * GitHub metadata fetch, and parameter update operations.
 */

import { z } from 'zod';

/**
 * GitHub source validation
 * Matches formats:
 * - user/repo/path[@version]
 * - https://github.com/user/repo/path
 */
export const githubSourceSchema = z
  .string()
  .min(1, 'Source is required')
  .refine(
    (val) => {
      // Standard format: user/repo/path or user/repo/path@version
      const standardFormat = /^[\w.-]+\/[\w.-]+\/[\w./-]+(@[\w.-]+)?$/;
      // HTTPS URL format
      const httpsFormat = /^https:\/\/github\.com\/.+/;
      return standardFormat.test(val) || httpsFormat.test(val);
    },
    'Invalid GitHub source format. Use: user/repo/path or https://github.com/...'
  );

/**
 * Version validation
 * Accepts:
 * - "latest"
 * - "@v1.0.0" or "@1.0.0"
 * - Semver format: "1.0.0" or "v1.0.0"
 * - Omitted (optional)
 */
export const versionSchema = z
  .string()
  .optional()
  .refine(
    (val) =>
      !val ||
      val === 'latest' ||
      val.startsWith('@') ||
      /^v?\d+\.\d+/.test(val),
    'Version must be "latest", "@v1.0.0", or a valid semver'
  );

/**
 * Scope validation
 * Only "user" (global) or "local" (project-specific)
 */
export const scopeSchema = z.enum(['user', 'local'], {
  errorMap: () => ({ message: 'Scope must be "user" or "local"' }),
});

/**
 * Tags validation
 * Array of non-empty strings
 */
export const tagsSchema = z
  .array(z.string().min(1, 'Tags cannot be empty'))
  .optional();

/**
 * Artifact type validation
 * Supports all current artifact types in SkillMeat
 */
export const artifactTypeSchema = z.enum(
  ['skill', 'command', 'agent', 'hook', 'mcp'],
  {
    errorMap: () => ({ message: 'Invalid artifact type' }),
  }
);

/**
 * Artifact parameters schema
 * Used for updating existing artifacts
 */
export const artifactParametersSchema = z.object({
  source: githubSourceSchema.optional(),
  version: versionSchema,
  scope: scopeSchema.optional(),
  tags: tagsSchema,
  aliases: z.array(z.string()).optional(),
});

/**
 * Single artifact for bulk import
 * All fields except source are optional (can be auto-populated)
 */
export const bulkImportArtifactSchema = z.object({
  source: githubSourceSchema,
  artifact_type: artifactTypeSchema,
  name: z.string().optional(),
  description: z.string().optional(),
  tags: tagsSchema,
  scope: scopeSchema.optional(),
});

/**
 * Bulk import request schema
 * Requires at least one artifact
 */
export const bulkImportRequestSchema = z.object({
  artifacts: z
    .array(bulkImportArtifactSchema)
    .min(1, 'At least one artifact required'),
  auto_resolve_conflicts: z.boolean().optional(),
});

// Type exports from schemas
export type ArtifactParametersInput = z.infer<typeof artifactParametersSchema>;
export type BulkImportArtifactInput = z.infer<typeof bulkImportArtifactSchema>;
export type BulkImportRequestInput = z.infer<typeof bulkImportRequestSchema>;

/**
 * Validate a GitHub source string
 * @param source - GitHub source string to validate
 * @returns Validation result with success status and error message
 */
export function validateGitHubSource(source: string): {
  success: boolean;
  error?: string;
} {
  const result = githubSourceSchema.safeParse(source);
  if (result.success) {
    return { success: true };
  }
  return {
    success: false,
    error: result.error.errors[0]?.message,
  };
}

/**
 * Validate artifact parameters
 * @param params - Artifact parameters to validate
 * @returns Validation result with success status and errors
 */
export function validateArtifactParameters(params: unknown): {
  success: boolean;
  data?: ArtifactParametersInput;
  errors?: Record<string, string>;
} {
  const result = artifactParametersSchema.safeParse(params);

  if (result.success) {
    return { success: true, data: result.data };
  }

  const errors: Record<string, string> = {};
  result.error.errors.forEach((err) => {
    const path = err.path.join('.');
    errors[path] = err.message;
  });

  return { success: false, errors };
}

/**
 * Validate bulk import request
 * @param request - Bulk import request to validate
 * @returns Validation result with success status and errors
 */
export function validateBulkImportRequest(request: unknown): {
  success: boolean;
  data?: BulkImportRequestInput;
  errors?: Record<string, string>;
} {
  const result = bulkImportRequestSchema.safeParse(request);

  if (result.success) {
    return { success: true, data: result.data };
  }

  const errors: Record<string, string> = {};
  result.error.errors.forEach((err) => {
    const path = err.path.join('.');
    errors[path] = err.message;
  });

  return { success: false, errors };
}
