# Next.js Build Cache MODULE_NOT_FOUND Fix
**Date**: 2025-11-26
**Type**: Bug Fix
**Component**: Web (Next.js)
**Severity**: High (Blocks production builds)

## Problem
Recurring MODULE_NOT_FOUND errors when building or starting the Next.js application:

```
Error: Cannot find module '/Users/miethe/dev/homelab/development/skillmeat/skillmeat/web/node_modules/.pnpm/next@15.5.6_@babel+core@7.28.5_@opentelemetry+api@1.9.0_@playwright+test@1.56.1_react-dom@19.2.0_react@19.2.0/node_modules/next/dist/cli/next-start.js'
  at __webpack_require__.f.require (.next/server/webpack-runtime.js:190:28)
  code: 'MODULE_NOT_FOUND',
```

## Root Cause Analysis

### Primary Issue: Mixed Build Caches
The `.next/cache/webpack/` directory contained both development and production caches simultaneously:
- `client-development/` and `server-development/`
- `client-production/` and `server-production/`

When webpack tries to load modules during builds, it can reference the wrong cache, leading to MODULE_NOT_FOUND errors.

### Contributing Factors
1. **Standalone builds** - `.next/standalone/` directory with stale dependencies
2. **Large cache size** - 657MB of cached webpack artifacts
3. **Dependency mismatches** - Standalone build's `node_modules` out of sync with main `node_modules`
4. **Cache corruption** - Interrupted builds or dependency changes without cache cleanup

## Solution Implemented

### 1. Added Cleanup Scripts to package.json
```json
{
  "scripts": {
    "clean": "rm -rf .next",
    "clean:cache": "rm -rf .next/cache",
    "clean:all": "rm -rf .next node_modules && pnpm install",
    "build:fresh": "pnpm clean && pnpm build"
  }
}
```

### 2. Created Validation Script
- **File**: `skillmeat/web/scripts/validate-build.sh`
- **Purpose**: Pre-build validation to detect and fix cache issues
- **Checks**:
  - Mixed development/production caches
  - Stale standalone builds
  - Missing dependencies
  - Interactive cleanup prompts

### 3. Created Troubleshooting Documentation
- **File**: `skillmeat/web/docs/BUILD_TROUBLESHOOTING.md`
- **Contents**:
  - Symptom identification
  - Root cause explanations
  - Quick fix commands
  - Prevention strategies
  - CI/CD best practices

## Prevention Measures

### For Development
```bash
# Always use these commands:
pnpm dev              # Development server (creates dev cache)
```

### For Production
```bash
# Always clean before production builds:
pnpm build:fresh      # Clean + build
pnpm start            # Start production server
```

### Before Building
```bash
# Run validation to catch issues early:
./scripts/validate-build.sh
```

## Testing Plan
1. Clean existing cache: `pnpm clean`
2. Run development server: `pnpm dev`
3. Test production build: `pnpm build:fresh`
4. Verify with chrome-devtools skill
5. Document any remaining issues

## Impact
- **Immediate**: Provides clear remediation path for MODULE_NOT_FOUND errors
- **Ongoing**: Prevents future cache corruption through better workflows
- **CI/CD**: Ensures consistent production builds with `build:fresh` command

## Files Modified
1. `skillmeat/web/package.json` - Added cleanup scripts
2. `skillmeat/web/scripts/validate-build.sh` - Created validation script
3. `skillmeat/web/docs/BUILD_TROUBLESHOOTING.md` - Created troubleshooting guide
4. `skillmeat/web/manager.py` - Updated `build_web()` to use `pnpm build:fresh`
5. `docs/worknotes/2025-11-26_nextjs-build-cache-fix.md` - This file

## CLI Integration
The `skillmeat web build` command now uses `pnpm build:fresh` automatically,
ensuring the cache is cleaned before every production build. This prevents
the MODULE_NOT_FOUND errors without requiring manual intervention.

## Next Steps
1. Test the fix thoroughly
2. Update CI/CD pipeline to use `pnpm build:fresh`
3. Add pre-commit hook to warn about mixed caches
4. Consider adding cache validation to dev server startup

## Related Issues
- Next.js webpack caching: https://nextjs.org/docs/app/building-your-application/optimizing/caching
- Standalone builds: https://nextjs.org/docs/app/api-reference/next-config-js/output
- pnpm store management: https://pnpm.io/cli/store

## Lessons Learned
1. **Always clean before switching build modes** - Development to production transitions should trigger cache cleanup
2. **Standalone builds need attention** - They create isolated dependency trees that can drift
3. **Large caches are warning signs** - 657MB cache suggests accumulated cruft
4. **Preventive tooling helps** - Validation scripts catch issues before they become blocking
