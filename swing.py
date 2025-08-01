#!/usr/bin/env python
# enhanced_swing_sectorwise.py - Ultimate Ichimoku Strategy with Sector-wise Analysis and Full Entry Logic

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

# SECTOR MAPPING FOR INDIAN STOCKS
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
    
    # Fast Moving Consumer Goods (FMCG)
    'HINDUNILVR': 'FMCG', 'ITC': 'FMCG', 'NESTLEIND': 'FMCG', 'BRITANNIA': 'FMCG',
    'DABUR': 'FMCG', 'MARICO': 'FMCG', 'GODREJCP': 'FMCG', 'COLPAL': 'FMCG',
    'PGHH': 'FMCG', 'EMAMILTD': 'FMCG', 'UBL': 'FMCG', 'VBL': 'FMCG',
    
    # Pharmaceuticals
    'SUNPHARMA': 'Pharmaceuticals', 'DRREDDY': 'Pharmaceuticals', 'CIPLA': 'Pharmaceuticals',
    'DIVISLAB': 'Pharmaceuticals', 'LUPIN': 'Pharmaceuticals', 'BIOCON': 'Pharmaceuticals',
    'TORNTPHARM': 'Pharmaceuticals', 'AUROPHARMA': 'Pharmaceuticals', 'CADILAHC': 'Pharmaceuticals',
    'GLENMARK': 'Pharmaceuticals', 'ALKEM': 'Pharmaceuticals', 'LALPATHLAB': 'Pharmaceuticals',
    
    # Automotive
    'MARUTI': 'Automotive', 'M&M': 'Automotive', 'TATAMOTORS': 'Automotive', 'BAJAJ-AUTO': 'Automotive',
    'HEROMOTOCO': 'Automotive', 'EICHERMOT': 'Automotive', 'APOLLOTYRE': 'Automotive',
    'MRF': 'Automotive', 'BALKRISIND': 'Automotive', 'ESCORTS': 'Automotive',
    'ASHOKLEY': 'Automotive', 'TVSMOTOR': 'Automotive', 'BOSCHLTD': 'Automotive',
    
    # Metals & Mining
    'TATASTEEL': 'Metals & Mining', 'JSWSTEEL': 'Metals & Mining', 'HINDALCO': 'Metals & Mining',
    'VEDL': 'Metals & Mining', 'COALINDIA': 'Metals & Mining', 'SAIL': 'Metals & Mining',
    'JINDALSTEL': 'Metals & Mining', 'NMDC': 'Metals & Mining', 'MOIL': 'Metals & Mining',
    'NATIONALUM': 'Metals & Mining', 'HINDZINC': 'Metals & Mining',
    
    # Cement
    'ULTRACEMCO': 'Cement', 'GRASIM': 'Cement', 'SHREECEM': 'Cement', 'ACC': 'Cement',
    'AMBUJACEML': 'Cement', 'JKCEMENT': 'Cement', 'RAMCOCEM': 'Cement', 'HEIDELBERG': 'Cement',
    'DALMIACEMT': 'Cement', 'INDIACEM': 'Cement',
    
    # Paints & Chemicals
    'ASIANPAINT': 'Paints & Chemicals', 'BERGER': 'Paints & Chemicals', 'KANSAINER': 'Paints & Chemicals',
    'AKZOINDIA': 'Paints & Chemicals', 'PIDILITIND': 'Paints & Chemicals',
    'UPL': 'Chemicals', 'SRF': 'Chemicals', 'AARTI': 'Chemicals', 'DEEPAKNTR': 'Chemicals',
    'TATACHEM': 'Chemicals', 'GNFC': 'Chemicals', 'CHAMBLFERT': 'Chemicals',
    
    # Capital Goods & Engineering
    'LT': 'Capital Goods', 'ABB': 'Capital Goods', 'SIEMENS': 'Capital Goods', 'BHEL': 'Capital Goods',
    'CUMMINSIND': 'Capital Goods', 'THERMAX': 'Capital Goods', 'KEI': 'Capital Goods',
    'VOLTAS': 'Capital Goods', 'CROMPTON': 'Capital Goods', 'HAVELLS': 'Capital Goods',
    
    # Power & Utilities
    'POWERGRID': 'Power', 'NTPC': 'Power', 'ADANIPOWER': 'Power', 'TATAPOWER': 'Power',
    'JSPL': 'Power', 'ADANIGREEN': 'Power', 'SUZLON': 'Power', 'NHPC': 'Power',
    
    # Telecommunications
    'BHARTIARTL': 'Telecom', 'IDEA': 'Telecom', 'RJIO': 'Telecom', 'RCOM': 'Telecom',
    
    # Consumer Durables
    'TITAN': 'Consumer Durables', 'BAJAJELEEC': 'Consumer Durables', 'WHIRLPOOL': 'Consumer Durables',
    'BLUESTARCO': 'Consumer Durables', 'AMBER': 'Consumer Durables', 'DIXON': 'Consumer Durables',
    
    # Textiles
    'RAYMOND': 'Textiles', 'ADITYA': 'Textiles', 'WELSPUNIND': 'Textiles', 'VARDHMAN': 'Textiles',
    'TRIDENT': 'Textiles', 'PAGES': 'Textiles',
    
    # Real Estate
    'DLF': 'Real Estate', 'GODREJPROP': 'Real Estate', 'OBEROIRLTY': 'Real Estate', 'BRIGADE': 'Real Estate',
    'SOBHA': 'Real Estate', 'PRESTIGE': 'Real Estate',
    
    # Airlines
    'INDIGO': 'Airlines', 'SPICEJET': 'Airlines',
    
    # Media & Entertainment
    'ZEEL': 'Media', 'SUNTV': 'Media', 'NETWORK18': 'Media', 'DISHTV': 'Media',
    
    # Diversified
    'ITC': 'Diversified', 'RELIANCE': 'Diversified', 'ADANIGROUP': 'Diversified', 'TATA': 'Diversified'
}

def get_sector(ticker):
    """Get sector for a ticker"""
    return SECTOR_MAPPING.get(ticker, 'Others')

# CUSTOMIZABLE ICHIMOKU CONDITIONS
class IchimokuConfig:
    # Long Entry Conditions (can enable/disable individually)
    LONG_CONDITIONS = {
        'conversion_crosses_base': True,      # Tenkan crosses above Kijun
        'conversion_above_base': False,       # Tenkan > Kijun  
        'positive_cloud': True,               # Span A > Span B
        'price_above_cloud': True,            # Price > Cloud
        'positive_chikou': True,              # Chikou > Price (26 bars ago)
        'price_above_conversion': True,       # Price > Tenkan
    }
    
    # Short Entry Conditions
    SHORT_CONDITIONS = {
        'base_crosses_conversion': True,      # Kijun crosses above Tenkan
        'base_above_conversion': False,       # Kijun > Tenkan
        'negative_cloud': True,               # Span B > Span A
        'price_below_cloud': True,            # Price < Cloud
        'negative_chikou': True,              # Chikou < Price (26 bars ago)
        'price_below_base': True,             # Price < Kijun
    }
    
    # Minimum conditions required (flexibility setting)
    MIN_LONG_CONDITIONS = 3    # Need at least 3 out of 6 conditions
    MIN_SHORT_CONDITIONS = 3   # Need at least 3 out of 6 conditions

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

