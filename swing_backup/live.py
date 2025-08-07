#!/usr/bin/env python
# live_sr_breakout_analyzer.py - Complete Live Support & Resistance Breakout Analysis

import os
import sys
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
import concurrent.futures
import argparse
from tabulate import tabulate
import json
import time
import threading
from scipy.signal import argrelextrema
# Optional audio imports
try:
    from playsound import playsound
    PLAYSOUND_AVAILABLE = True
except ImportError:
    PLAYSOUND_AVAILABLE = False

try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False

# Add your project directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import your existing configurations
try:
    from app import config
    print("✅ Successfully loaded config with tickers")
except ImportError:
    print("❌ Config not found! Using default tickers")
    class DefaultConfig:
        TOP_STOCKS = [
            {'symbol': 'RELIANCE'}, {'symbol': 'TCS'}, {'symbol': 'HDFCBANK'}, 
            {'symbol': 'INFY'}, {'symbol': 'HINDUNILVR'}, {'symbol': 'ICICIBANK'},
            {'symbol': 'KOTAKBANK'}, {'symbol': 'ITC'}, {'symbol': 'LT'}, 
            {'symbol': 'SBIN'}, {'symbol': 'BHARTIARTL'}, {'symbol': 'ASIANPAINT'},
            {'symbol': 'MARUTI'}, {'symbol': 'AXISBANK'}, {'symbol': 'BAJFINANCE'},
            {'symbol': 'WIPRO'}, {'symbol': 'NESTLEIND'}, {'symbol': 'ULTRACEMCO'},
            {'symbol': 'TITAN'}, {'symbol': 'POWERGRID'}, {'symbol': 'ONGC'},
            {'symbol': 'EXIDEIND'}, {'symbol': 'PAYTM'}, {'symbol': 'UPL'}
        ]
        OUTPUT_DIR = 'output'
    config = DefaultConfig()

warnings.filterwarnings("ignore")

class LiveDataFetcher:
    """Enhanced live data fetcher for real-time analysis"""
    
    def __init__(self):
        self.session_cache = {}
        
    def get_live_price_data(self, ticker):
        """Get live price with OHLCV data"""
        try:
            symbol = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
            
            # Method 1: Fast Info (Fastest for live price)
            try:
                if symbol not in self.session_cache:
                    self.session_cache[symbol] = yf.Ticker(symbol)
                
                stock = self.session_cache[symbol]
                fast_info = stock.fast_info
                
                live_price = fast_info.get('lastPrice')
                if live_price and live_price > 0:
                    return {
                        'price': float(live_price),
                        'open': float(fast_info.get('open', live_price)),
                        'high': float(fast_info.get('dayHigh', live_price)),
                        'low': float(fast_info.get('dayLow', live_price)),
                        'volume': int(fast_info.get('lastVolume', 0)),
                        'prev_close': float(fast_info.get('previousClose', live_price)),
                        'timestamp': datetime.now(),
                        'method': 'fast_info'
                    }
            except Exception as e:
                pass
            
            # Method 2: 1-minute history for more complete OHLCV
            try:
                stock = yf.Ticker(symbol)
                hist = stock.history(period="2d", interval="1m")
                
                if not hist.empty:
                    latest = hist.iloc[-1]
                    prev_latest = hist.iloc[-2] if len(hist) >= 2 else latest
                    
                    return {
                        'price': float(latest['Close']),
                        'open': float(latest['Open']),
                        'high': float(latest['High']),
                        'low': float(latest['Low']),
                        'volume': int(latest['Volume']),
                        'prev_close': float(prev_latest['Close']),
                        'timestamp': hist.index[-1],
                        'method': '1min_history'
                    }
            except Exception as e:
                pass
                
            return None
            
        except Exception as e:
            print(f"❌ Live data error for {ticker}: {e}")
            return None

