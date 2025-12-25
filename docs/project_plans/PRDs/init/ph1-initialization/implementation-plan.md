# SkillMeat MVP Implementation Plan

**Version:** 1.0
**Date:** 2025-11-07
**Status:** Active Development
**Target Completion:** 8 weeks

---

## Executive Summary

This document provides a detailed implementation plan for transforming **skillman** (skill-only manager) into **skillmeat** (unified Claude artifact manager). Based on comprehensive codebase analysis and architectural design, this plan breaks down the MVP (Phase 1) into 6 implementation phases over 8 weeks.

### Key Findings from Analysis

**Current State (skillman):**
- 1,682 LOC of production code across 8 modules
- Well-structured with 90-100% reusability for core components (models, installer, config, utils)
- CLI requires significant refactoring (40% reusability)
- Comprehensive test coverage with CI/CD pipeline

**Target State (skillmeat):**
- Collection-first architecture (vs. project-manifest)
- Support for Skills, Commands, Agents (3 artifact types for MVP)
- Three-tier system: Collection → Projects
- Enhanced version management with snapshots
- Deployment tracking and bidirectional sync

---

## Implementation Phases

### Phase 1: Foundation & Package Structure (Week 1)

**Goal:** Set up the new package structure and rename from skillman to skillmeat

#### Tasks

1. **Create New Module Structure**
   ```
   skillmeat/
   ├── __init__.py
   ├── cli.py (refactored)
   ├── core/
   │   ├── __init__.py
   │   ├── collection.py
   │   ├── artifact.py
   │   ├── deployment.py
   │   ├── sync.py
   │   └── version.py
   ├── sources/
   │   ├── __init__.py
   │   ├── base.py
   │   ├── github.py
   │   └── local.py
   ├── storage/
   │   ├── __init__.py
   │   ├── manifest.py
   │   ├── lockfile.py
   │   └── snapshot.py
   ├── utils/
   │   ├── __init__.py
   │   ├── metadata.py
   │   ├── validator.py
   │   ├── diff.py
   │   └── filesystem.py
   └── config.py
   ```

2. **Update Package Metadata**
   - Update `pyproject.toml`: name, version (0.1.0-alpha), description
   - Update imports throughout codebase
   - Update CLI entry point: `skillmeat` instead of `skillman`
   - Update configuration directory: `~/.skillmeat/` instead of `~/.skillman/`

3. **Set Up File Organization Structure**
   ```
   ~/.skillmeat/
   ├── config.toml
   ├── collections/
   │   └── default/
   │       ├── collection.toml
   │       ├── collection.lock
   │       ├── skills/
   │       ├── commands/
   │       └── agents/
   └── snapshots/
       └── default/
           └── snapshots.toml
   ```

**Deliverables:**
- [ ] New directory structure created
- [ ] Package renamed to skillmeat
- [ ] Configuration paths updated
- [ ] Basic imports working
- [ ] Git commit: "feat: initialize skillmeat package structure"

**Estimated Effort:** 2-3 days

---

### Phase 2: Data Models & Storage Layer (Week 1-2)

**Goal:** Create generalized data models and storage abstraction

#### Tasks

1. **Create Core Data Models** (`skillmeat/core/artifact.py`, `skillmeat/core/collection.py`)

   Based on analysis, port and generalize from `models.py`:

   ```python
   # skillmeat/core/artifact.py

   @dataclass
   class ArtifactType(Enum):
       SKILL = "skill"
       COMMAND = "command"
       AGENT = "agent"
       # Future: MCP, HOOK

   @dataclass
   class ArtifactMetadata:
       """Extracted from artifact files (SKILL.md, COMMAND.md, AGENT.md)"""
       title: Optional[str]
       description: Optional[str]
       author: Optional[str]
       license: Optional[str]
       version: Optional[str]
       tags: List[str]
       dependencies: List[str]
       extra: Dict[str, Any]

   @dataclass
   class Artifact:
       """Unified artifact representation"""
       name: str
       type: ArtifactType
       path: Path  # relative to collection root
       origin: str  # "local", "github"
       upstream: Optional[str]  # GitHub URL
       version_spec: Optional[str]  # "latest", "v1.0.0", "branch-name"
       resolved_sha: Optional[str]
       resolved_version: Optional[str]
       metadata: ArtifactMetadata
       added: datetime
       last_updated: Optional[datetime]
       tags: List[str]

   @dataclass
   class Collection:
       """Personal collection of Claude artifacts"""
       name: str
       version: str  # collection format version
       artifacts: List[Artifact]
       created: datetime
       updated: datetime
   ```

