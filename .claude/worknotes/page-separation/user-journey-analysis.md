# User Journey Analysis: /collection vs /manage Page Separation

## Executive Summary

This analysis maps user journeys across SkillMeat's dual-page artifact browsing experience, identifying decision points, information architecture expectations, and cross-linking opportunities. The goal is to ensure users intuitively navigate between discovery-focused (`/collection`) and operations-focused (`/manage`) experiences.

---

## 1. Primary User Journeys

### Journey 1: Discovery and Exploration (Primary: /collection)

```
                                    +------------------+
                                    |  User lands on   |
                                    |   /collection    |
                                    +--------+---------+
                                             |
                            +----------------+----------------+
                            |                                 |
                   +--------v--------+               +--------v--------+
                   | Browse "All     |               | Select specific |
                   | Collections"    |               | collection      |
                   +--------+--------+               +--------+--------+
                            |                                 |
                            +----------------+----------------+
                                             |
                                    +--------v--------+
                                    | Filter/search   |
                                    | artifacts       |
                                    +--------+--------+
                                             |
                                    +--------v--------+
                                    | Click artifact  |
                                    | card            |
                                    +--------+--------+
                                             |
                                    +--------v--------+
                                    | VIEW MODAL      |
                                    | (Collection)    |
                                    +--------+--------+
                                             |
                    +------------------------+------------------------+
                    |                        |                        |
           +--------v--------+      +--------v--------+      +--------v--------+
           | Read description|      | View source/    |      | Check sync      |
           | & metadata      |      | version info    |      | status          |
           +--------+--------+      +--------+--------+      +--------+--------+
                    |                        |                        |
                    +------------------------+------------------------+
                                             |
                    +------------------------+------------------------+
                    |                                                 |
           +--------v--------+                               +--------v--------+
           | "Deploy" button |                               | "Manage" button |
           | (Quick deploy)  |                               | (Go to /manage) |
           +-----------------+                               +-----------------+
```

**Key Insight**: Users in discovery mode want to understand what an artifact does and decide if it's useful. The modal should prioritize description, tags, and source information.

---

### Journey 2: Health Check and Maintenance (Primary: /manage)

```
                                    +------------------+
                                    |  User lands on   |
                                    |    /manage       |
                                    +--------+---------+
                                             |
                                    +--------v--------+
                                    | Select artifact |
                                    | type tab        |
                                    +--------+--------+
                                             |
                            +----------------+----------------+
                            |                                 |
                   +--------v--------+               +--------v--------+
                   | Filter by       |               | Filter by sync  |
                   | project         |               | status (issue)  |
                   +--------+--------+               +--------+--------+
                            |                                 |
                            +----------------+----------------+
                                             |
                                    +--------v--------+
                                    | See status      |
                                    | indicators      |
                                    | (sync, deploy)  |
                                    +--------+--------+
                                             |
                                    +--------v--------+
                                    | Click artifact  |
                                    | with issue      |
                                    +--------+--------+
                                             |
                                    +--------v--------+
                                    | MANAGE MODAL    |
                                    | (Operations)    |
                                    +--------+--------+
                                             |
                    +------------------------+------------------------+
                    |                        |                        |
           +--------v--------+      +--------v--------+      +--------v--------+
           | View diff/      |      | Check deploy    |      | Review version  |
           | changes         |      | targets         |      | history         |
           +--------+--------+      +--------+--------+      +--------+--------+
                    |                        |                        |
                    +------------------------+------------------------+
                                             |
                    +------------------------+------------------------+
                    |                        |                        |
           +--------v--------+      +--------v--------+      +--------v--------+
           | Sync/pull       |      | Deploy/undeploy |      | Rollback to     |
           | updates         |      | to project      |      | previous        |
           +-----------------+      +-----------------+      +-----------------+
```

**Key Insight**: Users in operations mode need quick visibility into problems (outdated, conflicts, errors) and efficient access to resolution actions.

---

### Journey 3: Deploy to New Project (Cross-Page)

