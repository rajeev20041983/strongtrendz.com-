"""
update_stocks.py
----------------
Weekend script — reads NSE CSV (Spurts in OI / FO momentum)
and writes a fresh stocks_config.json.

Usage:
    python scripts/update_stocks.py
    python scripts/update_stocks.py --csv SpurtsinOI.csv --min-change 10 --max-stocks 20

After running, reload live server without restarting:
    curl -X POST https://your-ngrok-url/reload-config
"""

import pandas as pd
import json
import os
import argparse
from datetime import datetime

CONFIG_PATH           = os.path.join(os.path.dirname(__file__), '..', 'config', 'stocks_config.json')
TARGET_POSITION_VALUE = 12000   # ₹ per position for quantity calculation


def calculate_quantity(price: float) -> int:
    """Quantity so position value stays near TARGET_POSITION_VALUE."""
    if not price or price <= 0:
        return 25
    qty = int(TARGET_POSITION_VALUE / price)
    if price < 100:   return min(200, max(50,  qty))
    if price < 500:   return min(50,  max(20,  qty))
    if price < 1000:  return min(25,  max(10,  qty))
    if price < 2000:  return min(15,  max(5,   qty))
    if price < 5000:  return min(5,   max(2,   qty))
    return max(1, qty)


def find_col(df, patterns):
    """Case-insensitive column search."""
    for pat in patterns:
        for col in df.columns:
            if pat.lower() in col.lower():
                return col
    return None


def update_stocks(csv_path: str, min_change: float = 10.0, max_stocks: int = 20):
    print(f"\n📂 Reading: {csv_path}")
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()

    symbol_col = find_col(df, ['symbol', 'ticker', 'scrip', 'underlying']) or df.columns[0]
    change_col = find_col(df, ['%chng', 'change%', 'chng%', '% change', 'change (%)'])
    price_col  = find_col(df, ['ltp', 'last price', 'close', 'prev. close'])

    if not change_col:
        print("❌ Cannot find change% column. Available:", df.columns.tolist())
        return

    print(f"   Symbol : {symbol_col}")
    print(f"   Change : {change_col}")
    print(f"   Price  : {price_col or 'not found — default qty used'}")

    # Clean and convert change column
    df[change_col] = (
        df[change_col].astype(str)
        .str.replace('%', '', regex=False)
        .str.replace(',', '', regex=False)
    )
    df[change_col] = pd.to_numeric(df[change_col], errors='coerce')

    filtered = df[df[change_col] > min_change].sort_values(change_col, ascending=False).head(max_stocks)

    if filtered.empty:
        print(f"⚠️  No stocks with change% > {min_change}%")
        return

    print(f"\n{'─'*55}")
    print(f"  {'SYMBOL':<14} {'QTY':<6} {'PRICE':>10}   {'CHANGE':>8}")
    print(f"{'─'*55}")

    stock_list = []
    for _, row in filtered.iterrows():
        symbol = str(row[symbol_col]).strip().upper().split(':')[-1]
        if not symbol or symbol == 'NAN':
            continue

        price = None
        if price_col:
            try:
                price = float(str(row[price_col]).replace(',', '').replace(' ', ''))
            except (ValueError, TypeError):
                pass

        qty    = calculate_quantity(price) if price else 25
        change = round(float(row[change_col]), 2) if pd.notna(row[change_col]) else 0

        stock_list.append({
            "symbol":   symbol,
            "quantity": qty,
            "enabled":  True,
        })

        price_str = f"Rs{price:>9.2f}" if price else f"{'N/A':>10}"
        print(f"  {symbol:<14} {qty:<6} {price_str}   {change:>+7.2f}%")

    print(f"{'─'*55}")
    print(f"  {len(stock_list)} stocks selected\n")

    if not stock_list:
        print("❌ No valid stocks")
        return

    config = {
        "stocks": {
            "list": stock_list
        },
        "trading_settings": {
            "max_total_positions": 10,
            "_updated": f"{datetime.now().strftime('%Y-%m-%d %H:%M')} | change>{min_change}% | {len(stock_list)} stocks"
        }
    }

    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"✅ Saved -> {CONFIG_PATH}")
    print(f"\nTo apply without restarting:")
    print(f"  curl -X POST https://your-ngrok-url/reload-config\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update stocks_config from NSE CSV")
    parser.add_argument('--csv',        default=None,             help='Path to NSE CSV file')
    parser.add_argument('--min-change', type=float, default=10.0, help='Min change%% (default 10)')
    parser.add_argument('--max-stocks', type=int,   default=20,   help='Max stocks (default 20)')
    args = parser.parse_args()

    csv_path = args.csv or input("Enter CSV file path: ").strip()

    if not os.path.exists(csv_path):
        print(f"❌ File not found: {csv_path}")
    else:
        update_stocks(csv_path, args.min_change, args.max_stocks)
