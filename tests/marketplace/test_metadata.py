"""Unit tests for marketplace metadata validation."""

import pytest

from skillmeat.marketplace.metadata import (
    PublishMetadata,
    PublisherMetadata,
    ValidationError,
)


class TestPublisherMetadata:
    """Test PublisherMetadata validation."""

    def test_valid_publisher(self):
        """Test creating valid publisher metadata."""
        publisher = PublisherMetadata(
            name="John Doe",
            email="john@example.com",
            homepage="https://example.com",
        )

        assert publisher.name == "John Doe"
        assert publisher.email == "john@example.com"
        assert publisher.homepage == "https://example.com"
        assert publisher.verified is False

    def test_empty_name(self):
        """Test that empty name raises error."""
        with pytest.raises(ValidationError, match="Publisher name cannot be empty"):
            PublisherMetadata(name="", email="john@example.com")

    def test_name_too_long(self):
        """Test that name too long raises error."""
        long_name = "x" * 101
        with pytest.raises(ValidationError, match="Publisher name too long"):
            PublisherMetadata(name=long_name, email="john@example.com")

    def test_empty_email(self):
        """Test that empty email raises error."""
        with pytest.raises(ValidationError, match="Publisher email cannot be empty"):
            PublisherMetadata(name="John Doe", email="")

    def test_invalid_email(self):
        """Test that invalid email raises error."""
        with pytest.raises(ValidationError, match="Invalid email address"):
            PublisherMetadata(name="John Doe", email="not-an-email")

    def test_invalid_homepage_url(self):
        """Test that invalid homepage URL raises error."""
        with pytest.raises(ValidationError, match="must be HTTP/HTTPS URL"):
            PublisherMetadata(
                name="John Doe",
                email="john@example.com",
                homepage="ftp://example.com",
            )

    def test_to_dict(self):
        """Test converting to dictionary."""
        publisher = PublisherMetadata(
            name="John Doe",
            email="john@example.com",
            homepage="https://example.com",
            verified=True,
        )

        data = publisher.to_dict()

        assert data["name"] == "John Doe"
        assert data["email"] == "john@example.com"
        assert data["homepage"] == "https://example.com"
        assert data["verified"] is True

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "homepage": "https://example.com",
            "verified": True,
        }

        publisher = PublisherMetadata.from_dict(data)

        assert publisher.name == "John Doe"
        assert publisher.email == "john@example.com"
        assert publisher.homepage == "https://example.com"
        assert publisher.verified is True


