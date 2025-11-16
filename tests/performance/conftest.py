"""Fixtures for performance benchmarks.

This module provides fixtures for generating large datasets (500+ artifacts)
and other benchmark-specific utilities.
"""

import hashlib
import random
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w


# Sample skill content templates for variety
SKILL_TEMPLATES = [
    """---
title: {title}
description: {description}
license: MIT
author: Benchmark Generator
version: {version}
tags:
  - {tag1}
  - {tag2}
---

# {title}

{description}

## Usage

{usage_instructions}

## Features

{features}

## Examples

```python
{example_code}
```

## Notes

{notes}
""",
    """---
title: {title}
description: {description}
version: {version}
---

# {title}

This is a skill for {purpose}.

## Overview

{overview}

## Configuration

{config}
""",
]

# Sample content generators
DESCRIPTIONS = [
    "A powerful tool for data analysis and visualization",
    "Automate your development workflow with this utility",
    "Advanced text processing and manipulation",
    "API integration and testing framework",
    "Database migration and schema management",
    "Code generation and scaffolding",
    "Documentation generator with markdown support",
    "Testing utilities and assertion helpers",
    "Performance monitoring and profiling",
    "Security scanning and vulnerability detection",
]

TAGS = [
    "python", "javascript", "testing", "documentation", "automation",
    "database", "api", "security", "performance", "utilities",
    "productivity", "development", "devops", "ci-cd", "monitoring"
]

USAGE_INSTRUCTIONS = [
    "Simply invoke this skill and follow the interactive prompts.",
    "Configure the settings in config.yaml and run the main command.",
    "Import the module and call the main function with your parameters.",
    "Use the CLI interface to interact with this skill.",
]

FEATURES = [
    "- Fast processing with optimized algorithms\n- Comprehensive error handling\n- Extensible plugin architecture",
    "- Easy to use API\n- Rich command-line interface\n- Detailed logging and debugging",
    "- Production-ready code\n- Well-tested and documented\n- Active community support",
]


def generate_artifact_name(index: int, artifact_type: str) -> str:
    """Generate a unique artifact name."""
    prefixes = {
        "skill": ["analyze", "process", "generate", "validate", "transform"],
        "command": ["run", "execute", "build", "deploy", "test"],
        "agent": ["monitor", "orchestrate", "manage", "coordinate", "supervise"],
    }
    suffixes = ["tool", "helper", "utility", "framework", "engine"]

    prefix = random.choice(prefixes.get(artifact_type, ["generic"]))
    suffix = random.choice(suffixes)

    return f"{prefix}-{suffix}-{index:04d}"


def generate_skill_content(name: str, index: int) -> str:
    """Generate realistic skill content."""
    template = random.choice(SKILL_TEMPLATES)

    context = {
        "title": name.replace("-", " ").title(),
        "description": random.choice(DESCRIPTIONS),
        "version": f"{random.randint(0, 3)}.{random.randint(0, 20)}.{random.randint(0, 10)}",
        "tag1": random.choice(TAGS),
        "tag2": random.choice(TAGS[::-1]),  # Reverse to get different tags
        "usage_instructions": random.choice(USAGE_INSTRUCTIONS),
        "features": random.choice(FEATURES),
        "example_code": f"result = {name.replace('-', '_')}(input_data)\nprint(result)",
        "notes": f"Generated for benchmark testing. Index: {index}",
        "purpose": random.choice(DESCRIPTIONS).lower(),
        "overview": "This skill provides comprehensive functionality for various use cases.",
        "config": "See config.example.yaml for configuration options.",
    }

    content = template.format(**context)

    # Add variable length padding to create different file sizes
    if index % 3 == 0:
        # Small files (~1-5 KB)
        padding_size = random.randint(100, 500)
    elif index % 3 == 1:
        # Medium files (~10-50 KB)
        padding_size = random.randint(1000, 5000)
    else:
        # Large files (~100-500 KB)
        padding_size = random.randint(10000, 50000)

    padding = "\n".join([f"# Padding line {i}" for i in range(padding_size)])
    content += f"\n\n## Additional Content\n\n{padding}\n"

    return content


def generate_command_content(name: str, index: int) -> str:
    """Generate realistic command content."""
    return f"""# {name.replace('-', ' ').title()}

This is a command for automation and workflow management.

## Usage

```bash
{name} --option value
```

## Options

- `--verbose`: Enable verbose output
- `--config PATH`: Path to configuration file
- `--output PATH`: Output directory

## Examples

```bash
{name} --config config.yaml --output ./results
```

## Index: {index}
"""


def generate_agent_content(name: str, index: int) -> str:
    """Generate realistic agent content."""
    return f"""# {name.replace('-', ' ').title()}

This is an agent for intelligent task coordination.

## Capabilities

- Task scheduling and execution
- Resource monitoring
- Error recovery
- Performance optimization

## Configuration

```yaml
agent:
  name: {name}
  max_workers: 4
  timeout: 300
```

## Index: {index}
"""


