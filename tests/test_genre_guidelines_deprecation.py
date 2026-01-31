"""
Unit and property tests for genre guidelines deprecation.

**Property 9: Genre Guidelines Deprecation**
**Validates: Requirements 3.1, 3.3**

The system should not load or reference genre_guidelines_v1.json, and Studio Director
should incorporate genre wisdom through high-level reasoning without explicit style instructions.
"""

import pytest
from pathlib import Path
from hypothesis import given, strategies as st, settings


# Property test 1: Genre guidelines file should never exist
@settings(max_examples=50)
@given(
    filename=st.sampled_from([
        "genre_guidelines_v1.json",
        "genre_guidelines.json",
        "genre_guidelines_v2.json",
    ])
)
def test_property_genre_guidelines_files_do_not_exist(filename: str):
    """
    Property: Genre guidelines files should not exist in config directory.
    
    This property verifies that no genre guidelines files exist, regardless
    of version or naming convention.
    """
    from app.config.loaders import _CONFIG_DIR
    
    file_path = _CONFIG_DIR / filename
    assert not file_path.exists(), (
        f"{filename} should not exist at {file_path}"
    )


# Property test 2: No genre guidelines references in codebase
@settings(max_examples=50)
@given(
    module_name=st.sampled_from([
        "app.config.loaders",
        "app.services.config_watcher",
        "app.graphs.nodes.planning.studio_director",
    ])
)
def test_property_no_genre_guidelines_references(module_name: str):
    """
    Property: No module should reference genre_guidelines.
    
    This property verifies that key modules do not contain references
    to genre_guidelines in their source code.
    """
    import importlib
    import inspect
    
    # Import the module
    module = importlib.import_module(module_name)
    
    # Get source code
    source = inspect.getsource(module)
    
    # Check for genre_guidelines references
    assert "genre_guidelines" not in source.lower(), (
        f"{module_name} should not reference genre_guidelines"
    )


def test_genre_guidelines_file_does_not_exist():
    """Test that genre_guidelines_v1.json file does not exist in config directory."""
    from app.config.loaders import _CONFIG_DIR
    
    genre_guidelines_path = _CONFIG_DIR / "genre_guidelines_v1.json"
    assert not genre_guidelines_path.exists(), (
        f"genre_guidelines_v1.json should not exist at {genre_guidelines_path}"
    )


def test_no_genre_guidelines_loader_function():
    """Test that load_genre_guidelines_v1() function does not exist in config loaders."""
    from app.config import loaders
    
    assert not hasattr(loaders, "load_genre_guidelines_v1"), (
        "load_genre_guidelines_v1() function should not exist in app.config.loaders"
    )


def test_config_watcher_does_not_import_genre_guidelines():
    """Test that config_watcher does not import genre_guidelines module."""
    import app.services.config_watcher as config_watcher
    import inspect
    
    # Get the source code of the module
    source = inspect.getsource(config_watcher)
    
    # Check that genre_guidelines is not imported
    assert "from app.graphs.nodes.genre_guidelines" not in source, (
        "config_watcher should not import genre_guidelines module"
    )
    assert "reload_guidelines" not in source, (
        "config_watcher should not call reload_guidelines()"
    )


def test_studio_director_does_not_reference_genre_guidelines():
    """Test that Studio Director does not reference genre guidelines."""
    import app.graphs.nodes.planning.studio_director as studio_director
    import inspect
    
    # Get the source code of the module
    source = inspect.getsource(studio_director)
    
    # Check that genre_guidelines is not referenced
    assert "genre_guidelines" not in source.lower(), (
        "Studio Director should not reference genre_guidelines"
    )


def test_clear_config_cache_does_not_clear_genre_guidelines():
    """Test that clear_config_cache() does not attempt to clear genre guidelines cache."""
    from app.config.loaders import clear_config_cache
    import inspect
    
    # Get the source code of clear_config_cache
    source = inspect.getsource(clear_config_cache)
    
    # Check that genre_guidelines is not referenced
    assert "genre_guidelines" not in source.lower(), (
        "clear_config_cache() should not reference genre_guidelines"
    )
