# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`swing_trader` is an AI-driven swing-trading analysis pipeline built on **CrewAI 1.8** with a **local Ollama** LLM (`llama3:8b`) and `nomic-embed-text` embeddings. It produces structured `PortfolioResponse` JSON containing per-symbol BUY/HOLD/SELL signals with Van Tharp expectancy scoring and position sizing.

When working on this project, apply swing trading best practices and methodologies — proper entry/exit timing, multi-timeframe analysis, risk/reward evaluation, trend confirmation, and volume analysis. Combine this domain expertise with strong Python engineering, CrewAI framework patterns, and API integration skills to deliver production-quality, well-structured code.

There is no cloud-LLM path — `helpers/utils.py` hardcodes `llm_provider="ollama"` and `ollama_base_url="http://localhost:11434"`. Ollama must be running locally before any crew is invoked.

## Run

```bash
uv sync                                  # installs from uv.lock
python -m src.main                       # runs SwingSentryFlow against the hardcoded watchlist in main.py
```

**Use `uv sync`, not `pip install -r requirements.txt`.** CrewAI is pinned to 1.8.1 in `pyproject.toml`. `crewai-tools` 1.8.1 declares `lancedb<0.6`, but PyPI deleted every lancedb release below 0.14, so pip cannot install it. `pyproject.toml` works around this with a `[tool.uv] override-dependencies` entry for `lancedb>=0.14`. Don't loosen the CrewAI pin: an unpinned lock refresh silently jumps to the latest CrewAI.

`pyproject.toml` registers only `ai_trading_crew` and `run_crew`, both pointing at `src.main:run`. The old `train`, `replay`, and `test` entry points were removed because they pointed at functions that do not exist. Don't re-add them without the code.

## Development workflow

Every routine action has a Makefile target; `make` alone lists them.

```bash
make setup     # uv sync --group dev
make test      # pytest, offline, a few seconds
make lint      # ruff check
make check     # lint + test, the same thing CI runs
make migrate   # apply db/migrations against $ALGO_TRADING_DATABASE_URL
```

**Tests are offline by design.** `tests/` never calls an LLM, a database, or the network. It holds static checks on the crew YAML (required keys, `{placeholder}` names matching what `src/main.py` passes to each kickoff, the no-lookahead bound) plus unit tests on `trade_signals.py` and the pure helpers in `db.py`. Anything needing a live service belongs behind the `integration` marker. Run tests after editing prompts: a `{typo}` in YAML otherwise surfaces only after minutes of LLM time.

**`xfail` markers document known defects.** Several tests are marked `xfail` with a reason tied to a code-review finding, for example the `{{` braces in `strategy_tasks.yaml` that CrewAI 1.8.1 does not unescape, and the deleted JSON-only rule. They are not flaky tests. Fix the defect, watch the test pass, then remove the marker.

**Lint is green; keep it that way.** `ruff check` passes on the whole repo. `src/main.py` is exempt from `E402` and import sorting because its import order is load-bearing: it sets environment variables and patches CrewAI tracing before importing crewai. The formatter has *not* been run repo-wide; pre-commit formats only the files in each commit, so the codebase converges without one giant diff. Install it with `uv run pre-commit install`.

CI (`.github/workflows/ci.yml`) installs a minimal dependency set rather than running `uv sync`, because `ta-lib` and `pygraphviz` need system libraries the tests don't touch. If a test starts importing something new, add it to that list.

## Required environment

The flow will fail or prompt interactively without these:

- `MEMORY_DB_BASE_DIR` — root for CrewAI's per-crew ChromaDB stores (see "Memory isolation" below)
- `FINAL_REPORT_BASE_DIR` — where the StrategyCrew writes its final JSON
- `FINNHUB_API_KEY`, `TAVILY_API_KEY` — used by tools in `src/tools/trading_tools.py`
- `OPENAI_API_KEY` — CrewAI requests it on import even though the runtime LLM is Ollama; supply any non-empty value
- `EQUITY`, `RISK_PER_TRADE` — drive position sizing in StrategyCrew prompts. `RISK_PER_TRADE` is a fraction (0.01 = 1%), and `main.py` multiplies it by 100 before interpolating it into prompts

`.env.example` is the tracked template listing every variable the flow reads; `.env` itself is gitignored.
- `ALGO_TRADING_DATABASE_URL` — optional Postgres connection string. When set, each run is persisted (see "Persistence" below) and an unreachable database fails the run before any LLM call. When unset, the flow writes JSON reports only.

## Architecture

The pipeline is a three-stage CrewAI Flow defined in [src/main.py](src/main.py):

```
SwingSentryFlow
  @start            get_global_macro()         → MacroCrew     (once per trade_date)
  @listen(...)      analyze_all_symbols()      → AnalysisCrew  (loop over watchlist, per-symbol)
  @listen(...)      finalize_plan()            → StrategyCrew  (once, synthesizes everything)
```

State is a single Pydantic `TradingState` object (`symbol`, `trade_date`, `start_date`, `end_date`, `macro_context`, `ticker_analysis_results: dict`, `equity`, `risk`, `watchlist`).

Each crew lives in [src/crews/](src/crews/) with agent + task definitions split into YAML under [src/crews/config/](src/crews/config/) (`<crew>_agents.yaml` + `<crew>_tasks.yaml`). When editing crew behavior, the YAML files are usually the right place — the `.py` wrappers are thin.

