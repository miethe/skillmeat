'use client';

import { Plus, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

export type GroupSortField = 'position' | 'name' | 'updated_at' | 'artifact_count';

interface GroupsToolbarProps {
  search: string;
  onSearchChange: (value: string) => void;
  sort: GroupSortField;
  onSortChange: (value: GroupSortField) => void;
  selectedTag: string | null;
  onSelectedTagChange: (value: string | null) => void;
  availableTags: string[];
  onCreate: () => void;
  disabled?: boolean;
}

export function GroupsToolbar({
  search,
  onSearchChange,
  sort,
  onSortChange,
  selectedTag,
  onSelectedTagChange,
  availableTags,
  onCreate,
  disabled = false,
}: GroupsToolbarProps) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Search groups by name, description, or tag"
            className="pl-9"
            aria-label="Search groups"
            disabled={disabled}
          />
        </div>

        <div className="flex flex-col gap-3 sm:flex-row">
          <Select
            value={selectedTag ?? 'all'}
            onValueChange={(value) => onSelectedTagChange(value === 'all' ? null : value)}
            disabled={disabled}
          >
            <SelectTrigger className="w-full sm:w-48">
              <SelectValue placeholder="Filter by tag" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All tags</SelectItem>
              {availableTags.map((tag) => (
                <SelectItem key={tag} value={tag}>
                  {tag}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={sort} onValueChange={(value) => onSortChange(value as GroupSortField)}>
            <SelectTrigger className="w-full sm:w-48">
              <SelectValue placeholder="Sort groups" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="position">Sort: Position</SelectItem>
              <SelectItem value="name">Sort: Name</SelectItem>
              <SelectItem value="updated_at">Sort: Recently updated</SelectItem>
              <SelectItem value="artifact_count">Sort: Artifact count</SelectItem>
            </SelectContent>
          </Select>

          <Button onClick={onCreate} disabled={disabled}>
            <Plus className="mr-2 h-4 w-4" />
            New Group
          </Button>
        </div>
      </div>
    </div>
  );
}
