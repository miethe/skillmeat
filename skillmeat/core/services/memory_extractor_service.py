"""Memory extraction service with heuristic and optional LLM classification.

Extracts candidate memory items from Claude Code session transcripts (JSONL format)
or plain text. Filters noise messages, classifies content by type (learning, constraint,
gotcha, decision, style_rule), and scores candidates by quality signals. Optionally
enhances classification via LLM (Anthropic, OpenAI, Ollama, OpenAI-compatible providers)
with retry backoff, cost monitoring, and usage tracking.

Extraction is review-first: creates only `candidate` memories requiring human approval.
Supports two input formats with automatic detection and fallback:
- JSONL: Structured message logs with provenance metadata (sessionId, gitBranch, timestamp)
- Plain text: Line-based extraction for backward compatibility

Noise filtering (applied before scoring):
- XML/HTML tags: <command-name>, <system-reminder>, etc.
- Table syntax: separator rows (|---|---|), bold headers (| **Header** |)
- Action phrases: "Let me check", "I'll start", "Now let me", "Hmm,"
- System markers: <system-reminder> tags

Quality signals for scoring (confidence 0.55-0.92):
- First-person learning indicators (+0.05): "learned that", "discovered that"
- Specificity (+0.03): file paths, function names, numbers
- Question penalty (-0.03): ends with '?' or starts with question word
- Vague language penalty (-0.04): "maybe", "probably", "might"
- Noise pattern penalty (-0.25): matches XML, tables, or action phrases
- Conversational filler penalty (-0.08): "let me", "here's what", "looks like"
- Structural content penalty (-0.12): >40% non-alphanumeric characters
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from skillmeat.cache.memory_repositories import _compute_content_hash

if TYPE_CHECKING:
    from skillmeat.core.services.llm_classifier import LLMClassifier
from skillmeat.core.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

try:
    from skillmeat.observability.metrics import (
        memory_operation_duration,
        memory_operations_total,
    )
except Exception:  # pragma: no cover - metrics are optional in some envs
    memory_operation_duration = None
    memory_operations_total = None


_TYPE_RULES: List[tuple[str, re.Pattern[str]]] = [
    ("constraint", re.compile(r"\b(must|require|cannot|never|limit|blocked)\b", re.I)),
    ("gotcha", re.compile(r"\b(gotcha|beware|pitfall|timeout|lock|race)\b", re.I)),
    (
        "style_rule",
        re.compile(r"\b(style|convention|naming|format|lint|prefer)\b", re.I),
    ),
    ("decision", re.compile(r"\b(decide|decision|use|adopt|choose|standard)\b", re.I)),
    ("learning", re.compile(r"\b(learned|learning|insight|remember)\b", re.I)),
]

# Noise detection patterns - compiled once for performance
_NOISE_PATTERNS: List[re.Pattern[str]] = [
    # XML/HTML tag patterns
    re.compile(r"^<[^>]+>.*</[^>]+>$"),  # Self-contained tag pairs
    re.compile(r"^<[a-z-]+(?:\s[^>]*)?>$", re.I),  # Opening tags
    re.compile(r"^</[a-z-]+>$", re.I),  # Closing tags
    re.compile(
        r"^<[a-z]+-[a-z-]+>", re.I
    ),  # Tags like <command-name>, <local-command-*>
    re.compile(r"^<[a-z-]+-[a-z-]+></[a-z-]+>$", re.I),  # Empty tag pairs
    # Table syntax
    re.compile(r"^\|[\s\-|]+\|$"),  # Separator rows |---|---|
    re.compile(r"^\|\s*\*\*"),  # Bold table headers | **Header** |
]

# Conversational action phrases that indicate noise (case-insensitive prefixes)
_NOISE_ACTION_PREFIXES: frozenset[str] = frozenset(
    {
        "let me ",
        "i'll ",
        "i will ",
        "now let me",
        "hmm,",
        "hmm ",
        "good.",
        "good —",
        "clean,",
    }
)

# Conversational filler patterns for scoring penalty
_FILLER_PATTERNS: frozenset[str] = frozenset(
    {
        "let me ",
        "i'll start",
        "i'll check",
        "now i",
        "here's what",
        "looks like",
        "seems like",
    }
)

_PROFILE_BONUS = {
    "strict": -0.08,
    "balanced": 0.0,
    "aggressive": 0.08,
}
_VALID_PROFILES = frozenset(_PROFILE_BONUS.keys())

_ANCHOR_MUTATION_TOOLS = frozenset({"Edit", "Write"})
_ANCHOR_READ_TOOLS = frozenset({"Read", "Grep", "Glob"})
_ANCHOR_ALL_TOOLS = _ANCHOR_MUTATION_TOOLS | _ANCHOR_READ_TOOLS

# System reminder markers to filter
_SYSTEM_MARKERS: frozenset[str] = frozenset(
    {
        "<system-reminder>",
        "</system-reminder>",
    }
)


class MemoryExtractorService:
    """Extract and optionally persist candidate memories from session transcripts.

    Supports heuristic classification (fast, deterministic) and optional LLM
    classification (semantic, provider-configurable). LLM classification can be
    enabled via constructor flags or environment variables (SKILLMEAT_LLM_ENABLED,
    SKILLMEAT_LLM_PROVIDER, SKILLMEAT_LLM_MODEL).

    Args:
        db_path: Path to SQLite database (None to use default).
        use_llm: Enable LLM classification (default: False).
        llm_provider: LLM provider name ("anthropic", "openai", "ollama", "openai-compatible").
        llm_model: Model name (provider-specific, e.g., "haiku", "gpt-4o-mini").
        llm_api_key: API key for LLM provider (fallback to env vars).
        llm_base_url: Base URL for Ollama/OpenAI-compatible endpoints.

    Example:
        >>> svc = MemoryExtractorService(db_path=None, use_llm=True, llm_provider="anthropic")
        >>> candidates = svc.preview("proj-1", jsonl_data, profile="balanced")
        >>> len(candidates)  # Typically 5-30 candidates per session
        12
        >>> result = svc.apply("proj-1", jsonl_data)
        >>> result["created"]
        [{"type": "learning", "content": "...", "confidence": 0.87}, ...]
    """

    def __init__(
        self,
        db_path: Optional[str],
        use_llm: bool = False,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        llm_base_url: Optional[str] = None,
    ):
        self.memory_service = MemoryService(db_path=db_path)
        self.memory_repo = self.memory_service.repo

        # LLM classification setup
        self._classifier: Optional["LLMClassifier"] = None

        # Check if LLM is enabled: CLI param takes priority over env var
        # Only check env var if use_llm is explicitly False (default)
        env_llm_enabled = (
            os.environ.get("SKILLMEAT_LLM_ENABLED", "false").lower() == "true"
        )
        llm_enabled = use_llm if use_llm else env_llm_enabled

        if llm_enabled:
            # Resolve provider (CLI param > env var > default)
            provider = llm_provider or os.environ.get(
                "SKILLMEAT_LLM_PROVIDER", "anthropic"
            )

            # Resolve model (CLI param > env var > provider default)
            model = llm_model or os.environ.get("SKILLMEAT_LLM_MODEL")

            # Resolve API key with fallback chain
            api_key = llm_api_key or os.environ.get("SKILLMEAT_LLM_API_KEY")
            if not api_key:
                if provider == "anthropic":
                    api_key = os.environ.get("ANTHROPIC_API_KEY")
                elif provider == "openai":
                    api_key = os.environ.get("OPENAI_API_KEY")

            # Resolve base URL (CLI param > env var > default for Ollama)
            base_url = llm_base_url or os.environ.get("SKILLMEAT_LLM_BASE_URL")
            if not base_url and provider == "ollama":
                base_url = "http://localhost:11434"

            # Create classifier
            try:
                from skillmeat.core.services.llm_classifier import get_classifier

                self._classifier = get_classifier(
                    provider=provider,
                    model=model,
                    api_key=api_key,
                    base_url=base_url,
                )
                logger.info(
                    f"LLM classifier initialized: provider={provider}, model={model or 'default'}"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize LLM classifier: {e}")
                self._classifier = None

    def preview(
        self,
        project_id: str,
        text_corpus: str,
        profile: str = "balanced",
        min_confidence: float = 0.6,
        run_id: Optional[str] = None,
        session_id: Optional[str] = None,
        commit_sha: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Extract candidate memory items without persisting to database.

        Parses JSONL session data, filters noise messages (progress, system, meta),
        classifies content by type, and scores candidates by quality signals.
        Optionally enhances classification via LLM (if enabled in constructor).
        Automatically detects format and falls back to plain-text if JSONL parsing fails.

        Args:
            project_id: Project ID for provenance tracking and duplicate detection.
            text_corpus: Raw session transcript (JSONL preferred, plain text fallback).
            profile: Extraction profile ("strict", "balanced", "aggressive"). Adjusts
                confidence threshold via profile bonus: strict -0.08, balanced 0.0,
                aggressive +0.08.
            min_confidence: Minimum confidence score to include candidate (default: 0.6).
            run_id: Optional run ID for provenance tracking.
            session_id: Optional session ID for provenance (extracted from JSONL if present).
            commit_sha: Optional commit SHA for provenance.

        Returns:
            List of candidate dicts sorted by confidence descending, each with keys:
            - type (str): Memory type (learning, constraint, gotcha, decision, style_rule)
            - content (str): Extracted text content
            - confidence (float): Score 0.0-0.98 (typical range 0.55-0.92)
            - status (str): Always "candidate"
            - duplicate_of (str|None): ID if content hash matches existing memory
            - provenance (dict): Metadata including format (jsonl|plain_text),
              session_id, git_branch, timestamp, classification_method (heuristic|llm)

        Raises:
            ValueError: If profile is not one of: strict, balanced, aggressive.

        Example:
            >>> svc = MemoryExtractorService(db_path=None)
            >>> jsonl_data = '{"type":"assistant","content":"Learned that uv is faster than pip"}\\n'
            >>> candidates = svc.preview("proj-1", jsonl_data)
            >>> len(candidates)
            1
            >>> candidates[0]["type"]
            'learning'
            >>> candidates[0]["confidence"]
            0.71
            >>> candidates[0]["provenance"]["format"]
            'jsonl'

        Note:
            If extraction returns 0 candidates, ensure input is JSONL format from
            Claude Code sessions, not plain conversation text. JSONL lines must
            parse to dictionaries with 'type' and 'content' fields.
        """
        started = time.perf_counter()
        status_label = "success"
        self._validate_profile(profile)
        try:
            candidates: List[Dict[str, Any]] = []
            seen_content: set[str] = set()

            # Two-path extraction: try JSONL parsing first, fall back to plain-text
            messages = self._parse_jsonl_messages(text_corpus)
            resolved_commit_sha = commit_sha or self._detect_git_commit(messages)

            # Detect if we should fall back: empty messages but non-empty input
            has_input = bool(text_corpus and text_corpus.strip())
            should_fallback = not messages and has_input

            if should_fallback:
                # Check if input looks like JSON attempts (heuristic: contains '{' or '[')
                looks_like_json = "{" in text_corpus or "[" in text_corpus
                if looks_like_json:
                    logger.info(
                        "All JSONL lines failed to parse; falling back to plain-text extraction"
                    )
                else:
                    logger.info(
                        "No JSONL messages found; falling back to plain-text extraction"
                    )

            if messages:
                tool_refs_by_message = self._extract_tool_call_paths(messages)
                content_blocks = self._extract_content_blocks(messages)
                for content_text, provenance_meta in content_blocks:
                    message_index = provenance_meta.get("message_index")
                    if not isinstance(message_index, int):
                        message_index = None
                    anchors = self._build_anchors_for_message_window(
                        tool_refs_by_message=tool_refs_by_message,
                        message_index=message_index,
                        commit_sha=resolved_commit_sha,
                    )

                    effective_session_id = (
                        provenance_meta.get("session_id")
                        or session_id
                        or ""
                    )
                    effective_git_branch = provenance_meta.get("git_branch") or ""
                    effective_git_commit = (
                        provenance_meta.get("git_commit")
                        or resolved_commit_sha
                        or ""
                    )
                    effective_agent_type = provenance_meta.get("agent_type")
                    effective_model = provenance_meta.get("model")

                    # Split each content block into candidate lines
                    block_lines = [
                        ln.strip(" -*\t") for ln in content_text.splitlines()
                    ]
                    block_lines = [ln for ln in block_lines if len(ln.strip()) >= 24]

                    for line in block_lines:
                        # Skip noise patterns early (before scoring)
                        if self._is_noise(line):
                            continue

                        mem_type = self._classify_type(line)
                        confidence = self._score(line, mem_type, profile)
                        if confidence < min_confidence:
                            continue

                        normalized = line.strip().lower()
                        if normalized in seen_content:
                            continue
                        seen_content.add(normalized)

                        content_hash = _compute_content_hash(line.strip())
                        duplicate = self.memory_repo.get_by_content_hash(content_hash)

                        # Build provenance: base fields + JSONL message metadata
                        provenance = {
                            "source": "memory_extraction",
                            "format": "jsonl",
                            "run_id": run_id,
                            "session_id": effective_session_id,
                            "commit_sha": effective_git_commit,
                            "workflow_stage": "extraction",
                            "classification_method": "heuristic",
                            "git_branch": effective_git_branch,
                            "git_commit": effective_git_commit,
                            "agent_type": effective_agent_type,
                            "model": effective_model,
                            "source_type": "extraction",
                        }
                        provenance.update(provenance_meta)
                        provenance.pop("message_index", None)
                        provenance["session_id"] = effective_session_id
                        provenance["git_branch"] = effective_git_branch
                        provenance["git_commit"] = effective_git_commit
                        provenance["source_type"] = "extraction"

                        candidates.append(
                            {
                                "type": mem_type,
                                "content": line.strip(),
                                "confidence": round(confidence, 3),
                                "status": "candidate",
                                "duplicate_of": duplicate.id if duplicate else None,
                                "provenance": provenance,
                                "anchors": anchors,
                                "git_branch": effective_git_branch,
                                "git_commit": effective_git_commit,
                                "session_id": effective_session_id,
                                "agent_type": effective_agent_type,
                                "model": effective_model,
                                "source_type": "extraction",
                            }
                        )
                        logger.debug(
                            "Built extraction candidate with %d anchors (message_index=%s)",
                            len(anchors),
                            message_index,
                        )
            else:
                # Fallback: plain-text line extraction (backward compat)
                for line in self._iter_candidate_lines(text_corpus):
                    # Skip noise patterns early (before scoring)
                    if self._is_noise(line):
                        continue

                    mem_type = self._classify_type(line)
                    confidence = self._score(line, mem_type, profile)
                    if confidence < min_confidence:
                        continue

                    normalized = line.strip().lower()
                    if normalized in seen_content:
                        continue
                    seen_content.add(normalized)

                    content_hash = _compute_content_hash(line.strip())
                    duplicate = self.memory_repo.get_by_content_hash(content_hash)
                    candidates.append(
                        {
                            "type": mem_type,
                            "content": line.strip(),
                            "confidence": round(confidence, 3),
                            "status": "candidate",
                            "duplicate_of": duplicate.id if duplicate else None,
                            "provenance": {
                                "source": "memory_extraction",
                                "format": "plain_text",
                                "run_id": run_id,
                                "session_id": session_id or "",
                                "commit_sha": resolved_commit_sha,
                                "workflow_stage": "extraction",
                                "classification_method": "heuristic",
                                "git_commit": resolved_commit_sha,
                                "source_type": "extraction",
                            },
                            "anchors": [],
                            "git_branch": "",
                            "git_commit": resolved_commit_sha,
                            "session_id": session_id or "",
                            "agent_type": None,
                            "model": None,
                            "source_type": "extraction",
                        }
                    )

            # Apply LLM classification if classifier is available
            if self._classifier and candidates:
                logger.info(
                    f"Applying LLM classification to {len(candidates)} candidates"
                )
                self._apply_llm_classification(candidates)

            candidates.sort(key=lambda c: (-c["confidence"], c["content"]))
            return candidates
        except Exception:
            status_label = "error"
            raise
        finally:
            self._record_operation_metrics(
                operation="extract_preview",
                status=status_label,
                started=started,
            )

    def apply(
        self,
        project_id: str,
        text_corpus: str,
        profile: str = "balanced",
        min_confidence: float = 0.6,
        run_id: Optional[str] = None,
        session_id: Optional[str] = None,
        commit_sha: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract and persist candidate memories to database.

        Calls preview() to extract candidates, then persists non-duplicate items
        to database with status="candidate". Duplicates are detected by content
        hash and skipped.

        Args:
            project_id: Project ID for provenance tracking and duplicate detection.
            text_corpus: Raw session transcript (JSONL preferred, plain text fallback).
            profile: Extraction profile ("strict", "balanced", "aggressive").
            min_confidence: Minimum confidence score to include candidate (default: 0.6).
            run_id: Optional run ID for provenance tracking.
            session_id: Optional session ID for provenance.
            commit_sha: Optional commit SHA for provenance.

        Returns:
            Dict with keys:
            - created (list): Persisted memory items with database IDs
            - skipped_duplicates (list): Items skipped due to duplicate content hash
            - preview_total (int): Total candidates extracted (created + skipped)

        Raises:
            ValueError: If profile is not one of: strict, balanced, aggressive.

        Example:
            >>> svc = MemoryExtractorService(db_path=None)
            >>> result = svc.apply("proj-1", jsonl_data)
            >>> result["preview_total"]
            12
            >>> len(result["created"])
            10
            >>> len(result["skipped_duplicates"])
            2
            >>> result["created"][0]["status"]
            'candidate'
        """
        started = time.perf_counter()
        status_label = "success"
        try:
            preview_items = self.preview(
                project_id=project_id,
                text_corpus=text_corpus,
                profile=profile,
                min_confidence=min_confidence,
                run_id=run_id,
                session_id=session_id,
                commit_sha=commit_sha,
            )

            created: List[Dict[str, Any]] = []
            skipped_duplicates: List[Dict[str, Any]] = []
            for item in preview_items:
                if item["duplicate_of"]:
                    skipped_duplicates.append(item)
                    continue
                created_item = self.memory_service.create(
                    project_id=project_id,
                    type=item["type"],
                    content=item["content"],
                    confidence=item["confidence"],
                    status="candidate",
                    provenance=item["provenance"],
                    anchors=item.get("anchors"),
                    git_branch=item.get("git_branch"),
                    git_commit=item.get("git_commit"),
                    session_id=item.get("session_id"),
                    agent_type=item.get("agent_type"),
                    model=item.get("model"),
                    source_type=item.get("source_type"),
                )
                created.append(created_item)

            return {
                "created": created,
                "skipped_duplicates": skipped_duplicates,
                "preview_total": len(preview_items),
            }
        except Exception:
            status_label = "error"
            raise
        finally:
            self._record_operation_metrics(
                operation="extract_apply",
                status=status_label,
                started=started,
            )

    @staticmethod
    def _iter_candidate_lines(text_corpus: str) -> List[str]:
        lines = [line.strip(" -*\t") for line in text_corpus.splitlines()]
        return [line for line in lines if len(line.strip()) >= 24]

    @staticmethod
    def _is_noise(line: str) -> bool:
        """Detect noise patterns that should be filtered before scoring.

        Identifies content that is structural, conversational filler, or
        non-substantive. Returns True for lines that match any noise pattern.

        Noise categories detected:
        1. XML/HTML tags: Opening, closing, self-contained, or empty tag pairs
           Examples: <command-name>/clear</command-name>, <system-reminder>
        2. Table syntax: Separator rows, bold headers, table-like structures
           Examples: |-------|-----------|-----|, | **Header** |
        3. Action phrases: Transitional or conversational starters
           Examples: "Let me check", "Hmm, the diff is empty", "Good. Now I"
        4. System markers: System reminder tags and similar structural markers

        Args:
            line: Candidate text line to check for noise patterns.

        Returns:
            True if the line matches any noise pattern, False otherwise.

        Example:
            >>> _is_noise("<command-name>/clear</command-name>")
            True
            >>> _is_noise("| Issue | Root Cause | Fix |")
            True
            >>> _is_noise("Let me check the configuration")
            True
            >>> _is_noise("Learned that uv resolves dependencies faster than pip")
            False
        """
        line_stripped = line.strip()
        line_lower = line_stripped.lower()

        # Check compiled regex patterns (XML/HTML tags, table separators)
        for pattern in _NOISE_PATTERNS:
            if pattern.match(line_stripped):
                return True

        # Check action phrase prefixes (case-insensitive)
        for prefix in _NOISE_ACTION_PREFIXES:
            if line_lower.startswith(prefix):
                return True

        # Check system markers
        for marker in _SYSTEM_MARKERS:
            if marker in line_lower:
                return True

        # Table-like structure: 3+ pipe characters suggests table row
        if line_stripped.count("|") >= 3:
            return True

        return False

    @staticmethod
    def _parse_jsonl_messages(text_corpus: str) -> list[dict]:
        """Parse JSONL format text corpus into list of message dictionaries.

        Handles three input formats:
        1. Standard JSONL: One JSON object per line
        2. JSON-string-wrapped JSONL: Entire corpus is a JSON string with escaped newlines
        3. Mixed: Lines that fail parsing are skipped with debug logging

        Claude Code session logs use standard JSONL format with one message per line.
        Each message typically contains: type, role, content, timestamp, sessionId,
        gitBranch, uuid, and optional metadata fields.

        Args:
            text_corpus: String containing JSONL data or JSON-string-wrapped JSONL.

        Returns:
            List of dictionaries parsed from valid JSON lines. Lines that fail
            parsing or parse to non-dict types are skipped with debug logging.
            Empty list if all lines fail to parse or input is empty.

        Example:
            >>> _parse_jsonl_messages('{"role":"user","content":"test"}\\n{"role":"assistant","content":"reply"}')
            [{"role": "user", "content": "test"}, {"role": "assistant", "content": "reply"}]

            >>> _parse_jsonl_messages('"{\\"role\\":\\"user\\"}\\n{\\"role\\":\\"assistant\\"}"')
            [{"role": "user"}, {"role": "assistant"}]

            >>> _parse_jsonl_messages('invalid json\\n{"role":"user"}')  # Mixed valid/invalid
            [{"role": "user"}]
        """
        if not text_corpus or not text_corpus.strip():
            return []

        corpus = text_corpus.strip()

        # Handle JSON-string-wrapped JSONL: if starts with quote, try unwrapping
        if corpus.startswith('"'):
            try:
                corpus = json.loads(corpus)
                if not isinstance(corpus, str):
                    logger.debug(
                        "Unwrapped JSON was not a string, using original corpus"
                    )
                    corpus = text_corpus.strip()
            except json.JSONDecodeError:
                logger.debug(
                    "Failed to unwrap JSON-string format, treating as regular JSONL"
                )

        messages: list[dict] = []
        for line_num, line in enumerate(corpus.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue

            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    messages.append(parsed)
                else:
                    logger.debug(
                        f"Line {line_num} parsed to non-dict type ({type(parsed).__name__}), skipping"
                    )
            except json.JSONDecodeError as e:
                logger.debug(f"Line {line_num} failed JSON parsing: {e}, skipping")

        return messages

    @staticmethod
    def _extract_content_blocks(messages: List[Dict]) -> List[tuple[str, Dict]]:
        """Extract content blocks from JSONL message structures with filtering.

        Supports two JSONL formats:
        1. Claude Code JSONL: content nested in a ``message`` sub-dict
           ``{"type": "assistant", "message": {"role": "assistant", "content": [...]}, ...}``
        2. Plain JSONL: content at the top level
           ``{"type": "assistant", "content": "...", ...}``

        Applies noise filtering to skip non-content messages:
        - Skips message types: progress, file-history-snapshot, system, result
        - Skips meta messages (isMeta=true)
        - Skips tool use results (toolUseResult=true)
        - Extracts only text blocks from content (skips tool_use/tool_result blocks)

        Processes both user and assistant messages. Extracts provenance metadata
        including sessionId, gitBranch, timestamp for tracking learning context.

        Args:
            messages: List of message dictionaries from JSONL run log. Expected
                structure per message (Claude Code format):
                - type: "user" | "assistant" | "progress" | "system" | etc.
                - message: {"role": "user"|"assistant", "content": str|list[dict]}
                - timestamp, sessionId, gitBranch, uuid: metadata fields (top-level)

                Plain format (backward-compatible):
                - type: "human" | "assistant" | "progress" | "system" | etc.
                - role: "user" | "assistant" (optional)
                - content: str | list[dict] (text blocks or mixed content)
                - timestamp, sessionId, gitBranch, uuid: metadata fields

        Returns:
            List of (content_text, provenance_metadata) tuples. Only includes
            content blocks >= 20 characters. Provenance dict keys:
            - message_uuid: Unique message identifier
            - message_role: Message type or role (e.g., "assistant", "human")
            - timestamp: ISO 8601 timestamp string
            - session_id: Session identifier from JSONL
            - git_branch: Git branch name (empty string if missing)

        Example:
            >>> messages = [
            ...     {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "Learned that uv is faster"}]}, "sessionId": "s1", "gitBranch": "main"},
            ...     {"type": "progress", "content": "Working..."},  # Skipped (noise)
            ...     {"type": "assistant", "content": [{"type": "text", "text": "Important insight"}]}
            ... ]
            >>> blocks = _extract_content_blocks(messages)
            >>> len(blocks)
            2
            >>> blocks[0][0]
            'Learned that uv is faster'
            >>> blocks[0][1]["git_branch"]
            'main'
        """
        # Message types to skip (noise)
        skip_types = {"progress", "file-history-snapshot", "system", "result"}

        results: List[tuple[str, Dict]] = []

        for message_index, message in enumerate(messages):
            msg_type = message.get("type")
            msg_role = message.get("role")

            # Skip noise message types
            if msg_type in skip_types:
                logger.debug(f"Skipping message with type={msg_type}")
                continue

            # Skip meta messages and tool results
            if message.get("isMeta") in (True, "true"):
                logger.debug("Skipping meta message")
                continue
            if message.get("toolUseResult") is True:
                logger.debug("Skipping tool use result message")
                continue

            # Determine if this is a user or assistant message
            # Claude Code JSONL uses type="user", plain JSONL uses type="human"
            is_user = msg_type in ("human", "user") or msg_role == "user"
            is_assistant = msg_type == "assistant" or msg_role == "assistant"

            if not (is_user or is_assistant):
                logger.debug(f"Skipping message with type={msg_type}, role={msg_role}")
                continue

            # Extract content - check nested message structure first (Claude Code JSONL),
            # then fall back to top-level content (plain JSONL)
            inner_msg = message.get("message")
            if isinstance(inner_msg, dict):
                content = inner_msg.get("content")
                # Also get role from inner message if not at top level
                if not msg_role:
                    msg_role = inner_msg.get("role")
            else:
                content = message.get("content")
            if content is None:
                continue

            # Extract text blocks
            text_blocks: List[str] = []
            if isinstance(content, str):
                text_blocks.append(content)
            elif isinstance(content, list):
                # Extract only text-type blocks, skip tool_use/tool_result
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_blocks.append(block.get("text", ""))
            else:
                logger.debug(f"Unexpected content type: {type(content)}")
                continue

            # Join text blocks and filter by length
            content_text = "\n".join(text_blocks).strip()
            if len(content_text) < 20:
                logger.debug(f"Skipping short content: {len(content_text)} chars")
                continue

            # Build provenance metadata
            metadata = message.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}

            inner_metadata = (
                inner_msg.get("metadata")
                if isinstance(inner_msg, dict) and isinstance(inner_msg.get("metadata"), dict)
                else {}
            )

            model = (
                message.get("model")
                or (inner_msg.get("model") if isinstance(inner_msg, dict) else None)
                or metadata.get("model")
                or inner_metadata.get("model")
            )

            agent_type = (
                message.get("agent_type")
                or message.get("agentType")
                or metadata.get("agent_type")
                or metadata.get("agentType")
                or inner_metadata.get("agent_type")
                or inner_metadata.get("agentType")
            )

            git_commit = (
                message.get("git_commit")
                or message.get("gitCommit")
                or metadata.get("git_commit")
                or metadata.get("gitCommit")
                or metadata.get("commit_sha")
                or metadata.get("commitSha")
                or inner_metadata.get("git_commit")
                or inner_metadata.get("gitCommit")
                or inner_metadata.get("commit_sha")
                or inner_metadata.get("commitSha")
            )

            provenance = {
                "message_uuid": message.get("uuid", ""),
                "message_role": msg_type or msg_role or "unknown",
                "timestamp": message.get("timestamp", ""),
                "session_id": message.get("sessionId", "")
                or message.get("session_id", "")
                or metadata.get("session_id", "")
                or metadata.get("sessionId", ""),
                "git_branch": message.get("gitBranch", "")
                or message.get("git_branch", "")
                or metadata.get("git_branch", "")
                or metadata.get("gitBranch", ""),
                "message_index": message_index,
            }
            if isinstance(model, str) and model.strip():
                provenance["model"] = model.strip()
            if isinstance(agent_type, str) and agent_type.strip():
                provenance["agent_type"] = agent_type.strip()
            if isinstance(git_commit, str) and git_commit.strip():
                provenance["git_commit"] = git_commit.strip()

            results.append((content_text, provenance))

        logger.debug(
            f"Extracted {len(results)} content blocks from {len(messages)} messages"
        )
        return results

    @staticmethod
    def _tool_call_priority(tool_name: str) -> int:
        """Rank mutation calls above read-only calls for anchor ordering."""
        if tool_name in _ANCHOR_MUTATION_TOOLS:
            return 0
        return 1

    @staticmethod
    def classify_anchor_type(path: str) -> str:
        """Classify an anchor path into code/test/doc/config/plan."""
        normalized = path.strip().lower()
        if not normalized:
            return "code"

        if "/tests/" in normalized or normalized.startswith("tests/"):
            return "test"
        basename = normalized.rsplit("/", 1)[-1]
        if basename.startswith("test_"):
            return "test"

        if normalized.endswith(".md"):
            if ".claude/progress/" in normalized or ".claude/worknotes/" in normalized:
                return "plan"
            if "/docs/" in normalized or normalized.startswith("docs/"):
                return "doc"
            if "project_plans/" in normalized:
                return "doc"

        config_exts = (".toml", ".yaml", ".yml", ".json", ".ini", ".cfg")
        if normalized.endswith(config_exts):
            return "config"
        if basename == ".env" or basename.startswith(".env."):
            return "config"

        return "code"

    @staticmethod
    def _extract_path_from_tool_input(
        tool_name: str, tool_input: Dict[str, Any]
    ) -> tuple[Optional[str], Optional[int], Optional[int]]:
        """Extract path and optional line range from a tool input payload."""
        path: Optional[str] = None
        if tool_name in {"Read", "Edit", "Write"}:
            path = tool_input.get("file_path") or tool_input.get("path")
        elif tool_name in {"Grep", "Glob"}:
            path = tool_input.get("path")

        if not isinstance(path, str) or not path.strip():
            return None, None, None

        line_start: Optional[int] = None
        line_end: Optional[int] = None
        if isinstance(tool_input.get("line_start"), int):
            line_start = tool_input["line_start"]
        elif isinstance(tool_input.get("start_line"), int):
            line_start = tool_input["start_line"]
        elif isinstance(tool_input.get("line"), int):
            line_start = tool_input["line"]
        elif isinstance(tool_input.get("start"), int):
            line_start = tool_input["start"]

        if isinstance(tool_input.get("line_end"), int):
            line_end = tool_input["line_end"]
        elif isinstance(tool_input.get("end_line"), int):
            line_end = tool_input["end_line"]
        elif isinstance(tool_input.get("end"), int):
            line_end = tool_input["end"]

        if line_start is not None and line_start < 1:
            line_start = None
        if line_end is not None and line_end < 1:
            line_end = None
        if line_start is not None and line_end is not None and line_end < line_start:
            line_start = None
            line_end = None

        return path.strip(), line_start, line_end

    def _extract_tool_call_paths(
        self, messages: List[Dict[str, Any]]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Extract tool call path references grouped by message index."""
        by_message: Dict[int, List[Dict[str, Any]]] = {}

        for index, message in enumerate(messages):
            inner_msg = message.get("message")
            if isinstance(inner_msg, dict):
                content = inner_msg.get("content")
            else:
                content = message.get("content")

            if not isinstance(content, list):
                continue

            refs: List[Dict[str, Any]] = []
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                tool_name = block.get("name")
                if tool_name not in _ANCHOR_ALL_TOOLS:
                    continue
                tool_input = block.get("input") or {}
                if not isinstance(tool_input, dict):
                    continue

                path, line_start, line_end = self._extract_path_from_tool_input(
                    tool_name, tool_input
                )
                if not path:
                    continue

                ref: Dict[str, Any] = {
                    "path": path,
                    "tool_name": tool_name,
                    "priority": self._tool_call_priority(tool_name),
                }
                if line_start is not None:
                    ref["line_start"] = line_start
                if line_end is not None:
                    ref["line_end"] = line_end
                refs.append(ref)

            if refs:
                by_message[index] = refs

        return by_message

    def _build_anchors_for_message_window(
        self,
        *,
        tool_refs_by_message: Dict[int, List[Dict[str, Any]]],
        message_index: Optional[int],
        commit_sha: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Construct ranked, deduplicated anchors for a candidate message window."""
        if message_index is None:
            return []

        combined: List[Dict[str, Any]] = []
        for idx in (message_index - 1, message_index, message_index + 1):
            combined.extend(tool_refs_by_message.get(idx, []))

        deduped: Dict[str, Dict[str, Any]] = {}

        def range_width(ref: Dict[str, Any]) -> int:
            start = ref.get("line_start")
            end = ref.get("line_end")
            if isinstance(start, int) and isinstance(end, int):
                return end - start
            if isinstance(start, int):
                return 0
            return 10**9

        for ref in combined:
            path = ref["path"]
            existing = deduped.get(path)
            if existing is None:
                deduped[path] = ref
                continue

            if ref["priority"] < existing["priority"]:
                deduped[path] = ref
                continue

            if ref["priority"] == existing["priority"] and range_width(ref) < range_width(
                existing
            ):
                deduped[path] = ref

        ordered = sorted(deduped.values(), key=lambda r: (r["priority"], r["path"]))
        anchors: List[Dict[str, Any]] = []
        for ref in ordered[:20]:
            anchor: Dict[str, Any] = {
                "path": ref["path"],
                "type": self.classify_anchor_type(ref["path"]),
            }
            if "line_start" in ref:
                anchor["line_start"] = ref["line_start"]
            if "line_end" in ref:
                anchor["line_end"] = ref["line_end"]
            if commit_sha:
                anchor["commit_sha"] = commit_sha
            anchors.append(anchor)

        return anchors

    @staticmethod
    def _detect_git_commit(messages: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
        """Best-effort git commit detection from git CLI or message metadata."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
                timeout=2,
            )
            commit = result.stdout.strip()
            if commit:
                return commit
        except Exception:
            pass

        if not messages:
            return None

        candidate_fields = ("git_commit", "gitCommit", "commit_sha", "commitSha", "commit")
        for message in messages:
            for field in candidate_fields:
                value = message.get(field)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            metadata = message.get("metadata")
            if isinstance(metadata, dict):
                for field in candidate_fields:
                    value = metadata.get(field)
                    if isinstance(value, str) and value.strip():
                        return value.strip()

        return None

    @staticmethod
    def _classify_type(line: str) -> str:
        for mem_type, pattern in _TYPE_RULES:
            if pattern.search(line):
                return mem_type
        return "learning"

    @classmethod
    def _score(cls, line: str, mem_type: str, profile: str) -> float:
        """Calculate confidence score for a candidate line using quality signals.

        Base scoring:
        - Start: 0.58 + length bonus (max 0.18 for lines >= 200 chars)
        - Type bonus: decision/constraint +0.08, gotcha/style_rule +0.05
        - Profile adjustment: strict -0.08, balanced 0.0, aggressive +0.08

        Content quality signals (additive):
        - First-person learning (+0.05): "learned that", "discovered that",
          "realized that", "found that", "noticed that", "understood that"
        - Specificity (+0.03): file paths (.py, .ts, .tsx, .js, .md), function
          names (contains "()"), or numbers
        - Question penalty (-0.03): ends with '?' or starts with question word
          (why, how, what, should, could, would, can, is, are, does, do)
        - Vague language (-0.04): "maybe", "probably", "might", "perhaps",
          "possibly", "somehow", "something", "somewhere"

        Noise penalties (post-quality signals):
        - Noise pattern penalty (-0.25): XML/HTML tags, table syntax, action phrases
        - Conversational filler penalty (-0.08): "let me ", "i'll start", etc.
        - Structural content penalty (-0.12): Lines with >40% non-alphanumeric chars

        Args:
            line: Candidate text to score.
            mem_type: Memory type from classification (learning, constraint, etc.).
            profile: Extraction profile ("strict", "balanced", "aggressive").

        Returns:
            Float confidence score clamped to [0.0, 0.98]. Typical range: 0.55-0.92.

        Example:
            >>> _score("Learned that uv is faster than pip for package management", "learning", "balanced")
            0.76  # Base + length + learning pattern + specificity
            >>> _score("Maybe we should try this approach?", "learning", "balanced")
            0.58  # Base - question - vague language
            >>> _score("Let me check the configuration files", "learning", "balanced")
            0.50  # Base - filler penalty
        """
        base = 0.58
        base += min(len(line) / 200.0, 0.18)
        if mem_type in {"decision", "constraint"}:
            base += 0.08
        elif mem_type in {"gotcha", "style_rule"}:
            base += 0.05
        base += _PROFILE_BONUS[profile]

        # Content quality signals
        line_lower = line.lower()

        # 1. First-person learning indicators (+0.05)
        learning_patterns = {
            "learned that",
            "discovered that",
            "realized that",
            "found that",
            "noticed that",
            "understood that",
        }
        if any(pattern in line_lower for pattern in learning_patterns):
            base += 0.05

        # 2. Specificity indicators (+0.03)
        has_path = "/" in line or any(
            ext in line_lower for ext in {".py", ".ts", ".tsx", ".js", ".md"}
        )
        has_function = "()" in line
        has_numbers = any(char.isdigit() for char in line)
        if has_path or has_function or has_numbers:
            base += 0.03

        # 3. Question penalty (-0.03)
        question_starters = {
            "why",
            "how",
            "what",
            "should",
            "could",
            "would",
            "can",
            "is",
            "are",
            "does",
            "do",
        }
        is_question = line.rstrip().endswith("?") or any(
            line_lower.startswith(word + " ") for word in question_starters
        )
        if is_question:
            base -= 0.03

        # 4. Vague language penalty (-0.04)
        vague_words = {
            "maybe",
            "probably",
            "might",
            "perhaps",
            "possibly",
            "somehow",
            "something",
            "somewhere",
        }
        if any(word in line_lower for word in vague_words):
            base -= 0.04

        # 5. Noise pattern penalty (-0.25) - severe penalty to push below threshold
        if cls._is_noise(line):
            base -= 0.25

        # 6. Conversational filler penalty (-0.08)
        if any(pattern in line_lower for pattern in _FILLER_PATTERNS):
            base -= 0.08

        # 7. Pure structural content penalty (-0.12)
        # Lines that are mostly punctuation/formatting (>40% non-alphanumeric)
        if len(line) > 0:
            non_alpha_count = sum(1 for c in line if not c.isalnum() and c != " ")
            non_alpha_ratio = non_alpha_count / len(line)
            if non_alpha_ratio > 0.4:
                base -= 0.12

        return max(0.0, min(base, 0.98))

    def _apply_llm_classification(self, candidates: List[Dict[str, Any]]) -> None:
        """Apply LLM semantic classification to candidates in-place.

        For each candidate where LLM returns a result, overrides the heuristic
        type and confidence with LLM values. Adds LLM reasoning and provider
        to provenance metadata. Gracefully falls back to heuristic classification
        when LLM fails (network error, rate limit, invalid response).

        Updates provenance field `classification_method` to "llm" on success,
        keeps "heuristic" on failure. Logs success/fallback counts and usage
        stats (tokens, cost) if available.

        Args:
            candidates: List of candidate dicts to classify (modified in-place).
                Each dict must have 'content' key. Modified keys: type, confidence,
                provenance (adds classification_method, llm_reasoning, llm_provider).

        Example:
            >>> candidates = [{"content": "Use uv not pip", "type": "learning", "confidence": 0.65}]
            >>> svc._apply_llm_classification(candidates)
            >>> candidates[0]["type"]  # May change based on LLM analysis
            'style_rule'
            >>> candidates[0]["confidence"]
            0.88
            >>> candidates[0]["provenance"]["classification_method"]
            'llm'
            >>> candidates[0]["provenance"]["llm_reasoning"]
            'Tool choice recommendation with clear preference'
        """
        if not self._classifier:
            return

        # Collect content texts for batch classification
        contents = [c["content"] for c in candidates]

        # Call LLM classifier
        llm_results = self._semantic_classify_batch(contents, self._classifier)

        # Track success/fallback counts
        llm_success = 0
        llm_fallback = 0

        # Apply LLM results to candidates
        for candidate, llm_result in zip(candidates, llm_results):
            if llm_result:
                # Override type and confidence with LLM values
                candidate["type"] = llm_result["type"]
                candidate["confidence"] = round(llm_result["confidence"], 3)

                # Add LLM metadata to provenance
                if "provenance" not in candidate:
                    candidate["provenance"] = {}

                candidate["provenance"]["classification_method"] = "llm"
                candidate["provenance"]["llm_reasoning"] = llm_result.get(
                    "reasoning", ""
                )
                candidate["provenance"]["llm_provider"] = self._classifier.provider_name
                llm_success += 1
            else:
                # LLM failed, keep heuristic values
                if "provenance" not in candidate:
                    candidate["provenance"] = {}

                candidate["provenance"]["classification_method"] = "heuristic"
                llm_fallback += 1

        logger.info(
            f"LLM classification complete: {llm_success}/{len(candidates)} classified, "
            f"{llm_fallback} fell back to heuristic (provider={self._classifier.provider_name})"
        )

        # Log usage stats
        if hasattr(self._classifier, "usage_stats"):
            logger.info(
                self._classifier.usage_stats.summary(
                    provider=self._classifier.provider_name,
                    model=getattr(self._classifier, "model", ""),
                )
            )

    def _semantic_classify_batch(
        self,
        contents: List[str],
        classifier: Optional["LLMClassifier"] = None,
    ) -> List[Optional[Dict[str, Any]]]:
        """Classify candidates using an LLM provider with automatic fallback.

        Calls LLM classifier in batch mode for efficiency. If classifier is None,
        unavailable, or classification fails, returns None values for transparent
        fallback to heuristic scoring. Handles network errors, rate limits, and
        invalid responses gracefully.

        Args:
            contents: List of candidate text strings to classify.
            classifier: An LLMClassifier instance from llm_classifier module.
                May be None to indicate LLM classification is disabled.

        Returns:
            List of classification dicts or None per item. Each successful
            classification dict contains:
            - type (str): Memory type (learning, constraint, gotcha, etc.)
            - confidence (float): LLM-assigned confidence score 0.0-1.0
            - reasoning (str): LLM explanation for classification
            Returns [None, None, ...] if classifier unavailable or fails.

        Example:
            >>> from skillmeat.core.services.llm_classifier import get_classifier
            >>> classifier = get_classifier(provider="anthropic")
            >>> results = _semantic_classify_batch(["Use uv not pip"], classifier)
            >>> results[0]["type"]
            'style_rule'
            >>> results[0]["confidence"]
            0.92
        """
        if classifier is None:
            return [None] * len(contents)

        # Import the type only for the availability check
        from skillmeat.core.services.llm_classifier import LLMClassifier as _LC

        if not isinstance(classifier, _LC) or not classifier.is_available():
            return [None] * len(contents)

        try:
            results = classifier.classify_batch(contents)
            return [r.to_dict() if r else None for r in results]
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")
            return [None] * len(contents)

    @staticmethod
    def _validate_profile(profile: str) -> None:
        if profile not in _VALID_PROFILES:
            raise ValueError(
                f"Invalid extraction profile '{profile}'. "
                f"Must be one of: {sorted(_VALID_PROFILES)}"
            )

    @staticmethod
    def _record_operation_metrics(operation: str, status: str, started: float) -> None:
        """Record extraction operation counters and duration."""
        duration = max(0.0, time.perf_counter() - started)
        if memory_operations_total is not None:
            memory_operations_total.labels(operation=operation, status=status).inc()
        if memory_operation_duration is not None:
            memory_operation_duration.labels(operation=operation).observe(duration)
