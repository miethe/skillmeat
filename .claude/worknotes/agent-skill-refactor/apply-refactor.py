#!/usr/bin/env python3
"""Apply agent/skill refactor changes from optimization-report.md.
Phases 1, 2, 3, 5 (skipping Phase 4 consolidation).
"""
import os
import re
import sys

AGENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "agents")
SKILLS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "skills")

# Comprehensive change mapping: relative path -> {field: value}
# All phases (1: model, 2: permissionMode/disallowedTools, 3: skills, 5: memory)
AGENT_CHANGES = {
    # === IMPLEMENTATION AGENTS (Sonnet + acceptEdits + skills/memory) ===
    "dev-team/python-backend-engineer.md": {
        "model": "sonnet",
        "permissionMode": "acceptEdits",
        "skills": ["skillmeat-cli", "artifact-tracking"],
        "memory": "project",
    },
    "dev-team/ui-engineer-enhanced.md": {
        "model": "sonnet",
        "permissionMode": "acceptEdits",
        "skills": ["frontend-design", "aesthetic", "artifact-tracking"],
        "memory": "project",
    },
    "ui-ux/ui-engineer.md": {
        "model": "sonnet",
        "permissionMode": "acceptEdits",
        "skills": ["frontend-design", "aesthetic"],
    },
    "dev-team/frontend-developer.md": {
        "model": "sonnet",
        "permissionMode": "acceptEdits",
        "skills": ["frontend-design"],
    },
    "architects/frontend-architect.md": {
        "model": "sonnet",
        "permissionMode": "acceptEdits",
    },
    "architects/backend-architect.md": {
        "model": "sonnet",
        "permissionMode": "acceptEdits",
    },
    "architects/backend-typescript-architect.md": {
        "model": "sonnet",
        "permissionMode": "acceptEdits",
    },
    "architects/nextjs-architecture-expert.md": {
        "model": "sonnet",
        "permissionMode": "acceptEdits",
    },
    "architects/data-layer-expert.md": {
        "model": "sonnet",
        "permissionMode": "acceptEdits",
    },
    "fix-team/refactoring-expert.md": {
        "model": "sonnet",
        "permissionMode": "acceptEdits",
    },
    "tech-writers/openapi-expert.md": {
        "model": "sonnet",
        "permissionMode": "acceptEdits",
        "skills": ["artifact-tracking"],
    },
    "ai/ai-engineer.md": {
        "model": "sonnet",
        "permissionMode": "acceptEdits",
    },
    "dev-team/python-pro.md": {
        "model": "sonnet",  # was sonnet 4.5, stays sonnet (gets 4.6)
    },
    "dev-team/mobile-app-builder.md": {
        "model": "sonnet",
    },
    "ai/ai-artifacts-engineer.md": {
        "model": "sonnet",  # already sonnet 4.5
    },
    "ai/prompt-engineer.md": {
        "model": "sonnet",  # already sonnet 4.5
    },
    "web-optimize-team/react-performance-optimizer.md": {
        "model": "sonnet",  # already sonnet 4.5
    },
    "tech-writers/documentation-complex.md": {
        "model": "sonnet",
        "permissionMode": "acceptEdits",
    },

    # === REVIEW & VALIDATION AGENTS (Sonnet + plan + disallowedTools) ===
    "reviewers/senior-code-reviewer.md": {
        "model": "sonnet",
        "permissionMode": "plan",
        "disallowedTools": ["Write", "Edit", "MultiEdit", "Bash"],
        "memory": "project",
    },
    "reviewers/task-completion-validator.md": {
        "model": "sonnet",
        "permissionMode": "plan",
        "disallowedTools": ["Write", "Edit", "MultiEdit"],
        "memory": "project",
    },
    "reviewers/api-librarian.md": {
        "model": "sonnet",
        "permissionMode": "plan",
        "disallowedTools": ["Write", "Edit", "MultiEdit"],
    },
    "reviewers/telemetry-auditor.md": {
        "model": "sonnet",
        "permissionMode": "plan",
        "disallowedTools": ["Write", "Edit", "MultiEdit"],
    },
    "reviewers/code-reviewer.md": {
        "permissionMode": "plan",
        "disallowedTools": ["Write", "Edit", "MultiEdit", "Bash"],
    },
    "ui-ux/a11y-sheriff.md": {
        "permissionMode": "plan",
    },

    # === ORCHESTRATION AGENTS (Keep Opus + skills/memory) ===
    "fix-team/ultrathink-debugger.md": {
        "model": "opus",  # was commented out sonnet
        "permissionMode": "acceptEdits",
        "memory": "project",
    },
    "architects/lead-architect.md": {
        "model": "opus",
        "skills": ["planning"],
    },
    "pm/lead-pm.md": {
        "model": "opus",
        "skills": ["planning", "artifact-tracking", "meatycapture-capture"],
        "memory": "project",
    },
    "pm/spike-writer.md": {
        "model": "opus",  # was haiku, upgrade to opus
        "skills": ["planning"],
    },
    "tech-writers/documentation-planner.md": {
        "model": "opus",
        "permissionMode": "plan",
        "disallowedTools": ["Write", "Edit", "MultiEdit"],
    },
    "reviewers/karen.md": {
        "model": "opus",
        "permissionMode": "plan",
        "disallowedTools": ["Write", "Edit", "MultiEdit"],
    },

    # === EXPLORATION AGENTS (Keep/Set Haiku + plan + skills/memory) ===
    "ai/codebase-explorer.md": {
        # already haiku
        "permissionMode": "plan",
        "skills": ["symbols"],
        "memory": "project",
    },
    "ai/search-specialist.md": {
        # already haiku
        "permissionMode": "plan",
    },
    "ai/symbols-engineer.md": {
        # already haiku
        "permissionMode": "plan",
    },
    "pm/task-decomposition-expert.md": {
        # already haiku
        "permissionMode": "plan",
    },
    "pm/implementation-planner.md": {
        # already haiku
        "permissionMode": "plan",
        "skills": ["planning"],
    },

    # === DOWNGRADE TO HAIKU (over-provisioned on Sonnet) ===
    "web-optimize-team/url-link-extractor.md": {
        "model": "haiku",
    },
    "web-optimize-team/url-context-validator.md": {
        "model": "haiku",
    },
    "tech-writers/changelog-generator.md": {
        "model": "haiku",
        "permissionMode": "acceptEdits",
    },
    "web-optimize-team/web-accessibility-checker.md": {
        "model": "haiku",
    },
    "tech-writers/technical-writer.md": {
        "model": "haiku",
    },

    # === DOCUMENTATION AGENTS ===
    "tech-writers/documentation-writer.md": {
        "model": "haiku",
        "permissionMode": "acceptEdits",
    },
    "tech-writers/documentation-expert.md": {
        "model": "haiku",
        "permissionMode": "acceptEdits",
    },
    "tech-writers/api-documenter.md": {
        # already haiku
        "permissionMode": "acceptEdits",
    },

    # === PM AGENTS (Sonnet upgrade + skills) ===
    "pm/prd-writer.md": {
        "model": "sonnet",  # was haiku, upgrade
        "skills": ["planning"],
    },
    "pm/feature-planner.md": {
        "model": "sonnet",  # was haiku, upgrade
        "skills": ["planning", "artifact-tracking"],
    },
}


