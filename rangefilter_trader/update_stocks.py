import pandas as pd
import json
import os
from datetime import datetime

def update_stocks_config(csv_file_path, config_file_path, min_change_percent=10.0, max_stocks=50):
    """
    Read CSV file, get stocks with change% > min_change_percent, limited to max_stocks
    
    Args:
        csv_file_path: Path to input CSV file
        config_file_path: Path to stocks_config.json
        min_change_percent: Minimum change percentage to include (default 10.0)
        max_stocks: Maximum number of stocks to include (default 50)
    """
    
    try:
        # Read the CSV file
        print(f"Reading CSV file: {csv_file_path}")
        df = pd.read_csv(csv_file_path)
        
        # Display column names to understand the structure
        print(f"Columns in CSV: {df.columns.tolist()}")
        
        # Clean column names (remove extra spaces and newlines)
        df.columns = df.columns.str.strip()
        
        # Look for change% column (might be named differently)
        change_col = None
        symbol_col = None
        
        # Common column name patterns for change percentage
        change_patterns = ['Change(%)', 'Change %', 'Change', '% Change', '%Change', '%CHNG', 'Chng%', 'Chng %']
        symbol_patterns = ['Symbol', 'SYMBOL', 'Ticker', 'Stock', 'Scrip', 'Underlying']
        
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
            # Remove % sign and commas if present and convert to float
            df[change_col] = df[change_col].astype(str).str.replace('%', '').str.replace(',', '')
            df[change_col] = pd.to_numeric(df[change_col], errors='coerce')
            
            # FILTER: Only keep stocks with change% > min_change_percent
            df_filtered = df[df[change_col] > min_change_percent]
            
            if df_filtered.empty:
                print(f"⚠️ No stocks found with change% > {min_change_percent}%")
                return None
            
            # Sort by change percentage in descending order
            df_sorted = df_filtered.sort_values(by=change_col, ascending=False, na_position='last')
            
            print(f"✅ Found {len(df_sorted)} stocks with change% > {min_change_percent}%")
        else:
            print("❌ Error: Change% column not found in CSV")
            return None
        
        # Limit to max_stocks
        df_top = df_sorted.head(max_stocks)
        
        # Prepare stock list for config
        stock_list = []
        
        # Calculate quantity based on price to maintain position size around 10-15k
        def calculate_quantity_by_price(price):
            """Calculate quantity based on price to maintain position size"""
            if pd.isna(price) or price <= 0:
                return 25  # Default
            
            target_position = 12000  # Target position size in rupees
            
            if price < 100:
                return min(200, max(50, int(target_position / price)))
            elif price < 500:
                return min(50, max(20, int(target_position / price)))
            elif price < 1000:
                return min(25, max(10, int(target_position / price)))
            elif price < 2000:
                return min(15, max(5, int(target_position / price)))
            elif price < 5000:
                return min(5, max(2, int(target_position / price)))
            else:
                return max(1, int(target_position / price))
        
        for _, row in df_top.iterrows():
            symbol = str(row[symbol_col]).strip()
            
            # Skip if symbol is empty or NaN
            if pd.isna(symbol) or symbol == '':
                continue
                
            # Remove any exchange prefix (NSE:, BSE:, etc.)
            if ':' in symbol:
                symbol = symbol.split(':')[-1]
            
            # Try to get price if available (look for common price column names)
            price = None
            price_patterns = ['Close', 'Last', 'Price', 'LTP', 'Last Price', 'Close Price', 'PREV. CLOSE', 'LTP']
            
            for pattern in price_patterns:
                if pattern in df.columns:
                    price_val = row[pattern]
                    if not pd.isna(price_val):
                        # Convert to string and remove commas and spaces
                        price_str = str(price_val).replace(',', '').replace(' ', '')
                        try:
                            price = float(price_str)
                            if price > 0:
                                break
                        except:
                            price = None
            
            # Calculate quantity
            if price and price > 0:
                quantity = calculate_quantity_by_price(price)
            else:
                quantity = 25  # Default if price not found
            
            stock_entry = {
                "symbol": symbol.upper(),
                "quantity": quantity,
                "timeframe": "5min",
                "enabled": True
            }
            
            # Add change% info for display
            if change_col and not pd.isna(row[change_col]):
                stock_entry["change_percent"] = round(float(row[change_col]), 2)
            
            stock_list.append(stock_entry)
        
        if not stock_list:
            print("❌ No valid stocks to add to config")
            return None
        
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
                    "market_close": "15:00",
                    "product_type": "INTRA",
                    "order_type": "MARKET",
                    "enable_reentry_after_squareoff": True,
                    "max_positions_per_symbol": 1,
                    "max_total_positions": 10,
                    "stop_loss_percentage": 1.0,
                    "target_percentage": 0.5,
                    "trailing_stop_loss": False,
                    "notes": f"Stocks with >{min_change_percent}% change - Updated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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
            config["trading_settings"]["notes"] = f"Stocks with >{min_change_percent}% change ({len(stock_list)} stocks) - Updated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
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
        print(f"📊 Added {len(stock_list)} stocks to config (all with >{min_change_percent}% change)")
        
        # Display all stocks with their change percentages
        print(f"\n📈 Stocks with >{min_change_percent}% change:")
        for i, stock in enumerate(stock_list, 1):
            change_info = f" ({stock.get('change_percent', 'N/A')}%)" if 'change_percent' in stock else ""
            print(f"{i}. {stock['symbol']:12} - Qty: {stock['quantity']:4}{change_info}")
        
        # Show statistics
        if stock_list:
            changes = [s.get('change_percent', 0) for s in stock_list if 'change_percent' in s]
            if changes:
                print(f"\n📊 Statistics:")
                print(f"   Highest change: {max(changes):.2f}%")
                print(f"   Lowest change:  {min(changes):.2f}%")
                print(f"   Average change: {sum(changes)/len(changes):.2f}%")
        
        return config
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

# Main execution
if __name__ == "__main__":
    # File paths
    csv_file = input("Enter CSV file path (or press Enter for default): ").strip()
    if not csv_file:
        csv_file = "SpurtsinOIByUnderlying18092025.csv"
    
    config_file = r"C:\Users\PC\OneDrive\projects\strongtrendz.com-\rangefilter_trader\stocks_config.json"
    
    # Check if files exist
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        print("Please ensure the CSV file is in the current directory or provide full path")
    else:
        # Ask for minimum change percentage
        min_change = input("Enter minimum change% threshold (default 10): ").strip()
        if min_change:
            try:
                min_change = float(min_change)
            except:
                min_change = 10.0
        else:
            min_change = 10.0
        
        # Update config with filtered stocks
        result = update_stocks_config(csv_file, config_file, min_change_percent=min_change, max_stocks=50)
        
        if result:
            print("\n✨ Configuration update complete!")
            print(f"📝 Config file: {config_file}")