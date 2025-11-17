"""Claude Hub marketplace broker.

This broker connects to public Claude artifact catalogs (Claude Hub)
for discovering and downloading community-contributed artifacts.
"""

import json
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests
from pydantic import HttpUrl, ValidationError

from ..broker import MarketplaceBroker
from ..models import (
    ArtifactCategory,
    DownloadResult,
    Listing,
    ListingPage,
    ListingQuery,
    PublishRequest,
    PublishResult,
    PublisherInfo,
)

logger = logging.getLogger(__name__)

# Default Claude Hub endpoint (public catalog)
DEFAULT_CLAUDEHUB_URL = "https://claudehub.dev/api"


class ClaudeHubBroker(MarketplaceBroker):
    """Claude Hub marketplace broker.

    Connects to public Claude Hub catalogs for browsing and downloading
    community-contributed artifacts. Claude Hub is a read-only catalog
    hosted by the community.

    Features:
    - Read-only access (no authentication required)
    - Public catalog of Skills, Commands, and Agents
    - Community contributions
    - GitHub-backed artifact sources

    Limitations:
    - No publishing support (use GitHub + submission process)
    - Limited search capabilities
    - Best-effort availability
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        rate_limit: int = 30,
    ):
        """Initialize Claude Hub broker.

        Args:
            base_url: Claude Hub API base URL (default: public catalog)
            rate_limit: Maximum API calls per minute (default: 30, lower for public API)
        """
        super().__init__(
            name="ClaudeHub",
            base_url=base_url or DEFAULT_CLAUDEHUB_URL,
            api_key=None,  # No authentication for public catalog
            rate_limit=rate_limit,
        )

        # Set up session headers
        self._session_headers = {
            "User-Agent": "SkillMeat/1.0",
            "Accept": "application/json",
        }

        logger.info("ClaudeHub broker: connected to public catalog (read-only)")

    def listings(self, query: Optional[ListingQuery] = None) -> ListingPage:
        """Fetch paginated listing feed from Claude Hub.

        Args:
            query: Optional query parameters for filtering/sorting

        Returns:
            ListingPage with matching listings

        Raises:
            ValueError: If query parameters are invalid
            ConnectionError: If Claude Hub is unreachable
            TimeoutError: If request times out
        """
        self._rate_limit_wait()

        # Build query parameters
        params = {}
        if query:
            if query.search:
                params["search"] = query.search
            if query.category:
                params["type"] = query.category  # Claude Hub uses "type" instead of "category"
            if query.tags:
                params["tags"] = ",".join(query.tags)
            params["page"] = query.page
            params["limit"] = query.page_size
        else:
            params["page"] = 1
            params["limit"] = 20

        # Make API request
        try:
            url = urljoin(self.base_url, "/catalog")
            logger.debug(f"Fetching listings from {url} with params: {params}")

            response = requests.get(
                url, params=params, headers=self._session_headers, timeout=10.0
            )

            response.raise_for_status()
            data = response.json()

            # Transform Claude Hub response to our format
            listings = [
                self._transform_claudehub_item(item) for item in data.get("items", [])
            ]

            # Calculate pagination
            total_count = data.get("total", len(listings))
            page = params["page"]
            page_size = params["limit"]
            total_pages = (total_count + page_size - 1) // page_size

            return ListingPage(
                listings=listings,
                total_count=total_count,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            )

        except requests.RequestException as e:
            logger.error(f"Failed to fetch listings from Claude Hub: {e}")
            raise ConnectionError(f"Failed to connect to Claude Hub: {e}") from e
        except (KeyError, ValidationError) as e:
            logger.error(f"Invalid response from Claude Hub: {e}")
            raise ValueError(f"Invalid Claude Hub response: {e}") from e

    def _transform_claudehub_item(self, item: dict) -> Listing:
        """Transform Claude Hub item to Listing format.

        Args:
            item: Claude Hub catalog item

        Returns:
            Listing object
        """
        # Map Claude Hub fields to our schema
        listing_id = item.get("id", item.get("slug", "unknown"))
        name = item.get("name", "Unnamed")
        description = item.get("description", "No description available")

        # Map type to category
        item_type = item.get("type", "skill").lower()
        try:
            category = ArtifactCategory(item_type)
        except ValueError:
            category = ArtifactCategory.SKILL

        version = item.get("version", "latest")
        license_str = item.get("license", "Unknown")
        tags = item.get("tags", [])

        # Publisher info
        publisher_name = item.get("author", {}).get("name", "Unknown")
        publisher_email = item.get("author", {}).get("email")
        publisher_website = item.get("author", {}).get("website")

        publisher = PublisherInfo(
            name=publisher_name,
            email=publisher_email,
            website=publisher_website if publisher_website else None,
            verified=False,  # Claude Hub doesn't verify publishers
            key_fingerprint=None,  # No signature support
        )

        # Timestamps
        created_at_str = item.get("created_at", datetime.utcnow().isoformat())
        updated_at_str = item.get("updated_at", created_at_str)

        try:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
        except Exception:
            created_at = datetime.utcnow()
            updated_at = created_at

        # URLs
        source_url = item.get("url", f"{self.base_url}/catalog/{listing_id}")
        bundle_url = item.get("download_url", item.get("github_url", source_url))

        # Repository and homepage
        repository = item.get("repository", item.get("github_url"))
        homepage = item.get("homepage", repository)

        downloads = item.get("downloads", 0)

        return Listing(
            listing_id=listing_id,
            name=name,
            description=description,
            category=category,
            version=version,
            publisher=publisher,
            license=license_str,
            tags=tags,
            artifact_count=1,  # Claude Hub items are single artifacts
            created_at=created_at,
            updated_at=updated_at,
            downloads=downloads,
            price=0.0,  # All Claude Hub items are free
            signature=None,  # No signature support
            source_url=HttpUrl(source_url),
            bundle_url=HttpUrl(bundle_url),
            homepage=HttpUrl(homepage) if homepage else None,
            repository=HttpUrl(repository) if repository else None,
            metadata=item.get("metadata", {}),
        )

    def get_listing(self, listing_id: str) -> Optional[Listing]:
        """Get a specific listing by ID.

        Args:
            listing_id: Listing identifier (slug or ID)

        Returns:
            Listing if found, None otherwise
        """
        self._rate_limit_wait()

        try:
            url = urljoin(self.base_url, f"/catalog/{listing_id}")
            logger.debug(f"Fetching listing {listing_id} from {url}")

            response = requests.get(url, headers=self._session_headers, timeout=10.0)

            if response.status_code == 404:
                logger.warning(f"Listing {listing_id} not found on Claude Hub")
                return None

            response.raise_for_status()
            item = response.json()

            return self._transform_claudehub_item(item)

        except requests.RequestException as e:
            logger.error(f"Failed to get listing {listing_id}: {e}")
            return None
        except ValidationError as e:
            logger.error(f"Invalid listing data for {listing_id}: {e}")
            return None

    def download(
        self, listing_id: str, output_dir: Optional[Path] = None
    ) -> DownloadResult:
        """Download artifact from Claude Hub.

        Note: Claude Hub items are typically GitHub repositories or direct files,
        not .skillmeat-pack bundles. This method will download and package them.

        Args:
            listing_id: Claude Hub listing identifier
            output_dir: Directory to save artifact (default: temp directory)

        Returns:
            DownloadResult with download status and artifact path

        Raises:
            ValueError: If listing_id is invalid
            FileNotFoundError: If listing not found
            ConnectionError: If download fails
        """
        self._rate_limit_wait()

        # Get listing metadata
        listing = self.get_listing(listing_id)
        if not listing:
            raise FileNotFoundError(f"Listing {listing_id} not found on Claude Hub")

        # Determine output path
        if output_dir is None:
            output_dir = Path(tempfile.gettempdir()) / "skillmeat-downloads"
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        # Download from bundle_url
        try:
            logger.info(f"Downloading artifact from {listing.bundle_url}")

            # Check if it's a GitHub URL (needs special handling)
            if "github.com" in str(listing.bundle_url):
                return self._download_from_github(listing, output_dir)

            # Direct download
            response = requests.get(
                str(listing.bundle_url),
                headers=self._session_headers,
                stream=True,
                timeout=30.0,
            )

            response.raise_for_status()

            # Determine filename
            filename = f"{listing.name}-{listing.version}.zip"
            artifact_path = output_dir / filename

            # Save to file
            with open(artifact_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Downloaded artifact to {artifact_path}")

            return DownloadResult(
                success=True,
                bundle_path=str(artifact_path),
                listing=listing,
                verified=False,  # Claude Hub has no signatures
                message=f"Successfully downloaded {listing.name} v{listing.version}",
                errors=[],
            )

        except requests.RequestException as e:
            logger.error(f"Failed to download artifact: {e}")
            return DownloadResult(
                success=False,
                bundle_path=None,
                listing=listing,
                verified=False,
                message=f"Download failed: {e}",
                errors=[str(e)],
            )
        except Exception as e:
            logger.error(f"Unexpected error during download: {e}")
            return DownloadResult(
                success=False,
                bundle_path=None,
                listing=listing,
                verified=False,
                message=f"Unexpected error: {e}",
                errors=[str(e)],
            )

    def _download_from_github(self, listing: Listing, output_dir: Path) -> DownloadResult:
        """Download artifact from GitHub repository.

        Args:
            listing: Listing with GitHub URL
            output_dir: Output directory

        Returns:
            DownloadResult
        """
        # For GitHub URLs, we'll use a simple approach:
        # Download the repository as a ZIP archive
        github_url = str(listing.bundle_url)

        # Convert to archive download URL if needed
        if "/tree/" in github_url or "/blob/" in github_url:
            # Extract repo and branch
            parts = github_url.split("/")
            repo_owner = parts[3]
            repo_name = parts[4]
            branch = parts[6] if len(parts) > 6 else "main"

            archive_url = f"https://github.com/{repo_owner}/{repo_name}/archive/refs/heads/{branch}.zip"
        else:
            # Assume it's already a download URL or repo URL
            archive_url = github_url.replace("github.com", "github.com") + "/archive/refs/heads/main.zip"

        try:
            logger.info(f"Downloading GitHub repository from {archive_url}")

            response = requests.get(archive_url, timeout=30.0)
            response.raise_for_status()

            filename = f"{listing.name}-{listing.version}-github.zip"
            artifact_path = output_dir / filename

            with open(artifact_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Downloaded GitHub artifact to {artifact_path}")

            return DownloadResult(
                success=True,
                bundle_path=str(artifact_path),
                listing=listing,
                verified=False,
                message=f"Successfully downloaded {listing.name} from GitHub",
                errors=[],
            )

        except Exception as e:
            logger.error(f"Failed to download from GitHub: {e}")
            return DownloadResult(
                success=False,
                bundle_path=None,
                listing=listing,
                verified=False,
                message=f"GitHub download failed: {e}",
                errors=[str(e)],
            )

    def publish(self, request: PublishRequest) -> PublishResult:
        """Publish artifact to Claude Hub.

        Note: Claude Hub does not support direct publishing via API.
        Users must submit their artifacts via GitHub and the submission process.

        Args:
            request: Publish request

        Returns:
            PublishResult indicating that publishing is not supported

        Raises:
            NotImplementedError: Always (publishing not supported)
        """
        logger.warning("Claude Hub does not support direct publishing via API")

        return PublishResult(
            success=False,
            listing_id=None,
            listing_url=None,
            message=(
                "Claude Hub does not support direct publishing. "
                "Please submit your artifact via GitHub: https://claudehub.dev/submit"
            ),
            errors=["Publishing not supported by Claude Hub"],
            warnings=[
                "To publish to Claude Hub, create a GitHub repository and submit it via claudehub.dev/submit"
            ],
        )
