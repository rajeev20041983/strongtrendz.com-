#!/usr/bin/env python
# vwap_rsi_strategy_analyzer.py - Advanced VWAP + RSI Intraday Strategy

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
    # Extended default configuration if config file not found
    class DefaultConfig:
        TOP_STOCKS = [
            {'symbol': 'RELIANCE'}, {'symbol': 'TCS'}, {'symbol': 'HDFCBANK'}, {'symbol': 'INFY'},
            {'symbol': 'HINDUNILVR'}, {'symbol': 'ICICIBANK'}, {'symbol': 'KOTAKBANK'}, {'symbol': 'ITC'},
            {'symbol': 'LT'}, {'symbol': 'SBIN'}, {'symbol': 'BHARTIARTL'}, {'symbol': 'ASIANPAINT'},
            {'symbol': 'MARUTI'}, {'symbol': 'AXISBANK'}, {'symbol': 'BAJFINANCE'}, {'symbol': 'WIPRO'},
            {'symbol': 'NESTLEIND'}, {'symbol': 'ULTRACEMCO'}, {'symbol': 'TITAN'}, {'symbol': 'POWERGRID'},
            {'symbol': 'SUNPHARMA'}, {'symbol': 'BAJAJFINSV'}, {'symbol': 'HCLTECH'}, {'symbol': 'NTPC'},
            {'symbol': 'DRREDDY'}, {'symbol': 'JSWSTEEL'}, {'symbol': 'TECHM'}, {'symbol': 'INDUSINDBK'},
            {'symbol': 'HINDALCO'}, {'symbol': 'ADANIENT'}, {'symbol': 'TATAMOTORS'}, {'symbol': 'COALINDIA'},
            {'symbol': 'BRITANNIA'}, {'symbol': 'CIPLA'}, {'symbol': 'EICHERMOT'}, {'symbol': 'BPCL'},
            {'symbol': 'APOLLOHOSP'}, {'symbol': 'DIVISLAB'}, {'symbol': 'GRASIM'}, {'symbol': 'TATACONSUM'},
            {'symbol': 'HEROMOTOCO'}, {'symbol': 'SHREECEM'}, {'symbol': 'UPL'}, {'symbol': 'BAJAJ-AUTO'},
            {'symbol': 'TRENT'}, {'symbol': 'TATASTEEL'}, {'symbol': 'GODREJCP'}, {'symbol': 'VEDL'},
            {'symbol': 'LTIM'}, {'symbol': 'SBILIFE'}, {'symbol': 'PIDILITIND'}, {'symbol': 'DABUR'},
            {'symbol': 'ADANIPORTS'}, {'symbol': 'ONGC'}, {'symbol': 'HDFCLIFE'}, {'symbol': 'GAIL'},
            {'symbol': 'ICICIPRULI'}, {'symbol': 'BERGEPAINT'}, {'symbol': 'MARICO'}, {'symbol': 'COLPAL'},
            {'symbol': 'HAVELLS'}, {'symbol': 'MCDOWELL-N'}, {'symbol': 'LUPIN'}, {'symbol': 'BANKBARODA'},
            {'symbol': 'INDIGO'}, {'symbol': 'PNB'}, {'symbol': 'IOC'}, {'symbol': 'SAIL'},
            {'symbol': 'NMDC'}, {'symbol': 'SIEMENS'}, {'symbol': 'CANBK'}, {'symbol': 'RECLTD'},
            {'symbol': 'BAJAJHLDNG'}, {'symbol': 'MUTHOOTFIN'}, {'symbol': 'ABFRL'}, {'symbol': 'GODREJPROP'},
            {'symbol': 'TORNTPHARM'}, {'symbol': 'MOTHERSON'}, {'symbol': 'AMBUJACEM'}, {'symbol': 'DMART'},
            {'symbol': 'PAGEIND'}, {'symbol': 'ADANITRANS'}, {'symbol': 'STAR'}, {'symbol': 'INDHOTEL'},
            {'symbol': 'ASHOKLEY'}, {'symbol': 'AUBANK'}, {'symbol': 'PERSISTENT'}, {'symbol': 'IDFCFIRSTB'},
            {'symbol': 'PFC'}, {'symbol': 'JINDALSTEL'}, {'symbol': 'ZEEL'}, {'symbol': 'FEDERALBNK'},
            {'symbol': 'IDEA'}, {'symbol': 'BHEL'}, {'symbol': 'BANDHANBNK'}, {'symbol': 'ALKEM'},
            {'symbol': 'MPHASIS'}, {'symbol': 'TIINDIA'}, {'symbol': 'BATAINDIA'}, {'symbol': 'SRTRANSFIN'},
            {'symbol': 'LICI'}, {'symbol': 'JUBLFOOD'}, {'symbol': 'TATAPOWER'}, {'symbol': 'BIOCON'},
            {'symbol': 'CONCOR'}, {'symbol': 'CROMPTON'}, {'symbol': 'ZYDUSLIFE'}, {'symbol': 'BOSCHLTD'},
            {'symbol': 'POLYCAB'}, {'symbol': 'CHOLAFIN'}, {'symbol': 'ABBOTINDIA'}, {'symbol': 'L&TFH'},
            {'symbol': 'OFSS'}, {'symbol': 'MAXHEALTH'}, {'symbol': 'VOLTAS'}, {'symbol': 'HONAUT'},
            {'symbol': 'SYNGENE'}, {'symbol': 'GODREJIND'}, {'symbol': 'BHARATFORG'}, {'symbol': 'LALPATHLAB'},
            {'symbol': 'CUMMINSIND'}, {'symbol': 'ESCORTS'}, {'symbol': 'PGHH'}, {'symbol': 'DELTACORP'},
            {'symbol': 'MANAPPURAM'}, {'symbol': 'METROPOLIS'}, {'symbol': 'HINDPETRO'}, {'symbol': 'APLAPOLLO'},
            {'symbol': 'EXIDEIND'}, {'symbol': 'PIIND'}, {'symbol': 'COFORGE'}, {'symbol': 'DIXON'},
            {'symbol': 'RAMCOCEM'}, {'symbol': 'WHIRLPOOL'}, {'symbol': 'NAUKRI'}, {'symbol': 'RELAXO'},
            {'symbol': 'JINDAL'}, {'symbol': 'PETRONET'}, {'symbol': 'BALKRISIND'}, {'symbol': 'MINDTREE'},
            {'symbol': 'SAIL'}, {'symbol': 'RBLBANK'}, {'symbol': 'COROMANDEL'}, {'symbol': 'JKCEMENT'},
            {'symbol': 'DABUR'}, {'symbol': 'SUNDRMFAST'}, {'symbol': 'LICHSGFIN'}, {'symbol': 'ASTRAL'},
            {'symbol': 'ADANIGREEN'}, {'symbol': 'SJVN'}, {'symbol': 'KPITTECH'}, {'symbol': 'GHCL'},
            {'symbol': 'CHEMPLAST'}, {'symbol': 'HFCL'}, {'symbol': 'MINDAIND'}, {'symbol': 'DALBHARAT'},
            {'symbol': 'IEX'}, {'symbol': 'KANSAINER'}, {'symbol': 'CENTURYTEX'}, {'symbol': 'DEEPAKNTR'},
            {'symbol': 'VBL'}, {'symbol': 'NATCOPHARM'}, {'symbol': 'NIACL'}, {'symbol': 'JSW'},
            {'symbol': 'PHOENIXLTD'}, {'symbol': 'GICRE'}, {'symbol': 'CHAMBLFERT'}, {'symbol': 'NESTLEIND'},
            {'symbol': 'NHPC'}, {'symbol': 'CUB'}, {'symbol': 'FCONSUMER'}, {'symbol': 'GLENMARK'},
            {'symbol': 'BASF'}, {'symbol': 'CREDITACC'}, {'symbol': 'TVSMOTORS'}, {'symbol': 'ADANIPOWER'},
            {'symbol': 'RAINBOW'}, {'symbol': 'RATNAMANI'}, {'symbol': 'FLUOROCHEM'}, {'symbol': 'CGCL'},
            {'symbol': 'THERMAX'}, {'symbol': 'GRINDWELL'}, {'symbol': 'PGHL'}, {'symbol': 'HINDZINC'},
            {'symbol': 'NIITLTD'}, {'symbol': 'PAGEIND'}, {'symbol': 'PFIZER'}, {'symbol': 'INDIANB'},
            {'symbol': 'FINEORG'}, {'symbol': 'KAJARIACER'}, {'symbol': 'HINDCOPPER'}, {'symbol': 'HAL'},
            {'symbol': 'GNFC'}, {'symbol': 'APLLTD'}, {'symbol': 'CENTURYPLY'}, {'symbol': 'SOUTHBANK'},
            {'symbol': 'AKZOINDIA'}, {'symbol': 'VINATIORGA'}, {'symbol': 'TATACHEM'}, {'symbol': 'WABCOINDIA'},
            {'symbol': 'SPARC'}, {'symbol': 'PRESTIGE'}, {'symbol': 'JSW'}, {'symbol': 'SYMPHONY'},
            {'symbol': 'NAVINFLUOR'}, {'symbol': 'SKFINDIA'}, {'symbol': 'GMDCLTD'}, {'symbol': 'HEIDELBERG'},
            {'symbol': 'GARFIBRES'}, {'symbol': 'CCL'}, {'symbol': 'HUDCO'}, {'symbol': 'MOIL'},
            {'symbol': 'RAIN'}, {'symbol': 'FINPIPE'}, {'symbol': 'SOBHA'}, {'symbol': 'FORTIS'},
            {'symbol': 'RALLIS'}, {'symbol': 'ALLCARGO'}, {'symbol': 'VGUARD'}, {'symbol': 'CANFINHOME'},
            {'symbol': 'INDIANHUME'}, {'symbol': 'BAYERCROP'}, {'symbol': 'GESHIP'}, {'symbol': 'REDINGTON'},
            {'symbol': 'NIITTECH'}, {'symbol': 'IFBIND'}, {'symbol': 'TATAELXSI'}, {'symbol': 'RUCHI'}
        ]
        OUTPUT_DIR = 'output'
    
    config = DefaultConfig()

