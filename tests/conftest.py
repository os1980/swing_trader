"""Shared fixtures. Tests here must stay offline: no Ollama, no database, no API calls."""
from __future__ import annotations

import pathlib

import pytest
import yaml

CONFIG_DIR = pathlib.Path(__file__).resolve().parents[1] / "src" / "crews" / "config"

# What src/main.py actually passes to each crew's kickoff(inputs=...).
# A placeholder in the YAML that is missing here blows up at run time, after
# minutes of LLM work, so it is checked statically instead.
CREW_INPUTS: dict[str, set[str]] = {
    "macro": {"trade_date", "start_date", "end_date"},
    "analysis": {
        "symbol", "trade_date", "start_date", "end_date",
        "macro_context", "equity", "risk",
    },
    "strategy": {
        "trade_date", "start_date", "end_date",
        "macro_report", "all_symbol_reports", "equity", "risk",
    },
}


def load_config(name: str) -> dict:
    return yaml.safe_load((CONFIG_DIR / name).read_text())


@pytest.fixture(scope="session")
def configs() -> dict[str, dict]:
    return {p.stem: load_config(p.name) for p in sorted(CONFIG_DIR.glob("*.yaml"))}
