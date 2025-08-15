# Step 7: Trading Strategy

This folder contains all scripts and documentation related to the development, analysis, and monitoring of your trading strategy.

## Trading Goals
- **Objective:** Achieve steady, risk-adjusted returns using a systematic mean reversion strategy on large-cap equities and top ETFs.
- **Risk Tolerance:** Moderate; the strategy is designed to minimize drawdowns while capturing mean reversion opportunities.
- **Instruments:** S&P 500 stocks and top-traded ETFs, as defined in your project watchlist.

## Strategy Overview
- **Technical Indicators:** Combines Relative Strength Index (RSI) and mean reversion (z-score of price vs. rolling mean).
- **Signals:**
  - Buy: RSI oversold and price significantly below mean
  - Sell: RSI overbought and price significantly above mean
- **Backtesting:** Simulates strategy performance using historical data from your SQLite database.
- **Paper Trading:** Integration with Alpaca's paper trading API for simulated live trading (see `trading_strategy.py` in `archive/experimental`).
- **Real-time Monitoring:** Scripts log and visualize performance, trade statistics, and key metrics.

## Folder Contents
- `strategy_analyzer.py` — Main script for analyzing and visualizing the RSI Mean Reversion strategy, including backtesting and performance metrics.
- `advanced_strategy_analyzer.py` — Multi-asset and advanced analytics, including portfolio metrics and volatility regime detection.
- *(See also: `trading_strategy.py` in `archive/experimental` for live/paper trading logic.)*

## Usage
1. **Backtest and Analyze:**
   - Run `strategy_analyzer.py` to backtest and visualize the strategy on a single asset (e.g., SPY).
   - Use `advanced_strategy_analyzer.py` for multi-asset or portfolio-level analysis.
2. **Paper Trading:**
   - Use the logic in `trading_strategy.py` (archive/experimental) to simulate trades with Alpaca's paper trading API.
3. **Monitor Performance:**
   - Review logs, visualizations, and summary statistics to evaluate and refine your strategy.

## Best Practices
- Clearly document your trading goals and risk profile (see above).
- Use backtesting to validate before deploying any strategy live.
- Monitor real-time performance and be prepared to adjust parameters as needed.

---
For more details, see the main project README or assignment instructions.
