/**
 * Source parsing and display utilities for artifact sources.
 *
 * Provides consistent GitHub URL parsing and source display logic
 * shared across card components and detail views.
 */

export interface GitHubSource {
  owner: string;
  repo: string;
  displayName: string;
  url: string;
}

export type SourceDisplay =
  | { type: 'local' }
  | { type: 'github'; displayName: string; url: string }
  | { type: 'unknown' };

/**
 * Parse a source string to extract GitHub owner/repo information.
 *
 * Handles both full GitHub URLs and shorthand path formats:
 * - `https://github.com/owner/repo/tree/main/path` -> owner/repo
 * - `owner/repo/path/to/artifact` -> owner/repo (constructs URL)
 *
 * Returns null if the source is not a valid GitHub reference.
 */
export function parseGitHubSource(source: string): GitHubSource | null {
  if (!source) return null;

  // Full GitHub URL
  if (source.includes('github.com')) {
    try {
      const url = new URL(source.startsWith('http') ? source : `https://${source}`);
      const pathSegments = url.pathname.split('/').filter(Boolean);

      if (pathSegments.length < 2) return null;

      const owner = pathSegments[0];
      const repo = pathSegments[1];

      return {
        owner,
        repo,
        displayName: `${owner}/${repo}`,
        url: source.startsWith('http') ? source : `https://${source}`,
      };
    } catch {
      return null;
    }
  }

  // Shorthand path format: owner/repo/... (at least owner/repo required)
  const segments = source.split('/').filter(Boolean);
  if (segments.length >= 2 && !source.startsWith('local') && source !== 'unknown') {
    const owner = segments[0];
    const repo = segments[1];
    const remainingPath = segments.slice(2).join('/');
    const url = remainingPath
      ? `https://github.com/${owner}/${repo}/tree/main/${remainingPath}`
      : `https://github.com/${owner}/${repo}`;

    return {
      owner,
      repo,
      displayName: `${owner}/${repo}`,
      url,
    };
  }

  return null;
}

/**
 * Determine how to display an artifact's source based on its origin and source fields.
 *
 * Priority:
 * 1. Explicit local indicators (origin='local', source starts with 'local:', source='local')
 * 2. GitHub detection (origin='github', or source contains github.com, or parseable path)
 * 3. Fallback to unknown
 */
export function getSourceDisplay(artifact: {
  source?: string;
  origin?: string;
}): SourceDisplay {
  const { source, origin } = artifact;

  // Local detection
  if (origin === 'local' || source === 'local' || source?.startsWith('local:')) {
    return { type: 'local' };
  }

  // GitHub detection
  if (source) {
    const parsed = parseGitHubSource(source);
    if (parsed) {
      return { type: 'github', displayName: parsed.displayName, url: parsed.url };
    }
  }

  // Origin hint without parseable source
  if (origin === 'github') {
    return {
      type: 'github',
      displayName: source || 'GitHub',
      url: source && source.startsWith('http') ? source : '#',
    };
  }

  return { type: 'unknown' };
}
