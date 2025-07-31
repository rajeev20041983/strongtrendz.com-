#!/usr/bin/env python
# live_supertrend_alerts.py - Live SuperTrend Breakout Alert System with Distance Filter

print("🔥 SUPERTREND ALERT SYSTEM: Only alerts within 0.5% distance from SuperTrend line")
print("🎯 Ensures fresh, timely signals - filters out late/distant signals")

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

# Optional timezone support for better market hours detection
try:
    import pytz
    TIMEZONE_AVAILABLE = True
except ImportError:
    TIMEZONE_AVAILABLE = False
    print("⚠️  pytz not available - install with 'pip install pytz' for better timezone handling")

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
    """Enhanced live data fetcher for real-time SuperTrend analysis"""
    
    def __init__(self):
        self.session_cache = {}
        
    def get_live_price_data(self, ticker):
        """Get live price with OHLCV data for SuperTrend calculation"""
        try:
            symbol = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
            
            # Method 1: Fast Info (Fastest for live price)
            try:
                if symbol not in self.session_cache:
                    self.session_cache[symbol] = yf.Ticker(symbol)
                
                stock = self.session_cache[symbol]
                fast_info = stock.fast_info
                
                # Get multiple price fields for better accuracy
                live_price = fast_info.get('lastPrice') or fast_info.get('regularMarketPrice')
                day_high = fast_info.get('dayHigh') or fast_info.get('regularMarketDayHigh', live_price)
                day_low = fast_info.get('dayLow') or fast_info.get('regularMarketDayLow', live_price)
                day_open = fast_info.get('open') or fast_info.get('regularMarketOpen', live_price)
                volume = fast_info.get('lastVolume') or fast_info.get('regularMarketVolume', 0)
                prev_close = fast_info.get('previousClose') or fast_info.get('regularMarketPreviousClose', live_price)
                market_state = fast_info.get('marketState', 'REGULAR')
                
                if live_price and live_price > 0:
                    return {
                        'price': float(live_price),
                        'open': float(day_open),
                        'high': float(day_high),
                        'low': float(day_low),
                        'volume': int(volume),
                        'prev_close': float(prev_close),
                        'timestamp': datetime.now(),
                        'method': 'fast_info',
                        'market_state': market_state
                    }
            except Exception as e:
                pass
            
            # Method 2: 1-minute history for more complete OHLCV
            try:
                stock = yf.Ticker(symbol)
                hist = stock.history(period="5d", interval="1m")
                
                if not hist.empty:
                    # Get today's data
                    today = datetime.now().date()
                    today_data = hist[hist.index.date == today]
                    
                    if not today_data.empty:
                        latest = today_data.iloc[-1]
                        
                        # Get day's OHLC from today's data
                        day_high = today_data['High'].max()
                        day_low = today_data['Low'].min()
                        day_open = today_data['Open'].iloc[0]
                        day_volume = today_data['Volume'].sum()
                        
                        # Get previous close from last trading day
                        prev_day_data = hist[hist.index.date < today]
                        prev_close = prev_day_data['Close'].iloc[-1] if not prev_day_data.empty else latest['Close']
                        
                        return {
                            'price': float(latest['Close']),
                            'open': float(day_open),
                            'high': float(day_high),
                            'low': float(day_low),
                            'volume': int(day_volume),
                            'prev_close': float(prev_close),
                            'timestamp': latest.name,
                            'method': '1min_history',
                            'market_state': 'REGULAR'
                        }
                    else:
                        # Fallback to latest available data
                        latest = hist.iloc[-1]
                        prev_latest = hist.iloc[-2] if len(hist) >= 2 else latest
                        
                        return {
                            'price': float(latest['Close']),
                            'open': float(latest['Open']),
                            'high': float(latest['High']),
                            'low': float(latest['Low']),
                            'volume': int(latest['Volume']),
                            'prev_close': float(prev_latest['Close']),
                            'timestamp': latest.name,
                            'method': '1min_fallback',
                            'market_state': 'CLOSED'
                        }
            except Exception as e:
                pass
            
            return None
            
        except Exception as e:
            print(f"❌ Live data error for {ticker}: {e}")
            return None