def parse_frontmatter(content: str):
    """Parse YAML frontmatter from markdown file.
    Returns (frontmatter_lines, body) where frontmatter_lines is list of lines
    between --- markers (excluding markers).
    """
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, content

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return None, content

    fm_lines = lines[1:end_idx]
    body = "\n".join(lines[end_idx + 1 :])
    return fm_lines, body


def build_frontmatter(fm_lines: list, changes: dict) -> str:
    """Apply changes to frontmatter lines and return new frontmatter string."""
    # Parse existing fields
    existing = {}
    field_order = []
    for line in fm_lines:
        # Skip commented lines (like #model: sonnet)
        if line.strip().startswith("#"):
            continue
        match = re.match(r"^(\w[\w-]*)\s*:\s*(.*)$", line)
        if match:
            key = match.group(1)
            val = match.group(2).strip()
            existing[key] = val
            field_order.append(key)

    # Apply changes
    for key, val in changes.items():
        if key not in existing:
            field_order.append(key)
        existing[key] = val

    # Build output lines
    out = []
    for key in field_order:
        val = existing[key]
        if isinstance(val, list):
            # YAML list format
            if key == "disallowedTools":
                # disallowedTools as comma-separated string
                out.append(f"{key}: {', '.join(val)}")
            else:
                # skills as YAML list
                out.append(f"{key}:")
                for item in val:
                    out.append(f"  - {item}")
        elif isinstance(val, str) and val.startswith('"'):
            # Already quoted
            out.append(f"{key}: {val}")
        else:
            out.append(f"{key}: {val}")

    return "\n".join(out)


