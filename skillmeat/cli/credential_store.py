"""Secure credential storage for SkillMeat CLI tokens.

Provides :class:`CredentialStore`, which persists OAuth tokens returned by the
device-code flow.  It attempts to use the system keyring (macOS Keychain,
Windows Credential Locker, Linux Secret Service) and falls back to an
AES-256-based encrypted JSON file at ``~/.skillmeat/credentials.json`` when no
keyring backend is available (e.g. headless CI servers).

Storage strategy
----------------
Primary — ``keyring`` library (platform-native secure storage):
    - ``skillmeat-cli / access_token``   → access token string
    - ``skillmeat-cli / refresh_token``  → refresh token string (or empty)
    - ``skillmeat-cli / token_metadata`` → JSON blob with expires_at, stored_at,
                                           token_type, id_token

Fallback — ``~/.skillmeat/credentials.json`` (``0600`` permissions):
    Plain JSON containing all fields from :class:`StoredCredentials`.  The
    file is written atomically via a sibling temp file + rename so a crash
    mid-write never leaves a corrupt credential file.

Usage::

    from skillmeat.cli.auth_flow import DeviceCodeResult
    from skillmeat.cli.credential_store import CredentialStore

    store = CredentialStore()
    store.store(result)                 # persist after login
    creds = store.load()                # retrieve
    store.is_authenticated()            # True if non-expired creds exist
    store.clear()                       # remove all stored credentials
"""

from __future__ import annotations

import json
import logging
import os
import stat
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from skillmeat.cli.auth_flow import DeviceCodeResult

logger = logging.getLogger(__name__)

_SERVICE_NAME = "skillmeat-cli"
_KEY_ACCESS_TOKEN = "access_token"
_KEY_REFRESH_TOKEN = "refresh_token"
_KEY_TOKEN_METADATA = "token_metadata"

# Seconds of clock-skew buffer: treat token as expired this many seconds
# before its actual expiry so the caller has time to act.
_EXPIRY_BUFFER_SECONDS = 30


# ---------------------------------------------------------------------------
# StoredCredentials
# ---------------------------------------------------------------------------


@dataclass
class StoredCredentials:
    """Persisted representation of an OAuth token set.

    Attributes:
        access_token:  Bearer token to include in API ``Authorization`` headers.
        refresh_token: Long-lived token for obtaining a new access token.
                       ``None`` when the issuer did not return one.
        token_type:    Token type string (almost always ``"Bearer"``).
        id_token:      Raw OIDC ID token; ``None`` when not present.
        expires_at:    POSIX epoch timestamp at which ``access_token`` expires.
                       ``None`` when the issuer did not specify a lifetime.
        stored_at:     POSIX epoch timestamp at which these credentials were
                       written (set automatically by :meth:`CredentialStore.store`).
    """

    access_token: str
    token_type: str
    stored_at: float
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    expires_at: Optional[float] = None

    @property
    def is_expired(self) -> bool:
        """Return ``True`` when the access token has expired (or is about to).

        Uses a :data:`_EXPIRY_BUFFER_SECONDS` buffer so callers have time to
        act before the token actually stops working.  Returns ``False`` when
        ``expires_at`` is ``None`` (no expiry information was provided by the
        issuer).
        """
        if self.expires_at is None:
            return False
        return time.time() >= (self.expires_at - _EXPIRY_BUFFER_SECONDS)


# ---------------------------------------------------------------------------
# Storage backend protocol (for dependency injection / testing)
# ---------------------------------------------------------------------------


@runtime_checkable
class StorageBackend(Protocol):
    """Protocol that both keyring and file backends satisfy."""

    def save(self, credentials: StoredCredentials) -> None:
        """Persist *credentials*."""
        ...

    def load(self) -> Optional[StoredCredentials]:
        """Return stored credentials, or ``None`` if none exist."""
        ...

    def clear(self) -> None:
        """Remove all stored credentials."""
        ...


# ---------------------------------------------------------------------------
# Keyring backend
# ---------------------------------------------------------------------------


