from flask import Flask, request, jsonify
from flask_cors import CORS
from dhanhq import dhanhq
import json
import pandas as pd
import logging
from datetime import datetime, time
import os
import pytz
import traceback

app = Flask(__name__)
CORS(app)

# Create necessary directories FIRST
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

# Configure logging (AFTER creating directories)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            f"logs/range_{datetime.now().strftime('%Y%m%d')}.log", encoding="utf-8"
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger()

# Create necessary directories
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

# Global tracking variables
current_positions = {}  # {symbol: {side, quantity, entry_price, entry_time}}
daily_trades = []  # List of all trades today
total_pnl = 0  # Total P&L for the day


# Load configurations
def load_stock_config():
    try:
        with open("stocks_config.json", "r") as f:
            config = json.load(f)

        stocks = {}
        for stock_data in config["stocks"]["list"]:
            if stock_data.get("enabled", True):
                stocks[stock_data["symbol"]] = {
                    "quantity": stock_data.get("quantity", 10),
                    "timeframe": stock_data.get("timeframe", "5min"),
                }

        logger.info(f"Loaded {len(stocks)} active stocks")
        return stocks, config.get("trading_settings", {})
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}, {}


STOCKS_CONFIG, TRADING_SETTINGS = load_stock_config()


# Load Dhan credentials
def load_credentials():
    try:
        with open("dhan_credentials.json", "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading credentials: {e}")
        return None


# Load security IDs
def load_security_ids():
    try:
        df = pd.read_excel("security_ids.xlsx")
        equity_df = df[
            (df["SEM_EXM_EXCH_ID"] == "NSE")
            & (df["SEM_INSTRUMENT_NAME"] == "EQUITY")
            & (df["SEM_SERIES"] == "EQ")
        ]

        security_ids = {}
        for _, row in equity_df.iterrows():
            if pd.isna(row["SEM_TRADING_SYMBOL"]) or pd.isna(
                row["SEM_SMST_SECURITY_ID"]
            ):
                continue
            symbol = str(row["SEM_TRADING_SYMBOL"]).strip()
            security_id = str(int(row["SEM_SMST_SECURITY_ID"])).strip()
            if symbol in STOCKS_CONFIG:
                security_ids[symbol] = security_id

        logger.info(f"Loaded {len(security_ids)} security IDs")
        return security_ids
    except Exception as e:
        logger.error(f"Error loading security IDs: {e}")
        return {}


# Initialize Dhan
creds = load_credentials()
if not creds:
    logger.error("No credentials found")
    exit(1)

dhan = dhanhq(creds["client_id"], creds["access_token"])
security_mapping = load_security_ids()


# Check if trading is allowed
def is_trading_allowed():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    current_time = now.time()

    # Parse market hours from config
    open_time = datetime.strptime(
        TRADING_SETTINGS.get("market_open", "09:30"), "%H:%M"
    ).time()
    close_time = datetime.strptime(
        TRADING_SETTINGS.get("market_close", "15:30"), "%H:%M"
    ).time()

    # Check weekend
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False

    return open_time <= current_time <= close_time


# Get IST time
def get_ist_time():
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S IST")


# Place order on Dhan
def place_order(action, symbol, quantity, security_id, price=None):
    try:
        if not is_trading_allowed():
            logger.warning(f"Order blocked - Market closed: {action} {symbol}")
            return None

        transaction_type = dhan.BUY if action == "BUY" else dhan.SELL

        logger.info(f"Placing {action} order: {symbol} Qty:{quantity} Price:{price}")

        response = dhan.place_order(
            security_id=int(security_id),
            exchange_segment=dhan.NSE,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type=dhan.MARKET,
            product_type=dhan.INTRA,
            price=0,
        )

        logger.info(f"Order response: {response}")
        return response

    except Exception as e:
        logger.error(f"Order failed: {e}")
        return None


