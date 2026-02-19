---
title: 'Phase 3: UI Components & Integration'
description: ContentPane updates, LinkedArtifactsSection, ArtifactLinkingDialog, tools
  filter
created: 2026-01-21
updated: 2026-01-21
status: inferred_complete
---
# Phase 3: UI Components & Integration

**Duration**: 1.5 weeks
**Dependencies**: Phases 0-2 complete
**Assigned Subagent(s)**: ui-engineer-enhanced (Opus), frontend-developer (Sonnet), testing-specialist (Opus)

## Phase Overview

Implement all user-facing UI components for frontmatter and linking features. This includes updating ContentPane to exclude raw frontmatter, creating LinkedArtifactsSection for display, ArtifactLinkingDialog for manual linking, and integrating tools filtering into the artifact search UI.

---

## Task Breakdown

### UI-001: ContentPane Raw Frontmatter Exclusion

**Duration**: 1.5 days
**Effort**: 2 story points
**Assigned**: ui-engineer-enhanced
**Dependencies**: Phase 1 complete (frontmatter data available)

#### Description

Update `skillmeat/web/components/entity/content-pane.tsx` to exclude raw YAML frontmatter block from displayed content when FrontmatterDisplay component is active.

#### Acceptance Criteria

- [ ] ContentPane imports `stripFrontmatter` from `skillmeat/web/lib/frontmatter`
- [ ] Detects if frontmatter is present in content AND FrontmatterDisplay is rendered
- [ ] Applies `stripFrontmatter()` to remove `---\n...\n---\n` block before display
- [ ] Only strips when FrontmatterDisplay is active (not for plain text views)
- [ ] Raw content body displays correctly (no missing content)
- [ ] No duplicate frontmatter display
- [ ] Works with all artifact types (skill, agent, command, hook, mcp)
- [ ] Markdown rendering unchanged for body content
- [ ] Performance: No noticeable lag from stripping

#### Implementation Notes

```typescript
// skillmeat/web/components/entity/content-pane.tsx
import { stripFrontmatter } from '@/lib/frontmatter';

interface ContentPaneProps {
  content: string;
  showFrontmatter?: boolean;  // NEW: Whether FrontmatterDisplay is shown
  contentType?: 'markdown' | 'plaintext' | 'code';
  // ... other props
}

export function ContentPane({
  content,
  showFrontmatter = false,
  contentType = 'markdown',
  ...props
}: ContentPaneProps) {
  // Strip raw frontmatter if FrontmatterDisplay is active
  const displayContent = showFrontmatter
    ? stripFrontmatter(content)
    : content;

  return (
    <div className="content-pane">
      {/* FrontmatterDisplay would be rendered by parent component */}
      {/* This component now displays cleaned content without raw frontmatter */}
      <MarkdownRenderer content={displayContent} />
    </div>
  );
}
```

#### Definition of Done

- [ ] ContentPane accepts showFrontmatter prop
- [ ] Raw frontmatter excluded when flag true
- [ ] FrontmatterDisplay shows formatted metadata
- [ ] Content body displays correctly
- [ ] Works with all artifact types
- [ ] No performance regression
- [ ] Tests verify frontmatter exclusion

---

### UI-002: LinkedArtifactsSection Component

**Duration**: 2 days
**Effort**: 5 story points
**Assigned**: ui-engineer-enhanced
**Dependencies**: Phase 2 API endpoints complete

#### Description

Create `skillmeat/web/components/entity/linked-artifacts-section.tsx` that displays linked artifacts and unlinked references with rich UI for navigation and linking.

#### Acceptance Criteria

- [ ] Component displays array of LinkedArtifactReference objects
- [ ] Shows artifact name, type (chip), link type (badge)
- [ ] Click artifact name → navigates to artifact detail
- [ ] Delete button removes link (calls API)
- [ ] Unlinked references section shows items with "Link" button
- [ ] Empty state when no linked artifacts
- [ ] Grid or list layout (responsive)
- [ ] Link type visual indicators (requires = solid, enables = outline, related = dotted)
- [ ] Confirmation dialog before delete
- [ ] Loading state during API calls
- [ ] Error state with retry
- [ ] Accessibility: ARIA labels, keyboard navigation

#### Component Structure

