---
type: progress
prd: tags-refactor-v1
phase: 5-6
title: Frontend - UI Components and Tag Filtering
status: pending
completed_at: null
progress: 0
total_tasks: 10
completed_tasks: 0
total_story_points: 16
completed_story_points: 0

tasks:
  - id: UI-001
    title: Tag Input Design
    description: Design tag input component spec (shadcn.io style, not shadcn/ui)
    status: pending
    story_points: 2
    assigned_to:
      - ui-engineer-enhanced
    dependencies:
      - API-005
    created_at: "2025-12-18"

  - id: UI-002
    title: Tag Input Component
    description: Implement TagInput component with all features
    status: pending
    story_points: 3
    assigned_to:
      - ui-engineer-enhanced
    dependencies:
      - UI-001
    created_at: "2025-12-18"

  - id: UI-003
    title: Tag Badge Component
    description: Update Badge component for tag display with colors
    status: pending
    story_points: 1
    assigned_to:
      - ui-engineer-enhanced
    dependencies:
      - UI-002
    created_at: "2025-12-18"

  - id: UI-004
    title: Parameter Editor Integration
    description: Integrate TagInput into ParameterEditorModal
    status: pending
    story_points: 2
    assigned_to:
      - frontend-developer
    dependencies:
      - UI-003
    created_at: "2025-12-18"

  - id: UI-005
    title: Tag Display in Detail View
    description: Show tags on artifact detail view (read-only)
    status: pending
    story_points: 1
    assigned_to:
      - frontend-developer
    dependencies:
      - UI-004
    created_at: "2025-12-18"

  - id: UI-006
    title: Accessibility
    description: Implement WCAG 2.1 AA features
    status: pending
    story_points: 1
    assigned_to:
      - ui-engineer-enhanced
    dependencies:
      - UI-005
    created_at: "2025-12-18"

  - id: FILTER-001
    title: Tag Filter Popover
    description: Create popover showing all tags with artifact counts
    status: pending
    story_points: 2
    assigned_to:
      - ui-engineer-enhanced
    dependencies:
      - UI-006
    created_at: "2025-12-18"

  - id: FILTER-002
    title: Tag Filter Button
    description: Add tag filter button to artifact views (collections, search)
    status: pending
    story_points: 2
    assigned_to:
      - ui-engineer-enhanced
    dependencies:
      - FILTER-001
    created_at: "2025-12-18"

  - id: FILTER-003
    title: Filter Integration
    description: Integrate tag filtering with artifact list queries
    status: pending
    story_points: 2
    assigned_to:
      - frontend-developer
    dependencies:
      - FILTER-002
    created_at: "2025-12-18"

  - id: FILTER-004
    title: Dashboard Tags Widget
    description: Add tag metrics to analytics dashboard
    status: pending
    story_points: 2
    assigned_to:
      - frontend-developer
    dependencies:
      - FILTER-003
    created_at: "2025-12-18"

parallelization:
  batch_1:
    - UI-001
  batch_2:
    - UI-002
  batch_3:
    - UI-003
  batch_4:
    - UI-004
  batch_5:
    - UI-005
  batch_6:
    - UI-006
  batch_7:
    - FILTER-001
  batch_8:
    - FILTER-002
  batch_9:
    - FILTER-003
  batch_10:
    - FILTER-004

context_files:
  - skillmeat/web/components/
  - skillmeat/web/hooks/
  - skillmeat/web/lib/api/

blockers: []
notes: "Frontend implementation for tags system. Phases 5-6 build UI components and filtering. Depends on API-005 completion."

---

# Phases 5-6: Frontend Implementation

Frontend implementation of the tags system including tag input component, badge display, and tag-based filtering UI. This section brings the complete tag feature to the user interface.

**Total Duration**: 6 days
**Total Story Points**: 16
**Dependencies**: Phase 4 (API-005) complete
**Assigned Agents**: ui-engineer-enhanced, frontend-developer

---

## Phase 5: Frontend UI - Tag Input Component & Integration

**Duration**: 3 days
**Story Points**: 10
**Objective**: Create TagInput component and integrate tags into artifact editing and viewing.