warnings.filterwarnings("ignore")

def get_stock_data(ticker, lookback_days=100):
    """Get stock data for comprehensive VWAP + RSI analysis"""
    try:
        # Add .NS for NSE stocks
        symbol = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
        
        # Get enough data for VWAP and RSI calculations
        days_needed = lookback_days + 100  # Extra buffer for weekends/holidays
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_needed)
        
        # Download data
        stock = yf.Ticker(symbol)
        data = stock.history(start=start_date, end=end_date)
        
        if data.empty or len(data) < 50:  # Minimum for meaningful analysis
            print(f"   ⚠️  {ticker}: Insufficient data ({len(data)} days)")
            return None
        
        # Clean data
        data = data.dropna()
        
        if len(data) < 50:
            print(f"   ⚠️  {ticker}: Insufficient clean data ({len(data)} days)")
            return None
        
        return data
        
    except Exception as e:
        print(f"   ❌ {ticker}: Data fetch error - {str(e)}")
        return None

def calculate_vwap(data, period=20):
    """
    Calculate VWAP (Volume Weighted Average Price)
    Since we're working with daily data, we'll calculate a rolling VWAP
    """
    try:
        if len(data) < period:
            return None
        
        # Calculate typical price (HLC/3 - most common VWAP calculation)
        typical_price = (data['High'] + data['Low'] + data['Close']) / 3
        
        # Calculate VWAP using rolling window
        # VWAP = sum(typical_price * volume) / sum(volume)
        volume_price = typical_price * data['Volume']
        
        # Rolling VWAP calculation
        vwap = volume_price.rolling(window=period).sum() / data['Volume'].rolling(window=period).sum()
        
        return vwap
        
    except Exception as e:
        print(f"Error calculating VWAP: {e}")
        return None

def calculate_rsi(prices, period=14):
    """
    Calculate RSI (Relative Strength Index) following PineScript logic
    """
    try:
        if len(prices) < period + 1:
            return None
        
        delta = prices.diff().dropna()
        if len(delta) < period:
            return None
        
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss.replace(0, 0.001)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
        
    except Exception as e:
        print(f"Error calculating RSI: {e}")
        return None

def detect_vwap_rsi_signals(data, vwap, rsi, rsi_buy=50, rsi_sell=50, use_reversal=True, position_mode='both'):
    """
    Detect VWAP + RSI signals following PineScript logic:
    
    LONG: vwap > vwap[1] AND rsi(close, rsiPeriod) > rsiBuy
    SHORT: vwap < vwap[1] AND rsi(close, rsiPeriod) < rsiSell
    
    EXIT (if isReversal):
    - Close Buy when vwap < vwap[1]
    - Close Sell when vwap > vwap[1]
    """
    try:
        if len(data) < 3 or vwap is None or rsi is None:
            return None
        
        # Get current and previous values
        current_close = data['Close'].iloc[-1]
        current_vwap = vwap.iloc[-1]
        prev_vwap = vwap.iloc[-2]
        current_rsi = rsi.iloc[-1]
        current_volume = data['Volume'].iloc[-1]
        
        # Check for NaN values
        if pd.isna(current_vwap) or pd.isna(prev_vwap) or pd.isna(current_rsi):
            return None
        
        signals = []
        
        # VWAP trend analysis
        vwap_rising = current_vwap > prev_vwap
        vwap_falling = current_vwap < prev_vwap
        vwap_momentum = ((current_vwap - prev_vwap) / prev_vwap) * 100
        
        # Price vs VWAP analysis
        price_vs_vwap = ((current_close - current_vwap) / current_vwap) * 100
        
        # LONG SIGNAL: vwap > vwap[1] AND rsi > rsiBuy
        long_condition = vwap_rising and current_rsi > rsi_buy
        
        if long_condition and position_mode.lower() in ['both', 'long', 'long_only']:
            # Calculate signal strength based on multiple factors
            vwap_strength = min(abs(vwap_momentum) * 20, 40)  # VWAP momentum strength
            rsi_strength = min((current_rsi - rsi_buy) * 0.5, 25)  # RSI above buy level
            price_vwap_strength = min(max(price_vs_vwap, 0) * 2, 20)  # Price above VWAP bonus
            volume_strength = 15  # Base volume strength (will be enhanced later)
            
            # Combined strength
            signal_strength = vwap_strength + rsi_strength + price_vwap_strength + volume_strength
            
            # Stop loss: Below VWAP or recent low
            recent_low = data['Low'].iloc[-5:].min()
            stop_loss = min(current_vwap * 0.98, recent_low)
            
            # Target: Based on VWAP momentum and recent highs
            if len(data) >= 10:
                recent_high = data['High'].iloc[-10:].max()
                vwap_target_multiplier = 1 + (abs(vwap_momentum) / 100)
                target_price = current_close * vwap_target_multiplier
                target_price = min(target_price, recent_high)
            else:
                target_price = current_vwap * 1.02
            
            signals.append({
                'signal_type': 'LONG',
                'entry_price': current_close,
                'stop_loss': stop_loss,
                'target_price': target_price,
                'signal_strength': signal_strength,
                'vwap_momentum': vwap_momentum,
                'rsi_value': current_rsi,
                'rsi_strength': rsi_strength,
                'price_vs_vwap': price_vs_vwap,
                'vwap_trend': 'RISING',
                'current_vwap': current_vwap,
                'volume': current_volume,
                'use_reversal': use_reversal
            })
        
        # SHORT SIGNAL: vwap < vwap[1] AND rsi < rsiSell
        short_condition = vwap_falling and current_rsi < rsi_sell
        
        if short_condition and position_mode.lower() in ['both', 'short', 'short_only']:
            # Calculate signal strength
            vwap_strength = min(abs(vwap_momentum) * 20, 40)  # VWAP momentum strength
            rsi_strength = min((rsi_sell - current_rsi) * 0.5, 25)  # RSI below sell level
            price_vwap_strength = min(max(-price_vs_vwap, 0) * 2, 20)  # Price below VWAP bonus
            volume_strength = 15  # Base volume strength
            
            # Combined strength
            signal_strength = vwap_strength + rsi_strength + price_vwap_strength + volume_strength
            
            # Stop loss: Above VWAP or recent high
            recent_high = data['High'].iloc[-5:].max()
            stop_loss = max(current_vwap * 1.02, recent_high)
            
            # Target: Based on VWAP momentum and recent lows
            if len(data) >= 10:
                recent_low = data['Low'].iloc[-10:].min()
                vwap_target_multiplier = 1 - (abs(vwap_momentum) / 100)
                target_price = current_close * vwap_target_multiplier
                target_price = max(target_price, recent_low)
            else:
                target_price = current_vwap * 0.98
            
            signals.append({
                'signal_type': 'SHORT',
                'entry_price': current_close,
                'stop_loss': stop_loss,
                'target_price': target_price,
                'signal_strength': signal_strength,
                'vwap_momentum': vwap_momentum,
                'rsi_value': current_rsi,
                'rsi_strength': rsi_strength,
                'price_vs_vwap': price_vs_vwap,
                'vwap_trend': 'FALLING',
                'current_vwap': current_vwap,
                'volume': current_volume,
                'use_reversal': use_reversal
            })
        
        return signals if signals else None
        
    except Exception as e:
        print(f"Error detecting VWAP RSI signals: {e}")
        return None

