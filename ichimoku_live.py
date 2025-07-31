#!/usr/bin/env python
# live_ichimoku_trading_signals.py - Live Ichimoku Trading Signals with Real-time Alerts
# 
# Dependencies: pip install yfinance pandas numpy pytz tabulate
# Optional: pip install playsound (for audio alerts)
#
# Usage: python live_ichimoku_trading_signals.py --help

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

# Timezone handling
try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False
    print("⚠️  pytz not available. Install with: pip install pytz")
    print("⚠️  Using system local time instead of IST")

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

# Sector mapping
SECTOR_MAPPING = {
    'RELIANCE': 'Oil & Gas', 'TCS': 'Information Technology', 'HDFCBANK': 'Banking',
    'INFY': 'Information Technology', 'HINDUNILVR': 'FMCG', 'ICICIBANK': 'Banking',
    'KOTAKBANK': 'Banking', 'ITC': 'FMCG', 'LT': 'Infrastructure', 'SBIN': 'Banking',
    'BHARTIARTL': 'Telecom', 'ASIANPAINT': 'Paints', 'MARUTI': 'Automobiles',
    'AXISBANK': 'Banking', 'BAJFINANCE': 'Financial Services', 'WIPRO': 'Information Technology',
    'NESTLEIND': 'FMCG', 'ULTRACEMCO': 'Cement', 'TITAN': 'Consumer Durables',
    'POWERGRID': 'Power', 'ONGC': 'Oil & Gas', 'EXIDEIND': 'Auto Ancillaries',
    'PAYTM': 'Fintech', 'UPL': 'Chemicals'
}

def get_stock_sector(ticker):
    return SECTOR_MAPPING.get(ticker, 'Others')

warnings.filterwarnings("ignore")

class LiveDataFetcher:
    """Enhanced live data fetcher for real-time Ichimoku analysis"""
    
    def __init__(self):
        self.session_cache = {}
    
    def get_ist_time(self):
        """Get current IST time"""
        try:
            if PYTZ_AVAILABLE:
                ist = pytz.timezone('Asia/Kolkata')
                return datetime.now(ist)
            else:
                # Fallback to system time
                return datetime.now()
        except:
            return datetime.now()
        
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
                        'timestamp': self.get_ist_time(),
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

