'use client';

import { useGroups } from '@/hooks';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

interface GroupFilterSelectProps {
  /** Collection ID to fetch groups for */
  collectionId: string;
  /** Currently selected group ID (undefined = All Groups) */
  value?: string;
  /** Callback when selection changes */
  onChange: (groupId: string | undefined) => void;
  /** Optional className for styling */
  className?: string;
}

/**
 * Filter select component for filtering artifacts by group.
 *
 * Fetches and displays groups from a collection, allowing users to filter
 * artifacts by group membership. Includes an "All Groups" option to clear filtering.
 *
 * @example
 * ```tsx
 * <GroupFilterSelect
 *   collectionId={collectionId}
 *   value={selectedGroupId}
 *   onChange={(groupId) => setSelectedGroupId(groupId)}
 * />
 * ```
 */
export function GroupFilterSelect({
  collectionId,
  value,
  onChange,
  className,
}: GroupFilterSelectProps) {
  const { data, isLoading, isError } = useGroups(collectionId);

  // Show loading skeleton while fetching
  if (isLoading) {
    return <Skeleton className={cn('h-9 w-full', className)} />;
  }

  // On error or no groups, show disabled "All Groups" only
  if (isError || !data?.groups || data.groups.length === 0) {
    return (
      <Select value="all" disabled>
        <SelectTrigger className={cn(className)}>
          <SelectValue placeholder="All Groups" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Groups</SelectItem>
        </SelectContent>
      </Select>
    );
  }

  // Convert undefined to "all" for Select component
  const selectValue = value ?? 'all';

  const handleValueChange = (newValue: string) => {
    // Convert "all" back to undefined
    onChange(newValue === 'all' ? undefined : newValue);
  };

  return (
    <Select value={selectValue} onValueChange={handleValueChange}>
      <SelectTrigger className={cn(className)}>
        <SelectValue placeholder="All Groups" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">All Groups</SelectItem>
        {data.groups.map((group) => (
          <SelectItem key={group.id} value={group.id}>
            {group.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
