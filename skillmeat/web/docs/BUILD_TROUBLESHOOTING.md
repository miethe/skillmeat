# Next.js Build Troubleshooting

## MODULE_NOT_FOUND Errors

### Symptoms

```
Error: Cannot find module '/path/to/node_modules/.pnpm/next@15.5.6.../next/dist/cli/next-start.js'
  at __webpack_require__.f.require (.next/server/webpack-runtime.js:190:28)
  code: 'MODULE_NOT_FOUND'
```

### Root Cause

This error occurs when Next.js build caches become corrupted or out of sync, typically when:

1. **Mixed development and production builds** - Both dev and prod webpack caches exist simultaneously
2. **Stale standalone builds** - The `.next/standalone` directory has outdated dependencies
3. **Dependency changes** - `node_modules` updated but `.next/cache` wasn't cleared
4. **Interrupted builds** - Build process was terminated mid-execution

### Quick Fix

```bash
# Option 1: Clean build cache only
pnpm clean

# Option 2: Full clean rebuild
pnpm build:fresh

# Option 3: Nuclear option (if issues persist)
pnpm clean:all
```

### Prevention

#### Use the right commands

```bash
# Development
pnpm dev              # Always use for development

# Production
pnpm build:fresh      # Clean build for production
pnpm start            # Start production server
```

#### Pre-build validation

Run the validation script before building:

```bash
./scripts/validate-build.sh
```

This checks for:

- Conflicting development/production caches
- Stale standalone builds
- Missing dependencies

#### CI/CD Best Practices

Always clean before production builds:

```yaml
# In your CI/CD pipeline
- run: pnpm clean
- run: pnpm build
```

### Available Scripts

| Script                        | Purpose                                      | When to Use                                   |
| ----------------------------- | -------------------------------------------- | --------------------------------------------- |
| `pnpm clean`                  | Remove `.next` directory                     | After dependency changes or when errors occur |
| `pnpm clean:cache`            | Remove only webpack cache                    | When you want to keep type definitions        |
| `pnpm clean:all`              | Remove `.next` and `node_modules`, reinstall | Nuclear option for persistent issues          |
| `pnpm build:fresh`            | Clean and build                              | Before production deploys                     |
| `./scripts/validate-build.sh` | Check build environment                      | Before any build to catch issues early        |

### Understanding the Cache Structure

```
.next/
├── cache/
│   └── webpack/
│       ├── client-development/     # Dev mode client cache
│       ├── server-development/     # Dev mode server cache
│       ├── client-production/      # Prod mode client cache ⚠️
│       └── server-production/      # Prod mode server cache ⚠️
└── standalone/                     # Standalone build ⚠️
    ├── .next/                      # Can get stale
    └── node_modules/               # Can mismatch main node_modules
```

⚠️ **Warning**: Having both dev and prod caches, or stale standalone builds, is the primary cause of MODULE_NOT_FOUND errors.

### Debugging Steps

1. **Check what's in your cache**:

   ```bash
   ls -la .next/cache/webpack/
   ```

2. **Check cache size** (large = potential issues):

   ```bash
   du -sh .next/cache
   ```

3. **Identify mixed caches**:

   ```bash
   # If both exist, you have a problem:
   ls .next/cache/webpack/client-development
   ls .next/cache/webpack/client-production
   ```

4. **Clean and rebuild**:
   ```bash
   pnpm clean
   pnpm install  # Ensure dependencies are fresh
   pnpm dev      # For development
   # OR
   pnpm build    # For production
   ```

### When to Use Each Clean Command

- **After pulling code**: `pnpm install` (usually sufficient)
- **After changing dependencies**: `pnpm clean && pnpm install`
- **Build errors**: `pnpm build:fresh`
- **Persistent issues**: `pnpm clean:all`
- **Before production deploy**: `pnpm build:fresh`
- **After switching branches**: `pnpm clean`

### Related Issues

- Next.js standalone builds: https://nextjs.org/docs/app/api-reference/next-config-js/output
- Webpack caching: https://webpack.js.org/configuration/cache/
- pnpm store management: https://pnpm.io/cli/store