def enhanced_volume_confirmation(data, current_volume, lookback_days):
    """Enhanced volume analysis for breakout confirmation"""
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
    """Calculate volume and momentum using ONLY trading days"""
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

def detect_fractals(data, n=2):
    """Detect fractal highs and lows"""
    try:
        highs = data['High'].values
        lows = data['Low'].values
        
        fractal_highs = []
        fractal_lows = []
        
        for i in range(n, len(highs) - n):
            # Fractal high: current high is highest among surrounding n bars
            is_fractal_high = True
            for j in range(i - n, i + n + 1):
                if j != i and highs[j] >= highs[i]:
                    is_fractal_high = False
                    break
            
            if is_fractal_high:
                fractal_highs.append({'price': highs[i], 'index': i, 'strength': n})
            
            # Fractal low: current low is lowest among surrounding n bars
            is_fractal_low = True
            for j in range(i - n, i + n + 1):
                if j != i and lows[j] <= lows[i]:
                    is_fractal_low = False
                    break
            
            if is_fractal_low:
                fractal_lows.append({'price': lows[i], 'index': i, 'strength': n})
        
        return fractal_highs, fractal_lows
    except:
        return [], []

def detect_support_resistance_levels(data, current_price, lookback_bars=50):
    """Detect support and resistance levels using multiple methods"""
    try:
        if len(data) < lookback_bars:
            lookback_bars = len(data) - 1
        
        recent_data = data.iloc[-lookback_bars:]
        support_levels = []
        resistance_levels = []
        
        # 1. Fractal-based levels
        fractal_highs, fractal_lows = detect_fractals(recent_data, n=2)
        
        for fh in fractal_highs[-5:]:  # Last 5 fractal highs
            resistance_levels.append({
                'price': fh['price'],
                'type': f'Fractal High ({fh["strength"]})',
                'strength': 4
            })
        
        for fl in fractal_lows[-5:]:  # Last 5 fractal lows
            support_levels.append({
                'price': fl['price'],
                'type': f'Fractal Low ({fl["strength"]})',
                'strength': 4
            })
        
        # 2. Volume-based support/resistance
        volume_weighted_highs = []
        volume_weighted_lows = []
        
        for i in range(len(recent_data)):
            vol_weight = recent_data['Volume'].iloc[i]
            high_price = recent_data['High'].iloc[i]
            low_price = recent_data['Low'].iloc[i]
            
            volume_weighted_highs.append((high_price, vol_weight))
            volume_weighted_lows.append((low_price, vol_weight))
        
        # Sort by volume and take top levels
        volume_weighted_highs.sort(key=lambda x: x[1], reverse=True)
        volume_weighted_lows.sort(key=lambda x: x[1], reverse=True)
        
        for i, (price, vol) in enumerate(volume_weighted_highs[:3]):
            resistance_levels.append({
                'price': price,
                'type': 'Volume Resistance',
                'strength': 4
            })
        
        for i, (price, vol) in enumerate(volume_weighted_lows[:3]):
            support_levels.append({
                'price': price,
                'type': 'Volume Support',
                'strength': 4
            })
        
        # 3. Round number levels
        price_range = recent_data['High'].max() - recent_data['Low'].min()
        if price_range > 0:
            # Find round numbers within range
            min_price = recent_data['Low'].min()
            max_price = recent_data['High'].max()
            
            # Determine round number step based on price level
            if max_price > 1000:
                step = 50
            elif max_price > 100:
                step = 10
            else:
                step = 5
            
            round_levels = []
            start = int(min_price / step) * step
            end = int(max_price / step + 1) * step
            
            for level in range(start, end + step, step):
                if min_price <= level <= max_price:
                    round_levels.append(level)
            
            for level in round_levels:
                if level > current_price:
                    resistance_levels.append({
                        'price': level,
                        'type': 'Round Number',
                        'strength': 5
                    })
                elif level < current_price:
                    support_levels.append({
                        'price': level,
                        'type': 'Round Number',
                        'strength': 5
                    })
        
        # 4. Moving average levels
        if len(recent_data) >= 20:
            sma_20 = recent_data['Close'].rolling(window=20).mean().iloc[-1]
            if not pd.isna(sma_20):
                if sma_20 > current_price:
                    resistance_levels.append({
                        'price': sma_20,
                        'type': '20-SMA',
                        'strength': 3
                    })
                else:
                    support_levels.append({
                        'price': sma_20,
                        'type': '20-SMA',
                        'strength': 3
                    })
        
        # 5. Recent highs and lows
        if len(recent_data) >= 20:
            recent_high = recent_data['High'].rolling(window=20).max().iloc[-1]
            recent_low = recent_data['Low'].rolling(window=20).min().iloc[-1]
            
            resistance_levels.append({
                'price': recent_high,
                'type': '20-bar High',
                'strength': 3
            })
            
            support_levels.append({
                'price': recent_low,
                'type': '20-bar Low',
                'strength': 3
            })
        
        # Remove duplicates and sort
        support_levels = [dict(t) for t in {tuple(d.items()) for d in support_levels}]
        resistance_levels = [dict(t) for t in {tuple(d.items()) for d in resistance_levels}]
        
        support_levels.sort(key=lambda x: abs(x['price'] - current_price))
        resistance_levels.sort(key=lambda x: abs(x['price'] - current_price))
        
        return support_levels, resistance_levels
        
    except Exception as e:
        return [], []