```
         /collection                                          /manage
    +------------------+                              +------------------+
    | User finds       |                              |                  |
    | useful artifact  |                              |                  |
    +--------+---------+                              |                  |
             |                                        |                  |
    +--------v--------+                               |                  |
    | Opens modal     |                               |                  |
    | (View Details)  |                               |                  |
    +--------+--------+                               |                  |
             |                                        |                  |
    +--------v--------+                               |                  |
    | Wants to deploy |                               |                  |
    | to specific     |                               |                  |
    | project         |                               |                  |
    +--------+--------+                               |                  |
             |                                        |                  |
             | [Click "Deploy" - select project]      |                  |
             +---------------------------------------->                  |
             |                                        |                  |
             |                              +---------v--------+         |
             |                              | Deployment modal |         |
             |                              | in /manage with  |         |
             |                              | project context  |         |
             |                              +--------+---------+         |
             |                                       |                   |
             |                              +--------v--------+          |
             |                              | Select target   |          |
             |                              | directory       |          |
             |                              +--------+--------+          |
             |                                       |                   |
             |                              +--------v--------+          |
             |                              | Deploy action   |          |
             |                              +--------+--------+          |
             |                                       |                   |
             |                              +--------v--------+          |
             | [Click "Back to Collection"]| Success - view  |          |
             <----------------------------------------+--------+          |
             |                              | deployment      |          |
    +--------v--------+                    +-----------------+          |
    | Continue        |                                                 |
    | browsing        |                                                 |
    +-----------------+                                                 |
```

---

### Journey 4: Troubleshoot Sync Issue (Cross-Page)

```
         /manage                                           /collection
    +------------------+                              +------------------+
    | User sees        |                              |                  |
    | "outdated"       |                              |                  |
    | indicator        |                              |                  |
    +--------+---------+                              |                  |
             |                                        |                  |
    +--------v--------+                               |                  |
    | Opens modal     |                               |                  |
    | (Manage)        |                               |                  |
    +--------+--------+                               |                  |
             |                                        |                  |
    +--------v--------+                               |                  |
    | Views diff -    |                               |                  |
    | unclear what    |                               |                  |
    | changed         |                               |                  |
    +--------+--------+                               |                  |
             |                                        |                  |
             | [Click "View Details"]                 |                  |
             +---------------------------------------->                  |
             |                                        |                  |
             |                              +---------v--------+         |
             |                              | Opens in         |         |
             |                              | /collection      |         |
             |                              | modal            |         |
             |                              +--------+---------+         |
             |                                       |                   |
             |                              +--------v--------+          |
             |                              | Read full       |          |
             |                              | description,    |          |
             |                              | changelog       |          |
             |                              +--------+--------+          |
             |                                       |                   |
             | [Click "Manage Artifact"]             |                   |
             <----------------------------------------+                   |
             |                                                           |
    +--------v--------+                                                  |
    | Back in /manage |                                                  |
    | - decides to    |                                                  |
    | sync            |                                                  |
    +-----------------+                                                  |
```

---

### Journey 5: Bulk Operations (Primary: /manage)

```
                                    +------------------+
                                    |  /manage with    |
                                    | project filter   |
                                    +--------+---------+
                                             |
                                    +--------v--------+
                                    | Filter: status  |
                                    | = "outdated"    |
                                    +--------+--------+
                                             |
                                    +--------v--------+
                                    | See 5 artifacts |
                                    | need update     |
                                    +--------+--------+
                                             |
                            +----------------+----------------+
                            |                                 |
                   +--------v--------+               +--------v--------+
                   | Select all      |               | Review each     |
                   | (bulk action)   |               | individually    |
                   +--------+--------+               +--------+--------+
                            |                                 |
                   +--------v--------+               +--------v--------+
                   | "Sync All"      |               | Open modal,     |
                   | button          |               | review, decide  |
                   +--------+--------+               +--------+--------+
                            |                                 |
                   +--------v--------+                        |
                   | Progress        |                        |
                   | indicator       |                        |
                   +--------+--------+                        |
                            |                                 |
                            +----------------+----------------+
                                             |
                                    +--------v--------+
                                    | All artifacts   |
                                    | now "synced"    |
                                    +-----------------+
```

---

### Journey 6: Add New Artifact from Marketplace (Cross-System)

```
    /marketplace                    /collection                      /manage
  +--------------+              +------------------+           +------------------+
  | Browse       |              |                  |           |                  |
  | marketplace  |              |                  |           |                  |
  +------+-------+              |                  |           |                  |
         |                      |                  |           |                  |
  +------v-------+              |                  |           |                  |
  | Find skill   |              |                  |           |                  |
  | to add       |              |                  |           |                  |
  +------+-------+              |                  |           |                  |
         |                      |                  |           |                  |
         | [Add to Collection]  |                  |           |                  |
         +---------------------->                  |           |                  |
         |                      |                  |           |                  |
         |              +-------v--------+         |           |                  |
         |              | Select target  |         |           |                  |
         |              | collection     |         |           |                  |
         |              +-------+--------+         |           |                  |
         |                      |                  |           |                  |
         |              +-------v--------+         |           |                  |
         |              | Artifact added |         |           |                  |
         |              | to collection  |         |           |                  |
         |              +-------+--------+         |           |                  |
         |                      |                  |           |                  |
         |              +-------v--------+         |           |                  |
         |              | "Deploy Now?"  |         |           |                  |
         |              | prompt         |         |           |                  |
         |              +-------+--------+         |           |                  |
         |                      |                  |           |                  |
         |                      +------------------+---------->|                  |
         |                                         |           |                  |
         |                                         |   +-------v--------+         |
         |                                         |   | Deploy flow    |         |
         |                                         |   | in /manage     |         |
         |                                         |   +----------------+         |
```

