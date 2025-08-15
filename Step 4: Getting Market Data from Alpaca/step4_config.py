"""
Basic configuration for Step 4.
- Reads Alpaca credentials from environment variables if available.
- Falls back to importing from Alpaca_API.py at the project root (git-ignored).
- Keeps things simple and explicit for learning purposes.
"""
from __future__ import annotations

import os
import sys
from typing import Tuple


def get_credentials() -> Tuple[str, str]:
    """Return (ALPACA_KEY, ALPACA_SECRET) from env or Alpaca_API.py.

    Order of precedence:
    1. Environment variables ALPACA_KEY, ALPACA_SECRET
    2. Import from Alpaca_API.py at project root
    """
    # Fallback to importing from root-level Alpaca_API.py
    # Add project root to path so we can import Alpaca_API
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    try:
        from Alpaca_API import ALPACA_KEY as FILE_KEY, ALPACA_SECRET as FILE_SECRET  # type: ignore
        if FILE_KEY and FILE_SECRET:
            return FILE_KEY, FILE_SECRET
    except Exception:
        pass

    raise RuntimeError(
        "Alpaca credentials not found. Set ALPACA_KEY and ALPACA_SECRET as environment variables, "
        "or create Alpaca_API.py at the project root with ALPACA_KEY and ALPACA_SECRET."
    )