class LiveSupportResistanceAnalyzer:
    """Live Support & Resistance Breakout Analysis"""
    
    def __init__(self, pivot_period=10, channel_width_pct=5, min_strength=1, 
                 max_channels=6, lookback_period=290):
        self.pivot_period = pivot_period
        self.channel_width_pct = channel_width_pct / 100
        self.min_strength = min_strength
        self.max_channels = max_channels
        self.lookback_period = lookback_period
        self.live_fetcher = LiveDataFetcher()
        
    def get_stock_data_with_live_price(self, ticker, days=400):
        """Get historical data with live price update"""
        try:
            symbol = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            stock = yf.Ticker(symbol)
            data = stock.history(start=start_date, end=end_date)
            
            if data.empty or len(data) < 100:
                return None
            
            data = data.dropna()
            
            # Get live price data
            live_data = self.live_fetcher.get_live_price_data(ticker)
            
            if live_data and self.is_market_hours():
                # Update or add latest bar with live data 
                current_date = pd.Timestamp.now().normalize()
                
                if current_date in data.index:
                    # Update existing bar
                    idx = current_date
                    data.at[idx, 'Close'] = live_data['price']
                    data.at[idx, 'High'] = max(data.at[idx, 'High'], live_data['high'])
                    data.at[idx, 'Low'] = min(data.at[idx, 'Low'], live_data['low'])
                    data.at[idx, 'Volume'] = live_data['volume']
                else:
                    # Add new bar for today
                    new_row = pd.DataFrame({
                        'Open': [live_data['open']],
                        'High': [live_data['high']],
                        'Low': [live_data['low']],
                        'Close': [live_data['price']],
                        'Volume': [live_data['volume']],
                        'Dividends': [0],
                        'Stock Splits': [0]
                    }, index=[current_date])
                    
                    data = pd.concat([data, new_row])
                
                # Add live metadata
                data.attrs['live_price'] = live_data['price']
                data.attrs['live_timestamp'] = live_data['timestamp']
                data.attrs['live_method'] = live_data['method']
                data.attrs['is_live'] = True
                data.attrs['prev_close'] = live_data['prev_close']
                
                return data
            else:
                data.attrs['is_live'] = False
                return data
                
        except Exception as e:
            print(f"❌ Data error for {ticker}: {e}")
            return None
    
    def is_market_hours(self):
        """Check if NSE market is open"""
        try:
            now = datetime.now()
            
            # Skip weekends
            if now.weekday() >= 5:
                return False
            
            # Market hours: 9:15 AM to 3:30 PM IST
            market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
            market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
            
            return market_open <= now <= market_close
            
        except:
            return True
    
    def find_pivot_points(self, data):
        """Find pivot highs and lows"""
        try:
            highs = data['High'].values
            lows = data['Low'].values
            
            # Find pivot highs and lows
            pivot_high_indices = argrelextrema(highs, np.greater, order=self.pivot_period)[0]
            pivot_low_indices = argrelextrema(lows, np.less, order=self.pivot_period)[0]
            
            pivot_points = []
            
            # Add pivot highs
            for idx in pivot_high_indices:
                if idx >= self.pivot_period and idx < len(data) - self.pivot_period:
                    pivot_points.append({
                        'index': idx,
                        'price': highs[idx],
                        'type': 'high',
                        'timestamp': data.index[idx],
                        'bar_index': idx
                    })
            
            # Add pivot lows
            for idx in pivot_low_indices:
                if idx >= self.pivot_period and idx < len(data) - self.pivot_period:
                    pivot_points.append({
                        'index': idx,
                        'price': lows[idx],
                        'type': 'low',
                        'timestamp': data.index[idx],
                        'bar_index': idx
                    })
            
            # Sort and filter recent pivots
            pivot_points.sort(key=lambda x: x['index'])
            current_bar = len(data) - 1
            
            recent_pivots = []
            for pivot in reversed(pivot_points):
                if current_bar - pivot['index'] <= self.lookback_period:
                    recent_pivots.insert(0, pivot)
                else:
                    break
                    
            return recent_pivots
            
        except Exception as e:
            print(f"❌ Pivot points error: {e}")
            return []
    
    def calculate_max_channel_width(self, data):
        """Calculate maximum channel width"""
        try:
            lookback = min(300, len(data))
            recent_data = data.tail(lookback)
            
            prdhighest = recent_data['High'].max()
            prdlowest = recent_data['Low'].min()
            
            cwidth = (prdhighest - prdlowest) * self.channel_width_pct
            return cwidth
            
        except Exception as e:
            return 0
    
    def get_sr_vals(self, pivot_index, pivot_points, cwidth):
        """Calculate support/resistance values for channel"""
        try:
            base_pivot = pivot_points[pivot_index]
            lo = base_pivot['price']
            hi = base_pivot['price']
            numpp = 0
            
            for pivot in pivot_points:
                cpp = pivot['price']
                
                if cpp <= hi:
                    potential_lo = min(lo, cpp)
                    wdth = hi - potential_lo
                else:
                    potential_hi = max(hi, cpp)
                    wdth = potential_hi - lo
                
                if wdth <= cwidth:
                    if cpp <= hi:
                        lo = min(lo, cpp)
                    else:
                        hi = max(hi, cpp)
                    numpp += 20
            
            return hi, lo, numpp
            
        except Exception as e:
            return base_pivot['price'], base_pivot['price'], 20
    
    def calculate_touch_strength(self, channel_high, channel_low, data):
        """Calculate channel strength from price touches"""
        try:
            touches = 0
            lookback = min(self.lookback_period, len(data))
            
            for i in range(len(data) - lookback, len(data)):
                if i < 0:
                    continue
                    
                high = data['High'].iloc[i]
                low = data['Low'].iloc[i]
                
                if ((high <= channel_high and high >= channel_low) or 
                    (low <= channel_high and low >= channel_low)):
                    touches += 1
            
            return touches
            
        except Exception as e:
            return 0
    
    def create_channels(self, pivot_points, data):
        """Create S&R channels from pivot points"""
        try:
            if len(pivot_points) < 2:
                return []
            
            cwidth = self.calculate_max_channel_width(data)
            channel_data = []
            
            for i, pivot in enumerate(pivot_points):
                hi, lo, strength = self.get_sr_vals(i, pivot_points, cwidth)
                touch_strength = self.calculate_touch_strength(hi, lo, data)
                total_strength = strength + touch_strength
                
                channel_data.append({
                    'high': hi,
                    'low': lo,
                    'strength': total_strength,
                    'pivot_count': strength // 20,
                    'touches': touch_strength,
                    'width': hi - lo,
                    'mid': (hi + lo) / 2
                })
            
            # Remove duplicates and sort by strength
            unique_channels = self.remove_duplicate_channels(channel_data, cwidth)
            unique_channels.sort(key=lambda x: x['strength'], reverse=True)
            
            strong_channels = [ch for ch in unique_channels 
                             if ch['strength'] >= self.min_strength * 20]
            
            return strong_channels[:self.max_channels]
            
        except Exception as e:
            print(f"❌ Channel creation error: {e}")
            return []
    
    def remove_duplicate_channels(self, channels, cwidth):
        """Remove duplicate/overlapping channels"""
        if not channels:
            return []
        
        unique_channels = []
        tolerance = cwidth * 0.1
        
        for channel in channels:
            is_duplicate = False
            
            for i, existing in enumerate(unique_channels):
                if (abs(channel['high'] - existing['high']) < tolerance and
                    abs(channel['low'] - existing['low']) < tolerance):
                    
                    if channel['strength'] > existing['strength']:
                        unique_channels[i] = channel
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_channels.append(channel)
        
        return unique_channels
    
    def detect_live_breakouts(self, channels, data):
        """Detect real-time breakouts"""
        try:
            if len(data) < 2 or not channels:
                return []
            
            current_close = data['Close'].iloc[-1]
            prev_close = data.attrs.get('prev_close', data['Close'].iloc[-2])
            
            breakouts = []
            
            for channel in channels:
                breakout_info = None
                
                # Resistance breakout
                if (prev_close <= channel['high'] and current_close > channel['high']):
                    breakout_info = {
                        'ticker': '',  # Will be set by caller
                        'price': float(current_close),
                        'breakout_type': 'Resistance Break',
                        'broken_level': f"₹{channel['low']:.2f}-₹{channel['high']:.2f}",
                        'strength': int(channel['strength']),
                        'channel_width': f"₹{channel['width']:.2f}",
                        'channel': channel,
                        'breakout_direction': 'up',
                        'prev_close': float(prev_close),
                        'signal': 'BUY'
                    }
                
                # Support breakdown
                elif (prev_close >= channel['low'] and current_close < channel['low']):
                    breakout_info = {
                        'ticker': '',  # Will be set by caller
                        'price': float(current_close),
                        'breakout_type': 'Support Break',
                        'broken_level': f"₹{channel['low']:.2f}-₹{channel['high']:.2f}",
                        'strength': int(channel['strength']),
                        'channel_width': f"₹{channel['width']:.2f}",
                        'channel': channel,
                        'breakout_direction': 'down',
                        'prev_close': float(prev_close),
                        'signal': 'SELL'
                    }
                
                if breakout_info:
                    breakouts.append(breakout_info)
            
            return breakouts
            
        except Exception as e:
            print(f"❌ Breakout detection error: {e}")
            return []

