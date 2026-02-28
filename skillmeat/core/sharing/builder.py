"""Bundle builder for creating .skillmeat-pack archives.

This module provides the BundleBuilder class for packaging SkillMeat artifacts
into distributable bundle files with validation and integrity checking.
"""

import logging
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from skillmeat.core.artifact import Artifact, ArtifactType
from skillmeat.core.collection import CollectionManager
from skillmeat.core.sharing.bundle import Bundle, BundleArtifact, BundleMetadata
from skillmeat.core.sharing.hasher import BundleHasher, FileHasher
from skillmeat.core.sharing.manifest import BundleManifest, ManifestValidator


class BundleValidationError(Exception):
    """Raised when bundle validation fails during creation."""

    pass


class BundleBuilder:
    """Builder for creating .skillmeat-pack bundle archives.

    Provides functionality to:
    - Add artifacts from collection
    - Generate manifest with metadata
    - Calculate cryptographic hashes
    - Create deterministic ZIP archives
    - Validate bundle integrity

    Example usage:
        builder = BundleBuilder(
            name="my-bundle",
            description="My artifact bundle",
            author="user@example.com"
        )
        builder.add_artifact("my-skill", ArtifactType.SKILL)
        bundle_path = builder.build("/output/my-bundle.skillmeat-pack")
    """

    def __init__(
        self,
        name: str,
        description: str,
        author: str,
        version: str = "1.0.0",
        license: str = "MIT",
        tags: Optional[List[str]] = None,
        homepage: Optional[str] = None,
        repository: Optional[str] = None,
        collection_name: Optional[str] = None,
        compression_level: int = zipfile.ZIP_DEFLATED,
    ):
        """Initialize bundle builder.

        Args:
            name: Bundle name (identifier, alphanumeric + dash/underscore)
            description: Human-readable description
            author: Author name or email
            version: Bundle version (semver recommended)
            license: License identifier (e.g., "MIT", "Apache-2.0")
            tags: Optional list of tags for categorization
            homepage: Optional URL to project homepage
            repository: Optional URL to source repository
            collection_name: Source collection (uses active if None)
            compression_level: ZIP compression level (default: ZIP_DEFLATED)

        Raises:
            ValueError: If name, description, or author are invalid
        """
        # Validate required fields
        if not name or not isinstance(name, str):
            raise ValueError("Bundle name must be a non-empty string")

        if not description or not isinstance(description, str):
            raise ValueError("Bundle description must be a non-empty string")

        if not author or not isinstance(author, str):
            raise ValueError("Bundle author must be a non-empty string")

        # Validate name format (alphanumeric + dash/underscore)
        if not all(c.isalnum() or c in ("-", "_") for c in name):
            raise ValueError(
                f"Bundle name '{name}' contains invalid characters. "
                "Only alphanumeric, dash, and underscore are allowed."
            )

        self.name = name
        self.description = description
        self.author = author
        self.version = version
        self.license = license
        self.tags = tags or []
        self.homepage = homepage
        self.repository = repository
        self.compression_level = compression_level

        # Initialize collection manager
        self.collection_mgr = CollectionManager()
        self.collection = self.collection_mgr.load_collection(collection_name)
        self.collection_path = self.collection_mgr.config.get_collection_path(
            self.collection.name
        )

        # Internal state
        self._artifacts: List[BundleArtifact] = []
        self._dependencies: List[str] = []
        self._artifact_paths: Dict[str, Path] = {}  # artifact key -> filesystem path

        logging.info(
            f"Initialized BundleBuilder for '{name}' from collection '{self.collection.name}'"
        )

    def add_artifact(
        self,
        artifact_name: str,
        artifact_type: Optional[ArtifactType] = None,
        custom_scope: Optional[str] = None,
    ) -> None:
        """Add artifact to bundle.

        Args:
            artifact_name: Name of artifact to add
            artifact_type: Type of artifact (required if ambiguous)
            custom_scope: Override scope (default: use artifact's current scope)

        Raises:
            ValueError: If artifact not found or already added
            BundleValidationError: If artifact validation fails
        """
        # Find artifact in collection
        artifact = self.collection.find_artifact(artifact_name, artifact_type)
        if not artifact:
            raise ValueError(
                f"Artifact '{artifact_name}' "
                f"{f'of type {artifact_type.value}' if artifact_type else ''} "
                f"not found in collection '{self.collection.name}'"
            )

        # Check for duplicates
        artifact_key = f"{artifact.type.value}::{artifact.name}"
        if artifact_key in self._artifact_paths:
            raise ValueError(
                f"Artifact '{artifact.name}' of type '{artifact.type.value}' "
                f"already added to bundle"
            )

        # Get artifact path on filesystem
        artifact_path = self.collection_path / artifact.path

        if not artifact_path.exists():
            raise BundleValidationError(f"Artifact files not found: {artifact_path}")

        # Collect all files in artifact
        files = self._collect_artifact_files(artifact_path, artifact.type)

        if not files:
            raise BundleValidationError(f"Artifact '{artifact.name}' contains no files")

        # Compute hash of artifact files
        artifact_hash = BundleHasher.hash_artifact_files(artifact_path, files)

        # Determine scope (use custom or artifact's current scope)
        scope = custom_scope or "user"  # Default to user scope

        # Create BundleArtifact
        bundle_artifact = BundleArtifact(
            type=artifact.type.value,
            name=artifact.name,
            version=artifact.metadata.version or "unknown",
            scope=scope,
            path=f"artifacts/{artifact.type.value}/{artifact.name}/",
            files=files,
            hash=artifact_hash,
            metadata={
                "title": artifact.metadata.title or artifact.name,
                "description": artifact.metadata.description or "",
                "author": artifact.metadata.author or "",
                "license": artifact.metadata.license or "",
            },
        )

        self._artifacts.append(bundle_artifact)
        self._artifact_paths[artifact_key] = artifact_path

        logging.info(
            f"Added artifact {artifact.type.value}/{artifact.name} to bundle "
            f"({len(files)} files, hash: {artifact_hash[:15]}...)"
        )

    def add_artifacts_by_type(
        self,
        artifact_type: ArtifactType,
        custom_scope: Optional[str] = None,
    ) -> int:
        """Add all artifacts of a specific type to bundle.

        Args:
            artifact_type: Type of artifacts to add
            custom_scope: Override scope for all artifacts

        Returns:
            Number of artifacts added

        Raises:
            BundleValidationError: If any artifact validation fails
        """
        artifacts = self.collection.get_artifacts_by_type(artifact_type)

        count = 0
        for artifact in artifacts:
            try:
                self.add_artifact(artifact.name, artifact_type, custom_scope)
                count += 1
            except ValueError as e:
                # Skip artifacts already added
                logging.warning(f"Skipping artifact {artifact.name}: {e}")
                continue

        logging.info(
            f"Added {count} artifact(s) of type {artifact_type.value} to bundle"
        )
        return count

    def add_all_artifacts(self, custom_scope: Optional[str] = None) -> int:
        """Add all artifacts from collection to bundle.

        Args:
            custom_scope: Override scope for all artifacts

        Returns:
            Number of artifacts added

        Raises:
            BundleValidationError: If any artifact validation fails
        """
        count = 0

        for artifact in self.collection.artifacts:
            try:
                self.add_artifact(artifact.name, artifact.type, custom_scope)
                count += 1
            except ValueError as e:
                logging.warning(f"Skipping artifact {artifact.name}: {e}")
                continue

        logging.info(f"Added {count} artifact(s) to bundle")
        return count

    def add_workflow(
        self,
        workflow_name: str,
        yaml_content: str,
        version: str = "unknown",
        description: str = "",
        custom_scope: Optional[str] = None,
    ) -> None:
        """Add a workflow to the bundle from its YAML definition string.

        Workflows are DB-backed (not filesystem-backed), so this method accepts
        the YAML content directly rather than resolving a filesystem path.

        Args:
            workflow_name: Identifier name for the workflow (used as bundle path)
            yaml_content: Raw YAML content of the workflow definition (SWDL format)
            version: Workflow version string (default: "unknown")
            description: Human-readable description for bundle metadata
            custom_scope: Override scope (default: "user")

        Raises:
            ValueError: If workflow already added to bundle
        """
        import hashlib

        artifact_key = f"workflow::{workflow_name}"
        if artifact_key in self._artifact_paths:
            raise ValueError(
                f"Workflow '{workflow_name}' already added to bundle"
            )

        # Compute hash of the YAML content
        content_hash = "sha256:" + hashlib.sha256(yaml_content.encode("utf-8")).hexdigest()

        scope = custom_scope or "user"
        bundle_path = f"artifacts/workflow/{workflow_name}/"
        yaml_filename = "WORKFLOW.yaml"

        bundle_artifact = BundleArtifact(
            type=ArtifactType.WORKFLOW.value,
            name=workflow_name,
            version=version,
            scope=scope,
            path=bundle_path,
            files=[yaml_filename],
            hash=content_hash,
            metadata={
                "description": description,
                "content": yaml_content,  # store inline for workflow artifacts
            },
        )

        self._artifacts.append(bundle_artifact)
        # Use sentinel None path — workflow content lives in metadata["content"]
        self._artifact_paths[artifact_key] = None  # type: ignore[assignment]
        self._workflow_yaml: Dict[str, str] = getattr(self, "_workflow_yaml", {})
        self._workflow_yaml[workflow_name] = yaml_content

        logging.info(
            f"Added workflow '{workflow_name}' to bundle (hash: {content_hash[:15]}...)"
        )

    def add_dependency(self, dependency: str) -> None:
        """Add bundle dependency.

        Args:
            dependency: Dependency identifier (bundle name or spec)

        Raises:
            ValueError: If dependency already added
        """
        if dependency in self._dependencies:
            raise ValueError(f"Dependency '{dependency}' already added")

        self._dependencies.append(dependency)
        logging.info(f"Added dependency: {dependency}")

    def _collect_artifact_files(
        self, artifact_path: Path, artifact_type: ArtifactType
    ) -> List[str]:
        """Collect all files in artifact directory.

        Args:
            artifact_path: Path to artifact root
            artifact_type: Type of artifact

        Returns:
            List of file paths relative to artifact_path

        Raises:
            ValueError: If artifact_path is not a directory
        """
        if not artifact_path.is_dir():
            raise ValueError(f"Artifact path is not a directory: {artifact_path}")

        files = []

        # Exclusion patterns (files to skip)
        exclude_patterns = [
            "__pycache__",
            "*.pyc",
            ".git",
            ".DS_Store",
            "node_modules",
            ".env",
            "*.lock",
        ]

        for file_path in artifact_path.rglob("*"):
            if not file_path.is_file():
                continue

            # Check exclusion patterns
            if any(file_path.match(pattern) for pattern in exclude_patterns):
                continue

            # Get relative path
            rel_path = file_path.relative_to(artifact_path)
            files.append(
                str(rel_path).replace("\\", "/")
            )  # Normalize to forward slashes

        return sorted(files)  # Sort for determinism

    def _validate_bundle(self) -> None:
        """Validate bundle before building.

        Raises:
            BundleValidationError: If validation fails
        """
        if not self._artifacts:
            raise BundleValidationError("Bundle must contain at least one artifact")

        # Validate all artifact files exist (skip workflow artifacts — DB-backed)
        for artifact in self._artifacts:
            if artifact.type == ArtifactType.WORKFLOW.value:
                # Workflow content is stored inline in metadata["content"]
                if "content" not in artifact.metadata:
                    raise BundleValidationError(
                        f"Workflow artifact '{artifact.name}' missing YAML content"
                    )
                continue

            artifact_key = f"{artifact.type}::{artifact.name}"
            artifact_path = self._artifact_paths[artifact_key]

            for file_rel_path in artifact.files:
                file_path = artifact_path / file_rel_path
                if not file_path.exists():
                    raise BundleValidationError(f"Artifact file not found: {file_path}")

        logging.info(f"Bundle validation passed: {len(self._artifacts)} artifact(s)")

    def build(
        self,
        output_path: Path,
        validate: bool = True,
        sign: bool = False,
        signing_key_id: Optional[str] = None,
    ) -> Bundle:
        """Build bundle archive.

        Creates a deterministic .skillmeat-pack ZIP archive with:
        - manifest.json in root
        - artifacts/ directory with all artifact files
        - Consistent timestamps for reproducible builds
        - Optional cryptographic signature

        Args:
            output_path: Path where bundle will be saved
            validate: Whether to validate bundle before building
            sign: Whether to sign the bundle with Ed25519 signature
            signing_key_id: Signing key ID (uses default if None and sign=True)

        Returns:
            Bundle object representing created bundle

        Raises:
            BundleValidationError: If validation fails
            PermissionError: If output path is not writable
            IOError: If bundle creation fails
            ValueError: If signing is requested but no key is available
        """
        # Validate bundle
        if validate:
            self._validate_bundle()

        # Create temporary workspace
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create bundle structure
            artifacts_dir = temp_path / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)

            # Copy artifacts to temp workspace
            for artifact in self._artifacts:
                if artifact.type == ArtifactType.WORKFLOW.value:
                    # Workflow: write YAML content directly (no filesystem source)
                    yaml_content = artifact.metadata.get("content", "")
                    dest_dir = temp_path / artifact.path
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    (dest_dir / "WORKFLOW.yaml").write_text(yaml_content, encoding="utf-8")
                    logging.debug(
                        f"Wrote workflow '{artifact.name}' YAML to {artifact.path}"
                    )
                    continue

                artifact_key = f"{artifact.type}::{artifact.name}"
                source_path = self._artifact_paths[artifact_key]
                dest_path = temp_path / artifact.path

                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(source_path, dest_path)

                logging.debug(f"Copied artifact {artifact.name} to {artifact.path}")

            # Create bundle metadata
            metadata = BundleMetadata(
                name=self.name,
                description=self.description,
                author=self.author,
                created_at=datetime.utcnow().isoformat(),
                version=self.version,
                license=self.license,
                tags=self.tags,
                homepage=self.homepage,
                repository=self.repository,
            )

            # Create Bundle object (without hash yet)
            bundle = Bundle(
                metadata=metadata,
                artifacts=self._artifacts,
                dependencies=self._dependencies,
            )

            # Generate manifest
            manifest_dict = bundle.to_dict()

            # Compute bundle hash
            artifact_hashes = [artifact.hash for artifact in self._artifacts]
            bundle_hash = BundleHasher.compute_bundle_hash(
                manifest_dict, artifact_hashes
            )

            # Update manifest with bundle hash
            manifest_dict["bundle_hash"] = bundle_hash
            bundle.bundle_hash = bundle_hash

            # Sign bundle if requested
            if sign:
                from skillmeat.core.signing import BundleSigner, KeyManager

                key_manager = KeyManager()
                signer = BundleSigner(key_manager)

                try:
                    signature_data = signer.sign_bundle(
                        bundle_hash, manifest_dict, signing_key_id
                    )
                    manifest_dict["signature"] = signature_data.to_dict()
                    bundle.signature = signature_data
                    logging.info(
                        f"Bundle signed with key {signature_data.key_fingerprint[:8]}... "
                        f"by {signature_data.signer_name}"
                    )
                except ValueError as e:
                    raise BundleValidationError(f"Bundle signing failed: {e}")

            # Validate manifest
            validation_result = ManifestValidator.validate_manifest(manifest_dict)
            if not validation_result.valid:
                error_messages = [
                    f"{error.field}: {error.message}"
                    for error in validation_result.errors
                ]
                raise BundleValidationError(
                    f"Manifest validation failed:\n" + "\n".join(error_messages)
                )

            # Write manifest to temp workspace
            manifest_path = temp_path / "manifest.json"
            BundleManifest.write_manifest(manifest_dict, manifest_path)

            # Create ZIP archive
            self._create_zip_archive(temp_path, output_path)

            # Set bundle path
            bundle.bundle_path = output_path

            logging.info(
                f"Bundle created successfully: {output_path} "
                f"({bundle.artifact_count} artifacts, hash: {bundle_hash[:15]}...)"
            )

            return bundle

    def _create_zip_archive(self, source_dir: Path, output_path: Path) -> None:
        """Create deterministic ZIP archive from directory.

        Creates ZIP with:
        - Sorted file entries (deterministic order)
        - Fixed timestamps (for reproducible builds)
        - Specified compression level

        Args:
            source_dir: Directory to archive
            output_path: Path where ZIP will be saved

        Raises:
            PermissionError: If output path is not writable
            IOError: If ZIP creation fails
        """
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Fixed timestamp for deterministic builds (2020-01-01 00:00:00)
        fixed_date_time = (2020, 1, 1, 0, 0, 0)

        with zipfile.ZipFile(
            output_path, "w", compression=self.compression_level
        ) as zipf:
            # Collect all files (sorted for determinism)
            files = sorted(source_dir.rglob("*"))

            for file_path in files:
                if not file_path.is_file():
                    continue

                # Get path relative to source_dir
                arcname = file_path.relative_to(source_dir)

                # Create ZipInfo with fixed timestamp
                zipinfo = zipfile.ZipInfo(
                    filename=str(arcname).replace("\\", "/"),
                    date_time=fixed_date_time,
                )
                zipinfo.compress_type = self.compression_level

                # Add file to archive
                with open(file_path, "rb") as f:
                    zipf.writestr(zipinfo, f.read())

        logging.info(f"Created ZIP archive: {output_path}")


