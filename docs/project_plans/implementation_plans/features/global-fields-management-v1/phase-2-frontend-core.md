# Phase 2: Frontend Core & Settings Page (5 days)

**Story Points**: 31 | **Duration**: 5 days | **Team**: Frontend Engineer

---

## Phase Overview

Phase 2 establishes the frontend foundation for the Global Fields Management feature. This phase focuses on building the `/settings/fields` page structure, core UI components (tabs, sidebar, options list), form dialogs (add/edit/remove), and TanStack Query integration for data fetching and mutations.

### Phase Goals

1. Create `/settings/fields` page with object type tabs (Artifacts, Marketplace Sources)
2. Implement FieldsClient layout component
3. Build reusable dialog components (Add, Edit, Remove)
4. Setup TanStack Query hooks for API integration
5. Implement error handling and loading states
6. Ensure responsive and accessible UI

### Deliverables

- `skillmeat/web/app/settings/fields/page.tsx` - Settings fields page (server component)
- `skillmeat/web/components/settings/fields-client.tsx` - Main client component
- `skillmeat/web/components/settings/fields-*.tsx` - Sub-components (tabs, sidebar, dialogs)
- `skillmeat/web/hooks/use-field-options.ts` - Custom TanStack Query hooks
- `skillmeat/web/hooks/index.ts` - Updated hook barrel export
- `skillmeat/web/lib/api/fields.ts` - API client functions

---

## Detailed Task Breakdown

### Task GFM-IMPL-2.1: Create Settings Fields Page

**Objective**: Create `/settings/fields` page (server component)

**Technical Specification**:

Create `skillmeat/web/app/settings/fields/page.tsx`:

```typescript
import { Metadata } from 'next';
import FieldsClient from '@/components/settings/fields-client';

export const metadata: Metadata = {
  title: 'Global Fields Management | SkillMeat',
  description: 'Manage enumerable field options across artifacts and marketplace sources',
};

export default function FieldsPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Global Fields Management</h1>
        <p className="text-muted-foreground mt-1">
          Manage enumerable field options (tags, trust levels, visibility) across your collection
        </p>
      </div>

      {/* Client Component */}
      <FieldsClient />
    </div>
  );
}
```

**Acceptance Criteria**:

- [ ] Page loads at `/settings/fields`
- [ ] Metadata set correctly for SEO
- [ ] Header displays title and description
- [ ] FieldsClient component rendered
- [ ] No console errors on load

---

### Task GFM-IMPL-2.2: Create FieldsClient Layout

**Objective**: Implement main FieldsClient component with layout

**Technical Specification**:

Create `skillmeat/web/components/settings/fields-client.tsx`:

```typescript
'use client';

import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card } from '@/components/ui/card';
import FieldSidebar from './field-sidebar';
import FieldOptionsContent from './field-options-content';

type ObjectType = 'artifacts' | 'marketplace_sources';

const OBJECT_TYPES = [
  { id: 'artifacts', label: 'Artifacts' },
  { id: 'marketplace_sources', label: 'Marketplace Sources' },
] as const;

export default function FieldsClient() {
  const [selectedObjectType, setSelectedObjectType] = useState<ObjectType>('artifacts');
  const [selectedField, setSelectedField] = useState<string | null>(null);

  return (
    <Tabs defaultValue="artifacts" onValueChange={(val) => {
      setSelectedObjectType(val as ObjectType);
      setSelectedField(null);  // Reset field selection on tab switch
    }}>
      <TabsList className="grid w-full max-w-md grid-cols-2">
        {OBJECT_TYPES.map((type) => (
          <TabsTrigger key={type.id} value={type.id}>
            {type.label}
          </TabsTrigger>
        ))}
      </TabsList>

      {OBJECT_TYPES.map((type) => (
        <TabsContent key={type.id} value={type.id} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
            {/* Left Sidebar: Field List */}
            <Card className="lg:col-span-1">
              <FieldSidebar
                objectType={type.id}
                selectedField={selectedField}
                onFieldSelect={setSelectedField}
              />
            </Card>

            {/* Right Content: Field Options */}
            <Card className="lg:col-span-3">
              {selectedField ? (
                <FieldOptionsContent
                  objectType={type.id}
                  fieldName={selectedField}
                />
              ) : (
                <div className="flex items-center justify-center h-96">
                  <div className="text-center">
                    <p className="text-muted-foreground">Select a field to manage options</p>
                  </div>
                </div>
              )}
            </Card>
          </div>
        </TabsContent>
      ))}
    </Tabs>
  );
}
```