class LiveIchimokuAnalyzer:
    """Live Ichimoku analyzer with real-time signal detection"""
    
    def __init__(self, tenkan_period=9, kijun_period=26, senkou_b_period=52, displacement=26):
        self.tenkan_period = tenkan_period
        self.kijun_period = kijun_period  
        self.senkou_b_period = senkou_b_period
        self.displacement = displacement
        self.live_fetcher = LiveDataFetcher()
        
    def get_ist_time(self):
        """Get current IST time"""
        try:
            if PYTZ_AVAILABLE:
                ist = pytz.timezone('Asia/Kolkata')
                return datetime.now(ist)
            else:
                # Fallback to system time
                return datetime.now()
        except:
            return datetime.now()
    
    def is_market_hours(self):
        """Check if NSE market is open (IST timezone)"""
        try:
            # Get current time in IST
            if PYTZ_AVAILABLE:
                ist = pytz.timezone('Asia/Kolkata')
                now_ist = datetime.now(ist)
            else:
                # Fallback to system time (assume it's IST or user's local time)
                now_ist = datetime.now()
            
            # Skip weekends
            if now_ist.weekday() >= 5:  # Saturday = 5, Sunday = 6
                return False
            
            # Market hours: 9:15 AM to 3:30 PM IST
            market_open = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
            market_close = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
            
            return market_open <= now_ist <= market_close
            
        except:
            return True
    
    def get_ist_time(self):
        """Get current IST time"""
        try:
            ist = pytz.timezone('Asia/Kolkata')
            return datetime.now(ist)
        except:
            return datetime.now()
    
    def get_stock_data_with_live_price(self, ticker, days=300):
        """Get historical data with live price update"""
        try:
            symbol = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
            
            # Use IST timezone if available
            if PYTZ_AVAILABLE:
                ist = pytz.timezone('Asia/Kolkata')
                end_date = datetime.now(ist)
            else:
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
    
    def donchian(self, data, period):
        """Calculate Donchian Channel"""
        try:
            high_roll = data['High'].rolling(window=period, min_periods=1).max()
            low_roll = data['Low'].rolling(window=period, min_periods=1).min()
            result = (high_roll + low_roll) / 2
            return result.fillna(data['Close'])
        except Exception as e:
            return data['Close']
    
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
    
    def calculate_ichimoku(self, data):
        """Calculate all Ichimoku Cloud components"""
        if len(data) < max(self.senkou_b_period, self.displacement) + 50:
            raise ValueError(f"Need at least {max(self.senkou_b_period, self.displacement) + 50} data points")
        
        # Calculate Ichimoku lines
        tenkan_line = self.donchian(data, self.tenkan_period)
        kijun_line = self.donchian(data, self.kijun_period)
        
        # Senkou Spans (Leading Spans)
        senkou_a = (tenkan_line + kijun_line) / 2
        senkou_b = self.donchian(data, self.senkou_b_period)
        
        # Chikou Span (Lagging Span)
        chikou_span = data['Close'].shift(-self.displacement + 1)
        
        # Cloud boundaries (displaced forward)
        senkou_a_displaced = senkou_a.shift(self.displacement - 1)
        senkou_b_displaced = senkou_b.shift(self.displacement - 1)
        
        # Fill NaN values
        senkou_a_displaced = senkou_a_displaced.fillna(senkou_a.iloc[0] if len(senkou_a) > 0 else 0)
        senkou_b_displaced = senkou_b_displaced.fillna(senkou_b.iloc[0] if len(senkou_b) > 0 else 0)
        
        # Current cloud levels
        cloud_high = np.maximum(senkou_a_displaced, senkou_b_displaced)
        cloud_low = np.minimum(senkou_a_displaced, senkou_b_displaced)
        
        # Cloud color
        cloud_green = (senkou_a_displaced > senkou_b_displaced).fillna(False)
        
        return {
            'tenkan_line': tenkan_line,
            'kijun_line': kijun_line,
            'senkou_a': senkou_a,
            'senkou_b': senkou_b,
            'senkou_a_displaced': senkou_a_displaced,
            'senkou_b_displaced': senkou_b_displaced,
            'chikou_span': chikou_span,
            'cloud_high': cloud_high,
            'cloud_low': cloud_low,
            'cloud_green': cloud_green,
            'close': data['Close'],
            'high': data['High'],
            'low': data['Low']
        }
    
    def calculate_signals(self, ichimoku_data):
        """Calculate 4-parameter Ichimoku signals"""
        tenkan = ichimoku_data['tenkan_line']
        kijun = ichimoku_data['kijun_line']
        cloud_high = ichimoku_data['cloud_high']
        cloud_low = ichimoku_data['cloud_low']
        cloud_green = ichimoku_data['cloud_green']
        close = ichimoku_data['close']
        high = ichimoku_data['high']
        low = ichimoku_data['low']
        
        # Parameter 1: Cloud color
        cloud_bullish = cloud_green.fillna(False)
        
        # Parameter 2: Price position
        price_above_cloud = (close > cloud_high).fillna(False)
        price_below_cloud = (close < cloud_low).fillna(False)
        price_in_cloud = (~price_above_cloud) & (~price_below_cloud)
        
        # Parameter 3: Tenkan-Kijun crossing
        tk_bullish = (tenkan > kijun).fillna(False)
        tk_bearish = (tenkan < kijun).fillna(False)
        
        # Parameter 4: Chikou Span conditions
        high_shifted = high.shift(self.displacement).fillna(high.iloc[0] if len(high) > 0 else 0)
        low_shifted = low.shift(self.displacement).fillna(low.iloc[0] if len(low) > 0 else 0)
        
        chikou_above_price = (close > high_shifted).fillna(False)
        chikou_below_price = (close < low_shifted).fillna(False)
        
        cloud_high_shifted = cloud_high.shift(self.displacement).fillna(cloud_high.iloc[0] if len(cloud_high) > 0 else 0)
        cloud_low_shifted = cloud_low.shift(self.displacement).fillna(cloud_low.iloc[0] if len(cloud_low) > 0 else 0)
        
        chikou_above_cloud = (close > cloud_high_shifted).fillna(False)
        chikou_below_cloud = (close < cloud_low_shifted).fillna(False)
        
        chikou_bullish = chikou_above_price & chikou_above_cloud
        chikou_bearish = chikou_below_price & chikou_below_cloud
        
        # Complete signals
        long_signal = (cloud_bullish & price_above_cloud & tk_bullish & chikou_bullish)
        short_signal = ((~cloud_bullish) & price_below_cloud & tk_bearish & chikou_bearish)
        
        # Signal triggers
        long_signal_prev = long_signal.shift(1).fillna(False)
        short_signal_prev = short_signal.shift(1).fillna(False)
        
        new_long = long_signal & (~long_signal_prev)
        new_short = short_signal & (~short_signal_prev)
        
        # Current status
        try:
            current_long = bool(long_signal.iloc[-1]) if long_signal.iloc[-1] in [True, False] else False
            current_short = bool(short_signal.iloc[-1]) if short_signal.iloc[-1] in [True, False] else False
            current_new_long = bool(new_long.iloc[-1]) if new_long.iloc[-1] in [True, False] else False
            current_new_short = bool(new_short.iloc[-1]) if new_short.iloc[-1] in [True, False] else False
        except (IndexError, ValueError, TypeError):
            current_long = False
            current_short = False
            current_new_long = False
            current_new_short = False
        
        return {
            'cloud_bullish': cloud_bullish,
            'price_above_cloud': price_above_cloud,
            'price_below_cloud': price_below_cloud,
            'price_in_cloud': price_in_cloud,
            'tk_bullish': tk_bullish,
            'tk_bearish': tk_bearish,
            'chikou_bullish': chikou_bullish,
            'chikou_bearish': chikou_bearish,
            'long_signal': long_signal,
            'short_signal': short_signal,
            'new_long': new_long,
            'new_short': new_short,
            'current_long': current_long,
            'current_short': current_short,
            'current_new_long': current_new_long,
            'current_new_short': current_new_short
        }
    
    def calculate_trading_levels(self, data, ichimoku_data, signals):
        """Calculate Entry, Current, Stop Loss levels"""
        try:
            current_price = data['Close'].iloc[-1]
            
            # Get current Ichimoku values
            tenkan_current = ichimoku_data['tenkan_line'].iloc[-1]
            kijun_current = ichimoku_data['kijun_line'].iloc[-1]
            cloud_high_current = ichimoku_data['cloud_high'].iloc[-1]
            cloud_low_current = ichimoku_data['cloud_low'].iloc[-1]
            
            # Determine signal type
            if signals['current_new_long'] or signals['current_long']:
                signal_type = 'LONG'
                
                # Entry level (for new positions)
                if signals['current_new_long']:
                    entry_level = current_price
                else:
                    entry_level = cloud_high_current
                
                # Stop Loss levels
                stop_loss_options = {
                    'conservative': cloud_low_current,
                    'aggressive': kijun_current,
                    'tight': tenkan_current
                }
                
                stop_loss = stop_loss_options['conservative']
                
                # Target levels
                risk_amount = entry_level - stop_loss
                target1 = entry_level + (risk_amount * 1.5)
                target2 = entry_level + (risk_amount * 2.5)
                
            elif signals['current_new_short'] or signals['current_short']:
                signal_type = 'SHORT'
                
                if signals['current_new_short']:
                    entry_level = current_price
                else:
                    entry_level = cloud_low_current
                
                stop_loss_options = {
                    'conservative': cloud_high_current,
                    'aggressive': kijun_current,
                    'tight': tenkan_current
                }
                
                stop_loss = stop_loss_options['conservative']
                
                risk_amount = stop_loss - entry_level
                target1 = entry_level - (risk_amount * 1.5)
                target2 = entry_level - (risk_amount * 2.5)
                
            else:
                signal_type = 'NO_SIGNAL'
                entry_level = current_price
                stop_loss = None
                target1 = None
                target2 = None
                stop_loss_options = {}
            
            # Calculate risk metrics
            if stop_loss:
                risk_per_share = abs(entry_level - stop_loss)
                risk_percent = (risk_per_share / entry_level) * 100
                
                capital = 100000
                risk_amount_total = capital * 0.01
                position_size = int(risk_amount_total / risk_per_share) if risk_per_share > 0 else 0
            else:
                risk_per_share = 0
                risk_percent = 0
                position_size = 0
            
            # Add explicit BUY/SELL recommendations
            if signal_type == 'LONG':
                action = 'BUY'
                action_emoji = '🟢 BUY'
            elif signal_type == 'SHORT':
                action = 'SELL'
                action_emoji = '🔴 SELL'
            else:
                action = 'HOLD'
                action_emoji = '🟡 HOLD'
            
            return {
                'signal_type': signal_type,
                'action': action,
                'action_emoji': action_emoji,
                'entry_level': float(entry_level),
                'current_price': float(current_price),
                'stop_loss': float(stop_loss) if stop_loss else None,
                'stop_loss_options': {k: float(v) for k, v in stop_loss_options.items()},
                'target1': float(target1) if target1 else None,
                'target2': float(target2) if target2 else None,
                'risk_per_share': float(risk_per_share),
                'risk_percent': float(risk_percent),
                'position_size': int(position_size),
                'tenkan_level': float(tenkan_current),
                'kijun_level': float(kijun_current),
                'cloud_high': float(cloud_high_current),
                'cloud_low': float(cloud_low_current)
            }
            
        except Exception as e:
            print(f"❌ Error calculating trading levels: {e}")
            return None
    
    def detect_live_signal_changes(self, previous_result, current_result, max_distance_pct=0.5):
        """Detect when Ichimoku signals change in real-time (only within distance threshold)"""
        try:
            if not previous_result or not current_result:
                return []
            
            signal_changes = []
            
            # Calculate distance from current price to entry level
            current_price = current_result['current_price']
            entry_level = current_result['entry_level']
            
            # Calculate percentage distance
            distance_pct = abs((current_price - entry_level) / entry_level * 100)
            
            # Only proceed if within distance threshold
            if distance_pct > max_distance_pct:
                return []  # Price too far from entry - no alert
            
            # Check for new LONG signal
            if (not previous_result.get('current_long', False) and 
                current_result.get('current_long', False)):
                signal_changes.append({
                    'ticker': current_result['ticker'],
                    'signal_type': 'NEW_LONG',
                    'action': 'BUY',
                    'price': current_result['current_price'],
                    'entry_level': current_result['entry_level'],
                    'stop_loss': current_result['stop_loss'],
                    'target1': current_result['target1'],
                    'target2': current_result['target2'],
                    'risk_percent': current_result['risk_percent'],
                    'distance_pct': distance_pct,
                    'timestamp': self.get_ist_time(),
                    'message': f"🟢 NEW BUY Signal at ₹{current_result['current_price']:.2f} (Entry: ₹{entry_level:.2f}, Distance: {distance_pct:.2f}%)"
                })
            
            # Check for new SHORT signal
            if (not previous_result.get('current_short', False) and 
                current_result.get('current_short', False)):
                signal_changes.append({
                    'ticker': current_result['ticker'],
                    'signal_type': 'NEW_SHORT',
                    'action': 'SELL',
                    'price': current_result['current_price'],
                    'entry_level': current_result['entry_level'],
                    'stop_loss': current_result['stop_loss'],
                    'target1': current_result['target1'],
                    'target2': current_result['target2'],
                    'risk_percent': current_result['risk_percent'],
                    'distance_pct': distance_pct,
                    'timestamp': self.get_ist_time(),
                    'message': f"🔴 NEW SELL Signal at ₹{current_result['current_price']:.2f} (Entry: ₹{entry_level:.2f}, Distance: {distance_pct:.2f}%)"
                })
            
            # Check for signal exit (always show exits regardless of distance)
            if (previous_result.get('current_long', False) and 
                not current_result.get('current_long', False)):
                signal_changes.append({
                    'ticker': current_result['ticker'],
                    'signal_type': 'EXIT_LONG',
                    'action': 'EXIT_BUY',
                    'price': current_result['current_price'],
                    'distance_pct': distance_pct,
                    'timestamp': self.get_ist_time(),
                    'message': f"🟡 EXIT BUY Signal at ₹{current_result['current_price']:.2f}"
                })
            
            if (previous_result.get('current_short', False) and 
                not current_result.get('current_short', False)):
                signal_changes.append({
                    'ticker': current_result['ticker'],
                    'signal_type': 'EXIT_SHORT',
                    'action': 'EXIT_SELL',
                    'price': current_result['current_price'],
                    'distance_pct': distance_pct,
                    'timestamp': self.get_ist_time(),
                    'message': f"🟡 EXIT SELL Signal at ₹{current_result['current_price']:.2f}"
                })
            
            return signal_changes
            
        except Exception as e:
            print(f"❌ Signal change detection error: {e}")
            return []

