# Bug Fixes - November 2025

## 2025-11-18

### API Import Errors

**Issue 1: BundleImporter Import Error**
- **Location**: `skillmeat/api/routers/marketplace.py:29`
- **Error**: Cannot import `BundleImporter` from `skillmeat.core.sharing.bundle`
- **Root Cause**: `BundleImporter` is defined in `skillmeat/core/sharing/importer.py`, not `bundle.py`
- **Fix**: Updated import from `from skillmeat.core.sharing.bundle import Bundle, BundleImporter` to separate imports

**Issue 2: RateLimitMiddleware Missing Import**
- **Location**: `skillmeat/api/server.py:103`
- **Error**: `RateLimitMiddleware` not defined
- **Root Cause**: Missing import in server.py, though class is properly exported from middleware module
- **Fix**: Added `RateLimitMiddleware, get_rate_limiter` to line 22 imports

**Validation**: Both imports now work successfully; server app creation succeeds
