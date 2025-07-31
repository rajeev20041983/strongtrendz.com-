#!/usr/bin/env python
# chandelier_exit.py - Chandelier Exit Trading System (Based on Pine Script Logic)

# 🔥 DEBUG: Print this immediately when script starts
print("🔥 SCRIPT VERSION: UPDATED - ALL SIGNALS HTML GENERATION")
print("🔥 If you see this, the updated script is running!")

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

# Add your project directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import your existing configurations
try:
    from app import config
    print("✅ Successfully loaded config with tickers")
except ImportError:
    print("❌ Config not found! Using default tickers")
    # Default configuration if config file not found
    class DefaultConfig:
        TOP_STOCKS = [
            {'symbol': 'RELIANCE'},
            {'symbol': 'TCS'},
            {'symbol': 'HDFCBANK'},
            {'symbol': 'INFY'},
            {'symbol': 'HINDUNILVR'},
            {'symbol': 'ICICIBANK'},
            {'symbol': 'KOTAKBANK'},
            {'symbol': 'ITC'},
            {'symbol': 'LT'},
            {'symbol': 'SBIN'},
            {'symbol': 'BHARTIARTL'},
            {'symbol': 'ASIANPAINT'},
            {'symbol': 'MARUTI'},
            {'symbol': 'AXISBANK'},
            {'symbol': 'BAJFINANCE'},
            {'symbol': 'WIPRO'},
            {'symbol': 'NESTLEIND'},
            {'symbol': 'ULTRACEMCO'},
            {'symbol': 'TITAN'},
            {'symbol': 'POWERGRID'}
        ]
        OUTPUT_DIR = 'output'
    
    config = DefaultConfig()

# Sector mapping for Indian stocks
SECTOR_MAPPING = {
    'RELIANCE': 'Oil & Gas',
    'TCS': 'Information Technology',
    'HDFCBANK': 'Banking',
    'INFY': 'Information Technology',
    'HINDUNILVR': 'FMCG',
    'ICICIBANK': 'Banking',
    'KOTAKBANK': 'Banking',
    'ITC': 'FMCG',
    'LT': 'Infrastructure',
    'SBIN': 'Banking',
    'BHARTIARTL': 'Telecom',
    'ASIANPAINT': 'Paints & Chemicals',
    'MARUTI': 'Automobiles',
    'AXISBANK': 'Banking',
    'BAJFINANCE': 'Financial Services',
    'WIPRO': 'Information Technology',
    'NESTLEIND': 'FMCG',
    'ULTRACEMCO': 'Cement',
    'TITAN': 'Consumer Durables',
    'POWERGRID': 'Power',
    'ADANIPORTS': 'Infrastructure',
    'BAJAJFINSV': 'Financial Services',
    'HCLTECH': 'Information Technology',
    'TATASTEEL': 'Metals & Mining',
    'COALINDIA': 'Metals & Mining',
    'NTPC': 'Power',
    'TECHM': 'Information Technology',
    'JSWSTEEL': 'Metals & Mining',
    'HEROMOTOCO': 'Automobiles',
    'BRITANNIA': 'FMCG',
    'DRREDDY': 'Pharmaceuticals',
    'APOLLOHOSP': 'Healthcare',
    'SUNPHARMA': 'Pharmaceuticals',
    'BPCL': 'Oil & Gas',
    'TATAMOTORS': 'Automobiles',
    'GRASIM': 'Textiles',
    'INDUSINDBK': 'Banking',
    'M&M': 'Automobiles',
    'EICHERMOT': 'Automobiles',
    'CIPLA': 'Pharmaceuticals',
    'BAJAJ-AUTO': 'Automobiles',
    'ONGC': 'Oil & Gas',
    'DIVISLAB': 'Pharmaceuticals',
    'HINDALCO': 'Metals & Mining',
    'TATACONSUM': 'FMCG',
    'SHREECEM': 'Cement',
    'SBILIFE': 'Insurance'
}

def get_stock_sector(ticker):
    """Get sector for a stock ticker"""
    return SECTOR_MAPPING.get(ticker, 'Others')

warnings.filterwarnings("ignore")

def get_stock_data(ticker, lookback_days=100):
    """Get stock data for analysis with proper error handling"""
    try:
        # Add .NS for NSE stocks
        symbol = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
        
        # Get enough data for lookback + buffer
        days_needed = lookback_days + 50  # Extra buffer for weekends/holidays
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_needed)
        
        # Download data
        stock = yf.Ticker(symbol)
        data = stock.history(start=start_date, end=end_date)
        
        if data.empty or len(data) < lookback_days:
            print(f"   ⚠️  {ticker}: Insufficient data ({len(data)} days)")
            return None
        
        # Clean data
        data = data.dropna()
        
        if len(data) < lookback_days:
            print(f"   ⚠️  {ticker}: Insufficient clean data ({len(data)} days)")
            return None
        
        return data
        
    except Exception as e:
        print(f"   ❌ {ticker}: Data fetch error - {str(e)}")
        return None

def calculate_atr(data, period=22):
    """Calculate Average True Range exactly like Pine Script ta.atr()"""
    try:
        if len(data) < period + 1:
            return pd.Series([0] * len(data), index=data.index)
        
        # True Range calculation
        high_low = data['High'] - data['Low']
        high_close = abs(data['High'] - data['Close'].shift(1))
        low_close = abs(data['Low'] - data['Close'].shift(1))
        
        # Get maximum of the three
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        
        # Calculate ATR using RMA (like Pine Script)
        atr = true_range.ewm(alpha=1/period, adjust=False).mean()
        
        return atr
        
    except Exception as e:
        return pd.Series([0] * len(data), index=data.index)

def calculate_chandelier_exit(data, length=22, multiplier=3.0, use_close=True, debug=False):
    """
    Calculate Chandelier Exit exactly like Pine Script logic
    """
    try:
        if len(data) < length + 5:
            return None, None, None, None, None
        
        # Calculate ATR
        atr = calculate_atr(data, length) * multiplier
        
        # Calculate highest/lowest over period
        if use_close:
            highest_vals = data['Close'].rolling(window=length).max()
            lowest_vals = data['Close'].rolling(window=length).min()
        else:
            highest_vals = data['High'].rolling(window=length).max()
            lowest_vals = data['Low'].rolling(window=length).min()
        
        # Initialize arrays
        long_stop = []
        short_stop = []
        direction = []
        buy_signals = []
        sell_signals = []
        
        # Initialize first values
        prev_long_stop = highest_vals.iloc[length-1] - atr.iloc[length-1]
        prev_short_stop = lowest_vals.iloc[length-1] + atr.iloc[length-1]
        current_dir = 1  # Start with long direction
        
        # Process each bar (starting from length index)
        for i in range(length, len(data)):
            current_close = data['Close'].iloc[i]
            prev_close = data['Close'].iloc[i-1]
            
            # Calculate raw stops
            raw_long_stop = highest_vals.iloc[i] - atr.iloc[i]
            raw_short_stop = lowest_vals.iloc[i] + atr.iloc[i]
            
            # Long stop ratcheting logic (from Pine Script)
            if prev_close > prev_long_stop:
                current_long_stop = max(raw_long_stop, prev_long_stop)
            else:
                current_long_stop = raw_long_stop
            
            # Short stop ratcheting logic (from Pine Script)
            if prev_close < prev_short_stop:
                current_short_stop = min(raw_short_stop, prev_short_stop)
            else:
                current_short_stop = raw_short_stop
            
            # Direction logic (from Pine Script)
            if current_close > prev_short_stop:
                new_dir = 1
            elif current_close < prev_long_stop:
                new_dir = -1
            else:
                new_dir = current_dir
            
            # Signal detection
            buy_signal = (new_dir == 1 and current_dir == -1)
            sell_signal = (new_dir == -1 and current_dir == 1)
            
            # Store values
            long_stop.append(current_long_stop)
            short_stop.append(current_short_stop)
            direction.append(new_dir)
            buy_signals.append(buy_signal)
            sell_signals.append(sell_signal)
            
            # Update for next iteration
            prev_long_stop = current_long_stop
            prev_short_stop = current_short_stop
            current_dir = new_dir
            
            if debug and i == len(data) - 1:  # Debug last value
                print(f"   🐛 DEBUG CE: Close={current_close:.2f}, LongStop={current_long_stop:.2f}, ShortStop={current_short_stop:.2f}, Dir={new_dir}")
        
        # Create series with proper index
        result_index = data.index[length:]
        
        long_stop_series = pd.Series(long_stop, index=result_index)
        short_stop_series = pd.Series(short_stop, index=result_index)
        direction_series = pd.Series(direction, index=result_index)
        buy_signals_series = pd.Series(buy_signals, index=result_index)
        sell_signals_series = pd.Series(sell_signals, index=result_index)
        
        return long_stop_series, short_stop_series, direction_series, buy_signals_series, sell_signals_series
        
    except Exception as e:
        if debug:
            print(f"   🐛 DEBUG: Chandelier Exit calculation error: {e}")
        return None, None, None, None, None

