#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ticker Formatter for Dhan Trading Configuration
---------------------------------------------
This program converts a simple buy/sell ticker list to the JSON format 
required by the Dhan trading program.

Usage:
    python ticker_formatter.py "buy-RECLTD.NS ADANIENSOL.NS sell-COFORGE.NS BHARATFORG.NS"
    
Or create a text file with the tickers and use:
    python ticker_formatter.py --file tickers.txt
"""

import json
import sys
import argparse
from datetime import datetime

def parse_tickers(ticker_string):
    """Parse the buy/sell ticker string into separate lists"""
    parts = ticker_string.replace('\n', ' ').replace('\r', ' ').split()
    
    buy_tickers = []
    sell_tickers = []
    current_type = None
    
    for part in parts:
        if part.startswith('buy-'):
            current_type = 'buy'
            # Remove 'buy-' prefix and add the ticker
            ticker = part[4:]
            if ticker:
                buy_tickers.append(ticker)
        elif part.startswith('sell-'):
            current_type = 'sell'
            # Remove 'sell-' prefix and add the ticker
            ticker = part[5:]
            if ticker:
                sell_tickers.append(ticker)
        else:
            # This is a ticker following a buy/sell declaration
            if current_type == 'buy':
                buy_tickers.append(part)
            elif current_type == 'sell':
                sell_tickers.append(part)
    
    return buy_tickers, sell_tickers

def create_ticker_config(symbol, transaction_type, quantity=20, stop_loss_percent=1.0, target_percent=1.0):
    """Create a single ticker configuration"""
    return {
        "symbol": symbol,
        "entry_price": "",
        "quantity": quantity,
        "transaction_type": transaction_type,
        "stop_loss_percent": stop_loss_percent,
        "target_percent": target_percent,
        "after_market_order": False,
        "active": True
    }

def generate_trading_config(buy_tickers, sell_tickers, 
                          client_id="1106497024", 
                          access_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzQ4NjM4MzIzLCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwNjQ5NzAyNCJ9.DQ2AER9jAvIYcSBrSWdvt-Hw43n1L4W8oT2kyZdCnjH53iHs0RzDaLs9FVFW0fvhHXg5leZW8YmfAcansDdnjg",
                          place_new_orders=True,
                          check_interval_seconds=30):
    """Generate the complete trading configuration JSON"""
    
    tickers = []
    
    # Add buy tickers
    for symbol in buy_tickers:
        tickers.append(create_ticker_config(symbol, "BUY"))
    
    # Add sell tickers
    for symbol in sell_tickers:
        tickers.append(create_ticker_config(symbol, "SELL"))
    
    # Create the complete configuration
    config = {
        "client_id": client_id,
        "access_token": access_token,
        "place_new_orders": place_new_orders,
        "check_interval_seconds": check_interval_seconds,
        "tickers": tickers
    }
    
    return config

def main():
    parser = argparse.ArgumentParser(description='Convert ticker list to Dhan trading config JSON format')
    
    # Create mutually exclusive group for input method
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('ticker_string', nargs='?', help='Ticker string directly as command line argument')
    input_group.add_argument('--file', '-f', help='File containing ticker string')
    
    # Optional arguments
    parser.add_argument('--output', '-o', help='Output file name (default: trading_config.json)')
    parser.add_argument('--client-id', help='Dhan client ID (default: 1106497024)')
    parser.add_argument('--access-token', help='Dhan access token (uses default if not provided)')
    parser.add_argument('--quantity', type=int, default=20, help='Quantity for each order (default: 20)')
    parser.add_argument('--stop-loss', type=float, default=1.0, help='Stop loss percentage (default: 1.0)')
    parser.add_argument('--target', type=float, default=1.0, help='Target percentage (default: 1.0)')
    parser.add_argument('--check-interval', type=int, default=30, help='Check interval in seconds (default: 30)')
    parser.add_argument('--pretty', action='store_true', help='Pretty print the JSON output')
    
    args = parser.parse_args()
    
    # Get ticker string from either command line or file
    if args.file:
        try:
            with open(args.file, 'r') as f:
                ticker_string = f.read()
        except Exception as e:
            print(f"Error reading file {args.file}: {e}")
            sys.exit(1)
    else:
        ticker_string = args.ticker_string
    
    # Parse tickers
    buy_tickers, sell_tickers = parse_tickers(ticker_string)
    
    # Print summary
    print(f"Parsed tickers:")
    print(f"  BUY ({len(buy_tickers)}): {', '.join(buy_tickers)}")
    print(f"  SELL ({len(sell_tickers)}): {', '.join(sell_tickers)}")
    print()
    
    # Generate configuration
    config = generate_trading_config(
        buy_tickers=buy_tickers,
        sell_tickers=sell_tickers,
        client_id=args.client_id or "1106497024",
        access_token=args.access_token or "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzQ4NjM4MzIzLCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwNjQ5NzAyNCJ9.DQ2AER9jAvIYcSBrSWdvt-Hw43n1L4W8oT2kyZdCnjH53iHs0RzDaLs9FVFW0fvhHXg5leZW8YmfAcansDdnjg",
        place_new_orders=True,
        check_interval_seconds=args.check_interval
    )
    
    # Output file name
    output_file = args.output or 'trading_config.json'
    
    # Save to file
    try:
        with open(output_file, 'w') as f:
            if args.pretty:
                json.dump(config, f, indent=4)
            else:
                json.dump(config, f)
        print(f"Configuration saved to {output_file}")
    except Exception as e:
        print(f"Error writing to file {output_file}: {e}")
        sys.exit(1)
    
    # Also print to console if pretty print is requested
    if args.pretty:
        print("\nGenerated configuration:")
        print(json.dumps(config, indent=4))

if __name__ == "__main__":
    main()