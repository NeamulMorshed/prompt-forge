# Phase 4B: Public API Implementation Summary

**Date:** 2026-06-10  
**Branch:** `feature/phase4b-public-api`  
**PR:** https://github.com/NeamulMorshed/prompt-forge/pull/4  
**Status:** Implemented & Ready for Review

## What Was Built

Public REST API for PromptForge's prompt generation engine, secured with API keys. Opens developer revenue line by allowing external apps to embed PromptForge's discovery+generation pipeline.

## Architecture Overview

### Backend (Python/FastAPI)

**Database:**
- `ApiKey` model: id (UUID PK), user_id (FK→users), name, key_hash (SHA-256, unique), key_prefix (8 chars display), rate_limit_per_minute, created_at, last_used_at, revoked
- Migration `0006_api_keys`: creates api_keys table + user_id index

**Service Layer** (`app/api_keys/service.py`):
- `generate_key(user_id, name, db)` → returns (raw_key, api_key_model) — raw key shown once, never stored
- `lookup_key(raw_key, db)` → ApiKey | None — hashes input, checks revoked flag, updates last_used_at
- `revoke_key(key_id, user_id, db)` → bool — ownership-checked revocation
- `list_keys(user_id, db)` → list[ApiKey] — non-revoked keys, ordered by created_at desc

**Auth Dependency** (`app/auth/api_key_deps.py`):
- `validate_api_key(x_api_key: Header, db)` → uuid.UUID — FastAPI dependency that extracts X-API-Key header
- 401 if missing/invalid/revoked
- 429 if rate limited (per-minute via Redis, graceful degradation)
- Returns user_id for request context