def analyze_stock_live_ichimoku(ticker, ichimoku_analyzer, debug=False):
    """Analyze single stock for live Ichimoku signals"""
    try:
        if debug:
            print(f"☁️ Analyzing {ticker} for Ichimoku signals...")
        
        # Get data with live prices
        data = ichimoku_analyzer.get_stock_data_with_live_price(ticker)
        if data is None:
            return None
        
        is_live = data.attrs.get('is_live', False)
        live_method = data.attrs.get('live_method', 'historical')
        current_price = data['Close'].iloc[-1]
        
        if debug:
            live_indicator = "🔴 LIVE" if is_live else "📊 HIST"
            print(f"   {live_indicator} Price: ₹{current_price:.2f} ({live_method})")
        
        # Calculate Ichimoku
        try:
            ichimoku_data = ichimoku_analyzer.calculate_ichimoku(data)
            signals = ichimoku_analyzer.calculate_signals(ichimoku_data)
            trading_levels = ichimoku_analyzer.calculate_trading_levels(data, ichimoku_data, signals)
        except Exception as e:
            if debug:
                print(f"   ❌ Error in calculations: {e}")
            return None
        
        if not trading_levels:
            return None
        
        # Calculate RSI
        rsi = ichimoku_analyzer.calculate_rsi(data['Close'])
        
        # Get parameter status
        cloud_status = signals['cloud_bullish'].iloc[-1] if len(signals['cloud_bullish']) > 0 else False
        price_above = signals['price_above_cloud'].iloc[-1] if len(signals['price_above_cloud']) > 0 else False
        price_below = signals['price_below_cloud'].iloc[-1] if len(signals['price_below_cloud']) > 0 else False
        tk_status = signals['tk_bullish'].iloc[-1] if len(signals['tk_bullish']) > 0 else False
        chikou_bull = signals['chikou_bullish'].iloc[-1] if len(signals['chikou_bullish']) > 0 else False
        chikou_bear = signals['chikou_bearish'].iloc[-1] if len(signals['chikou_bearish']) > 0 else False
        
        if debug:
            print(f"   📊 Signal: {trading_levels['signal_type']}")
            print(f"   📈 RSI: {rsi:.1f}")
        
        result = {
            'ticker': ticker,
            'sector': get_stock_sector(ticker),
            'rsi': float(rsi),
            'is_live': is_live,
            'live_method': live_method,
            'analysis_timestamp': ichimoku_analyzer.get_ist_time(),
            **trading_levels,
            'cloud_bullish': bool(cloud_status),
            'price_above_cloud': bool(price_above),
            'price_below_cloud': bool(price_below),
            'tk_bullish': bool(tk_status),
            'chikou_bullish': bool(chikou_bull),
            'chikou_bearish': bool(chikou_bear),
            'current_long': signals['current_long'],
            'current_short': signals['current_short'],
            'current_new_long': signals['current_new_long'],
            'current_new_short': signals['current_new_short']
        }
        
        return result
        
    except Exception as e:
        print(f"❌ Analysis error for {ticker}: {e}")
        return None

