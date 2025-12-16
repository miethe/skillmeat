# Phase 3: Web UI for Context Entities

**Parent Plan**: [agent-context-entities-v1.md](../agent-context-entities-v1.md)
**Duration**: 2 weeks
**Story Points**: 18
**Dependencies**: Phase 1 (Core Infrastructure), Phase 2 (CLI Management)

---

## Overview

Build React-based web interface for browsing, managing, and deploying context entities. Implements list view, detail modal, editor, filters, and deployment dialog using Next.js 15 and shadcn/ui components.

### Key Deliverables

1. Context entities list page (`/context-entities`)
2. Context entity card and detail components
3. Inline markdown editor with validation
4. Filter sidebar (type, category, auto-load, search)
5. Deploy to project dialog
6. TypeScript types and API client functions
7. React hooks with TanStack Query integration

---

## Task Breakdown

### TASK-3.1: Create Context Entities List Page

**Story Points**: 3
**Assigned To**: `ui-engineer-enhanced`
**Dependencies**: TASK-3.2, 3.5, 3.7, 3.8, 3.9

**Description**:
Create main page for browsing context entities with grid view, filters, pagination, and "Add Entity" button.

**Files to Create**:
- `skillmeat/web/app/context-entities/page.tsx`

**Implementation**:
```typescript
"use client";

import { useState } from "react";
import { useContextEntities } from "@/hooks/use-context-entities";
import { ContextEntityCard } from "@/components/context/context-entity-card";
import { ContextEntityFilters } from "@/components/context/context-entity-filters";
import { Button } from "@/components/ui/button";
import { PlusIcon } from "lucide-react";
import { ContextEntityType } from "@/types/context-entity";

export default function ContextEntitiesPage() {
  const [filters, setFilters] = useState({
    type: null as ContextEntityType | null,
    category: null as string | null,
    autoLoad: null as boolean | null,
    search: "",
  });

  const { data, isLoading, error } = useContextEntities(filters);

  return (
    <div className="container mx-auto py-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold">Context Entities</h1>
          <p className="text-muted-foreground mt-2">
            Manage agent configuration files (CLAUDE.md, specs, rules, context)
          </p>
        </div>
        <Button>
          <PlusIcon className="mr-2 h-4 w-4" />
          Add Entity
        </Button>
      </div>

      <div className="flex gap-6">
        {/* Filters Sidebar */}
        <aside className="w-64 flex-shrink-0">
          <ContextEntityFilters
            filters={filters}
            onFiltersChange={setFilters}
          />
        </aside>

        {/* Entity Grid */}
        <main className="flex-1">
          {isLoading && <div>Loading...</div>}
          {error && <div className="text-destructive">Error: {error.message}</div>}

          {data && data.items.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              No context entities found. Add your first entity to get started.
            </div>
          )}

          {data && data.items.length > 0 && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {data.items.map((entity) => (
                  <ContextEntityCard key={entity.id} entity={entity} />
                ))}
              </div>

              {/* Pagination */}
              <div className="mt-8 flex justify-center">
                <p className="text-sm text-muted-foreground">
                  Showing {data.items.length} of {data.total} entities
                </p>
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
```

**Features**:
- Grid layout (responsive: 1/2/3 columns)
- Loading and error states
- Empty state with helpful message
- Pagination footer
- Add entity button (future: opens dialog)

**Acceptance Criteria**:
- [ ] Page renders entity grid
- [ ] Filters update query params
- [ ] Loading states shown during fetch
- [ ] Error states handled gracefully
- [ ] Empty state message shown when no entities
- [ ] Responsive layout works on mobile

---

### TASK-3.2: Create ContextEntityCard Component

**Story Points**: 2
**Assigned To**: `ui-engineer-enhanced`
**Dependencies**: TASK-3.7

**Description**:
Create card component to display entity summary with type badge, category, auto-load indicator, and action buttons.

**Files to Create**:
- `skillmeat/web/components/context/context-entity-card.tsx`

