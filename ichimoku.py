#!/usr/bin/env python
# enhanced_ichimoku_analyzer.py - Complete Ichimoku System with Trading Levels & Entry Price Logic

import os
import sys
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Polygon
import argparse
import json
from tabulate import tabulate
import concurrent.futures

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

def get_stock_data(ticker, lookback_days=200):
    """Get stock data for analysis with proper error handling"""
    try:
        # Add .NS for NSE stocks
        symbol = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
        
        # Get enough data for lookback + buffer
        days_needed = lookback_days + 30  # Buffer for Ichimoku calculations
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_needed)
        
        # Download data
        stock = yf.Ticker(symbol)
        data = stock.history(start=start_date, end=end_date)
        
        # Need at least 100 trading days for meaningful Ichimoku
        min_required = 100
        
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

class EnhancedIchimokuAnalyzer:
    """
    Enhanced Ichimoku Cloud Analyzer with Trading Levels, Entry Price Logic & RSI
    Includes all features from the live monitoring system
    """
    
    def __init__(self, tenkan_period=9, kijun_period=26, senkou_b_period=52, displacement=26):
        self.tenkan_period = tenkan_period
        self.kijun_period = kijun_period  
        self.senkou_b_period = senkou_b_period
        self.displacement = displacement
        
    def donchian(self, data, period):
        """Calculate Donchian Channel (average of highest high and lowest low)"""
        try:
            high_roll = data['High'].rolling(window=period, min_periods=1).max()
            low_roll = data['Low'].rolling(window=period, min_periods=1).min()
            result = (high_roll + low_roll) / 2
            # Forward fill NaN values, then back fill with close price
            result = result.fillna(data['Close'])
            return result
        except Exception as e:
            print(f"   ⚠️  Donchian calculation error: {e}")
            # Return closing price as fallback
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
        """
        Calculate all Ichimoku Cloud components with proper displacement
        Returns dictionary with all lines and signals
        """
        if len(data) < max(self.senkou_b_period, self.displacement) + 50:
            raise ValueError(f"Need at least {max(self.senkou_b_period, self.displacement) + 50} data points")
        
        # Calculate Ichimoku lines
        tenkan_line = self.donchian(data, self.tenkan_period)
        kijun_line = self.donchian(data, self.kijun_period)
        
        # Senkou Spans (Leading Spans)
        senkou_a = (tenkan_line + kijun_line) / 2
        senkou_b = self.donchian(data, self.senkou_b_period)
        
        # Chikou Span (Lagging Span) - current close displaced back
        chikou_span = data['Close'].shift(-self.displacement + 1)
        
        # Cloud boundaries (displaced forward)
        senkou_a_displaced = senkou_a.shift(self.displacement - 1)
        senkou_b_displaced = senkou_b.shift(self.displacement - 1)
        
        # Fill initial NaN values with the first valid values
        senkou_a_displaced = senkou_a_displaced.fillna(senkou_a.iloc[0] if len(senkou_a) > 0 else 0)
        senkou_b_displaced = senkou_b_displaced.fillna(senkou_b.iloc[0] if len(senkou_b) > 0 else 0)
        
        # Current cloud levels
        cloud_high = np.maximum(senkou_a_displaced, senkou_b_displaced)
        cloud_low = np.minimum(senkou_a_displaced, senkou_b_displaced)
        
        # Cloud color (Green when Senkou A > Senkou B)
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
        """
        Calculate 4-parameter Ichimoku signals:
        1. Cloud color change
        2. Price above/below cloud
        3. Tenkan-Kijun crossing
        4. Chikou Span above/below cloud and price (with proper displacement)
        """
        
        tenkan = ichimoku_data['tenkan_line']
        kijun = ichimoku_data['kijun_line']
        cloud_high = ichimoku_data['cloud_high']
        cloud_low = ichimoku_data['cloud_low']
        cloud_green = ichimoku_data['cloud_green']
        close = ichimoku_data['close']
        high = ichimoku_data['high']
        low = ichimoku_data['low']
        
        # Parameter 1: Cloud color (Green = bullish cloud)
        cloud_bullish = cloud_green.fillna(False)
        cloud_color_change = (cloud_bullish != cloud_bullish.shift(1).fillna(False)).fillna(False)
        
        # Parameter 2: Price position relative to cloud
        price_above_cloud = (close > cloud_high).fillna(False)
        price_below_cloud = (close < cloud_low).fillna(False)
        price_in_cloud = (~price_above_cloud) & (~price_below_cloud)
        
        # Parameter 3: Tenkan-Kijun crossing
        tk_bullish = (tenkan > kijun).fillna(False)
        tk_bearish = (tenkan < kijun).fillna(False)
        
        # Fix for the bitwise NOT operator error - handle NaN values
        tk_bullish_prev = tk_bullish.shift(1).fillna(False)
        tk_bearish_prev = tk_bearish.shift(1).fillna(False)
        
        tk_cross_up = tk_bullish & (~tk_bullish_prev)  # Tenkan crosses above Kijun
        tk_cross_down = tk_bearish & (~tk_bearish_prev)  # Tenkan crosses below Kijun
        
        # Parameter 4: Chikou Span conditions (KEY INSIGHT FROM STACKOVERFLOW)
        # For current signal, check if chikou (displaced back) is above historical levels
        
        # Chikou above historical price - handle potential NaN values
        high_shifted = high.shift(self.displacement).fillna(high.iloc[0] if len(high) > 0 else 0)
        low_shifted = low.shift(self.displacement).fillna(low.iloc[0] if len(low) > 0 else 0)
        
        chikou_above_price = (close > high_shifted).fillna(False)
        chikou_below_price = (close < low_shifted).fillna(False)
        
        # Chikou above historical cloud (need to add displacements)
        cloud_high_shifted = cloud_high.shift(self.displacement).fillna(cloud_high.iloc[0] if len(cloud_high) > 0 else 0)
        cloud_low_shifted = cloud_low.shift(self.displacement).fillna(cloud_low.iloc[0] if len(cloud_low) > 0 else 0)
        
        chikou_above_cloud = (close > cloud_high_shifted).fillna(False)
        chikou_below_cloud = (close < cloud_low_shifted).fillna(False)
        
        # Combined Chikou conditions
        chikou_bullish = chikou_above_price & chikou_above_cloud
        chikou_bearish = chikou_below_price & chikou_below_cloud
        
        # COMPLETE 4-PARAMETER SIGNALS
        # Long Signal: All 4 conditions must be met
        long_signal = (
            cloud_bullish &           # 1. Green cloud
            price_above_cloud &       # 2. Price above cloud
            tk_bullish &              # 3. Tenkan above Kijun
            chikou_bullish            # 4. Chikou above historical price and cloud
        )
        
        # Short Signal: All 4 conditions must be met
        short_signal = (
            (~cloud_bullish) &        # 1. Red cloud
            price_below_cloud &       # 2. Price below cloud
            tk_bearish &              # 3. Tenkan below Kijun
            chikou_bearish            # 4. Chikou below historical price and cloud
        )
        
        # Signal triggers (new signals only) - fix NaN handling
        long_signal_prev = long_signal.shift(1).fillna(False)
        short_signal_prev = short_signal.shift(1).fillna(False)
        
        new_long = long_signal & (~long_signal_prev)
        new_short = short_signal & (~short_signal_prev)
        
        # Ensure we have valid data for current values
        if len(long_signal) == 0:
            current_long = False
            current_short = False
            current_new_long = False
            current_new_short = False
        else:
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
            # Individual parameters
            'cloud_bullish': cloud_bullish,
            'cloud_color_change': cloud_color_change,
            'price_above_cloud': price_above_cloud,
            'price_below_cloud': price_below_cloud,
            'price_in_cloud': price_in_cloud,
            'tk_bullish': tk_bullish,
            'tk_bearish': tk_bearish,
            'tk_cross_up': tk_cross_up,
            'tk_cross_down': tk_cross_down,
            'chikou_bullish': chikou_bullish,
            'chikou_bearish': chikou_bearish,
            'chikou_above_price': chikou_above_price,
            'chikou_below_price': chikou_below_price,
            'chikou_above_cloud': chikou_above_cloud,
            'chikou_below_cloud': chikou_below_cloud,
            
            # Combined signals
            'long_signal': long_signal,
            'short_signal': short_signal,
            'new_long': new_long,
            'new_short': new_short,
            
            # Current status
            'current_long': current_long,
            'current_short': current_short,
            'current_new_long': current_new_long,
            'current_new_short': current_new_short
        }
    
    def calculate_trading_levels(self, data, ichimoku_data, signals):
        """Calculate Entry, Stop Loss, Targets and Risk Management levels"""
        try:
            current_price = data['Close'].iloc[-1]
            
            # Get current Ichimoku values
            tenkan_current = ichimoku_data['tenkan_line'].iloc[-1]
            kijun_current = ichimoku_data['kijun_line'].iloc[-1]
            cloud_high_current = ichimoku_data['cloud_high'].iloc[-1]
            cloud_low_current = ichimoku_data['cloud_low'].iloc[-1]
            
            # Determine signal type and calculate levels
            if signals['current_new_long'] or signals['current_long']:
                signal_type = 'LONG'
                
                # Entry level logic based on cloud
                if signals['current_new_long']:
                    # For new signals, enter at current price if close to cloud top
                    distance_to_cloud = abs(current_price - cloud_high_current) / current_price * 100
                    if distance_to_cloud <= 2.0:  # Within 2% of cloud top
                        entry_level = current_price
                    else:
                        entry_level = cloud_high_current + (cloud_high_current * 0.002)  # 0.2% above cloud
                else:
                    # For active signals, use cloud top as entry reference
                    entry_level = cloud_high_current
                
                # Stop Loss levels (multiple options)
                stop_loss_options = {
                    'conservative': cloud_low_current,      # Safest - below cloud
                    'aggressive': kijun_current,            # Moderate - at Kijun line
                    'tight': tenkan_current                 # Risky - at Tenkan line
                }
                
                stop_loss = stop_loss_options['conservative']  # Default to conservative
                
                # Target levels based on risk-reward ratios
                risk_amount = entry_level - stop_loss
                target1 = entry_level + (risk_amount * 1.5)  # 1:1.5 risk-reward
                target2 = entry_level + (risk_amount * 2.5)  # 1:2.5 risk-reward
                target3 = entry_level + (risk_amount * 4.0)  # 1:4.0 risk-reward
                
            elif signals['current_new_short'] or signals['current_short']:
                signal_type = 'SHORT'
                
                # Entry level logic for short signals
                if signals['current_new_short']:
                    # For new short signals, enter at current price if close to cloud bottom
                    distance_to_cloud = abs(current_price - cloud_low_current) / current_price * 100
                    if distance_to_cloud <= 2.0:  # Within 2% of cloud bottom
                        entry_level = current_price
                    else:
                        entry_level = cloud_low_current - (cloud_low_current * 0.002)  # 0.2% below cloud
                else:
                    # For active signals, use cloud bottom as entry reference
                    entry_level = cloud_low_current
                
                # Stop Loss levels for short positions
                stop_loss_options = {
                    'conservative': cloud_high_current,     # Safest - above cloud
                    'aggressive': kijun_current,            # Moderate - at Kijun line  
                    'tight': tenkan_current                 # Risky - at Tenkan line
                }
                
                stop_loss = stop_loss_options['conservative']  # Default to conservative
                
                # Target levels for short positions
                risk_amount = stop_loss - entry_level
                target1 = entry_level - (risk_amount * 1.5)  # 1:1.5 risk-reward
                target2 = entry_level - (risk_amount * 2.5)  # 1:2.5 risk-reward  
                target3 = entry_level - (risk_amount * 4.0)  # 1:4.0 risk-reward
                
            else:
                signal_type = 'NO_SIGNAL'
                entry_level = current_price
                stop_loss = None
                target1 = None
                target2 = None
                target3 = None
                stop_loss_options = {}
            
            # Calculate risk metrics
            if stop_loss:
                risk_per_share = abs(entry_level - stop_loss)
                risk_percent = (risk_per_share / entry_level) * 100
                
                # Position sizing based on 1% portfolio risk
                capital = 100000  # Default ₹1 lakh capital
                risk_amount_total = capital * 0.01  # 1% risk
                position_size = int(risk_amount_total / risk_per_share) if risk_per_share > 0 else 0
                total_investment = position_size * entry_level
                
                # Risk-reward ratios
                if target1:
                    reward1 = abs(target1 - entry_level)
                    rr_ratio1 = reward1 / risk_per_share if risk_per_share > 0 else 0
                else:
                    rr_ratio1 = 0
                    
                if target2:
                    reward2 = abs(target2 - entry_level)
                    rr_ratio2 = reward2 / risk_per_share if risk_per_share > 0 else 0
                else:
                    rr_ratio2 = 0
            else:
                risk_per_share = 0
                risk_percent = 0
                position_size = 0
                total_investment = 0
                rr_ratio1 = 0
                rr_ratio2 = 0
            
            # Calculate distance from current price to entry level
            if signal_type != 'NO_SIGNAL':
                distance_pct = abs((current_price - entry_level) / entry_level * 100)
            else:
                distance_pct = 0
            
            # Determine action and strength
            if signal_type == 'LONG':
                if signals['current_new_long']:
                    action = 'STRONG BUY'
                    action_emoji = '🟢 STRONG BUY'
                    strength = 100
                else:
                    action = 'BUY'
                    action_emoji = '🟢 BUY'
                    strength = 75
            elif signal_type == 'SHORT':
                if signals['current_new_short']:
                    action = 'STRONG SELL'
                    action_emoji = '🔴 STRONG SELL'
                    strength = 100
                else:
                    action = 'SELL'
                    action_emoji = '🔴 SELL'
                    strength = 75
            else:
                action = 'HOLD'
                action_emoji = '🟡 HOLD'
                strength = 0
            
            # Signal quality assessment
            quality_score = 0
            quality_factors = []
            
            if signal_type != 'NO_SIGNAL':
                # Distance factor (closer to entry = better)
                if distance_pct <= 0.5:
                    quality_score += 25
                    quality_factors.append("Perfect Entry Distance")
                elif distance_pct <= 2.0:
                    quality_score += 15
                    quality_factors.append("Good Entry Distance")
                
                # Risk-reward factor
                if rr_ratio1 >= 2.0:
                    quality_score += 25
                    quality_factors.append("Excellent Risk-Reward")
                elif rr_ratio1 >= 1.5:
                    quality_score += 15
                    quality_factors.append("Good Risk-Reward")
                
                # Risk percentage factor
                if risk_percent <= 3.0:
                    quality_score += 25
                    quality_factors.append("Low Risk")
                elif risk_percent <= 5.0:
                    quality_score += 15
                    quality_factors.append("Moderate Risk")
                
                # New signal bonus
                if signals['current_new_long'] or signals['current_new_short']:
                    quality_score += 25
                    quality_factors.append("Fresh Signal")
            
            # Quality classification
            if quality_score >= 80:
                quality = "EXCELLENT"
            elif quality_score >= 60:
                quality = "GOOD"
            elif quality_score >= 40:
                quality = "FAIR"
            else:
                quality = "POOR"
            
            return {
                'signal_type': signal_type,
                'action': action,
                'action_emoji': action_emoji,
                'strength': strength,
                'quality': quality,
                'quality_score': quality_score,
                'quality_factors': quality_factors,
                'entry_level': float(entry_level),
                'current_price': float(current_price),
                'distance_pct': float(distance_pct),
                'stop_loss': float(stop_loss) if stop_loss else None,
                'stop_loss_options': {k: float(v) for k, v in stop_loss_options.items()},
                'target1': float(target1) if target1 else None,
                'target2': float(target2) if target2 else None,
                'target3': float(target3) if target3 else None,
                'risk_per_share': float(risk_per_share),
                'risk_percent': float(risk_percent),
                'rr_ratio1': float(rr_ratio1),
                'rr_ratio2': float(rr_ratio2),
                'position_size': int(position_size),
                'total_investment': float(total_investment),
                'tenkan_level': float(tenkan_current),
                'kijun_level': float(kijun_current),
                'cloud_high': float(cloud_high_current),
                'cloud_low': float(cloud_low_current)
            }
            
        except Exception as e:
            print(f"❌ Error calculating trading levels: {e}")
            return None
    
    def analyze_stock(self, ticker, days=200):
        """Analyze a single stock with enhanced Ichimoku including trading levels"""
        try:
            print(f"📊 Analyzing {ticker} with Enhanced Ichimoku...")
            
            # Get data
            data = get_stock_data(ticker, days)
            if data is None:
                return None
            
            print(f"   📅 Data: {len(data)} trading days available")
            
            # Calculate Ichimoku
            try:
                ichimoku_data = self.calculate_ichimoku(data)
                signals = self.calculate_signals(ichimoku_data)
                trading_levels = self.calculate_trading_levels(data, ichimoku_data, signals)
            except Exception as e:
                print(f"   ❌ Error in Ichimoku calculations: {e}")
                return None
            
            if not trading_levels:
                return None
            
            # Calculate additional metrics
            current_price = data['Close'].iloc[-1]
            current_volume = data['Volume'].iloc[-1]
            rsi = self.calculate_rsi(data['Close'])
            volume_ratio = self.calculate_volume_ratio(data)
            momentum = self.calculate_momentum(data)
            
            # Display analysis
            print(f"   💰 Current Price: ₹{current_price:.2f}")
            print(f"   🎯 Action: {trading_levels['action_emoji']}")
            print(f"   📊 Signal Quality: {trading_levels['quality']} ({trading_levels['quality_score']}/100)")
            print(f"   📈 RSI: {rsi:.1f}")
            
            if trading_levels['signal_type'] != 'NO_SIGNAL':
                print(f"   💎 Entry Level: ₹{trading_levels['entry_level']:.2f}")
                print(f"   📏 Distance: {trading_levels['distance_pct']:.2f}% from entry")
                print(f"   🛑 Stop Loss: ₹{trading_levels['stop_loss']:.2f}")
                print(f"   🎯 Target 1: ₹{trading_levels['target1']:.2f} (R:R {trading_levels['rr_ratio1']:.1f})")
                print(f"   🎯 Target 2: ₹{trading_levels['target2']:.2f} (R:R {trading_levels['rr_ratio2']:.1f})")
                print(f"   ⚠️  Risk: {trading_levels['risk_percent']:.1f}% per share")
                print(f"   📊 Position: {trading_levels['position_size']} shares (₹{trading_levels['total_investment']:,.0f})")
            
            # Parameter status
            print(f"\n   📋 4-PARAMETER STATUS:")
            cloud_status = signals['cloud_bullish'].iloc[-1] if len(signals['cloud_bullish']) > 0 else False
            price_above = signals['price_above_cloud'].iloc[-1] if len(signals['price_above_cloud']) > 0 else False
            price_below = signals['price_below_cloud'].iloc[-1] if len(signals['price_below_cloud']) > 0 else False
            tk_status = signals['tk_bullish'].iloc[-1] if len(signals['tk_bullish']) > 0 else False
            chikou_bull = signals['chikou_bullish'].iloc[-1] if len(signals['chikou_bullish']) > 0 else False
            chikou_bear = signals['chikou_bearish'].iloc[-1] if len(signals['chikou_bearish']) > 0 else False
            
            print(f"   1️⃣ Cloud Color: {'🟢 BULLISH' if cloud_status else '🔴 BEARISH'}")
            print(f"   2️⃣ Price vs Cloud: {'🟢 ABOVE' if price_above else '🔴 BELOW' if price_below else '🟡 INSIDE'}")
            print(f"   3️⃣ Tenkan-Kijun: {'🟢 BULLISH' if tk_status else '🔴 BEARISH'}")
            print(f"   4️⃣ Chikou Span: {'🟢 BULLISH' if chikou_bull else '🔴 BEARISH' if chikou_bear else '🟡 NEUTRAL'}")
            
            return {
                'ticker': ticker,
                'sector': get_stock_sector(ticker),
                'current_price': float(current_price),
                'current_volume': float(current_volume),
                'volume_ratio': float(volume_ratio),
                'momentum': float(momentum),
                'rsi': float(rsi),
                'cloud_bullish': bool(cloud_status),
                'price_above_cloud': bool(price_above),
                'price_below_cloud': bool(price_below),
                'price_in_cloud': bool(not price_above and not price_below),
                'tk_bullish': bool(tk_status),
                'chikou_bullish': bool(chikou_bull),
                'chikou_bearish': bool(chikou_bear),
                'long_signal': bool(signals['current_long']),
                'short_signal': bool(signals['current_short']),
                'new_long_signal': bool(signals['current_new_long']),
                'new_short_signal': bool(signals['current_new_short']),
                'trading_days_used': len(data),
                'ichimoku_settings': f"T{self.tenkan_period}_K{self.kijun_period}_S{self.senkou_b_period}_D{self.displacement}",
                **trading_levels,  # Include all trading level data
                'ichimoku_data': ichimoku_data,
                'signals': signals,
                'data': data
            }
            
        except Exception as e:
            print(f"   ❌ Error analyzing {ticker}: {e}")
            return None
    
    def calculate_volume_ratio(self, data, period=20):
        """Calculate volume ratio vs average"""
        if len(data) < period + 1:
            return 1.0
        
        current_volume = data['Volume'].iloc[-1]
        avg_volume = data['Volume'].rolling(window=period).mean().iloc[-1]
        
        return current_volume / avg_volume if avg_volume > 0 else 1.0
    
    def calculate_momentum(self, data, period=5):
        """Calculate momentum over period"""
        if len(data) < period + 1:
            return 0.0
        
        current_price = data['Close'].iloc[-1]
        past_price = data['Close'].iloc[-(period+1)]
        
        return ((current_price - past_price) / past_price) * 100