### UI-001: Tag Input Design (2 pts)

```markdown
Task("ui-engineer-enhanced", "UI-001: Design tag input component specification

Deliverable: Design specification document (Figma mockup or detailed wireframe)

Component: TagInput
Inspiration: shadcn.io registry style (NOT shadcn/ui library)
Reference: https://www.shadcn.io/registry/tags.json for styling patterns

Design specification should include:

1. Visual States
   - Default: empty input with placeholder
   - Focused: input border highlight, suggestion dropdown
   - Typing: search results showing below input
   - Tags added: badges displayed above/left of input
   - Readonly: disabled state for view-only mode

2. Interaction Patterns
   - Type to search existing tags or create new
   - Press Enter to add tag (new or existing)
   - Press Backspace/Delete to remove last tag
   - Click 'x' on badge to remove tag
   - Arrow keys to navigate suggestions
   - Escape to close dropdown

3. Accessibility Features
   - Full keyboard navigation (no mouse required)
   - ARIA labels for input and suggestions
   - ARIA live region for added/removed tags
   - Focus visible on all interactive elements
   - Semantic HTML structure

4. Copy-Paste Support
   - Support pasting comma-separated tags
   - Strip whitespace from pasted values
   - Handle edge cases (quotes, special chars)

5. Visual Design
   - Badges with colored backgrounds (use tag colors)
   - Rounded corners (border-radius: 0.375rem / 6px)
   - Icons: X icon for remove, search icon for input
   - Responsive width (full container width)
   - Consistent with SkillMeat design system (Tailwind + shadcn patterns)

6. Component Props (TypeScript)
   - value?: Tag[] - Current selected tags
   - onChange?: (tags: Tag[]) => void - Change handler
   - onCreateTag?: (name: string) => Promise<Tag> - Create new tag
   - onSearchTags?: (query: string) => Promise<Tag[]> - Search tags
   - disabled?: boolean - Disable input
   - placeholder?: string - Input placeholder text
   - maxTags?: number - Limit number of tags
   - allowCreate?: boolean - Allow creating new tags

Design should show:
- Component rendered in different states
- Interaction flow with annotations
- Keyboard shortcut legend
- Copy-paste example
- Mobile responsive behavior")
```

### UI-002: Tag Input Component (3 pts)

```markdown
Task("ui-engineer-enhanced", "UI-002: Implement TagInput React component

File: skillmeat/web/components/ui/tag-input.tsx (new)

Implement React functional component:

export interface Tag {
  id: number;
  name: string;
  slug: string;
  color: string;
  created_at: string;
  updated_at: string;
}

export interface TagInputProps {
  value?: Tag[];
  onChange?: (tags: Tag[]) => void;
  onCreateTag?: (name: string) => Promise<Tag>;
  onSearchTags?: (query: string) => Promise<Tag[]>;
  disabled?: boolean;
  placeholder?: string;
  maxTags?: number;
  allowCreate?: boolean;
  className?: string;
}

export const TagInput = React.forwardRef<HTMLInputElement, TagInputProps>(
  ({ ... }, ref) => { ... }
);

Component Features:

1. State Management
   - Track input value (typed text)
   - Track selected tags (array)
   - Track suggestions dropdown state
   - Track focused state

2. Input Handling
   - onChange: fetch suggestions on each keystroke
   - onKeyDown: handle Enter, Backspace, Delete, Escape, arrow keys
   - onPaste: handle comma-separated values
   - onBlur: close suggestions, validate

3. Suggestion Dropdown
   - Shows matching tags (search results)
   - Shows 'Create tag' option if allowCreate and no match
   - Keyboard navigation (up/down arrows to select)
   - Click to add tag

4. Badge Display
   - Show selected tags as removable badges
   - Color from tag.color field
   - X icon to remove
   - Responsive layout

5. Keyboard Shortcuts
   - Enter: Add selected suggestion or create new
   - Backspace/Delete on empty input: Remove last tag
   - Escape: Close suggestions
   - ArrowUp/Down: Navigate suggestions
   - Tab: Accept suggestion and move to next field

6. Copy-Paste Handling
   - Paste comma-separated tags (e.g., 'python, fastapi, async')
   - Strip whitespace
   - Try to match existing tags first
   - Create new if allowCreate and no match

7. Validation
   - Prevent duplicate tags (same tag twice)
   - Respect maxTags limit
   - Trim and normalize tag names

Component Tests:
- Render with empty value
- Add tag by typing and Enter
- Add tag by clicking suggestion
- Remove tag by clicking X
- Remove tag by Backspace on empty
- Copy-paste multiple tags
- Search functionality
- Create new tag
- Keyboard navigation
- Accessibility (keyboard only, no mouse)
- Mobile responsive

Use Tailwind CSS for styling, matching SkillMeat design system")
```

