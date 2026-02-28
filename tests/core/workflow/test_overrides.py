"""Tests for skillmeat.core.workflow.overrides.

Coverage:
  load_project_overrides:
    - Returns None when no override file exists
    - Loads and returns the full overrides mapping when workflow_id is None
    - Returns per-workflow block when workflow_id is provided
    - Returns None when workflow_id has no matching block
    - Raises WorkflowOverrideError on YAML parse failure
    - Raises WorkflowOverrideError when file lacks top-level 'overrides' key
    - Raises WorkflowOverrideError when 'overrides' value is not a dict
    - Raises WorkflowOverrideError when block contains unknown top-level keys
    - Raises WorkflowOverrideError when stage override touches protected id field
    - Raises WorkflowOverrideError when stage override touches protected depends_on field
    - Raises WorkflowOverrideError when stage override touches protected type field
    - Raises WorkflowOverrideError when workflow override touches protected id field
    - Handles empty override file gracefully (returns None)

  apply_overrides:
    - Returns deep copy of base when overrides is empty
    - Replaces scalar leaf values
    - Merges nested dicts recursively
    - Replaces lists entirely (not appended)
    - Adds keys that exist in override but not in base
    - Preserves keys that exist in base but not in override
    - Applies stage overrides by stage id matching
    - Raises WorkflowOverrideError for unknown stage id in stages override
    - Applies context module override (full replacement)
    - Applies config parameter default override (deep merge)
    - Ignores unknown top-level override keys (logs warning)

  _deep_merge:
    - Dicts merged recursively (nested)
    - Lists replaced entirely
    - Scalars replaced
    - Keys only in base preserved
    - Keys only in override added
    - Inputs are not mutated
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any, Dict

import pytest

from skillmeat.core.workflow.overrides import (
    OVERRIDE_FILENAME,
    WorkflowOverrideError,
    _deep_merge,
    _merge_stages,
    apply_overrides,
    load_project_overrides,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def write_override_file(tmp_path: Path, content: str) -> Path:
    """Write a .skillmeat-workflow-overrides.yaml file and return its path."""
    f = tmp_path / OVERRIDE_FILENAME
    f.write_text(textwrap.dedent(content), encoding="utf-8")
    return f


MINIMAL_BASE: Dict[str, Any] = {
    "workflow": {
        "id": "my-workflow",
        "name": "My Workflow",
        "version": "1.0.0",
        "description": "Test workflow",
    },
    "stages": [
        {
            "id": "research",
            "name": "Research",
            "type": "agent",
            "depends_on": [],
            "roles": {
                "primary": {
                    "artifact": "agent:researcher-v1",
                    "model": "opus",
                },
                "tools": ["skill:web-search"],
            },
        },
        {
            "id": "implement",
            "name": "Implement",
            "type": "agent",
            "depends_on": ["research"],
            "roles": {
                "primary": {
                    "artifact": "agent:developer-v1",
                    "model": "opus",
                },
                "tools": [],
            },
        },
    ],
    "context": {
        "global_modules": ["ctx:repo-rules"],
    },
    "config": {
        "parameters": {
            "feature_name": {
                "type": "string",
                "required": True,
            },
            "target_branch": {
                "type": "string",
                "default": "main",
            },
        },
    },
}


# ---------------------------------------------------------------------------
# _deep_merge tests
# ---------------------------------------------------------------------------


class TestDeepMerge:
    def test_scalar_replacement(self) -> None:
        base = {"a": 1, "b": "hello"}
        override = {"b": "world"}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": "world"}

    def test_nested_dict_merged_recursively(self) -> None:
        base = {"outer": {"a": 1, "b": 2}}
        override = {"outer": {"b": 99, "c": 3}}
        result = _deep_merge(base, override)
        assert result == {"outer": {"a": 1, "b": 99, "c": 3}}

    def test_list_replaced_entirely(self) -> None:
        base = {"items": [1, 2, 3]}
        override = {"items": [7, 8]}
        result = _deep_merge(base, override)
        assert result == {"items": [7, 8]}

    def test_key_only_in_base_preserved(self) -> None:
        base = {"a": 1, "b": 2}
        override = {"a": 10}
        result = _deep_merge(base, override)
        assert result["b"] == 2

    def test_key_only_in_override_added(self) -> None:
        base = {"a": 1}
        override = {"b": 2}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 2}

    def test_inputs_not_mutated(self) -> None:
        base = {"a": {"nested": 1}}
        override = {"a": {"nested": 99}}
        result = _deep_merge(base, override)
        # Base should be unchanged
        assert base["a"]["nested"] == 1
        assert result["a"]["nested"] == 99

    def test_deep_nesting(self) -> None:
        base = {"l1": {"l2": {"l3": {"value": "base"}}}}
        override = {"l1": {"l2": {"l3": {"value": "override"}, "sibling": True}}}
        result = _deep_merge(base, override)
        assert result["l1"]["l2"]["l3"]["value"] == "override"
        assert result["l1"]["l2"]["sibling"] is True

    def test_none_override_value_replaces(self) -> None:
        base = {"a": "something"}
        override = {"a": None}
        result = _deep_merge(base, override)
        assert result["a"] is None


# ---------------------------------------------------------------------------
# load_project_overrides tests
# ---------------------------------------------------------------------------


class TestLoadProjectOverrides:
    def test_returns_none_when_no_file(self, tmp_path: Path) -> None:
        result = load_project_overrides(tmp_path, workflow_id="my-wf")
        assert result is None

    def test_returns_none_for_empty_file(self, tmp_path: Path) -> None:
        (tmp_path / OVERRIDE_FILENAME).write_text("", encoding="utf-8")
        result = load_project_overrides(tmp_path, workflow_id="my-wf")
        assert result is None

    def test_loads_workflow_block_by_id(self, tmp_path: Path) -> None:
        write_override_file(
            tmp_path,
            """
            overrides:
              my-workflow:
                stages:
                  research:
                    roles:
                      primary:
                        artifact: "agent:custom-researcher"
            """,
        )
        result = load_project_overrides(tmp_path, workflow_id="my-workflow")
        assert result is not None
        assert result["stages"]["research"]["roles"]["primary"]["artifact"] == "agent:custom-researcher"

    def test_returns_none_when_workflow_id_not_in_file(self, tmp_path: Path) -> None:
        write_override_file(
            tmp_path,
            """
            overrides:
              other-workflow:
                context:
                  global_modules:
                    - "ctx:other"
            """,
        )
        result = load_project_overrides(tmp_path, workflow_id="my-workflow")
        assert result is None

    def test_returns_full_map_when_no_workflow_id(self, tmp_path: Path) -> None:
        write_override_file(
            tmp_path,
            """
            overrides:
              wf-a:
                context:
                  global_modules: ["ctx:a"]
              wf-b:
                context:
                  global_modules: ["ctx:b"]
            """,
        )
        result = load_project_overrides(tmp_path)
        assert result is not None
        assert "wf-a" in result
        assert "wf-b" in result

    def test_raises_on_yaml_parse_error(self, tmp_path: Path) -> None:
        (tmp_path / OVERRIDE_FILENAME).write_text(
            "overrides:\n  bad: [\n  - unclosed", encoding="utf-8"
        )
        with pytest.raises(WorkflowOverrideError, match="YAML parse error"):
            load_project_overrides(tmp_path, workflow_id="bad")

    def test_raises_when_missing_overrides_key(self, tmp_path: Path) -> None:
        write_override_file(tmp_path, "something_else:\n  key: value\n")
        with pytest.raises(WorkflowOverrideError, match="top-level 'overrides' key"):
            load_project_overrides(tmp_path, workflow_id="my-wf")

    def test_raises_when_overrides_is_not_dict(self, tmp_path: Path) -> None:
        write_override_file(tmp_path, "overrides:\n  - item1\n  - item2\n")
        with pytest.raises(WorkflowOverrideError, match="mapping"):
            load_project_overrides(tmp_path, workflow_id="my-wf")

    def test_raises_when_block_is_not_dict(self, tmp_path: Path) -> None:
        write_override_file(
            tmp_path,
            """
            overrides:
              my-workflow: "this should be a dict"
            """,
        )
        with pytest.raises(WorkflowOverrideError, match="mapping"):
            load_project_overrides(tmp_path, workflow_id="my-workflow")

    def test_raises_on_unknown_top_level_key_in_block(self, tmp_path: Path) -> None:
        write_override_file(
            tmp_path,
            """
            overrides:
              my-workflow:
                unknown_key:
                  foo: bar
            """,
        )
        with pytest.raises(WorkflowOverrideError, match="unknown top-level key"):
            load_project_overrides(tmp_path, workflow_id="my-workflow")

    def test_raises_when_stage_override_touches_id(self, tmp_path: Path) -> None:
        write_override_file(
            tmp_path,
            """
            overrides:
              my-workflow:
                stages:
                  research:
                    id: "new-id"
                    roles:
                      primary:
                        artifact: "agent:other"
            """,
        )
        with pytest.raises(WorkflowOverrideError, match="structural field"):
            load_project_overrides(tmp_path, workflow_id="my-workflow")

    def test_raises_when_stage_override_touches_depends_on(self, tmp_path: Path) -> None:
        write_override_file(
            tmp_path,
            """
            overrides:
              my-workflow:
                stages:
                  implement:
                    depends_on: []
            """,
        )
        with pytest.raises(WorkflowOverrideError, match="structural field"):
            load_project_overrides(tmp_path, workflow_id="my-workflow")

    def test_raises_when_stage_override_touches_type(self, tmp_path: Path) -> None:
        write_override_file(
            tmp_path,
            """
            overrides:
              my-workflow:
                stages:
                  research:
                    type: "gate"
            """,
        )
        with pytest.raises(WorkflowOverrideError, match="structural field"):
            load_project_overrides(tmp_path, workflow_id="my-workflow")

    def test_raises_when_workflow_override_touches_id(self, tmp_path: Path) -> None:
        write_override_file(
            tmp_path,
            """
            overrides:
              my-workflow:
                workflow:
                  id: "new-id"
            """,
        )
        with pytest.raises(WorkflowOverrideError, match="structural fields"):
            load_project_overrides(tmp_path, workflow_id="my-workflow")

    def test_top_level_file_is_not_dict(self, tmp_path: Path) -> None:
        (tmp_path / OVERRIDE_FILENAME).write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(WorkflowOverrideError, match="mapping at the top level"):
            load_project_overrides(tmp_path, workflow_id="any")

    def test_valid_context_override_loads(self, tmp_path: Path) -> None:
        write_override_file(
            tmp_path,
            """
            overrides:
              my-workflow:
                context:
                  global_modules:
                    - "ctx:my-project-rules"
                    - "ctx:my-coding-standards"
            """,
        )
        result = load_project_overrides(tmp_path, workflow_id="my-workflow")
        assert result is not None
        assert result["context"]["global_modules"] == [
            "ctx:my-project-rules",
            "ctx:my-coding-standards",
        ]

    def test_valid_config_override_loads(self, tmp_path: Path) -> None:
        write_override_file(
            tmp_path,
            """
            overrides:
              my-workflow:
                config:
                  parameters:
                    target_branch:
                      default: "develop"
            """,
        )
        result = load_project_overrides(tmp_path, workflow_id="my-workflow")
        assert result is not None
        assert result["config"]["parameters"]["target_branch"]["default"] == "develop"

    def test_valid_error_policy_override_loads(self, tmp_path: Path) -> None:
        write_override_file(
            tmp_path,
            """
            overrides:
              my-workflow:
                error_policy:
                  on_stage_failure: "continue"
            """,
        )
        result = load_project_overrides(tmp_path, workflow_id="my-workflow")
        assert result is not None
        assert result["error_policy"]["on_stage_failure"] == "continue"


# ---------------------------------------------------------------------------
# apply_overrides tests
# ---------------------------------------------------------------------------


class TestApplyOverrides:
    def test_returns_deep_copy_when_overrides_empty(self) -> None:
        result = apply_overrides(MINIMAL_BASE, {})
        assert result == MINIMAL_BASE
        # Must be a deep copy — mutating result should not affect original
        result["workflow"]["name"] = "Changed"
        assert MINIMAL_BASE["workflow"]["name"] == "My Workflow"

    def test_agent_artifact_override_in_stage(self) -> None:
        overrides = {
            "stages": {
                "research": {
                    "roles": {
                        "primary": {
                            "artifact": "agent:my-custom-researcher",
                            "model": "sonnet",
                        }
                    }
                }
            }
        }
        result = apply_overrides(MINIMAL_BASE, overrides)
        research = next(s for s in result["stages"] if s["id"] == "research")
        assert research["roles"]["primary"]["artifact"] == "agent:my-custom-researcher"
        assert research["roles"]["primary"]["model"] == "sonnet"

    def test_tools_list_replaced_entirely(self) -> None:
        overrides = {
            "stages": {
                "implement": {
                    "roles": {
                        "tools": ["skill:my-linter", "skill:git-ops"]
                    }
                }
            }
        }
        result = apply_overrides(MINIMAL_BASE, overrides)
        implement = next(s for s in result["stages"] if s["id"] == "implement")
        assert implement["roles"]["tools"] == ["skill:my-linter", "skill:git-ops"]

    def test_context_global_modules_replaced(self) -> None:
        overrides = {
            "context": {
                "global_modules": [
                    "ctx:my-project-rules",
                    "ctx:my-coding-standards",
                ]
            }
        }
        result = apply_overrides(MINIMAL_BASE, overrides)
        assert result["context"]["global_modules"] == [
            "ctx:my-project-rules",
            "ctx:my-coding-standards",
        ]

    def test_config_parameter_default_overridden(self) -> None:
        overrides = {
            "config": {
                "parameters": {
                    "target_branch": {
                        "default": "develop",
                    }
                }
            }
        }
        result = apply_overrides(MINIMAL_BASE, overrides)
        assert result["config"]["parameters"]["target_branch"]["default"] == "develop"
        # Other parameter untouched
        assert result["config"]["parameters"]["feature_name"]["required"] is True

    def test_base_unchanged_after_apply(self) -> None:
        import copy
        original = copy.deepcopy(MINIMAL_BASE)
        overrides = {
            "context": {"global_modules": ["ctx:new"]},
        }
        apply_overrides(MINIMAL_BASE, overrides)
        assert MINIMAL_BASE == original

    def test_raises_for_unknown_stage_id(self) -> None:
        overrides = {
            "stages": {
                "nonexistent-stage": {
                    "roles": {"primary": {"artifact": "agent:x"}}
                }
            }
        }
        with pytest.raises(WorkflowOverrideError, match="do not exist"):
            apply_overrides(MINIMAL_BASE, overrides)

    def test_adds_new_key_to_base(self) -> None:
        overrides = {
            "config": {
                "parameters": {
                    "new_param": {
                        "type": "string",
                        "default": "hello",
                    }
                }
            }
        }
        result = apply_overrides(MINIMAL_BASE, overrides)
        assert "new_param" in result["config"]["parameters"]
        assert result["config"]["parameters"]["new_param"]["default"] == "hello"

    def test_preserves_base_stage_not_in_override(self) -> None:
        overrides = {
            "stages": {
                "research": {
                    "roles": {"primary": {"artifact": "agent:custom"}}
                }
            }
        }
        result = apply_overrides(MINIMAL_BASE, overrides)
        # implement stage should be unchanged
        implement = next(s for s in result["stages"] if s["id"] == "implement")
        assert implement["roles"]["primary"]["artifact"] == "agent:developer-v1"

    def test_preserves_stage_fields_not_in_stage_override(self) -> None:
        overrides = {
            "stages": {
                "research": {
                    "roles": {"primary": {"model": "sonnet"}}
                }
            }
        }
        result = apply_overrides(MINIMAL_BASE, overrides)
        research = next(s for s in result["stages"] if s["id"] == "research")
        # artifact preserved, model overridden
        assert research["roles"]["primary"]["artifact"] == "agent:researcher-v1"
        assert research["roles"]["primary"]["model"] == "sonnet"

    def test_multiple_stages_overridden(self) -> None:
        overrides = {
            "stages": {
                "research": {
                    "roles": {"primary": {"artifact": "agent:research-custom"}}
                },
                "implement": {
                    "roles": {"primary": {"artifact": "agent:implement-custom"}}
                },
            }
        }
        result = apply_overrides(MINIMAL_BASE, overrides)
        research = next(s for s in result["stages"] if s["id"] == "research")
        implement = next(s for s in result["stages"] if s["id"] == "implement")
        assert research["roles"]["primary"]["artifact"] == "agent:research-custom"
        assert implement["roles"]["primary"]["artifact"] == "agent:implement-custom"

    def test_full_spec_example(self, tmp_path: Path) -> None:
        """End-to-end: write override file, load it, apply to base."""
        write_override_file(
            tmp_path,
            """
            overrides:
              my-workflow:
                stages:
                  research:
                    roles:
                      primary:
                        artifact: "agent:my-custom-researcher"
                        model: "sonnet"
                  implement:
                    roles:
                      primary:
                        artifact: "agent:my-fullstack-dev"
                      tools:
                        - "skill:my-custom-linter"
                        - "skill:git-ops"
                context:
                  global_modules:
                    - "ctx:my-project-rules"
                    - "ctx:my-coding-standards"
                config:
                  parameters:
                    target_branch:
                      default: "develop"
            """,
        )
        block = load_project_overrides(tmp_path, workflow_id="my-workflow")
        assert block is not None
        result = apply_overrides(MINIMAL_BASE, block)

        # Stage overrides applied
        research = next(s for s in result["stages"] if s["id"] == "research")
        assert research["roles"]["primary"]["artifact"] == "agent:my-custom-researcher"
        assert research["roles"]["primary"]["model"] == "sonnet"

        implement = next(s for s in result["stages"] if s["id"] == "implement")
        assert implement["roles"]["primary"]["artifact"] == "agent:my-fullstack-dev"
        assert implement["roles"]["tools"] == ["skill:my-custom-linter", "skill:git-ops"]

        # Context override applied
        assert result["context"]["global_modules"] == [
            "ctx:my-project-rules",
            "ctx:my-coding-standards",
        ]

        # Parameter default override applied
        assert result["config"]["parameters"]["target_branch"]["default"] == "develop"
        # Other parameter preserved
        assert result["config"]["parameters"]["feature_name"]["required"] is True

        # Base workflow dict not mutated
        assert MINIMAL_BASE["context"]["global_modules"] == ["ctx:repo-rules"]


# ---------------------------------------------------------------------------
# _merge_stages edge cases
# ---------------------------------------------------------------------------


class TestMergeStages:
    def test_returns_base_unchanged_when_override_empty(self) -> None:
        stages = [{"id": "a", "name": "A", "type": "agent"}]
        result = _merge_stages(stages, {})
        assert result == stages

    def test_raises_for_unknown_stage_id(self) -> None:
        stages = [{"id": "a", "name": "A"}]
        with pytest.raises(WorkflowOverrideError, match="do not exist"):
            _merge_stages(stages, {"unknown": {"roles": {}}})

    def test_merges_single_stage(self) -> None:
        stages = [{"id": "a", "name": "A", "roles": {"primary": {"artifact": "x"}}}]
        override = {"a": {"roles": {"primary": {"artifact": "y"}}}}
        result = _merge_stages(stages, override)
        assert result[0]["roles"]["primary"]["artifact"] == "y"
        assert result[0]["name"] == "A"  # preserved

    def test_base_stages_not_mutated(self) -> None:
        stages = [{"id": "a", "name": "A"}]
        _merge_stages(stages, {"a": {"name": "Modified"}})
        assert stages[0]["name"] == "A"
