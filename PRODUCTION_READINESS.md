# Production Readiness Checklist

## 1. Security
- [x] `.env` excluded from git.
- [x] `.env.example` provided with non-secret placeholders.
- [x] Backend enforces `SECRET_KEY` outside development mode.
- [x] OAuth state validation implemented using signed cookie.
- [ ] Rotate all previously exposed GitHub credentials/tokens.
- [ ] Move secrets to deployment secret manager (not file-based on server).

## 2. Auth & Sessions
- [x] Session cookie uses environment-based `secure` and `samesite`.
- [x] Session TTL configurable (`SESSION_TTL_SECONDS`).
- [x] Replace `sessions.json` with SQLite-backed session store (`sessions.db`).
- [ ] Add CSRF protections for state-changing endpoints.
- [ ] Optional: move sessions from SQLite to Redis for multi-instance horizontal scaling.

## 3. Reliability
- [x] AI model fallback and status endpoint (`/api/ai-status`) added.
- [x] Recursive file tree endpoint with graceful fallback.
- [x] Better GitHub/Ollama error messages exposed to frontend.
- [ ] Add circuit-breaker/retry policy for repeated upstream failures.

## 4. Observability
- [x] Request ID added on all responses (`X-Request-ID`).
- [x] Basic request latency logging middleware added.
- [ ] Centralized structured logging sink (ELK/Datadog/etc.).
- [ ] Error alerting and uptime checks.

## 5. Quality Gates
- [x] Static checks currently passing (`py_compile`, frontend lint).
- [x] Add backend API tests for auth/session lifecycle (`tests/test_auth_sessions.py`).
- [ ] Extend backend API tests to files/chat endpoints.
- [ ] Add frontend integration tests (repo tree + file preview + chat).
- [ ] CI pipeline enforcing lint/tests before merge.

## Recommended Next Sprint
1. Replace file-based session store with Redis.
2. Add automated tests for core flows.
3. Add deployment config for managed secrets and observability.