### UI-003: Tag Badge Component (1 pt)

```markdown
Task("ui-engineer-enhanced", "UI-003: Update Badge component for tag display

File: skillmeat/web/components/ui/badge.tsx (update existing)

Current Badge Component Issues:
- No color support beyond predefined variants
- Need to support dynamic hex colors from tag.color field
- Need to support 'x' remove button in edit mode

Update to support:

1. Color Variants
   - Keep existing variants (default, secondary, destructive, outline)
   - Add dynamic background color from hex (tag.color)
   - Use appropriate text color (white/black) based on background luminance
   - Apply proper contrast ratio (WCAG AA: 4.5:1)

2. Remove Button (Optional)
   - Add onRemove prop for remove callback
   - Show X icon only if onRemove provided
   - Click X to trigger callback and remove

3. Props Update
   interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
     variant?: 'default' | 'secondary' | 'destructive' | 'outline';
     bgColor?: string; // hex color like '#FF5733'
     onRemove?: () => void; // callback for remove button
     removable?: boolean; // show remove button if true
     icon?: React.ReactNode; // optional icon before text
   }

4. Updated Component Usage Examples
   - Default badge: <Badge>Default</Badge>
   - With color: <Badge bgColor=\"#FF5733\">Colored</Badge>
   - Removable: <Badge bgColor=\"#FF5733\" onRemove={() => ...}>Remove me</Badge>
   - In tag display: <Badge bgColor={tag.color} onRemove={() => removeTag(tag.id)}>{tag.name}</Badge>

5. Styling Details
   - Rounded corners: border-radius: 0.375rem (6px)
   - Padding: px-2.5 py-0.5
   - Font size: text-xs font-medium
   - Remove icon: X symbol, clickable, hover darker
   - Remove button styling: hover effect, cursor pointer

6. Accessibility
   - Proper color contrast
   - ARIA labels for interactive elements
   - Remove button is keyboard accessible
   - Focus visible on remove button

Update Tests:
- Render with bgColor prop
- Dynamic text color based on background
- Remove button click
- Remove button keyboard accessible
- Contrast ratio validation
- Dark/light mode support")
```

### UI-004: Parameter Editor Integration (2 pts)

```markdown
Task("frontend-developer", "UI-004: Integrate TagInput into ParameterEditorModal

File: skillmeat/web/components/ParameterEditorModal.tsx (update)

Current State:
- ParameterEditorModal edits artifact parameters
- Does NOT currently support tags field
- Need to add tags input field

Changes:

1. Add Tags Field to Form
   - Add field for tags in the form schema
   - Position below other parameter fields
   - Label: 'Tags' or 'Artifact Tags'
   - Help text: 'Organize artifacts with searchable tags'

2. Integrate TagInput Component
   - Import TagInput from ui/tag-input.tsx
   - Wire onChange handler to form state
   - Pass selected tags to form value
   - Display tags on initial load (if editing existing artifact)

3. API Integration
   - Hook: useSearchTags() - fetch matching tags
   - Hook: useCreateTag() - create new tag if needed
   - Hook: useUpdateArtifactTags() - save tags to artifact
   - Pass these hooks to TagInput as props

4. Form Handling
   - Add tags to form submission data
   - Include in PUT/POST request to API
   - Handle API errors from tag operations
   - Show success message after save

5. Modal Updates
   - Update modal title if editing tags only
   - Adjust modal height for tags field
   - Keep existing parameter fields functional
   - Update submit button label if appropriate

6. API Endpoints Used
   - GET /api/v1/tags?search={query} - search tags
   - POST /api/v1/tags - create new tag
   - GET /api/v1/artifacts/{id}/tags - get artifact tags
   - POST /api/v1/artifacts/{id}/tags/{tag_id} - add tag
   - DELETE /api/v1/artifacts/{id}/tags/{tag_id} - remove tag

Test Scenarios:
- Load existing artifact with tags
- Add new tags via TagInput
- Remove existing tags
- Create new tag while editing
- Save and reload to verify persistence
- Keyboard navigation in TagInput
- Error handling (tag creation fails, etc)")
```

