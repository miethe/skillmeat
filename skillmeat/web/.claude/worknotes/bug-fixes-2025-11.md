# Bug Fixes - November 2025

## 2025-11-21: Build Error - Missing UI Components

**Bug**: Next.js build failed with "Module not found: Can't resolve '@/components/ui/separator'" and missing Select component exports (SelectTrigger, SelectValue, SelectContent, SelectItem).

**Root Cause**:
- Separator component not implemented
- Select component using native HTML select instead of Radix UI primitives

**Fix**:
- Added Separator component using @radix-ui/react-separator
- Replaced Select with full Radix UI implementation providing all required exports
- Installed @radix-ui/react-separator dependency
- Build now passes successfully

**Files Modified**:
- `components/ui/separator.tsx` (created)
- `components/ui/select.tsx` (refactored to Radix UI)
- `package.json` (added dependency)

**Commit**: 8b88689
