import os
from collections.abc import Callable
from datetime import datetime, timedelta

import finnhub
import yfinance as yf
from crewai.tools import tool
from langchain_tavily import TavilySearch

from .indicators import compute_indicators


def get_yfinance_data(symbol: str, start_date: str, end_date: str) -> dict:
    """Retrieve the stock price data for a given ticker symbol from Yahoo Finance."""
    try:
        ticker = yf.Ticker(symbol.upper())
        data = ticker.history(start=start_date, end=end_date).reset_index(drop=False)
        if data.empty:
            return { "status": "no_data"} # f"No data found for symbol '{symbol}' between {start_date} and {end_date}"
        # return data.to_csv()
        return {
            "close_prices": data["Close"].tolist(),
            "highs": data["High"].tolist(),
            "lows": data["Low"].tolist(),
            "dates": data["Date"].dt.strftime('%Y-%m-%d').tolist()
        }
    except Exception:
        return { "status": "no_data"} #f"Error fetching Yahoo Finance data: {e}"

# Calendar days of history fetched before end_date so every indicator has enough bars.
# SMA-200 needs 200 trading bars, about 290 calendar days; the rest covers holidays and
# EMA warm-up for MACD. Only the lower bound moves: the data still stops at end_date.
INDICATOR_WARMUP_DAYS = 400

def get_technical_indicators(symbol: str, start_date: str, end_date: str) -> dict:
    """Retrieve key technical indicators for swing trading, as of the last bar before end_date.

    Returns the latest RSI(14), MACD, Bollinger upper and lower bands, SMA(50), SMA(200) and
    ATR(14), plus `as_of` (the date of the last bar used) and `bars` (how many bars were
    available). A value is null when there was not enough history to compute it honestly.
    """
    try:
        end = datetime.strptime(end_date, "%Y-%m-%d")
        warmup_start = (end - timedelta(days=INDICATOR_WARMUP_DAYS)).strftime("%Y-%m-%d")
        fetch_start = min(start_date, warmup_start)
        # yfinance treats `end` as exclusive, so the last bar is strictly before end_date.
        df = yf.download(symbol, start=fetch_start, end=end_date, progress=False)
        if df.empty:
            return {"status": "no_data"}
        return compute_indicators(df)
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}


def get_finnhub_news(symbol: str, start_date: str, end_date: str) -> str:
    """Get company-specific news from Finnhub."""
    try:
        finnhub_client = finnhub.Client(api_key=os.environ["FINNHUB_API_KEY"])
        news_list = finnhub_client.company_news(symbol, _from=start_date, to=end_date)
        news_items = []
        for news in news_list[:7]:
            dt = datetime.fromtimestamp(news['datetime'])
            news_items.append(f"Date: {dt.strftime('%Y-%m-%d')}\nHeadline: {news['headline']}\nSummary: {news['summary']}\n")
        return "\n---\n".join(news_items) if news_items else "No recent news found."
    except Exception as e:
        return f"Error fetching news: {e}"

def get_social_media_sentiment(symbol: str, end_date: str) -> str:
    """Search web for recent social sentiment relevant to swing trading."""
    tavily = TavilySearch(max_results=5)
    query = f"{symbol} stock sentiment OR discussion OR reddit OR stocktwits swing trading before:{end_date}"
    return tavily.invoke({"query": query})

# TODO Depper check on the input and output logic to make sure the Agent can decide on the company strength.
def get_fundamental_analysis(symbol: str, end_date: str) -> str:
    """Search for recent fundamental analysis reports suitable for swing trading."""
    tavily = TavilySearch(max_results=7)
    query = f"{symbol} fundamental analysis OR earnings OR valuation OR price target before:{end_date}"
    return tavily.invoke({"query": query})

def get_macroeconomic_news(end_date: str) -> str:
    """Search for macroeconomic events impacting markets around the trade date."""
    tavily = TavilySearch(max_results=15)
    query = f"macroeconomic news OR Fed OR inflation OR jobs OR GDP OR interest rates before {end_date}"
    return tavily.invoke({"query": query})

_TOOL_FUNCTIONS: dict[str, Callable] = {
    "get_yfinance_data": get_yfinance_data,
    "get_technical_indicators": get_technical_indicators,
    "get_finnhub_news": get_finnhub_news,
    "get_social_media_sentiment": get_social_media_sentiment,
    "get_fundamental_analysis": get_fundamental_analysis,
    "get_macroeconomic_news": get_macroeconomic_news,
}
TOOL_NAMES = tuple(_TOOL_FUNCTIONS)


def build_tools(*names: str, max_usage_count: int = 1) -> list:
    """Return fresh CrewAI tool objects for one crew instance.

    CrewAI counts usage on the tool object itself, writes that count back to the original
    tool, and never resets it. Module-level tool singletons with max_usage_count=1 therefore
    lock after the first crew that uses them: every watchlist symbol after the first got a
    usage-limit error on every tool. Build tools per crew instead, so the limit means
    "once per symbol".
    """
    unknown = [n for n in names if n not in _TOOL_FUNCTIONS]
    if unknown:
        raise KeyError(f"Unknown tools {unknown}; known tools are {list(TOOL_NAMES)}")
    return [tool(name, max_usage_count=max_usage_count)(_TOOL_FUNCTIONS[name]) for name in names]