2. **Implement Storage Layer**

   Port and adapt from `utils.py`:

   ```python
   # skillmeat/storage/manifest.py
   class ManifestManager:
       """Manages collection.toml files"""
       def read(self, path: Path) -> Collection
       def write(self, path: Path, collection: Collection) -> None
       def exists(self, path: Path) -> bool
       def create_empty(self, path: Path, name: str) -> Collection

   # skillmeat/storage/lockfile.py
   class LockManager:
       """Manages collection.lock files"""
       def read(self, path: Path) -> Dict[str, LockEntry]
       def write(self, path: Path, entries: Dict[str, LockEntry]) -> None
       def update_entry(self, path: Path, artifact: Artifact) -> None

   # skillmeat/storage/snapshot.py
   class SnapshotManager:
       """Manages collection snapshots"""
       def create_snapshot(self, collection_path: Path, message: str) -> Snapshot
       def list_snapshots(self, collection_path: Path) -> List[Snapshot]
       def restore_snapshot(self, snapshot_id: str, collection_path: Path) -> None
       def cleanup_old_snapshots(self, collection_path: Path, keep: int = 10) -> None
   ```

3. **Create TOML Format Specifications**

   Design `collection.toml` format:
   ```toml
   [collection]
   name = "default"
   version = "1.0.0"
   created = "2025-11-07T10:00:00Z"
   updated = "2025-11-07T14:30:00Z"

   [[artifacts]]
   name = "python-skill"
   type = "skill"
   path = "skills/python-skill/"
   origin = "github"
   upstream = "https://github.com/anthropics/skills/tree/main/python"
   version_spec = "latest"
   resolved_sha = "abc123def"
   resolved_version = "v2.1.0"
   added = "2025-11-07T10:30:00Z"
   last_updated = "2025-11-07T12:00:00Z"
   tags = ["python", "coding"]

   [[artifacts]]
   name = "custom-review"
   type = "command"
   path = "commands/custom-review.md"
   origin = "local"
   added = "2025-11-07T11:00:00Z"
   tags = ["review", "quality"]
   ```

**Deliverables:**
- [ ] Data models defined with full type hints
- [ ] ManifestManager implemented with tests
- [ ] LockManager implemented with tests
- [ ] SnapshotManager implemented with tests
- [ ] TOML serialization/deserialization working
- [ ] Git commit: "feat: implement data models and storage layer"

**Estimated Effort:** 3-4 days

---

### Phase 3: Source Abstraction & GitHub Integration (Week 2-3)

**Goal:** Create pluggable source system and adapt GitHub integration

#### Tasks

1. **Create Abstract Source Interface** (`skillmeat/sources/base.py`)

   ```python
   class ArtifactSource(ABC):
       """Abstract base for artifact sources"""

       @abstractmethod
       def fetch(self, spec: str, artifact_type: ArtifactType) -> FetchResult:
           """Fetch artifact from source"""
           pass

       @abstractmethod
       def check_updates(self, artifact: Artifact) -> Optional[UpdateInfo]:
           """Check if updates available"""
           pass

       @abstractmethod
       def validate(self, path: Path, artifact_type: ArtifactType) -> ValidationResult:
           """Validate artifact structure"""
           pass
   ```

