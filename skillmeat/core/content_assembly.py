"""Modular content assembly for context entities.

Provides platform-specific content assembly from a platform-agnostic
``core_content`` source.  This module is part of the CECO-4.1 Modular
Content Architecture feature and is gated behind the
``modular_content_architecture`` feature flag.

Usage::

    from skillmeat.core.content_assembly import assemble_content, extract_core_content

    # Assemble platform-specific content from core content
    platform_content = assemble_content(
        core_content="# My Rule\\n\\nDo X.",
        entity_type_config={"slug": "rule_file"},
        platform="claude-code",
    )

    # Strip platform wrappers back to core content (for editing)
    raw = extract_core_content(assembled_content, entity_type_slug="rule_file")

Architecture
------------
``PLATFORM_TRANSFORMERS`` maps ``(entity_type_slug, platform)`` pairs to
transformer callables.  Each transformer receives ``(core_content: str,
entity_type_config: dict) -> str`` and returns the assembled string.

New platforms and entity types can be added by inserting entries into
``PLATFORM_TRANSFORMERS`` without touching any existing transformer.

Supported platforms
-------------------
- ``claude-code``
- ``claude-desktop``
- ``windsurf``
- ``cursor``
- ``cline``

Supported entity type slugs
---------------------------
- ``skill``
- ``command``
- ``agent``
- ``mcp_server``
- ``hook``
- ``project_config``
- ``spec_file``
- ``rule_file``
- ``context_file``
- ``progress_template``
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

#: Transformer signature: (core_content, entity_type_config) -> assembled_content
TransformerFn = Callable[[str, dict], str]

#: Registry key: (entity_type_slug, platform_slug)
TransformerKey = Tuple[str, str]


# ---------------------------------------------------------------------------
# Skill transformers
# ---------------------------------------------------------------------------


def _skill_claude_code(core_content: str, config: dict) -> str:
    """Assemble a skill for Claude Code (no extra wrapper needed)."""
    return core_content


def _skill_claude_desktop(core_content: str, config: dict) -> str:
    """Assemble a skill for Claude Desktop (no extra wrapper needed)."""
    return core_content


def _skill_windsurf(core_content: str, config: dict) -> str:
    """Assemble a skill for Windsurf (no extra wrapper needed)."""
    return core_content


def _skill_cursor(core_content: str, config: dict) -> str:
    """Assemble a skill for Cursor.

    Cursor reads rules from ``.cursor/rules/``.  No additional frontmatter is
    required beyond what the author supplies.
    """
    return core_content


def _skill_cline(core_content: str, config: dict) -> str:
    """Assemble a skill for Cline (no extra wrapper needed)."""
    return core_content


# ---------------------------------------------------------------------------
# Command transformers
# ---------------------------------------------------------------------------

_COMMAND_FRONTMATTER_TEMPLATE = "---\nallowed-tools: []\n---\n\n"
_COMMAND_CURSOR_FRONTMATTER_TEMPLATE = "---\nalwaysApply: false\n---\n\n"


def _command_claude_code(core_content: str, config: dict) -> str:
    """Assemble a command for Claude Code.

    Prepends YAML frontmatter with ``allowed-tools`` if not already present.
    """
    if core_content.startswith("---"):
        return core_content
    return _COMMAND_FRONTMATTER_TEMPLATE + core_content


def _command_claude_desktop(core_content: str, config: dict) -> str:
    """Assemble a command for Claude Desktop (same as claude-code)."""
    return _command_claude_code(core_content, config)


def _command_windsurf(core_content: str, config: dict) -> str:
    """Assemble a command for Windsurf (no extra frontmatter needed)."""
    return core_content


def _command_cursor(core_content: str, config: dict) -> str:
    """Assemble a command for Cursor.

    Cursor rules use ``alwaysApply`` in frontmatter.
    """
    if core_content.startswith("---"):
        return core_content
    return _COMMAND_CURSOR_FRONTMATTER_TEMPLATE + core_content


def _command_cline(core_content: str, config: dict) -> str:
    """Assemble a command for Cline (no extra frontmatter needed)."""
    return core_content


# ---------------------------------------------------------------------------
# Agent transformers
# ---------------------------------------------------------------------------

_AGENT_HEADER_TEMPLATE = "# Agent Configuration\n\n"


def _agent_claude_code(core_content: str, config: dict) -> str:
    """Assemble an agent for Claude Code.

    Prepends a lightweight header if none is present.
    """
    if core_content.startswith("#"):
        return core_content
    return _AGENT_HEADER_TEMPLATE + core_content


def _agent_claude_desktop(core_content: str, config: dict) -> str:
    """Assemble an agent for Claude Desktop (same as claude-code)."""
    return _agent_claude_code(core_content, config)


def _agent_windsurf(core_content: str, config: dict) -> str:
    """Assemble an agent for Windsurf (no extra header needed)."""
    return core_content


def _agent_cursor(core_content: str, config: dict) -> str:
    """Assemble an agent for Cursor (no extra header needed)."""
    return core_content


def _agent_cline(core_content: str, config: dict) -> str:
    """Assemble an agent for Cline (no extra header needed)."""
    return core_content


# ---------------------------------------------------------------------------
# MCP server transformers
# ---------------------------------------------------------------------------

_MCP_SERVER_HEADER_TEMPLATE = "# MCP Server Configuration\n\n"


def _mcp_server_claude_code(core_content: str, config: dict) -> str:
    """Assemble an MCP server config for Claude Code."""
    if core_content.startswith("#"):
        return core_content
    return _MCP_SERVER_HEADER_TEMPLATE + core_content


def _mcp_server_claude_desktop(core_content: str, config: dict) -> str:
    """Assemble an MCP server config for Claude Desktop (same as claude-code)."""
    return _mcp_server_claude_code(core_content, config)


def _mcp_server_windsurf(core_content: str, config: dict) -> str:
    """Assemble an MCP server config for Windsurf (no extra wrapper needed)."""
    return core_content


def _mcp_server_cursor(core_content: str, config: dict) -> str:
    """Assemble an MCP server config for Cursor (no extra wrapper needed)."""
    return core_content


def _mcp_server_cline(core_content: str, config: dict) -> str:
    """Assemble an MCP server config for Cline (no extra wrapper needed)."""
    return core_content


# ---------------------------------------------------------------------------
# Hook transformers
# ---------------------------------------------------------------------------

_HOOK_FRONTMATTER_TEMPLATE = "---\nhook_type: pre-tool\n---\n\n"


def _hook_claude_code(core_content: str, config: dict) -> str:
    """Assemble a hook for Claude Code.

    Prepends hook-type frontmatter if not already present.
    """
    if core_content.startswith("---"):
        return core_content
    return _HOOK_FRONTMATTER_TEMPLATE + core_content


def _hook_claude_desktop(core_content: str, config: dict) -> str:
    """Assemble a hook for Claude Desktop (same as claude-code)."""
    return _hook_claude_code(core_content, config)


def _hook_windsurf(core_content: str, config: dict) -> str:
    """Assemble a hook for Windsurf (no extra wrapper needed)."""
    return core_content


def _hook_cursor(core_content: str, config: dict) -> str:
    """Assemble a hook for Cursor (no extra wrapper needed)."""
    return core_content


def _hook_cline(core_content: str, config: dict) -> str:
    """Assemble a hook for Cline (no extra wrapper needed)."""
    return core_content


# ---------------------------------------------------------------------------
# Context entity transformers (project_config, spec_file, etc.)
# These entity types are platform-agnostic and need no transformation.
# ---------------------------------------------------------------------------


def _identity(core_content: str, config: dict) -> str:
    """Return content unchanged (no platform-specific transformation needed)."""
    return core_content


# ---------------------------------------------------------------------------
# Transformer registry
# ---------------------------------------------------------------------------

#: Maps (entity_type_slug, platform_slug) → transformer function.
#: Falls back to ``_identity`` for unknown combinations.
PLATFORM_TRANSFORMERS: Dict[TransformerKey, TransformerFn] = {
    # Skills
    ("skill", "claude-code"): _skill_claude_code,
    ("skill", "claude-desktop"): _skill_claude_desktop,
    ("skill", "windsurf"): _skill_windsurf,
    ("skill", "cursor"): _skill_cursor,
    ("skill", "cline"): _skill_cline,
    # Commands
    ("command", "claude-code"): _command_claude_code,
    ("command", "claude-desktop"): _command_claude_desktop,
    ("command", "windsurf"): _command_windsurf,
    ("command", "cursor"): _command_cursor,
    ("command", "cline"): _command_cline,
    # Agents
    ("agent", "claude-code"): _agent_claude_code,
    ("agent", "claude-desktop"): _agent_claude_desktop,
    ("agent", "windsurf"): _agent_windsurf,
    ("agent", "cursor"): _agent_cursor,
    ("agent", "cline"): _agent_cline,
    # MCP servers
    ("mcp_server", "claude-code"): _mcp_server_claude_code,
    ("mcp_server", "claude-desktop"): _mcp_server_claude_desktop,
    ("mcp_server", "windsurf"): _mcp_server_windsurf,
    ("mcp_server", "cursor"): _mcp_server_cursor,
    ("mcp_server", "cline"): _mcp_server_cline,
    # Hooks
    ("hook", "claude-code"): _hook_claude_code,
    ("hook", "claude-desktop"): _hook_claude_desktop,
    ("hook", "windsurf"): _hook_windsurf,
    ("hook", "cursor"): _hook_cursor,
    ("hook", "cline"): _hook_cline,
    # Context entity types — all platforms → identity (no transformation)
    ("project_config", "claude-code"): _identity,
    ("project_config", "claude-desktop"): _identity,
    ("project_config", "windsurf"): _identity,
    ("project_config", "cursor"): _identity,
    ("project_config", "cline"): _identity,
    ("spec_file", "claude-code"): _identity,
    ("spec_file", "claude-desktop"): _identity,
    ("spec_file", "windsurf"): _identity,
    ("spec_file", "cursor"): _identity,
    ("spec_file", "cline"): _identity,
    ("rule_file", "claude-code"): _identity,
    ("rule_file", "claude-desktop"): _identity,
    ("rule_file", "windsurf"): _identity,
    ("rule_file", "cursor"): _identity,
    ("rule_file", "cline"): _identity,
    ("context_file", "claude-code"): _identity,
    ("context_file", "claude-desktop"): _identity,
    ("context_file", "windsurf"): _identity,
    ("context_file", "cursor"): _identity,
    ("context_file", "cline"): _identity,
    ("progress_template", "claude-code"): _identity,
    ("progress_template", "claude-desktop"): _identity,
    ("progress_template", "windsurf"): _identity,
    ("progress_template", "cursor"): _identity,
    ("progress_template", "cline"): _identity,
}

# Supported platform slugs (for documentation and validation)
SUPPORTED_PLATFORMS = frozenset(
    {
        "claude-code",
        "claude-desktop",
        "windsurf",
        "cursor",
        "cline",
    }
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def assemble_content(
    core_content: str,
    entity_type_config: dict,
    platform: str,
) -> str:
    """Assemble platform-specific content from platform-agnostic core content.

    Looks up the appropriate transformer in ``PLATFORM_TRANSFORMERS`` using
    the entity type slug and target platform.  Falls back to returning
    ``core_content`` unchanged when no transformer is registered for the
    combination.

    Args:
        core_content: Platform-agnostic content (the author's raw input).
        entity_type_config: Entity type configuration dict.  Must contain at
            minimum a ``"slug"`` key that identifies the entity type (e.g.
            ``"skill"``, ``"rule_file"``).
        platform: Target platform slug, e.g. ``"claude-code"``, ``"cursor"``.

    Returns:
        Assembled content string ready to be written to the target platform.

    Example::

        content = assemble_content(
            core_content="Do X.",
            entity_type_config={"slug": "rule_file"},
            platform="claude-code",
        )
    """
    entity_type_slug: str = entity_type_config.get("slug", "")

    transformer: Optional[TransformerFn] = PLATFORM_TRANSFORMERS.get(
        (entity_type_slug, platform)
    )

    if transformer is None:
        logger.debug(
            "No transformer registered for (%r, %r); returning core_content unchanged.",
            entity_type_slug,
            platform,
        )
        return core_content

    try:
        return transformer(core_content, entity_type_config)
    except Exception:
        logger.exception(
            "Transformer for (%r, %r) raised an exception; "
            "falling back to core_content.",
            entity_type_slug,
            platform,
        )
        return core_content


# ---------------------------------------------------------------------------
# Strip wrappers (for editing round-trips)
# ---------------------------------------------------------------------------

#: Frontmatter prefixes that assembly may prepend, keyed by entity_type_slug.
#: ``extract_core_content`` strips these when they are detected at the start
#: of the assembled content.
_ASSEMBLY_PREFIXES: Dict[str, str] = {
    "command": _COMMAND_FRONTMATTER_TEMPLATE,
    "hook": _HOOK_FRONTMATTER_TEMPLATE,
}

#: Header prefixes assembled by transformer functions.
_ASSEMBLY_HEADERS: Dict[str, str] = {
    "agent": _AGENT_HEADER_TEMPLATE,
    "mcp_server": _MCP_SERVER_HEADER_TEMPLATE,
}


def extract_core_content(content: str, entity_type_slug: str) -> str:
    """Strip platform-specific wrappers to recover the core content.

    This is the inverse of :func:`assemble_content` for entity types whose
    assembly prepends a known prefix.  For entity types that use an identity
    transform, the original content is returned unchanged.

    Only strips prefixes that were definitively added by the assembler (i.e.
    ``content`` must *start with* the exact prefix string).  If the author
    wrote their own frontmatter, ``content`` will not match the template and
    is returned as-is, preserving the author's intent.

    Args:
        content: The assembled (or plain) content string.
        entity_type_slug: The entity type slug (e.g. ``"command"``).

    Returns:
        Core content with assembly-added prefixes stripped, or ``content``
        unchanged when no stripping is applicable.

    Example::

        raw = extract_core_content(
            content="---\\nallowed-tools: []\\n---\\n\\nDo X.",
            entity_type_slug="command",
        )
        # raw == "Do X."
    """
    # Check frontmatter-style prefixes first
    prefix = _ASSEMBLY_PREFIXES.get(entity_type_slug)
    if prefix and content.startswith(prefix):
        return content[len(prefix):]

    # Check header-style prefixes
    header = _ASSEMBLY_HEADERS.get(entity_type_slug)
    if header and content.startswith(header):
        return content[len(header):]

    return content
