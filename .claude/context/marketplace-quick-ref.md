---
title: Marketplace Quick Reference
description: Quick lookup for confidence scoring, SKILL.md detection, and source detail patterns
last_verified: 2025-01-02
---

# Marketplace Quick Reference

## Confidence Score Thresholds

| Threshold | Meaning |
|-----------|---------|
| 0-29% | **Below minimum** - filtered out by default, requires `includeBelowThreshold=true` |
| 30-49% | **Low confidence** - detected but weak signals |
| 50-69% | **Medium confidence** - typical single-file artifacts |
| 70-89% | **High confidence** - good signals |
| 90-100% | **Very high** - manifest + frontmatter or multiple strong signals |

## Signal Points (Raw Score)

```
Maximum: 120 points total

✓ Manifest file (SKILL.md, etc.)     +20  ← STRONGEST per-signal
✓ Container hint (inside typed dir)  +25  ← Usually present
✓ Frontmatter type field             +30  ← STRONGEST if present
✓ Parent hint (parent dir pattern)   +15
✓ Frontmatter presence               +15
✓ Directory name pattern             +10
✓ File extensions                    +5
─ Depth penalty                      -N   (reduced 50% in containers)

Normalization: raw_score / 120 * 100 → 0-100
```

## SKILL.md Detection Checklist

### What Counts as SKILL.md?

```
✓ File named "SKILL.md" (case-insensitive)
✓ File named "skill.md" (case-insensitive)
✓ Must be in artifact directory
✓ Will trigger +20 manifest_score automatically
✓ Content frontmatter optional but recommended
```

### Example Valid SKILL.md

```markdown
---
type: skill
name: Canvas Designer
version: 1.0.0
description: Create designs using canvas
---

# Canvas Designer Skill

Professional canvas design tool.
```

### Why SKILL.md Matters

| Without SKILL.md | With SKILL.md |
|---|---|
| Directory name must match pattern | Works in any directory name |
| Needs other strong signals | Guaranteed +20 points |
| ~53% confidence typical | ~78%+ confidence typical |
| Can be overridden | Authoritative signal |

## Artifact Type Detection Priority

1. **Manifest file name** (HIGHEST) - e.g., SKILL.md → SKILL type
2. **Frontmatter type field** (if enabled) - from YAML metadata
3. **Directory name pattern** - e.g., /skills/ directory
4. **Container hint** - parent /skills/ directory
5. **File extensions** - presence of .py, .ts, etc. (LOWEST)

## Frontend Filters Mapping

| Frontend | API Parameter | Default | Example |
|----------|---|---|---|
| Type tabs | `artifact_type` | null (all) | "skill" |
| Status badges | `status` | null (all) | "new" |
| Min confidence slider | `min_confidence` | 50 | 70 |
| Max confidence slider | `max_confidence` | 100 | 100 |
| "Include below threshold" | `include_below_threshold` | false | true |
| Search box | client-side only | "" | "canvas" |

## URL Parameter Format

```
/marketplace/sources/src-123?
  type=skill              # Artifact type filter
  &status=new            # Status filter
  &minConfidence=70      # Minimum confidence
  &maxConfidence=100     # Maximum confidence
  &includeBelowThreshold=true  # Show low-confidence
```

## Status Lifecycle

```
new        → Never imported, first detection
updated    → Changed since last import
imported   → Currently in collection
removed    → Was imported, no longer detected
excluded   → Marked as non-artifact (hidden)

Exclude dialog: "Not an artifact" button
Restore: Click "Restore" on excluded entry
```

## Pagination & Deduplication

**API Response**:
```
CatalogListResponse {
  items: [CatalogEntryResponse, ...]    # Paginated entries
  page_info: PageInfo                   # Cursor pagination
  counts_by_status: {...}               # Aggregated counts
  counts_by_type: {...}                 # Aggregated counts
}
```

**Frontend Dedup Pattern**:
```typescript
const allEntries = useMemo(() => {
  if (!catalogData?.pages) return [];
  const seen = new Set<string>();
  return catalogData.pages
    .flatMap(page => page.items)
    .filter(entry => {
      if (seen.has(entry.id)) return false;
      seen.add(entry.id);
      return true;
    });
}, [catalogData]);
```

## Container vs Artifact

| Container | Artifact | Example |
|-----------|----------|---------|
| Named /skills/ | Inside /skills/ | /skills/canvas-design/ |
| Named /commands/ | Inside /commands/ | /commands/git/cm.md |
| Named /agents/ | Inside /agents/ | /agents/helper/ |
| No MANIFEST | Has MANIFEST | SKILL.md present |
| Type propagates down | Type inherited | Container=skill |
| Not detected itself | **Detected** | Returned in results |

