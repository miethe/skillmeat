---
title: Analytics, History, and Observability API
description: API reference for enterprise analytics, event streams, observability exports, and artifact provenance history.
audience: developers
tags: [api, analytics, observability, history, provenance]
created: 2026-02-21
updated: 2026-02-21
category: API Documentation
status: published
---

# Analytics, History, and Observability API

This document covers the enterprise analytics and artifact provenance endpoints introduced in the analytics/history refactor.

## Base URL

All endpoints are under:

```text
/api/v1
```

## Authentication

Endpoints use existing API auth middleware:

- `X-API-Key` when API key auth is enabled
- Bearer token when token auth is enabled

## Analytics Endpoints

### `GET /analytics/summary`

Legacy summary for dashboard compatibility.

### `GET /analytics/enterprise-summary`

Enterprise metrics for SDLC and operations dashboards.

Key response fields:

- `windows[]`: rolling windows (1, 7, 30, 90 days)
- `delivery`: deployment frequency and interval metrics
- `reliability`: failure/rollback/MTTR-style metrics
- `adoption`: project/collection activity and conversion metrics
- `top_projects`: high-activity projects
- `history_summary`: provenance-related aggregate counts

### `GET /analytics/top-artifacts`

Top artifact usage ranking with cursor pagination.

### `GET /analytics/trends`

Time-series trend buckets by `period` (`hour`, `day`, `week`, `month`).

### `GET /analytics/events`

Normalized analytics event feed with cursor pagination.

Query params:

- `limit` (1-500)
- `after` (base64 cursor)
- `event_type`
- `artifact_name`
- `artifact_type`
- `collection_name`

### `GET /analytics/export`

Observability export endpoint.

Query params:

- `format`: `json`, `prometheus`, or `otel`
- `include_events` (JSON only)
- `event_limit` (JSON only)

Formats:

- `json`: enterprise summary payload plus optional normalized events
- `prometheus`: Prometheus exposition format
- `otel`: OTLP-style JSON metrics payload

### `GET /analytics/stream`

Server-Sent Events stream for live dashboard updates.

Query params:

- `interval_seconds` (default `10`, range `3-60`)

Frame types:

- `data: { "type": "summary_update", ... }`
- heartbeat comments (`: heartbeat`)

## Artifact Provenance History Endpoint

### `GET /artifacts/{artifact_id}/history`

Unified history/provenance timeline used by artifact modal History tabs.

`artifact_id` supports:

- `type:name` (for example `skill:canvas-design`)
- artifact UUID

Query params:

- `include_versions` (default `true`)
- `include_analytics` (default `true`)
- `include_deployments` (default `true`)
- `limit` (default `300`, max `2000`)

Response shape:

- `artifact_name`
- `artifact_type`
- `timeline[]` with:
  - `event_category`: `version | analytics | deployment | snapshot`
  - `event_type`
  - `source`: `artifact_versions | analytics_events | deployment_tracker`
  - `timestamp`
  - `content_sha`, `parent_sha`, `version_lineage`, `metadata`
- `statistics` aggregate counts
- `last_updated`

Data sources merged into the timeline:

- Cache DB `artifact_versions`
- Analytics events DB
- Deployment tracker records from project deployment metadata

## Frontend Integration Notes

The web dashboard and modal history UIs consume these endpoints via:

- `skillmeat/web/hooks/useAnalytics.ts`
- `skillmeat/web/hooks/useAnalyticsStream.ts`
- `skillmeat/web/hooks/useArtifactHistory.ts`

Export buttons in the Enterprise Insights dashboard card call `GET /analytics/export` with each supported format.
