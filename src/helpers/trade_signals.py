from pydantic import BaseModel, Field
from typing import Optional, Dict
import os

class TradeSetup(BaseModel):
    entry_price: float
    stop_loss: float
    profit_target: float
    r_multiple_target: float = Field(description="Target Reward divided by Initial Risk (1R)")

class ExpectancyScorecard(BaseModel):
    win_probability: float = Field(description="Probability of a winning trade (0.0 to 1.0)")
    r_ratio: float = Field(description="The Reward-to-Risk ratio (e.g., 3.0 for 3:1)")
    expectancy_value: float = Field(description="The E-value: (Pw * Reward) - (Pl * Risk)")

class PositionSizing(BaseModel):
    shares: int
    risk_per_trade: float = os.getenv("RISK_PER_TRADE", 0.01)
    total_account_value: float = os.getenv("EQUITY", 10000)

class TradeSignal(BaseModel):
    symbol: str
    trade_date: str
    signal: str = Field(description="Must be BUY, HOLD, or SELL")
    market_type: str = Field(description="e.g., Bull Quiet, Bear Volatile")
    trade_setup: TradeSetup
    expectancy_scorecard: ExpectancyScorecard
    position_sizing: PositionSizing
    rationale: Dict[str, str] = Field(description="Keys: bull_case, bear_case (Steel-Man debate)")