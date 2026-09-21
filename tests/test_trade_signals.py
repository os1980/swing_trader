"""The StrategyCrew output contract. If this changes, the signals table changes too."""
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from src.helpers.trade_signals import PortfolioResponse, get_float_env

VALID_TRADE = {
    "symbol": "AAPL",
    "trade_date": "2025-01-07",
    "signal": "BUY",
    "market_type": "Bull Quiet",
    "trade_setup": {
        "entry_price": 100.0,
        "stop_loss": 95.0,
        "profit_target": 115.0,
        "r_multiple_target": 3.0,
    },
    "expectancy_scorecard": {
        "win_probability": 0.45,
        "r_ratio": 3.0,
        "expectancy_value": 0.8,
    },
    "position_sizing": {"shares": 20, "risk_per_trade": 0.01, "total_account_value": 10000.0},
    "rationale": {"bull_case": "Breakout holds", "bear_case": "Macro turns"},
}


def test_portfolio_response_round_trip():
    portfolio = PortfolioResponse.model_validate_json(
        json.dumps({"trades": [VALID_TRADE], "total_portfolio_risk_percent": 1.0})
    )
    trade = portfolio.trades[0]
    assert trade.symbol == "AAPL"
    assert trade.position_sizing.shares == 20
    assert portfolio.total_portfolio_risk_percent == 1.0


def test_hold_trade_may_omit_prices():
    hold = {**VALID_TRADE, "signal": "HOLD"}
    hold["trade_setup"] = dict.fromkeys(VALID_TRADE["trade_setup"])
    trade = PortfolioResponse.model_validate({"trades": [hold]}).trades[0]
    assert trade.trade_setup.entry_price is None


def test_empty_portfolio_is_valid():
    """Standing aside is a legitimate answer and must not crash the run."""
    portfolio = PortfolioResponse.model_validate({"trades": []})
    assert portfolio.trades == []
    assert portfolio.total_portfolio_risk_percent == 0.0


def test_missing_expectancy_is_rejected():
    broken = {k: v for k, v in VALID_TRADE.items() if k != "expectancy_scorecard"}
    with pytest.raises(ValidationError):
        PortfolioResponse.model_validate({"trades": [broken]})


def test_position_sizing_defaults_come_from_env(monkeypatch):
    monkeypatch.setenv("RISK_PER_TRADE", "0.02")
    monkeypatch.setenv("EQUITY", "50000")
    trade = {**VALID_TRADE, "position_sizing": {"shares": 5}}
    sizing = PortfolioResponse.model_validate({"trades": [trade]}).trades[0].position_sizing
    assert sizing.risk_per_trade == 0.02
    assert sizing.total_account_value == 50000.0


def test_get_float_env_falls_back_on_junk(monkeypatch):
    monkeypatch.setenv("RISK_PER_TRADE", "one percent")
    assert get_float_env("RISK_PER_TRADE", 0.01) == 0.01
    monkeypatch.delenv("RISK_PER_TRADE")
    assert get_float_env("RISK_PER_TRADE", 0.01) == 0.01


@pytest.mark.xfail(
    reason="Known gap from code review: `signal` is a free string, so the schema accepts "
           "values the database CHECK constraint rejects.",
    strict=False,
)
def test_invalid_signal_is_rejected():
    with pytest.raises(ValidationError):
        PortfolioResponse.model_validate({"trades": [{**VALID_TRADE, "signal": "MAYBE"}]})