**Acceptance Criteria**:

- [ ] Tabs switch between Artifacts and Marketplace Sources
- [ ] Sidebar renders on left, content on right
- [ ] Responsive grid layout (1 col mobile, 4 col desktop)
- [ ] Field selection state managed correctly
- [ ] Tab switch resets field selection

---

### Task GFM-IMPL-2.3: Create FieldOptionsList

**Objective**: Build options list component

**Technical Specification**:

Create `skillmeat/web/components/settings/field-options-list.tsx`:

```typescript
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Edit2, Trash2 } from 'lucide-react';
import type { FieldOption } from '@/types/fields';

interface FieldOptionsListProps {
  options: FieldOption[];
  readonly: boolean;
  onEdit: (option: FieldOption) => void;
  onRemove: (option: FieldOption) => void;
  isLoading: boolean;
}

export default function FieldOptionsList({
  options,
  readonly,
  onEdit,
  onRemove,
  isLoading,
}: FieldOptionsListProps) {
  if (isLoading) {
    return <div className="space-y-2">Loading options...</div>;
  }

  if (options.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-muted-foreground">No options available</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {options.map((option) => (
        <div
          key={option.id}
          className="flex items-center justify-between p-3 border rounded-md hover:bg-muted"
        >
          <div className="flex items-center gap-3">
            {/* Color Badge (if applicable) */}
            {option.color && (
              <div
                className="w-4 h-4 rounded-full border"
                style={{ backgroundColor: option.color }}
                title={option.color}
              />
            )}

            {/* Name */}
            <div>
              <div className="font-medium">{option.name}</div>
              <div className="text-xs text-muted-foreground">
                {option.usage_count === 0
                  ? 'Not in use'
                  : `Used in ${option.usage_count} artifact${option.usage_count !== 1 ? 's' : ''}`}
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            {!readonly && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onEdit(option)}
                  aria-label={`Edit ${option.name}`}
                >
                  <Edit2 className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onRemove(option)}
                  aria-label={`Remove ${option.name}`}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </>
            )}
            {readonly && (
              <Badge variant="secondary">Read-only</Badge>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
```

**Acceptance Criteria**:

- [ ] Options render as rows with name, color badge, usage count
- [ ] Edit/Remove buttons visible (disabled for readonly)
- [ ] Read-only badge displayed for system fields
- [ ] Loading state handled
- [ ] Empty state message shown
- [ ] ARIA labels on icon buttons

---

### Task GFM-IMPL-2.4: Create AddOptionDialog

**Objective**: Build dialog for adding field options

**Technical Specification**:

Create `skillmeat/web/components/settings/add-option-dialog.tsx`:

