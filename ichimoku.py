#!/usr/bin/env python
# ichimoku_analyzer.py - Comprehensive Ichimoku Strategy Analyzer

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
    print("⚠ Config not found! Using default tickers")
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

def get_stock_data(ticker, lookback_days=52):
    """Get stock data for Ichimoku analysis with proper error handling"""
    try:
        # Add .NS for NSE stocks
        symbol = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
        
        # Get enough data for lookback + buffer (trading days only)
        days_needed = lookback_days + 100  # Extra buffer for weekends/holidays
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

def calculate_donchian(data, period):
    """Calculate Donchian Channel (used in Ichimoku calculations)"""
    highest = data['High'].rolling(window=period).max()
    lowest = data['Low'].rolling(window=period).min()
    return (highest + lowest) / 2

def calculate_volume_analysis(data, current_volume, lookback_days):
    """Enhanced volume analysis"""
    try:
        if data is None or len(data) < 5:
            return {'volume_strength': 'WEAK', 'volume_trend': 'NEUTRAL', 'volume_ratio': 1.0}
        
        if lookback_days < 5:
            lookback_days = 5
        
        vol_sma_short = data['Volume'].rolling(window=min(5, len(data))).mean().iloc[-1]
        vol_sma_long = data['Volume'].rolling(window=min(lookback_days, len(data))).mean().iloc[-1]
        
        if pd.isna(vol_sma_short) or pd.isna(vol_sma_long) or vol_sma_long == 0:
            return {'volume_strength': 'WEAK', 'volume_trend': 'NEUTRAL', 'volume_ratio': 1.0}
        
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
            'volume_ratio': volume_ratio
        }
    except Exception as e:
        return {'volume_strength': 'WEAK', 'volume_trend': 'NEUTRAL', 'volume_ratio': 1.0}

def calculate_momentum(data, momentum_days=5):
    """Calculate momentum using trading days"""
    try:
        if len(data) < momentum_days + 1:
            return 0
        
        current_price = data['Close'].iloc[-1]
        price_n_days_ago = data['Close'].iloc[-(momentum_days+1)]
        momentum = ((current_price - price_n_days_ago) / price_n_days_ago) * 100
        return momentum
    except:
        return 0

