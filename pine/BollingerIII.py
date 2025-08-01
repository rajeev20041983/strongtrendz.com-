#!/usr/bin/env python
# bollinger_bands_iii_analyzer.py - Advanced Bollinger Bands with Intraday Intensity Index Strategy

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
    """Get stock data for comprehensive Bollinger Bands analysis"""
    try:
        # Add .NS for NSE stocks
        symbol = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
        
        # Get enough data for analysis
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

def calculate_moving_average(data, period, ma_type='SMA'):
    """Calculate moving average (SMA or EMA)"""
    try:
        if ma_type.upper() == 'EMA':
            return data.ewm(span=period).mean()
        else:  # SMA
            return data.rolling(window=period).mean()
    except Exception:
        return data.rolling(window=period).mean()  # Fallback to SMA

def calculate_bollinger_bands(data, length=20, multiplier=2.0, ma_type='SMA', price_source='Close'):
    """
    Calculate Bollinger Bands with custom standard deviation
    Following the PineScript logic exactly
    """
    try:
        if len(data) < length:
            return None, None, None
        
        # Get price source
        if price_source.lower() == 'close':
            prices = data['Close']
        elif price_source.lower() == 'open':
            prices = data['Open']
        elif price_source.lower() == 'high':
            prices = data['High']
        elif price_source.lower() == 'low':
            prices = data['Low']
        else:
            prices = data['Close']  # Default fallback
        
        # Calculate moving average (basis)
        basis = calculate_moving_average(prices, length, ma_type)
        
        # Calculate standard deviation using the PineScript method
        # This calculates rolling standard deviation
        if ma_type.upper() == 'EMA':
            # For EMA-based BB, use rolling std but with EMA basis
            rolling_std = prices.rolling(window=length).std()
        else:
            # Standard rolling standard deviation
            rolling_std = prices.rolling(window=length).std()
        
        # Calculate upper and lower bands
        deviation = multiplier * rolling_std
        upper_band = basis + deviation
        lower_band = basis - deviation
        
        return upper_band, basis, lower_band
        
    except Exception as e:
        print(f"Error calculating Bollinger Bands: {e}")
        return None, None, None

def calculate_intraday_intensity_index(data, length=21):
    """
    Calculate Intraday Intensity Index (III) following PineScript logic:
    k1 = (2 * close - high - low) * volume
    k2 = high != low ? high - low : 1
    i = k1 / k2
    iSum = sum(i, length)
    """
    try:
        if len(data) < length + 1:
            return None, 0
        
        # Calculate k1: (2 * close - high - low) * volume
        k1 = (2 * data['Close'] - data['High'] - data['Low']) * data['Volume']
        
        # Calculate k2: high != low ? high - low : 1
        k2 = np.where(data['High'] != data['Low'], data['High'] - data['Low'], 1)
        
        # Calculate i: k1 / k2
        i = k1 / k2
        
        # Calculate rolling sum over length periods
        i_sum = i.rolling(window=length).sum()
        
        # Get current III value
        current_iii = i_sum.iloc[-1] if not pd.isna(i_sum.iloc[-1]) else 0
        
        return i_sum, current_iii
        
    except Exception as e:
        print(f"Error calculating III: {e}")
        return None, 0

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
    except Exception:
        return 50

