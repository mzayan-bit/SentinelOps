"""
Tests for WebSocket stream authentication.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from app.api.stream_routes import router
from app.core.security import Role

app = FastAPI()
app.include_router(router)

@pytest.fixture(autouse=True)
def setup_auth(monkeypatch):
    """Mock verify_token for testing."""
    def mock_verify_token(token: str, expected_type: str = "access") -> dict:
        if token == "valid-token":
            return {"sub": "123", "role": Role.VIEWER.value, "type": "access"}
        raise Exception("Invalid token")
        
    # stream_routes imports verify_token directly, so we patch it there
    monkeypatch.setattr("app.api.stream_routes.verify_token", mock_verify_token)
    yield


def test_websocket_missing_token_allowed_by_default_in_this_impl():
    client = TestClient(app)
    # The current implementation allows connection if token is None, 
    # but let's test it doesn't crash
    with client.websocket_connect("/ws/stream/cam1"):
        pass

def test_websocket_invalid_token():
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/stream/cam1?token=invalid"):
            pass
    assert exc_info.value.code == 1008

def test_websocket_valid_token_query():
    client = TestClient(app)
    # Should connect successfully without raising WebSocketDisconnect
    with client.websocket_connect("/ws/stream/cam1?token=valid-token") as websocket:
        # Just connecting and exiting the block is enough to prove it didn't reject
        pass