def process_agent(rel_path: str, changes: dict) -> str:
    """Process a single agent file. Returns status message."""
    full_path = os.path.join(AGENTS_DIR, rel_path)
    if not os.path.exists(full_path):
        return f"SKIP (not found): {rel_path}"

    with open(full_path, "r") as f:
        content = f.read()

    fm_lines, body = parse_frontmatter(content)
    if fm_lines is None:
        return f"SKIP (no frontmatter): {rel_path}"

    new_fm = build_frontmatter(fm_lines, changes)
    new_content = f"---\n{new_fm}\n---{body}"

    with open(full_path, "w") as f:
        f.write(new_content)

    change_desc = ", ".join(f"{k}={v}" for k, v in changes.items())
    return f"OK: {rel_path} [{change_desc}]"


def process_skill(skill_name: str, changes: dict) -> str:
    """Process a single skill SKILL.md file."""
    full_path = os.path.join(SKILLS_DIR, skill_name, "SKILL.md")
    if not os.path.exists(full_path):
        return f"SKIP (not found): {skill_name}/SKILL.md"

    with open(full_path, "r") as f:
        content = f.read()

    fm_lines, body = parse_frontmatter(content)
    if fm_lines is None:
        return f"SKIP (no frontmatter): {skill_name}/SKILL.md"

    new_fm = build_frontmatter(fm_lines, changes)
    new_content = f"---\n{new_fm}\n---{body}"

    with open(full_path, "w") as f:
        f.write(new_content)

    change_desc = ", ".join(f"{k}={v}" for k, v in changes.items())
    return f"OK: {skill_name}/SKILL.md [{change_desc}]"


# Skill changes (Phase 3: context: fork + agent binding)
SKILL_CHANGES = {
    "symbols": {"context": "fork", "agent": "Explore"},
    "confidence-check": {"context": "fork", "agent": "general-purpose"},
    "chrome-devtools": {"context": "fork", "agent": "general-purpose"},
    "meeting-insights-analyzer": {"context": "fork", "agent": "general-purpose"},
}


def main():
    print("=" * 60)
    print("Agent/Skill Refactor - Phases 1, 2, 3, 5")
    print("=" * 60)

    print("\n--- Agent Updates ---")
    ok_count = 0
    skip_count = 0
    for rel_path, changes in sorted(AGENT_CHANGES.items()):
        if not changes:
            continue
        result = process_agent(rel_path, changes)
        print(result)
        if result.startswith("OK"):
            ok_count += 1
        else:
            skip_count += 1

    print(f"\nAgents: {ok_count} updated, {skip_count} skipped")

    print("\n--- Skill Updates ---")
    for skill_name, changes in sorted(SKILL_CHANGES.items()):
        result = process_skill(skill_name, changes)
        print(result)

    print("\nDone!")


if __name__ == "__main__":
    main()
