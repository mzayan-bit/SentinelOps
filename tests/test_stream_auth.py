"""
Tests for WebSocket stream authentication.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from app.api.stream_routes import router
from app.auth import _user_store, Role, User, set_auth_enabled


app = FastAPI()
app.include_router(router)

@pytest.fixture(autouse=True)
def setup_auth(monkeypatch):
    """Ensure auth is enabled and mock user store for testing."""
    set_auth_enabled(True)
    
    mock_user = User(username="viewer", role=Role.VIEWER, api_key="valid-key")
    
    def mock_authenticate(api_key: str) -> User | None:
        if api_key == "valid-key":
            return mock_user
        return None
        
    monkeypatch.setattr(_user_store, "authenticate", mock_authenticate)
    
    yield
    
    set_auth_enabled(False)


def test_websocket_missing_token():
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/stream/cam1"):
            pass
    assert exc_info.value.code == 1008


def test_websocket_invalid_token():
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/stream/cam1?api_key=invalid"):
            pass
    assert exc_info.value.code == 1008


def test_websocket_valid_token_query():
    client = TestClient(app)
    # Should connect successfully without raising WebSocketDisconnect
    with client.websocket_connect("/ws/stream/cam1?api_key=valid-key") as websocket:
        # Just connecting and exiting the block is enough to prove it didn't reject
        pass


def test_websocket_valid_token_header():
    client = TestClient(app)
    with client.websocket_connect("/ws/stream/cam1", headers={"x-api-key": "valid-key"}) as websocket:
        pass
