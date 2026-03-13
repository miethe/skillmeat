---
status: inferred_complete
---
# Gemini Layout Analysis: SkillBOM Provenance UI

This document provides a technical layout analysis and integration validation for the SkillBOM provenance and attestation UI components, ensuring consistency with the existing SkillMeat design system.

## 1. Integration Validation

| Component | Target Surface | Integration Fit | Pattern Alignment |
|-----------|----------------|-----------------|-------------------|
| **WF-1: ProvenanceTab** | `UnifiedEntityModal` | **Excellent**. Fits as a standard tab alongside 'History'. | Uses `TabsContent`, `ScrollArea`, and `Card` patterns. |
| **WF-2: BomViewer** | Standalone / Modal | **Good**. Follows the "Sidebar + Content" pattern seen in settings/collections. | Uses `Checkbox` filters and `VirtualizedList` (if needed). |
| **WF-3: AttestationBadge** | `EntityCard`, Headers | **Excellent**. Matches existing `Source` and `Version` badge patterns. | Uses `Badge` with `Tooltip` wrapper. |
| **WF-4: ActivityTimeline** | `ProvenanceTab` / Full | **High**. Evolves the basic 'History' timeline into a rich Feed. | Uses `Collapsible` for event details. |
| **WF-5: Filter Panel** | List Views | **Standard**. Matches `TagFilterPopover` and `ToolFilterPopover`. | Uses `Popover` with `Checkbox` groups. |
| **WF-6: Dashboard Sec.** | `Dashboard` | **Standard**. Follows existing 3-column/card dashboard layout. | Uses `Card` with `Stats` grid. |

## 2. Specific Refinements for Consistency

- **Tab Styling**: Ensure the `Provenance` tab uses the `rounded-none border-b-2` style defined in `unified-entity-modal.tsx`.
- **Iconography**: Use `ShieldCheck` or `FileCheck` for Provenance, `History` for Activity, and `BadgeCheck` for Attestations to maintain the Lucide-based visual language.
- **Color Semantics**: 
  - Attestation tiers (User/Team/Enterprise) should use the specific blue/green/purple hierarchy to distinguish from simple artifact types.
  - Verification status should reuse the `CheckCircle2` (green) and `Clock` (blue) colors from the existing `syncStatus` logic.
- **Density**: Maintain the `h-[calc(90vh-12rem)]` scroll area in the modal to prevent layout shifts when switching between Overview and Provenance.

## 3. Component Hierarchy & Primitives

### WF-1: ProvenanceTab
- **Hierarchy**:
  - `<ProvenanceTabContent artifactId={id} />`
    - `<BOMSummaryCard data={bomData} onExport={() => {}} />` → `Card`, `CardHeader`, `CardTitle`, `Badge`, `Button (Export)`
    - `<AttestationSection attestations={items} onCreate={() => {}} />` → `SectionHeader`, `Button (Create)`, `AttestationList`
      - `<AttestationItem key={id} scope={scope} actor={actor} date={date} />` → `Badge`, `Tooltip`, `RelativeTime`
    - `<RecentActivityPreview events={latest} onViewAll={() => {}} />` → `SectionHeader`, `ActivityFeed`, `Link (View All)`
- **Primitives**: `Card`, `Badge`, `Button`, `ScrollArea`, `Skeleton`.

### WF-2: BomViewer
- **Hierarchy**:
  - `<BomViewerLayout bom={bom} />`
    - `<BomSidebar filters={filterState} onFilterChange={handleFilter} />` → `ScrollArea`, `CheckboxGroup`, `SearchInput`
    - `<BomContent items={filteredItems} />` → `ScrollArea`
      - `<ArtifactGroup key={type} type={type} count={n}>` → `Separator`, `GroupTitle`
        - `<ArtifactBomEntry key={id} name={name} version={v} scope={s} />` → `ArtifactIcon`, `Name`, `Version`, `ScopeBadge`
    - `<BomFooter signature={sig} timestamp={ts} />` → `SignatureBadge`, `Timestamp`
- **Primitives**: `ScrollArea`, `Checkbox`, `Input`, `Separator`, `Badge`.

### WF-3: AttestationBadge
- **Hierarchy**:
  - `<Tooltip delayDuration={300}>`
    - `<TooltipTrigger>` → `<AttestationBadge variant={tier} />`
    - `<TooltipContent side="top">` → `AttesterInfo`, `Date`, `Scope`
- **Primitives**: `Tooltip`, `Badge`.

### WF-4: ActivityTimeline
- **Hierarchy**:
  - `<ActivityTimelineFeed events={allEvents} filters={activeFilters} />`
    - `<DateGroup date={day}>` → `DateHeader`
      - `<TimelineItem key={id} event={event} defaultExpanded={false}>` → `Collapsible`
        - `<TimelineTrigger>` → `Time`, `Icon`, `Description`, `ActorBadge`, `Chevron`
        - `<TimelineContent>` → `DetailCard`, `MetadataGrid`, `SignatureInfo`
- **Primitives**: `Collapsible`, `Badge`, `Separator`.

### WF-5: Attestation Filter Panel
- **Hierarchy**:
  - `<Popover open={isOpen} onOpenChange={setOpen}>`
    - `<PopoverTrigger>` → `Button`
    - `<PopoverContent align="end" className="w-80">`
      - `<FilterGroup title="Scope" options={scopes} selected={selectedScopes} />` → `CheckboxGroup`
      - `<FilterGroup title="Date" range={dateRange} onChange={setDateRange} />` → `DateRangePicker`
      - `<FilterActionRow onClear={reset} onApply={apply} />` → `Button (Clear)`, `Button (Apply)`
- **Primitives**: `Popover`, `Checkbox`, `Label`, `Calendar` (DateRange).

### WF-6: Project Dashboard Provenance Section
- **Hierarchy**:
  - `<DashboardCard title="Provenance & BOM" className="col-span-1">`
    - `<CardHeader>` → `Title`, `ViewBOMButton`
    - `<CardContent className="space-y-4">`
      - `<StatsGrid columns={3}>` → `<StatBox label="Artifacts" value={count} />` ...
      - `<MiniActivityList items={latest3} />`
    - `<CardFooter>` → `Link (View All)`
- **Primitives**: `Card`, `Badge`, `Button`.

## 4. Suggested Implementation Path

1. **Shared Primitives**: Ensure `Badge` and `Tooltip` are updated for the new attestation variants.
2. **Context Hooks**: Create `useProvenance(artifactId)` and `useAttestations(artifactId)` hooks to share state across the tab and dashboard.
3. **Modal Integration**: Add `provenance` to `ArtifactModalTab` enum in `unified-entity-modal.tsx` and implement the `TabsContent` using the hierarchy above.
