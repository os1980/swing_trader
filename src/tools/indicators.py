"""Indicator math with no network and no CrewAI, so it can be tested anywhere."""
from __future__ import annotations

import math

from stockstats import wrap as stockstats_wrap

# Bars each indicator needs before its value means what its name says. Below this,
# stockstats still returns a number (a 61-bar mean labelled close_200_sma, for example),
# so the tool reports None instead of a mislabelled value.
_MIN_BARS = {
    "rsi_14": 15,
    "macd": 35,
    "boll_upper": 20,
    "boll_lower": 20,
    "sma_50": 50,
    "sma_200": 200,
    "atr_14": 15,
}
_STOCKSTATS_COLUMN = {
    "rsi_14": "rsi_14",
    "macd": "macd",
    "boll_upper": "boll_ub",
    "boll_lower": "boll_lb",
    "sma_50": "close_50_sma",
    "sma_200": "close_200_sma",
    "atr_14": "atr_14",
}


def _flatten_columns(df):
    """yf.download returns (field, ticker) column pairs. stockstats silently mis-computes
    ATR on that shape (3.98 instead of 4.24 for AAPL on 2025-01-06), so flatten first."""
    if getattr(df.columns, "nlevels", 1) > 1:
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    return df


def compute_indicators(prices) -> dict:
    """Last-bar indicator values from an OHLC frame. Pure function, no network."""
    prices = _flatten_columns(prices)
    stock_df = stockstats_wrap(prices.copy())
    bars = len(prices)
    result = {"as_of": prices.index[-1].strftime("%Y-%m-%d"), "bars": bars}
    for name, column in _STOCKSTATS_COLUMN.items():
        if bars < _MIN_BARS[name]:
            result[name] = None
            continue
        value = float(stock_df[column].iloc[-1])
        result[name] = None if math.isnan(value) else round(value, 4)
    return result