def calculate_rsi(prices, period=14):
    """Calculate RSI (Relative Strength Index) manually"""
    try:
        if len(prices) < period + 1:
            return 50  # Neutral RSI if insufficient data
        
        delta = prices.diff().dropna()
        if len(delta) < period:
            return 50
        
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        # Avoid division by zero
        rs = gain / loss.replace(0, 0.001)  # Small value to avoid inf
        rsi = 100 - (100 / (1 + rs))
        
        final_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
        return max(0, min(100, final_rsi))  # Ensure RSI is between 0-100
    except Exception as e:
        return 50  # Return neutral RSI on any error

def detect_sideways_market(data, threshold=0.05):
    """Detect if market is moving sideways (low volatility)"""
    try:
        if len(data) < 20:
            return False
        
        # Calculate price range over period
        high_20 = data['High'].rolling(window=20).max().iloc[-1]
        low_20 = data['Low'].rolling(window=20).min().iloc[-1]
        current_price = data['Close'].iloc[-1]
        
        price_range = (high_20 - low_20) / current_price
        
        # If price range is less than threshold %, consider it sideways
        return price_range < threshold
    except:
        return False

def enhanced_volume_confirmation(data, current_volume, lookback_days):
    """Enhanced volume analysis for signal confirmation"""
    try:
        if data is None or len(data) < 5:
            return {'volume_strength': 'WEAK', 'volume_trend': 'NEUTRAL', 'volume_sma_ratio': 1.0}
        
        if lookback_days < 5:
            lookback_days = 5  # Minimum lookback
        
        # Volume moving averages with safety checks
        vol_sma_short = data['Volume'].rolling(window=min(5, len(data))).mean().iloc[-1]
        vol_sma_long = data['Volume'].rolling(window=min(lookback_days, len(data))).mean().iloc[-1]
        
        # Handle NaN values
        if pd.isna(vol_sma_short) or pd.isna(vol_sma_long) or vol_sma_long == 0:
            return {'volume_strength': 'WEAK', 'volume_trend': 'NEUTRAL', 'volume_sma_ratio': 1.0}
        
        # Volume strength classification
        volume_ratio = current_volume / vol_sma_long
        
        if volume_ratio > 2.0:
            volume_strength = 'VERY_HIGH'
        elif volume_ratio > 1.5:
            volume_strength = 'HIGH'
        elif volume_ratio > 0.8:
            volume_strength = 'NORMAL'
        else:
            volume_strength = 'WEAK'
        
        # Volume trend
        short_long_ratio = vol_sma_short / vol_sma_long
        if short_long_ratio > 1.2:
            volume_trend = 'INCREASING'
        elif short_long_ratio < 0.8:
            volume_trend = 'DECREASING'
        else:
            volume_trend = 'NEUTRAL'
        
        return {
            'volume_strength': volume_strength,
            'volume_trend': volume_trend,
            'volume_sma_ratio': volume_ratio
        }
    except Exception as e:
        # Return safe defaults on any error
        return {'volume_strength': 'WEAK', 'volume_trend': 'NEUTRAL', 'volume_sma_ratio': 1.0}

def calculate_proper_metrics(data, volume_days=20, momentum_days=5):
    """
    Calculate volume and momentum using ONLY trading days
    """
    # Get latest values
    latest = data.iloc[-1]
    current_price = latest['Close']
    current_volume = latest['Volume']
    
    # 📊 VOLUME RATIO - Last N TRADING DAYS
    if len(data) >= volume_days + 1:
        # Get exactly N trading days (excluding current day)
        volume_period = data['Volume'].iloc[-(volume_days+1):-1]  # Last N trading sessions
        avg_volume = volume_period.mean()
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
    else:
        # Fallback if less than N days of data
        avg_volume = data['Volume'].mean()
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
    
    # 🚀 MOMENTUM - Last N TRADING DAYS
    if len(data) >= momentum_days + 1:
        # Get price from N trading days ago
        price_n_days_ago = data['Close'].iloc[-(momentum_days+1)]  # N+1 rows back = N days ago
        momentum = ((current_price - price_n_days_ago) / price_n_days_ago) * 100
    else:
        momentum = 0
    
    return volume_ratio, momentum, len(data)

