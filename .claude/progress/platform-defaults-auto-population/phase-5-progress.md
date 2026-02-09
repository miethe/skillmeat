---
type: progress
prd: "platform-defaults-auto-population"
phase: 5
status: pending
progress: 0

tasks:
  - id: "PD-5.1"
    name: "Context prefix toggle"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["PD-3.1", "PD-4.2"]
    model: "opus"

parallelization:
  batch_1: ["PD-5.1"]
---

# Phase 5: Custom Context Toggle in Profile Form

## Quality Gates
- [ ] Toggle hidden when custom context disabled
- [ ] Toggle hidden when current platform not in custom context platforms
- [ ] Override mode replaces context prefixes completely
- [ ] Addendum mode appends without duplicates
- [ ] `pnpm type-check` and `pnpm lint` pass
