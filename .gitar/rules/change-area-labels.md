---
title: "Label PRs by change area"
description: "Tag the surface a PR touches so reviewers know what kind of review it needs"
type: automation
when: "A PR is opened or updated"
actions: "Apply the labels below based on the files changed, and remove ones that no longer apply"
---

# Change area labels

The three surfaces in this repository need different kinds of review, so label them:

| Label | Applies when the PR touches |
| --- | --- |
| `prompts` | any file under `src/crews/config/`, or a crew wrapper in `src/crews/` |
| `trading-logic` | `src/helpers/trade_signals.py`, or expectancy or position sizing rules in the strategy prompt |
| `persistence` | `src/helpers/db.py` or anything under `db/` |
| `tooling` | `Makefile`, `pyproject.toml`, `.github/workflows/`, `.pre-commit-config.yaml`, `tests/` |
| `docs` | `README.md`, `CLAUDE.md`, `AGENTS.md`, or `.gitar/` only |

A PR labelled `prompts` or `trading-logic` changes model behaviour that no test fully
covers. For those, also post a short comment reminding the author to run the flow against a
watchlist of at least two symbols before merging, since several past defects only appear
from the second symbol onward.