class LiveSuperTrendAnalyzer:
    """Live SuperTrend Analysis with exact Pine Script implementation"""
    
    def __init__(self, periods=10, multiplier=3.0, use_builtin_atr=True, max_distance_pct=0.5):
        self.periods = periods
        self.multiplier = multiplier
        self.use_builtin_atr = use_builtin_atr
        self.max_distance_pct = max_distance_pct
        self.live_fetcher = LiveDataFetcher()
        
    def is_market_hours(self):
        """Check if NSE market is open"""
        try:
            if TIMEZONE_AVAILABLE:
                import pytz
                india_tz = pytz.timezone('Asia/Kolkata')
                now = datetime.now(india_tz)
            else:
                now = datetime.now()
            
            # Skip weekends
            if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
                return False
            
            # Market hours: 9:15 AM to 3:30 PM IST
            market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
            market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
            
            return market_open <= now <= market_close
            
        except Exception as e:
            return True
    
    def calculate_true_range(self, data):
        """Calculate True Range exactly like Pine Script"""
        try:
            high = data['High']
            low = data['Low']
            close_prev = data['Close'].shift(1)
            
            # True Range = max(high-low, abs(high-close_prev), abs(low-close_prev))
            tr1 = high - low
            tr2 = abs(high - close_prev)
            tr3 = abs(low - close_prev)
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            return true_range
            
        except Exception as e:
            return pd.Series([0] * len(data), index=data.index)

    def calculate_atr_wilders(self, data, periods):
        """Calculate ATR using Wilder's smoothing method - EXACT FORMULA"""
        try:
            if len(data) < periods:
                return pd.Series([0] * len(data), index=data.index)
            
            # Calculate True Range
            true_range = self.calculate_true_range(data)
            
            # Initialize ATR array
            atr_values = []
            
            for i in range(len(data)):
                if i < periods - 1:
                    atr_values.append(0)
                elif i == periods - 1:
                    # First ATR value: Simple average of first n True Range values
                    initial_atr = true_range.iloc[:periods].mean()
                    atr_values.append(initial_atr)
                else:
                    # Wilder's smoothing: ATR = (Previous ATR x (n - 1) + TR) / n
                    previous_atr = atr_values[i-1]
                    current_tr = true_range.iloc[i]
                    current_atr = (previous_atr * (periods - 1) + current_tr) / periods
                    atr_values.append(current_atr)
            
            return pd.Series(atr_values, index=data.index)
            
        except Exception as e:
            return pd.Series([0] * len(data), index=data.index)

    def calculate_atr_sma(self, data, periods):
        """Calculate ATR using Simple Moving Average of True Range"""
        try:
            if len(data) < periods:
                return pd.Series([0] * len(data), index=data.index)
            
            true_range = self.calculate_true_range(data)
            atr = true_range.rolling(window=periods).mean()
            
            return atr.fillna(0)
            
        except Exception as e:
            return pd.Series([0] * len(data), index=data.index)

    def calculate_supertrend(self, data, debug=False):
        """
        Calculate SuperTrend using EXACT FORMULAS:
        1. ATR = (Previous ATR x (n - 1) + TR) / n (Wilder's smoothing)
        2. Upperband = (High + Low) / 2 + (Multiplier x ATR) 
        3. Lowerband = (High + Low) / 2 - (Multiplier x ATR)
        4. SuperTrend follows price with proper ratcheting logic
        """
        try:
            if len(data) < self.periods + 10:
                return None
            
            # Source = hl2 = (High + Low) / 2
            hl2 = (data['High'] + data['Low']) / 2
            
            # Calculate ATR using the specified method
            if self.use_builtin_atr:
                atr = self.calculate_atr_wilders(data, self.periods)
                atr_method = "Wilder's Smoothing"
            else:
                atr = self.calculate_atr_sma(data, self.periods)
                atr_method = "SMA of True Range"
            
            # Calculate Upper and Lower Bands
            basic_upperband = hl2 + (self.multiplier * atr)
            basic_lowerband = hl2 - (self.multiplier * atr)
            
            # Initialize arrays for SuperTrend calculation
            upperband = []
            lowerband = []
            trend = []
            supertrend = []
            
            close = data['Close']
            
            # Calculate SuperTrend with proper ratcheting logic
            for i in range(len(data)):
                current_upper = basic_upperband.iloc[i]
                current_lower = basic_lowerband.iloc[i]
                current_close = close.iloc[i]
                
                if i == 0:
                    # First values
                    upperband.append(current_upper)
                    lowerband.append(current_lower)
                    trend.append(1)  # Start with uptrend
                    supertrend.append(current_lower)  # Start with lower band
                else:
                    # Previous values
                    prev_upper = upperband[i-1]
                    prev_lower = lowerband[i-1]
                    prev_close = close.iloc[i-1]
                    prev_trend = trend[i-1]
                    
                    # Upper band ratcheting logic
                    if current_upper < prev_upper or prev_close > prev_upper:
                        final_upper = current_upper
                    else:
                        final_upper = prev_upper
                    
                    # Lower band ratcheting logic  
                    if current_lower > prev_lower or prev_close < prev_lower:
                        final_lower = current_lower
                    else:
                        final_lower = prev_lower
                    
                    upperband.append(final_upper)
                    lowerband.append(final_lower)
                    
                    # Trend determination logic
                    if prev_trend == -1 and current_close > prev_lower:
                        current_trend = 1  # Change to bullish
                    elif prev_trend == 1 and current_close < prev_upper:
                        current_trend = -1  # Change to bearish
                    else:
                        current_trend = prev_trend  # Maintain current trend
                    
                    trend.append(current_trend)
                    
                    # SuperTrend value based on current trend
                    if current_trend == 1:
                        supertrend.append(final_lower)  # Bullish: use lower band as support
                    else:
                        supertrend.append(final_upper)  # Bearish: use upper band as resistance
            
            # Convert to pandas series
            result_index = data.index
            upperband_series = pd.Series(upperband, index=result_index)
            lowerband_series = pd.Series(lowerband, index=result_index)
            trend_series = pd.Series(trend, index=result_index)
            supertrend_series = pd.Series(supertrend, index=result_index)
            
            # Generate signals (trend changes)
            buy_signals = []
            sell_signals = []
            
            for i in range(len(trend)):
                if i == 0:
                    buy_signals.append(False)
                    sell_signals.append(False)
                else:
                    # Buy signal: trend changes from bearish (-1) to bullish (1)
                    if trend[i] == 1 and trend[i-1] == -1:
                        buy_signals.append(True)
                        sell_signals.append(False)
                    # Sell signal: trend changes from bullish (1) to bearish (-1)
                    elif trend[i] == -1 and trend[i-1] == 1:
                        buy_signals.append(False)
                        sell_signals.append(True)
                    else:
                        buy_signals.append(False)
                        sell_signals.append(False)
            
            buy_signals_series = pd.Series(buy_signals, index=result_index)
            sell_signals_series = pd.Series(sell_signals, index=result_index)
            
            # Current values
            current_price = close.iloc[-1]
            current_supertrend = supertrend_series.iloc[-1]
            current_trend = trend_series.iloc[-1]
            current_buy_signal = buy_signals_series.iloc[-1]
            current_sell_signal = sell_signals_series.iloc[-1]
            
            return {
                'supertrend': supertrend_series,
                'trend': trend_series,
                'buy_signals': buy_signals_series,
                'sell_signals': sell_signals_series,
                'upper_band': upperband_series,
                'lower_band': lowerband_series,
                'atr': atr,
                'hl2': hl2,
                'current_price': current_price,
                'current_supertrend': current_supertrend,
                'current_trend': current_trend,
                'current_buy_signal': current_buy_signal,
                'current_sell_signal': current_sell_signal,
                'atr_method': atr_method
            }
            
        except Exception as e:
            if debug:
                print(f"❌ SuperTrend calculation error: {e}")
            return None

    def get_stock_data_with_live_price(self, ticker, lookback_days=100):
        """Get stock data with live price updates for SuperTrend calculation"""
        try:
            symbol = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
            
            # Get enough data for SuperTrend calculation
            days_needed = lookback_days + 30
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_needed)
            
            # Download historical data
            stock = yf.Ticker(symbol)
            data = stock.history(start=start_date, end=end_date)
            
            if data.empty or len(data) < self.periods + 20:
                return None
            
            # Clean data
            data = data.dropna()
            
            # Get live price data
            live_data = self.live_fetcher.get_live_price_data(ticker)
            is_market_open = self.is_market_hours()
            
            if live_data:
                # Update or add latest bar with live data 
                current_date = pd.Timestamp.now().normalize()
                
                if current_date in data.index:
                    # Update existing bar with live data
                    idx = current_date
                    data.at[idx, 'Close'] = live_data['price']
                    data.at[idx, 'High'] = max(data.at[idx, 'High'], live_data['high'])
                    data.at[idx, 'Low'] = min(data.at[idx, 'Low'], live_data['low'])
                    data.at[idx, 'Volume'] = max(data.at[idx, 'Volume'], live_data['volume'])
                    
                    # If market is open, ensure open price is set correctly
                    if is_market_open and data.at[idx, 'Open'] == 0:
                        data.at[idx, 'Open'] = live_data['open']
                else:
                    # Add new bar for today with live data
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
                data.attrs['market_state'] = live_data.get('market_state', 'REGULAR')
                data.attrs['is_market_open'] = is_market_open
                
            else:
                data.attrs['is_live'] = False
                data.attrs['live_method'] = 'historical'
                data.attrs['market_state'] = 'CLOSED' if not is_market_open else 'REGULAR'
                data.attrs['is_market_open'] = is_market_open
            
            return data
                
        except Exception as e:
            print(f"❌ Data error for {ticker}: {e}")
            return None

    def detect_live_supertrend_signals(self, data, max_distance_pct=0.5, debug=False):
        """Detect live SuperTrend breakout signals within distance threshold"""
        try:
            if data is None or len(data) < self.periods + 20:
                return None
            
            # Calculate SuperTrend
            st_result = self.calculate_supertrend(data, debug)
            
            if st_result is None:
                return None
            
            # Get current values
            is_live = data.attrs.get('is_live', False)
            live_method = data.attrs.get('live_method', 'historical')
            market_state = data.attrs.get('market_state', 'REGULAR')
            is_market_open = data.attrs.get('is_market_open', False)
            current_price = st_result['current_price']
            
            # Calculate distance from SuperTrend
            distance_pct = ((current_price - st_result['current_supertrend']) / current_price) * 100
            
            # Calculate RSI for additional context
            rsi = self.calculate_rsi(data['Close'])
            
            # Calculate volume ratio
            volume_ratio = self.calculate_volume_ratio(data)
            
            # Determine signal type and strength - ONLY WITHIN DISTANCE THRESHOLD
            signals = []
            
            if st_result['current_buy_signal']:
                # Only trigger BUY alert if price is within max_distance_pct of SuperTrend
                if abs(distance_pct) <= max_distance_pct:
                    signal = {
                        'ticker': '',  # Will be set by caller
                        'signal_type': 'SUPERTREND_BUY',
                        'signal_source': 'TREND_REVERSAL',
                        'price': float(current_price),
                        'supertrend': float(st_result['current_supertrend']),
                        'trend': int(st_result['current_trend']),
                        'trend_direction': 'BULLISH',
                        'buy_signal': True,
                        'sell_signal': False,
                        'strength': 100.0,  # Maximum strength for fresh signals
                        'distance_pct': float(distance_pct),
                        'atr': float(st_result['atr'].iloc[-1]),
                        'rsi': float(rsi),
                        'volume_ratio': float(volume_ratio),
                        'is_live': is_live,
                        'live_method': live_method,
                        'market_state': market_state,
                        'is_market_open': is_market_open,
                        'timestamp': datetime.now(),
                        'distance_filter': f"Within {max_distance_pct}%"
                    }
                    signals.append(signal)
                    
                    if debug:
                        print(f"   🟢 BUY SIGNAL QUALIFIED: Distance {distance_pct:+.2f}% within {max_distance_pct}% threshold")
                elif debug:
                    print(f"   ⚪ BUY SIGNAL FILTERED: Distance {distance_pct:+.2f}% exceeds {max_distance_pct}% threshold")
            
            elif st_result['current_sell_signal']:
                # Only trigger SELL alert if price is within max_distance_pct of SuperTrend
                if abs(distance_pct) <= max_distance_pct:
                    signal = {
                        'ticker': '',  # Will be set by caller
                        'signal_type': 'SUPERTREND_SELL',
                        'signal_source': 'TREND_REVERSAL',
                        'price': float(current_price),
                        'supertrend': float(st_result['current_supertrend']),
                        'trend': int(st_result['current_trend']),
                        'trend_direction': 'BEARISH',
                        'buy_signal': False,
                        'sell_signal': True,
                        'strength': 100.0,  # Maximum strength for fresh signals
                        'distance_pct': float(distance_pct),
                        'atr': float(st_result['atr'].iloc[-1]),
                        'rsi': float(rsi),
                        'volume_ratio': float(volume_ratio),
                        'is_live': is_live,
                        'live_method': live_method,
                        'market_state': market_state,
                        'is_market_open': is_market_open,
                        'timestamp': datetime.now(),
                        'distance_filter': f"Within {max_distance_pct}%"
                    }
                    signals.append(signal)
                    
                    if debug:
                        print(f"   🔴 SELL SIGNAL QUALIFIED: Distance {distance_pct:+.2f}% within {max_distance_pct}% threshold")
                elif debug:
                    print(f"   ⚪ SELL SIGNAL FILTERED: Distance {distance_pct:+.2f}% exceeds {max_distance_pct}% threshold")
            
            # Return current SuperTrend status even if no fresh signals
            current_status = {
                'ticker': '',
                'price': float(current_price),
                'supertrend': float(st_result['current_supertrend']),
                'trend': int(st_result['current_trend']),
                'trend_direction': 'BULLISH' if st_result['current_trend'] == 1 else 'BEARISH',
                'distance_pct': float(distance_pct),
                'atr': float(st_result['atr'].iloc[-1]),
                'rsi': float(rsi),
                'volume_ratio': float(volume_ratio),
                'is_live': is_live,
                'live_method': live_method,
                'market_state': market_state,
                'is_market_open': is_market_open,
                'signals': signals,
                'has_signal': len(signals) > 0,
                'distance_filter_applied': max_distance_pct,
                'signal_filtered': (st_result['current_buy_signal'] or st_result['current_sell_signal']) and len(signals) == 0
            }
            
            return current_status
            
        except Exception as e:
            if debug:
                print(f"❌ SuperTrend signal detection error: {e}")
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

    def calculate_volume_ratio(self, data, period=20):
        """Calculate volume ratio vs average"""
        try:
            if len(data) < period:
                return 1.0
            
            current_volume = data['Volume'].iloc[-1]
            avg_volume = data['Volume'].rolling(window=period).mean().iloc[-1]
            
            if pd.isna(avg_volume) or avg_volume == 0:
                return 1.0
            
            return current_volume / avg_volume
        except:
            return 1.0

