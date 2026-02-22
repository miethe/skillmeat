import type { Artifact } from '@/types/artifact';

/**
 * Check if an artifact has a valid upstream source for sync operations.
 *
 * Returns true ONLY when ALL conditions are met:
 * 1. origin is 'github' (excludes marketplace, local, etc.)
 * 2. upstream tracking is enabled
 * 3. source string looks like a valid remote path (contains '/', not local)
 *
 * Marketplace artifacts have origin: "marketplace" and will correctly
 * return false, even if their origin_source is "github".
 */
export function hasValidUpstreamSource(entity: Artifact): boolean {
  // Must be a github-origin artifact
  if (entity.origin !== 'github') return false;

  // Must have upstream tracking enabled
  if (!entity.upstream?.enabled) return false;

  // Source string must look like a valid remote source
  const source = entity.source;
  if (!source) return false;
  if (source === 'local' || source === 'unknown') return false;
  if (source.startsWith('local:')) return false;

  return source.includes('/') && !source.startsWith('local');
}

/**
 * Check if an artifact has a displayable source link.
 * Less strict than hasValidUpstreamSource — used for UI display
 * (flow banner, scope tab availability) rather than query gating.
 */
export function hasSourceLink(entity: Artifact): boolean {
  const source = entity.source;
  if (!source) return false;
  if (source === 'local' || source === 'unknown') return false;
  if (source.startsWith('local:')) return false;
  // Has a remote source path (GitHub URL or owner/repo format)
  return source.includes('/');
}