def calculate_entry_price(signal_type, current_price, support_levels, resistance_levels):
    """Calculate precise entry price based on support/resistance levels with full logic"""
    try:
        entry_price = current_price
        entry_logic = "Market Price"
        full_entry_explanation = "No specific entry level detected"
        
        if 'BUY' in signal_type.upper():
            # For BUY signals: Find nearest resistance ABOVE current price
            relevant_resistances = [r for r in resistance_levels if r['price'] > current_price]
            
            if relevant_resistances:
                # Sort by distance from current price
                relevant_resistances.sort(key=lambda x: abs(x['price'] - current_price))
                nearest_resistance = relevant_resistances[0]
                
                # Entry price: slightly above resistance (0.2% buffer)
                buffer = nearest_resistance['price'] * 0.002
                entry_price = nearest_resistance['price'] + buffer
                
                entry_logic = f"Above {nearest_resistance['type']} ₹{nearest_resistance['price']:.1f}"
                
                # Full explanation
                full_entry_explanation = (
                    f"🔍 BUY Entry Logic: "
                    f"Detected {nearest_resistance['type']} at ₹{nearest_resistance['price']:.2f}. "
                    f"Entry at ₹{entry_price:.2f} = Resistance + 0.2% buffer "
                    f"(₹{nearest_resistance['price']:.2f} + ₹{buffer:.2f}). "
                    f"This confirms breakout above key resistance level with {nearest_resistance['strength']}/5 strength. "
                    f"Distance from current price: {abs(entry_price - current_price):.2f} ({((entry_price - current_price)/current_price)*100:+.2f}%)"
                )
            else:
                # No resistance found, use small buffer above current price
                buffer = current_price * 0.002
                entry_price = current_price + buffer
                entry_logic = "Above Current Price (No Resistance)"
                full_entry_explanation = (
                    f"🔍 BUY Entry Logic: "
                    f"No clear resistance level detected above current price ₹{current_price:.2f}. "
                    f"Entry at ₹{entry_price:.2f} = Current Price + 0.2% buffer (₹{buffer:.2f}). "
                    f"This provides minimal confirmation of upward momentum."
                )
        
        elif 'SELL' in signal_type.upper():
            # For SELL signals: Find nearest support BELOW current price
            relevant_supports = [s for s in support_levels if s['price'] < current_price]
            
            if relevant_supports:
                # Sort by distance from current price (closest first)
                relevant_supports.sort(key=lambda x: abs(x['price'] - current_price))
                nearest_support = relevant_supports[0]
                
                # Entry price: slightly below support (0.2% buffer)
                buffer = nearest_support['price'] * 0.002
                entry_price = nearest_support['price'] - buffer
                
                entry_logic = f"Below {nearest_support['type']} ₹{nearest_support['price']:.1f}"
                
                # Full explanation
                full_entry_explanation = (
                    f"🔍 SELL Entry Logic: "
                    f"Detected {nearest_support['type']} at ₹{nearest_support['price']:.2f}. "
                    f"Entry at ₹{entry_price:.2f} = Support - 0.2% buffer "
                    f"(₹{nearest_support['price']:.2f} - ₹{buffer:.2f}). "
                    f"This confirms breakdown below key support level with {nearest_support['strength']}/5 strength. "
                    f"Distance from current price: {abs(current_price - entry_price):.2f} ({((current_price - entry_price)/current_price)*100:+.2f}%)"
                )
            else:
                # No support found, use small buffer below current price
                buffer = current_price * 0.002
                entry_price = current_price - buffer
                entry_logic = "Below Current Price (No Support)"
                full_entry_explanation = (
                    f"🔍 SELL Entry Logic: "
                    f"No clear support level detected below current price ₹{current_price:.2f}. "
                    f"Entry at ₹{entry_price:.2f} = Current Price - 0.2% buffer (₹{buffer:.2f}). "
                    f"This provides minimal confirmation of downward momentum."
                )
        
        return round(entry_price, 2), entry_logic, full_entry_explanation
        
    except Exception as e:
        return current_price, "Market Price (Error)", f"Error calculating entry: {str(e)}"

def calculate_ichimoku_ultimate(data):
    """Calculate Ultimate Ichimoku components"""
    try:
        high = data['High']
        low = data['Low']
        close = data['Close']
        
        # Ichimoku parameters (customizable)
        conversion_period = 9     # Tenkan-sen
        base_period = 26         # Kijun-sen  
        leading_span_period = 52 # Senkou Span B
        displacement = 26        # Displacement for spans
        
        # Donchian calculation (high + low) / 2 for periods
        def donchian(series_high, series_low, period):
            return (series_high.rolling(period).max() + series_low.rolling(period).min()) / 2
        
        # Calculate Ichimoku lines
        conversion_line = donchian(high, low, conversion_period)  # Tenkan-sen
        base_line = donchian(high, low, base_period)              # Kijun-sen
        
        # Leading spans (projected forward)
        leading_span_a = ((conversion_line + base_line) / 2).shift(displacement)
        leading_span_b = donchian(high, low, leading_span_period).shift(displacement)
        
        # Lagging span (current close shifted back)
        lagging_span = close.shift(-displacement)
        
        # Cloud boundaries
        cloud_top = pd.concat([leading_span_a, leading_span_b], axis=1).max(axis=1)
        cloud_bottom = pd.concat([leading_span_a, leading_span_b], axis=1).min(axis=1)
        
        # Cloud color (positive when Span A > Span B)
        positive_cloud = leading_span_a > leading_span_b
        
        return {
            'conversion_line': conversion_line,
            'base_line': base_line,
            'leading_span_a': leading_span_a,
            'leading_span_b': leading_span_b,
            'lagging_span': lagging_span,
            'cloud_top': cloud_top,
            'cloud_bottom': cloud_bottom,
            'positive_cloud': positive_cloud,
            'displacement': displacement
        }
    except Exception as e:
        return None

def check_ichimoku_conditions(data, ichimoku, config=IchimokuConfig()):
    """Check Ichimoku conditions with flexibility"""
    try:
        close = data['Close']
        high = data['High']
        low = data['Low']
        
        # Get current values
        current_close = close.iloc[-1]
        prev_close = close.iloc[-2] if len(close) > 1 else current_close
        
        current_conversion = ichimoku['conversion_line'].iloc[-1]
        prev_conversion = ichimoku['conversion_line'].iloc[-2]
        current_base = ichimoku['base_line'].iloc[-1]
        prev_base = ichimoku['base_line'].iloc[-2]
        
        # Cloud values (at displacement)
        disp = ichimoku['displacement']
        current_cloud_top = ichimoku['cloud_top'].iloc[-1] if not pd.isna(ichimoku['cloud_top'].iloc[-1]) else current_close
        current_cloud_bottom = ichimoku['cloud_bottom'].iloc[-1] if not pd.isna(ichimoku['cloud_bottom'].iloc[-1]) else current_close
        current_positive_cloud = ichimoku['positive_cloud'].iloc[-1] if not pd.isna(ichimoku['positive_cloud'].iloc[-1]) else True
        
        # Chikou comparison (current close vs price 26 bars ago)
        chikou_reference_price = close.iloc[-disp-1] if len(close) > disp else current_close
        
        # ============ LONG CONDITIONS ============
        long_conditions_met = {}
        
        # 1. Conversion crosses above Base (Tenkan crosses Kijun)
        long_conditions_met['conversion_crosses_base'] = (
            current_conversion > current_base and prev_conversion <= prev_base
        )
        
        # 2. Conversion above Base
        long_conditions_met['conversion_above_base'] = current_conversion > current_base
        
        # 3. Positive Cloud (Span A > Span B)
        long_conditions_met['positive_cloud'] = current_positive_cloud
        
        # 4. Price above Cloud
        long_conditions_met['price_above_cloud'] = (
            current_close > current_cloud_top
        )
        
        # 5. Positive Chikou (current close > price 26 bars ago)
        long_conditions_met['positive_chikou'] = current_close > chikou_reference_price
        
        # 6. Price above Conversion
        long_conditions_met['price_above_conversion'] = current_close > current_conversion
        
        # ============ SHORT CONDITIONS ============
        short_conditions_met = {}
        
        # 1. Base crosses above Conversion (Kijun crosses Tenkan)
        short_conditions_met['base_crosses_conversion'] = (
            current_base > current_conversion and prev_base <= prev_conversion
        )
        
        # 2. Base above Conversion
        short_conditions_met['base_above_conversion'] = current_base > current_conversion
        
        # 3. Negative Cloud (Span B > Span A)
        short_conditions_met['negative_cloud'] = not current_positive_cloud
        
        # 4. Price below Cloud
        short_conditions_met['price_below_cloud'] = (
            current_close < current_cloud_bottom
        )
        
        # 5. Negative Chikou (current close < price 26 bars ago)
        short_conditions_met['negative_chikou'] = current_close < chikou_reference_price
        
        # 6. Price below Base
        short_conditions_met['price_below_base'] = current_close < current_base
        
        return {
            'long_conditions': long_conditions_met,
            'short_conditions': short_conditions_met,
            'ichimoku_values': {
                'conversion_line': current_conversion,
                'base_line': current_base,
                'cloud_top': current_cloud_top,
                'cloud_bottom': current_cloud_bottom,
                'positive_cloud': current_positive_cloud,
                'chikou_vs_past': current_close - chikou_reference_price
            }
        }
        
    except Exception as e:
        return None

