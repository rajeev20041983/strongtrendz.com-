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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(
            f"logs/donchian_{datetime.now().strftime('%Y%m%d')}.log",
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

# Create necessary directories
os.makedirs('logs', exist_ok=True)
os.makedirs('data', exist_ok=True)

# Global tracking variables
current_positions = {}  # {symbol: {side, quantity, entry_price, entry_time}}
daily_trades = []       # List of all trades today
total_pnl = 0          # Total P&L for the day

# Load configurations
def load_stock_config():
    try:
        with open('stocks_config.json', 'r') as f:
            config = json.load(f)
            
        stocks = {}
        for stock_data in config['stocks']['list']:
            if stock_data.get('enabled', True):
                stocks[stock_data['symbol']] = {
                    'quantity': stock_data.get('quantity', 10),
                    'timeframe': stock_data.get('timeframe', '5min')
                }
        
        logger.info(f"Loaded {len(stocks)} active stocks")
        return stocks, config.get('trading_settings', {})
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}, {}

STOCKS_CONFIG, TRADING_SETTINGS = load_stock_config()

# Load Dhan credentials
def load_credentials():
    try:
        with open('dhan_credentials.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading credentials: {e}")
        return None

# Load security IDs
def load_security_ids():
    try:
        df = pd.read_excel("security_ids.xlsx")
        equity_df = df[
            (df['SEM_EXM_EXCH_ID'] == 'NSE') & 
            (df['SEM_INSTRUMENT_NAME'] == 'EQUITY') &
            (df['SEM_SERIES'] == 'EQ')
        ]
        
        security_ids = {}
        for _, row in equity_df.iterrows():
            if pd.isna(row['SEM_TRADING_SYMBOL']) or pd.isna(row['SEM_SMST_SECURITY_ID']):
                continue
            symbol = str(row['SEM_TRADING_SYMBOL']).strip()
            security_id = str(int(row['SEM_SMST_SECURITY_ID'])).strip()
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

dhan = dhanhq(creds['client_id'], creds['access_token'])
security_mapping = load_security_ids()

# Market hours check
def is_trading_allowed():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    current_time = now.time()
    
    # Parse market hours
    open_time = datetime.strptime(TRADING_SETTINGS.get('market_open', '09:25'), '%H:%M').time()
    close_time = datetime.strptime(TRADING_SETTINGS.get('market_close', '15:30'), '%H:%M').time()
    
    # Check weekend
    if now.weekday() >= 5:
        return False
        
    return open_time <= current_time <= close_time

# Get IST time
def get_ist_time():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S IST')

# Place order
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
            price=0
        )
        
        logger.info(f"Order response: {response}")
        return response
        
    except Exception as e:
        logger.error(f"Order failed: {e}")
        return None

# Enhanced parse function for multiple formats
def parse_signal(raw_data):
    """Parse multiple signal formats:
    - Simple: BUY/SELL SYMBOL price
    - Explicit close: CLOSE BUY/SELL SYMBOL price
    - With NSE prefix: BUY NSE:SYMBOL price
    """
    try:
        parts = raw_data.strip().split()
        if len(parts) < 2:
            return None, None, None, None
        
        # Check for CLOSE command
        is_close = False
        if parts[0].upper() == "CLOSE":
            is_close = True
            parts = parts[1:]  # Remove CLOSE and reprocess
            
        action = parts[0].upper()
        if action not in ['BUY', 'SELL']:
            return None, None, None, None
            
        symbol = parts[1].upper()
        
        # Handle NSE: prefix
        if "NSE:" in symbol:
            symbol = symbol.replace("NSE:", "")
        elif ":" in symbol:
            _, symbol = symbol.split(":", 1)
            
        price = None
        # Handle both direct price and "at price" formats
        if len(parts) >= 3:
            try:
                # Try direct price format (BUY SYMBOL 100.50)
                price = float(parts[2])
            except:
                # Try "at" format (BUY SYMBOL at 100.50)
                if len(parts) >= 4 and parts[2].lower() == "at":
                    try:
                        price = float(parts[3])
                    except:
                        pass
                        
        logger.info(f"Parsed - Action:{action} Symbol:{symbol} Price:{price} IsClose:{is_close}")
        return action, symbol, price, is_close
        
    except Exception as e:
        logger.error(f"Parse error: {e}")
        return None, None, None, None

