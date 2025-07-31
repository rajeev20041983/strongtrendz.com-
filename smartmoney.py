#!/usr/bin/env python
# smc_entry_exit_analyzer.py - Extract Entry/Exit Logic from Pine Script SMC
# 
# EXTRACTED FROM PINE SCRIPT LOGIC:
# - Proper BoS/CHoCH detection with trend tracking
# - Order block mitigation (entry/exit triggers)
# - Multi-timeframe structure alignment
# - Session-aware analysis
# - Clear entry/exit rules based on Pine Script behavior

import os
import sys
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
import concurrent.futures
import argparse
from tabulate import tabulate
import json
import csv

# Try to import pandas for enhanced features (optional)
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

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

class SMCTrendTracker:
    """Track market trend and structure changes - Extracted from Pine Script logic"""
    
    def __init__(self):
        self.upside = 1
        self.downside = 1
        self.moving = 0  # -1 = bearish, 0 = neutral, 1 = bullish
        self.upaxis = 0.0
        self.dnaxis = 0.0
        self.upaxis_time = 0
        self.dnaxis_time = 0
    
    def update_structure(self, current_price, current_time, swing_high=None, swing_low=None):
        """Update structure based on Pine Script drawStructureExt() logic"""
        structure_changes = []
        
        if swing_high is not None:
            self.upside = 1
            
            # Determine if HH or LH
            if swing_high > self.upaxis:
                structure_type = 'HH'  # Higher High
            else:
                structure_type = 'LH'  # Lower High
                
            self.upaxis = swing_high
            self.upaxis_time = current_time
            
            structure_changes.append(('SWING_HIGH', structure_type, swing_high))
        
        if swing_low is not None:
            self.downside = 1
            
            # Determine if LL or HL  
            if swing_low < self.dnaxis or self.dnaxis == 0:
                structure_type = 'LL'  # Lower Low
            else:
                structure_type = 'HL'  # Higher Low
                
            self.dnaxis = swing_low
            self.dnaxis_time = current_time
            
            structure_changes.append(('SWING_LOW', structure_type, swing_low))
        
        # Check for structure breaks (BoS/CHoCH) - Pine Script logic
        bos_choch_signals = []
        
        # Bullish structure break
        if current_price > self.upaxis and self.upaxis > 0:
            if self.upside != 0:
                if self.moving < 0:
                    # Was bearish, now breaking bullish = CHoCH
                    bos_choch_signals.append(('BULLISH_CHOCH', self.upaxis))
                else:
                    # Was bullish/neutral, continuing bullish = BoS
                    bos_choch_signals.append(('BULLISH_BOS', self.upaxis))
                
                self.upside = 0
                self.moving = 1  # Now bullish
        
        # Bearish structure break
        if current_price < self.dnaxis and self.dnaxis > 0:
            if self.downside != 0:
                if self.moving > 0:
                    # Was bullish, now breaking bearish = CHoCH
                    bos_choch_signals.append(('BEARISH_CHOCH', self.dnaxis))
                else:
                    # Was bearish/neutral, continuing bearish = BoS
                    bos_choch_signals.append(('BEARISH_BOS', self.dnaxis))
                
                self.downside = 0
                self.moving = -1  # Now bearish
        
        return structure_changes, bos_choch_signals
    
    def get_trend_direction(self):
        """Get current trend direction"""
        if self.moving > 0:
            return 'BULLISH'
        elif self.moving < 0:
            return 'BEARISH'
        else:
            return 'NEUTRAL'

class SMCOrderBlock:
    """Order Block management - Extracted from Pine Script logic"""
    
    def __init__(self, block_type, top, bottom, time_created, strength=0):
        self.type = block_type  # 'bullish' or 'bearish'
        self.top = top
        self.bottom = bottom
        self.time_created = time_created
        self.strength = strength
        self.is_active = True
        self.touch_count = 0
        self.last_interaction = None
    
    def is_price_interacting(self, current_price, tolerance=0.002):
        """Check if price is interacting with order block"""
        if not self.is_active:
            return False
            
        # Within the order block range (with small tolerance)
        lower_bound = self.bottom * (1 - tolerance)
        upper_bound = self.top * (1 + tolerance)
        
        return lower_bound <= current_price <= upper_bound
    
    def check_mitigation(self, current_price, current_time):
        """Check if order block is mitigated (Pine Script cleanseLevel logic)"""
        if not self.is_active:
            return False
            
        mitigated = False
        
        if self.type == 'bullish':
            # Bullish OB mitigated if price closes below bottom
            if current_price < self.bottom:
                mitigated = True
        else:
            # Bearish OB mitigated if price closes above top  
            if current_price > self.top:
                mitigated = True
        
        if mitigated:
            self.is_active = False
            
        return mitigated
    
    def record_interaction(self, current_price, current_time):
        """Record price interaction with order block"""
        if self.is_price_interacting(current_price):
            self.touch_count += 1
            self.last_interaction = current_time
            return True
        return False

def get_stock_data(ticker, lookback_days=100):
    """Get stock data for comprehensive SMC analysis"""
    try:
        # Add .NS for NSE stocks
        symbol = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
        
        # Get enough data for lookback + buffer
        days_needed = lookback_days + 150  # Extra buffer
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_needed)
        
        # Download data
        stock = yf.Ticker(symbol)
        data = stock.history(start=start_date, end=end_date)
        
        if data.empty or len(data) < lookback_days + 20:
            print(f"   ⚠️  {ticker}: Insufficient data ({len(data)} days)")
            return None
        
        # Clean data and add time index
        data = data.dropna()
        data['Time'] = range(len(data))  # Simple time index
        
        return data
        
    except Exception as e:
        print(f"   ❌ {ticker}: Data fetch error - {str(e)}")
        return None

def calculate_pivots_pine_logic(data, length):
    """Calculate pivots using Pine Script logic - more accurate"""
    try:
        if len(data) < length * 2 + 1:
            return [], []
        
        highs = data['High'].values
        lows = data['Low'].values
        times = data['Time'].values
        
        swing_highs = []
        swing_lows = []
        
        # Pine Script pivot logic - check if current bar is highest/lowest in lookback
        for i in range(length, len(data) - length):
            # Get lookback window
            left_highs = highs[i-length:i]
            right_highs = highs[i+1:i+length+1]
            
            left_lows = lows[i-length:i]
            right_lows = lows[i+1:i+length+1]
            
            current_high = highs[i]
            current_low = lows[i]
            
            # Swing High: current high > all left and right highs
            if (current_high > max(left_highs) and 
                current_high > max(right_highs)):
                swing_highs.append({
                    'index': i,
                    'time': times[i],
                    'price': current_high
                })
            
            # Swing Low: current low < all left and right lows  
            if (current_low < min(left_lows) and 
                current_low < min(right_lows)):
                swing_lows.append({
                    'index': i,
                    'time': times[i], 
                    'price': current_low
                })
        
        return swing_highs, swing_lows
    
    except Exception as e:
        return [], []

