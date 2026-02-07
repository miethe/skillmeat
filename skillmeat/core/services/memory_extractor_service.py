"""Heuristic memory extraction service.

Provides deterministic extraction of candidate memory items from run logs
or arbitrary text corpora. Extraction is review-first and only creates
`candidate` memories on apply.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List, Optional

from skillmeat.cache.memory_repositories import _compute_content_hash
from skillmeat.core.services.memory_service import MemoryService

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