# Enhanced trade type determination
def get_trade_type(action, symbol, is_close=False):
    """Determine if signal is entry or exit
    Handles both simple BUY/SELL and explicit CLOSE commands
    """
    
    # If explicit CLOSE command
    if is_close:
        if symbol in current_positions:
            position = current_positions[symbol]
            # Validate CLOSE matches position
            # CLOSE BUY should close a long (BUY) position
            # CLOSE SELL should close a short (SELL) position
            if (action == "BUY" and position['side'] == "BUY") or \
               (action == "SELL" and position['side'] == "SELL"):
                return "EXIT"
            else:
                logger.warning(f"CLOSE {action} doesn't match position {position['side']} for {symbol}")
                return "EXIT"  # Still exit even if mismatch
        else:
            logger.warning(f"CLOSE command for {symbol} but no position exists")
            return "IGNORE"
    
    # Regular BUY/SELL logic (no CLOSE prefix)
    if symbol not in current_positions:
        return "ENTRY"
    
    position = current_positions[symbol]
    
    # Opposite direction = Exit
    if (position['side'] == 'BUY' and action == 'SELL') or \
       (position['side'] == 'SELL' and action == 'BUY'):
        return "EXIT"
    
    # Same direction = Check if re-entry is allowed
    if TRADING_SETTINGS.get('enable_reentry_after_squareoff', False):
        return "ENTRY"  # Allow re-entry even in same direction
    else:
        return "DUPLICATE"