```typescript
'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Plus } from 'lucide-react';

interface AddOptionDialogProps {
  objectType: string;
  fieldName: string;
  isLoading: boolean;
  onSubmit: (data: { name: string; color?: string }) => Promise<void>;
}

export default function AddOptionDialog({
  objectType,
  fieldName,
  isLoading,
  onSubmit,
}: AddOptionDialogProps) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [color, setColor] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const isTag = fieldName === 'tags';

  const handleSubmit = async () => {
    setError(null);

    // Validation
    if (!name.trim()) {
      setError('Name is required');
      return;
    }

    if (color && !isValidHex(color)) {
      setError('Color must be valid hex (#RRGGBB or #RGB)');
      return;
    }

    try {
      setSubmitting(true);
      await onSubmit({
        name: name.trim(),
        color: color || undefined,
      });
      setOpen(false);
      setName('');
      setColor('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add option');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Button onClick={() => setOpen(true)} className="w-full">
        <Plus className="h-4 w-4 mr-2" />
        Add Option
      </Button>

      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add {fieldName} Option</DialogTitle>
          <DialogDescription>
            Create a new option for {fieldName}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Name Input */}
          <div className="space-y-2">
            <Label htmlFor="name">Name *</Label>
            <Input
              id="name"
              placeholder={isTag ? 'e.g., Python 3' : 'Option name'}
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={submitting}
            />
          </div>

          {/* Color Input (for tags) */}
          {isTag && (
            <div className="space-y-2">
              <Label htmlFor="color">Color (optional)</Label>
              <div className="flex gap-2">
                <Input
                  id="color"
                  placeholder="#3776AB"
                  value={color}
                  onChange={(e) => setColor(e.target.value)}
                  disabled={submitting}
                />
                {color && isValidHex(color) && (
                  <div
                    className="w-10 h-10 rounded-md border"
                    style={{ backgroundColor: color }}
                  />
                )}
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="text-sm text-destructive">{error}</div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={submitting || !name.trim()}
          >
            {submitting ? 'Adding...' : 'Add Option'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function isValidHex(color: string): boolean {
  return /^#(?:[0-9a-fA-F]{3}){1,2}$/.test(color);
}
```

**Acceptance Criteria**:

- [ ] Dialog opens on button click
- [ ] Form validates name (required, not empty)
- [ ] Form validates color (hex format or empty)
- [ ] Color preview shown
- [ ] Submit button disabled on invalid input
- [ ] Error messages displayed inline
- [ ] Loading state handled

---

### Task GFM-IMPL-2.5: Create EditOptionDialog

**Objective**: Build dialog for editing field options

**Technical Specification**:

Create `skillmeat/web/components/settings/edit-option-dialog.tsx`:

```typescript
'use client';

import { useEffect, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Edit2 } from 'lucide-react';
import type { FieldOption } from '@/types/fields';

interface EditOptionDialogProps {
  option: FieldOption | null;
  isLoading: boolean;
  onSubmit: (data: { name?: string; color?: string }) => Promise<void>;
}

export default function EditOptionDialog({
  option,
  isLoading,
  onSubmit,
}: EditOptionDialogProps) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [color, setColor] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Populate form when option changes
  useEffect(() => {
    if (option && open) {
      setName(option.name);
      setColor(option.color || '');
      setError(null);
    }
  }, [option, open]);

  const handleSubmit = async () => {
    setError(null);

    if (!name.trim()) {
      setError('Name is required');
      return;
    }

    if (color && !isValidHex(color)) {
      setError('Color must be valid hex');
      return;
    }

    try {
      setSubmitting(true);
      await onSubmit({
        name: name.trim() !== option?.name ? name.trim() : undefined,
        color: color !== (option?.color || '') ? color : undefined,
      });
      setOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update option');
    } finally {
      setSubmitting(false);
    }
  };

  if (!option) return null;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Button variant="ghost" size="sm" onClick={() => setOpen(true)}>
        <Edit2 className="h-4 w-4" />
      </Button>

      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit {option.name}</DialogTitle>
          <DialogDescription>
            Modify the option details
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name *</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={submitting}
            />
          </div>

          {option.color !== null && (
            <div className="space-y-2">
              <Label htmlFor="color">Color (optional)</Label>
              <div className="flex gap-2">
                <Input
                  id="color"
                  value={color}
                  onChange={(e) => setColor(e.target.value)}
                  disabled={submitting}
                />
                {color && isValidHex(color) && (
                  <div
                    className="w-10 h-10 rounded-md border"
                    style={{ backgroundColor: color }}
                  />
                )}
              </div>
            </div>
          )}

          {error && (
            <div className="text-sm text-destructive">{error}</div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={submitting}>
            {submitting ? 'Saving...' : 'Save Changes'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function isValidHex(color: string): boolean {
  return !color || /^#(?:[0-9a-fA-F]{3}){1,2}$/.test(color);
}
```