def detect_bb_bounce_signals(data, bb_upper, bb_basis, bb_lower, iii_sum=None, use_iii=True, 
                           time_stop=20, early_exit=False, position_mode='both'):
    """
    Detect Bollinger Bands bounce signals following PineScript logic:
    
    BUY: close[1] < BBlower[1] and close > BBlower and (withIII ? iSum > 0 : 1)
    SELL: close > BBbasis or (earlyExit ? strategy.openprofit > 0 : 0) or barssince(buy) > timeStop
    
    SHORT: close[1] > BBupper[1] and close < BBupper and (withIII ? iSum < 0 : 1)  
    COVER: close < BBbasis or (earlyExit ? strategy.openprofit > 0 : 0) or barssince(short) > timeStop
    """
    try:
        if len(data) < 3:
            return None
        
        # Get current and previous values
        current_close = data['Close'].iloc[-1]
        prev_close = data['Close'].iloc[-2]
        current_upper = bb_upper.iloc[-1]
        prev_upper = bb_upper.iloc[-2]
        current_lower = bb_lower.iloc[-1]
        prev_lower = bb_lower.iloc[-2]
        current_basis = bb_basis.iloc[-1]
        current_volume = data['Volume'].iloc[-1]
        
        # Check for NaN values
        if pd.isna(current_upper) or pd.isna(current_lower) or pd.isna(current_basis):
            return None
        
        # Get III confirmation if available
        iii_current = 0
        if iii_sum is not None and len(iii_sum) > 0:
            iii_current = iii_sum.iloc[-1] if not pd.isna(iii_sum.iloc[-1]) else 0
        
        signals = []
        
        # LONG ENTRY: Bounce off lower Bollinger Band
        # Condition: close[1] < BBlower[1] and close > BBlower and (withIII ? iSum > 0 : 1)
        long_condition = (prev_close < prev_lower and 
                         current_close > current_lower and
                         (not use_iii or iii_current > 0))
        
        if long_condition and position_mode.lower() in ['both', 'long', 'long_only']:
            # Calculate signal strength based on bounce magnitude and III confirmation
            bounce_strength = ((current_close - current_lower) / current_lower) * 100
            iii_strength = max(0, min(100, abs(iii_current) / 1000000 * 100)) if use_iii else 50
            
            # Distance from basis (target)
            distance_to_basis = ((current_basis - current_close) / current_close) * 100
            
            # Combined strength
            signal_strength = (bounce_strength * 0.4 + iii_strength * 0.3 + 
                             min(distance_to_basis, 10) * 0.3)
            
            signals.append({
                'signal_type': 'LONG',
                'entry_price': current_close,
                'stop_loss': current_lower * 0.995,  # Slightly below lower band
                'target_price': current_basis,  # Mean reversion to basis
                'signal_strength': signal_strength,
                'bounce_strength': bounce_strength,
                'iii_value': iii_current,
                'iii_confirmation': iii_current > 0 if use_iii else True,
                'distance_to_target': distance_to_basis,
                'volume': current_volume,
                'bb_upper': current_upper,
                'bb_basis': current_basis,
                'bb_lower': current_lower
            })
        
        # SHORT ENTRY: Bounce off upper Bollinger Band  
        # Condition: close[1] > BBupper[1] and close < BBupper and (withIII ? iSum < 0 : 1)
        short_condition = (prev_close > prev_upper and 
                          current_close < current_upper and
                          (not use_iii or iii_current < 0))
        
        if short_condition and position_mode.lower() in ['both', 'short', 'short_only']:
            # Calculate signal strength
            bounce_strength = ((current_upper - current_close) / current_upper) * 100
            iii_strength = max(0, min(100, abs(iii_current) / 1000000 * 100)) if use_iii else 50
            
            # Distance from basis (target)
            distance_to_basis = ((current_close - current_basis) / current_close) * 100
            
            # Combined strength
            signal_strength = (bounce_strength * 0.4 + iii_strength * 0.3 + 
                             min(distance_to_basis, 10) * 0.3)
            
            signals.append({
                'signal_type': 'SHORT',
                'entry_price': current_close,
                'stop_loss': current_upper * 1.005,  # Slightly above upper band
                'target_price': current_basis,  # Mean reversion to basis
                'signal_strength': signal_strength,
                'bounce_strength': bounce_strength,
                'iii_value': iii_current,
                'iii_confirmation': iii_current < 0 if use_iii else True,
                'distance_to_target': distance_to_basis,
                'volume': current_volume,
                'bb_upper': current_upper,
                'bb_basis': current_basis,
                'bb_lower': current_lower
            })
        
        return signals if signals else None
        
    except Exception as e:
        print(f"Error detecting BB signals: {e}")
        return None

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

def calculate_advanced_signals(data, current_price, bb_signals):
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
    
    # RSI and Stochastic RSI
    rsi = calculate_rsi(data['Close'])
    srsi_k, srsi_d = calculate_stochastic_rsi(data)
    
    # EMA trend filters
    ema_20 = data['Close'].ewm(span=20).mean().iloc[-1] if len(data) >= 20 else current_price
    ema_50 = data['Close'].ewm(span=50).mean().iloc[-1] if len(data) >= 50 else current_price
    
    # Trend direction
    if current_price > ema_20 > ema_50:
        trend_direction = 'STRONG_BULLISH'
    elif current_price > ema_20:
        trend_direction = 'BULLISH'
    elif current_price < ema_20 < ema_50:
        trend_direction = 'STRONG_BEARISH'
    elif current_price < ema_20:
        trend_direction = 'BEARISH'
    else:
        trend_direction = 'NEUTRAL'
    
    # Distance from support/resistance
    support_distance = ((current_price - support_level) / current_price) * 100
    resistance_distance = ((resistance_level - current_price) / current_price) * 100
    
    # Bollinger Band position
    bb_position = 0.5  # Default neutral
    if bb_signals and len(bb_signals) > 0:
        signal = bb_signals[0]
        bb_range = signal['bb_upper'] - signal['bb_lower']
        if bb_range > 0:
            bb_position = (current_price - signal['bb_lower']) / bb_range
    
    return {
        'support_level': support_level,
        'resistance_level': resistance_level,
        'pivot_level': pivot_level,
        'support_distance': support_distance,
        'resistance_distance': resistance_distance,
        'volatility_score': volatility_score,
        'sma_trend': sma_trend,
        'trend_direction': trend_direction,
        'rsi': rsi,
        'srsi_k': srsi_k,
        'srsi_d': srsi_d,
        'ema_20': ema_20,
        'ema_50': ema_50,
        'bb_position': bb_position,
        'atr': atr if 'atr' in locals() else volatility_score * current_price / 100
    }