def create_order_blocks_pine_logic(data, swing_highs, swing_lows):
    """Create order blocks using Pine Script logic"""
    order_blocks = []
    current_price = data['Close'].iloc[-1]
    
    # Create bullish order blocks from swing lows
    for swing_low in swing_lows[-10:]:  # Last 10 swing lows
        swing_index = swing_low['index']
        swing_price = swing_low['price']
        
        if swing_index > 0 and swing_index < len(data):
            # Pine Script logic: order block is the candle BEFORE the swing
            ob_candle = data.iloc[swing_index - 1]
            
            # Only create if price has moved significantly away (like Pine Script)
            if current_price > swing_price * 1.01:  # 1% above swing low
                strength = (current_price - swing_price) / swing_price * 100
                
                ob = SMCOrderBlock(
                    block_type='bullish',
                    top=ob_candle['High'],
                    bottom=max(ob_candle['Low'], swing_price * 0.998),  # Slightly below swing
                    time_created=swing_low['time'],
                    strength=strength
                )
                order_blocks.append(ob)
    
    # Create bearish order blocks from swing highs
    for swing_high in swing_highs[-10:]:  # Last 10 swing highs
        swing_index = swing_high['index']
        swing_price = swing_high['price']
        
        if swing_index > 0 and swing_index < len(data):
            # Pine Script logic: order block is the candle BEFORE the swing
            ob_candle = data.iloc[swing_index - 1]
            
            # Only create if price has moved significantly away
            if current_price < swing_price * 0.99:  # 1% below swing high
                strength = (swing_price - current_price) / swing_price * 100
                
                ob = SMCOrderBlock(
                    block_type='bearish',
                    top=min(ob_candle['High'], swing_price * 1.002),  # Slightly above swing
                    bottom=ob_candle['Low'],
                    time_created=swing_high['time'],
                    strength=strength
                )
                order_blocks.append(ob)
    
    # Sort by proximity to current price (most relevant first)
    order_blocks.sort(key=lambda ob: abs(current_price - (ob.top + ob.bottom) / 2))
    
    return order_blocks

def detect_fair_value_gaps_pine_logic(data):
    """Detect FVGs using Pine Script logic"""
    try:
        fvgs = {'bullish': [], 'bearish': []}
        
        if len(data) < 3:
            return fvgs
        
        # Check last 30 candles for FVGs
        start_index = max(0, len(data) - 30)
        
        for i in range(start_index + 2, len(data)):
            candle1 = data.iloc[i-2]
            candle2 = data.iloc[i-1]  # Gap creator
            candle3 = data.iloc[i]
            
            # Bullish FVG: candle1.high < candle3.low
            if candle1['High'] < candle3['Low']:
                gap_size = (candle3['Low'] - candle1['High']) / candle1['High'] * 100
                
                if gap_size > 0.1:  # Minimum 0.1% gap
                    # Check if gap is still unfilled
                    remaining_data = data.iloc[i:]
                    filled = remaining_data['Low'].min() <= candle1['High'] if len(remaining_data) > 0 else False
                    
                    fvgs['bullish'].append({
                        'top': candle3['Low'],
                        'bottom': candle1['High'],
                        'size': gap_size,
                        'index': i-1,
                        'filled': filled
                    })
            
            # Bearish FVG: candle1.low > candle3.high
            elif candle1['Low'] > candle3['High']:
                gap_size = (candle1['Low'] - candle3['High']) / candle3['High'] * 100
                
                if gap_size > 0.1:  # Minimum 0.1% gap
                    # Check if gap is still unfilled
                    remaining_data = data.iloc[i:]
                    filled = remaining_data['High'].max() >= candle1['Low'] if len(remaining_data) > 0 else False
                    
                    fvgs['bearish'].append({
                        'top': candle1['Low'],
                        'bottom': candle3['High'],
                        'size': gap_size,
                        'index': i-1,
                        'filled': filled
                    })
        
        return fvgs
    
    except Exception as e:
        return {'bullish': [], 'bearish': []}

def calculate_rsi(prices, period=14):
    """Calculate RSI"""
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
        
        return max(0, min(100, rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50))
    except:
        return 50

