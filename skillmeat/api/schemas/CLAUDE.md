# CLAUDE.md - api/schemas

Scope: Pydantic request/response models in `skillmeat/api/schemas/`.

## Invariants

- Schema changes must preserve backward compatibility unless explicitly planned.
- Keep request/response boundaries explicit.
- OpenAPI output must reflect schema updates.

## Read When

- Contract authority: `.claude/context/key-context/api-contract-source-of-truth.md`
- FE/BE type alignment: `.claude/context/key-context/fe-be-type-sync-playbook.md`
