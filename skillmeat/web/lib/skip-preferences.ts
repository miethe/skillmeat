/**
 * LocalStorage utilities for persisting artifact skip preferences
 *
 * Provides type-safe functions for managing which artifacts a user has chosen
 * to skip during discovery/import flows. Preferences are stored per-project
 * in browser localStorage with graceful degradation.
 */

import type { SkipPreference } from '@/types/discovery';

const STORAGE_KEY_PREFIX = 'skillmeat_skip_prefs_';

/**
 * Build storage key for a project's skip preferences
 */
function getStorageKey(projectId: string): string {
  return `${STORAGE_KEY_PREFIX}${projectId}`;
}

/**
 * Check if localStorage is available (handles SSR and privacy modes)
 */
function isStorageAvailable(): boolean {
  try {
    const test = '__storage_test__';
    localStorage.setItem(test, test);
    localStorage.removeItem(test);
    return true;
  } catch {
    return false;
  }
}

/**
 * Load skip preferences for a project from localStorage
 *
 * @param projectId - Unique project identifier
 * @returns Array of skip preferences, or empty array if unavailable
 */
export function loadSkipPrefs(projectId: string): SkipPreference[] {
  if (!isStorageAvailable()) return [];

  try {
    const stored = localStorage.getItem(getStorageKey(projectId));
    if (!stored) return [];
    const parsed = JSON.parse(stored);
    // Ensure we always return an array
    if (!Array.isArray(parsed)) return [];
    return parsed as SkipPreference[];
  } catch {
    return [];
  }
}

/**
 * Save skip preferences for a project to localStorage
 *
 * @param projectId - Unique project identifier
 * @param skipList - Array of skip preferences to persist
 */
export function saveSkipPrefs(projectId: string, skipList: SkipPreference[]): void {
  if (!isStorageAvailable()) return;

  try {
    localStorage.setItem(getStorageKey(projectId), JSON.stringify(skipList));
  } catch {
    // Silently fail if storage is full or unavailable
  }
}

/**
 * Add a new skip preference for an artifact
 *
 * @param projectId - Unique project identifier
 * @param artifactKey - Artifact identifier (format: "type:name")
 * @param reason - User's reason for skipping
 * @returns The newly created skip preference
 */
export function addSkipPref(
  projectId: string,
  artifactKey: string,
  reason: string
): SkipPreference {
  const current = loadSkipPrefs(projectId);
  const newPref: SkipPreference = {
    artifact_key: artifactKey,
    skip_reason: reason,
    added_date: new Date().toISOString(),
  };

  // Check for duplicates before adding
  if (!current.some((p) => p.artifact_key === artifactKey)) {
    current.push(newPref);
    saveSkipPrefs(projectId, current);
  }

  return newPref;
}

/**
 * Remove a skip preference for an artifact
 *
 * @param projectId - Unique project identifier
 * @param artifactKey - Artifact identifier to remove
 * @returns true if preference was removed, false if not found
 */
export function removeSkipPref(projectId: string, artifactKey: string): boolean {
  const current = loadSkipPrefs(projectId);
  const filtered = current.filter((p) => p.artifact_key !== artifactKey);

  if (filtered.length !== current.length) {
    saveSkipPrefs(projectId, filtered);
    return true;
  }
  return false;
}

/**
 * Clear all skip preferences for a project
 *
 * @param projectId - Unique project identifier
 */
export function clearSkipPrefs(projectId: string): void {
  if (!isStorageAvailable()) return;
  localStorage.removeItem(getStorageKey(projectId));
}

/**
 * Check if an artifact is marked as skipped
 *
 * @param projectId - Unique project identifier
 * @param artifactKey - Artifact identifier to check
 * @returns true if artifact should be skipped
 */
export function isSkipped(projectId: string, artifactKey: string): boolean {
  const prefs = loadSkipPrefs(projectId);
  return prefs.some((p) => p.artifact_key === artifactKey);
}

/**
 * Build artifact key from type and name (matches backend format)
 *
 * @param type - Artifact type (skill, command, agent, etc.)
 * @param name - Artifact name
 * @returns Formatted artifact key "type:name"
 */
export function buildArtifactKey(type: string, name: string): string {
  return `${type}:${name}`;
}
