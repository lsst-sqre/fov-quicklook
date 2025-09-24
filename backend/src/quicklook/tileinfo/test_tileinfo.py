"""TileInfoクラスのテスト."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from quicklook.tileinfo import TileInfo, _Ccd, ccd_list, ccds_by_name, ccds_intersecting, rtree_index
from quicklook.utils.geom import BBox


# テスト用のサンプルCCDデータ
SAMPLE_CCD_DATA = [
    {"name": "R00_SG0", "bbox": {"miny": 0.0, "maxy": 100.0, "minx": 0.0, "maxx": 100.0}},
    {"name": "R00_SG1", "bbox": {"miny": 50.0, "maxy": 150.0, "minx": 50.0, "maxx": 150.0}},
    {"name": "R01_SG0", "bbox": {"miny": 200.0, "maxy": 300.0, "minx": 200.0, "maxx": 300.0}},
]


@pytest.fixture
def mock_ccd_info(tmp_path):
    """テスト用のCCD情報ファイルを作成する."""
    ccd_file = tmp_path / "test-ccd-info.json"
    ccd_file.write_text(json.dumps(SAMPLE_CCD_DATA))

    with patch('quicklook.tileinfo.ccd_info_path', ccd_file):
        # キャッシュをクリア
        ccd_list.cache_clear()
        ccds_by_name.cache_clear()
        rtree_index.cache_clear()
        yield ccd_file


def test_tile_info_creation(mock_ccd_info):
    """TileInfoの基本的な作成テスト."""
    # レベル0、位置(0,0)のタイル（256x256ピクセル）
    tile = TileInfo.of(level=0, i=0, j=0)

    assert tile.level == 0
    assert tile.i == 0
    assert tile.j == 0
    assert isinstance(tile.ccd_names, list)


def test_tile_size_property(mock_ccd_info):
    """tile_sizeプロパティのテスト."""
    # デフォルトのtile_sizeは256と仮定
    tile_level0 = TileInfo.of(level=0, i=0, j=0)
    tile_level1 = TileInfo.of(level=1, i=0, j=0)
    tile_level2 = TileInfo.of(level=2, i=0, j=0)

    assert tile_level1.tile_size == tile_level0.tile_size * 2
    assert tile_level2.tile_size == tile_level0.tile_size * 4


def test_bbox_property(mock_ccd_info):
    """bboxプロパティのテスト."""
    tile = TileInfo.of(level=0, i=1, j=2)
    bbox = tile.bbox

    expected_size = tile.tile_size
    assert bbox.minx == 2 * expected_size
    assert bbox.miny == 1 * expected_size
    assert bbox.maxx == 3 * expected_size
    assert bbox.maxy == 2 * expected_size


def test_get_overlapping_ccds(mock_ccd_info):
    """get_overlapping_ccdsメソッドのテスト."""
    # レベル0で適切な位置のタイルを作成
    tile = TileInfo.of(level=0, i=0, j=0)
    overlapping_ccds = tile.get_overlapping_ccds()

    assert isinstance(overlapping_ccds, list)
    assert all(isinstance(ccd, _Ccd) for ccd in overlapping_ccds)


def test_ccds_intersecting():
    """ccds_intersecting関数のテスト."""
    # テスト用の境界ボックス
    bbox = BBox(minx=25.0, miny=25.0, maxx=75.0, maxy=75.0)

    with patch('quicklook.tileinfo.ccd_list') as mock_ccd_list, patch('quicklook.tileinfo.rtree_index') as mock_rtree:

        # モックの設定
        mock_ccd_list.return_value = [_Ccd(name="CCD1", bbox=BBox(0, 100, 0, 100)), _Ccd(name="CCD2", bbox=BBox(50, 150, 50, 150))]
        mock_rtree.return_value.intersection.return_value = [0, 1]

        result = ccds_intersecting(bbox)
        assert result == ["CCD1", "CCD2"]


def test_ccd_list_file_not_found():
    """CCD情報ファイルが見つからない場合のテスト."""
    with patch('quicklook.tileinfo.ccd_info_path') as mock_path:
        mock_path.exists.return_value = False
        ccd_list.cache_clear()

        with pytest.raises(FileNotFoundError, match="CCD情報ファイルが見つかりません"):
            ccd_list()


def test_ccd_list_invalid_json():
    """不正なJSONファイルの場合のテスト."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write("invalid json content")
        f.flush()

        with patch('quicklook.tileinfo.ccd_info_path', Path(f.name)):
            ccd_list.cache_clear()

            with pytest.raises(json.JSONDecodeError):
                ccd_list()


