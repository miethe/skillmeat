---
title: Memory Inbox User Guide
description: How to use the Memory Inbox to triage and manage project knowledge in SkillMeat
audience: [users]
tags: [memory, knowledge-management, triage, context, workflows]
created: 2026-02-06
updated: 2026-02-06
category: user-guide
status: published
related:
  - docs/user/guides/web-ui-guide.md
  - docs/project_plans/PRDs/features/memory-context-system-v1.md
---

# Memory Inbox User Guide

The Memory Inbox helps you capture, review, and manage knowledge from your AI agent sessions. Instead of losing important learnings in chat history, the Memory Inbox lets you triage extracted items, approve them for reuse, and organize project knowledge systematically.

## What Is the Memory Inbox?

The Memory Inbox is your command center for managing project memory items—atomic pieces of knowledge captured during AI agent workflows:

- **Constraints**: Rules and limitations ("API key must be refreshed every 3600 seconds")
- **Decisions**: Design choices made during implementation ("Use TanStack Query for server state")
- **Gotchas/Fixes**: Workarounds and bug resolutions ("list_id comes from URL path, not body")
- **Patterns/Learnings**: Reusable structures and discovered insights
- **Learnings**: Discovered insights ("React 19 requires async client components")
- **Style Rules**: Code style preferences ("Use named exports, not default exports")

Each memory item has a confidence score (0-100%), lifecycle status, and provenance tracking who created it and when.

## Accessing the Memory Inbox

### From the Project View

1. Open any project in SkillMeat
2. Navigate to the **Memory** section (in the project sidebar or navigation)
3. The Memory Inbox page appears with all memory items for this project

**Note**: Memory items are project-scoped. Each project has its own inbox.

## Understanding the Inbox Interface

### Page Layout

```
+--------------------------------------------------------------------+
| Breadcrumb: Projects > [Project Name] > Memory                     |
|                                                                    |
| [h1] Memory                          [+ Create Memory] [Settings]  |
+--------------------------------------------------------------------+
| [All] [Constraints] [Decisions] [Fixes] [Patterns] [Learnings]    |
| Status: [All Statuses v]  Sort: [Newest First v]   Search: [____] |
+--------------------------------------------------------------------+
| [ ] Confidence | Type      | Content Preview                       |
|     bar        |           |                                       |
| +--------------------------------------------------------------+   |
| | [x] ||| [Constraint] Don't use default exports...            |   |
| |     |||  87% | 2h ago | Used 3x                              |   |
| +--------------------------------------------------------------+   |
| | [ ] ||| [Fix] API requires list_id in URL path...           |   |
| |     |||  92% | 1d ago | Used 7x                              |   |
| +--------------------------------------------------------------+   |
```

### Header Area

- **Project Name** breadcrumb navigation
- **Create Memory** button: Add new memory items manually
- **Settings** button: Configure memory system behavior (coming soon)

### Type Tabs

Filter memory items by type. Each tab shows a count badge:

- **All**: All memory types combined
- **Constraints**: Rules and limitations
- **Decisions**: Design choices
- **Fixes**: Bug fixes and workarounds
- **Patterns**: Reusable code patterns
- **Learnings**: Insights and discoveries
- **Style Rules**: Code style preferences

Click any tab to filter to that type. The count updates as you filter.

### Filter Controls

- **Status Dropdown**: Filter by lifecycle status
  - **All Statuses**: Show everything
  - **Candidate**: Newly extracted items awaiting review
  - **Active**: Approved items being used
  - **Stable**: High-confidence, battle-tested items
  - **Deprecated**: Outdated items no longer used

- **Sort Dropdown**: Change ordering
  - **Newest First**: Most recently created (default)
  - **Oldest First**: Earliest created
  - **Highest Confidence**: Sort by confidence score (100% → 0%)
  - **Lowest Confidence**: Sort by confidence score (0% → 100%)
  - **Most Used**: Sort by access count

