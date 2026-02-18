/**
 * useDndAnimations Hook
 *
 * State machine managing drag-and-drop animation phases for the Groups view.
 * Controls drop-into-group, success feedback, remove poof, and idle phases.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type DndAnimPhase =
  | 'idle'
  | 'dropping-into-group'
  | 'success-feedback'
  | 'dropping-remove'
  | 'remove-feedback';

export interface DndAnimState {
  phase: DndAnimPhase;
  targetGroupId: string | null;
  sourceGroupId: string | null;
  targetRect: DOMRect | null;
}

const IDLE_STATE: DndAnimState = {
  phase: 'idle',
  targetGroupId: null,
  sourceGroupId: null,
  targetRect: null,
};

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useDndAnimations() {
  const [animState, setAnimState] = useState<DndAnimState>(IDLE_STATE);
  const timeoutsRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearTimeouts = useCallback(() => {
    timeoutsRef.current.forEach(clearTimeout);
    timeoutsRef.current = [];
  }, []);

  const addTimeout = useCallback((fn: () => void, ms: number) => {
    const id = setTimeout(fn, ms);
    timeoutsRef.current.push(id);
    return id;
  }, []);

  const triggerDropIntoGroup = useCallback(
    (groupId: string, targetRect: DOMRect) => {
      clearTimeouts();

      // Phase 1: dropping-into-group (card shrinks toward target)
      setAnimState({
        phase: 'dropping-into-group',
        targetGroupId: groupId,
        sourceGroupId: null,
        targetRect,
      });

      // Phase 2: success-feedback (checkmark + badge pop)
      addTimeout(() => {
        setAnimState((prev) => ({
          ...prev,
          phase: 'success-feedback',
        }));
      }, 300);

      // Phase 3: back to idle
      addTimeout(() => {
        setAnimState(IDLE_STATE);
      }, 1100);
    },
    [clearTimeouts, addTimeout]
  );

  const triggerRemovePoof = useCallback(
    (sourceGroupId: string) => {
      clearTimeouts();

      // Phase 1: dropping-remove (poof + particles)
      setAnimState({
        phase: 'dropping-remove',
        targetGroupId: null,
        sourceGroupId,
        targetRect: null,
      });

      // Phase 2: remove-feedback (badge shrink)
      addTimeout(() => {
        setAnimState((prev) => ({
          ...prev,
          phase: 'remove-feedback',
        }));
      }, 200);

      // Phase 3: back to idle
      addTimeout(() => {
        setAnimState(IDLE_STATE);
      }, 600);
    },
    [clearTimeouts, addTimeout]
  );

  const reset = useCallback(() => {
    clearTimeouts();
    setAnimState(IDLE_STATE);
  }, [clearTimeouts]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      // eslint-disable-next-line react-hooks/exhaustive-deps
      timeoutsRef.current.forEach(clearTimeout);
    };
  }, []);

  return {
    animState,
    triggerDropIntoGroup,
    triggerRemovePoof,
    reset,
  };
}