def analyze_stock_live_sr(ticker, sr_analyzer, debug=False):
    """Analyze single stock for live S&R breakouts"""
    try:
        if debug:
            print(f"📊 Analyzing {ticker} for S&R breakouts...")
        
        # Get data with live prices
        data = sr_analyzer.get_stock_data_with_live_price(ticker)
        if data is None:
            return None
        
        is_live = data.attrs.get('is_live', False)
        live_method = data.attrs.get('live_method', 'historical')
        current_price = data['Close'].iloc[-1]
        
        if debug:
            live_indicator = "🔴 LIVE" if is_live else "📊 HIST"
            print(f"   {live_indicator} Price: ₹{current_price:.2f} ({live_method})")
        
        # Find pivot points
        pivot_points = sr_analyzer.find_pivot_points(data)
        if debug:
            print(f"   📍 Found {len(pivot_points)} pivot points")
        
        # Create channels
        channels = sr_analyzer.create_channels(pivot_points, data)
        if debug:
            print(f"   📊 Created {len(channels)} S&R channels")
        
        # Detect breakouts
        breakouts = sr_analyzer.detect_live_breakouts(channels, data)
        
        # Set ticker for breakouts
        for breakout in breakouts:
            breakout['ticker'] = ticker
            breakout['is_live'] = is_live
        
        result = {
            'ticker': ticker,
            'current_price': float(current_price),
            'is_live': is_live,
            'live_method': live_method,
            'total_pivots': len(pivot_points),
            'total_channels': len(channels),
            'channels': channels,
            'breakouts': breakouts,
            'has_breakout': len(breakouts) > 0,
            'analysis_timestamp': datetime.now()
        }
        
        return result
        
    except Exception as e:
        print(f"❌ Analysis error for {ticker}: {e}")
        return None

