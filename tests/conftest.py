import pytest

@pytest.fixture(autouse=True)
def _disable_auth_for_tests():
    """
    Globally disable API key authentication for all existing tests.
    
    Since we introduced RBAC late, we don't want to break the 98 existing
    tests that don't send X-API-Key headers. This fixture mocks the auth
    check globally to allow all tests to pass.
    
    Tests in `test_rbac.py` will explicitly re-enable auth to test it.
    """
    import os
    os.environ["TESTING"] = "1"
    
    from app.core.security import set_auth_enabled
    
    set_auth_enabled(False)
    yield
    # Restore true state after test (though it will just be disabled again next test)
    set_auth_enabled(True)