2. **Port GitHub Source** (`skillmeat/sources/github.py`)

   Adapt from existing `github.py` (85% reusable):
   - Generalize `SkillSpec` → `ArtifactSpec`
   - Support artifact type detection
   - Enhance version resolution (tags, branches, SHAs)
   - Add rate limiting and retry logic

   ```python
   class GitHubSource(ArtifactSource):
       def __init__(self, github_token: Optional[str] = None):
           self.client = GitHubClient(github_token)

       def fetch(self, spec: str, artifact_type: ArtifactType) -> FetchResult:
           # Parse: username/repo/path/to/artifact[@version]
           # Clone repo, checkout version
           # Copy artifact to temp location
           # Extract metadata
           # Return FetchResult
           pass
   ```

3. **Implement Local Source** (`skillmeat/sources/local.py`)

   New implementation for adding from local filesystem:
   ```python
   class LocalSource(ArtifactSource):
       def fetch(self, path: str, artifact_type: ArtifactType) -> FetchResult:
           # Validate path exists
           # Detect artifact type if not specified
           # Extract metadata
           # Return FetchResult (no upstream tracking)
           pass

       def check_updates(self, artifact: Artifact) -> Optional[UpdateInfo]:
           # Local artifacts don't have upstream
           return None
   ```

4. **Implement Validators** (`skillmeat/utils/validator.py`)

   Port from `github.py` and generalize:
   ```python
   class ArtifactValidator:
       @staticmethod
       def validate_skill(path: Path) -> ValidationResult:
           """Validate SKILL.md presence and structure"""

       @staticmethod
       def validate_command(path: Path) -> ValidationResult:
           """Validate COMMAND.md or .md file"""

       @staticmethod
       def validate_agent(path: Path) -> ValidationResult:
           """Validate AGENT.md presence"""

       @staticmethod
       def validate(path: Path, artifact_type: ArtifactType) -> ValidationResult:
           """Route to appropriate validator"""
   ```

**Deliverables:**
- [ ] ArtifactSource abstract base class
- [ ] GitHubSource implemented and tested
- [ ] LocalSource implemented and tested
- [ ] ArtifactValidator for all 3 types
- [ ] Metadata extraction working
- [ ] Git commit: "feat: implement source abstraction and GitHub/local sources"

**Estimated Effort:** 4-5 days

---

### Phase 4: Core Collection Management (Week 3-4)

**Goal:** Implement collection creation, artifact management, and viewing

#### Tasks

1. **Implement CollectionManager** (`skillmeat/core/collection.py`)

   ```python
   class CollectionManager:
       """Manages collection lifecycle"""

       def __init__(self, config: ConfigManager):
           self.config = config
           self.manifest_mgr = ManifestManager()
           self.lock_mgr = LockManager()

       def init(self, name: str = "default") -> Collection:
           """Initialize new collection"""
           # Create ~/.skillmeat/collections/{name}/
           # Initialize collection.toml
           # Initialize collection.lock
           # Return Collection object

       def create(self, name: str) -> Collection:
           """Create named collection"""

       def list_collections(self) -> List[str]:
           """List all collections"""

       def get_active_collection(self) -> str:
           """Get current active collection name"""

       def switch_collection(self, name: str) -> None:
           """Switch active collection"""

       def load_collection(self, name: str) -> Collection:
           """Load collection from disk"""

       def save_collection(self, collection: Collection) -> None:
           """Save collection to disk"""
   ```

2. **Implement ArtifactManager** (`skillmeat/core/artifact.py`)

   ```python
   class ArtifactManager:
       """Manages artifacts within collection"""

       def __init__(self, collection_mgr: CollectionManager):
           self.collection_mgr = collection_mgr
           self.github_source = GitHubSource()
           self.local_source = LocalSource()

       def add_from_github(
           self,
           spec: str,
           artifact_type: ArtifactType,
           collection_name: str,
           custom_name: Optional[str] = None,
           tags: List[str] = []
       ) -> Artifact:
           """Add artifact from GitHub"""
           # Fetch from GitHub source
           # Validate artifact
           # Copy to collection directory
           # Update collection.toml
           # Update collection.lock
           # Return Artifact object

       def add_from_local(
           self,
           path: str,
           artifact_type: ArtifactType,
           collection_name: str,
           custom_name: Optional[str] = None,
           tags: List[str] = []
       ) -> Artifact:
           """Add artifact from local filesystem"""

       def remove(self, artifact_name: str, collection_name: str) -> None:
           """Remove artifact from collection"""

       def list_artifacts(
           self,
           collection_name: str,
           artifact_type: Optional[ArtifactType] = None,
           tags: Optional[List[str]] = None
       ) -> List[Artifact]:
           """List artifacts with optional filters"""

       def show(self, artifact_name: str, collection_name: str) -> Artifact:
           """Get detailed artifact information"""

       def check_updates(self, collection_name: str) -> Dict[str, UpdateInfo]:
           """Check all artifacts for updates"""

       def update(
           self,
           artifact_name: str,
           collection_name: str,
           strategy: str = "prompt"
       ) -> Artifact:
           """Update artifact from upstream"""
   ```