```typescript
// skillmeat/web/components/entity/linked-artifacts-section.tsx
import { LinkedArtifactReference, Artifact } from '@/types/artifact';
import { ArtifactLinkingDialog } from './artifact-linking-dialog';

interface LinkedArtifactsSectionProps {
  artifactId: string;
  linkedArtifacts?: LinkedArtifactReference[];
  unlinkedReferences?: string[];
  onLinkCreated?: () => void;
  onLinkDeleted?: () => void;
}

export function LinkedArtifactsSection({
  artifactId,
  linkedArtifacts = [],
  unlinkedReferences = [],
  onLinkCreated,
  onLinkDeleted,
}: LinkedArtifactsSectionProps) {
  const [showDialog, setShowDialog] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const deleteLink = useMutation(/* ... */);

  const handleDelete = async (targetId: string) => {
    setDeleting(targetId);
    await deleteLink.mutateAsync({ artifactId, targetArtifactId: targetId });
    onLinkDeleted?.();
    setDeleting(null);
  };

  if (linkedArtifacts.length === 0 && unlinkedReferences.length === 0) {
    return (
      <div className="linked-artifacts-section">
        <h3>Linked Artifacts</h3>
        <div className="empty-state">
          <p>No linked artifacts yet.</p>
          <Button onClick={() => setShowDialog(true)}>Add Link</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="linked-artifacts-section">
      <h3>Linked Artifacts</h3>

      {/* Linked artifacts grid */}
      <div className="linked-artifacts-grid">
        {linkedArtifacts.map((link) => (
          <Card key={link.artifact_id} className="artifact-card">
            <CardHeader>
              <Link href={`/artifacts/${link.artifact_id}`}>
                <h4 className="cursor-pointer hover:underline">
                  {link.artifact_name}
                </h4>
              </Link>
            </CardHeader>
            <CardContent className="flex items-center justify-between gap-2">
              <div className="flex gap-2">
                <ArtifactTypeBadge type={link.artifact_type} />
                <LinkTypeBadge type={link.link_type} />
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleDelete(link.artifact_id!)}
                disabled={deleting === link.artifact_id}
                aria-label={`Remove link to ${link.artifact_name}`}
              >
                ×
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Unlinked references section */}
      {unlinkedReferences.length > 0 && (
        <div className="unlinked-references mt-6">
          <h4>Unlinked References</h4>
          <p className="text-sm text-muted-foreground mb-3">
            These artifacts were referenced but not found in your collection.
          </p>
          <div className="space-y-2">
            {unlinkedReferences.map((ref) => (
              <div key={ref} className="flex items-center justify-between p-2 bg-muted rounded">
                <span className="text-sm">{ref}</span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowDialog(true)}
                >
                  Link
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Add Link button */}
      {linkedArtifacts.length > 0 && (
        <Button
          variant="outline"
          className="mt-4"
          onClick={() => setShowDialog(true)}
        >
          + Add Link
        </Button>
      )}

      {/* Linking dialog */}
      {showDialog && (
        <ArtifactLinkingDialog
          artifactId={artifactId}
          onSuccess={() => {
            setShowDialog(false);
            onLinkCreated?.();
          }}
          onOpenChange={setShowDialog}
        />
      )}
    </div>
  );
}
```

#### Definition of Done

- [ ] Component renders linked artifacts grid
- [ ] Click navigates to linked artifact
- [ ] Delete button removes link with confirmation
- [ ] Unlinked references displayed with "Link" button
- [ ] Empty state when no links
- [ ] Loading and error states working
- [ ] Responsive design (mobile, tablet, desktop)
- [ ] Accessibility compliant (WCAG 2.1 AA)
- [ ] Tests verify all interactions

---

### UI-003: ArtifactLinkingDialog Component

**Duration**: 2 days
**Effort**: 5 story points
**Assigned**: ui-engineer-enhanced
**Dependencies**: Phase 2 API endpoints complete

#### Description

Create `skillmeat/web/components/entity/artifact-linking-dialog.tsx` modal dialog that allows users to search and link artifacts from their collection.

#### Acceptance Criteria

- [ ] Dialog component for manual artifact linking
- [ ] Search field with debounced search across artifact names
- [ ] Filter by artifact type (dropdown or chips)
- [ ] Filter by source/collection (optional)
- [ ] Results show artifact name, type, version, source
- [ ] Single-select mode (select one artifact)
- [ ] Link type selector (requires, enables, related)
- [ ] Create button to POST new link
- [ ] Cancel button to close without linking
- [ ] Success state after link created
- [ ] Error state with helpful message
- [ ] Loading indicator during search/creation
- [ ] Keyboard navigation (arrow keys, Enter, Escape)
- [ ] Accessibility: ARIA labels, focus management

#### Component Implementation

