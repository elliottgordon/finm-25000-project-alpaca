
import os
import sys
import time
import logging
from datetime import datetime, timedelta
import pandas as pd
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# Add parent directory to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from trading_strategy import BollingerBandMeanReversionStrategy

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('live_trader.log'),
        logging.StreamHandler()
    ]
)

class LiveTrader:
    def __init__(self, symbols: list, trading_strategy: BollingerBandMeanReversionStrategy):
        self.symbols = symbols
        self.strategy = trading_strategy
        self.trading_client = trading_strategy.trading_client
        self.flag_file = os.path.join(CURRENT_DIR, 'live_trading.flag')

    def create_flag_file(self):
        with open(self.flag_file, 'w') as f:
            f.write('live trading is active')
        logging.info("Live trading flag file created.")

    def remove_flag_file(self):
        if os.path.exists(self.flag_file):
            os.remove(self.flag_file)
            logging.info("Live trading flag file removed.")

    def generate_live_signal(self, symbol: str):
        """
        Generates a trading signal based on the most recent data from the database.
        """
        window = self.strategy.strategy_parameters['bollinger_window']
        live_data = self.strategy.get_historical_data_from_db(symbol)

        if live_data.empty or len(live_data) < window:
            logging.warning(f"Not enough data to generate a signal for {symbol}")
            return 0

        bbands = self.strategy.calculate_bollinger_bands(live_data['close'])
        live_data = live_data.join(bbands)

        latest = live_data.iloc[-1]
        
        signal = 0
        if latest['close'] < latest['lower_band']:
            signal = 1  # Buy
        elif latest['close'] > latest['upper_band']:
            signal = -1 # Sell
        elif latest['close'] > latest['middle_band']:
            signal = 2 # Exit long
        
        return signal

    def execute_trade(self, symbol: str, signal: int):
        """
        Executes a trade based on the generated signal.
        """
        if not self.trading_client:
            logging.warning("Trading client not available. Cannot execute trades.")
            return

        try:
            positions = self.trading_client.get_all_positions()
            existing_position = next((p for p in positions if p.symbol == symbol), None)

            if signal == 1: # Buy signal
                if existing_position:
                    logging.info(f"Buy signal for {symbol}, but position already exists. Holding.")
                else:
                    logging.info(f"Buy signal for {symbol}. Placing market buy order.")
                    market_order_data = MarketOrderRequest(
                        symbol=symbol,
                        qty=1, # Simplified to 1 share for now
                        side=OrderSide.BUY,
                        time_in_force=TimeInForce.DAY
                    )
                    self.trading_client.submit_order(order_data=market_order_data)

            elif signal == -1 or signal == 2: # Sell or Exit signal
                if existing_position and existing_position.side == 'long':
                    logging.info(f"Sell/Exit signal for {symbol}. Closing long position.")
                    self.trading_client.close_position(symbol)
                else:
                    logging.info(f"Sell/Exit signal for {symbol}, but no long position to close.")

        except Exception as e:
            logging.error(f"Error executing trade for {symbol}: {e}")

    def run(self, interval_minutes: int = 1):
        """
        Main trading loop.
        """
        self.create_flag_file()
        try:
            logging.info("Starting live trading bot...")
            while True:
                for symbol in self.symbols:
                    logging.info(f"Analyzing {symbol}...")
                    signal = self.generate_live_signal(symbol)
                    self.execute_trade(symbol, signal)
                
                logging.info(f"Sleeping for {interval_minutes} minute(s)...")
                time.sleep(interval_minutes * 60)
        finally:
            self.remove_flag_file()

if __name__ == "__main__":
    # --- Configuration ---
    SYMBOLS_TO_TRADE = ['SPY', 'QQQ', 'AAPL', 'MSFT'] # Example symbols
    
    # Initialize the strategy
    strategy = BollingerBandMeanReversionStrategy()

    # Initialize and run the live trader
    live_trader = LiveTrader(symbols=SYMBOLS_TO_TRADE, trading_strategy=strategy)
    live_trader.run()
