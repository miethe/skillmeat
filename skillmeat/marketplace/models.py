"""Data models for marketplace integration.

Defines the core data structures used for marketplace listings,
publish results, and broker interactions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class MarketplaceListing:
    """Represents a marketplace listing for an artifact bundle.

    Attributes:
        listing_id: Unique identifier for the listing
        name: Human-readable name of the bundle
        publisher: Publisher name or organization
        license: License identifier (e.g., "MIT", "Apache-2.0")
        artifact_count: Number of artifacts in the bundle
        price: Price in cents (0 for free)
        signature: Base64-encoded Ed25519 signature
        source_url: URL to listing details page
        bundle_url: URL to download the bundle file
        tags: List of tags for categorization
        created_at: Timestamp when listing was created
        description: Optional detailed description
        version: Optional version string
        homepage: Optional URL to project homepage
        repository: Optional URL to source repository
        downloads: Optional download count
        rating: Optional rating (0.0-5.0)
    """

    listing_id: str
    name: str
    publisher: str
    license: str
    artifact_count: int
    price: int  # 0 for free, otherwise price in cents
    signature: str  # BASE64-encoded
    source_url: str
    bundle_url: str
    tags: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    description: Optional[str] = None
    version: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    downloads: Optional[int] = None
    rating: Optional[float] = None

    def __post_init__(self):
        """Validate listing data."""
        if not self.listing_id:
            raise ValueError("listing_id cannot be empty")

        if not self.name:
            raise ValueError("name cannot be empty")

        if not self.publisher:
            raise ValueError("publisher cannot be empty")

        if self.price < 0:
            raise ValueError(f"price cannot be negative: {self.price}")

        if self.artifact_count < 0:
            raise ValueError(
                f"artifact_count cannot be negative: {self.artifact_count}"
            )

        if self.rating is not None and not (0.0 <= self.rating <= 5.0):
            raise ValueError(f"rating must be between 0.0 and 5.0: {self.rating}")

    @property
    def is_free(self) -> bool:
        """Return True if listing is free."""
        return self.price == 0

    @property
    def is_signed(self) -> bool:
        """Return True if listing has a signature."""
        return bool(self.signature)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        result = {
            "listing_id": self.listing_id,
            "name": self.name,
            "publisher": self.publisher,
            "license": self.license,
            "artifact_count": self.artifact_count,
            "price": self.price,
            "signature": self.signature,
            "source_url": self.source_url,
            "bundle_url": self.bundle_url,
            "tags": self.tags,
        }

        if self.created_at:
            result["created_at"] = self.created_at.isoformat()

        if self.description:
            result["description"] = self.description

        if self.version:
            result["version"] = self.version

        if self.homepage:
            result["homepage"] = self.homepage

        if self.repository:
            result["repository"] = self.repository

        if self.downloads is not None:
            result["downloads"] = self.downloads

        if self.rating is not None:
            result["rating"] = self.rating

        return result

    @classmethod
    def from_dict(cls, data: Dict) -> "MarketplaceListing":
        """Create from dictionary (JSON deserialization).

        Args:
            data: Dictionary with listing data

        Returns:
            MarketplaceListing instance

        Raises:
            ValueError: If required fields are missing
        """
        # Parse created_at if present
        created_at = None
        if "created_at" in data:
            if isinstance(data["created_at"], str):
                created_at = datetime.fromisoformat(data["created_at"])
            elif isinstance(data["created_at"], datetime):
                created_at = data["created_at"]

        return cls(
            listing_id=data["listing_id"],
            name=data["name"],
            publisher=data["publisher"],
            license=data.get("license", "Unknown"),
            artifact_count=data.get("artifact_count", 0),
            price=data.get("price", 0),
            signature=data.get("signature", ""),
            source_url=data["source_url"],
            bundle_url=data["bundle_url"],
            tags=data.get("tags", []),
            created_at=created_at,
            description=data.get("description"),
            version=data.get("version"),
            homepage=data.get("homepage"),
            repository=data.get("repository"),
            downloads=data.get("downloads"),
            rating=data.get("rating"),
        )


@dataclass
class PublishResult:
    """Result of publishing a bundle to a marketplace.

    Attributes:
        submission_id: Unique identifier for the submission
        status: Status of the submission ("pending", "approved", "rejected")
        message: Human-readable status message
        listing_url: Optional URL to view the listing (if approved)
        errors: List of error messages if submission failed
        warnings: List of warning messages
        submitted_at: Timestamp when submission was made
        reviewed_at: Timestamp when submission was reviewed (if applicable)
        reviewer_notes: Optional notes from reviewer
    """

    submission_id: str
    status: str  # "pending", "approved", "rejected"
    message: str
    listing_url: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    reviewer_notes: Optional[str] = None

    def __post_init__(self):
        """Validate publish result data."""
        valid_statuses = {"pending", "approved", "rejected"}
        if self.status not in valid_statuses:
            raise ValueError(
                f"Invalid status '{self.status}'. Must be one of {valid_statuses}"
            )

        if not self.submission_id:
            raise ValueError("submission_id cannot be empty")

    @property
    def is_pending(self) -> bool:
        """Return True if submission is pending review."""
        return self.status == "pending"

    @property
    def is_approved(self) -> bool:
        """Return True if submission was approved."""
        return self.status == "approved"

    @property
    def is_rejected(self) -> bool:
        """Return True if submission was rejected."""
        return self.status == "rejected"

    @property
    def has_errors(self) -> bool:
        """Return True if there are errors."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Return True if there are warnings."""
        return len(self.warnings) > 0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        result = {
            "submission_id": self.submission_id,
            "status": self.status,
            "message": self.message,
            "errors": self.errors,
            "warnings": self.warnings,
        }

        if self.listing_url:
            result["listing_url"] = self.listing_url

        if self.submitted_at:
            result["submitted_at"] = self.submitted_at.isoformat()

        if self.reviewed_at:
            result["reviewed_at"] = self.reviewed_at.isoformat()

        if self.reviewer_notes:
            result["reviewer_notes"] = self.reviewer_notes

        return result

    @classmethod
    def from_dict(cls, data: Dict) -> "PublishResult":
        """Create from dictionary (JSON deserialization).

        Args:
            data: Dictionary with publish result data

        Returns:
            PublishResult instance

        Raises:
            ValueError: If required fields are missing
        """
        # Parse timestamps if present
        submitted_at = None
        if "submitted_at" in data:
            if isinstance(data["submitted_at"], str):
                submitted_at = datetime.fromisoformat(data["submitted_at"])
            elif isinstance(data["submitted_at"], datetime):
                submitted_at = data["submitted_at"]

        reviewed_at = None
        if "reviewed_at" in data:
            if isinstance(data["reviewed_at"], str):
                reviewed_at = datetime.fromisoformat(data["reviewed_at"])
            elif isinstance(data["reviewed_at"], datetime):
                reviewed_at = data["reviewed_at"]

        return cls(
            submission_id=data["submission_id"],
            status=data["status"],
            message=data["message"],
            listing_url=data.get("listing_url"),
            errors=data.get("errors", []),
            warnings=data.get("warnings", []),
            submitted_at=submitted_at,
            reviewed_at=reviewed_at,
            reviewer_notes=data.get("reviewer_notes"),
        )
