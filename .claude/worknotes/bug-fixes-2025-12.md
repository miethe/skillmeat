# Bug Fixes - December 2025

## 2025-12-01

### CollectionManager get_collection Method Not Found

**Issue**: `skillmeat sync-check` CLI command fails with `'CollectionManager' object has no attribute 'get_collection'`
- **Location**: `skillmeat/core/sync.py:413,622,762,1098,1428`
- **Root Cause**: `SyncManager` called `self.collection_mgr.get_collection()` but the correct method name is `load_collection()`
- **Fix**: Replaced all 5 occurrences of `get_collection` with `load_collection` in sync.py; updated corresponding test mocks in tests/test_sync.py
- **Commit(s)**: b13c97d
- **Status**: RESOLVED