**Implementation**:
```typescript
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FileTextIcon, EyeIcon, DownloadIcon } from "lucide-react";
import { ContextEntity } from "@/types/context-entity";

interface ContextEntityCardProps {
  entity: ContextEntity;
}

export function ContextEntityCard({ entity }: ContextEntityCardProps) {
  const typeColors = {
    project_config: "bg-blue-500",
    spec_file: "bg-purple-500",
    rule_file: "bg-green-500",
    context_file: "bg-orange-500",
    progress_template: "bg-pink-500",
  };

  const typeLabels = {
    project_config: "Project Config",
    spec_file: "Spec File",
    rule_file: "Rule File",
    context_file: "Context File",
    progress_template: "Progress Template",
  };

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <FileTextIcon className="h-5 w-5 text-muted-foreground" />
            <CardTitle className="text-lg">{entity.name}</CardTitle>
          </div>
          {entity.auto_load && (
            <Badge variant="outline" className="text-xs">
              Auto-Load
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent>
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Badge className={typeColors[entity.type]}>
              {typeLabels[entity.type]}
            </Badge>
            {entity.category && (
              <Badge variant="secondary">{entity.category}</Badge>
            )}
          </div>

          <p className="text-sm text-muted-foreground line-clamp-2">
            {entity.path_pattern}
          </p>

          {entity.version && (
            <p className="text-xs text-muted-foreground">
              Version: {entity.version}
            </p>
          )}
        </div>
      </CardContent>

      <CardFooter className="flex gap-2">
        <Button variant="outline" size="sm" className="flex-1">
          <EyeIcon className="mr-2 h-4 w-4" />
          Preview
        </Button>
        <Button size="sm" className="flex-1">
          <DownloadIcon className="mr-2 h-4 w-4" />
          Deploy
        </Button>
      </CardFooter>
    </Card>
  );
}
```

**Features**:
- Type-specific color coding
- Auto-load badge
- Category badge
- Path pattern preview
- Preview and Deploy buttons

**Acceptance Criteria**:
- [ ] Card displays entity metadata
- [ ] Type badge shows correct color
- [ ] Auto-load badge appears when applicable
- [ ] Hover effect works
- [ ] Buttons trigger correct actions (future: open modals)

---

### TASK-3.3: Create ContextEntityDetail Modal

**Story Points**: 3
**Assigned To**: `ui-engineer-enhanced`
**Dependencies**: TASK-3.7, 3.8

**Description**:
Create modal component for viewing entity details and markdown content with syntax highlighting. Lazy load content for performance.

**Files to Create**:
- `skillmeat/web/components/context/context-entity-detail.tsx`

