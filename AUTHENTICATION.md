# Authentication and multi-user setup

Meeting Brain now supports two API authentication modes.

## Development mode

By default, protected API endpoints stay open for local development when neither
`API_AUTH_TOKEN` nor `AUTH_REQUIRE_LOGIN=true` is configured.

## Service-token mode

Set `API_AUTH_TOKEN` to protect existing endpoints with one shared bearer token:

```env
API_AUTH_TOKEN=change-me
AUTH_REQUIRE_LOGIN=false
```

Use it with:

```http
Authorization: Bearer change-me
```

This is simple, but it is not ideal for several real users because all requests
share the same identity.

## User-token mode

Set:

```env
AUTH_REQUIRE_LOGIN=true
API_AUTH_TOKEN=
```

Start the API, then create the first admin while the `users` table is empty:

```bash
curl -X POST http://localhost:8000/auth/bootstrap \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"change-this-password","display_name":"Admin"}'
```

The response contains a bearer token. Store it securely; only a hash is saved in
the database.

Users can later get a fresh token with:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"change-this-password"}'
```

Check the active identity:

```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <token>"
```

Create another user as an admin:

```bash
curl -X POST http://localhost:8000/auth/users \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"email":"member@example.com","password":"change-this-password","display_name":"Member","role":"member"}'
```

Supported roles:

- `admin`: can see all data, create users, assign TODOs.
- `member`: can see meetings they created and TODOs assigned to them; can update those TODOs.
- `viewer`: can read data in their own scope but cannot modify TODOs.

Protected read endpoints automatically apply this scope when user-token mode is
enabled. In development mode, or when using the legacy `API_AUTH_TOKEN`, the API
keeps the previous global behavior.

Update a TODO status:

```bash
curl -X PATCH http://localhost:8000/todos/123/status \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"status":"in_progress","note":"Started from API"}'
```

Assign a TODO:

```bash
curl -X PATCH http://localhost:8000/todos/123/assignee \
  -H "Authorization: Bearer <admin-or-creator-token>" \
  -H "Content-Type: application/json" \
  -d '{"assigned_user_id":2}'
```

## Database

For multiple users, prefer PostgreSQL instead of the default SQLite file:

```env
MEETING_BRAIN_DB_URL=postgresql+psycopg://user:password@host:5432/meeting_brain
```

SQLite remains useful locally, but PostgreSQL handles concurrent writes,
backups, and deployment better.

## Streamlit integration

The `All TODOs` Streamlit view now uses the FastAPI backend instead of opening a
database session directly. Configure:

```env
MEETING_BRAIN_API_URL=http://localhost:8000
MEETING_BRAIN_API_TOKEN=
```

When user-token mode is enabled, users can log in from the TODOs sidebar panel
or paste a bearer token. This keeps TODO listing, status updates, and assignment
changes behind the same FastAPI authorization checks as external API clients.
