"""Publisher metadata validation for marketplace publishing.

This module provides validation for publisher metadata before bundle
submission to marketplaces.
"""

import logging
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl, field_validator

from skillmeat.core.marketplace.models import ArtifactCategory

logger = logging.getLogger(__name__)


class PublisherMetadata(BaseModel):
    """Metadata required for marketplace publication.

    Attributes:
        name: Listing name (3-100 characters)
        description: Description (10-5000 characters)
        category: Artifact category
        version: Version string (semver format)
        license: License identifier
        tags: List of tags (1-10 tags, each 2-30 characters)
        homepage: Optional homepage URL
        repository: Optional repository URL
        sign_bundle: Whether to sign the bundle
    """

    name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Listing name",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Listing description",
    )
    category: ArtifactCategory = Field(..., description="Artifact category")
    version: str = Field(..., description="Version string")
    license: str = Field(..., description="License identifier")
    tags: List[str] = Field(
        default_factory=list,
        min_length=0,
        max_length=10,
        description="Tags for discovery",
    )
    homepage: Optional[HttpUrl] = Field(None, description="Homepage URL")
    repository: Optional[HttpUrl] = Field(None, description="Repository URL")
    sign_bundle: bool = Field(True, description="Sign bundle before publishing")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate listing name.

        Args:
            v: Name to validate

        Returns:
            Validated name

        Raises:
            ValueError: If name is invalid
        """
        # Check length
        if len(v) < 3:
            raise ValueError("Name must be at least 3 characters")
        if len(v) > 100:
            raise ValueError("Name must be at most 100 characters")

        # Check characters (alphanumeric, space, dash, underscore)
        if not re.match(r"^[a-zA-Z0-9\s\-_]+$", v):
            raise ValueError(
                "Name can only contain letters, numbers, spaces, dashes, and underscores"
            )

        # Cannot start or end with whitespace
        if v != v.strip():
            raise ValueError("Name cannot start or end with whitespace")

        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate description.

        Args:
            v: Description to validate

        Returns:
            Validated description

        Raises:
            ValueError: If description is invalid
        """
        # Check length
        if len(v) < 10:
            raise ValueError("Description must be at least 10 characters")
        if len(v) > 5000:
            raise ValueError("Description must be at most 5000 characters")

        # Cannot be only whitespace
        if not v.strip():
            raise ValueError("Description cannot be only whitespace")

        return v

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate version string (semver).

        Args:
            v: Version to validate

        Returns:
            Validated version

        Raises:
            ValueError: If version is invalid
        """
        # Semver pattern: MAJOR.MINOR.PATCH with optional prerelease/build
        semver_pattern = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"

        if not re.match(semver_pattern, v):
            raise ValueError(
                f"Version '{v}' is not valid semver format. "
                "Expected: MAJOR.MINOR.PATCH (e.g., 1.0.0)"
            )

        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate tags list.

        Args:
            v: Tags to validate

        Returns:
            Validated tags

        Raises:
            ValueError: If tags are invalid
        """
        if len(v) > 10:
            raise ValueError("Maximum 10 tags allowed")

        # Validate each tag
        for tag in v:
            if len(tag) < 2:
                raise ValueError(f"Tag '{tag}' must be at least 2 characters")
            if len(tag) > 30:
                raise ValueError(f"Tag '{tag}' must be at most 30 characters")

            # Only alphanumeric, dash, underscore
            if not re.match(r"^[a-zA-Z0-9\-_]+$", tag):
                raise ValueError(
                    f"Tag '{tag}' can only contain letters, numbers, dashes, and underscores"
                )

        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("Duplicate tags not allowed")

        return v

    @field_validator("homepage", "repository")
    @classmethod
    def validate_url(cls, v: Optional[HttpUrl]) -> Optional[HttpUrl]:
        """Validate URL fields.

        Args:
            v: URL to validate

        Returns:
            Validated URL

        Raises:
            ValueError: If URL is invalid
        """
        if v is None:
            return v

        # Pydantic HttpUrl already validates basic URL format
        # Additional checks can be added here if needed

        return v