3. **Port Installer Logic** (`skillmeat/utils/filesystem.py`)

   Port from `installer.py` (95% reusable):
   ```python
   class FilesystemManager:
       """Handles file operations for artifacts"""

       IGNORE_PATTERNS = {
           ".git", ".github", ".gitignore",
           "__pycache__", "node_modules", ".venv",
           "*.egg-info", ".DS_Store"
       }

       @staticmethod
       def copy_artifact(
           source: Path,
           destination: Path,
           artifact_type: ArtifactType
       ) -> None:
           """Copy artifact files atomically"""
           # Use temp directory
           # Copy with ignore patterns
           # Atomic rename

       @staticmethod
       def remove_artifact(path: Path) -> None:
           """Remove artifact files safely"""
   ```

**Deliverables:**
- [ ] CollectionManager implemented
- [ ] ArtifactManager implemented
- [ ] FilesystemManager ported and adapted
- [ ] Unit tests for all managers
- [ ] Integration test: init → add → list → show workflow
- [ ] Git commit: "feat: implement collection and artifact management"

**Estimated Effort:** 5-6 days

---

### Phase 5: Deployment & Tracking (Week 5-6)

**Goal:** Deploy artifacts to projects and track deployments

#### Tasks

1. **Implement DeploymentManager** (`skillmeat/core/deployment.py`)

   ```python
   class DeploymentManager:
       """Manages artifact deployment to projects"""

       def deploy_artifacts(
           self,
           artifact_names: List[str],
           collection_name: str,
           project_path: Optional[Path] = None,
           interactive: bool = False
       ) -> List[Deployment]:
           """Deploy artifacts to project"""
           # Load collection
           # Find artifacts
           # Copy to .claude/ directory structure
           # Create/update .skillmeat-deployed.toml
           # Return deployment records

       def deploy_all(
           self,
           collection_name: str,
           project_path: Optional[Path] = None
       ) -> List[Deployment]:
           """Deploy entire collection"""

       def undeploy(
           self,
           artifact_name: str,
           project_path: Optional[Path] = None
       ) -> None:
           """Remove artifact from project"""

       def list_deployments(
           self,
           project_path: Optional[Path] = None
       ) -> List[Deployment]:
           """List deployed artifacts in project"""

       def check_deployment_status(
           self,
           project_path: Optional[Path] = None
       ) -> Dict[str, str]:
           """Check sync status (modified, synced, outdated)"""
   ```

2. **Create Deployment Tracking** (`skillmeat/storage/deployment.py`)

   ```python
   class DeploymentTracker:
       """Tracks artifact deployments"""

       def record_deployment(
           self,
           project_path: Path,
           artifact: Artifact,
           collection_name: str
       ) -> None:
           """Record deployment in .skillmeat-deployed.toml"""

       def get_deployments(self, project_path: Path) -> List[Deployment]:
           """Read deployment records"""

       def detect_modifications(
           self,
           project_path: Path,
           artifact_name: str
       ) -> bool:
           """Check if deployed artifact was modified"""
   ```

3. **Implement Interactive Selection**

   Add interactive mode using Rich prompts:
   ```python
   def interactive_deploy(collection: Collection) -> List[str]:
       """Interactive artifact selection"""
       # Display artifacts grouped by type
       # Checkbox selection using Rich
       # Return selected artifact names
   ```

