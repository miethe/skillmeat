"""Vault connector factory for creating vault instances.

Provides registry pattern for vault connector types and factory methods
for instantiating connectors from configuration.
"""

import logging
from typing import Any, Dict, Type

from .base import VaultConnector, VaultError
from .git_vault import GitVaultConnector
from .s3_vault import S3VaultConnector
from .local_vault import LocalVaultConnector

logger = logging.getLogger(__name__)


class VaultFactory:
    """Factory for creating vault connector instances.

    Maintains a registry of vault connector types and provides
    factory methods for instantiation from configuration.
    """

    _registry: Dict[str, Type[VaultConnector]] = {}

    @classmethod
    def register(cls, vault_type: str, connector_class: Type[VaultConnector]) -> None:
        """Register a vault connector type.

        Args:
            vault_type: Type identifier (e.g., "git", "s3", "local")
            connector_class: VaultConnector subclass

        Raises:
            ValueError: If vault_type is already registered
        """
        if vault_type in cls._registry:
            raise ValueError(
                f"Vault type '{vault_type}' is already registered "
                f"with {cls._registry[vault_type].__name__}"
            )

        if not issubclass(connector_class, VaultConnector):
            raise TypeError(
                f"Connector class must be a subclass of VaultConnector, "
                f"got {connector_class.__name__}"
            )

        cls._registry[vault_type] = connector_class
        logger.debug(f"Registered vault connector: {vault_type} -> {connector_class.__name__}")

    @classmethod
    def unregister(cls, vault_type: str) -> None:
        """Unregister a vault connector type.

        Args:
            vault_type: Type identifier to unregister

        Raises:
            KeyError: If vault_type is not registered
        """
        if vault_type not in cls._registry:
            raise KeyError(f"Vault type '{vault_type}' is not registered")

        del cls._registry[vault_type]
        logger.debug(f"Unregistered vault connector: {vault_type}")

    @classmethod
    def create(
        cls,
        vault_id: str,
        vault_type: str,
        config: Dict[str, Any],
        read_only: bool = False,
    ) -> VaultConnector:
        """Create a vault connector instance.

        Args:
            vault_id: Unique identifier for the vault
            vault_type: Type of vault (e.g., "git", "s3", "local")
            config: Configuration dictionary for the vault
            read_only: If True, prevent write operations

        Returns:
            VaultConnector instance

        Raises:
            VaultError: If vault_type is not registered
            ValueError: If configuration is invalid
        """
        if vault_type not in cls._registry:
            available_types = ", ".join(cls._registry.keys())
            raise VaultError(
                f"Unknown vault type: '{vault_type}'. "
                f"Available types: {available_types}"
            )

        connector_class = cls._registry[vault_type]

        try:
            connector = connector_class(
                vault_id=vault_id,
                config=config,
                read_only=read_only,
            )
            logger.info(
                f"Created {vault_type} vault connector: {vault_id} "
                f"(read_only={read_only})"
            )
            return connector
        except Exception as e:
            raise VaultError(
                f"Failed to create {vault_type} vault connector: {e}"
            ) from e

    @classmethod
    def get_registered_types(cls) -> list[str]:
        """Get list of registered vault types.

        Returns:
            List of vault type identifiers
        """
        return list(cls._registry.keys())

    @classmethod
    def is_registered(cls, vault_type: str) -> bool:
        """Check if a vault type is registered.

        Args:
            vault_type: Type identifier to check

        Returns:
            True if registered, False otherwise
        """
        return vault_type in cls._registry


# Register built-in vault connectors
def register_builtin_connectors():
    """Register all built-in vault connectors."""
    VaultFactory.register("local", LocalVaultConnector)
    VaultFactory.register("git", GitVaultConnector)
    VaultFactory.register("s3", S3VaultConnector)


# Register on module import
register_builtin_connectors()


# Convenience function for external connector registration
def register_vault_connector(vault_type: str, connector_class: Type[VaultConnector]) -> None:
    """Register a custom vault connector.

    Convenience function for external packages to register custom connectors.

    Args:
        vault_type: Type identifier (e.g., "azure", "gcp")
        connector_class: VaultConnector subclass

    Example:
        >>> from skillmeat.core.sharing.vault import register_vault_connector
        >>> register_vault_connector("custom", MyCustomVaultConnector)
    """
    VaultFactory.register(vault_type, connector_class)