def analyze_stock_live_supertrend(ticker, analyzer, debug=False):
    """Analyze single stock for live SuperTrend signals"""
    try:
        if debug:
            print(f"📊 Analyzing {ticker} for SuperTrend signals...")
        
        # Get data with live prices
        data = analyzer.get_stock_data_with_live_price(ticker)
        if data is None:
            if debug:
                print(f"   ❌ {ticker}: No data available")
            return None
        
        # Detect SuperTrend signals
        result = analyzer.detect_live_supertrend_signals(data, analyzer.max_distance_pct, debug)
        
        if result:
            # Set ticker for result and all signals
            result['ticker'] = ticker
            for signal in result.get('signals', []):
                signal['ticker'] = ticker
        
        return result
        
    except Exception as e:
        print(f"❌ Analysis error for {ticker}: {e}")
        return None

def play_alert_sound():
    """Play alert sound for SuperTrend signals"""
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

def analyze_multiple_stocks_live_supertrend(tickers, periods=10, multiplier=3.0, 
                                          use_builtin_atr=True, max_distance_pct=0.5, 
                                          update_interval=60, debug=False):
    """Continuously analyze multiple stocks for SuperTrend signals within distance threshold"""
    
    atr_method = "Wilder's Smoothing" if use_builtin_atr else "SMA Method"
    
    print(f"🚀 LIVE SUPERTREND BREAKOUT ANALYZER")
    print(f"📊 Strategy: Classic SuperTrend Trend Reversal Signals")
    print(f"📈 Monitoring {len(tickers)} stocks")
    print(f"📅 SuperTrend Settings: Periods {periods}, Multiplier {multiplier}")
    print(f"📊 ATR Method: {atr_method}")
    print(f"🎯 Distance Filter: Max {max_distance_pct}% from SuperTrend")
    print(f"⏱️  Update interval: {update_interval} seconds")
    print(f"🔴 Live data during market hours (9:15 AM - 3:30 PM IST)")
    print(f"🔥 ALERTS: SuperTrend BUY & SELL within {max_distance_pct}% distance only")
    print("="*70)
    
    # Initialize analyzer with distance filter
    analyzer = LiveSuperTrendAnalyzer(periods=periods, multiplier=multiplier, 
                                    use_builtin_atr=use_builtin_atr, max_distance_pct=max_distance_pct)
    
    # Check live data capabilities
    print(f"\n🔧 SUPERTREND SETUP:")
    print(f"   📡 Data Sources: yfinance fast_info + 1min history")
    print(f"   🕒 Market Hours: 9:15 AM - 3:30 PM IST (Mon-Fri)")
    print(f"   🌍 Timezone: {'IST (pytz)' if TIMEZONE_AVAILABLE else 'System Time'}")
    print(f"   📊 Fallback: Historical data when live unavailable")
    print(f"   📈 Signals: Trend reversals from SuperTrend crossovers")
    print(f"   🎯 Distance Filter: Only alerts within {max_distance_pct}% of SuperTrend")
    print(f"   🚫 Filtered Out: Signals beyond {max_distance_pct}% distance (too late)")
    
    # Test live data on first ticker
    test_ticker = tickers[0] if tickers else "RELIANCE"
    print(f"   🧪 Testing SuperTrend on {test_ticker}...")
    
    test_data = analyzer.live_fetcher.get_live_price_data(test_ticker)
    is_market_open = analyzer.is_market_hours()
    
    if test_data:
        print(f"   ✅ Live data working: ₹{test_data['price']:.2f} ({test_data['method']})")
        print(f"   📊 Market State: {test_data.get('market_state', 'UNKNOWN')}")
    else:
        print(f"   ⚠️  Live data unavailable - using historical data")
    
    print(f"   📈 Market Status: {'🟢 OPEN' if is_market_open else '🔴 CLOSED'}")
    print("="*70)
    
    # Track previous signals to avoid duplicate alerts
    previous_signals = {}
    signal_history = []
    
    def single_analysis_cycle():
        """Run one analysis cycle for all stocks"""
        nonlocal previous_signals, signal_history
        
        try:
            current_time = datetime.now()
            print(f"\n⏰ {current_time.strftime('%H:%M:%S')} - SuperTrend Analysis")
            print("-" * 50)
            
            all_new_signals = []
            
            # Analyze each stock
            for ticker in tickers:
                try:
                    result = analyze_stock_live_supertrend(ticker, analyzer, debug)
                    
                    if result:
                        is_live = result['is_live']
                        is_market_open = result.get('is_market_open', False)
                        market_state = result.get('market_state', 'UNKNOWN')
                        
                        # Enhanced live data indicators
                        if is_live:
                            if is_market_open:
                                live_indicator = "🔴 LIVE"
                            else:
                                live_indicator = "🟡 LIVE-CLOSED" 
                        else:
                            live_indicator = "📊 HIST"
                        
                        # Market state display
                        if market_state in ['REGULAR', 'OPEN']:
                            market_display = "OPEN"
                        elif market_state in ['CLOSED', 'POST_MARKET', 'PRE_MARKET']:
                            market_display = market_state
                        else:
                            market_display = "OPEN" if is_market_open else "CLOSED"
                        
                        price_display = f"₹{result['price']:.2f}"
                        supertrend_display = f"₹{result['supertrend']:.2f}"
                        trend_emoji = "🟢" if result['trend_direction'] == 'BULLISH' else "🔴"
                        distance_display = f"{result['distance_pct']:+.2f}%"
                        
                        if result.get('has_signal', False) and result.get('signals', []):
                            # New SuperTrend signal detected!
                            for signal in result['signals']:
                                try:
                                    signal_key = f"{ticker}_{signal['signal_type']}_{int(signal['strength'])}"
                                    
                                    # Check if this is a new signal
                                    if signal_key not in previous_signals:
                                        all_new_signals.append(signal)
                                        previous_signals[signal_key] = current_time
                                        
                                        # Play alert sound
                                        play_alert_sound()
                                        
                                        signal_emoji = "🚀" if signal['signal_type'] == 'SUPERTREND_BUY' else "📉"
                                        data_quality_emoji = "⚡" if is_live else "📊"
                                        
                                        print(f"🚨 {live_indicator} {ticker}: {signal_emoji} {signal['signal_type']} "
                                              f"at {price_display} (ST: {supertrend_display}) {data_quality_emoji}")
                                        print(f"   📊 Trend: {result['trend_direction']} | Distance: {distance_display} | "
                                              f"RSI: {signal['rsi']:.0f} | Vol: {signal['volume_ratio']:.1f}x | Market: {market_display}")
                                    else:
                                        print(f"   {live_indicator} {ticker}: Continuing signal at {price_display}")
                                except Exception as se:
                                    print(f"❌ {ticker}: Signal processing error - {str(se)[:50]}")
                        else:
                            # No signals - show current SuperTrend status
                            status_text = f"{price_display} (ST: {supertrend_display} {trend_emoji}) {distance_display}"
                            
                            # Check if signal was filtered due to distance
                            if result.get('signal_filtered', False):
                                status_text += " ⚠️FILTERED"
                            
                            print(f"   {live_indicator} {ticker}: {status_text} - {market_display}")
                    else:
                        print(f"❌ {ticker}: No analysis result")
                    
                    time.sleep(0.1)  # Rate limiting
                    
                except Exception as e:
                    print(f"❌ {ticker}: Error - {str(e)[:50]}")
            
            # Display new SuperTrend signals in detailed table
            if all_new_signals:
                print(f"\n🚨 NEW SUPERTREND ALERTS ({len(all_new_signals)} signals)")
                print(f"🎯 All signals within {analyzer.max_distance_pct}% distance from SuperTrend")
                print("="*120)
                
                table_data = []
                headers = ['Ticker', 'Signal', 'Price', 'SuperTrend', 'Distance%', 
                          'Trend', 'RSI', 'Volume', 'ATR', 'Filter']
                
                for signal in all_new_signals:
                    try:
                        trend_display = f"{signal['trend_direction']} {'🟢' if signal['trend_direction'] == 'BULLISH' else '🔴'}"
                        
                        table_data.append([
                            signal.get('ticker', 'N/A'),
                            signal.get('signal_type', 'Unknown').replace('_', ' '),
                            f"₹{signal.get('price', 0):.2f}",
                            f"₹{signal.get('supertrend', 0):.2f}",
                            f"{signal.get('distance_pct', 0):+.2f}%",
                            trend_display,
                            f"{signal.get('rsi', 50):.0f}",
                            f"{signal.get('volume_ratio', 1):.1f}x",
                            f"₹{signal.get('atr', 0):.2f}",
                            signal.get('distance_filter', 'Within 0.5%')
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
            
            # Market status and summary
            is_market = analyzer.is_market_hours()
            market_status = "🟢 LIVE" if is_market else "🔴 CLOSED"
            
            # Signal type summary
            buy_signals = len([s for s in signal_history if s.get('signal_type') == 'SUPERTREND_BUY'])
            sell_signals = len([s for s in signal_history if s.get('signal_type') == 'SUPERTREND_SELL'])
            
            print(f"\n📊 Status: {market_status} | "
                  f"SuperTrend Signals Today: {len(signal_history)} (BUY: {buy_signals}, SELL: {sell_signals}) | "
                  f"Next Update: {update_interval}s")
            
            # Wait for next update
            time.sleep(update_interval)
            
    except KeyboardInterrupt:
        print(f"\n🛑 Stopping live SuperTrend monitoring...")
        print(f"📊 Total SuperTrend signals detected: {len(signal_history)}")
        
        if signal_history:
            print(f"\n📋 SUPERTREND SIGNAL SUMMARY:")
            
            # Separate by type
            buy_signals = [s for s in signal_history if s.get('signal_type') == 'SUPERTREND_BUY']
            sell_signals = [s for s in signal_history if s.get('signal_type') == 'SUPERTREND_SELL']
            
            if buy_signals:
                print(f"\n🚀 SUPERTREND BUY ({len(buy_signals)} signals):")
                for signal in buy_signals[-10:]:  # Last 10
                    print(f"   {signal['ticker']}: ₹{signal['price']:.2f} "
                          f"(ST: ₹{signal['supertrend']:.2f}) - RSI: {signal['rsi']:.0f}")
            
            if sell_signals:
                print(f"\n📉 SUPERTREND SELL ({len(sell_signals)} signals):")
                for signal in sell_signals[-10:]:  # Last 10
                    print(f"   {signal['ticker']}: ₹{signal['price']:.2f} "
                          f"(ST: ₹{signal['supertrend']:.2f}) - RSI: {signal['rsi']:.0f}")
    
    except Exception as e:
        print(f"❌ Monitoring error: {e}")

def main():
    """Main function for Live SuperTrend Breakout Analysis"""
    parser = argparse.ArgumentParser(description="Live SuperTrend Breakout Alert System")
    
    parser.add_argument('--periods', type=int, default=10, 
                       help='ATR periods for SuperTrend (default: 10)')
    parser.add_argument('--multiplier', type=float, default=3.0, 
                       help='ATR multiplier for SuperTrend (default: 3.0)')
    parser.add_argument('--use-sma-atr', action='store_true', 
                       help='Use SMA of True Range instead of Wilder\'s smoothing')
    parser.add_argument('--max-distance', type=float, default=0.5, 
                       help='Maximum distance %% from SuperTrend for alerts (default: 0.5)')
    parser.add_argument('--interval', type=int, default=60, 
                       help='Update interval in seconds (default: 60)')
    parser.add_argument('--stocks', type=str, nargs='+',
                       help='Specific stocks to monitor (default: all from config)')
    parser.add_argument('--test-single', type=str, 
                       help='Test analysis on single ticker')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug output')
    
    args = parser.parse_args()
    
    # ATR calculation method
    use_builtin_atr = not args.use_sma_atr
    
    # Test single ticker
    if args.test_single:
        print(f"🧪 TESTING LIVE SUPERTREND ANALYSIS: {args.test_single}")
        print("="*50)
        
        analyzer = LiveSuperTrendAnalyzer(periods=args.periods, multiplier=args.multiplier, 
                                        use_builtin_atr=use_builtin_atr, max_distance_pct=args.max_distance)
        result = analyze_stock_live_supertrend(args.test_single, analyzer, debug=True)
        
        if result:
            print(f"\n✅ Analysis successful!")
            print(f"   💰 Current Price: ₹{result['price']:.2f}")
            print(f"   📈 SuperTrend: ₹{result['supertrend']:.2f}")
            print(f"   📊 Trend: {result['trend_direction']}")
            print(f"   📊 Distance: {result['distance_pct']:+.2f}%")
            print(f"   🎯 Distance Filter: {args.max_distance}%")
            print(f"   📈 RSI: {result['rsi']:.0f}")
            print(f"   🔴 Live Data: {result['is_live']}")
            
            if result['has_signal']:
                for signal in result['signals']:
                    print(f"   🔥 {signal['signal_type']}: Trend reversal detected within {args.max_distance}%!")
            elif result.get('signal_filtered', False):
                print(f"   ⚠️  Signal filtered: Distance {result['distance_pct']:+.2f}% exceeds {args.max_distance}% threshold")
            else:
                print(f"   ⚪ No fresh SuperTrend signals")
        else:
            print(f"❌ Analysis failed")
        return
    
    # Get tickers to monitor
    if args.stocks:
        tickers = args.stocks
    else:
        tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
    
    print(f"🎯 LIVE SUPERTREND MONITORING")
    print(f"📈 Strategy: Classic SuperTrend Trend Reversal Detection")
    print(f"📊 Monitoring {len(tickers)} stocks: {', '.join(tickers[:5])}{'...' if len(tickers) > 5 else ''}")
    print(f"📅 SuperTrend: Periods {args.periods}, Multiplier {args.multiplier}")
    atr_method = "Wilder's Smoothing" if use_builtin_atr else "SMA Method"
    print(f"📊 ATR Method: {atr_method}")
    print(f"🎯 Distance Filter: Maximum {args.max_distance}% from SuperTrend")
    print(f"⏱️  Update every: {args.interval} seconds")
    print(f"🔊 Audio alerts: Enabled")
    print(f"📊 Market hours: 9:15 AM - 3:30 PM IST")
    print("="*70)
    
    print(f"\n🎯 SUPERTREND SIGNAL CRITERIA:")
    print(f"   🚀 BUY SIGNAL: Trend changes from BEARISH to BULLISH (price crosses above SuperTrend)")
    print(f"   📉 SELL SIGNAL: Trend changes from BULLISH to BEARISH (price crosses below SuperTrend)")
    print(f"   🔥 DISTANCE FILTER: Only alerts when price is within {args.max_distance}% of SuperTrend")
    print(f"   📊 SuperTrend = HL2 ± (Multiplier × ATR) with ratcheting logic")
    print(f"   🛑 SuperTrend acts as dynamic trailing stop loss")
    print(f"   📈 Only fresh, timely trend reversal signals trigger alerts")
    print(f"   ⚠️  Signals beyond {args.max_distance}% distance are filtered out (too late)")
    
    # Start live monitoring
    analyze_multiple_stocks_live_supertrend(tickers, args.periods, args.multiplier, 
                                          use_builtin_atr, args.max_distance, args.interval, args.debug)

if __name__ == "__main__":
    main()