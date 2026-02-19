import json
import sys
from datetime import datetime

def load_stock_config():
    """Load stock configuration from JSON file"""
    try:
        with open('stocks_config.json', 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print("Error: stocks_config.json file not found!")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format - {e}")
        return None

def print_stock_list():
    """Print the current stock list"""
    config = load_stock_config()
    if not config:
        return
    
    print("\n" + "="*60)
    print("HIGH OPEN INTEREST STOCKS FOR ICHIMOKU TRADING")
    print("="*60)
    print(f"Last Updated: {config['stocks_open_interest'].get('last_updated', 'Unknown')}")
    print("-"*60)
    
    enabled_count = 0
    for i, stock_data in enumerate(config['stocks_open_interest']['stocks'], 1):
        symbol = stock_data['symbol']
        sector = stock_data.get('sector', 'Unknown')
        enabled = stock_data.get('enabled', True)
        alt_symbols = stock_data.get('alternative_symbols', [])
        
        status = "✓ ACTIVE" if enabled else "✗ DISABLED"
        print(f"{i:2d}. {symbol:15s} | {sector:30s} | {status}")
        
        if alt_symbols:
            print(f"    Alternative symbols: {', '.join(alt_symbols)}")
        
        if enabled:
            enabled_count += 1
    
    print("="*60)
    print(f"Total Stocks: {len(config['stocks_open_interest']['stocks'])}")
    print(f"Active Stocks: {enabled_count}")
    print("="*60)
    
    # Show trading settings
    settings = config.get('trading_settings', {})
    if settings:
        print("\nTRADING SETTINGS:")
        print("-"*60)
        for key, value in settings.items():
            print(f"  {key:30s}: {value}")
        print("-"*60)

def add_stock(symbol, sector="Unknown"):
    """Add a new stock to the configuration"""
    config = load_stock_config()
    if not config:
        return
    
    # Check if stock already exists
    for stock_data in config['stocks_open_interest']['stocks']:
        if stock_data['symbol'] == symbol:
            print(f"Stock {symbol} already exists!")
            return
    
    # Add new stock
    new_stock = {
        "symbol": symbol.upper(),
        "sector": sector,
        "enabled": True
    }
    
    config['stocks_open_interest']['stocks'].append(new_stock)
    config['stocks_open_interest']['last_updated'] = datetime.now().strftime('%Y-%m-%d')
    
    # Save back to file
    with open('stocks_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Added {symbol} to stock list")

def toggle_stock(symbol):
    """Enable/disable a stock"""
    config = load_stock_config()
    if not config:
        return
    
    found = False
    for stock_data in config['stocks_open_interest']['stocks']:
        if stock_data['symbol'] == symbol.upper():
            stock_data['enabled'] = not stock_data.get('enabled', True)
            found = True
            status = "enabled" if stock_data['enabled'] else "disabled"
            print(f"Stock {symbol} has been {status}")
            break
    
    if not found:
        print(f"Stock {symbol} not found!")
        return
    
    # Save back to file
    config['stocks_open_interest']['last_updated'] = datetime.now().strftime('%Y-%m-%d')
    with open('stocks_config.json', 'w') as f:
        json.dump(config, f, indent=2)

def remove_stock(symbol):
    """Remove a stock from the configuration"""
    config = load_stock_config()
    if not config:
        return
    
    initial_count = len(config['stocks_open_interest']['stocks'])
    config['stocks_open_interest']['stocks'] = [
        s for s in config['stocks_open_interest']['stocks'] 
        if s['symbol'] != symbol.upper()
    ]
    
    if len(config['stocks_open_interest']['stocks']) < initial_count:
        config['stocks_open_interest']['last_updated'] = datetime.now().strftime('%Y-%m-%d')
        with open('stocks_config.json', 'w') as f:
            json.dump(config, f, indent=2)
        print(f"Removed {symbol} from stock list")
    else:
        print(f"Stock {symbol} not found!")

def get_active_stocks():
    """Return list of active stock symbols"""
    config = load_stock_config()
    if not config:
        return []
    
    stocks = []
    for stock_data in config['stocks_open_interest']['stocks']:
        if stock_data.get('enabled', True):
            stocks.append(stock_data['symbol'])
    
    return stocks

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "add" and len(sys.argv) >= 3:
            symbol = sys.argv[2]
            sector = sys.argv[3] if len(sys.argv) > 3 else "Unknown"
            add_stock(symbol, sector)
        
        elif command == "remove" and len(sys.argv) >= 3:
            symbol = sys.argv[2]
            remove_stock(symbol)
        
        elif command == "toggle" and len(sys.argv) >= 3:
            symbol = sys.argv[2]
            toggle_stock(symbol)
        
        elif command == "list":
            print_stock_list()
        
        else:
            print("Usage:")
            print("  python stock_list.py list                    - Show all stocks")
            print("  python stock_list.py add SYMBOL [SECTOR]     - Add a stock")
            print("  python stock_list.py remove SYMBOL           - Remove a stock")
            print("  python stock_list.py toggle SYMBOL           - Enable/disable a stock")
    else:
        # Default action: show stock list
        print_stock_list()