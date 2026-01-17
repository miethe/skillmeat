/**
 * Settings API service functions
 *
 * Provides functions for managing application settings including GitHub PAT
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

/**
 * Build API URL with versioned path
 */
function buildUrl(path: string): string {
  return `${API_BASE}/api/${API_VERSION}${path}`;
}

/**
 * GitHub token status response
 */
export interface GitHubTokenStatus {
  is_set: boolean;
  masked_token?: string;
  username?: string;
}

/**
 * GitHub token validation response
 */
export interface GitHubTokenValidation {
  valid: boolean;
  username?: string;
  scopes?: string[];
  rate_limit?: number;
  rate_remaining?: number;
}

/**
 * Set GitHub Personal Access Token
 *
 * Stores the token securely for authenticated GitHub API requests.
 * Increases rate limit from 60 req/hr to 5000 req/hr.
 *
 * @param token - GitHub PAT (must start with ghp_ or github_pat_)
 * @throws Error if setting fails
 */
export async function setGitHubToken(token: string): Promise<void> {
  const response = await fetch(buildUrl('/settings/github-token'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ token }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to set GitHub token: ${response.statusText}`);
  }
}

/**
 * Get GitHub token status
 *
 * Returns whether a token is set and basic info about the authenticated user.
 *
 * @returns Token status with masked token and username if set
 * @throws Error if fetching status fails
 */
export async function getGitHubTokenStatus(): Promise<GitHubTokenStatus> {
  const response = await fetch(buildUrl('/settings/github-token/status'));

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to get token status: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Validate a GitHub token before saving
 *
 * Checks if the token is valid and returns details about permissions.
 *
 * @param token - GitHub PAT to validate
 * @returns Validation result with user info and rate limits
 * @throws Error if validation request fails
 */
export async function validateGitHubToken(token: string): Promise<GitHubTokenValidation> {
  const response = await fetch(buildUrl('/settings/github-token/validate'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ token }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to validate token: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Clear stored GitHub token
 *
 * Removes the token, reverting to unauthenticated API access (60 req/hr).
 *
 * @throws Error if clearing fails
 */
export async function clearGitHubToken(): Promise<void> {
  const response = await fetch(buildUrl('/settings/github-token'), {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to clear token: ${response.statusText}`);
  }
}
