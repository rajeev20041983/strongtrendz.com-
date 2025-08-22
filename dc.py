#!/usr/bin/env python
# complete_ichimoku_strategy.py - Full Ichimoku Cloud Strategy Implementation
# Based on Ichimoku Kinko Hyo by Goichi Hosoda

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
import math
from typing import Optional, Dict, List, Tuple, Any

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
            {'symbol': 'RELIANCE'}, {'symbol': 'TCS'}, {'symbol': 'HDFCBANK'},
            {'symbol': 'INFY'}, {'symbol': 'HINDUNILVR'}, {'symbol': 'ICICIBANK'},
            {'symbol': 'KOTAKBANK'}, {'symbol': 'ITC'}, {'symbol': 'LT'},
            {'symbol': 'SBIN'}, {'symbol': 'BHARTIARTL'}, {'symbol': 'ASIANPAINT'},
            {'symbol': 'MARUTI'}, {'symbol': 'AXISBANK'}, {'symbol': 'BAJFINANCE'},
            {'symbol': 'WIPRO'}, {'symbol': 'NESTLEIND'}, {'symbol': 'ULTRACEMCO'},
            {'symbol': 'TITAN'}, {'symbol': 'POWERGRID'}
        ]
        OUTPUT_DIR = 'output'
    
    config = DefaultConfig()

warnings.filterwarnings("ignore")

