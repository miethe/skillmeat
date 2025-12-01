"""Artifact discovery service for SkillMeat.

This module provides functionality to scan .claude/ directories and discover
existing artifacts that can be imported into the collection.
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from skillmeat.core.artifact import ArtifactType
from skillmeat.core.discovery_metrics import (
    discovery_artifacts_found,
    discovery_errors_total,
    discovery_metrics,
    discovery_scan_duration,
    discovery_scans_total,
    log_performance,
)
from skillmeat.utils.metadata import extract_yaml_frontmatter

logger = logging.getLogger(__name__)


class DiscoveryRequest(BaseModel):
    """Request model for artifact discovery.

    Attributes:
        scan_path: Optional path to scan. Defaults to collection artifacts directory.
    """

    scan_path: Optional[str] = None


class DiscoveredArtifact(BaseModel):
    """Metadata about a discovered artifact.

    Attributes:
        type: Artifact type (skill, command, agent, hook, mcp)
        name: Artifact name
        source: Optional source URL (GitHub, local, etc.)
        version: Optional version string
        scope: Optional scope (user or local)
        tags: Optional list of tags
        description: Optional description
        path: Full path to artifact directory
        discovered_at: Timestamp when artifact was discovered
    """

    type: str
    name: str
    source: Optional[str] = None
    version: Optional[str] = None
    scope: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)
    description: Optional[str] = None
    path: str
    discovered_at: datetime


class DiscoveryResult(BaseModel):
    """Result of artifact discovery scan.

    Attributes:
        discovered_count: Number of artifacts discovered
        artifacts: List of discovered artifacts
        errors: List of error messages for artifacts that failed discovery
        scan_duration_ms: Time taken to complete scan in milliseconds
    """

    discovered_count: int
    artifacts: List[DiscoveredArtifact]
    errors: List[str] = Field(default_factory=list)
    scan_duration_ms: float


class ArtifactDiscoveryService:
    """Service for discovering artifacts in .claude/ directories or collection artifacts.

    This service supports two scan modes:
    - project mode: Scans .claude/ subdirectories (skills/, commands/, agents/, hooks/, mcp/)
    - collection mode: Scans collection/artifacts/ subdirectories (legacy)
    - auto mode: Detects mode based on directory structure

    Supported artifact types:
    - Skills: Identified by SKILL.md
    - Commands: Identified by COMMAND.md or command.md
    - Agents: Identified by AGENT.md or agent.md
    - Hooks: Identified by HOOK.md
    - MCPs: Identified by MCP.md or mcp.json

    Performance target: <2 seconds for 50+ artifacts
    """

    supported_types: List[str] = ["skill", "command", "agent", "hook", "mcp"]

    def __init__(self, base_path: Path, scan_mode: str = "auto"):
        """Initialize the discovery service.

        Args:
            base_path: Base path to scan (project root or collection root)
            scan_mode: Scan mode - "project" (.claude/), "collection" (artifacts/), or "auto" (detect)
        """
        self.base_path = base_path
        self.scan_mode = scan_mode

        # Auto-detect mode based on directory structure
        if scan_mode == "auto":
            if (base_path / ".claude").exists():
                self.scan_mode = "project"
                self.artifacts_base = base_path / ".claude"
            elif (base_path / "artifacts").exists():
                self.scan_mode = "collection"
                self.artifacts_base = base_path / "artifacts"
            else:
                # Default to project mode
                self.scan_mode = "project"
                self.artifacts_base = base_path / ".claude"
        elif scan_mode == "project":
            self.artifacts_base = base_path / ".claude"
        else:  # collection
            self.artifacts_base = base_path / "artifacts"

        # Maintain backward compatibility with collection_path attribute
        self.collection_path = base_path
        self.artifacts_path = self.artifacts_base

    @log_performance("discovery_scan")
    def discover_artifacts(self) -> DiscoveryResult:
        """Scan artifacts directory and discover all artifacts.

        This method recursively scans the artifacts directory, detects
        artifact types, extracts metadata, and validates structure.

        Errors during individual artifact processing are collected but
        do not fail the entire scan.

        Returns:
            DiscoveryResult with discovered artifacts, error list, and metrics
        """
        start_time = time.time()
        discovered_artifacts: List[DiscoveredArtifact] = []
        errors: List[str] = []

        logger.info(
            "Starting artifact discovery",
            extra={
                "path": str(self.base_path),
                "scan_mode": self.scan_mode,
                "artifacts_base": str(self.artifacts_base)
            }
        )

        # Validate artifacts directory exists
        if not self.artifacts_base.exists():
            error_msg = (
                f"Artifacts directory not found: {self.artifacts_base} "
                f"(scan_mode={self.scan_mode})"
            )
            logger.warning(error_msg)
            errors.append(error_msg)
            discovery_scans_total.labels(status="no_artifacts_dir").inc()

            return DiscoveryResult(
                discovered_count=0,
                artifacts=[],
                errors=errors,
                scan_duration_ms=(time.time() - start_time) * 1000,
            )

        # Scan each artifact type directory
        try:
            for type_dir in self.artifacts_base.iterdir():
                if not type_dir.is_dir():
                    continue

                # Determine artifact type from directory name
                artifact_type = self._normalize_type_from_dirname(type_dir.name)
                if artifact_type not in self.supported_types:
                    logger.debug(f"Skipping unsupported directory: {type_dir.name}")
                    continue

                # Scan artifacts in this type directory
                try:
                    type_artifacts = self._scan_type_directory(
                        type_dir, artifact_type, errors
                    )
                    discovered_artifacts.extend(type_artifacts)
                except PermissionError as e:
                    error_msg = f"Permission denied accessing {type_dir}: {e}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                except Exception as e:
                    error_msg = f"Error scanning {type_dir}: {e}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)

        except PermissionError as e:
            error_msg = f"Permission denied accessing artifacts directory: {e}"
            logger.warning(error_msg)
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Error during artifact discovery: {e}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)

        # Calculate scan duration
        scan_duration_ms = (time.time() - start_time) * 1000
        scan_duration_sec = scan_duration_ms / 1000

        # Record metrics
        discovery_scans_total.labels(
            status="success" if not errors else "partial_success"
        ).inc()
        discovery_artifacts_found.set(len(discovered_artifacts))
        discovery_scan_duration.observe(scan_duration_sec)
        discovery_metrics.record_scan(len(discovered_artifacts), scan_duration_ms)

        logger.info(
            f"Discovery scan completed: {len(discovered_artifacts)} artifacts "
            f"found in {scan_duration_ms:.2f}ms",
            extra={
                "artifact_count": len(discovered_artifacts),
                "error_count": len(errors),
                "duration_ms": round(scan_duration_ms, 2),
            }
        )

        return DiscoveryResult(
            discovered_count=len(discovered_artifacts),
            artifacts=discovered_artifacts,
            errors=errors,
            scan_duration_ms=scan_duration_ms,
        )

    def _scan_type_directory(
        self, type_dir: Path, artifact_type: str, errors: List[str]
    ) -> List[DiscoveredArtifact]:
        """Scan a single artifact type directory.

        Args:
            type_dir: Path to artifact type directory (e.g., skills/)
            artifact_type: Type of artifacts in this directory
            errors: List to append errors to

        Returns:
            List of discovered artifacts in this directory
        """
        discovered = []

        # Use scandir for efficient directory traversal
        import os

        try:
            with os.scandir(type_dir) as entries:
                for entry in entries:
                    # Skip hidden files/directories
                    if entry.name.startswith("."):
                        continue

                    artifact_path = Path(entry.path)

                    # Try to detect and process artifact
                    try:
                        detected_type = self._detect_artifact_type(artifact_path)

                        # If detection failed or type mismatch, skip
                        if detected_type is None:
                            logger.debug(
                                f"Could not detect artifact type: {artifact_path}"
                            )
                            continue

                        # Validate artifact structure
                        if not self._validate_artifact(artifact_path, detected_type):
                            error_msg = f"Invalid artifact structure: {artifact_path}"
                            logger.warning(error_msg)
                            errors.append(error_msg)
                            continue

                        # Extract metadata
                        metadata = self._extract_artifact_metadata(
                            artifact_path, detected_type
                        )

                        # Create DiscoveredArtifact
                        artifact = DiscoveredArtifact(
                            type=detected_type,
                            name=metadata.get("name", artifact_path.stem),
                            source=metadata.get("source"),
                            version=metadata.get("version"),
                            scope=metadata.get("scope"),
                            tags=metadata.get("tags", []),
                            description=metadata.get("description"),
                            path=str(artifact_path),
                            discovered_at=datetime.utcnow(),
                        )

                        discovered.append(artifact)
                        logger.debug(f"Discovered {detected_type}: {artifact.name}")

                    except Exception as e:
                        error_msg = f"Error processing {artifact_path}: {e}"
                        logger.warning(error_msg)
                        errors.append(error_msg)

        except PermissionError as e:
            error_msg = f"Permission denied scanning {type_dir}: {e}"
            logger.warning(error_msg)
            errors.append(error_msg)

        return discovered

    def _detect_artifact_type(self, artifact_path: Path) -> Optional[str]:
        """Detect artifact type from directory structure.

        Detection logic:
        - Skills: Check for SKILL.md
        - Commands: Check for COMMAND.md or command.md
        - Agents: Check for AGENT.md or agent.md
        - Hooks: Check for HOOK.md or hook.md
        - MCPs: Check for MCP.md or mcp.json

        Args:
            artifact_path: Path to potential artifact

        Returns:
            Artifact type string, or None if not detected
        """
        # Check if path is a directory
        if artifact_path.is_dir():
            # Check for skill
            if (artifact_path / "SKILL.md").exists():
                return "skill"

            # Check for command
            if (artifact_path / "COMMAND.md").exists():
                return "command"
            if (artifact_path / "command.md").exists():
                return "command"

            # Check for agent
            if (artifact_path / "AGENT.md").exists():
                return "agent"
            if (artifact_path / "agent.md").exists():
                return "agent"

            # Check for hook
            if (artifact_path / "HOOK.md").exists():
                return "hook"
            if (artifact_path / "hook.md").exists():
                return "hook"

            # Check for MCP
            if (artifact_path / "MCP.md").exists():
                return "mcp"
            if (artifact_path / "mcp.json").exists():
                return "mcp"

        # Check if path is a file (for commands/agents that might be single files)
        elif artifact_path.is_file() and artifact_path.suffix == ".md":
            # Try to infer from filename
            name_lower = artifact_path.stem.lower()
            if "command" in name_lower:
                return "command"
            if "agent" in name_lower:
                return "agent"

        return None

    def _extract_artifact_metadata(
        self, artifact_path: Path, artifact_type: str
    ) -> Dict[str, Any]:
        """Extract metadata from artifact frontmatter.

        Reads the appropriate metadata file (SKILL.md, COMMAND.md, etc.)
        and extracts YAML frontmatter.

        Args:
            artifact_path: Path to artifact directory or file
            artifact_type: Type of artifact

        Returns:
            Dictionary of extracted metadata (normalized)
        """
        metadata: Dict[str, Any] = {}

        # Determine metadata file path
        metadata_file = self._find_metadata_file(artifact_path, artifact_type)

        if metadata_file is None or not metadata_file.exists():
            logger.debug(f"No metadata file found for {artifact_path}")
            return metadata

        # Extract YAML frontmatter
        try:
            yaml_data = extract_yaml_frontmatter(metadata_file)
            if yaml_data:
                # Normalize metadata fields
                metadata = {
                    "name": yaml_data.get("name", yaml_data.get("title")),
                    "description": yaml_data.get("description"),
                    "source": yaml_data.get("source", yaml_data.get("upstream")),
                    "version": yaml_data.get("version"),
                    "scope": yaml_data.get("scope"),
                    "tags": yaml_data.get("tags", []),
                    "author": yaml_data.get("author"),
                    "license": yaml_data.get("license"),
                }

                # Remove None values
                metadata = {k: v for k, v in metadata.items() if v is not None}

        except Exception as e:
            error_msg = f"Failed to extract frontmatter from {metadata_file}: {e}"
            logger.warning(error_msg)
            # Don't fail - just log warning and return empty metadata

        return metadata

    def _find_metadata_file(
        self, artifact_path: Path, artifact_type: str
    ) -> Optional[Path]:
        """Find the metadata file for an artifact.

        Args:
            artifact_path: Path to artifact
            artifact_type: Type of artifact

        Returns:
            Path to metadata file, or None if not found
        """
        if artifact_type == "skill":
            if artifact_path.is_dir():
                return artifact_path / "SKILL.md"

        elif artifact_type == "command":
            if artifact_path.is_file() and artifact_path.suffix == ".md":
                return artifact_path
            elif artifact_path.is_dir():
                # Check for COMMAND.md first, then command.md
                if (artifact_path / "COMMAND.md").exists():
                    return artifact_path / "COMMAND.md"
                if (artifact_path / "command.md").exists():
                    return artifact_path / "command.md"

        elif artifact_type == "agent":
            if artifact_path.is_file() and artifact_path.suffix == ".md":
                return artifact_path
            elif artifact_path.is_dir():
                # Check for AGENT.md first, then agent.md
                if (artifact_path / "AGENT.md").exists():
                    return artifact_path / "AGENT.md"
                if (artifact_path / "agent.md").exists():
                    return artifact_path / "agent.md"

        elif artifact_type == "hook":
            if artifact_path.is_dir():
                if (artifact_path / "HOOK.md").exists():
                    return artifact_path / "HOOK.md"
                if (artifact_path / "hook.md").exists():
                    return artifact_path / "hook.md"

        elif artifact_type == "mcp":
            if artifact_path.is_dir():
                # Prefer MCP.md over mcp.json for metadata
                if (artifact_path / "MCP.md").exists():
                    return artifact_path / "MCP.md"
                # Note: mcp.json is not markdown, so we don't extract from it
                # That would require different parsing logic

        return None

    def _validate_artifact(self, artifact_path: Path, artifact_type: str) -> bool:
        """Validate artifact structure.

        Checks that required files exist and frontmatter is valid.

        Args:
            artifact_path: Path to artifact
            artifact_type: Type of artifact

        Returns:
            True if valid, False otherwise
        """
        # Check that metadata file exists
        metadata_file = self._find_metadata_file(artifact_path, artifact_type)
        if metadata_file is None or not metadata_file.exists():
            return False

        # Try to parse frontmatter (validation)
        try:
            yaml_data = extract_yaml_frontmatter(metadata_file)
            # Valid if we can parse it (even if empty)
            return True
        except Exception as e:
            logger.debug(f"Frontmatter validation failed for {metadata_file}: {e}")
            return False

    def _normalize_type_from_dirname(self, dirname: str) -> str:
        """Normalize directory name to artifact type.

        Args:
            dirname: Directory name (e.g., "skills", "commands")

        Returns:
            Normalized artifact type (e.g., "skill", "command")
        """
        # Remove trailing 's' for plural directory names
        dirname_lower = dirname.lower()
        if dirname_lower.endswith("s") and len(dirname_lower) > 1:
            return dirname_lower[:-1]
        return dirname_lower