def analyze_all_stocks_enhanced(analyzer, max_workers=3, distance_filter=2.0):
    """Analyze all stocks with enhanced features including trading levels"""
    
    tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
    
    print(f"\n🚀 ENHANCED ICHIMOKU ANALYSIS WITH TRADING LEVELS")
    print(f"📊 Analyzing {len(tickers)} stocks")
    print(f"🎯 Distance Filter: ≤{distance_filter}% from entry price")
    ichimoku_settings = f"Tenkan({analyzer.tenkan_period}), Kijun({analyzer.kijun_period}), Senkou B({analyzer.senkou_b_period}), Displacement({analyzer.displacement})"
    print(f"⚙️  Settings: {ichimoku_settings}")
    print("="*80)
    
    all_results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(analyzer.analyze_stock, ticker): ticker 
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
                    all_results.append(result)
                    successful += 1
                    
                    signal_indicator = ""
                    if result.get('signal_type') == 'LONG':
                        signal_indicator = f" 🟢{result.get('action', 'BUY')}"
                    elif result.get('signal_type') == 'SHORT':
                        signal_indicator = f" 🔴{result.get('action', 'SELL')}"
                    else:
                        signal_indicator = " 🟡HOLD"
                    
                    quality_indicator = f" [{result.get('quality', 'N/A')}]"
                    print(f"✅ {ticker} ({completed}/{len(tickers)}){signal_indicator}{quality_indicator}")
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
        print(f"   📈 Total analyzed: {len(all_results)}")
    
    return all_results