def calculate_stochastic_rsi(data, period=14, k_period=3, d_period=3):
    """Calculate Stochastic RSI (SRSI)"""
    try:
        if len(data) < period + k_period + d_period:
            return 50, 50
        
        # Calculate RSI first
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, 0.001)
        rsi = 100 - (100 / (1 + rs))
        
        # Calculate Stochastic RSI
        rsi_min = rsi.rolling(window=period).min()
        rsi_max = rsi.rolling(window=period).max()
        stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min).replace(0, 0.001) * 100
        
        # Calculate %K and %D
        k_percent = stoch_rsi.rolling(window=k_period).mean()
        d_percent = k_percent.rolling(window=d_period).mean()
        
        # Get latest values
        k_latest = k_percent.iloc[-1] if not pd.isna(k_percent.iloc[-1]) else 50
        d_latest = d_percent.iloc[-1] if not pd.isna(d_percent.iloc[-1]) else 50
        
        return max(0, min(100, k_latest)), max(0, min(100, d_latest))
    except Exception:
        return 50, 50

def calculate_support_resistance(data, lookback=20):
    """Calculate dynamic support and resistance levels"""
    try:
        if len(data) < lookback:
            latest = data.iloc[-1]
            return latest['Low'], latest['High'], latest['Close']
        
        # Get recent data
        recent_data = data.iloc[-lookback:]
        
        # Support: Recent lows
        support_level = recent_data['Low'].min()
        
        # Resistance: Recent highs  
        resistance_level = recent_data['High'].max()
        
        # Pivot: Average of recent closes
        pivot_level = recent_data['Close'].mean()
        
        return support_level, resistance_level, pivot_level
    except Exception:
        latest = data.iloc[-1]
        return latest['Low'], latest['High'], latest['Close']

def enhanced_volume_confirmation(data, current_volume, lookback_days=20):
    """Enhanced volume analysis with multiple confirmation levels"""
    try:
        if data is None or len(data) < 10:
            return {
                'volume_strength': 'WEAK', 
                'volume_trend': 'NEUTRAL', 
                'volume_sma_ratio': 1.0,
                'volume_breakout': False,
                'volume_quality': 'LOW'
            }
        
        # Volume moving averages
        vol_sma_5 = data['Volume'].rolling(window=min(5, len(data))).mean().iloc[-1]
        vol_sma_10 = data['Volume'].rolling(window=min(10, len(data))).mean().iloc[-1]
        vol_sma_20 = data['Volume'].rolling(window=min(lookback_days, len(data))).mean().iloc[-1]
        
        # Handle NaN values
        if pd.isna(vol_sma_20) or vol_sma_20 == 0:
            return {
                'volume_strength': 'WEAK', 
                'volume_trend': 'NEUTRAL', 
                'volume_sma_ratio': 1.0,
                'volume_breakout': False,
                'volume_quality': 'LOW'
            }
        
        # Volume strength classification
        volume_ratio = current_volume / vol_sma_20
        
        if volume_ratio > 2.5:
            volume_strength = 'VERY_HIGH'
            volume_quality = 'EXCELLENT'
        elif volume_ratio > 2.0:
            volume_strength = 'HIGH'
            volume_quality = 'GOOD'
        elif volume_ratio > 1.5:
            volume_strength = 'ABOVE_AVERAGE'
            volume_quality = 'FAIR'
        elif volume_ratio > 0.8:
            volume_strength = 'NORMAL'
            volume_quality = 'AVERAGE'
        else:
            volume_strength = 'WEAK'
            volume_quality = 'POOR'
        
        # Volume trend analysis
        if not pd.isna(vol_sma_5) and not pd.isna(vol_sma_10):
            if vol_sma_5 > vol_sma_10 * 1.2:
                volume_trend = 'STRONGLY_INCREASING'
            elif vol_sma_5 > vol_sma_10:
                volume_trend = 'INCREASING'
            elif vol_sma_5 < vol_sma_10 * 0.8:
                volume_trend = 'DECREASING'
            else:
                volume_trend = 'NEUTRAL'
        else:
            volume_trend = 'NEUTRAL'
        
        # Volume breakout detection
        volume_breakout = volume_ratio > 2.0 and volume_trend in ['INCREASING', 'STRONGLY_INCREASING']
        
        return {
            'volume_strength': volume_strength,
            'volume_trend': volume_trend,
            'volume_sma_ratio': volume_ratio,
            'volume_breakout': volume_breakout,
            'volume_quality': volume_quality,
            'vol_sma_5': vol_sma_5,
            'vol_sma_10': vol_sma_10,
            'vol_sma_20': vol_sma_20
        }
    except Exception:
        return {
            'volume_strength': 'WEAK', 
            'volume_trend': 'NEUTRAL', 
            'volume_sma_ratio': 1.0,
            'volume_breakout': False,
            'volume_quality': 'LOW'
        }

def calculate_proper_metrics(data, volume_days=20, momentum_days=5):
    """Calculate comprehensive metrics using trading days"""
    # Get latest values
    latest = data.iloc[-1]
    current_price = latest['Close']
    current_volume = latest['Volume']
    
    # Volume ratio calculation
    if len(data) >= volume_days + 1:
        volume_period = data['Volume'].iloc[-(volume_days+1):-1]
        avg_volume = volume_period.mean()
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
    else:
        avg_volume = data['Volume'].mean()
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
    
    # Momentum calculation
    if len(data) >= momentum_days + 1:
        price_n_days_ago = data['Close'].iloc[-(momentum_days+1)]
        momentum = ((current_price - price_n_days_ago) / price_n_days_ago) * 100
    else:
        momentum = 0
    
    # Price velocity (rate of change acceleration)
    if len(data) >= 10:
        price_velocity = ((data['Close'].iloc[-1] - data['Close'].iloc[-6]) / data['Close'].iloc[-6]) * 100
    else:
        price_velocity = 0
    
    return volume_ratio, momentum, price_velocity, len(data)

