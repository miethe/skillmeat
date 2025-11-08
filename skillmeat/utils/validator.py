"""Artifact validation utilities."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from skillmeat.core.artifact import ArtifactType


@dataclass
class ValidationResult:
    """Result of artifact validation."""

    is_valid: bool
    error_message: Optional[str] = None
    artifact_type: Optional[ArtifactType] = None


class ArtifactValidator:
    """Validates artifact structure based on type."""

    @staticmethod
    def validate_skill(path: Path) -> ValidationResult:
        """Validate skill artifact structure.

        Requirements:
            - Must be a directory
            - Must contain SKILL.md in root
            - SKILL.md must have non-empty content

        Args:
            path: Path to skill directory

        Returns:
            ValidationResult with validation status
        """
        if not path.exists():
            return ValidationResult(
                is_valid=False,
                error_message=f"Path does not exist: {path}",
            )

        if not path.is_dir():
            return ValidationResult(
                is_valid=False,
                error_message=f"Skill path is not a directory: {path}",
            )

        # Check for SKILL.md
        skill_md = path / "SKILL.md"
        if not skill_md.exists():
            return ValidationResult(
                is_valid=False,
                error_message="Skill must contain SKILL.md in root",
            )

        # Check for readable content
        try:
            content = skill_md.read_text(encoding="utf-8")
            if not content.strip():
                return ValidationResult(
                    is_valid=False,
                    error_message="SKILL.md is empty",
                )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Failed to read SKILL.md: {e}",
            )

        return ValidationResult(
            is_valid=True,
            artifact_type=ArtifactType.SKILL,
        )

    @staticmethod
    def validate_command(path: Path) -> ValidationResult:
        """Validate command artifact structure.

        Requirements:
            - Must be a .md file OR a directory containing a .md file
            - File must exist and have content

        Args:
            path: Path to command file or directory

        Returns:
            ValidationResult with validation status
        """
        if not path.exists():
            return ValidationResult(
                is_valid=False,
                error_message=f"Path does not exist: {path}",
            )

        # Commands can be either a .md file or a directory with a .md file
        if path.is_file():
            if not path.suffix == ".md":
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Command file must be a .md file: {path}",
                )
            command_file = path
        elif path.is_dir():
            # Look for any .md file in directory (prefer command.md)
            command_md = path / "command.md"
            if command_md.exists():
                command_file = command_md
            else:
                # Try to find any .md file
                md_files = list(path.glob("*.md"))
                if not md_files:
                    return ValidationResult(
                        is_valid=False,
                        error_message="Command directory must contain a .md file",
                    )
                command_file = md_files[0]
        else:
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid path type: {path}",
            )

        # Check for readable content
        try:
            content = command_file.read_text(encoding="utf-8")
            if not content.strip():
                return ValidationResult(
                    is_valid=False,
                    error_message="Command file is empty",
                )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Failed to read command file: {e}",
            )

        return ValidationResult(
            is_valid=True,
            artifact_type=ArtifactType.COMMAND,
        )

    @staticmethod
    def validate_agent(path: Path) -> ValidationResult:
        """Validate agent artifact structure.

        Requirements:
            - Must be a .md file OR a directory containing an agent.md or AGENT.md
            - File must exist and have content

        Args:
            path: Path to agent file or directory

        Returns:
            ValidationResult with validation status
        """
        if not path.exists():
            return ValidationResult(
                is_valid=False,
                error_message=f"Path does not exist: {path}",
            )

        # Agents can be either a .md file or a directory with agent.md/AGENT.md
        if path.is_file():
            if not path.suffix == ".md":
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Agent file must be a .md file: {path}",
                )
            agent_file = path
        elif path.is_dir():
            # Look for AGENT.md or agent.md
            agent_md_upper = path / "AGENT.md"
            agent_md_lower = path / "agent.md"

            if agent_md_upper.exists():
                agent_file = agent_md_upper
            elif agent_md_lower.exists():
                agent_file = agent_md_lower
            else:
                # Try to find any .md file
                md_files = list(path.glob("*.md"))
                if not md_files:
                    return ValidationResult(
                        is_valid=False,
                        error_message="Agent directory must contain a .md file",
                    )
                agent_file = md_files[0]
        else:
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid path type: {path}",
            )

        # Check for readable content
        try:
            content = agent_file.read_text(encoding="utf-8")
            if not content.strip():
                return ValidationResult(
                    is_valid=False,
                    error_message="Agent file is empty",
                )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Failed to read agent file: {e}",
            )

        return ValidationResult(
            is_valid=True,
            artifact_type=ArtifactType.AGENT,
        )

    @staticmethod
    def validate(path: Path, artifact_type: ArtifactType) -> ValidationResult:
        """Route to appropriate validator based on type.

        Args:
            path: Path to artifact
            artifact_type: Type of artifact

        Returns:
            ValidationResult with validation status
        """
        validators = {
            ArtifactType.SKILL: ArtifactValidator.validate_skill,
            ArtifactType.COMMAND: ArtifactValidator.validate_command,
            ArtifactType.AGENT: ArtifactValidator.validate_agent,
        }

        validator = validators.get(artifact_type)
        if validator is None:
            return ValidationResult(
                is_valid=False,
                error_message=f"Unknown artifact type: {artifact_type}",
            )

        return validator(path)

    @staticmethod
    def detect_artifact_type(path: Path) -> Optional[ArtifactType]:
        """Auto-detect artifact type from filesystem structure.

        Detection rules:
            - Contains SKILL.md -> SKILL
            - Contains AGENT.md or agent.md -> AGENT
            - Is .md file or contains .md files -> COMMAND (fallback)

        Args:
            path: Path to artifact

        Returns:
            Detected ArtifactType or None if cannot determine
        """
        if not path.exists():
            return None

        # Check for SKILL.md
        if path.is_dir() and (path / "SKILL.md").exists():
            return ArtifactType.SKILL

        # Check for AGENT.md
        if path.is_dir() and (
            (path / "AGENT.md").exists() or (path / "agent.md").exists()
        ):
            return ArtifactType.AGENT

        # Check if it's a .md file or directory with .md files
        if path.is_file() and path.suffix == ".md":
            # Default to COMMAND for standalone .md files
            return ArtifactType.COMMAND

        if path.is_dir():
            md_files = list(path.glob("*.md"))
            if md_files:
                # Default to COMMAND if we have .md files but no SKILL.md or AGENT.md
                return ArtifactType.COMMAND

        return None