- **Search Box**: Type keywords to filter content
  - Searches memory content text
  - Updates results as you type
  - Clear with X button or Escape key

### Memory Card Structure

Each card in the list shows:

```
[Checkbox] [Confidence Bar] [Type Badge] Content preview text...
                            87% | 2 hours ago | Used 3x | session-abc | active
```

1. **Checkbox**: Select for bulk actions
2. **Confidence Bar**: Vertical 3px color-coded bar
   - Green: 85%+ (high confidence)
   - Yellow/Amber: 60-84% (medium confidence)
   - Red: <60% (low confidence)
3. **Type Badge**: Colored pill with icon and type label
4. **Content Preview**: First 2 lines of memory text
5. **Metadata Row**: Confidence %, relative time, usage count, source, status dot

### Action Buttons (Hover/Focus)

When you hover over or focus on a card, action buttons appear on the right:

- **✓ Approve** (green checkmark): Promote memory to next lifecycle stage
- **✎ Edit** (pencil): Open edit dialog
- **✗ Reject** (red X): Deprecate/dismiss memory

## Triaging Memories

Triage is the primary workflow: review candidate items and decide to approve, edit, or reject them.

### Approving a Memory

Approving promotes a memory through its lifecycle: Candidate → Active → Stable.

**Using the Mouse:**

1. Hover over a memory card
2. Click the green **✓ Approve** button
3. Memory status updates immediately
4. Card remains in list (filter by status to see active items)

**Using the Keyboard:**

1. Navigate to a memory with **J** (down) or **K** (up)
2. Press **A** to approve the focused memory
3. Memory is promoted immediately

**What Happens:**
- Candidate → Active: Item is now available for context injection
- Active → Stable: Item is marked as battle-tested (requires 2+ uses)
- Stable: Already at highest status, no change

### Rejecting a Memory

Rejecting deprecates a memory, marking it outdated or incorrect.

**Using the Mouse:**

1. Hover over a memory card
2. Click the red **✗ Reject** button
3. Confirmation dialog appears
4. Click **Reject** to confirm
5. Memory status changes to "deprecated"

**Using the Keyboard:**

1. Navigate to a memory with **J** or **K**
2. Press **R** to reject
3. Confirmation dialog opens
4. Press **Enter** to confirm or **Escape** to cancel

**What Happens:**
- Memory status changes to "deprecated"
- It no longer appears in context packs
- You can still filter to see it (Status: Deprecated)
- You can restore it by editing status back to Active

### Editing a Memory

Edit to fix typos, clarify content, adjust confidence, or change type.

**Using the Mouse:**

1. Hover over a memory card
2. Click the **✎ Edit** button
3. Edit dialog opens

**Using the Keyboard:**

1. Navigate to a memory with **J** or **K**
2. Press **E** to open edit dialog

**In the Edit Dialog:**

- **Type**: Change memory type (Constraint, Decision, etc.)
- **Content**: Edit the memory text (supports multi-line)
- **Confidence**: Adjust 0-100% slider or type exact value
- **Status**: Manually set status (Candidate, Active, Stable, Deprecated)

Click **Save** or press **Ctrl+Enter** to save changes. Click **Cancel** or press **Escape** to discard.

**What Happens:**
- Changes save immediately
- Memory updates in the list
- Provenance tracks who edited and when

### Viewing Full Details

Click any memory card (or press **Enter** with keyboard focus) to open the detail panel on the right.

**Detail Panel Sections:**

1. **Header**:
   - Type badge and status indicator
   - Back/close buttons

2. **Content**:
   - Full memory text (no truncation)
   - Formatted with proper line breaks

3. **Confidence**:
   - Large percentage display
   - Visual progress bar (color-coded by tier)

4. **Provenance** (collapsible):
   - **Source**: How memory was created (manual, auto-extracted, etc.)
   - **Session**: Session ID if extracted from agent run
   - **Extracted**: Timestamp of extraction
   - **Files**: Related files mentioned
   - **Commit**: Git commit SHA if applicable

