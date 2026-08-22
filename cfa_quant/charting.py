"""
Interactive Financial Charting Engine
Builds Plotly Candlestick charts with:
1. Range Selector Buttons (1M, 3M, 6M, YTD, 1Y, 5Y, ALL)
2. Interactive Range Slider & Click-and-Drag Box Zooming
3. Volume Subplot with Color-Coded Buying/Selling Pressure
4. 50-Day and 200-Day Simple Moving Averages (SMA) & Bollinger Bands
"""

import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Optional

class FinancialChartEngine:
    def __init__(self):
        pass

    def get_historical_ohlcv(self, ticker: str, period: str = "2y") -> pd.DataFrame:
        """
        Fetches adjusted OHLCV price history from Yahoo Finance.
        """
        t = yf.Ticker(ticker)
        df = t.history(period=period)
        if df.empty:
            return pd.DataFrame()
            
        df.reset_index(inplace=True)
        # Ensure standard column names
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
        
        # Technical Indicators
        df["SMA_50"] = df["Close"].rolling(window=50).mean()
        df["SMA_200"] = df["Close"].rolling(window=200).mean()
        
        # Bollinger Bands (20-day, 2 std dev)
        df["BB_Mid"] = df["Close"].rolling(window=20).mean()
        df["BB_Std"] = df["Close"].rolling(window=20).std()
        df["BB_Upper"] = df["BB_Mid"] + (2 * df["BB_Std"])
        df["BB_Lower"] = df["BB_Mid"] - (2 * df["BB_Std"])
        
        return df

    def build_candlestick_figure(self, ticker: str, period: str = "2y") -> go.Figure:
        """
        Constructs a dual-panel candlestick + volume interactive figure with range selector
        and custom box-zoom capabilities.
        """
        df = self.get_historical_ohlcv(ticker, period=period)
        if df.empty:
            fig = go.Figure()
            fig.add_annotation(text="No historical price data available", showarrow=False)
            return fig

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.75, 0.25],
            specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
        )

        # 1. Candlestick Trace
        fig.add_trace(
            go.Candlestick(
                x=df["Date"],
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name=f"{ticker} OHLC",
                increasing_line_color="#00E676",
                decreasing_line_color="#FF5252"
            ),
            row=1, col=1
        )

        # 2. Moving Averages
        fig.add_trace(
            go.Scatter(x=df["Date"], y=df["SMA_50"], mode="lines", name="50-Day SMA", line=dict(color="#FFD700", width=1.5)),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df["Date"], y=df["SMA_200"], mode="lines", name="200-Day SMA", line=dict(color="#2196F3", width=2)),
            row=1, col=1
        )

        # 3. Bollinger Bands
        fig.add_trace(
            go.Scatter(x=df["Date"], y=df["BB_Upper"], mode="lines", name="Bollinger Upper", line=dict(color="rgba(180, 180, 180, 0.4)", width=1, dash="dot")),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df["Date"], y=df["BB_Lower"], mode="lines", name="Bollinger Lower", line=dict(color="rgba(180, 180, 180, 0.4)", width=1, dash="dot"), fill="tonexty", fillcolor="rgba(100, 100, 100, 0.05)"),
            row=1, col=1
        )

        # 4. Volume Bar Chart with Color Coding
        colors = ["#00E676" if df["Close"].iloc[i] >= df["Open"].iloc[i] else "#FF5252" for i in range(len(df))]
        fig.add_trace(
            go.Bar(
                x=df["Date"],
                y=df["Volume"],
                name="Volume",
                marker_color=colors,
                opacity=0.7
            ),
            row=2, col=1
        )

        # 5. Range Selector & Slider Configuration
        fig.update_xaxes(
            rangeslider=dict(visible=True, thickness=0.05),
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=3, label="3M", step="month", stepmode="backward"),
                    dict(count=6, label="6M", step="month", stepmode="backward"),
                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                    dict(count=1, label="1Y", step="year", stepmode="backward"),
                    dict(count=5, label="5Y", step="year", stepmode="backward"),
                    dict(step="all", label="ALL")
                ]),
                bgcolor="#1e222d",
                activecolor="#2962FF",
                font=dict(color="#FFFFFF", size=11)
            ),
            row=1, col=1
        )

        fig.update_layout(
            title=f"📈 {ticker} Technical Price Action & Volume Flow",
            template="plotly_dark",
            dragmode="zoom",  # Enables click-and-drag box zoom
            hovermode="x unified",
            margin=dict(l=40, r=40, t=50, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        fig.update_yaxes(title_text="Stock Price ($)", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)

        return fig

if __name__ == "__main__":
    chart_engine = FinancialChartEngine()
    fig = chart_engine.build_candlestick_figure("MSFT", period="1y")
    print("✓ Interactive Candlestick Figure with Range Selector & Zoom successfully generated.")