def analyze_ichimoku_comprehensive(ticker, conversion_periods=9, base_periods=26, 
                                 lagging_span2_periods=52, displacement=26,
                                 volume_days=20, momentum_days=5, atr_length=14,
                                 risk_reward=2.0, debug=False):
    """
    Comprehensive Ichimoku analysis with all components
    """
    try:
        print(f"📊 Analyzing {ticker} (Ichimoku Cloud Strategy)...")
        
        # Get data
        data = get_stock_data(ticker, lagging_span2_periods + displacement)
        if data is None:
            return None
        
        print(f"   📅 Data: {len(data)} trading days available")
        
        # Calculate Ichimoku components
        data['Conversion_Line'] = calculate_donchian(data, conversion_periods)
        data['Base_Line'] = calculate_donchian(data, base_periods)
        data['Lead_Line_1'] = (data['Conversion_Line'] + data['Base_Line']) / 2
        data['Lead_Line_2'] = calculate_donchian(data, lagging_span2_periods)
        
        # Get latest values
        latest = data.iloc[-1]
        current_price = latest['Close']
        current_open = latest['Open']
        current_volume = latest['Volume']
        
        conversion_line = latest['Conversion_Line']
        base_line = latest['Base_Line']
        
        # Cloud values (displaced)
        if len(data) >= displacement:
            lead1_displaced = data['Lead_Line_1'].iloc[-displacement] if len(data) > displacement else data['Lead_Line_1'].iloc[-1]
            lead2_displaced = data['Lead_Line_2'].iloc[-displacement] if len(data) > displacement else data['Lead_Line_2'].iloc[-1]
        else:
            lead1_displaced = latest['Lead_Line_1']
            lead2_displaced = latest['Lead_Line_2']
        
        # Lagging span (current close displaced back)
        if len(data) >= displacement * 2:
            lagging_span_cloud1 = data['Lead_Line_1'].iloc[-displacement*2] if len(data) > displacement*2 else data['Lead_Line_1'].iloc[-1]
            lagging_span_cloud2 = data['Lead_Line_2'].iloc[-displacement*2] if len(data) > displacement*2 else data['Lead_Line_2'].iloc[-1]
        else:
            lagging_span_cloud1 = latest['Lead_Line_1']
            lagging_span_cloud2 = latest['Lead_Line_2']
        
        # Skip if no valid data
        if pd.isna(conversion_line) or pd.isna(base_line) or pd.isna(lead1_displaced) or pd.isna(lead2_displaced):
            print(f"   ⚠️  {ticker}: No valid Ichimoku data")
            return None
        
        # Calculate additional metrics
        volume_ratio = current_volume / data['Volume'].rolling(window=min(volume_days, len(data))).mean().iloc[-1] if len(data) >= volume_days else 1.0
        momentum = calculate_momentum(data, momentum_days)
        rsi = calculate_rsi(data['Close'])
        volume_analysis = calculate_volume_analysis(data, current_volume, volume_days)
        
        print(f"   📊 Volume: {volume_ratio:.1f}x ({volume_analysis['volume_strength']})")
        print(f"   🚀 Momentum: {momentum:+.1f}% ({momentum_days} trading days)")
        print(f"   📈 RSI: {rsi:.1f}")
        
        # Ichimoku Signal Analysis
        # LONG conditions
        con_above_base = conversion_line > base_line
        cloud_green = lead1_displaced > lead2_displaced
        close_above_cloud = current_open > lead1_displaced and current_open > lead2_displaced
        lagging_span_above_cloud = current_price > lagging_span_cloud1 and current_price > lagging_span_cloud2
        
        # SHORT conditions  
        con_below_base = conversion_line < base_line
        cloud_red = lead2_displaced > lead1_displaced
        close_below_cloud = current_open < lead1_displaced and current_open < lead2_displaced
        lagging_span_below_cloud = current_price < lagging_span_cloud1 and current_price < lagging_span_cloud2
        
        # Determine signal
        signal_type = 'HOLD'
        signal_strength = 0
        conditions_met = 0
        total_conditions = 4
        
        if con_above_base and cloud_green and close_above_cloud and lagging_span_above_cloud:
            signal_type = 'STRONG_BUY'
            conditions_met = 4
            signal_strength = (conditions_met / total_conditions) * 100
        elif (con_above_base and cloud_green and close_above_cloud) or \
             (con_above_base and cloud_green and lagging_span_above_cloud) or \
             (con_above_base and close_above_cloud and lagging_span_above_cloud):
            signal_type = 'WEAK_BUY'
            conditions_met = 3
            signal_strength = (conditions_met / total_conditions) * 100 * 0.75
        elif con_below_base and cloud_red and close_below_cloud and lagging_span_below_cloud:
            signal_type = 'STRONG_SELL'
            conditions_met = 4
            signal_strength = (conditions_met / total_conditions) * 100
        elif (con_below_base and cloud_red and close_below_cloud) or \
             (con_below_base and cloud_red and lagging_span_below_cloud) or \
             (con_below_base and close_below_cloud and lagging_span_below_cloud):
            signal_type = 'WEAK_SELL'
            conditions_met = 3
            signal_strength = (conditions_met / total_conditions) * 100 * 0.75
        
        if debug:
            print(f"   🛠 DEBUG: Conversion: {conversion_line:.2f}, Base: {base_line:.2f}")
            print(f"   🛠 DEBUG: Lead1: {lead1_displaced:.2f}, Lead2: {lead2_displaced:.2f}")
            print(f"   🛠 DEBUG: Conditions - Conv>Base: {con_above_base}, Green: {cloud_green}")
            print(f"   🛠 DEBUG: Above Cloud: {close_above_cloud}, Lag Above: {lagging_span_above_cloud}")
        
        # Risk management
        if signal_type in ['STRONG_BUY', 'WEAK_BUY']:
            stop_loss = min(lead1_displaced, lead2_displaced)
            target_price = current_price + ((current_price - stop_loss) * risk_reward)
        elif signal_type in ['STRONG_SELL', 'WEAK_SELL']:
            stop_loss = max(lead1_displaced, lead2_displaced)
            target_price = current_price - ((stop_loss - current_price) * risk_reward)
        else:
            stop_loss = lead1_displaced
            target_price = current_price
        
        risk_per_share = abs(current_price - stop_loss)
        
        # Position sizing (1% risk)
        capital = 100000
        risk_amount = capital * 0.01
        position_size = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
        
        # Calculate ATR for volatility
        if len(data) >= atr_length:
            high_low = data['High'] - data['Low']
            high_close = abs(data['High'] - data['Close'].shift(1))
            low_close = abs(data['Low'] - data['Close'].shift(1))
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = tr.rolling(window=atr_length).mean().iloc[-1]
            volatility_score = (atr / current_price) * 100
        else:
            volatility_score = 0
        
        result = {
            'ticker': ticker,
            'signal_type': signal_type,
            'signal_strength': float(signal_strength),
            'conditions_met': int(conditions_met),
            'total_conditions': int(total_conditions),
            'current_price': float(current_price),
            'conversion_line': float(conversion_line),
            'base_line': float(base_line),
            'lead1_displaced': float(lead1_displaced),
            'lead2_displaced': float(lead2_displaced),
            'cloud_color': 'GREEN' if lead1_displaced > lead2_displaced else 'RED',
            'stop_loss': float(stop_loss),
            'target_price': float(target_price),
            'volume_ratio': float(volume_ratio),
            'volume_analysis': volume_analysis,
            'momentum': float(momentum),
            'rsi': float(rsi),
            'volatility_score': float(volatility_score),
            'position_size': int(position_size),
            'risk_per_share': float(risk_per_share),
            'risk_reward_ratio': float(risk_reward),
            'trading_days_used': int(len(data)),
            'ichimoku_params': {
                'conversion_periods': int(conversion_periods),
                'base_periods': int(base_periods),
                'lagging_span2_periods': int(lagging_span2_periods),
                'displacement': int(displacement)
            },
            'conditions': {
                'conversion_above_base': bool(con_above_base),
                'cloud_green': bool(cloud_green),
                'close_above_cloud': bool(close_above_cloud),
                'lagging_span_above_cloud': bool(lagging_span_above_cloud),
                'conversion_below_base': bool(con_below_base),
                'cloud_red': bool(cloud_red),
                'close_below_cloud': bool(close_below_cloud),
                'lagging_span_below_cloud': bool(lagging_span_below_cloud)
            }
        }
        
        print(f"   🎯 Signal: {signal_type} ({conditions_met}/{total_conditions} conditions)")
        
        return result
        
    except Exception as e:
        print(f"❌ Error analyzing {ticker}: {e}")
        return None

