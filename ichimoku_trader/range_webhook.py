from flask import Flask, request, jsonify
from dhanhq import dhanhq
import json
import pandas as pd
import logging
from datetime import datetime, time
import os
import pytz
import traceback

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(
            f"logs/trading_{datetime.now().strftime('%Y%m%d')}.log",
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
current_positions = {}
daily_signals = {}
orders_today = []
total_pnl = 0

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
        
        logger.info(f"Loaded {len(stocks)} active stocks from config")
        return stocks, config.get('trading_settings', {})
    except Exception as e:
        logger.error(f"Error loading stock config: {e}")
        return {}, {}

STOCKS_CONFIG, TRADING_SETTINGS = load_stock_config()
STOCKS_LIST = list(STOCKS_CONFIG.keys())

# Load Dhan credentials
def load_credentials():
    try:
        with open('dhan_credentials.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading credentials: {e}")
        return None

# Load security IDs from Excel
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
            if symbol in STOCKS_LIST:
                security_ids[symbol] = security_id
                logger.info(f"Loaded security ID for {symbol}: {security_id}")
        
        logger.info(f"Loaded security IDs for {len(security_ids)} stocks")
        return security_ids
    except Exception as e:
        logger.error(f"Error loading security IDs: {e}")
        return {}

# Initialize Dhan client
creds = load_credentials()
if not creds:
    logger.error("Failed to load credentials - Exiting")
    exit(1)

dhan = dhanhq(creds['client_id'], creds['access_token'])
security_mapping = load_security_ids()

# Check if within trading hours
def is_trading_allowed():
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist).time()
    
    market_open_str = TRADING_SETTINGS.get('market_open', '09:30')
    market_close_str = TRADING_SETTINGS.get('market_close', '15:30')
    
    open_hour, open_min = map(int, market_open_str.split(':'))
    close_hour, close_min = map(int, market_close_str.split(':'))
    
    market_open = time(open_hour, open_min)
    market_close = time(close_hour, close_min)
    
    weekday = datetime.now(ist).weekday()
    if weekday >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    return market_open <= now_ist <= market_close

# Place order on Dhan
def place_dhan_order(action, symbol, quantity, security_id, signal_price=None):
    try:
        transaction_type = dhan.BUY if action == "BUY" else dhan.SELL
        product_type = getattr(dhan, TRADING_SETTINGS.get('product_type', 'INTRA'))
        order_type = getattr(dhan, TRADING_SETTINGS.get('order_type', 'MARKET'))
        
        logger.info(f"Placing {action} order for {symbol}, Qty: {quantity}, Signal Price: {signal_price}")
        
        order_response = dhan.place_order(
            security_id=int(security_id),
            exchange_segment=dhan.NSE,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type=order_type,
            product_type=product_type,
            price=0  # Market order
        )
        
        logger.info(f"Order response: {order_response}")
        
        # Track order
        orders_today.append({
            'time': datetime.now().isoformat(),
            'symbol': symbol,
            'action': action,
            'quantity': quantity,
            'signal_price': signal_price,
            'order_id': order_response.get('orderId', 'unknown'),
            'status': order_response.get('status', 'unknown')
        })
        
        return order_response
    except Exception as e:
        logger.error(f"Order placement error for {symbol}: {e}")
        logger.error(traceback.format_exc())
        return None

# Save state to file
def save_daily_state():
    try:
        today = datetime.now().date()
        state = {
            'date': today.isoformat(),
            'daily_signals': daily_signals.get(today, []),
            'current_positions': current_positions,
            'orders_today': orders_today,
            'total_pnl': total_pnl
        }
        
        filename = f"data/state_{today.strftime('%Y%m%d')}.json"
        with open(filename, 'w') as f:
            json.dump(state, f, indent=2, default=str)
        logger.info(f"State saved to {filename}")
    except Exception as e:
        logger.error(f"Error saving state: {e}")

# Load previous state
def load_daily_state():
    global current_positions, orders_today, daily_signals, total_pnl
    
    today = datetime.now().date()
    filename = f"data/state_{today.strftime('%Y%m%d')}.json"
    
    try:
        with open(filename, 'r') as f:
            saved_state = json.load(f)
            
        if 'current_positions' in saved_state:
            current_positions = saved_state['current_positions']
            logger.info(f"Restored {len(current_positions)} positions")
            
        if 'orders_today' in saved_state:
            orders_today = saved_state['orders_today']
            logger.info(f"Restored {len(orders_today)} orders")
            
        if 'daily_signals' in saved_state:
            daily_signals[today] = saved_state['daily_signals']
            
        if 'total_pnl' in saved_state:
            total_pnl = saved_state['total_pnl']
            
        return True
    except FileNotFoundError:
        logger.info("No previous state found for today")
        return False
    except Exception as e:
        logger.error(f"Error loading state: {e}")
        return False

# Parse webhook message - HANDLES {{ticker}} FORMAT
def parse_webhook_message(raw_data):
    """
    Parse TradingView webhook formats:
    1. "BUY HDFCLIFE" - Simple format
    2. "BUY NSE:HDFCLIFE at 725.50" - TradingView {{ticker}} format
    """
    try:
        parts = raw_data.strip().split()
        if len(parts) < 2:
            return None, None, None
        
        # Extract action (BUY/SELL)
        action = parts[0].upper()
        if action not in ['BUY', 'SELL']:
            logger.warning(f"Invalid action: {action}")
            return None, None, None
        
        # Extract symbol
        symbol = parts[1].upper()
        
        # Remove exchange prefix if present (NSE:SYMBOL -> SYMBOL)
        if ":" in symbol:
            exchange, symbol = symbol.split(":", 1)
            logger.info(f"Extracted symbol {symbol} from {exchange}:{symbol}")
        
        # Extract price if present (format: "at 725.50")
        price = None
        if len(parts) >= 4 and parts[2].lower() == "at":
            try:
                price = float(parts[3])
                logger.info(f"Extracted signal price: {price}")
            except ValueError:
                logger.warning(f"Could not parse price from: {parts[3]}")
        
        return action, symbol, price
    
    except Exception as e:
        logger.error(f"Error parsing webhook message: {e}")
        return None, None, None

# Main webhook endpoint
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    global daily_signals, current_positions
    
    try:
        # Get raw data from TradingView
        raw_data = request.get_data(as_text=True)
        logger.info(f"="*50)
        logger.info(f"Received webhook: {raw_data}")
        
        # Parse the message
        action, symbol, signal_price = parse_webhook_message(raw_data)
        
        if not action or not symbol:
            logger.error(f"Could not parse message: {raw_data}")
            return jsonify({'error': 'Invalid message format'}), 400
        
        # Validate symbol is in our config
        if symbol not in STOCKS_CONFIG:
            logger.warning(f"Symbol {symbol} not in config, skipping")
            return jsonify({
                'status': 'skipped', 
                'reason': f'{symbol} not in config',
                'configured_stocks': list(STOCKS_CONFIG.keys())
            })
        
        # Check if security ID exists
        if symbol not in security_mapping:
            logger.error(f"Security ID not found for {symbol}")
            return jsonify({'error': f'Security ID not found for {symbol}'}), 400
        
        # Get configured quantity
        quantity = STOCKS_CONFIG[symbol]['quantity']
        current_time = datetime.now()
        today = current_time.date()
        
        # Initialize daily signals for today
        if today not in daily_signals:
            daily_signals[today] = []
        
        # Check if trading is allowed
        if not is_trading_allowed():
            logger.warning("Signal received outside trading hours")
            return jsonify({
                'status': 'skipped', 
                'reason': 'Outside trading hours',
                'current_time': current_time.isoformat()
            })
        
        # Record the signal
        signal_record = {
            'time': current_time.isoformat(),
            'symbol': symbol,
            'action': action,
            'signal_price': signal_price
        }
        daily_signals[today].append(signal_record)
        
        # Process based on current position
        response_data = {
            'symbol': symbol,
            'action': action,
            'signal_price': signal_price
        }
        
        if symbol in current_positions:
            existing_position = current_positions[symbol]
            logger.info(f"Existing position: {existing_position}")
            
            # Check if opposite signal (need to square off)
            is_opposite = (
                (existing_position['side'] == 'BUY' and action == 'SELL') or
                (existing_position['side'] == 'SELL' and action == 'BUY')
            )
            
            if is_opposite:
                logger.info(f"OPPOSITE SIGNAL - Squaring off {existing_position['side']} position")
                
                # Square off existing position with ACTUAL quantity
                square_off_action = 'SELL' if existing_position['side'] == 'BUY' else 'BUY'
                square_off_qty = existing_position['quantity']
                
                logger.info(f"Square off: {square_off_action} {symbol} Qty:{square_off_qty}")
                order_result = place_dhan_order(
                    square_off_action, 
                    symbol, 
                    square_off_qty,
                    security_mapping[symbol],
                    signal_price
                )
                
                if order_result:
                    # Calculate P&L if entry price available
                    if 'entry_price' in existing_position and signal_price:
                        if existing_position['side'] == 'BUY':
                            pnl = (signal_price - existing_position['entry_price']) * square_off_qty
                        else:
                            pnl = (existing_position['entry_price'] - signal_price) * square_off_qty
                        logger.info(f"P&L for {symbol}: {pnl:.2f}")
                    
                    # Remove from current positions
                    current_positions.pop(symbol)
                    
                    # Re-enter with CONFIG quantity
                    if TRADING_SETTINGS.get('enable_reentry_after_squareoff', True):
                        logger.info(f"RE-ENTERING {action} position for {symbol}")
                        reentry_result = place_dhan_order(
                            action, 
                            symbol, 
                            quantity,  # Use config quantity for re-entry
                            security_mapping[symbol],
                            signal_price
                        )
                        
                        if reentry_result:
                            current_positions[symbol] = {
                                'side': action,
                                'quantity': quantity,
                                'entry_time': current_time.isoformat(),
                                'entry_price': signal_price,
                                'order_id': reentry_result.get('orderId', 'unknown'),
                                're_entry': True
                            }
                            response_data['status'] = 'squared_off_and_reentered'
                        else:
                            response_data['status'] = 'squared_off_only'
                    else:
                        response_data['status'] = 'squared_off'
            else:
                logger.info(f"Same direction signal for {symbol}, ignoring")
                response_data['status'] = 'ignored'
                response_data['reason'] = 'Same direction signal'
        else:
            # No existing position - open new
            logger.info(f"OPENING NEW {action} position for {symbol}")
            
            order_result = place_dhan_order(
                action, 
                symbol, 
                quantity, 
                security_mapping[symbol],
                signal_price
            )
            
            if order_result:
                current_positions[symbol] = {
                    'side': action,
                    'quantity': quantity,
                    'entry_time': current_time.isoformat(),
                    'entry_price': signal_price,
                    'order_id': order_result.get('orderId', 'unknown')
                }
                response_data['status'] = 'position_opened'
            else:
                response_data['status'] = 'order_failed'
        
        # Save state after each trade
        save_daily_state()
        
        response_data['positions_count'] = len(current_positions)
        logger.info(f"Response: {response_data}")
        logger.info(f"="*50)
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# Status endpoint
@app.route('/status')
def status():
    ist = pytz.timezone('Asia/Kolkata')
    current_ist = datetime.now(ist)
    
    # Format positions for display
    formatted_positions = {}
    for sym, pos in current_positions.items():
        formatted_positions[sym] = {
            'side': pos['side'],
            'quantity': pos['quantity'],
            'entry_time': pos.get('entry_time', 'Unknown'),
            'entry_price': pos.get('entry_price', 'N/A'),
            'is_reentry': pos.get('re_entry', False),
            'order_id': pos.get('order_id', 'Unknown')
        }
    
    return jsonify({
        'time': current_ist.strftime('%Y-%m-%d %H:%M:%S IST'),
        'trading_allowed': is_trading_allowed(),
        'positions': formatted_positions,
        'positions_count': len(current_positions),
        'today_signals': daily_signals.get(datetime.now().date(), []),
        'orders_today': len(orders_today),
        'stocks_configured': len(STOCKS_CONFIG),
        'stocks_list': list(STOCKS_CONFIG.keys())
    })

# Manual override endpoint
@app.route('/manual-override', methods=['POST'])
def manual_override():
    """
    Manually update position tracking
    Actions: OPENED_BUY, OPENED_SELL, CLOSED
    """
    try:
        data = request.json
        symbol = data.get('symbol', '').upper()
        action = data.get('action', '').upper()
        quantity = data.get('quantity', 0)
        price = data.get('price', None)
        
        current_time = datetime.now()
        
        if action == 'OPENED_BUY':
            current_positions[symbol] = {
                'side': 'BUY',
                'quantity': quantity,
                'entry_time': current_time.isoformat(),
                'entry_price': price,
                'order_id': 'MANUAL',
                'manual': True
            }
            logger.info(f"Manually set {symbol} as BUY position, qty: {quantity}, price: {price}")
            
        elif action == 'OPENED_SELL':
            current_positions[symbol] = {
                'side': 'SELL',
                'quantity': quantity,
                'entry_time': current_time.isoformat(),
                'entry_price': price,
                'order_id': 'MANUAL',
                'manual': True
            }
            logger.info(f"Manually set {symbol} as SELL position, qty: {quantity}, price: {price}")
            
        elif action == 'CLOSED':
            if symbol in current_positions:
                current_positions.pop(symbol)
                logger.info(f"Manually closed position for {symbol}")
            else:
                logger.warning(f"No position found for {symbol} to close")
                return jsonify({'error': f'No position for {symbol}'}), 404
        else:
            return jsonify({'error': 'Invalid action. Use OPENED_BUY, OPENED_SELL, or CLOSED'}), 400
        
        save_daily_state()
        return jsonify({
            'status': 'success',
            'action': action,
            'symbol': symbol,
            'current_positions': current_positions
        })
    except Exception as e:
        logger.error(f"Manual override error: {e}")
        return jsonify({'error': str(e)}), 500

# Clear all positions
@app.route('/clear-all', methods=['POST'])
def clear_all():
    """Clear all position tracking"""
    global current_positions, orders_today
    
    current_positions = {}
    orders_today = []
    save_daily_state()
    
    logger.info("Cleared all position tracking")
    return jsonify({
        'status': 'success', 
        'message': 'All positions cleared',
        'timestamp': datetime.now().isoformat()
    })

# Test webhook parsing
@app.route('/test-parse', methods=['POST'])
def test_parse():
    """Test webhook message parsing"""
    try:
        raw_data = request.get_data(as_text=True)
        action, symbol, price = parse_webhook_message(raw_data)
        
        return jsonify({
            'raw_message': raw_data,
            'parsed_action': action,
            'parsed_symbol': symbol,
            'parsed_price': price,
            'in_config': symbol in STOCKS_CONFIG if symbol else False,
            'has_security_id': symbol in security_mapping if symbol else False
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Health check
@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'time': datetime.now().isoformat(),
        'stocks_configured': len(STOCKS_CONFIG),
        'positions_open': len(current_positions),
        'orders_today': len(orders_today),
        'trading_enabled': is_trading_allowed()
    })

# Main execution
if __name__ == '__main__':
    logger.info("="*60)
    logger.info("Starting Trading System - Pine Script Compatible")
    logger.info("Webhook format: BUY/SELL {{ticker}} at {{close}}")
    logger.info("="*60)
    
    # Load previous state
    load_daily_state()
    
    # Display configuration
    logger.info(f"Configured stocks: {list(STOCKS_CONFIG.keys())}")
    logger.info(f"Trading hours: {TRADING_SETTINGS.get('market_open', '09:30')} - {TRADING_SETTINGS.get('market_close', '15:30')}")
    logger.info(f"Re-entry enabled: {TRADING_SETTINGS.get('enable_reentry_after_squareoff', True)}")
    
    app.run(host='0.0.0.0', port=5000, debug=False)