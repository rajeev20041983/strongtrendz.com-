from flask import Flask, request, jsonify
from dhanhq import dhanhq
import json
import pandas as pd
import logging
from datetime import datetime, time, timedelta
import os
import pytz

app = Flask(__name__)

# Configure logging with UTF-8 encoding to avoid character issues
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(
            f"logs/ichimoku_{datetime.now().strftime('%Y%m%d')}.log",
            encoding='utf-8'  # Add UTF-8 encoding for file handler
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

# Create logs directory
os.makedirs('logs', exist_ok=True)

# Load stock configuration from JSON file
def load_stock_config():
    try:
        with open('stocks_config.json', 'r') as f:
            config = json.load(f)
            
        # Extract enabled stocks with their quantities
        stocks = {}
        for stock_data in config['stocks_open_interest']['stocks']:
            if stock_data.get('enabled', True):
                stocks[stock_data['symbol']] = {
                    'quantity': stock_data.get('quantity', 10)
                }
        
        logger.info(f"Loaded {len(stocks)} active stocks from config")
        return stocks, config.get('trading_settings', {}), config.get('stocks_open_interest', {})
    except Exception as e:
        logger.error(f"Error loading stock config: {e}")
        # Fallback to default if config file is missing
        return {"HDFCBANK": {'quantity': 10}}, {}, {}

# Load configuration
STOCKS_CONFIG, TRADING_SETTINGS, STOCKS_INFO = load_stock_config()
STOCKS_OPEN_INTEREST = list(STOCKS_CONFIG.keys())  # Create list of stock symbols for compatibility

# Global tracking
daily_signals = {}
current_positions = {}

# Load Dhan credentials
def load_credentials():
    try:
        with open('dhan_credentials.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading credentials: {e}")
        return None

# Load security IDs - NOW ONLY FOR OUR TARGET STOCKS
def load_security_ids():
    try:
        logger.info("Loading security IDs from Excel file...")
        
        # Read the Excel file
        df = pd.read_excel("security_ids.xlsx")
        logger.info(f"Loaded {len(df)} total records from Excel")
        
        # Filter for NSE Equity instruments only
        equity_df = df[
            (df['SEM_EXM_EXCH_ID'] == 'NSE') & 
            (df['SEM_INSTRUMENT_NAME'] == 'EQUITY') &
            (df['SEM_SERIES'] == 'EQ')
        ]
        logger.info(f"Filtered to {len(equity_df)} NSE equity records")
        
        # Create security mapping - ONLY FOR OUR TARGET STOCKS
        security_ids = {}
        
        for _, row in equity_df.iterrows():
            if pd.isna(row['SEM_TRADING_SYMBOL']) or pd.isna(row['SEM_SMST_SECURITY_ID']):
                continue
                
            symbol = str(row['SEM_TRADING_SYMBOL']).strip()
            security_id = str(int(row['SEM_SMST_SECURITY_ID'])).strip()
            
            # ONLY add to mapping if it's in our target list
            if symbol in STOCKS_OPEN_INTEREST:
                security_ids[symbol] = security_id
            
        logger.info(f"Created security mapping with {len(security_ids)} symbols from our target list")
        
        # Check our target stocks availability
        found_count = 0
        missing_stocks = []
        
        logger.info(f"Checking availability of our {len(STOCKS_OPEN_INTEREST)} target stocks:")
        for stock in STOCKS_OPEN_INTEREST:
            if stock in security_ids:
                # Use simple text instead of Unicode symbols
                logger.info(f"[FOUND] {stock}: {security_ids[stock]}")
                found_count += 1
            else:
                logger.warning(f"[MISSING] {stock}: NOT FOUND")
                missing_stocks.append(stock)
        
        logger.info(f"Stock availability: {found_count}/{len(STOCKS_OPEN_INTEREST)} found")
        
        if missing_stocks:
            logger.warning(f"Missing stocks: {missing_stocks}")
        
        return security_ids
        
    except Exception as e:
        logger.error(f"Error loading security IDs: {e}")
        return {}

# Initialize
creds = load_credentials()
if not creds:
    logger.error("Failed to load credentials")
    exit(1)

dhan = dhanhq(creds['client_id'], creds['access_token'])
logger.info("Dhan client initialized")

security_mapping = load_security_ids()

@app.route('/ichimoku-alert', methods=['POST'])
def handle_ichimoku_alert():
    global daily_signals, current_positions
    
    try:
        # Parse TradingView webhook
        data = request.json
        alert_message = data.get('message', '')
        
        # Parse alert message - now supports four actions:
        # "LONG HDFCBANK" - Open long position
        # "SHORT HDFCBANK" - Open short position  
        # "CLOSE_LONG HDFCBANK" - Close long position
        # "CLOSE_SHORT HDFCBANK" - Close short position
        parts = alert_message.split()
        if len(parts) < 2:
            return jsonify({"error": "Invalid message format"})
        
        action = parts[0].upper()  # BUY, SELL, LONG, SHORT, CLOSE_LONG, or CLOSE_SHORT
        symbol = parts[1].upper()  # Stock symbol
        
        # Convert old format to new format for compatibility
        if action == "BUY":
            # BUY can mean either open long or close short
            if symbol in current_positions and current_positions[symbol].get('action') == 'SHORT':
                action = "CLOSE_SHORT"
                logger.info(f"BUY interpreted as CLOSE_SHORT (closing existing short)")
            else:
                action = "LONG"
                logger.info(f"BUY interpreted as LONG (opening new position)")
        elif action == "SELL":
            # SELL can mean either close long or open short
            if symbol in current_positions and current_positions[symbol].get('action') == 'LONG':
                action = "CLOSE_LONG"
                logger.info(f"SELL interpreted as CLOSE_LONG (closing existing long)")
            else:
                action = "SHORT"
                logger.info(f"SELL interpreted as SHORT (opening new position)")
        
        # Check if stock is in our config
        if symbol not in STOCKS_CONFIG:
            logger.warning(f"Signal for {symbol} not in our open interest stock list")
            return jsonify({"status": "skipped", "reason": "Stock not in config"})
        
        # Get quantity from config
        quantity = STOCKS_CONFIG[symbol]['quantity']
        logger.info(f"Using config quantity: {quantity}")
        
        current_time = datetime.now()
        logger.info(f"Ichimoku Signal: {action} {symbol} {quantity} shares")
        
        # Market hours check with IST
        if not is_market_hours():
            ist = pytz.timezone('Asia/Kolkata')
            current_ist_time = datetime.now(ist).strftime("%H:%M:%S IST")
            logger.info(f"Signal received outside market hours: {action} {symbol} at {current_ist_time}")
            return jsonify({"status": "skipped", "reason": "Market closed", "current_time_ist": current_ist_time})
        
        # Track daily signals
        today = current_time.date()
        if today not in daily_signals:
            daily_signals[today] = []
        
        # Position management logic
        if action == "CLOSE_LONG":
            # Close long position - verify we have a long position
            if symbol not in current_positions:
                logger.warning(f"CLOSE_LONG signal but NO position exists for {symbol} - REJECTING to prevent unwanted SELL")
                return jsonify({"status": "skipped", "reason": "No position exists to close"})
            elif current_positions[symbol]['action'] != 'LONG':
                logger.warning(f"CLOSE_LONG signal but position is {current_positions[symbol]['action']} not LONG - REJECTING")
                return jsonify({"status": "skipped", "reason": "No long position to close"})
            else:
                order_action = 'SELL'  # Sell to close long
                logger.info(f"Closing LONG position for {symbol} with SELL order")
                
        elif action == "CLOSE_SHORT":
            # Close short position - verify we have a short position
            if symbol not in current_positions:
                logger.warning(f"CLOSE_SHORT signal but NO position exists for {symbol} - REJECTING to prevent unwanted BUY")
                return jsonify({"status": "skipped", "reason": "No position exists to close"})
            elif current_positions[symbol]['action'] != 'SHORT':
                logger.warning(f"CLOSE_SHORT signal but position is {current_positions[symbol]['action']} not SHORT - REJECTING")
                return jsonify({"status": "skipped", "reason": "No short position to close"})
            else:
                order_action = 'BUY'  # Buy to close short
                logger.info(f"Closing SHORT position for {symbol} with BUY order")
                
        elif action == "LONG":
            # Opening new long position
            if symbol in current_positions:
                existing = current_positions[symbol]
                logger.info(f"Already have {existing['action']} position for {symbol}, skipping new LONG signal")
                return jsonify({"status": "skipped", "reason": f"Already have {existing['action']} position"})
            
            order_action = 'BUY'  # Buy to open long
            logger.info(f"Opening LONG position for {symbol} with BUY order")
            
        elif action == "SHORT":
            # Opening new short position
            if symbol in current_positions:
                existing = current_positions[symbol]
                logger.info(f"Already have {existing['action']} position for {symbol}, skipping new SHORT signal")
                return jsonify({"status": "skipped", "reason": f"Already have {existing['action']} position"})
            
            order_action = 'SELL'  # Sell to open short
            logger.info(f"Opening SHORT position for {symbol} with SELL order")
            
        else:
            logger.error(f"Unknown action: {action}")
            return jsonify({"error": f"Unknown action: {action}"})
        
        # Check daily signal limit per stock
        max_daily = TRADING_SETTINGS.get('max_signals_per_stock_daily', 3)
        today_signals_for_stock = len([s for s in daily_signals.get(today, []) 
                                     if s['symbol'] == symbol])
        if today_signals_for_stock >= max_daily:
            logger.info(f"Daily signal limit reached for {symbol}")
            return jsonify({"status": "skipped", "reason": "Daily limit reached"})
        
        # Place order
        if symbol in security_mapping:
            order_result = place_dhan_order(order_action, symbol, quantity, security_mapping[symbol])
            
            if order_result:
                # Log the signal
                signal_record = {
                    'time': current_time.isoformat(),
                    'symbol': symbol,
                    'signal': action,  # LONG, SHORT, CLOSE_LONG, or CLOSE_SHORT
                    'order_action': order_action,  # BUY or SELL
                    'quantity': quantity,
                    'order_id': order_result.get('orderId', 'unknown')
                }
                
                daily_signals[today].append(signal_record)
                
                # Update position tracking
                if action.startswith("CLOSE"):
                    # Closing position
                    closed_position = current_positions.pop(symbol)
                    logger.info(f"Position CLOSED: {symbol} - was {closed_position['action']} x{closed_position['quantity']}")
                else:
                    # Opening new position (LONG or SHORT)
                    entry_price = order_result.get('executed_price', 0)
                    current_positions[symbol] = {
                        'action': action,  # Store as LONG or SHORT
                        'quantity': quantity,
                        'entry_time': current_time.isoformat(),
                        'order_id': signal_record['order_id'],
                        'entry_price': entry_price,
                        'capital_deployed': quantity * entry_price
                    }
                    logger.info(f"Position OPENED: {action} {symbol} x{quantity} @ ₹{entry_price:,.2f}")
                
                # Save state
                save_daily_state()
                
                return jsonify({
                    "status": "success",
                    "message": f"Ichimoku {action} executed for {symbol}",
                    "quantity": quantity,
                    "order_id": signal_record['order_id'],
                    "daily_signals_count": len(daily_signals.get(today, [])),
                    "active_positions": len(current_positions)
                })
            else:
                logger.error(f"Failed to place order for {symbol}")
                return jsonify({"status": "error", "reason": "Order placement failed"})
        else:
            logger.error(f"No security ID found for {symbol}")
            return jsonify({"status": "error", "reason": f"No security ID for {symbol}"})
            
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"error": str(e)})

