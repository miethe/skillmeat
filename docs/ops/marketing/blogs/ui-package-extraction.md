---
status: draft-notes
date: 2026-03-14
linked_feature: artifact-modal-content-viewer-extraction-v1 (completed), skillmeat-ui-package-extraction-v1 (in progress)
related_prs:
  - "#122 — content-viewer extraction initial slice"
---

# Extracting a Reusable UI Package from a Production Next.js App (Without Breaking Anything)

**Working title alternatives:**
- "The Adapter Pattern That Freed Our Components from Their API Hooks"
- "875 Lines Removed, Zero Regressions: Extracting @skillmeat/content-viewer"
- "How We're Turning SkillMeat's UI Into a Shareable Package (And Why It's Harder Than It Sounds)"

---

## Overview / What This Post Is About

This covers the ongoing effort to extract SkillMeat's frontend UI surfaces — starting with the artifact modal content viewers — into standalone, reusable packages that live in the monorepo and can eventually be shared or open-sourced. The first slice is done. The bigger program is underway.

Audience: developers who work on production Next.js apps and have wondered whether their UI components are too tangled to ever be extracted cleanly.

Tone: honest engineering retrospective, not a how-to tutorial. We made specific decisions; here's what they were and why.

---

## The Problem (What Made This Hard)

### The coupling was subtle, not obvious

SkillMeat's modal UI was architecturally messy in a specific way: the components themselves were actually pretty generic — a file tree, a markdown preview pane, a frontmatter display. But they were wired directly to TanStack Query hooks that called SkillMeat-specific API endpoints. You could not take `ContentPane` and use it anywhere else without also pulling in `useCatalogFileContent`, which depended on `NEXT_PUBLIC_API_URL`, which assumed SkillMeat's backend URL structure.

The components weren't technically "business logic." But their data paths were locked to one backend.

### The quantity problem

Before extraction, the same components existed in roughly the same form inside `components/entity/` (the collection browser view), `components/editor/` (the edit surfaces), and increasingly as one-off copies wherever a modal needed content viewing. Not full duplicates — just close enough that any behavior fix needed to be applied in 3-4 places, and frequently wasn't.

**Concrete numbers going into this work:**
- `ContentPane`: ~420 lines, used in 5+ modal consumers
- `FileTree`: ~380 lines, duplicated keyboard nav logic
- `SplitPreview` + `MarkdownEditor`: ~250 lines with hardcoded CodeMirror imports
- `FrontmatterDisplay`: ~100 lines
- Frontmatter utilities (`parseFrontmatter`, `stripFrontmatter`, `detectFrontmatter`): scattered across `lib/frontmatter.ts` and inline in components
- README extraction helpers: another copy in `lib/folder-readme-utils.ts`, another in a component

Total: roughly 875 lines of duplicated or near-duplicated implementation code.

### Why we hadn't done this already

Honest answer: the parity risk was real. These components lived inside the artifact modal's Contents tab — the primary way users browse deployed artifact files. Getting something wrong there is high-visibility. The modal's behavior was tested informally through usage, not through a systematic test suite. We didn't have a clear picture of all the states it needed to handle.

---

## The Approach: Adapter-First Extraction

The key insight that made this tractable: separate "what the component renders" from "how the data arrives."

### The adapter pattern

Instead of hardcoding API calls inside components, we defined explicit interfaces:

```typescript
interface FileTreeAdapter {
  useFileTree(params: { entityId: string; path?: string }): AdapterQueryResult<FileTreeResponse>;
}

interface FileContentAdapter {
  useFileContent(params: { entityId: string; path: string }): AdapterQueryResult<FileContentResponse>;
}

type ContentViewerAdapter = FileTreeAdapter & FileContentAdapter;
```

The adapter is injected via a React context provider (`ContentViewerProvider`). Components call `useContentViewerAdapter()` to get it. They never import a hook from `@/hooks` or a URL constant — they only know about the adapter interface.

SkillMeat's concrete adapter lives in `lib/content-viewer-adapter.ts` and wraps the existing TanStack Query hooks. The package knows nothing about SkillMeat's API. SkillMeat's app knows everything — but only in one place.

This pattern has a name. It's ports and adapters (hexagonal architecture) applied to React's data-fetching layer. We'd already applied this on the backend in the repo-pattern-refactor. Doing it on the frontend is less common but equally useful.

### What stayed in the package vs. what stayed in the app

**Package (`@skillmeat/content-viewer`):**
- All five components
- Frontmatter parse/strip/detect utilities
- README extraction helpers
- Type definitions for `FileNode`, `FileTreeEntry`, `FileContentResponse`
- Adapter interfaces
- `ContentViewerProvider` and `useContentViewerAdapter`

**App (`skillmeat/web`):**
- The concrete adapter implementation (`lib/content-viewer-adapter.ts`)
- Domain-specific detection logic (artifact type detection, semantic tree filtering)
- API route ownership
- Marketplace-specific filter utilities

The keep-local list was important. Several things looked extractable but weren't — SkillMeat's artifact type detection, for example, understands the difference between a skill's `SKILL.md` and a command's `COMMAND.md`. That logic doesn't belong in a generic package.

### Zero-regression strategy: re-export stubs

Rather than doing a big-bang migration where every import in the app changed at once, we used re-export stubs. The old file `components/entity/content-pane.tsx` became:

```typescript
export { ContentPane } from '@skillmeat/content-viewer';
export type { ContentPaneProps, TruncationInfo } from '@skillmeat/content-viewer';
```

Three lines. All existing consumers kept importing from `@/components/entity/content-pane` without knowing anything changed. We then migrated the 5 modal consumers to use `@skillmeat/content-viewer` directly, which is the canonical import going forward.