def analyze_ultimate_ichimoku(ticker, volume_days=20, momentum_days=5, debug=False):
    """Ultimate Ichimoku Strategy Analysis with Entry Levels, RSI, Volume & Momentum"""
    try:
        if debug:
            print(f"📊 Analyzing {ticker} with Ultimate Ichimoku...")
        
        data = get_stock_data(ticker, 200)
        if data is None:
            return None
        
        # Calculate Ichimoku
        ichimoku = calculate_ichimoku_ultimate(data)
        if ichimoku is None:
            return None
        
        # Check conditions
        conditions = check_ichimoku_conditions(data, ichimoku)
        if conditions is None:
            return None
        
        # Get current market data
        close = data['Close']
        high = data['High']
        low = data['Low']
        volume = data['Volume']
        
        current_price = close.iloc[-1]
        current_volume = volume.iloc[-1]
        
        print(f"   📅 Data: {len(data)} trading days available")
        
        # Calculate metrics using proper trading days
        volume_ratio, momentum, trading_days_used = calculate_proper_metrics(
            data, volume_days, momentum_days
        )
        
        # Enhanced volume confirmation
        volume_analysis = enhanced_volume_confirmation(data, current_volume, volume_days)
        
        # Calculate RSI
        rsi = calculate_rsi(data['Close'])
        
        print(f"   📊 Volume: Current {current_volume:,.0f} vs {volume_days}-day avg = {volume_ratio:.1f}x ({volume_analysis['volume_strength']})")
        print(f"   🚀 Momentum: {momentum:+.1f}% ({momentum_days} trading days)")
        print(f"   📈 RSI: {rsi:.1f}")
        
        # Detect support and resistance levels
        support_levels, resistance_levels = detect_support_resistance_levels(
            data, current_price, lookback_bars=50
        )
        
        # ============ SIGNAL GENERATION ============
        
        config = IchimokuConfig()
        
        # Count long conditions met
        long_conditions = conditions['long_conditions']
        long_conditions_count = sum(
            1 for condition, enabled in config.LONG_CONDITIONS.items()
            if enabled and long_conditions.get(condition, False)
        )
        long_conditions_enabled = sum(1 for enabled in config.LONG_CONDITIONS.values() if enabled)
        
        # Count short conditions met  
        short_conditions = conditions['short_conditions']
        short_conditions_count = sum(
            1 for condition, enabled in config.SHORT_CONDITIONS.items()
            if enabled and short_conditions.get(condition, False)
        )
        short_conditions_enabled = sum(1 for enabled in config.SHORT_CONDITIONS.values() if enabled)
        
        # ============ DETERMINE SIGNAL ============
        
        signal_type = 'HOLD'
        signal_strength = 0
        entry_reason = ""
        conditions_breakdown = []
        
        # Long Signal
        if long_conditions_count >= config.MIN_LONG_CONDITIONS:
            signal_type = 'STRONG_BUY' if long_conditions_count >= 4 else 'WEAK_BUY'
            signal_strength = (long_conditions_count / long_conditions_enabled) * 10
            entry_reason = f"{long_conditions_count}/{long_conditions_enabled} Ichimoku Long Conditions"
            
            # Add specific conditions met
            for condition, met in long_conditions.items():
                if config.LONG_CONDITIONS.get(condition, False) and met:
                    condition_name = condition.replace('_', ' ').title()
                    conditions_breakdown.append(f"✅ {condition_name}")
        
        # Short Signal (only if no long signal)
        elif short_conditions_count >= config.MIN_SHORT_CONDITIONS:
            signal_type = 'STRONG_SELL' if short_conditions_count >= 4 else 'WEAK_SELL'  
            signal_strength = (short_conditions_count / short_conditions_enabled) * 10
            entry_reason = f"{short_conditions_count}/{short_conditions_enabled} Ichimoku Short Conditions"
            
            # Add specific conditions met
            for condition, met in short_conditions.items():
                if config.SHORT_CONDITIONS.get(condition, False) and met:
                    condition_name = condition.replace('_', ' ').title()
                    conditions_breakdown.append(f"✅ {condition_name}")
        
        # Volume boost
        if volume_ratio > 1.5:
            signal_strength *= 1.2
            entry_reason += f" + Volume ({volume_ratio:.1f}x)"
        
        # RSI boost
        if signal_type in ['STRONG_BUY', 'WEAK_BUY'] and rsi < 40:
            signal_strength *= 1.15  # Oversold boost for buys
        elif signal_type in ['STRONG_SELL', 'WEAK_SELL'] and rsi > 60:
            signal_strength *= 1.15  # Overbought boost for sells
        
        # Calculate entry price using support/resistance with full explanation
        entry_price, entry_logic, full_entry_explanation = calculate_entry_price(
            signal_type, current_price, support_levels, resistance_levels
        )
        
        # ============ RISK MANAGEMENT ============
        
        ichi_values = conditions['ichimoku_values']
        
        # Use Ichimoku levels for stops and targets
        if 'BUY' in signal_type:
            # Long stops: below cloud or Kijun
            stop_loss = min(ichi_values['cloud_bottom'], ichi_values['base_line']) * 0.98
            
            # Long targets: use 2:1 R:R or next resistance
            risk_distance = entry_price - stop_loss
            take_profit = entry_price + (risk_distance * 2)
            
        elif 'SELL' in signal_type:
            # Short stops: above cloud or Kijun  
            stop_loss = max(ichi_values['cloud_top'], ichi_values['base_line']) * 1.02
            
            # Short targets: use 2:1 R:R or next support
            risk_distance = stop_loss - entry_price
            take_profit = entry_price - (risk_distance * 2)
            
        else:
            stop_loss = current_price * 0.97
            take_profit = current_price * 1.06
            entry_price = current_price
            entry_logic = "Market Price"
            full_entry_explanation = "HOLD signal - no specific entry required"
        
        # Risk-Reward calculation
        risk_per_share = abs(entry_price - stop_loss)
        reward_per_share = abs(take_profit - entry_price)
        risk_reward_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 0
        
        # Filter poor R:R trades
        if risk_reward_ratio < 0.8 and signal_type != 'HOLD':
            signal_type = 'HOLD'
            signal_strength = 0
            entry_reason = f"Poor R:R {risk_reward_ratio:.1f} - Skipped"
            conditions_breakdown = []
            full_entry_explanation = f"Signal filtered out due to poor risk-reward ratio: 1:{risk_reward_ratio:.1f}"
        
        # Position sizing
        capital = 100000
        risk_amount = capital * 0.02
        position_size = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
        
        # Trend classification
        if ichi_values['positive_cloud'] and current_price > ichi_values['cloud_top']:
            trend_status = "BULLISH"
        elif not ichi_values['positive_cloud'] and current_price < ichi_values['cloud_bottom']:
            trend_status = "BEARISH"
        elif ichi_values['cloud_bottom'] <= current_price <= ichi_values['cloud_top']:
            trend_status = "IN_CLOUD"
        else:
            trend_status = "NEUTRAL"
        
        # Get sector
        sector = get_sector(ticker)
        
        print(f"   🎯 Signal: {signal_type}")
        print(f"   💰 Entry: ₹{entry_price:.2f} ({entry_logic})")
        print(f"   🏢 Sector: {sector}")
        
        result = {
            'ticker': ticker,
            'sector': sector,
            'signal_type': signal_type,
            'signal_strength': float(signal_strength),
            'current_price': float(current_price),
            'entry_price': float(entry_price),
            'entry_logic': entry_logic,
            'full_entry_explanation': full_entry_explanation,
            'entry_reason': entry_reason,
            'trend_status': trend_status,
            
            # Condition breakdown
            'conditions_met': conditions_breakdown,
            'long_conditions_count': long_conditions_count,
            'short_conditions_count': short_conditions_count,
            
            # Ichimoku Values
            'conversion_line': float(ichi_values['conversion_line']),
            'base_line': float(ichi_values['base_line']),
            'cloud_top': float(ichi_values['cloud_top']),
            'cloud_bottom': float(ichi_values['cloud_bottom']),
            'positive_cloud': bool(ichi_values['positive_cloud']),
            'chikou_vs_past': float(ichi_values['chikou_vs_past']),
            
            # Technical Indicators
            'rsi': float(rsi),
            'volume_ratio': float(volume_ratio),
            'volume_analysis': volume_analysis,
            'momentum': float(momentum),
            'trading_days_used': int(trading_days_used),
            'volume_period': f"{volume_days} trading days",
            'momentum_period': f"{momentum_days} trading days",
            
            # Support/Resistance
            'support_levels': support_levels[:3],  # Top 3 support levels
            'resistance_levels': resistance_levels[:3],  # Top 3 resistance levels
            
            # Risk Management
            'stop_loss': float(stop_loss),
            'take_profit': float(take_profit),
            'risk_reward_ratio': float(risk_reward_ratio),
            'position_size': int(position_size),
            'risk_per_share': float(risk_per_share),
            
            'strategy': 'Ultimate Ichimoku with Entry Levels'
        }
        
        return result
        
    except Exception as e:
        if debug:
            print(f"Error analyzing {ticker}: {e}")
        return None