---

### Journey 7: Project-Centric View (Primary: /manage)

```
                                    +------------------+
                                    | User working on  |
                                    | specific project |
                                    +--------+---------+
                                             |
                                    +--------v--------+
                                    | Go to /manage   |
                                    +--------+--------+
                                             |
                                    +--------v--------+
                                    | Filter: project |
                                    | = "my-project"  |
                                    +--------+--------+
                                             |
                                    +--------v--------+
                                    | See only        |
                                    | deployed        |
                                    | artifacts       |
                                    +--------+--------+
                                             |
                    +------------------------+------------------------+
                    |                        |                        |
           +--------v--------+      +--------v--------+      +--------v--------+
           | View deployment |      | Check which     |      | Identify        |
           | status for each |      | need updates    |      | conflicts       |
           +--------+--------+      +--------+--------+      +--------+--------+
                    |                        |                        |
                    +------------------------+------------------------+
                                             |
                                    +--------v--------+
                                    | Take action:    |
                                    | sync, undeploy, |
                                    | or rollback     |
                                    +-----------------+
```

---

## 2. Decision Points: Where Users Choose Between Pages

| Decision Point | User Context | Likely Choice | Navigation Trigger |
|---------------|--------------|---------------|-------------------|
| **Initial landing** | "I want to find a useful skill" | /collection | Direct URL or nav menu |
| **Initial landing** | "I need to fix sync issues" | /manage | Direct URL or nav menu |
| **From modal** | "Tell me more about this artifact" | Stay in /collection modal | - |
| **From modal** | "I want to deploy/sync this" | Navigate to /manage | "Manage Artifact" button |
| **After deployment** | "What else can I add?" | Navigate to /collection | "Browse More" button |
| **After sync** | "I want to learn what changed" | Navigate to /collection | "View Details" button |
| **Troubleshooting** | "Why is this broken?" | Start /manage, may visit /collection | View Details link |
| **Bulk operations** | "Update all my deployments" | Stay in /manage | Bulk action buttons |

### Decision Matrix: Which Page for Which Task?

| User Intent | /collection | /manage | Why |
|-------------|:-----------:|:-------:|-----|
| Find new artifacts | Primary | - | Discovery is core purpose |
| Read descriptions/docs | Primary | Secondary | Documentation-focused |
| Browse by tags | Primary | - | Tag filtering is discovery |
| View artifact metadata | Both | Both | Both modals show this |
| Deploy to project | Available | Primary | Operations-focused |
| Check sync status | - | Primary | Health/operations concern |
| Resolve conflicts | - | Primary | Requires operational tools |
| View deployment history | - | Primary | Operations data |
| Undeploy artifact | - | Primary | Destructive operation |
| Bulk sync operations | - | Primary | Efficiency operation |
| Compare versions | Secondary | Primary | Operations context needed |
| Manage groups | Primary | - | Organization/discovery |
| Move between collections | Primary | - | Organization feature |

---

## 3. Information Architecture

### What Users Expect to Find: /collection

| Information Type | Priority | Displayed Where | Notes |
|-----------------|:--------:|-----------------|-------|
| Artifact name | High | Card, modal header | Primary identifier |
| Description | High | Card preview, modal | Discovery driver |
| Type (skill/command/etc) | High | Card badge, filter | Quick categorization |
| Tags | High | Card, filter bar | Discovery/organization |
| Author | Medium | Modal | Trust signal |
| Version | Medium | Card badge, modal | Compatibility check |
| Source URL | Medium | Modal | Verification |
| Collection membership | Medium | Card badge | Context |
| Group membership | Low | Modal | Organization |
| Last updated | Low | Modal | Freshness indicator |
| **Sync status** | Low | Small indicator | Not primary concern here |
| **Deployment status** | Low | - | Not relevant for discovery |

### What Users Expect to Find: /manage

