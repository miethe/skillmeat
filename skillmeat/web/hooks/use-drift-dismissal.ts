'use client';

import { useState, useCallback, useEffect } from 'react';
import type { ComparisonScope, DriftStatus } from '@/components/sync-status/drift-alert-banner';

/**
 * localStorage key format for drift dismissal persistence.
 */
function getDismissalKey(artifactId: string, scope: ComparisonScope): string {
  return `skillmeat:drift-dismissed:${artifactId}:${scope}`;
}

/**
 * TTL for drift dismissals (24 hours in milliseconds).
 */
const DISMISSAL_TTL_MS = 24 * 60 * 60 * 1000;

interface DismissalRecord {
  /** The drift status at the time of dismissal */
  driftStatus: DriftStatus;
  /** Timestamp when the dismissal was recorded */
  dismissedAt: number;
}

/**
 * SSR-safe localStorage read.
 */
function readDismissal(key: string): DismissalRecord | null {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return null;
    const record: DismissalRecord = JSON.parse(raw);
    // Validate structure
    if (typeof record.driftStatus !== 'string' || typeof record.dismissedAt !== 'number') {
      return null;
    }
    return record;
  } catch {
    return null;
  }
}

/**
 * SSR-safe localStorage write.
 */
function writeDismissal(key: string, record: DismissalRecord): void {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    window.localStorage.setItem(key, JSON.stringify(record));
  } catch {
    // Silently fail if localStorage is full or unavailable
  }
}

/**
 * SSR-safe localStorage removal.
 */
function removeDismissal(key: string): void {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    window.localStorage.removeItem(key);
  } catch {
    // Silently fail
  }
}

export interface UseDriftDismissalOptions {
  artifactId: string;
  scope: ComparisonScope;
  driftStatus: DriftStatus;
}

export interface UseDriftDismissalReturn {
  /** Whether the current drift alert is dismissed */
  isDismissed: boolean;
  /** Dismiss the current drift alert */
  dismiss: () => void;
}

/**
 * useDriftDismissal - Persistent drift alert dismissal with 24h expiry
 *
 * Stores dismissal state in localStorage keyed by artifact ID and comparison scope.
 * Automatically clears dismissal when:
 * - The drift status changes from what was dismissed (new changes detected)
 * - The 24-hour TTL expires
 *
 * SSR-safe: All localStorage access is guarded with `typeof window` checks.
 *
 * @example
 * ```tsx
 * const { isDismissed, dismiss } = useDriftDismissal({
 *   artifactId: entity.id,
 *   scope: comparisonScope,
 *   driftStatus,
 * });
 *
 * if (!isDismissed) {
 *   return <DriftAlertBanner onDismiss={dismiss} ... />;
 * }
 * ```
 */
export function useDriftDismissal({
  artifactId,
  scope,
  driftStatus,
}: UseDriftDismissalOptions): UseDriftDismissalReturn {
  const key = getDismissalKey(artifactId, scope);

  const [isDismissed, setIsDismissed] = useState<boolean>(() => {
    const record = readDismissal(key);
    if (!record) return false;

    // Check TTL expiry
    const now = Date.now();
    if (now - record.dismissedAt > DISMISSAL_TTL_MS) {
      removeDismissal(key);
      return false;
    }

    // Check if drift status matches what was dismissed
    if (record.driftStatus !== driftStatus) {
      removeDismissal(key);
      return false;
    }

    return true;
  });

  // Auto-clear when drift status changes from what was dismissed
  useEffect(() => {
    const record = readDismissal(key);
    if (!record) return;

    // Check TTL expiry
    const now = Date.now();
    if (now - record.dismissedAt > DISMISSAL_TTL_MS) {
      removeDismissal(key);
      setIsDismissed(false);
      return;
    }

    // Clear if drift status changed
    if (record.driftStatus !== driftStatus) {
      removeDismissal(key);
      setIsDismissed(false);
    }
  }, [key, driftStatus]);

  const dismiss = useCallback(() => {
    const record: DismissalRecord = {
      driftStatus,
      dismissedAt: Date.now(),
    };
    writeDismissal(key, record);
    setIsDismissed(true);
  }, [key, driftStatus]);

  return { isDismissed, dismiss };
}
