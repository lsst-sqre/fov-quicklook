import pytest
from quicklook.utils.sizelimitedset import SizeLimitedSet
import time
from unittest.mock import patch

def test_add_and_contains() -> None:
    s: SizeLimitedSet[int] = SizeLimitedSet(3)
    s.add(1)
    s.add(2)
    s.add(3)
    assert 1 in s
    assert 2 in s
    assert 3 in s

def test_size_limit() -> None:
    s: SizeLimitedSet[int] = SizeLimitedSet(3)
    s.add(1)
    s.add(2)
    s.add(3)
    s.add(4)
    assert 1 not in s
    assert 2 in s
    assert 3 in s
    assert 4 in s

def test_duplicate_add() -> None:
    s: SizeLimitedSet[int] = SizeLimitedSet(3)
    s.add(1)
    s.add(2)
    s.add(2)
    s.add(3)
    assert len(s) == 3
    assert 1 in s
    assert 2 in s
    assert 3 in s

def test_iteration() -> None:
    s: SizeLimitedSet[int] = SizeLimitedSet(3)
    s.add(1)
    s.add(2)
    s.add(3)
    assert list(s) == [1, 2, 3]

def test_repr() -> None:
    s: SizeLimitedSet[int] = SizeLimitedSet(3)
    s.add(1)
    s.add(2)
    s.add(3)
    assert repr(s) == "SizeLimitedSet([1, 2, 3])"

def test_ttl_with_sleep() -> None:
    """実際に時間経過を待ってTTLの動作をテストする"""
    # TTLを0.1秒に設定
    s: SizeLimitedSet[int] = SizeLimitedSet(3, ttl=0.1)
    s.add(1)
    assert 1 in s
    
    # TTL時間経過を待つ
    time.sleep(0.2)
    
    # TTL経過後は要素が削除されているはず
    assert 1 not in s
    assert len(s) == 0

def test_ttl_without_expiration() -> None:
    """TTL経過前の状態をテスト"""
    # TTLを大きな値に設定
    s: SizeLimitedSet[int] = SizeLimitedSet(3, ttl=3600)
    s.add(1)
    s.add(2)
    
    # TTLが経過していないので要素は残っているはず
    assert 1 in s
    assert 2 in s
    assert len(s) == 2

def test_ttl_with_mock_time() -> None:
    """time.timeをモックしてTTLの動作をテストする"""
    with patch('time.time') as mock_time:
        # 初期時刻を設定
        mock_time.return_value = 1000.0
        
        # TTLを10秒に設定
        s: SizeLimitedSet[int] = SizeLimitedSet(3, ttl=10)
        
        # アイテムを追加
        s.add(1)
        s.add(2)
        
        # TTL経過前の確認
        assert 1 in s
        assert len(s) == 2
        
        # 時間を15秒進める (TTLの10秒を超過)
        mock_time.return_value = 1015.0
        
        # TTL経過後の確認
        assert 1 not in s
        assert len(s) == 0
        
        # 新しいアイテムを追加
        s.add(3)
        assert 3 in s
        
        # 時間をさらに5秒進める (まだTTL内)
        mock_time.return_value = 1020.0
        assert 3 in s
        
        # 時間をさらに10秒進める (TTLを超過)
        mock_time.return_value = 1030.0
        assert 3 not in s