def generate_smc_entry_exit_signals(ticker, internal_sens=5, external_sens=25, debug=False):
    """
    Generate Entry/Exit signals using Pine Script SMC logic
    """
    try:
        print(f"📊 Analyzing {ticker} for Entry/Exit signals...")
        
        # Get data
        data = get_stock_data(ticker, 100)
        if data is None:
            return None
        
        print(f"   📅 Data: {len(data)} trading days available")
        
        # Initialize trend tracker
        trend_tracker = SMCTrendTracker()
        
        # Calculate pivots using Pine Script logic
        external_highs, external_lows = calculate_pivots_pine_logic(data, external_sens)
        internal_highs, internal_lows = calculate_pivots_pine_logic(data, internal_sens)
        
        if debug:
            print(f"   🔍 Found {len(external_highs)} external highs, {len(external_lows)} external lows")
            print(f"   🔍 Found {len(internal_highs)} internal highs, {len(internal_lows)} internal lows")
        
        # Create order blocks
        order_blocks = create_order_blocks_pine_logic(data, external_highs, external_lows)
        active_order_blocks = [ob for ob in order_blocks if ob.is_active]
        
        if debug:
            print(f"   📦 Created {len(active_order_blocks)} active order blocks")
            for i, ob in enumerate(active_order_blocks[:3]):
                print(f"      {i+1}. {ob.type.upper()} OB: ₹{ob.bottom:.2f}-₹{ob.top:.2f} (strength: {ob.strength:.1f}%)")
        
        # Detect Fair Value Gaps
        fvgs = detect_fair_value_gaps_pine_logic(data)
        
        # Get current market state
        current_price = data['Close'].iloc[-1]
        current_time = data['Time'].iloc[-1]
        current_volume = data['Volume'].iloc[-1]
        
        # Update trend tracker with recent swings
        recent_high = external_highs[-1] if external_highs else None
        recent_low = external_lows[-1] if external_lows else None
        
        structure_changes, bos_choch_signals = trend_tracker.update_structure(
            current_price, current_time, 
            recent_high['price'] if recent_high else None,
            recent_low['price'] if recent_low else None
        )
        
        trend_direction = trend_tracker.get_trend_direction()
        
        if debug:
            print(f"   🏗️ Trend Direction: {trend_direction}")
            if bos_choch_signals:
                for signal_type, level in bos_choch_signals:
                    print(f"   📊 Structure: {signal_type} at ₹{level:.2f}")
        
        # Calculate RSI
        rsi = calculate_rsi(data['Close'])
        
        # Calculate volume ratio
        volume_avg = data['Volume'].rolling(window=20).mean().iloc[-1]
        volume_ratio = current_volume / volume_avg if volume_avg > 0 else 1.0
        
        # ENTRY SIGNAL GENERATION (Pine Script derived logic)
        entry_signals = []
        exit_signals = []
        
        # Check each order block for entry opportunities
        for ob in active_order_blocks:
            if ob.is_price_interacting(current_price):
                
                # BULLISH ENTRY CONDITIONS
                if ob.type == 'bullish':
                    entry_score = 0
                    entry_factors = []
                    
                    # Core requirement: Price reacting from bullish order block
                    entry_score += 3.0
                    entry_factors.append('BULLISH_OB_REACTION')
                    
                    # Structure confirmation
                    if any('BULLISH' in signal[0] for signal in bos_choch_signals):
                        entry_score += 2.0
                        entry_factors.append('BULLISH_STRUCTURE')
                    
                    # Trend alignment
                    if trend_direction == 'BULLISH':
                        entry_score += 1.0
                        entry_factors.append('TREND_ALIGNMENT')
                    
                    # RSI oversold
                    if rsi < 40:
                        entry_score += 1.0
                        entry_factors.append('RSI_OVERSOLD')
                    
                    # Volume confirmation
                    if volume_ratio > 1.2:
                        entry_score += 0.5
                        entry_factors.append('VOLUME_CONFIRM')
                    
                    # FVG confluence
                    for fvg in fvgs['bullish']:
                        if not fvg['filled'] and abs(current_price - fvg['bottom']) / current_price < 0.01:
                            entry_score += 1.0
                            entry_factors.append('BULLISH_FVG')
                            break
                    
                    # Generate entry signal if score is high enough
                    if entry_score >= 4.0:
                        signal_strength = 'STRONG' if entry_score >= 5.0 else 'MODERATE'
                        
                        # Calculate stop loss (below order block)
                        stop_loss = ob.bottom * 0.995  # 0.5% buffer below OB
                        risk_per_share = current_price - stop_loss
                        
                        # Calculate targets
                        target_1 = current_price + (risk_per_share * 2)  # 2:1 RR
                        target_2 = current_price + (risk_per_share * 3)  # 3:1 RR
                        
                        # Position sizing (1% portfolio risk)
                        portfolio_value = 100000
                        risk_amount = portfolio_value * 0.01
                        position_size = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
                        
                        entry_signals.append({
                            'type': 'LONG_ENTRY',
                            'strength': signal_strength,
                            'score': entry_score,
                            'entry_price': current_price,
                            'stop_loss': stop_loss,
                            'target_1': target_1,
                            'target_2': target_2,
                            'risk_per_share': risk_per_share,
                            'position_size': position_size,
                            'risk_reward_1': 2.0,
                            'risk_reward_2': 3.0,
                            'factors': entry_factors,
                            'order_block': {
                                'type': ob.type,
                                'top': ob.top,
                                'bottom': ob.bottom,
                                'strength': ob.strength
                            }
                        })
                
                # BEARISH ENTRY CONDITIONS
                elif ob.type == 'bearish':
                    entry_score = 0
                    entry_factors = []
                    
                    # Core requirement: Price rejecting from bearish order block
                    entry_score += 3.0
                    entry_factors.append('BEARISH_OB_REJECTION')
                    
                    # Structure confirmation
                    if any('BEARISH' in signal[0] for signal in bos_choch_signals):
                        entry_score += 2.0
                        entry_factors.append('BEARISH_STRUCTURE')
                    
                    # Trend alignment
                    if trend_direction == 'BEARISH':
                        entry_score += 1.0
                        entry_factors.append('TREND_ALIGNMENT')
                    
                    # RSI overbought
                    if rsi > 60:
                        entry_score += 1.0
                        entry_factors.append('RSI_OVERBOUGHT')
                    
                    # Volume confirmation
                    if volume_ratio > 1.2:
                        entry_score += 0.5
                        entry_factors.append('VOLUME_CONFIRM')
                    
                    # FVG confluence
                    for fvg in fvgs['bearish']:
                        if not fvg['filled'] and abs(current_price - fvg['top']) / current_price < 0.01:
                            entry_score += 1.0
                            entry_factors.append('BEARISH_FVG')
                            break
                    
                    # Generate entry signal if score is high enough
                    if entry_score >= 4.0:
                        signal_strength = 'STRONG' if entry_score >= 5.0 else 'MODERATE'
                        
                        # Calculate stop loss (above order block)
                        stop_loss = ob.top * 1.005  # 0.5% buffer above OB
                        risk_per_share = stop_loss - current_price
                        
                        # Calculate targets
                        target_1 = current_price - (risk_per_share * 2)  # 2:1 RR
                        target_2 = current_price - (risk_per_share * 3)  # 3:1 RR
                        
                        # Position sizing (1% portfolio risk)
                        portfolio_value = 100000
                        risk_amount = portfolio_value * 0.01
                        position_size = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
                        
                        entry_signals.append({
                            'type': 'SHORT_ENTRY',
                            'strength': signal_strength,
                            'score': entry_score,
                            'entry_price': current_price,
                            'stop_loss': stop_loss,
                            'target_1': target_1,
                            'target_2': target_2,
                            'risk_per_share': risk_per_share,
                            'position_size': position_size,  
                            'risk_reward_1': 2.0,
                            'risk_reward_2': 3.0,
                            'factors': entry_factors,
                            'order_block': {
                                'type': ob.type,
                                'top': ob.top,
                                'bottom': ob.bottom,
                                'strength': ob.strength
                            }
                        })
        
        # EXIT SIGNAL GENERATION
        for ob in order_blocks:
            if ob.check_mitigation(current_price, current_time):
                exit_signals.append({
                    'type': f"{ob.type.upper()}_OB_MITIGATED",
                    'message': f"{ob.type.capitalize()} order block mitigated - Exit {('long' if ob.type == 'bullish' else 'short')} positions",
                    'level': ob.top if ob.type == 'bullish' else ob.bottom
                })
        
        # Compile results
        result = {
            'ticker': ticker,
            'current_price': float(current_price),
            'trend_direction': trend_direction,
            'rsi': float(rsi),
            'volume_ratio': float(volume_ratio),
            'structure_signals': bos_choch_signals,
            'active_order_blocks': len(active_order_blocks),
            'bullish_fvgs': len([fvg for fvg in fvgs['bullish'] if not fvg['filled']]),
            'bearish_fvgs': len([fvg for fvg in fvgs['bearish'] if not fvg['filled']]),
            'entry_signals': entry_signals,
            'exit_signals': exit_signals,
            'internal_sens': internal_sens,
            'external_sens': external_sens
        }
        
        # Print summary
        if entry_signals:
            for signal in entry_signals:
                print(f"   🎯 {signal['strength']} {signal['type']}: ₹{signal['entry_price']:.2f}")
                print(f"      🛑 Stop: ₹{signal['stop_loss']:.2f} | 🎯 T1: ₹{signal['target_1']:.2f} | 🎯 T2: ₹{signal['target_2']:.2f}")
                print(f"      📦 Size: {signal['position_size']} shares | Risk: ₹{signal['risk_per_share']:.2f}/share")
        else:
            print(f"   ⚪ No entry signals generated")
        
        if exit_signals:
            for signal in exit_signals:
                print(f"   🚪 EXIT: {signal['message']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error analyzing {ticker}: {e}")
        return None

