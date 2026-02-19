"""Bundle data models for SkillMeat artifact sharing.

This module defines the core data structures for .skillmeat-pack bundles,
which are used to package and distribute artifacts across teams.

It also provides the :func:`export_composite_bundle` function for generating
composite-aware bundle zips from the DB cache.
"""

import json
import logging
import shutil
import tempfile
import zipfile
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from skillmeat.core.artifact import ArtifactType

logger = logging.getLogger(__name__)


@dataclass
class BundleArtifact:
    """Represents a single artifact within a bundle.

    Attributes:
        type: Type of artifact (skill, command, agent)
        name: Artifact name
        version: Artifact version string
        scope: Scope (user or local)
        path: Relative path within bundle archive
        files: List of file paths relative to artifact root
        hash: SHA-256 hash of artifact contents
        metadata: Optional artifact metadata dictionary
    """

    type: str  # ArtifactType.value
    name: str
    version: str
    scope: str
    path: str  # Relative path in bundle (e.g., "artifacts/my-skill/")
    files: List[str]  # List of files relative to path
    hash: str  # SHA-256 hash
    metadata: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Validate artifact data."""
        if self.type not in [t.value for t in ArtifactType]:
            raise ValueError(
                f"Invalid artifact type '{self.type}'. "
                f"Must be one of: {[t.value for t in ArtifactType]}"
            )

        if self.scope not in ("user", "local"):
            raise ValueError(f"Invalid scope '{self.scope}'. Must be 'user' or 'local'")

        if not self.hash.startswith("sha256:"):
            raise ValueError(
                f"Hash must be in format 'sha256:...' but got: {self.hash}"
            )

    def to_dict(self) -> Dict:
        """Convert to dictionary for manifest serialization."""
        return {
            "type": self.type,
            "name": self.name,
            "version": self.version,
            "scope": self.scope,
            "path": self.path,
            "files": self.files,
            "hash": self.hash,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "BundleArtifact":
        """Create from dictionary (manifest deserialization)."""
        return cls(
            type=data["type"],
            name=data["name"],
            version=data.get("version", "unknown"),
            scope=data.get("scope", "user"),
            path=data["path"],
            files=data.get("files", []),
            hash=data["hash"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class BundleMetadata:
    """Metadata for a bundle.

    Attributes:
        name: Bundle name (identifier)
        description: Human-readable description
        author: Author name or email
        created_at: ISO 8601 timestamp of bundle creation
        version: Bundle version (semver recommended)
        license: License identifier (e.g., "MIT", "Apache-2.0")
        tags: List of tags for categorization
        homepage: Optional URL to project homepage
        repository: Optional URL to source repository
    """

    name: str
    description: str
    author: str
    created_at: str  # ISO 8601 timestamp
    version: str = "1.0.0"
    license: str = "MIT"
    tags: List[str] = field(default_factory=list)
    homepage: Optional[str] = None
    repository: Optional[str] = None

    def __post_init__(self):
        """Validate metadata."""
        if not self.name:
            raise ValueError("Bundle name cannot be empty")

        if not self.description:
            raise ValueError("Bundle description cannot be empty")

        if not self.author:
            raise ValueError("Bundle author cannot be empty")

        # Validate ISO 8601 timestamp format
        try:
            datetime.fromisoformat(self.created_at)
        except ValueError as e:
            raise ValueError(f"created_at must be ISO 8601 format: {e}") from e

    def to_dict(self) -> Dict:
        """Convert to dictionary for manifest serialization."""
        result = {
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "created_at": self.created_at,
            "version": self.version,
            "license": self.license,
        }

        if self.tags:
            result["tags"] = self.tags

        if self.homepage:
            result["homepage"] = self.homepage

        if self.repository:
            result["repository"] = self.repository

        return result

    @classmethod
    def from_dict(cls, data: Dict) -> "BundleMetadata":
        """Create from dictionary (manifest deserialization)."""
        return cls(
            name=data["name"],
            description=data["description"],
            author=data["author"],
            created_at=data["created_at"],
            version=data.get("version", "1.0.0"),
            license=data.get("license", "MIT"),
            tags=data.get("tags", []),
            homepage=data.get("homepage"),
            repository=data.get("repository"),
        )


@dataclass
class Bundle:
    """Represents a complete .skillmeat-pack bundle.

    A bundle is a ZIP archive containing:
    - manifest.json: Bundle metadata and artifact listing
    - artifacts/: Directory containing artifact files

    Attributes:
        metadata: Bundle metadata
        artifacts: List of artifacts in the bundle
        dependencies: List of bundle dependencies (other bundles required)
        bundle_hash: SHA-256 hash of entire bundle contents
        bundle_path: Optional path to bundle file on disk
    """

    metadata: BundleMetadata
    artifacts: List[BundleArtifact] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    bundle_hash: Optional[str] = None
    bundle_path: Optional[Path] = None

    def __post_init__(self):
        """Validate bundle data."""
        if self.bundle_hash and not self.bundle_hash.startswith("sha256:"):
            raise ValueError(
                f"bundle_hash must be in format 'sha256:...' but got: {self.bundle_hash}"
            )

    @property
    def artifact_count(self) -> int:
        """Return number of artifacts in bundle."""
        return len(self.artifacts)

    @property
    def total_files(self) -> int:
        """Return total number of files across all artifacts."""
        return sum(len(artifact.files) for artifact in self.artifacts)

    def find_artifact(
        self, name: str, artifact_type: Optional[str] = None
    ) -> Optional[BundleArtifact]:
        """Find artifact by name and optional type.

        Args:
            name: Artifact name to find
            artifact_type: Optional type to filter by

        Returns:
            BundleArtifact if found, None otherwise
        """
        for artifact in self.artifacts:
            if artifact.name == name:
                if artifact_type is None or artifact.type == artifact_type:
                    return artifact
        return None

    def get_artifacts_by_type(self, artifact_type: str) -> List[BundleArtifact]:
        """Get all artifacts of a specific type.

        Args:
            artifact_type: Type to filter by (skill, command, agent)

        Returns:
            List of matching artifacts
        """
        return [a for a in self.artifacts if a.type == artifact_type]

    def to_dict(self) -> Dict:
        """Convert to dictionary for manifest serialization."""
        return {
            "version": "1.0",  # Manifest format version
            "name": self.metadata.name,
            "description": self.metadata.description,
            "author": self.metadata.author,
            "created_at": self.metadata.created_at,
            "license": self.metadata.license,
            "tags": self.metadata.tags,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "dependencies": self.dependencies,
            "bundle_hash": self.bundle_hash or "",
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Bundle":
        """Create from dictionary (manifest deserialization)."""
        metadata = BundleMetadata(
            name=data["name"],
            description=data["description"],
            author=data["author"],
            created_at=data["created_at"],
            version=data.get("version", "1.0.0"),
            license=data.get("license", "MIT"),
            tags=data.get("tags", []),
            homepage=data.get("homepage"),
            repository=data.get("repository"),
        )

        artifacts = [
            BundleArtifact.from_dict(artifact_data)
            for artifact_data in data.get("artifacts", [])
        ]

        return cls(
            metadata=metadata,
            artifacts=artifacts,
            dependencies=data.get("dependencies", []),
            bundle_hash=data.get("bundle_hash"),
        )


# ---------------------------------------------------------------------------
# Type-to-subdirectory mapping for artifact filesystem layout
# ---------------------------------------------------------------------------

#: Maps artifact type strings to their collection subdirectory names.
_TYPE_TO_SUBDIR: Dict[str, str] = {
    "skill": "skills",
    "command": "commands",
    "agent": "agents",
    "hook": "hooks",
    "mcp": "mcp",
    "mcp_server": "mcp",
    "composite": "composites",
}

#: Single-file artifact types (stored as ``<name>.md`` rather than a directory).
_SINGLE_FILE_TYPES = {"command", "agent"}


def _resolve_child_path(collection_path: Path, artifact_type: str, name: str) -> Path:
    """Return the filesystem path for a child artifact within a collection.

    Args:
        collection_path: Root directory of the collection (e.g., ``~/.skillmeat/collection``).
        artifact_type: Artifact type string (e.g., ``"skill"``, ``"command"``).
        name: Artifact name (without extension for single-file types).

    Returns:
        Absolute ``Path`` to the artifact on disk.

    Raises:
        ValueError: If ``artifact_type`` is not recognised.
    """
    subdir = _TYPE_TO_SUBDIR.get(artifact_type)
    if subdir is None:
        raise ValueError(
            f"Unknown artifact type '{artifact_type}'. "
            f"Expected one of: {sorted(_TYPE_TO_SUBDIR)}"
        )

    if artifact_type in _SINGLE_FILE_TYPES:
        return collection_path / subdir / f"{name}.md"

    return collection_path / subdir / name


def _collect_files(artifact_path: Path) -> List[str]:
    """Collect file paths relative to *artifact_path*, excluding cache/VCS noise.

    Args:
        artifact_path: Root of the artifact (directory or single file).

    Returns:
        Sorted list of relative file path strings (forward slashes).
    """
    exclude_patterns = [
        "__pycache__",
        "*.pyc",
        ".git",
        ".DS_Store",
        "node_modules",
        ".env",
        "*.lock",
    ]

    if artifact_path.is_file():
        return [artifact_path.name]

    files: List[str] = []
    for fp in artifact_path.rglob("*"):
        if not fp.is_file():
            continue
        if any(fp.match(pat) for pat in exclude_patterns):
            continue
        rel = fp.relative_to(artifact_path)
        files.append(str(rel).replace("\\", "/"))

    return sorted(files)


class CompositeBundleError(Exception):
    """Raised when composite bundle export fails."""


def export_composite_bundle(
    composite_id: str,
    output_path: str,
    session,  # sqlalchemy.orm.Session — not typed to avoid import cycle
    collection_name: Optional[str] = None,
) -> str:
    """Export a composite artifact and all its children as a Bundle zip.

    The generated archive follows the same ``.skillmeat-pack`` layout used by
    :class:`~skillmeat.core.sharing.builder.BundleBuilder`:

    .. code-block:: text

        manifest.json
        composite.json           # composite metadata (id, type, description)
        artifacts/
            skills/<name>/       # skill child artifacts
            commands/<name>.md   # single-file command artifacts
            agents/<name>.md     # single-file agent artifacts
            ...

    Args:
        composite_id: ``type:name`` identifier of the composite artifact
            (e.g. ``"composite:my-plugin"``).  Must exist in the DB session.
        output_path: Filesystem path where the ``.skillmeat-pack`` zip will
            be written.  The parent directory must exist.
        session: Active SQLAlchemy ``Session`` with access to the
            ``composite_artifacts`` and ``artifacts`` tables.
        collection_name: Optional collection name override.  When ``None`` the
            function resolves the collection via the
            :class:`~skillmeat.core.collection.CollectionManager` using the
            active collection name.

    Returns:
        Absolute path string to the created zip file.

    Raises:
        CompositeBundleError: If the composite is not found, has no children,
            or a child artifact cannot be located on the filesystem.
        ValueError: If ``output_path`` parent directory does not exist.
    """
    # Deferred imports to avoid circular dependency chains at module load time.
    from skillmeat.cache.models import CompositeArtifact, Collection
    from skillmeat.core.collection import CollectionManager
    from skillmeat.core.sharing.hasher import BundleHasher

    # ------------------------------------------------------------------
    # Step 1: Load composite from DB
    # ------------------------------------------------------------------
    composite = (
        session.query(CompositeArtifact)
        .filter(CompositeArtifact.id == composite_id)
        .first()
    )
    if composite is None:
        raise CompositeBundleError(
            f"Composite artifact '{composite_id}' not found in the database. "
            "Ensure the artifact has been imported before exporting."
        )

    memberships = composite.memberships  # eager-loaded via selectin
    if not memberships:
        raise CompositeBundleError(
            f"Composite artifact '{composite_id}' has no child members. "
            "Nothing to export."
        )

    # ------------------------------------------------------------------
    # Step 2: Resolve collection filesystem path
    # ------------------------------------------------------------------
    col_mgr = CollectionManager()

    if collection_name is not None:
        resolved_collection_name = collection_name
    else:
        # Try to look up the Collection row to get its name
        coll_row = (
            session.query(Collection)
            .filter(Collection.id == composite.collection_id)
            .first()
        )
        if coll_row is not None:
            resolved_collection_name = coll_row.name
        else:
            # collection_id may itself be a name (for test fixtures)
            resolved_collection_name = composite.collection_id

        # Fall back to active collection when resolution fails
        try:
            col_mgr.load_collection(resolved_collection_name)
        except (ValueError, FileNotFoundError):
            logger.warning(
                "export_composite_bundle: collection '%s' not found; "
                "falling back to active collection.",
                resolved_collection_name,
            )
            resolved_collection_name = col_mgr.get_active_collection_name()

    collection_path = col_mgr.config.get_collection_path(resolved_collection_name)

    logger.info(
        "export_composite_bundle: exporting composite=%s collection_path=%s",
        composite_id,
        collection_path,
    )

    # ------------------------------------------------------------------
    # Step 3: Collect child artifact files
    # ------------------------------------------------------------------
    # composite_name is the part after "composite:" prefix
    composite_name = (
        composite_id.split(":", 1)[-1] if ":" in composite_id else composite_id
    )

    bundle_artifacts: List[Dict] = []
    artifact_hashes: List[str] = []

    for membership in memberships:
        child = membership.child_artifact
        if child is None:
            logger.warning(
                "export_composite_bundle: membership with uuid=%s has no resolved "
                "child_artifact ORM object; skipping.",
                membership.child_artifact_uuid,
            )
            continue

        child_type = child.type
        child_name = child.name

        try:
            artifact_path = _resolve_child_path(collection_path, child_type, child_name)
        except ValueError as exc:
            raise CompositeBundleError(
                f"Cannot resolve filesystem path for child '{child_type}:{child_name}': {exc}"
            ) from exc

        if not artifact_path.exists():
            raise CompositeBundleError(
                f"Child artifact '{child_type}:{child_name}' not found on disk at "
                f"'{artifact_path}'.  Re-sync the collection before exporting."
            )

        files = _collect_files(artifact_path)
        if not files:
            logger.warning(
                "export_composite_bundle: child '%s:%s' has no files; skipping.",
                child_type,
                child_name,
            )
            continue

        subdir = _TYPE_TO_SUBDIR.get(child_type, f"{child_type}s")
        bundle_relative_path = f"artifacts/{subdir}/{child_name}/"

        # Compute per-artifact hash
        if artifact_path.is_dir():
            artifact_hash = BundleHasher.hash_artifact_files(artifact_path, files)
        else:
            from skillmeat.core.sharing.hasher import FileHasher

            artifact_hash = FileHasher.hash_file(artifact_path)

        deployed_version = child.deployed_version or "unknown"
        bundle_artifacts.append(
            {
                "type": child_type,
                "name": child_name,
                "version": deployed_version,
                "scope": "user",
                "path": bundle_relative_path,
                "files": files,
                "hash": artifact_hash,
                "metadata": {"description": child.description or ""},
            }
        )
        artifact_hashes.append(artifact_hash)

    if not bundle_artifacts:
        raise CompositeBundleError(
            f"No exportable child artifacts found for composite '{composite_id}'."
        )

    # ------------------------------------------------------------------
    # Step 4: Build manifest and composite metadata
    # ------------------------------------------------------------------
    now_iso = datetime.utcnow().isoformat()

    manifest: Dict = {
        "version": "1.0",
        "name": composite_name,
        "description": composite.description or f"Composite artifact: {composite_name}",
        "author": "SkillMeat",
        "created_at": now_iso,
        "license": "MIT",
        "tags": [composite.composite_type, "composite"],
        "artifacts": bundle_artifacts,
        "dependencies": [],
        "bundle_hash": "",  # filled in below
    }

    bundle_hash = BundleHasher.compute_bundle_hash(manifest, artifact_hashes)
    manifest["bundle_hash"] = bundle_hash

    composite_metadata: Dict = {
        "id": composite_id,
        "composite_type": composite.composite_type,
        "display_name": composite.display_name or composite_name,
        "description": composite.description,
        "collection_id": composite.collection_id,
        "created_at": (
            composite.created_at.isoformat() if composite.created_at else None
        ),
        "updated_at": (
            composite.updated_at.isoformat() if composite.updated_at else None
        ),
        "member_count": len(bundle_artifacts),
        "exported_at": now_iso,
    }

    # ------------------------------------------------------------------
    # Step 5: Write zip archive
    # ------------------------------------------------------------------
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    fixed_date_time = (2020, 1, 1, 0, 0, 0)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)

        # Write manifest.json
        manifest_file = tmp / "manifest.json"
        manifest_file.write_text(
            json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
        )

        # Write composite.json
        composite_file = tmp / "composite.json"
        composite_file.write_text(
            json.dumps(composite_metadata, indent=2, sort_keys=True), encoding="utf-8"
        )

        # Copy child artifact files
        for bundle_artifact in bundle_artifacts:
            child_type = bundle_artifact["type"]
            child_name = bundle_artifact["name"]
            artifact_path = _resolve_child_path(collection_path, child_type, child_name)
            dest_dir = tmp / bundle_artifact["path"].lstrip("/")

            if artifact_path.is_dir():
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.copytree(artifact_path, dest_dir, dirs_exist_ok=True)
            else:
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(artifact_path, dest_dir / artifact_path.name)

        # Create deterministic ZIP
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for fp in sorted(tmp.rglob("*")):
                if not fp.is_file():
                    continue
                arcname = fp.relative_to(tmp)
                zi = zipfile.ZipInfo(
                    filename=str(arcname).replace("\\", "/"),
                    date_time=fixed_date_time,
                )
                zi.compress_type = zipfile.ZIP_DEFLATED
                with open(fp, "rb") as fh:
                    zf.writestr(zi, fh.read())

    logger.info(
        "export_composite_bundle: created archive at %s (%d child artifacts)",
        output,
        len(bundle_artifacts),
    )

    return str(output.resolve())