**Acceptance Criteria**:

- [ ] Dialog pre-fills current option values
- [ ] Form validation prevents empty name
- [ ] Color validation works
- [ ] Submit button sends only changed fields
- [ ] Error messages displayed

---

### Task GFM-IMPL-2.6: Create RemoveConfirmDialog

**Objective**: Build confirmation dialog for removing options

**Technical Specification**:

Create `skillmeat/web/components/settings/remove-option-dialog.tsx`:

```typescript
'use client';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Trash2 } from 'lucide-react';
import { useState } from 'react';
import type { FieldOption } from '@/types/fields';

interface RemoveOptionDialogProps {
  option: FieldOption | null;
  isLoading: boolean;
  onConfirm: () => Promise<void>;
}

export default function RemoveOptionDialog({
  option,
  isLoading,
  onConfirm,
}: RemoveOptionDialogProps) {
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleConfirm = async () => {
    try {
      setSubmitting(true);
      await onConfirm();
      setOpen(false);
    } finally {
      setSubmitting(false);
    }
  };

  if (!option) return null;

  const hasUsage = option.usage_count > 0;

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setOpen(true)}
        aria-label={`Remove ${option.name}`}
      >
        <Trash2 className="h-4 w-4" />
      </Button>

      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Remove {option.name}?</AlertDialogTitle>
          <AlertDialogDescription>
            {hasUsage ? (
              <div className="space-y-2">
                <p>
                  This option is currently used in <strong>{option.usage_count}</strong> artifact
                  {option.usage_count !== 1 ? 's' : ''}.
                </p>
                <p>Removing it will delete the option from all artifacts.</p>
                <p>This action cannot be undone.</p>
              </div>
            ) : (
              <p>This option is not currently in use. It will be permanently deleted.</p>
            )}
          </AlertDialogDescription>
        </AlertDialogHeader>

        <AlertDialogFooter>
          <AlertDialogCancel disabled={submitting}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={submitting}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {submitting ? 'Removing...' : 'Remove'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

**Acceptance Criteria**:

- [ ] Dialog shows usage count clearly
- [ ] Warning message about cascade delete shown
- [ ] Destructive button for removal
- [ ] Confirmation required before deletion
- [ ] Loading state handled

---

### Task GFM-IMPL-2.7: Setup TanStack Query Hooks

**Objective**: Create custom hooks for API integration

**Technical Specification**:

Create `skillmeat/web/hooks/use-field-options.ts`:

```typescript
'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getFieldOptions, createFieldOption, updateFieldOption, deleteFieldOption } from '@/lib/api/fields';
import type { FieldListResponse, FieldOptionResponse, FieldOption } from '@/types/fields';

// Query key factory
const fieldQueryKeys = {
  all: ['fields'] as const,
  lists: () => [...fieldQueryKeys.all, 'list'] as const,
  list: (objectType: string, fieldName: string) =>
    [...fieldQueryKeys.lists(), { objectType, fieldName }] as const,
};

// Hook: Get field options
export function useFieldOptions(objectType: string, fieldName: string) {
  return useQuery({
    queryKey: fieldQueryKeys.list(objectType, fieldName),
    queryFn: () => getFieldOptions(objectType, fieldName),
    enabled: !!objectType && !!fieldName,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

// Hook: Create field option
export function useCreateFieldOption() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      objectType: string;
      fieldName: string;
      name: string;
      color?: string;
    }) => createFieldOption(data),
    onSuccess: (_, variables) => {
      // Invalidate list to refetch
      queryClient.invalidateQueries({
        queryKey: fieldQueryKeys.list(variables.objectType, variables.fieldName),
      });
    },
  });
}

// Hook: Update field option
export function useUpdateFieldOption() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      objectType: string;
      fieldName: string;
      optionId: string;
      name?: string;
      color?: string;
    }) => updateFieldOption(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: fieldQueryKeys.list(variables.objectType, variables.fieldName),
      });
    },
  });
}

