---
title: "Phase 9 Wireframe Brief"
description: "Visual wireframe specifications for SkillBOM provenance UI components"
created: 2026-03-13
phase: 9
status: complete
---

# Phase 9: Wireframe Brief

## Design System Context

SkillMeat follows a **Linear/Notion/Stripe-inspired** minimal design system:
- **Colors**: Dark sidebar (zinc-900), light content area (white/zinc-50), accent blue (blue-600)
- **Typography**: Inter font, subtle weight hierarchy (400/500/600)
- **Spacing**: Tight, information-dense layouts — not wasteful whitespace
- **Components**: Radix UI primitives via shadcn/ui — Tabs, Badge, ScrollArea, Collapsible, Tooltip, Card
- **Patterns**: Named exports, `cn()` class composition, skeleton loaders, accessible keyboard nav

## Existing UI Context

The wireframes must integrate with these existing surfaces:

### Artifact Detail Modal (`unified-entity-modal.tsx`)
- Full-screen modal with sidebar nav and content pane
- Existing tabs: Overview, Files, History, Sync, Deployments, Collections, Similar
- **ProvenanceTab goes here** as a new tab alongside History (not replacing it)

### Artifact Cards (`entity-card.tsx`, `artifact-browse-card.tsx`)
- Compact cards with name, type icon, version, tags, source badge
- **AttestationBadge goes inline** near version/source badges

### Project Dashboard (`app/dashboard/`)
- Section-based layout with cards for overview, recent activity, deployments
- **Provenance section goes here** as a new dashboard card/section

---

## Wireframe Specifications

### WF-1: ProvenanceTab (in artifact detail modal)

**Context**: New tab in the unified entity modal, rendered in the content pane area (~800px wide).

**Layout**:
```
┌─────────────────────────────────────────────────┐
│ [Overview] [Files] [History] [Provenance] [...]  │ ← tab bar
├─────────────────────────────────────────────────┤
│                                                   │
│  BOM Snapshot                    [Export JSON ↓]  │
│  ┌─────────────────────────────────────────────┐ │
│  │ Generated: 2026-03-12 14:30 UTC             │ │
│  │ Artifacts: 24 │ Signed: ✓ user@example.com  │ │
│  │ Owner: user │ Scope: local                   │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  Attestations (3)                [+ Create]       │
│  ┌─────────────────────────────────────────────┐ │
│  │ ● user attestation   2026-03-12  user scope │ │
│  │ ● team attestation   2026-03-11  team scope │ │
│  │ ● enterprise attest  2026-03-10  ent. scope │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  Recent Activity                                  │
│  ┌─────────────────────────────────────────────┐ │
│  │ ▸ BOM generated         12 Mar 14:30  user  │ │
│  │ ▸ Attestation created   11 Mar 09:15  team  │ │
│  │ ▸ BOM verified          10 Mar 16:45  CI    │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
└─────────────────────────────────────────────────┘
```

**Key details**:
- Three sections: BOM summary card, attestation list, activity preview
- Export JSON button top-right of BOM section
- Create attestation button on attestation section header
- Activity section shows last 5 events with "View all" link
- Skeleton loaders for each section during load

### WF-2: BomViewer (expanded view)

**Context**: Shown when user clicks into BOM details from ProvenanceTab or as standalone route.

**Layout**:
```
┌─────────────────────────────────────────────────┐
│  BOM Viewer                      [Export JSON ↓] │
│  context.lock — 24 artifacts                     │
├──────────┬──────────────────────────────────────┤
│ Filter   │                                       │
│ ┌──────┐ │  ┌─ skill ─────────────────────────┐ │
│ │☑ skill│ │  │ canvas-design    v2.1.0  user   │ │
│ │☑ cmd  │ │  │ document-skills  v1.3.2  user   │ │
│ │☑ agent│ │  │ code-review      v3.0.0  local  │ │
│ │☐ hook │ │  └────────────────────────────────┘ │
│ │☐ mcp  │ │                                     │
│ └──────┘ │  ┌─ command ───────────────────────┐ │
│          │  │ deploy-prod      v1.0.0  user   │ │
│ Search   │  │ run-tests        v2.0.1  local  │ │
│ [______] │  └────────────────────────────────┘ │
│          │                                       │
│          │  ┌─ agent ─────────────────────────┐ │
│          │  │ code-reviewer    v1.2.0  user   │ │
│          │  └────────────────────────────────┘ │
├──────────┴──────────────────────────────────────┤
│  Signature: ✓ Verified — user@example.com       │
│  Generated: 2026-03-12T14:30:00Z                │
└─────────────────────────────────────────────────┘
```

**Key details**:
- Left sidebar: checkbox filter by artifact type + search input
- Main area: grouped by type, each artifact shows name, version, scope
- Footer: signature verification status and generation timestamp
- Handles 100+ artifacts with virtualized scroll

### WF-3: AttestationBadge (inline on cards)

**Context**: Small inline badge appearing on artifact cards and detail headers.