def is_market_hours():
    """Check if NSE market is open (IST timezone)"""
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist).time()
    
    # Log current IST time for debugging
    logger.debug(f"Current IST time: {now_ist}")
    
    # NSE Market hours: 9:15 AM - 3:30 PM IST
    market_open = time(9, 15)
    market_close = time(15, 30)
    
    return market_open <= now_ist <= market_close

def get_current_price(symbol, security_id):
    """Get current market price from Dhan"""
    try:
        # Option 1: Try to get from positions if available
        positions = dhan.get_positions()
        if positions and 'data' in positions:
            for pos in positions['data']:
                if str(pos.get('securityId')) == str(security_id):
                    return float(pos.get('dayBuyValue', 0)) / float(pos.get('netQty', 1)) if pos.get('netQty') else 0
        
        # Option 2: Return 0 for now (won't affect order placement)
        logger.info(f"Price fetch not critical - order will still execute at market price")
        return 0
            
    except Exception as e:
        logger.error(f"Error fetching price for {symbol}: {e}")
        return 0

def place_dhan_order(action, symbol, quantity, security_id):
    """Place order through Dhan API"""
    try:
        transaction_type = dhan.BUY if action == "BUY" else dhan.SELL
        
        # Get current price before placing order
        current_price = get_current_price(symbol, security_id)
        
        order_response = dhan.place_order(
            security_id=int(security_id),  # Convert to integer
            exchange_segment=dhan.NSE,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type=dhan.MARKET,
            product_type=dhan.INTRA,
            price=0
        )
        
        logger.info(f"Dhan order response for {symbol}: {order_response}")
        
        # Add price to response for tracking
        if order_response:
            order_response['executed_price'] = current_price
        
        return order_response
        
    except Exception as e:
        logger.error(f"Dhan order error for {symbol}: {e}")
        return None

