# Quick Reference: Sample Data for Screenshot Capture

**Status**: ✅ READY TO PROCEED

## Data Available

**Collections** (3 total):
- `default`: 218 artifacts ← Use this one
- `personal`: 24 artifacts (backup for second collection)
- `work`: 1 artifact (needs expansion if required)

**Deployments**: 115 artifacts deployed across 4 projects

**Tags**: 100+ tags covering python, frontend, testing, automation, productivity, etc.

## What's Ready Now

- ✅ Default collection (218 artifacts)
- ✅ 4 projects with deployments
- ✅ All artifact types (Skills, Commands, Agents, Hooks)
- ✅ Tags and filtering
- ✅ GitHub source tracking
- ✅ Artifact descriptions and metadata

## What Needs Decision

- ⚠️ Second collection: Use "personal" (24) or expand "work" (currently 1)?
- ⚠️ Status fields: Are "modified"/"outdated" labels needed?
- ⚠️ Marketplace: Enable real brokers or use mock-local?

## No Setup Required

- ❌ No seed scripts to run
- ❌ No database migrations
- ❌ No data population needed
- ✅ Data already in filesystem at `~/.skillmeat/collections/`

## Start Dev Server

```bash
cd /Users/miethe/dev/homelab/development/skillmeat
skillmeat web dev
```

- API: http://localhost:8000 (docs at /docs)
- Web: http://localhost:3000

## Key Files

- Collections: `~/.skillmeat/collections/`
- Deployments: `.claude/.skillmeat-deployed.toml`
- API routes: `skillmeat/api/routers/`
- Manifests: `~/.skillmeat/collections/*/collection.toml`

## Full Details

See: `.claude/progress/screenshot-capture/sample-data-assessment.md`

---

## Action Items (Priority)

### Immediate (Before Screenshots)

1. ✅ Confirm second collection choice (personal vs work expansion)
2. ✅ Verify if status fields needed (check UI implementation)
3. ✅ Start dev server and test API endpoints

### Optional (For Enhanced Visuals)

1. Enable real marketplace if wanted (update `~/.skillmeat/marketplace.toml`)
2. Verify MCP server count in collections

### Ready Now

- Begin screenshot capture with "default" collection
- Use API endpoints at http://localhost:8000/api/v1/*
- Web interface at http://localhost:3000