def analyze_all_stocks(conversion_periods=9, base_periods=26, lagging_span2_periods=52,
                      displacement=26, volume_days=20, momentum_days=5, 
                      risk_reward=2.0, max_workers=3, debug=False):
    """Analyze all stocks with Ichimoku strategy"""
    
    tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
    
    print(f"\n🚀 COMPREHENSIVE ICHIMOKU CLOUD ANALYSIS")
    print(f"📊 Analyzing {len(tickers)} stocks")
    print(f"📈 Ichimoku Parameters:")
    print(f"   🔄 Conversion Line: {conversion_periods} periods")
    print(f"   📏 Base Line: {base_periods} periods") 
    print(f"   📊 Leading Span 2: {lagging_span2_periods} periods")
    print(f"   ➡️ Displacement: {displacement} periods")
    print(f"📊 Volume Period: {volume_days} trading days")
    print(f"🚀 Momentum Period: {momentum_days} trading days")
    print(f"💰 Risk/Reward Ratio: {risk_reward}:1")
    print("="*60)
    
    all_signals = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(analyze_ichimoku_comprehensive, ticker, conversion_periods, 
                          base_periods, lagging_span2_periods, displacement,
                          volume_days, momentum_days, 14, risk_reward, debug): ticker 
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

def sort_signals_by_strength(signals):
    """Sort signals by strength (conditions met and signal strength)"""
    if not signals:
        return signals
    
    # Sort by conditions met first, then by signal strength
    signals.sort(key=lambda x: (x['conditions_met'], x['signal_strength']), reverse=True)
    return signals