# Save state
def save_state():
    try:
        state = {
            'timestamp': datetime.now().isoformat(),
            'positions': current_positions,
            'trades': daily_trades,
            'total_pnl': total_pnl
        }
        
        filename = f"data/donchian_{datetime.now().strftime('%Y%m%d')}.json"
        with open(filename, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Save failed: {e}")

# Load state
def load_state():
    global current_positions, daily_trades, total_pnl
    
    filename = f"data/donchian_{datetime.now().strftime('%Y%m%d')}.json"
    try:
        with open(filename, 'r') as f:
            state = json.load(f)
            current_positions = state.get('positions', {})
            daily_trades = state.get('trades', [])
            total_pnl = state.get('total_pnl', 0)
            logger.info(f"Loaded state: {len(current_positions)} positions")
            return True
    except FileNotFoundError:
        logger.info("No saved state for today")
        return False

# Main webhook endpoint
@app.route('/webhook', methods=['POST'])
def webhook():
    global current_positions, daily_trades, total_pnl
    
    try:
        raw_data = request.get_data(as_text=True)
        logger.info(f"\n{'='*50}")
        logger.info(f"Signal received: {raw_data}")
        
        # Enhanced parsing with is_close flag
        action, symbol, price, is_close = parse_signal(raw_data)
        
        if not action or not symbol:
            logger.error(f"Invalid signal format: {raw_data}")
            return jsonify({'error': 'Invalid signal format', 'raw': raw_data}), 400
            
        # Log signal type
        signal_type = "CLOSE" if is_close else "REGULAR"
        logger.info(f"Signal type: {signal_type} | Action: {action} | Symbol: {symbol} | Price: {price}")
        
        # Validate symbol
        if symbol not in STOCKS_CONFIG:
            logger.warning(f"{symbol} not configured in stocks_config.json")
            return jsonify({'status': 'skipped', 'reason': 'Symbol not configured'})
            
        if symbol not in security_mapping:
            logger.error(f"Security ID not found for {symbol}")
            return jsonify({'error': 'Security ID not found'}), 400
            
        # Check market hours
        if not is_trading_allowed():
            logger.info("Market closed - order skipped")
            return jsonify({'status': 'skipped', 'reason': 'Market closed', 'time': get_ist_time()})
            
        # Get trade type with enhanced logic
        trade_type = get_trade_type(action, symbol, is_close)
        quantity = STOCKS_CONFIG[symbol]['quantity']
        
        logger.info(f"Trade type: {trade_type} | Quantity: {quantity}")
        
        # Handle IGNORE case (CLOSE without position)
        if trade_type == "IGNORE":
            return jsonify({'status': 'ignored', 'reason': 'No position to close'})
        
        # Process based on trade type
        if trade_type == "ENTRY":
            # Open new position
            logger.info(f"ENTRY: Opening {action} position for {symbol} Qty:{quantity}")
            
            result = place_order(action, symbol, quantity, security_mapping[symbol], price)
            
            if result:
                current_positions[symbol] = {
                    'side': action,
                    'quantity': quantity,
                    'entry_price': price,
                    'entry_time': datetime.now().isoformat(),
                    'strategy': 'donchian'
                }
                
                daily_trades.append({
                    'time': datetime.now().isoformat(),
                    'symbol': symbol,
                    'action': action,
                    'type': 'ENTRY',
                    'quantity': quantity,
                    'price': price,
                    'raw_signal': raw_data
                })
                
                save_state()
                
                logger.info(f"✅ Entry successful: {symbol} {action}")
                return jsonify({
                    'status': 'entry_success',
                    'symbol': symbol,
                    'side': action,
                    'quantity': quantity,
                    'price': price
                })
            else:
                logger.error(f"❌ Entry failed: {symbol}")
                return jsonify({'status': 'entry_failed'})
                
        elif trade_type == "EXIT":
            # Close position
            position = current_positions[symbol]
            logger.info(f"EXIT: Closing {position['side']} position for {symbol}")
            
            # Determine actual order direction for exit
            if is_close:
                # CLOSE BUY means close a long position (so we SELL)
                # CLOSE SELL means close a short position (so we BUY)
                if action == "BUY" and position['side'] == "BUY":
                    exit_action = "SELL"
                elif action == "SELL" and position['side'] == "SELL":
                    exit_action = "BUY"
                else:
                    # Mismatch but still exit with opposite of current position
                    exit_action = "SELL" if position['side'] == "BUY" else "BUY"
                    logger.warning(f"CLOSE {action} mismatch with position {position['side']}, using {exit_action}")
            else:
                # Regular exit (opposite signal)
                exit_action = action
                
            logger.info(f"Exit order: {exit_action} {symbol} Qty:{position['quantity']}")
            
            result = place_order(exit_action, symbol, position['quantity'], security_mapping[symbol], price)
            
            if result:
                # Calculate P&L
                if position.get('entry_price') and price:
                    if position['side'] == 'BUY':
                        pnl = (price - position['entry_price']) * position['quantity']
                    else:
                        pnl = (position['entry_price'] - price) * position['quantity']
                    
                    total_pnl += pnl
                    logger.info(f"💰 P&L: ₹{pnl:.2f} | Total P&L: ₹{total_pnl:.2f}")
                else:
                    pnl = 0
                
                daily_trades.append({
                    'time': datetime.now().isoformat(),
                    'symbol': symbol,
                    'action': exit_action,
                    'type': 'EXIT',
                    'quantity': position['quantity'],
                    'price': price,
                    'pnl': pnl,
                    'raw_signal': raw_data
                })
                
                del current_positions[symbol]
                save_state()
                
                logger.info(f"✅ Exit successful: {symbol}")
                return jsonify({
                    'status': 'exit_success',
                    'symbol': symbol,
                    'pnl': pnl,
                    'total_pnl': total_pnl
                })
            else:
                logger.error(f"❌ Exit failed: {symbol}")
                return jsonify({'status': 'exit_failed'})
                
        else:  # DUPLICATE
            logger.info(f"DUPLICATE: Already in {current_positions[symbol]['side']} position")
            return jsonify({'status': 'ignored', 'reason': 'Already in position'})
            
    except Exception as e:
        logger.error(f"Error: {e}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

# Status endpoint
@app.route('/status')
def status():
    return jsonify({
        'time': get_ist_time(),
        'market_open': is_trading_allowed(),
        'positions': current_positions,
        'position_count': len(current_positions),
        'trades_today': len(daily_trades),
        'total_pnl': total_pnl,
        'configured_stocks': len(STOCKS_CONFIG),
        'stocks': list(STOCKS_CONFIG.keys())
    })

# Test endpoint for signal parsing
@app.route('/test', methods=['POST'])
def test():
    """Test signal parsing without execution"""
    raw_data = request.get_data(as_text=True)
    action, symbol, price, is_close = parse_signal(raw_data)
    
    if not action or not symbol:
        return jsonify({'error': 'Parse failed', 'raw': raw_data})
        
    trade_type = get_trade_type(action, symbol, is_close) if symbol in STOCKS_CONFIG else "N/A"
    
    return jsonify({
        'raw_signal': raw_data,
        'parsed': {
            'action': action,
            'symbol': symbol,
            'price': price,
            'is_close': is_close
        },
        'signal_type': 'CLOSE' if is_close else 'REGULAR',
        'trade_type': trade_type,
        'has_position': symbol in current_positions,
        'position': current_positions.get(symbol, {}),
        'configured': symbol in STOCKS_CONFIG,
        'has_security_id': symbol in security_mapping,
        'market_open': is_trading_allowed()
    })

# Health check
@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'time': get_ist_time(),
        'version': '2.0'  # Updated version for Donchian support
    })

