"""coordinator-generator間の通信のテスト"""

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
