"""S3 vault connector for AWS S3 and S3-compatible storage.

Stores bundles in S3 buckets with metadata for team sharing.
Supports AWS S3, MinIO, DigitalOcean Spaces, and other S3-compatible services.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from skillmeat.core.sharing.bundle import BundleMetadata
from skillmeat.core.auth.storage import get_storage_backend

from .base import (
    ProgressCallback,
    VaultBundleMetadata,
    VaultConnector,
    VaultAuthError,
    VaultConnectionError,
    VaultError,
    VaultNotFoundError,
)

logger = logging.getLogger(__name__)


class S3VaultConnector(VaultConnector):
    """S3 storage vault connector.

    Stores bundles in an S3 bucket with this structure:

    bucket/
        prefix/
            bundles/
                bundle-name-v1.0.0.skillmeat-pack
                bundle-name-v1.1.0.skillmeat-pack
            metadata/
                bundle-name-v1.0.0.json
                bundle-name-v1.1.0.json
            index.json

    Configuration:
        bucket: str - S3 bucket name (required)
        region: str - AWS region (default: "us-east-1")
        prefix: str - Key prefix for bundles (default: "")
        endpoint_url: str - Custom S3 endpoint for S3-compatible services (optional)
        access_key_id: str - AWS access key ID (optional, uses env/credentials)
        secret_access_key: str - AWS secret access key (optional, uses env/credentials)
        use_ssl: bool - Use SSL for connections (default: True)

    Credentials can be provided via:
    1. Configuration (stored securely in keychain)
    2. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    3. AWS credentials file (~/.aws/credentials)
    4. IAM role (when running on EC2/ECS)
    """

    METADATA_FILENAME = "index.json"
    BUNDLES_DIR = "bundles"
    METADATA_DIR = "metadata"

    def __init__(
        self,
        vault_id: str,
        config: Dict[str, Any],
        read_only: bool = False,
    ):
        """Initialize S3 vault connector.

        Args:
            vault_id: Unique identifier for this vault
            config: Configuration dict with S3 settings
            read_only: If True, prevent write operations

        Raises:
            ValueError: If config is invalid
            ImportError: If boto3 is not installed
        """
        super().__init__(vault_id, config, read_only)

        if "bucket" not in config:
            raise ValueError("S3 vault config must contain 'bucket'")

        # Import boto3
        try:
            import boto3
            from botocore.exceptions import (
                BotoCoreError,
                ClientError,
                NoCredentialsError,
            )

            self.boto3 = boto3
            self.BotoCoreError = BotoCoreError
            self.ClientError = ClientError
            self.NoCredentialsError = NoCredentialsError
        except ImportError:
            raise ImportError(
                "boto3 is required for S3 vault. Install with: pip install boto3"
            )

        self.bucket = config["bucket"]
        self.region = config.get("region", "us-east-1")
        self.prefix = config.get("prefix", "").rstrip("/")
        self.endpoint_url = config.get("endpoint_url")
        self.use_ssl = config.get("use_ssl", True)

        # S3 client (initialized during authentication)
        self.s3_client = None

        # Credential storage
        self._storage = get_storage_backend()

        logger.info(f"S3 vault initialized for bucket: {self.bucket}")

    def authenticate(self) -> bool:
        """Authenticate with S3.

        Creates S3 client and verifies bucket access.

        Returns:
            True if authentication successful

        Raises:
            VaultAuthError: If authentication fails
            VaultConnectionError: If S3 is unreachable
        """
        try:
            # Get credentials
            cred_id = f"s3-vault:{self.vault_id}"
            access_key = None
            secret_key = None

            # Try to load from secure storage
            try:
                cred_data = self._storage.retrieve(cred_id)
                if cred_data:
                    creds = json.loads(cred_data)
                    access_key = creds.get("access_key_id")
                    secret_key = creds.get("secret_access_key")
                    logger.debug("Using stored S3 credentials")
            except Exception as e:
                logger.debug(f"No stored credentials found: {e}")

            # Fallback to config (not recommended, but supported)
            if not access_key:
                access_key = self.config.get("access_key_id")
            if not secret_key:
                secret_key = self.config.get("secret_access_key")

            # Create S3 client
            client_kwargs = {
                "region_name": self.region,
                "use_ssl": self.use_ssl,
            }

            if self.endpoint_url:
                client_kwargs["endpoint_url"] = self.endpoint_url

            if access_key and secret_key:
                client_kwargs["aws_access_key_id"] = access_key
                client_kwargs["aws_secret_access_key"] = secret_key

            self.s3_client = self.boto3.client("s3", **client_kwargs)

            # Verify bucket access
            try:
                self.s3_client.head_bucket(Bucket=self.bucket)
            except self.ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                if error_code == "404":
                    raise VaultConnectionError(f"S3 bucket not found: {self.bucket}")
                elif error_code == "403":
                    raise VaultAuthError(
                        f"Access denied to S3 bucket: {self.bucket}. "
                        f"Check credentials and permissions."
                    )
                raise

            # Test write permission (if not read-only)
            if not self.read_only:
                test_key = self._get_key(".test")
                try:
                    self.s3_client.put_object(
                        Bucket=self.bucket,
                        Key=test_key,
                        Body=b"test",
                    )
                    self.s3_client.delete_object(
                        Bucket=self.bucket,
                        Key=test_key,
                    )
                except self.ClientError as e:
                    raise VaultAuthError(f"No write permission on S3 bucket: {e}")

            self._authenticated = True
            logger.info(f"Authenticated with S3 vault: {self.bucket}")
            return True

        except self.NoCredentialsError:
            raise VaultAuthError(
                "No AWS credentials found. "
                "Provide credentials via config, environment, or AWS credentials file."
            )
        except (VaultAuthError, VaultConnectionError):
            raise
        except Exception as e:
            raise VaultError(f"Failed to authenticate with S3 vault: {e}")

    def push(
        self,
        bundle_path: Path,
        bundle_metadata: BundleMetadata,
        bundle_hash: str,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        """Upload bundle to S3.

        Args:
            bundle_path: Path to .skillmeat-pack file
            bundle_metadata: Bundle metadata from manifest
            bundle_hash: SHA-256 hash of bundle
            progress_callback: Optional callback for upload progress

        Returns:
            Bundle ID (S3 key)

        Raises:
            VaultError: If upload fails
            VaultPermissionError: If read-only mode enabled
            FileNotFoundError: If bundle_path doesn't exist
        """
        self._check_authenticated()
        self._check_write_permission()
        self._validate_bundle_path(bundle_path)

        try:
            # Generate bundle ID
            bundle_id = self._generate_bundle_id(
                bundle_metadata.name, bundle_metadata.version
            )

            # Upload bundle file
            bundle_key = self._get_key(f"{self.BUNDLES_DIR}/{bundle_id}.skillmeat-pack")
            bundle_size = bundle_path.stat().st_size

            # Progress callback wrapper
            def upload_callback(bytes_transferred):
                if progress_callback:
                    progress_callback(
                        self._create_progress_info(
                            bytes_transferred,
                            bundle_size,
                            "upload",
                            bundle_metadata.name,
                        )
                    )

            # Upload with progress tracking
            self.s3_client.upload_file(
                str(bundle_path),
                self.bucket,
                bundle_key,
                Callback=upload_callback,
            )

            # Create metadata
            uploaded_at = datetime.utcnow().isoformat()
            vault_metadata = VaultBundleMetadata.from_bundle_metadata(
                bundle_id=bundle_id,
                bundle_metadata=bundle_metadata,
                uploaded_at=uploaded_at,
                size_bytes=bundle_size,
                bundle_hash=bundle_hash,
                vault_path=f"s3://{self.bucket}/{bundle_key}",
            )

            # Upload metadata
            metadata_key = self._get_key(f"{self.METADATA_DIR}/{bundle_id}.json")
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=metadata_key,
                Body=json.dumps(vault_metadata.to_dict(), indent=2).encode(),
                ContentType="application/json",
            )

            # Update index
            index = self._read_index()
            index[bundle_id] = vault_metadata.to_dict()
            self._write_index(index)

            logger.info(f"Bundle pushed to S3 vault: {bundle_id}")
            return bundle_id

        except self.ClientError as e:
            raise VaultError(f"Failed to push bundle to S3: {e}")
        except Exception as e:
            if isinstance(e, VaultError):
                raise
            raise VaultError(f"Failed to push bundle to S3 vault: {e}")

    def pull(
        self,
        bundle_id: str,
        destination: Path,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Path:
        """Download bundle from S3.

        Args:
            bundle_id: Bundle identifier (S3 key prefix)
            destination: Directory where bundle will be saved
            progress_callback: Optional callback for download progress

        Returns:
            Path to downloaded bundle file

        Raises:
            VaultNotFoundError: If bundle not found
            VaultError: If download fails
        """
        self._check_authenticated()

        try:
            # Check if bundle exists
            bundle_key = self._get_key(f"{self.BUNDLES_DIR}/{bundle_id}.skillmeat-pack")

            try:
                response = self.s3_client.head_object(Bucket=self.bucket, Key=bundle_key)
                bundle_size = response["ContentLength"]
            except self.ClientError as e:
                if e.response.get("Error", {}).get("Code") == "404":
                    raise VaultNotFoundError(f"Bundle not found in vault: {bundle_id}")
                raise

            # Get metadata
            metadata = self._read_metadata(bundle_id)

            # Download to destination
            destination.mkdir(parents=True, exist_ok=True)
            dest_path = destination / f"{bundle_id}.skillmeat-pack"

            # Progress callback wrapper
            def download_callback(bytes_transferred):
                if progress_callback:
                    progress_callback(
                        self._create_progress_info(
                            bytes_transferred,
                            bundle_size,
                            "download",
                            metadata.name,
                        )
                    )

            # Download with progress tracking
            self.s3_client.download_file(
                self.bucket,
                bundle_key,
                str(dest_path),
                Callback=download_callback,
            )

            logger.info(f"Bundle pulled from S3 vault: {bundle_id} -> {dest_path}")
            return dest_path

        except VaultNotFoundError:
            raise
        except self.ClientError as e:
            raise VaultError(f"Failed to pull bundle from S3: {e}")
        except Exception as e:
            raise VaultError(f"Failed to pull bundle from S3 vault: {e}")

    def list(
        self,
        name_filter: Optional[str] = None,
        tag_filter: Optional[List[str]] = None,
    ) -> List[VaultBundleMetadata]:
        """List bundles in S3.

        Args:
            name_filter: Optional name pattern to filter bundles
            tag_filter: Optional list of tags to filter bundles

        Returns:
            List of bundle metadata

        Raises:
            VaultError: If listing fails
        """
        self._check_authenticated()

        try:
            index = self._read_index()
            bundles = []

            for bundle_id, metadata_dict in index.items():
                metadata = VaultBundleMetadata(**metadata_dict)

                # Apply filters
                if name_filter and name_filter.lower() not in metadata.name.lower():
                    continue

                if tag_filter and not any(tag in metadata.tags for tag in tag_filter):
                    continue

                bundles.append(metadata)

            # Sort by uploaded_at (newest first)
            bundles.sort(key=lambda b: b.uploaded_at, reverse=True)

            logger.debug(f"Listed {len(bundles)} bundles from S3 vault")
            return bundles

        except Exception as e:
            raise VaultError(f"Failed to list bundles from S3 vault: {e}")

    def delete(self, bundle_id: str) -> bool:
        """Delete bundle from S3.

        Args:
            bundle_id: Bundle identifier

        Returns:
            True if bundle was deleted, False if not found

        Raises:
            VaultError: If deletion fails
            VaultPermissionError: If read-only mode enabled
        """
        self._check_authenticated()
        self._check_write_permission()

        try:
            bundle_key = self._get_key(f"{self.BUNDLES_DIR}/{bundle_id}.skillmeat-pack")
            metadata_key = self._get_key(f"{self.METADATA_DIR}/{bundle_id}.json")

            # Check if bundle exists
            try:
                self.s3_client.head_object(Bucket=self.bucket, Key=bundle_key)
            except self.ClientError as e:
                if e.response.get("Error", {}).get("Code") == "404":
                    return False
                raise

            # Delete bundle file
            self.s3_client.delete_object(Bucket=self.bucket, Key=bundle_key)

            # Delete metadata file
            try:
                self.s3_client.delete_object(Bucket=self.bucket, Key=metadata_key)
            except self.ClientError:
                pass  # Metadata might not exist

            # Update index
            index = self._read_index()
            if bundle_id in index:
                del index[bundle_id]
                self._write_index(index)

            logger.info(f"Bundle deleted from S3 vault: {bundle_id}")
            return True

        except self.ClientError as e:
            raise VaultError(f"Failed to delete bundle from S3: {e}")
        except Exception as e:
            raise VaultError(f"Failed to delete bundle from S3 vault: {e}")

    def exists(self, bundle_id: str) -> bool:
        """Check if bundle exists in S3.

        Args:
            bundle_id: Bundle identifier

        Returns:
            True if bundle exists, False otherwise
        """
        self._check_authenticated()

        try:
            bundle_key = self._get_key(f"{self.BUNDLES_DIR}/{bundle_id}.skillmeat-pack")
            self.s3_client.head_object(Bucket=self.bucket, Key=bundle_key)
            return True
        except self.ClientError as e:
            if e.response.get("Error", {}).get("Code") == "404":
                return False
            raise VaultError(f"Failed to check bundle existence: {e}")

    def get_metadata(self, bundle_id: str) -> VaultBundleMetadata:
        """Get metadata for a specific bundle.

        Args:
            bundle_id: Bundle identifier

        Returns:
            Bundle metadata

        Raises:
            VaultNotFoundError: If bundle not found
            VaultError: If metadata retrieval fails
        """
        self._check_authenticated()

        if not self.exists(bundle_id):
            raise VaultNotFoundError(f"Bundle not found: {bundle_id}")

        return self._read_metadata(bundle_id)

    # ====================
    # Helper Methods
    # ====================

    def _get_key(self, path: str) -> str:
        """Get full S3 key with prefix.

        Args:
            path: Relative path

        Returns:
            Full S3 key
        """
        if self.prefix:
            return f"{self.prefix}/{path}"
        return path

    def _generate_bundle_id(self, name: str, version: str) -> str:
        """Generate bundle ID from name and version.

        Args:
            name: Bundle name
            version: Bundle version

        Returns:
            Bundle ID
        """
        safe_name = name.replace(" ", "-").lower()
        return f"{safe_name}-v{version}"

    def _read_index(self) -> Dict[str, Dict[str, Any]]:
        """Read vault index from S3.

        Returns:
            Index dictionary
        """
        index_key = self._get_key(self.METADATA_FILENAME)

        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=index_key)
            index_data = response["Body"].read().decode()
            return json.loads(index_data)
        except self.ClientError as e:
            if e.response.get("Error", {}).get("Code") == "NoSuchKey":
                return {}
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted vault index: {e}")
            return {}

    def _write_index(self, index: Dict[str, Dict[str, Any]]) -> None:
        """Write vault index to S3.

        Args:
            index: Index dictionary
        """
        index_key = self._get_key(self.METADATA_FILENAME)

        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=index_key,
            Body=json.dumps(index, indent=2, sort_keys=True).encode(),
            ContentType="application/json",
        )

    def _read_metadata(self, bundle_id: str) -> VaultBundleMetadata:
        """Read bundle metadata from S3.

        Args:
            bundle_id: Bundle identifier

        Returns:
            Bundle metadata

        Raises:
            VaultNotFoundError: If metadata not found
            VaultError: If metadata is invalid
        """
        metadata_key = self._get_key(f"{self.METADATA_DIR}/{bundle_id}.json")

        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=metadata_key)
            metadata_data = response["Body"].read().decode()
            metadata_dict = json.loads(metadata_data)
            return VaultBundleMetadata(**metadata_dict)
        except self.ClientError as e:
            if e.response.get("Error", {}).get("Code") == "NoSuchKey":
                raise VaultNotFoundError(f"Bundle metadata not found: {bundle_id}")
            raise VaultError(f"Failed to read bundle metadata: {e}")
        except Exception as e:
            raise VaultError(f"Failed to read bundle metadata: {e}")