def play_alert_sound():
    """Play alert sound for breakouts"""
    try:
        if WINSOUND_AVAILABLE:
            # Windows system beep
            winsound.Beep(1000, 500)  # 1000 Hz for 500ms
            return True
        elif PLAYSOUND_AVAILABLE:
            # Try playsound if available
            playsound('beep.wav')  # You'd need a beep.wav file
            return True
        else:
            # ASCII bell character (basic beep)
            print('\a', end='')
            return True
    except Exception as e:
        # Silent fallback - just print alert
        print("🔊 BEEP! 🔊", end='')
        return False

def analyze_multiple_stocks_live(tickers, update_interval=60, debug=False):
    """Continuously analyze multiple stocks for breakouts"""
    
    print(f"🚀 LIVE SUPPORT & RESISTANCE BREAKOUT ANALYZER")
    print(f"📊 Monitoring {len(tickers)} stocks")
    print(f"⏱️  Update interval: {update_interval} seconds")
    print(f"🔴 Live data during market hours (9:15 AM - 3:30 PM IST)")
    print("="*70)
    
    # Initialize analyzer
    sr_analyzer = LiveSupportResistanceAnalyzer(
        pivot_period=10,
        channel_width_pct=5,
        min_strength=1,
        max_channels=6,
        lookback_period=290
    )
    
    # Track previous signals to avoid duplicate alerts - FIXED SCOPE
    previous_signals = {}
    breakout_history = []
    
    def single_analysis_cycle():
        """Run one analysis cycle for all stocks"""
        nonlocal previous_signals, breakout_history  # FIXED: Declare nonlocal
        
        try:
            current_time = datetime.now()
            print(f"\n⏰ {current_time.strftime('%H:%M:%S')} - Analysis Update")
            print("-" * 50)
            
            all_breakouts = []
            
            # Analyze each stock
            for ticker in tickers:
                try:
                    result = analyze_stock_live_sr(ticker, sr_analyzer, debug)
                    
                    if result:
                        live_indicator = "🔴" if result['is_live'] else "📊"
                        price_display = f"₹{result['current_price']:.2f}"
                        
                        if result.get('has_breakout', False) and result.get('breakouts', []):
                            # New breakout detected!
                            for breakout in result['breakouts']:
                                try:
                                    breakout_key = f"{ticker}_{breakout['breakout_type']}_{breakout['strength']}"
                                    
                                    # Check if this is a new breakout
                                    if breakout_key not in previous_signals:
                                        all_breakouts.append(breakout)
                                        previous_signals[breakout_key] = current_time
                                        
                                        # Play alert sound
                                        play_alert_sound()
                                        
                                        print(f"🚨 {live_indicator} {ticker}: {breakout['breakout_type']} "
                                              f"at {price_display} (Strength: {breakout['strength']})")
                                    else:
                                        print(f"   {live_indicator} {ticker}: Continuing breakout "
                                              f"at {price_display}")
                                except Exception as be:
                                    print(f"❌ {ticker}: Breakout processing error - {str(be)[:50]}")
                        else:
                            print(f"   {live_indicator} {ticker}: {price_display} "
                                  f"({result.get('total_channels', 0)} channels)")
                    else:
                        print(f"❌ {ticker}: No analysis result")
                    
                    time.sleep(0.2)  # Reduced rate limiting
                    
                except Exception as e:
                    print(f"❌ {ticker}: Error - {str(e)[:50]}")
            
            # Display new breakouts in table format
            if all_breakouts:
                print(f"\n🚨 NEW BREAKOUT ALERTS ({len(all_breakouts)} signals)")
                print("="*80)
                
                table_data = []
                headers = ['Ticker', 'Price', 'Breakout Type', 'Broken Level', 'Strength', 'Channel Width']
                
                for breakout in all_breakouts:
                    try:
                        table_data.append([
                            breakout.get('ticker', 'N/A'),
                            f"₹{breakout.get('price', 0):.2f}",
                            breakout.get('breakout_type', 'Unknown'),
                            breakout.get('broken_level', 'N/A'),
                            breakout.get('strength', 0),
                            breakout.get('channel_width', 'N/A')
                        ])
                    except Exception as te:
                        print(f"❌ Table formatting error: {te}")
                
                if table_data:
                    print(tabulate(table_data, headers=headers, tablefmt="grid"))
                
                # Save to history
                breakout_history.extend(all_breakouts)
            
            # Clean old signals (older than 1 hour)
            try:
                cutoff_time = current_time - timedelta(hours=1)
                previous_signals = {k: v for k, v in previous_signals.items() if v > cutoff_time}
            except Exception as ce:
                print(f"❌ Signal cleanup error: {ce}")
            
            return all_breakouts
            
        except Exception as e:
            print(f"❌ Analysis cycle error: {e}")
            return []
    
    # Main monitoring loop
    try:
        while True:
            # Run analysis cycle
            new_breakouts = single_analysis_cycle()
            
            # Market status
            is_market = sr_analyzer.is_market_hours()
            market_status = "🟢 LIVE" if is_market else "🔴 CLOSED"
            
            print(f"\n📊 Status: {market_status} | "
                  f"Breakouts Today: {len(breakout_history)} | "
                  f"Next Update: {update_interval}s")
            
            # Wait for next update
            time.sleep(update_interval)
            
    except KeyboardInterrupt:
        print(f"\n🛑 Stopping live monitoring...")
        print(f"📊 Total breakouts detected: {len(breakout_history)}")
        
        if breakout_history:
            print(f"\n📋 BREAKOUT SUMMARY:")
            for breakout in breakout_history[-10:]:  # Last 10
                print(f"   {breakout['ticker']}: {breakout['breakout_type']} "
                      f"at ₹{breakout['price']:.2f} (Strength: {breakout['strength']})")
    
    except Exception as e:
        print(f"❌ Monitoring error: {e}")

