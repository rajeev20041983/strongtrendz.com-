#!/usr/bin/env python
# live_strong_breakout_analyzer.py - Live STRONG Breakout Strategy - Volume-Confirmed Breakouts Only

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

class LiveStrongBreakoutAnalyzer:
    """Live Strong Breakout Strategy - Volume-Confirmed Breakouts ONLY"""
    
    def __init__(self, lookback_days=21):
        self.lookback_days = lookback_days
        self.live_fetcher = LiveDataFetcher()
        
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
    
    def ATR(self, DF, n):
        """Calculate True Range and Average True Range"""
        df = DF.copy()
        df['H-L'] = abs(df['High'] - df['Low'])
        df['H-PC'] = abs(df['High'] - df['Adj Close'].shift(1))
        df['L-PC'] = abs(df['Low'] - df['Adj Close'].shift(1))
        df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1, skipna=False)
        df['ATR'] = df['TR'].rolling(n).mean()
        return df['ATR']

    def get_stock_data_with_live_price(self, ticker, lookback_days=21):
        """Get stock data with live price updates"""
        try:
            symbol = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
            
            # Get enough data for lookback + buffer
            days_needed = lookback_days + 50
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_needed)
            
            # Download historical data
            stock = yf.Ticker(symbol)
            data = stock.history(start=start_date, end=end_date)
            
            if data.empty or len(data) < lookback_days + 5:
                return None
            
            # Clean data and add Adj Close
            data = data.dropna()
            data['Adj Close'] = data['Close']
            
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
                    data.at[idx, 'Adj Close'] = live_data['price']
                else:
                    # Add new bar for today
                    new_row = pd.DataFrame({
                        'Open': [live_data['open']],
                        'High': [live_data['high']],
                        'Low': [live_data['low']],
                        'Close': [live_data['price']],
                        'Volume': [live_data['volume']],
                        'Dividends': [0],
                        'Stock Splits': [0],
                        'Adj Close': [live_data['price']]
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
    
    def calculate_rsi(self, prices, period=14):
        """Calculate RSI (Relative Strength Index)"""
        try:
            if len(prices) < period + 1:
                return 50
            
            delta = prices.diff().dropna()
            if len(delta) < period:
                return 50
            
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss.replace(0, 0.001)
            rsi = 100 - (100 / (1 + rs))
            
            final_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
            return max(0, min(100, final_rsi))
        except Exception as e:
            return 50
    
    def detect_sideways_market(self, data, threshold=0.05):
        """Detect if market is moving sideways"""
        try:
            if len(data) < 20:
                return False
            
            high_20 = data['High'].rolling(window=20).max().iloc[-1]
            low_20 = data['Low'].rolling(window=20).min().iloc[-1]
            current_price = data['Close'].iloc[-1]
            
            price_range = (high_20 - low_20) / current_price
            return price_range < threshold
        except:
            return False
    
    def detect_live_breakout_signals(self, data, debug=False):
        """Detect ONLY STRONG BREAKOUT signals (BUY/SELL) - Volume-confirmed breakouts only"""
        try:
            if len(data) < self.lookback_days + 5:
                return None
            
            # Calculate indicators - Only what's needed for strong breakouts
            data['ATR'] = self.ATR(data, 20)
            data['roll_max_cp'] = data['High'].rolling(self.lookback_days).max()
            data['roll_min_cp'] = data['Low'].rolling(self.lookback_days).min()
            data['roll_max_vol'] = data['Volume'].rolling(self.lookback_days).max()
            
            # Drop NaN values
            data = data.dropna()
            
            if len(data) < 15:
                return None
            
            # Get latest values
            latest = data.iloc[-1]
            previous = data.iloc[-2] if len(data) > 1 else latest
            
            current_price = latest['Adj Close']
            current_high = latest['High']
            current_low = latest['Low']
            current_volume = latest['Volume']
            
            # Key levels
            resistance_level = latest['roll_max_cp']
            support_level = latest['roll_min_cp']
            prev_max_volume = previous['roll_max_vol']
            current_atr = latest['ATR']
            
            # Calculate RSI and momentum for display purposes
            rsi = self.calculate_rsi(data['Adj Close'])
            
            if len(data) >= 6:
                momentum = ((current_price - data['Adj Close'].iloc[-6]) / data['Adj Close'].iloc[-6]) * 100
            else:
                momentum = 0
            
            # Volume analysis
            volume_ratio = current_volume / data['Volume'].rolling(20).mean().iloc[-1] if len(data) >= 20 else 1.0
            
            # Market condition
            is_sideways = self.detect_sideways_market(data)
            
            # SIGNAL DETECTION LOGIC - ONLY STRONG BREAKOUTS
            signals = []
            is_live = data.attrs.get('is_live', False)
            live_method = data.attrs.get('live_method', 'historical')
            
            # STRONG BREAKOUT BUY: High breaks above resistance with 1.5x volume
            if (current_high >= resistance_level and 
                current_volume > 1.5 * prev_max_volume):
                
                if debug:
                    print(f"   🔥 STRONG BREAKOUT BUY detected!")
                    print(f"      High: ₹{current_high:.2f} >= Resistance: ₹{resistance_level:.2f}")
                    print(f"      Volume: {current_volume:,.0f} > 1.5x Previous Max: {prev_max_volume:,.0f}")
                
                signal = {
                    'ticker': '',  # Will be set by caller
                    'signal_type': 'STRONG_BREAKOUT_BUY',
                    'signal_source': 'BREAKOUT',
                    'price': float(current_price),
                    'entry_price': float(resistance_level * 1.002),
                    'stop_loss': float(current_price - (current_atr * 2)),
                    'take_profit': float(current_price + (current_atr * 4)),
                    'resistance_level': float(resistance_level),
                    'support_level': float(support_level),
                    'strength': float(((current_high - resistance_level) / resistance_level) * 100),
                    'volume_ratio': float(volume_ratio),
                    'rsi': float(rsi),
                    'momentum': float(momentum),
                    'atr': float(current_atr),
                    'is_live': is_live,
                    'live_method': live_method,
                    'is_sideways': is_sideways,
                    'timestamp': datetime.now()
                }
                signals.append(signal)
            
            # STRONG BREAKOUT SELL: Low breaks below support with 1.5x volume
            elif (current_low <= support_level and 
                  current_volume > 1.5 * prev_max_volume):
                
                if debug:
                    print(f"   🔥 STRONG BREAKOUT SELL detected!")
                    print(f"      Low: ₹{current_low:.2f} <= Support: ₹{support_level:.2f}")
                    print(f"      Volume: {current_volume:,.0f} > 1.5x Previous Max: {prev_max_volume:,.0f}")
                
                signal = {
                    'ticker': '',
                    'signal_type': 'STRONG_BREAKOUT_SELL',
                    'signal_source': 'BREAKDOWN',
                    'price': float(current_price),
                    'entry_price': float(support_level * 0.998),
                    'stop_loss': float(current_price + (current_atr * 2)),
                    'take_profit': float(current_price - (current_atr * 4)),
                    'resistance_level': float(resistance_level),
                    'support_level': float(support_level),
                    'strength': float(((support_level - current_low) / support_level) * 100),
                    'volume_ratio': float(volume_ratio),
                    'rsi': float(rsi),
                    'momentum': float(momentum),
                    'atr': float(current_atr),
                    'is_live': is_live,
                    'live_method': live_method,
                    'is_sideways': is_sideways,
                    'timestamp': datetime.now()
                }
                signals.append(signal)
            
            # No other signal types - ONLY STRONG BREAKOUTS
            
            return signals
            
        except Exception as e:
            if debug:
                print(f"❌ Signal detection error: {e}")
            return None

def analyze_stock_live_strong_breakout(ticker, analyzer, debug=False):
    """Analyze single stock for live STRONG breakout signals ONLY"""
    try:
        if debug:
            print(f"📊 Analyzing {ticker} for hybrid breakout signals...")
        
        # Get data with live prices
        data = analyzer.get_stock_data_with_live_price(ticker, analyzer.lookback_days)
        if data is None:
            return None
        
        is_live = data.attrs.get('is_live', False)
        live_method = data.attrs.get('live_method', 'historical')
        current_price = data['Close'].iloc[-1]
        
        if debug:
            live_indicator = "🔴 LIVE" if is_live else "📊 HIST"
            print(f"   {live_indicator} Price: ₹{current_price:.2f} ({live_method})")
        
        # Detect breakout signals
        signals = analyzer.detect_live_breakout_signals(data, debug)
        
        if signals:
            # Set ticker for all signals
            for signal in signals:
                signal['ticker'] = ticker
        
        result = {
            'ticker': ticker,
            'current_price': float(current_price),
            'is_live': is_live,
            'live_method': live_method,
            'signals': signals or [],
            'has_signal': len(signals) > 0 if signals else False,
            'analysis_timestamp': datetime.now()
        }
        
        return result
        
    except Exception as e:
        print(f"❌ Analysis error for {ticker}: {e}")
        return None

def play_alert_sound():
    """Play alert sound for breakout signals"""
    try:
        if WINSOUND_AVAILABLE:
            winsound.Beep(1000, 500)
            return True
        elif PLAYSOUND_AVAILABLE:
            playsound('beep.wav')
            return True
        else:
            print('\a', end='')
            return True
    except Exception as e:
        print("🔊 BEEP! 🔊", end='')
        return False

def analyze_multiple_stocks_live_strong_breakout(tickers, lookback_days=21, update_interval=60, debug=False):
    """Continuously analyze multiple stocks for STRONG BREAKOUT signals ONLY"""
    
    print(f"🚀 LIVE STRONG BREAKOUT ANALYZER")
    print(f"📊 Strategy: STRONG Volume-Confirmed Breakouts ONLY")
    print(f"📈 Monitoring {len(tickers)} stocks")
    print(f"📅 Breakout Period: {lookback_days} days")
    print(f"⏱️  Update interval: {update_interval} seconds")
    print(f"🔴 Live data during market hours (9:15 AM - 3:30 PM IST)")
    print(f"🔥 ALERTS: Only STRONG_BREAKOUT_BUY & STRONG_BREAKOUT_SELL")
    print("="*70)
    
    # Initialize analyzer
    analyzer = LiveStrongBreakoutAnalyzer(lookback_days=lookback_days)
    
    # Track previous signals to avoid duplicate alerts
    previous_signals = {}
    signal_history = []
    
    def single_analysis_cycle():
        """Run one analysis cycle for all stocks"""
        nonlocal previous_signals, signal_history
        
        try:
            current_time = datetime.now()
            print(f"\n⏰ {current_time.strftime('%H:%M:%S')} - Strong Breakout Analysis")
            print("-" * 50)
            
            all_new_signals = []
            
            # Analyze each stock
            for ticker in tickers:
                try:
                    result = analyze_stock_live_strong_breakout(ticker, analyzer, debug)
                    
                    if result:
                        live_indicator = "🔴" if result['is_live'] else "📊"
                        price_display = f"₹{result['current_price']:.2f}"
                        
                        if result.get('has_signal', False) and result.get('signals', []):
                            # New STRONG BREAKOUT signal detected!
                            for signal in result['signals']:
                                try:
                                    # Only process STRONG BREAKOUT signals
                                    if signal['signal_type'] in ['STRONG_BREAKOUT_BUY', 'STRONG_BREAKOUT_SELL']:
                                        signal_key = f"{ticker}_{signal['signal_type']}_{int(signal['strength']*10)}"
                                        
                                        # Check if this is a new signal
                                        if signal_key not in previous_signals:
                                            all_new_signals.append(signal)
                                            previous_signals[signal_key] = current_time
                                            
                                            # Play alert sound
                                            play_alert_sound()
                                            
                                            signal_emoji = "🚀" if signal['signal_type'] == 'STRONG_BREAKOUT_BUY' else "📉"
                                            
                                            print(f"🚨 {live_indicator} {ticker}: {signal_emoji} {signal['signal_type']} "
                                                  f"at {price_display} (Strength: {signal['strength']:.1f}%)")
                                            print(f"   📊 Volume: {signal['volume_ratio']:.1f}x | RSI: {signal['rsi']:.0f} | ATR: ₹{signal['atr']:.2f}")
                                        else:
                                            print(f"   {live_indicator} {ticker}: Continuing breakout at {price_display}")
                                except Exception as se:
                                    print(f"❌ {ticker}: Signal processing error - {str(se)[:50]}")
                        else:
                            print(f"   {live_indicator} {ticker}: {price_display} (No strong breakouts)")
                    else:
                        print(f"❌ {ticker}: No analysis result")
                    
                    time.sleep(0.2)  # Rate limiting
                    
                except Exception as e:
                    print(f"❌ {ticker}: Error - {str(e)[:50]}")
            
            # Display new STRONG BREAKOUT signals in detailed table
            if all_new_signals:
                print(f"\n🚨 NEW STRONG BREAKOUT ALERTS ({len(all_new_signals)} signals)")
                print("="*100)
                
                table_data = []
                headers = ['Ticker', 'Signal Type', 'Price', 'Entry', 'Stop Loss', 
                          'Take Profit', 'Strength%', 'RSI', 'Volume', 'ATR']
                
                for signal in all_new_signals:
                    try:
                        table_data.append([
                            signal.get('ticker', 'N/A'),
                            signal.get('signal_type', 'Unknown').replace('_', ' '),
                            f"₹{signal.get('price', 0):.2f}",
                            f"₹{signal.get('entry_price', 0):.2f}",
                            f"₹{signal.get('stop_loss', 0):.2f}",
                            f"₹{signal.get('take_profit', 0):.2f}",
                            f"{signal.get('strength', 0):.1f}%",
                            f"{signal.get('rsi', 50):.0f}",
                            f"{signal.get('volume_ratio', 1):.1f}x",
                            f"₹{signal.get('atr', 0):.2f}"
                        ])
                    except Exception as te:
                        print(f"❌ Table formatting error: {te}")
                
                if table_data:
                    print(tabulate(table_data, headers=headers, tablefmt="grid"))
                
                # Save to history
                signal_history.extend(all_new_signals)
            
            # Clean old signals (older than 1 hour)
            try:
                cutoff_time = current_time - timedelta(hours=1)
                previous_signals = {k: v for k, v in previous_signals.items() if v > cutoff_time}
            except Exception as ce:
                print(f"❌ Signal cleanup error: {ce}")
            
            return all_new_signals
            
        except Exception as e:
            print(f"❌ Analysis cycle error: {e}")
            return []
    
    # Main monitoring loop
    try:
        while True:
            # Run analysis cycle
            new_signals = single_analysis_cycle()
            
            # Market status
            is_market = analyzer.is_market_hours()
            market_status = "🟢 LIVE" if is_market else "🔴 CLOSED"
            
            # Signal type summary - only strong breakouts
            buy_signals = len([s for s in signal_history if s.get('signal_type') == 'STRONG_BREAKOUT_BUY'])
            sell_signals = len([s for s in signal_history if s.get('signal_type') == 'STRONG_BREAKOUT_SELL'])
            
            print(f"\n📊 Status: {market_status} | "
                  f"Strong Breakouts Today: {len(signal_history)} (BUY: {buy_signals}, SELL: {sell_signals}) | "
                  f"Next Update: {update_interval}s")
            
            # Wait for next update
            time.sleep(update_interval)
            
    except KeyboardInterrupt:
        print(f"\n🛑 Stopping live strong breakout monitoring...")
        print(f"📊 Total strong breakouts detected: {len(signal_history)}")
        
        if signal_history:
            print(f"\n📋 STRONG BREAKOUT SUMMARY:")
            
            # Separate by type
            buy_signals = [s for s in signal_history if s.get('signal_type') == 'STRONG_BREAKOUT_BUY']
            sell_signals = [s for s in signal_history if s.get('signal_type') == 'STRONG_BREAKOUT_SELL']
            
            if buy_signals:
                print(f"\n🚀 STRONG BREAKOUT BUY ({len(buy_signals)} signals):")
                for signal in buy_signals[-10:]:  # Last 10
                    print(f"   {signal['ticker']}: ₹{signal['price']:.2f} "
                          f"(Strength: {signal['strength']:.1f}%) - Vol: {signal['volume_ratio']:.1f}x")
            
            if sell_signals:
                print(f"\n📉 STRONG BREAKOUT SELL ({len(sell_signals)} signals):")
                for signal in sell_signals[-10:]:  # Last 10
                    print(f"   {signal['ticker']}: ₹{signal['price']:.2f} "
                          f"(Strength: {signal['strength']:.1f}%) - Vol: {signal['volume_ratio']:.1f}x")
    
    except Exception as e:
        print(f"❌ Monitoring error: {e}")

def main():
    """Main function for Live STRONG BREAKOUT Analysis ONLY"""
    parser = argparse.ArgumentParser(description="Live STRONG Breakout Analyzer - Volume-Confirmed Breakouts Only")
    
    parser.add_argument('--days', type=int, default=21, 
                       help='Breakout lookback days (default: 21)')
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
        print(f"🧪 TESTING LIVE STRONG BREAKOUT ANALYSIS: {args.test_single}")
        print("="*50)
        
        analyzer = LiveStrongBreakoutAnalyzer(lookback_days=args.days)
        result = analyze_stock_live_strong_breakout(args.test_single, analyzer, debug=True)
        
        if result:
            print(f"\n✅ Analysis successful!")
            print(f"   💰 Current Price: ₹{result['current_price']:.2f}")
            print(f"   🚨 Strong Breakout Signals: {len(result['signals'])}")
            print(f"   🔴 Live Data: {result['is_live']}")
            
            if result['signals']:
                for signal in result['signals']:
                    if signal['signal_type'] in ['STRONG_BREAKOUT_BUY', 'STRONG_BREAKOUT_SELL']:
                        print(f"   🔥 {signal['signal_type']}: ₹{signal['price']:.2f} "
                              f"(Strength: {signal['strength']:.1f}%)")
                        print(f"      📊 Volume: {signal['volume_ratio']:.1f}x | "
                              f"RSI: {signal['rsi']:.0f} | ATR: ₹{signal['atr']:.2f}")
            else:
                print(f"   ⚪ No strong breakout signals detected")
        else:
            print(f"❌ Analysis failed")
        return
    
    # Get tickers to monitor
    if args.stocks:
        tickers = args.stocks
    else:
        tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
    
    print(f"🎯 LIVE STRONG BREAKOUT MONITORING")
    print(f"📊 Strategy: Volume-Confirmed Strong Breakouts ONLY")
    print(f"📈 Monitoring {len(tickers)} stocks: {', '.join(tickers[:5])}{'...' if len(tickers) > 5 else ''}")
    print(f"📅 Breakout Period: {args.days} days")
    print(f"⏱️  Update every: {args.interval} seconds")
    print(f"🔊 Audio alerts: Enabled")
    print(f"📊 Market hours: 9:15 AM - 3:30 PM IST")
    print("="*70)
    
    print(f"\n🔥 STRONG BREAKOUT CRITERIA:")
    print(f"   🚀 STRONG BUY: High breaks {args.days}-day resistance + Volume > 1.5x previous max")
    print(f"   📉 STRONG SELL: Low breaks {args.days}-day support + Volume > 1.5x previous max")
    print(f"   🛑 Stop Loss: 2x ATR below/above entry")
    print(f"   🎯 Take Profit: 4x ATR above/below entry")
    print(f"   📊 No other signal types - PURE BREAKOUT STRATEGY")
    
    # Start live monitoring
    analyze_multiple_stocks_live_strong_breakout(tickers, args.days, args.interval, args.debug)

if __name__ == "__main__":
    main()