```typescript
// skillmeat/web/components/entity/artifact-linking-dialog.tsx
import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface ArtifactLinkingDialogProps {
  artifactId: string;
  onSuccess: () => void;
  onOpenChange?: (open: boolean) => void;
}

export function ArtifactLinkingDialog({
  artifactId,
  onSuccess,
  onOpenChange,
}: ArtifactLinkingDialogProps) {
  const [search, setSearch] = useState('');
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null);
  const [linkType, setLinkType] = useState<'requires' | 'enables' | 'related'>('requires');
  const [typeFilter, setTypeFilter] = useState<string | null>(null);
  const [open, setOpen] = useState(true);

  // Search artifacts
  const { data: searchResults = [], isLoading } = useQuery({
    queryKey: ['artifacts-search', search, typeFilter],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (search) params.append('q', search);
      if (typeFilter) params.append('type', typeFilter);
      const res = await fetch(`/api/artifacts?${params}`);
      return res.json();
    },
    enabled: search.length > 1,
  });

  // Create link
  const createLink = useMutation({
    mutationFn: async () => {
      const res = await fetch(
        `/api/artifacts/${artifactId}/linked-artifacts`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            target_artifact_id: selectedArtifactId,
            link_type: linkType,
          }),
        }
      );
      if (!res.ok) throw new Error('Failed to create link');
      return res.json();
    },
    onSuccess: () => {
      onSuccess();
      setOpen(false);
      onOpenChange?.(false);
    },
  });

  const handleCreate = async () => {
    if (!selectedArtifactId) return;
    await createLink.mutateAsync();
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => {
      setOpen(isOpen);
      onOpenChange?.(isOpen);
    }}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Link Artifact</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Search Input */}
          <div>
            <label className="text-sm font-medium">Search Artifacts</label>
            <Input
              placeholder="Search by name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="mt-1"
              autoFocus
            />
          </div>

          {/* Type Filter */}
          <div>
            <label className="text-sm font-medium">Artifact Type</label>
            <Select value={typeFilter || ''} onValueChange={(v) => setTypeFilter(v || null)}>
              <SelectTrigger>
                <SelectValue placeholder="All types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All types</SelectItem>
                <SelectItem value="skill">Skill</SelectItem>
                <SelectItem value="agent">Agent</SelectItem>
                <SelectItem value="command">Command</SelectItem>
                <SelectItem value="hook">Hook</SelectItem>
                <SelectItem value="mcp">MCP Server</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Results */}
          <div className="space-y-2">
            {isLoading ? (
              <div className="text-sm text-muted-foreground">Searching...</div>
            ) : searchResults.length === 0 ? (
              <div className="text-sm text-muted-foreground">
                {search ? 'No artifacts found' : 'Type to search'}
              </div>
            ) : (
              <div className="border rounded max-h-64 overflow-y-auto space-y-1">
                {searchResults.map((artifact) => (
                  <button
                    key={artifact.id}
                    onClick={() => setSelectedArtifactId(artifact.id)}
                    className={cn(
                      'w-full text-left px-3 py-2 flex items-center gap-2 rounded hover:bg-accent',
                      selectedArtifactId === artifact.id && 'bg-primary text-primary-foreground'
                    )}
                  >
                    <input
                      type="radio"
                      checked={selectedArtifactId === artifact.id}
                      onChange={() => setSelectedArtifactId(artifact.id)}
                      aria-label={`Select ${artifact.name}`}
                    />
                    <div className="flex-1">
                      <div className="font-medium text-sm">{artifact.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {artifact.type} • {artifact.source}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Link Type Selector */}
          {selectedArtifactId && (
            <div>
              <label className="text-sm font-medium">Link Type</label>
              <Select value={linkType} onValueChange={(v: any) => setLinkType(v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="requires">Requires</SelectItem>
                  <SelectItem value="enables">Enables</SelectItem>
                  <SelectItem value="related">Related</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Error */}
          {createLink.isError && (
            <div className="text-sm text-destructive bg-destructive/10 p-2 rounded">
              Failed to create link. Please try again.
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2 mt-6">
          <Button variant="outline" onClick={() => {
            setOpen(false);
            onOpenChange?.(false);
          }}>
            Cancel
          </Button>
          <Button
            onClick={handleCreate}
            disabled={!selectedArtifactId || createLink.isPending}
          >
            {createLink.isPending ? 'Creating...' : 'Create Link'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

#### Definition of Done

- [ ] Dialog opens and closes correctly
- [ ] Search works with debounce
- [ ] Filter by type working
- [ ] Single-select works
- [ ] Link type selector available
- [ ] Create link API call successful
- [ ] Success/error states displayed
- [ ] Keyboard navigation working
- [ ] Accessibility compliant
- [ ] Tests verify all interactions

---

### UI-004: Tools Filter Integration

**Duration**: 1.5 days
**Effort**: 2 story points
**Assigned**: frontend-developer
**Dependencies**: Phase 1 API (tools field exposed)

#### Description

Integrate tools filter into artifact search/filter UI. Users should be able to filter artifacts by tools used.

#### Acceptance Criteria

- [ ] Search page supports optional `tools` query parameter
- [ ] Tools filter UI shows multi-select of available tools
- [ ] Filter results by selected tools (artifacts with ANY selected tool)
- [ ] Filters persist in URL for bookmarking/sharing
- [ ] Can combine with other filters (type, tag, source)
- [ ] Shows tool badges/chips for clarity
- [ ] Clear all filters button
- [ ] Mobile-friendly UI
- [ ] Performance: Filter updates within 500ms

#### Implementation Notes

```typescript
// Example: Add tools multi-select to search filters
const [selectedTools, setSelectedTools] = useState<Tool[]>([]);

