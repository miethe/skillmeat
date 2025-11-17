"""SkillMeat official marketplace broker.

This broker connects to the official SkillMeat marketplace API for
discovering, downloading, and publishing artifacts.
"""

import json
import logging
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests
from pydantic import ValidationError

from ..broker import MarketplaceBroker
from ..models import (
    DownloadResult,
    Listing,
    ListingPage,
    ListingQuery,
    PublishRequest,
    PublishResult,
)

logger = logging.getLogger(__name__)

# Default SkillMeat marketplace endpoint
DEFAULT_MARKETPLACE_URL = "https://marketplace.skillmeat.dev/api/v1"


class SkillMeatMarketplaceBroker(MarketplaceBroker):
    """Official SkillMeat marketplace broker.

    Connects to the SkillMeat marketplace API to list, download, and publish
    artifacts. Supports authenticated and anonymous access, with rate limiting
    for public endpoints.

    Authentication:
    - Anonymous: Read-only access with rate limits
    - API Key: Full access with higher rate limits
    - Publisher Key: Required for publishing
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        rate_limit: int = 60,
    ):
        """Initialize SkillMeat marketplace broker.

        Args:
            base_url: Marketplace API base URL (default: official marketplace)
            api_key: Optional API key for authentication
            rate_limit: Maximum API calls per minute (default: 60)
        """
        super().__init__(
            name="SkillMeat",
            base_url=base_url or DEFAULT_MARKETPLACE_URL,
            api_key=api_key,
            rate_limit=rate_limit,
        )

        # Set up session headers
        self._session_headers = {
            "User-Agent": "SkillMeat/1.0",
            "Accept": "application/json",
        }

        if self.api_key:
            self._session_headers["Authorization"] = f"Bearer {self.api_key}"
            logger.info("SkillMeat broker: authenticated with API key")
        else:
            logger.info("SkillMeat broker: anonymous access (read-only)")

    def listings(self, query: Optional[ListingQuery] = None) -> ListingPage:
        """Fetch paginated listing feed from SkillMeat marketplace.

        Args:
            query: Optional query parameters for filtering/sorting

        Returns:
            ListingPage with matching listings

        Raises:
            ValueError: If query parameters are invalid
            ConnectionError: If marketplace is unreachable
            TimeoutError: If request times out
        """
        self._rate_limit_wait()

        # Build query parameters
        params = {}
        if query:
            if query.search:
                params["q"] = query.search
            if query.category:
                params["category"] = query.category
            if query.tags:
                params["tags"] = ",".join(query.tags)
            if query.publisher:
                params["publisher"] = query.publisher
            if query.free_only:
                params["free"] = "true"
            if query.verified_only:
                params["verified"] = "true"
            params["sort"] = query.sort
            params["page"] = query.page
            params["page_size"] = query.page_size
        else:
            params["page"] = 1
            params["page_size"] = 20

        # Make API request
        try:
            url = urljoin(self.base_url, "/listings")
            logger.debug(f"Fetching listings from {url} with params: {params}")

            response = requests.get(
                url, params=params, headers=self._session_headers, timeout=10.0
            )

            response.raise_for_status()
            data = response.json()

            # Parse response
            listings = [Listing(**listing_data) for listing_data in data["listings"]]

            return ListingPage(
                listings=listings,
                total_count=data["total_count"],
                page=data["page"],
                page_size=data["page_size"],
                total_pages=data["total_pages"],
                has_next=data["has_next"],
                has_prev=data["has_prev"],
            )

        except requests.RequestException as e:
            logger.error(f"Failed to fetch listings: {e}")
            raise ConnectionError(f"Failed to connect to SkillMeat marketplace: {e}") from e
        except (KeyError, ValidationError) as e:
            logger.error(f"Invalid response from marketplace: {e}")
            raise ValueError(f"Invalid marketplace response: {e}") from e

    def get_listing(self, listing_id: str) -> Optional[Listing]:
        """Get a specific listing by ID.

        Args:
            listing_id: Listing identifier

        Returns:
            Listing if found, None otherwise
        """
        self._rate_limit_wait()

        try:
            url = urljoin(self.base_url, f"/listings/{listing_id}")
            logger.debug(f"Fetching listing {listing_id} from {url}")

            response = requests.get(
                url, headers=self._session_headers, timeout=10.0
            )

            if response.status_code == 404:
                logger.warning(f"Listing {listing_id} not found")
                return None

            response.raise_for_status()
            data = response.json()

            return Listing(**data)

        except requests.RequestException as e:
            logger.error(f"Failed to get listing {listing_id}: {e}")
            return None
        except ValidationError as e:
            logger.error(f"Invalid listing data for {listing_id}: {e}")
            return None

    def download(
        self, listing_id: str, output_dir: Optional[Path] = None
    ) -> DownloadResult:
        """Download bundle from SkillMeat marketplace.

        Args:
            listing_id: Marketplace listing identifier
            output_dir: Directory to save bundle (default: temp directory)

        Returns:
            DownloadResult with download status and bundle path

        Raises:
            ValueError: If listing_id is invalid
            FileNotFoundError: If listing not found
            PermissionError: If authentication fails
            ConnectionError: If download fails
        """
        self._rate_limit_wait()

        # Get listing metadata
        listing = self.get_listing(listing_id)
        if not listing:
            raise FileNotFoundError(f"Listing {listing_id} not found")

        # Verify signature if present
        verified = self.verify_signature(listing)
        if not verified:
            logger.warning(
                f"Listing {listing_id} signature verification failed - proceeding with caution"
            )

        # Determine output path
        if output_dir is None:
            output_dir = Path(tempfile.gettempdir()) / "skillmeat-downloads"
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate bundle filename
        bundle_filename = f"{listing.name}-{listing.version}.skillmeat-pack"
        bundle_path = output_dir / bundle_filename

        # Download bundle
        try:
            logger.info(f"Downloading bundle from {listing.bundle_url}")

            response = requests.get(
                str(listing.bundle_url),
                headers=self._session_headers,
                stream=True,
                timeout=30.0,
            )

            response.raise_for_status()

            # Save to file
            with open(bundle_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Downloaded bundle to {bundle_path}")

            # Verify bundle integrity
            from skillmeat.core.sharing.validator import BundleValidator

            validator = BundleValidator()
            validation_result = validator.validate(bundle_path)

            if not validation_result.is_valid:
                errors = [str(issue) for issue in validation_result.get_errors()]
                logger.error(f"Bundle validation failed: {errors}")

                return DownloadResult(
                    success=False,
                    bundle_path=None,
                    listing=listing,
                    verified=verified,
                    message="Bundle validation failed",
                    errors=errors,
                )

            return DownloadResult(
                success=True,
                bundle_path=str(bundle_path),
                listing=listing,
                verified=verified,
                message=f"Successfully downloaded {listing.name} v{listing.version}",
                errors=[],
            )

        except requests.RequestException as e:
            logger.error(f"Failed to download bundle: {e}")
            return DownloadResult(
                success=False,
                bundle_path=None,
                listing=listing,
                verified=verified,
                message=f"Download failed: {e}",
                errors=[str(e)],
            )
        except Exception as e:
            logger.error(f"Unexpected error during download: {e}")
            return DownloadResult(
                success=False,
                bundle_path=None,
                listing=listing,
                verified=verified,
                message=f"Unexpected error: {e}",
                errors=[str(e)],
            )

    def publish(self, request: PublishRequest) -> PublishResult:
        """Publish bundle to SkillMeat marketplace.

        Args:
            request: Publish request with bundle and metadata

        Returns:
            PublishResult with publication status

        Raises:
            ValueError: If request is invalid
            FileNotFoundError: If bundle file not found
            PermissionError: If authentication fails
            ConnectionError: If upload fails
        """
        self._rate_limit_wait()

        # Validate request
        bundle_path = Path(request.bundle_path)
        if not bundle_path.exists():
            raise FileNotFoundError(f"Bundle file not found: {bundle_path}")

        if not self.api_key:
            raise PermissionError(
                "API key required for publishing. Set api_key when initializing broker."
            )

        # Sign bundle if requested
        if request.sign_bundle:
            try:
                from skillmeat.core.signing.key_manager import KeyManager
                from skillmeat.core.signing.signer import BundleSigner

                key_manager = KeyManager()
                signer = BundleSigner(key_manager=key_manager)

                # Sign the bundle (modifies in place)
                logger.info(f"Signing bundle {bundle_path}")
                # Note: Actual signing implementation would go here
                # For now, we'll assume the bundle is already signed or signing is handled

            except Exception as e:
                logger.error(f"Failed to sign bundle: {e}")
                return PublishResult(
                    success=False,
                    listing_id=None,
                    listing_url=None,
                    message=f"Failed to sign bundle: {e}",
                    errors=[str(e)],
                )

        # Prepare multipart upload
        try:
            url = urljoin(self.base_url, "/listings")
            logger.info(f"Publishing bundle to {url}")

            # Prepare metadata
            metadata = {
                "name": request.name,
                "description": request.description,
                "category": request.category,
                "version": request.version,
                "license": request.license,
                "tags": json.dumps(request.tags),
                "price": request.price,
            }

            if request.homepage:
                metadata["homepage"] = str(request.homepage)
            if request.repository:
                metadata["repository"] = str(request.repository)

            # Upload bundle
            with open(bundle_path, "rb") as f:
                files = {"bundle": (bundle_path.name, f, "application/zip")}
                response = requests.post(
                    url,
                    data=metadata,
                    files=files,
                    headers=self._session_headers,
                    timeout=60.0,
                )

            response.raise_for_status()
            result_data = response.json()

            logger.info(
                f"Successfully published {request.name} as listing {result_data['listing_id']}"
            )

            return PublishResult(
                success=True,
                listing_id=result_data["listing_id"],
                listing_url=result_data.get("listing_url"),
                message=f"Successfully published {request.name} v{request.version}",
                errors=[],
                warnings=[],
            )

        except requests.RequestException as e:
            logger.error(f"Failed to publish bundle: {e}")

            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", str(e))
                except Exception:
                    error_msg = str(e)
            else:
                error_msg = str(e)

            return PublishResult(
                success=False,
                listing_id=None,
                listing_url=None,
                message=f"Failed to publish: {error_msg}",
                errors=[error_msg],
            )
        except Exception as e:
            logger.error(f"Unexpected error during publish: {e}")
            return PublishResult(
                success=False,
                listing_id=None,
                listing_url=None,
                message=f"Unexpected error: {e}",
                errors=[str(e)],
            )
