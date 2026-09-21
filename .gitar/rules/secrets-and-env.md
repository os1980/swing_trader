---
title: "Secrets stay in the environment"
description: "No credentials in the repository, and every new variable is documented"
type: check
when: "A PR adds or changes credentials, environment variable reads, .env.example, or .mcp.json"
actions: "Request changes when a credential is committed or a new variable is undocumented"
---

# Secrets and environment variables

All credentials come from the environment. `.env` is gitignored. `.env.example` is the
tracked template and carries variable names with empty or placeholder values only.

Fail this check when a PR:

- Adds a literal API key, token, password, or a database URL containing credentials, in any
  file, including tests, fixtures, docs, and notebooks.
- Inlines a credential into `.mcp.json` instead of referencing `${VAR}`.
- Reads a new environment variable in `src/` without adding it to `.env.example` and to the
  required-environment list in `CLAUDE.md`.
- Commits a real `.env`, a database dump, or a credential file.

Name the file and line, and say which of the two fixes applies: move it to the environment,
or document the variable.
