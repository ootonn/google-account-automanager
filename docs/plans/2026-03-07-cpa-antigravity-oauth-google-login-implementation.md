# Antigravity OAuth Google Login Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reuse existing Google password/TOTP automation so `cpa_oauth_bind` can complete real Antigravity OAuth flows and capture the callback URL.

**Architecture:** Keep the CPA management client and callback capture flow unchanged, but insert a Google account login helper inside `web/backend/services/cpa_oauth_antigravity.py` before the callback-wait phase settles. Reuse the existing `ensure_authenticator_method`, `handle_recovery_email_challenge`, and TOTP generation patterns from `run_playwright_google.py`/`google_recovery.py`, and keep logging sanitized.

**Tech Stack:** Python 3.12, Playwright CDP, BitBrowser, FastAPI task runner, `pyotp`

---

### Task 1: Lock desired OAuth login behavior with tests

**Files:**
- Modify: `web/backend/tests/test_tasks_cpa_oauth_bind.py`
- Modify: `web/backend/tests/test_cpa_oauth_callback_parser.py`

**Step 1: Write the failing test**
- Add a test that proves `execute_cpa_oauth_bind` passes account credentials into the browser automation layer so Google login/TOTP can run.
- Add a parser-level test if needed for recognizing callback URLs only after login flow completes.

**Step 2: Run test to verify it fails**
- Run: `python -m pytest web/backend/tests/test_tasks_cpa_oauth_bind.py -q`
- Expected: FAIL because the automation call currently has no account credential payload.

**Step 3: Write minimal implementation**
- Thread account credentials from task runner into the Antigravity browser automation call without changing unrelated task behavior.

**Step 4: Run test to verify it passes**
- Run: `python -m pytest web/backend/tests/test_tasks_cpa_oauth_bind.py -q`
- Expected: PASS.

### Task 2: Add Google login/TOTP automation into Antigravity OAuth browser flow

**Files:**
- Modify: `web/backend/services/cpa_oauth_antigravity.py`
- Reuse references: `run_playwright_google.py`, `google_recovery.py`
- Test: `web/backend/tests/test_tasks_cpa_oauth_bind.py`

**Step 1: Write the failing test**
- Add a focused test for the new helper behavior where account credentials are present and the login helper is invoked before waiting for callback capture.

**Step 2: Run test to verify it fails**
- Run: `python -m pytest web/backend/tests/test_tasks_cpa_oauth_bind.py -q`
- Expected: FAIL because no Google login helper exists in the OAuth flow yet.

**Step 3: Write minimal implementation**
- Add a helper inside `cpa_oauth_antigravity.py` that:
  - fills Google email/password when prompted,
  - switches to Authenticator when needed,
  - submits current TOTP from stored secret,
  - handles recovery-email challenge when shown,
  - keeps waiting for callback after login succeeds.

**Step 4: Run test to verify it passes**
- Run: `python -m pytest web/backend/tests/test_tasks_cpa_oauth_bind.py -q`
- Expected: PASS.

### Task 3: Re-verify backend and real E2E

**Files:**
- Modify: `docs/plans/2026-03-05-cpa-antigravity-oauth-binding-verification.md`

**Step 1: Run backend verification**
- Run: `python -m pytest web/backend/tests -q -W error::pydantic.warnings.PydanticDeprecatedSince20`
- Expected: PASS with zero warning failures.

**Step 2: Run real E2E**
- Start backend/frontend in this worktree.
- Reapply real CPA config from `data/test.data`.
- Run single-account `cpa_oauth_bind` via `/api/tasks` and collect `/ws` logs.
- Expected: logs reach `capture callback -> submit callback -> status ok/error` instead of stalling at Google sign-in.

**Step 3: Document evidence**
- Record exact real-E2E result and any remaining blocker in `docs/plans/2026-03-05-cpa-antigravity-oauth-binding-verification.md`.