class IchimokuCloudStrategy:
    """
    Complete Ichimoku Cloud Strategy implementation
    
    Components:
    - Tenkan-sen (Conversion Line): 9-period midpoint
    - Kijun-sen (Base Line): 26-period midpoint
    - Senkou Span A (Leading Span A): Average of Tenkan and Kijun, plotted ahead
    - Senkou Span B (Leading Span B): 52-period midpoint, plotted ahead
    - Chikou Span (Lagging Span): Closing price plotted behind
    """
    
    def __init__(self, tenkan_period=9, kijun_period=26, senkou_b_period=52, 
                 displacement=26, target_points=100, stop_loss_points=50):
        self.tenkan_period = tenkan_period          # Conversion Line period
        self.kijun_period = kijun_period            # Base Line period
        self.senkou_b_period = senkou_b_period      # Leading Span B period
        self.displacement = displacement             # Forward/backward displacement
        self.target_points = target_points          # Target in points
        self.stop_loss_points = stop_loss_points    # Stop loss in points
    
    def calculate_ichimoku_components(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate all Ichimoku Cloud components"""
        
        # 1. Tenkan-sen (Conversion Line) - 9 period midpoint
        tenkan_high = data['High'].rolling(window=self.tenkan_period).max()
        tenkan_low = data['Low'].rolling(window=self.tenkan_period).min()
        data['Tenkan_Sen'] = (tenkan_high + tenkan_low) / 2
        
        # 2. Kijun-sen (Base Line) - 26 period midpoint  
        kijun_high = data['High'].rolling(window=self.kijun_period).max()
        kijun_low = data['Low'].rolling(window=self.kijun_period).min()
        data['Kijun_Sen'] = (kijun_high + kijun_low) / 2
        
        # 3. Senkou Span A (Leading Span A) - Average of Tenkan and Kijun, shifted forward
        senkou_a = (data['Tenkan_Sen'] + data['Kijun_Sen']) / 2
        data['Senkou_Span_A'] = senkou_a.shift(self.displacement)
        
        # 4. Senkou Span B (Leading Span B) - 52 period midpoint, shifted forward
        senkou_b_high = data['High'].rolling(window=self.senkou_b_period).max()
        senkou_b_low = data['Low'].rolling(window=self.senkou_b_period).min()
        senkou_b = (senkou_b_high + senkou_b_low) / 2
        data['Senkou_Span_B'] = senkou_b.shift(self.displacement)
        
        # 5. Chikou Span (Lagging Span) - Closing price shifted backward
        data['Chikou_Span'] = data['Close'].shift(-self.displacement)
        
        # Cloud boundaries (for easier reference)
        data['Cloud_Top'] = np.maximum(data['Senkou_Span_A'], data['Senkou_Span_B'])
        data['Cloud_Bottom'] = np.minimum(data['Senkou_Span_A'], data['Senkou_Span_B'])
        
        return data
    
    def calculate_cloud_characteristics(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate cloud characteristics and trend signals"""
        
        # Cloud color (bullish/bearish)
        data['Cloud_Color'] = np.where(
            data['Senkou_Span_A'] > data['Senkou_Span_B'], 
            'BULLISH',  # Green cloud
            'BEARISH'   # Red cloud
        )
        
        # Cloud thickness (strength indicator)
        data['Cloud_Thickness'] = abs(data['Senkou_Span_A'] - data['Senkou_Span_B'])
        data['Cloud_Thickness_Pct'] = (data['Cloud_Thickness'] / data['Close']) * 100
        
        # Price position relative to cloud
        data['Price_vs_Cloud'] = np.where(
            data['Close'] > data['Cloud_Top'], 'ABOVE',
            np.where(data['Close'] < data['Cloud_Bottom'], 'BELOW', 'INSIDE')
        )
        
        # Tenkan-Kijun relationship
        data['TK_Cross'] = np.where(
            data['Tenkan_Sen'] > data['Kijun_Sen'], 'BULLISH', 'BEARISH'
        )
        
        # Chikou Span vs Price (confirmation signal)
        data['Chikou_Confirmation'] = np.where(
            data['Chikou_Span'] > data['Close'].shift(self.displacement), 
            'BULLISH', 'BEARISH'
        )
        
        return data
    
    def calculate_trading_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate Ichimoku trading signals"""
        
        # Basic Ichimoku signals
        data['Basic_Long'] = (
            (data['Close'] > data['Senkou_Span_A']) & 
            (data['Close'] > data['Senkou_Span_B'])
        )
        
        data['Basic_Short'] = (
            (data['Close'] < data['Senkou_Span_A']) & 
            (data['Close'] < data['Senkou_Span_B'])
        )
        
        # Strong signals (with confirmations)
        data['Strong_Long'] = (
            data['Basic_Long'] & 
            (data['Cloud_Color'] == 'BULLISH') &
            (data['TK_Cross'] == 'BULLISH') &
            (data['Chikou_Confirmation'] == 'BULLISH')
        )
        
        data['Strong_Short'] = (
            data['Basic_Short'] & 
            (data['Cloud_Color'] == 'BEARISH') &
            (data['TK_Cross'] == 'BEARISH') &
            (data['Chikou_Confirmation'] == 'BEARISH')
        )
        
        # Entry signals (new positions)
        data['Long_Entry'] = (
            data['Basic_Long'] & 
            ~data['Basic_Long'].shift(1).fillna(False)
        )
        
        data['Short_Entry'] = (
            data['Basic_Short'] & 
            ~data['Basic_Short'].shift(1).fillna(False)
        )
        
        # Exit signals
        data['Long_Exit'] = (
            data['Basic_Long'].shift(1).fillna(False) & 
            ~data['Basic_Long']
        )
        
        data['Short_Exit'] = (
            data['Basic_Short'].shift(1).fillna(False) & 
            ~data['Basic_Short']
        )
        
        return data
    
    def calculate_position_management(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate position management and alerts"""
        
        data['Position_State'] = 'NEUTRAL'
        data['Alert_Type'] = 'NONE'
        
        position_state = 'NEUTRAL'
        
        for i in range(len(data)):
            current_state = position_state
            
            # Check for entry signals
            if data['Long_Entry'].iloc[i]:
                position_state = 'LONG'
                data['Alert_Type'].iloc[i] = 'LONG_ENTRY'
            elif data['Short_Entry'].iloc[i]:
                position_state = 'SHORT'
                data['Alert_Type'].iloc[i] = 'SHORT_ENTRY'
            
            # Check for exit signals
            elif data['Long_Exit'].iloc[i] and current_state == 'LONG':
                position_state = 'NEUTRAL'
                data['Alert_Type'].iloc[i] = 'LONG_EXIT'
            elif data['Short_Exit'].iloc[i] and current_state == 'SHORT':
                position_state = 'NEUTRAL'
                data['Alert_Type'].iloc[i] = 'SHORT_EXIT'
            
            # Maintain current position
            elif current_state in ['LONG', 'SHORT']:
                data['Alert_Type'].iloc[i] = f'{current_state}_ACTIVE'
            
            data['Position_State'].iloc[i] = position_state
        
        return data
    
    def calculate_support_resistance(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate dynamic support and resistance levels"""
        
        # Primary support/resistance from cloud
        data['Primary_Support'] = np.where(
            data['Price_vs_Cloud'] == 'ABOVE',
            data['Cloud_Top'],
            data['Kijun_Sen']
        )
        
        data['Primary_Resistance'] = np.where(
            data['Price_vs_Cloud'] == 'BELOW',
            data['Cloud_Bottom'],
            data['Kijun_Sen']
        )
        
        # Secondary levels
        data['Secondary_Support'] = np.where(
            data['Price_vs_Cloud'] == 'ABOVE',
            data['Kijun_Sen'],
            data['Cloud_Bottom']
        )
        
        data['Secondary_Resistance'] = np.where(
            data['Price_vs_Cloud'] == 'BELOW',
            data['Kijun_Sen'],
            data['Cloud_Top']
        )
        
        return data
    
    def analyze_stock(self, data: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Complete Ichimoku analysis for a stock"""
        
        # Need sufficient data for all calculations
        min_required = max(self.senkou_b_period, self.displacement) + 10
        if len(data) < min_required:
            return None
        
        # Apply all calculations
        data = self.calculate_ichimoku_components(data)
        data = self.calculate_cloud_characteristics(data)
        data = self.calculate_trading_signals(data)
        data = self.calculate_position_management(data)
        data = self.calculate_support_resistance(data)
        
        # Get latest values (skip NaN rows)
        valid_data = data.dropna()
        if len(valid_data) == 0:
            return None
        
        latest = valid_data.iloc[-1]
        
        # Determine signal strength
        signal_strength = 'WEAK'
        if latest['Strong_Long'] or latest['Strong_Short']:
            signal_strength = 'STRONG'
        elif latest['Basic_Long'] or latest['Basic_Short']:
            signal_strength = 'MEDIUM'
        
        # Calculate targets and stops
        current_price = latest['Close']
        
        if latest['Alert_Type'] in ['LONG_ENTRY', 'LONG_ACTIVE']:
            target_price = current_price + self.target_points
            stop_loss = current_price - self.stop_loss_points
        elif latest['Alert_Type'] in ['SHORT_ENTRY', 'SHORT_ACTIVE']:
            target_price = current_price - self.target_points
            stop_loss = current_price + self.stop_loss_points
        else:
            target_price = current_price
            stop_loss = current_price
        
        # Calculate position in cloud
        if latest['Price_vs_Cloud'] == 'INSIDE':
            cloud_position = ((current_price - latest['Cloud_Bottom']) / 
                            (latest['Cloud_Top'] - latest['Cloud_Bottom'])) if latest['Cloud_Thickness'] > 0 else 0.5
        elif latest['Price_vs_Cloud'] == 'ABOVE':
            cloud_position = 1.0 + ((current_price - latest['Cloud_Top']) / current_price)
        else:  # BELOW
            cloud_position = -((latest['Cloud_Bottom'] - current_price) / current_price)
        
        return {
            'signal': latest['Alert_Type'],
            'signal_strength': signal_strength,
            'price': float(current_price),
            'tenkan_sen': float(latest['Tenkan_Sen']),
            'kijun_sen': float(latest['Kijun_Sen']),
            'senkou_span_a': float(latest['Senkou_Span_A']),
            'senkou_span_b': float(latest['Senkou_Span_B']),
            'chikou_span': float(latest['Chikou_Span']),
            'cloud_top': float(latest['Cloud_Top']),
            'cloud_bottom': float(latest['Cloud_Bottom']),
            'cloud_color': latest['Cloud_Color'],
            'cloud_thickness': float(latest['Cloud_Thickness']),
            'cloud_thickness_pct': float(latest['Cloud_Thickness_Pct']),
            'price_vs_cloud': latest['Price_vs_Cloud'],
            'cloud_position': float(cloud_position),
            'tk_cross': latest['TK_Cross'],
            'chikou_confirmation': latest['Chikou_Confirmation'],
            'primary_support': float(latest['Primary_Support']),
            'primary_resistance': float(latest['Primary_Resistance']),
            'target_price': float(target_price),
            'stop_loss': float(stop_loss),
            'position_state': latest['Position_State'],
            'volume': float(latest['Volume']),
            'data_length': len(valid_data)
        }

def get_stock_data(ticker: str, days_back: int = 150) -> Optional[pd.DataFrame]:
    """Get stock data with error handling"""
    try:
        symbol = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        stock = yf.Ticker(symbol)
        data = stock.history(start=start_date, end=end_date)
        
        if data.empty or len(data) < 60:
            print(f"   ⚠️  {ticker}: Insufficient data ({len(data)} days)")
            return None
        
        # Clean data
        data = data.dropna()
        data.reset_index(inplace=True)
        
        return data
        
    except Exception as e:
        print(f"   ❌ {ticker}: Data fetch error - {str(e)}")
        return None

def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
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
        
        final_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
        return max(0, min(100, final_rsi))
    except:
        return 50

def analyze_stock_ichimoku(ticker: str, tenkan_period: int = 9, kijun_period: int = 26,
                          senkou_b_period: int = 52, displacement: int = 26,
                          target_points: int = 100, stop_loss_points: int = 50) -> Optional[Dict]:
    """Complete Ichimoku analysis for a single stock"""
    try:
        print(f"☁️  Analyzing {ticker} (Ichimoku: {tenkan_period}/{kijun_period}/{senkou_b_period})...")
        
        # Get data
        data = get_stock_data(ticker, days_back=200)
        if data is None:
            return None
        
        print(f"   📅 Data: {len(data)} days available")
        
        # Initialize Ichimoku strategy
        ichimoku = IchimokuCloudStrategy(
            tenkan_period, kijun_period, senkou_b_period, 
            displacement, target_points, stop_loss_points
        )
        
        # Analyze
        result = ichimoku.analyze_stock(data)
        if result is None:
            print(f"   ⚠️  {ticker}: Analysis failed")
            return None
        
        # Add additional metrics
        result['ticker'] = ticker
        result['tenkan_period'] = tenkan_period
        result['kijun_period'] = kijun_period
        result['senkou_b_period'] = senkou_b_period
        result['displacement'] = displacement
        result['rsi'] = calculate_rsi(data['Close'])
        
        # Calculate volume ratio
        if len(data) >= 20:
            avg_volume = data['Volume'].rolling(window=20).mean().iloc[-1]
            result['volume_ratio'] = result['volume'] / avg_volume if avg_volume > 0 else 1.0
        else:
            result['volume_ratio'] = 1.0
        
        # Calculate momentum
        if len(data) >= 6:
            momentum = ((result['price'] - data['Close'].iloc[-6]) / data['Close'].iloc[-6]) * 100
            result['momentum'] = momentum
        else:
            result['momentum'] = 0
        
        # Position sizing (1% risk)
        risk_per_share = abs(result['price'] - result['stop_loss'])
        if risk_per_share > 0:
            capital = 100000
            risk_amount = capital * 0.01
            result['position_size'] = int(risk_amount / risk_per_share)
        else:
            result['position_size'] = 0
        
        print(f"   ☁️  Signal: {result['signal']} ({result['signal_strength']})")
        print(f"   📊 Cloud: {result['cloud_color']} | Position: {result['price_vs_cloud']}")
        print(f"   📈 RSI: {result['rsi']:.1f} | TK Cross: {result['tk_cross']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error analyzing {ticker}: {e}")
        return None

def analyze_all_stocks_ichimoku(tenkan_period: int = 9, kijun_period: int = 26,
                               senkou_b_period: int = 52, displacement: int = 26,
                               target_points: int = 100, stop_loss_points: int = 50,
                               max_workers: int = 3) -> List[Dict]:
    """Analyze all stocks using Ichimoku strategy"""
    
    tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
    
    print(f"\n☁️  ICHIMOKU CLOUD ANALYSIS")
    print(f"📊 Analyzing {len(tickers)} stocks")
    print(f"📈 Tenkan-sen: {tenkan_period} | Kijun-sen: {kijun_period}")
    print(f"📊 Senkou Span B: {senkou_b_period} | Displacement: {displacement}")
    print(f"🎯 Target: {target_points} pts | Stop: {stop_loss_points} pts")
    print("="*60)
    
    all_results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(analyze_stock_ichimoku, ticker, tenkan_period, kijun_period,
                          senkou_b_period, displacement, target_points, stop_loss_points): ticker 
            for ticker in tickers
        }
        
        completed = 0
        successful = 0
        
        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            completed += 1
            
            try:
                result = future.result(timeout=30)
                if result:
                    all_results.append(result)
                    successful += 1
                    print(f"✅ {ticker} ({completed}/{len(tickers)}) - {result['signal']}")
                else:
                    print(f"⚪ {ticker} ({completed}/{len(tickers)}) - No data")
            except Exception as e:
                print(f"❌ {ticker} ({completed}/{len(tickers)}) - Error: {str(e)[:50]}")
    
    print(f"\n📊 ANALYSIS SUMMARY:")
    print(f"   ✅ Successful: {successful}")
    print(f"   ☁️  Total signals: {len(all_results)}")
    
    return all_results

def display_ichimoku_signals(results: List[Dict], signal_types: List[str], title: str, top_n: int = 10):
    """Display Ichimoku signals filtered by type"""
    
    filtered = [r for r in results if r['signal'] in signal_types]
    
    if not filtered:
        print(f"\n❌ No {title} signals found!")
        return
    
    # Sort by signal strength and cloud position
    def sort_key(x):
        strength_score = {'STRONG': 3, 'MEDIUM': 2, 'WEAK': 1}.get(x['signal_strength'], 0)
        cloud_score = 1 if x['cloud_color'] == 'BULLISH' else 0
        return (strength_score, cloud_score, abs(x['cloud_position']))
    
    if any('LONG' in sig for sig in signal_types):
        filtered.sort(key=sort_key, reverse=True)
    else:
        filtered.sort(key=sort_key, reverse=True)
    
    top_signals = filtered[:top_n]
    
    print(f"\n☁️  TOP {len(top_signals)} {title} SIGNALS")
    print("="*90)
    
    # Prepare table
    headers = ['Rank', 'Ticker', 'Signal', 'Strength', 'Price', 'Cloud', 'Position', 
              'TK Cross', 'Volume', 'RSI', 'Target', 'Stop', 'Qty']
    
    table_data = []
    for i, result in enumerate(top_signals, 1):
        # Cloud display
        cloud_display = "🟢" if result['cloud_color'] == 'BULLISH' else "🔴"
        
        # Position display
        pos_display = result['price_vs_cloud'][:1]  # A/B/I for Above/Below/Inside
        if result['price_vs_cloud'] == 'ABOVE':
            pos_display += "🟢"
        elif result['price_vs_cloud'] == 'BELOW':
            pos_display += "🔴"
        else:
            pos_display += "🟡"
        
        # TK Cross display
        tk_display = "🟢" if result['tk_cross'] == 'BULLISH' else "🔴"
        
        # Volume display
        volume_display = f"{result['volume_ratio']:.1f}x"
        if result['volume_ratio'] > 2.0:
            volume_display += "🟢"
        elif result['volume_ratio'] > 1.5:
            volume_display += "🟡"
        elif result['volume_ratio'] < 0.5:
            volume_display += "🔴"
        
        # RSI display
        rsi_display = f"{result['rsi']:.0f}"
        if result['rsi'] > 70:
            rsi_display += "🔴"
        elif result['rsi'] < 30:
            rsi_display += "🟢"
        
        table_data.append([
            i,
            result['ticker'],
            result['signal'].replace('_', ' '),
            result['signal_strength'],
            f"₹{result['price']:.2f}",
            cloud_display,
            pos_display,
            tk_display,
            volume_display,
            rsi_display,
            f"₹{result['target_price']:.2f}",
            f"₹{result['stop_loss']:.2f}",
            result['position_size']
        ])
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Summary
    if filtered:
        strong_signals = len([r for r in filtered if r['signal_strength'] == 'STRONG'])
        bullish_cloud = len([r for r in filtered if r['cloud_color'] == 'BULLISH'])
        above_cloud = len([r for r in filtered if r['price_vs_cloud'] == 'ABOVE'])
        
        print(f"\n📊 SUMMARY ({len(filtered)} signals):")
        print(f"   💪 Strong Signals: {strong_signals}")
        print(f"   🟢 Bullish Cloud: {bullish_cloud}")
        print(f"   ⬆️  Above Cloud: {above_cloud}")

def generate_ichimoku_html_report(results: List[Dict], tenkan_period: int, kijun_period: int,
                                 senkou_b_period: int, displacement: int, output_dir: str):
    """Generate HTML report for Ichimoku analysis"""
    
    if not results:
        print("❌ No results to generate report")
        return None
    
    # Categorize signals
    entry_signals = [r for r in results if 'ENTRY' in r['signal']]
    exit_signals = [r for r in results if 'EXIT' in r['signal']]
    active_positions = [r for r in results if 'ACTIVE' in r['signal']]
    neutral_signals = [r for r in results if r['signal'] == 'NONE']
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Ichimoku Cloud Analysis - {datetime.now().strftime('%Y-%m-%d')}</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; 
                   background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }}
            .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 30px; 
                        border-radius: 15px; box-shadow: 0 15px 35px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                      color: white; padding: 40px; border-radius: 15px; margin-bottom: 30px; }}
            .header h1 {{ margin: 0; font-size: 2.8em; margin-bottom: 10px; }}
            .cloud-icon {{ font-size: 2em; margin: 0 10px; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                          gap: 20px; margin: 30px 0; }}
            .stat-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; 
                         padding: 20px; border-radius: 10px; text-align: center; }}
            .stat-card h3 {{ margin: 0 0 10px 0; font-size: 2em; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; 
                    box-shadow: 0 5px 15px rgba(0,0,0,0.1); border-radius: 10px; overflow: hidden; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #f8f9fa; font-weight: bold; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            tr:hover {{ background-color: #f0f0f0; }}
            .long-entry {{ background: linear-gradient(90deg, #28a745, #20c997); color: white; 
                          padding: 5px 10px; border-radius: 15px; font-weight: bold; }}
            .short-entry {{ background: linear-gradient(90deg, #dc3545, #e74c3c); color: white; 
                           padding: 5px 10px; border-radius: 15px; font-weight: bold; }}
            .long-active {{ background: linear-gradient(90deg, #17a2b8, #138496); color: white; 
                           padding: 5px 10px; border-radius: 15px; font-weight: bold; }}
            .short-active {{ background: linear-gradient(90deg, #6f42c1, #563d7c); color: white; 
                            padding: 5px 10px; border-radius: 15px; font-weight: bold; }}
            .section {{ margin: 40px 0; }}
            .section h2 {{ color: #333; border-bottom: 3px solid #667eea; padding-bottom: 10px; }}
            .cloud-bullish {{ color: #28a745; font-weight: bold; }}
            .cloud-bearish {{ color: #dc3545; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>☁️ ICHIMOKU CLOUD ANALYSIS <span class="cloud-icon">☁️</span></h1>
                <p><strong>Ichimoku Kinko Hyo Strategy</strong></p>
                <p>Tenkan: {tenkan_period} | Kijun: {kijun_period} | Senkou B: {senkou_b_period} | Displacement: {displacement}</p>
                <p>Generated: {timestamp}</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card"><h3>{len(entry_signals)}</h3><p>Entry Signals</p></div>
                <div class="stat-card"><h3>{len(exit_signals)}</h3><p>Exit Signals</p></div>
                <div class="stat-card"><h3>{len(active_positions)}</h3><p>Active Positions</p></div>
                <div class="stat-card"><h3>{len(results)}</h3><p>Total Analyzed</p></div>
            </div>
    """
    
    # Add tables for each signal type
    signal_groups = [
        (entry_signals, "☁️ ENTRY SIGNALS", "entry"),
        (exit_signals, "🔴 EXIT SIGNALS", "exit"), 
        (active_positions, "📊 ACTIVE POSITIONS", "active")
    ]
    
    for signals, title, signal_type in signal_groups:
        if signals:
            html_content += f"""
                <div class="section">
                    <h2>{title}</h2>
                    <table>
                        <thead>
                            <tr><th>Ticker</th><th>Signal</th><th>Strength</th><th>Price</th><th>Cloud</th>
                                <th>Position</th><th>TK Cross</th><th>RSI</th><th>Target</th><th>Stop</th></tr>
                        </thead>
                        <tbody>
            """
            
            for signal in signals[:15]:  # Top 15
                signal_class = signal['signal'].lower().replace('_', '-')
                cloud_class = 'cloud-bullish' if signal['cloud_color'] == 'BULLISH' else 'cloud-bearish'
                
                html_content += f"""
                    <tr>
                        <td><strong>{signal['ticker']}</strong></td>
                        <td><span class="{signal_class}">{signal['signal'].replace('_', ' ')}</span></td>
                        <td>{signal['signal_strength']}</td>
                        <td>₹{signal['price']:.2f}</td>
                        <td class="{cloud_class}">{signal['cloud_color']}</td>
                        <td>{signal['price_vs_cloud']}</td>
                        <td>{signal['tk_cross']}</td>
                        <td>{signal['rsi']:.0f}</td>
                        <td>₹{signal['target_price']:.2f}</td>
                        <td>₹{signal['stop_loss']:.2f}</td>
                    </tr>
                """
            
            html_content += "</tbody></table></div>"
    
    html_content += """
            <div style="text-align: center; margin-top: 40px; padding: 20px; 
                       background: #f8f9fa; border-radius: 10px;">
                <p><strong>⚠️ Disclaimer:</strong> Ichimoku Cloud analysis for educational purposes.</p>
                <p><strong>☁️ Strategy:</strong> Price above/below cloud with multiple confirmations for entry/exit signals.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Save file
    filename = f"ichimoku_analysis_{tenkan_period}_{kijun_period}_{senkou_b_period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return filepath

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Ichimoku Cloud Strategy - Complete Python Implementation")
    
    parser.add_argument('--tenkan-period', type=int, default=9, 
                       help='Tenkan-sen (Conversion Line) period (default: 9)')
    parser.add_argument('--kijun-period', type=int, default=26, 
                       help='Kijun-sen (Base Line) period (default: 26)')
    parser.add_argument('--senkou-b-period', type=int, default=52, 
                       help='Senkou Span B period (default: 52)')
    parser.add_argument('--displacement', type=int, default=26, 
                       help='Displacement for Senkou spans (default: 26)')
    parser.add_argument('--target-points', type=int, default=100, 
                       help='Target points (default: 100)')
    parser.add_argument('--stop-loss-points', type=int, default=50, 
                       help='Stop loss points (default: 50)')
    parser.add_argument('--top', type=int, default=10, 
                       help='Top N signals to display (default: 10)')
    parser.add_argument('--output', type=str, 
                       help='Output directory')
    parser.add_argument('--workers', type=int, default=3, 
                       help='Max concurrent workers (default: 3)')
    parser.add_argument('--test-single', type=str, 
                       help='Test single ticker')
    parser.add_argument('--show-entries', action='store_true', 
                       help='Show entry signals only')
    parser.add_argument('--show-exits', action='store_true', 
                       help='Show exit signals only')
    parser.add_argument('--show-active', action='store_true', 
                       help='Show active positions only')
    parser.add_argument('--show-all', action='store_true', 
                       help='Show all signal types')
    
    args = parser.parse_args()
    
    # Test single ticker
    if args.test_single:
        print(f"🧪 TESTING: {args.test_single}")
        result = analyze_stock_ichimoku(
            args.test_single, args.tenkan_period, args.kijun_period,
            args.senkou_b_period, args.displacement, args.target_points, args.stop_loss_points
        )
        if result:
            print(f"\n✅ Result: {result}")
        return
    
    print("☁️  ICHIMOKU CLOUD STRATEGY")
    print("="*50)
    print(f"📈 Tenkan-sen: {args.tenkan_period} periods")
    print(f"📊 Kijun-sen: {args.kijun_period} periods")
    print(f"📉 Senkou Span B: {args.senkou_b_period} periods")
    print(f"↔️  Displacement: {args.displacement} periods")
    print(f"🎯 Target/Stop: {args.target_points}/{args.stop_loss_points} points")
    print("="*50)
    
    # Set output directory
    output_dir = args.output or getattr(config, 'OUTPUT_DIR', 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Analyze all stocks
    results = analyze_all_stocks_ichimoku(
        args.tenkan_period, args.kijun_period, args.senkou_b_period,
        args.displacement, args.target_points, args.stop_loss_points, args.workers
    )
    
    if not results:
        print("\n❌ No results generated!")
        return
    
    # Display results based on arguments
    if args.show_entries:
        display_ichimoku_signals(results, ['LONG_ENTRY', 'SHORT_ENTRY'], "ENTRY", args.top)
    elif args.show_exits:
        display_ichimoku_signals(results, ['LONG_EXIT', 'SHORT_EXIT'], "EXIT", args.top)
    elif args.show_active:
        display_ichimoku_signals(results, ['LONG_ACTIVE', 'SHORT_ACTIVE'], "ACTIVE POSITIONS", args.top)
    elif args.show_all:
        display_ichimoku_signals(results, ['LONG_ENTRY', 'SHORT_ENTRY'], "ENTRY", args.top)
        display_ichimoku_signals(results, ['LONG_EXIT', 'SHORT_EXIT'], "EXIT", args.top)
        display_ichimoku_signals(results, ['LONG_ACTIVE', 'SHORT_ACTIVE'], "ACTIVE", args.top)
    else:
        # Default: show entry signals
        display_ichimoku_signals(results, ['LONG_ENTRY', 'SHORT_ENTRY'], "ENTRY", args.top)
    
    # Generate HTML report
    html_path = generate_ichimoku_html_report(
        results, args.tenkan_period, args.kijun_period, args.senkou_b_period, 
        args.displacement, output_dir
    )
    if html_path:
        print(f"\n🌐 HTML Report: {html_path}")
        print(f"🔗 Open: file://{os.path.abspath(html_path)}")
    
    # Save JSON
    json_data = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'tenkan_period': args.tenkan_period,
            'kijun_period': args.kijun_period,
            'senkou_b_period': args.senkou_b_period,
            'displacement': args.displacement,
            'target_points': args.target_points,
            'stop_loss_points': args.stop_loss_points,
            'total_analyzed': len(results)
        },
        'results': results
    }
    
    json_path = os.path.join(output_dir, f"ichimoku_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    print(f"📊 JSON Data: {json_path}")
    print(f"\n✅ Analysis Complete!")
    
    # Summary
    entry_count = len([r for r in results if 'ENTRY' in r['signal']])
    exit_count = len([r for r in results if 'EXIT' in r['signal']])
    active_count = len([r for r in results if 'ACTIVE' in r['signal']])
    
    print(f"\n☁️  ICHIMOKU SUMMARY:")
    print(f"   🟢 Entry Signals: {entry_count}")
    print(f"   🔴 Exit Signals: {exit_count}")
    print(f"   📊 Active Positions: {active_count}")
    print(f"   📈 Total Analyzed: {len(results)}")
    
    print(f"\n💡 ICHIMOKU TRADING NOTES:")
    print(f"   🟢 LONG: Price above both Senkou Spans (above cloud)")
    print(f"   🔴 SHORT: Price below both Senkou Spans (below cloud)")
    print(f"   ⚠️  INSIDE CLOUD: Neutral/consolidation zone")
    print(f"   💪 STRONG: All confirmations align (Tenkan/Kijun/Chikou)")
    print(f"   ☁️  CLOUD COLOR: Green=Bullish, Red=Bearish trend")

if __name__ == "__main__":
    main()