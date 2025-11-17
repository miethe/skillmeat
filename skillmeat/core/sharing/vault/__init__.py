"""Vault connector system for team bundle sharing.

This module provides pluggable storage backends for hosting bundles in team vaults.
Supports Git repositories, S3 buckets, and local file systems.
"""

from .base import VaultConnector, VaultError, VaultAuthError, VaultNotFoundError
from .factory import VaultFactory, register_vault_connector
from .git_vault import GitVaultConnector
from .s3_vault import S3VaultConnector
from .local_vault import LocalVaultConnector
from .config import VaultConfig, VaultConfigManager

__all__ = [
    "VaultConnector",
    "VaultError",
    "VaultAuthError",
    "VaultNotFoundError",
    "VaultFactory",
    "register_vault_connector",
    "GitVaultConnector",
    "S3VaultConnector",
    "LocalVaultConnector",
    "VaultConfig",
    "VaultConfigManager",
]
