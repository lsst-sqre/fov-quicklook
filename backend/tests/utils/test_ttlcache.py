from quicklook.utils.ttlcache import ttlcache
import time
from unittest.mock import patch, Mock


def test_basic_caching():
    """Test that function results are cached."""
    call_count = 0

    @ttlcache(ttl=60)
    def test_func(x: int, y: int) -> int:
        nonlocal call_count
        call_count += 1
        return x + y

    # First call should execute the function
    assert test_func(1, 2) == 3
    assert call_count == 1

    # Second call with same args should use cached result
    assert test_func(1, 2) == 3
    assert call_count == 1

    # Call with different args should execute the function again
    assert test_func(2, 3) == 5
    assert call_count == 2

    # Check with keyword arguments
    assert test_func(x=1, y=2) == 3
    assert call_count == 3  # Different call signature (kwargs vs args)

    # Check with same keyword arguments but different order
    assert test_func(y=2, x=1) == 3
    assert call_count == 3  # Should use cached result


def test_ttl_expiration():
    """Test that cache entries expire after the TTL period."""
    call_count = 0

    @ttlcache(ttl=0.1)  # Short TTL for testing
    def test_func(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    # First call
    assert test_func(5) == 10
    assert call_count == 1

    # Call immediately should use cache
    assert test_func(5) == 10
    assert call_count == 1

    # Wait for TTL to expire
    time.sleep(0.2)

    # Call after TTL expired should execute the function again
    assert test_func(5) == 10
    assert call_count == 2


def test_without_ttl():
    """Test decorator without TTL parameter."""
    call_count = 0

    @ttlcache()
    def test_func(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 3

    # First call
    assert test_func(3) == 9
    assert call_count == 1

    # Second call should use cache
    assert test_func(3) == 9
    assert call_count == 1

    # Wait some time (no TTL, so should still use cache)
    time.sleep(0.1)
    assert test_func(3) == 9
    assert call_count == 1


def test_cache_clear():
    """Test cache_clear functionality."""
    call_count = 0

    @ttlcache(ttl=60)
    def test_func(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 4

    # First call
    assert test_func(2) == 8
    assert call_count == 1

    # Second call should use cache
    assert test_func(2) == 8
    assert call_count == 1

    # Clear cache
    test_func.cache_clear()

    # Call after clearing should execute the function again
    assert test_func(2) == 8
    assert call_count == 2


def test_cache_info():
    """Test cache_info functionality."""

    @ttlcache(ttl=30)
    def test_func(x: int) -> int:
        return x * 5

    # Check initial cache info
    info = test_func.cache_info()
    assert info["currsize"] == 0
    assert info["ttl"] == 30

    # Add to cache
    test_func(4)
    test_func(5)

    # Check updated cache info
    info = test_func.cache_info()
    assert info["currsize"] == 2
    assert info["ttl"] == 30

    # Clear cache and check info again
    test_func.cache_clear()
    info = test_func.cache_info()
    assert info["currsize"] == 0


def test_with_mocked_time():
    """Test TTL with mocked time to avoid actual waiting."""
    call_count = 0
    current_time = 1000.0

    def mock_time():
        return current_time

    with patch('time.time', mock_time):

        @ttlcache(ttl=10)
        def test_func(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 6

        # First call
        assert test_func(2) == 12
        assert call_count == 1

        # Second call at same time should use cache
        assert test_func(2) == 12
        assert call_count == 1

        # Move time forward but still within TTL
        current_time += 5

        # Should still use cache
        assert test_func(2) == 12
        assert call_count == 1

        # Move time past TTL
        current_time += 6  # Total of 11 seconds passed

        # Should recalculate
        assert test_func(2) == 12
        assert call_count == 2
