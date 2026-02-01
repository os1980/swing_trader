from dotenv import load_dotenv
from getpass import getpass
import os
import sys

sys.stdin = open(os.devnull)

# Need to be before the crewai imports to control the location of the storage
def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass(f"Enter your {var}: ")

load_dotenv()


# Suppress the exact prompt
def no_prompt(*args, **kwargs):
    return "n"  # auto-answer "no"

try:
    from crewai.utilities import tracing
    if hasattr(tracing, "ask_to_view_traces"):
        tracing.ask_to_view_traces = no_prompt
    if hasattr(tracing, "prompt_for_traces"):
        tracing.prompt_for_traces = no_prompt
except ImportError:
    pass  # tracing module moved in some versions

import os
import warnings
import sys
from pathlib import Path

from crewai.flow.flow import Flow, listen, start
from pydantic import BaseModel
from crews.macro_crew import MacroCrew
from crews.analysis_crew import AnalysisCrew
from crews.strategy_crew import StrategyCrew
import datetime

# Silence only this exact family of pydantic serialization warnings
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message="Pydantic serializer warnings:",
    module="pydantic.main",  # or "pydantic" to be broader
)

# from crewai.utilities.paths import db_storage_path
# import os
#
# print("CREWAI_STORAGE_DIR env var:", os.getenv("CREWAI_STORAGE_DIR"))
# print("Actual CrewAI base storage path:", db_storage_path())
#
# # Optional: list contents to see subdirs
# base = db_storage_path()
# if os.path.exists(base):
#     print("Contents:")
#     for item in os.listdir(base):
#         print("  ", item)
#
# sys.exit(0)
class TradingState(BaseModel):
    symbol: str = ""
    trade_date: str = str(datetime.date.today())
    start_date: str = str(datetime.date.today() - datetime.timedelta(days=20))
    end_date: str = str(datetime.date.today() - datetime.timedelta(days=1))
    macro_context: str = ""
    ticker_data: str = ""
    watchlist: list[str] = []
    ticker_analysis_results: dict[str, str] = {}
    equity: int = os.getenv("EQUITY", 10000)
    risk: float = os.getenv("RISK_PER_TRADE", 0.01)  # How much percentage of the total equity to risk on single position

class SwingSentryFlow(Flow[TradingState]):
    def __init__(self):
        super().__init__()
        # Force tracing off at the object level
        self.tracing = False

    @start()
    def get_global_macro(self):
        """Runs once per trade_date, shared by all symbols."""
        print(f"--- Running Global Macro for {self.state.trade_date} ---")

        os.environ["CREWAI_STORAGE_DIR"] = f"{os.getenv('MEMORY_DB_BASE_DIR')}/global_macro"

        # 1. Run the crew once
        result = MacroCrew().crew().kickoff(inputs={
            "trade_date": self.state.trade_date,
            "start_date": self.state.start_date,
            "end_date": self.state.end_date,
        })

        # 2. Store in state so it persists for all listeners
        self.state.macro_context = result.raw
        # return result.raw

    @listen(get_global_macro)
    def analyze_all_symbols(self):
        """Triggers for each symbol using the pre-calculated macro."""

        for symbol in self.state.watchlist:
            print(f"--- Analyzing {symbol} using Global Macro context ---")
            #     # ISOLATION: Dynamic path based on symbol prevents memory bleed
            os.environ["CREWAI_STORAGE_DIR"] = f"{os.getenv('MEMORY_DB_BASE_DIR')}/analyze/tickers/{symbol}/"

            # 3. Pass the stored macro_context into the symbol-specific crew
            result = AnalysisCrew().crew().kickoff(inputs={
                "symbol": symbol,
                "trade_date": self.state.trade_date,
                "start_date": self.state.start_date,
                "end_date": self.state.end_date,
                # "macro_context": self.state.macro_context,
                "equity": self.state.equity,
                "risk": str(float(self.state.risk) * 100),
            })

            self.state.ticker_analysis_results[symbol] = result.raw

    @listen(analyze_all_symbols)
    def finalize_plan(self):
        """Triggers for each symbol using the pre-calculated macro."""

        all_plans = {}

        for symbol in self.state.watchlist:
            print(f"--- Analyzing {symbol} using Global Macro context ---")
            #     # ISOLATION: Dynamic path based on symbol prevents memory bleed
            os.environ["CREWAI_STORAGE_DIR"] = f"{os.getenv('MEMORY_DB_BASE_DIR')}/strategy/tickers/{symbol}/"

            result = StrategyCrew().crew().kickoff(inputs={
                        "symbol": symbol,
                        "trade_date": self.state.trade_date,
                        "start_date": self.state.start_date,
                        "end_date": self.state.end_date,
                        "macro_report": self.state.macro_context,
                        "analyst_dossier": self.state.ticker_analysis_results[symbol],
                       "equity": self.state.equity,
                       "risk": str(float(self.state.risk) * 100),
                    })

            all_plans[symbol] = result

        return all_plans


# TODO make sure no future look
# TODO teach to learn based on future look for swing trading both backtesting and daily runs


def run_multi_symbol(watchlist: list, trade_date: str):
    start_date = (datetime.datetime.strptime(trade_date, "%Y-%m-%d") - datetime.timedelta(days=90)).strftime("%Y-%m-%d")
    end_date = (datetime.datetime.strptime(trade_date, "%Y-%m-%d") - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    flow = SwingSentryFlow()

    print(f"\n{'=' * 30}\nSTARTING ANALYSIS: {watchlist}\n{'=' * 30}")
    flow.state.trade_date = trade_date
    flow.state.start_date = start_date
    flow.state.end_date = end_date
    flow.state.watchlist = watchlist
    final_report = flow.kickoff()

    for symbol, final_report in final_report.items():
        report_dir = Path(os.getenv("FINAL_REPORT_BASE_DIR")) / symbol
        report_dir.mkdir(parents=True, exist_ok=True)
        file_path = report_dir / f"{trade_date}_{symbol}_report.json"
        with open(file_path, "w") as f:
            f.write(str(final_report))

    # TODO add simple extract information from the report as dataframe (symbol, signal, stop loss, take profit etc.)


if __name__ == "__main__":
    run_multi_symbol(watchlist=["AAPL"], trade_date="2025-01-07")