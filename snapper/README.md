# TradeSmart — Automated Trading System

End-to-end guide: OI Spurts → Stock Selection → Ngrok → Webhook → Dhan Orders

---

## System Overview

```
NSE OI File (manual download)
        ↓
watch_oi.py (file watcher)
        ↓
stocks_config.json (filtered stocks by OI change%)
        ↓
TradeSmart Pine Script (5min chart signals)
        ↓
TradingView Webhook Alerts
        ↓
Ngrok Tunnel (strongtrendz.ngrok-free.app)
        ↓
tradesmart.py (Flask webhook server)
        ↓
Dhan API → NSE Market Order
```

---

## Files

| File | Purpose |
|------|---------|
| `tradesmart.py` | Flask webhook server — receives signals, places Dhan orders |
| `watch_oi.py` | Watches Downloads for NSE OI files, updates stock config |
| `TradeSmart.pine` | Pine Script indicator for TradingView |
| `config/stocks_config.json` | Active stock list with quantities |
| `config/dhan_credentials.json` | Dhan API credentials |
| `security_ids.xlsx` | NSE security IDs from Dhan |

---

## One-Time Setup

### 1 — Install dependencies

```bash
pip install flask flask-cors dhanhq pandas openpyxl pytz schedule --break-system-packages
```

### 2 — Create credentials file

`config/dhan_credentials.json`:
```json
{
  "client_id": "YOUR_CLIENT_ID",
  "access_token": "YOUR_ACCESS_TOKEN"
}
```

> ⚠️ Dhan access token expires daily — refresh every morning at dhanhq.co → API section

### 3 — Add TradeSmart to TradingView

- Open Pine Editor → paste `TradeSmart.pine` → Save → Add to chart
- Set chart to **5 min** timeframe

### 4 — Configure Ngrok

```bash
ngrok http 5000 --domain=strongtrendz.ngrok-free.app
```

---

## OI Filter Rules — How Stocks Are Selected

Every time you drop a new NSE file, `watch_oi.py` applies progressive filters based on how many files have been downloaded so far that day.

### Filter Rules (get stricter with each file)

| Files Downloaded | Rules Active |
|-----------------|--------------|
| 1 file | No filtering — take all stocks |
| 2 files | Rule 1: exclude if OI dropped vs previous file OR dropped from peak |
| 3 files | Rule 1 + Rule 2: also exclude weak builds below 2% |
| 4+ files | Rule 1 + Rule 2 + Rule 3: must show consistent climb |

### Rule Detail

**Rule 1 — Drop filter (2+ files)**
Two checks:
- If OI change% is lower than the immediately previous file → excluded
- If stock dropped more than 0.5% from its peak across all files → excluded

```
SIEMENS: peak +4.15 → final +4.00 = drop 0.15  ✅ within 0.5% tolerance → KEEP
FORTIS:  peak +4.29 → final +3.74 = drop 0.55  ❌ exceeded 0.5%         → EXCLUDE
```

**Rule 2 — Weak build filter (3+ files)**
If OI change% is below 2% → excluded. Not enough conviction.

**Rule 3 — Consistency filter (4+ files)**
If stock had more down moves than up moves across all files → excluded.

### Index Futures Always Excluded
NIFTY, BANKNIFTY, MIDCPNIFTY, FINNIFTY, SENSEX, BANKEX, NIFTYNXT50

### Example Result — 8 files downloaded (9:00 to 9:15am)

```
ABB        +10.08%  ✅ strongest — consistent climb all 8 files
PERSISTENT  +4.96%  ✅ steady build every file
SIEMENS     +4.00%  ✅ minor dip within 0.5% tolerance
ONGC        +2.96%  ✅ slow but clean
FORTIS      +3.74%  ❌ peaked at 4.29 — dropped 0.55% from peak
INDUSINDBK  +1.50%  ❌ weak build below 2%
```

Final result: **11 high conviction stocks**

---

## TradingView Alert Setup

### 2 Alerts Per Stock Only

**Alert 1 — Entry (A1):**
- Condition → `TradeSmart` → **"Any alert() function call"**
- Message → **leave blank** (Pine sends automatically)
- Webhook → `https://strongtrendz.ngrok-free.app/webhook`
- Trigger → Once Per Bar Close

