# No lookahead

Every tool call and every prompt is bounded by `end_date`, which defaults to the day before
the trade date. This is the load-bearing invariant of the whole project: without it, backtest
results are meaningless and no test will tell you.

Flag any diff that:

- Adds a data source, tool, or API call that does not take and enforce an `end_date` cutoff.
- Calls an existing tool without passing `end_date`. `get_finnhub_news` declares it as a
  required argument and applies no cutoff of its own, so an omitted value becomes whatever
  the model guesses.
- Uses `trade_date` or today's date where `end_date` belongs.
- Removes an `end_date` mention from a prompt in `src/crews/config/`. The strategy prompts
  have already lost theirs once.
- Filters by date after fetching rather than bounding the request, when the API supports a
  bound.

## Known trap: yfinance end is exclusive

`ticker.history(start=..., end=...)` excludes the `end` date. A report that labels a close
price "as of `{end_date}`" is therefore claiming a date the tool never returned a bar for.
Label a close with the last date the tool actually returned.

## Memory is a lookahead channel

`src/main.py` rewrites `CREWAI_STORAGE_DIR` between crew invocations so each crew, and each
symbol within the analysis crew, gets its own ChromaDB directory. Flag anything that
consolidates these stores. Also flag a crew whose memory store is shared across trade dates
while `memory=True`: a later run's output can be retrieved as context for an earlier date,
which is lookahead through the back door.
