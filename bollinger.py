#!/usr/bin/env python
# complete_bollinger_analyzer.py - Complete Bollinger Bands Strategy with Proper Trading Days Logic

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

def get_stock_data(ticker, lookback_days=20):
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
        
        # Clean data
        data = data.dropna()
        
        if len(data) < lookback_days + 5:
            print(f"   ⚠️  {ticker}: Insufficient clean data ({len(data)} days)")
            return None
        
        return data
        
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

def detect_false_breakout(data, current_price, upper_band, lower_band, lookback_days=3):
    """Detect potential false breakouts for Bollinger Bands"""
    try:
        if len(data) < lookback_days + 2:
            return False
        
        # Check if price broke bands but then reversed quickly
        recent_highs = data['High'].iloc[-lookback_days:].max()
        recent_lows = data['Low'].iloc[-lookback_days:].min()
        
        # False breakout indicators
        false_breakout_signals = 0
        
        # 1. Price broke above upper band but is now below it
        if recent_highs > upper_band and current_price < upper_band:
            false_breakout_signals += 1
        
        # 2. Price broke below lower band but is now above it
        if recent_lows < lower_band and current_price > lower_band:
            false_breakout_signals += 1
        
        # 3. High volatility without sustained direction
        if len(data) >= 5:
            price_volatility = data['Close'].iloc[-5:].std() / current_price
            if price_volatility > 0.03:  # > 3% volatility
                false_breakout_signals += 0.5
        
        return false_breakout_signals >= 1
    except:
        return False

