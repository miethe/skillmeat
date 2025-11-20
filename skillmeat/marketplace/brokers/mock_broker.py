"""Local mock marketplace broker for development and testing.

Provides in-memory sample listings with realistic data to enable local development
without requiring external marketplace services.
"""

import base64
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from skillmeat.core.sharing.bundle import Bundle

from ..broker import (
    DownloadError,
    MarketplaceBroker,
    MarketplaceBrokerError,
    PublishError,
    RateLimitConfig,
    ValidationError,
)
from ..models import MarketplaceListing, PublishResult

logger = logging.getLogger(__name__)


class MockLocalBroker(MarketplaceBroker):
    """Local mock broker for development without external dependencies.

    Provides in-memory sample listings covering various artifact types,
    licenses, and metadata. Useful for local development and testing
    marketplace UI without requiring network access.
    """

    def __init__(
        self,
        name: str = "mock-local",
        endpoint: str = "local://mock",
        rate_limit: Optional[RateLimitConfig] = None,
        cache_ttl: int = 300,
        key_manager=None,
    ):
        """Initialize mock local broker.

        Args:
            name: Broker name
            endpoint: Mock endpoint (always local://)
            rate_limit: Rate limiting configuration (unused for mock)
            cache_ttl: Cache TTL (unused for mock)
            key_manager: Key manager (unused for mock)
        """
        super().__init__(
            name=name,
            endpoint=endpoint,
            rate_limit=rate_limit,
            cache_ttl=cache_ttl,
            key_manager=key_manager,
        )

        # Initialize in-memory listings
        self._listings = self._create_sample_listings()
        self._publish_counter = 0

    def _create_sample_listings(self) -> List[MarketplaceListing]:
        """Create sample marketplace listings.

        Returns:
            List of MarketplaceListing objects with realistic data
        """
        base_time = datetime.now()

        return [
            # Skills
            MarketplaceListing(
                listing_id="mock-001",
                name="Python Code Analyzer",
                publisher="DevTools Inc",
                license="MIT",
                artifact_count=1,
                price=0,
                signature=base64.b64encode(b"mock-signature-001").decode(),
                source_url="local://mock/listings/mock-001",
                bundle_url="local://mock/bundles/mock-001.skillmeat-pack",
                tags=["python", "code-analysis", "linting"],
                created_at=base_time,
                description="Comprehensive Python code analysis and quality checking skill with support for modern Python features.",
                version="2.1.0",
                homepage="https://github.com/example/python-analyzer",
                repository="https://github.com/example/python-analyzer",
                downloads=15234,
                rating=4.8,
            ),
            MarketplaceListing(
                listing_id="mock-002",
                name="React Component Builder",
                publisher="Frontend Masters",
                license="Apache-2.0",
                artifact_count=1,
                price=0,
                signature=base64.b64encode(b"mock-signature-002").decode(),
                source_url="local://mock/listings/mock-002",
                bundle_url="local://mock/bundles/mock-002.skillmeat-pack",
                tags=["react", "typescript", "components", "ui"],
                created_at=base_time,
                description="Build React components with TypeScript, hooks, and best practices. Includes accessibility checks.",
                version="1.5.2",
                homepage="https://github.com/example/react-builder",
                repository="https://github.com/example/react-builder",
                downloads=8932,
                rating=4.6,
            ),
            MarketplaceListing(
                listing_id="mock-003",
                name="Database Schema Designer",
                publisher="DataEngineers",
                license="MIT",
                artifact_count=1,
                price=0,
                signature=base64.b64encode(b"mock-signature-003").decode(),
                source_url="local://mock/listings/mock-003",
                bundle_url="local://mock/bundles/mock-003.skillmeat-pack",
                tags=["database", "sql", "schema", "design"],
                created_at=base_time,
                description="Design normalized database schemas with support for PostgreSQL, MySQL, and SQLite.",
                version="3.0.1",
                homepage="https://github.com/example/db-schema",
                repository="https://github.com/example/db-schema",
                downloads=12456,
                rating=4.9,
            ),
            MarketplaceListing(
                listing_id="mock-004",
                name="API Documentation Generator",
                publisher="DocTeam",
                license="BSD-3-Clause",
                artifact_count=1,
                price=0,
                signature=base64.b64encode(b"mock-signature-004").decode(),
                source_url="local://mock/listings/mock-004",
                bundle_url="local://mock/bundles/mock-004.skillmeat-pack",
                tags=["documentation", "api", "openapi", "swagger"],
                created_at=base_time,
                description="Generate comprehensive API documentation from code with OpenAPI/Swagger support.",
                version="1.8.0",
                downloads=6721,
                rating=4.5,
            ),
            # Commands
            MarketplaceListing(
                listing_id="mock-005",
                name="Git Flow Automator",
                publisher="DevOps Pro",
                license="MIT",
                artifact_count=2,
                price=0,
                signature=base64.b64encode(b"mock-signature-005").decode(),
                source_url="local://mock/listings/mock-005",
                bundle_url="local://mock/bundles/mock-005.skillmeat-pack",
                tags=["git", "workflow", "automation", "commands"],
                created_at=base_time,
                description="Bundle of Git workflow commands for feature branches, releases, and hotfixes.",
                version="2.3.0",
                homepage="https://github.com/example/git-flow",
                repository="https://github.com/example/git-flow",
                downloads=19823,
                rating=4.7,
            ),
            MarketplaceListing(
                listing_id="mock-006",
                name="Docker Quick Commands",
                publisher="Container Experts",
                license="Apache-2.0",
                artifact_count=3,
                price=0,
                signature=base64.b64encode(b"mock-signature-006").decode(),
                source_url="local://mock/listings/mock-006",
                bundle_url="local://mock/bundles/mock-006.skillmeat-pack",
                tags=["docker", "containers", "devops", "commands"],
                created_at=base_time,
                description="Essential Docker commands for container management, cleanup, and debugging.",
                version="1.2.1",
                downloads=11234,
                rating=4.4,
            ),
            # Agents
            MarketplaceListing(
                listing_id="mock-007",
                name="Code Review Assistant",
                publisher="AI Solutions",
                license="MIT",
                artifact_count=1,
                price=0,
                signature=base64.b64encode(b"mock-signature-007").decode(),
                source_url="local://mock/listings/mock-007",
                bundle_url="local://mock/bundles/mock-007.skillmeat-pack",
                tags=["code-review", "quality", "agent", "automation"],
                created_at=base_time,
                description="AI agent for automated code reviews with style checking, security analysis, and best practice enforcement.",
                version="1.0.0",
                homepage="https://github.com/example/review-agent",
                repository="https://github.com/example/review-agent",
                downloads=5432,
                rating=4.3,
            ),
            MarketplaceListing(
                listing_id="mock-008",
                name="Test Case Generator",
                publisher="TestPro",
                license="MIT",
                artifact_count=1,
                price=0,
                signature=base64.b64encode(b"mock-signature-008").decode(),
                source_url="local://mock/listings/mock-008",
                bundle_url="local://mock/bundles/mock-008.skillmeat-pack",
                tags=["testing", "unit-tests", "agent", "automation"],
                created_at=base_time,
                description="Generates comprehensive test cases for Python, JavaScript, and TypeScript codebases.",
                version="2.0.3",
                downloads=9876,
                rating=4.6,
            ),
            # Multi-artifact bundles
            MarketplaceListing(
                listing_id="mock-009",
                name="Full Stack Development Kit",
                publisher="WebDev Studio",
                license="MIT",
                artifact_count=5,
                price=0,
                signature=base64.b64encode(b"mock-signature-009").decode(),
                source_url="local://mock/listings/mock-009",
                bundle_url="local://mock/bundles/mock-009.skillmeat-pack",
                tags=["fullstack", "react", "node", "bundle", "productivity"],
                created_at=base_time,
                description="Complete development kit with skills for React frontend, Node.js backend, API design, and testing.",
                version="1.5.0",
                homepage="https://github.com/example/fullstack-kit",
                repository="https://github.com/example/fullstack-kit",
                downloads=23451,
                rating=4.9,
            ),
            MarketplaceListing(
                listing_id="mock-010",
                name="DevOps Essentials",
                publisher="CloudOps Team",
                license="Apache-2.0",
                artifact_count=7,
                price=0,
                signature=base64.b64encode(b"mock-signature-010").decode(),
                source_url="local://mock/listings/mock-010",
                bundle_url="local://mock/bundles/mock-010.skillmeat-pack",
                tags=["devops", "ci-cd", "kubernetes", "docker", "bundle"],
                created_at=base_time,
                description="Essential DevOps tools including Docker commands, Kubernetes skills, and CI/CD automation agents.",
                version="3.1.2",
                downloads=18765,
                rating=4.8,
            ),
            # Different licenses
            MarketplaceListing(
                listing_id="mock-011",
                name="Enterprise Security Scanner",
                publisher="SecOps Inc",
                license="GPL-3.0",
                artifact_count=2,
                price=0,
                signature=base64.b64encode(b"mock-signature-011").decode(),
                source_url="local://mock/listings/mock-011",
                bundle_url="local://mock/bundles/mock-011.skillmeat-pack",
                tags=["security", "scanning", "vulnerability", "compliance"],
                created_at=base_time,
                description="Security vulnerability scanner with compliance checking for enterprise applications.",
                version="4.2.0",
                downloads=7654,
                rating=4.7,
            ),
            MarketplaceListing(
                listing_id="mock-012",
                name="Machine Learning Helper",
                publisher="ML Research Lab",
                license="BSD-2-Clause",
                artifact_count=3,
                price=0,
                signature=base64.b64encode(b"mock-signature-012").decode(),
                source_url="local://mock/listings/mock-012",
                bundle_url="local://mock/bundles/mock-012.skillmeat-pack",
                tags=["machine-learning", "data-science", "python", "tensorflow"],
                created_at=base_time,
                description="ML workflow automation with data preprocessing, model training, and evaluation tools.",
                version="1.3.5",
                homepage="https://github.com/example/ml-helper",
                repository="https://github.com/example/ml-helper",
                downloads=14321,
                rating=4.5,
            ),
            # More recent additions
            MarketplaceListing(
                listing_id="mock-013",
                name="Markdown Documentation Suite",
                publisher="DocWriters",
                license="MIT",
                artifact_count=4,
                price=0,
                signature=base64.b64encode(b"mock-signature-013").decode(),
                source_url="local://mock/listings/mock-013",
                bundle_url="local://mock/bundles/mock-013.skillmeat-pack",
                tags=["documentation", "markdown", "writing", "productivity"],
                created_at=base_time,
                description="Complete documentation toolkit with README generators, changelog builders, and API doc formatters.",
                version="2.2.0",
                downloads=10987,
                rating=4.6,
            ),
            MarketplaceListing(
                listing_id="mock-014",
                name="REST API Testing Bundle",
                publisher="QA Automation",
                license="MIT",
                artifact_count=3,
                price=0,
                signature=base64.b64encode(b"mock-signature-014").decode(),
                source_url="local://mock/listings/mock-014",
                bundle_url="local://mock/bundles/mock-014.skillmeat-pack",
                tags=["testing", "api", "rest", "automation", "qa"],
                created_at=base_time,
                description="Automated REST API testing with request builders, response validators, and load testing.",
                version="1.7.1",
                downloads=8234,
                rating=4.4,
            ),
            MarketplaceListing(
                listing_id="mock-015",
                name="Refactoring Assistant",
                publisher="CodeQuality Pro",
                license="MIT",
                artifact_count=1,
                price=0,
                signature=base64.b64encode(b"mock-signature-015").decode(),
                source_url="local://mock/listings/mock-015",
                bundle_url="local://mock/bundles/mock-015.skillmeat-pack",
                tags=["refactoring", "code-quality", "patterns", "best-practices"],
                created_at=base_time,
                description="Intelligent refactoring suggestions with design pattern recommendations and code smell detection.",
                version="1.1.0",
                downloads=6543,
                rating=4.8,
            ),
        ]

    def listings(
        self,
        filters: Optional[Dict] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[MarketplaceListing]:
        """Fetch paginated marketplace listings.

        Args:
            filters: Optional filters:
                - tags: List[str] - Filter by tags
                - license: str - Filter by license
                - price_max: int - Maximum price in cents
                - publisher: str - Filter by publisher
                - query: str - Search query
            page: Page number (1-indexed)
            page_size: Number of results per page (max 100)

        Returns:
            List of MarketplaceListing objects

        Raises:
            MarketplaceBrokerError: If listing fetch fails
        """
        filters = filters or {}

        # Validate pagination
        if page < 1:
            raise MarketplaceBrokerError(f"Invalid page number: {page}")

        if page_size < 1 or page_size > 100:
            raise MarketplaceBrokerError(
                f"Invalid page_size: {page_size} (must be 1-100)"
            )

        # Apply filters
        filtered_listings = self._listings.copy()

        # Filter by tags
        if "tags" in filters and filters["tags"]:
            tag_list = filters["tags"]
            if isinstance(tag_list, str):
                tag_list = [tag_list]
            filtered_listings = [
                listing
                for listing in filtered_listings
                if any(tag in listing.tags for tag in tag_list)
            ]

        # Filter by license
        if "license" in filters and filters["license"]:
            filtered_listings = [
                listing
                for listing in filtered_listings
                if listing.license == filters["license"]
            ]

        # Filter by price
        if "price_max" in filters:
            max_price = filters["price_max"]
            filtered_listings = [
                listing for listing in filtered_listings if listing.price <= max_price
            ]

        # Filter by publisher
        if "publisher" in filters and filters["publisher"]:
            publisher = filters["publisher"].lower()
            filtered_listings = [
                listing
                for listing in filtered_listings
                if publisher in listing.publisher.lower()
            ]

        # Search query
        if "query" in filters and filters["query"]:
            query = filters["query"].lower()
            filtered_listings = [
                listing
                for listing in filtered_listings
                if (
                    query in listing.name.lower()
                    or (listing.description and query in listing.description.lower())
                    or any(query in tag.lower() for tag in listing.tags)
                )
            ]

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_listings = filtered_listings[start_idx:end_idx]

        total_pages = (len(filtered_listings) + page_size - 1) // page_size

        logger.info(
            f"Fetched {len(paginated_listings)} mock listings "
            f"(page {page}/{total_pages}, {len(filtered_listings)} total after filters)"
        )

        return paginated_listings

    def get_listing(self, listing_id: str) -> Optional[MarketplaceListing]:
        """Get single listing by ID.

        Args:
            listing_id: Listing ID to fetch

        Returns:
            MarketplaceListing or None if not found
        """
        for listing in self._listings:
            if listing.listing_id == listing_id:
                return listing
        return None

    def download(self, listing_id: str, output_dir: Optional[Path] = None) -> Path:
        """Download bundle from marketplace to temp location.

        For mock broker, this creates a minimal mock bundle file.

        Args:
            listing_id: Listing ID to download
            output_dir: Optional output directory (uses temp dir if None)

        Returns:
            Path to downloaded bundle file

        Raises:
            DownloadError: If download fails
            ValidationError: If bundle validation fails
        """
        if not listing_id:
            raise DownloadError("listing_id cannot be empty")

        # Get listing details
        listing = self.get_listing(listing_id)
        if not listing:
            raise DownloadError(f"Listing not found: {listing_id}")

        # Create output directory
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp(prefix="skillmeat-mock-"))
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        # Create mock bundle file
        bundle_path = output_dir / f"{listing_id}.skillmeat-pack"

        try:
            # Write minimal mock bundle content
            mock_content = f"""Mock bundle for: {listing.name}
Publisher: {listing.publisher}
Version: {listing.version}
Artifacts: {listing.artifact_count}

This is a mock bundle for development purposes.
It does not contain actual artifact data.
"""
            bundle_path.write_text(mock_content)

            logger.info(f"Created mock bundle at {bundle_path}")
            return bundle_path

        except Exception as e:
            raise DownloadError(f"Failed to create mock bundle: {e}") from e

    def publish(
        self,
        bundle: Bundle,
        metadata: Optional[Dict] = None,
    ) -> PublishResult:
        """Publish bundle to marketplace.

        For mock broker, this simulates a successful publish operation.

        Args:
            bundle: Bundle to publish (must have bundle_path set)
            metadata: Optional additional metadata

        Returns:
            PublishResult with submission details

        Raises:
            PublishError: If publishing fails
            ValidationError: If bundle validation fails
        """
        metadata = metadata or {}

        # Validate bundle
        if not bundle.bundle_path:
            raise PublishError("Bundle must have bundle_path set")

        if not bundle.bundle_path.exists():
            raise PublishError(f"Bundle file not found: {bundle.bundle_path}")

        # Generate mock submission ID
        self._publish_counter += 1
        submission_id = f"mock-submission-{self._publish_counter:04d}"

        # Create publish result
        result = PublishResult(
            submission_id=submission_id,
            status="approved",
            message=f"Mock bundle '{bundle.metadata.name}' published successfully",
            listing_url=f"local://mock/listings/{submission_id}",
            submitted_at=datetime.now(),
            reviewed_at=datetime.now(),
        )

        logger.info(f"Mock publish successful: {submission_id}")
        return result
