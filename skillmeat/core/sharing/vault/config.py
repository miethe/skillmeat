"""Vault configuration management.

Manages vault definitions, credentials, and configuration via sharing.toml.
"""

import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Handle tomli/tomllib import for different Python versions
if sys.version_info >= (3, 11):
    import tomllib

    TOML_LOADS = tomllib.loads
else:
    import tomli as tomllib

    TOML_LOADS = tomllib.loads

import tomli_w

from skillmeat.core.auth.storage import get_storage_backend

TOML_DUMPS = tomli_w.dumps

logger = logging.getLogger(__name__)


@dataclass
class VaultConfig:
    """Configuration for a vault.

    Attributes:
        name: Vault identifier
        type: Vault type (git, s3, local)
        config: Type-specific configuration
        read_only: If True, prevent write operations
        is_default: If True, this is the default vault
    """

    name: str
    type: str
    config: Dict[str, Any] = field(default_factory=dict)
    read_only: bool = False
    is_default: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for TOML serialization.

        Returns:
            Dictionary representation
        """
        result = {
            "type": self.type,
            **self.config,  # Flatten config into vault section
        }

        if self.read_only:
            result["read_only"] = True

        return result

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "VaultConfig":
        """Create from dictionary (TOML deserialization).

        Args:
            name: Vault name
            data: Dictionary from TOML

        Returns:
            VaultConfig instance
        """
        vault_type = data.get("type")
        if not vault_type:
            raise ValueError(f"Vault '{name}' missing required 'type' field")

        # Extract read_only flag
        read_only = data.get("read_only", False)

        # Everything else is vault-specific config
        config = {k: v for k, v in data.items() if k not in ("type", "read_only")}

        return cls(
            name=name,
            type=vault_type,
            config=config,
            read_only=read_only,
        )


class VaultConfigManager:
    """Manages vault configurations in sharing.toml.

    Configuration file structure:

    [sharing]
    default_vault = "team-git"

    [vault.team-git]
    type = "git"
    url = "git@github.com:team/skill-vault.git"
    branch = "main"

    [vault.team-s3]
    type = "s3"
    bucket = "team-skillmeat-bundles"
    region = "us-east-1"
    prefix = "bundles/"

    [vault.local-dev]
    type = "local"
    path = "~/.skillmeat/local-vault"
    """

    DEFAULT_CONFIG_DIR = Path.home() / ".skillmeat"
    CONFIG_FILE = "sharing.toml"

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize vault config manager.

        Args:
            config_dir: Override default config directory (for testing)
        """
        self.config_dir = config_dir or self.DEFAULT_CONFIG_DIR
        self.config_path = self.config_dir / self.CONFIG_FILE
        self._credential_storage = get_storage_backend()

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def read_config(self) -> Dict[str, Any]:
        """Read sharing configuration.

        Returns:
            Configuration dictionary

        Raises:
            ValueError: If config file is corrupted
        """
        if not self.config_path.exists():
            return {}

        try:
            with open(self.config_path, "rb") as f:
                return TOML_LOADS(f.read().decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Failed to parse sharing config: {e}")

    def write_config(self, config: Dict[str, Any]) -> None:
        """Write sharing configuration.

        Args:
            config: Configuration dictionary to write

        Raises:
            IOError: If write operation fails
        """
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "wb") as f:
            f.write(TOML_DUMPS(config).encode("utf-8"))

    def list_vaults(self) -> List[str]:
        """List all configured vaults.

        Returns:
            List of vault names
        """
        config = self.read_config()
        vault_section = config.get("vault", {})
        return list(vault_section.keys())

    def get_vault(self, name: str) -> Optional[VaultConfig]:
        """Get vault configuration by name.

        Args:
            name: Vault name

        Returns:
            VaultConfig if found, None otherwise
        """
        config = self.read_config()
        vault_section = config.get("vault", {})

        if name not in vault_section:
            return None

        vault_config = VaultConfig.from_dict(name, vault_section[name])

        # Check if this is the default vault
        default_vault = config.get("sharing", {}).get("default_vault")
        vault_config.is_default = name == default_vault

        return vault_config

    def add_vault(self, vault_config: VaultConfig) -> None:
        """Add or update vault configuration.

        Args:
            vault_config: Vault configuration to add

        Raises:
            ValueError: If vault configuration is invalid
        """
        if not vault_config.name:
            raise ValueError("Vault name cannot be empty")

        if not vault_config.type:
            raise ValueError("Vault type cannot be empty")

        config = self.read_config()

        # Ensure vault section exists
        if "vault" not in config:
            config["vault"] = {}

        # Add vault
        config["vault"][vault_config.name] = vault_config.to_dict()

        # Set as default if it's the first vault or marked as default
        if vault_config.is_default or len(config["vault"]) == 1:
            if "sharing" not in config:
                config["sharing"] = {}
            config["sharing"]["default_vault"] = vault_config.name

        self.write_config(config)
        logger.info(f"Added vault configuration: {vault_config.name}")

    def remove_vault(self, name: str) -> bool:
        """Remove vault configuration.

        Args:
            name: Vault name to remove

        Returns:
            True if vault was removed, False if not found

        Raises:
            ValueError: If trying to remove the default vault
        """
        config = self.read_config()
        vault_section = config.get("vault", {})

        if name not in vault_section:
            return False

        # Check if this is the default vault
        default_vault = config.get("sharing", {}).get("default_vault")
        if name == default_vault:
            raise ValueError(
                f"Cannot remove default vault '{name}'. "
                f"Set a different default vault first."
            )

        # Remove vault
        del vault_section[name]

        # Update config
        if not vault_section:
            # No more vaults, remove vault section
            del config["vault"]
            # Remove sharing section if it exists
            if "sharing" in config:
                del config["sharing"]
        else:
            config["vault"] = vault_section

        self.write_config(config)
        logger.info(f"Removed vault configuration: {name}")
        return True

    def get_default_vault(self) -> Optional[str]:
        """Get default vault name.

        Returns:
            Default vault name if set, None otherwise
        """
        config = self.read_config()
        return config.get("sharing", {}).get("default_vault")

    def set_default_vault(self, name: str) -> None:
        """Set default vault.

        Args:
            name: Vault name to set as default

        Raises:
            ValueError: If vault doesn't exist
        """
        config = self.read_config()
        vault_section = config.get("vault", {})

        if name not in vault_section:
            raise ValueError(f"Vault '{name}' not found")

        if "sharing" not in config:
            config["sharing"] = {}

        config["sharing"]["default_vault"] = name
        self.write_config(config)
        logger.info(f"Set default vault: {name}")

    # ====================
    # Credential Management
    # ====================

    def store_credentials(
        self,
        vault_name: str,
        vault_type: str,
        credentials: Dict[str, str],
    ) -> None:
        """Store vault credentials securely.

        Args:
            vault_name: Vault identifier
            vault_type: Vault type (git, s3, etc.)
            credentials: Credentials dictionary

        Raises:
            ValueError: If credentials are invalid
        """
        if not vault_name:
            raise ValueError("Vault name cannot be empty")

        # Validate credentials based on vault type
        if vault_type == "git":
            self._validate_git_credentials(credentials)
        elif vault_type == "s3":
            self._validate_s3_credentials(credentials)

        # Store credentials in secure storage
        cred_id = f"{vault_type}-vault:{vault_name}"
        cred_data = json.dumps(credentials)

        try:
            self._credential_storage.store(cred_id, cred_data)
            logger.info(f"Stored credentials for vault: {vault_name}")
        except Exception as e:
            raise ValueError(f"Failed to store credentials: {e}")

    def get_credentials(
        self,
        vault_name: str,
        vault_type: str,
    ) -> Optional[Dict[str, str]]:
        """Retrieve vault credentials.

        Args:
            vault_name: Vault identifier
            vault_type: Vault type

        Returns:
            Credentials dictionary if found, None otherwise
        """
        cred_id = f"{vault_type}-vault:{vault_name}"

        try:
            cred_data = self._credential_storage.retrieve(cred_id)
            if cred_data:
                return json.loads(cred_data)
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve credentials for {vault_name}: {e}")
            return None

    def delete_credentials(self, vault_name: str, vault_type: str) -> bool:
        """Delete vault credentials.

        Args:
            vault_name: Vault identifier
            vault_type: Vault type

        Returns:
            True if credentials were deleted, False if not found
        """
        cred_id = f"{vault_type}-vault:{vault_name}"

        try:
            return self._credential_storage.delete(cred_id)
        except Exception as e:
            logger.error(f"Failed to delete credentials for {vault_name}: {e}")
            return False

    def _validate_git_credentials(self, credentials: Dict[str, str]) -> None:
        """Validate Git credentials.

        Args:
            credentials: Credentials to validate

        Raises:
            ValueError: If credentials are invalid
        """
        # Git credentials can have:
        # - username + password (HTTPS)
        # - ssh_key_path (SSH)
        # - None (use default Git credentials)

        if "username" in credentials:
            if "password" not in credentials:
                raise ValueError("Git credentials with username must include password")

    def _validate_s3_credentials(self, credentials: Dict[str, str]) -> None:
        """Validate S3 credentials.

        Args:
            credentials: Credentials to validate

        Raises:
            ValueError: If credentials are invalid
        """
        # S3 credentials should have:
        # - access_key_id + secret_access_key
        # - Or use IAM role (no credentials needed)

        if "access_key_id" in credentials:
            if "secret_access_key" not in credentials:
                raise ValueError(
                    "S3 credentials with access_key_id must include secret_access_key"
                )

        if "secret_access_key" in credentials:
            if "access_key_id" not in credentials:
                raise ValueError(
                    "S3 credentials with secret_access_key must include access_key_id"
                )

    # ====================
    # Utility Methods
    # ====================

    def get_vault_with_credentials(self, name: str) -> Optional[VaultConfig]:
        """Get vault configuration with credentials merged in.

        Args:
            name: Vault name

        Returns:
            VaultConfig with credentials, None if vault not found

        Note:
            Credentials are merged into the config dict but should
            NOT be logged or displayed.
        """
        vault_config = self.get_vault(name)
        if not vault_config:
            return None

        # Get credentials
        credentials = self.get_credentials(name, vault_config.type)
        if credentials:
            # Merge credentials into config (shallow merge)
            vault_config.config = {**vault_config.config, **credentials}

        return vault_config
