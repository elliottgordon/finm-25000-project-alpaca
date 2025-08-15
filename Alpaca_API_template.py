# Alpaca_API_template.py
# 
# This is a template file for your Alpaca API credentials.
# 
# SETUP INSTRUCTIONS:
# 1. Copy this file and rename it to "Alpaca_API.py"
# 2. Replace the placeholder values below with your actual API credentials
# 3. The Alpaca_API.py file will be ignored by git to keep your credentials secure
#
# SECURITY WARNING: Never commit actual API keys to version control!

ALPACA_ENDPOINT = "https://paper-api.alpaca.markets/v2"  # Use this for paper trading
# ALPACA_ENDPOINT = "https://api.alpaca.markets/v2"     # Use this for live trading

# Replace these with your actual Alpaca API credentials
ALPACA_KEY = "YOUR_ALPACA_API_KEY_HERE"
ALPACA_SECRET = "YOUR_ALPACA_SECRET_KEY_HERE"

# You can get your API credentials from: https://app.alpaca.markets/paper/dashboard/overview

# Verification check to prevent running with template values
if ALPACA_KEY == "YOUR_ALPACA_API_KEY_HERE" or ALPACA_SECRET == "YOUR_ALPACA_SECRET_KEY_HERE":
    raise ValueError(
        "Please update your API credentials in Alpaca_API.py before running any scripts. "
        "Copy Alpaca_API_template.py to Alpaca_API.py and replace the placeholder values."
    )
