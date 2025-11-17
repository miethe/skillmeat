"""Publishing metadata schemas for SkillMeat marketplace.

Defines the data structures for publisher information and publish metadata,
with comprehensive validation rules for marketplace submissions.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class ValidationError(Exception):
    """Raised when metadata validation fails."""

    pass


@dataclass
class PublisherMetadata:
    """Publisher information for marketplace submissions.

    Attributes:
        name: Display name for the publisher
        email: Contact email address
        homepage: Optional publisher homepage URL
        verified: Whether the publisher is verified (set by marketplace)
    """

    name: str
    email: str
    homepage: Optional[str] = None
    verified: bool = False

    def __post_init__(self):
        """Validate publisher metadata."""
        if not self.name or not self.name.strip():
            raise ValidationError("Publisher name cannot be empty")

        if len(self.name) > 100:
            raise ValidationError(
                f"Publisher name too long ({len(self.name)} chars, max 100)"
            )

        if not self.email or not self.email.strip():
            raise ValidationError("Publisher email cannot be empty")

        # Basic email validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, self.email):
            raise ValidationError(f"Invalid email address: {self.email}")

        # Validate homepage URL if present
        if self.homepage:
            if not self.homepage.startswith(("http://", "https://")):
                raise ValidationError(
                    f"Publisher homepage must be HTTP/HTTPS URL: {self.homepage}"
                )

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        result = {
            "name": self.name,
            "email": self.email,
            "verified": self.verified,
        }

        if self.homepage:
            result["homepage"] = self.homepage

        return result

    @classmethod
    def from_dict(cls, data: Dict) -> "PublisherMetadata":
        """Create from dictionary (JSON deserialization).

        Args:
            data: Dictionary with publisher data

        Returns:
            PublisherMetadata instance

        Raises:
            ValidationError: If required fields are missing
        """
        return cls(
            name=data["name"],
            email=data["email"],
            homepage=data.get("homepage"),
            verified=data.get("verified", False),
        )


@dataclass
class PublishMetadata:
    """Comprehensive metadata for marketplace bundle publishing.

    Attributes:
        title: Bundle title (required, 5-100 chars)
        description: Detailed description (required, 100-5000 chars)
        tags: List of tags for categorization (required, 1-10 tags)
        license: SPDX license identifier (required)
        homepage: Optional bundle homepage URL
        repository: Optional source repository URL
        documentation: Optional documentation URL
        screenshots: Optional list of screenshot URLs
        publisher: Publisher information (required)
        price: Price in cents (0 = free, >0 = paid)
    """

    title: str
    description: str
    tags: List[str]
    license: str
    publisher: PublisherMetadata
    homepage: Optional[str] = None
    repository: Optional[str] = None
    documentation: Optional[str] = None
    screenshots: List[str] = field(default_factory=list)
    price: int = 0

    # Allowed tags (marketplace-specific)
    ALLOWED_TAGS = {
        "productivity",
        "documentation",
        "development",
        "testing",
        "data-analysis",
        "automation",
        "ai-ml",
        "web-dev",
        "backend",
        "frontend",
        "database",
        "security",
        "devops",
        "cloud",
        "api",
        "cli",
        "education",
        "research",
        "creative",
        "business",
    }

    def __post_init__(self):
        """Validate publish metadata."""
        self.validate()

    def validate(self):
        """Validate all metadata fields.

        Raises:
            ValidationError: If validation fails with detailed error message
        """
        errors = []

        # Validate title
        if not self.title or not self.title.strip():
            errors.append("Title cannot be empty")
        elif len(self.title) < 5:
            errors.append(f"Title too short ({len(self.title)} chars, min 5)")
        elif len(self.title) > 100:
            errors.append(f"Title too long ({len(self.title)} chars, max 100)")

        # Validate description
        if not self.description or not self.description.strip():
            errors.append("Description cannot be empty")
        elif len(self.description) < 100:
            errors.append(
                f"Description too short ({len(self.description)} chars, min 100)"
            )
        elif len(self.description) > 5000:
            errors.append(
                f"Description too long ({len(self.description)} chars, max 5000)"
            )

        # Validate tags
        if not self.tags:
            errors.append("At least one tag is required")
        elif len(self.tags) > 10:
            errors.append(f"Too many tags ({len(self.tags)}, max 10)")
        else:
            # Check for invalid tags
            invalid_tags = [tag for tag in self.tags if tag not in self.ALLOWED_TAGS]
            if invalid_tags:
                errors.append(
                    f"Invalid tags: {', '.join(invalid_tags)}. "
                    f"Allowed tags: {', '.join(sorted(self.ALLOWED_TAGS))}"
                )

            # Check for duplicate tags
            if len(self.tags) != len(set(self.tags)):
                errors.append("Duplicate tags found")

        # Validate license
        if not self.license or not self.license.strip():
            errors.append("License identifier is required")

        # Validate price
        if self.price < 0:
            errors.append(f"Price cannot be negative: {self.price}")

        # Validate URLs if present
        if self.homepage and not self.homepage.startswith(("http://", "https://")):
            errors.append(f"Homepage must be HTTP/HTTPS URL: {self.homepage}")

        if self.repository and not self.repository.startswith(
            ("http://", "https://", "git://")
        ):
            errors.append(f"Repository must be valid URL: {self.repository}")

        if self.documentation and not self.documentation.startswith(
            ("http://", "https://")
        ):
            errors.append(f"Documentation must be HTTP/HTTPS URL: {self.documentation}")

        # Validate screenshots
        if self.screenshots:
            if len(self.screenshots) > 5:
                errors.append(f"Too many screenshots ({len(self.screenshots)}, max 5)")

            for i, screenshot in enumerate(self.screenshots):
                if not screenshot.startswith(("http://", "https://")):
                    errors.append(
                        f"Screenshot {i+1} must be HTTP/HTTPS URL: {screenshot}"
                    )

        # Validate publisher
        # Publisher validation happens in its own __post_init__

        # Raise validation error if any issues found
        if errors:
            raise ValidationError(
                "Metadata validation failed:\n  - " + "\n  - ".join(errors)
            )

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        result = {
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "license": self.license,
            "publisher": self.publisher.to_dict(),
            "price": self.price,
        }

        if self.homepage:
            result["homepage"] = self.homepage

        if self.repository:
            result["repository"] = self.repository

        if self.documentation:
            result["documentation"] = self.documentation

        if self.screenshots:
            result["screenshots"] = self.screenshots

        return result

    @classmethod
    def from_dict(cls, data: Dict) -> "PublishMetadata":
        """Create from dictionary (JSON deserialization).

        Args:
            data: Dictionary with metadata

        Returns:
            PublishMetadata instance

        Raises:
            ValidationError: If required fields are missing or invalid
        """
        publisher_data = data.get("publisher")
        if not publisher_data:
            raise ValidationError("Publisher information is required")

        publisher = PublisherMetadata.from_dict(publisher_data)

        return cls(
            title=data["title"],
            description=data["description"],
            tags=data.get("tags", []),
            license=data["license"],
            publisher=publisher,
            homepage=data.get("homepage"),
            repository=data.get("repository"),
            documentation=data.get("documentation"),
            screenshots=data.get("screenshots", []),
            price=data.get("price", 0),
        )
