#!/usr/bin/env python
# supertrend_classic.py - Classic SuperTrend Trading System

# 🔥 DEBUG: Print this immediately when script starts
print("🔥 SCRIPT VERSION: CLASSIC SUPERTREND - EXACT PINE SCRIPT IMPLEMENTATION")
print("🔥 Traditional SuperTrend with ATR-based dynamic support and resistance!")

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
        days_needed = lookback_days + 15  # Minimal buffer
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_needed)
        
        # Download data
        stock = yf.Ticker(symbol)
        data = stock.history(start=start_date, end=end_date)
        
        # Need at least 50 trading days for meaningful SuperTrend
        min_required = 50
        
        if data.empty or len(data) < min_required:
            print(f"   ⚠️  {ticker}: Insufficient data ({len(data)} days, need {min_required})")
            return None
        
        # Clean data
        data = data.dropna()
        
        if len(data) < min_required:
            print(f"   ⚠️  {ticker}: Insufficient clean data ({len(data)} days, need {min_required})")
            return None
        
        return data
        
    except Exception as e:
        print(f"   ❌ {ticker}: Data fetch error - {str(e)}")
        return None

def calculate_true_range(data):
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
        print(f"   ❌ True Range calculation error: {e}")
        return pd.Series([0] * len(data), index=data.index)

def calculate_atr_wilders(data, periods=10):
    """
    Calculate ATR using Wilder's smoothing method - EXACT FORMULA
    ATR = (Previous ATR x (n - 1) + TR) / n
    For initial ATR: (1/n) ∑ TRi (Simple average of first n periods)
    """
    try:
        if len(data) < periods:
            return pd.Series([0] * len(data), index=data.index)
        
        # Calculate True Range
        true_range = calculate_true_range(data)
        
        # Initialize ATR array
        atr_values = []
        
        for i in range(len(data)):
            if i < periods - 1:
                # Not enough data yet
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
        print(f"   ❌ ATR Wilder's calculation error: {e}")
        return pd.Series([0] * len(data), index=data.index)

def calculate_atr_sma(data, periods=10):
    """
    Calculate ATR using Simple Moving Average of True Range
    This is the alternative method (changeATR=false in Pine Script)
    """
    try:
        if len(data) < periods:
            return pd.Series([0] * len(data), index=data.index)
        
        # Calculate True Range
        true_range = calculate_true_range(data)
        
        # Simple Moving Average of True Range
        atr = true_range.rolling(window=periods).mean()
        
        return atr.fillna(0)
        
    except Exception as e:
        print(f"   ❌ ATR SMA calculation error: {e}")
        return pd.Series([0] * len(data), index=data.index)