**Deliverables:**
- [ ] DeploymentManager implemented
- [ ] DeploymentTracker implemented
- [ ] Interactive selection mode working
- [ ] Deployment tracking TOML format defined
- [ ] Tests for deployment workflows
- [ ] Git commit: "feat: implement deployment and tracking system"

**Estimated Effort:** 4-5 days

---

### Phase 6: Versioning & Snapshots (Week 6-7)

**Goal:** Implement collection versioning with snapshots and rollback

#### Tasks

1. **Implement VersionManager** (`skillmeat/core/version.py`)

   ```python
   class VersionManager:
       """Manages collection versioning and snapshots"""

       def create_snapshot(
           self,
           collection_name: str,
           message: str
       ) -> Snapshot:
           """Create collection snapshot"""
           # Read current collection state
           # Create tarball of collection directory
           # Store in ~/.skillmeat/snapshots/{collection}/
           # Update snapshots.toml
           # Return Snapshot object

       def list_snapshots(self, collection_name: str) -> List[Snapshot]:
           """List all snapshots"""

       def rollback(
           self,
           snapshot_id: str,
           collection_name: str,
           confirm: bool = True
       ) -> None:
           """Rollback to snapshot"""
           # Create safety snapshot first
           # Extract snapshot tarball
           # Replace collection directory
           # Reload collection

       def auto_snapshot(self, collection_name: str) -> Snapshot:
           """Create automatic snapshot before destructive ops"""

       def cleanup_snapshots(
           self,
           collection_name: str,
           keep_count: int = 10
       ) -> None:
           """Remove old snapshots"""
   ```

2. **Integrate Auto-Snapshots**

   Add automatic snapshots before:
   - Artifact updates
   - Artifact removals
   - Rollbacks

   ```python
   # In ArtifactManager.update()
   version_mgr.auto_snapshot(collection_name)
   # Then proceed with update
   ```

**Deliverables:**
- [ ] VersionManager implemented
- [ ] SnapshotManager enhanced with tarball operations
- [ ] Auto-snapshot integration in ArtifactManager
- [ ] Snapshot cleanup logic
- [ ] Tests for versioning workflows
- [ ] Git commit: "feat: implement versioning and snapshot system"

**Estimated Effort:** 3-4 days

---

### Phase 7: CLI Refactoring (Week 7)

**Goal:** Refactor CLI to use new architecture

#### Tasks

1. **Refactor Command Structure**

   Create modular command groups:
   ```python
   # skillmeat/cli.py

   @click.group()
   def main():
       """SkillMeat: Personal collection manager for Claude artifacts"""

   # Collection commands
   @main.group()
   def collection():
       """Manage collections"""

   @collection.command("create")
   def collection_create(name: str):
       """Create new collection"""

   # Artifact commands
   @main.group()
   def add():
       """Add artifacts to collection"""

   @add.command("skill")
   def add_skill(spec: str, ...):
       """Add skill from GitHub or local path"""

   @add.command("command")
   def add_command(spec: str, ...):
       """Add command from GitHub or local path"""

   # Deployment commands
   @main.command()
   def deploy(artifacts: List[str], ...):
       """Deploy artifacts to project"""

   # Versioning commands
   @main.command()
   def snapshot(message: str):
       """Create collection snapshot"""
   ```

2. **Update Existing Commands**

   Map old skillman commands to new architecture:
   - `skillmeat init` → `CollectionManager.init()`
   - `skillmeat add skill <spec>` → `ArtifactManager.add_from_github()`
   - `skillmeat list` → `ArtifactManager.list_artifacts()`
   - `skillmeat show <name>` → `ArtifactManager.show()`
   - `skillmeat deploy <name>` → `DeploymentManager.deploy_artifacts()`
   - `skillmeat update <name>` → `ArtifactManager.update()`
   - `skillmeat snapshot` → `VersionManager.create_snapshot()`

3. **Add New Commands**

   Implement new MVP commands:
   - `skillmeat collection create <name>`
   - `skillmeat collection list`
   - `skillmeat collection use <name>`
   - `skillmeat add command <spec>`
   - `skillmeat add agent <spec>`
   - `skillmeat status` → Check update status
   - `skillmeat history` → List snapshots
   - `skillmeat rollback <id>` → Restore snapshot
   - `skillmeat undeploy <name>` → Remove from project