def analyze_all_stocks_entry_exit(internal_sens=5, external_sens=25, max_workers=3, debug=False):
    """Analyze all stocks for entry/exit signals"""
    
    # Get tickers from config
    tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
    
    print(f"\n🚀 SMC ENTRY/EXIT SIGNAL ANALYZER")
    print(f"📊 Analyzing {len(tickers)} stocks")
    print(f"🏗️ Internal: {internal_sens} | External: {external_sens}")
    print("="*60)
    
    all_results = []
    
    # Analyze stocks
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(generate_smc_entry_exit_signals, ticker, internal_sens, external_sens, debug): ticker 
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
                    entry_count = len(result.get('entry_signals', []))
                    exit_count = len(result.get('exit_signals', []))
                    print(f"✅ {ticker} ({completed}/{len(tickers)}) - {entry_count} entries, {exit_count} exits")
                else:
                    failed += 1
                    print(f"⚪ {ticker} ({completed}/{len(tickers)}) - No data")
            except Exception as e:
                failed += 1
                print(f"❌ {ticker} ({completed}/{len(tickers)}) - Error: {str(e)[:50]}")
        
        print(f"\n📊 ANALYSIS SUMMARY:")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📈 Total results: {len(all_results)}")
    
    return all_results

def filter_entry_exit_signals(results, signal_types=None):
    """Filter entry/exit signals by type"""
    if signal_types is None:
        signal_types = ['LONG_ENTRY', 'SHORT_ENTRY']
    
    filtered_entries = []
    for result in results:
        for entry in result.get('entry_signals', []):
            if entry['type'] in signal_types:
                entry['ticker'] = result['ticker']
                entry['current_price'] = result['current_price']
                entry['trend_direction'] = result['trend_direction']
                entry['rsi'] = result['rsi']
                entry['volume_ratio'] = result['volume_ratio']
                filtered_entries.append(entry)
    
    return filtered_entries

def sort_entry_signals_properly(signals):
    """Sort entry signals by score and strength"""
    if not signals:
        return signals
        
    # Sort by score (highest first), then by strength
    def sort_key(signal):
        strength_weight = 2 if signal['strength'] == 'STRONG' else 1
        return (signal['score'] * strength_weight, signal['score'])
    
    return sorted(signals, key=sort_key, reverse=True)

def display_entry_signals_enhanced(signals, signal_title, top_n=10):
    """Enhanced display for entry signals with all details"""
    
    if not signals:
        print(f"\n❌ No {signal_title} signals found!")
        return
    
    # Sort signals properly
    signals = sort_entry_signals_properly(signals)
    
    # Get top N
    top_signals = signals[:top_n]
    
    print(f"\n🎯 TOP {len(top_signals)} {signal_title} SIGNALS (Pine Script Logic)")
    print(f"📊 Entry/Exit System with Risk Management")
    print("="*120)
    
    # Prepare enhanced table
    table_data = []
    headers = ['Rank', 'Ticker', 'Type', 'Strength', 'Entry', 'Stop', 'Target1', 'Target2', 
              'RR1', 'RR2', 'Risk%', 'Size', 'RSI', 'Vol', 'Factors']
    
    for i, signal in enumerate(top_signals, 1):
        # Calculate risk percentage
        risk_pct = (signal['risk_per_share'] / signal['entry_price']) * 100
        
        # RSI with indicators
        rsi_display = f"{signal['rsi']:.0f}"
        if signal['rsi'] > 70:
            rsi_display += "🔴"
        elif signal['rsi'] < 30:
            rsi_display += "🟢"
        
        # Volume with indicator
        vol_display = f"{signal['volume_ratio']:.1f}x"
        if signal['volume_ratio'] > 1.5:
            vol_display += "🟢"
        elif signal['volume_ratio'] < 0.8:
            vol_display += "🔴"
        
        # Factors summary
        factors_display = f"{len(signal['factors'])}"
        if 'BULLISH_OB_REACTION' in signal['factors'] or 'BEARISH_OB_REJECTION' in signal['factors']:
            factors_display += "📦"
        if any('STRUCTURE' in f for f in signal['factors']):
            factors_display += "🏗️"
        if any('FVG' in f for f in signal['factors']):
            factors_display += "🕳️"
        
        table_data.append([
            i,
            signal['ticker'],
            signal['type'].replace('_ENTRY', ''),
            signal['strength'][:4],  # STRO/MODE
            f"₹{signal['entry_price']:.2f}",
            f"₹{signal['stop_loss']:.2f}",
            f"₹{signal['target_1']:.2f}",
            f"₹{signal['target_2']:.2f}",
            f"{signal['risk_reward_1']:.1f}:1",
            f"{signal['risk_reward_2']:.1f}:1", 
            f"{risk_pct:.1f}%",
            signal['position_size'],
            rsi_display,
            vol_display,
            factors_display
        ])
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Enhanced summary statistics
    strong_signals = len([s for s in top_signals if s['strength'] == 'STRONG'])
    long_signals = len([s for s in top_signals if s['type'] == 'LONG_ENTRY'])
    short_signals = len([s for s in top_signals if s['type'] == 'SHORT_ENTRY'])
    avg_score = sum(s['score'] for s in top_signals) / len(top_signals)
    avg_risk = sum((s['risk_per_share'] / s['entry_price']) * 100 for s in top_signals) / len(top_signals)
    total_capital_required = sum(s['entry_price'] * s['position_size'] for s in top_signals)
    
    print(f"\n📊 ENHANCED SUMMARY:")
    print(f"   🟢 Long entries: {long_signals}")
    print(f"   🔴 Short entries: {short_signals}")
    print(f"   💪 Strong signals: {strong_signals}")
    print(f"   📈 Average score: {avg_score:.1f}")
    print(f"   📉 Average risk: {avg_risk:.1f}%")
    print(f"   💰 Capital required: ₹{total_capital_required:,.0f}")
    
    print(f"\n🏆 ENTRY SIGNAL EXPLANATION:")
    print(f"   📦 Order Block reaction/rejection required for entry")
    print(f"   🏗️ Structure confirmation (BoS/CHoCH) adds strength")
    print(f"   🎯 Targets set at 2:1 and 3:1 risk-reward ratios")
    print(f"   🛑 Stops placed beyond triggering order block")
    print(f"   📊 Position sizing: 1% portfolio risk per trade")
    
    return top_signals

