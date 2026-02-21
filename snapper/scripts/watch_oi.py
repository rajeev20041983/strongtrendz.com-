"""
watch_oi.py
-----------
Watches a folder for new OI Spurts xlsx files dropped manually.
On each new file:
  - Reads stocks with change% > MIN_CHANGE
  - Compares with current stocks_config.json
  - Removes stocks not in new file
  - Adds new stocks that qualify
  - Updates stocks_config.json
  - Reloads live trading server automatically

Usage:
    python watch_oi.py
    python watch_oi.py --folder "C:/Downloads" --min-change 5
"""

import os
import sys
import json
import time
import glob
import argparse
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────
WATCH_FOLDER    = os.path.expanduser("~/Downloads")   # folder to watch
CONFIG_FILE     = "config/stocks_config.json"
RELOAD_URL      = "https://strongtrendz.ngrok-free.app/reload-config"
MIN_CHANGE      = 2.0      # minimum change% to qualify (weak build threshold)

# Index futures to exclude — not tradeable as equity cash
EXCLUDE_SYMBOLS = {
    'NIFTY', 'BANKNIFTY', 'MIDCPNIFTY', 'FINNIFTY',
    'SENSEX', 'BANKEX', 'NIFTYNXT50', 'CRUDEOIL',
    'GOLD', 'SILVER', 'NATURALGAS'
}
MAX_STOCKS      = 30       # max stocks in config
TARGET_VALUE    = 12000    # ₹ per position for qty calc
POLL_INTERVAL   = 10       # seconds between folder checks
FILE_PREFIX     = "Spurts-in-OI"  # filename prefix to watch for
FILE_EXT        = "*.csv"             # NSE downloads as CSV

# ── QUANTITY CALC ─────────────────────────────────────────────
def calculate_quantity(price: float) -> int:
    if not price or price <= 0:
        return 25
    qty = int(TARGET_VALUE / price)
    if price < 100:   return min(200, max(50,  qty))
    if price < 500:   return min(50,  max(20,  qty))
    if price < 1000:  return min(25,  max(10,  qty))
    if price < 2000:  return min(15,  max(5,   qty))
    if price < 5000:  return min(5,   max(2,   qty))
    return max(1, qty)


# ── EXCEL PARSER ──────────────────────────────────────────────
def parse_oi_file(filepath: str) -> list:
    """
    Parse NSE OI Spurts xlsx file.
    Returns list of dicts with symbol, change_pct, ltp, quantity
    sorted by change% descending.
    """
    try:
        df = pd.read_csv(filepath, header=0)
        df.columns = df.columns.str.strip()

        print(f"   Columns found: {df.columns.tolist()}")

        # Find relevant columns — NSE file uses various names
        def find_col(patterns):
            for pat in patterns:
                for col in df.columns:
                    if pat.lower() in col.lower():
                        return col
            return None

        sym_col    = find_col(['symbol', 'underlying', 'scrip', 'ticker'])
        change_col = find_col(['%chng', 'change%', 'chng%', '% change', 'change (%)'])
        price_col  = find_col(['underlying value', 'ltp', 'last price', 'close', 'prev. close', 'price', 'underlying'])

        if not sym_col:
            sym_col = df.columns[0]
            print(f"   ⚠️  Using first column as symbol: {sym_col}")

        if not change_col:
            print(f"   ❌ Cannot find change% column")
            return []

        print(f"   Symbol col  : {sym_col}")
        print(f"   Change col  : {change_col}")
        print(f"   Price col   : {price_col or 'not found'}")

        # Clean change column
        df[change_col] = (
            df[change_col].astype(str)
            .str.replace('%', '', regex=False)
            .str.replace(',', '', regex=False)
            .str.strip()
        )
        df[change_col] = pd.to_numeric(df[change_col], errors='coerce')

        # Sort by change% descending, take top MAX_STOCKS
        # No minimum filter — take all stocks ordered by OI change
        filtered = df.copy()
        filtered = filtered.sort_values(change_col, ascending=False)
        filtered = filtered.head(MAX_STOCKS)

        results = []
        for _, row in filtered.iterrows():
            symbol = str(row[sym_col]).strip().upper().split(':')[-1]
            if not symbol or symbol in ('NAN', 'SYMBOL', ''):
                continue

            # Skip index futures
            if symbol in EXCLUDE_SYMBOLS:
                print(f"   ⏭️  Skipping index: {symbol}")
                continue

            # Get price for qty calculation
            price = None
            if price_col:
                try:
                    price = float(str(row[price_col]).replace(',', '').replace(' ', ''))
                except (ValueError, TypeError):
                    pass

            change = round(float(row[change_col]), 2) if pd.notna(row[change_col]) else 0
            qty    = calculate_quantity(price) if price else 25

            results.append({
                "symbol":     symbol,
                "change_pct": change,
                "ltp":        round(price, 2) if price else None,
                "quantity":   qty,
            })

        return results

    except Exception as e:
        print(f"   ❌ Parse error: {e}")
        return []


