# Workflow rules (enforced for this project)

Apply these rules for every task unless the user overrides. Full prose version
lives in `AGENTS.md`.

## Branches & PRs
- Never commit/push to `main`. Create a short-lived feature branch.
- Branch naming: `feat/`, `fix/`, `chore/`, `docs/`, `refactor/`, `test/` + kebab slug.
- One logical change per branch/PR. Base off `origin/main` (fetch first).
- Do NOT re-include work already merged to `main` in a new PR.
- Open PRs against `main` via `gh pr create --base main --head <branch>`.
  Include: concise title, Summary, What changed, Test plan, and caveats
  (e.g. depends on another PR, or part already in `main`).
- Reference the originating request/issue when relevant.

## Commits
- Use Conventional Commits: `<type>(<scope>): <subject>` (types: feat, fix,
  docs, style, refactor, perf, test, build, ci, chore, revert). Imperative,
  lowercase subject, no trailing period. `feat`/`fix` drive release notes.
- Review `git status` / `git diff`; stage only intended files. Never commit
  secrets, `.env`, or credentials. No build artifacts.

## Releases
- `.github/workflows/release.yml` cuts a release when a merged PR to `main` has a
  `major`/`minor`/`patch` label (or via manual dispatch). Notes are generated
  from Conventional Commits and categorized; each merged PR also gets a release
  notes comment. Don't bump versions by hand.

## Pre-commit / pre-PR checks (match CI)
- Backend: `cd backend && pytest -q`
- Frontend: `cd frontend && npm test` and `npx quasar build`
- If a check can't run locally, say so in the PR.

## Migrations
- Model changes need a new Alembic migration in
  `backend/migrations/versions/` with correct `down_revision`.
- Never edit a committed migration; add a new one.

## Testing
- Update existing tests when behavior changes; a change that breaks CI tests
  without updating them is incomplete (fix the tests, don't skip them).
- Add tests for every user-facing workflow (auth, wishlists, items, sharing,
  roles/permissions, settings) — unit/component plus a Playwright path for
  critical flows. Include the tests in the same PR as the feature.

## Code conventions
- Match existing style; reuse existing libs; don't add deps without reason.
- i18n: add keys to BOTH `en` and `sv` and keep valid JS (a stray brace breaks
  `quasar build`).
- Keep changes minimal; avoid unrelated refactors.
- Never log/commit secrets; use env vars.
