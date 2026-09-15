"""Persist SwingSentryFlow runs to Postgres.

Tables live in the ``trading_strategy`` schema and are created by
``db/migrations/001_swing_sentry_tables.sql``.

Persistence is optional. When ``ALGO_TRADING_DATABASE_URL`` is unset, ``is_enabled()`` returns
False and the flow runs with JSON reports only. When it is set, a database that
cannot be reached fails the run up front, before any LLM time is spent.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from typing import Any

import psycopg
from pydantic import ValidationError

from .trade_signals import PortfolioResponse

VALID_SIGNALS = frozenset({"BUY", "HOLD", "SELL"})


def is_enabled() -> bool:
    return bool(os.getenv("ALGO_TRADING_DATABASE_URL"))


def new_run_id() -> str:
    """Same format as the run_id values in app_logs.trading_run_logs."""
    return uuid.uuid4().hex


def _connect() -> psycopg.Connection:
    # Used as a context manager: commits on success, rolls back on exception, then closes.
    return psycopg.connect(os.environ["ALGO_TRADING_DATABASE_URL"], connect_timeout=10)


def _normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def start_run(
    run_id: str,
    *,
    trade_date: str,
    start_date: str,
    end_date: str,
    watchlist: list[str],
    equity: float,
    risk_per_trade: float,
    llm_model: str,
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO trading_strategy.swing_sentry_runs
                (run_id, status, trade_date, start_date, end_date, watchlist,
                 equity, risk_per_trade, llm_model)
            VALUES (%s, 'RUNNING', %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                run_id, trade_date, start_date, end_date,
                [_normalize_symbol(s) for s in watchlist],
                equity, risk_per_trade, llm_model,
            ),
        )


def fail_run(run_id: str, error_message: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            UPDATE trading_strategy.swing_sentry_runs
               SET status = 'FAILED', error_message = %s,
                   run_end_time = now(), db_modify_date = now()
             WHERE run_id = %s
            """,
            (error_message, run_id),
        )


def parse_portfolio(strategy_result: Any) -> PortfolioResponse:
    """Validate the StrategyCrew output, accepting a CrewOutput, dict, or JSON string."""
    if isinstance(strategy_result, PortfolioResponse):
        return strategy_result
    pydantic_output = getattr(strategy_result, "pydantic", None)
    if isinstance(pydantic_output, PortfolioResponse):
        return pydantic_output
    json_dict = getattr(strategy_result, "json_dict", None)
    if json_dict:
        return PortfolioResponse.model_validate(json_dict)
    if isinstance(strategy_result, dict):
        return PortfolioResponse.model_validate(strategy_result)
    raw = getattr(strategy_result, "raw", strategy_result)
    return PortfolioResponse.model_validate_json(str(raw))


def raw_output(strategy_result: Any) -> str:
    raw = getattr(strategy_result, "raw", None)
    if raw:
        return raw
    if isinstance(strategy_result, dict):
        return json.dumps(strategy_result)
    return str(strategy_result)


@dataclass
class FinishSummary:
    status: str
    signals_written: int = 0
    skipped: list[str] = field(default_factory=list)
    # Symbols whose LLM-echoed trade_date differed from the run's; stored with the run's date.
    date_mismatches: list[str] = field(default_factory=list)
    error_message: str | None = None


def finish_run(
    run_id: str,
    *,
    trade_date: str,
    watchlist: list[str],
    macro_context: str,
    analyses: dict[str, str],
    strategy_result: Any,
) -> FinishSummary:
    """Write analyses and signals, then close the run, all in one transaction.

    The raw StrategyCrew output and every symbol analysis are always saved.
    Signals are written only for output that validates against PortfolioResponse.
    A trade is skipped when its symbol is not on the watchlist, repeats an earlier
    trade, or has a signal other than BUY/HOLD/SELL. Output that fails validation
    closes the run as FAILED with the validation error.
    """
    allowed = {_normalize_symbol(s) for s in watchlist}
    summary = FinishSummary(status="FINISHED")

    try:
        portfolio: PortfolioResponse | None = parse_portfolio(strategy_result)
    except (ValidationError, ValueError) as exc:
        portfolio = None
        summary.status = "FAILED"
        summary.error_message = f"StrategyCrew output did not validate as PortfolioResponse: {exc}"

    signal_rows = []
    if portfolio is not None:
        seen: set[str] = set()
        for rank, trade in enumerate(portfolio.trades, start=1):
            symbol = _normalize_symbol(trade.symbol)
            signal = trade.signal.strip().upper()
            if symbol not in allowed:
                summary.skipped.append(f"{symbol}: not on watchlist")
                continue
            if symbol in seen:
                summary.skipped.append(f"{symbol}: duplicate trade")
                continue
            if signal not in VALID_SIGNALS:
                summary.skipped.append(f"{symbol}: invalid signal {trade.signal!r}")
                continue
            seen.add(symbol)
            if trade.trade_date != trade_date:
                # The run's trade_date is authoritative; the LLM-echoed date is not trusted.
                summary.date_mismatches.append(f"{symbol}: {trade.trade_date!r}")
            setup, score, sizing = trade.trade_setup, trade.expectancy_scorecard, trade.position_sizing
            signal_rows.append((
                run_id, symbol, trade_date, rank, signal, trade.market_type,
                setup.entry_price, setup.stop_loss, setup.profit_target, setup.r_multiple_target,
                score.win_probability, score.r_ratio, score.expectancy_value,
                sizing.shares, sizing.risk_per_trade, sizing.total_account_value,
                trade.rationale.get("bull_case"), trade.rationale.get("bear_case"),
            ))

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO trading_strategy.swing_sentry_symbol_analyses
                    (run_id, symbol, analysis_report)
                VALUES (%s, %s, %s)
                """,
                [(run_id, _normalize_symbol(s), report) for s, report in analyses.items()],
            )
            if signal_rows:
                cur.executemany(
                    """
                    INSERT INTO trading_strategy.swing_sentry_signals
                        (run_id, symbol, trade_date, expectancy_rank, signal, market_type,
                         entry_price, stop_loss, profit_target, r_multiple_target,
                         win_probability, r_ratio, expectancy_value,
                         shares, risk_per_trade, total_account_value,
                         bull_case, bear_case)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    signal_rows,
                )
            cur.execute(
                """
                UPDATE trading_strategy.swing_sentry_runs
                   SET status = %s,
                       macro_context = %s,
                       strategy_raw_output = %s,
                       total_portfolio_risk_percent = %s,
                       error_message = %s,
                       run_end_time = now(),
                       db_modify_date = now()
                 WHERE run_id = %s
                """,
                (
                    summary.status, macro_context, raw_output(strategy_result),
                    portfolio.total_portfolio_risk_percent if portfolio else None,
                    summary.error_message, run_id,
                ),
            )

    summary.signals_written = len(signal_rows)
    return summary