5. **Access Stats**:
   - Usage count ("Used 7 times")
   - Last used timestamp

6. **Timestamps**:
   - Created date
   - Updated date
   - Deprecated date (if applicable)

7. **Footer Actions**:
   - **Edit**: Open edit dialog
   - **Approve**: Promote memory
   - **Reject**: Deprecate memory
   - **More Menu** (⋯): Additional actions
     - **Merge**: Consolidate with duplicate
     - **Deprecate**: Mark as outdated

**Keyboard Shortcuts in Detail Panel:**

- **Escape**: Close detail panel and return to list
- **E**: Edit memory
- **A**: Approve memory
- **R**: Reject memory

## Bulk Actions

Select multiple memories to perform batch operations.

### Selecting Memories

**Using Checkboxes:**

1. Click the checkbox on each memory card
2. Selected cards highlight with blue background
3. Batch action bar appears at bottom

**Using Keyboard:**

1. Navigate to a memory with **J** or **K**
2. Press **Space** to toggle selection
3. Repeat to select multiple memories
4. Press **Ctrl+A** to select all visible memories

**Clearing Selection:**

- Click **Clear Selection** in batch action bar
- Press **Escape** with no detail panel open

### Batch Approve

Approve multiple memories at once.

1. Select 2+ memories using checkboxes or keyboard
2. Batch action bar shows count: "3 items selected"
3. Click **Approve All** button
4. All selected items are promoted
5. Selection clears automatically
6. Items remain in list with updated status

**Use Case**: Quickly approve 5-10 high-quality candidate items after a review session.

### Batch Reject

Reject multiple memories at once.

1. Select 2+ memories
2. Click **Reject All** in batch action bar
3. Confirmation dialog appears
4. Click **Reject** to confirm
5. All selected items move to deprecated status
6. Selection clears

**Use Case**: Clean up low-confidence candidates or obsolete items after a refactoring.

## Merging Duplicate Memories

Sometimes the system extracts similar memories. Use the merge feature to consolidate duplicates.

### Identifying Duplicates

Look for:
- Similar content with different wording
- Same constraint/decision captured multiple times
- Overlapping learnings from different sessions

### Merging Memories

1. **Select source memory** (the one to keep)
2. Open detail panel or hover to reveal **More Menu** (⋯)
3. Click **Merge** from the menu
4. Merge dialog opens

**In the Merge Dialog:**

1. **Source Memory**: Pre-selected (the one you chose)
2. **Target Selection**:
   - Search box to filter candidates
   - List of similar memories (sorted by content similarity)
   - Preview each target's full content
3. **Select target** (the memory to merge into source)
4. **Preview Result**:
   - Combined content (source content wins by default)
   - Higher of the two confidence scores
   - Combined access counts
5. Click **Merge** to confirm

**What Happens:**
- Target memory is deprecated
- Source memory gains target's access count
- Confidence updates to higher value
- Provenance tracks the merge action

**Important**: Merging cannot be undone. Always preview before confirming.

## Keyboard Shortcuts

The Memory Inbox is designed for keyboard-first triage.

### Navigation

| Key | Action |
|-----|--------|
| `J` | Move focus down to next memory |
| `K` | Move focus up to previous memory |
| `Enter` | Open detail panel for focused memory |
| `Escape` | Close detail panel or clear selection |

### Triage Actions

| Key | Action |
|-----|--------|
| `A` | Approve (promote) focused memory |
| `E` | Edit focused memory |
| `R` | Reject (deprecate) focused memory |
| `M` | Merge focused memory |

### Selection

| Key | Action |
|-----|--------|
| `Space` | Toggle selection for focused memory |
| `Ctrl+A` | Select all visible memories |

### Quick Access

| Key | Action |
|-----|--------|
| `?` | Show keyboard shortcuts help modal |

