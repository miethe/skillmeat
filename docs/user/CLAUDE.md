# User Documentation Rules

Path scope: `docs/user/**`

## Audience

All docs under this scope are **user-facing**. The reader is an operator, developer, or end user of SkillMeat — not a contributor to its codebase.

## Key Rules

1. **Never reference implementation details** — no PRD phases, task IDs, internal architecture, agent names, or codebase internals. Document *what the feature does* and *how to use it*, not how it was built.

2. **Feature-first framing** — organize around capabilities and configuration modes, not development timelines. If a feature has multiple levels (e.g., auth modes), name each clearly and explain when to use it.

3. **Practical examples** — every guide should include copy-paste-ready commands, config snippets, or curl examples. Show what the user types and what they see.

4. **YAML frontmatter required** — all docs must include `title`, `description`, `domain`, `category`, `subcategory`, `created`, `last_updated`, and `tags` in frontmatter.

## When to Update

| Trigger | Action |
|---------|--------|
| New user-facing feature | Create or update the relevant guide |
| CLI command added/changed | Update CLI guide (`docs/user/guides/cli/commands.md`) |
| Config option added | Update the relevant guide's configuration reference |
| Migration path created | Add to `docs/user/migration/` |
| Feature removed or renamed | Update all affected guides; remove stale references |