| Information Type | Priority | Displayed Where | Notes |
|-----------------|:--------:|-----------------|-------|
| Artifact name | High | List item, modal | Primary identifier |
| Sync status | High | Prominent badge | Health indicator |
| Type | High | Tab, icon | Categorization |
| Deployed projects | High | Indicators, modal | Operations context |
| Last synced | High | List item | Freshness |
| Version (local vs remote) | High | Modal comparison | Update decision |
| Deployment path | Medium | Modal | Debug info |
| Diff/changes | Medium | Modal tab | Decision support |
| Version history | Medium | Modal tab | Rollback support |
| **Description** | Low | Collapsible/link | Available if needed |
| **Tags** | Low | - | Not operations-relevant |
| **Author** | Low | - | Not operations-relevant |

### Modal Tab Structure

**Collection Modal Tabs** (Discovery-focused):
1. **Overview** (default) - Description, metadata, tags, upstream summary
2. **Contents** - View artifact structure/contents (existing data)
3. **Links** - Linked artifacts + references
4. **Collections** - Which collections contain this
5. **Sources** - Repository/source details
6. **History** - General artifact timeline

**Manage Modal Tabs** (Operations-focused):
1. **Status** (default) - Detailed operational status
2. **Sync Status** - Drift + sync actions (existing data)
3. **Deployments** - Deploy/undeploy controls
4. **Version History** - Timeline + rollback options

---

## 4. Pain Point Analysis

### Pain Point 1: Modal Context Mismatch

**Scenario**: User opens artifact in /collection, wants to deploy, has to figure out how.

**Current State**: Single `CollectionArtifactModal` wraps `UnifiedEntityModal` with navigation handlers, but modal doesn't clearly signal "you're in discovery mode."

**User Frustration**: "Where do I go to actually deploy this thing?"

**Recommendation**:
- Add clear "Deploy to Project" CTA in collection modal
- Include "For sync status and deployments, see Manage" subtle link
- Consider inline deploy option for simple cases

**Severity**: Medium (users can navigate, but path unclear)

---

### Pain Point 2: Sync Status Buried in Discovery View

**Scenario**: User in /collection sees artifact they already have deployed, doesn't realize it's outdated.

**Current State**: `/collection` focuses on discovery; sync status may not be prominently displayed.

**User Frustration**: "I didn't know my deployed version was out of date."

**Recommendation**:
- Add subtle sync status indicator on artifact cards in /collection for deployed artifacts
- Badge: "Deployed (outdated)" with link to /manage
- Don't clutter discovery view, but surface critical operational info

**Severity**: Medium-High (users may miss important updates)

---

### Pain Point 3: Cross-Page Context Loss

**Scenario**: User clicks "View Details" from /manage to learn about artifact, loses their operational context.

**Current State**: Navigation happens but user must manually return.

**User Frustration**: "I just wanted to read the docs, now I lost where I was."

**Recommendation**:
- Implement "breadcrumb" state or "return to /manage" persistent button
- Consider: /collection modal with "Return to Manage" button when referred from /manage
- Preserve filter state when returning

**Severity**: Medium (disrupts workflow, requires re-navigation)

---

### Pain Point 4: Project Filter Discovery

**Scenario**: User wants to see all artifacts deployed to a specific project.

**Current State**: /manage has project filter, but users may not realize they can filter this way.

**User Frustration**: "How do I see what's in my project?"

**Recommendation**:
- Prominent "Filter by Project" dropdown in /manage header
- Consider: Project cards/tiles as alternative navigation
- Add "View deployments" link in project detail pages

**Severity**: Low (feature exists, just needs better visibility)

---

### Pain Point 5: Bulk Operations Discoverability

**Scenario**: User has 10 outdated artifacts across projects, wants to sync all.

**Current State**: Individual sync from modal; bulk operations not clearly exposed.

**User Frustration**: "Do I really have to do this one by one?"

**Recommendation**:
- Add checkbox selection mode in /manage list view
- "Sync All Outdated" batch action button
- Filter + bulk action = powerful workflow

**Severity**: Medium (significant time savings possible)

---

### Pain Point 6: Unclear System Boundaries

**Scenario**: User doesn't understand why some features are on /collection vs /manage.

**Current State**: Dual system (file-based CollectionManager vs database) is implementation detail exposed to users.

**User Frustration**: "Why can't I do everything in one place?"

**Recommendation**:
- Clear page headers explaining purpose: "Browse & Discover" vs "Operations Dashboard"
- Consistent cross-linking so users don't feel "stuck"
- Unified artifact identity across both pages (same IDs, same modals with different defaults)

