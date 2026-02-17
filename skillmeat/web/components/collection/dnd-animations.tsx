/**
 * DnD Animation Components
 *
 * Visual feedback components for drag-and-drop operations in the Groups view:
 * - DropIntoGroupOverlay: Animates card shrinking toward target group
 * - SuccessCheckmark: Green check that appears over the target group badge
 * - PoofParticles: Particle burst effect for remove-from-group
 */

'use client';

import * as React from 'react';
import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Artifact } from '@/types/artifact';
import { MiniArtifactCard } from './mini-artifact-card';

// ---------------------------------------------------------------------------
// DropIntoGroupOverlay
// ---------------------------------------------------------------------------

export interface DropIntoGroupOverlayProps {
  /** The artifact being dropped */
  artifact: Artifact;
  /** Target element's bounding rect (sidebar group button) */
  targetRect: DOMRect;
}

/**
 * Fixed-positioned card that animates shrinking toward the target group's
 * sidebar position. Renders only during the `dropping-into-group` phase.
 */
export function DropIntoGroupOverlay({ artifact, targetRect }: DropIntoGroupOverlayProps) {
  return (
    <div
      className="pointer-events-none fixed z-50 animate-dnd-drop-into"
      style={{
        left: targetRect.left + targetRect.width / 2 - 80,
        top: targetRect.top + targetRect.height / 2 - 40,
        width: 160,
      }}
    >
      <MiniArtifactCard
        artifact={artifact}
        onClick={() => {}}
        className="shadow-lg"
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// SuccessCheckmark
// ---------------------------------------------------------------------------

export interface SuccessCheckmarkProps {
  /** Whether the checkmark is fading out */
  isFadingOut?: boolean;
}

/**
 * Small green circle with a Check icon. Positioned absolute (-top-1 -right-1)
 * relative to a parent with `position: relative`.
 *
 * Uses `animate-dnd-success-check` on appear, switches to
 * `animate-dnd-success-check-out` when fading.
 */
export function SuccessCheckmark({ isFadingOut = false }: SuccessCheckmarkProps) {
  return (
    <div
      className={cn(
        'absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-green-500 text-white',
        isFadingOut ? 'animate-dnd-success-check-out' : 'animate-dnd-success-check'
      )}
    >
      <Check className="h-3 w-3" strokeWidth={3} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// PoofParticles
// ---------------------------------------------------------------------------

/**
 * Five particle dots that burst outward from the center. Used when an artifact
 * is removed from a group via the remove drop zone.
 */
export function PoofParticles() {
  return (
    <div className="pointer-events-none relative h-0 w-0">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className={`dnd-particle dnd-particle-${i}`} />
      ))}
    </div>
  );
}