def calculate_supertrend(data, periods=10, multiplier=3.0, use_builtin_atr=True, debug=False):
    """
    Calculate SuperTrend using EXACT FORMULAS as specified:
    
    1. ATR = (Previous ATR x (n - 1) + TR) / n (Wilder's smoothing)
    2. Upperband = (High + Low) / 2 + (Multiplier x ATR) 
    3. Lowerband = (High + Low) / 2 - (Multiplier x ATR)
    4. SuperTrend follows price with proper ratcheting logic
    """
    try:
        if len(data) < periods + 10:
            print(f"   ❌ Insufficient data: {len(data)} days, need {periods + 10}")
            return None
        
        # Source = hl2 = (High + Low) / 2 - EXACT FORMULA
        hl2 = (data['High'] + data['Low']) / 2
        
        # Calculate ATR using the specified method
        if use_builtin_atr:
            # Use Wilder's smoothing (traditional SuperTrend method)
            atr = calculate_atr_wilders(data, periods)
            atr_method = "Wilder's Smoothing"
        else:
            # Use SMA of True Range (alternative method)
            atr = calculate_atr_sma(data, periods)
            atr_method = "SMA of True Range"
        
        if debug:
            print(f"   📊 ATR Method: {atr_method}")
            print(f"   📊 Current ATR: {atr.iloc[-1]:.4f}")
        
        # Calculate Upper and Lower Bands - EXACT FORMULAS
        # Upperband = (High + Low) / 2 + (Multiplier x ATR)
        # Lowerband = (High + Low) / 2 - (Multiplier x ATR)
        basic_upperband = hl2 + (multiplier * atr)
        basic_lowerband = hl2 - (multiplier * atr)
        
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
                # If current upper < previous upper OR previous close > previous upper:
                #   use current upper, else use previous upper
                if current_upper < prev_upper or prev_close > prev_upper:
                    final_upper = current_upper
                else:
                    final_upper = prev_upper
                
                # Lower band ratcheting logic  
                # If current lower > previous lower OR previous close < previous lower:
                #   use current lower, else use previous lower
                if current_lower > prev_lower or prev_close < prev_lower:
                    final_lower = current_lower
                else:
                    final_lower = prev_lower
                
                upperband.append(final_upper)
                lowerband.append(final_lower)
                
                # Trend determination logic
                # Trend changes from bearish (-1) to bullish (1) when close > previous lower band
                # Trend changes from bullish (1) to bearish (-1) when close < previous upper band
                if prev_trend == -1 and current_close > prev_lower:
                    current_trend = 1  # Change to bullish
                elif prev_trend == 1 and current_close < prev_upper:
                    current_trend = -1  # Change to bearish
                else:
                    current_trend = prev_trend  # Maintain current trend
                
                trend.append(current_trend)
                
                # SuperTrend value based on current trend
                if current_trend == 1:
                    # Bullish trend: SuperTrend = lower band (acts as support)
                    supertrend.append(final_lower)
                else:
                    # Bearish trend: SuperTrend = upper band (acts as resistance)
                    supertrend.append(final_upper)
        
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
        
        if debug:
            print(f"   📈 Current Price: ₹{current_price:.2f}")
            print(f"   📊 SuperTrend: ₹{current_supertrend:.2f}")
            print(f"   📈 Trend: {'BULLISH (Green)' if current_trend == 1 else 'BEARISH (Red)'}")
            print(f"   📊 Price vs SuperTrend: {'ABOVE' if current_price > current_supertrend else 'BELOW'}")
            if current_buy_signal:
                print(f"   🟢 BUY SIGNAL: Trend changed to BULLISH!")
            elif current_sell_signal:
                print(f"   🔴 SELL SIGNAL: Trend changed to BEARISH!")
        
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
            'periods': periods,
            'multiplier': multiplier,
            'atr_method': atr_method
        }
        
    except Exception as e:
        if debug:
            print(f"   ❌ SuperTrend calculation error: {e}")
        return None

def calculate_rsi(prices, period=14):
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

def enhanced_volume_confirmation(data, current_volume, lookback_days):
    """Enhanced volume analysis for signal confirmation"""
    try:
        if data is None or len(data) < 5:
            return {'volume_strength': 'WEAK', 'volume_trend': 'NEUTRAL', 'volume_sma_ratio': 1.0}
        
        if lookback_days < 5:
            lookback_days = 5
        
        vol_sma_short = data['Volume'].rolling(window=min(5, len(data))).mean().iloc[-1]
        vol_sma_long = data['Volume'].rolling(window=min(lookback_days, len(data))).mean().iloc[-1]
        
        if pd.isna(vol_sma_short) or pd.isna(vol_sma_long) or vol_sma_long == 0:
            return {'volume_strength': 'WEAK', 'volume_trend': 'NEUTRAL', 'volume_sma_ratio': 1.0}
        
        volume_ratio = current_volume / vol_sma_long
        
        if volume_ratio > 2.0:
            volume_strength = 'VERY_HIGH'
        elif volume_ratio > 1.5:
            volume_strength = 'HIGH'
        elif volume_ratio > 0.8:
            volume_strength = 'NORMAL'
        else:
            volume_strength = 'WEAK'
        
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
        return {'volume_strength': 'WEAK', 'volume_trend': 'NEUTRAL', 'volume_sma_ratio': 1.0}

def calculate_proper_metrics(data, volume_days=20, momentum_days=5):
    """Calculate volume and momentum using ONLY trading days"""
    latest = data.iloc[-1]
    current_price = latest['Close']
    current_volume = latest['Volume']
    
    # Volume ratio
    if len(data) >= volume_days + 1:
        volume_period = data['Volume'].iloc[-(volume_days+1):-1]
        avg_volume = volume_period.mean()
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
    else:
        avg_volume = data['Volume'].mean()
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
    
    # Momentum
    if len(data) >= momentum_days + 1:
        price_n_days_ago = data['Close'].iloc[-(momentum_days+1)]
        momentum = ((current_price - price_n_days_ago) / price_n_days_ago) * 100
    else:
        momentum = 0
    
    return volume_ratio, momentum, len(data)

