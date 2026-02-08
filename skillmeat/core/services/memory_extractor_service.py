"""Heuristic memory extraction service.

Provides deterministic extraction of candidate memory items from run logs
or arbitrary text corpora. Extraction is review-first and only creates
`candidate` memories on apply.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

from skillmeat.cache.memory_repositories import _compute_content_hash
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
    ("style_rule", re.compile(r"\b(style|convention|naming|format|lint|prefer)\b", re.I)),
    ("decision", re.compile(r"\b(decide|decision|use|adopt|choose|standard)\b", re.I)),
    ("learning", re.compile(r"\b(learned|learning|insight|remember)\b", re.I)),
]

_PROFILE_BONUS = {
    "strict": -0.08,
    "balanced": 0.0,
    "aggressive": 0.08,
}
_VALID_PROFILES = frozenset(_PROFILE_BONUS.keys())


class MemoryExtractorService:
    """Extract and optionally persist candidate memories."""

    def __init__(self, db_path: Optional[str]):
        self.memory_service = MemoryService(db_path=db_path)
        self.memory_repo = self.memory_service.repo

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
        """Extract candidate memory items without persisting."""
        started = time.perf_counter()
        status_label = "success"
        self._validate_profile(profile)
        try:
            candidates: List[Dict[str, Any]] = []
            seen_content: set[str] = set()

            # Two-path extraction: try JSONL parsing first, fall back to plain-text
            messages = self._parse_jsonl_messages(text_corpus)

            # Detect if we should fall back: empty messages but non-empty input
            has_input = bool(text_corpus and text_corpus.strip())
            should_fallback = not messages and has_input

            if should_fallback:
                # Check if input looks like JSON attempts (heuristic: contains '{' or '[')
                looks_like_json = "{" in text_corpus or "[" in text_corpus
                if looks_like_json:
                    logger.info("All JSONL lines failed to parse; falling back to plain-text extraction")
                else:
                    logger.info("No JSONL messages found; falling back to plain-text extraction")

            if messages:
                content_blocks = self._extract_content_blocks(messages)
                for content_text, provenance_meta in content_blocks:
                    # Split each content block into candidate lines
                    block_lines = [
                        ln.strip(" -*\t")
                        for ln in content_text.splitlines()
                    ]
                    block_lines = [ln for ln in block_lines if len(ln.strip()) >= 24]

                    for line in block_lines:
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
                            "session_id": session_id,
                            "commit_sha": commit_sha,
                            "workflow_stage": "extraction",
                        }
                        provenance.update(provenance_meta)

                        candidates.append(
                            {
                                "type": mem_type,
                                "content": line.strip(),
                                "confidence": round(confidence, 3),
                                "status": "candidate",
                                "duplicate_of": duplicate.id if duplicate else None,
                                "provenance": provenance,
                            }
                        )
            else:
                # Fallback: plain-text line extraction (backward compat)
                for line in self._iter_candidate_lines(text_corpus):
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
                                "session_id": session_id,
                                "commit_sha": commit_sha,
                                "workflow_stage": "extraction",
                            },
                        }
                    )

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
        """Extract and persist candidate memories."""
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
    def _parse_jsonl_messages(text_corpus: str) -> list[dict]:
        """Parse JSONL format text corpus into list of message dictionaries.

        Handles three input formats:
        1. Standard JSONL: One JSON object per line
        2. JSON-string-wrapped JSONL: Entire corpus is a JSON string with escaped newlines
        3. Mixed: Lines that fail parsing are skipped with debug logging

        Args:
            text_corpus: String containing JSONL data or JSON-string-wrapped JSONL

        Returns:
            List of dictionaries parsed from valid JSON lines. Lines that fail
            parsing or parse to non-dict types are skipped.

        Examples:
            >>> _parse_jsonl_messages('{"role":"user"}\\n{"role":"assistant"}')
            [{"role": "user"}, {"role": "assistant"}]

            >>> _parse_jsonl_messages('"{\\"role\\":\\"user\\"}\\n{\\"role\\":\\"assistant\\"}"')
            [{"role": "user"}, {"role": "assistant"}]
        """
        if not text_corpus or not text_corpus.strip():
            return []

        corpus = text_corpus.strip()

        # Handle JSON-string-wrapped JSONL: if starts with quote, try unwrapping
        if corpus.startswith('"'):
            try:
                corpus = json.loads(corpus)
                if not isinstance(corpus, str):
                    logger.debug("Unwrapped JSON was not a string, using original corpus")
                    corpus = text_corpus.strip()
            except json.JSONDecodeError:
                logger.debug("Failed to unwrap JSON-string format, treating as regular JSONL")

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
        """Extract content blocks from JSONL message structures.

        Filters messages by type, skips metadata/tool results, and extracts
        text content blocks with provenance metadata.

        Args:
            messages: List of message dictionaries from run log JSONL

        Returns:
            List of (content_text, provenance_metadata) tuples for non-empty
            content >= 20 characters
        """
        # Message types to skip (noise)
        skip_types = {"progress", "file-history-snapshot", "system", "result"}

        results: List[tuple[str, Dict]] = []

        for message in messages:
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
            is_user = msg_type == "human" or msg_role == "user"
            is_assistant = msg_type == "assistant" or msg_role == "assistant"

            if not (is_user or is_assistant):
                logger.debug(f"Skipping message with type={msg_type}, role={msg_role}")
                continue

            # Extract content (handle both string and list formats)
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
            provenance = {
                "message_uuid": message.get("uuid", ""),
                "message_role": msg_type or msg_role or "unknown",
                "timestamp": message.get("timestamp", ""),
                "session_id": message.get("sessionId", ""),
                "git_branch": message.get("gitBranch", ""),
            }

            results.append((content_text, provenance))

        logger.debug(f"Extracted {len(results)} content blocks from {len(messages)} messages")
        return results

    @staticmethod
    def _classify_type(line: str) -> str:
        for mem_type, pattern in _TYPE_RULES:
            if pattern.search(line):
                return mem_type
        return "learning"

    @staticmethod
    def _score(line: str, mem_type: str, profile: str) -> float:
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
            "learned that", "discovered that", "realized that",
            "found that", "noticed that", "understood that"
        }
        if any(pattern in line_lower for pattern in learning_patterns):
            base += 0.05

        # 2. Specificity indicators (+0.03)
        has_path = "/" in line or any(ext in line_lower for ext in {".py", ".ts", ".tsx", ".js", ".md"})
        has_function = "()" in line
        has_numbers = any(char.isdigit() for char in line)
        if has_path or has_function or has_numbers:
            base += 0.03

        # 3. Question penalty (-0.03)
        question_starters = {
            "why", "how", "what", "should", "could",
            "would", "can", "is", "are", "does", "do"
        }
        is_question = line.rstrip().endswith("?") or any(
            line_lower.startswith(word + " ") for word in question_starters
        )
        if is_question:
            base -= 0.03

        # 4. Vague language penalty (-0.04)
        vague_words = {
            "maybe", "probably", "might", "perhaps",
            "possibly", "somehow", "something", "somewhere"
        }
        if any(word in line_lower for word in vague_words):
            base -= 0.04

        return max(0.0, min(base, 0.98))

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