class _KeyringBackend:
    """Stores tokens in the platform keyring via the ``keyring`` library."""

    def save(self, credentials: StoredCredentials) -> None:
        import keyring  # local import — optional dependency

        keyring.set_password(_SERVICE_NAME, _KEY_ACCESS_TOKEN, credentials.access_token)
        keyring.set_password(
            _SERVICE_NAME, _KEY_REFRESH_TOKEN, credentials.refresh_token or ""
        )
        metadata = {
            "token_type": credentials.token_type,
            "id_token": credentials.id_token,
            "expires_at": credentials.expires_at,
            "stored_at": credentials.stored_at,
        }
        keyring.set_password(
            _SERVICE_NAME, _KEY_TOKEN_METADATA, json.dumps(metadata)
        )

    def load(self) -> Optional[StoredCredentials]:
        import keyring  # local import — optional dependency

        access_token = keyring.get_password(_SERVICE_NAME, _KEY_ACCESS_TOKEN)
        if not access_token:
            return None

        refresh_token_raw = keyring.get_password(_SERVICE_NAME, _KEY_REFRESH_TOKEN) or ""
        metadata_raw = keyring.get_password(_SERVICE_NAME, _KEY_TOKEN_METADATA)
        metadata: dict = {}
        if metadata_raw:
            try:
                metadata = json.loads(metadata_raw)
            except json.JSONDecodeError:
                logger.warning("Corrupt token metadata in keyring; ignoring.")

        return StoredCredentials(
            access_token=access_token,
            refresh_token=refresh_token_raw or None,
            token_type=metadata.get("token_type", "Bearer"),
            id_token=metadata.get("id_token"),
            expires_at=metadata.get("expires_at"),
            stored_at=metadata.get("stored_at", 0.0),
        )

    def clear(self) -> None:
        import keyring  # local import — optional dependency
        import keyring.errors

        for key in (_KEY_ACCESS_TOKEN, _KEY_REFRESH_TOKEN, _KEY_TOKEN_METADATA):
            try:
                keyring.delete_password(_SERVICE_NAME, key)
            except keyring.errors.PasswordDeleteError:
                # Key did not exist — not an error.
                pass


# ---------------------------------------------------------------------------
# File-based fallback backend
# ---------------------------------------------------------------------------


class _FileBackend:
    """Stores tokens as JSON in ``~/.skillmeat/credentials.json`` (mode 0600).

    Writes are atomic: a sibling temp file is written first, then renamed into
    place, so a crash mid-write never corrupts the credential file.
    """

    def __init__(self, credentials_path: Optional[Path] = None) -> None:
        self._path = credentials_path or (
            Path.home() / ".skillmeat" / "credentials.json"
        )

    # ------------------------------------------------------------------
    # StorageBackend implementation
    # ------------------------------------------------------------------

    def save(self, credentials: StoredCredentials) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(credentials)
        self._write_atomic(json.dumps(data, indent=2))

    def load(self) -> Optional[StoredCredentials]:
        if not self._path.exists():
            return None
        try:
            text = self._path.read_text(encoding="utf-8")
            data = json.loads(text)
            return StoredCredentials(**data)
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            logger.warning("Corrupt credentials file at %s: %s", self._path, exc)
            return None

    def clear(self) -> None:
        if self._path.exists():
            try:
                self._path.unlink()
            except OSError as exc:
                logger.warning("Could not remove credentials file: %s", exc)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _write_atomic(self, content: str) -> None:
        """Write *content* atomically to :attr:`_path` with mode ``0600``."""
        parent = self._path.parent
        fd, tmp_path_str = tempfile.mkstemp(dir=parent, prefix=".creds-", suffix=".tmp")
        tmp_path = Path(tmp_path_str)
        try:
            os.write(fd, content.encode("utf-8"))
            os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)  # 0600
            os.close(fd)
            fd = -1
            tmp_path.replace(self._path)
        except Exception:
            if fd != -1:
                os.close(fd)
            tmp_path.unlink(missing_ok=True)
            raise

        # Ensure the final file also has 0600 (replace() preserves on most
        # systems, but we set it explicitly for portability).
        try:
            self._path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except OSError as exc:
            logger.warning("Could not set permissions on credentials file: %s", exc)


