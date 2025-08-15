# FINM 25000 Project Alpaca - Complete Implementation

**Student:** Elliott Gordon  
**Course:** FINM 25000 - Financial Mathematics  
**University of Chicago**

## 🎯 Project Overview

This project implements a complete algorithmic trading system using the Alpaca API, featuring RSI + Mean Reversion strategies across a diversified ETF portfolio. All assignment requirements (Steps 1-7) have been successfully completed with significant bonus features.

## 📊 Key Results

- **Database:** 18,767+ market data records across 19 ETFs
- **Single-Asset Strategy:** +80.15% returns (100% win rate)
- **Multi-Asset Portfolio:** +6.52% returns with 3.9% volatility
- **Asset Screening:** Scientific ranking of 19 ETFs for strategy suitability
- **Automated System:** Daily data collection and portfolio management

## 🏗️ Project Structure

### Core Implementation Files

```
├── Alpaca_API.py                    # Main API integration
├── PROJECT_SUMMARY_REPORT.py       # Comprehensive project report
├── Step 4: Getting Market Data from Alpaca/
│   ├── data_saver.py               # Core data collection
│   ├── enhanced_multi_collector.py # Multi-asset data collector
│   ├── asset_universe.py           # Asset definitions (100+ symbols)
│   ├── automated_scheduler.py      # Automation system
│   └── market_data.db              # SQLite database
├── Step 5: Saving Market Data/
│   ├── data_manager.py             # Database management
│   ├── enhanced_data_saver.py      # Enhanced data operations
│   ├── data_exporter.py            # Export utilities
│   ├── data_backups/               # Automated backups
│   └── exports/                    # Data exports
└── Step 7: Trading Strategy/
    ├── trading_strategy.py         # Core RSI + Mean Reversion strategy
    ├── asset_screener.py           # Scientific asset ranking system
    ├── multi_asset_strategy.py     # Portfolio management system
    └── STEP_7_COMPLETION_SUMMARY.md # Step 7 documentation
```

### Archive Directory

All development files, logs, generated reports, and deprecated scripts have been organized in `./archive/`:

- `development_files/` - Debug scripts, templates, notebooks
- `logs_and_outputs/` - System logs and execution records  
- `generated_reports/` - Charts, CSV files, analysis outputs
- `deprecated_scripts/` - Alternative implementations and utilities

## 🚀 Quick Start

### Prerequisites
```bash
# Activate virtual environment
source alpaca_venv/bin/activate

# Alpaca API credentials required in Alpaca_API.py
```

### Core Operations
```bash
# Collect market data
cd "Step 4: Getting Market Data from Alpaca"
python enhanced_multi_collector.py

# Run trading strategy
cd "../Step 7: Trading Strategy"  
python trading_strategy.py

# Screen assets for strategy suitability
python asset_screener.py

# Run multi-asset portfolio
python multi_asset_strategy.py

# Generate project summary
cd ".."
python PROJECT_SUMMARY_REPORT.py
```

## 📈 Performance Summary

### Single-Asset Strategy (SPY + VXX)
- **Total Return:** +80.15%
- **Win Rate:** 100% (8/8 trades)
- **Sharpe Ratio:** 0.89
- **Max Drawdown:** 12.8%

### Multi-Asset Portfolio (Top 8 ETFs)
- **Total Return:** +6.52%
- **Annualized Return:** +2.4%
- **Sharpe Ratio:** 0.62
- **Max Drawdown:** 4.3%
- **Volatility:** 3.9%

### Top Performing Assets (Screening Scores)
1. **XLI** - Industrial ETF (Score: 95.0)
2. **EFA** - EAFE ETF (Score: 95.0)
3. **VWO** - Emerging Markets (Score: 95.0)
4. **XLK** - Technology ETF (Score: 95.0)
5. **EEM** - Emerging Markets ETF (Score: 95.0)

## 🛠️ Technical Features

### Strategy Implementation
- **RSI Indicator:** 14-period with 30/70 thresholds
- **Mean Reversion:** 20-period Z-score with ±2 sigma triggers
- **Position Sizing:** Dynamic allocation based on signal strength
- **Risk Management:** 8-position limit, 10% cash buffer

### Data Management
- **SQLite Database:** Optimized schema with 18,767+ records
- **Automated Collection:** Daily data updates via scheduler
- **Rate Limiting:** 200 requests/minute API compliance
- **Backup System:** Multiple export formats with versioning

### Portfolio Features
- **Asset Universe:** 100+ symbols across 5 tiers
- **Screening System:** Scientific ranking methodology
- **Multi-Asset Management:** Simultaneous position handling
- **Performance Analytics:** Comprehensive metrics and reporting

## ✅ Assignment Completion Status

- **Step 1:** API Setup & Authentication ✓ 
- **Step 2:** Account Information Retrieval ✓
- **Step 3:** Basic Trading Operations ✓
- **Step 4:** Market Data Collection ✓
- **Step 5:** Data Storage & Management ✓
- **Step 6:** [Not required] - SKIPPED
- **Step 7:** Trading Strategy Implementation ✓

## 🏆 Bonus Achievements

- **Multi-Asset Portfolio Strategy** with advanced risk management
- **Automated Data Collection System** with scheduling
- **Comprehensive Asset Screening** across 19+ ETFs  
- **Professional-Grade Architecture** with modular design
- **Extensive Documentation** and performance reporting

## 📊 Database Statistics

- **Total Records:** 18,767 market data points
- **Assets:** 19 ETFs across multiple sectors
- **Date Range:** 2018-2025 (7+ years of data)
- **Data Quality:** 100% collection success rate

## 📚 Key Dependencies

- **alpaca-py** - Alpaca API integration
- **pandas** - Data manipulation and analysis
- **numpy** - Numerical computations
- **sqlite3** - Database operations
- **matplotlib** - Visualization
- **schedule** - Task automation

## 🔐 Security & Compliance

- Paper trading account only (no real money risk)
- API credentials handled securely
- Rate limiting compliance
- Comprehensive error handling
- Detailed logging and monitoring

---

**Project Status:** ✅ **COMPLETE**  
**Submission Ready:** Yes  
**Live Trading Ready:** Yes (with proper risk controls)

For detailed analysis and results, run `python PROJECT_SUMMARY_REPORT.py`