# ── CONFIG MANAGER ────────────────────────────────────────────
def load_config() -> dict:
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"stocks": {"list": []}, "trading_settings": {"max_total_positions": 10}}


def save_config(stock_list: list, note: str):
    config = {
        "stocks": {
            "list": stock_list
        },
        "trading_settings": {
            "max_total_positions": min(len(stock_list), MAX_STOCKS),
            "_updated": note
        }
    }
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        # Write header
        f.write('{\n  "stocks": {\n    "list": [\n')
        # Write each stock on one line
        for i, s in enumerate(stock_list):
            comma = ',' if i < len(stock_list) - 1 else ''
            f.write(f'      {{"symbol": "{s["symbol"]}", "quantity": {s["quantity"]}, "enabled": {str(s["enabled"]).lower()}}}{comma}\n')
        f.write('    ]\n  },\n')
        f.write(f'  "trading_settings": {{\n')
        f.write(f'    "max_total_positions": {min(len(stock_list), MAX_STOCKS)},\n')
        f.write(f'    "_updated": "{note}"\n')
        f.write('  }\n}\n')


def reload_server():
    try:
        resp = requests.post(RELOAD_URL, timeout=5)
        if resp.status_code == 200:
            print(f"   ✅ Server reloaded — {resp.json().get('stocks', '?')} stocks active")
        else:
            print(f"   ⚠️  Reload returned {resp.status_code}")
    except Exception as e:
        print(f"   ⚠️  Could not reach server: {e}")


