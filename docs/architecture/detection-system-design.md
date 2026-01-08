# Unified Artifact Detection System

## Overview

The Unified Artifact Detection system is the core component responsible for identifying and classifying Claude Code artifacts (skills, agents, commands, etc.) within the SkillMeat ecosystem. It provides a shared set of types, rules, and logic used across the CLI (discovery), the Marketplace (heuristic detection), and the API (validation).

This system ensures that an artifact identified as a "skill" in the local filesystem is treated identically by the deployment engine and the web marketplace.

## Architecture

The system is centered around `skillmeat/core/artifact_detection.py`, which acts as the canonical source of truth for all artifact metadata and detection logic.

```
                    artifact_detection.py (Core)
                    ├── ArtifactType enum
                    ├── DetectionResult
                    ├── ARTIFACT_SIGNATURES
                    └── Detection functions
                              │
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓
   discovery.py      heuristic_detector.py    validator.py
   (strict mode)      (heuristic mode)      (validation)
```

## Key Design Decisions

- **Single Source of Truth**: All artifact types and their structural rules are defined in one module, eliminating duplication and drift between different parts of the system.
- **Centralized Types**: The `ArtifactType` enum is the canonical definition for all artifact categories, supporting both primary deployable artifacts (skills, agents) and context entities (specs, rules).
- **Signature-Based Logic**: Uses `ArtifactSignature` dataclasses to define the "fingerprint" of each artifact type, including valid container names, manifest requirements, and nesting rules.
- **Data-Driven Configuration**: A registry-based approach (`ARTIFACT_SIGNATURES`) separates the definition of artifact types from the logic used to detect them.

## Detection Modes

The system supports two primary modes of operation to balance safety and flexibility:

### Strict Mode
Used by local discovery and validators.
- **Strict Validation**: Requires high confidence (70+) based on exact structural matches.
- **Mandatory Manifests**: Fails if a required manifest (like `SKILL.md`) is missing.
- **Error-First**: Raises a `DetectionError` if an artifact cannot be confidently identified.
- **Consistency**: Ensures that only valid, well-formed artifacts are processed by the deployment engine.

### Heuristic Mode
Used by the marketplace and external source imports (e.g., GitHub scrapers).
- **Best Guess**: Provides a classification even with limited information.
- **Confidence Scoring**: Returns a `DetectionResult` with a confidence score from 0-100.
- **Fuzzy Matching**: Allows for non-standard directory structures or missing manifest files.
- **Discovery-First**: Optimized for finding potential artifacts in unknown repositories.

## Future Extensibility

Adding support for a new artifact type (e.g., a new Claude Code extension type) is a declarative process:

1.  **Update Enum**: Add the new type to the `ArtifactType` enum.
2.  **Define Signature**: Create an `ArtifactSignature` in the `ARTIFACT_SIGNATURES` registry defining its structure (e.g., is it a file or directory?).
3.  **Register Containers**: Add valid directory names to `CONTAINER_ALIASES` and define the `CANONICAL_CONTAINERS` mapping.
4.  **Register Manifests**: If the type uses a specific manifest file (e.g., `CONFIG.json`), add it to `MANIFEST_FILES`.

Once registered, the core `detect_artifact` and `infer_artifact_type` functions will automatically support the new type across the entire application.

## Component Interactions

- **`skillmeat/core/discovery.py`**: Uses `detect_artifact(mode="strict")` to find artifacts in local project directories for deployment.
- **`skillmeat/marketplace/heuristic_detector.py`**: Uses `detect_artifact(mode="heuristic")` to crawl GitHub repositories and identify potential artifacts for the marketplace.
- **`skillmeat/api/validators/`**: Uses `ArtifactType` and signatures to validate incoming requests and ensure artifacts match their declared types.
