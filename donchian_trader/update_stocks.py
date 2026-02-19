import pandas as pd
import json
import os
from datetime import datetime

def update_stocks_config(csv_file_path, config_file_path, top_n=50):
    """
    Read CSV file, get top N stocks by change%, and update stocks_config.json
    
    Args:
        csv_file_path: Path to input CSV file
        config_file_path: Path to stocks_config.json
        top_n: Number of top stocks to include (default 50)
    """
    
    try:
        # Read the CSV file
        print(f"Reading CSV file: {csv_file_path}")
        df = pd.read_csv(csv_file_path)
        
        # Display column names to understand the structure
        print(f"Columns in CSV: {df.columns.tolist()}")
        
        # Clean column names (remove extra spaces)
        df.columns = df.columns.str.strip()
        
        # Look for change% column (might be named differently)
        change_col = None
        symbol_col = None
        
        # Common column name patterns for change percentage
        change_patterns = ['Change(%)', 'Change %', 'Change', '% Change', '%Change', 'Chng%', 'Chng %']
        symbol_patterns = ['Symbol', 'Ticker', 'Stock', 'Scrip', 'SYMBOL', 'Underlying']
        
        # Find the change column
        for pattern in change_patterns:
            if pattern in df.columns:
                change_col = pattern
                break
        
        # Find the symbol column
        for pattern in symbol_patterns:
            if pattern in df.columns:
                symbol_col = pattern
                break
                
        if not change_col:
            # Try to find any column with % in name
            for col in df.columns:
                if '%' in col:
                    change_col = col
                    break
        
        if not symbol_col:
            # Use first column as symbol if not found
            symbol_col = df.columns[0]
            
        print(f"Using Symbol column: {symbol_col}")
        print(f"Using Change column: {change_col}")
        
        # Clean and prepare data
        if change_col:
            # Remove % sign if present and convert to float
            df[change_col] = df[change_col].astype(str).str.replace('%', '').str.replace(',', '')
            df[change_col] = pd.to_numeric(df[change_col], errors='coerce')
            
            # Sort by change percentage in descending order
            df_sorted = df.sort_values(by=change_col, ascending=False, na_position='last')
        else:
            print("Warning: Change% column not found, using original order")
            df_sorted = df
        
        # Get top N stocks
        df_top = df_sorted.head(top_n)
        
        # Prepare stock list for config
        stock_list = []
        
        # Default quantities based on typical price ranges (you can adjust these)
        def get_default_quantity(symbol):
            # High-value stocks (typically > 10000)
            high_value = ['MRF', 'PAGEIND', 'SHREECEM', 'ABBOTINDIA', 'HONAUT', '3MINDIA']
            # Mid-high value stocks (typically 5000-10000)
            mid_high = ['MARUTI', 'EICHERMOT', 'BOSCHLTD', 'NESTLEIND', 'BAJAJFINSV']
            # Mid value stocks (typically 1000-5000)
            mid_value = ['ASIANPAINT', 'HAVELLS', 'LT', 'DRREDDY', 'TCS', 'INFY', 'HDFCBANK']
            # Low-mid value stocks (typically 500-1000)
            low_mid = ['TATAPOWER', 'TATACHEM', 'VOLTAS', 'INDHOTEL', 'GODREJCP']
            # Low value stocks (typically < 500)
            low_value = ['SUZLON', 'IDFC', 'YESBANK', 'IDFCFIRSTB', 'JP POWER']
            
            symbol_upper = symbol.upper()
            
            if symbol_upper in high_value:
                return 1
            elif symbol_upper in mid_high:
                return 2
            elif symbol_upper in mid_value:
                return 10
            elif symbol_upper in low_mid:
                return 25
            elif symbol_upper in low_value:
                return 100
            else:
                # Default quantity
                return 25
        
        for _, row in df_top.iterrows():
            symbol = str(row[symbol_col]).strip()
            
            # Skip if symbol is empty or NaN
            if pd.isna(symbol) or symbol == '':
                continue
                
            # Remove any exchange prefix (NSE:, BSE:, etc.)
            if ':' in symbol:
                symbol = symbol.split(':')[-1]
            
            stock_entry = {
                "symbol": symbol.upper(),
                "quantity": get_default_quantity(symbol),
                "timeframe": "5min",
                "enabled": True
            }
            
            # Add change% info as comment if available
            if change_col and not pd.isna(row[change_col]):
                stock_entry["change_percent"] = round(float(row[change_col]), 2)
            
            stock_list.append(stock_entry)
        
        # Load existing config if it exists
        if os.path.exists(config_file_path):
            print(f"Loading existing config: {config_file_path}")
            with open(config_file_path, 'r') as f:
                config = json.load(f)
        else:
            # Create default config structure
            config = {
                "stocks": {"list": []},
                "trading_settings": {
                    "market_open": "09:30",
                    "market_close": "14:30",
                    "product_type": "INTRA",
                    "order_type": "MARKET",
                    "enable_reentry_after_squareoff": False,
                    "max_positions_per_symbol": 1,
                    "max_total_positions": 10,
                    "stop_loss_percentage": 1.0,
                    "target_percentage": 1.0,
                    "trailing_stop_loss": False,
                    "notes": f"Top {top_n} stocks by change% - Updated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            }
        
        # Update the stock list (remove change_percent from final output)
        clean_stock_list = []
        for stock in stock_list:
            clean_entry = {
                "symbol": stock["symbol"],
                "quantity": stock["quantity"],
                "timeframe": stock["timeframe"],
                "enabled": stock["enabled"]
            }
            clean_stock_list.append(clean_entry)
        
        config["stocks"]["list"] = clean_stock_list
        
        # Update notes with timestamp
        if "trading_settings" in config:
            config["trading_settings"]["notes"] = f"Top {top_n} stocks by change% - Updated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Custom JSON formatting - each stock entry on one line
        def format_json_compact(config):
            lines = ['{']
            lines.append('  "stocks": {')
            lines.append('    "list": [')
            
            # Format each stock on a single line
            stock_lines = []
            for stock in config["stocks"]["list"]:
                stock_line = '      {"symbol": "' + stock["symbol"] + '", "quantity": ' + str(stock["quantity"]) + ', "timeframe": "' + stock["timeframe"] + '", "enabled": ' + str(stock["enabled"]).lower() + '}'
                stock_lines.append(stock_line)
            
            lines.append(',\n'.join(stock_lines))
            lines.append('    ]')
            lines.append('  },')
            
            # Format trading settings
            lines.append('  "trading_settings": {')
            settings = config["trading_settings"]
            settings_lines = []
            for key, value in settings.items():
                if isinstance(value, str):
                    settings_lines.append(f'    "{key}": "{value}"')
                elif isinstance(value, bool):
                    settings_lines.append(f'    "{key}": {str(value).lower()}')
                else:
                    settings_lines.append(f'    "{key}": {value}')
            
            lines.append(',\n'.join(settings_lines))
            lines.append('  }')
            lines.append('}')
            
            return '\n'.join(lines)
        
        # Save updated config with compact formatting
        with open(config_file_path, 'w') as f:
            f.write(format_json_compact(config))
        
        print(f"\n✅ Successfully updated {config_file_path}")
        print(f"📊 Added {len(stock_list)} stocks to config")
        
        # Display top 10 for verification
        print("\n📈 Top 10 stocks by change%:")
        for i, stock in enumerate(stock_list[:10], 1):
            change_info = f" (Change: {stock.get('change_percent', 'N/A')}%)" if 'change_percent' in stock else ""
            print(f"{i}. {stock['symbol']} - Qty: {stock['quantity']}{change_info}")
        
        # Create backup of original config
        backup_path = config_file_path.replace('.json', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        
        return config
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

# Main execution
if __name__ == "__main__":
    # File paths
    csv_file = input("Enter CSV file path (or press Enter for default): ").strip()
    if not csv_file:
        csv_file = "SpurtsinOIByUnderlying18092025.csv"
    
    config_file = r"C:\Users\PC\OneDrive\projects\strongtrendz.com-\donchian_trader\stocks_config.json"
    
    # Check if files exist
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        print("Please ensure the CSV file is in the current directory or provide full path")
    else:
        # Update config with top 50 stocks
        result = update_stocks_config(csv_file, config_file, top_n=50)
        
        if result:
            print("\n✨ Configuration update complete!")
            print(f"📁 Config file: {config_file}")
            
            # Option to adjust quantities manually
            adjust = input("\nDo you want to adjust quantities for specific stocks? (y/n): ").lower()
            if adjust == 'y':
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                while True:
                    symbol = input("Enter stock symbol (or 'done' to finish): ").upper()
                    if symbol == 'DONE':
                        break
                    
                    # Find stock in list
                    for stock in config["stocks"]["list"]:
                        if stock["symbol"] == symbol:
                            try:
                                new_qty = int(input(f"Current quantity for {symbol}: {stock['quantity']}. Enter new quantity: "))
                                stock["quantity"] = new_qty
                                print(f"✅ Updated {symbol} quantity to {new_qty}")
                            except ValueError:
                                print("❌ Invalid quantity, skipping...")
                            break
                    else:
                        print(f"❌ Stock {symbol} not found in list")
                
                # Save adjusted config
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=2)
                print("\n✅ Quantities adjusted and saved!")