# ── CORE UPDATE LOGIC ─────────────────────────────────────────
def update_from_file(filepath: str):
    print(f"\n{'─'*55}")
    print(f"📂 New file detected: {Path(filepath).name}")
    print(f"{'─'*55}")

    # Step 1 — Parse latest OI file only
    oi_stocks = parse_oi_file(filepath)

    if not oi_stocks:
        print("   ⚠️  No stocks found in OI file — config unchanged")
        return

    # Find ALL today's files to check OI direction across them
    today     = DATE_OVERRIDE or datetime.now().strftime("%d%m%Y")
    pattern   = os.path.join(os.path.dirname(filepath), f"{FILE_PREFIX}*{today}*.csv")
    all_today = sorted(glob.glob(pattern), key=os.path.getmtime)

    # Build OI history: symbol → [pct_file1, pct_file2, ... pct_latest]
    oi_history = {}
    for f in all_today:
        stocks = parse_oi_file(f)
        for s in stocks:
            sym = s["symbol"]
            if sym not in oi_history:
                oi_history[sym] = []
            oi_history[sym].append(s["change_pct"])

    # ── Filter rules — stricter with more files ─────────────────
    # 1 file  → no filtering, take everything
    # 2 files → Rule 1: exclude stocks where OI dropped vs previous
    # 3 files → Rule 1 + Rule 2: also exclude weak builds
    # 4+ files→ Rule 1 + Rule 2 + Rule 3: must show consistent climb

    num_files = len(all_today)
    filtered_stocks = []
    excluded = []

    print(f"   📂 Files so far today: {num_files} → ", end='')
    if num_files == 1:
        print("no filters applied")
    elif num_files == 2:
        print("Rule 1 active: drop filter")
    elif num_files == 3:
        print("Rules 1+2 active: drop + weak build filter")
    else:
        print(f"Rules 1+2+3 active: drop + weak + consistent climb filter")

    for s in oi_stocks:
        sym      = s["symbol"]
        curr_pct = s["change_pct"]
        history  = oi_history.get(sym, [curr_pct])

        # Rule 1 (2+ files) — OI dropped vs previous file OR dropped from peak
        if num_files >= 2 and len(history) >= 2:
            prev_pct = history[-2]
            peak_pct = max(history)
            # Dropped vs previous file
            if curr_pct < prev_pct:
                excluded.append(f"{sym}(dropped:{prev_pct:+.2f}→{curr_pct:+.2f})")
                continue
            # Dropped from peak by more than 0.5% tolerance
            PEAK_TOLERANCE = 0.5
            if (peak_pct - curr_pct) > PEAK_TOLERANCE:
                excluded.append(f"{sym}(peak:{peak_pct:+.2f}→now:{curr_pct:+.2f} drop:{peak_pct-curr_pct:.2f})")
                continue

        # Rule 2 (3+ files) — Weak build, barely moved
        if num_files >= 3:
            if curr_pct < MIN_CHANGE:
                excluded.append(f"{sym}(weak:{curr_pct:+.2f}%)")
                continue

        # Rule 3 (4+ files) — Must show consistent upward climb
        # i.e. more ups than downs across all files
        if num_files >= 4 and len(history) >= 3:
            ups   = sum(1 for i in range(1, len(history)) if history[i] >= history[i-1])
            downs = sum(1 for i in range(1, len(history)) if history[i] < history[i-1])
            if downs > ups:
                excluded.append(f"{sym}(inconsistent:{ups}up/{downs}dn)")
                continue

        filtered_stocks.append(s)

    if excluded:
        print(f"\n   ❌ Excluded ({len(excluded)}): {', '.join(excluded)}")
    print(f"   ✅ Qualifying: {len(filtered_stocks)} stocks")

    oi_stocks = filtered_stocks

    # Step 2 — Load current config (deduplicate in case of bad state)
    current_cfg  = load_config()
    current_list = current_cfg.get("stocks", {}).get("list", [])
    seen = set()
    deduped = []
    for s in current_list:
        if s["symbol"] not in seen:
            seen.add(s["symbol"])
            deduped.append(s)
    current_list = deduped
    current_map  = {s["symbol"]: s for s in current_list}
    current_syms = set(current_map.keys())

    # Step 3 — Build OI lookup map for quick reference
    oi_map     = {s["symbol"]: s for s in oi_stocks}
    oi_symbols = [s["symbol"] for s in oi_stocks]  # ordered by change% desc

    # Step 4 — Start with existing config stocks that are still in today's OI
    final_list  = []
    kept_syms   = set()
    added_syms  = set()
    removed_syms = set()

    # Keep existing config stocks that appear in today's OI file
    for sym, cfg_stock in current_map.items():
        if sym in oi_map:
            # Stock still active in OI — keep with existing qty
            final_list.append({
                "symbol":   sym,
                "quantity": cfg_stock.get("quantity", oi_map[sym]["quantity"]),
                "enabled":  cfg_stock.get("enabled", True),
            })
            kept_syms.add(sym)
        else:
            # Stock no longer in today's OI file — remove
            removed_syms.add(sym)

    # Step 5 — Add all remaining OI stocks (no cap)
    for sym in oi_symbols:
        if sym not in kept_syms:
            s = oi_map[sym]
            final_list.append({
                "symbol":   sym,
                "quantity": s["quantity"],
                "enabled":  True,
            })
            added_syms.add(sym)

    # Step 6 — Deduplicate and sort final list by OI change% desc
    seen_final = set()
    deduped_final = []
    for s in final_list:
        if s["symbol"] not in seen_final:
            seen_final.add(s["symbol"])
            deduped_final.append(s)
    final_list = deduped_final

    oi_rank = {sym: i for i, sym in enumerate(oi_symbols)}
    final_list.sort(key=lambda x: oi_rank.get(x["symbol"], 999))

    # Print summary table
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n   {'SYMBOL':<14} {'CHANGE%':>8} {'LTP':>9} {'QTY':>5} {'STATUS'}")
    print(f"   {'─'*55}")
    for stock in final_list:
        sym    = stock["symbol"]
        oi     = oi_map.get(sym, {})
        chg    = f"{oi.get('change_pct', 0):>+7.2f}%" if oi else "  N/A  "
        ltp    = f"₹{oi['ltp']:.2f}" if oi.get('ltp') else "    N/A"
        status = "🆕 NEW" if sym in added_syms else "✅ KEPT"
        print(f"   {sym:<14} {chg}  {ltp:>9}  {stock['quantity']:>4}  {status}")

    print(f"\n   ✅ Kept    : {len(kept_syms)} | 🆕 Added: {len(added_syms)} | ❌ Removed: {len(removed_syms)}")
    if removed_syms:
        print(f"   ❌ Removed : {', '.join(sorted(removed_syms))}")
    print(f"   📊 Total   : {len(final_list)} stocks (all qualifying)")

    # Save config
    note = f"{now} | top{MAX_STOCKS} by OI change% | {len(final_list)} stocks | {Path(filepath).name}"
    save_config(final_list, note)
    print(f"\n   💾 Config saved → {CONFIG_FILE}")

    # Reload live server
    reload_server()


