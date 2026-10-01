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
- **Check a PR is still open before pushing to its branch.** If you want to add
  a follow-up change, first confirm the branch's PR hasn't been merged/closed
  (e.g. `gh pr view -H <branch> --json state`). Once a PR is merged its branch
  is closed for new work — **create a new branch off `origin/main`** for the
  follow-up and open a new PR. Don't keep committing/pushing to a merged branch;
  those commits won't appear in any review and get stranded.
- Reference the originating request/issue when relevant.

## Commits

- **Follow [Conventional Commits](https://www.conventionalcommits.org).** Format
  is `<type>(<scope>): <subject>` (scope optional), e.g.
  `feat(wishlists): add cancelable creation dialog`,
  `fix(auth): reject expired tokens`, `chore(release): v1.2.2`. The subject is
  imperative, lowercase, and has no trailing period.
- **Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`,
  `build`, `ci`, `chore`, `revert`. Use `feat` / `fix` so release notes
  categorize correctly (see Releases).
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
- **Dark mode & contrast:** WishDeck supports light and dark themes, so every
  new UI piece must stay readable in both. Quasar color utilities are
  *fixed* (e.g. `bg-grey-2` is light even in dark mode), so pairing a fixed
  light background with the inherited (white, in dark mode) text yields
  invisible text. Always set an explicit text color that contrasts the
  background, or make it theme-aware
  (e.g. `bg-grey-2 text-dark dark:bg-grey-9 dark:text-white`). Never rely on
  the inherited text color over a fixed background. Check both themes before
  reporting UI work done.
- Keep changes minimal; avoid unrelated refactors in the same PR.
- Never log or commit secrets; use environment variables for config.

## Releases

- Releases are produced by `.github/workflows/release.yml`. A release is cut when
  a PR merged to `main` carries a `major` / `minor` / `patch` label (or by
  running the workflow manually with a bump choice).
- The changelog is generated from the merged commits and **categorized by
  Conventional Commits** (Features, Bug Fixes, Breaking Changes, Dependencies,
  Other). Write commit messages accordingly so the notes are accurate.
- Every merged PR also gets an automatic "Release Notes" comment summarizing its
  conventional commits.
- Don't bump versions or cut releases by hand — let the workflow do it once the
  PR is labeled and merged.

## General

- Confirm the task scope before large changes. When unsure about permissions,
  behavior, or design, ask rather than guessing.
- After implementing, verify with tests/builds before reporting done.
