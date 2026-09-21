# Expectancy and position sizing

The strategy crew is built on Van Tharp expectancy: `E = (Pw x Reward) - (Pl x Risk)`, with
position sizing such that 1R equals exactly `RISK_PER_TRADE x EQUITY`. Do not accept an
alternative sizing scheme unless the strategy task definition changes with it.

## Percent versus fraction

`RISK_PER_TRADE` is a fraction in the environment: `0.01` means one percent. `src/main.py`
multiplies it by 100 before interpolating it into prompts, so the prompt carries a percent
while `PositionSizing.risk_per_trade` in `src/helpers/trade_signals.py` defaults to the
fraction. Flag any diff that injects the prompt value straight into a schema field, or that
mixes the two representations. A 100x sizing error is the failure mode.

## Things to check in any sizing or expectancy change

- The sizing rule is stated explicitly in the task prompt. If the rule is deleted, the model
  improvises share counts.
- `shares` is consistent with `(risk x equity) / (entry - stop)`. Prefer computing it in
  Python after parsing over trusting the model's arithmetic.
- `total_portfolio_risk_percent` counts only signals that actually open risk. Summing HOLD
  rows into portfolio risk is wrong.
- A negative expectancy value paired with a BUY signal and a positive share count is a
  contradiction worth flagging.
- Standing aside stays possible. A prompt that forbids omitting any symbol, while also
  offering no SELL or no-trade option, forces a fabricated BUY.

## Signal vocabulary

`BUY`, `HOLD`, and `SELL` must agree in three places: the task prompt, `TradeSignal.signal`
in `src/helpers/trade_signals.py`, and the CHECK constraint in
`db/migrations/001_swing_sentry_tables.sql`. Flag a change that narrows the vocabulary in
one place only.