This meant we could ship the extraction incrementally and verify each step, rather than changing 30 import sites at once.

---

## The Parity Work

Before shipping, we wrote the test suite that should have existed from the start.

**10 parity scenarios from the test matrix:**
1. No file selected → empty state placeholder
2. File tree item click → ContentPane loads correct content
3. Keyboard navigation (arrow keys, Home/End, Enter, Space)
4. Loading states (skeleton while fetching)
5. API error states (error message, role="alert")
6. Markdown frontmatter detection and stripping
7. FrontmatterDisplay rendering for detected frontmatter
8. Truncated file warnings (large files)
9. Edit mode transitions
10. Re-export stub equivalence (same function object, same output)

**78 tests** covering all of the above. All passing.

**55 accessibility tests** separately, checking WCAG 2.1 AA compliance:
- `FileTree`: `role="tree"`, `role="treeitem"`, `aria-expanded`, `aria-selected`, roving tabindex, full keyboard nav (ArrowDown/Up/Left/Right/Home/End/Enter/Space)
- `ContentPane`: `role="region"` with labelling, `<nav aria-label="File path">` breadcrumb landmark, `role="alert"` on error and truncation banners
- `FrontmatterDisplay`: collapsible trigger with state-aware `aria-label`

Three a11y findings documented (not violations, but worth noting):
- ContentPane has both `aria-label` and `aria-labelledby` simultaneously — redundant
- `<FileText>` icon in empty state missing `aria-hidden`
- FrontmatterDisplay uses `div + strong` for key-value pairs instead of `<dl>/<dt>/<dd>`

None are blocking. All logged as TODOs.

**Bundle impact**: 85.3 KB (comfortably inside the 110 KB target). The heavy editor path (CodeMirror) is lazy-loaded — `SplitPreview` and `MarkdownEditor` are behind a dynamic import boundary, so they don't inflate the initial read-only render.

---

## What's Next: The Bigger Program

The content-viewer extraction was the "initial slice" of a larger program: extracting SkillMeat's modal viewer surfaces more broadly.

The umbrella plan (`skillmeat-ui-package-extraction-v1`) has 5 phases:

1. **Package Foundation and Governance** — formalize the workspace package structure, semver/release policy, and public API boundary conventions (the content-viewer extraction did this informally; we need to harden it)
2. **Initial Content Viewer Module** — done ✓
3. **SkillMeat Integration and Parity Validation** — done ✓
4. **Additional Modal Viewer Waves** — the sync-status tab surfaces, the deployment views, the diff viewer. These have higher coupling to SkillMeat-specific domain logic; extraction needs careful scoping
5. **Stabilization and Adoption** — remove legacy duplicates, publish docs, consider tagging a 1.0

### The upcoming challenges in the expansion waves

The content viewer was selected specifically because it was high-readiness: the components were relatively generic and the data paths were cleanly separable. Later waves will be harder:

- **SyncStatusTab** (~1,000 lines): Tightly coupled to 3 comparison scopes, multiple diff query strategies, and SkillMeat-specific sync semantics. The component structure is good; the data paths are complex.
- **DiffViewer**: Uses a `parseCacheRef` pattern for lazy unified diff parsing that's specific to SkillMeat's upstream tracking model. True generalization would require designing a diff format abstraction.
- **ArtifactOperationsModal**: Already uses `BaseArtifactModal` composition pattern. Extraction here might mean extracting the composition framework itself.

The adapter pattern scales to all of these. The question is how much domain abstraction we want to build vs. how much we accept that some surfaces are SkillMeat-specific and stay local.

---

## The Bigger Question: Why Publish?

SkillMeat is a personal project. There's no business case for open-sourcing a UI package. So why go through the extraction at all?

A few reasons:

**Forcing function for clean architecture.** The extraction pressure forced us to eliminate coupling that wouldn't have been noticed otherwise. The concrete result — one adapter file where all the API binding happens, all components clean — is better code than what we started with. We'd do it again even if we never published.

**Future tooling flexibility.** SkillMeat might eventually have an Electron shell, a VS Code extension sidebar, or a different backend. Components that don't hardcode their data paths work in all of those contexts. Components that do, don't.

**Open-source optionality.** If there's ever interest in sharing the viewer stack — for other Claude Code management tools, artifact browsers, filesystem viewers — the package structure makes that possible. If not, nothing is lost.

---

## Things Worth Expanding in the Final Post

- **Code snippet**: the before/after of `ContentPane` — showing the old hook import at the top vs. `useContentViewerAdapter()` call
- **Diagram**: package boundary diagram showing what's inside the package, what's in the app, and where the adapter connects them
- **The stub pattern in more detail**: how three-line re-exports protect existing consumers and how they can be deprecated gradually
- **Side-by-side test count**: before (0 component-level tests for these surfaces) vs. after (133 tests)
- **The lazy load story in more detail**: why CodeMirror can't just be imported normally in a workspace package, how the dynamic import boundary works, and why the performance test verifies it
- **Context on the repo-pattern-refactor**: this is the frontend equivalent of the backend work in #109. Worth pointing readers at that post.

---

## Draft Outline (for when this becomes a real post)

1. The problem: components that look generic but aren't
2. The inventory: what we had, where the coupling lived
3. The approach: ports and adapters for React
4. What we extracted vs. what we kept local
5. The re-export stub pattern
6. Building the parity test suite after the fact
7. Accessibility as a first-class output, not an afterthought
8. Bundle constraints and the lazy-load boundary
9. Results: the numbers
10. What comes next in the extraction program
11. The broader case for extraction even without publication intent
