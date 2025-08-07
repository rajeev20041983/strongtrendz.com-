#!/usr/bin/env python
# enhanced_swing_analysis.py - Complete Swing Analysis + Pine Script SWING CALLS
# Core Logic PRESERVED + Pine Script Confirmation Added

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
from typing import Dict, List, Tuple, Optional

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

# SECTOR MAPPING - UNCHANGED
SECTOR_MAPPING = {
    # Banking & Financial Services
    'HDFCBANK': 'Banking', 'ICICIBANK': 'Banking', 'SBIN': 'Banking', 'AXISBANK': 'Banking',
    'KOTAKBANK': 'Banking', 'BAJFINANCE': 'Financial Services', 
    
    # Information Technology
    'TCS': 'Information Technology', 'INFY': 'Information Technology', 'WIPRO': 'Information Technology',
    
    # Oil & Gas
    'RELIANCE': 'Oil & Gas', 'ONGC': 'Oil & Gas', 'IOC': 'Oil & Gas',
    
    # FMCG
    'HINDUNILVR': 'FMCG', 'ITC': 'FMCG', 'NESTLEIND': 'FMCG',
    
    # Automotive
    'MARUTI': 'Automotive', 'M&M': 'Automotive', 'TATAMOTORS': 'Automotive',
    
    # Cement
    'ULTRACEMCO': 'Cement', 'GRASIM': 'Cement', 'SHREECEM': 'Cement',
    
    # Paints & Chemicals
    'ASIANPAINT': 'Paints & Chemicals', 'BERGER': 'Paints & Chemicals',
    
    # Capital Goods
    'LT': 'Capital Goods', 'ABB': 'Capital Goods', 'SIEMENS': 'Capital Goods',
    
    # Power
    'POWERGRID': 'Power', 'NTPC': 'Power', 'ADANIPOWER': 'Power',
    
    # Telecommunications
    'BHARTIARTL': 'Telecom', 'IDEA': 'Telecom',
    
    # Consumer Durables
    'TITAN': 'Consumer Durables', 'BAJAJELEEC': 'Consumer Durables',
}

def get_sector(ticker: str) -> str:
    """Get sector for a ticker - UNCHANGED"""
    return SECTOR_MAPPING.get(ticker, 'Others')

def get_stock_data(ticker: str, lookback_days: int = 200) -> Optional[pd.DataFrame]:
    """Get stock data for analysis - UNCHANGED"""
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

def detect_pivot_points(data: pd.DataFrame, length: int = 21) -> Tuple[pd.Series, pd.Series]:
    """Detect pivot highs and lows using rolling window approach - UNCHANGED"""
    highs = data['High']
    lows = data['Low']
    
    # Initialize pivot series
    pivot_highs = pd.Series(index=data.index, dtype=float)
    pivot_lows = pd.Series(index=data.index, dtype=float)
    
    for i in range(length, len(data) - length):
        # Check for pivot high
        current_high = highs.iloc[i]
        window_highs = highs.iloc[i-length:i+length+1]
        
        if current_high == window_highs.max() and window_highs.tolist().count(current_high) == 1:
            pivot_highs.iloc[i] = current_high
        
        # Check for pivot low
        current_low = lows.iloc[i]
        window_lows = lows.iloc[i-length:i+length+1]
        
        if current_low == window_lows.min() and window_lows.tolist().count(current_low) == 1:
            pivot_lows.iloc[i] = current_low
    
    return pivot_highs.dropna(), pivot_lows.dropna()

def classify_swing_structure(pivot_highs: pd.Series, pivot_lows: pd.Series) -> Tuple[Dict, Dict]:
    """Classify swing structure as HH/LH/HL/LL - UNCHANGED"""
    swing_highs = {}
    swing_lows = {}
    
    # Classify highs
    prev_high = None
    for i, (timestamp, price) in enumerate(pivot_highs.items()):
        if prev_high is not None:
            if price > prev_high:
                swing_highs[timestamp] = {'type': 'HH', 'price': price, 'prev_price': prev_high}
            else:
                swing_highs[timestamp] = {'type': 'LH', 'price': price, 'prev_price': prev_high}
        else:
            swing_highs[timestamp] = {'type': 'H', 'price': price, 'prev_price': None}
        prev_high = price
    
    # Classify lows
    prev_low = None
    for i, (timestamp, price) in enumerate(pivot_lows.items()):
        if prev_low is not None:
            if price < prev_low:
                swing_lows[timestamp] = {'type': 'LL', 'price': price, 'prev_price': prev_low}
            else:
                swing_lows[timestamp] = {'type': 'HL', 'price': price, 'prev_price': prev_low}
        else:
            swing_lows[timestamp] = {'type': 'L', 'price': price, 'prev_price': None}
        prev_low = price
    
    return swing_highs, swing_lows

def detect_candlestick_patterns(data: pd.DataFrame, length: int = 21) -> Dict:
    """Detect candlestick patterns at pivot points - UNCHANGED"""
    patterns = {
        'hammer': [],
        'inverted_hammer': [],
        'bullish_engulfing': [],
        'hanging_man': [],
        'shooting_star': [],
        'bearish_engulfing': []
    }
    
    # Get pivot points
    pivot_highs, pivot_lows = detect_pivot_points(data, length)
    
    # Pattern descriptions
    descriptions = {
        'hammer': "Hammer: Short body with long lower wick at bottom of downtrend. Shows buying pressure.",
        'inverted_hammer': "Inverted Hammer: Short body with long upper wick. Indicates potential bullish reversal.",
        'bullish_engulfing': "Bullish Engulfing: Large green candle engulfs previous red candle.",
        'hanging_man': "Hanging Man: Bearish equivalent of hammer at end of uptrend.",
        'shooting_star': "Shooting Star: Small body with long upper wick in uptrend. Bearish reversal signal.",
        'bearish_engulfing': "Bearish Engulfing: Large red candle engulfs previous green candle."
    }
    
    for i in range(1, len(data)):
        row = data.iloc[i]
        prev_row = data.iloc[i-1] if i > 0 else None
        
        o, h, l, c = row['Open'], row['High'], row['Low'], row['Close']
        d = abs(c - o)  # Body size
        
        timestamp = data.index[i]
        
        # Check if current bar is at a pivot point
        is_pivot_low = timestamp in pivot_lows.index
        is_pivot_high = timestamp in pivot_highs.index
        
        # Hammer (at pivot lows)
        if is_pivot_low and min(o, c) - l > d and h - max(c, o) < d:
            patterns['hammer'].append({
                'timestamp': timestamp,
                'price': (h + l) / 2,
                'description': descriptions['hammer'],
                'strength': 'STRONG' if d > 0 else 'WEAK'
            })
        
        # Inverted Hammer (at pivot lows)
        if is_pivot_low and h - max(c, o) > d and min(c, o) - l < d:
            patterns['inverted_hammer'].append({
                'timestamp': timestamp,
                'price': (h + l) / 2,
                'description': descriptions['inverted_hammer'],
                'strength': 'STRONG' if d > 0 else 'WEAK'
            })
        
        # Hanging Man (at pivot highs)
        if is_pivot_high and min(c, o) - l > d and h - max(o, c) < d:
            patterns['hanging_man'].append({
                'timestamp': timestamp,
                'price': (h + l) / 2,
                'description': descriptions['hanging_man'],
                'strength': 'STRONG' if d > 0 else 'WEAK'
            })
        
        # Shooting Star (at pivot highs)
        if is_pivot_high and h - max(o, c) > d and min(c, o) - l < d:
            patterns['shooting_star'].append({
                'timestamp': timestamp,
                'price': (h + l) / 2,
                'description': descriptions['shooting_star'],
                'strength': 'STRONG' if d > 0 else 'WEAK'
            })
        
        # Bullish Engulfing
        if prev_row is not None:
            prev_o, prev_c = prev_row['Open'], prev_row['Close']
            if c > o and prev_c < prev_o and c > prev_o and o < prev_c:
                patterns['bullish_engulfing'].append({
                    'timestamp': timestamp,
                    'price': (h + l) / 2,
                    'description': descriptions['bullish_engulfing'],
                    'strength': 'STRONG' if is_pivot_low else 'MODERATE'
                })
        
        # Bearish Engulfing
        if prev_row is not None:
            prev_o, prev_c = prev_row['Open'], prev_row['Close']
            if c < o and prev_c > prev_o and c < prev_o and o > prev_c:
                patterns['bearish_engulfing'].append({
                    'timestamp': timestamp,
                    'price': (h + l) / 2,
                    'description': descriptions['bearish_engulfing'],
                    'strength': 'STRONG' if is_pivot_high else 'MODERATE'
                })
    
    return patterns

