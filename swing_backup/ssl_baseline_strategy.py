#!/usr/bin/env python
# ssl_baseline_strategy.py - SSL Baseline Strategy (Converted from Pine Script)
# Original Pine Script by @fpemehd - Thanks to @kevinmck100 and @Mihkel00

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
from collections import defaultdict
# Optional imports - will work without these
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    print("⚠️  TA-Lib not available - using manual calculations (install with: pip install talib)")

try:
    from scipy import signal
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("⚠️  SciPy not available - some advanced features disabled (install with: pip install scipy)")

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

warnings.filterwarnings("ignore")

# Print availability status
print("📦 LIBRARY STATUS:")
print(f"   ✅ TA-Lib: {'Available' if TALIB_AVAILABLE else 'Not Available (using manual calculations)'}")
print(f"   ✅ SciPy: {'Available' if SCIPY_AVAILABLE else 'Not Available (basic functionality only)'}")
if not TALIB_AVAILABLE:
    print("   💡 Install TA-Lib for faster calculations: pip install talib")
print()

# SECTOR MAPPING FOR INDIAN STOCKS (same as your existing code)
SECTOR_MAPPING = {
    # Banking & Financial Services
    'HDFCBANK': 'Banking', 'ICICIBANK': 'Banking', 'SBIN': 'Banking', 'AXISBANK': 'Banking',
    'KOTAKBANK': 'Banking', 'INDUSINDBK': 'Banking', 'FEDERALBNK': 'Banking', 'BANDHANBNK': 'Banking',
    'PNB': 'Banking', 'BANKBARODA': 'Banking', 'CANBK': 'Banking', 'IDFCFIRSTB': 'Banking',
    
    'BAJFINANCE': 'Financial Services', 'BAJAJFINSV': 'Financial Services', 'HDFCLIFE': 'Financial Services',
    'SBILIFE': 'Financial Services', 'ICICIPRULI': 'Financial Services', 'LICI': 'Financial Services',
    'MUTHOOTFIN': 'Financial Services', 'CHOLAFIN': 'Financial Services', 'PFC': 'Financial Services',
    'RECLTD': 'Financial Services', 'SHRIRAMFIN': 'Financial Services',
    
    # Information Technology
    'TCS': 'Information Technology', 'INFY': 'Information Technology', 'WIPRO': 'Information Technology',
    'HCLTECH': 'Information Technology', 'TECHM': 'Information Technology', 'LTI': 'Information Technology',
    'LTIM': 'Information Technology', 'MPHASIS': 'Information Technology', 'MINDTREE': 'Information Technology',
    'COFORGE': 'Information Technology', 'PERSISTENT': 'Information Technology', 'LTTS': 'Information Technology',
    
    # Oil & Gas
    'RELIANCE': 'Oil & Gas', 'ONGC': 'Oil & Gas', 'IOC': 'Oil & Gas', 'BPCL': 'Oil & Gas',
    'HPCL': 'Oil & Gas', 'GAIL': 'Oil & Gas', 'OIL': 'Oil & Gas', 'MGL': 'Oil & Gas',
    'IGL': 'Oil & Gas', 'PETRONET': 'Oil & Gas',
    
    # FMCG
    'HINDUNILVR': 'FMCG', 'ITC': 'FMCG', 'NESTLEIND': 'FMCG', 'BRITANNIA': 'FMCG',
    'DABUR': 'FMCG', 'MARICO': 'FMCG', 'GODREJCP': 'FMCG', 'COLPAL': 'FMCG',
    
    # Pharmaceuticals
    'SUNPHARMA': 'Pharmaceuticals', 'DRREDDY': 'Pharmaceuticals', 'CIPLA': 'Pharmaceuticals',
    'DIVISLAB': 'Pharmaceuticals', 'LUPIN': 'Pharmaceuticals', 'BIOCON': 'Pharmaceuticals',
    
    # Automotive
    'MARUTI': 'Automotive', 'M&M': 'Automotive', 'TATAMOTORS': 'Automotive', 'BAJAJ-AUTO': 'Automotive',
    'HEROMOTOCO': 'Automotive', 'EICHERMOT': 'Automotive', 'APOLLOTYRE': 'Automotive',
    
    # Metals & Mining
    'TATASTEEL': 'Metals & Mining', 'JSWSTEEL': 'Metals & Mining', 'HINDALCO': 'Metals & Mining',
    'VEDL': 'Metals & Mining', 'COALINDIA': 'Metals & Mining', 'SAIL': 'Metals & Mining',
    
    # Cement
    'ULTRACEMCO': 'Cement', 'GRASIM': 'Cement', 'SHREECEM': 'Cement', 'ACC': 'Cement',
    'AMBUJACEML': 'Cement', 'JKCEMENT': 'Cement',
    
    # Paints & Chemicals
    'ASIANPAINT': 'Paints & Chemicals', 'BERGER': 'Paints & Chemicals', 'UPL': 'Chemicals',
    
    # Capital Goods & Engineering
    'LT': 'Capital Goods', 'ABB': 'Capital Goods', 'SIEMENS': 'Capital Goods',
    
    # Power & Utilities
    'POWERGRID': 'Power', 'NTPC': 'Power', 'ADANIPOWER': 'Power', 'TATAPOWER': 'Power',
    
    # Telecommunications
    'BHARTIARTL': 'Telecom', 'IDEA': 'Telecom',
    
    # Consumer Durables
    'TITAN': 'Consumer Durables', 'BAJAJELEEC': 'Consumer Durables', 'WHIRLPOOL': 'Consumer Durables',
}

def get_sector(ticker):
    """Get sector for a ticker"""
    return SECTOR_MAPPING.get(ticker, 'Others')

def get_stock_data(ticker, lookback_days=200):
    """Get stock data for analysis"""
    try:
        symbol = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
        days_needed = lookback_days + 100
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_needed)
        
        stock = yf.Ticker(symbol)
        data = stock.history(start=start_date, end=end_date)
        
        if data.empty or len(data) < 100:
            print(f"   ⚠️  {ticker}: Insufficient data ({len(data)} days)")
            return None
        
        return data.dropna()
        
    except Exception as e:
        print(f"   ❌ {ticker}: Data fetch error - {str(e)}")
        return None

def calculate_rsi(prices, period=14):
    """Calculate RSI using talib if available, else manual calculation"""
    try:
        if len(prices) < period + 1:
            return 50
        
        # Try using talib first if available
        if TALIB_AVAILABLE:
            try:
                rsi_values = talib.RSI(prices.values, timeperiod=period)
                return rsi_values[-1] if not np.isnan(rsi_values[-1]) else 50
            except:
                pass  # Fall through to manual calculation
        
        # Manual calculation (always works)
        delta = prices.diff().dropna()
        if len(delta) < period:
            return 50
        
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        # Avoid division by zero
        rs = gain / loss.replace(0, 0.001)
        rsi = 100 - (100 / (1 + rs))
        
        final_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
        return max(0, min(100, final_rsi))
    except Exception as e:
        return 50