def display_top_ichimoku_signals(signals, signal_title, top_n=10):
    """Display top N Ichimoku signals"""
    
    if not signals:
        print(f"\n❌ No {signal_title} signals found!")
        return
    
    signals = sort_signals_by_strength(signals)
    top_signals = signals[:top_n]
    
    print(f"\n🏆 TOP {len(top_signals)} {signal_title} SIGNALS")
    print(f"📊 Ichimoku Cloud Strategy")
    print("="*80)
    
    table_data = []
    headers = ['Rank', 'Ticker', 'Signal', 'Price', 'Target', 'Conditions', 
              'Volume', 'RSI', 'Momentum%', 'Stop Loss', 'R:R', 'Qty']
    
    for i, signal in enumerate(top_signals, 1):
        # RSI display
        rsi_value = signal.get('rsi', 50)
        rsi_display = f"{rsi_value:.0f}"
        if rsi_value > 70:
            rsi_display += "🔴"
        elif rsi_value < 30:
            rsi_display += "🟢"
        
        # Volume display
        volume_strength = signal['volume_analysis']['volume_strength']
        volume_display = f"{signal['volume_ratio']:.1f}x"
        if volume_strength == 'VERY_HIGH':
            volume_display += "🟢"
        elif volume_strength == 'HIGH':
            volume_display += "🟡"
        elif volume_strength == 'WEAK':
            volume_display += "🔴"
        
        # Momentum color
        momentum_class = '🟢' if signal['momentum'] >= 0 else '🔴'
        
        table_data.append([
            i,
            signal['ticker'],
            signal['signal_type'].replace('_', ' '),
            f"₹{signal['current_price']:.2f}",
            f"₹{signal['target_price']:.2f}",
            f"{signal['conditions_met']}/{signal['total_conditions']}",
            volume_display,
            rsi_display,
            f"{signal['momentum']:+.1f}%{momentum_class}",
            f"₹{signal['stop_loss']:.2f}",
            f"{signal['risk_reward_ratio']:.1f}:1",
            signal['position_size']
        ])
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Summary statistics
    avg_conditions = sum(signal['conditions_met'] for signal in top_signals) / len(top_signals)
    avg_volume = sum(signal['volume_ratio'] for signal in top_signals) / len(top_signals)
    avg_momentum = sum(signal['momentum'] for signal in top_signals) / len(top_signals)
    
    print(f"\n📊 SUMMARY:")
    print(f"   🎯 {signal_title} signals: {len(signals)}")
    print(f"   📈 Average conditions met: {avg_conditions:.1f}/4")
    print(f"   📊 Average volume ratio: {avg_volume:.1f}x")
    print(f"   🚀 Average momentum: {avg_momentum:+.1f}%")
    
    print(f"\n🏆 ICHIMOKU CONDITIONS:")
    print(f"   1️⃣ Conversion Line > Base Line (Tenkan > Kijun)")
    print(f"   2️⃣ Cloud is Green (Senkou A > Senkou B)")
    print(f"   3️⃣ Price Above Cloud")
    print(f"   4️⃣ Lagging Span Above Cloud")
    print(f"   🎯 4/4 = STRONG signal, 3/4 = WEAK signal")