def display_enhanced_signals(all_results, distance_filter=2.0):
    """Display enhanced signals with trading levels and filtering"""
    
    if not all_results:
        print(f"\n❌ No signals found!")
        return
    
    # Filter results by distance and signal type
    actionable_signals = []
    all_signals = []
    
    for result in all_results:
        if result.get('signal_type') != 'NO_SIGNAL':
            all_signals.append(result)
            
            # Check if within distance threshold
            distance = result.get('distance_pct', 100)
            if distance <= distance_filter:
                actionable_signals.append(result)
    
    # Sort by quality score and strength
    actionable_signals.sort(key=lambda x: (x.get('quality_score', 0), x.get('strength', 0)), reverse=True)
    all_signals.sort(key=lambda x: (x.get('quality_score', 0), x.get('strength', 0)), reverse=True)
    
    print(f"\n🎯 ACTIONABLE SIGNALS (≤{distance_filter}% from entry - {len(actionable_signals)} signals)")
    print("="*160)
    
    if actionable_signals:
        table_data = []
        headers = ['Rank', 'Ticker', 'Action', 'Quality', 'Price', 'Entry', 'Distance%', 'Stop Loss', 'Target 1', 'Target 2', 'Risk%', 'R:R', 'Position', 'RSI']
        
        for i, result in enumerate(actionable_signals, 1):
            table_data.append([
                i,
                result['ticker'],
                result.get('action', 'HOLD'),
                result.get('quality', 'N/A'),
                f"₹{result['current_price']:.2f}",
                f"₹{result['entry_level']:.2f}",
                f"{result.get('distance_pct', 0):.2f}%",
                f"₹{result['stop_loss']:.2f}" if result.get('stop_loss') else "N/A",
                f"₹{result['target1']:.2f}" if result.get('target1') else "N/A",
                f"₹{result['target2']:.2f}" if result.get('target2') else "N/A",
                f"{result.get('risk_percent', 0):.1f}%",
                f"1:{result.get('rr_ratio1', 0):.1f}",
                f"{result.get('position_size', 0)} shares",
                f"{result['rsi']:.0f}"
            ])
        
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    else:
        print("   ❌ No actionable signals within distance threshold!")
    
    # Show all signals summary
    if all_signals:
        print(f"\n📊 ALL SIGNALS SUMMARY ({len(all_signals)} total signals)")
        print("="*120)
        
        table_data = []
        headers = ['Rank', 'Ticker', 'Sector', 'Action', 'Price', 'Distance%', 'Quality', 'Risk%', 'RSI']
        
        for i, result in enumerate(all_signals[:20], 1):  # Top 20
            table_data.append([
                i,
                result['ticker'],
                result.get('sector', 'Others'),
                result.get('action', 'HOLD'),
                f"₹{result['current_price']:.2f}",
                f"{result.get('distance_pct', 0):.2f}%",
                result.get('quality', 'N/A'),
                f"{result.get('risk_percent', 0):.1f}%",
                f"{result['rsi']:.0f}"
            ])
        
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    return actionable_signals, all_signals