class MetadataValidationError(Exception):
    """Raised when metadata validation fails."""

    pass


class MetadataValidator:
    """Validates publisher metadata for marketplace submissions.

    Provides comprehensive validation including:
    - Required field validation
    - Format validation (semver, URLs)
    - Length constraints
    - Character restrictions
    - Business logic validation
    """

    # Minimum required fields
    REQUIRED_FIELDS = ["name", "description", "category", "version", "license"]

    # Valid categories (from ArtifactCategory enum)
    VALID_CATEGORIES = [cat.value for cat in ArtifactCategory]

    # Recommended tag categories
    RECOMMENDED_TAGS = [
        "productivity",
        "automation",
        "development",
        "documentation",
        "data-analysis",
        "testing",
        "deployment",
        "security",
        "monitoring",
        "cli",
        "ui",
        "api",
        "database",
        "cloud",
        "ai",
        "ml",
    ]

    def __init__(self):
        """Initialize metadata validator."""
        pass

    def validate_metadata(self, metadata: Dict) -> PublisherMetadata:
        """Validate publisher metadata.

        Args:
            metadata: Metadata dictionary to validate

        Returns:
            Validated PublisherMetadata instance

        Raises:
            MetadataValidationError: If validation fails
        """
        # Check required fields
        missing_fields = []
        for field in self.REQUIRED_FIELDS:
            if field not in metadata or not metadata[field]:
                missing_fields.append(field)

        if missing_fields:
            raise MetadataValidationError(
                f"Missing required fields: {', '.join(missing_fields)}"
            )

        # Validate using Pydantic model (raises ValidationError)
        try:
            validated_metadata = PublisherMetadata(**metadata)
        except Exception as e:
            raise MetadataValidationError(f"Validation failed: {e}")

        return validated_metadata

    def validate_metadata_with_suggestions(
        self, metadata: Dict
    ) -> tuple[PublisherMetadata, List[str]]:
        """Validate metadata and provide suggestions.

        Args:
            metadata: Metadata dictionary to validate

        Returns:
            Tuple of (validated metadata, list of suggestions)

        Raises:
            MetadataValidationError: If validation fails
        """
        validated = self.validate_metadata(metadata)
        suggestions = []

        # Check if homepage is provided
        if not validated.homepage:
            suggestions.append(
                "Consider adding a homepage URL for better discoverability"
            )

        # Check if repository is provided
        if not validated.repository:
            suggestions.append(
                "Consider adding a repository URL to help users review the code"
            )

        # Check if tags are provided
        if not validated.tags:
            suggestions.append(
                f"Consider adding tags for better discoverability. "
                f"Recommended: {', '.join(self.RECOMMENDED_TAGS[:5])}"
            )
        elif len(validated.tags) < 3:
            suggestions.append(
                f"Consider adding more tags (you have {len(validated.tags)}, "
                f"recommended: 3-5)"
            )

        # Check description length
        if len(validated.description) < 50:
            suggestions.append(
                "Consider adding more detail to the description (current: "
                f"{len(validated.description)} chars, recommended: 50+ chars)"
            )

        # Check if category is appropriate
        if validated.category == ArtifactCategory.BUNDLE:
            suggestions.append(
                "Bundle category is for collections of artifacts. "
                "Consider using a more specific category if this is a single artifact."
            )

        return validated, suggestions

    def check_name_availability(self, name: str, broker_name: str) -> bool:
        """Check if a name is available on a marketplace.

        Args:
            name: Name to check
            broker_name: Marketplace broker name

        Returns:
            True if available, False if taken

        Note:
            This is a placeholder. Actual implementation would query
            the marketplace API to check name availability.
        """
        # TODO: Implement actual marketplace API call
        logger.warning(
            f"Name availability check not implemented for broker '{broker_name}'"
        )
        return True

    def suggest_tags(self, name: str, description: str) -> List[str]:
        """Suggest tags based on name and description.

        Args:
            name: Artifact name
            description: Artifact description

        Returns:
            List of suggested tags
        """
        suggested = []

        # Combine name and description for keyword search
        text = (name + " " + description).lower()

        # Check for keywords
        keyword_map = {
            "productivity": ["productivity", "workflow", "efficiency"],
            "automation": ["automation", "automate", "automated"],
            "development": ["development", "dev", "developer"],
            "documentation": ["documentation", "docs", "document"],
            "testing": ["testing", "test", "qa"],
            "deployment": ["deployment", "deploy", "release"],
            "security": ["security", "secure", "auth"],
            "monitoring": ["monitoring", "monitor", "metrics"],
            "cli": ["cli", "command-line", "terminal"],
            "api": ["api", "rest", "graphql"],
            "database": ["database", "db", "sql"],
            "cloud": ["cloud", "aws", "azure", "gcp"],
            "ai": ["ai", "artificial intelligence", "machine learning"],
        }

        for tag, keywords in keyword_map.items():
            if any(keyword in text for keyword in keywords):
                suggested.append(tag)

        # Limit to top 5 suggestions
        return suggested[:5]

    def validate_version_increment(
        self, new_version: str, current_version: Optional[str]
    ) -> bool:
        """Validate that new version is a proper increment.

        Args:
            new_version: New version string
            current_version: Current version string (None if first version)

        Returns:
            True if valid increment, False otherwise
        """
        if current_version is None:
            # First version, any valid semver is OK
            return True

        # Parse versions
        def parse_semver(v: str) -> tuple[int, int, int]:
            """Parse semver string into (major, minor, patch)."""
            parts = v.split("-")[0].split("+")[0]  # Remove prerelease/build
            major, minor, patch = parts.split(".")
            return (int(major), int(minor), int(patch))

        try:
            new_parts = parse_semver(new_version)
            current_parts = parse_semver(current_version)

            # Check if new version is greater
            return new_parts > current_parts

        except (ValueError, IndexError):
            # Invalid version format
            return False

    def sanitize_metadata(self, metadata: Dict) -> Dict:
        """Sanitize metadata by removing/fixing problematic content.

        Args:
            metadata: Metadata dictionary

        Returns:
            Sanitized metadata dictionary
        """
        sanitized = metadata.copy()

        # Trim whitespace from string fields
        for field in ["name", "description", "license"]:
            if field in sanitized and isinstance(sanitized[field], str):
                sanitized[field] = sanitized[field].strip()

        # Remove empty tags
        if "tags" in sanitized and isinstance(sanitized["tags"], list):
            sanitized["tags"] = [
                tag.strip() for tag in sanitized["tags"] if tag.strip()
            ]

        # Ensure URLs are strings if provided
        for field in ["homepage", "repository"]:
            if field in sanitized and sanitized[field] is not None:
                sanitized[field] = str(sanitized[field])

        return sanitized

    def get_validation_summary(self, metadata: PublisherMetadata) -> str:
        """Get human-readable validation summary.

        Args:
            metadata: Validated metadata

        Returns:
            Summary string
        """
        lines = [
            "Metadata Validation Summary:",
            f"  Name: {metadata.name}",
            f"  Description: {len(metadata.description)} characters",
            f"  Category: {metadata.category}",
            f"  Version: {metadata.version}",
            f"  License: {metadata.license}",
            f"  Tags: {len(metadata.tags)} tags",
        ]

        if metadata.homepage:
            lines.append(f"  Homepage: {metadata.homepage}")

        if metadata.repository:
            lines.append(f"  Repository: {metadata.repository}")

        lines.append(f"  Sign Bundle: {'Yes' if metadata.sign_bundle else 'No'}")

        return "\n".join(lines)
