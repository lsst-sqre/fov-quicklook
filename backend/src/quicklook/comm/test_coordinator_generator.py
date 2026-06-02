"""coordinator-generator間の通信のテスト"""

import asyncio
import errno
from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from quicklook.comm import coordinator, generator
from quicklook.comm.types import CoordinatorId, GeneratorRegistrationRequest, GeneratorId


@pytest.fixture
def coordinator_app():
    app = FastAPI(lifespan=coordinator.lifespan)
    app.include_router(coordinator.router)
    return app


@pytest.fixture
def coordinator_client(coordinator_app):
    return TestClient(coordinator_app)


def test_coordinator_id_initialization():
    """coordinatorのlifespan時にUUIDが割り当てられることを確認"""
    app = FastAPI(lifespan=coordinator.lifespan)
    app.include_router(coordinator.router)
    
    with TestClient(app) as client:
        response = client.get("/comm/healthz")
        assert response.status_code == 200
        assert coordinator.get_coordinator_id() is not None
        assert coordinator.get_coordinator_id().startswith("c-")


def test_generator_registration_initial():
    """初回のgenerator登録時にcoordinator_idが返されることを確認"""
    app = FastAPI(lifespan=coordinator.lifespan)
    app.include_router(coordinator.router)
    
    with TestClient(app) as client:
        coordinator_id = coordinator.get_coordinator_id()
        assert coordinator_id is not None
        
        registration_request = GeneratorRegistrationRequest(
            generator_id=GeneratorId("test-gen-1"),
            port=8001,
            coordinator_id=None,
        )
        
        response = client.post("/comm/register", json=registration_request.model_dump())
        assert response.status_code == 200
        
        data = response.json()
        assert "coordinator_id" in data
        assert data["coordinator_id"] == coordinator_id


def test_generator_registration_with_matching_coordinator_id():
    """正しいcoordinator_idでの登録が成功することを確認"""
    app = FastAPI(lifespan=coordinator.lifespan)
    app.include_router(coordinator.router)
    
    with TestClient(app) as client:
        coordinator_id = coordinator.get_coordinator_id()
        assert coordinator_id is not None
        
        registration_request = GeneratorRegistrationRequest(
            generator_id=GeneratorId("test-gen-2"),
            port=8002,
            coordinator_id=coordinator_id,
        )
        
        response = client.post("/comm/register", json=registration_request.model_dump())
        assert response.status_code == 200
        
        data = response.json()
        assert data["coordinator_id"] == coordinator_id


def test_generator_registration_with_mismatched_coordinator_id():
    """異なるcoordinator_idでの登録が拒否されることを確認"""
    app = FastAPI(lifespan=coordinator.lifespan)
    app.include_router(coordinator.router)
    
    with TestClient(app) as client:
        coordinator_id = coordinator.get_coordinator_id()
        assert coordinator_id is not None
        
        wrong_coordinator_id = CoordinatorId("c-wrong-id")
        registration_request = GeneratorRegistrationRequest(
            generator_id=GeneratorId("test-gen-3"),
            port=8003,
            coordinator_id=wrong_coordinator_id,
        )
        
        response = client.post("/comm/register", json=registration_request.model_dump())
        assert response.status_code == 409
        assert "Coordinator ID mismatch" in response.json()["detail"]


async def test_registration_loop_retries_transient_errors_without_shutdown(monkeypatch):
    attempts = 0
    shutdown_called = False
    original_sleep = asyncio.sleep

    monkeypatch.setattr(generator, "_generator_id", GeneratorId("test-gen"))
    monkeypatch.setattr(generator, "_coordinator_id", None)
    monkeypatch.setattr(generator, "_shutdown_requested", False)

    async def fake_register():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("temporary network error")
        generator._shutdown_requested = True

    async def fake_shutdown():
        nonlocal shutdown_called
        shutdown_called = True

    async def fake_sleep(_delay: float):
        await original_sleep(0)

    monkeypatch.setattr(generator, "_register_to_coordinator", fake_register)
    monkeypatch.setattr(generator, "_shutdown", fake_shutdown)
    monkeypatch.setattr(generator.asyncio, "sleep", fake_sleep)

    await generator._registration_loop()

    assert attempts == 2
    assert shutdown_called is False


async def test_registration_loop_shuts_down_on_coordinator_restart(monkeypatch):
    shutdown_called = False

    monkeypatch.setattr(generator, "_generator_id", GeneratorId("test-gen"))
    monkeypatch.setattr(generator, "_coordinator_id", CoordinatorId("c-old"))
    monkeypatch.setattr(generator, "_shutdown_requested", False)

    async def fake_register():
        raise generator.CoordinatorRestartedError("Coordinator ID mismatch")

    async def fake_shutdown():
        nonlocal shutdown_called
        shutdown_called = True
        generator._shutdown_requested = True

    monkeypatch.setattr(generator, "_register_to_coordinator", fake_register)
    monkeypatch.setattr(generator, "_shutdown", fake_shutdown)

    await generator._registration_loop()

    assert shutdown_called is True


async def test_registration_loop_shuts_down_immediately_on_permission_error(monkeypatch):
    immediate_shutdown_called = False
    sleep_called = False

    monkeypatch.setattr(generator, "_generator_id", GeneratorId("test-gen"))
    monkeypatch.setattr(generator, "_coordinator_id", None)
    monkeypatch.setattr(generator, "_shutdown_requested", False)

    class ConnectorError(Exception):
        def __init__(self):
            super().__init__("Cannot connect [Operation not permitted]")
            self.os_error = PermissionError(errno.EPERM, "Operation not permitted")

    async def fake_register():
        raise ConnectorError()

    async def fake_immediate_shutdown():
        nonlocal immediate_shutdown_called
        immediate_shutdown_called = True
        generator._shutdown_requested = True

    async def fake_sleep(_delay: float):
        nonlocal sleep_called
        sleep_called = True

    monkeypatch.setattr(generator, "_register_to_coordinator", fake_register)
    monkeypatch.setattr(generator, "_immediate_shutdown", fake_immediate_shutdown)
    monkeypatch.setattr(generator.asyncio, "sleep", fake_sleep)

    await generator._registration_loop()

    assert immediate_shutdown_called is True
    assert sleep_called is False


async def test_generator_lifespan_starts_before_registration_succeeds(monkeypatch):
    attempts = 0
    original_sleep = asyncio.sleep

    monkeypatch.setattr(generator, "_coordinator_id", None)
    monkeypatch.setattr(generator, "_shutdown_requested", False)

    @asynccontextmanager
    async def fake_managed_session():
        yield

    async def fake_register():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("temporary network error")
        generator._shutdown_requested = True

    async def fake_sleep(_delay: float):
        await original_sleep(0)

    async def fake_shutdown():
        raise AssertionError("shutdown should not be requested for transient startup errors")

    monkeypatch.setattr(generator, "managed_session", fake_managed_session)
    monkeypatch.setattr(generator, "_register_to_coordinator", fake_register)
    monkeypatch.setattr(generator, "_shutdown", fake_shutdown)
    monkeypatch.setattr(generator.asyncio, "sleep", fake_sleep)

    async with generator.lifespan(object()):
        await original_sleep(0)
        assert generator.self_generator_id().startswith("g-")
        assert attempts >= 1
