# Repository Pattern Gotchas

## LocalArtifactRepository UUID Resolution (ADR-007)

**Problem**: `LocalArtifactRepository._artifact_to_dto()` used `getattr(artifact, "uuid", None)` which
always returns `None` because filesystem `Artifact` instances don't store UUIDs. The UUID is used
to build `uuid_lookup` in the artifacts list endpoint, causing deployment set members to fail to
resolve (they got MD5 hashes instead of real DB UUIDs).

**Root cause**: Per ADR-007, UUIDs live exclusively in the DB cache (`artifacts.uuid`), not on the
filesystem. The FS `Artifact` dataclass has no `uuid` field.

**Fix** (in `skillmeat/core/repositories/local_artifact.py`):
- Added module-level optional imports: `_get_db_session`, `_DBArtifact`, `_db_available`
- Added `_get_db_uuid(artifact_id: str) -> Optional[str]` — single lookup via `Artifact.uuid` WHERE `Artifact.id == artifact_id`
- Added `_get_db_uuid_batch(artifact_ids: List[str]) -> dict[str, str]` — batch lookup for `list()` and `search()`
- Updated `_artifact_to_dto()` to accept `db_uuid` kwarg; DB UUID takes precedence over any FS attribute
- Updated `get()`, `list()`, `search()`, and `get_by_uuid()` to pass DB UUIDs through

**Pattern for get()**: Single UUID lookup → pass as `db_uuid=` to `_artifact_to_dto()`
**Pattern for list()/search()**: Batch lookup → `uuid_map = self._get_db_uuid_batch(ids)` → pass per-item in comprehension
**Pattern for get_by_uuid()**: DB-first lookup by UUID → resolve to `artifact_id` → call `self.get(artifact_id)`

**Verification**: `curl -s "http://localhost:8080/api/v1/artifacts?limit=5" | jq '.items[].uuid'`
should return real DB UUIDs (like `bb14e35440cf4a9ca8574c6967baf0de`), not MD5 hashes.

**Graceful degradation**: When DB is unavailable (unit tests without DB), `_db_available=False`
and all UUID lookups return `None` — no crash.