# Parse webhook message - handles all formats including DIVERGENCE
def parse_signal(raw_data):
    """
    Parse formats:
    1. BUY SYMBOL price - Open long position
    2. SELL SYMBOL price - Open short position
    3. BUY SYMBOL price PROFIT - Exit short with profit
    4. BUY SYMBOL price LOSS - Exit short with loss
    5. SELL SYMBOL price PROFIT - Exit long with profit
    6. SELL SYMBOL price LOSS - Exit long with loss
    7. BUY/SELL SYMBOL price DIVERGENCE[...] - 3/4 Divergence exit (close only)
    8. BUY/SELL SYMBOL price RFEXIT - Range Filter exit (close only, no new position)
    9. BUY/SELL SYMBOL price VOLEXIT - Volume Divergence exit (close only, RF recovery monitoring)
    10. BUY/SELL SYMBOL price STEXIT - SuperTrend exit (close only, RF recovery monitoring)
    """
    try:
        parts = raw_data.strip().split()
        if len(parts) < 2:
            return None, None, None, None

        action = parts[0].upper()
        if action not in ["BUY", "SELL"]:
            return None, None, None, None

        symbol = parts[1].upper()

        # Remove exchange prefix if present
        if ":" in symbol:
            _, symbol = symbol.split(":", 1)

        # Default values
        price = None
        exit_type = None

        # Check for DIVERGENCE exit with bracket details
        if "DIVERGENCE" in raw_data.upper():
            exit_type = "DIVERGENCE"
            # Try to get price (should be parts[2])
            try:
                price = float(parts[2])
            except:
                pass
        # Check if this is a P&L exit or any type of exit
        elif len(parts) >= 4 and parts[-1].upper() in [
            "PROFIT",
            "LOSS",
            "RFEXIT",
            "VOLEXIT",
            "STEXIT",
        ]:
            exit_type = parts[-1].upper()
            # Try to get price (should be parts[2])
            try:
                price = float(parts[2])
            except:
                pass
        else:
            # Regular signal - try to get price
            if len(parts) >= 3:
                try:
                    price = float(parts[2])
                except:
                    pass

        logger.info(
            f"Parsed - Action:{action} Symbol:{symbol} Price:{price} ExitType:{exit_type}"
        )
        return action, symbol, price, exit_type

    except Exception as e:
        logger.error(f"Parse error: {e}")
        return None, None, None, None


# Determine trade type
def get_trade_type(action, symbol, exit_type):
    """
    Determine if signal is:
    - P&L exit
    - Signal reversal (opposite direction)
    - New entry
    """
    # If it's any type of exit (PROFIT/LOSS/DIVERGENCE/RFEXIT/VOLEXIT/STEXIT)
    if exit_type:
        return "PL_EXIT"

    # Check current position
    if symbol not in current_positions:
        return "NEW_ENTRY"

    position = current_positions[symbol]

    # Check if opposite signal (reversal)
    if (position["side"] == "BUY" and action == "SELL") or (
        position["side"] == "SELL" and action == "BUY"
    ):
        return "REVERSAL"

    # Same direction - ignore
    return "IGNORE"


