"""BOM (Bill of Materials) generation package for SkillMeat.

Provides the BomGenerator service and adapter infrastructure for producing
deterministic Software Bills of Materials from deployed artifact sets.

Exports:
    BomGenerator: Core service that queries artifacts and assembles the BOM dict.
    BaseArtifactAdapter: Abstract base class for per-type artifact adapters.
    SkillAdapter: Reference adapter implementation for skill-type artifacts.
"""

from __future__ import annotations

from skillmeat.core.bom.generator import BaseArtifactAdapter, BomGenerator, SkillAdapter

__all__ = [
    "BomGenerator",
    "BaseArtifactAdapter",
    "SkillAdapter",
]