def analyze_all_stocks_ultimate(volume_days=20, momentum_days=5, max_workers=3, debug=False):
    """Analyze all stocks with Ultimate Ichimoku strategy"""
    
    tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
    
    print(f"\n🚀 ULTIMATE ICHIMOKU CLOUD STRATEGY")
    print(f"📊 Analyzing {len(tickers)} stocks with Entry Levels & Sector Analysis")
    print(f"⚙️  Flexible Conditions - Partial Confirmations Allowed")
    print(f"📊 Volume Period: {volume_days} trading days")
    print(f"🚀 Momentum Period: {momentum_days} trading days")
    print("="*80)
    
    all_signals = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(analyze_ultimate_ichimoku, ticker, volume_days, momentum_days, debug): ticker 
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
        
        print(f"\n📊 ANALYSIS SUMMARY:")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📈 Total signals: {len(all_signals)}")
    
    return all_signals

def sort_signals_by_combined_score(signals):
    """Sort signals by combined score of RSI, Volume, and Momentum"""
    if not signals:
        return signals
    
    for signal in signals:
        # Calculate combined score
        rsi_score = 0
        volume_score = 0
        momentum_score = 0
        
        # RSI scoring
        rsi = signal.get('rsi', 50)
        if 'BUY' in signal['signal_type']:
            # For BUY: Lower RSI is better (oversold)
            if rsi <= 30:
                rsi_score = 10
            elif rsi <= 40:
                rsi_score = 8
            elif rsi <= 50:
                rsi_score = 6
            else:
                rsi_score = max(0, 10 - (rsi - 50) * 0.2)
        else:
            # For SELL: Higher RSI is better (overbought)
            if rsi >= 70:
                rsi_score = 10
            elif rsi >= 60:
                rsi_score = 8
            elif rsi >= 50:
                rsi_score = 6
            else:
                rsi_score = max(0, 10 - (50 - rsi) * 0.2)
        
        # Volume scoring
        volume_ratio = signal.get('volume_ratio', 1.0)
        if volume_ratio >= 2.0:
            volume_score = 10
        elif volume_ratio >= 1.5:
            volume_score = 8
        elif volume_ratio >= 1.2:
            volume_score = 6
        elif volume_ratio >= 0.8:
            volume_score = 4
        else:
            volume_score = 2
        
        # Momentum scoring
        momentum = signal.get('momentum', 0)
        if 'BUY' in signal['signal_type']:
            # For BUY: Positive momentum is better
            if momentum >= 5:
                momentum_score = 10
            elif momentum >= 2:
                momentum_score = 8
            elif momentum >= 0:
                momentum_score = 6
            else:
                momentum_score = max(0, 6 + momentum * 0.5)
        else:
            # For SELL: Negative momentum is better
            if momentum <= -5:
                momentum_score = 10
            elif momentum <= -2:
                momentum_score = 8
            elif momentum <= 0:
                momentum_score = 6
            else:
                momentum_score = max(0, 6 - momentum * 0.5)
        
        # Combined score with weights
        signal['combined_score'] = (
            rsi_score * 0.3 +      # 30% weight
            volume_score * 0.4 +   # 40% weight  
            momentum_score * 0.3   # 30% weight
        )
        
        signal['rsi_score'] = rsi_score
        signal['volume_score'] = volume_score
        signal['momentum_score'] = momentum_score
    
    # Sort by combined score (highest first)
    return sorted(signals, key=lambda x: x['combined_score'], reverse=True)

