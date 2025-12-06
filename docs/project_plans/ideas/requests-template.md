---
type: request-log
template_version: 1
doc_id: "REQ-YYYYMMDD-slug"
title: "Enhancements & Issues — YYYY-MM-DD"
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: "open"
owners: ["owner-or-role"]
domains: ["web"]
item_count: 0
items_index: []
---

# Template: Enhancements & Issues Log

> Copy this file to `docs/project_plans/ideas/YYYY-MM-DD-requests.md` (or similar), fill the front matter, and add items using the format below. Keep IDs stable once issued.

## How to issue IDs
- **Doc ID:** `REQ-YYYYMMDD-slug` (human-readable slug, lowercase kebab, e.g., `REQ-20251203-web`).
- **Item ID:** `REQ-YYYYMMDD-slug-XX` (two-digit counter per doc, e.g., `REQ-20251203-web-01`).

## Front matter fields (machine-friendly)
- `type` must stay `request-log`.
- `doc_id` unique per doc.
- `title` concise, human-readable.
- `created` / `updated` ISO dates (`YYYY-MM-DD`).
- `status` one of `open|triage|in-progress|paused|closed`.
- `owners` array of roles/people.
- `domains` array of scopes (`web|api|cli|data|infra|ml|ops`).
- `item_count` integer (update when adding items).
- `items_index` short list for agents to scan without parsing the whole doc:
  ```yaml
  items_index:
    - id: "REQ-20251203-web-01"
      type: enhancement        # enhancement|bug|design|research|task
      domain: web              # domain/area
      context: "/collection"   # page/component/endpoint/entity
      priority: medium         # p0|p1|p2|p3 or high|medium|low
      status: triage           # triage|todo|in-progress|blocked|done|deferred
      title: "Custom artifact groups at collection level"
      tags: ["ux", "grouping"]
  ```

## Quick index table (fill once items exist)
| ID | Type | Domain | Context | Priority | Status | Title |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-YYYYMMDD-slug-01 | enhancement | web | /collection | medium | triage | Custom artifact groups at collection level |

## Item format (repeat per item)
### REQ-YYYYMMDD-slug-01 — Custom artifact groups at collection level
**Type:** enhancement | **Domain:** web | **Context:** /collection | **Priority:** medium | **Status:** triage  
**Tags:** ux, grouping  
**Owner:** product-owner (optional)  

- Problem/goal: …
- Key behaviors/acceptance: …
- Notes/open questions: …
- Related: links/IDs (optional)

## Minimal creation steps (for fast manual entry)
1. Duplicate this file and rename appropriately.
2. Fill front matter values.
3. Add `items_index` entries (1–2 lines each).
4. Populate quick index table (copy from `items_index`).
5. Add item detail sections (keep bullet-heavy for speed).

## Automation hook (optional)
- Accept POST payload `{ doc_id, title, date, items: [...] }` to render this shape server-side (e.g., simple Next.js API or Python script). Store files under `docs/project_plans/ideas/`.
- Agents can query `items_index` in the front matter without reading the full file.