def calculate_advanced_signals(data, current_price, vwap_signals):
    """Calculate comprehensive technical signals"""
    
    # Support and resistance levels
    support_level, resistance_level, pivot_level = calculate_support_resistance(data)
    
    # Price trend analysis
    if len(data) >= 20:
        sma_20 = data['Close'].rolling(window=20).mean()
        if len(sma_20) >= 2:
            sma_trend = ((sma_20.iloc[-1] - sma_20.iloc[-2]) / sma_20.iloc[-2]) * 100
        else:
            sma_trend = 0
    else:
        sma_trend = 0
    
    # Volatility analysis (ATR approximation)
    if len(data) >= 20:
        high_low = data['High'] - data['Low']
        high_close = abs(data['High'] - data['Close'].shift(1))
        low_close = abs(data['Low'] - data['Close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=20).mean().iloc[-1]
        volatility_score = (atr / current_price) * 100
    else:
        volatility_score = 0
    
    # Stochastic RSI
    srsi_k, srsi_d = calculate_stochastic_rsi(data)
    
    # VWAP analysis from signals
    vwap_trend = 'NEUTRAL'
    vwap_momentum = 0
    price_vs_vwap = 0
    current_vwap = current_price
    
    if vwap_signals and len(vwap_signals) > 0:
        signal = vwap_signals[0]
        vwap_trend = signal.get('vwap_trend', 'NEUTRAL')
        vwap_momentum = signal.get('vwap_momentum', 0)
        price_vs_vwap = signal.get('price_vs_vwap', 0)
        current_vwap = signal.get('current_vwap', current_price)
    
    # Distance from support/resistance
    support_distance = ((current_price - support_level) / current_price) * 100
    resistance_distance = ((resistance_level - current_price) / current_price) * 100
    
    return {
        'support_level': support_level,
        'resistance_level': resistance_level,
        'pivot_level': pivot_level,
        'support_distance': support_distance,
        'resistance_distance': resistance_distance,
        'volatility_score': volatility_score,
        'sma_trend': sma_trend,
        'vwap_trend': vwap_trend,
        'vwap_momentum': vwap_momentum,
        'price_vs_vwap': price_vs_vwap,
        'current_vwap': current_vwap,
        'srsi_k': srsi_k,
        'srsi_d': srsi_d,
        'atr': atr if 'atr' in locals() else volatility_score * current_price / 100
    }

def analyze_stock_comprehensive(ticker, vwap_period=20, rsi_period=14, rsi_buy=50, rsi_sell=50,
                              use_reversal=True, position_mode='both', volume_days=20, momentum_days=5, debug=False):
    """
    Comprehensive stock analysis for VWAP + RSI strategy
    """
    try:
        print(f"📊 Analyzing {ticker} (VWAP + RSI Strategy)...")
        
        # Initialize variables
        volume_analysis = {
            'volume_strength': 'NORMAL', 
            'volume_trend': 'NEUTRAL', 
            'volume_sma_ratio': 1.0,
            'volume_quality': 'AVERAGE'
        }
        advanced = {
            'support_level': 0, 'resistance_level': 0, 'pivot_level': 0,
            'volatility_score': 0, 'sma_trend': 0, 
            'vwap_trend': 'NEUTRAL', 'vwap_momentum': 0, 'price_vs_vwap': 0,
            'srsi_k': 50, 'srsi_d': 50, 'current_vwap': 0
        }
        
        # Get data (need more for VWAP and RSI calculations)
        data = get_stock_data(ticker, max(vwap_period * 3, rsi_period * 3, 100))
        if data is None:
            return None
        
        print(f"   📅 Data: {len(data)} trading days available")
        
        # Calculate VWAP
        vwap = calculate_vwap(data, vwap_period)
        if vwap is None:
            print(f"   ❌ Could not calculate VWAP")
            return None
        
        # Calculate RSI
        rsi = calculate_rsi(data['Close'], rsi_period)
        if rsi is None:
            print(f"   ❌ Could not calculate RSI")
            return None
        
        if debug:
            print(f"   🐛 DEBUG: VWAP({vwap_period}): {vwap.iloc[-1]:.2f}, RSI({rsi_period}): {rsi.iloc[-1]:.1f}")
        
        # Detect VWAP + RSI signals
        vwap_signals = detect_vwap_rsi_signals(
            data, vwap, rsi, rsi_buy, rsi_sell, use_reversal, position_mode
        )
        
        # Get latest values
        latest = data.iloc[-1]
        current_price = latest['Close']
        current_volume = latest['Volume']
        
        # Initialize signal variables
        signal_type = 'HOLD'
        entry_price = current_price
        stop_loss = current_price
        target_price = current_price
        signal_strength = 0
        vwap_signal_info = None
        
        if vwap_signals and len(vwap_signals) > 0:
            # Use the first (strongest) signal
            vwap_signal_info = vwap_signals[0]
            
            if vwap_signal_info['signal_type'] == 'LONG':
                signal_type = 'STRONG_BUY' if vwap_signal_info['signal_strength'] >= 60 else 'WEAK_BUY'
                entry_price = vwap_signal_info['entry_price']
                stop_loss = vwap_signal_info['stop_loss']
                target_price = vwap_signal_info['target_price']
                signal_strength = vwap_signal_info['signal_strength']
                
                print(f"   📊 VWAP+RSI LONG - Strength: {signal_strength:.1f}% (VWAP: {vwap_signal_info['vwap_trend']}, RSI: {vwap_signal_info['rsi_value']:.1f})")
                
            elif vwap_signal_info['signal_type'] == 'SHORT':
                signal_type = 'STRONG_SELL' if vwap_signal_info['signal_strength'] >= 60 else 'WEAK_SELL'
                entry_price = vwap_signal_info['entry_price']
                stop_loss = vwap_signal_info['stop_loss']
                target_price = vwap_signal_info['target_price']
                signal_strength = vwap_signal_info['signal_strength']
                
                print(f"   📊 VWAP+RSI SHORT - Strength: {signal_strength:.1f}% (VWAP: {vwap_signal_info['vwap_trend']}, RSI: {vwap_signal_info['rsi_value']:.1f})")
        else:
            print(f"   ⚪ No VWAP+RSI signals detected")
        
        # Calculate metrics
        volume_ratio, momentum, price_velocity, trading_days_used = calculate_proper_metrics(
            data, volume_days, momentum_days
        )
        
        # Enhanced volume analysis
        try:
            volume_analysis = enhanced_volume_confirmation(data, current_volume, volume_days)
            print(f"   📊 Volume: {volume_ratio:.1f}x ({volume_analysis['volume_strength']}) - {volume_analysis['volume_quality']}")
        except Exception as e:
            if debug:
                print(f"   🐛 DEBUG: Volume analysis error: {e}")
        
        print(f"   🚀 Momentum: {momentum:+.1f}% ({momentum_days} days)")
        print(f"   ⚡ Velocity: {price_velocity:+.1f}%")
        print(f"   📊 VWAP({vwap_period}): ₹{vwap.iloc[-1]:.2f} | RSI({rsi_period}): {rsi.iloc[-1]:.1f}")
        
        # Calculate advanced signals
        try:
            advanced = calculate_advanced_signals(data, current_price, vwap_signals)
            print(f"   📈 SRSI: {advanced['srsi_k']:.1f}/{advanced['srsi_d']:.1f}")
            print(f"   📊 Support: ₹{advanced['support_level']:.2f} | Resistance: ₹{advanced['resistance_level']:.2f}")
            print(f"   📊 VWAP Trend: {advanced['vwap_trend']} | Price vs VWAP: {advanced['price_vs_vwap']:+.2f}%")
        except Exception as e:
            if debug:
                print(f"   🐛 DEBUG: Advanced analysis error: {e}")
        
        # Risk management
        risk_per_share = abs(entry_price - stop_loss)
        
        # Position sizing (1% risk on 100k capital)
        capital = 100000
        risk_amount = capital * 0.01
        position_size = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
        
        result = {
            'ticker': ticker,
            'signal_type': signal_type,
            'current_price': float(current_price),
            'entry_price': float(entry_price),
            'target_price': float(target_price),
            'stop_loss': float(stop_loss),
            'signal_strength': float(signal_strength),
            'volume_ratio': float(volume_ratio),
            'volume_analysis': volume_analysis,
            'momentum': float(momentum),
            'price_velocity': float(price_velocity),
            'position_size': int(position_size),
            'risk_per_share': float(risk_per_share),
            'trading_days_used': int(trading_days_used),
            'volume_period': f"{volume_days} trading days",
            'momentum_period': f"{momentum_days} trading days",
            'vwap_signal_info': vwap_signal_info,
            'current_vwap': float(vwap.iloc[-1]),
            'current_rsi': float(rsi.iloc[-1]),
            'vwap_period': int(vwap_period),
            'rsi_period': int(rsi_period),
            'rsi_buy_level': int(rsi_buy),
            'rsi_sell_level': int(rsi_sell),
            'vwap_momentum': float(vwap_signal_info.get('vwap_momentum', 0) if vwap_signal_info else 0),
            'price_vs_vwap': float(vwap_signal_info.get('price_vs_vwap', 0) if vwap_signal_info else 0),
            'vwap_trend': vwap_signal_info.get('vwap_trend', 'NEUTRAL') if vwap_signal_info else 'NEUTRAL',
            'support_level': float(advanced.get('support_level', current_price)),
            'resistance_level': float(advanced.get('resistance_level', current_price)),
            'pivot_level': float(advanced.get('pivot_level', current_price)),
            'support_distance': float(advanced.get('support_distance', 0)),
            'resistance_distance': float(advanced.get('resistance_distance', 0)),
            'volatility_score': float(advanced.get('volatility_score', 0)),
            'sma_trend': float(advanced.get('sma_trend', 0)),
            'srsi_k': float(advanced.get('srsi_k', 50)),
            'srsi_d': float(advanced.get('srsi_d', 50)),
            'use_reversal': bool(use_reversal),
            'position_mode': position_mode
        }
        
        print(f"   🎯 Signal: {signal_type}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error analyzing {ticker}: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return None

def analyze_all_stocks(vwap_period=20, rsi_period=14, rsi_buy=50, rsi_sell=50, use_reversal=True,
                      position_mode='both', volume_days=20, momentum_days=5, max_workers=3, debug=False):
    """Analyze all stocks for VWAP + RSI strategy"""
    
    # Get tickers from config
    tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
    
    print(f"\n📊 COMPREHENSIVE VWAP + RSI ANALYSIS")
    print(f"📊 Analyzing {len(tickers)} stocks from config")
    print(f"📊 VWAP Period: {vwap_period} days")
    print(f"📊 RSI Settings: {rsi_period}-period, Buy>{rsi_buy}, Sell<{rsi_sell}")
    print(f"📊 Reversal Exit: {'ENABLED' if use_reversal else 'DISABLED'}")
    print(f"📊 Position Mode: {position_mode.upper()}")
    print(f"📊 Volume Period: {volume_days} trading days")
    print(f"🚀 Momentum Period: {momentum_days} trading days")
    print("="*60)
    
    all_signals = []
    
    # Analyze stocks
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(analyze_stock_comprehensive, ticker, vwap_period, rsi_period, 
                          rsi_buy, rsi_sell, use_reversal, position_mode, volume_days, momentum_days, debug): ticker 
            for ticker in tickers
        }
        
        completed = 0
        successful = 0
        failed = 0
        
        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            completed += 1
            
            try:
                result = future.result(timeout=45)  # Increased timeout
                if result:
                    all_signals.append(result)
                    successful += 1
                    signal_info = ""
                    if result.get('vwap_signal_info'):
                        vwap_type_str = result['vwap_signal_info']['signal_type']
                        strength = result['vwap_signal_info']['signal_strength']
                        vwap_trend = result['vwap_signal_info']['vwap_trend']
                        rsi_val = result['vwap_signal_info']['rsi_value']
                        signal_info = f" - {vwap_type_str} ({strength:.0f}% | {vwap_trend} | RSI:{rsi_val:.0f})"
                    print(f"✅ {ticker} ({completed}/{len(tickers)}) - {result['signal_type']}{signal_info}")
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
        print(f"   📊 Total signals: {len(all_signals)}")
    
    return all_signals

def filter_signals_by_type(all_signals, signal_types):
    """Filter signals by type"""
    return [signal for signal in all_signals if signal['signal_type'] in signal_types]

def sort_signals_properly(signals):
    """Sort signals with STRONG first, then WEAK, by strength within each category"""
    
    if not signals:
        return signals
    
    # Separate STRONG and WEAK signals
    strong_signals = [s for s in signals if 'STRONG' in s['signal_type']]
    weak_signals = [s for s in signals if 'WEAK' in s['signal_type']]
    
    # Sort by signal strength (descending)
    strong_signals.sort(key=lambda x: x['signal_strength'], reverse=True)
    weak_signals.sort(key=lambda x: x['signal_strength'], reverse=True)
    
    # Return STRONG first, then WEAK
    return strong_signals + weak_signals

def display_top_signals(signals, signal_title, top_n=10):
    """Display top N signals with comprehensive information"""
    
    if not signals:
        print(f"\n❌ No {signal_title} signals found!")
        return
    
    # Sort signals properly
    signals = sort_signals_properly(signals)
    
    # Get top N
    top_signals = signals[:top_n]
    
    print(f"\n🏆 TOP {len(top_signals)} {signal_title} SIGNALS")
    print(f"📊 VWAP + RSI Strategy Analysis")
    print("="*130)
    
    # Prepare table
    table_data = []
    headers = ['Rank', 'Ticker', 'VWAP Signal', 'Entry', 'Target', 'Stop', 'Strength%', 
              'VWAP Trend', 'RSI', 'SRSI', 'Price vs VWAP%', 'Volume', 'Momentum%', 'Qty']
    
    for i, signal in enumerate(top_signals, 1):
        strength = signal['signal_strength']
        
        # VWAP Signal information
        vwap_signal_name = 'HOLD'
        vwap_trend = signal.get('vwap_trend', 'NEUTRAL')
        rsi_value = signal.get('current_rsi', 50)
        price_vs_vwap = signal.get('price_vs_vwap', 0)
        
        if signal.get('vwap_signal_info'):
            vwap_info = signal['vwap_signal_info']
            if vwap_info['signal_type'] == 'LONG':
                vwap_momentum = vwap_info.get('vwap_momentum', 0)
                vwap_signal_name = f"📊 LONG ({vwap_momentum:+.2f}%)"
            elif vwap_info['signal_type'] == 'SHORT':
                vwap_momentum = vwap_info.get('vwap_momentum', 0)
                vwap_signal_name = f"📊 SHORT ({vwap_momentum:+.2f}%)"
        
        # VWAP trend with emoji
        vwap_trend_display = vwap_trend
        if vwap_trend == 'RISING':
            vwap_trend_display = "📈RISING"
        elif vwap_trend == 'FALLING':
            vwap_trend_display = "📉FALLING"
        
        # RSI with levels and color coding
        rsi_display = f"{rsi_value:.0f}"
        rsi_buy_level = signal.get('rsi_buy_level', 50)
        rsi_sell_level = signal.get('rsi_sell_level', 50)
        
        if rsi_value > 70:
            rsi_display += "🔴"  # Overbought
        elif rsi_value < 30:
            rsi_display += "🟢"  # Oversold
        elif rsi_value > rsi_buy_level:
            rsi_display += "⬆️"  # Above buy level
        elif rsi_value < rsi_sell_level:
            rsi_display += "⬇️"  # Below sell level
        
        # SRSI display
        srsi_k = signal.get('srsi_k', 50)
        srsi_d = signal.get('srsi_d', 50)
        srsi_display = f"{srsi_k:.0f}/{srsi_d:.0f}"
        
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
            vwap_signal_name,
            f"₹{signal['entry_price']:.2f}",
            f"₹{signal['target_price']:.2f}",
            f"₹{signal['stop_loss']:.2f}",
            f"{strength:.1f}%",
            vwap_trend_display,
            rsi_display,
            srsi_display,
            f"{price_vs_vwap:+.2f}%",
            volume_display,
            f"{signal['momentum']:+.1f}%",
            signal['position_size']
        ])
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Summary statistics
    avg_strength = sum(signal['signal_strength'] for signal in top_signals) / len(top_signals)
    avg_volume = sum(signal['volume_ratio'] for signal in top_signals) / len(top_signals)
    avg_momentum = sum(signal['momentum'] for signal in top_signals) / len(top_signals)
    avg_rsi = sum(signal.get('current_rsi', 50) for signal in top_signals) / len(top_signals)
    avg_price_vs_vwap = sum(signal.get('price_vs_vwap', 0) for signal in top_signals) / len(top_signals)
    
    # Signal breakdown
    long_count = sum(1 for s in top_signals if s.get('vwap_signal_info', {}).get('signal_type') == 'LONG')
    short_count = sum(1 for s in top_signals if s.get('vwap_signal_info', {}).get('signal_type') == 'SHORT')
    rising_vwap_count = sum(1 for s in top_signals if s.get('vwap_trend') == 'RISING')
    falling_vwap_count = sum(1 for s in top_signals if s.get('vwap_trend') == 'FALLING')
    
    print(f"\n📊 SUMMARY:")
    print(f"   📊 {signal_title} signals: {len(signals)}")
    print(f"   📈 Average strength: {avg_strength:.1f}%")
    print(f"   📊 Average volume ratio: {avg_volume:.1f}x")
    print(f"   🚀 Average momentum: {avg_momentum:+.1f}%")
    print(f"   📊 Average RSI: {avg_rsi:.1f}")
    print(f"   📊 Avg Price vs VWAP: {avg_price_vs_vwap:+.2f}%")
    if long_count > 0:
        print(f"   📈 Long signals: {long_count}")
    if short_count > 0:
        print(f"   📉 Short signals: {short_count}")
    if rising_vwap_count > 0:
        print(f"   📈 Rising VWAP: {rising_vwap_count}")
    if falling_vwap_count > 0:
        print(f"   📉 Falling VWAP: {falling_vwap_count}")
    
    print(f"\n🏆 RANKING EXPLANATION:")
    print(f"   📊 Sorted by: STRONG signals first, then WEAK signals")
    print(f"   🎯 Strength includes: VWAP momentum + RSI level + Price vs VWAP + Volume")
    print(f"   📊 LONG = VWAP rising + RSI > buy level (trend following)")
    print(f"   📊 SHORT = VWAP falling + RSI < sell level (trend following)")
    print(f"   📊 Price vs VWAP% = How far price is from VWAP (+ above, - below)")

