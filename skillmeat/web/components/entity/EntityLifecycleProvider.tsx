'use client';

/**
 * Entity Lifecycle Provider Component
 *
 * Re-exports the EntityLifecycleProvider from hooks for easy composition
 * in component hierarchies.
 */

import {
  EntityLifecycleProvider as BaseProvider,
  EntityLifecycleProviderProps,
} from '@/hooks';

export type { EntityLifecycleProviderProps };

/**
 * EntityLifecycleProvider Component
 *
 * Wraps children with entity lifecycle management context.
 * Supports both collection and project modes.
 *
 * @example Collection mode
 * ```tsx
 * <EntityLifecycleProvider mode="collection">
 *   <CollectionView />
 * </EntityLifecycleProvider>
 * ```
 *
 * @example Project mode
 * ```tsx
 * <EntityLifecycleProvider mode="project" projectPath="/path/to/project">
 *   <ProjectView />
 * </EntityLifecycleProvider>
 * ```
 */
export function EntityLifecycleProvider({
  children,
  mode = 'collection',
  projectPath,
}: EntityLifecycleProviderProps) {
  return (
    <BaseProvider mode={mode} projectPath={projectPath}>
      {children}
    </BaseProvider>
  );
}

export { useEntityLifecycle } from '@/hooks';