def save_daily_state():
    """Save current state to file"""
    try:
        today = datetime.now().date()
        state = {
            'date': today.isoformat(),
            'daily_signals': daily_signals.get(today, []),
            'current_positions': current_positions,
            'total_signals': len(daily_signals.get(today, []))
        }
        
        with open(f"logs/state_{today.strftime('%Y%m%d')}.json", 'w') as f:
            json.dump(state, f, indent=2, default=str)
            
    except Exception as e:
        logger.error(f"Error saving state: {e}")

@app.route('/positions')
def get_positions_with_pnl():
    """Get all open positions with real-time P&L"""
    positions_pnl = []
    total_capital = 0
    total_current_value = 0
    
    for symbol, position in current_positions.items():
        security_id = security_mapping.get(symbol)
        if security_id:
            current_price = get_current_price(symbol, security_id)
            entry_price = position.get('entry_price', 0)
            quantity = position['quantity']
            action = position['action']
            
            # Calculate P&L
            if entry_price > 0 and current_price > 0:
                if action == 'BUY':
                    pnl_amount = (current_price - entry_price) * quantity
                    pnl_percent = ((current_price - entry_price) / entry_price) * 100
                else:  # SELL (short position)
                    pnl_amount = (entry_price - current_price) * quantity
                    pnl_percent = ((entry_price - current_price) / entry_price) * 100
                
                capital_deployed = entry_price * quantity
                current_value = current_price * quantity
                total_capital += capital_deployed
                total_current_value += current_value + pnl_amount
                
                positions_pnl.append({
                    "symbol": symbol,
                    "action": action,
                    "quantity": quantity,
                    "entry_price": entry_price,
                    "current_price": current_price,
                    "capital_deployed": capital_deployed,
                    "current_value": current_value,
                    "pnl_amount": pnl_amount,
                    "pnl_percent": pnl_percent,
                    "status": "PROFIT" if pnl_percent > 0 else "LOSS" if pnl_percent < 0 else "BREAKEVEN",
                    "entry_time": position.get('entry_time')
                })
    
    # Calculate overall P&L
    overall_pnl = total_current_value - total_capital if total_capital > 0 else 0
    overall_pnl_percent = (overall_pnl / total_capital * 100) if total_capital > 0 else 0
    
    return jsonify({
        "positions": positions_pnl,
        "summary": {
            "total_positions": len(positions_pnl),
            "total_capital_deployed": total_capital,
            "total_current_value": total_current_value,
            "total_pnl_amount": overall_pnl,
            "total_pnl_percent": overall_pnl_percent,
            "profitable_positions": len([p for p in positions_pnl if p['pnl_percent'] > 0]),
            "losing_positions": len([p for p in positions_pnl if p['pnl_percent'] < 0])
        }
    })

