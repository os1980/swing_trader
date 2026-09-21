"""Indicator math in src/tools/indicators.py. Synthetic prices, no network."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from src.tools.indicators import compute_indicators


def _prices(bars: int, seed: int = 7) -> pd.DataFrame:
    """A deterministic random walk with realistic high/low spread."""
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1.5, bars))
    spread = np.abs(rng.normal(1.0, 0.4, bars))
    index = pd.bdate_range("2024-01-02", periods=bars, name="Date")
    return pd.DataFrame(
        {
            "Close": close,
            "High": close + spread,
            "Low": close - spread,
            "Open": close + rng.normal(0, 0.5, bars),
            "Volume": rng.integers(1_000_000, 5_000_000, bars),
        },
        index=index,
    )


def _as_yfinance_download(df: pd.DataFrame, symbol: str = "AAPL") -> pd.DataFrame:
    """yf.download returns (field, ticker) column pairs even for one symbol."""
    out = df.copy()
    out.columns = pd.MultiIndex.from_product([out.columns, [symbol]], names=["Price", "Ticker"])
    return out


def _wilder_atr(df: pd.DataFrame, period: int = 14) -> float:
    high, low, close = df["High"], df["Low"], df["Close"]
    true_range = pd.concat(
        [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1
    ).max(axis=1)
    return float(true_range.ewm(alpha=1 / period, adjust=False).mean().iloc[-1])


def test_yfinance_column_shape_gives_the_same_answer_as_flat_columns():
    """Regression: stockstats mis-computed ATR on the (field, ticker) shape."""
    flat = _prices(260)
    assert compute_indicators(_as_yfinance_download(flat)) == compute_indicators(flat)


def test_atr_matches_wilder_smoothing():
    flat = _prices(260)
    result = compute_indicators(_as_yfinance_download(flat))
    assert result["atr_14"] == pytest.approx(_wilder_atr(flat), abs=1e-3)


def test_sma_200_is_null_without_200_bars():
    """Regression: on ~61 bars stockstats returned the 61-bar mean as close_200_sma."""
    result = compute_indicators(_prices(61))
    assert result["bars"] == 61
    assert result["sma_200"] is None
    assert result["sma_50"] is not None


def test_sma_200_is_the_trailing_200_bar_mean_when_history_allows():
    flat = _prices(260)
    result = compute_indicators(flat)
    assert result["sma_200"] == pytest.approx(flat["Close"].iloc[-200:].mean(), abs=1e-3)


def test_reports_the_date_of_the_last_bar_used():
    flat = _prices(260)
    result = compute_indicators(flat)
    assert result["as_of"] == flat.index[-1].strftime("%Y-%m-%d")


def test_output_is_plain_json():
    """The agent receives this as tool output; numpy scalars or NaN would leak through."""
    result = compute_indicators(_prices(30))
    decoded = json.loads(json.dumps(result, allow_nan=False))
    assert decoded == result
    assert all(v is None or isinstance(v, (int, float, str)) for v in result.values())
