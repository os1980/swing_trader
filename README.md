# swing_trader

An AI-driven swing-trading research pipeline. Three CrewAI crews run in sequence against a
watchlist and emit one JSON document of per-symbol signals, each scored with Van Tharp
expectancy and sized so that 1R equals a fixed fraction of account equity.

Everything runs locally. The LLM is Ollama (`llama3:8b`), embeddings are `nomic-embed-text`,
and there is no cloud-LLM path.

## Quick start

```bash
cp .env.example .env          # then fill in the API keys
ollama serve                  # the flow fails without it
make setup                    # uv sync --group dev
make test                     # offline checks, a few seconds
make run                      # the real thing: python -m src.main
```

`make` on its own lists every target.

Persistence is optional. Set `ALGO_TRADING_DATABASE_URL` and run `make migrate` once to
create the tables. Without it the flow writes JSON reports only.

## How it works

```
SwingSentryFlow  (src/main.py)
  MacroCrew      once per trade date      -> macro context
  AnalysisCrew   once per watchlist symbol -> a data dossier per symbol
  StrategyCrew   once over all dossiers    -> PortfolioResponse JSON
```

Each crew is a thin Python wrapper around two YAML files in `src/crews/config/`, one for
agents and one for tasks. Prompt changes belong in the YAML.

| Path | What lives there |
| --- | --- |
| `src/main.py` | The flow, the watchlist, and per-crew memory isolation |
| `src/crews/` | Crew wrappers plus the agent and task YAML |
| `src/tools/trading_tools.py` | The six tools the agents may call |
| `src/helpers/trade_signals.py` | The output schema |
| `src/helpers/db.py` | Optional Postgres persistence |
| `db/migrations/` | SQL for the persistence tables |
| `tests/` | Offline tests |

## Two rules that are easy to break

**No lookahead.** Every tool and prompt is bounded by `end_date`, which defaults to the day
before the trade date. A new data source that ignores this makes backtest results meaningless.

**Memory isolation.** Each crew, and each symbol within the analysis crew, gets its own
ChromaDB directory. Sharing one store makes the model invent cross-symbol references.

`CLAUDE.md` holds the full set of conventions and is the file to read before changing
anything. `AGENTS.md` points at it. Automated review instructions for those same rules live
in `.gitar/review/`, with automations in `.gitar/rules/`.

## Developing

```bash
make lint            # ruff
make test            # pytest
make check           # both, same as CI
uv run pre-commit install   # format and secret-scan on commit
```

The tests are static checks on the crew YAML plus unit tests on the schema and the database
helpers. They never call an LLM, a database, or the network, so they stay fast enough to run
on every edit.

Some tests are marked `xfail`. Each one documents a known defect found in code review, with
the reason in the marker. When a fix lands, its test turns green and the marker comes off.

The formatter has not been run across the whole repo. Pre-commit formats the files in each
commit, which is how the codebase converges without one giant diff.