@app.route('/position/<symbol>')
def get_single_position_pnl(symbol):
    """Get P&L for a single position"""
    symbol = symbol.upper()
    
    if symbol not in current_positions:
        return jsonify({"error": f"No open position for {symbol}"})
    
    position = current_positions[symbol]
    security_id = security_mapping.get(symbol)
    
    if not security_id:
        return jsonify({"error": f"No security ID found for {symbol}"})
    
    current_price = get_current_price(symbol, security_id)
    entry_price = position.get('entry_price', 0)
    quantity = position['quantity']
    action = position['action']
    
    if entry_price > 0 and current_price > 0:
        if action == 'BUY':
            pnl_amount = (current_price - entry_price) * quantity
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
        else:  # SELL (short position)
            pnl_amount = (entry_price - current_price) * quantity
            pnl_percent = ((entry_price - current_price) / entry_price) * 100
        
        return jsonify({
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "entry_price": entry_price,
            "current_price": current_price,
            "price_change": current_price - entry_price,
            "pnl_amount": pnl_amount,
            "pnl_percent": pnl_percent,
            "capital_deployed": entry_price * quantity,
            "current_value": current_price * quantity,
            "status": "PROFIT" if pnl_percent > 0 else "LOSS" if pnl_percent < 0 else "BREAKEVEN",
            "entry_time": position.get('entry_time'),
            "holding_time": str(datetime.now() - datetime.fromisoformat(position.get('entry_time')))
        })
    else:
        return jsonify({"error": "Unable to calculate P&L - price data unavailable"})