**Tip**: Keep one hand on the home row (J/K/A/E/R) for fast triage without touching the mouse.

### Keyboard Shortcuts Help

Press **?** anytime to open the Keyboard Shortcuts Help modal. It shows all shortcuts organized by category with visual key representations.

## Creating Memories Manually

While most memories are auto-extracted from agent sessions, you can create them manually.

### Creating a New Memory

1. Click **+ Create Memory** in the page header
2. Create Memory dialog opens

**Form Fields:**

- **Type** (required): Select from dropdown
  - Constraint, Decision, Fix, Pattern, Learning, Style Rule
- **Content** (required): Enter memory text
  - Multi-line text area
  - 10-5000 characters
  - Describe the knowledge clearly and concisely
- **Confidence** (optional): Set 0-100% slider
  - Default: 80%
  - Use higher values (85%+) for verified items
  - Use lower values (60-70%) for tentative items
- **Status** (optional): Choose lifecycle status
  - Default: Candidate (requires review)
  - Set to Active to skip review
  - Set to Stable for pre-verified knowledge

**Saving:**

- Click **Create** or press **Ctrl+Enter**
- Memory appears in inbox immediately
- Filter to status "Candidate" to see it (if you used default)

**Use Case**: Manually record critical constraints discovered during debugging before you forget them.

## Managing Memory Status

### Lifecycle Stages

Memories progress through stages based on usage and validation:

```
Candidate → Active → Stable
    ↓
Deprecated (optional exit)
```

1. **Candidate**: Newly created or extracted; awaiting review
2. **Active**: Approved for use; included in context packs
3. **Stable**: Battle-tested; high confidence (typically 85%+)
4. **Deprecated**: Outdated or incorrect; excluded from context

**Transitions:**

- **Candidate → Active**: Manual approval (click Approve or press A)
- **Active → Stable**: Manual promotion (Approve again) or automatic after 2+ uses
- **Any → Deprecated**: Manual rejection (click Reject/Deprecate)
- **Deprecated → Active**: Edit memory and change status back to Active

### Status Indicators

In the memory list:
- **Colored dot** next to status label
  - 🟡 Amber: Candidate
  - 🟢 Green: Active
  - 🔵 Blue: Stable
  - ⚪ Gray: Deprecated

In the detail panel:
- **Status badge** with dot and label at top

### Filtering by Status

Use the **Status** dropdown in the filter bar:

- **All Statuses**: See everything (default)
- **Candidate**: Review queue for new items
- **Active**: Currently in use
- **Stable**: High-confidence, proven items
- **Deprecated**: Historical/outdated items

**Recommended Workflow:**

1. Start with Status: Candidate (your review queue)
2. Approve high-quality items → they move to Active
3. After a few days, check Status: Active → promote top items to Stable
4. Periodically check Status: Deprecated → delete if no longer needed

## Understanding Confidence Scores

Confidence indicates how reliable a memory is (0-100%).

### Confidence Tiers

- **High (85-100%)**: Verified, battle-tested knowledge
  - Green bar and text
  - Example: "Python 3.9+ required for this project" (proven fact)

- **Medium (60-84%)**: Reasonable confidence, needs validation
  - Yellow/Amber bar and text
  - Example: "API timeout might be 30s" (likely, not confirmed)

- **Low (<60%)**: Tentative, experimental knowledge
  - Red bar and text
  - Example: "Consider using Redis for caching" (suggestion, not decision)

### Setting Confidence

**Auto-Extracted Memories:**
- System assigns confidence based on:
  - Frequency (how many times mentioned)
  - Recency (recent discoveries score higher)
  - Source quality (agent vs. manual)

**Manual Memories:**
- You set confidence when creating
- Adjust via Edit dialog if confidence changes
- Increase after validation
- Decrease if uncertainty grows

**Best Practices:**

- Start with 80% for manually created items
- Raise to 90%+ after confirming accuracy
- Lower to 60-70% for "nice to have" tips
- Drop to <50% for deprecated items before removing

