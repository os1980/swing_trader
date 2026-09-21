Changes to the crew prompts under `src/crews/config/` are at least medium risk, and high
risk when they touch the strategy task's JSON template, the position sizing rule, or any
`end_date` bound. These prompts decide entry prices, stop losses, and share counts, and a
regression in them produces confident, well-formed, wrong output rather than an error.

Changes to position sizing, expectancy arithmetic, or the `PortfolioResponse` schema are
high risk.

Database migrations under `db/` are high risk.

Changes to data-fetching tools in `src/tools/` are high risk when they affect which dates
are fetched, because lookahead silently invalidates every backtest result.

Changes limited to `tests/`, `.github/`, `Makefile`, documentation, or `.gitar/` are low risk.