def calculate_atr(data, period=14):
    """Calculate Average True Range"""
    try:
        high = data['High'].values
        low = data['Low'].values
        close = data['Close'].values
        
        # Try using talib first if available
        if TALIB_AVAILABLE:
            try:
                atr_values = talib.ATR(high, low, close, timeperiod=period)
                return atr_values[-1] if not np.isnan(atr_values[-1]) else 0
            except:
                pass  # Fall through to manual calculation
        
        # Manual ATR calculation (always works)
        tr_list = []
        for i in range(1, len(data)):
            hl = high[i] - low[i]
            hc = abs(high[i] - close[i-1])
            lc = abs(low[i] - close[i-1])
            tr = max(hl, hc, lc)
            tr_list.append(tr)
        
        if len(tr_list) >= period:
            return sum(tr_list[-period:]) / period
        else:
            return sum(tr_list) / len(tr_list) if tr_list else 0
    except:
        return 0

# ============= MOVING AVERAGE FUNCTIONS (From Pine Script) =============

def sma(data, length):
    """Simple Moving Average"""
    return data.rolling(window=length).mean()

def ema(data, length):
    """Exponential Moving Average"""
    return data.ewm(span=length).mean()

def dema(data, length):
    """Double Exponential Moving Average"""
    e1 = ema(data, length)
    e2 = ema(e1, length)
    return 2 * e1 - e2

def tema(data, length):
    """Triple Exponential Moving Average"""
    e1 = ema(data, length)
    e2 = ema(e1, length)
    e3 = ema(e2, length)
    return 3 * e1 - 3 * e2 + e3

def lsma(data, length):
    """Linear Regression Moving Average"""
    try:
        result = []
        for i in range(len(data)):
            if i < length - 1:
                result.append(np.nan)
            else:
                y = data.iloc[i-length+1:i+1].values
                x = np.arange(length)
                slope, intercept = np.polyfit(x, y, 1)
                result.append(slope * (length - 1) + intercept)
        return pd.Series(result, index=data.index)
    except:
        return sma(data, length)

def wma(data, length):
    """Weighted Moving Average"""
    try:
        weights = np.arange(1, length + 1)
        result = []
        for i in range(len(data)):
            if i < length - 1:
                result.append(np.nan)
            else:
                values = data.iloc[i-length+1:i+1].values
                result.append(np.dot(values, weights) / weights.sum())
        return pd.Series(result, index=data.index)
    except:
        return sma(data, length)

def hma(data, length):
    """Hull Moving Average"""
    try:
        half_length = int(length / 2)
        sqrt_length = int(np.sqrt(length))
        
        wma1 = wma(data, half_length)
        wma2 = wma(data, length)
        diff = 2 * wma1 - wma2
        
        return wma(diff, sqrt_length)
    except:
        return sma(data, length)

def vama(data, length, volatility_lookback=10):
    """Volatility Adjusted Moving Average"""
    try:
        mid = ema(data, length)
        dev = data - mid
        vol_up = dev.rolling(volatility_lookback).max()
        vol_down = dev.rolling(volatility_lookback).min()
        return mid + (vol_up + vol_down) / 2
    except:
        return ema(data, length)

def tma(data, length):
    """Triangular Moving Average"""
    try:
        first_smooth = sma(data, int(np.ceil(length / 2)))
        return sma(first_smooth, int(np.floor(length / 2)) + 1)
    except:
        return sma(data, length)

def mcginley(data, length):
    """McGinley Dynamic"""
    try:
        mg = pd.Series(index=data.index, dtype=float)
        mg.iloc[0] = data.iloc[0]
        
        for i in range(1, len(data)):
            if pd.isna(mg.iloc[i-1]):
                mg.iloc[i] = data.iloc[i]
            else:
                mg.iloc[i] = mg.iloc[i-1] + (data.iloc[i] - mg.iloc[i-1]) / (length * (data.iloc[i] / mg.iloc[i-1]) ** 4)
        
        return mg
    except:
        return ema(data, length)

def kijun_v2(data, length, kidiv=1):
    """Kijun v2 (Ichimoku-based)"""
    try:
        # Use high and low for traditional Kijun calculation
        if hasattr(data, 'index'):  # If it's a series, we need high/low from parent
            kijun = (data.rolling(length).max() + data.rolling(length).min()) / 2
            conversion_length = max(1, int(length / kidiv))
            conversion = (data.rolling(conversion_length).max() + data.rolling(conversion_length).min()) / 2
            return (kijun + conversion) / 2
        else:
            return sma(data, length)
    except:
        return sma(data, length)

def jma(data, length, phase=3, power=1):
    """Jurik Moving Average (simplified)"""
    try:
        phase_ratio = phase / 100 + 1.5 if phase >= -100 and phase <= 100 else 1.5
        beta = 0.45 * (length - 1) / (0.45 * (length - 1) + 2)
        alpha = beta ** power
        
        jma_values = pd.Series(index=data.index, dtype=float)
        e0 = pd.Series(index=data.index, dtype=float)
        e1 = pd.Series(index=data.index, dtype=float)
        e2 = pd.Series(index=data.index, dtype=float)
        
        # Initialize
        e0.iloc[0] = data.iloc[0]
        e1.iloc[0] = 0
        e2.iloc[0] = 0
        jma_values.iloc[0] = data.iloc[0]
        
        for i in range(1, len(data)):
            e0.iloc[i] = (1 - alpha) * data.iloc[i] + alpha * e0.iloc[i-1]
            e1.iloc[i] = (data.iloc[i] - e0.iloc[i]) * (1 - beta) + beta * e1.iloc[i-1]
            e2.iloc[i] = (e0.iloc[i] + phase_ratio * e1.iloc[i] - jma_values.iloc[i-1]) * (1 - alpha)**2 + alpha**2 * e2.iloc[i-1]
            jma_values.iloc[i] = e2.iloc[i] + jma_values.iloc[i-1]
        
        return jma_values
    except:
        return ema(data, length)

def modular_filter(data, length, beta=0.8, feedback=False, z=0.5):
    """Modular Filter"""
    try:
        alpha = 2 / (length + 1)
        ts = pd.Series(index=data.index, dtype=float)
        b = pd.Series(index=data.index, dtype=float)
        c = pd.Series(index=data.index, dtype=float)
        os = pd.Series(index=data.index, dtype=float)
        
        # Initialize
        ts.iloc[0] = data.iloc[0]
        b.iloc[0] = data.iloc[0]
        c.iloc[0] = data.iloc[0]
        os.iloc[0] = 1
        
        for i in range(1, len(data)):
            if feedback:
                a = z * data.iloc[i] + (1 - z) * ts.iloc[i-1]
            else:
                a = data.iloc[i]
            
            b.iloc[i] = a if a > alpha * a + (1 - alpha) * b.iloc[i-1] else alpha * a + (1 - alpha) * b.iloc[i-1]
            c.iloc[i] = a if a < alpha * a + (1 - alpha) * c.iloc[i-1] else alpha * a + (1 - alpha) * c.iloc[i-1]
            os.iloc[i] = 1 if a == b.iloc[i] else (0 if a == c.iloc[i] else os.iloc[i-1])
            
            upper = beta * b.iloc[i] + (1 - beta) * c.iloc[i]
            lower = beta * c.iloc[i] + (1 - beta) * b.iloc[i]
            ts.iloc[i] = os.iloc[i] * upper + (1 - os.iloc[i]) * lower
        
        return ts
    except:
        return ema(data, length)

