import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quicklook.comm.rpc_worker import YieledValue, rpc_scatter, rpc_scatter_stream
from quicklook.comm.types import GeneratorId, GeneratorInfo


@pytest.fixture
def mock_generators():
    """モックジェネレータのフィクスチャ"""
    return {
        GeneratorId('gen1'): GeneratorInfo(
            id=GeneratorId('gen1'),
            host='localhost',
            port=8001,
        ),
        GeneratorId('gen2'): GeneratorInfo(
            id=GeneratorId('gen2'),
            host='localhost',
            port=8002,
        ),
    }


def dummy_rpc_func():
    """テスト用のRPC関数（通常関数）"""
    return 42


def dummy_rpc_func_with_args(x: int, y: int):
    """テスト用のRPC関数（引数あり）"""
    return x + y


def dummy_rpc_generator_func():
    """テスト用のRPC関数（ジェネレータ）"""
    for i in range(3):
        yield i


async def test_rpc_scatter_returns_results(mock_generators):
    """rpc_scatterが各ジェネレータからの結果を返すことを確認"""
    with (
        patch('quicklook.comm.rpc_worker.get_available_generators', return_value=mock_generators),
        patch('quicklook.comm.rpc_worker.RpcClient') as mock_rpc_client,
    ):
        mock_result1 = 10
        mock_result2 = 20
        mock_rpc_client.return_value.run = AsyncMock(side_effect=[mock_result1, mock_result2])

        results = await rpc_scatter(dummy_rpc_func)

        assert len(results) == 2
        assert mock_result1 in results
        assert mock_result2 in results
        assert mock_rpc_client.call_count == 2


async def test_rpc_scatter_with_args_kwargs(mock_generators):
    """rpc_scatterが引数とキーワード引数を正しく渡すことを確認"""
    with (
        patch('quicklook.comm.rpc_worker.get_available_generators', return_value=mock_generators),
        patch('quicklook.comm.rpc_worker.RpcClient') as mock_rpc_client,
    ):
        mock_rpc_client.return_value.run = AsyncMock(return_value=100)

        results = await rpc_scatter(dummy_rpc_func_with_args, 10, 20)

        assert len(results) == 2
        assert all(r == 100 for r in results)





async def test_rpc_scatter_stream_calls_on_yield(mock_generators):
    """rpc_scatter_streamがon_yieldコールバックを呼び出すことを確認"""

    async def mock_generator():
        yield 'value1'
        yield 'value2'
        yield 'value3'

    yielded_values = []

    async def on_yield(msg: YieledValue):
        yielded_values.append(msg)

    with (
        patch('quicklook.comm.rpc_worker.get_available_generators', return_value=mock_generators),
        patch('quicklook.comm.rpc_worker.RpcClient') as mock_rpc_client,
    ):

        def mock_iterate_factory():
            return mock_generator()

        mock_rpc_client.return_value.iterate = mock_iterate_factory

        await rpc_scatter_stream(on_yield, dummy_rpc_generator_func)

        assert len(yielded_values) == 6
        assert all(isinstance(v, YieledValue) for v in yielded_values)
        assert all(v.value in ['value1', 'value2', 'value3'] for v in yielded_values)
        assert all(v.generator_id in [GeneratorId('gen1'), GeneratorId('gen2')] for v in yielded_values)


async def test_rpc_scatter_with_empty_generators():
    """ジェネレータが存在しない場合のrpc_scatterの動作を確認"""
    with patch('quicklook.comm.rpc_worker.get_available_generators', return_value={}):
        results = await rpc_scatter(dummy_rpc_func)
        assert results == []


async def test_rpc_scatter_stream_with_empty_generators():
    """ジェネレータが存在しない場合のrpc_scatter_streamの動作を確認"""
    yielded_values = []

    async def on_yield(msg: YieledValue):
        yielded_values.append(msg)

    with patch('quicklook.comm.rpc_worker.get_available_generators', return_value={}):
        await rpc_scatter_stream(on_yield, dummy_rpc_generator_func)
        assert len(yielded_values) == 0
