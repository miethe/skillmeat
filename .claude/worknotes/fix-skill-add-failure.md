# Fix Skill Add Failure

## Issue
- GitHub skill addition fails: `ArtifactManager.add_from_github() got an unexpected keyword argument 'override_name'`
- Local skill addition fails: `ArtifactManager.add_from_local() got an unexpected keyword argument 'local_path'`

## Tasks
- [ ] Investigate ArtifactManager method signatures
- [ ] Investigate CLI calls to ArtifactManager
- [ ] Fix method signature mismatches
- [ ] Test the fixes
- [ ] Commit fixes

## Progress
- ✅ Investigated ArtifactManager method signatures
- ✅ Found CLI parameter mismatches
- ✅ Fixed parameter names in cli.py:
  - Changed `override_name` to `custom_name`
  - Changed `local_path` to `path`
  - Removed `verify` and `force` parameters
  - Added `tags=None` parameter