**Severity**: Low-Medium (mental model issue, not blocking)

---

### Pain Point 7: Deployment Target Selection

**Scenario**: User wants to deploy from /collection but doesn't know which projects are available.

**Current State**: Deployment requires project path knowledge.

**User Frustration**: "What's the path to my project again?"

**Recommendation**:
- Project picker dropdown with recent/registered projects
- "Deploy to..." flow with project search
- Remember last deployment target

**Severity**: Medium (friction in common workflow)

---

## 5. Cross-Linking Recommendations

### From /collection to /manage

| Trigger Location | Link Text | Destination | When to Show |
|-----------------|-----------|-------------|--------------|
| Artifact card | "Manage" icon | /manage?artifact={id} | When artifact is deployed |
| Card badge | "Outdated" | /manage?artifact={id}&focus=sync | When sync status is outdated |
| Modal header | "Manage Artifact" button | /manage?artifact={id} | Always |
| Modal deploy tab | "Advanced Deploy Options" | /manage?artifact={id}&tab=deploy | After simple deploy |
| Collection header | "View Operations" | /manage | Always (subtle) |

### From /manage to /collection

| Trigger Location | Link Text | Destination | When to Show |
|-----------------|-----------|-------------|--------------|
| Artifact row | "Collection Details" | /collection?artifact={id} | Always |
| Modal header | "Collection Details" button | /collection?artifact={id} | Always |
| Sync Status tab | "What's new?" link | /collection?artifact={id}&tab=history | When showing changes |
| Empty state | "Browse Collection" | /collection | When no artifacts deployed |
| After undeploy | "Find Replacement" | /collection?type={type} | After removing artifact |

### Contextual Deep Links

| Scenario | Deep Link Pattern | Purpose |
|----------|------------------|---------|
| Direct to artifact in manage | `/manage?artifact={id}` | Open modal automatically |
| Direct to artifact in collection | `/collection?artifact={id}` | Open modal automatically |
| Focus specific modal tab | `?artifact={id}&tab={tab}` | Jump to relevant content |
| Filter preset | `/manage?status=outdated&project={path}` | Bookmarkable workflows |
| Return context | `?returnTo=/manage?project={path}` | Preserve navigation stack |

### Navigation State Preservation

**Recommended Implementation**:

```typescript
// Track origin for cross-page navigation
interface NavigationContext {
  origin: '/collection' | '/manage' | '/marketplace';
  filters?: Record<string, string>;
  scrollPosition?: number;
}

// Store in sessionStorage or URL state
// Enables "Back to [Origin]" functionality
```

---

## 6. Summary Recommendations

### High Priority

1. **Dual-button modal design**: "View Details" and "Manage Artifact" buttons clearly direct users
2. **Sync status indicator in /collection**: Subtle badge on deployed artifacts showing operational state
3. **Project filter prominence in /manage**: Make filter-by-project a primary navigation element
4. **Deep link support**: Enable `?artifact={id}` pattern on both pages

### Medium Priority

5. **Return-to-origin button**: When navigating cross-page, show clear return path
6. **Bulk operations UI**: Checkbox selection + batch actions in /manage
7. **Deployment target picker**: Project dropdown for easy deployment from /collection

### Low Priority (Polish)

8. **Page purpose messaging**: Clear headers explaining each page's focus
9. **Keyboard shortcuts**: Q to quick-deploy, M to manage, etc.
10. **Filter state preservation**: Maintain filters when returning from cross-page navigation

---

## 7. Validation Plan

### Usability Test Script (15 minutes)

**Task 1: Discovery** (5 min)
- "Find a skill that helps with documentation"
- Observe: Do they go to /collection? Can they filter/search?

**Task 2: Operations** (5 min)
- "Check if any of your deployed skills need updates"
- Observe: Do they go to /manage? Can they find sync status?

**Task 3: Cross-Page** (5 min)
- "You found an outdated skill in /manage. Learn more about what changed."
- Observe: Can they navigate to /collection? Do they know how to return?

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Task 1 completion | >90% | User finds artifact in collection |
| Task 2 completion | >85% | User identifies outdated artifacts |
| Task 3 completion | >80% | User navigates both directions |
| Cross-page confusion | <20% | User expresses uncertainty about which page |
| Navigation clicks | <3 per task | Efficient pathfinding |

---

*Analysis prepared: 2026-02-01*
*Context: SkillMeat page separation refactor*
*Next steps: Review with design, implement cross-linking, conduct usability validation*