def edsma(data, length, ssf_length=20, ssf_poles=2):
    """EDSMA (Ehlers Dynamic Smoothed Moving Average)"""
    try:
        # Simplified version of EDSMA
        zeros = data.diff(2).fillna(0)
        avg_zeros = (zeros + zeros.shift(1)).fillna(0) / 2
        
        # Simple smoothing instead of complex SSF
        smoothed = avg_zeros.rolling(window=ssf_length).mean()
        stdev = smoothed.rolling(window=length).std()
        
        scaled_filter = smoothed / stdev.replace(0, 1)
        alpha = 5 * abs(scaled_filter) / length
        alpha = alpha.clip(0, 1)  # Ensure alpha is between 0 and 1
        
        edsma_values = pd.Series(index=data.index, dtype=float)
        edsma_values.iloc[0] = data.iloc[0]
        
        for i in range(1, len(data)):
            if pd.isna(alpha.iloc[i]):
                alpha_val = 0.1
            else:
                alpha_val = alpha.iloc[i]
            edsma_values.iloc[i] = alpha_val * data.iloc[i] + (1 - alpha_val) * edsma_values.iloc[i-1]
        
        return edsma_values
    except:
        return ema(data, length)

def calculate_moving_average(data, ma_type, length, **kwargs):
    """Calculate moving average based on type"""
    ma_type = ma_type.upper()
    
    if ma_type == 'SMA':
        return sma(data, length)
    elif ma_type == 'EMA':
        return ema(data, length)
    elif ma_type == 'DEMA':
        return dema(data, length)
    elif ma_type == 'TEMA':
        return tema(data, length)
    elif ma_type == 'LSMA':
        return lsma(data, length)
    elif ma_type == 'WMA':
        return wma(data, length)
    elif ma_type == 'HMA':
        return hma(data, length)
    elif ma_type == 'VAMA':
        return vama(data, length, kwargs.get('volatility_lookback', 10))
    elif ma_type == 'TMA':
        return tma(data, length)
    elif ma_type == 'JMA':
        return jma(data, length, kwargs.get('jurik_phase', 3), kwargs.get('jurik_power', 1))
    elif ma_type == 'KIJUN V2':
        return kijun_v2(data, length, kwargs.get('kidiv', 1))
    elif ma_type == 'MCGINLEY':
        return mcginley(data, length)
    elif ma_type == 'MF':
        return modular_filter(data, length, kwargs.get('beta', 0.8), kwargs.get('feedback', False), kwargs.get('z', 0.5))
    elif ma_type == 'EDSMA':
        return edsma(data, length, kwargs.get('ssfLength', 20), kwargs.get('ssfPoles', 2))
    else:
        return ema(data, length)  # Default to EMA

def calculate_ssl_baseline(data, ma_type='EMA', length=30, multiplier=0.2, use_true_range=True, **ma_kwargs):
    """Calculate SSL Baseline (Keltner Channel based)"""
    try:
        close = data['Close']
        high = data['High']
        low = data['Low']
        volume = data['Volume']
        
        # Calculate baseline moving average
        baseline = calculate_moving_average(close, ma_type, length, **ma_kwargs)
        
        # Calculate range for Keltner Channel
        if use_true_range:
            # True Range calculation
            tr_list = []
            for i in range(1, len(data)):
                hl = high.iloc[i] - low.iloc[i]
                hc = abs(high.iloc[i] - close.iloc[i-1])
                lc = abs(low.iloc[i] - close.iloc[i-1])
                tr = max(hl, hc, lc)
                tr_list.append(tr)
            
            # Pad the first value
            tr_series = pd.Series([tr_list[0]] + tr_list, index=data.index)
            range_ma = ema(tr_series, length)
        else:
            # Simple high-low range
            range_series = high - low
            range_ma = ema(range_series, length)
        
        # Calculate Keltner Channel
        upper_channel = baseline + range_ma * multiplier
        lower_channel = baseline - range_ma * multiplier
        
        # SSL conditions
        bull_ssl = close > upper_channel
        bear_ssl = close < lower_channel
        
        return {
            'baseline': baseline,
            'upper_channel': upper_channel,
            'lower_channel': lower_channel,
            'range_ma': range_ma,
            'bull_ssl': bull_ssl,
            'bear_ssl': bear_ssl,
            'current_baseline': baseline.iloc[-1],
            'current_upper': upper_channel.iloc[-1],
            'current_lower': lower_channel.iloc[-1],
            'current_bull': bull_ssl.iloc[-1],
            'current_bear': bear_ssl.iloc[-1]
        }
    except Exception as e:
        print(f"Error calculating SSL baseline: {e}")
        return None

