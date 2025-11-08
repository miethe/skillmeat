"""Smoke tests for SkillMeat Phase 1 foundation.

Verifies basic package structure and imports work correctly.
"""

import sys
import pytest


def test_import_skillmeat():
    """Test that skillmeat package can be imported."""
    import skillmeat
    assert skillmeat is not None


def test_version():
    """Test that version is defined and correct."""
    import skillmeat
    assert skillmeat.__version__ == "0.1.0-alpha"
    assert skillmeat.VERSION == "0.1.0-alpha"


def test_cli_entry_point():
    """Test that CLI main function exists and is callable."""
    from skillmeat.cli import main
    assert callable(main)


def test_package_metadata():
    """Test that package metadata is correctly set."""
    import skillmeat
    assert skillmeat.__license__ == "MIT"
    assert skillmeat.__author__ == "SkillMeat Contributors"


def test_core_modules_exist():
    """Test that core module structure exists."""
    import skillmeat.core
    import skillmeat.sources
    import skillmeat.storage
    import skillmeat.utils

    # Verify submodules exist (even if empty)
    assert hasattr(skillmeat, 'core')
    assert hasattr(skillmeat, 'sources')
    assert hasattr(skillmeat, 'storage')
    assert hasattr(skillmeat, 'utils')


def test_cli_help():
    """Test that CLI help command works."""
    from click.testing import CliRunner
    from skillmeat.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ['--help'])

    assert result.exit_code == 0
    assert 'SkillMeat' in result.output
    assert 'Personal collection manager' in result.output


def test_cli_version():
    """Test that CLI version command works."""
    from click.testing import CliRunner
    from skillmeat.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ['--version'])

    assert result.exit_code == 0
    assert '0.1.0-alpha' in result.output


def test_cli_init_placeholder():
    """Test that init command works (no longer a placeholder)."""
    from click.testing import CliRunner
    from skillmeat.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ['init'])

    # Init should succeed whether creating new or collection already exists
    assert result.exit_code == 0
    # Should mention collection (either initialized or already exists)
    assert 'collection' in result.output.lower()