def group_signals_by_sector(signals):
    """Group signals by sector"""
    sector_groups = defaultdict(list)
    
    for signal in signals:
        sector = signal.get('sector', 'Others')
        sector_groups[sector].append(signal)
    
    # Sort each sector's signals by combined score
    for sector in sector_groups:
        sector_groups[sector] = sort_signals_by_combined_score(sector_groups[sector])
    
    return dict(sector_groups)

def display_sector_wise_signals(all_signals, signal_types, title):
    """Display sector-wise signals with full entry logic"""
    
    # Filter signals
    filtered_signals = [s for s in all_signals if s['signal_type'] in signal_types]
    
    if not filtered_signals:
        print(f"\n❌ No {title} signals found!")
        return
    
    # Sort by combined score
    filtered_signals = sort_signals_by_combined_score(filtered_signals)
    
    # Group by sector
    sector_groups = group_signals_by_sector(filtered_signals)
    
    print(f"\n🏆 SECTOR-WISE {title} SIGNALS")
    print(f"📊 Ultimate Ichimoku with Full Entry Logic")
    print("="*120)
    
    total_signals = 0
    
    # Display each sector
    for sector, signals in sector_groups.items():
        if not signals:
            continue
            
        total_signals += len(signals)
        
        # Show strong signals first (top 5 per sector)
        strong_signals = [s for s in signals if 'STRONG' in s['signal_type']][:5]
        
        if strong_signals:
            print(f"\n🏢 {sector.upper()} SECTOR - STRONG {title} SIGNALS")
            print("-" * 120)
            
            for i, signal in enumerate(strong_signals, 1):
                # Basic info
                print(f"{i}. {signal['ticker']:10} | {signal['signal_type']:11} | "
                      f"Current: ₹{signal['current_price']:7.1f} | "
                      f"Entry: ₹{signal['entry_price']:7.1f} | "
                      f"Score: {signal.get('combined_score', 0):4.1f}/10")
                
                # Technical indicators
                rsi_icon = "🔴" if signal['rsi'] > 70 else "🟢" if signal['rsi'] < 30 else ""
                volume_icon = "🟢" if signal['volume_analysis']['volume_strength'] in ['HIGH', 'VERY_HIGH'] else "🟡" if signal['volume_analysis']['volume_strength'] == 'NORMAL' else "🔴"
                momentum_icon = "🟢" if ('BUY' in signal['signal_type'] and signal['momentum'] > 0) or ('SELL' in signal['signal_type'] and signal['momentum'] < 0) else "🔴"
                
                print(f"   📊 RSI: {signal['rsi']:4.1f}{rsi_icon} | "
                      f"Volume: {signal['volume_ratio']:4.1f}x{volume_icon} | "
                      f"Momentum: {signal['momentum']:+5.1f}%{momentum_icon} | "
                      f"R:R: 1:{signal['risk_reward_ratio']:.1f}")
                
                # Full entry explanation
                print(f"   💡 {signal['full_entry_explanation']}")
                
                # Ichimoku levels
                cloud_status = "☁️ Positive" if signal['positive_cloud'] else "☁️ Negative"
                print(f"   ☁️  Tenkan: ₹{signal['conversion_line']:6.1f} | "
                      f"Kijun: ₹{signal['base_line']:6.1f} | "
                      f"{cloud_status} | "
                      f"Cloud: ₹{signal['cloud_bottom']:6.1f}-₹{signal['cloud_top']:6.1f}")
                
                # Risk management
                print(f"   🛑 Stop: ₹{signal['stop_loss']:6.1f} | "
                      f"Target: ₹{signal['take_profit']:6.1f} | "
                      f"Position: {signal['position_size']} shares | "
                      f"Risk: ₹{signal['risk_per_share']:5.1f}/share")
                
                print()
    
    # Summary by sector
    print(f"\n📊 SECTOR SUMMARY:")
    sector_stats = []
    for sector, signals in sector_groups.items():
        strong_count = len([s for s in signals if 'STRONG' in s['signal_type']])
        avg_score = sum(s.get('combined_score', 0) for s in signals) / len(signals) if signals else 0
        avg_rsi = sum(s['rsi'] for s in signals) / len(signals) if signals else 50
        avg_volume = sum(s['volume_ratio'] for s in signals) / len(signals) if signals else 1
        
        sector_stats.append({
            'sector': sector,
            'total': len(signals),
            'strong': strong_count,
            'avg_score': avg_score,
            'avg_rsi': avg_rsi,
            'avg_volume': avg_volume
        })
    
    # Sort sectors by number of strong signals
    sector_stats.sort(key=lambda x: x['strong'], reverse=True)
    
    for stat in sector_stats:
        print(f"   🏢 {stat['sector']:20} | "
              f"Total: {stat['total']:2d} | "
              f"Strong: {stat['strong']:2d} | "
              f"Avg Score: {stat['avg_score']:4.1f} | "
              f"Avg RSI: {stat['avg_rsi']:4.1f} | "
              f"Avg Vol: {stat['avg_volume']:4.1f}x")
    
    print(f"\n🎯 BEST PERFORMING SECTORS:")
    top_3_sectors = sector_stats[:3]
    for i, stat in enumerate(top_3_sectors, 1):
        print(f"   {i}. {stat['sector']} - {stat['strong']} strong signals, {stat['avg_score']:.1f} avg score")

