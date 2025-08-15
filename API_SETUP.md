# API Configuration Setup

## ⚠️ IMPORTANT: Setting Up Your API Keys

This project requires Alpaca API credentials to function. For security reasons, the actual API key file (`Alpaca_API.py`) is **not included** in this repository and is ignored by git.

### Setup Instructions:

1. **Copy the template file:**
   ```bash
   cp Alpaca_API_template.py Alpaca_API.py
   ```

2. **Get your Alpaca API credentials:**
   - Go to [Alpaca Paper Trading Dashboard](https://app.alpaca.markets/paper/dashboard/overview)
   - Create a paper trading account if you don't have one
   - Generate your API key and secret key

3. **Update `Alpaca_API.py`:**
   - Open the newly created `Alpaca_API.py` file
   - Replace `YOUR_ALPACA_API_KEY_HERE` with your actual API key
   - Replace `YOUR_ALPACA_SECRET_KEY_HERE` with your actual secret key

4. **Verify the setup:**
   - The code includes a check that will raise an error if you try to run scripts with placeholder values
   - This prevents accidental execution with invalid credentials

### Security Notes:

- ✅ `Alpaca_API.py` is automatically ignored by git (listed in `.gitignore`)
- ✅ Template file `Alpaca_API_template.py` is safe to commit (contains no secrets)
- ❌ **NEVER** commit actual API keys to version control
- ❌ **NEVER** share your API keys publicly

### File Structure:
```
├── Alpaca_API_template.py  # Template (safe to commit)
├── Alpaca_API.py          # Your actual credentials (git ignored)
└── .gitignore             # Ensures API keys are never committed
```