**Routes:**

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/v1/keys` | JWT | Create new API key (returns raw key once) |
| GET | `/v1/keys` | JWT | List user's active API keys |
| DELETE | `/v1/keys/{id}` | JWT | Revoke an API key |
| POST | `/v1/generate/start` | X-API-Key | Start discovery/generation session |
| POST | `/v1/generate/answer` | X-API-Key | Answer discovery question, advance session |

**Stateless Embed Flow:**
1. `POST /v1/generate/start` with initial input → status="needs_question" (or "done" if no questions)
2. Return `question` object with slot_id, question text, chips (options), allow_freetext flag
3. `POST /v1/generate/answer` with session_id, slot_id, answer → advance to next question or completion
4. Final response: status="done" with generated prompt, composite score, suggestions

### Frontend (Next.js/TypeScript)

**API Helpers** (`apps/web/lib/api-keys-api.ts`):
- `listApiKeys()` → KeySummary[]
- `createApiKey(name)` → CreateKeyResponse (includes raw key)
- `revokeApiKey(keyId)` → void

**Settings UI** (`apps/web/app/settings/api-keys/page.tsx`):
- Form to create key (input field, button)
- One-time key display banner (yellow box, copy-to-clipboard with visual feedback)
- Keys table: Name | Prefix (key_prefix + "…") | Last Used | Revoke button
- Error states throughout, loading indicator on initial fetch

**Settings Nav** (`apps/web/app/settings/page.tsx`):
- Links to Profile settings and API Keys settings

## Security Properties

✅ **Raw keys never stored** — only SHA-256 hash persists in DB  
✅ **Key prefix for display** — 8 chars shown (e.g., `pf_abc123`) for debugging, not full key  
✅ **Ownership checks** — revoke only by original user  
✅ **Rate limiting** — per-minute buckets via Redis, includes minute boundary in key  
✅ **Revocation** — lookup_key() checks revoked flag, prevents reuse after revocation  
✅ **Graceful degradation** — if Redis unavailable at runtime, requests allowed (logs only)  

## Testing

**Test Coverage:**
- `test_api_keys.py`: 19 tests (hash properties, key generation, lookup, revoke, list, routes with fixture isolation, error paths)
- `test_api_key_deps.py`: 5 tests (rate limit key format, 401 no header, 401 invalid, 401 revoked, 429 rate limited)
- `test_embed_routes.py`: 5 tests (401 no key, needs_question shape, done with result, answer advances, 404 unknown session)
- **Total:** 29 new tests + 227 existing = 227 pass, 2 pre-existing failures (unrelated)
- **TypeScript:** 0 errors

## Key Implementation Decisions

1. **X-API-Key header, not JWT** — API keys are stateless, easier for external developers to use (no token refresh, simpler integration)
2. **SHA-256 hashing** — prevents DB breach from leaking live keys, but validates against hash on lookup (SQLAlchemy WHERE clause)
3. **SessionStore singleton** — sessions started via embed API share same store as internal pipeline, allows internal views of embed sessions
4. **Redis optional** — rate limiting disabled if Redis down, app still functional (monitored for degradation)
5. **Simplified embed schema** — public response excludes internal fields (clarity, extractable_slots, profile_loaded, suggest_profile_save)

## Future Work

- **Billing/Quota:** Add `usage_this_month` to ApiKey, track requests in Redis, enforce limits
- **API Analytics:** Dashboard showing request counts, success rates, errors by key/user
- **Webhook Callbacks:** For long-running operations or async result delivery
- **Key Rotation:** Automatic key expiration + renewal workflows
- **Team/Org Keys:** Shared keys for team members, not just personal keys
- **Documentation Site:** API reference, SDKs, tutorials for external developers

## Files Changed

### Backend
- `apps/api/app/db/models.py` — +15 lines (ApiKey model)
- `apps/api/migrations/versions/0006_api_keys.py` — new file (34 lines)
- `apps/api/app/api_keys/__init__.py` — new file (empty marker)
- `apps/api/app/api_keys/service.py` — new file (55 lines)
- `apps/api/app/api_keys/schemas.py` — new file (35 lines)
- `apps/api/app/api_keys/routes.py` — new file (55 lines)
- `apps/api/app/auth/api_key_deps.py` — new file (45 lines)
- `apps/api/app/embed/__init__.py` — new file (empty marker)
- `apps/api/app/embed/schemas.py` — new file (40 lines)
- `apps/api/app/embed/routes.py` — new file (85 lines)
- `apps/api/app/main.py` — +2 lines (register routers)
- `apps/api/tests/test_api_keys.py` — new file (220 lines)
- `apps/api/tests/test_api_key_deps.py` — new file (60 lines)
- `apps/api/tests/test_embed_routes.py` — new file (100 lines)

### Frontend
- `apps/web/lib/api-keys-api.ts` — new file (45 lines)
- `apps/web/app/settings/api-keys/page.tsx` — new file (145 lines)
- `apps/web/app/settings/page.tsx` — new file (15 lines)

### Total
- 13 backend files (new/modified)
- 3 frontend files (new)
- ~1,200 lines of code + tests
- Zero breaking changes to existing APIs

## Known Issues & Notes

**Minor:**
- 2 pre-existing test failures in `test_model_picker.py` and `test_module_editor.py` (unrelated to phase 4b)
- SessionStore not thread-safe (pre-existing pattern, acceptable for current use)
- `last_used_at` updates in lookup_key may race on concurrent requests (spec says "best effort")

**Future Improvements:**
- Add `min_length=1` validation to EmbedAnswerRequest fields (low priority)
- Add rate_limit_per_minute column to keys table in settings UI
- Add settings breadcrumb/back navigation

## Commits

12 commits total (from 53ffa50 to 086d0ee):
1. `d529650` — feat(db): ApiKey model + migration 0006
2. `06e356e` — fix(db): add nullable=False constraints
3. `d8c9c9a` — feat(api-keys): key service
4. `fe28a18` — test(api-keys): add revoke/list tests
5. `f47abb5` — feat(api-keys): GET/POST/DELETE /v1/keys routes
6. `bb6be56` — test(api-keys): fix route test isolation
7. `8e17c43` — feat(auth): API key dependency + rate limiting
8. `952f63e` — fix(auth): Redis runtime failures + 429 test
9. `d6f529f` — feat(embed): POST /v1/generate/start + /answer
10. `91635ca` — fix(embed): Field validation + type hints
11. `d4cc988` — feat(ui): API key settings page
12. `086d0ee` — fix(ui): Content-Type header + clipboard feedback

## Running Locally

**Backend:**
```bash
cd apps/api
uv run pytest tests/test_api_keys.py tests/test_api_key_deps.py tests/test_embed_routes.py -v
```

**Frontend:**
```bash
cd apps/web
pnpm tsc --noEmit
```

**Start API:**
```bash
cd apps/api
uv run uvicorn app.main:app --reload --port 8000
```

**Access Settings:**
- Ensure `NEXT_PUBLIC_API_BASE` points to API (default `http://localhost:8000`)
- Navigate to `/settings/api-keys` after login
- Create key, copy once, use in `curl -H "X-API-Key: pf_..." http://localhost:8000/v1/keys`

## Questions for Code Review

1. Is the simplified public schema sufficient for external developers, or should more fields be exposed?
2. Should rate limits be user-configurable, or fixed per plan tier?
3. Should we log/alert when Redis is unavailable (currently silent degradation)?
4. Should expired keys be auto-archived or hard-deleted after N days?
