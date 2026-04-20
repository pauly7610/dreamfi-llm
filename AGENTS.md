# Agent conventions (for Claude Code / Cursor)

## Non-negotiables

1. **Never modify** files under `evals/` (templates or runners). They are locked by repository policy.
2. **Never hand-edit** Alembic revisions that have already shipped; create new ones.
3. All Onyx HTTP must go through `dreamfi.onyx.client.OnyxClient`. No raw
   `httpx`/`requests` calls to Onyx anywhere else.
4. In unit tests, mock Onyx with `respx`. Live-Onyx tests are marked
   `@pytest.mark.live_onyx` and run only with `make test-live`.
5. Database tests use either in-memory SQLite or a tmp-path SQLite. No
   network calls in unit tests.
6. Strict typing on `dreamfi/`. Runtime magic numbers live in
   `dreamfi/config.py`.

## Adding a new skill (should be rare — we ship 9)

1. Add the locked eval template under `evals/<name>.md`.
2. Add the locked runner class under `evals/runners/run_<name>_eval.py`.
3. Register it in `dreamfi/skills/registry.py` (the `SKILLS` tuple) and add
   a Jinja prompt under `dreamfi/skills/prompts/`.

## Test layout

- `tests/unit/` - fully local, fast.
- `tests/integration/onyx/` - `live_onyx`-marked; need `$ONYX_BASE_URL`.
