"""Migration utility for skillman to skillmeat."""

import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Handle tomli/tomllib import for different Python versions
if sys.version_info >= (3, 11):
    import tomllib

    TOML_LOADS = tomllib.loads
else:
    import tomli as tomllib

    TOML_LOADS = tomllib.loads

import tomli_w

from skillmeat.core.artifact import Artifact, ArtifactMetadata, ArtifactType
from skillmeat.core.collection import CollectionManager
from skillmeat.core.version import VersionManager
from skillmeat.storage.manifest import ManifestManager


@dataclass
class SkillmanSkill:
    """Represents a skill from skillman's skills.toml."""

    name: str
    source: str
    version: str = "latest"
    scope: str = "local"
    aliases: List[str] = field(default_factory=list)


@dataclass
class SkillmanLockEntry:
    """Represents a lock entry from skillman's skills.lock."""

    name: str
    source: str
    version_spec: str
    resolved_sha: Optional[str] = None
    resolved_version: Optional[str] = None


@dataclass
class MigrationResult:
    """Result of a migration operation."""

    success: bool
    artifacts_imported: int = 0
    artifacts_skipped: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    skipped_items: List[Tuple[str, str]] = field(default_factory=list)  # (name, reason)


class SkillmanMigrator:
    """Handles migration from skillman to skillmeat."""

    def __init__(
        self,
        collection_mgr: CollectionManager,
        version_mgr: Optional[VersionManager] = None,
    ):
        """Initialize migrator.

        Args:
            collection_mgr: Collection manager for target collection
            version_mgr: Version manager for snapshots (optional)
        """
        self.collection_mgr = collection_mgr
        self.version_mgr = version_mgr
        self.skillman_config_dir = Path.home() / ".skillman"
        self.skillman_config_file = self.skillman_config_dir / "config.toml"

    def find_skillman_installation(self, path: Optional[Path] = None) -> Dict[str, Any]:
        """Locate skillman installation and catalog what's available.

        Args:
            path: Optional path to skills.toml file

        Returns:
            Dictionary with installation info:
            {
                "found": bool,
                "config_path": Optional[Path],
                "manifest_path": Optional[Path],
                "user_skills_dir": Optional[Path],
                "local_skills_dir": Optional[Path],
                "skill_count": int,
                "user_skill_count": int,
                "local_skill_count": int,
            }
        """
        result = {
            "found": False,
            "config_path": None,
            "manifest_path": None,
            "user_skills_dir": None,
            "local_skills_dir": None,
            "skill_count": 0,
            "user_skill_count": 0,
            "local_skill_count": 0,
        }

        # Check for config
        if self.skillman_config_file.exists():
            result["config_path"] = self.skillman_config_file
            result["found"] = True

        # Check for manifest (project-level)
        if path:
            manifest_path = path
        else:
            # Look in current directory
            manifest_path = Path.cwd() / "skills.toml"

        if manifest_path.exists():
            result["manifest_path"] = manifest_path
            result["found"] = True
            # Count skills in manifest
            try:
                skills = self._parse_skillman_manifest(manifest_path)
                result["skill_count"] = len(skills)
            except Exception:
                pass

        # Check user skills directory
        user_skills_dir = Path.home() / ".claude" / "skills" / "user"
        if user_skills_dir.exists():
            result["user_skills_dir"] = user_skills_dir
            result["found"] = True
            # Count skill directories
            try:
                result["user_skill_count"] = len(
                    [d for d in user_skills_dir.iterdir() if d.is_dir()]
                )
            except Exception:
                pass

        # Check local skills directory
        local_skills_dir = Path.cwd() / ".claude" / "skills"
        if local_skills_dir.exists():
            result["local_skills_dir"] = local_skills_dir
            result["found"] = True
            # Count skill directories
            try:
                result["local_skill_count"] = len(
                    [d for d in local_skills_dir.iterdir() if d.is_dir()]
                )
            except Exception:
                pass

        return result

    def _parse_skillman_manifest(
        self, manifest_path: Path
    ) -> List[SkillmanSkill]:
        """Parse skillman's skills.toml file.

        Args:
            manifest_path: Path to skills.toml

        Returns:
            List of SkillmanSkill objects

        Raises:
            ValueError: If manifest is invalid
        """
        try:
            with open(manifest_path, "rb") as f:
                data = TOML_LOADS(f.read().decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Failed to parse skills.toml: {e}")

        tool_data = data.get("tool", {}).get("skillman", {})
        skills = []

        for skill_data in tool_data.get("skills", []):
            skill = SkillmanSkill(
                name=skill_data["name"],
                source=skill_data["source"],
                version=skill_data.get("version", "latest"),
                scope=skill_data.get("scope", "local"),
                aliases=skill_data.get("aliases", []),
            )
            skills.append(skill)

        return skills

    def _parse_skillman_lockfile(
        self, lockfile_path: Path
    ) -> Dict[str, SkillmanLockEntry]:
        """Parse skillman's skills.lock file.

        Args:
            lockfile_path: Path to skills.lock

        Returns:
            Dictionary mapping skill name to lock entry
        """
        if not lockfile_path.exists():
            return {}

        try:
            with open(lockfile_path, "rb") as f:
                data = TOML_LOADS(f.read().decode("utf-8"))
        except Exception:
            return {}

        lock_data = data.get("lock", {})
        entries = {}

        for name, entry_data in lock_data.get("entries", {}).items():
            entry = SkillmanLockEntry(
                name=name,
                source=entry_data.get("source", ""),
                version_spec=entry_data.get("version_spec", "latest"),
                resolved_sha=entry_data.get("resolved_sha"),
                resolved_version=entry_data.get("resolved_version"),
            )
            entries[name] = entry

        return entries

    def _parse_skillman_config(self) -> Dict[str, Any]:
        """Parse skillman's config.toml.

        Returns:
            Configuration dictionary
        """
        if not self.skillman_config_file.exists():
            return {}

        try:
            with open(self.skillman_config_file, "rb") as f:
                return TOML_LOADS(f.read().decode("utf-8"))
        except Exception:
            return {}

    def import_config(self) -> Tuple[bool, List[str]]:
        """Import configuration from skillman to skillmeat.

        Returns:
            Tuple of (success, list of imported keys)
        """
        skillman_config = self._parse_skillman_config()
        if not skillman_config:
            return False, []

        imported = []

        # Import github-token if present
        if "github-token" in skillman_config:
            from skillmeat.config import ConfigManager

            config_mgr = ConfigManager()
            config_mgr.set("settings.github-token", skillman_config["github-token"])
            imported.append("github-token")

        # Import default-scope (note: different meaning in skillmeat)
        # In skillman: "local" or "user"
        # In skillmeat: collection name
        # We'll skip this as it's not directly compatible

        return len(imported) > 0, imported

    def convert_skill_to_artifact(
        self,
        skill: SkillmanSkill,
        lock_entry: Optional[SkillmanLockEntry] = None,
    ) -> Artifact:
        """Convert skillman Skill to skillmeat Artifact.

        Args:
            skill: SkillmanSkill from manifest
            lock_entry: Optional lock entry with resolved versions

        Returns:
            Artifact object
        """
        # Determine origin
        origin = "github" if "/" in skill.source else "local"

        # Build upstream URL if from GitHub
        upstream = None
        if origin == "github":
            # Parse source: "user/repo" or "user/repo/path/to/skill"
            upstream = f"https://github.com/{skill.source}"

        # Use lock entry data if available
        resolved_sha = None
        resolved_version = None
        version_spec = skill.version

        if lock_entry:
            resolved_sha = lock_entry.resolved_sha
            resolved_version = lock_entry.resolved_version
            version_spec = lock_entry.version_spec

        # Create artifact metadata (empty for now, will be populated from SKILL.md)
        metadata = ArtifactMetadata()

        # Determine path (will be set properly during import)
        path = f"skills/{skill.name}"

        return Artifact(
            name=skill.name,
            type=ArtifactType.SKILL,
            path=path,
            origin=origin,
            metadata=metadata,
            added=datetime.now(),
            upstream=upstream,
            version_spec=version_spec,
            resolved_sha=resolved_sha,
            resolved_version=resolved_version,
            tags=skill.aliases,  # Use aliases as tags
        )

    def import_skills_from_manifest(
        self,
        manifest_path: Path,
        force: bool = False,
    ) -> MigrationResult:
        """Import skills from skillman manifest.

        Args:
            manifest_path: Path to skills.toml
            force: Whether to overwrite existing artifacts

        Returns:
            MigrationResult with import statistics
        """
        result = MigrationResult(success=True)

        try:
            # Parse manifest
            skills = self._parse_skillman_manifest(manifest_path)

            # Parse lock file if exists
            lockfile_path = manifest_path.parent / "skills.lock"
            lock_entries = self._parse_skillman_lockfile(lockfile_path)

            # Get collection path
            collection_name = self.collection_mgr.config.get_active_collection()
            collection_path = self.collection_mgr.config.get_collection_path(
                collection_name
            )

            # Import each skill
            for skill in skills:
                try:
                    # Convert to artifact
                    lock_entry = lock_entries.get(skill.name)
                    artifact = self.convert_skill_to_artifact(skill, lock_entry)

                    # Check if already exists
                    manifest_mgr = ManifestManager()
                    collection = manifest_mgr.read(collection_path)

                    # Check if artifact already exists
                    exists = any(
                        a.name == skill.name and a.type == ArtifactType.SKILL
                        for a in collection.artifacts
                    )

                    if exists and not force:
                        result.artifacts_skipped += 1
                        result.warnings.append(
                            f"Skill '{skill.name}' already exists (use --force to overwrite)"
                        )
                        result.skipped_items.append((skill.name, "already exists"))
                        continue

                    # For manifest-based skills, we need to re-fetch from GitHub
                    # or copy from installed location if available
                    # For now, we'll add the artifact metadata and expect the user
                    # to deploy or update to get the actual files

                    # Remove if exists (for --force)
                    if exists:
                        collection.artifacts = [
                            a for a in collection.artifacts
                            if not (a.name == skill.name and a.type == ArtifactType.SKILL)
                        ]

                    # Add to collection
                    collection.artifacts.append(artifact)

                    # Write collection
                    manifest_mgr.write(collection_path, collection)

                    # Update lock file
                    from skillmeat.storage.lockfile import LockManager

                    lock_mgr = LockManager()
                    if artifact.upstream:
                        lock = lock_mgr.read(collection_path) if lock_mgr.exists(collection_path) else None
                        if lock is None:
                            # Create new lock
                            from skillmeat.storage.lockfile import LockFile
                            lock = LockFile(version="1.0.0", entries=[])

                        # Add or update entry
                        from skillmeat.storage.lockfile import LockEntry
                        lock_entry = LockEntry(
                            name=artifact.name,
                            artifact_type=artifact.type.value,
                            source=artifact.upstream,
                            version_spec=artifact.version_spec or "latest",
                            resolved_sha=artifact.resolved_sha,
                            resolved_version=artifact.resolved_version,
                        )

                        # Remove existing entry if present
                        lock.entries = [
                            e for e in lock.entries
                            if not (e.name == artifact.name and e.artifact_type == artifact.type.value)
                        ]
                        lock.entries.append(lock_entry)

                        # Write lock
                        lock_mgr.write(collection_path, lock)

                    result.artifacts_imported += 1

                except Exception as e:
                    result.errors.append(f"Failed to import skill '{skill.name}': {e}")
                    result.success = False

        except Exception as e:
            result.errors.append(f"Failed to parse manifest: {e}")
            result.success = False

        return result

    def import_skills_from_directory(
        self,
        skills_dir: Path,
        force: bool = False,
    ) -> MigrationResult:
        """Import skills from installed skills directory.

        Args:
            skills_dir: Path to skills directory (e.g., ~/.claude/skills/user/)
            force: Whether to overwrite existing artifacts

        Returns:
            MigrationResult with import statistics
        """
        result = MigrationResult(success=True)

        if not skills_dir.exists() or not skills_dir.is_dir():
            result.warnings.append(f"Skills directory not found: {skills_dir}")
            return result

        collection_name = self.collection_mgr.config.get_active_collection()
        collection_path = self.collection_mgr.config.get_collection_path(collection_name)
        skills_target_dir = collection_path / "skills"
        skills_target_dir.mkdir(parents=True, exist_ok=True)

        manifest_mgr = ManifestManager()

        # Iterate over skill directories
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_name = skill_dir.name

            try:
                # Read collection
                collection = manifest_mgr.read(collection_path)

                # Check if skill already exists
                exists = any(
                    a.name == skill_name and a.type == ArtifactType.SKILL
                    for a in collection.artifacts
                )

                if exists and not force:
                    result.artifacts_skipped += 1
                    result.warnings.append(
                        f"Skill '{skill_name}' already exists (use --force to overwrite)"
                    )
                    result.skipped_items.append((skill_name, "already exists"))
                    continue

                # Copy skill directory to collection
                target_dir = skills_target_dir / skill_name
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                shutil.copytree(skill_dir, target_dir)

                # Create artifact metadata
                # Try to extract metadata from SKILL.md if available
                from skillmeat.utils.metadata import MetadataExtractor

                metadata = ArtifactMetadata()
                skill_md = target_dir / "SKILL.md"
                if skill_md.exists():
                    try:
                        extractor = MetadataExtractor(skill_md)
                        extracted = extractor.extract()
                        if extracted:
                            metadata = ArtifactMetadata(
                                title=extracted.get("title"),
                                description=extracted.get("description"),
                                author=extracted.get("author"),
                                license=extracted.get("license"),
                                version=extracted.get("version"),
                                tags=extracted.get("tags", []),
                            )
                    except Exception:
                        pass

                # Create artifact (origin=local since we don't know upstream)
                artifact = Artifact(
                    name=skill_name,
                    type=ArtifactType.SKILL,
                    path=f"skills/{skill_name}",
                    origin="local",
                    metadata=metadata,
                    added=datetime.now(),
                )

                # Remove if exists (for --force)
                if exists:
                    collection.artifacts = [
                        a for a in collection.artifacts
                        if not (a.name == skill_name and a.type == ArtifactType.SKILL)
                    ]

                # Add to collection
                collection.artifacts.append(artifact)

                # Write collection
                manifest_mgr.write(collection_path, collection)

                result.artifacts_imported += 1

            except Exception as e:
                result.errors.append(f"Failed to import skill '{skill_name}': {e}")
                result.success = False

        return result

    def create_migration_snapshot(
        self,
        message: str = "Migrated from skillman",
    ) -> bool:
        """Create a snapshot after migration.

        Args:
            message: Snapshot message

        Returns:
            True if snapshot created successfully
        """
        if not self.version_mgr:
            return False

        try:
            collection_name = self.collection_mgr.config.get_active_collection()
            snapshot_id = self.version_mgr.create_snapshot(collection_name, message)
            return snapshot_id is not None
        except Exception:
            return False

    def generate_report(self, results: List[MigrationResult]) -> str:
        """Generate migration report from results.

        Args:
            results: List of migration results

        Returns:
            Formatted report string
        """
        total_imported = sum(r.artifacts_imported for r in results)
        total_skipped = sum(r.artifacts_skipped for r in results)
        total_errors = sum(len(r.errors) for r in results)

        report = []
        report.append("\nMigration Summary:")
        report.append(f"  {total_imported} artifacts imported successfully")
        report.append(f"  {total_skipped} artifacts skipped")
        report.append(f"  {total_errors} errors")

        # Show errors
        if total_errors > 0:
            report.append("\nErrors:")
            for result in results:
                for error in result.errors:
                    report.append(f"  - {error}")

        # Show warnings
        warnings = []
        for result in results:
            warnings.extend(result.warnings)
        if warnings:
            report.append("\nWarnings:")
            for warning in warnings[:5]:  # Show first 5 warnings
                report.append(f"  - {warning}")
            if len(warnings) > 5:
                report.append(f"  ... and {len(warnings) - 5} more")

        # Show skipped items
        skipped = []
        for result in results:
            skipped.extend(result.skipped_items)
        if skipped:
            report.append("\nSkipped:")
            for name, reason in skipped[:5]:  # Show first 5
                report.append(f"  - {name}: {reason}")
            if len(skipped) > 5:
                report.append(f"  ... and {len(skipped) - 5} more")

        return "\n".join(report)
