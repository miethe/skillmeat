"""Domain exceptions for SkillMeat core services.

This module centralises domain-specific exception types that cut across
multiple core services.  Module-local exceptions (e.g. scoring, signing)
remain co-located with their module.
"""

from typing import List


class DeploymentSetError(Exception):
    """Base class for DeploymentSet domain errors."""


class DeploymentSetResolutionError(DeploymentSetError):
    """Raised when resolution of a DeploymentSet exceeds the depth limit.

    Attributes:
        set_id: The set ID that was being resolved when the limit fired.
        path: Ordered list of set IDs representing the traversal path from
              the root set down to the offending nested set.
        depth_limit: The configured maximum depth that was breached.
    """

    def __init__(
        self,
        set_id: str,
        path: List[str],
        depth_limit: int = 20,
    ) -> None:
        self.set_id = set_id
        self.path = list(path)
        self.depth_limit = depth_limit
        path_str = " -> ".join(path)
        super().__init__(
            f"DeploymentSet resolution depth limit ({depth_limit}) exceeded "
            f"at set '{set_id}'. Traversal path: {path_str}"
        )


class DeploymentSetCycleError(DeploymentSetError):
    """Raised when a circular reference is detected during set resolution.

    Attributes:
        set_id: The set ID that forms the cycle.
        path: Ordered list of set IDs showing the cycle path.
    """

    def __init__(self, set_id: str, path: List[str]) -> None:
        self.set_id = set_id
        self.path = list(path)
        path_str = " -> ".join(path)
        super().__init__(
            f"Circular reference detected in DeploymentSet '{set_id}'. "
            f"Traversal path: {path_str}"
        )