def generate_ichimoku_html_report(all_signals, ichimoku_params, volume_days, momentum_days, output_dir):
    """Generate comprehensive HTML report for Ichimoku analysis"""
    
    if not all_signals:
        print("❌ No signals to generate report")
        return None
    
    # Separate signals by type
    buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY', 'WEAK_BUY'])
    sell_signals = filter_signals_by_type(all_signals, ['STRONG_SELL', 'WEAK_SELL'])
    hold_signals = filter_signals_by_type(all_signals, ['HOLD'])
    
    # Sort by strength
    buy_signals = sort_signals_by_strength(buy_signals) if buy_signals else []
    sell_signals = sort_signals_by_strength(sell_signals) if sell_signals else []
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Comprehensive Ichimoku Cloud Analysis - {datetime.now().strftime('%Y-%m-%d')}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
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
                background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
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
                background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
            }}
            .stat-card h3 {{
                margin: 0 0 10px 0;
                font-size: 2em;
            }}
            .ichimoku-params {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
                border-left: 5px solid #e74c3c;
            }}
            .section {{
                margin: 40px 0;
            }}
            .section h2 {{
                color: #333;
                border-bottom: 3px solid #e74c3c;
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
            .conditions {{
                text-align: center;
                font-weight: bold;
            }}
            .conditions.perfect {{
                color: #28a745;
            }}
            .conditions.good {{
                color: #ffc107;
            }}
            .conditions.weak {{
                color: #dc3545;
            }}
            .footer {{
                text-align: center;
                margin-top: 40px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 10px;
                border-left: 5px solid #e74c3c;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>☁️ COMPREHENSIVE ICHIMOKU CLOUD ANALYSIS</h1>
                <p><strong>Japanese Cloud Trading Strategy Report</strong></p>
                <p>Generated: {timestamp}</p>
            </div>
            
            <div class="ichimoku-params">
                <h3>🏯 Ichimoku Parameters</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                    <div><strong>Conversion Line:</strong> {ichimoku_params.get('conversion_periods', 9)} periods</div>
                    <div><strong>Base Line:</strong> {ichimoku_params.get('base_periods', 26)} periods</div>
                    <div><strong>Leading Span 2:</strong> {ichimoku_params.get('lagging_span2_periods', 52)} periods</div>
                    <div><strong>Displacement:</strong> {ichimoku_params.get('displacement', 26)} periods</div>
                    <div><strong>Volume Period:</strong> {volume_days} days</div>
                    <div><strong>Momentum Period:</strong> {momentum_days} days</div>
                </div>
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
                            <th>Conditions</th>
                            <th>Volume</th>
                            <th>RSI</th>
                            <th>Momentum</th>
                            <th>Stop Loss</th>
                            <th>R:R</th>
                            <th>Qty</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for i, signal in enumerate(buy_signals[:15], 1):
            signal_class = signal['signal_type'].lower().replace('_', '-')
            momentum_class = 'positive' if signal['momentum'] >= 0 else 'negative'
            
            # Conditions styling
            conditions_met = signal['conditions_met']
            if conditions_met == 4:
                conditions_class = 'perfect'
            elif conditions_met == 3:
                conditions_class = 'good'
            else:
                conditions_class = 'weak'
            
            html_content += f"""
                        <tr>
                            <td class="rank">{i}</td>
                            <td class="ticker">{signal['ticker']}</td>
                            <td><span class="{signal_class}">{signal['signal_type'].replace('_', ' ')}</span></td>
                            <td class="price">₹{signal['current_price']:.2f}</td>
                            <td class="price">₹{signal['target_price']:.2f}</td>
                            <td class="conditions {conditions_class}">{conditions_met}/4</td>
                            <td>{signal['volume_ratio']:.1f}x</td>
                            <td>{signal.get('rsi', 50):.0f}</td>
                            <td class="{momentum_class}">{signal['momentum']:+.1f}%</td>
                            <td class="price">₹{signal['stop_loss']:.2f}</td>
                            <td>{signal['risk_reward_ratio']:.1f}:1</td>
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
                            <th>Conditions</th>
                            <th>Volume</th>
                            <th>RSI</th>
                            <th>Momentum</th>
                            <th>Stop Loss</th>
                            <th>R:R</th>
                            <th>Qty</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for i, signal in enumerate(sell_signals[:15], 1):
            signal_class = signal['signal_type'].lower().replace('_', '-')
            momentum_class = 'positive' if signal['momentum'] >= 0 else 'negative'
            
            conditions_met = signal['conditions_met']
            if conditions_met == 4:
                conditions_class = 'perfect'
            elif conditions_met == 3:
                conditions_class = 'good'
            else:
                conditions_class = 'weak'
            
            html_content += f"""
                        <tr>
                            <td class="rank">{i}</td>
                            <td class="ticker">{signal['ticker']}</td>
                            <td><span class="{signal_class}">{signal['signal_type'].replace('_', ' ')}</span></td>
                            <td class="price">₹{signal['current_price']:.2f}</td>
                            <td class="price">₹{signal['target_price']:.2f}</td>
                            <td class="conditions {conditions_class}">{conditions_met}/4</td>
                            <td>{signal['volume_ratio']:.1f}x</td>
                            <td>{signal.get('rsi', 50):.0f}</td>
                            <td class="{momentum_class}">{signal['momentum']:+.1f}%</td>
                            <td class="price">₹{signal['stop_loss']:.2f}</td>
                            <td>{signal['risk_reward_ratio']:.1f}:1</td>
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
                <p><strong>☁️ Strategy:</strong> Ichimoku Cloud system with 4 key conditions: Conversion > Base, Green Cloud, Price Above Cloud, Lagging Span Above Cloud.</p>
                <p><strong>🎯 Signal Strength:</strong> STRONG = 4/4 conditions, WEAK = 3/4 conditions. Higher ranked signals meet more conditions.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Save HTML
    html_filename = f"ichimoku_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    html_path = os.path.join(output_dir, html_filename)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return html_path

def save_ichimoku_json(all_signals, output_dir, ichimoku_params):
    """Save Ichimoku results to JSON"""
    
    if not all_signals:
        return None
    
    # Prepare data for JSON
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
            'strategy': 'Ichimoku Cloud Analysis',
            'ichimoku_parameters': ichimoku_params
        },
        'signals': json_signals
    }
    
    json_filename = f"ichimoku_signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_path = os.path.join(output_dir, json_filename)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    return json_path

def main():
    """Main function for Ichimoku analysis"""
    parser = argparse.ArgumentParser(description="Comprehensive Ichimoku Cloud Analyzer")
    
    parser.add_argument('--conversion', type=int, default=9, 
                       help='Conversion line periods (default: 9)')
    parser.add_argument('--base', type=int, default=26, 
                       help='Base line periods (default: 26)')
    parser.add_argument('--lagging', type=int, default=52, 
                       help='Leading span 2 periods (default: 52)')
    parser.add_argument('--displacement', type=int, default=26, 
                       help='Cloud displacement (default: 26)')
    parser.add_argument('--volume-days', type=int, default=20, 
                       help='Volume average days (default: 20)')
    parser.add_argument('--momentum-days', type=int, default=5, 
                       help='Momentum calculation days (default: 5)')
    parser.add_argument('--risk-reward', type=float, default=2.0, 
                       help='Risk/Reward ratio (default: 2.0)')
    parser.add_argument('--top', type=int, default=10, 
                       help='Top N signals to display (default: 10)')
    parser.add_argument('--output', type=str, 
                       help='Output directory (default: output)')
    parser.add_argument('--workers', type=int, default=3, 
                       help='Max concurrent workers (default: 3)')
    parser.add_argument('--test-single', type=str, 
                       help='Test analysis on a single ticker')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug output')
    parser.add_argument('--show-all', action='store_true', 
                       help='Show all signal types')
    parser.add_argument('--buy-only', action='store_true', 
                       help='Show only BUY signals')
    parser.add_argument('--sell-only', action='store_true', 
                       help='Show only SELL signals')
    
    args = parser.parse_args()
    
    # Test single ticker if requested
    if args.test_single:
        print(f"🧪 TESTING SINGLE TICKER: {args.test_single}")
        print("="*50)
        result = analyze_ichimoku_comprehensive(
            args.test_single, 
            args.conversion, args.base, args.lagging, args.displacement,
            args.volume_days, args.momentum_days, 14, args.risk_reward,
            debug=True
        )
        if result:
            print(f"\n✅ SUCCESS! Signal: {result['signal_type']}")
            print(f"📊 Conditions: {result['conditions_met']}/{result['total_conditions']}")
        else:
            print(f"\n❌ No result for {args.test_single}")
        return
    
    print("🏯 COMPREHENSIVE ICHIMOKU CLOUD ANALYZER")
    print("☁️ Japanese Trading Strategy Analysis")
    print("="*50)
    
    ichimoku_params = {
        'conversion_periods': args.conversion,
        'base_periods': args.base, 
        'lagging_span2_periods': args.lagging,
        'displacement': args.displacement
    }
    
    # Set output directory
    output_dir = args.output or getattr(config, 'OUTPUT_DIR', 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Analyze all stocks
    all_signals = analyze_all_stocks(
        conversion_periods=args.conversion,
        base_periods=args.base,
        lagging_span2_periods=args.lagging,
        displacement=args.displacement,
        volume_days=args.volume_days,
        momentum_days=args.momentum_days,
        risk_reward=args.risk_reward,
        max_workers=args.workers,
        debug=args.debug
    )
    
    if not all_signals:
        print("\n❌ No signals generated!")
        print("💡 TROUBLESHOOTING TIPS:")
        print("   🔧 Try different Ichimoku parameters")
        print("   🔧 Check if markets are open")
        print("   🔧 Enable debug mode: --debug")
        print("   🔧 Test single stock: --test-single RELIANCE")
        return
    
    # Display results
    if args.buy_only:
        buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY', 'WEAK_BUY'])
        display_top_ichimoku_signals(buy_signals, "BUY", args.top)
    elif args.sell_only:
        sell_signals = filter_signals_by_type(all_signals, ['STRONG_SELL', 'WEAK_SELL'])
        display_top_ichimoku_signals(sell_signals, "SELL", args.top)
    elif args.show_all:
        buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY', 'WEAK_BUY'])
        sell_signals = filter_signals_by_type(all_signals, ['STRONG_SELL', 'WEAK_SELL'])
        hold_signals = filter_signals_by_type(all_signals, ['HOLD'])
        
        if buy_signals:
            display_top_ichimoku_signals(buy_signals, "BUY", args.top)
        if sell_signals:
            display_top_ichimoku_signals(sell_signals, "SELL", args.top)
        
        print(f"\n📊 OVERALL SUMMARY:")
        print(f"   🟢 BUY signals: {len(buy_signals)}")
        print(f"   🔴 SELL signals: {len(sell_signals)}")
        print(f"   ⚪ HOLD signals: {len(hold_signals)}")
    else:
        # Default: Show BUY signals only
        buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY', 'WEAK_BUY'])
        display_top_ichimoku_signals(buy_signals, "BUY", args.top)
    
    # Generate reports
    print(f"\n📄 Generating reports...")
    
    # HTML Report
    html_path = generate_ichimoku_html_report(
        all_signals, ichimoku_params, args.volume_days, args.momentum_days, output_dir
    )
    if html_path:
        print(f"🌐 HTML Report: {html_path}")
        print(f"🔗 Open: file://{os.path.abspath(html_path)}")
    
    # JSON Report
    json_path = save_ichimoku_json(all_signals, output_dir, ichimoku_params)
    if json_path:
        print(f"📊 JSON Data: {json_path}")
    
    print(f"\n✅ Analysis Complete!")
    print(f"📁 Output Directory: {os.path.abspath(output_dir)}")
    
    print(f"\n💡 ICHIMOKU CLOUD STRATEGY:")
    print(f"   ☁️ 4 Key Conditions for Strong Signals:")
    print(f"   1️⃣ Conversion Line > Base Line")
    print(f"   2️⃣ Cloud is Green (Lead 1 > Lead 2)")
    print(f"   3️⃣ Price Above Cloud")
    print(f"   4️⃣ Lagging Span Above Cloud")
    print(f"   🎯 Risk/Reward: {args.risk_reward}:1")

if __name__ == "__main__":
    main()