# Save state
def save_state():
    try:
        state = {
            "timestamp": datetime.now().isoformat(),
            "positions": current_positions,
            "trades": daily_trades,
            "total_pnl": total_pnl,
        }

        filename = f"data/range_{datetime.now().strftime('%Y%m%d')}.json"
        with open(filename, "w") as f:
            json.dump(state, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Save failed: {e}")


# Load state
def load_state():
    global current_positions, daily_trades, total_pnl

    filename = f"data/range_{datetime.now().strftime('%Y%m%d')}.json"
    try:
        with open(filename, "r") as f:
            state = json.load(f)
            current_positions = state.get("positions", {})
            daily_trades = state.get("trades", [])
            total_pnl = state.get("total_pnl", 0)
            logger.info(f"Loaded state: {len(current_positions)} positions")
            return True
    except FileNotFoundError:
        logger.info("No saved state for today")
        return False


# Main webhook endpoint
@app.route("/webhook", methods=["POST"])
def webhook():
    global current_positions, daily_trades, total_pnl

    try:
        raw_data = request.get_data(as_text=True)
        logger.info(f"\n{'='*50}")
        logger.info(f"Signal received: {raw_data}")

        # Parse the signal
        action, symbol, price, exit_type = parse_signal(raw_data)

        if not action or not symbol:
            logger.error(f"Invalid signal format: {raw_data}")
            return jsonify({"error": "Invalid signal format", "raw": raw_data}), 400

        # Validate symbol
        if symbol not in STOCKS_CONFIG:
            logger.warning(f"{symbol} not configured in stocks_config.json")
            return jsonify({"status": "skipped", "reason": "Symbol not configured"})

        if symbol not in security_mapping:
            logger.error(f"Security ID not found for {symbol}")
            return jsonify({"error": "Security ID not found"}), 400

        # Check market hours
        if not is_trading_allowed():
            logger.info("Market closed - order skipped")
            return jsonify(
                {"status": "skipped", "reason": "Market closed", "time": get_ist_time()}
            )

        quantity = STOCKS_CONFIG[symbol]["quantity"]
        trade_type = get_trade_type(action, symbol, exit_type)

        logger.info(f"Trade type: {trade_type} | Quantity: {quantity}")

        # Process based on trade type
        if trade_type == "PL_EXIT":
            # P&L exit or any divergence exit - ONLY close position, NEVER open new
            if symbol not in current_positions:
                logger.warning(
                    f"{exit_type} EXIT IGNORED: No position exists for {symbol}"
                )
                return jsonify(
                    {
                        "status": "ignored",
                        "reason": f"No position to exit on {exit_type}",
                        "symbol": symbol,
                        "signal_type": exit_type,
                    }
                )

            position = current_positions[symbol]

            # Determine exit reason
            if exit_type == "DIVERGENCE":
                # Extract divergence details if present
                divergence_details = ""
                if "[" in raw_data and "]" in raw_data:
                    start = raw_data.index("[")
                    end = raw_data.index("]")
                    divergence_details = raw_data[start + 1 : end]
                exit_reason = f"3/4 Divergence Exit [{divergence_details}]"
            elif exit_type == "RFEXIT":
                exit_reason = "Range Filter Exit"
            elif exit_type == "VOLEXIT":
                exit_reason = "Volume Divergence Exit"
            elif exit_type == "STEXIT":
                exit_reason = "SuperTrend Exit"
            else:
                exit_reason = f"P&L {exit_type}"

            logger.info(
                f"{exit_reason}: Closing {position['side']} position with {action}"
            )

            # Place exit order with ACTUAL position quantity
            result = place_order(
                action, symbol, position["quantity"], security_mapping[symbol], price
            )

            if result:
                # Calculate P&L
                pnl = 0
                if position.get("entry_price") and price:
                    if position["side"] == "BUY":
                        # Long position: profit = exit - entry
                        pnl = (price - position["entry_price"]) * position["quantity"]
                    else:
                        # Short position: profit = entry - exit
                        pnl = (position["entry_price"] - price) * position["quantity"]

                    total_pnl += pnl

                    # Log P&L with appropriate emoji
                    if exit_type == "DIVERGENCE":
                        logger.info(
                            f"🔄 3/4 Divergence Exit P&L: ₹{pnl:.2f} | Total: ₹{total_pnl:.2f}"
                        )
                    elif exit_type == "RFEXIT":
                        logger.info(
                            f"🔄 RF Exit P&L: ₹{pnl:.2f} | Total: ₹{total_pnl:.2f}"
                        )
                    elif exit_type == "VOLEXIT":
                        logger.info(
                            f"📊 Volume Exit P&L: ₹{pnl:.2f} | Total: ₹{total_pnl:.2f}"
                        )
                    elif exit_type == "STEXIT":
                        logger.info(
                            f"📈 SuperTrend Exit P&L: ₹{pnl:.2f} | Total: ₹{total_pnl:.2f}"
                        )
                    else:
                        emoji = "💰" if exit_type == "PROFIT" else "💸"
                        logger.info(
                            f"{emoji} P&L: ₹{pnl:.2f} ({exit_type}) | Total: ₹{total_pnl:.2f}"
                        )

                # Log the trade with proper classification
                trade_type_mapping = {
                    "DIVERGENCE": "3_4_DIVERGENCE_EXIT",
                    "VOLEXIT": "VOLUME_EXIT",
                    "STEXIT": "ST_EXIT",
                    "RFEXIT": "RF_EXIT",
                }

                daily_trades.append(
                    {
                        "time": datetime.now().isoformat(),
                        "symbol": symbol,
                        "action": action,
                        "type": trade_type_mapping.get(exit_type, "PL_EXIT"),
                        "exit_reason": exit_type,
                        "quantity": position["quantity"],
                        "entry_price": position.get("entry_price"),
                        "exit_price": price,
                        "position_side": position["side"],
                        "pnl": pnl,
                        "raw_signal": raw_data,
                    }
                )

                # Remove position - DO NOT open any new position
                del current_positions[symbol]
                save_state()

                logger.info(f"✅ {exit_reason} complete - Position CLOSED, now FLAT")

                # Check if recovery mode should be triggered (only for certain exit types)
                trigger_recovery = (
                    exit_type in ["VOLEXIT", "STEXIT"] and not exit_type == "DIVERGENCE"
                )

                return jsonify(
                    {
                        "status": f"{exit_type.lower()}_exit_success",
                        "symbol": symbol,
                        "exit_type": exit_type,
                        "closed_side": position["side"],
                        "exit_action": action,
                        "pnl": pnl,
                        "total_pnl": total_pnl,
                        "position_now": "FLAT",
                        "recovery_triggered": trigger_recovery,
                    }
                )
            else:
                logger.error(f"❌ {exit_reason} order failed for {symbol}")
                return jsonify({"status": f"{exit_type.lower()}_exit_failed"})

        elif trade_type == "REVERSAL":
            # Signal reversal - square off and reverse
            position = current_positions[symbol]
            logger.info(f"REVERSAL: Closing {position['side']} and opening {action}")

            # First square off existing position (action is already the exit action)
            result = place_order(
                action, symbol, position["quantity"], security_mapping[symbol], price
            )

            if result:
                # Calculate P&L on square off
                pnl = 0
                if position.get("entry_price") and price:
                    if position["side"] == "BUY":
                        pnl = (price - position["entry_price"]) * position["quantity"]
                    else:
                        pnl = (position["entry_price"] - price) * position["quantity"]

                    total_pnl += pnl
                    logger.info(f"Square off P&L: ₹{pnl:.2f}")

                # Log the exit
                daily_trades.append(
                    {
                        "time": datetime.now().isoformat(),
                        "symbol": symbol,
                        "action": action,
                        "type": "REVERSAL_EXIT",
                        "quantity": position["quantity"],
                        "entry_price": position.get("entry_price"),
                        "exit_price": price,
                        "pnl": pnl,
                        "raw_signal": raw_data,
                    }
                )

                # Now open new position in opposite direction IF enabled
                if TRADING_SETTINGS.get("enable_reentry_after_squareoff", True):
                    # For reversal, we need to enter with the SAME action that closed
                    # because it represents the new direction
                    result = place_order(
                        action, symbol, quantity, security_mapping[symbol], price
                    )

                    if result:
                        current_positions[symbol] = {
                            "side": action,  # New position direction
                            "quantity": quantity,
                            "entry_price": price,
                            "entry_time": datetime.now().isoformat(),
                            "strategy": "range_filter",
                        }

                        daily_trades.append(
                            {
                                "time": datetime.now().isoformat(),
                                "symbol": symbol,
                                "action": action,
                                "type": "REVERSAL_ENTRY",
                                "quantity": quantity,
                                "price": price,
                                "raw_signal": raw_data,
                            }
                        )

                        save_state()

                        return jsonify(
                            {
                                "status": "reversal_success",
                                "symbol": symbol,
                                "closed": position["side"],
                                "opened": action,
                                "pnl": pnl,
                            }
                        )
                else:
                    # Just close, don't reverse
                    del current_positions[symbol]
                    save_state()
                    return jsonify({"status": "squared_off_only", "pnl": pnl})

        elif trade_type == "NEW_ENTRY":
            # Fresh entry - no existing position
            logger.info(f"NEW ENTRY: Opening {action} position for {symbol}")

            result = place_order(
                action, symbol, quantity, security_mapping[symbol], price
            )

            if result:
                current_positions[symbol] = {
                    "side": action,
                    "quantity": quantity,
                    "entry_price": price,
                    "entry_time": datetime.now().isoformat(),
                    "strategy": "range_filter",
                }

                daily_trades.append(
                    {
                        "time": datetime.now().isoformat(),
                        "symbol": symbol,
                        "action": action,
                        "type": "ENTRY",
                        "quantity": quantity,
                        "price": price,
                        "raw_signal": raw_data,
                    }
                )

                save_state()

                logger.info(f"✅ Entry successful: {symbol} {action}")
                return jsonify(
                    {
                        "status": "entry_success",
                        "symbol": symbol,
                        "side": action,
                        "quantity": quantity,
                        "price": price,
                    }
                )

        else:  # IGNORE
            logger.info(f"Signal ignored - same direction as existing position")
            return jsonify({"status": "ignored", "reason": "Same direction"})

    except Exception as e:
        logger.error(f"Error: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


# Status endpoint
@app.route("/status")
def status():
    return jsonify(
        {
            "time": get_ist_time(),
            "market_open": is_trading_allowed(),
            "positions": current_positions,
            "position_count": len(current_positions),
            "trades_today": len(daily_trades),
            "total_pnl": total_pnl,
            "configured_stocks": len(STOCKS_CONFIG),
            "stocks": list(STOCKS_CONFIG.keys()),
            "settings": {
                "pl_target": "0.75%",
                "pl_stoploss_long": "2.0%",
                "pl_stoploss_short": "2.0%",
                "divergence_exit": "3/4 indicators",
                "reentry_enabled": TRADING_SETTINGS.get(
                    "enable_reentry_after_squareoff", True
                ),
            },
        }
    )


# Test endpoint
@app.route("/test", methods=["POST"])
def test():
    """Test signal parsing without execution"""
    raw_data = request.get_data(as_text=True)
    action, symbol, price, exit_type = parse_signal(raw_data)

    if not action or not symbol:
        return jsonify({"error": "Parse failed", "raw": raw_data})

    trade_type = (
        get_trade_type(action, symbol, exit_type) if symbol in STOCKS_CONFIG else "N/A"
    )

    # Simulate what would happen
    position = current_positions.get(symbol, {})
    expected_behavior = "N/A"

    if trade_type == "PL_EXIT":
        if symbol in current_positions:
            exit_desc = {
                "DIVERGENCE": "3/4 Divergence exit",
                "RFEXIT": "Range Filter exit",
                "VOLEXIT": "Volume Divergence exit",
                "STEXIT": "SuperTrend exit",
                "PROFIT": "Profit target exit",
                "LOSS": "Stop loss exit",
            }.get(exit_type, f"{exit_type} exit")
            expected_behavior = f"Would close {position['side']} position with {action} order ({exit_desc})"
        else:
            expected_behavior = f"Would be ignored - no position to exit on {exit_type}"
    elif trade_type == "REVERSAL":
        expected_behavior = f"Would close {position['side']} and open {action}"
    elif trade_type == "NEW_ENTRY":
        expected_behavior = f"Would open new {action} position"
    elif trade_type == "IGNORE":
        expected_behavior = "Would be ignored - same direction"

    return jsonify(
        {
            "raw_signal": raw_data,
            "parsed": {
                "action": action,
                "symbol": symbol,
                "price": price,
                "exit_type": exit_type,
            },
            "trade_type": trade_type,
            "has_position": symbol in current_positions,
            "position": position,
            "expected_behavior": expected_behavior,
            "configured": symbol in STOCKS_CONFIG,
            "has_security_id": symbol in security_mapping,
            "market_open": is_trading_allowed(),
        }
    )


# Health check
@app.route("/health")
def health():
    return jsonify(
        {
            "status": "healthy",
            "time": get_ist_time(),
            "version": "Range Filter with 3/4 Divergence Exit - v3.0",
        }
    )


# Dashboard
@app.route("/")
def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>RF+VST+ST Smart Trading with 3/4 Exit</title>
        <style>
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                margin: 0; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container { 
                max-width: 1400px; 
                margin: auto; 
                background: white; 
                padding: 30px; 
                border-radius: 15px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }
            h1 { 
                color: #333; 
                border-bottom: 3px solid #667eea; 
                padding-bottom: 15px;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }
            .stat-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
            }
            table { 
                width: 100%; 
                border-collapse: collapse; 
                margin: 20px 0;
            }
            th, td { 
                padding: 12px; 
                text-align: left; 
                border-bottom: 1px solid #ddd;
            }
            th { 
                background: #667eea; 
                color: white;
            }
            .buy { color: #28a745; font-weight: bold; }
            .sell { color: #dc3545; font-weight: bold; }
            .profit { color: #28a745; }
            .loss { color: #dc3545; }
            .trade-entry { background: #e8f5e9; }
            .trade-exit { background: #ffebee; }
            .trade-reversal { background: #fff3e0; }
            .divergence-exit { background: #fce4ec; }
            .volume-exit { background: #e3f2fd; }
            .st-exit { background: #f3e5f5; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 RF+VST+ST Trading with 3/4 Divergence Exit</h1>
            <div id="status"></div>
            <div class="stats-grid" id="stats"></div>
            <h2>📊 Open Positions</h2>
            <div id="positions"></div>
            <h2>📈 Today's Trades</h2>
            <div id="trades"></div>
        </div>
        <script>
            function refresh() {
                fetch('/status').then(r => r.json()).then(data => {
                    document.getElementById('status').innerHTML = `
                        <p>⏰ ${data.time} | Market: ${data.market_open ? '🟢 OPEN' : '🔴 CLOSED'}</p>
                        <p>Settings: Target ${data.settings.pl_target} | Stop Long ${data.settings.pl_stoploss_long} | Stop Short ${data.settings.pl_stoploss_short} | Divergence Exit: ${data.settings.divergence_exit}</p>
                    `;
                    
                    const pnlColor = data.total_pnl >= 0 ? '#28a745' : '#dc3545';
                    document.getElementById('stats').innerHTML = `
                        <div class="stat-card">
                            <h3>${data.position_count}</h3>
                            <p>Open Positions</p>
                        </div>
                        <div class="stat-card">
                            <h3>${data.trades_today}</h3>
                            <p>Trades Today</p>
                        </div>
                        <div class="stat-card" style="background: ${pnlColor};">
                            <h3>₹${data.total_pnl.toFixed(2)}</h3>
                            <p>Total P&L</p>
                        </div>
                        <div class="stat-card">
                            <h3>${data.configured_stocks}</h3>
                            <p>Active Stocks</p>
                        </div>
                    `;
                    
                    if (Object.keys(data.positions).length > 0) {
                        let html = '<table><tr><th>Symbol</th><th>Side</th><th>Qty</th><th>Entry</th><th>Time</th></tr>';
                        for(let [sym, pos] of Object.entries(data.positions)) {
                            const entryTime = pos.entry_time ? new Date(pos.entry_time).toLocaleTimeString() : 'N/A';
                            html += `<tr>
                                <td>${sym}</td>
                                <td class="${pos.side.toLowerCase()}">${pos.side}</td>
                                <td>${pos.quantity}</td>
                                <td>₹${pos.entry_price || 'N/A'}</td>
                                <td>${entryTime}</td>
                            </tr>`;
                        }
                        html += '</table>';
                        document.getElementById('positions').innerHTML = html;
                    } else {
                        document.getElementById('positions').innerHTML = '<p>No open positions</p>';
                    }
                });
            }
            refresh();
            setInterval(refresh, 5000);
        </script>
    </body>
    </html>
    """


@app.route("/manual-override", methods=["POST"])
def manual_override():
    """Manually update position tracking"""
    try:
        data = request.json
        symbol = data.get("symbol", "").upper()
        action = data.get("action", "").upper()

        if action == "CLOSE":
            if symbol in current_positions:
                old_position = current_positions.pop(symbol)
                save_state()
                logger.info(f"Manually closed position for {symbol}")
                return jsonify(
                    {
                        "status": "success",
                        "message": f"{symbol} position closed",
                        "was": old_position,
                    }
                )
            else:
                return jsonify({"error": f"No position for {symbol}"}), 404

        elif action == "CLEAR_ALL":
            count = len(current_positions)
            current_positions.clear()
            save_state()
            return jsonify(
                {"status": "success", "message": f"Cleared {count} positions"}
            )

        return jsonify({"error": "Invalid action. Use CLOSE or CLEAR_ALL"}), 400

    except Exception as e:
        logger.error(f"Manual override error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("RF+VST+ST TRADING WITH 3/4 DIVERGENCE EXIT")
    logger.info("=" * 60)

    # Load previous state
    load_state()

    # Display configuration
    logger.info(f"Configured Stocks: {len(STOCKS_CONFIG)}")
    for symbol, config in STOCKS_CONFIG.items():
        logger.info(f"  - {symbol}: Qty={config['quantity']}")

    logger.info(
        f"Market Hours: {TRADING_SETTINGS.get('market_open')} - {TRADING_SETTINGS.get('market_close')}"
    )
    logger.info(f"Current Time: {get_ist_time()}")
    logger.info(f"Market Status: {'OPEN' if is_trading_allowed() else 'CLOSED'}")
    logger.info(
        f"Re-entry: {TRADING_SETTINGS.get('enable_reentry_after_squareoff', True)}"
    )
    logger.info("3/4 Divergence Exit: ENABLED")

    if current_positions:
        logger.info(f"Active Positions: {len(current_positions)}")
        for symbol, pos in current_positions.items():
            logger.info(f"  - {symbol}: {pos['side']} Qty={pos['quantity']}")

    logger.info("=" * 60)
    logger.info("Supported Exit Types:")
    logger.info("  🔄 DIVERGENCE - 3/4 Indicator Divergence Exit")
    logger.info("  📊 VOLEXIT - Volume Divergence (triggers recovery)")
    logger.info("  📈 STEXIT - SuperTrend Divergence (triggers recovery)")
    logger.info("  🔄 RFEXIT - Range Filter Exit (complete reset)")
    logger.info("  💰 PROFIT - Profit Target Hit")
    logger.info("  💸 LOSS - Stop Loss Hit")
    logger.info("=" * 60)
    logger.info("Server starting on http://0.0.0.0:5000")
    logger.info("Dashboard: http://localhost:5000")
    logger.info("=" * 60)

    app.run(host="0.0.0.0", port=5000, debug=False)
