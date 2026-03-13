"""BOM (Bill of Materials) generation package for SkillMeat.

Provides the BomGenerator service and adapter infrastructure for producing
deterministic Software Bills of Materials from deployed artifact sets.
Also provides ownership resolution and attestation scope filtering for
owner-scoped BOM attestation records.

Exports:
    BomGenerator: Core service that queries artifacts and assembles the BOM dict.
    BaseArtifactAdapter: Abstract base class for per-type artifact adapters.
    SkillAdapter: Reference adapter implementation for skill-type artifacts.
    OwnershipResolver: Resolves effective owner_type/owner_id from auth context.
    AttestationScopeResolver: Enforces owner-scoped visibility for attestation records.
"""

from __future__ import annotations

from skillmeat.core.bom.generator import BaseArtifactAdapter, BomGenerator, SkillAdapter
from skillmeat.core.bom.scope import AttestationScopeResolver, OwnershipResolver

__all__ = [
    "BomGenerator",
    "BaseArtifactAdapter",
    "SkillAdapter",
    "OwnershipResolver",
    "AttestationScopeResolver",
]
