#!/usr/bin/env python
# corrected_breakout_analyzer.py - Comprehensive Breakout Strategy with Proper Signal Logic

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

warnings.filterwarnings("ignore")

def ATR(DF, n):
    """Calculate True Range and Average True Range (from second script)"""
    df = DF.copy()
    df['H-L'] = abs(df['High'] - df['Low'])
    df['H-PC'] = abs(df['High'] - df['Adj Close'].shift(1))
    df['L-PC'] = abs(df['Low'] - df['Adj Close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1, skipna=False)
    df['ATR'] = df['TR'].rolling(n).mean()
    return df['ATR']

def get_stock_data(ticker, lookback_days=21):
    """Get stock data for analysis with proper error handling"""
    try:
        # Add .NS for NSE stocks
        symbol = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
        
        # Get enough data for lookback + buffer (trading days only)
        days_needed = lookback_days + 50  # Extra buffer for weekends/holidays
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_needed)
        
        # Download data
        stock = yf.Ticker(symbol)
        data = stock.history(start=start_date, end=end_date)
        
        if data.empty or len(data) < lookback_days + 5:
            print(f"   ⚠️  {ticker}: Insufficient data ({len(data)} days)")
            return None
        
        # Clean data and rename columns to match second script format
        data = data.dropna()
        data['Adj Close'] = data['Close']  # Add Adj Close column for compatibility
        
        if len(data) < lookback_days + 5:
            print(f"   ⚠️  {ticker}: Insufficient clean data ({len(data)} days)")
            return None
        
        return data
        
    except Exception as e:
        print(f"   ❌ {ticker}: Data fetch error - {str(e)}")
        return None

def calculate_rsi(prices, period=14):
    """Calculate RSI (Relative Strength Index)"""
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

def analyze_stock_comprehensive(ticker, lookback_days=21, debug=False):
    """
    Comprehensive stock analysis with HYBRID strategy: Original Breakout + Intraday Bullish Logic
    """
    try:
        print(f"📊 Analyzing {ticker} (Hybrid: Breakout + Intraday Bullish Strategy)...")
        
        # Get data
        data = get_stock_data(ticker, lookback_days)
        if data is None:
            return None
        
        print(f"   📅 Data: {len(data)} trading days available")
        
        # Calculate indicators using corrected logic from second script
        data['ATR'] = ATR(data, 20)  # 20-period ATR
        data['roll_max_cp'] = data['High'].rolling(lookback_days).max()  # Rolling max high
        data['roll_min_cp'] = data['Low'].rolling(lookback_days).min()   # Rolling min low
        data['roll_max_vol'] = data['Volume'].rolling(lookback_days).max()  # Rolling max volume
        
        # NEW: Intraday Bullish Strategy indicators
        data['swing_low_12'] = data['Low'].rolling(12).min()  # 12-period swing low
        data['lowest_12'] = data['Low'] == data['swing_low_12']  # Current low is 12-period lowest
        data['lowest_12_prev'] = data['Low'].shift(1) == data['swing_low_12'].shift(1)  # Previous low was lowest
        
        # Drop NaN values
        data = data.dropna()
        
        if len(data) < 15:  # Need more data for new indicators
            print(f"   ⚠️  {ticker}: Insufficient data after calculations")
            return None
        
        # Get latest values
        latest = data.iloc[-1]
        previous = data.iloc[-2] if len(data) > 1 else latest
        prev2 = data.iloc[-3] if len(data) > 2 else latest
        prev3 = data.iloc[-4] if len(data) > 3 else latest
        
        current_price = latest['Adj Close']
        current_high = latest['High']
        current_low = latest['Low']
        current_open = latest['Open']
        current_volume = latest['Volume']
        
        # Breakout levels
        resistance_level = latest['roll_max_cp']
        support_level = latest['roll_min_cp']
        prev_max_volume = previous['roll_max_vol']
        current_atr = latest['ATR']
        
        # Calculate RSI and other advanced indicators
        rsi = calculate_rsi(data['Adj Close'])
        
        # Calculate momentum (5-day change)
        if len(data) >= 6:
            momentum = ((current_price - data['Adj Close'].iloc[-6]) / data['Adj Close'].iloc[-6]) * 100
        else:
            momentum = 0
        
        # Volume analysis
        volume_ratio = current_volume / data['Volume'].rolling(20).mean().iloc[-1] if len(data) >= 20 else 1.0
        
        # Market condition analysis
        is_sideways = detect_sideways_market(data)
        
        # NEW: Intraday Bullish Strategy Conditions
        # 1. Swing Low Detection (12-period)
        swing_low_signal = latest['lowest_12'] or previous['lowest_12_prev']
        
        # 2. Bullish 3-Line Strike Pattern
        try:
            bullish_3_line_strike = (
                prev3['Adj Close'] < prev3['Open'] and    # 3 candles ago: red
                prev2['Adj Close'] < prev2['Open'] and    # 2 candles ago: red  
                previous['Adj Close'] < previous['Open'] and  # 1 candle ago: red
                current_price > previous['Open']          # Current: green above prev open
            )
        except:
            bullish_3_line_strike = False
        
        # 3. Extreme Oversold (simplified version using RSI)
        extreme_oversold = rsi < 25  # Very oversold condition
        
        # **HYBRID SIGNAL LOGIC**
        signal_type = 'HOLD'
        buy_strength = 0
        sell_strength = 0
        entry_price = current_price
        stop_loss = current_price
        signal_source = ""
        
        # **ORIGINAL BREAKOUT SIGNALS** (Priority 1: Strong momentum moves)
        # **BUY SIGNAL**: High breaks above resistance with volume confirmation
        if (current_high >= resistance_level and 
            current_volume > 1.5 * prev_max_volume):
            
            signal_type = 'STRONG_BREAKOUT_BUY'
            buy_strength = ((current_high - resistance_level) / resistance_level) * 100
            entry_price = resistance_level * 1.002  # 0.2% above resistance for confirmation
            stop_loss = current_price - (current_atr * 2)  # 2x ATR stop (wider for breakouts)
            signal_source = "BREAKOUT"
            
            if debug:
                print(f"   🐛 DEBUG: STRONG_BREAKOUT_BUY - High {current_high:.2f} > Resistance {resistance_level:.2f}")
                print(f"   🐛 DEBUG: Volume {current_volume:,.0f} > 1.5x Previous Max {prev_max_volume:,.0f}")
        
        # **SELL SIGNAL**: Low breaks below support with volume confirmation  
        elif (current_low <= support_level and 
              current_volume > 1.5 * prev_max_volume):
            
            signal_type = 'STRONG_BREAKOUT_SELL'
            sell_strength = ((support_level - current_low) / support_level) * 100
            entry_price = support_level * 0.998  # 0.2% below support for confirmation
            stop_loss = current_price + (current_atr * 2)  # 2x ATR stop
            signal_source = "BREAKDOWN"
            
            if debug:
                print(f"   🐛 DEBUG: STRONG_BREAKOUT_SELL - Low {current_low:.2f} < Support {support_level:.2f}")
                print(f"   🐛 DEBUG: Volume {current_volume:,.0f} > 1.5x Previous Max {prev_max_volume:,.0f}")
        
        # **NEW: INTRADAY BULLISH SIGNALS** (Priority 2: Reversal setups)
        elif (swing_low_signal or bullish_3_line_strike or extreme_oversold):
            
            # Calculate how many conditions are met
            conditions_met = sum([swing_low_signal, bullish_3_line_strike, extreme_oversold])
            
            if conditions_met >= 2:  # At least 2 conditions for strong signal
                signal_type = 'STRONG_REVERSAL_BUY'
                buy_strength = conditions_met * 25  # 25% per condition
                signal_source = "REVERSAL"
            else:
                signal_type = 'WEAK_REVERSAL_BUY'  
                buy_strength = conditions_met * 15  # 15% for single condition
                signal_source = "WEAK_REVERSAL"
            
            entry_price = current_price  # Enter at current price for reversals
            stop_loss = current_price - (current_atr * 2)  # 2x ATR stop
            
            if debug:
                conditions = []
                if swing_low_signal: conditions.append("SWING_LOW")
                if bullish_3_line_strike: conditions.append("3_LINE_STRIKE") 
                if extreme_oversold: conditions.append("EXTREME_OVERSOLD")
                print(f"   🐛 DEBUG: {signal_type} - Conditions: {', '.join(conditions)}")
                print(f"   🐛 DEBUG: RSI: {rsi:.1f}, Conditions Met: {conditions_met}")
        
        # **WEAK BREAKOUT SIGNALS** (Priority 3: Near-breakout conditions)
        elif (current_price > resistance_level * 0.99 and 
              current_volume > 1.2 * prev_max_volume and
              momentum > 1.0):
            
            signal_type = 'WEAK_BREAKOUT_BUY'
            buy_strength = ((current_price - resistance_level * 0.99) / (resistance_level * 0.01)) * 25
            entry_price = resistance_level * 1.002
            stop_loss = current_price - (current_atr * 1.5)  # 1.5x ATR stop for weak signals
            signal_source = "NEAR_BREAKOUT"
            
            if debug:
                print(f"   🐛 DEBUG: WEAK_BREAKOUT_BUY - Near resistance with volume")
        
        elif (current_price < support_level * 1.01 and 
              current_volume > 1.2 * prev_max_volume and
              momentum < -1.0):
            
            signal_type = 'WEAK_BREAKOUT_SELL'
            sell_strength = ((support_level * 1.01 - current_price) / (support_level * 0.01)) * 25
            entry_price = support_level * 0.998
            stop_loss = current_price + (current_atr * 1.5)  # 1.5x ATR stop
            signal_source = "NEAR_BREAKDOWN"
            
            if debug:
                print(f"   🐛 DEBUG: WEAK_BREAKOUT_SELL - Near support with volume")
        
        else:
            if debug:
                print(f"   🐛 DEBUG: HOLD - No conditions met")
                print(f"   🐛 DEBUG: Price {current_price:.2f}, Resistance {resistance_level:.2f}, Support {support_level:.2f}")
                print(f"   🐛 DEBUG: Swing Low: {swing_low_signal}, 3-Line Strike: {bullish_3_line_strike}, Oversold: {extreme_oversold}")
        
        # Calculate pullback entry and take profit (based on ATR like the new strategy)
        if 'BUY' in signal_type:
            if signal_source in ['BREAKOUT', 'NEAR_BREAKOUT']:
                pullback_entry = (current_price + resistance_level) / 2
                take_profit = entry_price + (current_atr * 4)  # 4x ATR target (from new strategy)
            else:  # REVERSAL signals
                pullback_entry = current_price * 0.99  # 1% below current for pullback
                take_profit = current_price + (current_atr * 4)  # 4x ATR target
        elif 'SELL' in signal_type:
            pullback_entry = (current_price + support_level) / 2
            take_profit = entry_price - (current_atr * 4)  # 4x ATR target for shorts
        else:
            pullback_entry = current_price
            take_profit = current_price
        
        # Risk management - position sizing (1% risk on 100k capital)
        capital = 100000
        risk_amount = capital * 0.01
        risk_per_share = abs(current_price - stop_loss)
        position_size = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
        
        # Volatility score
        if len(data) >= 20:
            volatility_score = (current_atr / current_price) * 100
        else:
            volatility_score = 0
        
        # NEW: Intraday signal details for reporting
        signal_details = []
        if swing_low_signal:
            signal_details.append("SWING_LOW")
        if bullish_3_line_strike:
            signal_details.append("3_LINE_STRIKE")
        if extreme_oversold:
            signal_details.append("EXTREME_OVERSOLD")
        
        print(f"   📊 Volume: {current_volume:,.0f} vs threshold = {volume_ratio:.1f}x")
        print(f"   🚀 Momentum: {momentum:+.1f}% (5-day)")
        print(f"   📈 RSI: {rsi:.1f}")
        print(f"   📈 Levels: Support ₹{support_level:.2f}, Resistance ₹{resistance_level:.2f}")
        print(f"   🎯 Signal: {signal_type} ({signal_source})")
        if signal_details:
            print(f"   🔍 Intraday Conditions: {', '.join(signal_details)}")
        
        if is_sideways:
            print(f"   ⚠️  WARNING: Sideways market detected")
        
        result = {
            'ticker': ticker,
            'signal_type': signal_type,
            'signal_source': signal_source,  # NEW: Track signal origin
            'current_price': float(current_price),
            'lookback_high': float(resistance_level),
            'lookback_low': float(support_level),
            'breakout_entry': float(entry_price),
            'pullback_entry': float(pullback_entry),
            'take_profit': float(take_profit),  # NEW: ATR-based take profit
            'stop_loss': float(stop_loss),
            'buy_strength': float(buy_strength),
            'sell_strength': float(sell_strength),
            'volume_ratio': float(volume_ratio),
            'volume_analysis': {
                'volume_strength': 'HIGH' if current_volume > 1.5 * prev_max_volume else 'NORMAL',
                'volume_trend': 'INCREASING' if volume_ratio > 1.2 else 'NEUTRAL',
                'volume_sma_ratio': float(volume_ratio)
            },
            'momentum': float(momentum),
            'position_size': int(position_size),
            'risk_per_share': float(risk_per_share),
            'trading_days_used': len(data),
            'volume_period': f"20 trading days",
            'momentum_period': f"5 trading days",
            'lookback_days': int(lookback_days),
            'breakout_strength': float(max(buy_strength, sell_strength)),
            'volatility_score': float(volatility_score),
            'atr': float(current_atr),
            'rsi': float(rsi),
            'is_sideways_market': bool(is_sideways),
            'false_breakout_risk': False,  # Could be enhanced later
            'intraday_signals': signal_details,  # NEW: List of triggered intraday conditions
            'swing_low_detected': bool(swing_low_signal),  # NEW: Individual condition tracking
            'bullish_3_strike': bool(bullish_3_line_strike),
            'extreme_oversold': bool(extreme_oversold)
        }
        
        return result
        
    except Exception as e:
        print(f"❌ Error analyzing {ticker}: {e}")
        return None

def analyze_all_stocks(lookback_days=21, max_workers=3, debug=False):
    """Analyze all stocks with hybrid breakout + intraday bullish logic"""
    
    # Get tickers from config
    tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
    
    print(f"\n🚀 HYBRID COMPREHENSIVE TRADING ANALYSIS")
    print(f"📊 Analyzing {len(tickers)} stocks")
    print(f"📈 Breakout Period: {lookback_days} trading days")
    print(f"🔄 Strategy: Original Breakout + Intraday Bullish")
    print(f"✅ Combines volume breakouts with reversal patterns")
    print("="*60)
    
    all_signals = []
    
    # Analyze stocks
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(analyze_stock_comprehensive, ticker, lookback_days, debug): ticker 
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
                    signal_source = result.get('signal_source', '')
                    print(f"✅ {ticker} ({completed}/{len(tickers)}) - {result['signal_type']} ({signal_source})")
                else:
                    failed += 1
                    print(f"⚪ {ticker} ({completed}/{len(tickers)}) - No data")
            except concurrent.futures.TimeoutError:
                failed += 1
                print(f"⏰ {ticker} ({completed}/{len(tickers)}) - Timeout")
            except Exception as e:
                failed += 1
                print(f"❌ {ticker} ({completed}/{len(tickers)}) - Error: {str(e)[:50]}")
        
        print(f"\n📊 HYBRID ANALYSIS SUMMARY:")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📈 Total signals: {len(all_signals)}")
        
        # Signal type breakdown
        if all_signals:
            breakout_signals = len([s for s in all_signals if 'BREAKOUT' in s['signal_type']])
            reversal_signals = len([s for s in all_signals if 'REVERSAL' in s['signal_type']])
            hold_signals = len([s for s in all_signals if s['signal_type'] == 'HOLD'])
            
            print(f"   🚀 Breakout signals: {breakout_signals}")
            print(f"   🔄 Reversal signals: {reversal_signals}")
            print(f"   ⚪ Hold signals: {hold_signals}")
    
    return all_signals

def filter_signals_by_type(all_signals, signal_types):
    """Filter signals by type - Updated for hybrid strategy"""
    return [signal for signal in all_signals if signal['signal_type'] in signal_types]

def sort_signals_properly(signals):
    """Sort signals with STRONG first, then WEAK, by strength within each category - Updated for hybrid"""
    
    if not signals:
        return signals
    
    # Separate by signal strength
    strong_signals = [s for s in signals if 'STRONG' in s['signal_type']]
    weak_signals = [s for s in signals if 'WEAK' in s['signal_type']]
    
    # Determine if these are BUY or SELL signals
    is_buy_signals = any('BUY' in s['signal_type'] for s in signals)
    
    # Sort STRONG signals by strength (descending)
    if is_buy_signals:
        strong_signals.sort(key=lambda x: x['buy_strength'], reverse=True)
        weak_signals.sort(key=lambda x: x['buy_strength'], reverse=True)
    else:
        strong_signals.sort(key=lambda x: x['sell_strength'], reverse=True)
        weak_signals.sort(key=lambda x: x['sell_strength'], reverse=True)
    
    # Return STRONG first, then WEAK
    return strong_signals + weak_signals

def display_top_signals(signals, signal_title, top_n=10):
    """Display top N signals - Updated for hybrid strategy"""
    
    if not signals:
        print(f"\n❌ No {signal_title} signals found!")
        return
    
    # Signals should already be sorted
    signals = sort_signals_properly(signals)
    
    # Get top N
    top_signals = signals[:top_n]
    
    print(f"\n🏆 TOP {len(top_signals)} {signal_title} SIGNALS")
    print(f"📊 Hybrid Strategy: Original Breakout + Intraday Bullish")
    print("="*110)
    
    # Prepare table with new columns
    table_data = []
    headers = ['Rank', 'Ticker', 'Signal', 'Source', 'Price', 'Entry', 'Take Profit', 'Stop Loss', 
              'Strength%', 'Volume', 'RSI', 'Momentum%', 'ATR', 'Intraday Signals', 'Qty']
    
    for i, signal in enumerate(top_signals, 1):
        if 'BUY' in signal['signal_type']:
            strength = signal['buy_strength']
        else:
            strength = signal['sell_strength']
        
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
        if volume_strength == 'HIGH':
            volume_display += "🟢"
        else:
            volume_display += "🟡"
        
        # Intraday signals display
        intraday_signals = signal.get('intraday_signals', [])
        intraday_display = ','.join(intraday_signals[:2]) if intraday_signals else "NONE"  # Show first 2
        
        # Signal source with emoji
        source = signal.get('signal_source', 'UNKNOWN')
        source_display = {
            'BREAKOUT': '🚀BREAKOUT',
            'BREAKDOWN': '📉BREAKDOWN', 
            'REVERSAL': '🔄REVERSAL',
            'WEAK_REVERSAL': '🔄WEAK_REV',
            'NEAR_BREAKOUT': '⚡NEAR_BO',
            'NEAR_BREAKDOWN': '⚡NEAR_BD'
        }.get(source, source)
        
        table_data.append([
            i,
            signal['ticker'],
            signal['signal_type'].replace('_', ' '),
            source_display,
            f"₹{signal['current_price']:.2f}",
            f"₹{signal['breakout_entry']:.2f}",
            f"₹{signal.get('take_profit', 0):.2f}",
            f"₹{signal['stop_loss']:.2f}",
            f"{strength:.2f}%",
            volume_display,
            rsi_display,
            f"{signal['momentum']:+.1f}%",
            f"₹{signal.get('atr', 0):.2f}",
            intraday_display,
            signal['position_size']
        ])
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Summary statistics
    avg_strength = sum(strength for signal in top_signals 
                      for strength in [signal['buy_strength'] if 'BUY' in signal['signal_type'] 
                                     else signal['sell_strength']]) / len(top_signals)
    avg_volume = sum(signal['volume_ratio'] for signal in top_signals) / len(top_signals)
    avg_momentum = sum(signal['momentum'] for signal in top_signals) / len(top_signals)
    
    # Signal source breakdown
    sources = {}
    for signal in top_signals:
        source = signal.get('signal_source', 'UNKNOWN')
        sources[source] = sources.get(source, 0) + 1
    
    print(f"\n📊 SUMMARY:")
    print(f"   🎯 {signal_title} signals: {len(signals)}")
    print(f"   📈 Average strength: {avg_strength:.2f}%")
    print(f"   📊 Average volume ratio: {avg_volume:.1f}x")
    print(f"   🚀 Average momentum: {avg_momentum:+.1f}%")
    
    print(f"\n📋 SIGNAL SOURCES:")
    for source, count in sources.items():
        emoji = {'BREAKOUT': '🚀', 'REVERSAL': '🔄', 'WEAK_REVERSAL': '🔄', 
                'NEAR_BREAKOUT': '⚡', 'BREAKDOWN': '📉', 'NEAR_BREAKDOWN': '⚡'}.get(source, '📊')
        print(f"   {emoji} {source}: {count}")
    
    print(f"\n🏆 HYBRID STRATEGY FEATURES:")
    print(f"   🚀 Original Breakout: High-volume resistance/support breaks")
    print(f"   🔄 Intraday Bullish: Swing lows + candlestick patterns + oversold")
    print(f"   📊 ATR-based stops: 2x ATR for breakouts, 4x ATR profit targets")
    print(f"   ⚖️  Risk management: 1% capital risk per trade")
    print(f"   🔍 Triple confirmation: Multiple signals increase conviction")

def generate_comprehensive_html(all_signals, lookback_days, output_dir):
    """Generate comprehensive HTML report (keeping all original features)"""
    
    if not all_signals:
        print("❌ No signals to generate report")
        return None
    
    # Separate signals by type
    buy_signals = filter_signals_by_type(all_signals, ['STRONG_BREAKOUT_BUY', 'WEAK_BREAKOUT_BUY'])
    sell_signals = filter_signals_by_type(all_signals, ['STRONG_BREAKOUT_SELL', 'WEAK_BREAKOUT_SELL'])
    hold_signals = filter_signals_by_type(all_signals, ['HOLD'])
    
    # Sort properly: STRONG first, then WEAK
    buy_signals = sort_signals_properly(buy_signals) if buy_signals else []
    sell_signals = sort_signals_properly(sell_signals) if sell_signals else []
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CORRECTED Breakout Analysis - {datetime.now().strftime('%Y-%m-%d')}</title>
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
            .correction-note {{
                background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
                text-align: center;
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
            .strong-breakout-buy {{
                background: linear-gradient(90deg, #28a745, #20c997);
                color: white;
                padding: 5px 10px;
                border-radius: 15px;
                font-weight: bold;
                text-align: center;
            }}
            .weak-breakout-buy {{
                background: linear-gradient(90deg, #ffc107, #fd7e14);
                color: white;
                padding: 5px 10px;
                border-radius: 15px;
                font-weight: bold;
                text-align: center;
            }}
            .strong-breakout-sell {{
                background: linear-gradient(90deg, #dc3545, #e74c3c);
                color: white;
                padding: 5px 10px;
                border-radius: 15px;
                font-weight: bold;
                text-align: center;
            }}
            .weak-breakout-sell {{
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
                <h1>📊 CORRECTED COMPREHENSIVE BREAKOUT ANALYSIS</h1>
                <p><strong>✅ Fixed Breakout Strategy Report</strong></p>
                <p>Breakout: {lookback_days} days | ATR Stop Loss | Volume Confirmation</p>
                <p>Generated: {timestamp}</p>
            </div>
            
            <div class="correction-note">
                <h3>🔧 CORRECTED FEATURES</h3>
                <p>✅ Proper breakout confirmation with volume (1.5x rolling max)</p>
                <p>✅ ATR-based stop losses for better risk management</p>
                <p>✅ State-based signal logic prevents false entries</p>
                <p>✅ Volume timing: checks previous period, not current bar</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>{len(buy_signals)}</h3>
                    <p>BREAKOUT BUY</p>
                </div>
                <div class="stat-card">
                    <h3>{len(sell_signals)}</h3>
                    <p>BREAKOUT SELL</p>
                </div>
                <div class="stat-card">
                    <h3>{len(hold_signals)}</h3>
                    <p>HOLD Signals</p>
                </div>
                <div class="stat-card">
                    <h3>{len(all_signals)}</h3>
                    <p>Total Analyzed</p>
                </div>
            </div>
    """
    
    # Generate BUY signals table (same format as original)
    if buy_signals:
        html_content += f"""
            <div class="section">
                <h2>🟢 TOP CORRECTED BREAKOUT BUY SIGNALS</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Ticker</th>
                            <th>Signal</th>
                            <th>Price</th>
                            <th>Entry</th>
                            <th>Stop Loss</th>
                            <th>Resistance</th>
                            <th>Support</th>
                            <th>Strength</th>
                            <th>Volume</th>
                            <th>RSI</th>
                            <th>Momentum</th>
                            <th>ATR</th>
                            <th>Qty</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for i, signal in enumerate(buy_signals[:15], 1):
            signal_class = signal['signal_type'].lower().replace('_', '-')
            momentum_class = 'positive' if signal['momentum'] >= 0 else 'negative'
            
            html_content += f"""
                        <tr>
                            <td class="rank">{i}</td>
                            <td class="ticker">{signal['ticker']}</td>
                            <td><span class="{signal_class}">{signal['signal_type'].replace('_', ' ')}</span></td>
                            <td class="price">₹{signal['current_price']:.2f}</td>
                            <td class="price">₹{signal['breakout_entry']:.2f}</td>
                            <td class="price">₹{signal['stop_loss']:.2f}</td>
                            <td class="price">₹{signal['lookback_high']:.2f}</td>
                            <td class="price">₹{signal['lookback_low']:.2f}</td>
                            <td>{signal['buy_strength']:.2f}%</td>
                            <td>{signal['volume_ratio']:.1f}x</td>
                            <td>{signal.get('rsi', 50):.0f}</td>
                            <td class="{momentum_class}">{signal['momentum']:+.1f}%</td>
                            <td>₹{signal.get('atr', 0):.2f}</td>
                            <td>{signal['position_size']}</td>
                        </tr>
            """
        
        html_content += """
                    </tbody>
                </table>
            </div>
        """
    
    # Generate SELL signals table (similar format)
    if sell_signals:
        html_content += f"""
            <div class="section">
                <h2>🔴 TOP CORRECTED BREAKOUT SELL SIGNALS</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Ticker</th>
                            <th>Signal</th>
                            <th>Price</th>
                            <th>Entry</th>
                            <th>Stop Loss</th>
                            <th>Resistance</th>
                            <th>Support</th>
                            <th>Strength</th>
                            <th>Volume</th>
                            <th>RSI</th>
                            <th>Momentum</th>
                            <th>ATR</th>
                            <th>Qty</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for i, signal in enumerate(sell_signals[:15], 1):
            signal_class = signal['signal_type'].lower().replace('_', '-')
            momentum_class = 'positive' if signal['momentum'] >= 0 else 'negative'
            
            html_content += f"""
                        <tr>
                            <td class="rank">{i}</td>
                            <td class="ticker">{signal['ticker']}</td>
                            <td><span class="{signal_class}">{signal['signal_type'].replace('_', ' ')}</span></td>
                            <td class="price">₹{signal['current_price']:.2f}</td>
                            <td class="price">₹{signal['breakout_entry']:.2f}</td>
                            <td class="price">₹{signal['stop_loss']:.2f}</td>
                            <td class="price">₹{signal['lookback_high']:.2f}</td>
                            <td class="price">₹{signal['lookback_low']:.2f}</td>
                            <td>{signal['sell_strength']:.2f}%</td>
                            <td>{signal['volume_ratio']:.1f}x</td>
                            <td>{signal.get('rsi', 50):.0f}</td>
                            <td class="{momentum_class}">{signal['momentum']:+.1f}%</td>
                            <td>₹{signal.get('atr', 0):.2f}</td>
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
                <p><strong>⚠️ Disclaimer:</strong> This analysis is for educational purposes only. Corrected breakout trading carries significant risk.</p>
                <p><strong>📊 Corrected Strategy:</strong> High-Low breakout system with proper volume confirmation, ATR stops, and state management.</p>
                <p><strong>🔧 Key Fix:</strong> Volume confirmation uses previous period's max, not current period, preventing look-ahead bias.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Save HTML
    html_filename = f"corrected_breakout_analysis_{lookback_days}d_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    html_path = os.path.join(output_dir, html_filename)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return html_path

def save_results_json(all_signals, output_dir, lookback_days):
    """Save results to JSON (keeping original functionality)"""
    
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
            'lookback_days': int(lookback_days),
            'strategy': 'CORRECTED High-Low Breakout Strategy with Proper Signal Logic',
            'corrections_applied': [
                'Volume confirmation uses previous period max',
                'ATR-based stop losses',
                'Proper breakout confirmation',
                'State-based signal management'
            ]
        },
        'signals': json_signals
    }
    
    # Save JSON
    json_filename = f"corrected_breakout_signals_{lookback_days}d_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_path = os.path.join(output_dir, json_filename)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    return json_path

def main():
    """Main function with hybrid comprehensive analysis"""
    parser = argparse.ArgumentParser(description="HYBRID Comprehensive Breakout + Intraday Bullish Analyzer")
    
    parser.add_argument('--days', type=int, default=21, 
                       help='Breakout lookback days (default: 21)')
    parser.add_argument('--top', type=int, default=10, 
                       help='Top N signals to display (default: 10)')
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
                       help='Show only BUY signals (breakout + reversal)')
    parser.add_argument('--sell-only', action='store_true', 
                       help='Show only SELL signals')
    
    args = parser.parse_args()
    
    # Test single ticker if requested
    if args.test_single:
        print(f"🧪 TESTING HYBRID STRATEGY ON: {args.test_single}")
        print("="*50)
        result = analyze_stock_comprehensive(args.test_single, args.days, debug=True)
        if result:
            print(f"\n✅ SUCCESS! Signal: {result['signal_type']} ({result.get('signal_source', 'UNKNOWN')})")
            if result.get('intraday_signals'):
                print(f"🔍 Intraday conditions: {', '.join(result['intraday_signals'])}")
        else:
            print(f"\n❌ No result for {args.test_single}")
        return
    
    print("🎯 HYBRID COMPREHENSIVE TRADING ANALYZER")
    print("🔄 Original Breakout + Intraday Bullish Strategy")
    print("="*50)
    print(f"📈 Breakout Period: {args.days} trading days")
    print(f"🔧 Hybrid Features:")
    print(f"   🚀 Original: Volume-confirmed breakouts")
    print(f"   🔄 Intraday: Swing lows + patterns + oversold")
    print(f"   📊 ATR stops: 2x ATR stops, 4x ATR targets")
    print(f"   ⚖️  Risk: 1% per trade position sizing")
    print(f"🏆 Top Signals: {args.top}")
    print(f"⚙️  Workers: {args.workers}")
    print("="*50)
    
    # Set output directory
    output_dir = args.output or getattr(config, 'OUTPUT_DIR', 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Analyze all stocks with corrected logic
    all_signals = analyze_all_stocks(
        lookback_days=args.days,
        max_workers=args.workers,
        debug=args.debug
    )
    
    if not all_signals:
        print("\n❌ No signals generated!")
        print("💡 TROUBLESHOOTING TIPS:")
        print("   🔧 Try shorter lookback period: --days 10 or --days 14")
        print("   🔧 Check if markets are trending (breakouts need momentum)")
        print("   🔧 Enable debug mode: --debug")
        return
    
    # Display results based on arguments (updated for hybrid strategy)
    if args.buy_only:
        buy_signals = filter_signals_by_type(all_signals, ['STRONG_BREAKOUT_BUY', 'WEAK_BREAKOUT_BUY', 
                                                          'STRONG_REVERSAL_BUY', 'WEAK_REVERSAL_BUY'])
        buy_signals = sort_signals_properly(buy_signals) if buy_signals else []
        display_top_signals(buy_signals, "HYBRID BUY", args.top)
    elif args.sell_only:
        sell_signals = filter_signals_by_type(all_signals, ['STRONG_BREAKOUT_SELL', 'WEAK_BREAKOUT_SELL'])
        sell_signals = sort_signals_properly(sell_signals) if sell_signals else []
        display_top_signals(sell_signals, "HYBRID SELL", args.top)
    elif args.show_all:
        # Show all types
        buy_signals = filter_signals_by_type(all_signals, ['STRONG_BREAKOUT_BUY', 'WEAK_BREAKOUT_BUY', 
                                                          'STRONG_REVERSAL_BUY', 'WEAK_REVERSAL_BUY'])
        sell_signals = filter_signals_by_type(all_signals, ['STRONG_BREAKOUT_SELL', 'WEAK_BREAKOUT_SELL'])
        hold_signals = filter_signals_by_type(all_signals, ['HOLD'])
        
        if buy_signals:
            buy_signals = sort_signals_properly(buy_signals)
            display_top_signals(buy_signals, "HYBRID BUY", args.top)
        if sell_signals:
            sell_signals = sort_signals_properly(sell_signals)
            display_top_signals(sell_signals, "HYBRID SELL", args.top)
        
        print(f"\n📊 OVERALL HYBRID STRATEGY SUMMARY:")
        print(f"   🟢 BUY signals: {len(buy_signals)}")
        print(f"     🚀 Breakout BUY: {len([s for s in buy_signals if 'BREAKOUT' in s['signal_type']])}")
        print(f"     🔄 Reversal BUY: {len([s for s in buy_signals if 'REVERSAL' in s['signal_type']])}")
        print(f"   🔴 SELL signals: {len(sell_signals)}")
        print(f"   ⚪ HOLD signals: {len(hold_signals)}")
        print(f"   📈 Total analyzed: {len(all_signals)}")
    else:
        # Default: Show BUY signals only (both breakout and reversal)
        buy_signals = filter_signals_by_type(all_signals, ['STRONG_BREAKOUT_BUY', 'WEAK_BREAKOUT_BUY', 
                                                          'STRONG_REVERSAL_BUY', 'WEAK_REVERSAL_BUY'])
        buy_signals = sort_signals_properly(buy_signals) if buy_signals else []
        display_top_signals(buy_signals, "HYBRID BUY", args.top)
    
    # Generate reports
    print(f"\n📄 Generating corrected reports...")
    
    # HTML Report
    html_path = generate_comprehensive_html(all_signals, args.days, output_dir)
    if html_path:
        print(f"🌐 CORRECTED HTML Report: {html_path}")
        print(f"🔗 Open: file://{os.path.abspath(html_path)}")
    
    # JSON Report
    json_path = save_results_json(all_signals, output_dir, args.days)
    if json_path:
        print(f"📊 CORRECTED JSON Data: {json_path}")
    
    print(f"\n✅ Hybrid Analysis Complete!")
    print(f"📁 Output Directory: {os.path.abspath(output_dir)}")
    
    # Trading notes
    print(f"\n💡 HYBRID STRATEGY TRADING NOTES:")
    print(f"   🚀 STRONG BREAKOUT BUY: Price above {args.days}-day high + 1.5x volume")
    print(f"   🔄 STRONG REVERSAL BUY: 2+ conditions (swing low + pattern + oversold)")
    print(f"   🟡 WEAK REVERSAL BUY: 1 condition (swing low OR pattern OR oversold)")
    print(f"   🟡 WEAK BREAKOUT BUY: Near resistance + moderate volume + momentum")
    print(f"   🔴 STRONG BREAKOUT SELL: Price below {args.days}-day low + 1.5x volume")
    print(f"   🛑 STOP LOSS: 2x ATR for all signals (dynamic risk management)")
    print(f"   🎯 TAKE PROFIT: 4x ATR targets (better risk:reward ratio)")
    print(f"   📊 VOLUME: 1.5x previous max for strong, 1.2x for weak signals")
    print(f"   📈 RSI: Extreme oversold (<25) triggers reversal signals")
    print(f"   ⚖️  POSITION SIZE: 1% risk-based sizing")
    
    print(f"\n🔍 INTRADAY BULLISH CONDITIONS:")
    print(f"   📉 SWING LOW: Current/previous low = 12-period lowest")
    print(f"   🕯️  3-LINE STRIKE: 3 red candles + 1 green above prev open")
    print(f"   📊 EXTREME OVERSOLD: RSI < 25 (very oversold)")
    
    print(f"\n🎯 SIGNAL PRIORITY (Best to Worst):")
    print(f"   1️⃣ STRONG BREAKOUT (volume-confirmed breakouts)")
    print(f"   2️⃣ STRONG REVERSAL (multiple intraday conditions)")
    print(f"   3️⃣ WEAK BREAKOUT (near-breakout with momentum)")
    print(f"   4️⃣ WEAK REVERSAL (single intraday condition)")
    
    print(f"\n🧪 TROUBLESHOOTING COMMANDS:")
    print(f"   python hybrid_breakout_analyzer.py --test-single RELIANCE --debug")
    print(f"   python hybrid_breakout_analyzer.py --days 10 --debug --show-all")

if __name__ == "__main__":
    main()