# Dashboard endpoint
@app.route('/')
def dashboard():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Donchian Trading System</title>
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
                margin-bottom: 30px;
            }
            h2 {
                color: #555;
                margin-top: 30px;
                margin-bottom: 15px;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }
            .stat-label {
                font-size: 0.9em;
                opacity: 0.9;
                margin-bottom: 5px;
            }
            .stat-value {
                font-size: 1.8em;
                font-weight: bold;
            }
            table { 
                width: 100%; 
                border-collapse: collapse; 
                margin: 20px 0;
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            }
            th, td { 
                padding: 12px 15px; 
                text-align: left; 
            }
            th { 
                background: #667eea; 
                color: white;
                font-weight: 600;
            }
            tr:nth-child(even) {
                background: #f8f9fa;
            }
            tr:hover {
                background: #e9ecef;
            }
            .buy { color: #28a745; font-weight: bold; }
            .sell { color: #dc3545; font-weight: bold; }
            .profit { color: #28a745; font-weight: bold; }
            .loss { color: #dc3545; font-weight: bold; }
            .market-open { 
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                background: #28a745;
                color: white;
                font-weight: bold;
            }
            .market-closed {
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                background: #dc3545;
                color: white;
                font-weight: bold;
            }
            .no-data {
                text-align: center;
                padding: 40px;
                color: #999;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 Donchian Trading System v2.0</h1>
            
            <div id="status"></div>
            
            <div class="stats-grid" id="stats"></div>
            
            <h2>📊 Open Positions</h2>
            <div id="positions"></div>
            
            <h2>📈 Today's Trades</h2>
            <div id="trades"></div>
        </div>
        <script>
            function formatTime(timeStr) {
                if (!timeStr) return 'N/A';
                const date = new Date(timeStr);
                return date.toLocaleTimeString('en-IN');
            }
            
            function refresh() {
                fetch('/status').then(r => r.json()).then(data => {
                    // Status bar
                    document.getElementById('status').innerHTML = `
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <span style="font-size: 1.1em;">⏰ ${data.time}</span>
                            </div>
                            <div>
                                <span class="${data.market_open ? 'market-open' : 'market-closed'}">
                                    ${data.market_open ? '🟢 MARKET OPEN' : '🔴 MARKET CLOSED'}
                                </span>
                            </div>
                        </div>
                    `;
                    
                    // Stats grid
                    document.getElementById('stats').innerHTML = `
                        <div class="stat-card">
                            <div class="stat-label">Open Positions</div>
                            <div class="stat-value">${data.position_count}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Today's Trades</div>
                            <div class="stat-value">${data.trades_today}</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Total P&L</div>
                            <div class="stat-value ${data.total_pnl >= 0 ? '' : 'loss'}">
                                ₹${data.total_pnl.toFixed(2)}
                            </div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-label">Active Symbols</div>
                            <div class="stat-value">${data.configured_stocks}</div>
                        </div>
                    `;
                    
                    // Positions table
                    if (Object.keys(data.positions).length > 0) {
                        let posHtml = '<table><tr><th>Symbol</th><th>Side</th><th>Quantity</th><th>Entry Price</th><th>Entry Time</th></tr>';
                        for(let [sym, pos] of Object.entries(data.positions)) {
                            posHtml += `<tr>
                                <td><strong>${sym}</strong></td>
                                <td class="${pos.side.toLowerCase()}">${pos.side}</td>
                                <td>${pos.quantity}</td>
                                <td>₹${pos.entry_price || 'N/A'}</td>
                                <td>${formatTime(pos.entry_time)}</td>
                            </tr>`;
                        }
                        posHtml += '</table>';
                        document.getElementById('positions').innerHTML = posHtml;
                    } else {
                        document.getElementById('positions').innerHTML = '<div class="no-data">No open positions</div>';
                    }
                });
                
                // Fetch and display trades
                fetch('/trades').then(r => r.json()).then(data => {
                    if (data.trades && data.trades.length > 0) {
                        let tradesHtml = '<table><tr><th>Time</th><th>Symbol</th><th>Type</th><th>Action</th><th>Qty</th><th>Price</th><th>P&L</th></tr>';
                        data.trades.forEach(trade => {
                            tradesHtml += `<tr>
                                <td>${formatTime(trade.time)}</td>
                                <td><strong>${trade.symbol}</strong></td>
                                <td>${trade.type}</td>
                                <td class="${trade.action.toLowerCase()}">${trade.action}</td>
                                <td>${trade.quantity}</td>
                                <td>₹${trade.price || 'N/A'}</td>
                                <td class="${trade.pnl >= 0 ? 'profit' : 'loss'}">
                                    ${trade.pnl !== undefined ? '₹' + trade.pnl.toFixed(2) : '-'}
                                </td>
                            </tr>`;
                        });
                        tradesHtml += '</table>';
                        document.getElementById('trades').innerHTML = tradesHtml;
                    } else {
                        document.getElementById('trades').innerHTML = '<div class="no-data">No trades today</div>';
                    }
                }).catch(err => {
                    document.getElementById('trades').innerHTML = '<div class="no-data">No trades today</div>';
                });
            }
            
            refresh();
            setInterval(refresh, 5000);
        </script>
    </body>
    </html>
    '''

# Trades endpoint for dashboard
@app.route('/trades')
def get_trades():
    return jsonify({'trades': daily_trades})

# Clear positions endpoint (use with caution!)
@app.route('/clear', methods=['POST'])
def clear_positions():
    """Emergency clear all positions - USE WITH CAUTION"""
    global current_positions, daily_trades, total_pnl
    
    password = request.json.get('password') if request.json else None
    if password != "emergency123":  # Change this password
        return jsonify({'error': 'Unauthorized'}), 401
        
    old_positions = current_positions.copy()
    current_positions = {}
    save_state()
    
    return jsonify({
        'status': 'cleared',
        'cleared_positions': old_positions
    })

if __name__ == '__main__':
    logger.info("="*60)
    logger.info("DONCHIAN TRADING SYSTEM v2.0")
    logger.info("="*60)
    
    # Load previous state if exists
    load_state()
    
    # Display configuration
    logger.info(f"Configured Stocks: {len(STOCKS_CONFIG)}")
    for symbol, config in STOCKS_CONFIG.items():
        logger.info(f"  - {symbol}: Qty={config['quantity']}")
    
    logger.info(f"Market Hours: {TRADING_SETTINGS.get('market_open')} - {TRADING_SETTINGS.get('market_close')}")
    logger.info(f"Current Time: {get_ist_time()}")
    logger.info(f"Market Status: {'OPEN' if is_trading_allowed() else 'CLOSED'}")
    logger.info(f"Re-entry Enabled: {TRADING_SETTINGS.get('enable_reentry_after_squareoff', False)}")
    
    if current_positions:
        logger.info(f"Active Positions: {len(current_positions)}")
        for symbol, pos in current_positions.items():
            logger.info(f"  - {symbol}: {pos['side']} Qty={pos['quantity']}")
    
    logger.info("="*60)
    logger.info("Server starting on http://0.0.0.0:5000")
    logger.info("Dashboard available at http://localhost:5000")
    logger.info("="*60)
    
    app.run(host='0.0.0.0', port=5000, debug=False)