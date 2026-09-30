# AGENTS.md — Development conventions for LLM-assisted work

These rules keep automated (LLM) and human changes consistent. Follow them for
every task unless the user explicitly overrides.

## Branching & pull requests

- **Never commit or push directly to `main`.** Always work on a short-lived
  feature branch.
- **Branch naming:** `feat/<kebab-description>`, `fix/...`, `chore/...`,
  `docs/...`, `refactor/...`, `test/...`. Use a descriptive, lowercase slug.
- **One logical change per branch/PR.** Don't mix unrelated work (e.g. a feature
  and a meta/docs change) unless the user asks for it explicitly.
- **Base off `origin/main`** (run `git fetch origin main` first). If a related
  change is already merged to `main`, do **not** re-include it in a new PR.
- **Open PRs against `main`** with `gh pr create --base main --head <branch>`
  (or the hosting UI). Every PR needs:
  - a concise title,
  - a description with *Summary*, *What changed*, and *Test plan*,
  - any caveats (e.g. depends on another open PR, or part of the feature is
    already in `main`).
- Reference the originating request/issue when relevant.

## Commits

- Subject: imperative, concise ("Add collaborator manager roles"), no trailing
  period. Optional body for *why*, not *what*.
- **Stage only intended files.** Always review `git status` and `git diff`
  before committing. Never commit secrets, `.env`, or credentials.
- Don't commit build artifacts or generated files (`node_modules/`, `.venv/`
  are gitignored already).
- Prefer small, reviewable commits. Don't force-push shared branches unless
  asked.

## Before committing / opening a PR

Run the same checks CI runs so PRs are green:

- Backend: `cd backend && pytest -q`
- Frontend: `cd frontend && npm test` and `npx quasar build`
- (If an ESLint config exists, run `npm run lint`; one is not configured yet —
  adding one is welcome but not required.)

If you cannot run a check locally, say so and note it in the PR.

## Testing

- **Update tests when behavior changes.** If a change alters existing behavior
  (UI flow, API contract, validation, error handling, or permissions), update
  the affected unit, component, and/or e2e tests so they assert the *new*
  behavior. A change that breaks CI tests without updating them is incomplete —
  fix or update the tests, don't skip/disable them to go green.
- **Tests for every workflow.** Every user-facing workflow must have test
  coverage: registration, login, wishlist create/edit/delete, item add/archive,
  sharing/collaborators, roles/permissions, and settings. Prefer unit/component
  tests where practical, plus at least one end-to-end (Playwright) path for the
  critical flows. **Add a workflow's tests in the same PR as the feature.**
- Backend tests: `cd backend && pytest -q`. Frontend tests: `cd frontend &&
  npm test`. Run them before opening a PR and resolve failures.

## Database / migrations

- Model changes **must** be accompanied by a new Alembic migration under
  `backend/migrations/versions/` with the correct `down_revision` (the latest
  revision id).
- **Never edit an already-committed migration.** Add a new one instead.
- `init_db()` only creates missing tables, so migrations are the source of truth
  for schema in deployed environments.

## Code conventions

- Match existing style. Reuse existing libraries/utilities; don't add new
  dependencies without a reason.
- Backend: FastAPI + async SQLAlchemy + Pydantic v2. Keep request/response
  schemas in `app/schemas/__init__.py`; authz helpers belong near the router
  they guard.
- Frontend: Vue 3 `<script setup>`, Quasar, Pinia. Keep components small.
- **i18n:** every user-facing string needs keys in **both** `en` and `sv`
  (`frontend/src/i18n/{en,sv}/index.js`). Keep the two files in sync and
  valid JS (a stray brace breaks the production `quasar build`).
- Keep changes minimal; avoid unrelated refactors in the same PR.
- Never log or commit secrets; use environment variables for config.

## General

- Confirm the task scope before large changes. When unsure about permissions,
  behavior, or design, ask rather than guessing.
- After implementing, verify with tests/builds before reporting done.
