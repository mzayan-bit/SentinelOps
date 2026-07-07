import pytest
import os

@pytest.fixture(autouse=True)
def _disable_auth_for_tests():
    """
    Globally disable API key/JWT authentication for all existing tests.
    """
    os.environ["TESTING"] = "1"
    
    from app.api.app import app
    from app.core.security import get_current_user, Role
    from app.db.models import UserModel, OrganizationModel
    
    mock_org = OrganizationModel(id="org-1", name="Test Org")
    mock_user = UserModel(id="1", email="test@test.com", role=Role.SUPER_ADMIN, is_active=True, organization=mock_org)
    
    async def mock_get_user():
        return mock_user
        
    app.dependency_overrides[get_current_user] = mock_get_user
    
    yield
    
    app.dependency_overrides = {}