def test_ccd_list_missing_keys():
    """必要なキーが不足している場合のテスト."""
    invalid_data = [{"name": "CCD1"}]  # bboxキーが不足

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(invalid_data, f)
        f.flush()

        with patch('quicklook.tileinfo.ccd_info_path', Path(f.name)):
            ccd_list.cache_clear()

            with pytest.raises(ValueError, match="CCD情報ファイルに必要なキーがありません"):
                ccd_list()


def test_ccds_by_name(mock_ccd_info):
    """ccds_by_name関数のテスト."""
    ccds_dict = ccds_by_name()

    assert isinstance(ccds_dict, dict)
    assert "R00_SG0" in ccds_dict
    assert "R00_SG1" in ccds_dict
    assert "R01_SG0" in ccds_dict

    # 各CCDが正しい型であることを確認
    for ccd in ccds_dict.values():
        assert isinstance(ccd, _Ccd)
        assert hasattr(ccd, 'name')
        assert hasattr(ccd, 'bbox')


def test_rtree_index_creation(mock_ccd_info):
    """R-treeインデックスの作成テスト."""
    index = rtree_index()

    # インデックスが作成されていることを確認
    assert index is not None

    # インデックスに検索をかけてみる
    result = list(index.intersection([0, 0, 50, 50]))
    assert isinstance(result, list)


def test_tile_info_with_different_levels(mock_ccd_info):
    """異なるレベルでのタイル作成テスト."""
    levels = [0, 1, 2, 3]

    for level in levels:
        tile = TileInfo.of(level=level, i=0, j=0)
        assert tile.level == level
        assert tile.tile_size == 256 * (2**level)  # デフォルトtile_size=256と仮定


def test_tile_info_ccd_overlap_logic(mock_ccd_info):
    """CCDとタイルの重複ロジックのテスト."""
    # レベル0で大きなタイル（位置によってはCCDと重複する）
    large_tile = TileInfo.of(level=3, i=0, j=0)  # 2048x2048のタイル

    # このタイルは複数のCCDと重複する可能性がある
    overlapping_ccds = large_tile.get_overlapping_ccds()
    assert isinstance(overlapping_ccds, list)


def test_ccd_class():
    """_Ccdクラスの基本テスト."""
    bbox = BBox(minx=0.0, miny=0.0, maxx=100.0, maxy=100.0)
    ccd = _Ccd(name="TEST_CCD", bbox=bbox)

    assert ccd.name == "TEST_CCD"
    assert ccd.bbox == bbox


def test_tile_info_edge_cases(mock_ccd_info):
    """TileInfoのエッジケーステスト."""
    # 非常に大きなインデックス
    tile = TileInfo.of(level=0, i=1000, j=1000)
    assert tile.i == 1000
    assert tile.j == 1000

    # 負のインデックス（位置としては有効）
    tile_negative = TileInfo.of(level=0, i=-1, j=-1)
    assert tile_negative.i == -1
    assert tile_negative.j == -1


def test_bbox_intersection_boundary_cases(mock_ccd_info):
    """境界ケースでの交差テスト."""
    # CCDの境界ぎりぎりの境界ボックス
    bbox_exact = BBox(minx=0.0, miny=0.0, maxx=100.0, maxy=100.0)
    bbox_no_overlap = BBox(minx=500.0, miny=500.0, maxx=600.0, maxy=600.0)

    intersecting_exact = ccds_intersecting(bbox_exact)
    intersecting_none = ccds_intersecting(bbox_no_overlap)

    assert isinstance(intersecting_exact, list)
    assert isinstance(intersecting_none, list)
