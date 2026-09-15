-- SwingSentryFlow persistence.
--   swing_sentry_runs              one row per flow execution
--   swing_sentry_symbol_analyses   one row per watchlist symbol (AnalysisCrew output)
--   swing_sentry_signals           one row per trade the StrategyCrew emits (PortfolioResponse.trades)
--
-- Follows the conventions of the existing schemas: db_creation_date/db_modify_date audit
-- columns, varchar run_id, upper-case trimmed symbols.
-- Idempotent: safe to re-run.
--
-- Apply with:
--   psql "$ALGO_TRADING_DATABASE_URL" -v ON_ERROR_STOP=1 -f db/migrations/001_swing_sentry_tables.sql

BEGIN;

CREATE TABLE IF NOT EXISTS trading_strategy.swing_sentry_runs (
    db_creation_date             timestamptz  NOT NULL DEFAULT now(),
    db_modify_date               timestamptz  NOT NULL DEFAULT now(),
    run_id                       varchar(100) PRIMARY KEY,
    status                       varchar(25)  NOT NULL,
    trade_date                   date         NOT NULL,
    start_date                   date         NOT NULL,
    end_date                     date         NOT NULL,
    watchlist                    text[]       NOT NULL,
    equity                       numeric      NOT NULL,
    risk_per_trade               numeric      NOT NULL,
    llm_model                    varchar(100),
    run_start_time               timestamptz  NOT NULL DEFAULT now(),
    run_end_time                 timestamptz,
    macro_context                text,
    strategy_raw_output          text,
    total_portfolio_risk_percent numeric,
    error_message                text,
    CONSTRAINT swing_sentry_runs_status_check
        CHECK (status IN ('RUNNING', 'FINISHED', 'FAILED')),
    -- No lookahead: the data window must close before the trade date.
    CONSTRAINT swing_sentry_runs_window_check
        CHECK (start_date <= end_date AND end_date < trade_date)
);

CREATE INDEX IF NOT EXISTS swing_sentry_runs_trade_date_idx
    ON trading_strategy.swing_sentry_runs (trade_date);

CREATE TABLE IF NOT EXISTS trading_strategy.swing_sentry_symbol_analyses (
    db_creation_date timestamptz  NOT NULL DEFAULT now(),
    db_modify_date   timestamptz  NOT NULL DEFAULT now(),
    run_id           varchar(100) NOT NULL
        REFERENCES trading_strategy.swing_sentry_runs (run_id) ON DELETE CASCADE,
    symbol           varchar(25)  NOT NULL,
    analysis_report  text         NOT NULL,
    PRIMARY KEY (run_id, symbol),
    CONSTRAINT swing_sentry_symbol_analyses_symbol_check
        CHECK (symbol = upper(trim(symbol)))
);

CREATE TABLE IF NOT EXISTS trading_strategy.swing_sentry_signals (
    db_creation_date    timestamptz  NOT NULL DEFAULT now(),
    db_modify_date      timestamptz  NOT NULL DEFAULT now(),
    run_id              varchar(100) NOT NULL
        REFERENCES trading_strategy.swing_sentry_runs (run_id) ON DELETE CASCADE,
    symbol              varchar(25)  NOT NULL,
    trade_date          date         NOT NULL,
    expectancy_rank     integer      NOT NULL,  -- 1-based position in PortfolioResponse.trades
    signal              varchar(10)  NOT NULL,
    market_type         text,
    -- TradeSetup
    entry_price         numeric,
    stop_loss           numeric,
    profit_target       numeric,
    r_multiple_target   numeric,
    -- ExpectancyScorecard (Van Tharp)
    win_probability     numeric,
    r_ratio             numeric,
    expectancy_value    numeric,
    -- PositionSizing
    shares              integer,
    risk_per_trade      numeric,
    total_account_value numeric,
    -- Steel-man rationale
    bull_case           text,
    bear_case           text,
    PRIMARY KEY (run_id, symbol),
    CONSTRAINT swing_sentry_signals_symbol_check
        CHECK (symbol = upper(trim(symbol))),
    CONSTRAINT swing_sentry_signals_signal_check
        CHECK (signal IN ('BUY', 'HOLD', 'SELL'))
);

CREATE INDEX IF NOT EXISTS swing_sentry_signals_symbol_trade_date_idx
    ON trading_strategy.swing_sentry_signals (symbol, trade_date);

COMMIT;