Crews share a common toolkit in [src/tools/trading_tools.py](src/tools/trading_tools.py) — six `@tool`-decorated functions:
`get_yfinance_data`, `get_technical_indicators` (RSI/MACD/Bollinger/ATR/SMA via `ta-lib` + `stockstats`), `get_finnhub_news`, `get_social_media_sentiment` (Tavily), `get_fundamental_analysis` (Tavily), `get_macroeconomic_news` (Tavily).

Output schemas live in [src/helpers/trade_signals.py](src/helpers/trade_signals.py): `TradeSignal` (per symbol) and `PortfolioResponse` (the StrategyCrew's required output).

### Persistence

[src/helpers/db.py](src/helpers/db.py) writes each run to the shared Postgres/TimescaleDB instance, in the `trading_strategy` schema. The tables come from [db/migrations/001_swing_sentry_tables.sql](db/migrations/001_swing_sentry_tables.sql):

- `swing_sentry_runs` — one row per flow execution, with status `RUNNING` / `FINISHED` / `FAILED`, the macro context, and the raw StrategyCrew output. A check constraint enforces `end_date < trade_date`.
- `swing_sentry_symbol_analyses` — the AnalysisCrew report for each watchlist symbol.
- `swing_sentry_signals` — one row per validated `TradeSignal`. Trades for symbols outside the watchlist, duplicate symbols, and signals other than BUY/HOLD/SELL are skipped. The raw output keeps them.

The same database holds other systems' schemas (`market_history`, `trading`, `backtesting`, `app_logs`). Treat those as read-only from this project. The existing tables follow `db_creation_date` / `db_modify_date` audit columns and upper-case trimmed symbols; keep new tables consistent. If `PortfolioResponse` changes, update the signals table and `finish_run` together.

## Conventions to preserve

**Memory isolation by crew and symbol.** [src/main.py](src/main.py) mutates `os.environ["CREWAI_STORAGE_DIR"]` between crew invocations so each crew (and each symbol within AnalysisCrew) gets its own ChromaDB directory. Don't refactor this into a single shared store — cross-symbol memory bleed produces hallucinated cross-references. Pattern:
```
$MEMORY_DB_BASE_DIR/global_macro/                    # MacroCrew
$MEMORY_DB_BASE_DIR/analyze/tickers/<SYMBOL>/        # AnalysisCrew, per symbol
```

**No lookahead.** Tools and prompts are explicitly bounded by `end_date` (defaults to `trade_date - 1`). The TODOs in `main.py` about "make sure no future look" are load-bearing — any new tool or data source must enforce the same cutoff or the backtest results become meaningless.

**Strict JSON from StrategyCrew.** The strategy task is configured to emit raw `PortfolioResponse` JSON only — no prose, no markdown fences. The YAML config and agent backstory both warn that any extra text crashes downstream parsing. If you change the schema, update both [src/helpers/trade_signals.py](src/helpers/trade_signals.py) and [src/crews/config/strategy_tasks.yaml](src/crews/config/strategy_tasks.yaml) together.

**Tracing-prompt suppression.** `main.py` monkey-patches CrewAI's tracing module with a `no_prompt` stub that auto-answers "n" to interactive prompts. Don't remove this — it's what lets the flow run unattended.

**Research framing in agent backstories.** Agents are described as "Quantitative Macro Researcher" / "Computational Research" rather than "advisor" / "recommendation." This is deliberate language to avoid implying regulated investment advice; preserve it when editing YAML backstories.

**Van Tharp expectancy.** The strategy crew's logic is built around `E = (Pw × Reward) − (Pl × Risk)` with position sizing such that 1R equals exactly `RISK_PER_TRADE × EQUITY`. Don't introduce alternative sizing without coordinating with the strategy task definition.

## Skills

Use these skills when working on this project:

- `/engineering-skills:senior-backend` — Python backend work: API integrations, data pipelines, Pydantic models, async patterns
- `/engineering-skills:senior-data-scientist` — Statistical analysis, signal evaluation, expectancy modeling, indicator research
- `/engineering-skills:senior-data-engineer` — Data pipeline architecture, ETL flows, data quality and validation
- `/engineering-skills:senior-ml-engineer` — LLM integration, CrewAI agent tuning, embedding pipelines, model orchestration
- `/engineering-skills:senior-prompt-engineer` — CrewAI agent backstories and task prompts, output formatting, hallucination reduction
- `/engineering-skills:code-reviewer` — Code review for Python quality, API safety, and trading logic correctness
- `/engineering-skills:tdd-guide` — Extending the test suite in `tests/`
- `/engineering-skills:senior-security` — API key management, credential handling, .env safety
- `/engineering-skills:adversarial-reviewer` — Stress-testing trading logic, edge cases, and data boundary assumptions

## MCP Servers

Project-level MCP servers are configured in [.mcp.json](.mcp.json):

- **finnhub** — Direct Finnhub API access for real-time quotes, company fundamentals, and market news (requires `FINNHUB_API_KEY`)
- **yahoo-finance** — Yahoo Finance data for historical OHLCV, financials, and company profiles
- **tavily** — Web search for sentiment analysis, fundamental research, and macro news (requires `TAVILY_API_KEY`)
- **postgres** — Read-only (`--access-mode=restricted`) access to the Postgres database via `postgres-mcp`. It reads `ALGO_TRADING_DATABASE_URL` from the environment Claude Code was launched in, not from `.env`, so export it in your shell first.
- **filesystem** — Scoped file access to `./final_reports` and `./knowledge` directories