### UI-005: Tag Display in Detail View (1 pt)

```markdown
Task("frontend-developer", "UI-005: Show tags on artifact detail view

File: skillmeat/web/components/ArtifactDetail.tsx (update)

Current State:
- Artifact detail view shows artifact metadata
- Does NOT show tags
- Need to display tags in read-only mode with filtering

Changes:

1. Display Tags Section
   - Add new section on artifact detail view
   - Title: 'Tags' or 'Labels'
   - Show as colored badges using Badge component
   - Position: Below artifact metadata, above description

2. Badge Display
   - Each tag shows: <Badge bgColor={tag.color}>{tag.name}</Badge>
   - Use Tag Badge component created in UI-003
   - Colored backgrounds from tag.color field
   - Proper contrast for readability

3. Clickable Tags for Filtering
   - Make tags clickable
   - On click: filter artifact list to show artifacts with that tag
   - Update URL with tag filter parameter
   - Navigate to artifact list view with filter applied

4. Read-Only Mode
   - Tags display as view-only (no remove/edit button)
   - No TagInput component (display only)
   - Scrollable if many tags
   - Empty state: 'No tags' message if none

5. API Integration
   - Fetch artifact tags: GET /api/v1/artifacts/{id}/tags
   - Use hook: useArtifactTags(artifactId)
   - Handle loading and error states

6. Responsive Design
   - Tags wrap to multiple lines on small screens
   - Space tags appropriately
   - Maintain readability on mobile

Test Scenarios:
- Load artifact with multiple tags
- Load artifact with no tags
- Click tag to filter artifact list
- URL updates with tag filter
- Mobile responsive layout
- Error handling (tag fetch fails)")
```

### UI-006: Accessibility (1 pt)

```markdown
Task("ui-engineer-enhanced", "UI-006: Implement WCAG 2.1 AA accessibility features

Files:
  - skillmeat/web/components/ui/tag-input.tsx (update)
  - skillmeat/web/components/ui/badge.tsx (update)
  - skillmeat/web/components/ArtifactDetail.tsx (update)

WCAG 2.1 AA Requirements:

1. Keyboard Navigation
   - All interactive elements keyboard accessible
   - Tab order logical and visible
   - Focus trap in dropdown suggestions
   - Escape to close dropdowns
   - No keyboard trap (can always escape)

2. ARIA Attributes
   - Input: aria-label, aria-describedby
   - Suggestions: role=\"listbox\", aria-label
   - Tags: role=\"button\" if clickable, aria-pressed if toggled
   - Remove buttons: aria-label=\"Remove {tag name}\"
   - Live region: aria-live=\"polite\" for tag additions/removals

3. Focus Management
   - Visual focus indicator on all interactive elements
   - Focus visible on buttons, inputs, suggestions
   - Focus color: consistent with design system
   - High contrast: at least 3:1 ratio

4. Color Contrast
   - Text on tag badges: 4.5:1 minimum for normal text
   - Calculate luminance from tag.color
   - Use white or black text automatically based on background
   - Verify with axe or WAVE tools

5. Labels & Descriptions
   - Input has explicit <label> (not just placeholder)
   - Placeholder not used as only description
   - Help text associated via aria-describedby
   - Error messages associated with input

6. Screen Reader Support
   - Announce tags as they're added: \"Tag 'python' added\"
   - Announce tags as removed: \"Tag 'python' removed\"
   - Describe suggestions: \"Suggestion list, 5 items\"
   - Badge clickable: \"Link, filter by tag python\"

7. Semantic HTML
   - Use semantic elements: <button>, <input>, <ul>, <li>
   - Don't use divs for buttons
   - Use <fieldset> for related form fields
   - Proper heading hierarchy

8. Mobile & Touch
   - Touch targets: minimum 44x44 pixels
   - Adequate spacing between clickable elements
   - No hover-only interactions
   - Works with screen reader + touch

Tests (Automated & Manual):
- axe-core audit (automated)
- WAVE extension validation
- Manual keyboard-only navigation
- Screen reader testing (NVDA or JAWS)
- Mobile screen reader (iOS VoiceOver, Android TalkBack)
- Keyboard focus visible
- Color contrast verification
- Tab order verification

Document:
- List of WCAG 2.1 AA criteria met
- Test results (pass/fail)
- Known limitations (if any)
- Remediation steps for failures")
```