def play_alert_sound():
    """Play alert sound for new signals"""
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

def analyze_multiple_stocks_live_ichimoku(tickers, update_interval=60, debug=False, max_distance_pct=0.5):
    """Continuously analyze multiple stocks for Ichimoku signals (with distance filter)"""
    
    print(f"☁️ LIVE ICHIMOKU TRADING SIGNALS ANALYZER")
    print(f"📊 Monitoring {len(tickers)} stocks")
    print(f"⏱️  Update interval: {update_interval} seconds")
    print(f"🎯 Distance Filter: ≤{max_distance_pct}% from entry price")
    if PYTZ_AVAILABLE:
        print(f"🔴 Live data during IST market hours (9:15 AM - 3:30 PM)")
    else:
        print(f"🔴 Live data during market hours (9:15 AM - 3:30 PM Local Time)")
    print("="*70)
    
    # Initialize analyzer
    ichimoku_analyzer = LiveIchimokuAnalyzer(
        tenkan_period=9,
        kijun_period=26,
        senkou_b_period=52,
        displacement=26
    )
    
    # Track previous results to detect signal changes
    previous_results = {}
    signal_history = []
    
    def single_analysis_cycle():
        """Run one analysis cycle for all stocks"""
        nonlocal previous_results, signal_history
        
        try:
            # Get current IST time
            if PYTZ_AVAILABLE:
                ist = pytz.timezone('Asia/Kolkata')
                current_time = datetime.now(ist)
                time_display = current_time.strftime('%H:%M:%S IST')
            else:
                current_time = datetime.now()
                time_display = current_time.strftime('%H:%M:%S')
            
            print(f"\n⏰ {time_display} - Ichimoku Analysis Update")
            print("-" * 50)
            
            all_signal_changes = []
            current_signals = []
            
            # Analyze each stock
            for ticker in tickers:
                try:
                    result = analyze_stock_live_ichimoku(ticker, ichimoku_analyzer, debug)
                    
                    if result:
                        live_indicator = "🔴" if result['is_live'] else "📊"
                        price_display = f"₹{result['current_price']:.2f}"
                        signal_type = result['signal_type']
                        
                        # Check for signal changes (with distance filter)
                        previous_result = previous_results.get(ticker)
                        signal_changes = ichimoku_analyzer.detect_live_signal_changes(
                            previous_result, result, max_distance_pct
                        )
                        
                        if signal_changes:
                            all_signal_changes.extend(signal_changes)
                            for change in signal_changes:
                                play_alert_sound()
                                action_msg = change.get('action', change.get('signal_type', 'UNKNOWN'))
                                print(f"🚨 {live_indicator} {ticker}: {change['message']}")
                        
                        # Display current status with distance info
                        if signal_type in ['LONG', 'SHORT']:
                            # Calculate distance from entry
                            distance_pct = abs((result['current_price'] - result['entry_level']) / result['entry_level'] * 100)
                            result['distance_pct'] = distance_pct
                            
                            # Only add to current signals if within distance threshold
                            if distance_pct <= max_distance_pct:
                                current_signals.append(result)
                                action_display = result.get('action_emoji', result['signal_type'])
                                print(f"   {live_indicator} {ticker}: {action_display} at {price_display} "
                                      f"(Entry: ₹{result['entry_level']:.2f}, Dist: {distance_pct:.2f}%)")
                            else:
                                # Signal exists but too far from entry
                                action_display = result.get('action_emoji', result['signal_type'])
                                print(f"   {live_indicator} {ticker}: {action_display} at {price_display} "
                                      f"(Entry: ₹{result['entry_level']:.2f}, Dist: {distance_pct:.2f}% - TOO FAR)")
                        else:
                            print(f"   {live_indicator} {ticker}: {price_display} - 🟡 HOLD")
                        
                        # Update previous results
                        previous_results[ticker] = result
                    else:
                        print(f"❌ {ticker}: No analysis result")
                    
                    time.sleep(0.2)
                    
                except Exception as e:
                    print(f"❌ {ticker}: Error - {str(e)[:50]}")
            
            # Display active signals table (only signals within distance threshold)
            if current_signals:
                print(f"\n📊 ACTIVE ICHIMOKU SIGNALS (≤{max_distance_pct}% from entry - {len(current_signals)} signals)")
                print("="*130)
                
                table_data = []
                headers = ['Ticker', 'Action', 'Price', 'Entry', 'Distance%', 'Stop Loss', 'Target 1', 'Risk%', 'RSI']
                
                for result in current_signals:
                    distance_pct = result.get('distance_pct', 0)
                    table_data.append([
                        result['ticker'],
                        result.get('action', result['signal_type']),
                        f"₹{result['current_price']:.2f}",
                        f"₹{result['entry_level']:.2f}",
                        f"{distance_pct:.2f}%",
                        f"₹{result['stop_loss']:.2f}" if result['stop_loss'] else "N/A",
                        f"₹{result['target1']:.2f}" if result['target1'] else "N/A",
                        f"{result['risk_percent']:.1f}%",
                        f"{result['rsi']:.0f}"
                    ])
                
                print(tabulate(table_data, headers=headers, tablefmt="grid"))
            
            # Display new signal changes
            if all_signal_changes:
                print(f"\n🚨 NEW SIGNAL ALERTS (≤{max_distance_pct}% from entry - {len(all_signal_changes)} alerts)")
                print("="*80)
                
                for change in all_signal_changes:
                    distance_info = f" (Dist: {change.get('distance_pct', 0):.2f}%)" if 'distance_pct' in change else ""
                    print(f"   {change['ticker']}: {change['message']}{distance_info}")
                
                signal_history.extend(all_signal_changes)
            
            return all_signal_changes
            
        except Exception as e:
            print(f"❌ Analysis cycle error: {e}")
            return []
    
    # Main monitoring loop
    try:
        while True:
            # Run analysis cycle
            new_signals = single_analysis_cycle()
            
            # Market status (count only actionable signals within distance threshold)
            is_market = ichimoku_analyzer.is_market_hours()
            market_status = "🟢 LIVE" if is_market else "🔴 CLOSED"
            
            active_buy = len([r for r in current_signals if r.get('signal_type') == 'LONG'])
            active_sell = len([r for r in current_signals if r.get('signal_type') == 'SHORT'])
            
            print(f"\n📊 Status: {market_status} | "
                  f"🟢 BUY: {active_buy} | 🔴 SELL: {active_sell} | "
                  f"Distance: ≤{max_distance_pct}% | "
                  f"Alerts Today: {len(signal_history)} | "
                  f"Next Update: {update_interval}s")
            
            # Wait for next update
            time.sleep(update_interval)
            
    except KeyboardInterrupt:
        print(f"\n🛑 Stopping live Ichimoku monitoring...")
        print(f"📊 Total signals detected: {len(signal_history)}")
        
        if signal_history:
            print(f"\n📋 SIGNAL SUMMARY:")
            for signal in signal_history[-10:]:
                action_display = signal.get('action', signal.get('signal_type', 'UNKNOWN'))
                print(f"   {signal['ticker']}: {action_display} "
                      f"at ₹{signal['price']:.2f}")
    
    except Exception as e:
        print(f"❌ Monitoring error: {e}")