**Deliverables:**
- [ ] CLI refactored to new architecture
- [ ] All MVP commands implemented
- [ ] Help text updated for all commands
- [ ] Rich output formatting consistent
- [ ] Security warnings preserved
- [ ] Git commit: "feat: refactor CLI to new architecture"

**Estimated Effort:** 4-5 days

---

### Phase 8: Testing & Documentation (Week 8)

**Goal:** Comprehensive testing and documentation

#### Tasks

1. **Write Unit Tests**

   Target: >80% coverage
   - `tests/unit/test_collection.py` - CollectionManager
   - `tests/unit/test_artifact.py` - ArtifactManager
   - `tests/unit/test_deployment.py` - DeploymentManager
   - `tests/unit/test_version.py` - VersionManager
   - `tests/unit/test_github_source.py` - GitHubSource
   - `tests/unit/test_local_source.py` - LocalSource
   - `tests/unit/test_manifest.py` - ManifestManager
   - `tests/unit/test_lockfile.py` - LockManager
   - `tests/unit/test_snapshot.py` - SnapshotManager

2. **Write Integration Tests**

   - `tests/integration/test_cli.py` - All CLI commands
   - `tests/integration/test_workflows.py` - End-to-end workflows:
     - Init → Add (GitHub) → List → Deploy → Update
     - Init → Add (Local) → Deploy → Snapshot → Rollback
     - Multiple collections workflow

3. **Create Test Fixtures**

   ```
   tests/fixtures/
   ├── sample_skills/
   │   └── test-skill/
   │       └── SKILL.md
   ├── sample_commands/
   │   └── test-command.md
   └── sample_agents/
       └── test-agent.md
   ```

4. **Update Documentation**

   - `README.md` - Quickstart, installation, basic usage
   - `docs/user/cli/commands.md` - Complete command reference
   - `docs/dev/architecture/` - Already created by subagents
   - `docs/user/migration/README.md` - Migration from skillman guide
   - `docs/user/examples.md` - Common workflows

5. **Create Migration Tool**

   ```python
   @main.command()
   def migrate(from_skillman: str):
       """Migrate from skillman to skillmeat"""
       # Detect skillman installation
       # Create default collection
       # Import skills.toml → collection.toml
       # Convert Skill → Artifact data model
       # Preserve upstream tracking
       # Create initial snapshot
   ```

**Deliverables:**
- [ ] >80% test coverage
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Migration tool working
- [ ] Examples documented
- [ ] Git commit: "test: comprehensive test suite and documentation"

**Estimated Effort:** 5-6 days

---

### Phase 9: Polish & Release Preparation (Week 8)

**Goal:** Final polish and prepare for alpha release

#### Tasks

1. **Update CI/CD**

   - Update GitHub Actions workflow
   - Test on Python 3.9, 3.10, 3.11, 3.12
   - Test on Ubuntu, Windows, macOS
   - Add codecov integration
   - Add package build job

2. **Code Quality**

   - Run Black formatter
   - Run flake8 linter
   - Run mypy type checker
   - Fix all issues

3. **Security Audit**

   - Review all input validation
   - Check for path traversal vulnerabilities
   - Ensure token security
   - Review file permissions

4. **Performance Testing**

   - Benchmark collection operations
   - Test with large collections (100+ artifacts)
   - Optimize slow operations

5. **Package Preparation**

   - Update `pyproject.toml` metadata
   - Create `CHANGELOG.md`
   - Update version to `0.1.0-alpha`
   - Build distribution packages
   - Test installation via pip

**Deliverables:**
- [ ] CI/CD pipeline updated and passing
- [ ] Code quality checks passing
- [ ] Security audit complete
- [ ] Performance acceptable
- [ ] Package ready for distribution
- [ ] Git commit: "chore: prepare for 0.1.0-alpha release"

**Estimated Effort:** 3-4 days

---

## Success Criteria