// Hook: Delete field option
export function useDeleteFieldOption() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      objectType: string;
      fieldName: string;
      optionId: string;
    }) => deleteFieldOption(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: fieldQueryKeys.list(variables.objectType, variables.fieldName),
      });
    },
  });
}
```

**Update `skillmeat/web/hooks/index.ts`**:

```typescript
// Export all hooks from barrel file
export { useFieldOptions, useCreateFieldOption, useUpdateFieldOption, useDeleteFieldOption } from './use-field-options';
// ... other hook exports
```

**Acceptance Criteria**:

- [ ] useFieldOptions fetches from API
- [ ] useCreateFieldOption creates and invalidates cache
- [ ] useUpdateFieldOption updates and invalidates cache
- [ ] useDeleteFieldOption deletes and invalidates cache
- [ ] Hooks exported from barrel import
- [ ] Stale time set appropriately

---

### Task GFM-IMPL-2.8: Error Handling & UX

**Objective**: Implement error display and loading states

**Technical Specification**:

- Form validation shows inline errors immediately
- API errors displayed as toast notifications
- Loading skeletons show during data fetching
- Disabled buttons during submission

Create `skillmeat/web/components/settings/field-options-content.tsx`:

```typescript
'use client';

import { useState } from 'react';
import { useFieldOptions, useCreateFieldOption, useUpdateFieldOption, useDeleteFieldOption } from '@/hooks';
import { useToast } from '@/components/ui/use-toast';
import { CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import FieldOptionsList from './field-options-list';
import AddOptionDialog from './add-option-dialog';
import EditOptionDialog from './edit-option-dialog';
import RemoveOptionDialog from './remove-option-dialog';
import type { FieldOption } from '@/types/fields';

interface FieldOptionsContentProps {
  objectType: string;
  fieldName: string;
}

export default function FieldOptionsContent({
  objectType,
  fieldName,
}: FieldOptionsContentProps) {
  const { toast } = useToast();
  const [selectedOption, setSelectedOption] = useState<FieldOption | null>(null);
  const [editingOption, setEditingOption] = useState<FieldOption | null>(null);
  const [removingOption, setRemovingOption] = useState<FieldOption | null>(null);

  const { data, isLoading, error } = useFieldOptions(objectType, fieldName);
  const createMutation = useCreateFieldOption();
  const updateMutation = useUpdateFieldOption();
  const deleteMutation = useDeleteFieldOption();

  const handleCreate = async (formData: { name: string; color?: string }) => {
    try {
      await createMutation.mutateAsync({
        objectType,
        fieldName,
        ...formData,
      });
      toast({
        title: 'Success',
        description: `Option "${formData.name}" created`,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create option';
      toast({
        title: 'Error',
        description: message,
        variant: 'destructive',
      });
      throw err;
    }
  };

  const handleUpdate = async (formData: { name?: string; color?: string }) => {
    if (!editingOption) return;
    try {
      await updateMutation.mutateAsync({
        objectType,
        fieldName,
        optionId: editingOption.id,
        ...formData,
      });
      toast({
        title: 'Success',
        description: 'Option updated',
      });
      setEditingOption(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update';
      toast({
        title: 'Error',
        description: message,
        variant: 'destructive',
      });
      throw err;
    }
  };

  const handleDelete = async () => {
    if (!removingOption) return;
    try {
      await deleteMutation.mutateAsync({
        objectType,
        fieldName,
        optionId: removingOption.id,
      });
      toast({
        title: 'Success',
        description: `Option "${removingOption.name}" removed`,
      });
      setRemovingOption(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to remove';
      toast({
        title: 'Error',
        description: message,
        variant: 'destructive',
      });
      throw err;
    }
  };

  return (
    <>
      <CardHeader>
        <CardTitle>{fieldName.charAt(0).toUpperCase() + fieldName.slice(1)}</CardTitle>
        <CardDescription>Manage options for this field</CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Add Button */}
        <AddOptionDialog
          objectType={objectType}
          fieldName={fieldName}
          isLoading={createMutation.isPending}
          onSubmit={handleCreate}
        />

        {/* Options List */}
        {error && (
          <div className="text-sm text-destructive">
            Failed to load options: {error.message}
          </div>
        )}

        {data && (
          <FieldOptionsList
            options={data.items}
            readonly={data.items[0]?.readonly || false}
            onEdit={setEditingOption}
            onRemove={setRemovingOption}
            isLoading={isLoading}
          />
        )}

        {/* Edit/Remove Dialogs */}
        <EditOptionDialog
          option={editingOption}
          isLoading={updateMutation.isPending}
          onSubmit={handleUpdate}
        />

        <RemoveOptionDialog
          option={removingOption}
          isLoading={deleteMutation.isPending}
          onConfirm={handleDelete}
        />
      </CardContent>
    </>
  );
}
```

**Acceptance Criteria**:

- [ ] Form validation prevents invalid submissions
- [ ] API errors shown as toast notifications
- [ ] Loading skeletons visible during fetch
- [ ] Disabled buttons during operations
- [ ] Error messages clear and actionable

---

## API Client Functions

Create `skillmeat/web/lib/api/fields.ts`:

```typescript
import { apiClient } from '@/lib/api';
import type { FieldListResponse, FieldOptionResponse } from '@/types/fields';

export async function getFieldOptions(
  objectType: string,
  fieldName: string,
  limit = 50,
  after?: string
): Promise<FieldListResponse> {
  const params = new URLSearchParams({
    object_type: objectType,
    field_name: fieldName,
    limit: limit.toString(),
    ...(after && { after }),
  });

  const response = await apiClient.get(`/api/v1/fields?${params}`);
  return response.json();
}

export async function createFieldOption(data: {
  objectType: string;
  fieldName: string;
  name: string;
  color?: string;
}): Promise<FieldOptionResponse> {
  const response = await apiClient.post('/api/v1/fields/options', {
    object_type: data.objectType,
    field_name: data.fieldName,
    name: data.name,
    color: data.color,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create option');
  }

  return response.json();
}

export async function updateFieldOption(data: {
  objectType: string;
  fieldName: string;
  optionId: string;
  name?: string;
  color?: string;
}): Promise<FieldOptionResponse> {
  const params = new URLSearchParams({
    object_type: data.objectType,
    field_name: data.fieldName,
  });

  const response = await apiClient.put(
    `/api/v1/fields/options/${data.optionId}?${params}`,
    {
      ...(data.name && { name: data.name }),
      ...(data.color !== undefined && { color: data.color }),
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to update option');
  }

  return response.json();
}

export async function deleteFieldOption(data: {
  objectType: string;
  fieldName: string;
  optionId: string;
}): Promise<{ success: boolean; cascade_count: number }> {
  const params = new URLSearchParams({
    object_type: data.objectType,
    field_name: data.fieldName,
  });

  const response = await apiClient.delete(
    `/api/v1/fields/options/${data.optionId}?${params}`
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to delete option');
  }

  return response.json();
}
```

---

## TypeScript Types

Create `skillmeat/web/types/fields.ts`:

```typescript
export interface FieldOption {
  id: string;
  name: string;
  color?: string | null;
  usage_count: number;
  readonly: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface FieldListResponse {
  items: FieldOption[];
  page_info: {
    has_next_page: boolean;
    has_previous_page: boolean;
    start_cursor?: string;
    end_cursor?: string;
    total_count?: number;
  };
}

export interface FieldOptionResponse extends FieldOption {}
```

---

## Phase 2 Quality Checklist

- [ ] Page loads at `/settings/fields` without errors
- [ ] Tabs switch correctly between object types
- [ ] Sidebar displays all fields for selected object type
- [ ] Field selection updates content area
- [ ] Form validation prevents invalid submissions
- [ ] API errors shown as toasts
- [ ] Loading states visible during operations
- [ ] Responsive layout on desktop and tablet
- [ ] Accessible keyboard navigation (Tab, Enter, Esc)
- [ ] ARIA labels on icon buttons

---

**Phase 2 ready for implementation. Frontend engineer should start with FieldsClient layout, then build sub-components and hooks in parallel.**