class TestPublishMetadata:
    """Test PublishMetadata validation."""

    def create_valid_publisher(self):
        """Helper to create valid publisher metadata."""
        return PublisherMetadata(
            name="John Doe",
            email="john@example.com",
        )

    def test_valid_metadata(self):
        """Test creating valid publish metadata."""
        publisher = self.create_valid_publisher()

        metadata = PublishMetadata(
            title="My Bundle",
            description="A" * 100,  # Min 100 chars
            tags=["productivity", "automation"],
            license="MIT",
            publisher=publisher,
            price=0,
        )

        assert metadata.title == "My Bundle"
        assert len(metadata.description) == 100
        assert metadata.tags == ["productivity", "automation"]
        assert metadata.license == "MIT"
        assert metadata.publisher == publisher
        assert metadata.price == 0

    def test_title_too_short(self):
        """Test that title too short raises error."""
        publisher = self.create_valid_publisher()

        with pytest.raises(ValidationError, match="Title too short"):
            PublishMetadata(
                title="Ab",  # Less than 5 chars
                description="A" * 100,
                tags=["productivity"],
                license="MIT",
                publisher=publisher,
            )

    def test_title_too_long(self):
        """Test that title too long raises error."""
        publisher = self.create_valid_publisher()

        with pytest.raises(ValidationError, match="Title too long"):
            PublishMetadata(
                title="A" * 101,  # More than 100 chars
                description="A" * 100,
                tags=["productivity"],
                license="MIT",
                publisher=publisher,
            )

    def test_description_too_short(self):
        """Test that description too short raises error."""
        publisher = self.create_valid_publisher()

        with pytest.raises(ValidationError, match="Description too short"):
            PublishMetadata(
                title="My Bundle",
                description="Too short",  # Less than 100 chars
                tags=["productivity"],
                license="MIT",
                publisher=publisher,
            )

    def test_description_too_long(self):
        """Test that description too long raises error."""
        publisher = self.create_valid_publisher()

        with pytest.raises(ValidationError, match="Description too long"):
            PublishMetadata(
                title="My Bundle",
                description="A" * 5001,  # More than 5000 chars
                tags=["productivity"],
                license="MIT",
                publisher=publisher,
            )

    def test_no_tags(self):
        """Test that no tags raises error."""
        publisher = self.create_valid_publisher()

        with pytest.raises(ValidationError, match="At least one tag is required"):
            PublishMetadata(
                title="My Bundle",
                description="A" * 100,
                tags=[],
                license="MIT",
                publisher=publisher,
            )

    def test_too_many_tags(self):
        """Test that too many tags raises error."""
        publisher = self.create_valid_publisher()

        with pytest.raises(ValidationError, match="Too many tags"):
            PublishMetadata(
                title="My Bundle",
                description="A" * 100,
                tags=["tag" + str(i) for i in range(11)],  # More than 10
                license="MIT",
                publisher=publisher,
            )

    def test_invalid_tags(self):
        """Test that invalid tags raise error."""
        publisher = self.create_valid_publisher()

        with pytest.raises(ValidationError, match="Invalid tags"):
            PublishMetadata(
                title="My Bundle",
                description="A" * 100,
                tags=["productivity", "invalid-tag"],
                license="MIT",
                publisher=publisher,
            )

    def test_duplicate_tags(self):
        """Test that duplicate tags raise error."""
        publisher = self.create_valid_publisher()

        with pytest.raises(ValidationError, match="Duplicate tags"):
            PublishMetadata(
                title="My Bundle",
                description="A" * 100,
                tags=["productivity", "productivity"],
                license="MIT",
                publisher=publisher,
            )

    def test_empty_license(self):
        """Test that empty license raises error."""
        publisher = self.create_valid_publisher()

        with pytest.raises(ValidationError, match="License identifier is required"):
            PublishMetadata(
                title="My Bundle",
                description="A" * 100,
                tags=["productivity"],
                license="",
                publisher=publisher,
            )

    def test_negative_price(self):
        """Test that negative price raises error."""
        publisher = self.create_valid_publisher()

        with pytest.raises(ValidationError, match="Price cannot be negative"):
            PublishMetadata(
                title="My Bundle",
                description="A" * 100,
                tags=["productivity"],
                license="MIT",
                publisher=publisher,
                price=-100,
            )

    def test_invalid_homepage_url(self):
        """Test that invalid homepage URL raises error."""
        publisher = self.create_valid_publisher()

        with pytest.raises(ValidationError, match="must be HTTP/HTTPS URL"):
            PublishMetadata(
                title="My Bundle",
                description="A" * 100,
                tags=["productivity"],
                license="MIT",
                publisher=publisher,
                homepage="ftp://example.com",
            )

    def test_invalid_repository_url(self):
        """Test that invalid repository URL raises error."""
        publisher = self.create_valid_publisher()

        with pytest.raises(ValidationError, match="must be valid URL"):
            PublishMetadata(
                title="My Bundle",
                description="A" * 100,
                tags=["productivity"],
                license="MIT",
                publisher=publisher,
                repository="not-a-url",
            )

    def test_too_many_screenshots(self):
        """Test that too many screenshots raise error."""
        publisher = self.create_valid_publisher()

        with pytest.raises(ValidationError, match="Too many screenshots"):
            PublishMetadata(
                title="My Bundle",
                description="A" * 100,
                tags=["productivity"],
                license="MIT",
                publisher=publisher,
                screenshots=[
                    f"https://example.com/{i}.png" for i in range(6)
                ],  # More than 5
            )

    def test_to_dict(self):
        """Test converting to dictionary."""
        publisher = self.create_valid_publisher()

        metadata = PublishMetadata(
            title="My Bundle",
            description="A" * 100,
            tags=["productivity", "automation"],
            license="MIT",
            publisher=publisher,
            homepage="https://example.com",
            repository="https://github.com/example/repo",
            price=999,
        )

        data = metadata.to_dict()

        assert data["title"] == "My Bundle"
        assert len(data["description"]) == 100
        assert data["tags"] == ["productivity", "automation"]
        assert data["license"] == "MIT"
        assert "publisher" in data
        assert data["homepage"] == "https://example.com"
        assert data["repository"] == "https://github.com/example/repo"
        assert data["price"] == 999

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "title": "My Bundle",
            "description": "A" * 100,
            "tags": ["productivity", "automation"],
            "license": "MIT",
            "publisher": {
                "name": "John Doe",
                "email": "john@example.com",
            },
            "homepage": "https://example.com",
            "repository": "https://github.com/example/repo",
            "price": 999,
        }

        metadata = PublishMetadata.from_dict(data)

        assert metadata.title == "My Bundle"
        assert len(metadata.description) == 100
        assert metadata.tags == ["productivity", "automation"]
        assert metadata.license == "MIT"
        assert metadata.publisher.name == "John Doe"
        assert metadata.homepage == "https://example.com"
        assert metadata.repository == "https://github.com/example/repo"
        assert metadata.price == 999
