---
description: Scaffold a feature following MP architecture (schema → DTO → repo → service → API → UI)
allowed-tools: Read(./**), Write(./**), Edit, MultiEdit
argument-hint: [feature-name]
---

Using MP architecture rules:

1. Plan "$ARGUMENTS" (scope 1-2 files per layer)
2. Implement sequence: schema → DTO → repo → service → API → web hook + UI → tests
3. Wire telemetry spans & JSON logs
4. Update OpenAPI docs
5. Create commit with clear message

Follow @CLAUDE.md implementation sequence exactly.
