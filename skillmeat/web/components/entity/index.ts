/**
 * Entity Management Components Module
 *
 * Provides all UI components and utilities for entity lifecycle management in SkillMeat.
 *
 * Core Components:
 * - EntityList: Grid/list view of entities
 * - EntityCard: Card layout for grid view
 * - EntityRow: Table row layout for list view
 * - EntityForm: Dynamic form for creating/editing entities
 * - EntityActions: Context menu with lifecycle actions
 *
 * Merge & Conflict Resolution:
 * - MergeWorkflow: Multi-step merge process with conflict resolution
 * - ConflictResolver: Interactive conflict resolution card
 * - DiffViewer: Side-by-side diff viewer
 *
 * Context & Hooks:
 * - EntityLifecycleProvider: Context provider for entity management
 * - useEntityLifecycle: Hook to access entity management context
 *
 * @example
 * ```tsx
 * import {
 *   EntityLifecycleProvider,
 *   useEntityLifecycle,
 *   EntityList,
 *   EntityForm,
 * } from '@/components/entity';
 *
 * export function App() {
 *   return (
 *     <EntityLifecycleProvider mode="collection">
 *       <EntityList viewMode="grid" />
 *       <EntityForm mode="create" entityType="skill" />
 *     </EntityLifecycleProvider>
 *   );
 * }
 * ```
 */

export { DiffViewer } from './diff-viewer';
export { EntityLifecycleProvider, useEntityLifecycle } from './EntityLifecycleProvider';
export type { EntityLifecycleProviderProps } from './EntityLifecycleProvider';
export { EntityForm } from './entity-form';
export { EntityActions } from './entity-actions';
export type { EntityActionsProps } from './entity-actions';
export { EntityCard } from './entity-card';
export type { EntityCardProps } from './entity-card';
export { EntityRow } from './entity-row';
export type { EntityRowProps } from './entity-row';
export { EntityList } from './entity-list';
export type { EntityListProps } from './entity-list';
export { ConflictResolver } from './conflict-resolver';
export type { ConflictResolverProps } from './conflict-resolver';
export { MergeWorkflow } from './merge-workflow';
export { ProjectSelectorForDiff } from './project-selector-for-diff';