const toolsQuery = selectedTools.length > 0
  ? `&tools=${selectedTools.join(',')}`
  : '';

const { data: artifacts } = useQuery({
  queryKey: ['artifacts', search, selectedTools],
  queryFn: async () => {
    const res = await fetch(
      `/api/artifacts?q=${search}${toolsQuery}`
    );
    return res.json();
  },
});

// UI: Multi-select for tools
<MultiSelect
  options={allTools.map(t => ({ value: t, label: t }))}
  selected={selectedTools}
  onChange={setSelectedTools}
  placeholder="Filter by tools..."
/>
```

#### Definition of Done

- [ ] Tools filter UI present in search
- [ ] Filtering works with API
- [ ] Multiple tools can be selected
- [ ] URL parameters updated
- [ ] Persists across page refresh
- [ ] Responsive design
- [ ] Performance acceptable

---

### UI-005: Manual Linking Workflow Integration

**Duration**: 1.5 days
**Effort**: 2 story points
**Assigned**: frontend-developer
**Dependencies**: UI-002, UI-003

#### Description

Integrate LinkedArtifactsSection and ArtifactLinkingDialog into artifact detail pages to enable complete manual linking workflow.

#### Acceptance Criteria

- [ ] Artifact detail page includes LinkedArtifactsSection
- [ ] Linked artifacts fetched via API on page load
- [ ] Unlinked references fetched and displayed
- [ ] "Add Link" button opens ArtifactLinkingDialog
- [ ] Link created in dialog → immediately visible in LinkedArtifactsSection
- [ ] Delete link from section → immediately removed from UI
- [ ] Refresh not needed (optimistic UI updates)
- [ ] Works on artifact edit page as well
- [ ] Mobile responsive
- [ ] Loading states handled

#### Integration Pattern

```typescript
// In artifact detail page
export function ArtifactDetailPage({ artifactId }: Props) {
  const { data: artifact } = useArtifact(artifactId);
  const [refreshLinks, setRefreshLinks] = useState(0);

  return (
    <>
      {/* ... other sections ... */}

      {artifact && (
        <LinkedArtifactsSection
          artifactId={artifactId}
          linkedArtifacts={artifact.linked_artifacts}
          unlinkedReferences={artifact.unlinked_references}
          onLinkCreated={() => setRefreshLinks(r => r + 1)}
          onLinkDeleted={() => setRefreshLinks(r => r + 1)}
        />
      )}
    </>
  );
}
```

#### Definition of Done

- [ ] LinkedArtifactsSection displayed on artifact page
- [ ] Links fetch from API on load
- [ ] Manual linking workflow complete
- [ ] Optimistic UI updates working
- [ ] No page refresh needed
- [ ] Mobile responsive
- [ ] Works on both view and edit pages

---

### TEST-002: Component & E2E Tests

**Duration**: 2 days
**Effort**: 3 story points
**Assigned**: testing-specialist
**Dependencies**: All UI components complete

#### Description

Comprehensive component and E2E tests for all new UI components and linking workflows.

#### Acceptance Criteria

- [ ] Unit tests for LinkedArtifactsSection component
  - Renders linked artifacts
  - Delete button triggers confirmation
  - "Link" button opens dialog
  - Empty state displays correctly
- [ ] Unit tests for ArtifactLinkingDialog
  - Search input works
  - Filter by type works
  - Select artifact works
  - Create link button calls API
  - Error handling works
- [ ] Unit tests for tools filter
  - Multi-select works
  - Filter updates results
  - URL parameters set correctly
- [ ] E2E tests for complete workflows
  - View artifact → see linked artifacts
  - Click to navigate linked artifact
  - Delete link → removed from UI
  - Add link → dialog opens → search → select → create
  - Verify link persisted (reload page)
- [ ] ContentPane tests
  - Raw frontmatter excluded when FrontmatterDisplay active
  - Content body displays correctly
  - No duplicate frontmatter
- [ ] Coverage: >80% for new components
- [ ] No flaky tests

#### Test Structure

```typescript
// LinkedArtifactsSection.test.tsx
describe('LinkedArtifactsSection', () => {
  it('renders linked artifacts', () => {
    const { getByText } = render(
      <LinkedArtifactsSection
        artifactId="123"
        linkedArtifacts={[{ artifact_name: 'test-skill', ... }]}
      />
    );
    expect(getByText('test-skill')).toBeInTheDocument();
  });

  it('opens dialog when Add Link clicked', async () => {
    const { getByRole } = render(
      <LinkedArtifactsSection artifactId="123" />
    );
    fireEvent.click(getByRole('button', { name: /add link/i }));
    expect(getByRole('dialog')).toBeInTheDocument();
  });

  // ... more tests
});