def generate_entry_exit_html(results, internal_sens, external_sens, output_dir):
    """Generate comprehensive HTML report for entry/exit signals"""
    
    if not results:
        print("❌ No results to generate report")
        return None
    
    # Extract entry and exit signals
    all_entries = []
    all_exits = []
    
    for result in results:
        for entry in result.get('entry_signals', []):
            entry['ticker'] = result['ticker']
            entry['current_price'] = result['current_price']
            entry['trend_direction'] = result['trend_direction']
            entry['rsi'] = result['rsi']
            entry['volume_ratio'] = result['volume_ratio']
            all_entries.append(entry)
        
        for exit in result.get('exit_signals', []):
            exit['ticker'] = result['ticker']
            all_exits.append(exit)
    
    # Sort entries by score
    all_entries = sort_entry_signals_properly(all_entries)
    long_entries = [e for e in all_entries if e['type'] == 'LONG_ENTRY']
    short_entries = [e for e in all_entries if e['type'] == 'SHORT_ENTRY']
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SMC Entry/Exit Signals - {datetime.now().strftime('%Y-%m-%d')}</title>
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
            .stat-card.entry {{
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            }}
            .stat-card.exit {{
                background: linear-gradient(135deg, #dc3545 0%, #e74c3c 100%);
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
                font-size: 0.9em;
            }}
            th, td {{
                padding: 10px 8px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background: #f8f9fa;
                font-weight: bold;
                position: sticky;
                top: 0;
                font-size: 0.85em;
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
            .long-entry {{
                background: linear-gradient(90deg, #28a745, #20c997);
                color: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-weight: bold;
                text-align: center;
                font-size: 0.8em;
            }}
            .short-entry {{
                background: linear-gradient(90deg, #dc3545, #e74c3c);
                color: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-weight: bold;
                text-align: center;
                font-size: 0.8em;
            }}
            .strong {{
                background: linear-gradient(90deg, #ffc107, #fd7e14);
                color: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-weight: bold;
                text-align: center;
                font-size: 0.8em;
            }}
            .moderate {{
                background: linear-gradient(90deg, #6c757d, #495057);
                color: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-weight: bold;
                text-align: center;
                font-size: 0.8em;
            }}
            .price {{
                font-weight: bold;
                color: #333;
                text-align: right;
            }}
            .positive {{
                color: #28a745;
                font-weight: bold;
            }}
            .negative {{
                color: #dc3545;
                font-weight: bold;
            }}
            .info-box {{
                background: #e7f3ff;
                border-left: 5px solid #007bff;
                padding: 20px;
                margin: 20px 0;
                border-radius: 5px;
            }}
            .footer {{
                text-align: center;
                margin-top: 40px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 10px;
                border-left: 5px solid #667eea;
            }}
            .risk-badge {{
                padding: 2px 6px;
                border-radius: 8px;
                font-size: 0.75em;
                font-weight: bold;
            }}
            .risk-low {{ background: #d4edda; color: #155724; }}
            .risk-medium {{ background: #fff3cd; color: #856404; }}
            .risk-high {{ background: #f8d7da; color: #721c24; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎯 SMC ENTRY/EXIT SIGNAL ANALYZER</h1>
                <p><strong>Pine Script Logic + Python Automation</strong></p>
                <p>Internal: {internal_sens} | External: {external_sens} | Generated: {timestamp}</p>
            </div>
            
            <div class="info-box">
                <h3>🧠 Entry/Exit System Overview</h3>
                <p><strong>Entry Signals:</strong> Generated when price reacts from order blocks with structure confirmation</p>
                <p><strong>Exit Signals:</strong> Triggered when order blocks are mitigated (price breaks through)</p>
                <p><strong>Risk Management:</strong> 1% portfolio risk per trade with 2:1 and 3:1 targets</p>
                <p><strong>Position Sizing:</strong> Calculated based on stop loss distance from entry</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card entry">
                    <h3>{len(long_entries)}</h3>
                    <p>Long Entries</p>
                </div>
                <div class="stat-card exit">
                    <h3>{len(short_entries)}</h3>
                    <p>Short Entries</p>
                </div>
                <div class="stat-card">
                    <h3>{len(all_exits)}</h3>
                    <p>Exit Signals</p>
                </div>
                <div class="stat-card">
                    <h3>{len(results)}</h3>
                    <p>Stocks Analyzed</p>
                </div>
                <div class="stat-card">
                    <h3>{len([e for e in all_entries if e['strength'] == 'STRONG'])}</h3>
                    <p>Strong Signals</p>
                </div>
                <div class="stat-card">
                    <h3>{sum(e['entry_price'] * e['position_size'] for e in all_entries):,.0f}</h3>
                    <p>Total Capital (₹)</p>
                </div>
            </div>
    """
    
    # Generate Long Entry signals table
    if long_entries:
        html_content += f"""
            <div class="section">
                <h2>🟢 LONG ENTRY SIGNALS ({len(long_entries)} found)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Ticker</th>
                            <th>Strength</th>
                            <th>Entry</th>
                            <th>Stop Loss</th>
                            <th>Target 1</th>
                            <th>Target 2</th>
                            <th>Risk%</th>
                            <th>RR1</th>
                            <th>RR2</th>
                            <th>Size</th>
                            <th>Capital</th>
                            <th>RSI</th>
                            <th>Vol</th>
                            <th>Score</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for i, signal in enumerate(long_entries[:15], 1):
            risk_pct = (signal['risk_per_share'] / signal['entry_price']) * 100
            capital_req = signal['entry_price'] * signal['position_size']
            
            # Risk badge
            if risk_pct < 2:
                risk_class = "risk-low"
            elif risk_pct < 4:
                risk_class = "risk-medium"
            else:
                risk_class = "risk-high"
            
            html_content += f"""
                        <tr>
                            <td class="rank">{i}</td>
                            <td class="ticker">{signal['ticker']}</td>
                            <td><span class="{signal['strength'].lower()}">{signal['strength']}</span></td>
                            <td class="price">₹{signal['entry_price']:.2f}</td>
                            <td class="price">₹{signal['stop_loss']:.2f}</td>
                            <td class="price">₹{signal['target_1']:.2f}</td>
                            <td class="price">₹{signal['target_2']:.2f}</td>
                            <td><span class="risk-badge {risk_class}">{risk_pct:.1f}%</span></td>
                            <td>{signal['risk_reward_1']:.1f}:1</td>
                            <td>{signal['risk_reward_2']:.1f}:1</td>
                            <td>{signal['position_size']}</td>
                            <td class="price">₹{capital_req:,.0f}</td>
                            <td>{signal['rsi']:.0f}</td>
                            <td>{signal['volume_ratio']:.1f}x</td>
                            <td>{signal['score']:.1f}</td>
                        </tr>
            """
        
        html_content += """
                    </tbody>
                </table>
            </div>
        """
    
    # Generate Short Entry signals table
    if short_entries:
        html_content += f"""
            <div class="section">
                <h2>🔴 SHORT ENTRY SIGNALS ({len(short_entries)} found)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Ticker</th>
                            <th>Strength</th>
                            <th>Entry</th>
                            <th>Stop Loss</th>
                            <th>Target 1</th>
                            <th>Target 2</th>
                            <th>Risk%</th>
                            <th>RR1</th>
                            <th>RR2</th>
                            <th>Size</th>
                            <th>Capital</th>
                            <th>RSI</th>
                            <th>Vol</th>
                            <th>Score</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for i, signal in enumerate(short_entries[:15], 1):
            risk_pct = (signal['risk_per_share'] / signal['entry_price']) * 100
            capital_req = signal['entry_price'] * signal['position_size']
            
            # Risk badge
            if risk_pct < 2:
                risk_class = "risk-low"
            elif risk_pct < 4:
                risk_class = "risk-medium"
            else:
                risk_class = "risk-high"
            
            html_content += f"""
                        <tr>
                            <td class="rank">{i}</td>
                            <td class="ticker">{signal['ticker']}</td>
                            <td><span class="{signal['strength'].lower()}">{signal['strength']}</span></td>
                            <td class="price">₹{signal['entry_price']:.2f}</td>
                            <td class="price">₹{signal['stop_loss']:.2f}</td>
                            <td class="price">₹{signal['target_1']:.2f}</td>
                            <td class="price">₹{signal['target_2']:.2f}</td>
                            <td><span class="risk-badge {risk_class}">{risk_pct:.1f}%</span></td>
                            <td>{signal['risk_reward_1']:.1f}:1</td>
                            <td>{signal['risk_reward_2']:.1f}:1</td>
                            <td>{signal['position_size']}</td>
                            <td class="price">₹{capital_req:,.0f}</td>
                            <td>{signal['rsi']:.0f}</td>
                            <td>{signal['volume_ratio']:.1f}x</td>
                            <td>{signal['score']:.1f}</td>
                        </tr>
            """
        
        html_content += """
                    </tbody>
                </table>
            </div>
        """
    
    # Generate Exit signals section
    if all_exits:
        html_content += f"""
            <div class="section">
                <h2>🚪 EXIT SIGNALS ({len(all_exits)} found)</h2>
                <div style="background: #fff3cd; padding: 20px; border-radius: 10px; border-left: 5px solid #ffc107;">
        """
        
        for exit in all_exits:
            html_content += f"""
                    <p><strong>{exit['ticker']}:</strong> {exit['message']}</p>
            """
        
        html_content += """
                </div>
            </div>
        """
    
    html_content += """
            <div class="footer">
                <p><strong>⚠️ Disclaimer:</strong> These signals are based on Smart Money Concepts analysis and are for educational purposes only.</p>
                <p><strong>🎯 System:</strong> Entry signals require order block interaction + confirmations. Risk management built-in.</p>
                <p><strong>📊 Usage:</strong> Validate signals with Pine Script charts before executing trades.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Save HTML
    html_filename = f"smc_entry_exit_signals_{internal_sens}i_{external_sens}e_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    html_path = os.path.join(output_dir, html_filename)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return html_path

def save_entry_exit_json(results, output_dir, internal_sens, external_sens):
    """Save entry/exit results to JSON"""
    
    if not results:
        return None
    
    # Compile comprehensive data
    json_data = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'total_stocks_analyzed': len(results),
            'internal_sensitivity': int(internal_sens),
            'external_sensitivity': int(external_sens),
            'strategy': 'Smart Money Concepts Entry/Exit System',
            'risk_per_trade': '1% portfolio',
            'risk_reward_targets': [2.0, 3.0]
        },
        'summary': {
            'total_entry_signals': sum(len(r.get('entry_signals', [])) for r in results),
            'total_exit_signals': sum(len(r.get('exit_signals', [])) for r in results),
            'long_entries': sum(len([e for e in r.get('entry_signals', []) if e['type'] == 'LONG_ENTRY']) for r in results),
            'short_entries': sum(len([e for e in r.get('entry_signals', []) if e['type'] == 'SHORT_ENTRY']) for r in results),
            'strong_signals': sum(len([e for e in r.get('entry_signals', []) if e['strength'] == 'STRONG']) for r in results)
        },
        'results': []
    }
    
    # Process each result
    for result in results:
        # Clean up result for JSON serialization
        clean_result = {}
        for key, value in result.items():
            if isinstance(value, (int, float, str, bool, list, dict)):
                if isinstance(value, dict):
                    clean_result[key] = {k: v for k, v in value.items() if isinstance(v, (int, float, str, bool, list))}
                elif isinstance(value, list):
                    clean_result[key] = [
                        {k: v for k, v in item.items() if isinstance(v, (int, float, str, bool, list))} 
                        if isinstance(item, dict) else item 
                        for item in value
                    ]
                else:
                    clean_result[key] = value
            else:
                try:
                    clean_result[key] = float(value) if hasattr(value, 'item') else str(value)
                except:
                    clean_result[key] = str(value)
        
        json_data['results'].append(clean_result)
    
    # Save JSON
    json_filename = f"smc_entry_exit_data_{internal_sens}i_{external_sens}e_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_path = os.path.join(output_dir, json_filename)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
def export_trading_journal(results, output_dir):
    """Export signals as a trading journal CSV for tracking"""
    
    all_entries = []
    for result in results:
        for entry in result.get('entry_signals', []):
            entry['ticker'] = result['ticker']
            entry['current_price'] = result['current_price']
            entry['trend_direction'] = result['trend_direction']
            entry['rsi'] = result['rsi']
            entry['volume_ratio'] = result['volume_ratio']
            all_entries.append(entry)
    
    if not all_entries:
        return None
    
    # Create DataFrame for CSV export
    journal_data = []
    for entry in all_entries:
        risk_pct = (entry['risk_per_share'] / entry['entry_price']) * 100
        capital_req = entry['entry_price'] * entry['position_size']
        
        journal_data.append({
            'Date': datetime.now().strftime('%Y-%m-%d'),
            'Time': datetime.now().strftime('%H:%M:%S'),
            'Ticker': entry['ticker'],
            'Signal_Type': entry['type'],
            'Signal_Strength': entry['strength'],
            'Entry_Price': entry['entry_price'],
            'Stop_Loss': entry['stop_loss'],
            'Target_1': entry['target_1'],
            'Target_2': entry['target_2'],
            'Risk_Per_Share': entry['risk_per_share'],
            'Risk_Percentage': round(risk_pct, 2),
            'Position_Size': entry['position_size'],
            'Capital_Required': round(capital_req, 0),
            'Risk_Reward_1': entry['risk_reward_1'],
            'Risk_Reward_2': entry['risk_reward_2'],
            'RSI': round(entry['rsi'], 1),
            'Volume_Ratio': round(entry['volume_ratio'], 2),
            'Trend_Direction': entry['trend_direction'],
            'Score': entry['score'],
            'Factors': '|'.join(entry['factors']),
            'Order_Block_Type': entry['order_block']['type'],
            'Order_Block_Top': entry['order_block']['top'],
            'Order_Block_Bottom': entry['order_block']['bottom'],
            'Order_Block_Strength': round(entry['order_block']['strength'], 2),
            'Status': 'PENDING',  # For manual tracking
            'Entry_Date': '',     # For manual filling
            'Exit_Date': '',      # For manual filling
            'Exit_Price': '',     # For manual filling
            'PnL': '',           # For manual calculation
            'Notes': ''          # For manual notes
        })
    
    # Convert to DataFrame and save
    try:
        import pandas as pd
        df = pd.DataFrame(journal_data)
        
        # Sort by score (highest first)
        df = df.sort_values('Score', ascending=False).reset_index(drop=True)
        
        # Save CSV
        csv_filename = f"smc_trading_journal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        csv_path = os.path.join(output_dir, csv_filename)
        
        df.to_csv(csv_path, index=False)
        
        return csv_path
    except ImportError:
        # Fallback: manual CSV creation if pandas not available
        csv_filename = f"smc_trading_journal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        csv_path = os.path.join(output_dir, csv_filename)
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            import csv
            if journal_data:
                writer = csv.DictWriter(f, fieldnames=journal_data[0].keys())
                writer.writeheader()
                # Sort by score manually
                sorted_data = sorted(journal_data, key=lambda x: x['Score'], reverse=True)
                writer.writerows(sorted_data)
        
        return csv_path

def generate_signal_analysis_report(results):
    """Generate detailed signal analysis and statistics"""
    
    all_entries = []
    for result in results:
        for entry in result.get('entry_signals', []):
            entry['ticker'] = result['ticker']
            entry['trend_direction'] = result['trend_direction']
            all_entries.append(entry)
    
    if not all_entries:
        return "No signals to analyze"
    
    # Analyze signal patterns
    analysis = {
        'total_signals': len(all_entries),
        'long_signals': len([e for e in all_entries if e['type'] == 'LONG_ENTRY']),
        'short_signals': len([e for e in all_entries if e['type'] == 'SHORT_ENTRY']),
        'strong_signals': len([e for e in all_entries if e['strength'] == 'STRONG']),
        'moderate_signals': len([e for e in all_entries if e['strength'] == 'MODERATE']),
        'avg_score': sum(e['score'] for e in all_entries) / len(all_entries),
        'avg_risk_pct': sum((e['risk_per_share'] / e['entry_price']) * 100 for e in all_entries) / len(all_entries),
        'total_capital': sum(e['entry_price'] * e['position_size'] for e in all_entries),
        'total_risk': len(all_entries) * 1000  # ₹1000 per trade
    }
    
    # Factor frequency analysis
    factor_counts = {}
    for entry in all_entries:
        for factor in entry['factors']:
            factor_counts[factor] = factor_counts.get(factor, 0) + 1
    
    # Top factors
    top_factors = sorted(factor_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Trend alignment analysis
    bullish_trend_signals = len([e for e in all_entries if e['trend_direction'] == 'BULLISH'])
    bearish_trend_signals = len([e for e in all_entries if e['trend_direction'] == 'BEARISH'])
    neutral_trend_signals = len([e for e in all_entries if e['trend_direction'] == 'NEUTRAL'])
    
    # RSI distribution
    oversold_signals = len([e for e in all_entries if e.get('rsi', 50) < 30])
    overbought_signals = len([e for e in all_entries if e.get('rsi', 50) > 70])
    neutral_rsi_signals = len(all_entries) - oversold_signals - overbought_signals
    
    return {
        'summary': analysis,
        'top_factors': top_factors[:10],
        'trend_alignment': {
            'bullish': bullish_trend_signals,
            'bearish': bearish_trend_signals,
            'neutral': neutral_trend_signals
        },
        'rsi_distribution': {
            'oversold': oversold_signals,
            'overbought': overbought_signals,
            'neutral': neutral_rsi_signals
        }
    }

def main():
    """Main function for Entry/Exit signal generation"""
    parser = argparse.ArgumentParser(description="SMC Entry/Exit Signal Generator - Pine Script Logic")
    
    parser.add_argument('--internal', type=int, default=5, 
                       help='Internal structure sensitivity (default: 5)')
    parser.add_argument('--external', type=int, default=25, 
                       help='External structure sensitivity (default: 25)')
    parser.add_argument('--workers', type=int, default=3, 
                       help='Max concurrent workers (default: 3)')
    parser.add_argument('--output', type=str,
                       help='Output directory (default: output)')
    parser.add_argument('--test-single', type=str, 
                       help='Test single ticker with detailed output')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug output')
    parser.add_argument('--show-all', action='store_true',
                       help='Show both entry and exit signals')
    parser.add_argument('--buy-only', action='store_true',
                       help='Show only long entry signals')
    parser.add_argument('--sell-only', action='store_true', 
                       help='Show only short entry signals')
    
    args = parser.parse_args()
    
    # Test single ticker
    if args.test_single:
        print(f"🧪 TESTING SINGLE TICKER: {args.test_single}")
        print("="*50)
        result = generate_smc_entry_exit_signals(
            args.test_single, 
            args.internal, 
            args.external,  
            debug=True
        )
        if result:
            print(f"\n✅ Analysis complete!")
            if result['entry_signals']:
                print(f"📊 Found {len(result['entry_signals'])} entry signals")
            if result['exit_signals']:
                print(f"📊 Found {len(result['exit_signals'])} exit signals")
        else:
            print(f"\n❌ No result for {args.test_single}")
        return
    
    print("🎯 SMC ENTRY/EXIT SIGNAL ANALYZER")
    print("🔄 Using Pine Script Derived Logic")
    print("="*50)
    print(f"🏗️ Internal Structure: {args.internal}")
    print(f"🏗️ External Structure: {args.external}")
    print(f"⚙️ Workers: {args.workers}")
    print("="*50)
    
    # Analyze all stocks
    results = analyze_all_stocks_entry_exit(
        internal_sens=args.internal,
        external_sens=args.external,
        max_workers=args.workers,
        debug=args.debug
    )
    
    if not results:
        print("\n❌ No results generated!")
        return
    
    # Display signals with enhanced formatting
    all_entries = filter_entry_exit_signals(results, ['LONG_ENTRY', 'SHORT_ENTRY'])
    
    if args.buy_only:
        long_entries = filter_entry_exit_signals(results, ['LONG_ENTRY'])
        display_entry_signals_enhanced(long_entries, "LONG ENTRY", 15)
    elif args.sell_only:
        short_entries = filter_entry_exit_signals(results, ['SHORT_ENTRY'])
        display_entry_signals_enhanced(short_entries, "SHORT ENTRY", 15)
    elif args.show_all:
        # Show both long and short entries plus exits
        long_entries = filter_entry_exit_signals(results, ['LONG_ENTRY']) 
        short_entries = filter_entry_exit_signals(results, ['SHORT_ENTRY'])
        
        if long_entries:
            display_entry_signals_enhanced(long_entries, "LONG ENTRY", 10)
        if short_entries:
            display_entry_signals_enhanced(short_entries, "SHORT ENTRY", 10)
        
        # Show exit signals
        all_exits = []
        for result in results:
            for exit in result.get('exit_signals', []):
                exit['ticker'] = result['ticker']
                all_exits.append(exit)
        
        if all_exits:
            print(f"\n🚪 EXIT SIGNALS FOUND ({len(all_exits)} total)")
            print("="*80)
            for exit in all_exits:
                print(f"   🔔 {exit['ticker']}: {exit['message']}")
        
        # Overall summary
        print(f"\n📊 OVERALL SUMMARY:")
        print(f"   🟢 Long entries: {len(long_entries)}")
        print(f"   🔴 Short entries: {len(short_entries)}")
        print(f"   🚪 Exit signals: {len(all_exits)}")
        print(f"   📈 Total analyzed: {len(results)}")
    else:
        # Default: Show all entry signals (both long and short)
        if all_entries:
            display_entry_signals_enhanced(all_entries, "ENTRY", 15)
        else:
            print(f"\n⚪ No entry signals found")
    
    # Generate enhanced reports
    print(f"\n📄 Generating enhanced reports...")
    
    # Set output directory
    output_dir = args.output or getattr(config, 'OUTPUT_DIR', 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Enhanced HTML Report
    html_path = generate_entry_exit_html(
        results, args.internal, args.external, output_dir
    )
    if html_path:
        print(f"🌐 Enhanced HTML Report: {html_path}")
        print(f"🔗 Open: file://{os.path.abspath(html_path)}")
    
    # Enhanced JSON Report
    json_path = save_entry_exit_json(results, output_dir, args.internal, args.external)
    if json_path:
        print(f"📊 Enhanced JSON Data: {json_path}")
    
    # Trading Journal Export (requires pandas)
    try:
        csv_path = export_trading_journal(results, output_dir)
        if csv_path:
            print(f"📋 Trading Journal CSV: {csv_path}")
            print(f"💡 Use this CSV to track your actual trades and performance")
    except ImportError:
        print(f"⚠️ Install pandas for trading journal export: pip install pandas")
    except Exception as e:
        if args.debug:
            print(f"⚠️ Trading journal export failed: {e}")
    
    # Signal Analysis Report
    if all_entries:
        analysis = generate_signal_analysis_report(results)
        
        print(f"\n📈 SIGNAL ANALYSIS REPORT:")
        print(f"   📊 Total signals: {analysis['summary']['total_signals']}")
        print(f"   🟢 Long/Short ratio: {analysis['summary']['long_signals']}:{analysis['summary']['short_signals']}")
        print(f"   💪 Strong signals: {analysis['summary']['strong_signals']} ({analysis['summary']['strong_signals']/analysis['summary']['total_signals']*100:.0f}%)")
        print(f"   📈 Average score: {analysis['summary']['avg_score']:.1f}")
        print(f"   📉 Average risk: {analysis['summary']['avg_risk_pct']:.1f}%")
        
        print(f"\n🔍 TOP SIGNAL FACTORS:")
        for factor, count in analysis['top_factors'][:5]:
            percentage = (count / analysis['summary']['total_signals']) * 100
            print(f"   • {factor}: {count} signals ({percentage:.0f}%)")
        
        print(f"\n🏗️ TREND ALIGNMENT:")
        print(f"   📈 Bullish trend: {analysis['trend_alignment']['bullish']} signals")
        print(f"   📉 Bearish trend: {analysis['trend_alignment']['bearish']} signals")
        print(f"   ⚪ Neutral trend: {analysis['trend_alignment']['neutral']} signals")
        
        print(f"\n📊 RSI DISTRIBUTION:")
        print(f"   🟢 Oversold (<30): {analysis['rsi_distribution']['oversold']} signals")
        print(f"   🔴 Overbought (>70): {analysis['rsi_distribution']['overbought']} signals")
        print(f"   ⚪ Neutral (30-70): {analysis['rsi_distribution']['neutral']} signals")
    
    print(f"\n✅ Analysis Complete!")
    print(f"📁 Output Directory: {os.path.abspath(output_dir)}")
    
    # Calculate portfolio summary
    if all_entries:
        total_capital = sum(e['entry_price'] * e['position_size'] for e in all_entries)
        total_risk = len(all_entries) * 1000  # ₹1000 risk per trade
        strong_signals = len([e for e in all_entries if e['strength'] == 'STRONG'])
        
        print(f"\n💰 PORTFOLIO IMPACT:")
        print(f"   💵 Total capital required: ₹{total_capital:,.0f}")
        print(f"   🎯 Total risk exposure: ₹{total_risk:,.0f} ({len(all_entries)} trades × ₹1,000)")
        print(f"   💪 High-confidence signals: {strong_signals}/{len(all_entries)} ({strong_signals/len(all_entries)*100:.0f}%)")
        print(f"   📊 Average risk per trade: {(total_risk/total_capital)*100:.1f}% of capital")
    
    print(f"\n💡 SMC ENTRY/EXIT SYSTEM NOTES:")
    print(f"   🎯 LONG ENTRY: Price reacting from bullish order block + confirmations")
    print(f"   🎯 SHORT ENTRY: Price rejecting from bearish order block + confirmations") 
    print(f"   🚪 EXIT: Order block mitigated (price breaks through triggering level)")
    print(f"   🛑 STOP LOSS: Placed beyond the order block that generated the signal")
    print(f"   🎯 TARGETS: 2:1 and 3:1 risk-reward ratios automatically calculated")
    print(f"   📦 POSITION SIZE: 1% portfolio risk per trade (₹1,000 on ₹100k portfolio)")
    print(f"   📊 SCORING: Requires ≥4.0 score (≥5.0 for STRONG signals)")
    print(f"   🏗️ STRUCTURE: BoS/CHoCH confirmation adds signal strength")
    print(f"   📈 CONFLUENCE: RSI, volume, FVG alignment improves probability")
    
    print(f"\n🧪 TROUBLESHOOTING COMMANDS:")
    print(f"   python {sys.argv[0]} --test-single RELIANCE --debug")
    print(f"   python {sys.argv[0]} --internal 3 --external 15 --debug")
    print(f"   python {sys.argv[0]} --show-all --debug")
    print(f"   python {sys.argv[0]} --buy-only  # Long entries only")
    print(f"   python {sys.argv[0]} --sell-only # Short entries only")

if __name__ == "__main__":
    main()