def analyze_stock_comprehensive(ticker, periods=10, multiplier=3.0, use_builtin_atr=True, 
                              volume_days=20, momentum_days=5, debug=False):
    """
    Comprehensive stock analysis with Classic SuperTrend system
    """
    try:
        print(f"📊 Analyzing {ticker} (using Classic SuperTrend)...")
        
        # Get data
        data = get_stock_data(ticker, periods + 50)
        if data is None:
            return None
        
        print(f"   📅 Data: {len(data)} trading days available")
        
        # Calculate SuperTrend
        st_result = calculate_supertrend(data, periods, multiplier, use_builtin_atr, debug)
        
        if st_result is None:
            print(f"   ⚠️  {ticker}: SuperTrend calculation failed")
            return None
        
        # Get latest values
        latest = data.iloc[-1]
        current_price = latest['Close']
        current_volume = latest['Volume']
        
        print(f"   📈 SuperTrend: ₹{st_result['current_supertrend']:.2f}")
        print(f"   📊 Trend: {'BULLISH (Green)' if st_result['current_trend'] == 1 else 'BEARISH (Red)'}")
        print(f"   📊 ATR Method: {st_result['atr_method']}")
        print(f"   📊 Current ATR: {st_result['atr'].iloc[-1]:.4f}")
        print(f"   📊 Price Position: {'ABOVE SuperTrend' if current_price > st_result['current_supertrend'] else 'BELOW SuperTrend'}")
        
        # Calculate metrics
        volume_ratio, momentum, trading_days_used = calculate_proper_metrics(data, volume_days, momentum_days)
        
        # Volume confirmation
        volume_analysis = enhanced_volume_confirmation(data, current_volume, volume_days)
        
        print(f"   📊 Volume: Current {current_volume:,.0f} vs {volume_days}-day avg = {volume_ratio:.1f}x ({volume_analysis['volume_strength']})")
        print(f"   🚀 Momentum: {momentum:+.1f}% ({momentum_days} trading days)")
        
        # RSI calculation
        rsi = calculate_rsi(data['Close'])
        print(f"   📈 RSI: {rsi:.1f}")
        
        # Determine signal and strength
        if st_result['current_buy_signal']:
            signal_type = 'STRONG_BUY'
            strength = 100  # Maximum strength for fresh signals
            print(f"   🎯 STRONG BUY Signal detected!")
        elif st_result['current_sell_signal']:
            signal_type = 'STRONG_SELL'
            strength = 100  # Maximum strength for fresh signals
            print(f"   🎯 STRONG SELL Signal detected!")
        elif st_result['current_trend'] == 1:
            signal_type = 'WEAK_BUY'  # Following uptrend
            strength = 50
        else:
            signal_type = 'WEAK_SELL'  # Following downtrend
            strength = 50
        
        # Calculate distance from SuperTrend
        st_distance = ((current_price - st_result['current_supertrend']) / current_price) * 100
        
        # Risk management - use SuperTrend as stop loss
        stop_loss = st_result['current_supertrend']
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
            'supertrend': float(st_result['current_supertrend']),
            'stop_loss': float(stop_loss),
            'trend': int(st_result['current_trend']),
            'trend_direction': 'BULLISH' if st_result['current_trend'] == 1 else 'BEARISH',
            'buy_signal': bool(st_result['current_buy_signal']),
            'sell_signal': bool(st_result['current_sell_signal']),
            'strength': float(strength),
            'st_distance': float(st_distance),
            'volume_ratio': float(volume_ratio),
            'volume_analysis': volume_analysis,
            'momentum': float(momentum),
            'rsi': float(rsi),
            'position_size': int(position_size),
            'risk_per_share': float(risk_per_share),
            'trading_days_used': int(trading_days_used),
            'volume_period': f"{volume_days} trading days",
            'momentum_period': f"{momentum_days} trading days",
            'st_settings': f"P{periods}_M{multiplier}_{st_result['atr_method'].replace(' ', '_')}",
            'periods': int(periods),
            'multiplier': float(multiplier),
            'use_builtin_atr': bool(use_builtin_atr),
            'atr_method': st_result['atr_method'],
            'current_atr': float(st_result['atr'].iloc[-1])
        }
        
        print(f"   🎯 Signal: {signal_type}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error analyzing {ticker}: {e}")
        return None