---

## Phase 6: Frontend UI - Tag Filtering & Dashboard

**Duration**: 3 days
**Story Points**: 6
**Objective**: Implement tag-based filtering and dashboard metrics.

### FILTER-001: Tag Filter Popover (2 pts)

```markdown
Task("ui-engineer-enhanced", "FILTER-001: Create tag filter popover component

File: skillmeat/web/components/TagFilterPopover.tsx (new)

Component: TagFilterPopover
Purpose: Shows all available tags with artifact counts, allows multi-select

Interface:

interface TagWithCount {
  id: number;
  name: string;
  slug: string;
  color: string;
  artifact_count: number;
}

interface TagFilterPopoverProps {
  tags: TagWithCount[];
  selectedTagIds: number[];
  onTagsChange: (tagIds: number[]) => void;
  isLoading?: boolean;
  error?: string;
  trigger?: React.ReactNode; // Custom trigger button
}

Features:

1. Popover Structure
   - Trigger: Filter button (icon + count of selected tags)
   - Content: Popover panel positioned below trigger
   - Close: Click outside, Escape key, or close button
   - Position: Avoid viewport edges, auto-reposition

2. Tag List Display
   - Show all available tags with counts
   - Format: '🏷️ python (24)' - tag name with artifact count
   - Color indicator: Small colored square before tag name
   - Selectable: Checkbox or click to toggle

3. Search/Filter Tags
   - Search box at top of popover
   - Search by tag name (case-insensitive)
   - Real-time filtering of tag list
   - Keyboard navigation in search

4. Multi-Select Behavior
   - Checkboxes to select multiple tags
   - Visual indicator of selection (checked state)
   - Immediate feedback on selection
   - AND logic: Show artifacts with ALL selected tags

5. Selection Controls
   - 'Select All' button (select all visible tags)
   - 'Clear All' button (deselect all tags)
   - Count display: 'X of Y tags selected'
   - Apply button (if modal-style) or immediate apply

6. Visual States
   - Hover: Tag background highlight
   - Selected: Checkmark, darker background
   - Disabled: Grayed out if 0 artifacts
   - Loading: Spinner while fetching tags
   - Empty: 'No tags available' message

7. Responsive Design
   - Popover width: 300-400px
   - Scrollable if many tags (max-height: 300px)
   - Mobile: Full-width or overlay
   - Touch-friendly: Larger tap targets (44px+)

Implementation Details:

Use Popover component from Radix UI or shadcn:
- @radix-ui/react-popover for positioning
- Keyboard handling: Escape to close
- Focus management: Auto-focus search on open

Component Tests:
- Render with tag list
- Search filters tags
- Checkbox toggles selection
- Multiple selections possible
- Select All / Clear All buttons
- Popover opens/closes
- Keyboard: Escape to close
- Keyboard: Tab navigation
- Mobile responsive
- Accessibility (screen reader, keyboard)
- Loading and error states")
```

### FILTER-002: Tag Filter Button (2 pts)