**Variants**:
```
Unsigned:        [○ No attestation]     (muted, zinc-400)
User attested:   [● User attested]      (blue-600, subtle)
Team attested:   [●● Team attested]     (green-600, subtle)
Enterprise:      [●●● Enterprise]       (purple-600, bold)
```

**Key details**:
- Tooltip on hover shows: attester, date, scope
- Size matches existing source/version badges on cards
- No layout shift when badge appears/changes
- Screen reader: "Attestation status: [scope] attested by [actor] on [date]"

### WF-4: ActivityTimeline (full view)

**Context**: Expandable timeline shown in ProvenanceTab "View all" or standalone.

**Layout**:
```
┌─────────────────────────────────────────────────┐
│  Activity History               [Filter ▾]       │
├─────────────────────────────────────────────────┤
│                                                   │
│  ● 12 Mar 2026                                   │
│  │                                                │
│  ├─ 14:30  BOM generated              user       │
│  │  ┌──────────────────────────────────────┐     │
│  │  │ 24 artifacts │ SHA: abc123...        │     │
│  │  │ Signature: ✓ verified                │     │
│  │  └──────────────────────────────────────┘     │
│  │                                                │
│  ├─ 09:15  Attestation created         team      │
│  │  > "Reviewed and approved for prod deploy"    │
│  │                                                │
│  ● 11 Mar 2026                                   │
│  │                                                │
│  ├─ 16:45  BOM verified               CI         │
│  │  > Automated verification passed              │
│  │                                                │
│  ├─ 10:00  Artifact updated            user      │
│  │  > canvas-design v2.0.0 → v2.1.0             │
│  │                                                │
│  ● 10 Mar 2026                                   │
│  │                                                │
│  ├─ 12:00  Enterprise attestation      admin     │
│  │                                                │
│                    [Load more]                    │
└─────────────────────────────────────────────────┘
```

**Key details**:
- Grouped by date, vertical timeline line connecting events
- Each event: timestamp, type icon, description, actor badge
- Expandable detail cards (click or Enter to expand)
- Keyboard: Arrow keys move between events, Enter expands, Escape collapses
- ARIA: `role="feed"`, each event is `role="article"` with `aria-label`

### WF-5: Attestation Filter Panel

**Context**: Dropdown or sidebar panel triggered from filter button on attestation list or activity timeline.

**Layout**:
```
┌────────────────────────┐
│  Filter Attestations   │
├────────────────────────┤
│  Owner Scope           │
│  ☑ User                │
│  ☑ Team                │
│  ☑ Enterprise          │
├────────────────────────┤
│  Date Range            │
│  [From: ____] [To: __] │
├────────────────────────┤
│  Artifact Type         │
│  ☑ skill  ☑ command    │
│  ☑ agent  ☐ hook       │
│  ☐ mcp                 │
├────────────────────────┤
│  [Clear]    [Apply]    │
└────────────────────────┘
```

**Key details**:
- Popover or sheet component (matches existing filter patterns in `collection/filters.tsx`)
- Checkbox groups for scope and type
- Date range inputs
- Apply button triggers re-fetch; Clear resets all

### WF-6: Project Dashboard Provenance Section

**Context**: New card section on the project dashboard, alongside existing overview/deployments cards.

**Layout**:
```
┌─────────────────────────────────────────────────┐
│  Provenance & BOM                  [View BOM →]  │
├─────────────────────────────────────────────────┤
│                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ 24       │  │ 3        │  │ ✓ Verified    │  │
│  │ Artifacts│  │ Attests  │  │ Last: 12 Mar  │  │
│  └──────────┘  └──────────┘  └──────────────┘  │
│                                                   │
│  Recent Activity                                  │
│  ─────────────                                    │
│  BOM generated          12 Mar 14:30    user     │
│  Attestation created    11 Mar 09:15    team     │
│  BOM verified           10 Mar 16:45    CI       │
│                                                   │
│                              [View all activity]  │
└─────────────────────────────────────────────────┘
```

**Key details**:
- Stats row: artifact count, attestation count, verification status
- Mini activity feed: last 3 events
- "View BOM" and "View all activity" links to full views
- Same card styling as other dashboard sections

---

## Generation Instructions

### For Gemini (layout reasoning)
1. Analyze existing SkillMeat component screenshots/patterns
2. Validate that the wireframe layouts above integrate correctly with existing surfaces
3. Suggest any layout adjustments based on the existing design language
4. Produce refined component hierarchy descriptions for each wireframe

### For Nano Banana (image generation)
1. Generate clean wireframe-style images for each WF-1 through WF-6
2. Style: Minimal, grayscale with blue accent, Linear/Notion aesthetic
3. Resolution: 1200x800 for full views (WF-1, WF-2, WF-4, WF-6), 400x100 for badge (WF-3), 400x500 for filter (WF-5)
4. Output to: `docs/project_plans/implementation_plans/features/skillbom-attestation-v1/wireframes/`

### Naming Convention
- `wf-1-provenance-tab.png`
- `wf-2-bom-viewer.png`
- `wf-3-attestation-badge.png`
- `wf-4-activity-timeline.png`
- `wf-5-filter-panel.png`
- `wf-6-dashboard-provenance.png`
