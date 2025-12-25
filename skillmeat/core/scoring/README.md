# Artifact Scoring System

Confidence and quality scoring infrastructure for SkillMeat artifacts.

## Components

### ContextBooster

Context-aware scoring that boosts artifacts matching the current project's technology stack.

**Features**:
- Detects project type from manifest files (package.json, pyproject.toml, Cargo.toml, etc.)
- Boosts artifact scores when they match detected language/framework
- Configurable boost multiplier (default 1.1x, max 1.2x)
- Lazy initialization and caching of project context

**Supported Project Types**:
- **JavaScript/TypeScript**: package.json (React, Vue, Angular, Next.js, Express)
- **Python**: pyproject.toml, requirements.txt, setup.py (FastAPI, Django, Flask)
- **Rust**: Cargo.toml (Actix-web, Rocket)
- **Go**: go.mod (Gin, Echo)
- **Java**: pom.xml (Maven), build.gradle (Gradle)
- **Claude Code**: .claude/settings.local.json

**Usage**:
```python
from skillmeat.core.scoring import ContextBooster
from skillmeat.core.artifact import ArtifactMetadata

# Auto-detect project type from current directory
booster = ContextBooster()

# Or specify project root
booster = ContextBooster(project_root=Path("/path/to/project"))

# Custom boost multiplier
booster = ContextBooster(boost_multiplier=1.15)  # 15% boost

# Get boost for artifact
artifact = ArtifactMetadata(
    title="React Hooks",
    tags=["react", "hooks"]
)
boost = booster.get_boost(artifact)  # 1.1 in React project, 1.0 otherwise

# Apply boost to score
boosted_score = booster.apply_boost(artifact, base_score=75.0)
```

**Detection Logic**:
1. Search for manifest files in project root
2. Extract language/framework from dependencies
3. Match artifact tags/description against detected context
4. Return boost multiplier (1.0 = no boost, 1.1-1.2 = boosted)

**Example**:
```python
# React project with package.json
booster = ContextBooster(project_root=Path("./my-react-app"))
context = booster.context
# ProjectContext(language="javascript", framework="react", package_manager="npm")

react_artifact = ArtifactMetadata(title="React Component", tags=["react"])
python_artifact = ArtifactMetadata(title="Python Tool", tags=["python"])

booster.get_boost(react_artifact)   # 1.1 (boosted)
booster.get_boost(python_artifact)  # 1.0 (not boosted)
```

### QualityScorer

Artifact quality scoring based on metadata completeness and documentation.

(See existing implementation in quality_scorer.py)

### Models

Core data models for scoring:
- `ArtifactScore`: Combined score with quality and context components
- `UserRating`: User-submitted ratings
- `CommunityScore`: Aggregated community metrics

## Testing

Run tests with coverage:
```bash
pytest tests/test_context_booster.py -v --cov=skillmeat.core.scoring.context_booster
```

Run demo:
```bash
python examples/context_booster_demo.py
```

## Implementation Status

- [x] Phase 0-1: QualityScorer foundation
- [x] Phase 2: ContextBooster (P2-T3)
- [ ] Phase 3: Integration with recommendation system
- [ ] Phase 4: Community scoring and user ratings