def analyze_all_stocks(periods=10, multiplier=3.0, use_builtin_atr=True, volume_days=20, 
                      momentum_days=5, max_workers=3, debug=False):
    """Analyze all stocks with Classic SuperTrend"""
    
    tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
    
    print(f"\n🚀 COMPREHENSIVE CLASSIC SUPERTREND ANALYSIS")
    print(f"📊 Analyzing {len(tickers)} stocks")
    atr_method_name = "Wilder's Smoothing" if use_builtin_atr else "SMA Method"
    print(f"📈 SuperTrend Settings: Periods {periods}, Multiplier {multiplier}, ATR {atr_method_name}")
    print(f"📊 Volume Period: {volume_days} trading days")
    print(f"🚀 Momentum Period: {momentum_days} trading days")
    print("="*70)
    
    all_signals = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(analyze_stock_comprehensive, ticker, periods, multiplier, 
                          use_builtin_atr, volume_days, momentum_days, debug): ticker 
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
                    trend_str = result['trend_direction']
                    signal_indicator = ""
                    if result['buy_signal']:
                        signal_indicator = " 🟢BUY"
                    elif result['sell_signal']:
                        signal_indicator = " 🔴SELL"
                    print(f"✅ {ticker} ({completed}/{len(tickers)}) - {result['signal_type']} - {trend_str}{signal_indicator}")
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
    
    sorted_sectors = dict(sorted(sector_signals.items(), key=lambda x: len(x[1]), reverse=True))
    return sorted_sectors

def sort_signals_properly(signals):
    """Sort signals by comprehensive metrics ranking"""
    if not signals:
        return signals
    
    # Sort by: 1) Signal strength, 2) ST distance, 3) Volume ratio, 4) Momentum
    signals.sort(key=lambda x: (
        x['strength'],
        abs(x.get('st_distance', 0)),
        x['volume_ratio'],
        x['momentum'] if 'BUY' in x['signal_type'] else -x['momentum']
    ), reverse=True)
    
    return signals

def display_sector_wise_signals(all_signals, signal_title="ALL"):
    """Display all signals organized by sector"""
    
    if not all_signals:
        print(f"\n❌ No signals found!")
        return
    
    sector_signals = organize_signals_by_sector(all_signals)
    
    print(f"\n🏢 SECTOR-WISE {signal_title} SIGNALS ANALYSIS")
    print(f"📊 Total Signals: {len(all_signals)} across {len(sector_signals)} sectors")
    print("="*130)
    
    sector_summary = []
    
    for sector, signals in sector_signals.items():
        if not signals:
            continue
            
        sorted_signals = sort_signals_properly(signals)
        
        # Calculate sector statistics
        strong_buy = len([s for s in signals if s['signal_type'] == 'STRONG_BUY'])
        weak_buy = len([s for s in signals if s['signal_type'] == 'WEAK_BUY'])
        strong_sell = len([s for s in signals if s['signal_type'] == 'STRONG_SELL'])
        weak_sell = len([s for s in signals if s['signal_type'] == 'WEAK_SELL'])
        
        avg_volume = sum(s['volume_ratio'] for s in signals) / len(signals)
        avg_momentum = sum(s['momentum'] for s in signals) / len(signals)
        avg_rsi = sum(s.get('rsi', 50) for s in signals) / len(signals)
        
        print(f"\n🏢 {sector.upper()} SECTOR ({len(signals)} stocks)")
        print(f"   📊 Strong Buy: {strong_buy} | Weak Buy: {weak_buy} | Strong Sell: {strong_sell} | Weak Sell: {weak_sell}")
        print(f"   📈 Avg Volume: {avg_volume:.1f}x | Avg Momentum: {avg_momentum:+.1f}% | Avg RSI: {avg_rsi:.0f}")
        print("-" * 130)
        
        table_data = []
        headers = ['Rank', 'Ticker', 'Signal', 'Price', 'SuperTrend', 'Distance%', 
                  'Trend', 'Volume', 'RSI', 'Momentum%', 'Strength', 'Qty']
        
        for i, signal in enumerate(sorted_signals, 1):
            # Trend display
            trend_display = "BULLISH🟢" if signal['trend_direction'] == 'BULLISH' else "BEARISH🔴"
            
            # Signal display
            signal_display = signal['signal_type']
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
                f"₹{signal['supertrend']:.2f}",
                f"{signal['st_distance']:+.2f}%",
                trend_display,
                volume_display,
                rsi_display,
                f"{signal['momentum']:+.1f}%",
                f"{signal['strength']:.0f}",
                signal['position_size']
            ])
        
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        
        sector_summary.append({
            'sector': sector,
            'total': len(signals),
            'strong_buy': strong_buy,
            'weak_buy': weak_buy,
            'strong_sell': strong_sell,
            'weak_sell': weak_sell,
            'avg_volume': avg_volume,
            'avg_momentum': avg_momentum,
            'avg_rsi': avg_rsi
        })
    
    # Overall sector summary
    print(f"\n📊 SECTOR-WISE SUMMARY")
    print("="*100)
    
    summary_table = []
    summary_headers = ['Sector', 'Total', 'Strong Buy', 'Weak Buy', 'Strong Sell', 'Weak Sell', 'Avg Vol', 'Avg Mom%', 'Avg RSI']
    
    for sector_data in sector_summary:
        summary_table.append([
            sector_data['sector'],
            sector_data['total'],
            sector_data['strong_buy'],
            sector_data['weak_buy'],
            sector_data['strong_sell'],
            sector_data['weak_sell'],
            f"{sector_data['avg_volume']:.1f}x",
            f"{sector_data['avg_momentum']:+.1f}%",
            f"{sector_data['avg_rsi']:.0f}"
        ])
    
    print(tabulate(summary_table, headers=summary_headers, tablefmt="grid"))
    
    return sector_signals

