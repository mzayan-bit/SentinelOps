# SentinelOps Role-Based Access Control (RBAC)

SentinelOps implements a lightweight, API-key based RBAC system designed for machine-to-machine integration (like the inference pipeline) and administrative dashboard usage.

## Authentication

All protected API endpoints require an API key to be passed via the `X-API-Key` HTTP header.

```bash
curl -X GET "http://localhost:8000/alerts" \
     -H "X-API-Key: sentinelops-admin-key"
```

> [!NOTE]
> The `/health` endpoint and WebSocket streaming endpoints (`/ws/stream/{id}`) do NOT require an API key.

## Roles

The system enforces a strict role hierarchy where higher roles inherit all permissions of lower roles.

1. **Admin (3)**: Full system access. Can delete alerts and cameras.
2. **Supervisor (2)**: Operational access. Can create/update alerts, assign/resolve alerts, generate reports, log incidents, and start/stop camera processing streams. Cannot delete data.
3. **Viewer (1)**: Read-only access. Can list alerts, view analytics, download reports, view camera health.

## Permission Matrix

| Endpoint | Viewer | Supervisor | Admin |
|---|---|---|---|
| `GET /alerts` | ✅ | ✅ | ✅ |
| `GET /analytics/*` | ✅ | ✅ | ✅ |
| `GET /reports` | ✅ | ✅ | ✅ |
| `GET /api/cameras` | ✅ | ✅ | ✅ |
| `POST /alerts` | ❌ | ✅ | ✅ |
| `PUT /alerts/{id}` | ❌ | ✅ | ✅ |
| `POST /reports/generate` | ❌ | ✅ | ✅ |
| `POST /api/incidents` | ❌ | ✅ | ✅ |
| `POST /api/cameras/{id}/start` | ❌ | ✅ | ✅ |
| `DELETE /alerts/{id}` | ❌ | ❌ | ✅ |
| `DELETE /api/cameras/{id}` | ❌ | ❌ | ✅ |
| `POST /api/cameras` | ❌ | ❌ | ✅ |

## Configuration

Users and API keys are stored in a simple JSON file located at `config/users.json`. The application reads this file at startup.

```json
{
  "users": [
    {
      "username": "admin",
      "role": "admin",
      "api_key": "sentinelops-admin-key"
    },
    {
      "username": "operator_bot",
      "role": "supervisor",
      "api_key": "pipeline-webhook-key-x8z"
    }
  ]
}
```

To rotate a key or add a user, simply modify the `config/users.json` file. Note that a restart of the API service is required for the new users to be loaded into memory.

## Testing

For automated testing, the RBAC system includes a global disable switch. When using the `_disable_auth_for_tests` fixture (enabled by default in `conftest.py`), all endpoints simulate authentication as an Admin user, ensuring legacy tests do not break.

To explicitly test RBAC behaviors, tests should call `set_auth_enabled(True)` or use the `test_rbac.py` module setup.