def main():
    """Main function with enhanced Ichimoku analysis"""
    parser = argparse.ArgumentParser(description="Enhanced Ichimoku Analyzer with Trading Levels")
    
    parser.add_argument('--tenkan', type=int, default=9, 
                       help='Tenkan-Sen period (default: 9)')
    parser.add_argument('--kijun', type=int, default=26, 
                       help='Kijun-Sen period (default: 26)')
    parser.add_argument('--senkou-b', type=int, default=52, 
                       help='Senkou Span B period (default: 52)')
    parser.add_argument('--displacement', type=int, default=26, 
                       help='Displacement period (default: 26)')
    parser.add_argument('--ticker', type=str, 
                       help='Single ticker to analyze')
    parser.add_argument('--distance', type=float, default=2.0, 
                       help='Maximum distance from entry price in %% (default: 2.0)')
    parser.add_argument('--workers', type=int, default=3, 
                       help='Max concurrent workers (default: 3)')
    parser.add_argument('--days', type=int, default=200, 
                       help='Number of days of data to analyze (default: 200)')
    
    args = parser.parse_args()
    
    print("🚀 ENHANCED ICHIMOKU ANALYZER")
    print("📊 Complete Trading System with Entry, Stop Loss & Targets")
    print("="*60)
    print(f"⚙️  Settings: Tenkan({args.tenkan}), Kijun({args.kijun}), Senkou B({args.senkou_b}), Displacement({args.displacement})")
    print(f"📅 Data Period: {args.days} days")
    print(f"🎯 Distance Filter: ≤{args.distance}% from entry")
    print(f"🏭 Workers: {args.workers}")
    print("="*60)
    
    # Create enhanced analyzer
    analyzer = EnhancedIchimokuAnalyzer(
        tenkan_period=args.tenkan,
        kijun_period=args.kijun,
        senkou_b_period=args.senkou_b,
        displacement=args.displacement
    )
    
    if args.ticker:
        # Single ticker analysis
        print(f"🎯 SINGLE TICKER ANALYSIS: {args.ticker}")
        print("="*40)
        result = analyzer.analyze_stock(args.ticker, args.days)
        if result:
            print(f"\n✅ Analysis Complete for {args.ticker}!")
        else:
            print(f"\n❌ Analysis failed for {args.ticker}")
    else:
        # Comprehensive analysis
        print(f"🎯 COMPREHENSIVE ENHANCED ANALYSIS")
        print("="*50)
        
        all_results = analyze_all_stocks_enhanced(analyzer, args.workers, args.distance)
        
        if not all_results:
            print("\n❌ No successful analyses!")
            return
        
        # Display enhanced results
        actionable_signals, all_signals = display_enhanced_signals(all_results, args.distance)
        
        # Summary statistics
        total_long = len([r for r in all_signals if r.get('signal_type') == 'LONG'])
        total_short = len([r for r in all_signals if r.get('signal_type') == 'SHORT'])
        actionable_long = len([r for r in actionable_signals if r.get('signal_type') == 'LONG'])
        actionable_short = len([r for r in actionable_signals if r.get('signal_type') == 'SHORT'])
        
        print(f"\n📊 SUMMARY STATISTICS:")
        print(f"   📈 Total Signals: {len(all_signals)} (Long: {total_long}, Short: {total_short})")
        print(f"   🎯 Actionable Signals: {len(actionable_signals)} (Long: {actionable_long}, Short: {actionable_short})")
        print(f"   📏 Distance Threshold: ≤{args.distance}%")
        
        if actionable_signals:
            avg_risk = sum(r.get('risk_percent', 0) for r in actionable_signals) / len(actionable_signals)
            avg_rr = sum(r.get('rr_ratio1', 0) for r in actionable_signals) / len(actionable_signals)
            excellent_quality = len([r for r in actionable_signals if r.get('quality') == 'EXCELLENT'])
            
            print(f"   ⚠️  Average Risk: {avg_risk:.1f}%")
            print(f"   🎯 Average R:R: 1:{avg_rr:.1f}")
            print(f"   ⭐ Excellent Quality: {excellent_quality}")
        
        print(f"\n✅ Enhanced Analysis Complete!")

if __name__ == '__main__':
    main()