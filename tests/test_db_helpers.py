"""Pure helpers in src/helpers/db.py. Nothing here opens a connection."""
from __future__ import annotations

import json

import pytest

from src.helpers import db
from src.helpers.trade_signals import PortfolioResponse

from .test_trade_signals import VALID_TRADE

PAYLOAD = {"trades": [VALID_TRADE], "total_portfolio_risk_percent": 1.0}


class FakeCrewOutput:
    """Stands in for crewai.CrewOutput, which carries raw text plus parsed forms."""

    def __init__(self, raw="", json_dict=None, pydantic=None):
        self.raw = raw
        self.json_dict = json_dict
        self.pydantic = pydantic


def test_is_enabled_follows_the_env_var(monkeypatch):
    monkeypatch.delenv("ALGO_TRADING_DATABASE_URL", raising=False)
    assert db.is_enabled() is False
    monkeypatch.setenv("ALGO_TRADING_DATABASE_URL", "postgresql://localhost/test")
    assert db.is_enabled() is True


def test_new_run_id_is_unique_hex():
    first, second = db.new_run_id(), db.new_run_id()
    assert first != second
    assert len(first) == 32 and int(first, 16) >= 0


@pytest.mark.parametrize(
    "result",
    [
        PAYLOAD,
        json.dumps(PAYLOAD),
        FakeCrewOutput(raw=json.dumps(PAYLOAD)),
        FakeCrewOutput(raw="ignored", json_dict=PAYLOAD),
        FakeCrewOutput(raw="ignored", pydantic=PortfolioResponse.model_validate(PAYLOAD)),
    ],
)
def test_parse_portfolio_accepts_every_shape_crewai_returns(result):
    portfolio = db.parse_portfolio(result)
    assert portfolio.trades[0].symbol == "AAPL"


def test_parse_portfolio_rejects_prose():
    with pytest.raises(ValueError):
        db.parse_portfolio("Here is your portfolio: no trades today.")


def test_raw_output_prefers_the_untouched_text():
    assert db.raw_output(FakeCrewOutput(raw="{'trades': []}")) == "{'trades': []}"
    assert json.loads(db.raw_output({"trades": []})) == {"trades": []}
    assert db.raw_output(None) == "None"


def test_normalize_symbol_matches_the_database_check():
    assert db._normalize_symbol("  aapl ") == "AAPL"


def test_valid_signals_match_the_schema_docstring():
    assert {"BUY", "HOLD", "SELL"} == db.VALID_SIGNALS