def generate_sector_wise_html(all_signals, volume_days, momentum_days, output_dir):
    """Generate sector-wise HTML report in donchian.py table format"""
    
    if not all_signals:
        print("❌ No signals to generate report")
        return None
    
    # Separate signals by type
    buy_signals = [s for s in all_signals if s['signal_type'] in ['STRONG_BUY', 'WEAK_BUY']]
    sell_signals = [s for s in all_signals if s['signal_type'] in ['STRONG_SELL', 'WEAK_SELL']]
    
    # Sort by combined score
    buy_signals = sort_signals_by_combined_score(buy_signals) if buy_signals else []
    sell_signals = sort_signals_by_combined_score(sell_signals) if sell_signals else []
    
    # Group by sector
    buy_sectors = group_signals_by_sector(buy_signals)
    sell_sectors = group_signals_by_sector(sell_signals)
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sector-wise Ichimoku Analysis - {datetime.now().strftime('%Y-%m-%d')}</title>
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
                <h1>☁️ SECTOR-WISE ICHIMOKU ANALYSIS</h1>
                <p><strong>Ultimate Ichimoku Strategy with Entry Levels</strong></p>
                <p>Volume: {volume_days} days | Momentum: {momentum_days} days</p>
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
                    <h3>{len(buy_sectors)}</h3>
                    <p>BUY Sectors</p>
                </div>
                <div class="stat-card">
                    <h3>{len(sell_sectors)}</h3>
                    <p>SELL Sectors</p>
                </div>
            </div>
    """
    
    # Generate BUY signals by sector
    if buy_sectors:
        html_content += f"""
            <div class="section">
                <h2>🟢 BUY SIGNALS BY SECTOR</h2>
        """
        
        # Sort sectors by number of strong signals
        sorted_buy_sectors = sorted(buy_sectors.items(), 
                                   key=lambda x: len([s for s in x[1] if 'STRONG' in s['signal_type']]), 
                                   reverse=True)
        
        for sector, signals in sorted_buy_sectors:
            if not signals:
                continue
                
            # Separate strong and weak signals
            strong_signals = [s for s in signals if 'STRONG' in s['signal_type']]
            weak_signals = [s for s in signals if 'WEAK' in s['signal_type']]
            
            # Combine: strong first, then weak
            ordered_signals = strong_signals + weak_signals
            
            if ordered_signals:
                html_content += f'<div class="sector-header">🏢 {sector.upper()} SECTOR ({len(strong_signals)} Strong, {len(weak_signals)} Weak)</div>'
                html_content += '''
                    <table>
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th>Ticker</th>
                                <th>Signal</th>
                                <th>Current</th>
                                <th>Entry</th>
                                <th>Entry Logic</th>
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
                
                for i, signal in enumerate(ordered_signals, 1):
                    signal_class = signal['signal_type'].lower().replace('_', '-')
                    momentum_class = 'positive' if signal['momentum'] >= 0 else 'negative'
                    
                    # RSI interpretation
                    rsi_value = signal.get('rsi', 50)
                    rsi_display = f"{rsi_value:.0f}"
                    if rsi_value > 70:
                        rsi_display += "🔴"  # Overbought
                    elif rsi_value < 30:
                        rsi_display += "🟢"  # Oversold
                    
                    # Volume with strength indicator
                    volume_strength = signal['volume_analysis']['volume_strength']
                    volume_display = f"{signal['volume_ratio']:.1f}x"
                    if volume_strength == 'VERY_HIGH':
                        volume_display += "🟢"
                    elif volume_strength == 'HIGH':
                        volume_display += "🟡"
                    elif volume_strength == 'WEAK':
                        volume_display += "🔴"
                    
                    # Truncate entry logic for table
                    entry_logic_short = signal['entry_logic'][:25] + "..." if len(signal['entry_logic']) > 25 else signal['entry_logic']
                    
                    html_content += f'''
                            <tr>
                                <td class="rank">{i}</td>
                                <td class="ticker">{signal['ticker']}</td>
                                <td><span class="{signal_class}">{signal['signal_type'].replace('_', ' ')}</span></td>
                                <td class="price">₹{signal['current_price']:.1f}</td>
                                <td class="price">₹{signal['entry_price']:.1f}</td>
                                <td title="{signal['full_entry_explanation']}">{entry_logic_short}</td>
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
    
    # Generate SELL signals by sector
    if sell_sectors:
        html_content += f"""
            <div class="section">
                <h2>🔴 SELL SIGNALS BY SECTOR</h2>
        """
        
        # Sort sectors by number of strong signals
        sorted_sell_sectors = sorted(sell_sectors.items(), 
                                    key=lambda x: len([s for s in x[1] if 'STRONG' in s['signal_type']]), 
                                    reverse=True)
        
        for sector, signals in sorted_sell_sectors:
            if not signals:
                continue
                
            # Separate strong and weak signals
            strong_signals = [s for s in signals if 'STRONG' in s['signal_type']]
            weak_signals = [s for s in signals if 'WEAK' in s['signal_type']]
            
            # Combine: strong first, then weak
            ordered_signals = strong_signals + weak_signals
            
            if ordered_signals:
                html_content += f'<div class="sector-header">🏢 {sector.upper()} SECTOR ({len(strong_signals)} Strong, {len(weak_signals)} Weak)</div>'
                html_content += '''
                    <table>
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th>Ticker</th>
                                <th>Signal</th>
                                <th>Current</th>
                                <th>Entry</th>
                                <th>Entry Logic</th>
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
                
                for i, signal in enumerate(ordered_signals, 1):
                    signal_class = signal['signal_type'].lower().replace('_', '-')
                    momentum_class = 'positive' if signal['momentum'] >= 0 else 'negative'
                    
                    # RSI interpretation
                    rsi_value = signal.get('rsi', 50)
                    rsi_display = f"{rsi_value:.0f}"
                    if rsi_value > 70:
                        rsi_display += "🔴"  # Overbought
                    elif rsi_value < 30:
                        rsi_display += "🟢"  # Oversold
                    
                    # Volume with strength indicator
                    volume_strength = signal['volume_analysis']['volume_strength']
                    volume_display = f"{signal['volume_ratio']:.1f}x"
                    if volume_strength == 'VERY_HIGH':
                        volume_display += "🟢"
                    elif volume_strength == 'HIGH':
                        volume_display += "🟡"
                    elif volume_strength == 'WEAK':
                        volume_display += "🔴"
                    
                    # Truncate entry logic for table
                    entry_logic_short = signal['entry_logic'][:25] + "..." if len(signal['entry_logic']) > 25 else signal['entry_logic']
                    
                    html_content += f'''
                            <tr>
                                <td class="rank">{i}</td>
                                <td class="ticker">{signal['ticker']}</td>
                                <td><span class="{signal_class}">{signal['signal_type'].replace('_', ' ')}</span></td>
                                <td class="price">₹{signal['current_price']:.1f}</td>
                                <td class="price">₹{signal['entry_price']:.1f}</td>
                                <td title="{signal['full_entry_explanation']}">{entry_logic_short}</td>
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
    
    html_content += """
            <div class="footer">
                <p><strong>⚠️ Disclaimer:</strong> This analysis is for educational purposes only. Entry levels calculated based on support/resistance methodology.</p>
                <p><strong>☁️ Strategy:</strong> Sector-wise Ultimate Ichimoku system with precise entry calculations and comprehensive analysis.</p>
                <p><strong>🎯 Entry Logic:</strong> BUY above resistance + 0.2%, SELL below support - 0.2%. Hover over "Entry Logic" for full explanation.</p>
                <p><strong>📊 Ranking:</strong> Strong signals first, then weak signals. Sorted by combined RSI + Volume + Momentum score.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Save HTML
    html_filename = f"sector_wise_ichimoku_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    html_path = os.path.join(output_dir, html_filename)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return html_path

