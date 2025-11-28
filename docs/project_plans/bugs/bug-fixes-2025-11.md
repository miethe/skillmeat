# Bug Fixes - November 2025

## Summary

Bug fixes resolved during November 2025.

---

### Web Build Clean Script Fails on pnpm Symlinks

**Issue**: `pnpm build:fresh` fails when cleaning `.next` directory due to nested pnpm symlinks in `.next/standalone/node_modules/.pnpm/` causing "Directory not empty" errors on macOS.

- **Location**: `skillmeat/web/package.json:11-13`
- **Root Cause**: pnpm creates complex symlink structures inside the Next.js standalone build output. On macOS, `rm -rf` can fail on these nested symlink directories when file permissions or locks prevent immediate deletion.
- **Fix**: Enhanced clean scripts to retry with permission fix if initial `rm -rf` fails:
  - `clean`: Attempts `rm -rf`, falls back to `chmod -R u+w` then retry, always succeeds
  - `clean:cache`: Same pattern for cache-only cleanup
  - `clean:all`: Same pattern for full cleanup including node_modules
- **Commit(s)**: `cb8e14c`
- **Status**: RESOLVED
