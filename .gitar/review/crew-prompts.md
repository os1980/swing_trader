# Crew prompts and CrewAI specifics

Prompt changes land in `src/crews/config/<crew>_agents.yaml` and `<crew>_tasks.yaml`. The
Python wrappers in `src/crews/` are thin. Pinned versions: `crewai==1.8.1`,
`crewai-tools==1.8.1`.

## Interpolation uses str.replace, not str.format

CrewAI 1.8.1 substitutes `{var}` tokens by literal replacement. It does **not** call
`str.format`, so `{{` and `}}` are not unescaped and reach the model as doubled braces.
Flag any doubled brace in a task or agent YAML. A JSON template written with `{{ }}` teaches
the model to emit `{{"trades": ...}}`, which fails `PortfolioResponse` validation and kills
the run.

## Every placeholder must be supplied at kickoff

`src/main.py` passes a fixed set of inputs to each crew:

| Crew | Inputs |
| --- | --- |
| macro | `trade_date`, `start_date`, `end_date` |
| analysis | `symbol`, `trade_date`, `start_date`, `end_date`, `macro_context`, `equity`, `risk` |
| strategy | `trade_date`, `start_date`, `end_date`, `macro_report`, `all_symbol_reports`, `equity`, `risk` |

A placeholder outside that set breaks at run time, minutes into an LLM run.
`tests/test_crew_configs.py` checks this statically, so a diff that adds a placeholder
should keep those tests passing.

## Do not ask for values the tools cannot return

The agents have six tools, in `src/tools/trading_tools.py`. `get_yfinance_data` returns only
close prices, highs, lows, and dates. `get_technical_indicators` is meant to return RSI,
MACD, Bollinger bands, ATR, and two moving averages, but every value is built with
`float(series.tolist())`, which raises `TypeError` on a list, so the tool always returns
`{"status": "no_data"}`. Until that is fixed, no prompt can rely on an indicator value. The
Tavily and Finnhub tools return prose with no numeric score.

Flag a report template that demands a value none of these produce, for example a moving
average the indicator tool does not compute, a MACD signal line, a support or resistance
level, or a numeric sentiment score. Combined with an instruction to fill every field, that
guarantees invented numbers. The fix is to shrink the template or compute the value in the
tool, never to add another instruction telling the model not to guess.

## Tool usage limits are per object, not per run

The tools are module-level singletons with `max_usage_count=1`, and the count is never
reset. After the first watchlist symbol, every later symbol gets a usage-limit error.
Flag a change that keeps that pattern while adding symbols, and flag any instruction telling
the agent to write "Data not available" on tool failure, which converts a hard failure into
a plausible-looking empty report.

## Strategy output must be bare JSON

The strategy task must instruct the model to return raw `PortfolioResponse` JSON with no
prose and no markdown fences. Extra text crashes downstream parsing. Flag any diff that
deletes that instruction.

## Preserve the research framing

Agent roles and backstories are written as research, for example "Quantitative Macro
Researcher" and "Computational Research", never "advisor" or "recommendation". This is
deliberate wording to avoid implying regulated investment advice. Flag language that drifts
toward advice.

## Context window

`src/helpers/utils.py` sets no `num_ctx`, and neither CrewAI nor litellm forwards one to
Ollama, so the default applies. The strategy prompt already inlines every symbol dossier
plus the macro report. Flag changes that materially grow that prompt without setting an
explicit context size: Ollama truncates silently rather than erroring.
