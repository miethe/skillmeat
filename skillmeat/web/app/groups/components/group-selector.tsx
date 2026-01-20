'use client';

import { useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loader2, AlertCircle, Inbox } from 'lucide-react';

import { useGroups } from '@/hooks';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';

interface GroupSelectorProps {
  /** Collection ID to fetch groups for */
  collectionId: string;
  /** Currently selected group ID (controlled mode) - overrides URL param */
  selectedGroupId?: string | null;
  /** Callback when a group is selected (controlled mode) */
  onGroupSelect?: (groupId: string | null) => void;
  /** Additional CSS classes for the trigger */
  className?: string;
}

/**
 * GroupSelector - Dropdown for selecting a group within a collection
 *
 * Features:
 * - Fetches groups for the specified collection via useGroups hook
 * - Supports both controlled (via props) and uncontrolled (via URL) selection
 * - Updates URL query param (?group=<group-id>) when selection changes
 * - Shows artifact count for each group
 * - "All artifacts" option to clear group filter
 * - Loading and error states
 * - Accessible with proper ARIA labels
 *
 * @example
 * ```tsx
 * // Uncontrolled - uses URL params
 * <GroupSelector collectionId={collectionId} />
 *
 * // Controlled - uses props
 * <GroupSelector
 *   collectionId={collectionId}
 *   selectedGroupId={selectedGroup}
 *   onGroupSelect={setSelectedGroup}
 * />
 * ```
 */
export function GroupSelector({
  collectionId,
  selectedGroupId,
  onGroupSelect,
  className,
}: GroupSelectorProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Use provided selectedGroupId or get from URL
  const currentGroupId = selectedGroupId ?? searchParams.get('group');

  // Fetch groups for collection
  const { data: groupsData, isLoading, error } = useGroups(collectionId);
  const groups = groupsData?.groups ?? [];

  const handleChange = useCallback(
    (value: string) => {
      const groupId = value === 'all' ? null : value;

      // Call callback if provided
      onGroupSelect?.(groupId);

      // Update URL
      const params = new URLSearchParams(searchParams.toString());
      if (groupId) {
        params.set('group', groupId);
      } else {
        params.delete('group');
      }
      router.push(`/groups?${params.toString()}`);
    },
    [onGroupSelect, router, searchParams]
  );

  if (isLoading) {
    return (
      <div
        className={cn('flex h-9 w-64 items-center justify-center rounded-md border', className)}
        role="status"
        aria-label="Loading groups"
      >
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        <span className="sr-only">Loading groups...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={cn(
          'flex h-9 w-64 items-center gap-2 rounded-md border border-destructive/50 bg-destructive/10 px-3',
          className
        )}
        role="alert"
      >
        <AlertCircle className="h-4 w-4 text-destructive" aria-hidden="true" />
        <span className="text-sm text-destructive">Failed to load groups</span>
      </div>
    );
  }

  // Empty state - no groups in collection
  if (groups.length === 0) {
    return (
      <div
        className={cn(
          'flex h-9 w-64 items-center gap-2 rounded-md border border-dashed border-muted-foreground/50 bg-muted/30 px-3',
          className
        )}
        role="status"
        aria-label="No groups available"
      >
        <Inbox className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        <span className="text-sm text-muted-foreground">No groups in this collection</span>
      </div>
    );
  }

  return (
    <Select value={currentGroupId ?? 'all'} onValueChange={handleChange}>
      <SelectTrigger className={cn('w-64', className)} aria-label="Select group">
        <SelectValue placeholder="Select a group" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">All artifacts</SelectItem>
        {groups.map((group) => (
          <SelectItem key={group.id} value={group.id}>
            <span className="flex items-center gap-2">
              <span className="truncate">{group.name}</span>
              {group.artifact_count !== undefined && group.artifact_count > 0 && (
                <span className="text-muted-foreground">({group.artifact_count})</span>
              )}
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
