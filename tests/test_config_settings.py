import pytest
from pathlib import Path
from skillmeat.config import ConfigManager
from skillmeat.api.routers.settings import (
    get_project_search_paths,
    set_project_search_paths,
    add_project_search_path,
    remove_project_search_path,
)
from skillmeat.api.schemas.settings import ProjectSearchPathsRequest

@pytest.fixture
def temp_config(tmp_path):
    config_dir = tmp_path / ".skillmeat"
    config_dir.mkdir()
    return ConfigManager(config_dir=config_dir)

def test_config_manager_search_paths(temp_config):
    # Test default
    paths = temp_config.get_project_search_paths()
    assert isinstance(paths, list)
    assert len(paths) > 0
    # Default paths should contain user home
    assert any(str(Path.home()) in p for p in paths)

    # Test set
    new_paths = ["/tmp/projects", "/tmp/dev"]
    temp_config.set_project_search_paths(new_paths)
    assert temp_config.get_project_search_paths() == new_paths

    # Test add
    temp_config.add_project_search_path("/tmp/new")
    assert "/tmp/new" in temp_config.get_project_search_paths()
    assert len(temp_config.get_project_search_paths()) == 3

    # Test add existing (no dupes)
    temp_config.add_project_search_path("/tmp/new")
    assert len(temp_config.get_project_search_paths()) == 3

    # Test remove
    temp_config.remove_project_search_path("/tmp/projects")
    assert "/tmp/projects" not in temp_config.get_project_search_paths()
    assert "/tmp/dev" in temp_config.get_project_search_paths()
    assert "/tmp/new" in temp_config.get_project_search_paths()

@pytest.mark.asyncio
async def test_settings_api_search_paths(temp_config):
    # Test GET
    response = await get_project_search_paths(config=temp_config)
    initial_paths = response.paths
    assert isinstance(initial_paths, list)

    # Test POST (Set)
    new_paths = ["/api/test/1", "/api/test/2"]
    request = ProjectSearchPathsRequest(paths=new_paths)
    response = await set_project_search_paths(request, config=temp_config)
    assert response.paths == new_paths
    assert temp_config.get_project_search_paths() == new_paths

    # Test Add
    response = await add_project_search_path(path="/api/test/3", config=temp_config)
    assert "/api/test/3" in response.paths
    assert "/api/test/3" in temp_config.get_project_search_paths()

    # Test Remove
    response = await remove_project_search_path(path="/api/test/1", config=temp_config)
    assert "/api/test/1" not in response.paths
    assert "/api/test/2" in response.paths