@pytest.fixture(scope="session")
def large_collection_500(tmp_path_factory) -> Path:
    """Generate a collection with 500 artifacts for performance testing.

    This fixture creates a realistic collection with:
    - 300 skills (60%)
    - 100 commands (20%)
    - 100 agents (20%)
    - Varying file sizes (1KB to 500KB)
    - Realistic metadata

    Returns:
        Path to the generated collection directory
    """
    collection_dir = tmp_path_factory.mktemp("large_collection_500")

    # Distribution: 300 skills, 100 commands, 100 agents
    artifact_counts = {
        "skill": 300,
        "command": 100,
        "agent": 100,
    }

    index = 0
    for artifact_type, count in artifact_counts.items():
        for i in range(count):
            name = generate_artifact_name(index, artifact_type)
            artifact_path = collection_dir / artifact_type / name
            artifact_path.mkdir(parents=True, exist_ok=True)

            # Create main metadata file
            if artifact_type == "skill":
                metadata_file = artifact_path / "SKILL.md"
                content = generate_skill_content(name, index)
            elif artifact_type == "command":
                metadata_file = artifact_path / "COMMAND.md"
                content = generate_command_content(name, index)
            else:  # agent
                metadata_file = artifact_path / "AGENT.md"
                content = generate_agent_content(name, index)

            metadata_file.write_text(content)

            # Add some additional files to some artifacts (30%)
            if random.random() < 0.3:
                (artifact_path / "README.md").write_text(f"# {name}\n\nAdditional documentation.")
                (artifact_path / "config.yaml").write_text(f"name: {name}\nenabled: true\n")

            # Add Python files to some artifacts (20%)
            if random.random() < 0.2:
                (artifact_path / "main.py").write_text(
                    f'"""Main module for {name}."""\n\ndef main():\n    pass\n'
                )

            index += 1

    return collection_dir


@pytest.fixture(scope="session")
def modified_collection_500(tmp_path_factory, large_collection_500: Path) -> Path:
    """Generate a modified version of the large collection with 10% changes.

    This simulates drift/changes for sync and diff benchmarks.

    Returns:
        Path to the modified collection directory
    """
    modified_dir = tmp_path_factory.mktemp("modified_collection_500")

    # Copy the entire collection
    shutil.copytree(large_collection_500, modified_dir, dirs_exist_ok=True)

    # Modify ~10% of artifacts (50 artifacts)
    all_artifacts = list(modified_dir.rglob("*/SKILL.md")) + \
                    list(modified_dir.rglob("*/COMMAND.md")) + \
                    list(modified_dir.rglob("*/AGENT.md"))

    artifacts_to_modify = random.sample(all_artifacts, min(50, len(all_artifacts)))

    for artifact_file in artifacts_to_modify:
        content = artifact_file.read_text()
        # Append modification marker
        modified_content = content + f"\n\n## MODIFIED: {datetime.now().isoformat()}\n"
        artifact_file.write_text(modified_content)

    return modified_dir


@pytest.fixture(scope="session")
def large_analytics_dataset(tmp_path_factory) -> Path:
    """Generate a large analytics dataset with 10k events.

    Returns:
        Path to the analytics events.db directory
    """
    analytics_dir = tmp_path_factory.mktemp("analytics_10k")
    events_file = analytics_dir / "events.db"

    # Generate 10,000 events
    events = []
    start_date = datetime.now() - timedelta(days=30)

    event_types = ["artifact_added", "artifact_deployed", "artifact_updated",
                   "sync_performed", "search_executed", "diff_performed"]
    artifact_names = [f"test-artifact-{i:04d}" for i in range(100)]

    for i in range(10000):
        event_time = start_date + timedelta(seconds=i * 259)  # ~30 days spread
        event = {
            "timestamp": event_time.isoformat(),
            "event_type": random.choice(event_types),
            "artifact_name": random.choice(artifact_names),
            "metadata": {
                "user": "benchmark_user",
                "session_id": f"session-{i // 100}",
                "success": random.random() > 0.05,  # 95% success rate
            }
        }
        events.append(event)

    # Write as JSON lines
    with events_file.open("w") as f:
        for event in events:
            f.write(f"{event}\n")

    return analytics_dir


@pytest.fixture
def benchmark_skill_dir(tmp_path: Path) -> Path:
    """Create a single skill directory for isolated benchmarks."""
    skill_dir = tmp_path / "benchmark-skill"
    skill_dir.mkdir()

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
title: Benchmark Skill
description: A skill for benchmarking
version: 1.0.0
tags:
  - testing
  - benchmark
---

# Benchmark Skill

This skill is used for performance benchmarking.
""")

    return skill_dir


@pytest.fixture
def benchmark_collection_dir(tmp_path: Path) -> Path:
    """Create a small collection directory for setup benchmarks."""
    collection_dir = tmp_path / "benchmark_collection"
    collection_dir.mkdir()

    # Create a manifest
    manifest_file = collection_dir / "collection.toml"
    manifest_data = {
        "collection": {
            "name": "benchmark-collection",
            "version": "1.0.0",
        }
    }
    manifest_file.write_bytes(tomli_w.dumps(manifest_data).encode())

    return collection_dir
