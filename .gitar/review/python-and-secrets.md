# Python, tests, and secrets

## Secrets

All credentials come from the environment. `.env` is gitignored; `.env.example` is the
tracked template and carries names only, never values. Flag any literal API key, database
URL with a password, or connection string in code, YAML, docs, or a test fixture, and flag a
new secret that is read but not added to `.env.example`.

`.mcp.json` must keep referencing credentials as `${VAR}` rather than inlining them.

## Import order in src/main.py

`src/main.py` sets environment variables and patches CrewAI's tracing module before importing
crewai. That order is load-bearing: the tracing stub is what lets the flow run unattended,
and the storage directory must be set before the import. The file is exempt from import
sorting in the ruff config. Flag a diff that reorders those imports or removes the stub.

## Tests

`tests/` is offline by design: no LLM, no database, no network. A test that needs a live
service belongs behind the `integration` marker. Flag a new test that reaches out over the
network, and flag a change to `tests/` that weakens a check rather than fixing the code it
guards.

Several tests carry `xfail` markers, each tied to a known review finding. That is deliberate
bookkeeping, not flakiness. When a diff fixes the underlying defect, the marker should come
off in the same change. Flag a new `xfail` added to silence a failure the diff itself caused.

## General

- `ruff check` passes on the whole repo. Keep it that way; a new `noqa` should carry a
  reason.
- Prefer failing loudly over a fallback that returns an empty or default value. A tool that
  swallows an exception and returns `{"status": "no_data"}` produces a confident, empty
  report instead of an error.
- Bare `except Exception` that drops the error, or a fallback that hides a missing data
  source, is worth flagging here even though it is ordinary elsewhere.
