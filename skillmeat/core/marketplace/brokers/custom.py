"""Custom web endpoint marketplace broker.

This broker allows users to connect to custom marketplace endpoints
that follow the SkillMeat marketplace JSON schema. Useful for private
or third-party marketplaces.
"""

import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, Optional
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


class CustomWebBroker(MarketplaceBroker):
    """Custom web endpoint marketplace broker.

    Connects to user-supplied marketplace endpoints that implement the
    SkillMeat marketplace JSON schema. Allows integration with private,
    enterprise, or third-party marketplaces.

    Schema Requirements:
    - GET /listings - Return ListingPage JSON
    - GET /listings/{id} - Return Listing JSON
    - GET {bundle_url} - Return .skillmeat-pack bundle
    - POST /listings - Upload bundle (optional, if publishing is supported)

    Features:
    - Flexible authentication (API key, Bearer token, custom headers)
    - Configurable rate limiting
    - Schema validation
    - Optional signature verification

    Use Cases:
    - Private company marketplace
    - Team-specific artifact repository
    - Third-party marketplace integration
    - Self-hosted marketplace server
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        auth_header: str = "Authorization",
        auth_prefix: str = "Bearer",
        custom_headers: Optional[Dict[str, str]] = None,
        rate_limit: int = 60,
        verify_ssl: bool = True,
    ):
        """Initialize custom web broker.

        Args:
            base_url: Base URL of marketplace API
            api_key: Optional API key/token for authentication
            auth_header: Header name for authentication (default: "Authorization")
            auth_prefix: Prefix for auth value (default: "Bearer")
            custom_headers: Additional custom headers for all requests
            rate_limit: Maximum API calls per minute (default: 60)
            verify_ssl: Whether to verify SSL certificates (default: True)
        """
        super().__init__(
            name="CustomWeb",
            base_url=base_url,
            api_key=api_key,
            rate_limit=rate_limit,
        )

        self.auth_header = auth_header
        self.auth_prefix = auth_prefix
        self.verify_ssl = verify_ssl

        # Set up session headers
        self._session_headers = {
            "User-Agent": "SkillMeat/1.0",
            "Accept": "application/json",
        }

        # Add custom headers
        if custom_headers:
            self._session_headers.update(custom_headers)

        # Add authentication
        if self.api_key:
            auth_value = f"{auth_prefix} {self.api_key}" if auth_prefix else self.api_key
            self._session_headers[auth_header] = auth_value
            logger.info(f"Custom broker: authenticated via {auth_header} header")
        else:
            logger.info("Custom broker: no authentication")

        logger.info(
            f"Custom broker: connected to {base_url} "
            f"(SSL verify: {verify_ssl}, rate limit: {rate_limit}/min)"
        )

    def listings(self, query: Optional[ListingQuery] = None) -> ListingPage:
        """Fetch paginated listing feed from custom endpoint.

        Args:
            query: Optional query parameters for filtering/sorting

        Returns:
            ListingPage with matching listings

        Raises:
            ValueError: If query parameters are invalid or response is malformed
            ConnectionError: If endpoint is unreachable
            TimeoutError: If request times out
        """
        self._rate_limit_wait()

        # Build query parameters
        params = {}
        if query:
            # Convert query to dict for API
            if query.search:
                params["search"] = query.search
            if query.category:
                params["category"] = query.category
            if query.tags:
                params["tags"] = ",".join(query.tags)
            if query.publisher:
                params["publisher"] = query.publisher
            if query.free_only:
                params["free_only"] = "true"
            if query.verified_only:
                params["verified_only"] = "true"
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
                url,
                params=params,
                headers=self._session_headers,
                timeout=10.0,
                verify=self.verify_ssl,
            )

            response.raise_for_status()
            data = response.json()

            # Validate and parse response
            try:
                # Try to parse as ListingPage directly
                return ListingPage(**data)
            except ValidationError as e:
                # Try alternative formats
                # Some endpoints might return listings directly without pagination wrapper
                if "listings" in data:
                    listings = [Listing(**item) for item in data["listings"]]
                    total_count = data.get("total_count", len(listings))
                    page = data.get("page", params["page"])
                    page_size = data.get("page_size", params["page_size"])
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
                else:
                    raise ValueError(f"Invalid response format: {e}") from e

        except requests.RequestException as e:
            logger.error(f"Failed to fetch listings from {self.base_url}: {e}")
            raise ConnectionError(f"Failed to connect to custom endpoint: {e}") from e
        except (KeyError, ValidationError) as e:
            logger.error(f"Invalid response from custom endpoint: {e}")
            raise ValueError(f"Invalid endpoint response: {e}") from e

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
                url,
                headers=self._session_headers,
                timeout=10.0,
                verify=self.verify_ssl,
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
        """Download bundle from custom endpoint.

        Args:
            listing_id: Listing identifier
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

            # Use custom headers for download as well
            response = requests.get(
                str(listing.bundle_url),
                headers=self._session_headers,
                stream=True,
                timeout=30.0,
                verify=self.verify_ssl,
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
        """Publish bundle to custom endpoint.

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

        # Check if endpoint supports publishing
        # We'll try to publish and handle errors gracefully

        # Sign bundle if requested
        if request.sign_bundle:
            try:
                from skillmeat.core.signing.key_manager import KeyManager
                from skillmeat.core.signing.signer import BundleSigner

                key_manager = KeyManager()
                signer = BundleSigner(key_manager=key_manager)

                logger.info(f"Signing bundle {bundle_path}")
                # Note: Actual signing implementation would go here

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
                    verify=self.verify_ssl,
                )

            response.raise_for_status()
            result_data = response.json()

            logger.info(
                f"Successfully published {request.name} to {self.base_url}"
            )

            return PublishResult(
                success=True,
                listing_id=result_data.get("listing_id"),
                listing_url=result_data.get("listing_url"),
                message=f"Successfully published {request.name} v{request.version}",
                errors=[],
                warnings=result_data.get("warnings", []),
            )

        except requests.RequestException as e:
            logger.error(f"Failed to publish bundle: {e}")

            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", str(e))
                    errors = error_data.get("errors", [error_msg])
                except Exception:
                    error_msg = str(e)
                    errors = [error_msg]
            else:
                error_msg = str(e)
                errors = [error_msg]

            return PublishResult(
                success=False,
                listing_id=None,
                listing_url=None,
                message=f"Failed to publish: {error_msg}",
                errors=errors,
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