def analyze_stock_comprehensive(ticker, bb_length=20, bb_multiplier=2.0, bb_type='SMA', 
                              bb_price='Close', iii_length=21, use_iii=True, time_stop=20,
                              position_mode='both', volume_days=20, momentum_days=5, debug=False):
    """
    Comprehensive stock analysis for Bollinger Bands + III strategy
    """
    try:
        print(f"📊 Analyzing {ticker} (Bollinger Bands + III Strategy)...")
        
        # Initialize variables
        volume_analysis = {
            'volume_strength': 'NORMAL', 
            'volume_trend': 'NEUTRAL', 
            'volume_sma_ratio': 1.0,
            'volume_quality': 'AVERAGE'
        }
        advanced = {
            'support_level': 0, 'resistance_level': 0, 'pivot_level': 0,
            'volatility_score': 0, 'sma_trend': 0, 'rsi': 50,
            'srsi_k': 50, 'srsi_d': 50, 'ema_20': 0, 'ema_50': 0,
            'trend_direction': 'NEUTRAL', 'bb_position': 0.5
        }
        
        # Get data
        data = get_stock_data(ticker, 100)
        if data is None:
            return None
        
        print(f"   📅 Data: {len(data)} trading days available")
        
        # Calculate Bollinger Bands
        bb_upper, bb_basis, bb_lower = calculate_bollinger_bands(
            data, bb_length, bb_multiplier, bb_type, bb_price
        )
        
        if bb_upper is None or bb_basis is None or bb_lower is None:
            print(f"   ❌ Could not calculate Bollinger Bands")
            return None
        
        # Calculate Intraday Intensity Index
        iii_sum, current_iii = calculate_intraday_intensity_index(data, iii_length)
        
        if debug:
            print(f"   🐛 DEBUG: BB Upper: {bb_upper.iloc[-1]:.2f}, Basis: {bb_basis.iloc[-1]:.2f}, Lower: {bb_lower.iloc[-1]:.2f}")
            print(f"   🐛 DEBUG: III Current: {current_iii:.0f}")
        
        # Detect Bollinger Band bounce signals
        bb_signals = detect_bb_bounce_signals(
            data, bb_upper, bb_basis, bb_lower, iii_sum, use_iii, time_stop, False, position_mode
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
        bb_signal_info = None
        
        if bb_signals and len(bb_signals) > 0:
            # Use the first (strongest) signal
            bb_signal_info = bb_signals[0]
            
            if bb_signal_info['signal_type'] == 'LONG':
                signal_type = 'STRONG_BUY' if bb_signal_info['signal_strength'] >= 60 else 'WEAK_BUY'
                entry_price = bb_signal_info['entry_price']
                stop_loss = bb_signal_info['stop_loss']
                target_price = bb_signal_info['target_price']
                signal_strength = bb_signal_info['signal_strength']
                
                print(f"   📈 BB LONG signal - Strength: {signal_strength:.1f}% (III: {current_iii:.0f})")
                
            elif bb_signal_info['signal_type'] == 'SHORT':
                signal_type = 'STRONG_SELL' if bb_signal_info['signal_strength'] >= 60 else 'WEAK_SELL'
                entry_price = bb_signal_info['entry_price']
                stop_loss = bb_signal_info['stop_loss']
                target_price = bb_signal_info['target_price']
                signal_strength = bb_signal_info['signal_strength']
                
                print(f"   📉 BB SHORT signal - Strength: {signal_strength:.1f}% (III: {current_iii:.0f})")
        else:
            print(f"   ⚪ No BB bounce signals detected")
        
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
        print(f"   📊 III Value: {current_iii:.0f}")
        
        # Calculate advanced signals
        try:
            advanced = calculate_advanced_signals(data, current_price, bb_signals)
            print(f"   📈 RSI: {advanced['rsi']:.1f} | SRSI: {advanced['srsi_k']:.1f}/{advanced['srsi_d']:.1f}")
            print(f"   📊 Support: ₹{advanced['support_level']:.2f} | Resistance: ₹{advanced['resistance_level']:.2f}")
            print(f"   🎯 Trend: {advanced['trend_direction']} | BB Pos: {advanced['bb_position']:.2f}")
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
            'bb_signal_info': bb_signal_info,
            'iii_value': float(current_iii),
            'iii_length': int(iii_length),
            'bb_upper': float(bb_upper.iloc[-1]),
            'bb_basis': float(bb_basis.iloc[-1]),
            'bb_lower': float(bb_lower.iloc[-1]),
            'bb_length': int(bb_length),
            'bb_multiplier': float(bb_multiplier),
            'bb_type': bb_type,
            'support_level': float(advanced.get('support_level', current_price)),
            'resistance_level': float(advanced.get('resistance_level', current_price)),
            'pivot_level': float(advanced.get('pivot_level', current_price)),
            'support_distance': float(advanced.get('support_distance', 0)),
            'resistance_distance': float(advanced.get('resistance_distance', 0)),
            'volatility_score': float(advanced.get('volatility_score', 0)),
            'sma_trend': float(advanced.get('sma_trend', 0)),
            'trend_direction': advanced.get('trend_direction', 'NEUTRAL'),
            'rsi': float(advanced.get('rsi', 50)),
            'srsi_k': float(advanced.get('srsi_k', 50)),
            'srsi_d': float(advanced.get('srsi_d', 50)),
            'ema_20': float(advanced.get('ema_20', current_price)),
            'ema_50': float(advanced.get('ema_50', current_price)),
            'bb_position': float(advanced.get('bb_position', 0.5)),
            'use_iii': bool(use_iii),
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

def analyze_all_stocks(bb_length=20, bb_multiplier=2.0, bb_type='SMA', bb_price='Close',
                      iii_length=21, use_iii=True, position_mode='both', volume_days=20, 
                      momentum_days=5, max_workers=3, debug=False):
    """Analyze all stocks for Bollinger Bands + III strategy"""
    
    # Get tickers from config
    tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
    
    print(f"\n📊 COMPREHENSIVE BOLLINGER BANDS + III ANALYSIS")
    print(f"📈 Analyzing {len(tickers)} stocks from config")
    print(f"📊 BB Settings: {bb_length}-period {bb_type} with {bb_multiplier}x multiplier")
    print(f"📊 III Length: {iii_length} periods {'(ENABLED)' if use_iii else '(DISABLED)'}")
    print(f"📊 Position Mode: {position_mode.upper()}")
    print(f"📊 Volume Period: {volume_days} trading days")
    print(f"🚀 Momentum Period: {momentum_days} trading days")
    print("="*60)
    
    all_signals = []
    
    # Analyze stocks
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(analyze_stock_comprehensive, ticker, bb_length, bb_multiplier, 
                          bb_type, bb_price, iii_length, use_iii, 20, position_mode,
                          volume_days, momentum_days, debug): ticker 
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
                    if result.get('bb_signal_info'):
                        bb_type_str = result['bb_signal_info']['signal_type']
                        strength = result['bb_signal_info']['signal_strength']
                        signal_info = f" - {bb_type_str} ({strength:.0f}%)"
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
    print(f"📊 Bollinger Bands Mean Reversion Strategy")
    print("="*110)
    
    # Prepare table
    table_data = []
    headers = ['Rank', 'Ticker', 'BB Signal', 'Entry', 'Target', 'Stop', 'Strength%', 
              'III', 'Volume', 'RSI', 'SRSI', 'Momentum%', 'BB Pos', 'Qty']
    
    for i, signal in enumerate(top_signals, 1):
        strength = signal['signal_strength']
        
        # BB Signal information
        bb_signal_name = 'HOLD'
        if signal.get('bb_signal_info'):
            bb_info = signal['bb_signal_info']
            if bb_info['signal_type'] == 'LONG':
                bb_signal_name = f"📈 LONG ({bb_info['bounce_strength']:.1f}%)"
            elif bb_info['signal_type'] == 'SHORT':
                bb_signal_name = f"📉 SHORT ({bb_info['bounce_strength']:.1f}%)"
        
        # III value with confirmation
        iii_value = signal.get('iii_value', 0)
        iii_display = f"{iii_value:.0f}"
        if signal.get('bb_signal_info'):
            if signal['bb_signal_info']['iii_confirmation']:
                iii_display += "✅"
            else:
                iii_display += "❌"
        
        # RSI with color coding
        rsi_value = signal.get('rsi', 50)
        rsi_display = f"{rsi_value:.0f}"
        if rsi_value > 70:
            rsi_display += "🔴"  # Overbought
        elif rsi_value < 30:
            rsi_display += "🟢"  # Oversold
        
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
        
        # BB Position
        bb_pos = signal.get('bb_position', 0.5)
        bb_pos_display = f"{bb_pos:.2f}"
        if bb_pos < 0.2:
            bb_pos_display += "🔽"  # Near lower band
        elif bb_pos > 0.8:
            bb_pos_display += "🔼"  # Near upper band
        
        table_data.append([
            i,
            signal['ticker'],
            bb_signal_name,
            f"₹{signal['entry_price']:.2f}",
            f"₹{signal['target_price']:.2f}",
            f"₹{signal['stop_loss']:.2f}",
            f"{strength:.1f}%",
            iii_display,
            volume_display,
            rsi_display,
            srsi_display,
            f"{signal['momentum']:+.1f}%",
            bb_pos_display,
            signal['position_size']
        ])
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Summary statistics
    avg_strength = sum(signal['signal_strength'] for signal in top_signals) / len(top_signals)
    avg_volume = sum(signal['volume_ratio'] for signal in top_signals) / len(top_signals)
    avg_momentum = sum(signal['momentum'] for signal in top_signals) / len(top_signals)
    avg_rsi = sum(signal.get('rsi', 50) for signal in top_signals) / len(top_signals)
    avg_iii = sum(signal.get('iii_value', 0) for signal in top_signals) / len(top_signals)
    
    # Signal breakdown
    long_count = sum(1 for s in top_signals if s.get('bb_signal_info', {}).get('signal_type') == 'LONG')
    short_count = sum(1 for s in top_signals if s.get('bb_signal_info', {}).get('signal_type') == 'SHORT')
    
    print(f"\n📊 SUMMARY:")
    print(f"   📊 {signal_title} signals: {len(signals)}")
    print(f"   📈 Average strength: {avg_strength:.1f}%")
    print(f"   📊 Average volume ratio: {avg_volume:.1f}x")
    print(f"   🚀 Average momentum: {avg_momentum:+.1f}%")
    print(f"   📊 Average RSI: {avg_rsi:.1f}")
    print(f"   📊 Average III: {avg_iii:.0f}")
    if long_count > 0:
        print(f"   📈 Long signals: {long_count}")
    if short_count > 0:
        print(f"   📉 Short signals: {short_count}")
    
    print(f"\n🏆 RANKING EXPLANATION:")
    print(f"   📊 Sorted by: STRONG signals first, then WEAK signals")
    print(f"   🎯 Strength includes: Bounce magnitude + III confirmation + Distance to target")
    print(f"   📈 LONG = Bounce off lower BB (mean reversion up)")
    print(f"   📉 SHORT = Bounce off upper BB (mean reversion down)")
    print(f"   📊 Target = BB Middle Line (Basis)")

def generate_comprehensive_html(all_signals, bb_length, bb_multiplier, bb_type, iii_length, 
                              use_iii, position_mode, volume_days, momentum_days, output_dir):
    """Generate comprehensive HTML report for BB + III strategy"""
    
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
        <title>Bollinger Bands + III Strategy Analysis - {datetime.now().strftime('%Y-%m-%d')}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
                font-size: 0.85em;
            }}
            th, td {{
                padding: 10px 6px;
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
                <h1>📊 BOLLINGER BANDS + III STRATEGY</h1>
                <p><strong>Advanced Mean Reversion Analysis</strong></p>
                <p>BB: {bb_length}-period {bb_type} ({bb_multiplier}x) | III: {iii_length} periods {'✅' if use_iii else '❌'}</p>
                <p>Mode: {position_mode.upper()} | Volume: {volume_days} days | Momentum: {momentum_days} days</p>
                <p>Generated: {timestamp}</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>{len(buy_signals)}</h3>
                    <p>📈 BUY Signals</p>
                </div>
                <div class="stat-card">
                    <h3>{len(sell_signals)}</h3>
                    <p>📉 SELL Signals</p>
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
                <h3>📊 Bollinger Bands + Intraday Intensity Index Strategy</h3>
                <div class="features-grid">
                    <div class="feature-card">
                        <h4>📈 Mean Reversion Logic</h4>
                        <p><strong>BUY:</strong> Price bounces off lower BB (prev_close < lower AND close > lower)</p>
                        <p><strong>SELL:</strong> Price bounces off upper BB (prev_close > upper AND close < upper)</p>
                        <p><strong>Target:</strong> BB Middle Line (Basis) - Mean reversion point</p>
                    </div>
                    <div class="feature-card">
                        <h4>📊 Intraday Intensity Index (III)</h4>
                        <p>Volume-weighted momentum indicator: III = [(2×Close - High - Low) × Volume] / (High - Low)</p>
                        <p><strong>Confirmation:</strong> Positive III for longs, Negative III for shorts</p>
                        <p><strong>Length:</strong> {iii_length}-period rolling sum</p>
                    </div>
                    <div class="feature-card">
                        <h4>📊 Bollinger Band Settings</h4>
                        <p><strong>Length:</strong> {bb_length} periods</p>
                        <p><strong>Type:</strong> {bb_type} (Simple or Exponential Moving Average)</p>
                        <p><strong>Multiplier:</strong> {bb_multiplier}× Standard Deviation</p>
                    </div>
                    <div class="feature-card">
                        <h4>🎯 Signal Strength Calculation</h4>
                        <p>Bounce Strength (40%) + III Confirmation (30%) + Distance to Target (30%)</p>
                        <p><strong>Volume Confirmation:</strong> Enhanced with trend analysis</p>
                        <p><strong>Risk Management:</strong> Stop slightly outside BB bands</p>
                    </div>
                </div>
            </div>
    """
    
    # Generate BUY signals table
    if buy_signals:
        html_content += f"""
            <div class="section">
                <h2>📈 TOP BOLLINGER BANDS BUY SIGNALS (MEAN REVERSION UP)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Ticker</th>
                            <th>BB Signal</th>
                            <th>Entry</th>
                            <th>Target</th>
                            <th>Stop</th>
                            <th>Strength</th>
                            <th>III</th>
                            <th>Volume</th>
                            <th>RSI</th>
                            <th>SRSI</th>
                            <th>Momentum</th>
                            <th>BB Position</th>
                            <th>Qty</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for i, signal in enumerate(buy_signals[:20], 1):  # Top 20
            strength = signal['signal_strength']
            momentum_class = 'positive' if signal['momentum'] >= 0 else 'negative'
            
            # BB Signal display
            bb_signal_display = '📈 LONG'
            if signal.get('bb_signal_info'):
                bounce_strength = signal['bb_signal_info']['bounce_strength']
                bb_signal_display = f'📈 LONG ({bounce_strength:.1f}%)'
            
            # III confirmation
            iii_value = signal.get('iii_value', 0)
            iii_display = f"{iii_value:.0f}"
            if signal.get('bb_signal_info') and signal['bb_signal_info'].get('iii_confirmation'):
                iii_display += " ✅"
            else:
                iii_display += " ❌"
            
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
                            <td>{bb_signal_display}</td>
                            <td>₹{signal['entry_price']:.2f}</td>
                            <td>₹{signal['target_price']:.2f}</td>
                            <td>₹{signal['stop_loss']:.2f}</td>
                            <td>{strength:.1f}%</td>
                            <td>{iii_display}</td>
                            <td>{volume_display}</td>
                            <td>{signal.get('rsi', 50):.0f}</td>
                            <td>{signal.get('srsi_k', 50):.0f}/{signal.get('srsi_d', 50):.0f}</td>
                            <td class="{momentum_class}">{signal['momentum']:+.1f}%</td>
                            <td>{signal.get('bb_position', 0.5):.2f}</td>
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
                <h2>📉 TOP BOLLINGER BANDS SELL SIGNALS (MEAN REVERSION DOWN)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Ticker</th>
                            <th>BB Signal</th>
                            <th>Entry</th>
                            <th>Target</th>
                            <th>Stop</th>
                            <th>Strength</th>
                            <th>III</th>
                            <th>Volume</th>
                            <th>RSI</th>
                            <th>SRSI</th>
                            <th>Momentum</th>
                            <th>BB Position</th>
                            <th>Qty</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for i, signal in enumerate(sell_signals[:20], 1):  # Top 20
            strength = signal['signal_strength']
            momentum_class = 'positive' if signal['momentum'] >= 0 else 'negative'
            
            # BB Signal display
            bb_signal_display = '📉 SHORT'
            if signal.get('bb_signal_info'):
                bounce_strength = signal['bb_signal_info']['bounce_strength']
                bb_signal_display = f'📉 SHORT ({bounce_strength:.1f}%)'
            
            # III confirmation
            iii_value = signal.get('iii_value', 0)
            iii_display = f"{iii_value:.0f}"
            if signal.get('bb_signal_info') and signal['bb_signal_info'].get('iii_confirmation'):
                iii_display += " ✅"
            else:
                iii_display += " ❌"
            
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
                            <td>{bb_signal_display}</td>
                            <td>₹{signal['entry_price']:.2f}</td>
                            <td>₹{signal['target_price']:.2f}</td>
                            <td>₹{signal['stop_loss']:.2f}</td>
                            <td>{strength:.1f}%</td>
                            <td>{iii_display}</td>
                            <td>{volume_display}</td>
                            <td>{signal.get('rsi', 50):.0f}</td>
                            <td>{signal.get('srsi_k', 50):.0f}/{signal.get('srsi_d', 50):.0f}</td>
                            <td class="{momentum_class}">{signal['momentum']:+.1f}%</td>
                            <td>{signal.get('bb_position', 0.5):.2f}</td>
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
                <p><strong>⚠️ Disclaimer:</strong> This analysis is for educational purposes only. Mean reversion strategies work best in ranging markets and can fail in strong trending conditions. Always use proper risk management.</p>
                <p><strong>📊 Strategy:</strong> Bollinger Bands mean reversion with Intraday Intensity Index volume confirmation</p>
                <p><strong>🎯 Logic:</strong> Buy bounces off lower BB, Sell bounces off upper BB, Target middle line (basis)</p>
                <p><strong>📊 III Confirmation:</strong> Positive III for longs (buying pressure), Negative III for shorts (selling pressure)</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Save HTML
    html_filename = f"bollinger_bands_iii_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    html_path = os.path.join(output_dir, html_filename)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return html_path

def save_results_json(all_signals, output_dir, bb_length, iii_length):
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
            'bb_length': int(bb_length),
            'iii_length': int(iii_length),
            'strategy': 'Bollinger Bands with Intraday Intensity Index Mean Reversion',
            'features': [
                'Bollinger Bands Mean Reversion',
                'Intraday Intensity Index Volume Confirmation', 
                'RSI and Stochastic RSI',
                'Support/Resistance Levels',
                'Momentum and Velocity Analysis',
                'Multi-confirmation Signal Strength',
                'Dynamic Entry/Exit with BB Basis Target'
            ]
        },
        'signals': json_signals
    }
    
    # Save JSON
    json_filename = f"bollinger_bands_iii_signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_path = os.path.join(output_dir, json_filename)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    return json_path

