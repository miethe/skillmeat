# Fix Skill Add Failure

## Issue
- GitHub skill addition fails: `ArtifactManager.add_from_github() got an unexpected keyword argument 'override_name'`
- Local skill addition fails: `ArtifactManager.add_from_local() got an unexpected keyword argument 'local_path'`

## Tasks
- [x] Investigate ArtifactManager method signatures
- [x] Investigate CLI calls to ArtifactManager
- [x] Fix method signature mismatches
- [x] Implement force flag support
- [x] Test the fixes
- [x] Commit fixes
- [ ] Push changes to remote

## Progress
- ✅ Investigated ArtifactManager method signatures
- ✅ Found CLI parameter mismatches
- ✅ Fixed parameter names in cli.py:
  - Changed `override_name` to `custom_name`
  - Changed `local_path` to `path`
  - Added `tags=None` parameter
- ✅ Implemented force flag support in ArtifactManager:
  - Added `force: bool = False` parameter to both methods
  - Implemented artifact removal when force=True
  - Updated docstrings
- ✅ Tested implementation - 38/47 tests passing
- ✅ Committed changes in 2 commits
