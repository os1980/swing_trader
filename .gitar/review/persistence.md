# Persistence

`src/helpers/db.py` writes runs, per-symbol analyses, and validated signals to Postgres,
in the `trading_strategy` schema. Tables come from `db/migrations/001_swing_sentry_tables.sql`.
Persistence is optional: with `ALGO_TRADING_DATABASE_URL` unset the flow writes JSON only.

## The contract to keep in sync

`PortfolioResponse` in `src/helpers/trade_signals.py`, the `swing_sentry_signals` columns,
and the row tuple built in `finish_run` are one contract. A change to any one of them
without the other two is a defect. The same goes for the signal vocabulary and its CHECK
constraint.

## What to check

- Migrations stay idempotent and re-runnable, with `IF NOT EXISTS` and an explicit transaction.
- SQL is parameterized. No f-strings or concatenation into a statement.
- The run row is written before the crews start, so a bad connection string fails before
  minutes of LLM time are spent, and failures mark the run `FAILED` rather than leaving it
  `RUNNING`.
- The `end_date < trade_date` CHECK stays. It is the no-lookahead rule expressed in the schema.
- Model output is validated against the watchlist before being written. Symbols off the
  watchlist, duplicates, and unknown signal values are skipped, not stored.
- The run's own `trade_date` wins over any date echoed by the model.
- Other schemas in this database (`market_history`, `trading`, `backtesting`, `app_logs`)
  belong to other systems. Flag any write to them.
- New tables follow the local conventions: `db_creation_date` and `db_modify_date` audit
  columns, and upper-case trimmed symbols.
