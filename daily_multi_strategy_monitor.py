#!/usr/bin/env python
# quick_signal_generator.py - Generate test signals for monitor testing

import os
import json
import yfinance as yf
from datetime import datetime
import warnings

warnings.filterwarnings("ignore")

def get_live_price(ticker):
    """Get current live price for a ticker"""
    try:
        symbol = f"{ticker}.NS"
        stock = yf.Ticker(symbol)
        
        # Try multiple methods
        try:
            info = stock.info
            price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
            if price and price > 0:
                return float(price)
        except:
            pass
        
        try:
            fast_info = stock.fast_info
            price = fast_info.get('lastPrice') or fast_info.get('regularMarketPrice')
            if price and price > 0:
                return float(price)
        except:
            pass
        
        return None
    except Exception as e:
        print(f"❌ Error fetching {ticker}: {e}")
        return None

def create_realistic_signals(output_dir):
    """Create realistic signals for testing"""
    
    # Popular NSE stocks with realistic scenarios
    test_stocks = [
        {'ticker': 'RELIANCE', 'signal_type': 'STRONG_BUY', 'target_multiplier': 1.04, 'sector': 'Oil & Gas'},
        {'ticker': 'TCS', 'signal_type': 'STRONG_BUY', 'target_multiplier': 1.035, 'sector': 'IT Services'},
        {'ticker': 'HDFCBANK', 'signal_type': 'STRONG_SELL', 'target_multiplier': 0.96, 'sector': 'Banking'},
        {'ticker': 'INFY', 'signal_type': 'STRONG_BUY', 'target_multiplier': 1.042, 'sector': 'IT Services'},
        {'ticker': 'HINDUNILVR', 'signal_type': 'STRONG_BUY', 'target_multiplier': 1.038, 'sector': 'FMCG'},
        {'ticker': 'ICICIBANK', 'signal_type': 'STRONG_SELL', 'target_multiplier': 0.958, 'sector': 'Banking'},
        {'ticker': 'KOTAKBANK', 'signal_type': 'STRONG_BUY', 'target_multiplier': 1.045, 'sector': 'Banking'},
        {'ticker': 'ITC', 'signal_type': 'STRONG_SELL', 'target_multiplier': 0.962, 'sector': 'FMCG'},
        {'ticker': 'LT', 'signal_type': 'STRONG_BUY', 'target_multiplier': 1.041, 'sector': 'Construction'},
        {'ticker': 'SBIN', 'signal_type': 'STRONG_SELL', 'target_multiplier': 0.955, 'sector': 'Banking'}
    ]
    
    print("🚀 Generating realistic test signals...")
    print("📊 Fetching live prices for target calculation...")
    
    # Create signals for each strategy
    strategies = ['breakout', 'donchian', 'bollinger']
    
    for strategy in strategies:
        print(f"\n📊 Creating {strategy.upper()} signals...")
        
        strategy_signals = []
        signals_created = 0
        
        for i, stock_info in enumerate(test_stocks):
            # Assign different stocks to different strategies
            if (i % 3) == strategies.index(strategy):
                ticker = stock_info['ticker']
                
                print(f"   📈 Processing {ticker}...")
                
                # Get live price
                live_price = get_live_price(ticker)
                
                if live_price:
                    # Calculate target based on signal type
                    if 'BUY' in stock_info['signal_type']:
                        target_price = live_price * stock_info['target_multiplier']
                        stop_loss = live_price * 0.955  # 4.5% stop loss
                    else:
                        target_price = live_price * stock_info['target_multiplier']
                        stop_loss = live_price * 1.045  # 4.5% stop loss
                    
                    # Create signal
                    signal = {
                        'ticker': ticker,
                        'signal_type': stock_info['signal_type'],
                        'current_price': live_price,
                        'target_price': target_price,
                        'stop_loss': stop_loss,
                        'upper_channel': target_price if 'BUY' in stock_info['signal_type'] else live_price * 1.05,
                        'lower_channel': target_price if 'SELL' in stock_info['signal_type'] else live_price * 0.95,
                        'upper_band': target_price if 'BUY' in stock_info['signal_type'] else live_price * 1.05,
                        'lower_band': target_price if 'SELL' in stock_info['signal_type'] else live_price * 0.95,
                        'bb_upper': target_price if 'BUY' in stock_info['signal_type'] else live_price * 1.05,
                        'bb_lower': target_price if 'SELL' in stock_info['signal_type'] else live_price * 0.95,
                        'volume_ratio': round(1.2 + (i * 0.1), 1),
                        'rsi': 65 if 'BUY' in stock_info['signal_type'] else 35,
                        'momentum': round(2.5 - (i * 0.3), 1) if 'BUY' in stock_info['signal_type'] else round(-2.5 + (i * 0.3), 1),
                        'sector': stock_info['sector']
                    }
                    
                    strategy_signals.append(signal)
                    signals_created += 1
                    
                    print(f"      ✅ {ticker}: {stock_info['signal_type']} - Target: ₹{target_price:.1f} (Current: ₹{live_price:.1f})")
                
                else:
                    print(f"      ❌ {ticker}: Could not fetch live price")
        
        # Create JSON file for strategy
        timestamp = datetime.now()
        date_str = timestamp.strftime('%Y%m%d')
        time_str = timestamp.strftime('%H%M%S')
        
        if strategy == 'breakout':
            filename = f"corrected_breakout_signals_21d_{date_str}_{time_str}.json"
            metadata = {
                "timestamp": timestamp.isoformat(),
                "total_stocks_analyzed": signals_created,
                "lookback_days": 21,
                "strategy": "CORRECTED High-Low Breakout Strategy with Proper Signal Logic",
                "corrections_applied": [
                    "Volume confirmation uses previous period max",
                    "ATR-based stop losses", 
                    "Proper breakout confirmation",
                    "State-based signal management"
                ]
            }
        elif strategy == 'donchian':
            filename = f"donchian_signals_21d_{date_str}_{time_str}.json"
            metadata = {
                "timestamp": timestamp.isoformat(),
                "total_stocks_analyzed": signals_created,
                "lookback_days": 21,
                "strategy": "Donchian Channel with Trading Days Logic"
            }
        else:  # bollinger
            filename = f"bollinger_signals_20d_2.0std_{date_str}_{time_str}.json"
            metadata = {
                "timestamp": timestamp.isoformat(),
                "total_stocks_analyzed": signals_created,
                "bb_period": 20,
                "std_multiplier": 2.0,
                "strategy": "Bollinger Bands with Trading Days Logic"
            }
        
        # Create JSON data
        json_data = {
            "metadata": metadata,
            "signals": strategy_signals
        }
        
        # Save file
        file_path = os.path.join(output_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        print(f"   ✅ Created: {filename} ({signals_created} signals)")
    
    print(f"\n🎉 SUCCESS! Generated test signals for all 3 strategies")
    print(f"📁 Files saved to: {output_dir}")
    print(f"🎯 Now you can test the monitor with real data!")

def main():
    output_dir = r'C:\Users\PC\OneDrive\projects\strongtrendz.com-\output'
    
    print("🚀 QUICK SIGNAL GENERATOR")
    print("📊 Creating realistic test signals for monitor testing")
    print("="*60)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📁 Created output directory: {output_dir}")
    
    create_realistic_signals(output_dir)
    
    print(f"\n💡 NEXT STEPS:")
    print(f"   1. Run the monitor: python daily_multi_strategy_monitor.py")
    print(f"   2. Or test demo mode: python daily_multi_strategy_monitor.py --demo")
    print(f"   3. Monitor will automatically find today's generated files")

if __name__ == "__main__":
    main()