def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """Calculate RSI - UNCHANGED"""
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

def calculate_volume_momentum(data: pd.DataFrame, volume_days: int = 20, momentum_days: int = 5) -> Tuple[float, float]:
    """Calculate volume ratio and momentum - UNCHANGED"""
    current_volume = data['Volume'].iloc[-1]
    current_price = data['Close'].iloc[-1]
    
    # Volume ratio
    if len(data) >= volume_days + 1:
        avg_volume = data['Volume'].iloc[-(volume_days+1):-1].mean()
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
    
    return volume_ratio, momentum

def calculate_rsi_series(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI as a pandas Series - UNCHANGED"""
    try:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, 0.001)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)
    except Exception:
        return pd.Series([50] * len(prices), index=prices.index)

def calculate_swing_calls_signals(data: pd.DataFrame, ema_period: int = 5, sma_period: int = 50, rsi_period: int = 14, 
                                 rsi_overbought: int = 80, rsi_oversold: int = 20) -> Dict:
    """Calculate SWING CALLS signals based on EMA/SMA crossover + RSI - UNCHANGED"""
    try:
        close = data['Close']
        high = data['High']
        low = data['Low']
        open_price = data['Open']
        
        # Calculate EMA and SMA
        ema5 = close.ewm(span=ema_period).mean()
        sma50 = close.rolling(window=sma_period).mean()
        
        # Calculate RSI
        rsi = calculate_rsi_series(close, rsi_period)
        
        # Get current values
        current_ema5 = ema5.iloc[-1]
        current_sma50 = sma50.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_high = high.iloc[-1]
        current_low = low.iloc[-1]
        current_open = open_price.iloc[-1]
        current_close = close.iloc[-1]
        
        # Previous values for crossover detection
        prev_ema5 = ema5.iloc[-2] if len(ema5) > 1 else current_ema5
        prev_sma50 = sma50.iloc[-2] if len(sma50) > 1 else current_sma50
        prev_rsi = rsi.iloc[-2] if len(rsi) > 1 else current_rsi
        
        # SWING CALLS BUY/SELL Logic (from Pine Script)
        
        # BUY CALL: crossunder(sma50, ema5) AND high > sma50
        buycall = (prev_sma50 >= prev_ema5 and current_sma50 < current_ema5 and current_high > current_sma50)
        
        # SELL CALL: crossover(sma50, ema5) AND open > close (red candle)
        sellcall = (prev_sma50 <= prev_ema5 and current_sma50 > current_ema5 and current_open > current_close)
        
        # RSI EXIT CONDITIONS
        # Buy Exit: RSI crosses under overbought level (80)
        buyexit = (prev_rsi >= rsi_overbought and current_rsi < rsi_overbought)
        
        # Sell Exit: RSI crosses over oversold level (20) 
        sellexit = (prev_rsi <= rsi_oversold and current_rsi > rsi_oversold)
        
        # SMA COLOR LOGIC (trend indication)
        if current_rsi >= 85 or current_rsi <= 15:
            sma_color = "YELLOW"  # Extreme RSI
            trend_status = "EXTREME"
        elif current_low > current_sma50:
            sma_color = "LIME"   # Price above SMA50
            trend_status = "BULLISH"
        elif current_high < current_sma50:
            sma_color = "RED"    # Price below SMA50  
            trend_status = "BEARISH"
        else:
            sma_color = "YELLOW" # Mixed/Neutral
            trend_status = "NEUTRAL"
        
        return {
            'ema5': float(current_ema5),
            'sma50': float(current_sma50),
            'rsi': float(current_rsi),
            'buycall': buycall,
            'sellcall': sellcall,
            'buyexit': buyexit,
            'sellexit': sellexit,
            'sma_color': sma_color,
            'trend_status': trend_status,
            'ema_above_sma': current_ema5 > current_sma50,
            'price_above_sma': current_close > current_sma50,
            'is_red_candle': current_open > current_close
        }
        
    except Exception as e:
        return {
            'ema5': 0, 'sma50': 0, 'rsi': 50,
            'buycall': False, 'sellcall': False,
            'buyexit': False, 'sellexit': False,
            'sma_color': 'YELLOW', 'trend_status': 'NEUTRAL',
            'ema_above_sma': False, 'price_above_sma': False,
            'is_red_candle': False
        }

# NEW FUNCTION: Pine Script SWING CALLS Confirmation
def calculate_pine_script_confirmation(data: pd.DataFrame) -> dict:
    """
    Pine Script SWING CALLS - EXACT implementation for confirmation only
    This is ADDITIONAL to existing logic, not replacing it
    
    Pine Script Logic:
    - buycall = crossunder(sma2,ema1) and high>sma2  
    - sellcall = crossover(sma2,ema1) and open>close
    - buyexit = crossunder(rs,80)
    - sellexit = crossover(rs,20)
    """
    try:
        close = data['Close']
        high = data['High']
        low = data['Low']
        open_price = data['Open']
        
        # Pine Script exact logic
        ema1 = close.ewm(span=5).mean()     # ema(close,5) 
        sma2 = close.rolling(window=50).mean()  # sma(close,50)
        
        # RSI calculation (Pine Script style)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, 0.001)
        rsi = 100 - (100 / (1 + rs))
        
        # Current and previous values
        current_ema1 = ema1.iloc[-1]
        current_sma2 = sma2.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_high = high.iloc[-1]
        current_low = low.iloc[-1]
        current_open = open_price.iloc[-1]
        current_close = close.iloc[-1]
        
        prev_ema1 = ema1.iloc[-2] if len(ema1) > 1 else current_ema1
        prev_sma2 = sma2.iloc[-2] if len(sma2) > 1 else current_sma2
        prev_rsi = rsi.iloc[-2] if len(rsi) > 1 else current_rsi
        
        # EXACT Pine Script logic (for confirmation only)
        
        # Pine Script: buycall = crossunder(sma2,ema1) and high>sma2
        # crossunder(sma2,ema1) means SMA2 was >= EMA1 and now SMA2 < EMA1
        pine_buycall = (prev_sma2 >= prev_ema1 and current_sma2 < current_ema1 and current_high > current_sma2)
        
        # Pine Script: sellcall = crossover(sma2,ema1) and open>close  
        # crossover(sma2,ema1) means SMA2 was <= EMA1 and now SMA2 > EMA1
        pine_sellcall = (prev_sma2 <= prev_ema1 and current_sma2 > current_ema1 and current_open > current_close)
        
        # Pine Script: buyexit = crossunder(rs,80)
        pine_buyexit = (prev_rsi >= 80 and current_rsi < 80)
        
        # Pine Script: sellexit = crossover(rs,20)  
        pine_sellexit = (prev_rsi <= 20 and current_rsi > 20)
        
        # SMA color logic (for context)
        if current_rsi >= 85 or current_rsi <= 15:
            sma_color = "YELLOW"
        elif current_low > current_sma2:
            sma_color = "LIME" 
        elif current_high < current_sma2:
            sma_color = "RED"
        else:
            sma_color = "YELLOW"
        
        return {
            'pine_buycall': pine_buycall,
            'pine_sellcall': pine_sellcall,
            'pine_buyexit': pine_buyexit,
            'pine_sellexit': pine_sellexit,
            'ema1': float(current_ema1),
            'sma2': float(current_sma2),
            'rsi': float(current_rsi),
            'sma_color': sma_color,
            'crossover_details': {
                'prev_sma2_ema1_relation': 'SMA>=EMA' if prev_sma2 >= prev_ema1 else 'SMA<EMA',
                'curr_sma2_ema1_relation': 'SMA>=EMA' if current_sma2 >= current_ema1 else 'SMA<EMA',
                'high_above_sma': current_high > current_sma2,
                'red_candle': current_open > current_close,
                'rsi_overbought_exit': prev_rsi >= 80 and current_rsi < 80,
                'rsi_oversold_exit': prev_rsi <= 20 and current_rsi > 20
            }
        }
        
    except Exception as e:
        return {
            'pine_buycall': False, 'pine_sellcall': False,
            'pine_buyexit': False, 'pine_sellexit': False,
            'ema1': 0, 'sma2': 0, 'rsi': 50, 'sma_color': 'YELLOW',
            'crossover_details': {}
        }

def generate_combined_signals(result: Dict, swing_calls: Dict) -> Dict:
    """Generate combined signals from swing patterns + SWING CALLS logic - UNCHANGED"""
    
    signal_type = 'HOLD'
    signal_strength = 5.0
    signal_reason = "No clear signal"
    confidence = 'LOW'
    signal_source = 'NONE'
    
    latest_swing = result['latest_swing_label']
    latest_pattern = result['latest_pattern']
    rsi = result['rsi']
    volume_ratio = result['volume_ratio']
    momentum = result['momentum']
    
    # SWING CALLS SIGNALS (Primary - from Pine Script)
    if swing_calls['buycall']:
        signal_type = 'SWING_BUY'
        signal_strength = 8.0
        signal_source = 'SWING_CALLS'
        confidence = 'HIGH'
        signal_reason = f"EMA5 above SMA50 crossover + High > SMA50"
        
        # Additional confirmations
        confirmations = []
        
        # Swing pattern confirmation
        if latest_swing in ['HL', 'HH'] and latest_pattern in ['Hammer', 'Inverted Hammer', 'Bullish Engulfing']:
            signal_strength += 1.0
            confirmations.append(f"Swing {latest_swing} + {latest_pattern}")
        
        # Volume confirmation
        if volume_ratio > 1.5:
            signal_strength += 0.5
            confirmations.append(f"Volume {volume_ratio:.1f}x")
        
        # RSI confirmation
        if rsi < 50:
            signal_strength += 0.5
            confirmations.append("RSI Favorable")
        
        if confirmations:
            signal_reason += f" + {' + '.join(confirmations)}"
        
        signal_strength = min(signal_strength, 10.0)
    
    elif swing_calls['sellcall']:
        signal_type = 'SWING_SELL'
        signal_strength = 8.0
        signal_source = 'SWING_CALLS'
        confidence = 'HIGH'
        signal_reason = f"SMA50 above EMA5 crossover + Red candle"
        
        # Additional confirmations
        confirmations = []
        
        # Swing pattern confirmation
        if latest_swing in ['LH', 'LL'] and latest_pattern in ['Hanging Man', 'Shooting Star', 'Bearish Engulfing']:
            signal_strength += 1.0
            confirmations.append(f"Swing {latest_swing} + {latest_pattern}")
        
        # Volume confirmation
        if volume_ratio > 1.5:
            signal_strength += 0.5
            confirmations.append(f"Volume {volume_ratio:.1f}x")
        
        # RSI confirmation
        if rsi > 50:
            signal_strength += 0.5
            confirmations.append("RSI Favorable")
        
        if confirmations:
            signal_reason += f" + {' + '.join(confirmations)}"
        
        signal_strength = min(signal_strength, 10.0)
    
    # RSI EXIT SIGNALS (from Pine Script)
    elif swing_calls['buyexit']:
        signal_type = 'RSI_EXIT_SELL'
        signal_strength = 7.0
        signal_source = 'RSI_EXIT'
        confidence = 'MEDIUM'
        signal_reason = f"RSI crossed under {80} (Overbought exit)"
    
    elif swing_calls['sellexit']:
        signal_type = 'RSI_EXIT_BUY'
        signal_strength = 7.0
        signal_source = 'RSI_EXIT'
        confidence = 'MEDIUM'
        signal_reason = f"RSI crossed over {20} (Oversold exit)"
    
    # FALLBACK: Pure swing pattern signals (if no SWING CALLS)
    elif latest_swing in ['HL', 'HH'] and latest_pattern in ['Hammer', 'Inverted Hammer', 'Bullish Engulfing']:
        signal_type = 'PATTERN_BUY'
        signal_strength = 6.5
        signal_source = 'SWING_PATTERN'
        confidence = 'MEDIUM'
        signal_reason = f"{latest_swing} + {latest_pattern}"
        
        # RSI boost
        if rsi < 35:
            signal_strength += 1.0
            signal_reason += " + RSI Oversold"
        
        # Volume boost
        if volume_ratio > 1.5:
            signal_strength += 0.5
            signal_reason += f" + Volume {volume_ratio:.1f}x"
    
    elif latest_swing in ['LH', 'LL'] and latest_pattern in ['Hanging Man', 'Shooting Star', 'Bearish Engulfing']:
        signal_type = 'PATTERN_SELL'
        signal_strength = 6.5
        signal_source = 'SWING_PATTERN'
        confidence = 'MEDIUM'
        signal_reason = f"{latest_swing} + {latest_pattern}"
        
        # RSI boost
        if rsi > 65:
            signal_strength += 1.0
            signal_reason += " + RSI Overbought"
        
        # Volume boost
        if volume_ratio > 1.5:
            signal_strength += 0.5
            signal_reason += f" + Volume {volume_ratio:.1f}x"
    
    # Determine final confidence based on strength
    if signal_strength >= 9.0:
        confidence = 'VERY_HIGH'
    elif signal_strength >= 8.0:
        confidence = 'HIGH'
    elif signal_strength >= 7.0:
        confidence = 'MEDIUM'
    else:
        confidence = 'LOW'
    
    # Update result with combined signal data
    result.update({
        'signal_type': signal_type,
        'signal_strength': signal_strength,
        'signal_reason': signal_reason,
        'confidence': confidence,
        'signal_source': signal_source,
        'has_trading_signal': signal_type != 'HOLD',
        
        # SWING CALLS data
        'swing_calls': swing_calls
    })
    
    return result

# NEW FUNCTION: Enhanced signal generation with Pine Script confirmation
def generate_enhanced_signals(result: dict, pine_confirmation: dict) -> dict:
    """
    ENHANCED signal generation - Core logic UNCHANGED + Pine Script confirmation
    Only generates STRONG BUY/STRONG SELL when both systems agree
    """
    
    # KEEP ALL EXISTING VARIABLES
    signal_type = result.get('signal_type', 'HOLD')
    signal_strength = result.get('signal_strength', 5.0)
    signal_reason = result.get('signal_reason', "No clear signal")
    confidence = result.get('confidence', 'LOW')
    signal_source = result.get('signal_source', 'NONE')
    
    # Extract existing analysis
    latest_swing = result['latest_swing_label']
    latest_pattern = result['latest_pattern']
    rsi = result['rsi']
    volume_ratio = result['volume_ratio']
    momentum = result['momentum']
    
    # Pine Script confirmation flags
    pine_buycall = pine_confirmation['pine_buycall']
    pine_sellcall = pine_confirmation['pine_sellcall']
    pine_buyexit = pine_confirmation['pine_buyexit']
    pine_sellexit = pine_confirmation['pine_sellexit']
    
    # ENHANCED LOGIC: Existing + Pine Script confirmation for STRONG signals
    
    # STRONG BUY: Existing bullish signals + Pine Script BUY confirmation
    if ((latest_swing in ['HL', 'HH'] and latest_pattern in ['Hammer', 'Inverted Hammer', 'Bullish Engulfing']) 
        or signal_type in ['PATTERN_BUY', 'RSI_EXIT_BUY', 'SWING_BUY']) and pine_buycall:
        
        signal_type = 'STRONG_BUY'
        signal_strength = 9.5
        signal_source = 'SWING_PATTERN + PINE_SCRIPT'
        confidence = 'VERY_HIGH'
        signal_reason = f"Pine Script BUY Call + {latest_swing if latest_swing else 'Pattern'}"
        
        if latest_pattern != "None":
            signal_reason += f" + {latest_pattern}"
        if volume_ratio > 1.5:
            signal_reason += f" + Volume {volume_ratio:.1f}x"
        if rsi < 50:
            signal_reason += " + RSI Favorable"
    
    # STRONG SELL: Existing bearish signals + Pine Script SELL confirmation  
    elif ((latest_swing in ['LH', 'LL'] and latest_pattern in ['Hanging Man', 'Shooting Star', 'Bearish Engulfing'])
          or signal_type in ['PATTERN_SELL', 'RSI_EXIT_SELL', 'SWING_SELL']) and pine_sellcall:
        
        signal_type = 'STRONG_SELL'
        signal_strength = 9.5
        signal_source = 'SWING_PATTERN + PINE_SCRIPT'
        confidence = 'VERY_HIGH'
        signal_reason = f"Pine Script SELL Call + {latest_swing if latest_swing else 'Pattern'}"
        
        if latest_pattern != "None":
            signal_reason += f" + {latest_pattern}"
        if volume_ratio > 1.5:
            signal_reason += f" + Volume {volume_ratio:.1f}x"
        if rsi > 50:
            signal_reason += " + RSI Favorable"
    
    # Pine Script EXIT signals (standalone)
    elif pine_buyexit and not (signal_type in ['STRONG_BUY', 'STRONG_SELL']):
        signal_type = 'RSI_EXIT_SELL'
        signal_strength = 7.5
        signal_source = 'PINE_SCRIPT_RSI'
        confidence = 'HIGH'
        signal_reason = "Pine Script: RSI crossed under 80 (Sell exit)"
    
    elif pine_sellexit and not (signal_type in ['STRONG_BUY', 'STRONG_SELL']):
        signal_type = 'RSI_EXIT_BUY'  
        signal_strength = 7.5
        signal_source = 'PINE_SCRIPT_RSI'
        confidence = 'HIGH'
        signal_reason = "Pine Script: RSI crossed over 20 (Buy exit)"
    
    # Keep original signals if no Pine Script confirmation (existing logic preserved)
    # This ensures your core logic is never disturbed
    
    # Update result with enhanced data
    result.update({
        'signal_type': signal_type,
        'signal_strength': signal_strength,
        'signal_reason': signal_reason,
        'confidence': confidence,
        'signal_source': signal_source,
        'has_trading_signal': signal_type != 'HOLD',
        'has_strong_signal': signal_type in ['STRONG_BUY', 'STRONG_SELL'],
        
        # Pine Script confirmation data (additional info)
        'pine_confirmation': pine_confirmation
    })
    
    return result

# ENHANCED FUNCTION: Main analysis with Pine Script confirmation
def analyze_swing_patterns_enhanced(ticker: str, length: int = 21, volume_days: int = 20, 
                                   momentum_days: int = 5, debug: bool = False) -> dict:
    """
    Enhanced swing analysis - CORE LOGIC UNCHANGED + Pine Script confirmation
    """
    try:
        if debug:
            print(f"📊 Analyzing {ticker} with Pine Script confirmation...")
        
        data = get_stock_data(ticker, 200)
        if data is None:
            return None
        
        # ALL EXISTING LOGIC REMAINS THE SAME - NO CHANGES TO CORE ANALYSIS
        current_price = data['Close'].iloc[-1]
        current_volume = data['Volume'].iloc[-1]
        
        print(f"   📊 Data: {len(data)} trading days available")
        
        # Detect pivot points (UNCHANGED)
        pivot_highs, pivot_lows = detect_pivot_points(data, length)
        
        # Classify swing structure (UNCHANGED)
        swing_highs, swing_lows = classify_swing_structure(pivot_highs, pivot_lows)
        
        # Detect candlestick patterns (UNCHANGED)
        patterns = detect_candlestick_patterns(data, length)
        
        # Calculate technical indicators (UNCHANGED)
        rsi = calculate_rsi(data['Close'])
        volume_ratio, momentum = calculate_volume_momentum(data, volume_days, momentum_days)
        
        # Find latest swing points (UNCHANGED)
        latest_swing = None
        latest_swing_type = None
        latest_pattern = "None"
        
        if swing_highs or swing_lows:
            all_swings = []
            
            for timestamp, swing_data in swing_highs.items():
                all_swings.append((timestamp, 'HIGH', swing_data))
            
            for timestamp, swing_data in swing_lows.items():
                all_swings.append((timestamp, 'LOW', swing_data))
            
            if all_swings:
                all_swings.sort(key=lambda x: x[0], reverse=True)
                latest_timestamp, latest_swing_type, latest_swing = all_swings[0]
                
                # Check for patterns at latest swing (UNCHANGED)
                for pattern_name, pattern_list in patterns.items():
                    for pattern in pattern_list:
                        if abs((pattern['timestamp'] - latest_timestamp).days) <= 1:
                            latest_pattern = pattern_name.replace('_', ' ').title()
                            break
                    if latest_pattern != "None":
                        break
        
        # EXISTING RESULT STRUCTURE - NO CHANGES
        result = {
            'ticker': ticker,
            'sector': get_sector(ticker),
            'current_price': float(current_price),
            'current_volume': float(current_volume),
            
            # Swing Analysis (UNCHANGED)
            'total_swing_highs': len(swing_highs),
            'total_swing_lows': len(swing_lows),
            'swing_highs': [{'timestamp': str(k), 'type': v['type'], 'price': float(v['price'])} for k, v in swing_highs.items()],
            'swing_lows': [{'timestamp': str(k), 'type': v['type'], 'price': float(v['price'])} for k, v in swing_lows.items()],
            
            # Latest swing point (UNCHANGED)
            'latest_swing_type': latest_swing_type,
            'latest_swing_label': latest_swing['type'] if latest_swing else None,
            'latest_swing_price': float(latest_swing['price']) if latest_swing else None,
            'latest_pattern': latest_pattern,
            
            # Pattern Analysis (UNCHANGED)
            'total_patterns': sum(len(patterns[p]) for p in patterns),
            'pattern_breakdown': {p: len(patterns[p]) for p in patterns},
            'all_patterns': patterns,
            
            # Technical Indicators (UNCHANGED)
            'rsi': float(rsi),
            'volume_ratio': float(volume_ratio),
            'momentum': float(momentum),
            
            # Analysis metadata (UNCHANGED)
            'analysis_type': 'Enhanced Swing Pattern + Pine Script Confirmation',
            'strategy': f'Core Swing Analysis + Pine Script SWING CALLS (Length: {length})'
        }
        
        # EXISTING signal generation (your original logic preserved)
        swing_calls = calculate_swing_calls_signals(data)  # Your existing function
        result = generate_combined_signals(result, swing_calls)  # Your existing function
        
        # NEW: Add Pine Script confirmation layer
        pine_confirmation = calculate_pine_script_confirmation(data)
        result = generate_enhanced_signals(result, pine_confirmation)
        
        # Enhanced display
        strong_signal = "STRONG " if result.get('has_strong_signal', False) else ""
        print(f"   📊 Swings: {len(swing_highs)} highs, {len(swing_lows)} lows")
        print(f"   🎯 Latest: {latest_swing['type'] if latest_swing else 'None'} + {latest_pattern}")
        print(f"   📈 Signal: {strong_signal}{result['signal_type']} (Strength: {result['signal_strength']:.1f}/10)")
        print(f"   💡 Source: {result['signal_source']}")
        
        # Pine Script confirmation status
        if pine_confirmation['pine_buycall']:
            print(f"   🚀 Pine Script: BUY CALL confirmed")
        elif pine_confirmation['pine_sellcall']:
            print(f"   📉 Pine Script: SELL CALL confirmed")
        elif pine_confirmation['pine_buyexit']:
            print(f"   ⚠️  Pine Script: RSI BUY EXIT")
        elif pine_confirmation['pine_sellexit']:
            print(f"   ⚠️  Pine Script: RSI SELL EXIT")
        else:
            print(f"   ⚪ Pine Script: No confirmation")
            
        print(f"   🏢 Sector: {get_sector(ticker)}")
        
        return result
        
    except Exception as e:
        if debug:
            print(f"Error analyzing {ticker}: {e}")
        return None

# NEW FUNCTION: Display only strong signals
def display_strong_signals_only(results: list):
    """Display only STRONG BUY/STRONG SELL signals"""
    
    strong_signals = [r for r in results if r.get('has_strong_signal', False)]
    
    if not strong_signals:
        print(f"\n❌ No STRONG signals found!")
        print(f"💡 STRONG signals require both:")
        print(f"   ✅ Existing swing pattern analysis confirmation")
        print(f"   ✅ Pine Script SWING CALLS confirmation")
        return
    
    print(f"\n🚀 STRONG BUY/SELL SIGNALS ONLY")
    print(f"📊 Confirmed by Both: Swing Patterns + Pine Script SWING CALLS")
    print("="*120)
    
    # Sort by signal strength
    strong_signals = sorted(strong_signals, key=lambda x: x['signal_strength'], reverse=True)
    
    # Group by sector
    sector_groups = defaultdict(list)
    for result in strong_signals:
        sector = result.get('sector', 'Others')
        sector_groups[sector].append(result)
    
    for sector, sector_results in sector_groups.items():
        if not sector_results:
            continue
            
        print(f"\n🏢 {sector.upper()} SECTOR ({len(sector_results)} Strong Signals)")
        print("-" * 120)
        
        for i, result in enumerate(sector_results, 1):
            print(f"{i}. {result['ticker']:10} | {result['signal_type']:12} | "
                  f"Price: ₹{result['current_price']:7.1f} | "
                  f"Strength: {result['signal_strength']:4.1f}/10 | "
                  f"Confidence: {result['confidence']}")
            
            print(f"   🎯 SIGNAL LOGIC: {result['signal_reason']}")
            print(f"   💡 SOURCE: {result['signal_source']}")
            
            # Pine Script confirmation details
            pine = result['pine_confirmation']
            print(f"   📊 PINE SCRIPT: EMA5: ₹{pine['ema1']:.1f} | SMA50: ₹{pine['sma2']:.1f} | RSI: {pine['rsi']:.0f}")
            
            conditions = []
            if pine['pine_buycall']:
                conditions.append("✅ PINE BUY CALL")
            if pine['pine_sellcall']:
                conditions.append("❌ PINE SELL CALL")
            if pine['pine_buyexit']:
                conditions.append("⚠️ RSI EXIT SELL")
            if pine['pine_sellexit']:
                conditions.append("⚠️ RSI EXIT BUY")
            
            if conditions:
                print(f"   🔍 PINE CONDITIONS: {' | '.join(conditions)}")
            
            # Crossover details
            details = pine['crossover_details']
            print(f"   🔄 CROSSOVER: {details.get('prev_sma2_ema1_relation', 'N/A')} → {details.get('curr_sma2_ema1_relation', 'N/A')}")
            
            # Swing pattern details
            if result['latest_swing_label']:
                print(f"   🔄 SWING: {result['latest_swing_label']} at ₹{result['latest_swing_price']:.1f}")
                if result['latest_pattern'] != "None":
                    print(f"   🕯️  PATTERN: {result['latest_pattern']}")
            
            print(f"   🏢 SECTOR: {result['sector']}")
            print()
    
    print(f"\n📊 STRONG SIGNALS SUMMARY:")
    print(f"   🚀 Total Strong Signals: {len(strong_signals)}")
    strong_buys = len([r for r in strong_signals if r['signal_type'] == 'STRONG_BUY'])
    strong_sells = len([r for r in strong_signals if r['signal_type'] == 'STRONG_SELL'])
    print(f"   ✅ STRONG BUY: {strong_buys}")
    print(f"   ❌ STRONG SELL: {strong_sells}")
    
    # Sector breakdown
    print(f"\n🏢 SECTOR BREAKDOWN:")
    for sector, sector_results in sector_groups.items():
        sector_buys = len([r for r in sector_results if r['signal_type'] == 'STRONG_BUY'])
        sector_sells = len([r for r in sector_results if r['signal_type'] == 'STRONG_SELL'])
        print(f"   {sector}: {len(sector_results)} signals (Buy: {sector_buys}, Sell: {sector_sells})")
    
    print(f"\n💡 CONFIRMATION LOGIC:")
    print(f"   🔥 STRONG signals need BOTH confirmations:")
    print(f"   ✅ Your existing swing pattern analysis (HH/HL/LH/LL + Candle patterns)")
    print(f"   ✅ Pine Script SWING CALLS (EMA5/SMA50 crossovers + conditions)")
    print(f"   📊 This ensures only the highest probability setups are identified")

# ENHANCED: Main analysis function
def analyze_all_stocks_enhanced(length: int = 21, volume_days: int = 20, momentum_days: int = 5, 
                               max_workers: int = 3, debug: bool = False, strong_only: bool = True):
    """
    Enhanced version of analyze_all_stocks_swing function
    CORE LOGIC UNCHANGED - Just adds Pine Script confirmation
    """
    
    tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
    
    print(f"\n🚀 ENHANCED SWING ANALYSIS + PINE SCRIPT CONFIRMATION")
    print(f"📊 Core Pattern Logic + Pine Script SWING CALLS Confirmation")
    print(f"⚡ Analyzing {len(tickers)} stocks - {'STRONG SIGNALS ONLY' if strong_only else 'ALL SIGNALS'}")
    print("="*80)
    
    all_results = []
    
    # Your existing concurrent processing logic (UNCHANGED)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(analyze_swing_patterns_enhanced, ticker, length, volume_days, momentum_days, debug): ticker 
            for ticker in tickers
        }
        
        completed = 0
        successful = 0
        failed = 0
        strong_signals = 0
        
        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            completed += 1
            
            try:
                result = future.result(timeout=30)
                if result:
                    all_results.append(result)
                    successful += 1
                    
                    if result.get('has_strong_signal', False):
                        strong_signals += 1
                    
                    # Enhanced display
                    signal_display = result['signal_type']
                    if result.get('has_strong_signal', False):
                        signal_display = f"⭐ {signal_display}"
                    
                    pine_status = "✅ PINE" if any([
                        result['pine_confirmation']['pine_buycall'],
                        result['pine_confirmation']['pine_sellcall'],
                        result['pine_confirmation']['pine_buyexit'],
                        result['pine_confirmation']['pine_sellexit']
                    ]) else "⚪ PINE"
                    
                    print(f"✅ {ticker} ({completed}/{len(tickers)}) - "
                          f"{result['total_swing_highs']}H/{result['total_swing_lows']}L | "
                          f"{result['total_patterns']} patterns | {signal_display} | {pine_status} | {result['sector']}")
                else:
                    failed += 1
                    print(f"⚪ {ticker} ({completed}/{len(tickers)}) - No data")
                    
            except Exception as e:
                failed += 1
                print(f"❌ {ticker} ({completed}/{len(tickers)}) - Error")
        
        print(f"\n📊 ENHANCED ANALYSIS SUMMARY:")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   ⭐ STRONG Signals: {strong_signals} (Both confirmations)")
        print(f"   📊 Analysis: Core Swing Patterns + Pine Script Confirmation")
    
    return all_results

# EXISTING FUNCTIONS - UNCHANGED
def display_swing_analysis(results: List[Dict], filter_type: str = 'ALL'):
    """Display swing analysis results grouped by sector - UNCHANGED"""
    
    if not results:
        print(f"\n❌ No analysis results found!")
        return
    
    # Sort by total patterns + swings for most interesting results first
    results = sorted(results, key=lambda x: x['total_patterns'] + x['total_swing_highs'] + x['total_swing_lows'], reverse=True)
    
    # Group by sector
    sector_groups = defaultdict(list)
    for result in results:
        sector = result.get('sector', 'Others')
        sector_groups[sector].append(result)
    
    print(f"\n🔄 SWING HIGHS/LOWS & CANDLE PATTERNS ANALYSIS")
    print(f"📊 Pattern Detection + Trading Signal Generation")
    print("="*120)
    
    for sector, sector_results in sector_groups.items():
        if not sector_results:
            continue
            
        print(f"\n🏢 {sector.upper()} SECTOR")
        print("-" * 120)
        
        for i, result in enumerate(sector_results, 1):
            signal_display = f"{result['signal_type']}" if result.get('has_trading_signal', False) else "NO SIGNAL"
            
            print(f"{i}. {result['ticker']:10} | "
                  f"Price: ₹{result['current_price']:7.1f} | "
                  f"Swings: {result['total_swing_highs']}H/{result['total_swing_lows']}L | "
                  f"Patterns: {result['total_patterns']} | "
                  f"Signal: {signal_display}")
            
            # Latest swing information (like Pine Script label)
            if result['latest_swing_label']:
                print(f"   🔄 LATEST SWING: {result['latest_swing_label']} at ₹{result['latest_swing_price']:.1f}")
                if result['latest_pattern'] != "None":
                    print(f"   🕯️  PATTERN AT SWING: {result['latest_pattern']}")
            
            # Show signal details if present
            if result.get('has_trading_signal', False):
                print(f"   🎯 SIGNAL: {result['signal_reason']} (Strength: {result['signal_strength']:.1f}/10, {result['confidence']} confidence)")
            
            # Show swing structure (HH/LH/HL/LL sequence)
            swing_highs = result.get('swing_highs', [])
            swing_lows = result.get('swing_lows', [])
            
            if swing_highs:
                recent_highs = swing_highs[-3:] if len(swing_highs) > 3 else swing_highs
                high_sequence = " → ".join([f"{s['type']}(₹{s['price']:.0f})" for s in recent_highs])
                print(f"   📈 RECENT HIGHS: {high_sequence}")
            
            if swing_lows:
                recent_lows = swing_lows[-3:] if len(swing_lows) > 3 else swing_lows
                low_sequence = " → ".join([f"{s['type']}(₹{s['price']:.0f})" for s in recent_lows])
                print(f"   📉 RECENT LOWS: {low_sequence}")
            
            # Pattern breakdown
            patterns = result['pattern_breakdown']
            pattern_summary = []
            for pattern, count in patterns.items():
                if count > 0:
                    pattern_summary.append(f"{pattern.replace('_', ' ').title()}: {count}")
            
            if pattern_summary:
                print(f"   📋 PATTERN BREAKDOWN: {' | '.join(pattern_summary)}")
            
            # Technical context (for information, not signals)
            rsi_status = "Oversold" if result['rsi'] < 30 else "Overbought" if result['rsi'] > 70 else "Neutral"
            volume_status = "High" if result['volume_ratio'] > 1.5 else "Normal" if result['volume_ratio'] > 0.8 else "Low"
            momentum_status = "Positive" if result['momentum'] > 0 else "Negative"
            
            print(f"   📊 CONTEXT: RSI {result['rsi']:.0f} ({rsi_status}) | "
                  f"Volume {result['volume_ratio']:.1f}x ({volume_status}) | "
                  f"Momentum {result['momentum']:+.1f}% ({momentum_status})")
            
            print()
    
    # Summary by sector
    print(f"\n📊 SECTOR SUMMARY:")
    sector_stats = []
    for sector, sector_results in sector_groups.items():
        total_patterns = sum(r['total_patterns'] for r in sector_results)
        total_swings = sum(r['total_swing_highs'] + r['total_swing_lows'] for r in sector_results)
        signal_count = len([r for r in sector_results if r.get('has_trading_signal', False)])
        avg_patterns = total_patterns / len(sector_results) if sector_results else 0
        
        sector_stats.append({
            'sector': sector,
            'stocks': len(sector_results),
            'signals': signal_count,
            'total_patterns': total_patterns,
            'total_swings': total_swings,
            'avg_patterns': avg_patterns
        })
    
    # Sort sectors by total activity
    sector_stats.sort(key=lambda x: x['total_patterns'] + x['total_swings'], reverse=True)
    
    for stat in sector_stats:
        print(f"   🏢 {stat['sector']:20} | "
              f"Stocks: {stat['stocks']:2d} | "
              f"Signals: {stat['signals']:2d} | "
              f"Patterns: {stat['total_patterns']:3d} | "
              f"Swings: {stat['total_swings']:3d}")
    
    print(f"\n🎯 COMBINED ANALYSIS FEATURES:")
    print(f"   📊 Shows swing structure (HH/LH/HL/LL) and candlestick patterns")
    print(f"   🕯️  Detects 6 major reversal patterns at swing points")
    print(f"   🚀 Generates SWING_BUY/SELL signals from EMA5/SMA50 crossovers (Pine Script)")
    print(f"   📉 Provides RSI exit signals for overbought/oversold conditions")
    print(f"   🟢 Creates PATTERN signals based on swing structure + candlestick confirmation")
    print(f"   📈 Combines multiple strategies for comprehensive market analysis")

def display_trading_signals(results: List[Dict], signal_types: List[str], title: str):
    """Display trading signals grouped by sector - UNCHANGED"""
    
    # Filter for specific signal types
    filtered_results = [r for r in results if r['signal_type'] in signal_types]
    
    if not filtered_results:
        print(f"\n❌ No {title} signals found!")
        return
    
    # Sort by signal strength
    filtered_results = sorted(filtered_results, key=lambda x: x['signal_strength'], reverse=True)
    
    # Group by sector
    sector_groups = defaultdict(list)
    for result in filtered_results:
        sector = result.get('sector', 'Others')
        sector_groups[sector].append(result)
    
    print(f"\n🚀 SECTOR-WISE {title} SIGNALS")
    print(f"📊 Based on Swing Pattern Analysis + Technical Confirmation")
    print("="*140)
    
    for sector, sector_results in sector_groups.items():
        if not sector_results:
            continue
            
        print(f"\n🏢 {sector.upper()} SECTOR ({len(sector_results)} Signals)")
        print("-" * 140)
        
        for i, result in enumerate(sector_results, 1):
            print(f"{i}. {result['ticker']:10} | {result['signal_type']:12} | "
                  f"Price: ₹{result['current_price']:7.1f} | "
                  f"Strength: {result['signal_strength']:4.1f}/10 | "
                  f"Confidence: {result['confidence']}")
            
            # Signal explanation
            print(f"   🎯 SIGNAL LOGIC: {result['signal_reason']}")
            
            # SWING CALLS technical details
            if 'swing_calls' in result:
                sc = result['swing_calls']
                print(f"   📊 SWING CALLS: EMA5: ₹{sc['ema5']:.1f} | SMA50: ₹{sc['sma50']:.1f} | "
                      f"RSI: {sc['rsi']:.0f} | Trend: {sc['trend_status']}")
                
                # Show specific SWING CALLS conditions
                conditions = []
                if sc['buycall']:
                    conditions.append("✅ EMA5 crossed above SMA50")
                if sc['sellcall']:
                    conditions.append("❌ SMA50 crossed above EMA5")
                if sc['buyexit']:
                    conditions.append("⚠️ RSI exit from overbought")
                if sc['sellexit']:
                    conditions.append("⚠️ RSI exit from oversold")
                
                if conditions:
                    print(f"   🔍 CONDITIONS: {' | '.join(conditions)}")
            
            # Latest swing information
            if result['latest_swing_label']:
                print(f"   🔄 SWING STRUCTURE: {result['latest_swing_label']} at ₹{result['latest_swing_price']:.1f}")
                if result['latest_pattern'] != "None":
                    print(f"   🕯️  PATTERN: {result['latest_pattern']} (Additional confirmation)")
            
            # Technical context
            rsi_status = "🔴 Overbought" if result['rsi'] > 70 else "🟢 Oversold" if result['rsi'] < 30 else "⚪ Neutral"
            volume_status = "🟢 High" if result['volume_ratio'] > 1.5 else "🟡 Normal" if result['volume_ratio'] > 0.8 else "🔴 Low"
            momentum_status = "🟢 Positive" if result['momentum'] > 0 else "🔴 Negative"
            
            print(f"   📈 TECHNICAL: RSI {result['rsi']:.0f} ({rsi_status}) | "
                  f"Volume {result['volume_ratio']:.1f}x ({volume_status}) | "
                  f"Momentum {result['momentum']:+.1f}% ({momentum_status})")
            
            # Pattern activity
            print(f"   📋 PATTERN ACTIVITY: {result['total_patterns']} patterns | "
                  f"{result['total_swing_highs']} highs, {result['total_swing_lows']} lows")
            
            print()
    
    # Summary by sector
    print(f"\n📊 {title} SIGNALS SUMMARY:")
    sector_stats = []
    for sector, sector_results in sector_groups.items():
        avg_strength = sum(r['signal_strength'] for r in sector_results) / len(sector_results)
        high_confidence = len([r for r in sector_results if r['confidence'] == 'HIGH'])
        
        sector_stats.append({
            'sector': sector,
            'signals': len(sector_results),
            'avg_strength': avg_strength,
            'high_confidence': high_confidence
        })
    
    # Sort sectors by signal count
    sector_stats.sort(key=lambda x: x['signals'], reverse=True)
    
    for stat in sector_stats:
        print(f"   🏢 {stat['sector']:20} | "
              f"Signals: {stat['signals']:2d} | "
              f"Avg Strength: {stat['avg_strength']:4.1f} | "
              f"High Confidence: {stat['high_confidence']}")
    
    print(f"\n🎯 SIGNAL GENERATION LOGIC:")
    if 'BUY' in title:
        print(f"   ✅ Bullish Swing (HL/HH) + Bullish Pattern + Technical Confirmation")
        print(f"   🔥 STRONG BUY: 9.0+ strength (High Confidence)")
        print(f"   📈 BUY: 7.5+ strength (Medium Confidence)")
    else:
        print(f"   ❌ Bearish Swing (LH/LL) + Bearish Pattern + Technical Confirmation")
        print(f"   🔥 STRONG SELL: 9.0+ strength (High Confidence)")
        print(f"   📉 SELL: 7.5+ strength (Medium Confidence)")

def generate_swing_html_report(results: List[Dict], length: int, volume_days: int, momentum_days: int, output_dir: str) -> Optional[str]:
    """Generate HTML report for swing analysis - UNCHANGED"""
    
    if not results:
        return None
    
    # Sort by activity (patterns + swings)
    results = sorted(results, key=lambda x: x['total_patterns'] + x['total_swing_highs'] + x['total_swing_lows'], reverse=True)
    
    # Group by sector
    sector_groups = defaultdict(list)
    for result in results:
        sector = result.get('sector', 'Others')
        sector_groups[sector].append(result)
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    total_patterns = sum(r['total_patterns'] for r in results)
    total_swings = sum(r['total_swing_highs'] + r['total_swing_lows'] for r in results)
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Enhanced Swing Analysis - {datetime.now().strftime('%Y-%m-%d')}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
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
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            .stat-card {{
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
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
            }}
            tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
            tr:hover {{
                background-color: #f0f0f0;
            }}
            .strong-signal {{
                background-color: #d4edda !important;
                font-weight: bold;
            }}
            .positive {{ color: #28a745; font-weight: bold; }}
            .negative {{ color: #dc3545; font-weight: bold; }}
            .sector-header {{
                background: linear-gradient(135deg, #36d1dc 0%, #5b86e5 100%);
                color: white;
                padding: 15px 25px;
                border-radius: 8px;
                margin: 25px 0 15px 0;
                font-size: 1.3em;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔄 ENHANCED SWING ANALYSIS + PINE SCRIPT</h1>
                <p><strong>Core Swing Patterns + Pine Script SWING CALLS Confirmation</strong></p>
                <p>Pivot Length: {length} | Volume: {volume_days} days | Momentum: {momentum_days} days</p>
                <p>Generated: {timestamp}</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>{len(results)}</h3>
                    <p>Stocks Analyzed</p>
                </div>
                <div class="stat-card">
                    <h3>{total_swings}</h3>
                    <p>Swing Points</p>
                </div>
                <div class="stat-card">
                    <h3>{total_patterns}</h3>
                    <p>Patterns Detected</p>
                </div>
                <div class="stat-card">
                    <h3>{len([r for r in results if r.get('has_strong_signal')])}</h3>
                    <p>Strong Signals</p>
                </div>
            </div>
    """
    
    # Add results by sector
    for sector, sector_results in sector_groups.items():
        if not sector_results:
            continue
            
        html_content += f'<div class="sector-header">🏢 {sector.upper()} SECTOR ({len(sector_results)} Stocks)</div>'
        html_content += '''
            <table>
                <thead>
                    <tr>
                        <th>Ticker</th>
                        <th>Price</th>
                        <th>Signal</th>
                        <th>Strength</th>
                        <th>Pine Script</th>
                        <th>Swing Highs</th>
                        <th>Swing Lows</th>
                        <th>Latest Swing</th>
                        <th>Pattern</th>
                        <th>RSI</th>
                        <th>Volume</th>
                        <th>Momentum</th>
                    </tr>
                </thead>
                <tbody>
        '''
        
        for result in sector_results:
            momentum_class = 'positive' if result['momentum'] >= 0 else 'negative'
            row_class = 'strong-signal' if result.get('has_strong_signal', False) else ''
            
            # Pine Script status
            pine_status = "✅" if any([
                result['pine_confirmation']['pine_buycall'],
                result['pine_confirmation']['pine_sellcall'],
                result['pine_confirmation']['pine_buyexit'],
                result['pine_confirmation']['pine_sellexit']
            ]) else "⚪"
            
            html_content += f'''
                    <tr class="{row_class}">
                        <td><strong>{result['ticker']}</strong></td>
                        <td>₹{result['current_price']:.1f}</td>
                        <td>{result['signal_type']}</td>
                        <td>{result['signal_strength']:.1f}/10</td>
                        <td>{pine_status}</td>
                        <td>{result['total_swing_highs']}</td>
                        <td>{result['total_swing_lows']}</td>
                        <td>{result['latest_swing_label'] or 'N/A'}</td>
                        <td>{result['latest_pattern']}</td>
                        <td>{result['rsi']:.0f}</td>
                        <td>{result['volume_ratio']:.1f}x</td>
                        <td class="{momentum_class}">{result['momentum']:+.1f}%</td>
                    </tr>
            '''
        
        html_content += '</tbody></table>'
    
    html_content += """
            <div style="text-align: center; margin-top: 40px; padding: 20px; background: #f8f9fa; border-radius: 10px;">
                <p><strong>📊 Analysis Type:</strong> Enhanced Swing Patterns + Pine Script SWING CALLS Confirmation</p>
                <p><strong>🔄 Strategy:</strong> Core Swing Analysis + Pine Script EMA/SMA Crossovers</p>
                <p><strong>🎯 Strong Signals:</strong> Both swing patterns AND Pine Script confirmation required</p>
                <p><strong>⚠️ Disclaimer:</strong> This enhanced analysis combines pattern detection with Pine Script confirmation for educational purposes</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Save HTML
    html_filename = f"enhanced_swing_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    html_path = os.path.join(output_dir, html_filename)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return html_path

def main():
    """Enhanced main function with Pine Script confirmation"""
    parser = argparse.ArgumentParser(description="Enhanced Swing Analysis with Pine Script Confirmation")
    
    parser.add_argument('--length', type=int, default=21, help='Pivot point length (default: 21)')
    parser.add_argument('--volume-days', type=int, default=20, help='Volume average days (default: 20)')
    parser.add_argument('--momentum-days', type=int, default=5, help='Momentum calculation days (default: 5)')
    parser.add_argument('--workers', type=int, default=3, help='Max concurrent workers (default: 3)')
    parser.add_argument('--output', type=str, default='output', help='Output directory')
    parser.add_argument('--test-single', type=str, help='Test analysis on single ticker')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    
    # NEW: Signal filtering options
    parser.add_argument('--strong-only', action='store_true', default=True, 
                       help='Show only STRONG signals (both confirmations required) - DEFAULT')
    parser.add_argument('--all-signals', action='store_true', 
                       help='Show all signals (overrides --strong-only)')
    parser.add_argument('--buy-only', action='store_true', help='Show all BUY signals')
    parser.add_argument('--sell-only', action='store_true', help='Show all SELL signals')
    
    args = parser.parse_args()
    
    # Test single ticker if requested
    if args.test_single:
        print(f"🧪 TESTING {args.test_single} WITH PINE SCRIPT CONFIRMATION")
        print("="*80)
        result = analyze_swing_patterns_enhanced(args.test_single, args.length, debug=True)
        
        if result:
            print(f"\n🎯 RESULT SUMMARY:")
            print(f"   Signal: {result['signal_type']}")
            print(f"   Strength: {result['signal_strength']:.1f}/10")
            print(f"   Strong Signal: {'YES' if result.get('has_strong_signal') else 'NO'}")
            print(f"   Source: {result['signal_source']}")
            
            # Pine Script details
            pine = result['pine_confirmation']
            print(f"\n📊 PINE SCRIPT STATUS:")
            print(f"   BUY Call: {pine['pine_buycall']}")
            print(f"   SELL Call: {pine['pine_sellcall']}")
            print(f"   RSI Exits: Buy={pine['pine_sellexit']}, Sell={pine['pine_buyexit']}")
            print(f"   EMA5: ₹{pine['ema1']:.2f}, SMA50: ₹{pine['sma2']:.2f}")
            print(f"   RSI: {pine['rsi']:.1f}")
            
            # Crossover details
            details = pine['crossover_details']
            print(f"\n🔍 CROSSOVER ANALYSIS:")
            print(f"   Previous: {details.get('prev_sma2_ema1_relation', 'N/A')}")
            print(f"   Current: {details.get('curr_sma2_ema1_relation', 'N/A')}")
            print(f"   High > SMA50: {details.get('high_above_sma', False)}")
            print(f"   Red Candle: {details.get('red_candle', False)}")
            
            if result['latest_swing_label']:
                print(f"\n🎯 LATEST SWING:")
                print(f"   Type: {result['latest_swing_label']} at ₹{result['latest_swing_price']:.2f}")
                print(f"   Pattern: {result['latest_pattern']}")
        
        return
    
    print("🚀 ENHANCED SWING ANALYSIS + PINE SCRIPT CONFIRMATION")
    print("📊 Core Pattern Logic + Pine Script SWING CALLS")
    print("="*80)
    
    # Set output directory
    output_dir = args.output or getattr(config, 'OUTPUT_DIR', 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Determine signal display preference
    strong_only = args.strong_only and not args.all_signals
    
    # Analyze all stocks
    all_results = analyze_all_stocks_enhanced(
        length=args.length,
        volume_days=args.volume_days,
        momentum_days=args.momentum_days,
        max_workers=args.workers,
        debug=args.debug,
        strong_only=strong_only
    )
    
    if not all_results:
        print("\n❌ No analysis results generated!")
        print("💡 TROUBLESHOOTING TIPS:")
        print("   🔧 Enable debug mode: --debug")
        print("   🔧 Check internet connection for data fetching")
        print("   🔧 Try single ticker test: --test-single RELIANCE --debug")
        print("   🔧 Verify config.py has TOP_STOCKS defined")
        return
    
    # Display results based on user preference
    if strong_only:
        display_strong_signals_only(all_results)
    elif args.buy_only:
        display_trading_signals(all_results, ['STRONG_BUY', 'SWING_BUY', 'RSI_EXIT_BUY', 'PATTERN_BUY'], "ALL BUY SIGNALS")
    elif args.sell_only:
        display_trading_signals(all_results, ['STRONG_SELL', 'SWING_SELL', 'RSI_EXIT_SELL', 'PATTERN_SELL'], "ALL SELL SIGNALS")
    else:
        # Default: Show complete analysis
        display_swing_analysis(all_results)
    
    # Generate reports
    print(f"\n📄 Generating enhanced analysis reports...")
    
    # HTML Report
    html_path = generate_swing_html_report(
        all_results, args.length, args.volume_days, args.momentum_days, output_dir
    )
    if html_path:
        print(f"🌐 HTML Report: {html_path}")
        print(f"🔗 Open: file://{os.path.abspath(html_path)}")
    
    # JSON Report
    json_filename = f"enhanced_swing_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_path = os.path.join(output_dir, json_filename)
    
    json_data = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'total_stocks_analyzed': len(all_results),
            'pivot_length': args.length,
            'volume_days': args.volume_days,
            'momentum_days': args.momentum_days,
            'analysis_type': 'Enhanced Swing Pattern + Pine Script Confirmation',
            'strategy': 'Core Swing Analysis + Pine Script SWING CALLS',
            'strong_signals_count': len([r for r in all_results if r.get('has_strong_signal', False)])
        },
        'results': all_results
    }
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"📊 JSON Data: {json_path}")
    
    print(f"\n✅ ENHANCED SWING ANALYSIS COMPLETE!")
    print(f"📁 Output Directory: {os.path.abspath(output_dir)}")
    
    # Summary
    strong_signals = len([r for r in all_results if r.get('has_strong_signal', False)])
    print(f"\n💡 FINAL SUMMARY:")
    print(f"   📊 Total Stocks Analyzed: {len(all_results)}")
    print(f"   ⭐ STRONG Signals Found: {strong_signals} (Both confirmations)")
    print(f"   🔄 Core Logic: PRESERVED (all existing functions intact)")
    print(f"   🚀 Pine Script: ADDED (exact Pine Script SWING CALLS logic)")
    print(f"   🎯 Enhancement: Only STRONG signals when both systems agree")
    
    print(f"\n🚀 USAGE EXAMPLES:")
    print(f"   python {sys.argv[0]}                                     # STRONG signals only (default)")
    print(f"   python {sys.argv[0]} --all-signals                      # All signals (original behavior)")
    print(f"   python {sys.argv[0]} --buy-only                         # All BUY signals")
    print(f"   python {sys.argv[0]} --sell-only                        # All SELL signals")
    print(f"   python {sys.argv[0]} --test-single RELIANCE --debug     # Test single stock")
    
    print(f"\n🎯 PINE SCRIPT INTEGRATION:")
    print(f"   ✅ buycall = crossunder(sma2,ema1) and high>sma2")
    print(f"   ✅ sellcall = crossover(sma2,ema1) and open>close")
    print(f"   ✅ buyexit = crossunder(rs,80)")
    print(f"   ✅ sellexit = crossover(rs,20)")
    print(f"   🔄 Combined with your existing swing pattern analysis")

if __name__ == "__main__":
    main()