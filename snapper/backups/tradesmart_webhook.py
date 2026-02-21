"""
TradeSmart Automated Trading Engine v7.0
Flask webhook → Dhan API → NSE

Signal protocol (TradeSmart Pine):
  ENTRY LONG  : TS+ SYMBOL price
  ENTRY SHORT : TS- SYMBOL price
  EXIT TP HIT : TST SYMBOL
  EXIT SL HIT : TSS SYMBOL

Pine handles: signals, SL, TP, time window, Daily EMA filter, VWAP filter
Python handles: receive alert, place order, track position, P&L
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from dhanhq import dhanhq
import json, os, logging, traceback, threading, time as _time
import pandas as pd
from datetime import datetime
from collections import defaultdict
import pytz

# ── APP ───────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

# ── LOGGING ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(
            f"logs/tradesmart_{datetime.now().strftime('%Y%m%d')}.log", encoding="utf-8"
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ── CONSTANTS ─────────────────────────────────────────────────
IST = pytz.timezone("Asia/Kolkata")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
SIGNAL_COOLDOWN = 2  # seconds — duplicate guard per symbol

# ── STATE ─────────────────────────────────────────────────────
positions = {}  # symbol → {side, quantity, entry_price, entry_time, sl, tp}
trades = []  # list of all trade dicts today
total_pnl = 0.0
position_lock = threading.Lock()
last_signal_ts = defaultdict(float)

# ── GLOBALS SET AT STARTUP ────────────────────────────────────
STOCKS = {}  # symbol → {quantity}
SETTINGS = {}  # max_total_positions
dhan = None
sec_ids = {}  # symbol → security_id string


# ─────────────────────────────────────────────────────────────
# CONFIG + INIT
# ─────────────────────────────────────────────────────────────


def load_config():
    global STOCKS, SETTINGS
    with open("config/stocks_config.json") as f:
        cfg = json.load(f)
    STOCKS = {
        s["symbol"]: {"quantity": s["quantity"]}
        for s in cfg["stocks"]["list"]
        if s.get("enabled", True)
    }
    SETTINGS = cfg.get("trading_settings", {})
    logger.info(f"✅ Config loaded — {len(STOCKS)} stocks")


def load_security_ids():
    global sec_ids
    df = pd.read_excel("security_ids.xlsx")
    eq = df[
        (df["SEM_EXM_EXCH_ID"] == "NSE")
        & (df["SEM_INSTRUMENT_NAME"] == "EQUITY")
        & (df["SEM_SERIES"] == "EQ")
    ]
    sec_ids = {
        str(r["SEM_TRADING_SYMBOL"]).strip(): str(int(r["SEM_SMST_SECURITY_ID"]))
        for _, r in eq.iterrows()
        if str(r["SEM_TRADING_SYMBOL"]).strip() in STOCKS
    }
    logger.info(f"✅ Security IDs loaded — {len(sec_ids)}")


def init_dhan():
    global dhan
    with open("config/dhan_credentials.json") as f:
        creds = json.load(f)
    dhan = dhanhq(creds["client_id"], creds["access_token"])
    logger.info("✅ Dhan connected")


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────


def ist_now():
    return datetime.now(IST)


def ist_str():
    return ist_now().strftime("%Y-%m-%d %H:%M:%S IST")


def state_file():
    return f"data/tradesmart_{ist_now().strftime('%Y%m%d')}.json"


def save_state():
    try:
        with open(state_file(), "w") as f:
            json.dump(
                {"positions": positions, "trades": trades, "pnl": total_pnl},
                f,
                indent=2,
                default=str,
            )
    except Exception as e:
        logger.error(f"Save state error: {e}")


def load_state():
    global positions, trades, total_pnl
    try:
        with open(state_file()) as f:
            s = json.load(f)
        positions = s.get("positions", {})
        trades = s.get("trades", [])
        total_pnl = s.get("pnl", 0.0)
        logger.info(
            f"♻️  State restored — {len(positions)} positions, P&L ₹{total_pnl:.2f}"
        )
    except FileNotFoundError:
        logger.info("No saved state — starting fresh")


def max_positions_reached():
    return len(positions) >= SETTINGS.get("max_total_positions", 10)


# ─────────────────────────────────────────────────────────────
# ORDER
# ─────────────────────────────────────────────────────────────


def place_order(
    action: str, symbol: str, quantity: int, security_id: str
) -> dict | None:
    try:
        txn = dhan.BUY if action == "BUY" else dhan.SELL
        logger.info(f"📤 {action} {symbol} × {quantity}")
        resp = dhan.place_order(
            security_id=int(security_id),
            exchange_segment=dhan.NSE,
            transaction_type=txn,
            quantity=quantity,
            order_type=dhan.MARKET,
            product_type=dhan.INTRA,
            price=0,
        )
        if isinstance(resp, dict) and resp.get("status") in ("failure", "error"):
            logger.error(f"❌ Dhan rejected: {resp}")
            return None
        logger.info(f"📨 Order placed: {resp}")
        return resp
    except Exception as e:
        logger.error(f"❌ Order exception: {e}\n{traceback.format_exc()}")
        return None


# ─────────────────────────────────────────────────────────────
# SIGNAL PARSER
# ─────────────────────────────────────────────────────────────


def parse_signal(raw: str):
    """
    TradeSmart signal formats:
      TS+ SYMBOL price   → LONG entry
      TS- SYMBOL price   → SHORT entry
      TST SYMBOL         → TP hit  (exit long/short)
      TSS SYMBOL         → SL hit  (exit long/short)

    Returns (action, symbol, price, sl, tp, exit_type)
    action values: BUY | SELL | EXIT
    exit_type    : TPHIT | SLHIT | None
    """
    try:
        raw = raw.strip()
        parts = raw.split()
        if not parts:
            return None, None, None, None, None, None

        prefix = parts[0].upper()

        # ── LONG entry: TS+ SYMBOL price ──────────────────────
        if prefix == "TS+":
            if len(parts) < 2:
                return None, None, None, None, None, None
            symbol = parts[1].upper().split(":")[-1]
            price  = float(parts[2]) if len(parts) > 2 else None
            logger.info(f"📥 LONG entry | {symbol} @ {price}")
            return "BUY", symbol, price, None, None, None

        # ── SHORT entry: TS- SYMBOL price ─────────────────────
        elif prefix == "TS-":
            if len(parts) < 2:
                return None, None, None, None, None, None
            symbol = parts[1].upper().split(":")[-1]
            price  = float(parts[2]) if len(parts) > 2 else None
            logger.info(f"📥 SHORT entry | {symbol} @ {price}")
            return "SELL", symbol, price, None, None, None

        # ── TP hit: TST SYMBOL ─────────────────────────────────
        elif prefix == "TST":
            if len(parts) < 2:
                return None, None, None, None, None, None
            symbol = parts[1].upper().split(":")[-1]
            logger.info(f"📥 TP HIT exit | {symbol}")
            return "EXIT", symbol, None, None, None, "TPHIT"

        # ── SL hit: TSS SYMBOL ─────────────────────────────────
        elif prefix == "TSS":
            if len(parts) < 2:
                return None, None, None, None, None, None
            symbol = parts[1].upper().split(":")[-1]
            logger.info(f"📥 SL HIT exit | {symbol}")
            return "EXIT", symbol, None, None, None, "SLHIT"

        else:
            logger.warning(f"⚠️  Unknown signal prefix: {prefix} | raw: {raw}")
            return None, None, None, None, None, None

    except Exception as e:
        logger.error(f"Parse error: {e} | raw: {raw}")
        return None, None, None, None, None, None


# ─────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────


@app.route("/webhook", methods=["POST"])
def webhook():
    global total_pnl

    # Auth
    if WEBHOOK_SECRET:
        token = request.headers.get("X-Webhook-Token") or request.args.get("token", "")
        if token != WEBHOOK_SECRET:
            return jsonify({"error": "Unauthorized"}), 401

    raw = request.get_data(as_text=True).strip()
    logger.info(f"\n{'─'*50}\n📩 {raw}\n{'─'*50}")

    action, symbol, price, sl, tp, exit_type = parse_signal(raw)

    if not action or not symbol:
        return jsonify({"error": "Invalid signal", "raw": raw}), 400

    if symbol not in STOCKS:
        return jsonify({"status": "skipped", "reason": f"{symbol} not in config"})

    if symbol not in sec_ids:
        return jsonify({"error": f"No security ID for {symbol}"}), 400

    # Duplicate guard
    now = _time.time()
    if now - last_signal_ts[symbol] < SIGNAL_COOLDOWN:
        return jsonify({"status": "ignored", "reason": "Duplicate cooldown"})
    last_signal_ts[symbol] = now

    quantity = STOCKS[symbol]["quantity"]
    sec_id = sec_ids[symbol]

    with position_lock:

        # ── EXIT ─────────────────────────────────────────────
        if action == "EXIT":
            if symbol not in positions:
                logger.warning(f"EXIT ignored — no position for {symbol}")
                return jsonify({"status": "ignored", "reason": "No open position"})

            pos = positions[symbol]
            close_side = "SELL" if pos["side"] == "BUY" else "BUY"
            result = place_order(close_side, symbol, pos["quantity"], sec_id)

            if result:
                pnl = 0.0
                if pos.get("entry_price") and price:
                    pnl = (
                        (price - pos["entry_price"]) * pos["quantity"]
                        if pos["side"] == "BUY"
                        else (pos["entry_price"] - price) * pos["quantity"]
                    )
                    total_pnl += pnl

                logger.info(
                    f"{'💰' if pnl >= 0 else '💸'} {exit_type} | P&L ₹{pnl:.2f} | Day ₹{total_pnl:.2f}"
                )

                trades.append(
                    {
                        "time": ist_str(),
                        "symbol": symbol,
                        "type": f"EXIT_{exit_type}",
                        "side": close_side,
                        "quantity": pos["quantity"],
                        "entry_price": pos.get("entry_price"),
                        "exit_price": price,
                        "pnl": round(pnl, 2),
                    }
                )

                del positions[symbol]
                save_state()
                return jsonify(
                    {
                        "status": "exit_success",
                        "symbol": symbol,
                        "exit_type": exit_type,
                        "pnl": round(pnl, 2),
                    }
                )

            return jsonify({"error": "Exit order failed"}), 500

        # ── ENTRY ─────────────────────────────────────────────
        else:
            if symbol in positions:
                return jsonify({"status": "ignored", "reason": "Position already open"})

            if max_positions_reached():
                return jsonify(
                    {
                        "status": "skipped",
                        "reason": f"Max {SETTINGS.get('max_total_positions', 10)} positions reached",
                    }
                )

            result = place_order(action, symbol, quantity, sec_id)

            if result:
                positions[symbol] = {
                    "side": action,
                    "quantity": quantity,
                    "entry_price": price,
                    "entry_time": ist_str(),
                    "sl": sl,
                    "tp": tp,
                }
                trades.append(
                    {
                        "time": ist_str(),
                        "symbol": symbol,
                        "type": "ENTRY",
                        "side": action,
                        "quantity": quantity,
                        "price": price,
                        "sl": sl,
                        "tp": tp,
                    }
                )
                save_state()
                logger.info(f"✅ {action} {symbol} × {quantity} | SL={sl} TP={tp}")
                return jsonify(
                    {
                        "status": "entry_success",
                        "symbol": symbol,
                        "side": action,
                        "quantity": quantity,
                        "price": price,
                        "sl": sl,
                        "tp": tp,
                    }
                )

            return jsonify({"error": "Entry order failed"}), 500


@app.route("/status")
def status():
    return jsonify(
        {
            "time": ist_str(),
            "positions": positions,
            "position_count": len(positions),
            "trades_today": len(trades),
            "total_pnl": round(total_pnl, 2),
            "max_positions": SETTINGS.get("max_total_positions", 10),
            "stocks_count": len(STOCKS),
        }
    )


@app.route("/trades")
def get_trades():
    return jsonify(
        {
            "date": ist_now().strftime("%Y-%m-%d"),
            "trades": trades,
            "total_pnl": round(total_pnl, 2),
        }
    )


@app.route("/health")
def health():
    return jsonify(
        {"status": "ok", "time": ist_str(), "dhan": dhan is not None, "version": "v7.0"}
    )


@app.route("/reload-config", methods=["POST"])
def reload_config():
    load_config()
    load_security_ids()
    return jsonify({"status": "reloaded", "stocks": len(STOCKS)})


@app.route("/manual-override", methods=["POST"])
def manual_override():
    """Sync a manual trade placed directly in Dhan."""
    data = request.json or {}
    symbol = data.get("symbol", "").upper()
    action = data.get(
        "action", ""
    ).upper()  # OPENED_BUY | OPENED_SELL | CLOSED | CLEAR_ALL
    qty = data.get("quantity", STOCKS.get(symbol, {}).get("quantity", 0))
    price = data.get("price", 0)

    with position_lock:
        if action in ("OPENED_BUY", "OPENED_SELL"):
            side = "BUY" if action == "OPENED_BUY" else "SELL"
            positions[symbol] = {
                "side": side,
                "quantity": qty,
                "entry_price": price,
                "entry_time": ist_str(),
                "sl": None,
                "tp": None,
            }
            save_state()
            return jsonify({"status": "recorded", "symbol": symbol, "side": side})

        if action == "CLOSED":
            removed = positions.pop(symbol, None)
            save_state()
            return jsonify({"status": "closed", "was": removed})

        if action == "CLEAR_ALL":
            n = len(positions)
            positions.clear()
            save_state()
            return jsonify({"status": "cleared", "count": n})

    return jsonify({"error": "Invalid action"}), 400


@app.route("/clear-all", methods=["POST"])
def clear_all():
    with position_lock:
        n = len(positions)
        positions.clear()
        save_state()
    return jsonify({"status": "cleared", "count": n})


@app.route("/test-parse", methods=["POST"])
def test_parse():
    """
    Dry-run — parse a TradeSmart signal without placing any order.
    Test examples:
      curl -X POST https://your-ngrok/test-parse -d "TS+ RELIANCE 2450.50"
      curl -X POST https://your-ngrok/test-parse -d "TS- INFY 1800.00"
      curl -X POST https://your-ngrok/test-parse -d "TST RELIANCE"
      curl -X POST https://your-ngrok/test-parse -d "TSS INFY"
    """
    raw = request.get_data(as_text=True)
    action, symbol, price, sl, tp, exit_type = parse_signal(raw)
    pos = positions.get(symbol, {}) if symbol else {}
    return jsonify(
        {
            "raw":             raw,
            "action":          action,
            "symbol":          symbol,
            "price":           price,
            "exit_type":       exit_type,
            "in_config":       symbol in STOCKS       if symbol else False,
            "has_security_id": symbol in sec_ids      if symbol else False,
            "has_position":    symbol in positions     if symbol else False,
            "current_position": pos if pos else None,
            "would_execute":   action is not None and symbol in STOCKS and symbol in sec_ids,
        }
    )


# ── DASHBOARD ─────────────────────────────────────────────────
@app.route("/")
def dashboard():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TradeSmart</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Segoe UI',sans-serif;background:#0d0d0d;color:#eee;padding:16px}
  h1{color:#f0c040;margin-bottom:12px;font-size:1.4rem}
  h2{color:#aaa;margin:16px 0 8px;font-size:.95rem}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:16px}
  .card{background:#1a1a2e;border:1px solid #2a2a4a;border-radius:8px;padding:14px;text-align:center}
  .card h3{font-size:1.5rem;font-weight:700}
  .card p{font-size:.75rem;color:#888;margin-top:4px}
  .green{color:#00e676}.red{color:#ff1744}.yellow{color:#f0c040}
  .section{background:#111;border:1px solid #222;border-radius:8px;padding:14px;margin-bottom:12px}
  table{width:100%;border-collapse:collapse;font-size:.83rem}
  th,td{padding:7px 10px;border-bottom:1px solid #1a1a1a;text-align:left}
  th{background:#1a1a2e;color:#aaa}
  .b{background:#003300;color:#00e676;padding:2px 7px;border-radius:10px;font-size:.75rem;font-weight:700}
  .s{background:#330000;color:#ff1744;padding:2px 7px;border-radius:10px;font-size:.75rem;font-weight:700}
  #tick{font-size:.78rem;color:#666;margin-bottom:10px}
</style>
</head>
<body>
<h1>🎯 TradeSmart v7.0</h1>
<div id="tick">—</div>
<div class="grid" id="cards"></div>
<div class="section"><h2>📊 Open Positions</h2><div id="pos"></div></div>
<div class="section"><h2>📈 Trades Today</h2><div id="trd"></div></div>
<script>
const f=n=>n==null?'—':'₹'+Number(n).toFixed(2)
async function refresh(){
  const [s,t]=await Promise.all([fetch('/status').then(r=>r.json()),fetch('/trades').then(r=>r.json())])
  document.getElementById('tick').textContent=`${s.time} | Positions: ${s.position_count}/${s.max_positions}`
  const pc=s.total_pnl>=0?'green':'red'
  document.getElementById('cards').innerHTML=`
    <div class="card"><h3 class="yellow">${s.position_count}</h3><p>Open</p></div>
    <div class="card"><h3 class="yellow">${s.trades_today}</h3><p>Trades</p></div>
    <div class="card"><h3 class="${pc}">${f(s.total_pnl)}</h3><p>P&L</p></div>
    <div class="card"><h3 class="yellow">${s.stocks_count}</h3><p>Stocks</p></div>`
  const pos=s.positions
  if(Object.keys(pos).length){
    let h='<table><tr><th>Symbol</th><th>Side</th><th>Qty</th><th>Entry</th><th>SL</th><th>TP</th><th>Time</th></tr>'
    for(const[sym,p] of Object.entries(pos))
      h+=`<tr><td><b>${sym}</b></td><td><span class="${p.side=='BUY'?'b':'s'}">${p.side}</span></td>
      <td>${p.quantity}</td><td>${f(p.entry_price)}</td>
      <td class="red">${f(p.sl)}</td><td class="green">${f(p.tp)}</td>
      <td style="font-size:.72rem">${p.entry_time||'—'}</td></tr>`
    document.getElementById('pos').innerHTML=h+'</table>'
  } else document.getElementById('pos').innerHTML='<p style="color:#444;padding:8px">No open positions</p>'
  const tl=t.trades.slice(-30).reverse()
  if(tl.length){
    let h='<table><tr><th>Time</th><th>Symbol</th><th>Type</th><th>Side</th><th>Qty</th><th>Entry</th><th>Exit</th><th>P&L</th></tr>'
    for(const tr of tl){
      const pc=tr.pnl==null?'':tr.pnl>=0?'green':'red'
      h+=`<tr><td style="font-size:.72rem">${tr.time}</td><td><b>${tr.symbol}</b></td>
      <td>${tr.type}</td><td>${tr.side}</td><td>${tr.quantity}</td>
      <td>${f(tr.entry_price||tr.price)}</td><td>${f(tr.exit_price)}</td>
      <td class="${pc}">${tr.pnl!=null?f(tr.pnl):''}</td></tr>`
    }
    document.getElementById('trd').innerHTML=h+'</table>'
  } else document.getElementById('trd').innerHTML='<p style="color:#444;padding:8px">No trades yet</p>'
}
refresh(); setInterval(refresh,5000)
</script>
</body></html>"""


# ── STARTUP ───────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("=" * 55)
    logger.info("  TradeSmart Trading Engine v7.0")
    logger.info("=" * 55)
    load_config()
    init_dhan()
    load_security_ids()
    load_state()
    logger.info(f"📋 Stocks    : {len(STOCKS)}")
    logger.info(f"🔑 Sec IDs   : {len(sec_ids)}")
    logger.info(f"📍 Positions : {len(positions)}")
    logger.info(f"💰 P&L       : ₹{total_pnl:.2f}")
    logger.info(
        f"🔐 Auth      : {'ON' if WEBHOOK_SECRET else 'OFF — set WEBHOOK_SECRET'}"
    )
    logger.info(f"🌐 Dashboard : http://localhost:5000")
    logger.info("=" * 55)
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