## Search and Filtering

### Text Search

The search box filters memory content in real-time.

**How to Search:**

1. Click the search box (or press **/** to focus)
2. Type keywords (e.g., "api", "timeout", "authentication")
3. Results filter as you type
4. Case-insensitive matching
5. Clear with **X** button or **Escape**

**What It Searches:**
- Memory content text (full text, not just preview)
- Type labels (searching "constraint" shows all constraints)

**Search Tips:**

- Use specific terms: "API key rotation" vs. "API"
- Combine with filters: Search "timeout" + Type: Constraint
- Search partial words: "auth" matches "authentication"

### Combining Filters

Stack filters for powerful discovery:

**Example 1: High-Confidence Constraints**
- Type: Constraints
- Status: Active or Stable
- Sort: Highest Confidence
- Result: All verified rules and limitations

**Example 2: Recent Fixes**
- Type: Fixes
- Status: All Statuses
- Sort: Newest First
- Result: Latest bug fixes and workarounds

**Example 3: Review Queue**
- Status: Candidate
- Sort: Highest Confidence
- Result: Best new items needing approval, sorted by quality

## Accessibility Features

The Memory Inbox is designed for full keyboard and screen reader accessibility.

### Keyboard Navigation

- **Fully keyboard-operable**: No mouse required for any action
- **Roving tabindex**: J/K navigation with visible focus indicators
- **Focus trapping**: Modals trap focus until dismissed
- **Escape handling**: Escape key always closes top modal/panel

### Screen Reader Support

- **ARIA labels**: All interactive elements labeled
- **Role attributes**: Proper semantic roles (grid, row, complementary)
- **Live regions**: Status updates announced ("Memory approved")
- **Helpful descriptions**: Context for each action button

**Screen Reader Tips:**

- Cards announce: "Memory item: Constraint, 87% confidence, Active"
- Action buttons announce: "Approve memory: Don't use default exports..."
- Status changes announced: "Memory promoted to Active"

### Visual Accessibility

- **High contrast**: Confidence colors meet WCAG AA standards
  - Green: `#059669` (emerald-600)
  - Yellow: `#d97706` (amber-600)
  - Red: `#dc2626` (red-600)
- **Focus indicators**: Clear blue ring on focused elements
- **Sufficient text size**: Minimum 12px (0.75rem) for metadata, 14px (0.875rem) for content
- **Color not sole indicator**: Confidence shown as % text + color bar

### Reduced Motion

The interface respects `prefers-reduced-motion`:
- Detail panel slides reduced to fade
- Hover transitions disabled
- Focus changes instant instead of animated

## Tips and Best Practices

### Inbox Zero Strategy

Keep your review queue small:

1. **Daily Triage**: Spend 5 minutes reviewing new Candidates
2. **Approve Quickly**: High-confidence items → Approve immediately
3. **Reject Low-Quality**: <60% confidence + vague content → Reject
4. **Edit When Close**: 70%+ confidence but needs tweaks → Edit then Approve
5. **Use Bulk Actions**: Select 5-10 items, batch approve/reject

**Goal**: Keep Candidate count <20 at all times.

### Confidence Guidelines

**When to Use High Confidence (85%+):**
- Verified facts: "Python 3.9+ required"
- Proven constraints: "API key expires in 3600s"
- Battle-tested patterns: "Always validate with Zod"

**When to Use Medium Confidence (60-84%):**
- Reasonable assumptions: "Timeout likely 30s"
- Unverified tips: "Consider caching with Redis"
- Documented recommendations: "Prefer named exports"

**When to Use Low Confidence (<60%):**
- Experimental ideas: "Maybe use WebSockets?"
- Uncertain workarounds: "Tried restarting server, seemed to help"
- Deprecated items: Old information kept for reference

### Organizing by Type

Use type tags consistently:

- **Constraint**: Hard rules, blockers, limitations
- **Decision**: Architectural choices, design decisions
- **Fix**: Bug resolutions, workarounds, patches
- **Pattern**: Reusable code structures, templates
- **Learning**: New insights, discoveries, gotchas
- **Style Rule**: Code style, formatting, conventions

**If Uncertain:**
- "Can't do X" → Constraint
- "We chose Y" → Decision
- "Solved Z by..." → Fix
- "Always do W" → Pattern
- "Discovered that..." → Learning
- "Format code with..." → Style Rule

### Merging Strategy

**When to Merge:**
- Exact duplicates with different wording
- Same constraint mentioned twice
- Overlapping learnings from different sessions

**When NOT to Merge:**
- Related but distinct items ("API timeout" vs. "API retry logic")
- Same topic, different contexts ("React hooks in components" vs. "React hooks in custom hooks")
- Different confidence levels with conflicting info (keep higher confidence)

**Before Merging:**
- Read both memories fully
- Check provenance (different sources = might be different contexts)
- Preview result to ensure combined content makes sense

### Batch vs. Individual Actions

**Use Individual Actions When:**
- Reviewing 1-5 items carefully
- Need to read full content before deciding
- Different actions for different items (approve some, edit others)

**Use Batch Actions When:**
- 10+ similar items (all approve or all reject)
- Clear quality distinction (high confidence batch, low confidence batch)
- Cleaning up after auto-extraction (bulk reject noise)

**Workflow Example:**
1. Filter: Status: Candidate, Sort: Highest Confidence
2. Review top 5 individually (approve, edit, or skip)
3. Select next 10 (70-80% confidence)
4. Batch approve all 10
5. Scroll to bottom (50-60% confidence)
6. Select all low-confidence items
7. Batch reject

## Troubleshooting

### Memory Won't Approve

**Problem**: Clicked Approve but status didn't change.

**Solutions:**
- Check browser console (F12) for errors
- Refresh the page and try again
- Verify you have edit permissions on the project
- Check network connection (API call might have failed)

### Detail Panel Won't Close

**Problem**: Pressed Escape but panel is still open.

**Solutions:**
- Click the X button in panel header
- Click the back arrow button
- Refresh the page
- Check if a modal is open on top (close modal first)

### Keyboard Shortcuts Not Working

**Problem**: Pressing J/K/A/E/R does nothing.

**Solutions:**
- Click anywhere in the memory list to focus the container
- Close any open modals (shortcuts disabled when modals open)
- Check if search box has focus (press Escape to unfocus)
- Refresh the page
- Try mouse actions to verify the memory is interactive

### Search Returns No Results

**Problem**: Searched for a keyword but no memories appear.

**Solutions:**
- Check spelling
- Try partial word: "auth" instead of "authentication"
- Clear other filters (Type, Status) that might exclude results
- Check if memory content actually contains that word
- Try searching a different word from the same memory

### Confidence Score Wrong

**Problem**: Auto-extracted memory has unrealistic confidence.

**Solutions:**
- Edit the memory and adjust confidence manually
- If consistently wrong, report feedback via Settings → Support
- For now, manually adjust all auto-extracted items after review

### Missing Provenance

**Problem**: Memory shows "No provenance data available."

**Solutions:**
- Manually created memories have no provenance (expected)
- Auto-extracted memories should have provenance (bug if missing)
- Check the creation date: old memories might predate provenance tracking
- Provenance is optional; memory still works without it

## See Also

- [Memory & Context Intelligence Guide](./memory-context-system.md) - Overview and workflow map
- [Context Modules Guide](./context-modules.md) - Build reusable context packs
- [Web UI Guide](./web-ui-guide.md) - Complete web interface reference
- [Context Entities Guide](./context-entities.md) - Managing context files and entities
- [Tags User Guide](./tags-user-guide.md) - Organizing artifacts with tags
- [Memory & Context System PRD](../../project_plans/PRDs/features/memory-context-system-v1.md) - Technical details and architecture
