# Agent guide

CLI that syncs a tree of markdown notes into Anki via the AnkiConnect HTTP API.
Each `.md` becomes one or more notes; a sibling `.anki` JSON sidecar stores
the created Anki note IDs keyed by 1-based card position so re-runs update
in place instead of duplicating.

## Layout

- `markdown_to_anki/cli.py` — Click entry (`m2a check | init | sync | sync_web`).
- `markdown_to_anki/services/anki.py` — `import_notes`, `import_medias`, `ensure_models`, built-in + user model definitions.
- `markdown_to_anki/services/anki_api.py` — thin HTTP client for AnkiConnect (default `localhost:8765`).
- `markdown_to_anki/services/render.py` — markdown→HTML, frontmatter parsing, card/field splitting.
- `markdown_to_anki/helpers/store.py` — `.anki` sidecar read/write.
- `markdown_to_anki/helpers/path.py` — resources-dir override; built-in templates/CSS live in `markdown_to_anki/resources/anki/`.
- `markdown_to_anki/config.py` — env + `~/.config/markdown-to-anki/config.yaml` resolution.

## Conventions

- Config precedence: CLI flag → env (`ANKI_URL`, `MD_FOLDER`, `M2A_RESOURCES_DIR`, `TIME_RANGE`) → YAML file → default.
- `TIME_RANGE` (default 7200s) skips files whose mtime is older. This is the change-detection mechanism — `touch` a file to force re-sync.
- Card/field syntax inside markdown is **literal HTML comments** ignored by the parser; splitting is plain string ops:
  - `<!--CARD-->` separates cards within one file.
  - `<!--FIELD-->` separates fields within a card.
  - `<!--TAGS: a, b-->` adds per-card tags on top of file-level `tags:` frontmatter.
- Built-in models: `m2a-basic`, `m2a-basic-reverse`, `m2a-cloze`, `m2a-english`. User models live in `<resources>/models/*.yaml|*.yml`; a user model with the same `name:` as a builtin overrides it.
- Service functions accept `anki_url: str | None = None`. If you add another entry point, thread it through — do **not** call `AnkiApi()` with no args inside a service.

## Dev workflow

- Install: `uv sync`.
- Fast tests: `uv run pytest tests/ --ignore=tests/test_integration.py` (mocked, ~0.3s).
- Integration tests: `uv run pytest tests/test_integration.py` — require a running Anki with AnkiConnect at `localhost:8765`; cards persist in `M2A::IntegrationTest::*` decks.
- Lint: `ruff` (line length 80, see `pyproject.toml`).
- Pre-commit hooks: `.pre-commit-config.yaml`.

## Versioning & release

- Single source of truth is `pyproject.toml`'s `version =` line. `markdown_to_anki/__init__.py` re-exports it as `__version__` via `importlib.metadata`. Don't hardcode a version anywhere else — `tests/test_version.py` guards against drift.
- `m2a --version` / `m2a -V` / `m2a version` all print the same value.
- To cut a release:
  ```
  scripts/release.sh 0.1.6
  git push origin main v0.1.6
  ```
  The script validates the version, refuses a dirty tree, updates `pyproject.toml` + `uv.lock`, commits, and creates an annotated tag `v<ver>`. It does **not** push — review the commit/tag, then push manually. `.github/workflows/release.yml` runs on `v*` push and handles build + PyPI publish + GitHub Release.

## Easy traps

- Media filenames are flattened to `basename` when uploaded *and* when rewritten in HTML — both sides must keep agreeing.
- The `.anki` sidecar's keys are 1-indexed **card positions in the file**, not Anki IDs. Reordering cards in a file breaks the mapping; deleting a card leaves a stale entry.
- The user-models cache is keyed on the resources dir — call `set_resources_dir(...)` then reset `_user_models_cache` / `_user_models_cache_dir` in tests, or use the autouse `reset_resources` fixture.
- `config.py` reads env at import time. Tests that need to override `TIME_RANGE` etc. must patch the module attribute, not just set the env var.