def calculate_ssl_signals(data, ssl_data, sl_type='ATR', sl_percent=3.0, sl_atr_length=14, 
                         sl_atr_multiplier=4.0, sl_lookback=30, risk_reward=2.0, 
                         account_risk_percent=1.0, capital=100000):
    """Calculate SSL entry/exit signals with risk management"""
    try:
        close = data['Close']
        high = data['High']
        low = data['Low']
        volume = data['Volume']
        
        current_price = close.iloc[-1]
        current_volume = volume.iloc[-1]
        
        # Entry conditions
        bull_entry = ssl_data['current_bull'] and not ssl_data['bull_ssl'].iloc[-2] if len(ssl_data['bull_ssl']) > 1 else False
        bear_entry = ssl_data['current_bear'] and not ssl_data['bear_ssl'].iloc[-2] if len(ssl_data['bear_ssl']) > 1 else False
        
        signal_type = 'HOLD'
        entry_price = current_price
        stop_loss = current_price
        take_profit = current_price
        
        if bull_entry:
            signal_type = 'BUY'
            entry_price = current_price
            
            # Calculate stop loss
            if sl_type == 'ATR':
                atr = calculate_atr(data, sl_atr_length)
                stop_loss = current_price - (atr * sl_atr_multiplier)
            elif sl_type == 'Percent':
                stop_loss = current_price * (1 - sl_percent / 100)
            elif sl_type == 'Previous LL / HH':
                if len(data) >= sl_lookback:
                    lowest_low = low.iloc[-sl_lookback:].min()
                    stop_loss = lowest_low * 0.98  # Small buffer below lowest low
                else:
                    stop_loss = current_price * 0.97
            
            # Calculate take profit
            risk_distance = entry_price - stop_loss
            take_profit = entry_price + (risk_distance * risk_reward)
            
        elif bear_entry:
            signal_type = 'SELL'
            entry_price = current_price
            
            # Calculate stop loss
            if sl_type == 'ATR':
                atr = calculate_atr(data, sl_atr_length)
                stop_loss = current_price + (atr * sl_atr_multiplier)
            elif sl_type == 'Percent':
                stop_loss = current_price * (1 + sl_percent / 100)
            elif sl_type == 'Previous LL / HH':
                if len(data) >= sl_lookback:
                    highest_high = high.iloc[-sl_lookback:].max()
                    stop_loss = highest_high * 1.02  # Small buffer above highest high
                else:
                    stop_loss = current_price * 1.03
            
            # Calculate take profit
            risk_distance = stop_loss - entry_price
            take_profit = entry_price - (risk_distance * risk_reward)
        
        # Position sizing
        risk_per_share = abs(entry_price - stop_loss)
        risk_amount = capital * (account_risk_percent / 100)
        position_size = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
        
        # Risk-reward ratio
        risk_distance = abs(entry_price - stop_loss)
        reward_distance = abs(take_profit - entry_price)
        rr_ratio = reward_distance / risk_distance if risk_distance > 0 else 0
        
        return {
            'signal_type': signal_type,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'position_size': position_size,
            'risk_reward_ratio': rr_ratio,
            'risk_per_share': risk_per_share,
            'bull_entry': bull_entry,
            'bear_entry': bear_entry,
            'ssl_baseline': ssl_data['current_baseline'],
            'ssl_upper': ssl_data['current_upper'],
            'ssl_lower': ssl_data['current_lower']
        }
    except Exception as e:
        print(f"Error calculating SSL signals: {e}")
        return None

def enhanced_volume_confirmation(data, current_volume, lookback_days):
    """Enhanced volume analysis"""
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
    except:
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

def analyze_ssl_baseline_strategy(ticker, ma_type='EMA', length=30, multiplier=0.2, 
                                 sl_type='ATR', sl_percent=3.0, sl_atr_length=14,
                                 sl_atr_multiplier=4.0, risk_reward=2.0, 
                                 volume_days=20, momentum_days=5, debug=False, **ma_kwargs):
    """Main SSL Baseline Strategy Analysis"""
    try:
        if debug:
            print(f"📊 Analyzing {ticker} with SSL Baseline Strategy...")
        
        data = get_stock_data(ticker, 200)
        if data is None:
            return None
        
        # Calculate SSL Baseline
        ssl_data = calculate_ssl_baseline(data, ma_type, length, multiplier, True, **ma_kwargs)
        if ssl_data is None:
            return None
        
        # Calculate signals
        signals = calculate_ssl_signals(data, ssl_data, sl_type, sl_percent, sl_atr_length,
                                       sl_atr_multiplier, 30, risk_reward, 1.0, 100000)
        if signals is None:
            return None
        
        # Get current data
        close = data['Close']
        volume = data['Volume']
        current_price = close.iloc[-1]
        current_volume = volume.iloc[-1]
        
        print(f"   📅 Data: {len(data)} trading days available")
        
        # Calculate metrics
        volume_ratio, momentum, trading_days_used = calculate_proper_metrics(data, volume_days, momentum_days)
        volume_analysis = enhanced_volume_confirmation(data, current_volume, volume_days)
        rsi = calculate_rsi(data['Close'])
        
        print(f"   📊 Volume: Current {current_volume:,.0f} vs {volume_days}-day avg = {volume_ratio:.1f}x ({volume_analysis['volume_strength']})")
        print(f"   🚀 Momentum: {momentum:+.1f}% ({momentum_days} trading days)")
        print(f"   📈 RSI: {rsi:.1f}")
        
        # Determine signal strength
        signal_strength = 5.0  # Base strength
        entry_reason = f"SSL {signals['signal_type']}: Price {'above upper channel' if signals['signal_type'] == 'BUY' else 'below lower channel' if signals['signal_type'] == 'SELL' else 'in middle zone'}"
        
        # Enhance signal with confirmations
        if signals['signal_type'] == 'BUY':
            if volume_ratio > 1.5:
                signal_strength += 2.0
                entry_reason += f" + High Volume ({volume_ratio:.1f}x)"
            if rsi < 40:
                signal_strength += 1.5
                entry_reason += f" + RSI Oversold ({rsi:.1f})"
            if momentum > 2:
                signal_strength += 1.0
                entry_reason += f" + Positive Momentum ({momentum:+.1f}%)"
        elif signals['signal_type'] == 'SELL':
            if volume_ratio > 1.5:
                signal_strength += 2.0
                entry_reason += f" + High Volume ({volume_ratio:.1f}x)"
            if rsi > 60:
                signal_strength += 1.5
                entry_reason += f" + RSI Overbought ({rsi:.1f})"
            if momentum < -2:
                signal_strength += 1.0
                entry_reason += f" + Negative Momentum ({momentum:+.1f}%)"
        
        signal_strength = min(signal_strength, 10.0)  # Cap at 10
        
        # Filter poor R:R trades
        if signals['risk_reward_ratio'] < 0.8 and signals['signal_type'] in ['BUY', 'SELL']:
            signals['signal_type'] = 'HOLD'
            signal_strength = 0
            entry_reason = f"Poor R:R {signals['risk_reward_ratio']:.1f} - Filtered"
        
        # Get sector
        sector = get_sector(ticker)
        
        print(f"   🎯 Signal: {signals['signal_type']}")
        print(f"   💰 Entry: ₹{signals['entry_price']:.2f}")
        print(f"   🏢 Sector: {sector}")
        
        result = {
            'ticker': ticker,
            'sector': sector,
            'signal_type': signals['signal_type'],
            'signal_strength': float(signal_strength),
            'current_price': float(current_price),
            'entry_price': float(signals['entry_price']),
            'entry_reason': entry_reason,
            'strategy': f'SSL Baseline ({ma_type})',
            
            # SSL Specific data
            'ssl_baseline': float(signals['ssl_baseline']),
            'ssl_upper_channel': float(signals['ssl_upper']),
            'ssl_lower_channel': float(signals['ssl_lower']),
            'ma_type': ma_type,
            'ma_length': length,
            'channel_multiplier': multiplier,
            
            # Technical indicators
            'rsi': float(rsi),
            'volume_ratio': float(volume_ratio),
            'volume_analysis': volume_analysis,
            'momentum': float(momentum),
            'trading_days_used': int(trading_days_used),
            
            # Risk management
            'stop_loss': float(signals['stop_loss']),
            'take_profit': float(signals['take_profit']),
            'risk_reward_ratio': float(signals['risk_reward_ratio']),
            'position_size': int(signals['position_size']),
            'risk_per_share': float(signals['risk_per_share']),
            'sl_type': sl_type,
            
            # SSL conditions
            'bull_entry': signals['bull_entry'],
            'bear_entry': signals['bear_entry']
        }
        
        return result
        
    except Exception as e:
        if debug:
            print(f"Error analyzing {ticker}: {e}")
        return None

