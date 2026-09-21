---
title: "No lookahead in new data access"
description: "Every data fetch must be bounded by end_date"
type: check
when: "A PR adds or modifies a data fetch, a tool in src/tools/, or any date handling in src/ or src/crews/config/"
actions: "Request changes when a data path is not bounded by end_date, quoting the line"
---

# Lookahead guard

Backtest integrity depends on every data path stopping at `end_date`, which defaults to the
day before the trade date. A violation produces no error and no failing test. It just makes
the results meaningless.

Fail this check when a PR:

- Adds a tool, API call, or data source with no `end_date` parameter, or one that accepts it
  and never applies it.
- Calls an existing tool without passing `end_date`, or passes `trade_date` or a current
  date in its place.
- Removes an `end_date` reference from a prompt in `src/crews/config/`.
- Widens a date window, or makes a date bound depend on a value the model supplies.
- Shares a memory or cache store across trade dates for a crew that has `memory=True`, which
  lets a later run's output surface as context for an earlier date.

Quote the specific line and name the date that should bound it.
