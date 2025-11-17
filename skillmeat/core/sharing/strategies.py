"""Import conflict resolution strategies for bundle import.

Defines various strategies for resolving conflicts when importing artifacts
that already exist in the target collection.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.prompt import Confirm, Prompt

from skillmeat.core.artifact import Artifact, ArtifactType

logger = logging.getLogger(__name__)


class ConflictResolution(str, Enum):
    """Conflict resolution decision."""

    MERGE = "merge"  # Overwrite existing with imported
    FORK = "fork"  # Create new version with suffix
    SKIP = "skip"  # Keep existing, don't import


@dataclass
class ConflictDecision:
    """Decision for resolving a single artifact conflict."""

    artifact_name: str
    artifact_type: ArtifactType
    resolution: ConflictResolution
    new_name: Optional[str] = None  # For fork strategy
    reason: Optional[str] = None


class ImportStrategy(ABC):
    """Base class for import conflict resolution strategies."""

    @abstractmethod
    def resolve_conflict(
        self,
        existing: Artifact,
        imported: dict,
        console: Optional[Console] = None,
    ) -> ConflictDecision:
        """Resolve conflict between existing and imported artifact.

        Args:
            existing: Existing artifact in collection
            imported: Imported artifact data (dict from manifest)
            console: Optional Rich console for output

        Returns:
            ConflictDecision indicating how to resolve
        """
        pass

    @abstractmethod
    def name(self) -> str:
        """Return strategy name for display."""
        pass


class MergeStrategy(ImportStrategy):
    """Always overwrite existing artifacts with imported ones."""

    def resolve_conflict(
        self,
        existing: Artifact,
        imported: dict,
        console: Optional[Console] = None,
    ) -> ConflictDecision:
        """Resolve by merging (overwriting existing).

        Args:
            existing: Existing artifact in collection
            imported: Imported artifact data
            console: Optional console (unused)

        Returns:
            ConflictDecision with MERGE resolution
        """
        logger.info(
            f"Merge strategy: overwriting {existing.type.value}/{existing.name}"
        )

        return ConflictDecision(
            artifact_name=existing.name,
            artifact_type=existing.type,
            resolution=ConflictResolution.MERGE,
            reason="merge strategy: always overwrite",
        )

    def name(self) -> str:
        """Return strategy name."""
        return "merge"


class ForkStrategy(ImportStrategy):
    """Create new version with suffix when conflicts occur."""

    def __init__(self, suffix_template: str = "-imported"):
        """Initialize fork strategy.

        Args:
            suffix_template: Suffix to append to forked artifacts (default: "-imported")
        """
        self.suffix_template = suffix_template

    def resolve_conflict(
        self,
        existing: Artifact,
        imported: dict,
        console: Optional[Console] = None,
    ) -> ConflictDecision:
        """Resolve by forking (creating new version with suffix).

        Args:
            existing: Existing artifact in collection
            imported: Imported artifact data
            console: Optional console (unused)

        Returns:
            ConflictDecision with FORK resolution
        """
        # Generate new name with suffix
        base_name = existing.name
        new_name = f"{base_name}{self.suffix_template}"

        # Handle collision with existing fork
        counter = 1
        while self._name_exists(new_name, existing.type):
            new_name = f"{base_name}{self.suffix_template}-{counter}"
            counter += 1

        logger.info(
            f"Fork strategy: creating {existing.type.value}/{new_name} "
            f"from {existing.name}"
        )

        return ConflictDecision(
            artifact_name=existing.name,
            artifact_type=existing.type,
            resolution=ConflictResolution.FORK,
            new_name=new_name,
            reason=f"fork strategy: created as '{new_name}'",
        )

    def _name_exists(self, name: str, artifact_type: ArtifactType) -> bool:
        """Check if artifact name already exists.

        This is a placeholder - actual implementation should check collection.

        Args:
            name: Artifact name to check
            artifact_type: Artifact type

        Returns:
            True if name exists (placeholder always returns False)
        """
        # TODO: Implement actual collision check with collection
        # For now, assume no collision
        return False

    def name(self) -> str:
        """Return strategy name."""
        return "fork"


class SkipStrategy(ImportStrategy):
    """Keep existing artifacts, skip importing conflicting ones."""

    def resolve_conflict(
        self,
        existing: Artifact,
        imported: dict,
        console: Optional[Console] = None,
    ) -> ConflictDecision:
        """Resolve by skipping (keeping existing).

        Args:
            existing: Existing artifact in collection
            imported: Imported artifact data
            console: Optional console (unused)

        Returns:
            ConflictDecision with SKIP resolution
        """
        logger.info(
            f"Skip strategy: keeping existing {existing.type.value}/{existing.name}"
        )

        return ConflictDecision(
            artifact_name=existing.name,
            artifact_type=existing.type,
            resolution=ConflictResolution.SKIP,
            reason="skip strategy: kept existing",
        )

    def name(self) -> str:
        """Return strategy name."""
        return "skip"


class InteractiveStrategy(ImportStrategy):
    """Prompt user for each conflict."""

    def __init__(
        self,
        default_choice: Optional[ConflictResolution] = None,
        apply_to_all: bool = False,
    ):
        """Initialize interactive strategy.

        Args:
            default_choice: Optional default resolution
            apply_to_all: If True, use first choice for all conflicts
        """
        self.default_choice = default_choice
        self.apply_to_all = apply_to_all
        self._cached_choice: Optional[ConflictResolution] = None

    def resolve_conflict(
        self,
        existing: Artifact,
        imported: dict,
        console: Optional[Console] = None,
    ) -> ConflictDecision:
        """Resolve by prompting user.

        Args:
            existing: Existing artifact in collection
            imported: Imported artifact data
            console: Optional Rich console for display

        Returns:
            ConflictDecision based on user choice
        """
        if console is None:
            console = Console()

        # Use cached choice if apply_to_all is enabled
        if self.apply_to_all and self._cached_choice is not None:
            resolution = self._cached_choice
        else:
            # Show conflict info
            console.print(
                f"\n[yellow]Conflict detected:[/yellow] "
                f"{existing.type.value}/{existing.name}"
            )
            console.print(f"  Existing: {existing.metadata.title or 'No title'}")
            console.print(
                f"  Existing version: {existing.metadata.version or 'unknown'}"
            )
            console.print(
                f"  Imported version: {imported.get('metadata', {}).get('version', 'unknown')}"
            )

            # Prompt for resolution
            choices = ["merge", "fork", "skip"]
            default_idx = 2  # skip by default

            if self.default_choice:
                if self.default_choice == ConflictResolution.MERGE:
                    default_idx = 0
                elif self.default_choice == ConflictResolution.FORK:
                    default_idx = 1

            console.print("\nResolution options:")
            console.print("  [cyan]merge[/cyan]: Overwrite existing with imported")
            console.print("  [cyan]fork[/cyan]: Import as new artifact with suffix")
            console.print("  [cyan]skip[/cyan]: Keep existing, don't import")

            choice = Prompt.ask(
                "\nHow to resolve?",
                choices=choices,
                default=choices[default_idx],
            )

            resolution = ConflictResolution(choice)

            # Ask if should apply to all
            if self.apply_to_all is False:
                apply_all = Confirm.ask(
                    "Apply this choice to all remaining conflicts?",
                    default=False,
                )
                if apply_all:
                    self.apply_to_all = True
                    self._cached_choice = resolution

        # Execute resolution
        if resolution == ConflictResolution.MERGE:
            return ConflictDecision(
                artifact_name=existing.name,
                artifact_type=existing.type,
                resolution=ConflictResolution.MERGE,
                reason="user chose: merge",
            )
        elif resolution == ConflictResolution.FORK:
            # Generate fork name
            fork_strategy = ForkStrategy()
            fork_decision = fork_strategy.resolve_conflict(existing, imported, console)
            fork_decision.reason = "user chose: fork"
            return fork_decision
        else:  # SKIP
            return ConflictDecision(
                artifact_name=existing.name,
                artifact_type=existing.type,
                resolution=ConflictResolution.SKIP,
                reason="user chose: skip",
            )

    def name(self) -> str:
        """Return strategy name."""
        return "interactive"


def get_strategy(
    strategy_name: str,
    interactive: bool = True,
    default_choice: Optional[str] = None,
) -> ImportStrategy:
    """Factory function to get import strategy by name.

    Args:
        strategy_name: Name of strategy ("merge", "fork", "skip", "interactive")
        interactive: Whether to allow interactive prompts
        default_choice: Default choice for interactive mode

    Returns:
        ImportStrategy instance

    Raises:
        ValueError: If strategy_name is invalid
    """
    if strategy_name == "merge":
        return MergeStrategy()
    elif strategy_name == "fork":
        return ForkStrategy()
    elif strategy_name == "skip":
        return SkipStrategy()
    elif strategy_name == "interactive":
        default_resolution = None
        if default_choice:
            try:
                default_resolution = ConflictResolution(default_choice)
            except ValueError:
                logger.warning(f"Invalid default choice: {default_choice}")

        return InteractiveStrategy(
            default_choice=default_resolution,
            apply_to_all=False,
        )
    else:
        raise ValueError(
            f"Invalid strategy: {strategy_name}. "
            "Must be one of: merge, fork, skip, interactive"
        )