def calculate_advanced_signals(data, current_price, long_stop, short_stop, direction):
    """Calculate advanced trading signals"""
    
    # Stop distance analysis
    if direction == 1:  # Long position
        stop_distance = (current_price - long_stop) / current_price * 100
        stop_level = long_stop
    else:  # Short position
        stop_distance = (short_stop - current_price) / current_price * 100
        stop_level = short_stop
    
    # Volatility (20-day ATR approximation)
    if len(data) >= 20:
        high_low = data['High'] - data['Low']
        high_close = abs(data['High'] - data['Close'].shift(1))
        low_close = abs(data['Low'] - data['Close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=20).mean().iloc[-1]
        volatility_score = (atr / current_price) * 100
    else:
        volatility_score = 0
    
    # Price trend (20-day SMA direction)
    if len(data) >= 20:
        sma_20 = data['Close'].rolling(window=20).mean()
        if len(sma_20) >= 2:
            sma_trend = ((sma_20.iloc[-1] - sma_20.iloc[-2]) / sma_20.iloc[-2]) * 100
        else:
            sma_trend = 0
    else:
        sma_trend = 0
    
    # RSI calculation
    rsi = calculate_rsi(data['Close'])
    
    # Market condition analysis
    is_sideways = detect_sideways_market(data)
    
    return {
        'stop_distance': stop_distance,
        'stop_level': stop_level,
        'volatility_score': volatility_score,
        'sma_trend': sma_trend,
        'rsi': rsi,
        'is_sideways_market': is_sideways,
        'direction': direction
    }

def analyze_stock_comprehensive(ticker, atr_length=22, atr_multiplier=3.0, use_close=True, 
                              volume_days=20, momentum_days=5, debug=False):
    """
    Comprehensive stock analysis with Chandelier Exit system
    """
    try:
        print(f"📊 Analyzing {ticker} (using Chandelier Exit system)...")
        
        # Initialize variables with safe defaults
        volume_analysis = {'volume_strength': 'NORMAL', 'volume_trend': 'NEUTRAL', 'volume_sma_ratio': 1.0}
        advanced = {
            'stop_distance': 0,
            'stop_level': 0,
            'volatility_score': 0,
            'sma_trend': 0,
            'rsi': 50,
            'is_sideways_market': False,
            'direction': 1
        }
        
        # Get data
        data = get_stock_data(ticker, atr_length + 50)
        if data is None:
            return None
        
        print(f"   📅 Data: {len(data)} trading days available")
        
        # Calculate Chandelier Exit
        long_stop, short_stop, direction, buy_signals, sell_signals = calculate_chandelier_exit(
            data, atr_length, atr_multiplier, use_close, debug
        )
        
        if long_stop is None or short_stop is None or direction is None:
            print(f"   ⚠️  {ticker}: Chandelier Exit calculation failed")
            return None
        
        # Get latest values
        latest = data.iloc[-1]
        current_price = latest['Close']
        current_volume = latest['Volume']
        
        # Get current Chandelier Exit values
        current_long_stop = long_stop.iloc[-1]
        current_short_stop = short_stop.iloc[-1]
        current_direction = direction.iloc[-1]
        current_buy_signal = buy_signals.iloc[-1] if len(buy_signals) > 0 else False
        current_sell_signal = sell_signals.iloc[-1] if len(sell_signals) > 0 else False
        
        print(f"   📊 CE Direction: {'LONG' if current_direction == 1 else 'SHORT'}")
        print(f"   📈 Long Stop: ₹{current_long_stop:.2f}")
        print(f"   📉 Short Stop: ₹{current_short_stop:.2f}")
        
        # Calculate metrics using proper trading days
        volume_ratio, momentum, trading_days_used = calculate_proper_metrics(
            data, volume_days, momentum_days
        )
        
        # Enhanced volume confirmation
        try:
            volume_analysis = enhanced_volume_confirmation(data, current_volume, volume_days)
            if debug:
                print(f"   🐛 DEBUG: Volume analysis successful - {volume_analysis}")
        except Exception as e:
            if debug:
                print(f"   🐛 DEBUG: Volume analysis error: {e}")
        
        print(f"   📊 Volume: Current {current_volume:,.0f} vs {volume_days}-day avg = {volume_ratio:.1f}x ({volume_analysis['volume_strength']})")
        print(f"   🚀 Momentum: {momentum:+.1f}% ({momentum_days} trading days)")
        
        # Calculate advanced signals
        try:
            advanced = calculate_advanced_signals(
                data, current_price, current_long_stop, current_short_stop, current_direction
            )
            print(f"   📈 RSI: {advanced['rsi']:.1f}")
            print(f"   🛑 Stop Distance: {advanced['stop_distance']:.2f}%")
            
            # Market condition warnings
            if advanced['is_sideways_market']:
                print(f"   ⚠️  WARNING: Sideways market detected")
                
        except Exception as e:
            if debug:
                print(f"   🐛 DEBUG: Advanced analysis error: {e}")
        
        # Determine signal type and strength
        signal_type = 'HOLD'
        buy_strength = 0
        sell_strength = 0
        stop_loss = current_price
        
        # Signal generation based on Chandelier Exit
        if current_buy_signal:
            signal_type = 'STRONG_BUY'
            buy_strength = advanced['stop_distance']  # Distance from stop as strength
            stop_loss = current_long_stop
            print(f"   🎯 BUY Signal detected!")
            
        elif current_sell_signal:
            signal_type = 'STRONG_SELL'
            sell_strength = advanced['stop_distance']  # Distance from stop as strength
            stop_loss = current_short_stop
            print(f"   🎯 SELL Signal detected!")
            
        elif current_direction == 1:
            signal_type = 'WEAK_BUY'  # Following long trend
            buy_strength = advanced['stop_distance'] * 0.5
            stop_loss = current_long_stop
            
        else:
            signal_type = 'WEAK_SELL'  # Following short trend
            sell_strength = advanced['stop_distance'] * 0.5
            stop_loss = current_short_stop
        
        # Risk management
        risk_per_share = abs(current_price - stop_loss)
        
        # Position sizing (1% risk on 100k capital)
        capital = 100000
        risk_amount = capital * 0.01
        position_size = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
        
        result = {
            'ticker': ticker,
            'sector': get_stock_sector(ticker),
            'signal_type': signal_type,
            'current_price': float(current_price),
            'long_stop': float(current_long_stop),
            'short_stop': float(current_short_stop),
            'stop_loss': float(stop_loss),
            'direction': int(current_direction),
            'buy_signal': bool(current_buy_signal),
            'sell_signal': bool(current_sell_signal),
            'buy_strength': float(buy_strength),
            'sell_strength': float(sell_strength),
            'volume_ratio': float(volume_ratio),
            'volume_analysis': volume_analysis,
            'momentum': float(momentum),
            'position_size': int(position_size),
            'risk_per_share': float(risk_per_share),
            'trading_days_used': int(trading_days_used),
            'volume_period': f"{volume_days} trading days",
            'momentum_period': f"{momentum_days} trading days",
            'ce_settings': f"ATR{atr_length}_M{atr_multiplier}_Close{use_close}",
            'stop_distance': float(advanced.get('stop_distance', 0)),
            'volatility_score': float(advanced.get('volatility_score', 0)),
            'sma_trend': float(advanced.get('sma_trend', 0)),
            'rsi': float(advanced.get('rsi', 50)),
            'is_sideways_market': bool(advanced.get('is_sideways_market', False))
        }
        
        print(f"   🎯 Signal: {signal_type}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error analyzing {ticker}: {e}")
        return None

def analyze_all_stocks(atr_length=22, atr_multiplier=3.0, use_close=True, volume_days=20, 
                      momentum_days=5, max_workers=3, debug=False):
    """Analyze all stocks with comprehensive metrics"""
    
    # Get tickers from config
    tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
    
    print(f"\n🚀 COMPREHENSIVE CHANDELIER EXIT ANALYSIS")
    print(f"📊 Analyzing {len(tickers)} stocks")
    print(f"📈 ATR Length: {atr_length} periods")
    print(f"📊 ATR Multiplier: {atr_multiplier}x")
    print(f"🎯 Use Close: {use_close}")
    print(f"📊 Volume Period: {volume_days} trading days")
    print(f"🚀 Momentum Period: {momentum_days} trading days")
    print("="*70)
    
    all_signals = []
    
    # Analyze stocks
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(analyze_stock_comprehensive, ticker, atr_length, atr_multiplier, 
                          use_close, volume_days, momentum_days, debug): ticker 
            for ticker in tickers
        }
        
        completed = 0
        successful = 0
        failed = 0
        
        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            completed += 1
            
            try:
                result = future.result(timeout=30)
                if result:
                    all_signals.append(result)
                    successful += 1
                    direction_str = "LONG" if result['direction'] == 1 else "SHORT"
                    signal_indicator = ""
                    if result['buy_signal']:
                        signal_indicator = " 🟢BUY"
                    elif result['sell_signal']:
                        signal_indicator = " 🔴SELL"
                    print(f"✅ {ticker} ({completed}/{len(tickers)}) - {result['signal_type']} - {direction_str}{signal_indicator}")
                else:
                    failed += 1
                    print(f"⚪ {ticker} ({completed}/{len(tickers)}) - No data")
            except concurrent.futures.TimeoutError:
                failed += 1
                print(f"⏰ {ticker} ({completed}/{len(tickers)}) - Timeout")
            except Exception as e:
                failed += 1
                print(f"❌ {ticker} ({completed}/{len(tickers)}) - Error: {str(e)[:50]}")
        
        print(f"\n📊 ANALYSIS SUMMARY:")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📈 Total signals: {len(all_signals)}")
    
    return all_signals

def filter_signals_by_type(all_signals, signal_types):
    """Filter signals by type"""
    return [signal for signal in all_signals if signal['signal_type'] in signal_types]

def organize_signals_by_sector(signals):
    """Organize signals by sector"""
    sector_signals = {}
    for signal in signals:
        sector = signal.get('sector', 'Others')
        if sector not in sector_signals:
            sector_signals[sector] = []
        sector_signals[sector].append(signal)
    
    # Sort sectors by number of signals (descending)
    sorted_sectors = dict(sorted(sector_signals.items(), key=lambda x: len(x[1]), reverse=True))
    return sorted_sectors

def display_sector_wise_signals(all_signals, signal_title="ALL"):
    """Display all signals organized by sector"""
    
    if not all_signals:
        print(f"\n❌ No signals found!")
        return
    
    # Organize by sector
    sector_signals = organize_signals_by_sector(all_signals)
    
    print(f"\n🏢 SECTOR-WISE {signal_title} SIGNALS ANALYSIS")
    print(f"📊 Total Signals: {len(all_signals)} across {len(sector_signals)} sectors")
    print("="*130)
    
    sector_summary = []
    
    for sector, signals in sector_signals.items():
        if not signals:
            continue
            
        # Sort signals within sector
        sorted_signals = sort_signals_properly(signals)
        
        # Calculate sector statistics
        strong_buy = len([s for s in signals if s['signal_type'] == 'STRONG_BUY'])
        weak_buy = len([s for s in signals if s['signal_type'] == 'WEAK_BUY'])
        strong_sell = len([s for s in signals if s['signal_type'] == 'STRONG_SELL'])
        weak_sell = len([s for s in signals if s['signal_type'] == 'WEAK_SELL'])
        hold = len([s for s in signals if s['signal_type'] == 'HOLD'])
        
        avg_volume = sum(s['volume_ratio'] for s in signals) / len(signals)
        avg_momentum = sum(s['momentum'] for s in signals) / len(signals)
        avg_rsi = sum(s.get('rsi', 50) for s in signals) / len(signals)
        
        print(f"\n🏢 {sector.upper()} SECTOR ({len(signals)} stocks)")
        print(f"   📊 Strong Buy: {strong_buy} | Weak Buy: {weak_buy} | Strong Sell: {strong_sell} | Weak Sell: {weak_sell} | Hold: {hold}")
        print(f"   📈 Avg Volume: {avg_volume:.1f}x | Avg Momentum: {avg_momentum:+.1f}% | Avg RSI: {avg_rsi:.0f}")
        print("-" * 130)
        
        # Display top signals in this sector
        table_data = []
        headers = ['Rank', 'Ticker', 'Signal', 'Price', 'Stop Loss', 'Distance%', 
                  'Direction', 'Volume', 'RSI', 'Momentum%', 'Score', 'Qty']
        
        for i, signal in enumerate(sorted_signals, 1):
            if 'BUY' in signal['signal_type']:
                strength = signal['buy_strength']
            else:
                strength = signal['sell_strength']
            
            # Calculate composite score
            volume_score = min(signal['volume_ratio'] * 10, 30)
            rsi_score = 50 - abs(signal.get('rsi', 50) - 50)
            momentum_score = signal['momentum'] if 'BUY' in signal['signal_type'] else -signal['momentum']
            stop_score = signal.get('stop_distance', 0)
            
            composite_score = (strength * 0.4 + stop_score * 0.3 + volume_score * 0.2 + 
                             max(momentum_score, 0) * 0.1)
            
            # Direction display
            direction_display = "LONG🟢" if signal['direction'] == 1 else "SHORT🔴"
            
            # Signal indicators
            signal_display = signal['signal_type'].replace('_', ' ')
            if signal['buy_signal']:
                signal_display += " 🟢"
            elif signal['sell_signal']:
                signal_display += " 🔴"
            
            # RSI interpretation
            rsi_value = signal.get('rsi', 50)
            rsi_display = f"{rsi_value:.0f}"
            if rsi_value > 70:
                rsi_display += "🔴"
            elif rsi_value < 30:
                rsi_display += "🟢"
            
            # Volume with strength indicator
            volume_strength = signal['volume_analysis'].get('volume_strength', 'NORMAL')
            volume_display = f"{signal['volume_ratio']:.1f}x"
            if volume_strength == 'VERY_HIGH':
                volume_display += "🟢"
            elif volume_strength == 'HIGH':
                volume_display += "🟡"
            elif volume_strength == 'WEAK':
                volume_display += "🔴"
            
            table_data.append([
                i,
                signal['ticker'],
                signal_display,
                f"₹{signal['current_price']:.2f}",
                f"₹{signal['stop_loss']:.2f}",
                f"{signal.get('stop_distance', 0):.2f}%",
                direction_display,
                volume_display,
                rsi_display,
                f"{signal['momentum']:+.1f}%",
                f"{composite_score:.1f}",
                signal['position_size']
            ])
        
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        
        # Store sector summary
        sector_summary.append({
            'sector': sector,
            'total': len(signals),
            'strong_buy': strong_buy,
            'weak_buy': weak_buy,
            'strong_sell': strong_sell,
            'weak_sell': weak_sell,
            'hold': hold,
            'avg_volume': avg_volume,
            'avg_momentum': avg_momentum,
            'avg_rsi': avg_rsi
        })
    
    # Overall sector summary
    print(f"\n📊 SECTOR-WISE SUMMARY")
    print("="*100)
    
    summary_table = []
    summary_headers = ['Sector', 'Total', 'Strong Buy', 'Weak Buy', 'Strong Sell', 'Weak Sell', 'Hold', 'Avg Vol', 'Avg Mom%', 'Avg RSI']
    
    for sector_data in sector_summary:
        summary_table.append([
            sector_data['sector'],
            sector_data['total'],
            sector_data['strong_buy'],
            sector_data['weak_buy'],
            sector_data['strong_sell'],
            sector_data['weak_sell'],
            sector_data['hold'],
            f"{sector_data['avg_volume']:.1f}x",
            f"{sector_data['avg_momentum']:+.1f}%",
            f"{sector_data['avg_rsi']:.0f}"
        ])
    
    print(tabulate(summary_table, headers=summary_headers, tablefmt="grid"))
    
    # Sector insights
    most_bullish = max(sector_summary, key=lambda x: x['strong_buy'] + x['weak_buy'])
    most_bearish = max(sector_summary, key=lambda x: x['strong_sell'] + x['weak_sell'])
    highest_volume = max(sector_summary, key=lambda x: x['avg_volume'])
    highest_momentum = max(sector_summary, key=lambda x: x['avg_momentum'])
    
    print(f"\n🎯 SECTOR INSIGHTS:")
    print(f"   🟢 Most Bullish: {most_bullish['sector']} ({most_bullish['strong_buy'] + most_bullish['weak_buy']} buy signals)")
    print(f"   🔴 Most Bearish: {most_bearish['sector']} ({most_bearish['strong_sell'] + most_bearish['weak_sell']} sell signals)")
    print(f"   📊 Highest Volume: {highest_volume['sector']} ({highest_volume['avg_volume']:.1f}x avg)")
    print(f"   🚀 Highest Momentum: {highest_momentum['sector']} ({highest_momentum['avg_momentum']:+.1f}% avg)")
    
    return sector_signals

def sort_signals_properly(signals):
    """Sort signals by comprehensive metrics ranking"""
    
    if not signals:
        return signals
    
    # Determine if these are BUY or SELL signals
    is_buy_signals = any('BUY' in s['signal_type'] for s in signals)
    
    # Multi-criteria sorting for better ranking
    if is_buy_signals:
        # Sort by: 1) Signal strength, 2) Stop distance, 3) Volume ratio, 4) Momentum
        signals.sort(key=lambda x: (
            x['buy_strength'],
            x.get('stop_distance', 0),
            x['volume_ratio'],
            x['momentum']
        ), reverse=True)
    else:
        # Sort by: 1) Signal strength, 2) Stop distance, 3) Volume ratio, 4) Momentum (descending for shorts)
        signals.sort(key=lambda x: (
            x['sell_strength'],
            x.get('stop_distance', 0),
            x['volume_ratio'],
            -x['momentum']  # Negative momentum is better for sells
        ), reverse=True)
    
    return signals

def display_top_signals(signals, signal_title, top_n=None):
    """Display signals with comprehensive ranking"""
    
    if not signals:
        print(f"\n❌ No {signal_title} signals found!")
        return
    
    # Sort signals properly
    signals = sort_signals_properly(signals)
    
    # If top_n is None, show ALL signals
    if top_n is None:
        display_signals = signals
    else:
        display_signals = signals[:top_n]
    
    print(f"\n🏆 ALL {signal_title} SIGNALS ({len(display_signals)} found)")
    print(f"📊 Chandelier Exit Trading System - Comprehensive Ranking")
    print("="*120)
    
    # Prepare table
    table_data = []
    headers = ['Rank', 'Ticker', 'Signal', 'Price', 'Stop Loss', 'Distance%', 
              'Direction', 'Volume', 'RSI', 'Momentum%', 'Score', 'Qty', 'Risk₹']
    
    for i, signal in enumerate(display_signals, 1):
        if 'BUY' in signal['signal_type']:
            strength = signal['buy_strength']
        else:
            strength = signal['sell_strength']
        
        # Calculate composite score for ranking
        volume_score = min(signal['volume_ratio'] * 10, 30)  # Cap at 30
        rsi_score = 50 - abs(signal.get('rsi', 50) - 50)  # Distance from 50
        momentum_score = signal['momentum'] if 'BUY' in signal['signal_type'] else -signal['momentum']
        stop_score = signal.get('stop_distance', 0)
        
        composite_score = (strength * 0.4 + stop_score * 0.3 + volume_score * 0.2 + 
                         max(momentum_score, 0) * 0.1)
        
        # Direction display
        direction_display = "LONG🟢" if signal['direction'] == 1 else "SHORT🔴"
        
        # Signal indicators
        signal_display = signal['signal_type'].replace('_', ' ')
        if signal['buy_signal']:
            signal_display += " 🟢"
        elif signal['sell_signal']:
            signal_display += " 🔴"
        
        # RSI interpretation
        try:
            rsi_value = signal.get('rsi', 50)
            rsi_display = f"{rsi_value:.0f}"
            if rsi_value > 70:
                rsi_display += "🔴"  # Overbought
            elif rsi_value < 30:
                rsi_display += "🟢"  # Oversold
        except:
            rsi_display = "50"
        
        # Volume with strength indicator
        try:
            volume_strength = signal['volume_analysis']['volume_strength']
            volume_display = f"{signal['volume_ratio']:.1f}x"
            if volume_strength == 'VERY_HIGH':
                volume_display += "🟢"
            elif volume_strength == 'HIGH':
                volume_display += "🟡"
            elif volume_strength == 'WEAK':
                volume_display += "🔴"
        except:
            volume_display = f"{signal['volume_ratio']:.1f}x"
        
        table_data.append([
            i,
            signal['ticker'],
            signal_display,
            f"₹{signal['current_price']:.2f}",
            f"₹{signal['stop_loss']:.2f}",
            f"{signal.get('stop_distance', 0):.2f}%",
            direction_display,
            volume_display,
            rsi_display,
            f"{signal['momentum']:+.1f}%",
            f"{composite_score:.1f}",
            signal['position_size'],
            f"₹{signal['risk_per_share']:.2f}"
        ])
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Enhanced summary statistics
    avg_stop_distance = sum(signal.get('stop_distance', 0) for signal in display_signals) / len(display_signals)
    avg_volume = sum(signal['volume_ratio'] for signal in display_signals) / len(display_signals)
    avg_momentum = sum(signal['momentum'] for signal in display_signals) / len(display_signals)
    avg_rsi = sum(signal.get('rsi', 50) for signal in display_signals) / len(display_signals)
    long_count = sum(1 for signal in display_signals if signal['direction'] == 1)
    short_count = len(display_signals) - long_count
    fresh_signals = sum(1 for signal in display_signals if signal.get('buy_signal') or signal.get('sell_signal'))
    high_volume_count = sum(1 for signal in display_signals 
                           if signal['volume_analysis']['volume_strength'] in ['HIGH', 'VERY_HIGH'])
    
    print(f"\n📊 COMPREHENSIVE SUMMARY:")
    print(f"   🎯 Total {signal_title} signals: {len(display_signals)}")
    print(f"   📈 Average stop distance: {avg_stop_distance:.2f}%")
    print(f"   📊 Average volume ratio: {avg_volume:.1f}x")
    print(f"   🚀 Average momentum: {avg_momentum:+.1f}%")
    print(f"   📈 Average RSI: {avg_rsi:.1f}")
    print(f"   🟢 Long positions: {long_count}")
    print(f"   🔴 Short positions: {short_count}")
    print(f"   ⚡ Fresh signals: {fresh_signals}")
    print(f"   📊 High volume signals: {high_volume_count}")
    
    # Quality metrics
    quality_signals = sum(1 for signal in display_signals 
                         if signal.get('stop_distance', 0) > 2.0 and 
                         signal['volume_ratio'] > 1.2)
    
    print(f"\n🏆 QUALITY ANALYSIS:")
    print(f"   ⭐ High quality signals: {quality_signals} (Stop>2% + Volume>1.2x)")
    print(f"   📊 Quality ratio: {quality_signals/len(display_signals)*100:.1f}%")
    
    print(f"\n🏆 RANKING METHODOLOGY:")
    print(f"   📊 Multi-criteria ranking: Signal Strength (40%) + Stop Distance (30%)")
    print(f"   📊                        + Volume Ratio (20%) + Momentum (10%)")
    print(f"   🎯 Higher composite score = Better opportunity")
    print(f"   🟢🔴 Fresh signals (direction changes) are prioritized")
    print(f"   📊 Score combines risk/reward, volume confirmation, and momentum")

def generate_comprehensive_html(all_signals, atr_length, atr_multiplier, use_close, 
                              volume_days, momentum_days, output_dir):
    """Generate comprehensive HTML report"""
    
    if not all_signals:
        print("❌ No signals to generate report")
        return None
    
    # Separate signals by type - show ALL strong signals
    strong_buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY'])
    strong_sell_signals = filter_signals_by_type(all_signals, ['STRONG_SELL'])
    weak_buy_signals = filter_signals_by_type(all_signals, ['WEAK_BUY'])
    weak_sell_signals = filter_signals_by_type(all_signals, ['WEAK_SELL'])
    hold_signals = filter_signals_by_type(all_signals, ['HOLD'])
    
    # Sort properly
    strong_buy_signals = sort_signals_properly(strong_buy_signals) if strong_buy_signals else []
    strong_sell_signals = sort_signals_properly(strong_sell_signals) if strong_sell_signals else []
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Chandelier Exit Analysis - {datetime.now().strftime('%Y-%m-%d')}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 15px 35px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                color: white;
                padding: 40px;
                border-radius: 15px;
                margin-bottom: 30px;
            }}
            .header h1 {{
                margin: 0;
                font-size: 2.8em;
                margin-bottom: 10px;
            }}
            .header p {{
                margin: 5px 0;
                font-size: 1.1em;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minval(200px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            .stat-card {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
            }}
            .stat-card h3 {{
                margin: 0 0 10px 0;
                font-size: 2em;
            }}
            .section {{
                margin: 40px 0;
            }}
            .section h2 {{
                color: #333;
                border-bottom: 3px solid #667eea;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                border-radius: 10px;
                overflow: hidden;
            }}
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background: #f8f9fa;
                font-weight: bold;
                position: sticky;
                top: 0;
            }}
            tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
            tr:hover {{
                background-color: #f0f0f0;
            }}
            .rank {{
                font-weight: bold;
                color: #007bff;
                text-align: center;
            }}
            .ticker {{
                font-weight: bold;
                color: #28a745;
            }}
            .strong-buy {{
                background: linear-gradient(90deg, #28a745, #20c997);
                color: white;
                padding: 5px 10px;
                border-radius: 15px;
                font-weight: bold;
                text-align: center;
            }}
            .weak-buy {{
                background: linear-gradient(90deg, #ffc107, #fd7e14);
                color: white;
                padding: 5px 10px;
                border-radius: 15px;
                font-weight: bold;
                text-align: center;
            }}
            .strong-sell {{
                background: linear-gradient(90deg, #dc3545, #e74c3c);
                color: white;
                padding: 5px 10px;
                border-radius: 15px;
                font-weight: bold;
                text-align: center;
            }}
            .weak-sell {{
                background: linear-gradient(90deg, #6c757d, #495057);
                color: white;
                padding: 5px 10px;
                border-radius: 15px;
                font-weight: bold;
                text-align: center;
            }}
            .hold {{
                background: linear-gradient(90deg, #6c757d, #adb5bd);
                color: white;
                padding: 5px 10px;
                border-radius: 15px;
                font-weight: bold;
                text-align: center;
            }}
            .price {{
                font-weight: bold;
                color: #333;
            }}
            .positive {{
                color: #28a745;
                font-weight: bold;
            }}
            .negative {{
                color: #dc3545;
                font-weight: bold;
            }}
            .footer {{
                text-align: center;
                margin-top: 40px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 10px;
                border-left: 5px solid #667eea;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 CHANDELIER EXIT ANALYSIS</h1>
                <p><strong>ATR-based Trailing Stop System</strong></p>
                <p>ATR Length: {atr_length} | Multiplier: {atr_multiplier}x | Use Close: {use_close}</p>
                <p>Volume: {volume_days} days | Momentum: {momentum_days} days</p>
                <p>Generated: {timestamp}</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>{len(strong_buy_signals)}</h3>
                    <p>STRONG BUY Signals</p>
                </div>
                <div class="stat-card">
                    <h3>{len(strong_sell_signals)}</h3>
                    <p>STRONG SELL Signals</p>
                </div>
                <div class="stat-card">
                    <h3>{len(weak_buy_signals) + len(weak_sell_signals)}</h3>
                    <p>WEAK Signals</p>
                </div>
                <div class="stat-card">
                    <h3>{len(all_signals)}</h3>
                    <p>Total Analyzed</p>
                </div>
            </div>
    """
    
    # Generate STRONG BUY signals table - ALL signals
    if strong_buy_signals:
        html_content += f"""
            <div class="section">
                <h2>🟢 ALL STRONG BUY SIGNALS ({len(strong_buy_signals)} found)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Ticker</th>
                            <th>Signal</th>
                            <th>Price</th>
                            <th>Stop Loss</th>
                            <th>Distance%</th>
                            <th>Direction</th>
                            <th>Volume</th>
                            <th>RSI</th>
                            <th>Momentum</th>
                            <th>Score</th>
                            <th>Qty</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for i, signal in enumerate(strong_buy_signals, 1):  # ALL signals
            signal_class = signal['signal_type'].lower().replace('_', '-')
            momentum_class = 'positive' if signal['momentum'] >= 0 else 'negative'
            direction_display = "LONG" if signal['direction'] == 1 else "SHORT"
            
            # Calculate composite score
            volume_score = min(signal['volume_ratio'] * 10, 30)
            rsi_score = 50 - abs(signal.get('rsi', 50) - 50)
            momentum_score = max(signal['momentum'], 0)
            stop_score = signal.get('stop_distance', 0)
            composite_score = (signal['buy_strength'] * 0.4 + stop_score * 0.3 + 
                             volume_score * 0.2 + momentum_score * 0.1)
            
            html_content += f"""
                        <tr>
                            <td class="rank">{i}</td>
                            <td class="ticker">{signal['ticker']}</td>
                            <td><span class="{signal_class}">{signal['signal_type'].replace('_', ' ')}</span></td>
                            <td class="price">₹{signal['current_price']:.2f}</td>
                            <td class="price">₹{signal['stop_loss']:.2f}</td>
                            <td>{signal.get('stop_distance', 0):.2f}%</td>
                            <td>{direction_display}</td>
                            <td>{signal['volume_ratio']:.1f}x</td>
                            <td>{signal.get('rsi', 50):.0f}</td>
                            <td class="{momentum_class}">{signal['momentum']:+.1f}%</td>
                            <td>{composite_score:.1f}</td>
                            <td>{signal['position_size']}</td>
                        </tr>
            """
        
        html_content += """
                    </tbody>
                </table>
            </div>
        """
    
    # Generate STRONG SELL signals table - ALL signals
    if strong_sell_signals:
        html_content += f"""
            <div class="section">
                <h2>🔴 ALL STRONG SELL SIGNALS ({len(strong_sell_signals)} found)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Ticker</th>
                            <th>Signal</th>
                            <th>Price</th>
                            <th>Stop Loss</th>
                            <th>Distance%</th>
                            <th>Direction</th>
                            <th>Volume</th>
                            <th>RSI</th>
                            <th>Momentum</th>
                            <th>Score</th>
                            <th>Qty</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for i, signal in enumerate(strong_sell_signals, 1):  # ALL signals
            signal_class = signal['signal_type'].lower().replace('_', '-')
            momentum_class = 'positive' if signal['momentum'] >= 0 else 'negative'
            direction_display = "LONG" if signal['direction'] == 1 else "SHORT"
            
            # Calculate composite score
            volume_score = min(signal['volume_ratio'] * 10, 30)
            rsi_score = 50 - abs(signal.get('rsi', 50) - 50)
            momentum_score = max(-signal['momentum'], 0)  # Negative momentum is good for sells
            stop_score = signal.get('stop_distance', 0)
            composite_score = (signal['sell_strength'] * 0.4 + stop_score * 0.3 + 
                             volume_score * 0.2 + momentum_score * 0.1)
            
            html_content += f"""
                        <tr>
                            <td class="rank">{i}</td>
                            <td class="ticker">{signal['ticker']}</td>
                            <td><span class="{signal_class}">{signal['signal_type'].replace('_', ' ')}</span></td>
                            <td class="price">₹{signal['current_price']:.2f}</td>
                            <td class="price">₹{signal['stop_loss']:.2f}</td>
                            <td>{signal.get('stop_distance', 0):.2f}%</td>
                            <td>{direction_display}</td>
                            <td>{signal['volume_ratio']:.1f}x</td>
                            <td>{signal.get('rsi', 50):.0f}</td>
                            <td class="{momentum_class}">{signal['momentum']:+.1f}%</td>
                            <td>{composite_score:.1f}</td>
                            <td>{signal['position_size']}</td>
                        </tr>
            """
        
        html_content += """
                    </tbody>
                </table>
            </div>
        """
    
    html_content += """
            <div class="footer">
                <p><strong>⚠️ Disclaimer:</strong> This analysis is for educational purposes only. Past performance does not guarantee future results. Always consult with financial advisors before making investment decisions.</p>
                <p><strong>📊 Strategy:</strong> Chandelier Exit system uses ATR-based trailing stops that follow the trend. Long stops trail below price in uptrends, short stops trail above price in downtrends.</p>
                <p><strong>🎯 Logic:</strong> Based on Pine Script "Chandelier Exit" - signals generated when price crosses from one side of the trailing stop to the other, indicating trend changes.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Save HTML
    html_filename = f"chandelier_exit_ATR{atr_length}_M{int(atr_multiplier*10)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    html_path = os.path.join(output_dir, html_filename)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return html_path

def save_results_json(all_signals, output_dir, atr_length, atr_multiplier, use_close):
    """Save results to JSON for further analysis"""
    
    if not all_signals:
        return None
    
    # Prepare data for JSON serialization
    json_signals = []
    for signal in all_signals:
        json_signal = {}
        for key, value in signal.items():
            if isinstance(value, (int, float, str, bool, list, dict)):
                if isinstance(value, dict):
                    json_signal[key] = {k: v for k, v in value.items() if isinstance(v, (int, float, str, bool, list))}
                else:
                    json_signal[key] = value
            else:
                try:
                    json_signal[key] = float(value) if hasattr(value, 'item') else str(value)
                except:
                    json_signal[key] = str(value)
    
    json_data = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'total_stocks_analyzed': len(json_signals),
            'ce_settings': f"ATR{atr_length}_M{atr_multiplier}_Close{use_close}",
            'strategy': 'Chandelier Exit Trailing Stop System'
        },
        'signals': json_signals
    }
    
    # Save JSON
    json_filename = f"chandelier_exit_ATR{atr_length}_M{int(atr_multiplier*10)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_path = os.path.join(output_dir, json_filename)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    return json_path

def main():
    """Main function with comprehensive analysis"""
    parser = argparse.ArgumentParser(description="Chandelier Exit Trading System")
    
    parser.add_argument('--atr-length', type=int, default=22, 
                       help='ATR period (default: 22)')
    parser.add_argument('--atr-multiplier', type=float, default=3.0, 
                       help='ATR multiplier (default: 3.0)')
    parser.add_argument('--use-close', type=bool, default=True, 
                       help='Use close price for extremums (default: True)')
    parser.add_argument('--volume-days', type=int, default=20, 
                       help='Volume average days (default: 20)')
    parser.add_argument('--momentum-days', type=int, default=5, 
                       help='Momentum calculation days (default: 5)')
    parser.add_argument('--top', type=int, default=10, 
                       help='Top N signals to display (default: 10, ignored if --show-all-strong)')
    parser.add_argument('--show-all-strong', action='store_true', 
                       help='Show ALL strong signals (not limited to top N)')
    parser.add_argument('--sector-wise', action='store_true', 
                       help='Show signals organized by sector (includes weak signals)')
    parser.add_argument('--min-signals', type=int, default=50, 
                       help='Minimum signals to show when using --show-all-strong (default: 50)')
    parser.add_argument('--output', type=str, 
                       help='Output directory (default: output)')
    parser.add_argument('--workers', type=int, default=3, 
                       help='Max concurrent workers (default: 3)')
    parser.add_argument('--test-single', type=str, 
                       help='Test analysis on a single ticker for debugging')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug output for troubleshooting')
    parser.add_argument('--show-all', action='store_true', 
                       help='Show all signal types (BUY, SELL, HOLD)')
    parser.add_argument('--buy-only', action='store_true', 
                       help='Show only BUY signals')
    parser.add_argument('--sell-only', action='store_true', 
                       help='Show only SELL signals')
    
    args = parser.parse_args()
    
    # Test single ticker if requested
    if args.test_single:
        print(f"🧪 TESTING SINGLE TICKER: {args.test_single}")
        print("="*50)
        result = analyze_stock_comprehensive(
            args.test_single, 
            args.atr_length, 
            args.atr_multiplier,
            args.use_close,
            args.volume_days, 
            args.momentum_days,
            debug=True
        )
        if result:
            print(f"\n✅ SUCCESS! Signal: {result['signal_type']}")
            print(f"   📊 Direction: {'LONG' if result['direction'] == 1 else 'SHORT'}")
            print(f"   🛑 Stop Distance: {result['stop_distance']:.2f}%")
            if result['buy_signal']:
                print(f"   🟢 Fresh BUY signal detected!")
            elif result['sell_signal']:
                print(f"   🔴 Fresh SELL signal detected!")
        else:
            print(f"\n❌ No result for {args.test_single}")
        return
    
    print("🎯 CHANDELIER EXIT ANALYZER")
    print("🔄 Using ATR-based Trailing Stop System")
    print("="*50)
    print(f"📅 ATR Length: {args.atr_length} periods")
    print(f"📊 ATR Multiplier: {args.atr_multiplier}x")
    print(f"🎯 Use Close: {args.use_close}")
    print(f"📊 Volume Period: {args.volume_days} trading days") 
    print(f"🚀 Momentum Period: {args.momentum_days} trading days")
    print(f"🏆 Top Signals: {args.top}")
    print(f"⚙️  Workers: {args.workers}")
    print("="*50)
    
    # Set output directory
    output_dir = args.output or getattr(config, 'OUTPUT_DIR', 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Analyze all stocks
    all_signals = analyze_all_stocks(
        atr_length=args.atr_length,
        atr_multiplier=args.atr_multiplier,
        use_close=args.use_close,
        volume_days=args.volume_days, 
        momentum_days=args.momentum_days,
        max_workers=args.workers,
        debug=args.debug
    )
    
    if not all_signals:
        print("\n❌ No signals generated!")
        print("💡 TROUBLESHOOTING TIPS:")
        print("   🔧 Try shorter ATR length: --atr-length 14")
        print("   🔧 Adjust multiplier: --atr-multiplier 2.5")
        print("   🔧 Enable debug mode: --debug")
        print("   🔧 Check internet connection for data fetching")
        return
    
    # Display results based on arguments
    if args.sector_wise:
        # Show ALL signals organized by sector (including weak signals)
        print(f"\n🏢 COMPREHENSIVE SECTOR-WISE ANALYSIS")
        print(f"📊 Including all signal types: STRONG BUY, WEAK BUY, STRONG SELL, WEAK SELL, HOLD")
        sector_signals = display_sector_wise_signals(all_signals, "COMPREHENSIVE")
        
        # Generate comprehensive HTML with ALL signals
        print(f"\n📄 Generating HTML report with ALL {len(all_signals)} signals...")
        signal_breakdown = {
            'STRONG_BUY': len([s for s in all_signals if s['signal_type'] == 'STRONG_BUY']),
            'WEAK_BUY': len([s for s in all_signals if s['signal_type'] == 'WEAK_BUY']),
            'STRONG_SELL': len([s for s in all_signals if s['signal_type'] == 'STRONG_SELL']),
            'WEAK_SELL': len([s for s in all_signals if s['signal_type'] == 'WEAK_SELL']),
            'HOLD': len([s for s in all_signals if s['signal_type'] == 'HOLD'])
        }
        print(f"📊 Signal breakdown for HTML: {signal_breakdown}")
        
    elif args.show_all_strong:
        # Show ALL strong signals with comprehensive ranking
        strong_buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY'])
        strong_sell_signals = filter_signals_by_type(all_signals, ['STRONG_SELL'])
        
        if strong_buy_signals:
            strong_buy_signals = sort_signals_properly(strong_buy_signals)
            print(f"\n🔥 SHOWING ALL STRONG BUY SIGNALS")
            display_top_signals(strong_buy_signals, "STRONG BUY", top_n=None)
        
        if strong_sell_signals:
            strong_sell_signals = sort_signals_properly(strong_sell_signals)
            print(f"\n🔥 SHOWING ALL STRONG SELL SIGNALS")
            display_top_signals(strong_sell_signals, "STRONG SELL", top_n=None)
        
        # Overall summary for strong signals
        total_strong = len(strong_buy_signals) + len(strong_sell_signals)
        if total_strong > 0:
            print(f"\n🔥 OVERALL STRONG SIGNALS SUMMARY:")
            print(f"   ⚡ Total strong signals: {total_strong}")
            print(f"   🟢 Strong BUY signals: {len(strong_buy_signals)}")
            print(f"   🔴 Strong SELL signals: {len(strong_sell_signals)}")
            print(f"   📊 Strong signal ratio: {total_strong/len(all_signals)*100:.1f}%")
            
            # Check minimum threshold
            if total_strong < args.min_signals:
                print(f"   ⚠️  WARNING: Only {total_strong} strong signals found (minimum: {args.min_signals})")
                print(f"   💡 Consider adjusting ATR settings for more signals")
        else:
            print(f"\n❌ No strong signals found!")
            print(f"💡 Try adjusting parameters: --atr-length 14 --atr-multiplier 2.5")
            
    elif args.buy_only:
        buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY', 'WEAK_BUY'])
        buy_signals = sort_signals_properly(buy_signals) if buy_signals else []
        display_top_signals(buy_signals, "BUY", args.top)
    elif args.sell_only:
        sell_signals = filter_signals_by_type(all_signals, ['STRONG_SELL', 'WEAK_SELL'])
        sell_signals = sort_signals_properly(sell_signals) if sell_signals else []
        display_top_signals(sell_signals, "SELL", args.top)
    elif args.show_all:
        # Show all types
        buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY', 'WEAK_BUY'])
        sell_signals = filter_signals_by_type(all_signals, ['STRONG_SELL', 'WEAK_SELL'])
        hold_signals = filter_signals_by_type(all_signals, ['HOLD'])
        
        if buy_signals:
            buy_signals = sort_signals_properly(buy_signals)
            display_top_signals(buy_signals, "BUY", args.top)
        if sell_signals:
            sell_signals = sort_signals_properly(sell_signals)
            display_top_signals(sell_signals, "SELL", args.top)
        
        print(f"\n📊 OVERALL SUMMARY:")
        print(f"   🟢 BUY signals: {len(buy_signals)}")
        print(f"   🔴 SELL signals: {len(sell_signals)}")
        print(f"   ⚪ HOLD signals: {len(hold_signals)}")
        print(f"   📈 Total analyzed: {len(all_signals)}")
    else:
        # Default: Show BUY signals only in console, but HTML gets ALL signals
        buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY', 'WEAK_BUY'])
        buy_signals = sort_signals_properly(buy_signals) if buy_signals else []
        display_top_signals(buy_signals, "BUY", args.top)
        
        # Show signal breakdown for HTML generation
        print(f"\n📄 HTML will include ALL {len(all_signals)} signals:")
        signal_breakdown = {
            'STRONG_BUY': len([s for s in all_signals if s['signal_type'] == 'STRONG_BUY']),
            'WEAK_BUY': len([s for s in all_signals if s['signal_type'] == 'WEAK_BUY']),
            'STRONG_SELL': len([s for s in all_signals if s['signal_type'] == 'STRONG_SELL']),
            'WEAK_SELL': len([s for s in all_signals if s['signal_type'] == 'WEAK_SELL']),
            'HOLD': len([s for s in all_signals if s['signal_type'] == 'HOLD'])
        }
        print(f"📊 Signal breakdown: {signal_breakdown}")
    
    # Generate reports - ALWAYS pass ALL signals to HTML
    print(f"\n📄 Generating comprehensive reports with ALL {len(all_signals)} signals...")
    
    # HTML Report - Pass ALL signals (not filtered)
    html_path = generate_comprehensive_html(
        all_signals,  # Pass ALL signals including weak and hold
        args.atr_length, args.atr_multiplier, args.use_close,
        args.volume_days, args.momentum_days, output_dir
    )
    if html_path:
        print(f"🌐 Complete HTML Report: {html_path}")
        print(f"🔗 Open: file://{os.path.abspath(html_path)}")
        print(f"📊 Contains ALL {len(all_signals)} signals with Strong Buy priority")
    
    # JSON Report - Also pass ALL signals
    json_path = save_results_json(all_signals, output_dir, args.atr_length, 
                                args.atr_multiplier, args.use_close)
    if json_path:
        print(f"📊 Complete JSON Data: {json_path}")
    
    print(f"\n✅ Analysis Complete!")
    print(f"📁 Output Directory: {os.path.abspath(output_dir)}")
    
    # Trading notes
    print(f"\n💡 TRADING NOTES:")
    print(f"   🟢 STRONG BUY: Fresh Chandelier Exit direction change to LONG")
    print(f"   🟡 WEAK BUY: Following existing LONG trend") 
    print(f"   🔴 STRONG SELL: Fresh Chandelier Exit direction change to SHORT")
    print(f"   🟠 WEAK SELL: Following existing SHORT trend")
    print(f"   🛑 STOP LOSS: Long Stop (for longs) / Short Stop (for shorts)")
    print(f"   📊 Stop Distance: Room between price and stop (higher = better)")
    print(f"   📈 System automatically trails stops based on ATR")
    print(f"   ⚖️  POSITION SIZE: 1% risk-based sizing")
    
    print(f"\n🧪 USAGE EXAMPLES:")
    print(f"   # Show ALL signals organized by sector (RECOMMENDED)")
    print(f"   python {sys.argv[0]} --sector-wise")
    print(f"   ")
    print(f"   # Show ALL strong buy and sell signals with comprehensive ranking")
    print(f"   python {sys.argv[0]} --show-all-strong")
    print(f"   ")
    print(f"   # Test single stock with debug")
    print(f"   python {sys.argv[0]} --test-single RELIANCE --debug")
    print(f"   ")
    print(f"   # Sector-wise analysis with custom ATR settings")
    print(f"   python {sys.argv[0]} --sector-wise --atr-length 14 --atr-multiplier 2.5")
    print(f"   ")
    print(f"   # Show only strong signals sector-wise")
    print(f"   python {sys.argv[0]} --sector-wise --show-all-strong")

if __name__ == "__main__":
    main()