def main():
    """Main function with sector-wise comprehensive analysis"""
    parser = argparse.ArgumentParser(description="Sector-wise Ultimate Ichimoku Strategy")
    
    parser.add_argument('--volume-days', type=int, default=20, 
                       help='Volume average days (default: 20)')
    parser.add_argument('--momentum-days', type=int, default=5, 
                       help='Momentum calculation days (default: 5)')
    parser.add_argument('--workers', type=int, default=3, 
                       help='Max concurrent workers (default: 3)')
    parser.add_argument('--output', type=str, 
                       help='Output directory (default: output)')
    parser.add_argument('--test-single', type=str, 
                       help='Test analysis on a single ticker for debugging')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug output for troubleshooting')
    parser.add_argument('--sector', type=str, 
                       help='Show signals for specific sector only')
    parser.add_argument('--buy-only', action='store_true', 
                       help='Show only BUY signals')
    parser.add_argument('--sell-only', action='store_true', 
                       help='Show only SELL signals')
    
    args = parser.parse_args()
    
    # Test single ticker if requested
    if args.test_single:
        print(f"🧪 TESTING SINGLE TICKER: {args.test_single}")
        print("="*80)
        result = analyze_ultimate_ichimoku(
            args.test_single, 
            args.volume_days, 
            args.momentum_days, 
            debug=True
        )
        if result:
            print(f"\n✅ SUCCESS! Signal: {result['signal_type']}")
            print(f"   🏢 Sector: {result['sector']}")
            print(f"   📊 Current Price: ₹{result['current_price']:.2f}")
            print(f"   💰 Entry Price: ₹{result['entry_price']:.2f}")
            print(f"   🎯 Entry Logic: {result['entry_logic']}")
            print(f"\n💡 FULL ENTRY EXPLANATION:")
            print(f"   {result['full_entry_explanation']}")
            print(f"\n📊 Technical Indicators:")
            print(f"   📈 RSI: {result['rsi']:.1f}")
            print(f"   📊 Volume: {result['volume_ratio']:.1f}x")
            print(f"   🚀 Momentum: {result['momentum']:+.1f}%")
            print(f"   🏆 Combined Score: {result.get('combined_score', 0):.1f}/10")
        else:
            print(f"\n❌ No result for {args.test_single}")
        return
    
    print("☁️ SECTOR-WISE ULTIMATE ICHIMOKU ANALYZER")
    print("🎯 With Full Entry Logic & Comprehensive Analysis")
    print("="*80)
    print(f"📊 Volume Period: {args.volume_days} trading days") 
    print(f"🚀 Momentum Period: {args.momentum_days} trading days")
    print(f"⚙️  Workers: {args.workers}")
    print("="*80)
    
    # Set output directory
    output_dir = args.output or getattr(config, 'OUTPUT_DIR', 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Analyze all stocks
    all_signals = analyze_all_stocks_ultimate(
        volume_days=args.volume_days,
        momentum_days=args.momentum_days,
        max_workers=args.workers,
        debug=args.debug
    )
    
    if not all_signals:
        print("\n❌ No signals generated!")
        print("💡 TROUBLESHOOTING TIPS:")
        print("   🔧 Enable debug mode: --debug")
        print("   🔧 Check internet connection for data fetching")
        print("   🔧 Try single ticker test: --test-single RELIANCE --debug")
        return
    
    # Filter by sector if specified
    if args.sector:
        all_signals = [s for s in all_signals if s['sector'].upper() == args.sector.upper()]
        if not all_signals:
            print(f"\n❌ No signals found for sector: {args.sector}")
            return
    
    # Display results based on arguments
    if args.buy_only:
        display_sector_wise_signals(all_signals, ['STRONG_BUY', 'WEAK_BUY'], "BUY")
    elif args.sell_only:
        display_sector_wise_signals(all_signals, ['STRONG_SELL', 'WEAK_SELL'], "SELL")
    else:
        # Show both BUY and SELL signals
        display_sector_wise_signals(all_signals, ['STRONG_BUY', 'WEAK_BUY'], "BUY")
        display_sector_wise_signals(all_signals, ['STRONG_SELL', 'WEAK_SELL'], "SELL")
    
    # Generate reports
    print(f"\n📄 Generating sector-wise reports...")
    
    # HTML Report
    html_path = generate_sector_wise_html(
        all_signals, args.volume_days, args.momentum_days, output_dir
    )
    if html_path:
        print(f"🌐 Sector-wise HTML Report: {html_path}")
        print(f"🔗 Open: file://{os.path.abspath(html_path)}")
    
    # JSON Report (existing function can be reused)
    json_filename = f"sector_wise_ichimoku_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_path = os.path.join(output_dir, json_filename)
    
    # Prepare JSON data
    json_data = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'total_stocks_analyzed': len(all_signals),
            'volume_days': int(args.volume_days),  
            'momentum_days': int(args.momentum_days),
            'strategy': 'Sector-wise Ultimate Ichimoku with Entry Levels'
        },
        'signals': all_signals
    }
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"📊 JSON Data: {json_path}")
    
    print(f"\n✅ Sector-wise Analysis Complete!")
    print(f"📁 Output Directory: {os.path.abspath(output_dir)}")
    
    # Enhanced trading notes
    print(f"\n💡 SECTOR-WISE ICHIMOKU FEATURES:")
    print(f"   🏢 SECTOR ANALYSIS: Stocks grouped by industry sectors")
    print(f"   ☁️  ICHIMOKU: Full cloud analysis with flexible conditions")
    print(f"   🎯 ENTRY LEVELS: Precise entry above resistance/below support")
    print(f"   💡 FULL LOGIC: Complete entry explanation for each signal")
    print(f"   📊 RSI + VOLUME + MOMENTUM: Combined scoring system")
    print(f"   🏆 SECTOR RANKING: Best performing sectors highlighted")
    print(f"   💰 ENTRY BUFFER: 0.2% buffer for breakout confirmation")
    print(f"   🛑 RISK MANAGEMENT: Ichimoku-based stops with 2:1 R:R minimum")
    
    print(f"\n🚀 USAGE EXAMPLES:")
    print(f"   python swing.py --buy-only                    # Show all BUY signals by sector")
    print(f"   python swing.py --sell-only                   # Show all SELL signals by sector") 
    print(f"   python swing.py --sector Banking              # Show only Banking sector signals")
    print(f"   python swing.py --test-single RELIANCE --debug # Test single stock with full details")

if __name__ == "__main__":
    main()