def analyze_all_stocks_ssl(ma_type='EMA', length=30, multiplier=0.2, volume_days=20, 
                          momentum_days=5, max_workers=3, debug=False, **ma_kwargs):
    """Analyze all stocks with SSL Baseline strategy"""
    
    tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
    
    print(f"\n🚀 SSL BASELINE STRATEGY ANALYSIS")
    print(f"📊 MA Type: {ma_type} | Length: {length} | Multiplier: {multiplier}")
    print(f"⚡ Analyzing {len(tickers)} stocks")
    print(f"📊 Volume Period: {volume_days} trading days")
    print(f"🚀 Momentum Period: {momentum_days} trading days")
    print("="*80)
    
    all_signals = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(analyze_ssl_baseline_strategy, ticker, ma_type, length, 
                          multiplier, 'ATR', 3.0, 14, 4.0, 2.0, volume_days, 
                          momentum_days, debug, **ma_kwargs): ticker 
            for ticker in tickers
        }
        
        completed = 0
        successful = 0
        failed = 0
        buy_signals = 0
        sell_signals = 0
        
        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            completed += 1
            
            try:
                result = future.result(timeout=30)
                if result:
                    all_signals.append(result)
                    successful += 1
                    
                    if result['signal_type'] == 'BUY':
                        buy_signals += 1
                    elif result['signal_type'] == 'SELL':
                        sell_signals += 1
                    
                    print(f"✅ {ticker} ({completed}/{len(tickers)}) - {result['signal_type']} | {result['sector']}")
                else:
                    failed += 1
                    print(f"⚪ {ticker} ({completed}/{len(tickers)}) - No data")
            except concurrent.futures.TimeoutError:
                failed += 1
                print(f"⏰ {ticker} ({completed}/{len(tickers)}) - Timeout")
            except Exception as e:
                failed += 1
                print(f"❌ {ticker} ({completed}/{len(tickers)}) - Error: {str(e)[:50]}")
        
        print(f"\n📊 SSL BASELINE ANALYSIS SUMMARY:")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📈 BUY signals: {buy_signals}")
        print(f"   📉 SELL signals: {sell_signals}")
        print(f"   🔥 Total signals: {len(all_signals)}")
        print(f"   🎯 Strategy: SSL Baseline ({ma_type})")
    
    return all_signals

def sort_signals_by_strength(signals):
    """Sort signals by signal strength and confirmations"""
    if not signals:
        return signals
    
    for signal in signals:
        # Calculate combined score
        strength_score = signal.get('signal_strength', 0)
        volume_score = min(signal.get('volume_ratio', 1.0) * 2, 10)  # Volume boost
        
        rsi = signal.get('rsi', 50)
        if signal['signal_type'] == 'BUY':
            rsi_score = max(0, (50 - rsi) / 5)  # Better score for lower RSI
        elif signal['signal_type'] == 'SELL':
            rsi_score = max(0, (rsi - 50) / 5)  # Better score for higher RSI
        else:
            rsi_score = 0
        
        momentum = signal.get('momentum', 0)
        if signal['signal_type'] == 'BUY':
            momentum_score = max(0, momentum / 2)  # Positive momentum for buy
        elif signal['signal_type'] == 'SELL':
            momentum_score = max(0, -momentum / 2)  # Negative momentum for sell
        else:
            momentum_score = 0
        
        signal['combined_score'] = (
            strength_score * 0.4 +      # 40% weight on signal strength
            volume_score * 0.3 +        # 30% weight on volume
            rsi_score * 0.15 +          # 15% weight on RSI
            momentum_score * 0.15       # 15% weight on momentum
        )
    
    return sorted(signals, key=lambda x: x['combined_score'], reverse=True)

def group_signals_by_sector(signals):
    """Group signals by sector"""
    sector_groups = defaultdict(list)
    
    for signal in signals:
        sector = signal.get('sector', 'Others')
        sector_groups[sector].append(signal)
    
    # Sort each sector's signals
    for sector in sector_groups:
        sector_groups[sector] = sort_signals_by_strength(sector_groups[sector])
    
    return dict(sector_groups)

def display_ssl_signals(all_signals, signal_types, title):
    """Display SSL Baseline signals by sector"""
    
    filtered_signals = [s for s in all_signals if s['signal_type'] in signal_types]
    
    if not filtered_signals:
        print(f"\n❌ No {title} signals found!")
        return
    
    filtered_signals = sort_signals_by_strength(filtered_signals)
    sector_groups = group_signals_by_sector(filtered_signals)
    
    print(f"\n🏆 SECTOR-WISE {title} SIGNALS (SSL BASELINE)")
    print(f"📊 Strategy: SSL Baseline with Keltner Channels")
    print("="*140)
    
    total_signals = 0
    
    for sector, signals in sector_groups.items():
        if not signals:
            continue
            
        total_signals += len(signals)
        
        print(f"\n🏢 {sector.upper()} SECTOR - {title} SIGNALS")
        print("-" * 140)
        
        for i, signal in enumerate(signals, 1):
            print(f"{i}. {signal['ticker']:10} | {signal['signal_type']:5} | "
                  f"Current: ₹{signal['current_price']:7.1f} | "
                  f"Entry: ₹{signal['entry_price']:7.1f} | "
                  f"Score: {signal.get('combined_score', 0):4.1f}/10")
            
            # Technical indicators
            rsi_icon = "🔴" if signal['rsi'] > 70 else "🟢" if signal['rsi'] < 30 else ""
            volume_icon = "🟢" if signal['volume_analysis']['volume_strength'] in ['HIGH', 'VERY_HIGH'] else "🟡" if signal['volume_analysis']['volume_strength'] == 'NORMAL' else "🔴"
            momentum_icon = "🟢" if (signal['signal_type'] == 'BUY' and signal['momentum'] > 0) or (signal['signal_type'] == 'SELL' and signal['momentum'] < 0) else "🔴"
            
            print(f"   📊 RSI: {signal['rsi']:4.1f}{rsi_icon} | "
                  f"Volume: {signal['volume_ratio']:4.1f}x{volume_icon} | "
                  f"Momentum: {signal['momentum']:+5.1f}%{momentum_icon} | "
                  f"R:R: 1:{signal['risk_reward_ratio']:.1f}")
            
            # SSL specific info
            print(f"   🎯 SSL LOGIC: {signal['entry_reason']}")
            print(f"   📊 SSL Baseline: ₹{signal['ssl_baseline']:6.1f} | "
                  f"Upper: ₹{signal['ssl_upper_channel']:6.1f} | "
                  f"Lower: ₹{signal['ssl_lower_channel']:6.1f}")
            print(f"   ⚙️  MA: {signal['ma_type']}({signal['ma_length']}) | "
                  f"Multiplier: {signal['channel_multiplier']} | "
                  f"SL Type: {signal['sl_type']}")
            
            # Risk management
            print(f"   🛑 Stop: ₹{signal['stop_loss']:6.1f} | "
                  f"Target: ₹{signal['take_profit']:6.1f} | "
                  f"Position: {signal['position_size']} shares | "
                  f"Risk: ₹{signal['risk_per_share']:5.1f}/share")
            
            print()
    
    print(f"\n📊 SSL BASELINE SECTOR SUMMARY:")
    sector_stats = []
    for sector, signals in sector_groups.items():
        avg_score = sum(s.get('combined_score', 0) for s in signals) / len(signals) if signals else 0
        avg_rsi = sum(s['rsi'] for s in signals) / len(signals) if signals else 50
        avg_volume = sum(s['volume_ratio'] for s in signals) / len(signals) if signals else 1
        
        sector_stats.append({
            'sector': sector,
            'total': len(signals),
            'avg_score': avg_score,
            'avg_rsi': avg_rsi,
            'avg_volume': avg_volume
        })
    
    sector_stats.sort(key=lambda x: x['total'], reverse=True)
    
    for stat in sector_stats:
        print(f"   🏢 {stat['sector']:20} | "
              f"Signals: {stat['total']:2d} | "
              f"Avg Score: {stat['avg_score']:4.1f} | "
              f"Avg RSI: {stat['avg_rsi']:4.1f} | "
              f"Avg Vol: {stat['avg_volume']:4.1f}x")