## Score Breakdown Fields

```typescript
score_breakdown?: {
  dir_name_score: number;        // 0-10 matched directory pattern
  manifest_score: number;        // 0-20 manifest file presence
  extensions_score: number;      // 0-5 file types
  parent_hint_score: number;     // 0-15 parent directory
  frontmatter_score: number;     // 0-15 metadata presence
  frontmatter_type_score: number;  // 0-30 type field if present
  container_hint_score: number;  // 0-25 typed parent
  depth_penalty: number;         // negative (reduced in container)
  raw_total: number;             // sum before normalization
  normalized_score: number;      // final 0-100
  single_file_detection?: boolean;  // true if .md file
}
```

## Common Confidence Scenarios

### Scenario 1: Well-Formed Skill

```
skills/canvas-design/
  SKILL.md (with type: skill)
  index.ts
  package.json

Expected Score: 85-95%
Reason: manifest(20) + container(25) + frontmatter_type(30) + ...
```

### Scenario 2: Single-File Command

```
commands/git/cm.md

Expected Score: 70%
Reason: container_hint(25) + extensions(5) + single-file(70% base)
```

### Scenario 3: Deeply Nested

```
src/artifacts/skills/my-skill/
  SKILL.md

Expected Score: 60-70%
Reason: manifest(20) + container(25) + parent(15) - depth_penalty(5)
```

### Scenario 4: No Manifest, No Container

```
some-skill/
  README.md
  index.ts

Expected Score: 25-35% (BELOW THRESHOLD)
Reason: extensions(5) + dir_name(maybe 10) - depth_penalty(-5)
Status: Filtered out unless `includeBelowThreshold=true`
```

## Frontmatter Type Support

### Supported Type Values

```yaml
type: skill       # → ArtifactType.SKILL
type: command     # → ArtifactType.COMMAND
type: agent       # → ArtifactType.AGENT
type: hook        # → ArtifactType.HOOK
type: mcp         # → ArtifactType.MCP_SERVER
type: mcp_server  # → ArtifactType.MCP_SERVER
type: mcp-server  # → ArtifactType.MCP_SERVER
```

### Parsing Rules

```
✓ Case-insensitive ("SKILL", "Skill", "skill" all work)
✓ Whitespace trimmed
✓ Requires YAML frontmatter format (--- delimited)
✓ Must be in "type:" field
✓ If multiple manifest files, first one parsed wins
✓ Overrides manifest filename type if different
```

## ImportRequest Parameters

```typescript
interface ImportRequest {
  entry_ids: string[];              // IDs to import
  conflict_strategy: 'skip' | 'merge' | 'fork';  // usually 'skip'
}
```

## ExcludeArtifactRequest

```typescript
interface ExcludeArtifactRequest {
  excluded: boolean;    // true = exclude, false = restore
  reason?: string;      // Optional: max 500 chars
}
```

**Example Reasons**:
- "Not a valid artifact - documentation only"
- "False positive detection"
- "Duplicate artifact"
- "Not a Claude Code artifact"

## Rescan Behavior

```
POST /marketplace/sources/{id}/rescan

Triggers:
1. Fetch latest repository tree from GitHub
2. Re-run heuristic detector
3. Update catalog with new/updated/removed entries
4. Preserve import and exclusion status
5. Update last_sync_at timestamp

Returns:
- ScanResultDTO with new counts
- Same structure as initial scan
```

## Performance Considerations

| Operation | Bottleneck | Mitigation |
|-----------|-----------|-----------|
| Large repos | Tree fetching | GitHub cache (TTL 1h) |
| Deep scanning | Heuristic analysis | Configurable max_depth |
| Pagination | Database queries | Cursor-based pagination |
| Search filter | Client-side | JavaScript filter loop |
| Type filtering | Server-side | Indexed by artifact_type |

## Troubleshooting

### Issue: Entry shows 0% confidence

**Check**:
- No manifest file (SKILL.md, etc.)
- Not in typed container (skills/, commands/)
- Very deep nesting (>10 levels)
- Unusual directory name

**Fix**: Add SKILL.md manifest file

### Issue: Entry filtered out (not visible)

**Check**:
- Confidence < 30% (below threshold)
- Status excluded
- Type filter doesn't match

**Fix**: Enable "Include below threshold" toggle or rescan with `enable_frontmatter_detection=true`

### Issue: Two entries for same artifact

**Check**:
- Duplication in catalog (detected twice)
- One may have different confidence

**Fix**: Mark one as excluded with reason "Duplicate artifact"