def main():
    """Main function for Live Ichimoku Analysis"""
    parser = argparse.ArgumentParser(description="Live Ichimoku Trading Signals Analyzer")
    
    parser.add_argument('--interval', type=int, default=60, 
                       help='Update interval in seconds (default: 60)')
    parser.add_argument('--stocks', type=str, nargs='+',
                       help='Specific stocks to monitor (default: all from config)')
    parser.add_argument('--test-single', type=str, 
                       help='Test analysis on single ticker')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug output')
    parser.add_argument('--distance', type=float, default=0.5, 
                       help='Maximum distance from entry price in %% (default: 0.5)')
    parser.add_argument('--tenkan', type=int, default=9, 
                       help='Tenkan-Sen period (default: 9)')
    parser.add_argument('--kijun', type=int, default=26, 
                       help='Kijun-Sen period (default: 26)')
    parser.add_argument('--displacement', type=int, default=26, 
                       help='Displacement period (default: 26)')
    
    args = parser.parse_args()
    
    # Test single ticker
    if args.test_single:
        print(f"🧪 TESTING LIVE ICHIMOKU ANALYSIS: {args.test_single}")
        print("="*50)
        
        ichimoku_analyzer = LiveIchimokuAnalyzer(
            tenkan_period=args.tenkan,
            kijun_period=args.kijun,
            displacement=args.displacement
        )
        result = analyze_stock_live_ichimoku(args.test_single, ichimoku_analyzer, debug=True)
        
        if result:
            print(f"\n✅ Analysis successful!")
            print(f"   💰 Current Price: ₹{result['current_price']:.2f}")
            print(f"   📊 Signal: {result['signal_type']}")
            print(f"   🎯 Action: {result.get('action_emoji', result.get('action', 'HOLD'))}")
            print(f"   📈 RSI: {result['rsi']:.1f}")
            
            if result['signal_type'] != 'NO_SIGNAL':
                distance_pct = abs((result['current_price'] - result['entry_level']) / result['entry_level'] * 100)
                print(f"   🎯 Entry: ₹{result['entry_level']:.2f}")
                print(f"   📏 Distance: {distance_pct:.2f}% from entry")
                print(f"   🛑 Stop Loss: ₹{result['stop_loss']:.2f}")
                print(f"   🎯 Target 1: ₹{result['target1']:.2f}")
                print(f"   ⚠️  Risk: {result['risk_percent']:.1f}%")
                print(f"   📊 Position Size: {result['position_size']} shares")
                
                if distance_pct <= 0.5:
                    print(f"   ✅ ACTIONABLE: Within 0.5% distance threshold")
                else:
                    print(f"   ❌ TOO FAR: Outside 0.5% distance threshold (need {distance_pct:.2f}%)")
        else:
            print(f"❌ Analysis failed")
        return
    
    # Get tickers to monitor
    if args.stocks:
        tickers = args.stocks
    else:
        tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
    
    print(f"☁️ LIVE ICHIMOKU SIGNAL MONITORING")
    print(f"📈 Monitoring {len(tickers)} stocks: {', '.join(tickers[:5])}{'...' if len(tickers) > 5 else ''}")
    print(f"⏱️  Update every: {args.interval} seconds")
    print(f"🎯 Distance Filter: ≤{args.distance}% from entry price")
    print(f"🔊 Audio alerts: Enabled")
    if PYTZ_AVAILABLE:
        print(f"📊 Market hours: 9:15 AM - 3:30 PM IST (India Standard Time)")
    else:
        print(f"📊 Market hours: 9:15 AM - 3:30 PM (Local Time - install pytz for IST)")
    print(f"⚙️  Ichimoku Settings: T({args.tenkan}), K({args.kijun}), D({args.displacement})")
    print("="*70)
    
    # Start live monitoring with distance filter
    analyze_multiple_stocks_live_ichimoku(tickers, args.interval, args.debug, args.distance)

if __name__ == "__main__":
    main()