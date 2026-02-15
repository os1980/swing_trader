from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import os

def get_float_env(key: str, default: float) -> float:
    """Get environment variable as float with fallback to default."""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

class TradeSetup(BaseModel):
    entry_price: Optional[float] = Field(description="The price at which to enter the trade. Optional if the signal is HOLD or SELL.")
    stop_loss: Optional[float] = Field(description="The price at which to exit the trade to limit losses. Optional if the signal is HOLD or SELL.")
    profit_target: Optional[float] = Field(description="The price at which to exit the trade to take profits. Optional if the signal is HOLD or SELL.")
    r_multiple_target: Optional[float] = Field(description="Target Reward divided by Initial Risk (1R). Optional if the signal is HOLD or SELL.")

class ExpectancyScorecard(BaseModel):
    win_probability: float = Field(description="Probability of a winning trade (0.0 to 1.0)")
    r_ratio: float = Field(description="The Reward-to-Risk ratio (e.g., 3.0 for 3:1)")
    expectancy_value: float = Field(description="The E-value: (Pw * Reward) - (Pl * Risk)")

class PositionSizing(BaseModel):
    shares: int
    risk_per_trade: float = Field(default_factory=lambda: get_float_env("RISK_PER_TRADE", 0.01))
    total_account_value: float = Field(default_factory=lambda: get_float_env("EQUITY", 10000.0))

class TradeSignal(BaseModel):
    symbol: str
    trade_date: str
    signal: str = Field(description="Must be BUY, HOLD, or SELL")
    market_type: str = Field(description="e.g., Bull Quiet, Bear Volatile")
    trade_setup: TradeSetup
    expectancy_scorecard: ExpectancyScorecard
    position_sizing: PositionSizing
    rationale: Dict[str, Optional[str]] = Field(description="Keys: bull_case, bear_case (Steel-Man debate). Values may be null.")

class PortfolioResponse(BaseModel):
    """The final output sent to the application"""
    trades: List[TradeSignal] = Field(description="A list of trade signals ranked by Expectancy.")
    total_portfolio_risk_percent: float = Field(default=0.0, description="Sum of 1% risk for all BUY signals.")