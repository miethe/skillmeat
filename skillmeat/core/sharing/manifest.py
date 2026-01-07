"""Bundle manifest schema and validation.

This module provides JSON schema validation for bundle manifests
and utilities for reading/writing manifest files.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from skillmeat.core.artifact import ArtifactType


# Bundle manifest JSON schema (version 1.0)
BUNDLE_MANIFEST_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "SkillMeat Bundle Manifest",
    "description": "Manifest schema for .skillmeat-pack bundle files",
    "type": "object",
    "required": [
        "version",
        "name",
        "description",
        "author",
        "created_at",
        "artifacts",
    ],
    "properties": {
        "version": {
            "type": "string",
            "description": "Manifest format version",
            "enum": ["1.0"],
        },
        "name": {
            "type": "string",
            "description": "Bundle name (identifier)",
            "minLength": 1,
            "maxLength": 100,
            "pattern": "^[a-zA-Z0-9_-]+$",
        },
        "description": {
            "type": "string",
            "description": "Human-readable description",
            "minLength": 1,
            "maxLength": 500,
        },
        "author": {
            "type": "string",
            "description": "Author name or email",
            "minLength": 1,
            "maxLength": 100,
        },
        "created_at": {
            "type": "string",
            "description": "ISO 8601 timestamp",
            "format": "date-time",
        },
        "license": {
            "type": "string",
            "description": "License identifier (SPDX recommended)",
            "default": "MIT",
        },
        "tags": {
            "type": "array",
            "description": "Categorization tags",
            "items": {"type": "string"},
            "uniqueItems": True,
        },
        "homepage": {
            "type": "string",
            "description": "Project homepage URL",
            "format": "uri",
        },
        "repository": {
            "type": "string",
            "description": "Source repository URL",
            "format": "uri",
        },
        "artifacts": {
            "type": "array",
            "description": "List of artifacts in bundle",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": [
                    "type",
                    "name",
                    "version",
                    "scope",
                    "path",
                    "files",
                    "hash",
                ],
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "Artifact type",
                        "enum": ["skill", "command", "agent"],
                    },
                    "name": {
                        "type": "string",
                        "description": "Artifact name",
                        "minLength": 1,
                    },
                    "version": {
                        "type": "string",
                        "description": "Artifact version",
                    },
                    "scope": {
                        "type": "string",
                        "description": "Artifact scope",
                        "enum": ["user", "local"],
                    },
                    "path": {
                        "type": "string",
                        "description": "Path within bundle archive",
                    },
                    "files": {
                        "type": "array",
                        "description": "List of files in artifact",
                        "items": {"type": "string"},
                        "minItems": 1,
                    },
                    "hash": {
                        "type": "string",
                        "description": "SHA-256 hash of artifact",
                        "pattern": "^sha256:[a-f0-9]{64}$",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional artifact metadata",
                        "additionalProperties": {"type": "string"},
                    },
                },
            },
        },
        "dependencies": {
            "type": "array",
            "description": "List of bundle dependencies",
            "items": {"type": "string"},
            "uniqueItems": True,
        },
        "bundle_hash": {
            "type": "string",
            "description": "SHA-256 hash of entire bundle",
            "pattern": "^sha256:[a-f0-9]{64}$",
        },
    },
}


@dataclass
class ValidationError:
    """Represents a single validation error.

    Attributes:
        field: Field path where error occurred (e.g., "artifacts[0].hash")
        message: Human-readable error message
        value: Optional actual value that caused error
    """

    field: str
    message: str
    value: Optional[Any] = None


@dataclass
class ValidationResult:
    """Result of manifest validation.

    Attributes:
        valid: True if manifest is valid
        errors: List of validation errors (empty if valid)
        warnings: List of non-critical warnings
    """

    valid: bool
    errors: List[ValidationError]
    warnings: List[str] = None

    def __post_init__(self):
        """Initialize warnings list if not provided."""
        if self.warnings is None:
            self.warnings = []

    @property
    def error_count(self) -> int:
        """Return number of validation errors."""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Return number of warnings."""
        return len(self.warnings)

    def summary(self) -> str:
        """Generate human-readable summary of validation result."""
        if self.valid:
            if self.warning_count > 0:
                return f"Valid with {self.warning_count} warning(s)"
            return "Valid"

        return f"Invalid: {self.error_count} error(s)"


