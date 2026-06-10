# Phase 4B: Quick Start for Future Sessions

**TL;DR:** Phase 4B adds a public REST API behind API keys. Developers create keys in settings UI, use them to call `/v1/generate/start` + `/v1/generate/answer` for stateless prompt generation.

## One-Minute Overview

```
User creates API key in UI
        ↓
Raw key displayed once (pf_abc123xyz...)
        ↓
Developer uses: curl -H "X-API-Key: pf_abc123xyz..." POST /v1/generate/start
        ↓
API returns: session_id, status="needs_question", question object
        ↓
Developer answers via POST /v1/generate/answer
        ↓
Final response: status="done", prompt + score
```

## What Changed

### New Database Table
```
api_keys:
  - id (UUID PK)
  - user_id (FK)
  - name (e.g., "My App")
  - key_hash (SHA-256, unique)
  - key_prefix (display only)
  - rate_limit_per_minute (default 60)
  - created_at, last_used_at, revoked
```

### New Routes
```
[JWT-Protected: authenticated users]
POST   /v1/keys              → create API key (shows raw key once)
GET    /v1/keys              → list user's active keys
DELETE /v1/keys/{id}         → revoke a key

[X-API-Key Protected: external developers]
POST   /v1/generate/start    → begin session (input → question or done)
POST   /v1/generate/answer   → answer question (session_id, slot_id, answer → next state)
```

### New UI
- `/settings/api-keys` page to create/revoke keys
- Raw key banner (copy-to-clipboard, shown once)
- Keys table (Name, Prefix, Last Used, Revoke button)

## File Structure

```
apps/api/
  ├─ app/
  │  ├─ api_keys/
  │  │  ├─ service.py        (generate_key, lookup_key, revoke_key, list_keys)
  │  │  ├─ schemas.py        (Pydantic models for request/response)
  │  │  └─ routes.py         (GET/POST/DELETE /v1/keys endpoints)
  │  ├─ auth/
  │  │  └─ api_key_deps.py   (validate_api_key dependency)
  │  ├─ embed/
  │  │  ├─ schemas.py        (public API request/response models)
  │  │  └─ routes.py         (POST /v1/generate/* endpoints)
  │  └─ db/
  │     └─ models.py         (+ ApiKey model)
  ├─ migrations/
  │  └─ versions/
  │     └─ 0006_api_keys.py  (create api_keys table)
  └─ tests/
     ├─ test_api_keys.py
     ├─ test_api_key_deps.py
     └─ test_embed_routes.py

apps/web/
  ├─ lib/
  │  └─ api-keys-api.ts      (listApiKeys, createApiKey, revokeApiKey)
  └─ app/settings/
     ├─ api-keys/
     │  └─ page.tsx          (key management UI)
     └─ page.tsx             (settings nav)
```

## Key Concepts

### Raw Key = Never Stored
- User gets: `pf_abc123xyz...` (full raw key, 40+ chars)
- Database stores: SHA-256 hash only
- On API request: hash raw key from header, look up by hash
- If DB breached: attacker can't use keys (doesn't have raw key)

### Rate Limiting = Per-Minute Buckets
- Redis key format: `rl:apikey:{user_id}:{minute}`
- On first request in minute: INCR, set TTL 120s
- On subsequent requests: INCR, check if count > limit (429 if yes)
- If Redis down: allow request (graceful degradation)

### Sessions = Shared Store
- `SessionStore()` is module-level singleton
- Sessions created via `/v1/generate/start` use same store as internal pipeline
- Sessions don't persist (in-memory + optional Redis)

### Two Auth Schemes
- **JWT Bearer token** (`Authorization: Bearer ...`) — for web UI, internal endpoints
- **X-API-Key header** (e.g., `X-API-Key: pf_abc123...`) — for external API, public endpoints

## Common Tasks

### Add a New API Route Under `/v1/generate`
1. Add Pydantic model to `apps/api/app/embed/schemas.py`
2. Add handler to `apps/api/app/embed/routes.py` with `@router.post(...)` or `@router.get(...)`
3. Use `Depends(validate_api_key)` for auth
4. Return `EmbedTurnResponse` or similar public schema
5. Add tests in `apps/api/tests/test_embed_routes.py`
6. Commit

### Add Rate Limit Tier
1. Modify `ApiKey` model to add `tier` column (e.g., "free", "pro", "enterprise")
2. Update migration
3. Modify `validate_api_key()` to check tier → look up limit from config
4. Test

### Add API Analytics
1. Create `ApiKeyUsage` model (user_id, key_id, request_count, timestamp)
2. In `validate_api_key()`, increment usage counter after successful auth
3. Build dashboard to query usage by key/user

## Testing

### Run New Tests Only
```bash
cd apps/api
uv run pytest tests/test_api_keys.py tests/test_api_key_deps.py tests/test_embed_routes.py -v
```

### Run All Tests
```bash
cd apps/api
uv run pytest --tb=short -q
```

### Debug a Test
```bash
cd apps/api
uv run pytest tests/test_api_keys.py::TestGenerateKey::test_returns_raw_key_and_model -vv
```

## Known Issues

- 2 pre-existing test failures (`test_model_picker.py`, `test_module_editor.py`) — unrelated to phase 4b
- SessionStore not thread-safe (acceptable for MVP)
- `last_used_at` updates may race on concurrent requests (spec: "best effort")

## Next Steps

- **Code Review:** PR #4 ready for review
- **Merge:** After approval, merge to main
- **Deploy:** Update `NEXT_PUBLIC_API_BASE` in production environment
- **Documentation Site:** Create API reference for external developers
- **SDK Generation:** Consider OpenAPI spec → auto-generate SDKs (Python, JS, etc.)

## References

- **Summary:** `docs/superpowers/PHASE4B_SUMMARY.md`
- **Plan:** `docs/superpowers/plans/2026-06-10-phase4b-public-api.md`
- **PR:** https://github.com/NeamulMorshed/prompt-forge/pull/4
- **Branch:** `feature/phase4b-public-api`