def generate_ssl_html_report(all_signals, ma_type, length, multiplier, volume_days, momentum_days, output_dir):
    """Generate SSL Baseline HTML report"""
    
    if not all_signals:
        print("❌ No signals to generate report")
        return None
    
    buy_signals = [s for s in all_signals if s['signal_type'] == 'BUY']
    sell_signals = [s for s in all_signals if s['signal_type'] == 'SELL']
    
    buy_signals = sort_signals_by_strength(buy_signals) if buy_signals else []
    sell_signals = sort_signals_by_strength(sell_signals) if sell_signals else []
    
    buy_sectors = group_signals_by_sector(buy_signals)
    sell_sectors = group_signals_by_sector(sell_signals)
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SSL Baseline Strategy Analysis - {datetime.now().strftime('%Y-%m-%d')}</title>
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
                font-size: 1.8em;
            }}
            .sector-header {{
                background: linear-gradient(135deg, #36d1dc 0%, #5b86e5 100%);
                color: white;
                padding: 15px 25px;
                border-radius: 8px;
                margin: 25px 0 15px 0;
                font-size: 1.3em;
                font-weight: bold;
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
                font-size: 0.9em;
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
            .buy {{
                background: linear-gradient(90deg, #28a745, #20c997);
                color: white;
                padding: 5px 10px;
                border-radius: 15px;
                font-weight: bold;
                text-align: center;
            }}
            .sell {{
                background: linear-gradient(90deg, #dc3545, #e74c3c);
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
                <h1>⚡ SSL BASELINE STRATEGY ANALYSIS</h1>
                <p><strong>Keltner Channel Based SSL with Multiple Moving Averages</strong></p>
                <p>MA: {ma_type}({length}) | Multiplier: {multiplier} | Volume: {volume_days} days | Momentum: {momentum_days} days</p>
                <p>Generated: {timestamp}</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>{len(buy_signals)}</h3>
                    <p>BUY Signals</p>
                </div>
                <div class="stat-card">
                    <h3>{len(sell_signals)}</h3>
                    <p>SELL Signals</p>
                </div>
                <div class="stat-card">
                    <h3>{len(all_signals)}</h3>
                    <p>Total Analyzed</p>
                </div>
                <div class="stat-card">
                    <h3>{ma_type}</h3>
                    <p>Moving Average</p>
                </div>
            </div>
    """
    
    # Generate BUY signals by sector
    if buy_sectors:
        html_content += f"""
            <div class="section">
                <h2>🟢 BUY SIGNALS BY SECTOR</h2>
        """
        
        sorted_buy_sectors = sorted(buy_sectors.items(), key=lambda x: len(x[1]), reverse=True)
        
        for sector, signals in sorted_buy_sectors:
            if not signals:
                continue
                
            html_content += f'<div class="sector-header">🏢 {sector.upper()} SECTOR ({len(signals)} Signals)</div>'
            html_content += '''
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Ticker</th>
                            <th>Signal</th>
                            <th>Current</th>
                            <th>Entry</th>
                            <th>SSL Baseline</th>
                            <th>Upper Channel</th>
                            <th>Lower Channel</th>
                            <th>RSI</th>
                            <th>Volume</th>
                            <th>Momentum</th>
                            <th>Score</th>
                            <th>Stop Loss</th>
                            <th>Target</th>
                            <th>R:R</th>
                        </tr>
                    </thead>
                    <tbody>
            '''
            
            for i, signal in enumerate(signals, 1):
                signal_class = signal['signal_type'].lower()
                momentum_class = 'positive' if signal['momentum'] >= 0 else 'negative'
                
                rsi_value = signal.get('rsi', 50)
                rsi_display = f"{rsi_value:.0f}"
                if rsi_value > 70:
                    rsi_display += "🔴"
                elif rsi_value < 30:
                    rsi_display += "🟢"
                
                volume_strength = signal['volume_analysis']['volume_strength']
                volume_display = f"{signal['volume_ratio']:.1f}x"
                if volume_strength == 'VERY_HIGH':
                    volume_display += "🟢"
                elif volume_strength == 'HIGH':
                    volume_display += "🟡"
                elif volume_strength == 'WEAK':
                    volume_display += "🔴"
                
                html_content += f'''
                        <tr>
                            <td class="rank">{i}</td>
                            <td class="ticker">{signal['ticker']}</td>
                            <td><span class="{signal_class}">{signal['signal_type']}</span></td>
                            <td class="price">₹{signal['current_price']:.1f}</td>
                            <td class="price">₹{signal['entry_price']:.1f}</td>
                            <td class="price">₹{signal['ssl_baseline']:.1f}</td>
                            <td class="price">₹{signal['ssl_upper_channel']:.1f}</td>
                            <td class="price">₹{signal['ssl_lower_channel']:.1f}</td>
                            <td>{rsi_display}</td>
                            <td>{volume_display}</td>
                            <td class="{momentum_class}">{signal['momentum']:+.1f}%</td>
                            <td>{signal.get('combined_score', 0):.1f}</td>
                            <td class="price">₹{signal['stop_loss']:.1f}</td>
                            <td class="price">₹{signal['take_profit']:.1f}</td>
                            <td>1:{signal['risk_reward_ratio']:.1f}</td>
                        </tr>
                '''
            
            html_content += '''
                    </tbody>
                </table>
            '''
        
        html_content += '</div>'
    
    # Generate SELL signals by sector (similar structure)
    if sell_sectors:
        html_content += f"""
            <div class="section">
                <h2>🔴 SELL SIGNALS BY SECTOR</h2>
        """
        
        sorted_sell_sectors = sorted(sell_sectors.items(), key=lambda x: len(x[1]), reverse=True)
        
        for sector, signals in sorted_sell_sectors:
            if not signals:
                continue
                
            html_content += f'<div class="sector-header">🏢 {sector.upper()} SECTOR ({len(signals)} Signals)</div>'
            html_content += '''
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Ticker</th>
                            <th>Signal</th>
                            <th>Current</th>
                            <th>Entry</th>
                            <th>SSL Baseline</th>
                            <th>Upper Channel</th>
                            <th>Lower Channel</th>
                            <th>RSI</th>
                            <th>Volume</th>
                            <th>Momentum</th>
                            <th>Score</th>
                            <th>Stop Loss</th>
                            <th>Target</th>
                            <th>R:R</th>
                        </tr>
                    </thead>
                    <tbody>
            '''
            
            for i, signal in enumerate(signals, 1):
                signal_class = signal['signal_type'].lower()
                momentum_class = 'positive' if signal['momentum'] >= 0 else 'negative'
                
                rsi_value = signal.get('rsi', 50)
                rsi_display = f"{rsi_value:.0f}"
                if rsi_value > 70:
                    rsi_display += "🔴"
                elif rsi_value < 30:
                    rsi_display += "🟢"
                
                volume_strength = signal['volume_analysis']['volume_strength']
                volume_display = f"{signal['volume_ratio']:.1f}x"
                if volume_strength == 'VERY_HIGH':
                    volume_display += "🟢"
                elif volume_strength == 'HIGH':
                    volume_display += "🟡"
                elif volume_strength == 'WEAK':
                    volume_display += "🔴"
                
                html_content += f'''
                        <tr>
                            <td class="rank">{i}</td>
                            <td class="ticker">{signal['ticker']}</td>
                            <td><span class="{signal_class}">{signal['signal_type']}</span></td>
                            <td class="price">₹{signal['current_price']:.1f}</td>
                            <td class="price">₹{signal['entry_price']:.1f}</td>
                            <td class="price">₹{signal['ssl_baseline']:.1f}</td>
                            <td class="price">₹{signal['ssl_upper_channel']:.1f}</td>
                            <td class="price">₹{signal['ssl_lower_channel']:.1f}</td>
                            <td>{rsi_display}</td>
                            <td>{volume_display}</td>
                            <td class="{momentum_class}">{signal['momentum']:+.1f}%</td>
                            <td>{signal.get('combined_score', 0):.1f}</td>
                            <td class="price">₹{signal['stop_loss']:.1f}</td>
                            <td class="price">₹{signal['take_profit']:.1f}</td>
                            <td>1:{signal['risk_reward_ratio']:.1f}</td>
                        </tr>
                '''
            
            html_content += '''
                    </tbody>
                </table>
            '''
        
        html_content += '</div>'
    
    html_content += f"""
            <div class="footer">
                <p><strong>⚠️ Disclaimer:</strong> This analysis is for educational purposes only.</p>
                <p><strong>⚡ Strategy:</strong> SSL Baseline with Keltner Channels using {ma_type} moving average.</p>
                <p><strong>🎯 Logic:</strong> BUY when price breaks above upper channel, SELL when price breaks below lower channel.</p>
                <p><strong>🏆 Ranking:</strong> Combined score based on signal strength, volume, RSI, and momentum.</p>
                <p><strong>📊 MA Types:</strong> Supports SMA, EMA, DEMA, TEMA, LSMA, WMA, HMA, VAMA, TMA, JMA, Kijun v2, McGinley, MF, EDSMA.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Save HTML
    html_filename = f"ssl_baseline_{ma_type.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    html_path = os.path.join(output_dir, html_filename)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return html_path

def main():
    """Main function for SSL Baseline Strategy"""
    print("⚡ SSL BASELINE STRATEGY ANALYZER")
    print("🎯 Keltner Channel Based SSL with Multiple Moving Averages")
    print("="*80)
    
    # Check dependencies
    missing_deps = []
    if not TALIB_AVAILABLE:
        missing_deps.append("talib (for faster technical calculations)")
    if not SCIPY_AVAILABLE:
        missing_deps.append("scipy (for advanced mathematical functions)")
    
    if missing_deps:
        print("📦 OPTIONAL DEPENDENCIES:")
        for dep in missing_deps:
            print(f"   ⚠️  Missing: {dep}")
        print("   💡 Install with: pip install talib scipy")
        print("   🔄 The strategy will work with manual calculations")
        print()
    
    parser = argparse.ArgumentParser(description="SSL Baseline Strategy Analysis")
    
    parser.add_argument('--ma-type', type=str, default='EMA', 
                       choices=['SMA', 'EMA', 'DEMA', 'TEMA', 'LSMA', 'WMA', 'HMA', 'VAMA', 'TMA', 'JMA', 'KIJUN V2', 'MCGINLEY', 'MF', 'EDSMA'],
                       help='Moving average type (default: EMA)')
    parser.add_argument('--length', type=int, default=30, 
                       help='MA length (default: 30)')
    parser.add_argument('--multiplier', type=float, default=0.2, 
                       help='Channel multiplier (default: 0.2)')
    parser.add_argument('--volume-days', type=int, default=20, 
                       help='Volume average days (default: 20)')
    parser.add_argument('--momentum-days', type=int, default=5, 
                       help='Momentum calculation days (default: 5)')
    parser.add_argument('--workers', type=int, default=3, 
                       help='Max concurrent workers (default: 3)')
    parser.add_argument('--output', type=str, 
                       help='Output directory (default: output)')
    parser.add_argument('--test-single', type=str, 
                       help='Test analysis on a single ticker')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug output')
    parser.add_argument('--sector', type=str, 
                       help='Show signals for specific sector only')
    parser.add_argument('--buy-only', action='store_true', 
                       help='Show only BUY signals')
    parser.add_argument('--sell-only', action='store_true', 
                       help='Show only SELL signals')
    
    # MA-specific parameters
    parser.add_argument('--kidiv', type=int, default=1, 
                       help='Kijun MOD Divider for Kijun v2 (default: 1)')
    parser.add_argument('--jurik-phase', type=int, default=3, 
                       help='Jurik Phase for JMA (default: 3)')
    parser.add_argument('--jurik-power', type=int, default=1, 
                       help='Jurik Power for JMA (default: 1)')
    parser.add_argument('--volatility-lookback', type=int, default=10, 
                       help='Volatility lookback for VAMA (default: 10)')
    parser.add_argument('--beta', type=float, default=0.8, 
                       help='Beta for MF (default: 0.8)')
    parser.add_argument('--feedback', action='store_true', 
                       help='Use feedback for MF (default: False)')
    parser.add_argument('--z', type=float, default=0.5, 
                       help='Feedback weighting for MF (default: 0.5)')
    
    args = parser.parse_args()
    
    # Prepare MA-specific kwargs
    ma_kwargs = {
        'kidiv': args.kidiv,
        'jurik_phase': args.jurik_phase,
        'jurik_power': args.jurik_power,
        'volatility_lookback': args.volatility_lookback,
        'beta': args.beta,
        'feedback': args.feedback,
        'z': args.z
    }
    
    # Test single ticker if requested
    if args.test_single:
        print(f"🧪 TESTING SINGLE TICKER: {args.test_single}")
        print("="*80)
        try:
            result = analyze_ssl_baseline_strategy(
                args.test_single, 
                args.ma_type, 
                args.length, 
                args.multiplier,
                'ATR', 3.0, 14, 4.0, 2.0,
                args.volume_days, 
                args.momentum_days, 
                debug=True,
                **ma_kwargs
            )
            if result:
                print(f"\n✅ SUCCESS! Signal: {result['signal_type']}")
                print(f"   🏢 Sector: {result['sector']}")
                print(f"   📊 Current Price: ₹{result['current_price']:.2f}")
                print(f"   💰 Entry Price: ₹{result['entry_price']:.2f}")
                print(f"   🎯 Entry Logic: {result['entry_reason']}")
                print(f"   📊 SSL Baseline: ₹{result['ssl_baseline']:.2f}")
                print(f"   📈 Upper Channel: ₹{result['ssl_upper_channel']:.2f}")
                print(f"   📉 Lower Channel: ₹{result['ssl_lower_channel']:.2f}")
                print(f"   🎯 MA Type: {result['ma_type']}({result['ma_length']})")
                print(f"   💰 Risk Management:")
                print(f"      Stop Loss: ₹{result['stop_loss']:.2f}")
                print(f"      Take Profit: ₹{result['take_profit']:.2f}")
                print(f"      R:R = 1:{result['risk_reward_ratio']:.1f}")
            else:
                print(f"\n❌ No result for {args.test_single}")
                print("💡 Possible issues:")
                print("   - Ticker not found or no data available")
                print("   - Internet connectivity issues")
                print("   - Insufficient historical data")
        except Exception as e:
            print(f"\n❌ Error testing {args.test_single}: {str(e)}")
            print("💡 Try with --debug flag for more details")
        return
    
    print("⚡ SSL BASELINE STRATEGY ANALYZER")
    print("🎯 Keltner Channel Based SSL with Multiple Moving Averages")
    print("="*80)
    print(f"📊 MA Type: {args.ma_type}")
    print(f"📏 MA Length: {args.length}")
    print(f"📊 Channel Multiplier: {args.multiplier}")
    print(f"📊 Volume Period: {args.volume_days} trading days")
    print(f"🚀 Momentum Period: {args.momentum_days} trading days")
    print(f"⚙️  Workers: {args.workers}")
    print("="*80)
    
    # Set output directory
    output_dir = args.output or getattr(config, 'OUTPUT_DIR', 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Analyze all stocks
    all_signals = analyze_all_stocks_ssl(
        ma_type=args.ma_type,
        length=args.length,
        multiplier=args.multiplier,
        volume_days=args.volume_days,
        momentum_days=args.momentum_days,
        max_workers=args.workers,
        debug=args.debug,
        **ma_kwargs
    )
    
    if not all_signals:
        print("\n❌ No signals generated!")
        return
    
    # Filter by sector if specified
    if args.sector:
        all_signals = [s for s in all_signals if s['sector'].upper() == args.sector.upper()]
        if not all_signals:
            print(f"\n❌ No signals found for sector: {args.sector}")
            return
    
    # Display results
    if args.buy_only:
        display_ssl_signals(all_signals, ['BUY'], "BUY")
    elif args.sell_only:
        display_ssl_signals(all_signals, ['SELL'], "SELL")
    else:
        display_ssl_signals(all_signals, ['BUY'], "BUY")
        display_ssl_signals(all_signals, ['SELL'], "SELL")
    
    # Generate reports
    print(f"\n📄 Generating SSL Baseline reports...")
    
    # HTML Report
    html_path = generate_ssl_html_report(
        all_signals, args.ma_type, args.length, args.multiplier,
        args.volume_days, args.momentum_days, output_dir
    )
    if html_path:
        print(f"🌐 SSL Baseline HTML Report: {html_path}")
        print(f"🔗 Open: file://{os.path.abspath(html_path)}")
    
    # JSON Report
    json_filename = f"ssl_baseline_{args.ma_type.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_path = os.path.join(output_dir, json_filename)
    
    json_data = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'total_stocks_analyzed': len(all_signals),
            'ma_type': args.ma_type,
            'ma_length': args.length,
            'channel_multiplier': args.multiplier,
            'volume_days': args.volume_days,
            'momentum_days': args.momentum_days,
            'strategy': f'SSL Baseline ({args.ma_type})',
            'ma_parameters': ma_kwargs
        },
        'signals': all_signals
    }
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"📊 JSON Data: {json_path}")
    print(f"\n✅ SSL Baseline Analysis Complete!")
    print(f"📁 Output Directory: {os.path.abspath(output_dir)}")
    
    print(f"\n💡 SSL BASELINE FEATURES:")
    print(f"   ⚡ KELTNER CHANNELS: Dynamic support/resistance based on volatility")
    print(f"   📊 MULTIPLE MA TYPES: 14 different moving averages supported")
    print(f"   🎯 SSL LOGIC: Buy above upper channel, sell below lower channel")
    print(f"   📈 RISK MANAGEMENT: ATR/Percent/Previous LL-HH based stops")
    print(f"   🏢 SECTOR ANALYSIS: Industry-wise grouping and performance")
    print(f"   💰 POSITION SIZING: Risk-based position calculations")
    
    print(f"\n🚀 USAGE EXAMPLES:")
    print(f"   python ssl_baseline.py --ma-type HMA --length 21           # Hull MA with 21 periods")
    print(f"   python ssl_baseline.py --ma-type JMA --jurik-phase 5       # Jurik MA with custom phase")
    print(f"   python ssl_baseline.py --buy-only --sector Banking         # Banking BUY signals only")
    print(f"   python ssl_baseline.py --test-single RELIANCE --debug      # Test single stock with details")
    
    print(f"\n🛠️  INSTALLATION HELP:")
    print(f"   pip install yfinance pandas numpy                         # Required packages")
    print(f"   pip install talib scipy                                   # Optional (faster calculations)")
    print(f"   pip install tabulate                                      # For table formatting")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        print("💡 Try running with --debug flag for more details")
        print("💡 Check if all required packages are installed:")
        print("   pip install yfinance pandas numpy tabulate")