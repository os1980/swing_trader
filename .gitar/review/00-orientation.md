# What this repository is

An AI swing-trading research pipeline. Three CrewAI crews run in sequence over a watchlist
and produce one `PortfolioResponse` JSON document of per-symbol signals. The LLM is always
local Ollama (`llama3:8b`). There is no cloud-LLM path.

`CLAUDE.md` in the repository root holds the full conventions and is read automatically.
The files in this directory say what to look for in a diff, not what the project is.

## Where the bodies are buried

Most of the behaviour lives in prompts, not in Python. The four YAML files under
`src/crews/config/` are the main edit surface, and a bad prompt fails silently: the model
invents a number instead of erroring. Review prompt diffs as carefully as code.

Two failure modes matter more than style here.

**Silent fabrication.** A prompt that asks for a value no tool returns does not fail. The
model fills the gap with an invented number, which then flows into entry prices, stop
losses, and position sizes.

**Silent lookahead.** A data fetch that is not bounded by `end_date` contaminates a
backtest with future information. Nothing downstream can detect it, and the results look
fine.

## Review priorities, in order

1. Lookahead and data-boundary correctness.
2. Fabricated or unsourced numbers reaching a trade decision.
3. Position sizing and expectancy arithmetic.
4. The strategy output contract holding across the prompt, the Pydantic schema, and the database.
5. Ordinary Python correctness and clarity.