def display_top_signals(signals, signal_title, top_n=None):
    """Display signals with comprehensive ranking"""
    
    if not signals:
        print(f"\n❌ No {signal_title} signals found!")
        return
    
    signals = sort_signals_properly(signals)
    
    if top_n is None:
        display_signals = signals
    else:
        display_signals = signals[:top_n]
    
    print(f"\n🏆 ALL {signal_title} SIGNALS ({len(display_signals)} found)")
    print(f"📊 Classic SuperTrend System - Comprehensive Ranking")
    print("="*140)
    
    table_data = []
    headers = ['Rank', 'Ticker', 'Signal', 'Price', 'SuperTrend', 'Distance%', 
              'Trend', 'Volume', 'RSI', 'Momentum%', 'Strength', 'Qty', 'Risk₹']
    
    for i, signal in enumerate(display_signals, 1):
        trend_display = "BULLISH🟢" if signal['trend_direction'] == 'BULLISH' else "BEARISH🔴"
        
        signal_display = signal['signal_type']
        if signal['buy_signal']:
            signal_display += " 🟢"
        elif signal['sell_signal']:
            signal_display += " 🔴"
        
        rsi_value = signal.get('rsi', 50)
        rsi_display = f"{rsi_value:.0f}"
        if rsi_value > 70:
            rsi_display += "🔴"
        elif rsi_value < 30:
            rsi_display += "🟢"
        
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
            f"₹{signal['supertrend']:.2f}",
            f"{signal['st_distance']:+.2f}%",
            trend_display,
            volume_display,
            rsi_display,
            f"{signal['momentum']:+.1f}%",
            f"{signal['strength']:.0f}",
            signal['position_size'],
            f"₹{signal['risk_per_share']:.2f}"
        ])
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Summary statistics
    avg_st_distance = sum(abs(signal.get('st_distance', 0)) for signal in display_signals) / len(display_signals)
    avg_volume = sum(signal['volume_ratio'] for signal in display_signals) / len(display_signals)
    avg_momentum = sum(signal['momentum'] for signal in display_signals) / len(display_signals)
    avg_rsi = sum(signal.get('rsi', 50) for signal in display_signals) / len(display_signals)
    bullish_count = sum(1 for signal in display_signals if signal['trend_direction'] == 'BULLISH')
    bearish_count = len(display_signals) - bullish_count
    fresh_signals = sum(1 for signal in display_signals if signal.get('buy_signal') or signal.get('sell_signal'))
    
    print(f"\n📊 COMPREHENSIVE SUMMARY:")
    print(f"   🎯 Total {signal_title} signals: {len(display_signals)}")
    print(f"   📈 Average ST distance: {avg_st_distance:.2f}%")
    print(f"   📊 Average volume ratio: {avg_volume:.1f}x")
    print(f"   🚀 Average momentum: {avg_momentum:+.1f}%")
    print(f"   📈 Average RSI: {avg_rsi:.1f}")
    print(f"   🟢 Bullish trend: {bullish_count}")
    print(f"   🔴 Bearish trend: {bearish_count}")
    print(f"   ⚡ Fresh signals: {fresh_signals}")
    
    print(f"\n🏆 RANKING METHODOLOGY:")
    print(f"   📊 Multi-criteria ranking: Signal Strength + ST Distance + Volume + Momentum")
    print(f"   🎯 Fresh trend change signals get maximum strength (100)")
    print(f"   🎯 SuperTrend acts as dynamic trailing stop loss")