def calculate_proper_metrics(data, volume_days=20, momentum_days=5):
    """
    Calculate volume and momentum using ONLY trading days (Fixed version)
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

def calculate_advanced_signals(data, current_price, upper_band, middle_band, lower_band):
    """Calculate advanced trading signals with RSI for Bollinger Bands"""
    
    # Band position
    band_range = upper_band - lower_band
    if band_range > 0:
        band_position = (current_price - lower_band) / band_range
    else:
        band_position = 0.5
    
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
    
    # False breakout detection
    false_breakout = detect_false_breakout(data, current_price, upper_band, lower_band)
    
    return {
        'band_position': band_position,
        'volatility_score': volatility_score,
        'sma_trend': sma_trend,
        'rsi': rsi,
        'is_sideways_market': is_sideways,
        'false_breakout_risk': false_breakout
    }

def analyze_stock_comprehensive(ticker, bb_period=20, std_multiplier=2.0, volume_days=20, momentum_days=5, debug=False):
    """
    Comprehensive stock analysis with Bollinger Bands and proper trading days logic
    """
    try:
        print(f"📊 Analyzing {ticker} (using TRADING DAYS only)...")
        
        # Initialize variables with safe defaults
        volume_analysis = {'volume_strength': 'NORMAL', 'volume_trend': 'NEUTRAL', 'volume_sma_ratio': 1.0}
        advanced = {
            'band_position': 0.5,
            'volatility_score': 0,
            'sma_trend': 0,
            'rsi': 50,
            'is_sideways_market': False,
            'false_breakout_risk': False
        }
        
        # Get data
        data = get_stock_data(ticker, bb_period)
        if data is None:
            return None
        
        print(f"   📅 Data: {len(data)} trading days available")
        
        # Calculate Bollinger Bands using TRADING DAYS
        data['Middle_Band'] = data['Close'].rolling(window=bb_period).mean()
        data['BB_Std'] = data['Close'].rolling(window=bb_period).std()
        data['Upper_Band'] = data['Middle_Band'] + (std_multiplier * data['BB_Std'])
        data['Lower_Band'] = data['Middle_Band'] - (std_multiplier * data['BB_Std'])
        
        # Get latest values
        latest = data.iloc[-1]
        current_price = latest['Close']
        upper_band = latest['Upper_Band']
        lower_band = latest['Lower_Band']
        middle_band = latest['Middle_Band']
        current_volume = latest['Volume']
        
        # Skip if no valid band data
        if pd.isna(upper_band) or pd.isna(lower_band) or pd.isna(middle_band):
            print(f"   ⚠️  {ticker}: No valid Bollinger Bands data")
            return None
        
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
            volume_analysis = {'volume_strength': 'NORMAL', 'volume_trend': 'NEUTRAL', 'volume_sma_ratio': 1.0}
        
        print(f"   📊 Volume: Current {current_volume:,.0f} vs {volume_days}-day avg = {volume_ratio:.1f}x ({volume_analysis['volume_strength']})")
        print(f"   🚀 Momentum: {momentum:+.1f}% ({momentum_days} trading days)")
        
        # Calculate advanced signals with RSI
        try:
            advanced = calculate_advanced_signals(data, current_price, upper_band, middle_band, lower_band)
            if debug:
                print(f"   🐛 DEBUG: Advanced signals successful - RSI: {advanced['rsi']:.1f}")
            print(f"   📈 RSI: {advanced['rsi']:.1f}")
            
            # Market condition warnings
            if advanced['is_sideways_market']:
                print(f"   ⚠️  WARNING: Sideways market detected - signals may be less reliable")
            
            if advanced['false_breakout_risk']:
                print(f"   ⚠️  WARNING: False breakout risk detected")
        except Exception as e:
            if debug:
                print(f"   🐛 DEBUG: Advanced analysis error: {e}")
            # Keep the initialized fallback values
            print(f"   📈 RSI: {advanced['rsi']:.1f} (using defaults)")
        
        if debug:
            print(f"   🐛 DEBUG: BB values - Upper: {upper_band:.2f}, Middle: {middle_band:.2f}, Lower: {lower_band:.2f}")
            print(f"   🐛 DEBUG: Signal determination - Price: {current_price:.2f}")
        
        # Determine signal type and strength based on Bollinger Bands logic
        signal_type = 'HOLD'
        buy_strength = 0
        sell_strength = 0
        
        # STRONG_BUY: Price breaks above upper Bollinger Band
        if current_price > upper_band:
            signal_type = 'STRONG_BUY'
            buy_strength = ((current_price - upper_band) / upper_band) * 100
            if debug:
                print(f"   🐛 DEBUG: STRONG_BUY detected - {buy_strength:.2f}% above upper band")
        
        # WEAK_BUY: Price above middle band (SMA) but below upper band
        elif current_price > middle_band:
            signal_type = 'WEAK_BUY'
            buy_strength = ((current_price - middle_band) / middle_band) * 100 * 0.5
            if debug:
                print(f"   🐛 DEBUG: WEAK_BUY detected - {buy_strength:.2f}% above middle band")
        
        # STRONG_SELL: Price breaks below lower Bollinger Band
        elif current_price < lower_band:
            signal_type = 'STRONG_SELL'
            sell_strength = ((lower_band - current_price) / lower_band) * 100
            if debug:
                print(f"   🐛 DEBUG: STRONG_SELL detected - {sell_strength:.2f}% below lower band")
        
        # WEAK_SELL: Price below middle band (SMA) but above lower band
        elif current_price < middle_band:
            signal_type = 'WEAK_SELL'
            sell_strength = ((middle_band - current_price) / middle_band) * 100 * 0.5
            if debug:
                print(f"   🐛 DEBUG: WEAK_SELL detected - {sell_strength:.2f}% below middle band")
        else:
            if debug:
                print(f"   🐛 DEBUG: HOLD signal - price within middle range")
        
        # Risk management
        if signal_type in ['STRONG_BUY', 'WEAK_BUY']:
            stop_loss = lower_band  # Use lower band as stop loss for long positions
            risk_per_share = current_price - stop_loss
        else:
            stop_loss = upper_band  # Use upper band as stop loss for short positions
            risk_per_share = stop_loss - current_price
        
        # Position sizing (1% risk on 100k capital)
        capital = 100000
        risk_amount = capital * 0.01
        position_size = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
        
        result = {
            'ticker': ticker,
            'signal_type': signal_type,
            'current_price': float(current_price),
            'upper_band': float(upper_band),
            'middle_band': float(middle_band),
            'lower_band': float(lower_band),
            'stop_loss': float(stop_loss),
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
            'bb_period': int(bb_period),
            'std_multiplier': float(std_multiplier),
            'band_position': float(advanced.get('band_position', 0.5)),
            'volatility_score': float(advanced.get('volatility_score', 0)),
            'sma_trend': float(advanced.get('sma_trend', 0)),
            'rsi': float(advanced.get('rsi', 50)),
            'is_sideways_market': bool(advanced.get('is_sideways_market', False)),
            'false_breakout_risk': bool(advanced.get('false_breakout_risk', False))
        }
        
        print(f"   🎯 Signal: {signal_type}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error analyzing {ticker}: {e}")
        return None

def analyze_all_stocks(bb_period=20, std_multiplier=2.0, volume_days=20, momentum_days=5, max_workers=3, debug=False):
    """Analyze all stocks with comprehensive Bollinger Bands metrics"""
    
    # Get tickers from config
    tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
    
    print(f"\n🚀 COMPREHENSIVE BOLLINGER BANDS ANALYSIS")
    print(f"📊 Analyzing {len(tickers)} stocks")
    print(f"📈 Bollinger Period: {bb_period} trading days")
    print(f"📊 Standard Deviation: {std_multiplier}x")
    print(f"📊 Volume Period: {volume_days} trading days")
    print(f"🚀 Momentum Period: {momentum_days} trading days")
    print("="*60)
    
    all_signals = []
    
    # Analyze stocks (reduced workers to avoid rate limits)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(analyze_stock_comprehensive, ticker, bb_period, std_multiplier, volume_days, momentum_days, debug): ticker 
            for ticker in tickers
        }
        
        completed = 0
        successful = 0
        failed = 0
        
        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            completed += 1
            
            try:
                result = future.result(timeout=30)  # 30 second timeout per stock
                if result:
                    all_signals.append(result)
                    successful += 1
                    print(f"✅ {ticker} ({completed}/{len(tickers)}) - {result['signal_type']}")
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

def sort_signals_properly(signals):
    """Sort signals with STRONG first, then WEAK, by strength within each category"""
    
    if not signals:
        return signals
    
    # Separate STRONG and WEAK signals
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
    """Display top N signals"""
    
    if not signals:
        print(f"\n❌ No {signal_title} signals found!")
        return
    
    # Signals should already be sorted by sort_signals_properly function
    # but ensure they are sorted correctly here too
    signals = sort_signals_properly(signals)
    
    # Get top N
    top_signals = signals[:top_n]
    
    print(f"\n🏆 TOP {len(top_signals)} {signal_title} SIGNALS")
    print(f"📊 {top_signals[0]['bb_period']}-Day Bollinger Bands ({top_signals[0]['std_multiplier']}σ)")
    print("="*80)
    
    # Prepare table
    table_data = []
    headers = ['Rank', 'Ticker', 'Signal', 'Price', 'Target', 'Strength%', 
              'Volume', 'RSI', 'Momentum%', 'Stop Loss', 'Qty']
    
    for i, signal in enumerate(top_signals, 1):
        if 'BUY' in signal['signal_type']:
            target_level = signal['upper_band'] if signal['signal_type'] == 'STRONG_BUY' else signal['middle_band']
            strength = signal['buy_strength']
        else:
            target_level = signal['lower_band'] if signal['signal_type'] == 'STRONG_SELL' else signal['middle_band']
            strength = signal['sell_strength']
        
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
            # Fallback if volume_analysis is not available
            volume_display = f"{signal['volume_ratio']:.1f}x"
        
        table_data.append([
            i,
            signal['ticker'],
            signal['signal_type'].replace('_', ' '),
            f"₹{signal['current_price']:.2f}",
            f"₹{target_level:.2f}",
            f"{strength:.2f}%",
            volume_display,
            rsi_display,
            f"{signal['momentum']:+.1f}%",
            f"₹{signal['stop_loss']:.2f}",
            signal['position_size']
        ])
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Summary statistics
    avg_strength = sum(strength for signal in top_signals 
                      for strength in [signal['buy_strength'] if 'BUY' in signal['signal_type'] 
                                     else signal['sell_strength']]) / len(top_signals)
    avg_volume = sum(signal['volume_ratio'] for signal in top_signals) / len(top_signals)
    avg_momentum = sum(signal['momentum'] for signal in top_signals) / len(top_signals)
    
    print(f"\n📊 SUMMARY:")
    print(f"   🎯 {signal_title} signals: {len(signals)}")
    print(f"   📈 Average strength: {avg_strength:.2f}%")
    print(f"   📊 Average volume ratio: {avg_volume:.1f}x")
    print(f"   🚀 Average momentum: {avg_momentum:+.1f}%")
    
    print(f"\n🏆 RANKING EXPLANATION:")
    print(f"   📊 Sorted by: STRONG signals first, then WEAK signals")
    print(f"   🎯 Within each type: Higher strength = Better opportunities") 

def generate_comprehensive_html(all_signals, bb_period, std_multiplier, volume_days, momentum_days, output_dir):
    """Generate comprehensive HTML report for Bollinger Bands"""
    
    if not all_signals:
        print("❌ No signals to generate report")
        return None
    
    # Separate signals by type
    buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY', 'WEAK_BUY'])
    sell_signals = filter_signals_by_type(all_signals, ['STRONG_SELL', 'WEAK_SELL'])
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
        <title>Comprehensive Bollinger Bands Analysis - {datetime.now().strftime('%Y-%m-%d')}</title>
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
                <h1>📊 COMPREHENSIVE BOLLINGER BANDS ANALYSIS</h1>
                <p><strong>Trading Days Strategy Report</strong></p>
                <p>Bollinger: {bb_period} days ({std_multiplier}σ) | Volume: {volume_days} days | Momentum: {momentum_days} days</p>
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
                    <h3>{len(hold_signals)}</h3>
                    <p>HOLD Signals</p>
                </div>
                <div class="stat-card">
                    <h3>{len(all_signals)}</h3>
                    <p>Total Analyzed</p>
                </div>
            </div>
    """
    
    # Generate BUY signals table
    if buy_signals:
        html_content += f"""
            <div class="section">
                <h2>🟢 TOP BUY SIGNALS</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Ticker</th>
                            <th>Signal</th>
                            <th>Price</th>
                            <th>Target</th>
                            <th>Strength</th>
                            <th>Volume</th>
                            <th>RSI</th>
                            <th>Momentum</th>
                            <th>Stop Loss</th>
                            <th>Qty</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for i, signal in enumerate(buy_signals[:15], 1):  # Top 15
            target = signal['upper_band'] if signal['signal_type'] == 'STRONG_BUY' else signal['middle_band']
            signal_class = signal['signal_type'].lower().replace('_', '-')
            momentum_class = 'positive' if signal['momentum'] >= 0 else 'negative'
            
            html_content += f"""
                        <tr>
                            <td class="rank">{i}</td>
                            <td class="ticker">{signal['ticker']}</td>
                            <td><span class="{signal_class}">{signal['signal_type'].replace('_', ' ')}</span></td>
                            <td class="price">₹{signal['current_price']:.2f}</td>
                            <td class="price">₹{target:.2f}</td>
                            <td>{signal['buy_strength']:.2f}%</td>
                            <td>{signal['volume_ratio']:.1f}x</td>
                            <td>{signal.get('rsi', 50):.0f}</td>
                            <td class="{momentum_class}">{signal['momentum']:+.1f}%</td>
                            <td class="price">₹{signal['stop_loss']:.2f}</td>
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
                <h2>🔴 TOP SELL SIGNALS</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Ticker</th>
                            <th>Signal</th>
                            <th>Price</th>
                            <th>Target</th>
                            <th>Strength</th>
                            <th>Volume</th>
                            <th>RSI</th>
                            <th>Momentum</th>
                            <th>Stop Loss</th>
                            <th>Qty</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for i, signal in enumerate(sell_signals[:15], 1):  # Top 15
            target = signal['lower_band'] if signal['signal_type'] == 'STRONG_SELL' else signal['middle_band']
            signal_class = signal['signal_type'].lower().replace('_', '-')
            momentum_class = 'positive' if signal['momentum'] >= 0 else 'negative'
            
            html_content += f"""
                        <tr>
                            <td class="rank">{i}</td>
                            <td class="ticker">{signal['ticker']}</td>
                            <td><span class="{signal_class}">{signal['signal_type'].replace('_', ' ')}</span></td>
                            <td class="price">₹{signal['current_price']:.2f}</td>
                            <td class="price">₹{target:.2f}</td>
                            <td>{signal['sell_strength']:.2f}%</td>
                            <td>{signal['volume_ratio']:.1f}x</td>
                            <td>{signal.get('rsi', 50):.0f}</td>
                            <td class="{momentum_class}">{signal['momentum']:+.1f}%</td>
                            <td class="price">₹{signal['stop_loss']:.2f}</td>
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
                <p><strong>📊 Strategy:</strong> Bollinger Bands mean reversion/breakout system with volume confirmation and momentum analysis using proper trading days calculation.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Save HTML
    html_filename = f"comprehensive_bollinger_analysis_{bb_period}d_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    html_path = os.path.join(output_dir, html_filename)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return html_path

def save_results_json(all_signals, output_dir, bb_period, std_multiplier):
    """Save results to JSON for further analysis"""
    
    if not all_signals:
        return None
    
    # Prepare data for JSON serialization - Convert all non-serializable types
    json_signals = []
    for signal in all_signals:
        json_signal = {}
        for key, value in signal.items():
            if isinstance(value, (int, float, str, bool, list, dict)):
                # Handle nested dictionaries
                if isinstance(value, dict):
                    json_signal[key] = {k: v for k, v in value.items() if isinstance(v, (int, float, str, bool, list))}
                else:
                    json_signal[key] = value
            else:
                # Convert numpy types and other non-serializable types
                try:
                    json_signal[key] = float(value) if hasattr(value, 'item') else str(value)
                except:
                    json_signal[key] = str(value)
    
    # Prepare data for JSON serialization
    json_data = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'total_stocks_analyzed': len(json_signals),
            'bb_period': int(bb_period),
            'std_multiplier': float(std_multiplier),
            'strategy': 'Bollinger Bands with Trading Days Logic'
        },
        'signals': json_signals
    }
    
    # Save JSON
    json_filename = f"bollinger_signals_{bb_period}d_{std_multiplier}std_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_path = os.path.join(output_dir, json_filename)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    return json_path

def main():
    """Main function with comprehensive Bollinger Bands analysis"""
    parser = argparse.ArgumentParser(description="Comprehensive Bollinger Bands Analyzer with Trading Days Logic")
    
    parser.add_argument('--period', type=int, default=20, 
                       help='Bollinger Bands period (default: 20)')
    parser.add_argument('--std', type=float, default=2.0, 
                       help='Standard deviation multiplier (default: 2.0)')
    parser.add_argument('--volume-days', type=int, default=20, 
                       help='Volume average days (default: 20)')
    parser.add_argument('--momentum-days', type=int, default=5, 
                       help='Momentum calculation days (default: 5)')
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
            args.period, 
            args.std,
            args.volume_days, 
            args.momentum_days, 
            debug=True
        )
        if result:
            print(f"\n✅ SUCCESS! Signal: {result['signal_type']}")
        else:
            print(f"\n❌ No result for {args.test_single}")
        return
    
    print("🎯 COMPREHENSIVE BOLLINGER BANDS ANALYZER")
    print("🔄 Using Proper Trading Days Logic")
    print("="*50)
    print(f"📅 Bollinger Period: {args.period} trading days")
    print(f"📊 Standard Deviation: {args.std}x")
    print(f"📊 Volume Period: {args.volume_days} trading days") 
    print(f"🚀 Momentum Period: {args.momentum_days} trading days")
    print(f"🏆 Top Signals: {args.top}")
    print(f"⚙️  Workers: {args.workers}")
    print("="*50)
    
    # Set output directory
    output_dir = args.output or getattr(config, 'OUTPUT_DIR', 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Get tickers for debug info
    tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
    
    # Analyze all stocks
    all_signals = analyze_all_stocks(
        bb_period=args.period,
        std_multiplier=args.std,
        volume_days=args.volume_days, 
        momentum_days=args.momentum_days,
        max_workers=args.workers,
        debug=args.debug
    )
    
    if not all_signals:
        print("\n❌ No signals generated!")
        print("💡 TROUBLESHOOTING TIPS:")
        print("   🔧 Try shorter period: --period 10 or --period 14")
        print("   🔧 Try different std multiplier: --std 1.5 or --std 2.5")
        print("   🔧 Check if markets are open and data is available")
        print("   🔧 Reduce volume/momentum periods: --volume-days 10 --momentum-days 3")
        print("   🔧 Enable debug mode: --debug")
        print("   🔧 Check internet connection for data fetching")
        print("   🔧 Verify stock symbols are correct in config")
        if args.debug:
            print(f"\n🐛 DEBUG INFO:")
            print(f"   📊 Total tickers attempted: {len(tickers)}")
            print(f"   📅 BB Period: {args.period}")
            print(f"   📊 Std Multiplier: {args.std}")
            print(f"   📊 Volume days: {args.volume_days}")
            print(f"   🚀 Momentum days: {args.momentum_days}")
        return
    
    # Display results based on arguments
    if args.buy_only:
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
        # Default: Show BUY signals only
        buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY', 'WEAK_BUY'])
        buy_signals = sort_signals_properly(buy_signals) if buy_signals else []
        display_top_signals(buy_signals, "BUY", args.top)
    
    # Generate reports
    print(f"\n📄 Generating reports...")
    
    # HTML Report
    html_path = generate_comprehensive_html(
        all_signals, args.period, args.std, args.volume_days, args.momentum_days, output_dir
    )
    if html_path:
        print(f"🌐 HTML Report: {html_path}")
        print(f"🔗 Open: file://{os.path.abspath(html_path)}")
    
    # JSON Report
    json_path = save_results_json(all_signals, output_dir, args.period, args.std)
    if json_path:
        print(f"📊 JSON Data: {json_path}")
    
    print(f"\n✅ Analysis Complete!")
    print(f"📁 Output Directory: {os.path.abspath(output_dir)}")
    
    # Trading notes
    print(f"\n💡 TRADING NOTES:")
    print(f"   🟢 STRONG BUY: Price broke above upper Bollinger Band")
    print(f"   🟡 WEAK BUY: Price above middle band (SMA)")
    print(f"   🔴 STRONG SELL: Price broke below lower Bollinger Band")
    print(f"   🟠 WEAK SELL: Price below middle band (SMA)")
    print(f"   🛑 STOP LOSS: Use opposite band as stop")
    print(f"   📊 VOLUME: Enhanced analysis with strength classification")
    print(f"   📈 RSI: Overbought/oversold confirmation")
    print(f"   ⚖️  POSITION SIZE: 1% risk-based sizing")
    print(f"   📏 BB PARAMETERS: {args.period}-period SMA ± {args.std}σ")
    
    print(f"\n🧪 TROUBLESHOOTING COMMANDS:")
    print(f"   python {sys.argv[0]} --test-single RELIANCE --debug")
    print(f"   python {sys.argv[0]} --period 10 --std 1.5 --debug")

if __name__ == "__main__":
    main()