Pine sends automatically: `LONG|ABB|5923.45` or `SHORT|ABB|5923.45`

**Alert 2 — Exit (A2):**
- Condition → `TradeSmart` → **A2**
- Message → `{{ticker}}|{{close}}`
- Webhook → `https://strongtrendz.ngrok-free.app/webhook`
- Trigger → Once Per Bar Close

> 30 stocks × 2 alerts = 60 alerts — requires TradingView Pro+ plan (100 alert limit)

---

## Signal Flow

### LONG Signal
```
TradeSmart fires LONG on 5min candle close
        ↓
Pine sends: LONG|ABB|5923.45
        ↓
POST https://strongtrendz.ngrok-free.app/webhook
        ↓
Ngrok → localhost:5000/webhook
        ↓
Python checks:
  ABB in config?        ✅
  ABB already LONG?     → ignore duplicate
  ABB open SHORT?       → square off SHORT first → then BUY
  No position?          → BUY directly
        ↓
Dhan MARKET BUY ABB × qty
        ↓
NSE fills at best available price
        ↓
Position saved to state file
Dashboard updates
```

### SHORT Signal
Same as LONG but reversed — squares off any open LONG first, then enters SHORT.

### Exit Signal (TP or SL)
```
TradeSmart TP or SL fires
        ↓
TradingView sends: ABB|5960.00
        ↓
Python → no LONG/SHORT prefix → EXIT
        ↓
Squares off open ABB position at MARKET
        ↓
P&L calculated and logged
```

---

## Monday Morning Flow — Step by Step