def main():
    """Main function for Live S&R Breakout Analysis"""
    parser = argparse.ArgumentParser(description="Live Support & Resistance Breakout Analyzer")
    
    parser.add_argument('--interval', type=int, default=60, 
                       help='Update interval in seconds (default: 60)')
    parser.add_argument('--stocks', type=str, nargs='+',
                       help='Specific stocks to monitor (default: all from config)')
    parser.add_argument('--test-single', type=str, 
                       help='Test analysis on single ticker')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug output')
    
    args = parser.parse_args()
    
    # Test single ticker
    if args.test_single:
        print(f"🧪 TESTING LIVE S&R ANALYSIS: {args.test_single}")
        print("="*50)
        
        sr_analyzer = LiveSupportResistanceAnalyzer()
        result = analyze_stock_live_sr(args.test_single, sr_analyzer, debug=True)
        
        if result:
            print(f"\n✅ Analysis successful!")
            print(f"   💰 Current Price: ₹{result['current_price']:.2f}")
            print(f"   📊 Channels: {result['total_channels']}")
            print(f"   🚨 Breakouts: {len(result['breakouts'])}")
            
            if result['breakouts']:
                for breakout in result['breakouts']:
                    print(f"   🔥 {breakout['breakout_type']}: {breakout['broken_level']} "
                          f"(Strength: {breakout['strength']})")
        else:
            print(f"❌ Analysis failed")
        return
    
    # Get tickers to monitor
    if args.stocks:
        tickers = args.stocks
    else:
        tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
    
    print(f"🎯 LIVE S&R BREAKOUT MONITORING")
    print(f"📈 Monitoring {len(tickers)} stocks: {', '.join(tickers[:5])}{'...' if len(tickers) > 5 else ''}")
    print(f"⏱️  Update every: {args.interval} seconds")
    print(f"🔊 Audio alerts: Enabled")
    print(f"📊 Market hours: 9:15 AM - 3:30 PM IST")
    print("="*70)
    
    # Start live monitoring
    analyze_multiple_stocks_live(tickers, args.interval, args.debug)

if __name__ == "__main__":
    main()