```markdown
Task("ui-engineer-enhanced", "FILTER-002: Add tag filter button to artifact views

Files:
  - skillmeat/web/components/ArtifactList.tsx (update)
  - skillmeat/web/components/SearchBar.tsx (update if applicable)
  - skillmeat/web/pages/collections/[id].tsx (update)

Components Updated:

1. Add Filter Button
   - Position: Top toolbar, near search/sort buttons
   - Icon: Filter icon (from lucide-react or custom)
   - Label: 'Tags' or 'Filter by tags'
   - Badge: Show selected tag count (e.g., 'Tags 3')

2. Filter Button Trigger
   - Click opens TagFilterPopover component
   - Button text shows: 'Filter' + selected count
   - Example: 'Tags (3)' when 3 tags selected
   - Visual: Primary or secondary variant

3. Integrations Points
   - ArtifactList.tsx: Add filter button to toolbar
   - SearchBar: Add as filter option
   - Collections page: Add to collection artifact list header

4. Visual Design
   - Button styling: Consistent with other toolbar buttons
   - Active state: Highlight when filters applied
   - Responsive: Stack on mobile or collapse to icon
   - Icon + text on desktop, icon only on mobile

5. Popover Trigger
   - Render TagFilterPopover as popover content
   - Pass selected tags state to popover
   - Handle popover open/close state

Implementation Details:

```typescript
export const FilterButton = ({ selectedCount }) => (
  <button aria-label=\"Filter by tags\">
    <FilterIcon />
    <span>{selectedCount > 0 ? \`Tags (\${selectedCount})\` : 'Tags'}</span>
  </button>
);
```

Component Tests:
- Button renders with correct label
- Badge shows selected count
- Click opens popover
- Button active state when filters applied
- Mobile responsive (icon only if needed)
- Accessibility (aria-label, keyboard accessible)")
```

### FILTER-003: Filter Integration (2 pts)

```markdown
Task("frontend-developer", "FILTER-003: Integrate tag filtering with artifact list queries

Files:
  - skillmeat/web/components/ArtifactList.tsx (update)
  - skillmeat/web/hooks/use-artifacts.ts (update/create)
  - skillmeat/web/lib/api/artifacts.ts (update/create)

Integration Requirements:

1. Filter State Management
   - Track selected tag IDs in component state or URL params
   - Use React Query for artifact list fetching
   - Update artifact list when filters change

2. URL Parameter Updates
   - Add tag_ids query param: ?tag_ids=1,2,3
   - Encode tag IDs as comma-separated list
   - Read from URL on page load
   - Persist filters when user navigates

3. API Call Modification
   - Pass selected tag_ids to artifact list endpoint
   - Example: GET /api/v1/artifacts?tag_ids=1,2,3
   - Backend filters by all tags (AND logic)
   - Results show only artifacts with ALL selected tags

4. Hook: useArtifactsWithFilter
   ```typescript
   export const useArtifactsWithFilter = (tagIds?: number[]) => {
     const query = useMemo(() => {
       const params = new URLSearchParams();
       if (tagIds?.length) {
         params.set('tag_ids', tagIds.join(','));
       }
       return params;
     }, [tagIds]);

     return useQuery({
       queryKey: ['artifacts', tagIds],
       queryFn: () => fetchArtifacts({ tag_ids: tagIds }),
       enabled: true,
     });
   };
   ```

5. ArtifactList Component Update
   - Track selected tag IDs state
   - Pass to useArtifactsWithFilter hook
   - Display artifact results
   - Show 'No artifacts with selected tags' if empty

6. Behavior
   - Update artifact list in real-time as filters change
   - Show count: 'Showing X artifacts (2 tags selected)'
   - Clear filters button to reset
   - Preserve filters on page reload (URL params)

7. Empty State
   - Message: 'No artifacts match selected tags'
   - Show which tags are selected
   - Link to clear filters or adjust selection

8. Performance
   - Debounce filter changes if needed
   - Use query key for cache invalidation
   - Don't refetch if filters unchanged

Integration Tests:
- Click tag filter updates artifact list
- URL updates with tag_ids param
- Reload page preserves filters
- Clear filters resets list
- Empty state shows correctly
- Loading state during fetch
- Error state handling
- Performance: No unnecessary fetches")
```

### FILTER-004: Dashboard Tags Widget (2 pts)

```markdown
Task("frontend-developer", "FILTER-004: Add tag metrics to analytics dashboard

File: skillmeat/web/pages/index.tsx or dashboard component (update)

Dashboard Widget: Tag Metrics

Purpose: Show tag usage statistics and insights at a glance

Widget Components:

1. Tag Distribution Chart
   - Visualization: Pie chart or horizontal bar chart
   - Data: Top 5-10 tags with artifact counts
   - Interaction: Click tag to filter artifact list
   - Labels: Tag name + count + percentage
   - Colors: Use actual tag.color values

2. Tag Statistics
   - Total tags count (e.g., '45 tags')
   - Most used tag (e.g., 'python (156 artifacts)')
   - Least used tag (e.g., '1 artifact')
   - Average artifacts per tag (e.g., '12.4')

3. Recent Tags
   - List of 5 most recently created tags
   - Format: Tag name, count, creation date
   - Link: Click to filter by tag

4. Tag Cloud (Optional)
   - Visual representation of all tags
   - Size: Based on artifact count
   - Color: From tag.color
   - Interactive: Click to filter

Implementation:

API Endpoints:
- GET /api/v1/tags/stats - Get tag statistics
- GET /api/v1/tags/top - Get top N tags by artifact count
- GET /api/v1/tags/recent - Get recently created tags

Hooks:
- useTagStats() - Get overall statistics
- useTopTags(limit=10) - Get top tags
- useRecentTags(limit=5) - Get recent tags

Component Structure:
```typescript
export const TagMetricsWidget = () => {
  const stats = useTagStats();
  const topTags = useTopTags(10);

  return (
    <Card title=\"Tag Metrics\">
      <StatCards stats={stats} />
      <TagChart tags={topTags} />
      <TagList tags={topTags} />
    </Card>
  );
};
```

3. Widget Styling
   - Card container with title and stats
   - Responsive: Full width on mobile
   - Charts responsive (recharts or similar)
   - Color-coded with tag.color values

4. Interactions
   - Click tag name to filter artifact list
   - Hover shows artifact count tooltip
   - Drill-down: Click 'View all tags' to tag management
   - Filters: Show stats for selected artifact types only

5. Responsive Design
   - Desktop: Full chart + statistics
   - Tablet: Simplified chart + key metrics
   - Mobile: Metric cards only, no chart

Widget Tests:
- Render with tag data
- Chart displays correctly
- Click tag filters artifact list
- Mobile responsive layout
- Error state (no tags)
- Loading state during fetch
- Accessibility (chart labels, keyboard navigation)
- Colors match tag.color values")
```

---

## Quality Gates

### Phase 5 - UI Components
- [ ] TagInput component renders correctly
- [ ] Tag CRUD operations work (add, remove, search)
- [ ] Copy-paste CSV support working
- [ ] Keyboard navigation functional (arrows, Backspace, Enter)
- [ ] Badge component displays colors correctly
- [ ] Parameter editor saves tags successfully
- [ ] Artifact detail view shows tags
- [ ] Component tests >80% coverage
- [ ] Accessibility requirements met (WCAG 2.1 AA)

### Phase 6 - Tag Filtering
- [ ] Tag filter popover renders correctly
- [ ] Multi-select filtering works
- [ ] Artifact lists update based on selected tags
- [ ] URL parameters preserved on reload
- [ ] Dashboard metrics display accurately
- [ ] Component tests >80% coverage
- [ ] Keyboard navigation works
- [ ] Mobile responsive
- [ ] All interactions tested

---

## Dependencies Summary

**Sequential Path** (must complete in order):
1. UI-001 → UI-002 (design then implement component)
2. UI-002 → UI-003 (component ready for use)
3. UI-003 → UI-004 (badge ready for modal integration)
4. UI-004 → UI-005 (artifact view ready)
5. UI-005 → UI-006 (accessibility pass)
6. UI-006 → FILTER-001 (UI complete)
7. FILTER-001 → FILTER-002 (popover ready)
8. FILTER-002 → FILTER-003 (filter button ready)
9. FILTER-003 → FILTER-004 (filtering complete)

**Parallelization Opportunities**:
- Limited sequential dependencies
- Can't parallelize much (each builds on previous)
- Could design UI-001 while Phase 4 API is being built
- FILTER-001 and FILTER-002 could start design in parallel

---

## Orchestration Quick Reference

### Batch 1-3: Tag Input Component (Sequential, 3 days)

```markdown
Task("ui-engineer-enhanced", "UI-001-UI-003: Design and implement tag input

UI-001: Design TagInput component specification (2 pts)
- Visual states, interactions, accessibility features
- Component props and TypeScript interface
- Design spec document with mockups

UI-002: Implement TagInput React component (3 pts)
- Full component with all features
- Keyboard shortcuts: Enter, Backspace, Arrow keys, Escape
- Copy-paste CSV support (comma-separated values)
- Search suggestions, create new tags
- Styled with Tailwind CSS

UI-003: Update Badge component (1 pt)
- Add dynamic color support from hex values
- Add optional remove button
- Proper contrast ratio (white/black text)
- Test with tag colors

File: skillmeat/web/components/ui/tag-input.tsx
File: skillmeat/web/components/ui/badge.tsx")
```

### Batch 4-6: Modal Integration (Sequential, 2 days)

```markdown
Task("frontend-developer", "UI-004-UI-006: Integrate tags and accessibility

UI-004: Add TagInput to ParameterEditorModal (2 pts)
- Wire API hooks for tag search and creation
- Form submission includes tags
- Display existing tags on edit

UI-005: Show tags in artifact detail view (1 pt)
- Display tags as read-only badges
- Clickable tags to filter artifact list
- Responsive layout

UI-006: WCAG 2.1 AA accessibility (1 pt)
- Keyboard navigation: Full support
- ARIA attributes: labels, descriptions, live regions
- Color contrast: 4.5:1 minimum
- Screen reader testing
- Focus management

Files:
  - skillmeat/web/components/ParameterEditorModal.tsx
  - skillmeat/web/components/ArtifactDetail.tsx
  - skillmeat/web/components/ui/tag-input.tsx (updates)")
```

### Batch 7-10: Tag Filtering (Sequential, 3 days)

```markdown
Task("ui-engineer-enhanced", "FILTER-001-FILTER-002: Create filter UI

FILTER-001: Tag filter popover component (2 pts)
- Shows all tags with artifact counts
- Search box for tags
- Multi-select checkboxes
- Select All / Clear All buttons
- Responsive to mobile

FILTER-002: Add filter button to artifact views (2 pts)
- Filter button in toolbar
- Badge showing selected count
- Opens TagFilterPopover on click
- Consistent styling

File: skillmeat/web/components/TagFilterPopover.tsx")
```

```markdown
Task("frontend-developer", "FILTER-003-FILTER-004: Integrate filtering and dashboard

FILTER-003: Wire tag filtering to artifact list (2 pts)
- Update artifact list when filters change
- Persist filters in URL params (?tag_ids=1,2,3)
- Reload page preserves filters
- API call includes tag_ids param

FILTER-004: Dashboard tag metrics widget (2 pts)
- Chart of top tags by artifact count
- Statistics cards (total, most used, etc.)
- Recent tags list
- Click tag to filter artifacts

Files:
  - skillmeat/web/components/ArtifactList.tsx
  - skillmeat/web/pages/index.tsx (dashboard)")
```

---

## Context Files for Implementation

**Frontend Components**:
- `skillmeat/web/components/ui/` - UI component library
- `skillmeat/web/components/` - Feature components
- `skillmeat/web/hooks/` - Custom React hooks
- `skillmeat/web/lib/api/` - API client functions

**Key Patterns**:
- React functional components with hooks
- TanStack Query v5 for data fetching
- Tailwind CSS for styling
- Radix UI for accessible primitives
- Pydantic types for API responses

**Related Rules**:
- `.claude/rules/web/api-client.md` - API client patterns
- `.claude/rules/web/hooks.md` - Hook patterns
- Accessible design for WCAG 2.1 AA compliance