**Implementation**:
```typescript
import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ContextEntity } from "@/types/context-entity";
import { fetchContextEntityContent } from "@/lib/api/context-entities";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

interface ContextEntityDetailProps {
  entity: ContextEntity;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ContextEntityDetail({
  entity,
  open,
  onOpenChange,
}: ContextEntityDetailProps) {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open && !content) {
      // Lazy load content when modal opens
      setLoading(true);
      fetchContextEntityContent(entity.id)
        .then((data) => setContent(data.content))
        .catch((err) => console.error("Failed to load content:", err))
        .finally(() => setLoading(false));
    }
  }, [open, entity.id, content]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{entity.name}</DialogTitle>
          <DialogDescription>
            <div className="flex gap-2 mt-2">
              <Badge>{entity.type}</Badge>
              {entity.category && <Badge variant="secondary">{entity.category}</Badge>}
              {entity.auto_load && <Badge variant="outline">Auto-Load</Badge>}
            </div>
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="preview" className="mt-4">
          <TabsList>
            <TabsTrigger value="preview">Preview</TabsTrigger>
            <TabsTrigger value="metadata">Metadata</TabsTrigger>
            <TabsTrigger value="raw">Raw Content</TabsTrigger>
          </TabsList>

          <TabsContent value="preview" className="mt-4">
            {loading && <p>Loading content...</p>}
            {content && (
              <div className="prose prose-sm max-w-none dark:prose-invert">
                <ReactMarkdown
                  components={{
                    code({ node, inline, className, children, ...props }) {
                      const match = /language-(\w+)/.exec(className || "");
                      return !inline && match ? (
                        <SyntaxHighlighter
                          style={vscDarkPlus}
                          language={match[1]}
                          PreTag="div"
                          {...props}
                        >
                          {String(children).replace(/\n$/, "")}
                        </SyntaxHighlighter>
                      ) : (
                        <code className={className} {...props}>
                          {children}
                        </code>
                      );
                    },
                  }}
                >
                  {content}
                </ReactMarkdown>
              </div>
            )}
          </TabsContent>

          <TabsContent value="metadata" className="mt-4">
            <dl className="space-y-2">
              <div>
                <dt className="font-semibold">Path Pattern:</dt>
                <dd className="text-sm text-muted-foreground">{entity.path_pattern}</dd>
              </div>
              <div>
                <dt className="font-semibold">Version:</dt>
                <dd className="text-sm text-muted-foreground">{entity.version || "None"}</dd>
              </div>
              <div>
                <dt className="font-semibold">Source:</dt>
                <dd className="text-sm text-muted-foreground">{entity.source || "None"}</dd>
              </div>
              <div>
                <dt className="font-semibold">Content Hash:</dt>
                <dd className="text-sm text-muted-foreground font-mono">{entity.content_hash}</dd>
              </div>
              <div>
                <dt className="font-semibold">Created:</dt>
                <dd className="text-sm text-muted-foreground">
                  {new Date(entity.created_at).toLocaleString()}
                </dd>
              </div>
              <div>
                <dt className="font-semibold">Updated:</dt>
                <dd className="text-sm text-muted-foreground">
                  {new Date(entity.updated_at).toLocaleString()}
                </dd>
              </div>
            </dl>
          </TabsContent>

          <TabsContent value="raw" className="mt-4">
            {content && (
              <pre className="bg-muted p-4 rounded-md overflow-x-auto text-sm">
                <code>{content}</code>
              </pre>
            )}
          </TabsContent>
        </Tabs>

        <div className="flex justify-end gap-2 mt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <Button>Deploy to Project</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

**Features**:
- Tabs: Preview (rendered markdown), Metadata, Raw Content
- Lazy loading of content
- Syntax highlighting for code blocks
- Scrollable modal for large content
- Deploy action button

**Acceptance Criteria**:
- [ ] Modal opens when card preview clicked
- [ ] Content is lazy loaded
- [ ] Markdown renders correctly
- [ ] Syntax highlighting works for code blocks
- [ ] Metadata tab shows all fields
- [ ] Raw content tab shows plain text

---

### TASK-3.4: Create ContextEntityEditor Component

**Story Points**: 3
**Assigned To**: `ui-engineer-enhanced`
**Dependencies**: TASK-3.7, 3.9

**Description**:
Create inline markdown editor with validation, frontmatter field extraction, and real-time feedback.

**Files to Create**:
- `skillmeat/web/components/context/context-entity-editor.tsx`

**Implementation**:
```typescript
import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { ContextEntityType } from "@/types/context-entity";
import { useCreateContextEntity, useUpdateContextEntity } from "@/hooks/use-context-entities";

const contextEntitySchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  type: z.enum([
    "project_config",
    "spec_file",
    "rule_file",
    "context_file",
    "progress_template",
  ]),
  category: z.string().max(100).optional(),
  path_pattern: z
    .string()
    .min(1, "Path pattern is required")
    .startsWith(".claude/", "Path must start with .claude/")
    .refine((val) => !val.includes(".."), "Path cannot contain .."),
  auto_load: z.boolean().default(false),
  content: z.string().min(1, "Content is required"),
  version: z.string().max(50).optional(),
});

type ContextEntityFormData = z.infer<typeof contextEntitySchema>;