class ManifestValidator:
    """Validator for bundle manifest JSON.

    Validates manifest structure, field types, and constraints
    according to the bundle manifest schema.
    """

    @staticmethod
    def validate_manifest(manifest_dict: Dict) -> ValidationResult:
        """Validate bundle manifest against schema.

        Performs comprehensive validation including:
        - Required fields presence
        - Field types and formats
        - Value constraints (min/max length, patterns)
        - Artifact structure
        - Hash format validation

        Args:
            manifest_dict: Manifest dictionary to validate

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []

        # Check required top-level fields
        required_fields = [
            "version",
            "name",
            "description",
            "author",
            "created_at",
            "artifacts",
        ]
        for field in required_fields:
            if field not in manifest_dict:
                errors.append(
                    ValidationError(
                        field=field,
                        message=f"Required field '{field}' is missing",
                    )
                )

        # If missing required fields, return early
        if errors:
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        # Validate version
        if manifest_dict["version"] != "1.0":
            errors.append(
                ValidationError(
                    field="version",
                    message=f"Unsupported manifest version: {manifest_dict['version']}. Expected '1.0'",
                    value=manifest_dict["version"],
                )
            )

        # Validate name format
        name = manifest_dict["name"]
        if not isinstance(name, str) or len(name) == 0:
            errors.append(
                ValidationError(
                    field="name",
                    message="Bundle name must be a non-empty string",
                    value=name,
                )
            )
        elif len(name) > 100:
            errors.append(
                ValidationError(
                    field="name",
                    message="Bundle name must be 100 characters or less",
                    value=name,
                )
            )

        # Validate description
        desc = manifest_dict["description"]
        if not isinstance(desc, str) or len(desc) == 0:
            errors.append(
                ValidationError(
                    field="description",
                    message="Description must be a non-empty string",
                    value=desc,
                )
            )

        # Validate author
        author = manifest_dict["author"]
        if not isinstance(author, str) or len(author) == 0:
            errors.append(
                ValidationError(
                    field="author",
                    message="Author must be a non-empty string",
                    value=author,
                )
            )

        # Validate created_at timestamp
        created_at = manifest_dict["created_at"]
        try:
            datetime.fromisoformat(created_at)
        except (ValueError, TypeError) as e:
            errors.append(
                ValidationError(
                    field="created_at",
                    message=f"Invalid ISO 8601 timestamp: {e}",
                    value=created_at,
                )
            )

        # Validate artifacts
        artifacts = manifest_dict.get("artifacts", [])
        if not isinstance(artifacts, list) or len(artifacts) == 0:
            errors.append(
                ValidationError(
                    field="artifacts",
                    message="Bundle must contain at least one artifact",
                    value=artifacts,
                )
            )
        else:
            for idx, artifact in enumerate(artifacts):
                artifact_errors = ManifestValidator._validate_artifact(artifact, idx)
                errors.extend(artifact_errors)

        # Validate bundle_hash format if present
        if "bundle_hash" in manifest_dict:
            bundle_hash = manifest_dict["bundle_hash"]
            if not ManifestValidator._is_valid_sha256_hash(bundle_hash):
                errors.append(
                    ValidationError(
                        field="bundle_hash",
                        message="bundle_hash must be in format 'sha256:...' with 64 hex digits",
                        value=bundle_hash,
                    )
                )

        # Warnings (non-critical)
        if "license" not in manifest_dict:
            warnings.append("No license specified (defaults to MIT)")

        if "tags" not in manifest_dict or len(manifest_dict.get("tags", [])) == 0:
            warnings.append("No tags specified - bundle may be harder to discover")

        valid = len(errors) == 0
        return ValidationResult(valid=valid, errors=errors, warnings=warnings)

    @staticmethod
    def _validate_artifact(artifact: Dict, index: int) -> List[ValidationError]:
        """Validate individual artifact in manifest.

        Args:
            artifact: Artifact dictionary to validate
            index: Index in artifacts array (for error reporting)

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        field_prefix = f"artifacts[{index}]"

        # Check required fields
        required_fields = ["type", "name", "version", "scope", "path", "files", "hash"]
        for field in required_fields:
            if field not in artifact:
                errors.append(
                    ValidationError(
                        field=f"{field_prefix}.{field}",
                        message=f"Required field '{field}' is missing",
                    )
                )

        # If missing required fields, return early
        if errors:
            return errors

        # Validate type
        artifact_type = artifact["type"]
        valid_types = [t.value for t in ArtifactType]
        if artifact_type not in valid_types:
            errors.append(
                ValidationError(
                    field=f"{field_prefix}.type",
                    message=f"Invalid artifact type: {artifact_type}. Must be one of {valid_types}",
                    value=artifact_type,
                )
            )

        # Validate scope
        scope = artifact["scope"]
        if scope not in ("user", "local"):
            errors.append(
                ValidationError(
                    field=f"{field_prefix}.scope",
                    message=f"Invalid scope: {scope}. Must be 'user' or 'local'",
                    value=scope,
                )
            )

        # Validate files array
        files = artifact["files"]
        if not isinstance(files, list) or len(files) == 0:
            errors.append(
                ValidationError(
                    field=f"{field_prefix}.files",
                    message="Artifact must contain at least one file",
                    value=files,
                )
            )

        # Validate hash format
        hash_value = artifact["hash"]
        if not ManifestValidator._is_valid_sha256_hash(hash_value):
            errors.append(
                ValidationError(
                    field=f"{field_prefix}.hash",
                    message="Hash must be in format 'sha256:...' with 64 hex digits",
                    value=hash_value,
                )
            )

        return errors

    @staticmethod
    def _is_valid_sha256_hash(hash_str: str) -> bool:
        """Check if string is a valid SHA-256 hash in format 'sha256:...'

        Args:
            hash_str: Hash string to validate

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(hash_str, str):
            return False

        if not hash_str.startswith("sha256:"):
            return False

        hex_part = hash_str[7:]  # Remove 'sha256:' prefix
        if len(hex_part) != 64:
            return False

        # Check if all characters are valid hex
        try:
            int(hex_part, 16)
            return True
        except ValueError:
            return False


class BundleManifest:
    """Utility for reading and writing bundle manifest files."""

    MANIFEST_FILENAME = "manifest.json"

    @staticmethod
    def read_manifest(manifest_path: Path) -> Dict:
        """Read and parse manifest.json file.

        Args:
            manifest_path: Path to manifest.json file

        Returns:
            Manifest dictionary

        Raises:
            FileNotFoundError: If manifest file doesn't exist
            json.JSONDecodeError: If manifest is not valid JSON
        """
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def write_manifest(manifest_dict: Dict, output_path: Path) -> None:
        """Write manifest dictionary to JSON file.

        Writes with:
        - 2-space indentation for readability
        - Sorted keys for determinism
        - UTF-8 encoding
        - Newline at end of file

        Args:
            manifest_dict: Manifest dictionary to write
            output_path: Path where manifest.json will be written

        Raises:
            PermissionError: If output path is not writable
        """
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                manifest_dict,
                f,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            f.write("\n")  # Newline at end of file

    @staticmethod
    def validate_and_read(manifest_path: Path) -> tuple[Dict, ValidationResult]:
        """Read manifest and validate in one operation.

        Args:
            manifest_path: Path to manifest.json file

        Returns:
            Tuple of (manifest_dict, validation_result)

        Raises:
            FileNotFoundError: If manifest file doesn't exist
            json.JSONDecodeError: If manifest is not valid JSON
        """
        manifest_dict = BundleManifest.read_manifest(manifest_path)
        validation_result = ManifestValidator.validate_manifest(manifest_dict)
        return manifest_dict, validation_result