def main():
    """Main function with comprehensive BB + III analysis"""
    parser = argparse.ArgumentParser(description="Advanced Bollinger Bands + Intraday Intensity Index Strategy Analyzer")
    
    parser.add_argument('--bb-length', type=int, default=20, 
                       help='Bollinger Bands length (default: 20)')
    parser.add_argument('--bb-multiplier', type=float, default=2.0, 
                       help='BB standard deviation multiplier (default: 2.0)')
    parser.add_argument('--bb-type', type=str, default='SMA', choices=['SMA', 'EMA'],
                       help='BB moving average type (default: SMA)')
    parser.add_argument('--bb-price', type=str, default='Close', choices=['Close', 'Open', 'High', 'Low'],
                       help='BB price source (default: Close)')
    parser.add_argument('--iii-length', type=int, default=21, 
                       help='Intraday Intensity Index length (default: 21)')
    parser.add_argument('--use-iii', action='store_true', default=True,
                       help='Use III confirmation (default: True)')
    parser.add_argument('--no-iii', action='store_true',
                       help='Disable III confirmation')
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
                       help='Show only BUY signals (BB lower bounce)')
    parser.add_argument('--sell-only', action='store_true', 
                       help='Show only SELL signals (BB upper bounce)')
    
    args = parser.parse_args()
    
    # Handle III flag
    use_iii = args.use_iii and not args.no_iii
    
    # Test single ticker if requested
    if args.test_single:
        print(f"🧪 TESTING SINGLE TICKER: {args.test_single}")
        print("="*50)
        result = analyze_stock_comprehensive(
            args.test_single, 
            args.bb_length, 
            args.bb_multiplier, 
            args.bb_type,
            args.bb_price,
            args.iii_length,
            use_iii,
            20,  # time_stop
            args.position_mode,
            args.volume_days, 
            args.momentum_days, 
            debug=True
        )
        if result:
            print(f"\n✅ SUCCESS! Signal: {result['signal_type']}")
            if result.get('bb_signal_info'):
                bb_info = result['bb_signal_info']
                print(f"📊 BB Signal: {bb_info['signal_type']} - Strength: {bb_info['signal_strength']:.1f}%")
                print(f"📊 Entry: ₹{result['entry_price']:.2f} | Target: ₹{result['target_price']:.2f} | Stop: ₹{result['stop_loss']:.2f}")
                print(f"📊 III Value: {result['iii_value']:.0f} | Confirmation: {'✅' if bb_info['iii_confirmation'] else '❌'}")
                print(f"📈 RSI: {result['rsi']:.1f} | SRSI: {result['srsi_k']:.1f}/{result['srsi_d']:.1f}")
                print(f"📊 BB Bands: Upper: ₹{result['bb_upper']:.2f} | Basis: ₹{result['bb_basis']:.2f} | Lower: ₹{result['bb_lower']:.2f}")
        else:
            print(f"\n❌ No result for {args.test_single}")
        return
    
    print("📊 ADVANCED BOLLINGER BANDS + III ANALYZER")
    print("🔄 Mean Reversion Strategy with Volume Confirmation")
    print("="*60)
    print(f"📊 BB Settings: {args.bb_length}-period {args.bb_type} ({args.bb_multiplier}x)")
    print(f"📊 III Length: {args.iii_length} periods {'✅' if use_iii else '❌'}")
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
        bb_length=args.bb_length,
        bb_multiplier=args.bb_multiplier,
        bb_type=args.bb_type,
        bb_price=args.bb_price,
        iii_length=args.iii_length,
        use_iii=use_iii,
        position_mode=args.position_mode,
        volume_days=args.volume_days, 
        momentum_days=args.momentum_days,
        max_workers=args.workers,
        debug=args.debug
    )
    
    if not all_signals:
        print("\n❌ No signals generated!")
        print("💡 TROUBLESHOOTING TIPS:")
        print("   🔧 Try different BB settings: --bb-length 15 --bb-multiplier 1.5")
        print("   🔧 Disable III confirmation: --no-iii")
        print("   🔧 Change position mode: --position-mode long")
        print("   🔧 Reduce periods: --volume-days 10 --momentum-days 3")
        print("   🔧 Enable debug mode: --debug")
        print("   🔧 Test single stock: --test-single RELIANCE --debug")
        return
    
    # Display results based on arguments
    if args.buy_only:
        buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY', 'WEAK_BUY'])
        buy_signals = sort_signals_properly(buy_signals) if buy_signals else []
        display_top_signals(buy_signals, "BOLLINGER BANDS BUY", args.top)
    elif args.sell_only:
        sell_signals = filter_signals_by_type(all_signals, ['STRONG_SELL', 'WEAK_SELL'])
        sell_signals = sort_signals_properly(sell_signals) if sell_signals else []
        display_top_signals(sell_signals, "BOLLINGER BANDS SELL", args.top)
    elif args.show_all:
        # Show all types
        buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY', 'WEAK_BUY'])
        sell_signals = filter_signals_by_type(all_signals, ['STRONG_SELL', 'WEAK_SELL'])
        hold_signals = filter_signals_by_type(all_signals, ['HOLD'])
        
        if buy_signals:
            buy_signals = sort_signals_properly(buy_signals)
            display_top_signals(buy_signals, "BOLLINGER BANDS BUY", args.top)
        if sell_signals:
            sell_signals = sort_signals_properly(sell_signals)
            display_top_signals(sell_signals, "BOLLINGER BANDS SELL", args.top)
        
        print(f"\n📊 OVERALL SUMMARY:")
        print(f"   📈 BB BUY signals: {len(buy_signals)}")
        print(f"   📉 BB SELL signals: {len(sell_signals)}")
        print(f"   ⚪ HOLD signals: {len(hold_signals)}")
        print(f"   📊 Total analyzed: {len(all_signals)}")
    else:
        # Default: Show BUY signals only
        buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY', 'WEAK_BUY'])
        buy_signals = sort_signals_properly(buy_signals) if buy_signals else []
        display_top_signals(buy_signals, "BOLLINGER BANDS BUY", args.top)
    
    # Generate reports
    print(f"\n📄 Generating comprehensive reports...")
    
    # HTML Report
    html_path = generate_comprehensive_html(
        all_signals, args.bb_length, args.bb_multiplier, args.bb_type, args.iii_length,
        use_iii, args.position_mode, args.volume_days, args.momentum_days, output_dir
    )
    if html_path:
        print(f"🌐 HTML Report: {html_path}")
        print(f"🔗 Open: file://{os.path.abspath(html_path)}")
    
    # JSON Report
    json_path = save_results_json(all_signals, output_dir, args.bb_length, args.iii_length)
    if json_path:
        print(f"📊 JSON Data: {json_path}")
    
    print(f"\n✅ Analysis Complete!")
    print(f"📁 Output Directory: {os.path.abspath(output_dir)}")
    
    # Trading notes
    print(f"\n💡 BOLLINGER BANDS + III STRATEGY FEATURES:")
    print(f"   📊 MEAN REVERSION: Buy BB lower bounces, Sell BB upper bounces")
    print(f"   📊 BB SETTINGS: {args.bb_length}-period {args.bb_type} with {args.bb_multiplier}x std dev")
    print(f"   📊 III CONFIRMATION: {'✅ Volume-weighted momentum filter' if use_iii else '❌ Disabled'}")
    print(f"   🎯 TARGET: BB Middle Line (Basis) - Mean reversion point")
    print(f"   🛑 STOPS: Slightly outside BB bands for safety")
    print(f"   📊 SIGNAL STRENGTH: Bounce + III + Distance scoring")
    print(f"   📈 TECHNICAL ANALYSIS: RSI, SRSI, Support/Resistance, Volume")
    print(f"   ⚖️  POSITION SIZING: 1% risk-based position calculation")
    print(f"   📊 POSITION MODE: {args.position_mode.upper()} trades allowed")
    
    print(f"\n🧪 TROUBLESHOOTING COMMANDS:")
    print(f"   python {sys.argv[0]} --test-single RELIANCE --debug")
    print(f"   python {sys.argv[0]} --bb-length 15 --no-iii --debug --show-all")
    print(f"   python {sys.argv[0]} --position-mode long --top 20")

if __name__ == "__main__":
    main()