### 8:50am — Refresh Dhan Token
1. Go to [dhanhq.co](https://dhanhq.co) → Login → My Account → API
2. Generate new access token
3. Open `config/dhan_credentials.json` → replace `access_token`
4. Save file

### 8:55am — Start All 3 Terminals

**Terminal 1 — Ngrok:**
```bash
ngrok http 5000 --domain=strongtrendz.ngrok-free.app
```

**Terminal 2 — Webhook server:**
```bash
cd ~/OneDrive/projects/strongtrendz.com-/snapper
py tradesmart.py
```

**Terminal 3 — OI watcher:**
```bash
cd ~/OneDrive/projects/strongtrendz.com-/snapper/scripts
py watch_oi.py --folder "C:/Users/PC/Downloads"
```

Leave all 3 running. Never close during market hours.

### 9:00am — Download File 1 from NSE
1. Go to [nseindia.com](https://nseindia.com) → Derivatives → OI Spurts
2. Download CSV
3. Terminal 3 detects within 10 seconds
4. Config updates — **1 file = no filters yet, all stocks loaded**

### 9:05am — Download File 2
Terminal 3 detects → **Rule 1 activates**
Stocks that dropped vs file 1 or from peak → removed

### 9:08am — Download File 3
Terminal 3 detects → **Rules 1+2 active**
Stocks below 2% also removed

### 9:10am — Download File 4
Terminal 3 detects → **Rules 1+2+3 all active**
Only consistent climbers remain

### 9:12am — Verify Config
```bash
curl https://strongtrendz.ngrok-free.app/status
```
Check stock list looks right. Edit `config/stocks_config.json` manually if needed.

### 9:13am — Set TradingView Alerts
For each stock in final config — create Alert 1 and Alert 2 as described above.

### 9:15am — Market Opens
Stop downloading new files. System runs fully automatically from here.

### During Market — Monitor
```
http://localhost:5000
```
Auto-refreshes every 5 seconds. Shows positions, trades, P&L.

---

## Manual Controls

### Reload config without restart
```bash
curl -X POST https://strongtrendz.ngrok-free.app/reload-config
```

### Check positions and P&L
```bash
curl https://strongtrendz.ngrok-free.app/status
```

### View today's trades
```bash
curl https://strongtrendz.ngrok-free.app/trades
```

### Health check
```bash
curl https://strongtrendz.ngrok-free.app/health
```

### Sync manually placed Dhan order
```bash
curl -X POST https://strongtrendz.ngrok-free.app/manual-override \
  -H "Content-Type: application/json" \
  -d '{"symbol": "RELIANCE", "action": "OPENED_BUY", "quantity": 8, "price": 1410.50}'
```

### Sync manually closed position
```bash
curl -X POST https://strongtrendz.ngrok-free.app/manual-override \
  -H "Content-Type: application/json" \
  -d '{"symbol": "RELIANCE", "action": "CLOSED"}'
```

### Emergency — clear all positions from Python state
```bash
curl -X POST https://strongtrendz.ngrok-free.app/clear-all
```

> This only clears Python memory — does NOT place orders in Dhan. Square off in Dhan first.

### Test signal without placing order
```bash
curl -X POST https://strongtrendz.ngrok-free.app/test-parse \
  -d "LONG|RELIANCE|1410"
```

---

## End of Day (3:15pm)

```bash
# Check all positions closed
curl https://strongtrendz.ngrok-free.app/status

# Square off any remaining in Dhan manually, then sync
curl -X POST https://strongtrendz.ngrok-free.app/clear-all

# Review trades
curl https://strongtrendz.ngrok-free.app/trades
```

---

## Daily Checklist

| Time | Action |
|------|--------|
| 8:50am | Refresh Dhan access token at dhanhq.co |
| 8:55am | Start Terminal 1 — Ngrok |
| 8:55am | Start Terminal 2 — tradesmart.py |
| 8:55am | Start Terminal 3 — watch_oi.py |
| 9:00am | Download first OI file from NSE |
| 9:05am | Download second OI file |
| 9:08am | Download third OI file |
| 9:10am | Download fourth OI file |
| 9:12am | Health check + verify config |
| 9:13am | Set TradingView alerts for today's stocks |
| 9:15am | Market opens — stop downloading — monitor dashboard |
| 3:15pm | Verify all positions closed |
| 3:20pm | Review P&L — clear state |

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `DH-901 Invalid Authentication` | Dhan token expired | Refresh token at dhanhq.co |
| `DH-906 Market is Closed` | NSE closed | Expected on weekends/holidays |
| `Entry order failed` | Check server terminal | See Dhan error code |
| `No Spurts-in-OI*.csv files found` | No today's file in Downloads | Download from NSE or check folder |
| `Reload returned 404/502` | Webhook server not running | Start tradesmart.py first |
| Config has fewer stocks than expected | Filter rules removing weak stocks | Normal — working correctly |
| `fatal: 'swing' does not appear to be a git repository` | Using branch name as remote | Use `git push origin swing` |

---

## Git Workflow

```bash
# Check branch
git branch

# Stage all changes
git add -A

# Commit
git commit -m "your message"

# Push to remote
git push origin swing

# If rejected (diverged) — force push your local version
git push origin swing --force
```

---

## Key Rules to Remember

1. **Dhan token refreshes daily** — do this first every morning
2. **Stop downloading new files after 9:14am** — lock in the stock list
3. **Do not manually edit config after 9:15** — positions may already be open
4. **Never close Terminal 1 (ngrok)** — TradingView alerts will stop reaching Python
5. **3:15pm hard stop** — square off everything before NSE closes at 3:30
6. **2 alerts per stock only** — A1 (entry) and A2 (exit)
7. **Market orders only** — fills instantly at best available price

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   NSE Website   │────▶│   watch_oi.py    │────▶│stocks_config.json│
│  OI Spurts CSV  │     │  (file watcher)  │     │  filtered stocks │
└─────────────────┘     └──────────────────┘     └────────┬─────────┘
                                                           │
┌─────────────────┐     ┌──────────────────┐              │
│   TradeSmart    │     │   TradingView    │              │
│  Pine Script    │────▶│ Webhook Alerts   │              │
│  (5min chart)   │     └────────┬─────────┘              │
└─────────────────┘              │                        │
                                 ▼                        │
                    ┌────────────────────────┐            │
                    │        Ngrok           │            │
                    │ strongtrendz.ngrok-    │            │
                    │    free.app            │            │
                    └────────┬───────────────┘            │
                             │                            │
                             ▼                            │
                    ┌────────────────────────┐            │
                    │     tradesmart.py      │◀───────────┘
                    │     Flask :5000        │
                    └────────┬───────────────┘
                             │
                             ▼
                    ┌────────────────────────┐
                    │       Dhan API         │
                    │   MARKET orders only   │
                    └────────┬───────────────┘
                             │
                             ▼
                    ┌────────────────────────┐
                    │    NSE Exchange        │
                    │   Instant fill         │
                    └────────────────────────┘
```
