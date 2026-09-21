---
title: "Strategy output contract stays in sync"
description: "The Pydantic schema, the signals table, and the strategy prompt are one contract"
type: check
when: "A PR modifies src/helpers/trade_signals.py, db/migrations/*.sql, or src/crews/config/strategy_tasks.yaml"
actions: "Comment naming the parts of the contract the PR did not update, and request changes if any are missing"
---

# Strategy output contract

`PortfolioResponse` and `TradeSignal` in `src/helpers/trade_signals.py`, the
`swing_sentry_signals` columns in `db/migrations/001_swing_sentry_tables.sql`, the row tuple
built by `finish_run` in `src/helpers/db.py`, and the JSON template in
`src/crews/config/strategy_tasks.yaml` all describe the same object.

When a PR changes one of them, check the others:

- A new or renamed field on `TradeSignal` needs a column, a place in the `finish_run` insert,
  and a slot in the prompt's JSON template.
- A change to the allowed `signal` values needs the prompt, the schema docstring, and the
  `swing_sentry_signals_signal_check` CHECK constraint to agree.
- A removed field needs a migration, not just a schema edit.

Say which specific file is missing the matching change. If all parts move together, say so
and pass.
