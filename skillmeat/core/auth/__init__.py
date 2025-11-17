"""Authentication and token management for SkillMeat web interface.

This module provides secure token-based authentication for local CLI-to-web
communication. It supports multiple storage backends including OS keychains
and encrypted file storage.
"""

from .storage import TokenStorage, KeychainStorage, EncryptedFileStorage
from .token_manager import TokenManager, Token, TokenInfo

__all__ = [
    "TokenStorage",
    "KeychainStorage",
    "EncryptedFileStorage",
    "TokenManager",
    "Token",
    "TokenInfo",
]
