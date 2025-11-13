---
title: "Design: Team Sharing & Marketplace Federation"
description: "Detailed architecture for Phase 3 features F3.2 and F3.4"
audience: [ai-agents, backend-architects, frontend-engineers]
tags: [design, sharing, marketplace, phase3]
created: 2025-11-10
updated: 2025-11-10
status: draft
related:
  - /docs/project_plans/ph1-initialization/init-prd.md
  - /docs/project_plans/ph3-advanced/adr-0001-web-platform.md
---

# Design Document — Team Sharing & Marketplace Federation

## 1. Purpose

Enable developers to:
1. Export/share curated collections with teammates without forcing adoption.
2. Import shared collections or marketplace offerings while tracking provenance.
3. Publish optional listings to public marketplaces and pull updates securely.

## 2. Functional Requirements

### Team Sharing (F3.2)
- Export entire collections or scoped subsets to a portable bundle (`.skillmeat-pack`).
- Include metadata: artifact types, tags, upstream links, version pins, usage stats.
- Allow importing bundles with option to merge, fork, or link back to upstream team source.
- Support recommendation links (share read-only reference without cloning).
- Provide per-project override of shared defaults (e.g., override command config locally).

### Marketplace Integration (F3.4)
- Browse curated feeds (SkillMeat Marketplace, Claude public catalogs) from web + CLI.
- Install artifacts or whole packs into local collection with trust prompts.
- Publish optional listings that reference GitHub repos or SkillMeat packs.
- Track licensing + attribution; warn on incompatible licenses.

## 3. Non-Functional Requirements

- Bundles must be deterministic (hashable) to support integrity checks.
- Imports should be idempotent and safe to re-run (no duplicate artifacts).
- Public marketplace calls require signature validation + rate limiting.
- Sharing operations should run offline when using direct file exchange.

## 4. Architecture Overview

```
┌──────────────────────────┐     ┌────────────────────┐
│ SkillMeat Web (Next.js) │◀───▶│ FastAPI Sharing API │
└──────────────────────────┘     └────────┬───────────┘
                                          │
                                          ▼
                                ┌─────────────────────┐
                                │ Bundle Builder      │
                                │ (Python service)    │
                                └────────┬────────────┘
                                          │
                    ┌─────────────────────┴──────────────────────┐
                    │                                            │
             ┌──────▼──────┐                               ┌──────▼──────┐
             │ Team Vault  │                               │ Marketplace │
             │ (S3/Git)    │                               │ Brokers     │
             └─────────────┘                               └─────────────┘
```

- **Bundle Builder**: Python module that serializes selected artifacts + metadata into a `.skillmeat-pack` (TAR + manifest). Reuses DiffEngine for integrity verification.
- **Team Vault Adapter**: pluggable storage (Git repo, S3 bucket, shared folder). Exposed via FastAPI endpoints for upload/download, with per-team token auth.
- **Marketplace Brokers**: connectors for public marketplaces (Anthropic, community registries). Each broker handles listing fetch, signature check, and install hooks.

## 5. Data Formats

### Bundle Manifest (`bundle.toml`)

```toml
[bundle]
id = "sm-pack-2025-11-10-A1B2"
name = "web-dev-starter"
created_at = "2025-11-10T09:30:00Z"
owner = "team-xyz"
source = "team-vault::git@github.com:team/skillmeat-packs.git"

[[artifacts]]
name = "code-review"
type = "command"
version = "v1.4.0"
upstream = "github:team/code-review"
hash = "sha256:..."
tags = ["review", "backend"]
```

### Marketplace Listing Schema

```json
{
  "listing_id": "market-42",
  "name": "Security Scan Pack",
  "publisher": "SecureCorp",
  "license": "Apache-2.0",
  "artifact_count": 5,
  "price": 0,
  "signature": "BASE64",
  "source_url": "https://market.skillmeat.dev/listings/market-42",
  "bundle_url": "https://..."
}
```

## 6. API Surface

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/api/sharing/bundles` | POST | Create bundle from selection | Local token |
| `/api/sharing/bundles/{id}` | GET | Download bundle binary | Token/signature |
| `/api/sharing/import` | POST | Upload `.skillmeat-pack` and import | Token |
| `/api/sharing/recommend` | POST | Generate shareable link referencing vault | Token |
| `/api/marketplace/listings` | GET | Paginated listing feed | Public (rate limited) |
| `/api/marketplace/install` | POST | Install listing into collection | Token |
| `/api/marketplace/publish` | POST | Publish local bundle to configured broker | Token + publisher key |

## 7. Permission Model

- **Local personal mode**: uses local API token; bundles stored under `~/.skillmeat/shared`.
- **Team mode**: OAuth or PAT for remote vault. Access levels:
  - `viewer`: browse + import.
  - `publisher`: export/publish.
  - `admin`: manage tokens + vault configuration.
- Marketplace publish requires signing key stored in OS keychain; CLI prompts when needed.

## 8. Import Workflow

1. User selects `.skillmeat-pack` via UI or CLI.
2. FastAPI validates bundle signature/hash.
3. Artifact diff vs existing collection computed.
4. User chooses action per artifact: merge, fork, skip.
5. Manifest updated; analytics event `IMPORT` recorded.

## 9. Export Workflow

1. User selects artifacts (filters by tags/type).
2. Bundle Builder copies files + metadata + dependency graph.
3. Optional scrub step removes secrets.
4. Bundle uploaded to selected destination (local path, Git remote, S3).
5. Share link returned; UI can render QR/link.

## 10. Marketplace Broker Strategy

- Implement base `MarketplaceBroker` class with methods: `listings()`, `download(listing_id)`, `publish(bundle)`.
- Default brokers:
  - `SkillMeatMarketplaceBroker` (official feed).
  - `ClaudeHubBroker` (public Claude catalogs via REST).
  - `CustomWebBroker` (user-supplied endpoint with JSON schema).
- Brokers registered via config file `marketplace.toml`.

## 11. Telemetry & Analytics

- Events: `BUNDLE_EXPORT`, `BUNDLE_IMPORT`, `MARKETPLACE_INSTALL`, `MARKETPLACE_PUBLISH`.
- Each event logs artifact counts, duration, success/failure.
- Failures trigger retry queue and UI notifications.

## 12. Failure Handling

- Bundle validation errors produce actionable messages (missing metadata, hash mismatch).
- Imports performed in temp workspace; manifest updated only after success.
- Marketplace downloads use checksum; mismatch aborts install.

## 13. Open Questions

1. Which storage backend should be default for Team Vault (Git vs S3)? → Default to Git repo for parity with developer workflows; S3 adapter optional.
2. Will publishing to public marketplace require review queue? → Assume yes; build CLI output with submission ID and pending status.
3. Do we need paid marketplace support in Phase 3? → Not in scope per MVP; design keeps metadata fields for price but UI hides purchase flows.

## 14. Next Steps

- Align with security review on bundle format + signing.
- Add API contracts to OpenAPI schema for SDK generation.
- Incorporate workflow steps into Phase 3 implementation plan tasks.