interface ContextEntityEditorProps {
  entity?: ContextEntity; // If editing existing
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function ContextEntityEditor({
  entity,
  onSuccess,
  onCancel,
}: ContextEntityEditorProps) {
  const isEditing = !!entity;
  const createMutation = useCreateContextEntity();
  const updateMutation = useUpdateContextEntity();

  const form = useForm<ContextEntityFormData>({
    resolver: zodResolver(contextEntitySchema),
    defaultValues: entity || {
      name: "",
      type: "spec_file",
      category: "",
      path_pattern: ".claude/specs/",
      auto_load: false,
      content: "",
      version: "",
    },
  });

  const onSubmit = async (data: ContextEntityFormData) => {
    try {
      if (isEditing) {
        await updateMutation.mutateAsync({ id: entity.id, data });
      } else {
        await createMutation.mutateAsync(data);
      }
      onSuccess?.();
    } catch (error) {
      console.error("Failed to save entity:", error);
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <Input placeholder="doc-policy-spec" {...field} />
              </FormControl>
              <FormDescription>
                Unique identifier for this entity
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="type"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Type</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectItem value="project_config">Project Config</SelectItem>
                  <SelectItem value="spec_file">Spec File</SelectItem>
                  <SelectItem value="rule_file">Rule File</SelectItem>
                  <SelectItem value="context_file">Context File</SelectItem>
                  <SelectItem value="progress_template">Progress Template</SelectItem>
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="path_pattern"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Path Pattern</FormLabel>
              <FormControl>
                <Input placeholder=".claude/specs/doc-policy-spec.md" {...field} />
              </FormControl>
              <FormDescription>
                Deployment path relative to project root (must start with .claude/)
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="auto_load"
          render={({ field }) => (
            <FormItem className="flex items-center justify-between rounded-lg border p-4">
              <div className="space-y-0.5">
                <FormLabel>Auto-Load</FormLabel>
                <FormDescription>
                  Load this entity automatically in Claude Code
                </FormDescription>
              </div>
              <FormControl>
                <Switch checked={field.value} onCheckedChange={field.onChange} />
              </FormControl>
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="content"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Content</FormLabel>
              <FormControl>
                <Textarea
                  placeholder="Markdown content..."
                  className="font-mono min-h-[300px]"
                  {...field}
                />
              </FormControl>
              <FormDescription>
                Markdown content with optional YAML frontmatter
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="flex justify-end gap-2">
          {onCancel && (
            <Button type="button" variant="outline" onClick={onCancel}>
              Cancel
            </Button>
          )}
          <Button type="submit" disabled={createMutation.isPending || updateMutation.isPending}>
            {isEditing ? "Update" : "Create"} Entity
          </Button>
        </div>
      </form>
    </Form>
  );
}
```

**Features**:
- Form validation with Zod
- Type-specific path pattern suggestions
- Auto-load toggle
- Real-time validation feedback
- Create and edit modes

**Acceptance Criteria**:
- [ ] Form validates all fields
- [ ] Path pattern validation prevents traversal
- [ ] Content textarea is monospace
- [ ] Save button disabled during submission
- [ ] Success callback triggered after save
- [ ] Error messages are descriptive

---

### TASK-3.5: Create Context Entity Filters Sidebar

**Story Points**: 2
**Assigned To**: `ui-engineer`
**Dependencies**: TASK-3.7

**Description**:
Create filter sidebar component with checkboxes for types, category select, auto-load toggle, and search input.

**Files to Create**:
- `skillmeat/web/components/context/context-entity-filters.tsx`

**Implementation** (abbreviated):
```typescript
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { ContextEntityType } from "@/types/context-entity";

interface ContextEntityFiltersProps {
  filters: {
    type: ContextEntityType | null;
    category: string | null;
    autoLoad: boolean | null;
    search: string;
  };
  onFiltersChange: (filters: any) => void;
}

export function ContextEntityFilters({ filters, onFiltersChange }: ContextEntityFiltersProps) {
  const types: ContextEntityType[] = [
    "project_config",
    "spec_file",
    "rule_file",
    "context_file",
    "progress_template",
  ];

  const handleTypeChange = (type: ContextEntityType, checked: boolean) => {
    onFiltersChange({
      ...filters,
      type: checked ? type : null,
    });
  };

  const handleClearFilters = () => {
    onFiltersChange({
      type: null,
      category: null,
      autoLoad: null,
      search: "",
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="font-semibold mb-3">Search</h3>
        <Input
          placeholder="Search entities..."
          value={filters.search}
          onChange={(e) => onFiltersChange({ ...filters, search: e.target.value })}
        />
      </div>

      <div>
        <h3 className="font-semibold mb-3">Type</h3>
        <div className="space-y-2">
          {types.map((type) => (
            <div key={type} className="flex items-center space-x-2">
              <Checkbox
                id={type}
                checked={filters.type === type}
                onCheckedChange={(checked) => handleTypeChange(type, !!checked)}
              />
              <Label htmlFor={type} className="text-sm">
                {type.replace("_", " ")}
              </Label>
            </div>
          ))}
        </div>
      </div>

      {/* Category, Auto-Load filters... */}

      <Button variant="outline" onClick={handleClearFilters} className="w-full">
        Clear Filters
      </Button>
    </div>
  );
}
```

**Acceptance Criteria**:
- [ ] Type checkboxes filter entities
- [ ] Search input filters by name
- [ ] Auto-load toggle filters correctly
- [ ] Clear filters button resets all
- [ ] Filter state updates parent component

---

### TASK-3.6: Create DeployToProjectDialog Component

**Story Points**: 2
**Assigned To**: `ui-engineer-enhanced`
**Dependencies**: TASK-3.7, 3.8, 3.9

**Description**:
Create dialog for deploying entity to project with project selector, target path display, and overwrite warning.

**Files to Create**:
- `skillmeat/web/components/context/deploy-to-project-dialog.tsx`

**Implementation** (abbreviated):
```typescript
import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";
import { ContextEntity } from "@/types/context-entity";
import { useProjects } from "@/hooks/use-projects"; // Assuming project management exists
import { deployContextEntity } from "@/lib/api/context-entities";
import { useToast } from "@/hooks/use-toast";

interface DeployToProjectDialogProps {
  entity: ContextEntity;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DeployToProjectDialog({
  entity,
  open,
  onOpenChange,
}: DeployToProjectDialogProps) {
  const [selectedProject, setSelectedProject] = useState<string>("");
  const [deploying, setDeploying] = useState(false);
  const { data: projects } = useProjects();
  const { toast } = useToast();

  const handleDeploy = async () => {
    if (!selectedProject) return;

    setDeploying(true);
    try {
      await deployContextEntity(entity.id, selectedProject);
      toast({
        title: "Entity deployed",
        description: `${entity.name} has been deployed to ${selectedProject}`,
      });
      onOpenChange(false);
    } catch (error) {
      toast({
        title: "Deployment failed",
        description: error.message,
        variant: "destructive",
      });
    } finally {
      setDeploying(false);
    }
  };

  const targetPath = selectedProject
    ? `${selectedProject}/${entity.path_pattern}`
    : entity.path_pattern;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Deploy Entity to Project</DialogTitle>
          <DialogDescription>
            Deploy <strong>{entity.name}</strong> to a project
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Select Project</label>
            <Select value={selectedProject} onValueChange={setSelectedProject}>
              <SelectTrigger>
                <SelectValue placeholder="Choose project..." />
              </SelectTrigger>
              <SelectContent>
                {projects?.map((project) => (
                  <SelectItem key={project.id} value={project.path}>
                    {project.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {selectedProject && (
            <div className="space-y-2">
              <label className="text-sm font-medium">Deployment Path</label>
              <p className="text-sm text-muted-foreground font-mono bg-muted p-2 rounded">
                {targetPath}
              </p>
            </div>
          )}

          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              If a file already exists at this path, it will be overwritten.
            </AlertDescription>
          </Alert>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleDeploy} disabled={!selectedProject || deploying}>
            {deploying ? "Deploying..." : "Deploy"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

**Acceptance Criteria**:
- [ ] Project selector shows available projects
- [ ] Target path updates based on selection
- [ ] Overwrite warning is visible
- [ ] Deploy button disabled until project selected
- [ ] Success toast shown after deployment
- [ ] Error toast shown on failure

---

### TASK-3.7: Create TypeScript Types for Context Entities

**Story Points**: 1
**Assigned To**: `ui-engineer`
**Dependencies**: Phase 1 (API schemas)

**Description**:
Create TypeScript type definitions matching backend API schemas.

**Files to Create**:
- `skillmeat/web/types/context-entity.ts`

**Implementation**:
```typescript
export type ContextEntityType =
  | "project_config"
  | "spec_file"
  | "rule_file"
  | "context_file"
  | "progress_template";

export interface ContextEntity {
  id: string;
  name: string;
  type: ContextEntityType;
  category?: string;
  path_pattern: string;
  auto_load: boolean;
  content_hash: string;
  source?: string;
  version?: string;
  created_at: string;
  updated_at: string;
  collections: string[]; // Collection IDs
}

export interface CreateContextEntityRequest {
  name: string;
  type: ContextEntityType;
  category?: string;
  path_pattern: string;
  auto_load?: boolean;
  content: string;
  source?: string;
  version?: string;
}

export interface UpdateContextEntityRequest {
  name?: string;
  category?: string;
  path_pattern?: string;
  auto_load?: boolean;
  content?: string;
  version?: string;
}

export interface ContextEntityListResponse {
  items: ContextEntity[];
  total: number;
  page_info?: {
    has_next: boolean;
    cursor?: string;
  };
}

export interface ContextEntityContentResponse {
  content: string;
  content_hash: string;
}

export interface ContextEntityFilters {
  type?: ContextEntityType;
  category?: string;
  autoLoad?: boolean;
  search?: string;
}
```

**Acceptance Criteria**:
- [ ] Types match backend schemas exactly
- [ ] All enum values included
- [ ] Optional fields marked with `?`
- [ ] Export all types for use in components

---

### TASK-3.8: Create API Client Functions

**Story Points**: 2
**Assigned To**: `ui-engineer`
**Dependencies**: TASK-3.7, Phase 1 (API endpoints)

**Description**:
Create API client functions for context entities following patterns from `lib/api/collections.ts`.

**Files to Create**:
- `skillmeat/web/lib/api/context-entities.ts`

**Implementation**:
```typescript
import type {
  ContextEntity,
  CreateContextEntityRequest,
  UpdateContextEntityRequest,
  ContextEntityListResponse,
  ContextEntityContentResponse,
  ContextEntityFilters,
} from "@/types/context-entity";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || "v1";

function buildUrl(path: string): string {
  return `${API_BASE}/api/${API_VERSION}${path}`;
}

export async function fetchContextEntities(
  filters?: ContextEntityFilters
): Promise<ContextEntityListResponse> {
  const params = new URLSearchParams();
  if (filters?.type) params.set("type", filters.type);
  if (filters?.category) params.set("category", filters.category);
  if (filters?.autoLoad !== undefined) params.set("auto_load", String(filters.autoLoad));

  const url = buildUrl(`/context-entities${params.toString() ? `?${params}` : ""}`);
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch context entities: ${response.statusText}`);
  }

  return response.json();
}

export async function fetchContextEntity(id: string): Promise<ContextEntity> {
  const response = await fetch(buildUrl(`/context-entities/${id}`));

  if (!response.ok) {
    throw new Error(`Failed to fetch context entity: ${response.statusText}`);
  }

  return response.json();
}

export async function createContextEntity(
  data: CreateContextEntityRequest
): Promise<ContextEntity> {
  const response = await fetch(buildUrl("/context-entities"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to create context entity: ${response.statusText}`);
  }

  return response.json();
}

export async function updateContextEntity(
  id: string,
  data: UpdateContextEntityRequest
): Promise<ContextEntity> {
  const response = await fetch(buildUrl(`/context-entities/${id}`), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to update context entity: ${response.statusText}`);
  }

  return response.json();
}

export async function deleteContextEntity(id: string): Promise<void> {
  const response = await fetch(buildUrl(`/context-entities/${id}`), {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error(`Failed to delete context entity: ${response.statusText}`);
  }
}

export async function fetchContextEntityContent(
  id: string
): Promise<ContextEntityContentResponse> {
  const response = await fetch(buildUrl(`/context-entities/${id}/content`));

  if (!response.ok) {
    throw new Error(`Failed to fetch context entity content: ${response.statusText}`);
  }

  return response.json();
}

export async function deployContextEntity(
  entityId: string,
  projectPath: string
): Promise<void> {
  // Future: API endpoint for deployment
  // For now, this is a placeholder
  throw new Error("Deployment via web UI not yet implemented");
}
```

**Acceptance Criteria**:
- [ ] All CRUD operations implemented
- [ ] URL building uses `buildUrl` helper
- [ ] Error handling extracts backend `detail`
- [ ] Functions match hook expectations
- [ ] Types are correctly imported and used

---

### TASK-3.9: Create React Hooks for Context Entities

**Story Points**: 2
**Assigned To**: `ui-engineer`
**Dependencies**: TASK-3.7, 3.8

**Description**:
Create React hooks using TanStack Query for context entity operations with proper cache management.

**Files to Create**:
- `skillmeat/web/hooks/use-context-entities.ts`

**Implementation**:
```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type {
  ContextEntity,
  CreateContextEntityRequest,
  UpdateContextEntityRequest,
  ContextEntityFilters,
} from "@/types/context-entity";
import {
  fetchContextEntities,
  fetchContextEntity,
  createContextEntity,
  updateContextEntity,
  deleteContextEntity,
} from "@/lib/api/context-entities";

export const contextEntityKeys = {
  all: ["context-entities"] as const,
  lists: () => [...contextEntityKeys.all, "list"] as const,
  list: (filters?: ContextEntityFilters) => [...contextEntityKeys.lists(), filters] as const,
  details: () => [...contextEntityKeys.all, "detail"] as const,
  detail: (id: string) => [...contextEntityKeys.details(), id] as const,
};

export function useContextEntities(filters?: ContextEntityFilters) {
  return useQuery({
    queryKey: contextEntityKeys.list(filters),
    queryFn: () => fetchContextEntities(filters),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useContextEntity(id: string) {
  return useQuery({
    queryKey: contextEntityKeys.detail(id),
    queryFn: () => fetchContextEntity(id),
    enabled: !!id,
  });
}

export function useCreateContextEntity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: CreateContextEntityRequest) => {
      return createContextEntity(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: contextEntityKeys.all });
    },
  });
}

export function useUpdateContextEntity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateContextEntityRequest }) => {
      return updateContextEntity(id, data);
    },
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: contextEntityKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: contextEntityKeys.lists() });
    },
  });
}