# ── FILE WATCHER ──────────────────────────────────────────────
# Global date override — set via --date argument
DATE_OVERRIDE = None


def get_latest_file(folder: str) -> str | None:
    """
    Get the most recently modified OI spurts file.
    Tries today first — if not found falls back to yesterday.
    NSE file format: Spurts-in-OI-By-Underlying-DDMMYYYY.csv
    Use --date DDMMYYYY to override for testing.
    """
    from datetime import timedelta

    if DATE_OVERRIDE:
        dates_to_try = [DATE_OVERRIDE]
    else:
        today     = datetime.now()
        yesterday = today - timedelta(days=1)
        dates_to_try = [
            today.strftime("%d%m%Y"),
            yesterday.strftime("%d%m%Y"),
        ]

    for date in dates_to_try:
        pattern = os.path.join(folder, f"{FILE_PREFIX}*{date}*.csv")
        files   = glob.glob(pattern)
        if files:
            latest = max(files, key=os.path.getmtime)
            print(f"   📅 Using file date: {date} → {Path(latest).name}")
            return latest
        else:
            print(f"   📅 No files for {date} — trying previous day...")

    print(f"   ❌ No OI files found for today or yesterday")
    return None


def watch_folder(folder: str):
    print(f"\n{'═'*55}")
    print(f"  👁️  OI Spurts File Watcher")
    print(f"{'═'*55}")
    print(f"  Watching : {folder}")
    print(f"  Pattern  : {FILE_PREFIX}*.xlsx")
    print(f"  Min Δ%   : {MIN_CHANGE}%")
    print(f"  Max stks : {MAX_STOCKS}")
    print(f"  Reload   : {RELOAD_URL}")
    print(f"{'═'*55}")
    print(f"\n  Drop any '{FILE_PREFIX}*.xlsx' file into the folder.")
    print(f"  Config updates automatically.\n")

    last_processed = None

    while True:
        try:
            latest = get_latest_file(folder)

            if latest and latest != last_processed:
                # Wait briefly — file might still be copying
                time.sleep(1.5)
                # Check file is not still being written (size stable)
                size1 = os.path.getsize(latest)
                time.sleep(0.5)
                size2 = os.path.getsize(latest)
                if size1 != size2:
                    continue  # still copying
                update_from_file(latest)
                last_processed = latest

        except KeyboardInterrupt:
            print("\n\n👋 Watcher stopped.")
            sys.exit(0)
        except Exception as e:
            print(f"⚠️  Watcher error: {e}")

        time.sleep(POLL_INTERVAL)


# ── MAIN ──────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OI Spurts file watcher")
    parser.add_argument("--folder",     default=WATCH_FOLDER,
                        help=f"Folder to watch (default: {WATCH_FOLDER})")
    parser.add_argument("--min-change", type=float, default=0.0,
                        help="Min change%% (default 0 = no filter)")
    parser.add_argument("--max-stocks", type=int,   default=MAX_STOCKS,
                        help=f"Max stocks (default {MAX_STOCKS})")
    parser.add_argument("--run-once",   action="store_true",
                        help="Process latest file once and exit")
    parser.add_argument("--date",       default=None,
                        help="Date override for testing e.g. 20022026")
    args = parser.parse_args()

    MIN_CHANGE = args.min_change
    MAX_STOCKS = args.max_stocks

    # Apply date override globally so update_from_file can use it
    if args.date:
        import re
        if re.match(r'\d{8}', args.date):
            DATE_OVERRIDE = args.date
            print(f"📅 Date override: {DATE_OVERRIDE}")
        else:
            print("❌ Invalid date format — use DDMMYYYY e.g. 20022026")
            sys.exit(1)

    if args.run_once:
        # Process latest file immediately and exit
        latest = get_latest_file(args.folder)
        if latest:
            update_from_file(latest)
        else:
            print(f"No {FILE_PREFIX}*.csv files found in {args.folder}")
    else:
        watch_folder(args.folder)