def inspect_bundle(bundle_path: Path) -> Bundle:
    """Inspect a .skillmeat-pack bundle file.

    Reads and validates the bundle without extracting it.

    Args:
        bundle_path: Path to .skillmeat-pack file

    Returns:
        Bundle object with metadata and artifact listing

    Raises:
        FileNotFoundError: If bundle file doesn't exist
        ValueError: If bundle is not a valid ZIP
        BundleValidationError: If manifest validation fails
    """
    if not bundle_path.exists():
        raise FileNotFoundError(f"Bundle file not found: {bundle_path}")

    if not zipfile.is_zipfile(bundle_path):
        raise ValueError(f"Not a valid ZIP file: {bundle_path}")

    # Open ZIP and read manifest
    with zipfile.ZipFile(bundle_path, "r") as zipf:
        # Check if manifest.json exists
        if "manifest.json" not in zipf.namelist():
            raise BundleValidationError(
                "Invalid bundle: manifest.json not found in archive"
            )

        # Read and parse manifest
        manifest_data = zipf.read("manifest.json")
        manifest_dict = __import__("json").loads(manifest_data)

        # Validate manifest
        validation_result = ManifestValidator.validate_manifest(manifest_dict)
        if not validation_result.valid:
            error_messages = [
                f"{error.field}: {error.message}" for error in validation_result.errors
            ]
            raise BundleValidationError(
                f"Manifest validation failed:\n" + "\n".join(error_messages)
            )

        # Create Bundle object
        bundle = Bundle.from_dict(manifest_dict)
        bundle.bundle_path = bundle_path

        # Verify bundle integrity (hash check)
        artifact_hashes = [artifact.hash for artifact in bundle.artifacts]
        if not BundleHasher.verify_bundle_integrity(manifest_dict, artifact_hashes):
            logging.warning(
                f"Bundle hash verification failed for {bundle_path}. "
                f"Bundle may have been tampered with."
            )

        return bundle