// artifact-linking.e2e.ts (Playwright)
test('complete linking workflow', async ({ page }) => {
  await page.goto('/artifacts/abc-123');

  // Click add link
  await page.click('button:has-text("Add Link")');

  // Search for artifact
  await page.fill('input[placeholder="Search artifacts"]', 'python');
  await page.waitForSelector('text=python-utils');

  // Select and link
  await page.click('text=python-utils');
  await page.click('button:has-text("Create Link")');

  // Verify link appears
  await expect(page.locator('text=python-utils')).toBeVisible();
});
```

#### Definition of Done

- [ ] All component tests passing
- [ ] >80% coverage for new components
- [ ] E2E tests verify complete workflows
- [ ] Edge cases covered
- [ ] No flaky tests
- [ ] Performance acceptable

---

## Phase 3 Quality Gates

Before proceeding to Phase 4, verify:

### UI Components
- [ ] ContentPane properly excludes raw frontmatter
- [ ] LinkedArtifactsSection renders all states (loaded, empty, error)
- [ ] ArtifactLinkingDialog search/filter/select working
- [ ] Tools filter integrated and functional
- [ ] All interactions responsive and smooth

### Accessibility
- [ ] WCAG 2.1 AA compliant (Axe audit <2 violations)
- [ ] Keyboard navigation works (Tab, Arrow keys, Enter, Escape)
- [ ] Screen reader friendly (ARIA labels present)
- [ ] Focus management correct

### Testing
- [ ] >80% code coverage for new components
- [ ] All component tests passing
- [ ] E2E tests verify critical workflows
- [ ] No flaky tests
- [ ] Performance targets met

### Integration
- [ ] All API calls working correctly
- [ ] Optimistic UI updates functional
- [ ] Error handling user-friendly
- [ ] Loading states displayed

### Documentation
- [ ] Component PropTypes documented
- [ ] Usage examples provided
- [ ] Component stories created (Storybook)

---

## Risk Assessment

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| API calls fail or timeout | Medium | High | Error boundaries, retry logic, fallback UI |
| Search performance degrades | Low | Medium | Debounce, pagination, caching |
| Accessibility issues | Low | Medium | Axe audit, keyboard testing, ARIA review |
| Mobile responsiveness broken | Low | Medium | Responsive testing on multiple devices |

### UX Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Users don't understand linking | Medium | Medium | Clear labels, help text, documentation |
| Dialog too complex | Low | Medium | Simplify UX, user testing, iterative refinement |
| Performance feels sluggish | Low | Medium | Optimize queries, add loading states |

---

## Success Criteria Summary

**UI Components**: All new components render correctly and are fully functional
**Workflows**: Manual linking workflow <30 seconds from start to finish
**Accessibility**: WCAG 2.1 AA compliant with no keyboard navigation issues
**Testing**: >80% coverage with all critical workflows E2E tested
**Performance**: No load time increase vs baseline, filter updates within 500ms

---

## Next Steps

Once Phase 3 is complete:
1. Begin Phase 4: Polish, Validation & Deployment
2. Phase 3 enables: Full feature usable end-to-end
3. Ready for: Performance testing, regression testing, deployment
