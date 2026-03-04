"""
Interfaces layer for SkillMeat's hexagonal architecture.

This module defines the contracts between the application core and its
infrastructure adapters. It contains:

- Abstract repository interfaces (ABCs): define data access contracts that
  infrastructure implementations must satisfy, keeping the core independent
  of any specific storage technology.

- Domain DTOs (dataclasses): lightweight, immutable data transfer objects
  used to pass data across layer boundaries without leaking ORM models or
  external schemas into the core.

- RequestContext: carries per-request metadata (auth, tracing, etc.) through
  the call stack without threading globals.

Design principles:
- Nothing in this module may import from other skillmeat modules except
  `skillmeat.core.enums` and `skillmeat.core.exceptions`.
- All interfaces use Python's `abc.ABC` / `abc.abstractmethod`.
- DTOs are frozen dataclasses to enforce immutability at the boundary.
"""

from skillmeat.core.interfaces.context import RequestContext
from skillmeat.core.interfaces.dtos import (
    ArtifactDTO,
    CollectionDTO,
    DeploymentDTO,
    ProjectDTO,
    SettingsDTO,
    TagDTO,
)

__all__: list[str] = [
    "RequestContext",
    "ArtifactDTO",
    "CollectionDTO",
    "DeploymentDTO",
    "ProjectDTO",
    "SettingsDTO",
    "TagDTO",
]