### MVP Launch Checklist

**Core Features:**
- [x] Collection initialization (`skillmeat init`)
- [x] Named collections (`skillmeat collection create/list/use`)
- [x] Add artifacts from GitHub (Skills, Commands, Agents)
- [x] Add artifacts from local filesystem
- [x] List artifacts with filtering
- [x] Show artifact details
- [x] Deploy to projects
- [x] Deployment tracking
- [x] Check for updates
- [x] Update artifacts
- [x] Create snapshots
- [x] List snapshot history
- [x] Rollback to snapshot
- [x] Remove artifacts
- [x] Configuration management

**Quality:**
- [x] >80% test coverage
- [x] All tests passing on CI
- [x] Type checking passes
- [x] Linting passes
- [x] Documentation complete
- [x] Migration tool working

**Performance:**
- [x] Collection list <500ms for 100 artifacts
- [x] Deploy <5s for 10 artifacts
- [x] Update check <10s for 20 GitHub sources

---

## Risk Mitigation

| Risk | Mitigation Strategy |
|------|---------------------|
| **Scope Creep** | Strict adherence to MVP feature list; defer Phase 2/3 |
| **GitHub Rate Limits** | Implement caching, support tokens, exponential backoff |
| **Migration Complexity** | Provide clear migration guide and automated tool |
| **Breaking Changes** | Offer backward compatibility mode for skillman users |
| **Testing Gaps** | Achieve >80% coverage before launch |

---

## Dependencies & Blockers

**External Dependencies:**
- GitHub API availability
- Python ecosystem stability
- Claude Code compatibility

**Internal Dependencies:**
- Phase 1-2 must complete before Phase 3
- Phase 3-4 must complete before Phase 5
- All core phases before CLI refactoring

**Potential Blockers:**
- Design decisions on open questions (artifact naming, update strategies)
- GitHub API changes
- Claude Code format changes

---

## Timeline Summary

| Week | Phase | Key Deliverables |
|------|-------|------------------|
| 1 | Foundation & Data Models | Package structure, models, storage layer |
| 2 | Sources & GitHub | Source abstraction, GitHub/local sources |
| 3-4 | Collection Management | CollectionManager, ArtifactManager |
| 5-6 | Deployment | DeploymentManager, tracking system |
| 6-7 | Versioning | VersionManager, snapshots, rollback |
| 7 | CLI Refactoring | All commands updated to new architecture |
| 8 | Testing & Polish | Tests, docs, migration tool, release prep |

---

## Next Steps

1. **Review and Approve** this implementation plan
2. **Make Design Decisions** on open questions (see Architecture docs)
3. **Begin Phase 1** - Foundation & Package Structure
4. **Set Up Project Board** to track tasks
5. **Schedule Weekly Reviews** to assess progress

---

## Appendix: Command Mapping

### Old (skillman) → New (skillmeat)

| skillman Command | skillmeat Command | Notes |
|------------------|-------------------|-------|
| `skillman init` | `skillmeat init` | Creates default collection |
| `skillman add <spec>` | `skillmeat add skill <spec>` | Type-specific |
| - | `skillmeat add command <spec>` | New |
| - | `skillmeat add agent <spec>` | New |
| `skillman remove <name>` | `skillmeat remove <name>` | Same |
| `skillman list` | `skillmeat list` | Enhanced filtering |
| `skillman show <name>` | `skillmeat show <name>` | Same |
| `skillman update <name>` | `skillmeat update <name>` | Enhanced with strategies |
| `skillman verify <spec>` | `skillmeat verify <spec>` | Same |
| `skillman config` | `skillmeat config` | Same |
| - | `skillmeat collection create <name>` | New |
| - | `skillmeat collection list` | New |
| - | `skillmeat collection use <name>` | New |
| - | `skillmeat deploy <name>` | New |
| - | `skillmeat status` | New |
| - | `skillmeat snapshot [msg]` | New |
| - | `skillmeat history` | New |
| - | `skillmeat rollback <id>` | New |
| - | `skillmeat migrate --from-skillman` | New |

---

**End of Implementation Plan**