@app.route('/status')
def get_status():
    """Get current trading status"""
    today = datetime.now().date()
    today_signals = daily_signals.get(today, [])
    
    # Get current IST time
    ist = pytz.timezone('Asia/Kolkata')
    current_ist = datetime.now(ist)
    
    return jsonify({
        "date": today.isoformat(),
        "current_time_ist": current_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
        "market_open": is_market_hours(),
        "total_signals_today": len(today_signals),
        "active_positions": len(current_positions),
        "positions": current_positions,
        "recent_signals": today_signals[-10:],
        "stocks_monitored": len(STOCKS_OPEN_INTEREST),
        "stocks_with_security_ids": len([s for s in STOCKS_OPEN_INTEREST if s in security_mapping])
    })

@app.route('/stocks')
def get_stock_list():
    """Get the list of open interest stocks and their availability"""
    stock_status = []
    for stock in STOCKS_OPEN_INTEREST:
        stock_status.append({
            "symbol": stock,
            "has_security_id": stock in security_mapping,
            "has_position": stock in current_positions,
            "quantity": STOCKS_CONFIG[stock]['quantity']
        })
    
    return jsonify({
        "total_stocks": len(STOCKS_OPEN_INTEREST),
        "available_stocks": len([s for s in STOCKS_OPEN_INTEREST if s in security_mapping]),
        "stocks": stock_status
    })

@app.route('/dhan-positions')
def get_dhan_positions():
    """Get positions directly from Dhan"""
    try:
        positions = dhan.get_positions()
        return jsonify(positions)
    except Exception as e:
        return jsonify({"error": str(e)})

def print_stock_list():
    """Print the high open interest stocks for Ichimoku trading"""
    print("\n" + "="*50)
    print("HIGH OPEN INTEREST STOCKS FOR ICHIMOKU TRADING")
    print("="*50)
    
    # Show current IST time
    ist = pytz.timezone('Asia/Kolkata')
    current_ist = datetime.now(ist)
    print(f"Current IST Time: {current_ist.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Market Status: {'OPEN' if is_market_hours() else 'CLOSED'}")
    print("-"*50)
    
    for i, stock in enumerate(STOCKS_OPEN_INTEREST, 1):
        status = "[READY]" if stock in security_mapping else "[MISSING]"
        qty = STOCKS_CONFIG[stock]['quantity']
        print(f"{i:2d}. {stock:15s} Qty: {qty:4d} {status}")
    print("="*50)
    print(f"Total: {len(STOCKS_OPEN_INTEREST)} stocks")
    print(f"Available: {len([s for s in STOCKS_OPEN_INTEREST if s in security_mapping])} stocks")
    print("="*50 + "\n")

if __name__ == '__main__':
    logger.info("Starting Ichimoku Webhook Server for Open Interest Stocks")
    logger.info(f"Monitoring {len(STOCKS_OPEN_INTEREST)} high open interest stocks")
    
    # Print stock list to console
    print_stock_list()
    
    # Load any existing state for today
    today = datetime.now().date()
    try:
        with open(f"logs/state_{today.strftime('%Y%m%d')}.json", 'r') as f:
            saved_state = json.load(f)
            daily_signals[today] = saved_state.get('daily_signals', [])
            
            # IMPORTANT: Restore position tracking from saved state
            saved_positions = saved_state.get('current_positions', {})
            if saved_positions:
                current_positions.update(saved_positions)
                logger.info(f"Restored {len(saved_positions)} open positions from saved state")
                for sym, pos in saved_positions.items():
                    logger.info(f"  - {sym}: {pos['action']} x{pos['quantity']}")
            
            logger.info(f"Loaded existing state: {len(daily_signals.get(today, []))} signals, {len(current_positions)} positions")
    except FileNotFoundError:
        logger.info("No existing state found, starting fresh")
        logger.warning("WARNING: No saved positions found - close signals will be rejected until new positions are opened")
    
    app.run(host='0.0.0.0', port=5000, debug=False)