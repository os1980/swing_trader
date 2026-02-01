from crewai.tools import tool
import yfinance as yf
import finnhub
from langchain_tavily import TavilySearch
# import pandas as pd
from datetime import datetime#, timedelta
from stockstats import wrap as stockstats_wrap
import os


# Now define your tools using the correct @tool decorator
@tool("get_yfinance_data", max_usage_count=1)
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
    except Exception as e:
        return { "status": "no_data"} #f"Error fetching Yahoo Finance data: {e}"

@tool("get_technical_indicators", max_usage_count=1)
def get_technical_indicators(symbol: str, start_date: str, end_date: str) -> dict:
    """Retrieve key technical indicators for swing trading."""
    try:
        df = yf.download(symbol, start=start_date, end=end_date, progress=False)
        if df.empty:
            return { "status": "no_data"}

        stock_df = stockstats_wrap(df)

        return {
            "rsi_14": float(stock_df["rsi_14"].tolist()),
            "macd": float(stock_df["macd"].tolist()),
            "boll_upper": float(stock_df["boll_ub"].tolist()),
            "boll_lower": float(stock_df["boll_lb"].tolist()),
            "sma_50": float(stock_df["close_50_sma"].tolist()),
            "sma_200": float(stock_df["close_200_sma"].tolist()),
            "atr_14": float(stock_df["atr_14"].tolist())
        }

        # return {
        #     "rsi_14": float(stock_df["rsi_14"].iloc[-1]),
        #     "macd": float(stock_df["macd"].iloc[-1]),
        #     "boll_upper": float(stock_df["boll_ub"].iloc[-1]),
        #     "boll_lower": float(stock_df["boll_lb"].iloc[-1]),
        #     "sma_50": float(stock_df["close_50_sma"].iloc[-1]),
        #     "sma_200": float(stock_df["close_200_sma"].iloc[-1]),
        #     "atr_14": float(stock_df["atr_14"].iloc[-1])
        # }
        #

    except Exception:
        return { "status": "no_data"}


@tool("get_finnhub_news", max_usage_count=1)
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

@tool("get_social_media_sentiment", max_usage_count=1)
def get_social_media_sentiment(symbol: str, end_date: str) -> str:
    """Search web for recent social sentiment relevant to swing trading."""
    tavily = TavilySearch(max_results=5)
    query = f"{symbol} stock sentiment OR discussion OR reddit OR stocktwits swing trading before:{end_date}"
    return tavily.invoke({"query": query})

# TODO Depper check on the input and output logic to make sure the Agent can decide on the company strength.
@tool("get_fundamental_analysis", max_usage_count=1)
def get_fundamental_analysis(symbol: str, end_date: str) -> str:
    """Search for recent fundamental analysis reports suitable for swing trading."""
    tavily = TavilySearch(max_results=7)
    query = f"{symbol} fundamental analysis OR earnings OR valuation OR price target before:{end_date}"
    return tavily.invoke({"query": query})

@tool("get_macroeconomic_news", max_usage_count=1)
def get_macroeconomic_news(end_date: str) -> str:
    """Search for macroeconomic events impacting markets around the trade date."""
    tavily = TavilySearch(max_results=15)
    query = f"macroeconomic news OR Fed OR inflation OR jobs OR GDP OR interest rates before {end_date}"
    return tavily.invoke({"query": query})

# Export list of tools
TOOLS = {
    "get_yfinance_data": get_yfinance_data,
    "get_technical_indicators": get_technical_indicators,
    "get_finnhub_news": get_finnhub_news,
    "get_social_media_sentiment": get_social_media_sentiment,
    "get_fundamental_analysis": get_fundamental_analysis,
    "get_macroeconomic_news": get_macroeconomic_news,
}