import shutil
from pathlib import Path
from typing import Generator

import numpy as np
import pytest

from quicklook.config import config
from quicklook.generator.tmptile import tmptile
from quicklook.types import CcdId, Tile, Visit


@pytest.fixture
def test_tmpdir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary directory for test"""
    original_tmpdir = config.tile_tmpdir
    config.tile_tmpdir = str(tmp_path)
    try:
        yield tmp_path
    finally:
        config.tile_tmpdir = original_tmpdir


@pytest.fixture
def sample_visit() -> Visit:
    """Create a sample Visit object"""
    return Visit(id="12345")


@pytest.fixture
def sample_ccd_id(sample_visit: Visit) -> CcdId:
    """Create a sample CcdId object"""
    return CcdId(
        visit=sample_visit,
        ccd_name='R00_SG0',
    )


@pytest.fixture
def sample_tile(sample_visit: Visit) -> Tile:
    """Create a sample Tile object"""
    data = np.zeros((100, 100), dtype=np.float32)
    return Tile(visit=sample_visit, level=0, i=1, j=2, data=data)


def test_delete_all_cache(test_tmpdir: Path) -> None:
    """Test that delete_all_cache method correctly removes the cache directory"""
    # Create test directory and file
    test_dir = test_tmpdir / "test_dir"
    test_dir.mkdir(parents=True)
    test_file = test_dir / "test_file.txt"
    test_file.write_text("test content")
    
    # Verify directory exists
    assert test_tmpdir.exists()
    
    # Delete cache
    tmptile.delete_all_cache()
    
    # Verify directory was deleted
    assert not test_tmpdir.exists()


def test_delete_all_cache_not_found(test_tmpdir: Path) -> None:
    """Test that delete_all_cache handles FileNotFoundError gracefully"""
    # Delete the directory first
    shutil.rmtree(test_tmpdir)
    
    # This should not raise an exception
    tmptile.delete_all_cache()


def test_iter_tiles(test_tmpdir: Path, sample_visit: Visit, sample_ccd_id: CcdId) -> None:
    """Test that iter_tiles method correctly iterates through tile directories"""
    # Create test directory structure with multiple tiles
    # Setup: level/i/j
    test_structures = [
        (0, 1, 2),
        (0, 3, 4),
        (1, 5, 6),
    ]
    
    # Create tile files using TmpTile.put
    for level, i, j in test_structures:
        # Create a sample tile with the current level, i, j coordinates
        tile = Tile(visit=sample_visit, level=level, i=i, j=j, data=np.zeros((10, 10), dtype=np.float32))
        # Use TmpTile.put to save it
        tmptile.put_tile(sample_ccd_id, tile)
    
    # Collect results from iter_tiles
    result_tiles = list(tmptile.iter_tiles(sample_visit))
    
    # Verify all expected structures are found
    assert len(result_tiles) == len(test_structures)
    for expected in test_structures:
        assert expected in result_tiles