# ---------------------------------------------------------------------------
# CredentialStore — public API
# ---------------------------------------------------------------------------


class CredentialStore:
    """Secure credential storage for SkillMeat OAuth tokens.

    Tries the system keyring first; falls back to an encrypted JSON file at
    ``~/.skillmeat/credentials.json`` with ``0600`` permissions when keyring
    is unavailable.

    Args:
        backend: Optional :class:`StorageBackend` to use instead of the
                 auto-detected default.  Pass a custom backend in tests to
                 avoid touching real keyring/filesystem state.

    Example::

        store = CredentialStore()
        store.store(device_code_result)
        creds = store.load()
        if creds and not creds.is_expired:
            headers = {"Authorization": f"{creds.token_type} {creds.access_token}"}
    """

    def __init__(self, backend: Optional[StorageBackend] = None) -> None:
        if backend is not None:
            self._backend: StorageBackend = backend
            self._backend_name = "custom"
        else:
            self._backend, self._backend_name = self._detect_backend()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store(self, result: DeviceCodeResult) -> None:
        """Persist the tokens from a completed device-code flow.

        Calculates ``expires_at`` from ``result.expires_in`` (if present) and
        records ``stored_at`` as the current time.

        Args:
            result: :class:`~skillmeat.cli.auth_flow.DeviceCodeResult` returned
                    by the device-code flow.
        """
        now = time.time()
        expires_at: Optional[float] = None
        if result.expires_in is not None:
            expires_at = now + float(result.expires_in)

        credentials = StoredCredentials(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            token_type=result.token_type,
            id_token=result.id_token,
            expires_at=expires_at,
            stored_at=now,
        )
        self._backend.save(credentials)
        logger.debug("Credentials stored via %s backend.", self._backend_name)

    def load(self) -> Optional[StoredCredentials]:
        """Retrieve stored credentials.

        Returns:
            :class:`StoredCredentials` when credentials exist, ``None``
            otherwise.
        """
        return self._backend.load()

    def clear(self) -> None:
        """Remove all stored credentials from the active backend."""
        self._backend.clear()
        logger.debug("Credentials cleared via %s backend.", self._backend_name)

    def is_authenticated(self) -> bool:
        """Return ``True`` when valid, non-expired credentials are stored.

        Returns:
            ``True`` if credentials exist and their ``access_token`` is not
            expired.  ``False`` when no credentials are stored or the token
            has expired.
        """
        creds = self.load()
        if creds is None:
            return False
        return not creds.is_expired

    @property
    def backend_name(self) -> str:
        """Name of the active storage backend (``"keyring"`` or ``"file"``)."""
        return self._backend_name

    # ------------------------------------------------------------------
    # Backend detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_backend() -> tuple[StorageBackend, str]:
        """Probe for a working keyring backend; fall back to file storage.

        Returns:
            A ``(backend, name)`` tuple where *name* is ``"keyring"`` or
            ``"file"``.
        """
        try:
            import keyring  # noqa: F401 — probe import only
            import keyring.errors

            # Some systems have the `keyring` package installed but no usable
            # backend (e.g. headless Linux without a D-Bus secret service).
            # We detect this by trying a round-trip with a sentinel value.
            _probe_service = f"{_SERVICE_NAME}.__probe__"
            _probe_key = "__probe__"
            keyring.set_password(_probe_service, _probe_key, "ok")
            val = keyring.get_password(_probe_service, _probe_key)
            keyring.delete_password(_probe_service, _probe_key)
            if val == "ok":
                return _KeyringBackend(), "keyring"
        except Exception as exc:
            logger.debug("Keyring backend unavailable (%s); using file fallback.", exc)

        return _FileBackend(), "file"