def generate_comprehensive_html(all_signals, vwap_period, rsi_period, rsi_buy, rsi_sell, use_reversal,
                              position_mode, volume_days, momentum_days, output_dir):
    """Generate comprehensive HTML report for VWAP + RSI strategy"""
    
    if not all_signals:
        print("❌ No signals to generate report")
        return None
    
    # Separate signals by type
    buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY', 'WEAK_BUY'])
    sell_signals = filter_signals_by_type(all_signals, ['STRONG_SELL', 'WEAK_SELL'])
    hold_signals = filter_signals_by_type(all_signals, ['HOLD'])
    
    # Sort properly
    buy_signals = sort_signals_properly(buy_signals) if buy_signals else []
    sell_signals = sort_signals_properly(sell_signals) if sell_signals else []
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VWAP + RSI Strategy Analysis - {datetime.now().strftime('%Y-%m-%d')}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                min-height: 100vh;
            }}
            .container {{
                max-width: 1600px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 15px 35px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
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
                font-size: 0.8em;
            }}
            th, td {{
                padding: 8px 6px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background: #f8f9fa;
                font-weight: bold;
                position: sticky;
                top: 0;
                font-size: 0.75em;
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
            .strategy-info {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
                border-left: 5px solid #667eea;
            }}
            .features-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }}
            .feature-card {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                border-left: 4px solid #667eea;
            }}
            .vwap-visual {{
                background: linear-gradient(90deg, #4CAF50 0%, #2196F3 50%, #FF9800 100%);
                height: 15px;
                border-radius: 10px;
                margin: 10px 0;
                position: relative;
            }}
            .vwap-label {{
                position: absolute;
                left: 50%;
                top: -25px;
                transform: translateX(-50%);
                color: #333;
                font-weight: bold;
                font-size: 0.9em;
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
                <h1>📊 VWAP + RSI STRATEGY ANALYSIS</h1>
                <p><strong>Volume Weighted Average Price with RSI Confirmation</strong></p>
                <p>VWAP: {vwap_period}-period | RSI: {rsi_period}-period (Buy>{rsi_buy}, Sell<{rsi_sell})</p>
                <p>Reversal Exit: {'✅ ENABLED' if use_reversal else '❌ DISABLED'} | Mode: {position_mode.upper()}</p>
                <p>Volume: {volume_days} days | Momentum: {momentum_days} days</p>
                <p>Generated: {timestamp}</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>{len(buy_signals)}</h3>
                    <p>📊 BUY Signals</p>
                </div>
                <div class="stat-card">
                    <h3>{len(sell_signals)}</h3>
                    <p>📊 SELL Signals</p>
                </div>
                <div class="stat-card">
                    <h3>{len(hold_signals)}</h3>
                    <p>⚪ HOLD Signals</p>
                </div>
                <div class="stat-card">
                    <h3>{len(all_signals)}</h3>
                    <p>📊 Total Analyzed</p>
                </div>
            </div>
            
            <div class="strategy-info">
                <h3>📊 VWAP + RSI Strategy (Based on PineScript Logic)</h3>
                <div class="vwap-visual">
                    <div class="vwap-label">VWAP Trend Analysis</div>
                </div>
                <div class="features-grid">
                    <div class="feature-card">
                        <h4>📊 VWAP Analysis</h4>
                        <p><strong>VWAP:</strong> Volume Weighted Average Price ({vwap_period}-period rolling)</p>
                        <p><strong>Rising VWAP:</strong> vwap > vwap[1] - Bullish momentum</p>
                        <p><strong>Falling VWAP:</strong> vwap < vwap[1] - Bearish momentum</p>
                        <p><strong>Price vs VWAP:</strong> Key relationship for trend confirmation</p>
                    </div>
                    <div class="feature-card">
                        <h4>📊 RSI Confirmation</h4>
                        <p><strong>RSI Period:</strong> {rsi_period} periods</p>
                        <p><strong>Buy Level:</strong> RSI > {rsi_buy} (bullish momentum)</p>
                        <p><strong>Sell Level:</strong> RSI < {rsi_sell} (bearish momentum)</p>
                        <p><strong>Dual Confirmation:</strong> VWAP trend + RSI level alignment</p>
                    </div>
                    <div class="feature-card">
                        <h4>📈 Entry Conditions</h4>
                        <p><strong>LONG:</strong> VWAP rising AND RSI > {rsi_buy}</p>
                        <p><strong>SHORT:</strong> VWAP falling AND RSI < {rsi_sell}</p>
                        <p><strong>Session:</strong> Original strategy: 11:00-15:00 trading window</p>
                        <p><strong>Adaptation:</strong> Daily analysis with trend confirmation</p>
                    </div>
                    <div class="feature-card">
                        <h4>🛑 Exit Conditions</h4>
                        <p><strong>Reversal Exit:</strong> {'ENABLED - Exit on VWAP trend reversal' if use_reversal else 'DISABLED - Hold until other conditions'}</p>
                        <p><strong>Long Exit:</strong> VWAP starts falling (if reversal enabled)</p>
                        <p><strong>Short Exit:</strong> VWAP starts rising (if reversal enabled)</p>
                        <p><strong>Session End:</strong> Original: Close all at 15:00</p>
                    </div>
                </div>
            </div>
    """
    
    # Generate BUY signals table
    if buy_signals:
        html_content += f"""
            <div class="section">
                <h2>📊 TOP VWAP + RSI BUY SIGNALS (RISING VWAP + HIGH RSI)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Ticker</th>
                            <th>VWAP Signal</th>
                            <th>Entry</th>
                            <th>Target</th>
                            <th>Stop</th>
                            <th>Strength</th>
                            <th>VWAP Trend</th>
                            <th>RSI</th>
                            <th>SRSI</th>
                            <th>Price vs VWAP</th>
                            <th>Volume</th>
                            <th>Momentum</th>
                            <th>Qty</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for i, signal in enumerate(buy_signals[:20], 1):  # Top 20
            strength = signal['signal_strength']
            momentum_class = 'positive' if signal['momentum'] >= 0 else 'negative'
            
            # VWAP Signal display
            vwap_signal_display = '📊 VWAP LONG'
            if signal.get('vwap_signal_info'):
                vwap_momentum = signal['vwap_signal_info'].get('vwap_momentum', 0)
                vwap_signal_display = f'📊 LONG ({vwap_momentum:+.2f}%)'
            
            # VWAP trend
            vwap_trend = signal.get('vwap_trend', 'NEUTRAL')
            vwap_trend_display = '📈RISING' if vwap_trend == 'RISING' else '📉FALLING' if vwap_trend == 'FALLING' else 'NEUT'
            
            # RSI with buy level
            rsi_value = signal.get('current_rsi', 50)
            rsi_buy_level = signal.get('rsi_buy_level', 50)
            rsi_display = f"{rsi_value:.0f}"
            if rsi_value > rsi_buy_level:
                rsi_display += "⬆️"
            
            # Price vs VWAP
            price_vs_vwap = signal.get('price_vs_vwap', 0)
            
            # Volume strength indicator
            volume_display = f"{signal['volume_ratio']:.1f}x"
            try:
                volume_strength = signal['volume_analysis']['volume_strength']
                if volume_strength == 'VERY_HIGH':
                    volume_display += " 🟢"
                elif volume_strength == 'HIGH':
                    volume_display += " 🟡"
                elif volume_strength == 'WEAK':
                    volume_display += " 🔴"
            except:
                pass
            
            html_content += f"""
                        <tr>
                            <td class="rank">{i}</td>
                            <td class="ticker">{signal['ticker']}</td>
                            <td>{vwap_signal_display}</td>
                            <td>₹{signal['entry_price']:.2f}</td>
                            <td>₹{signal['target_price']:.2f}</td>
                            <td>₹{signal['stop_loss']:.2f}</td>
                            <td>{strength:.1f}%</td>
                            <td>{vwap_trend_display}</td>
                            <td>{rsi_display}</td>
                            <td>{signal.get('srsi_k', 50):.0f}/{signal.get('srsi_d', 50):.0f}</td>
                            <td>{price_vs_vwap:+.2f}%</td>
                            <td>{volume_display}</td>
                            <td class="{momentum_class}">{signal['momentum']:+.1f}%</td>
                            <td>{signal['position_size']}</td>
                        </tr>
            """
        
        html_content += """
                    </tbody>
                </table>
            </div>
        """
    
    # Generate SELL signals table
    if sell_signals:
        html_content += f"""
            <div class="section">
                <h2>📊 TOP VWAP + RSI SELL SIGNALS (FALLING VWAP + LOW RSI)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Ticker</th>
                            <th>VWAP Signal</th>
                            <th>Entry</th>
                            <th>Target</th>
                            <th>Stop</th>
                            <th>Strength</th>
                            <th>VWAP Trend</th>
                            <th>RSI</th>
                            <th>SRSI</th>
                            <th>Price vs VWAP</th>
                            <th>Volume</th>
                            <th>Momentum</th>
                            <th>Qty</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for i, signal in enumerate(sell_signals[:20], 1):  # Top 20
            strength = signal['signal_strength']
            momentum_class = 'positive' if signal['momentum'] >= 0 else 'negative'
            
            # VWAP Signal display
            vwap_signal_display = '📊 VWAP SHORT'
            if signal.get('vwap_signal_info'):
                vwap_momentum = signal['vwap_signal_info'].get('vwap_momentum', 0)
                vwap_signal_display = f'📊 SHORT ({vwap_momentum:+.2f}%)'
            
            # VWAP trend
            vwap_trend = signal.get('vwap_trend', 'NEUTRAL')
            vwap_trend_display = '📈RISING' if vwap_trend == 'RISING' else '📉FALLING' if vwap_trend == 'FALLING' else 'NEUT'
            
            # RSI with sell level
            rsi_value = signal.get('current_rsi', 50)
            rsi_sell_level = signal.get('rsi_sell_level', 50)
            rsi_display = f"{rsi_value:.0f}"
            if rsi_value < rsi_sell_level:
                rsi_display += "⬇️"
            
            # Price vs VWAP
            price_vs_vwap = signal.get('price_vs_vwap', 0)
            
            # Volume strength indicator
            volume_display = f"{signal['volume_ratio']:.1f}x"
            try:
                volume_strength = signal['volume_analysis']['volume_strength']
                if volume_strength == 'VERY_HIGH':
                    volume_display += " 🟢"
                elif volume_strength == 'HIGH':
                    volume_display += " 🟡"
                elif volume_strength == 'WEAK':
                    volume_display += " 🔴"
            except:
                pass
            
            html_content += f"""
                        <tr>
                            <td class="rank">{i}</td>
                            <td class="ticker">{signal['ticker']}</td>
                            <td>{vwap_signal_display}</td>
                            <td>₹{signal['entry_price']:.2f}</td>
                            <td>₹{signal['target_price']:.2f}</td>
                            <td>₹{signal['stop_loss']:.2f}</td>
                            <td>{strength:.1f}%</td>
                            <td>{vwap_trend_display}</td>
                            <td>{rsi_display}</td>
                            <td>{signal.get('srsi_k', 50):.0f}/{signal.get('srsi_d', 50):.0f}</td>
                            <td>{price_vs_vwap:+.2f}%</td>
                            <td>{volume_display}</td>
                            <td class="{momentum_class}">{signal['momentum']:+.1f}%</td>
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
                <p><strong>⚠️ Disclaimer:</strong> This analysis is for educational purposes only. VWAP + RSI strategy works best in trending markets with strong volume. The original strategy was designed for intraday trading (11:00-15:00). Always use proper risk management.</p>
                <p><strong>📊 Strategy:</strong> Volume Weighted Average Price with RSI momentum confirmation</p>
                <p><strong>🎯 Logic:</strong> Buy when VWAP rising + RSI high, Sell when VWAP falling + RSI low</p>
                <p><strong>📊 VWAP:</strong> Volume-weighted price over specified period - superior to simple moving averages</p>
                <p><strong>📊 RSI:</strong> Momentum oscillator confirming price strength in VWAP direction</p>
                <p><strong>🛑 Exits:</strong> VWAP trend reversal (if enabled) or session-based management</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Save HTML
    html_filename = f"vwap_rsi_strategy_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    html_path = os.path.join(output_dir, html_filename)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return html_path

def save_results_json(all_signals, output_dir, vwap_period, rsi_period):
    """Save comprehensive results to JSON"""
    
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
    
    # Create comprehensive metadata
    json_data = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'total_stocks_analyzed': len(json_signals),
            'vwap_period': int(vwap_period),
            'rsi_period': int(rsi_period),
            'strategy': 'VWAP + RSI Strategy (Based on PineScript)',
            'features': [
                'Volume Weighted Average Price Analysis',
                'RSI Momentum Confirmation', 
                'VWAP Trend Detection (Rising/Falling)',
                'Price vs VWAP Relationship',
                'Stochastic RSI Analysis',
                'Support/Resistance Levels',
                'Momentum and Velocity Analysis',
                'Multi-confirmation Signal Strength',
                'Dynamic Entry/Exit with Reversal Logic'
            ]
        },
        'signals': json_signals
    }
    
    # Save JSON
    json_filename = f"vwap_rsi_strategy_signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_path = os.path.join(output_dir, json_filename)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    return json_path

def main():
    """Main function with comprehensive VWAP + RSI analysis"""
    parser = argparse.ArgumentParser(description="Advanced VWAP + RSI Strategy Analyzer")
    
    parser.add_argument('--vwap-period', type=int, default=20, 
                       help='VWAP calculation period (default: 20)')
    parser.add_argument('--rsi-period', type=int, default=14, 
                       help='RSI calculation period (default: 14)')
    parser.add_argument('--rsi-buy', type=int, default=50, 
                       help='RSI buy level (default: 50)')
    parser.add_argument('--rsi-sell', type=int, default=50, 
                       help='RSI sell level (default: 50)')
    parser.add_argument('--use-reversal', action='store_true', default=True,
                       help='Use VWAP reversal exits (default: True)')
    parser.add_argument('--no-reversal', action='store_true',
                       help='Disable VWAP reversal exits')
    parser.add_argument('--position-mode', type=str, default='both', 
                       choices=['both', 'long', 'short', 'long_only', 'short_only'],
                       help='Position mode (default: both)')
    parser.add_argument('--volume-days', type=int, default=20, 
                       help='Volume average days (default: 20)')
    parser.add_argument('--momentum-days', type=int, default=5, 
                       help='Momentum calculation days (default: 5)')
    parser.add_argument('--top', type=int, default=15, 
                       help='Top N signals to display (default: 15)')
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
                       help='Show only BUY signals (VWAP + RSI longs)')
    parser.add_argument('--sell-only', action='store_true', 
                       help='Show only SELL signals (VWAP + RSI shorts)')
    
    args = parser.parse_args()
    
    # Handle reversal flag
    use_reversal = args.use_reversal and not args.no_reversal
    
    # Validate RSI levels
    if not (0 <= args.rsi_buy <= 100) or not (0 <= args.rsi_sell <= 100):
        print("❌ Error: RSI levels must be between 0 and 100")
        return
    
    # Test single ticker if requested
    if args.test_single:
        print(f"🧪 TESTING SINGLE TICKER: {args.test_single}")
        print("="*50)
        result = analyze_stock_comprehensive(
            args.test_single, 
            args.vwap_period, 
            args.rsi_period, 
            args.rsi_buy,
            args.rsi_sell,
            use_reversal,
            args.position_mode,
            args.volume_days, 
            args.momentum_days, 
            debug=True
        )
        if result:
            print(f"\n✅ SUCCESS! Signal: {result['signal_type']}")
            if result.get('vwap_signal_info'):
                vwap_info = result['vwap_signal_info']
                print(f"📊 VWAP Signal: {vwap_info['signal_type']} - Strength: {vwap_info['signal_strength']:.1f}%")
                print(f"📊 Entry: ₹{result['entry_price']:.2f} | Target: ₹{result['target_price']:.2f} | Stop: ₹{result['stop_loss']:.2f}")
                print(f"📊 VWAP: ₹{result['current_vwap']:.2f} ({result['vwap_trend']}) | RSI: {result['current_rsi']:.1f}")
                print(f"📊 VWAP Momentum: {result['vwap_momentum']:+.2f}% | Price vs VWAP: {result['price_vs_vwap']:+.2f}%")
                print(f"📈 SRSI: {result['srsi_k']:.1f}/{result['srsi_d']:.1f}")
        else:
            print(f"\n❌ No result for {args.test_single}")
        return
    
    print("📊 ADVANCED VWAP + RSI STRATEGY ANALYZER")
    print("🔄 Volume Weighted Average Price with RSI Confirmation")
    print("="*60)
    print(f"📊 VWAP Period: {args.vwap_period} days")
    print(f"📊 RSI Settings: {args.rsi_period}-period, Buy>{args.rsi_buy}, Sell<{args.rsi_sell}")
    print(f"📊 Reversal Exit: {'ENABLED' if use_reversal else 'DISABLED'}")
    print(f"📊 Position Mode: {args.position_mode.upper()}")
    print(f"📊 Volume Period: {args.volume_days} trading days") 
    print(f"🚀 Momentum Period: {args.momentum_days} trading days")
    print(f"🏆 Top Signals: {args.top}")
    print(f"⚙️  Workers: {args.workers}")
    print("="*60)
    
    # Set output directory
    output_dir = args.output or getattr(config, 'OUTPUT_DIR', 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Analyze all stocks
    all_signals = analyze_all_stocks(
        vwap_period=args.vwap_period,
        rsi_period=args.rsi_period,
        rsi_buy=args.rsi_buy,
        rsi_sell=args.rsi_sell,
        use_reversal=use_reversal,
        position_mode=args.position_mode,
        volume_days=args.volume_days, 
        momentum_days=args.momentum_days,
        max_workers=args.workers,
        debug=args.debug
    )
    
    if not all_signals:
        print("\n❌ No signals generated!")
        print("💡 TROUBLESHOOTING TIPS:")
        print("   🔧 Try different VWAP period: --vwap-period 10 or --vwap-period 30")
        print("   🔧 Adjust RSI levels: --rsi-buy 40 --rsi-sell 60")
        print("   🔧 Different RSI period: --rsi-period 9 or --rsi-period 21")
        print("   🔧 Disable reversal: --no-reversal")
        print("   🔧 Change position mode: --position-mode long")
        print("   🔧 Reduce periods: --volume-days 10 --momentum-days 3")
        print("   🔧 Enable debug mode: --debug")
        print("   🔧 Test single stock: --test-single RELIANCE --debug")
        return
    
    # Display results based on arguments
    if args.buy_only:
        buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY', 'WEAK_BUY'])
        buy_signals = sort_signals_properly(buy_signals) if buy_signals else []
        display_top_signals(buy_signals, "VWAP + RSI BUY", args.top)
    elif args.sell_only:
        sell_signals = filter_signals_by_type(all_signals, ['STRONG_SELL', 'WEAK_SELL'])
        sell_signals = sort_signals_properly(sell_signals) if sell_signals else []
        display_top_signals(sell_signals, "VWAP + RSI SELL", args.top)
    elif args.show_all:
        # Show all types
        buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY', 'WEAK_BUY'])
        sell_signals = filter_signals_by_type(all_signals, ['STRONG_SELL', 'WEAK_SELL'])
        hold_signals = filter_signals_by_type(all_signals, ['HOLD'])
        
        if buy_signals:
            buy_signals = sort_signals_properly(buy_signals)
            display_top_signals(buy_signals, "VWAP + RSI BUY", args.top)
        if sell_signals:
            sell_signals = sort_signals_properly(sell_signals)
            display_top_signals(sell_signals, "VWAP + RSI SELL", args.top)
        
        print(f"\n📊 OVERALL SUMMARY:")
        print(f"   📊 VWAP + RSI BUY signals: {len(buy_signals)}")
        print(f"   📊 VWAP + RSI SELL signals: {len(sell_signals)}")
        print(f"   ⚪ HOLD signals: {len(hold_signals)}")
        print(f"   📊 Total analyzed: {len(all_signals)}")
    else:
        # Default: Show BUY signals only
        buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY', 'WEAK_BUY'])
        buy_signals = sort_signals_properly(buy_signals) if buy_signals else []
        display_top_signals(buy_signals, "VWAP + RSI BUY", args.top)
    
    # Generate reports
    print(f"\n📄 Generating comprehensive reports...")
    
    # HTML Report
    html_path = generate_comprehensive_html(
        all_signals, args.vwap_period, args.rsi_period, args.rsi_buy, args.rsi_sell, use_reversal,
        args.position_mode, args.volume_days, args.momentum_days, output_dir
    )
    if html_path:
        print(f"🌐 HTML Report: {html_path}")
        print(f"🔗 Open: file://{os.path.abspath(html_path)}")
    
    # JSON Report
    json_path = save_results_json(all_signals, output_dir, args.vwap_period, args.rsi_period)
    if json_path:
        print(f"📊 JSON Data: {json_path}")
    
    print(f"\n✅ Analysis Complete!")
    print(f"📁 Output Directory: {os.path.abspath(output_dir)}")
    
    # Trading notes
    print(f"\n💡 VWAP + RSI STRATEGY FEATURES:")
    print(f"   📊 VWAP: Volume Weighted Average Price ({args.vwap_period}-period rolling)")
    print(f"   📊 VWAP TREND: Rising (bullish) vs Falling (bearish) momentum")
    print(f"   📊 RSI CONFIRMATION: {args.rsi_period}-period RSI with Buy>{args.rsi_buy}, Sell<{args.rsi_sell}")
    print(f"   📈 LONG ENTRY: VWAP rising AND RSI > {args.rsi_buy}")
    print(f"   📉 SHORT ENTRY: VWAP falling AND RSI < {args.rsi_sell}")
    print(f"   🛑 REVERSAL EXIT: {'ENABLED - Exit on VWAP trend change' if use_reversal else 'DISABLED - Hold positions longer'}")
    print(f"   📊 PRICE vs VWAP: Key relationship for entry quality")
    print(f"   📊 SIGNAL STRENGTH: VWAP momentum + RSI level + Price distance + Volume")
    print(f"   ⚖️  POSITION SIZING: 1% risk-based position calculation")
    print(f"   🕐 ORIGINAL LOGIC: Intraday 11:00-15:00 session (adapted for daily analysis)")
    
    print(f"\n🧪 TROUBLESHOOTING COMMANDS:")
    print(f"   python {sys.argv[0]} --test-single RELIANCE --debug")
    print(f"   python {sys.argv[0]} --vwap-period 15 --rsi-buy 40 --debug --show-all")
    print(f"   python {sys.argv[0]} --position-mode long --no-reversal --top 20")

if __name__ == "__main__":
    main()