export function useDeleteContextEntity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      return deleteContextEntity(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: contextEntityKeys.all });
    },
  });
}
```

**Acceptance Criteria**:
- [ ] Query hooks fetch data correctly
- [ ] Mutation hooks call API functions
- [ ] Cache invalidation works (all, lists, detail)
- [ ] Query keys follow factory pattern
- [ ] Stale time configured appropriately

---

## Parallelization Plan

### Batch 1 (Parallel - Foundation)
Types and API client first:
- TASK-3.7: TypeScript types
- TASK-3.8: API client functions

**Delegation**:
```python
Task("ui-engineer", "TASK-3.7: TypeScript types for context entities...")
Task("ui-engineer", "TASK-3.8: API client functions...")
```

### Batch 2 (Sequential)
Hooks depend on types and API client:
- TASK-3.9: React hooks

**Delegation**:
```python
Task("ui-engineer", "TASK-3.9: React hooks with TanStack Query...")
```

### Batch 3 (Parallel - Components)
After hooks are ready, build components in parallel:
- TASK-3.2: ContextEntityCard
- TASK-3.3: ContextEntityDetail modal
- TASK-3.4: ContextEntityEditor
- TASK-3.5: ContextEntityFilters
- TASK-3.6: DeployToProjectDialog

**Delegation**:
```python
Task("ui-engineer-enhanced", "TASK-3.2: ContextEntityCard component...")
Task("ui-engineer-enhanced", "TASK-3.3: ContextEntityDetail modal with lazy loading...")
Task("ui-engineer-enhanced", "TASK-3.4: ContextEntityEditor with validation...")
Task("ui-engineer", "TASK-3.5: ContextEntityFilters sidebar...")
Task("ui-engineer-enhanced", "TASK-3.6: DeployToProjectDialog component...")
```

### Batch 4 (Sequential)
Page integration after components:
- TASK-3.1: Context entities list page

**Delegation**:
```python
Task("ui-engineer-enhanced", "TASK-3.1: Context entities list page integration...")
```

---

## Quality Gates

Before completing Phase 3:

- [ ] All components render without errors
- [ ] TypeScript types match backend schemas
- [ ] API client handles all CRUD operations
- [ ] Query hooks fetch and cache data correctly
- [ ] Filters update entity list
- [ ] Markdown preview renders correctly
- [ ] Syntax highlighting works for code blocks
- [ ] Form validation prevents invalid submissions
- [ ] Loading and error states handled
- [ ] Responsive design works on mobile

---

## Success Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Components created | 6 | ___ |
| API client functions | 7 | ___ |
| React hooks | 5 | ___ |
| TypeScript type coverage | 100% | ___ |
| Component test coverage | 80%+ | ___ |

---

## Next Phase

Once Phase 3 is complete and all quality gates pass, proceed to:
**[Phase 4: Context Collections & Templates](phase-4-context-collections-templates.md)**