def generate_comprehensive_html(all_signals, periods, multiplier, use_builtin_atr, 
                              volume_days, momentum_days, output_dir):
    """Generate comprehensive HTML report for Classic SuperTrend"""
    
    if not all_signals:
        print("❌ No signals to generate report")
        return None
    
    sector_signals = organize_signals_by_sector(all_signals)
    
    strong_buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY'])
    weak_buy_signals = filter_signals_by_type(all_signals, ['WEAK_BUY'])
    strong_sell_signals = filter_signals_by_type(all_signals, ['STRONG_SELL'])
    weak_sell_signals = filter_signals_by_type(all_signals, ['WEAK_SELL'])
    
    all_buy_signals = sort_signals_properly(strong_buy_signals + weak_buy_signals)
    all_sell_signals = sort_signals_properly(strong_sell_signals + weak_sell_signals)
    
    master_signals_list = all_buy_signals + all_sell_signals
    
    atr_display = "Wilder's Smoothing" if use_builtin_atr else "SMA Method"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Classic SuperTrend Analysis - {datetime.now().strftime('%Y-%m-%d')}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }}
            .container {{
                max-width: 1800px;
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
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
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
                margin: 15px 0;
                box-shadow: 0 3px 10px rgba(0,0,0,0.1);
                border-radius: 8px;
                overflow: hidden;
                background: white;
                font-size: 0.85em;
            }}
            th, td {{
                padding: 8px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background: #f8f9fa;
                font-weight: bold;
                position: sticky;
                top: 0;
                font-size: 0.8em;
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
            .sector {{
                font-size: 0.75em;
                color: #6c757d;
                font-weight: bold;
            }}
            .strong-buy {{
                background: linear-gradient(90deg, #28a745, #20c997);
                color: white;
                padding: 3px 6px;
                border-radius: 10px;
                font-weight: bold;
                font-size: 0.75em;
            }}
            .weak-buy {{
                background: linear-gradient(90deg, #ffc107, #fd7e14);
                color: white;
                padding: 3px 6px;
                border-radius: 10px;
                font-weight: bold;
                font-size: 0.75em;
            }}
            .strong-sell {{
                background: linear-gradient(90deg, #dc3545, #e74c3c);
                color: white;
                padding: 3px 6px;
                border-radius: 10px;
                font-weight: bold;
                font-size: 0.75em;
            }}
            .weak-sell {{
                background: linear-gradient(90deg, #6c757d, #495057);
                color: white;
                padding: 3px 6px;
                border-radius: 10px;
                font-weight: bold;
                font-size: 0.75em;
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
                <h1>📈 CLASSIC SUPERTREND ANALYSIS</h1>
                <p><strong>Traditional SuperTrend with ATR-based Dynamic Support & Resistance</strong></p>
                <p>Periods: {periods} | Multiplier: {multiplier} | ATR: {atr_display}</p>
                <p>Volume: {volume_days} days | Momentum: {momentum_days} days</p>
                <p><strong>Total Signals: {len(all_signals)} | Buy First Priority</strong></p>
                <p>Generated: {timestamp}</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>{len(strong_buy_signals)}</h3>
                    <p>STRONG BUY</p>
                </div>
                <div class="stat-card">
                    <h3>{len(weak_buy_signals)}</h3>
                    <p>WEAK BUY</p>
                </div>
                <div class="stat-card">
                    <h3>{len(strong_sell_signals)}</h3>
                    <p>STRONG SELL</p>
                </div>
                <div class="stat-card">
                    <h3>{len(weak_sell_signals)}</h3>
                    <p>WEAK SELL</p>
                </div>
                <div class="stat-card">
                    <h3>{len(sector_signals)}</h3>
                    <p>SECTORS</p>
                </div>
            </div>
            
            <div class="section">
                <h2>🏆 ALL SIGNALS RANKED - MASTER LIST ({len(master_signals_list)} signals)</h2>
                <p><strong>✅ Classic SuperTrend with trend change signals prioritized</strong></p>
                <p><strong>🎯 Priority: Fresh trend changes get maximum strength, then trend followers</strong></p>
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Ticker</th>
                            <th>Sector</th>
                            <th>Signal</th>
                            <th>Price</th>
                            <th>SuperTrend</th>
                            <th>Distance%</th>
                            <th>Trend</th>
                            <th>Volume</th>
                            <th>RSI</th>
                            <th>Momentum</th>
                            <th>Strength</th>
                            <th>Qty</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for i, signal in enumerate(master_signals_list, 1):
        signal_class = signal['signal_type'].lower().replace('_', '-')
        momentum_class = 'positive' if signal['momentum'] >= 0 else 'negative'
        trend_display = signal['trend_direction']
        
        html_content += f"""
                        <tr>
                            <td class="rank">{i}</td>
                            <td class="ticker">{signal['ticker']}</td>
                            <td class="sector">{signal.get('sector', 'Others')}</td>
                            <td><span class="{signal_class}">{signal['signal_type'].replace('_', ' ')}</span></td>
                            <td class="price">₹{signal['current_price']:.2f}</td>
                            <td class="price">₹{signal['supertrend']:.2f}</td>
                            <td class="{momentum_class}">{signal['st_distance']:+.2f}%</td>
                            <td>{trend_display}</td>
                            <td>{signal['volume_ratio']:.1f}x</td>
                            <td>{signal.get('rsi', 50):.0f}</td>
                            <td class="{momentum_class}">{signal['momentum']:+.1f}%</td>
                            <td>{signal['strength']:.0f}</td>
                            <td>{signal['position_size']}</td>
                        </tr>
        """
    
    html_content += """
                    </tbody>
                </table>
            </div>
            
            <div class="footer">
                <p><strong>⚠️ Disclaimer:</strong> This analysis is for educational purposes only. Past performance does not guarantee future results. Always consult with financial advisors before making investment decisions.</p>
                <p><strong>📊 Strategy:</strong> Classic SuperTrend using ATR-based dynamic support and resistance levels.</p>
                <p><strong>🎯 Signal Logic:</strong> Buy on trend change to bullish, Sell on trend change to bearish, SuperTrend acts as trailing stop.</p>
                <p><strong>🏆 Ranking:</strong> Signal strength + SuperTrend distance + Volume confirmation + Momentum alignment</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Save HTML
    atr_method = "Wilders" if use_builtin_atr else "SMA"
    html_filename = f"CLASSIC_SUPERTREND_P{periods}_M{int(multiplier*10)}_{atr_method}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    html_path = os.path.join(output_dir, html_filename)
    
    try:
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        if os.path.exists(html_path):
            file_size = os.path.getsize(html_path)
            print(f"✅ HTML file successfully written: {html_path}")
            print(f"📊 File size: {file_size:,} bytes")
            return html_path
        else:
            print(f"❌ ERROR: HTML file was not created at {html_path}")
            return None
            
    except Exception as e:
        print(f"❌ ERROR writing HTML file: {e}")
        return None

def save_results_json(all_signals, output_dir, periods, multiplier, use_builtin_atr):
    """Save results to JSON for further analysis"""
    
    if not all_signals:
        return None
    
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
    
    atr_method = "Wilders" if use_builtin_atr else "SMA"
    json_data = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'total_stocks_analyzed': len(json_signals),
            'st_settings': f"P{periods}_M{multiplier}_{atr_method}",
            'strategy': 'Classic SuperTrend with ATR'
        },
        'signals': json_signals
    }
    
    json_filename = f"classic_supertrend_P{periods}_M{int(multiplier*10)}_{atr_method}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_path = os.path.join(output_dir, json_filename)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    return json_path

def main():
    """Main function with Classic SuperTrend analysis"""
    parser = argparse.ArgumentParser(description="Classic SuperTrend Trading System")
    
    parser.add_argument('--periods', type=int, default=10, 
                       help='ATR period (default: 10)')
    parser.add_argument('--multiplier', type=float, default=3.0, 
                       help='ATR multiplier (default: 3.0)')
    parser.add_argument('--use-sma-atr', action='store_true', 
                       help='Use SMA of True Range instead of built-in ATR')
    parser.add_argument('--volume-days', type=int, default=20, 
                       help='Volume average days (default: 20)')
    parser.add_argument('--momentum-days', type=int, default=5, 
                       help='Momentum calculation days (default: 5)')
    parser.add_argument('--top', type=int, default=10, 
                       help='Top N signals to display (default: 10)')
    parser.add_argument('--sector-wise', action='store_true', 
                       help='Show signals organized by sector')
    parser.add_argument('--output', type=str, 
                       help='Output directory (default: output)')
    parser.add_argument('--workers', type=int, default=3, 
                       help='Max concurrent workers (default: 3)')
    parser.add_argument('--test-single', type=str, 
                       help='Test analysis on a single ticker for debugging')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug output for troubleshooting')
    parser.add_argument('--show-all', action='store_true', 
                       help='Show all signal types (BUY, SELL)')
    parser.add_argument('--buy-only', action='store_true', 
                       help='Show only BUY signals')
    parser.add_argument('--sell-only', action='store_true', 
                       help='Show only SELL signals')
    
    args = parser.parse_args()
    
    # ATR calculation method
    use_builtin_atr = not args.use_sma_atr
    
    # Test single ticker if requested
    if args.test_single:
        print(f"🧪 TESTING SINGLE TICKER: {args.test_single}")
        print("="*50)
        result = analyze_stock_comprehensive(
            args.test_single, 
            args.periods, 
            args.multiplier,
            use_builtin_atr,
            args.volume_days, 
            args.momentum_days,
            debug=True
        )
        if result:
            print(f"\n✅ SUCCESS! Signal: {result['signal_type']}")
            print(f"   📊 Trend: {result['trend_direction']}")
            print(f"   📈 SuperTrend: ₹{result['supertrend']:.2f}")
            print(f"   📊 Distance: {result['st_distance']:+.2f}%")
            if result['buy_signal']:
                print(f"   🟢 Fresh BUY signal detected!")
            elif result['sell_signal']:
                print(f"   🔴 Fresh SELL signal detected!")
        else:
            print(f"\n❌ No result for {args.test_single}")
        return
    
    print("🎯 CLASSIC SUPERTREND ANALYZER")
    print("📈 Traditional ATR-based Trend Following")
    print("="*50)
    print(f"📅 SuperTrend Settings: Periods {args.periods}, Multiplier {args.multiplier}")
    atr_method_display = "Wilder's Smoothing (Traditional)" if use_builtin_atr else "SMA of True Range (Alternative)"
    print(f"📊 ATR Method: {atr_method_display}")
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
        periods=args.periods,
        multiplier=args.multiplier,
        use_builtin_atr=use_builtin_atr,
        volume_days=args.volume_days, 
        momentum_days=args.momentum_days,
        max_workers=args.workers,
        debug=args.debug
    )
    
    if not all_signals:
        print("\n❌ No signals generated!")
        print("💡 TROUBLESHOOTING TIPS:")
        print("   🔧 Try different periods: --periods 14")
        print("   🔧 Adjust multiplier: --multiplier 2.5")
        print("   🔧 Try SMA ATR: --use-sma-atr")
        print("   🔧 Enable debug mode: --debug")
        return
    
    # Display results
    if args.sector_wise:
        display_sector_wise_signals(all_signals, "COMPREHENSIVE")
    elif args.buy_only:
        buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY', 'WEAK_BUY'])
        buy_signals = sort_signals_properly(buy_signals) if buy_signals else []
        display_top_signals(buy_signals, "BUY", args.top)
    elif args.sell_only:
        sell_signals = filter_signals_by_type(all_signals, ['STRONG_SELL', 'WEAK_SELL'])
        sell_signals = sort_signals_properly(sell_signals) if sell_signals else []
        display_top_signals(sell_signals, "SELL", args.top)
    elif args.show_all:
        buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY', 'WEAK_BUY'])
        sell_signals = filter_signals_by_type(all_signals, ['STRONG_SELL', 'WEAK_SELL'])
        
        if buy_signals:
            buy_signals = sort_signals_properly(buy_signals)
            display_top_signals(buy_signals, "BUY", args.top)
        if sell_signals:
            sell_signals = sort_signals_properly(sell_signals)
            display_top_signals(sell_signals, "SELL", args.top)
        
        print(f"\n📊 OVERALL SUMMARY:")
        print(f"   🟢 BUY signals: {len(buy_signals)}")
        print(f"   🔴 SELL signals: {len(sell_signals)}")
        print(f"   📈 Total analyzed: {len(all_signals)}")
    else:
        # Default: Show BUY signals
        buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY', 'WEAK_BUY'])
        buy_signals = sort_signals_properly(buy_signals) if buy_signals else []
        display_top_signals(buy_signals, "BUY", args.top)
    
    print(f"\n✅ Analysis Complete!")
    print(f"📁 Output Directory: {os.path.abspath(output_dir)}")
    
    # Generate HTML report
    html_path = generate_comprehensive_html(
        all_signals, args.periods, args.multiplier, use_builtin_atr, 
        args.volume_days, args.momentum_days, output_dir
    )
    
    if html_path:
        print(f"🌐 ✅ Complete HTML Report Generated: {html_path}")
        print(f"🔗 Open: file://{os.path.abspath(html_path)}")
        print(f"📊 ✅ HTML Contains ALL {len(all_signals)} signals with comprehensive SuperTrend analysis")
        print(f"🔍 File size: {os.path.getsize(html_path) if os.path.exists(html_path) else 'FILE NOT FOUND'} bytes")
    else:
        print(f"❌ ERROR: HTML generation failed!")

if __name__ == '__main__':
    main()