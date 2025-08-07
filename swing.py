#!/usr/bin/env python
# swing_calls_analyzer.py - SWING CALLS Strategy (Pine Script Faithful)
# MODIFIED: Added surajkumarsadhaphule's EMA(2)/SMA(200) suggestion

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

class SwingCallsStrategy:
    """SWING CALLS Strategy - Faithful Pine Script Implementation"""
    
    def __init__(self, ema_value: int = 5, sma_value: int = 50, 
                 rsi_overbought: int = 80, rsi_oversold: int = 20):
        
        # Pine Script parameters
        self.ema_value = ema_value          # Fast EMA (default: 5)
        self.sma_value = sma_value          # Slow SMA (default: 50)
        self.rsi_overbought = rsi_overbought # RSI overbought limit (default: 80)
        self.rsi_oversold = rsi_oversold     # RSI oversold limit (default: 20)
        self.rsi_period = 14                 # RSI period (fixed in Pine Script)
    
    def calculate_indicators(self, data: pd.DataFrame) -> dict:
        """Calculate all SWING CALLS indicators exactly like Pine Script"""
        try:
            # Pine Script: ema1=ema(close,ema_value)
            ema1 = data['Close'].ewm(span=self.ema_value).mean()
            
            # Pine Script: sma2=sma(close,sma_value)  
            sma2 = data['Close'].rolling(window=self.sma_value).mean()
            
            # Pine Script: rs=rsi(close,14)
            rs = self.calculate_rsi(data['Close'], self.rsi_period)
            
            # Pine Script color logic:
            # mycolor= iff(rs>=85 or rs<=15,color.yellow,iff(low> sma2,color.lime,iff(high<sma2,color.red,color.yellow)))
            sma_color = []
            for i in range(len(data)):
                if i < len(rs) and not pd.isna(rs.iloc[i]) and not pd.isna(sma2.iloc[i]):
                    rsi_val = rs.iloc[i]
                    if rsi_val >= 85 or rsi_val <= 15:
                        sma_color.append('yellow')  # Extreme RSI
                    elif data['Low'].iloc[i] > sma2.iloc[i]:
                        sma_color.append('green')   # Bullish (low > SMA)
                    elif data['High'].iloc[i] < sma2.iloc[i]:
                        sma_color.append('red')     # Bearish (high < SMA)  
                    else:
                        sma_color.append('yellow')  # Neutral
                else:
                    sma_color.append('yellow')
            
            return {
                'ema1': ema1,
                'sma2': sma2, 
                'rsi': rs,
                'sma_color': sma_color
            }
            
        except Exception as e:
            return {}
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI exactly like Pine Script"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss.replace(0, 0.001)
            rsi = 100 - (100 / (1 + rs))
            return rsi.fillna(50)
        except:
            return pd.Series([50] * len(prices), index=prices.index)
    
    def detect_signals(self, data: pd.DataFrame) -> dict:
        """Detect SWING CALLS signals exactly like Pine Script"""
        
        if len(data) < max(self.sma_value, self.rsi_period) + 5:
            return {'signal': 'NO_DATA', 'details': {}}
        
        # Calculate indicators
        indicators = self.calculate_indicators(data)
        if not indicators:
            return {'signal': 'NO_DATA', 'details': {}}
        
        try:
            # Get latest values
            ema1 = indicators['ema1']
            sma2 = indicators['sma2']
            rsi = indicators['rsi']
            sma_color = indicators['sma_color']
            
            # Current bar values
            current_close = data['Close'].iloc[-1]
            current_open = data['Open'].iloc[-1]
            current_high = data['High'].iloc[-1]
            current_low = data['Low'].iloc[-1]
            current_ema = ema1.iloc[-1]
            current_sma = sma2.iloc[-1]
            current_rsi = rsi.iloc[-1]
            current_color = sma_color[-1]
            
            # Previous bar values for crossover detection
            prev_ema = ema1.iloc[-2] if len(ema1) > 1 else current_ema
            prev_sma = sma2.iloc[-2] if len(sma2) > 1 else current_sma
            prev_rsi = rsi.iloc[-2] if len(rsi) > 1 else current_rsi
            
            # Check for NaN values
            values_to_check = [current_ema, current_sma, current_rsi, prev_ema, prev_sma, prev_rsi]
            if any(pd.isna(v) for v in values_to_check):
                return {'signal': 'HOLD', 'details': self._get_details(data, indicators)}
            
            signal = 'HOLD'
            signal_type = 'None'
            rsi_alert = 'None'
            
            # Pine Script RSI alerts:
            # buyexit= crossunder(rs,hl)  -> RSI crosses under overbought (exit buy position)
            # sellexit=crossover(rs,ll)   -> RSI crosses over oversold (exit sell position)
            if current_rsi < self.rsi_overbought and prev_rsi >= self.rsi_overbought:
                rsi_alert = 'RSI_BEARISH'  # Exit buy positions
            elif current_rsi > self.rsi_oversold and prev_rsi <= self.rsi_oversold:
                rsi_alert = 'RSI_BULLISH'  # Exit sell positions
            
            # Pine Script main signals:
            # buycall=crossunder(sma2,ema1) and high>sma2
            # This means: SMA crosses under EMA (EMA > SMA = bullish) AND high > SMA
            crossunder_sma_ema = (current_sma < current_ema and prev_sma >= prev_ema)
            high_above_sma = current_high > current_sma
            
            if crossunder_sma_ema and high_above_sma:
                signal = 'BUY'
                signal_type = 'SWING_BUY'
            
            # sellcall=crossover(sma2,ema1) and open>close  
            # This means: SMA crosses over EMA (SMA > EMA = bearish) AND red candle
            crossover_sma_ema = (current_sma > current_ema and prev_sma <= prev_ema)
            red_candle = current_open > current_close
            
            if crossover_sma_ema and red_candle:
                signal = 'SELL'
                signal_type = 'SWING_SELL'
            
            return {
                'signal': signal,
                'signal_type': signal_type,
                'rsi_alert': rsi_alert,
                'details': self._get_details(data, indicators),
                'conditions': {
                    'crossunder_sma_ema': crossunder_sma_ema,
                    'high_above_sma': high_above_sma,
                    'crossover_sma_ema': crossover_sma_ema,
                    'red_candle': red_candle
                }
            }
            
        except Exception as e:
            return {'signal': 'HOLD', 'details': self._get_details(data, indicators)}
    
    def _get_details(self, data: pd.DataFrame, indicators: dict) -> dict:
        """Get current market details for context"""
        try:
            # Current values
            current_close = float(data['Close'].iloc[-1])
            current_open = float(data['Open'].iloc[-1])
            current_high = float(data['High'].iloc[-1])
            current_low = float(data['Low'].iloc[-1])
            current_volume = float(data['Volume'].iloc[-1])
            
            # Indicator values
            current_ema = float(indicators['ema1'].iloc[-1]) if 'ema1' in indicators else 0
            current_sma = float(indicators['sma2'].iloc[-1]) if 'sma2' in indicators else 0
            current_rsi = float(indicators['rsi'].iloc[-1]) if 'rsi' in indicators else 50
            current_color = indicators['sma_color'][-1] if 'sma_color' in indicators else 'yellow'
            
            # Additional metrics
            volume_ratio = 1.0
            momentum = 0.0
            
            if len(data) >= 21:
                avg_volume = data['Volume'].iloc[-21:-1].mean()
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            if len(data) >= 6:
                past_price = float(data['Close'].iloc[-6])
                momentum = ((current_close - past_price) / past_price) * 100
            
            # Candle type
            candle_type = 'Green' if current_close > current_open else 'Red'
            
            # Market position relative to SMA
            market_position = 'Above_SMA' if current_close > current_sma else 'Below_SMA'
            
            return {
                'current_price': current_close,
                'current_open': current_open,
                'current_high': current_high,
                'current_low': current_low,
                'ema_5': current_ema,
                'sma_50': current_sma,
                'rsi': current_rsi,
                'sma_color': current_color,
                'candle_type': candle_type,
                'market_position': market_position,
                'volume_ratio': volume_ratio,
                'momentum': momentum
            }
            
        except Exception as e:
            return {
                'current_price': 0,
                'current_open': 0,
                'current_high': 0,
                'current_low': 0,
                'ema_5': 0,
                'sma_50': 0,
                'rsi': 50,
                'sma_color': 'yellow',
                'candle_type': 'Unknown',
                'market_position': 'Unknown',
                'volume_ratio': 1.0,
                'momentum': 0
            }

def get_stock_data(ticker, lookback_days=100, interval='1d'):
    """Get stock data for analysis with configurable timeframe
    
    Args:
        ticker: Stock symbol
        lookback_days: Number of periods to fetch
        interval: Timeframe - '5m', '15m', '1h', '4h', '1d', '1wk', '1mo'
    """
    try:
        if ticker.endswith('.NS'):
            symbol = ticker
        else:
            symbol = f"{ticker}.NS"
        
        # Calculate date range based on interval
        if interval == '5m':
            # 5-minute data: Limited to ~60 days, fetch more periods but fewer days
            days_needed = min(60, lookback_days // 10 + 10)  # Fewer days, more periods per day
            lookback_days = min(lookback_days, days_needed * 80)  # ~80 periods per trading day
        elif interval == '15m':
            # 15-minute data: Limited to ~60 days
            days_needed = min(60, lookback_days // 5 + 15)  # ~26 periods per trading day
            lookback_days = min(lookback_days, days_needed * 26)
        elif interval == '1h':
            # For hourly data, we need more calendar days
            days_needed = lookback_days * 3 + 30  # Account for weekends/holidays
        elif interval == '4h':
            days_needed = lookback_days * 2 + 20
        elif interval == '1d':
            days_needed = lookback_days + 100
        elif interval == '1wk':
            days_needed = lookback_days * 7 + 50
        elif interval == '1mo':
            days_needed = lookback_days * 30 + 100
        else:
            days_needed = lookback_days + 100
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_needed)
        
        for attempt in range(3):
            try:
                stock = yf.Ticker(symbol)
                data = stock.history(start=start_date, end=end_date, interval=interval, 
                                   auto_adjust=True, prepost=True)
                if not data.empty:
                    break
            except Exception as e:
                if attempt == 2:
                    raise e
                continue
        
        if data.empty or len(data) < lookback_days:
            return None
        
        data = data.dropna()
        required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in data.columns for col in required_columns):
            return None
        
        if len(data) < lookback_days or (data['High'] < data['Low']).any() or (data['Close'] <= 0).any():
            return None
        
        return data.sort_index()
        
    except Exception:
        return None

def analyze_stock_swing_calls(ticker, ema_value=5, sma_value=50, rsi_overbought=80, rsi_oversold=20, interval='1d', debug=False):
    """Analyze single stock using SWING CALLS strategy
    
    Args:
        interval: Timeframe - '1d', '1h', '4h', '1wk', '1mo'
    """
    try:
        if debug:
            print(f"📊 Analyzing {ticker} - SWING CALLS Strategy ({interval} timeframe)...")
        
        data = get_stock_data(ticker, lookback_days=100, interval=interval)
        if data is None:
            if debug:
                print(f"   ❌ {ticker}: No data available")
            return None
        
        if debug:
            print(f"   📅 Data: {len(data)} {interval} periods available")
        
        min_required = max(sma_value, 20) + 10
        if len(data) < min_required:
            if debug:
                print(f"   ⚠️  {ticker}: Insufficient data {len(data)} < {min_required}")
            return None
        
        # Create SWING CALLS analyzer
        swing_strategy = SwingCallsStrategy(ema_value, sma_value, rsi_overbought, rsi_oversold)
        
        # Detect current signal
        analysis = swing_strategy.detect_signals(data)
        if analysis['signal'] == 'NO_DATA':
            if debug:
                print(f"   ⚠️  {ticker}: Unable to analyze SWING CALLS")
            return None
        
        details = analysis['details']
        signal = analysis['signal']
        signal_type = analysis.get('signal_type', 'None')
        rsi_alert = analysis.get('rsi_alert', 'None')
        
        if debug:
            print(f"   🎯 Signal: {signal}")
            if signal_type != 'None':
                print(f"   📊 Signal Type: {signal_type}")
            if rsi_alert != 'None':
                print(f"   📈 RSI Alert: {rsi_alert}")
            print(f"   💰 Price: ₹{details['current_price']:.2f}")
            print(f"   📈 EMA({ema_value}): ₹{details['ema_5']:.2f}")
            print(f"   📊 SMA({sma_value}): ₹{details['sma_50']:.2f}")
            print(f"   📈 RSI: {details['rsi']:.1f}")
            print(f"   🎨 SMA Color: {details['sma_color']}")
            print(f"   🕯️  Candle: {details['candle_type']}")
            print(f"   📍 Position: {details['market_position']}")
            print(f"   📊 Volume: {details['volume_ratio']:.1f}x")
            
            if 'conditions' in analysis:
                print(f"   🔍 Signal Conditions:")
                for condition, met in analysis['conditions'].items():
                    status = "✅" if met else "❌"
                    print(f"      {status} {condition}: {met}")
        
        # Build result
        result = {
            'ticker': ticker,
            'signal': signal,
            'signal_type': signal_type,
            'rsi_alert': rsi_alert,
            'current_price': details['current_price'],
            'ema_5': details['ema_5'],
            'sma_50': details['sma_50'],
            'rsi': details['rsi'],
            'sma_color': details['sma_color'],
            'candle_type': details['candle_type'],
            'market_position': details['market_position'],
            'volume_ratio': details['volume_ratio'],
            'momentum': details['momentum'],
            # Strategy parameters
            'ema_value': ema_value,
            'sma_value': sma_value,
            'rsi_overbought': rsi_overbought,
            'rsi_oversold': rsi_oversold,
            'interval': interval
        }
        
        return result
        
    except Exception as e:
        if debug:
            print(f"❌ Error analyzing {ticker}: {e}")
        return None

def analyze_all_stocks_swing_calls(ema_value=5, sma_value=50, rsi_overbought=80, rsi_oversold=20, interval='1d', max_workers=3, debug=False):
    """Analyze all stocks using SWING CALLS strategy"""
    
    tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
    
    timeframe_name = {
        '5m': '5-Minute',
        '15m': '15-Minute',
        '1h': 'Hourly',
        '4h': '4-Hour',
        '1d': 'Daily',
        '1wk': 'Weekly',
        '1mo': 'Monthly'
    }.get(interval, interval)
    
    print(f"\n🚀 SWING CALLS STRATEGY ANALYSIS")
    print(f"📊 Analyzing {len(tickers)} stocks")
    print(f"⏰ Timeframe: {timeframe_name} ({interval})")
    print(f"📈 Strategy: EMA({ema_value}) vs SMA({sma_value}) + RSI({rsi_overbought}/{rsi_oversold})")
    print(f"🎯 Pine Script: SMA/EMA Crossover + RSI Alerts")
    print("="*60)
    
    all_signals = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(analyze_stock_swing_calls, ticker, ema_value, sma_value, rsi_overbought, rsi_oversold, interval, debug): ticker 
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
                    signal_display = result['signal']
                    price_display = f"₹{result['current_price']:.2f}"
                    rsi_display = f"RSI:{result['rsi']:.0f}"
                    color_display = result['sma_color']
                    print(f"✅ {ticker} ({completed}/{len(tickers)}) - {signal_display} | {price_display} | {rsi_display} | {color_display}")
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
    return [signal for signal in all_signals if signal['signal'] in signal_types]

def display_swing_signals(signals, signal_title, top_n=10):
    """Display SWING CALLS signals"""
    
    if not signals:
        print(f"\n❌ No {signal_title} signals found!")
        return
    
    # Sort by RSI and volume for better signals
    signals.sort(key=lambda x: (abs(x['rsi'] - 50), x['volume_ratio']), reverse=True)
    top_signals = signals[:top_n]
    
    print(f"\n🏆 TOP {len(top_signals)} {signal_title} SIGNALS")
    print(f"📊 SWING CALLS Strategy (Pine Script Style)")
    print("="*100)
    
    table_data = []
    headers = ['Rank', 'Ticker', 'Signal', 'Timeframe', 'Price', 'EMA', 'SMA', 'RSI', 
               'SMA Color', 'Candle', 'Position', 'Volume']
    
    for i, signal in enumerate(top_signals, 1):
        volume_display = f"{signal['volume_ratio']:.1f}x"
        if signal['volume_ratio'] > 2.0:
            volume_display += "🟢"
        elif signal['volume_ratio'] > 1.5:
            volume_display += "🟡"
        elif signal['volume_ratio'] < 0.8:
            volume_display += "🔴"
        
        rsi_display = f"{signal['rsi']:.0f}"
        if signal['rsi'] >= 80:
            rsi_display += "🔴"  # Overbought
        elif signal['rsi'] <= 20:
            rsi_display += "🟢"  # Oversold
        elif signal['rsi'] >= 70:
            rsi_display += "🟡"  # Warning overbought
        elif signal['rsi'] <= 30:
            rsi_display += "🟡"  # Warning oversold
        
        # Color code SMA Color
        color_display = signal['sma_color']
        if color_display == 'green':
            color_display = "🟢Bullish"
        elif color_display == 'red':
            color_display = "🔴Bearish"
        else:
            color_display = "🟡Neutral"
        
        # Candle type
        candle_display = signal['candle_type']
        if candle_display == 'Green':
            candle_display = "🟢"
        else:
            candle_display = "🔴"
        
        # Timeframe display
        timeframe_display = signal.get('interval', '1d')
        
        table_data.append([
            i,
            signal['ticker'],
            signal['signal'],
            timeframe_display,
            f"₹{signal['current_price']:.2f}",
            f"₹{signal['ema_5']:.2f}",
            f"₹{signal['sma_50']:.2f}",
            rsi_display,
            color_display,
            candle_display,
            signal['market_position'].replace('_', ' '),
            volume_display
        ])
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Summary statistics
    avg_rsi = sum(signal['rsi'] for signal in top_signals) / len(top_signals)
    avg_volume = sum(signal['volume_ratio'] for signal in top_signals) / len(top_signals)
    avg_momentum = sum(abs(signal['momentum']) for signal in top_signals) / len(top_signals)
    
    # Count signal types
    swing_buy_count = sum(1 for signal in top_signals if signal['signal'] == 'BUY')
    swing_sell_count = sum(1 for signal in top_signals if signal['signal'] == 'SELL')
    rsi_alerts = sum(1 for signal in top_signals if signal['rsi_alert'] != 'None')
    
    # Count by timeframes
    timeframe_counts = {}
    for signal in top_signals:
        tf = signal.get('interval', '1d')
        timeframe_counts[tf] = timeframe_counts.get(tf, 0) + 1
    
    print(f"\n📊 SWING CALLS SUMMARY:")
    print(f"   🎯 {signal_title} signals: {len(signals)}")
    print(f"   📈 Average RSI: {avg_rsi:.1f}")
    print(f"   📊 Average volume: {avg_volume:.1f}x")
    print(f"   🚀 Average momentum: {avg_momentum:.1f}%")
    print(f"   📈 Swing signals: {swing_buy_count + swing_sell_count}")
    print(f"   🔔 RSI alerts: {rsi_alerts}")
    
    if timeframe_counts:
        print(f"   ⏰ Timeframe breakdown:")
        for tf, count in timeframe_counts.items():
            tf_name = {
                '5m': '5-Minute',
                '15m': '15-Minute', 
                '1h': 'Hourly',
                '4h': '4-Hour',
                '1d': 'Daily',
                '1wk': 'Weekly',
                '1mo': 'Monthly'
            }.get(tf, tf)
            print(f"      {tf_name} ({tf}): {count} signals")

def compare_configurations(interval='1d'):
    """Compare original EMA(5)/SMA(50) vs suggested EMA(2)/SMA(200) on single timeframe"""
    
    timeframe_name = {
        '5m': '5-Minute',
        '15m': '15-Minute',
        '1h': 'Hourly', 
        '4h': '4-Hour',
        '1d': 'Daily',
        '1wk': 'Weekly',
        '1mo': 'Monthly'
    }.get(interval, interval)
    
    print("🎯 COMPARING CONFIGURATIONS: Original vs Suggested")
    print("📊 Testing surajkumarsadhaphule's EMA(2)/SMA(200) suggestion")
    print(f"⏰ Timeframe: {timeframe_name} ({interval})")
    print("="*70)
    
    test_tickers = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ITC', 'KOTAKBANK']
    
    configs = [
        {'ema': 5, 'sma': 50, 'name': 'Original EMA(5)/SMA(50)'},
        {'ema': 2, 'sma': 200, 'name': 'Suggested EMA(2)/SMA(200)'}
    ]
    
    results = {}
    
    for config in configs:
        print(f"\n📈 Testing {config['name']} on {timeframe_name}...")
        print("-" * 40)
        
        config_signals = []
        
        for ticker in test_tickers:
            result = analyze_stock_swing_calls(
                ticker, config['ema'], config['sma'], 80, 20, interval, debug=False
            )
            if result:
                config_signals.append(result)
                if result['signal'] in ['BUY', 'SELL']:
                    print(f"   ✅ {ticker}: {result['signal']} @ ₹{result['current_price']:.2f}")
        
        buy_count = sum(1 for r in config_signals if r['signal'] == 'BUY')
        sell_count = sum(1 for r in config_signals if r['signal'] == 'SELL')
        total_signals = buy_count + sell_count
        
        results[config['name']] = {
            'signals': config_signals,
            'buy_count': buy_count,
            'sell_count': sell_count,
            'total_signals': total_signals
        }
        
        print(f"   📊 Results: {buy_count} BUY, {sell_count} SELL = {total_signals} total signals")
    
    # Comparison
    original = results['Original EMA(5)/SMA(50)']
    suggested = results['Suggested EMA(2)/SMA(200)']
    
    print(f"\n🏆 COMPARISON RESULTS ({timeframe_name} timeframe):")
    print("="*50)
    print(f"   Original  EMA(5)/SMA(50):  {original['total_signals']} signals")
    print(f"   Suggested EMA(2)/SMA(200): {suggested['total_signals']} signals")
    
    if suggested['total_signals'] > original['total_signals']:
        improvement = suggested['total_signals'] - original['total_signals']
        print(f"\n✅ SURAJKUMARSADHAPHULE WAS RIGHT!")
        print(f"   🎉 EMA(2)/SMA(200) gives +{improvement} more signals on {timeframe_name}!")
        print(f"   📊 Improvement: {improvement} additional signals found")
    elif suggested['total_signals'] < original['total_signals']:
        decrease = original['total_signals'] - suggested['total_signals']
        print(f"\n📉 Original performs better on {timeframe_name} timeframe")
        print(f"   📊 Original has {decrease} more signals than suggested")
    else:
        print(f"\n➡️  Both configurations give same number of signals on {timeframe_name}")
    
    print(f"\n🚀 Try the suggested config: python swing.py --suggested --timeframe {interval}")


def analyze_custom_timeframes(timeframes, ema_value=5, sma_value=50, rsi_overbought=80, rsi_oversold=20, max_workers=3, debug=False):
    """Analyze stocks across custom specified timeframes"""
    
    timeframe_names = {
        '5m': '5-Min',
        '15m': '15-Min',
        '1h': '1-Hour',
        '4h': '4-Hour',
        '1d': 'Daily',
        '1wk': 'Weekly',
        '1mo': 'Monthly'
    }
    
    # Use more stocks for analysis but still reasonable for API limits
    tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS[:30]]  # First 30 stocks
    
    print(f"\n🚀 CUSTOM MULTI-TIMEFRAME SWING CALLS ANALYSIS")
    print(f"📊 Analyzing {len(tickers)} stocks across {len(timeframes)} timeframes")
    print(f"📈 Strategy: EMA({ema_value}) vs SMA({sma_value}) + RSI({rsi_overbought}/{rsi_oversold})")
    print(f"⏰ Selected Timeframes: {', '.join([f'{timeframe_names[tf]} ({tf})' for tf in timeframes])}")
    print("="*80)
    
    all_signals = []
    
    for timeframe in timeframes:
        print(f"\n📊 Analyzing {timeframe_names[timeframe]} ({timeframe}) timeframe...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ticker = {
                executor.submit(analyze_stock_swing_calls, ticker, ema_value, sma_value, rsi_overbought, rsi_oversold, timeframe, False): ticker 
                for ticker in tickers
            }
            
            timeframe_signals = []
            completed = 0
            successful = 0
            
            for future in concurrent.futures.as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                completed += 1
                
                try:
                    result = future.result(timeout=30)
                    if result:
                        successful += 1
                        if result['signal'] in ['BUY', 'SELL']:
                            timeframe_signals.append(result)
                            all_signals.append(result)
                            signal_display = result['signal']
                            price_display = f"₹{result['current_price']:.2f}"
                            rsi_display = f"RSI:{result['rsi']:.0f}"
                            print(f"   ✅ {ticker} ({completed}/{len(tickers)}): {signal_display} @ {price_display} | {rsi_display}")
                        else:
                            print(f"   ⚪ {ticker} ({completed}/{len(tickers)}): HOLD")
                except Exception as e:
                    print(f"   ❌ {ticker} ({completed}/{len(tickers)}): Error")
                    continue
            
            buy_signals = sum(1 for s in timeframe_signals if s['signal'] == 'BUY')
            sell_signals = sum(1 for s in timeframe_signals if s['signal'] == 'SELL')
            
            print(f"\n   📊 {timeframe_names[timeframe]} ({timeframe}) SUMMARY:")
            print(f"      ✅ Analyzed: {successful}/{len(tickers)} stocks")
            print(f"      🟢 BUY signals: {buy_signals}")
            print(f"      🔴 SELL signals: {sell_signals}")
            print(f"      📈 Total signals: {len(timeframe_signals)}")
    
    print(f"\n📊 COMBINED MULTI-TIMEFRAME SUMMARY:")
    print(f"   📈 Total signals found: {len(all_signals)}")
    
    # Group by timeframe for summary
    by_timeframe = {}
    for signal in all_signals:
        tf = signal.get('interval', '1d')
        if tf not in by_timeframe:
            by_timeframe[tf] = {'buy': 0, 'sell': 0, 'total': 0}
        by_timeframe[tf][signal['signal'].lower()] += 1
        by_timeframe[tf]['total'] += 1
    
    print(f"   📊 Breakdown by timeframe:")
    for tf in timeframes:
        if tf in by_timeframe:
            data = by_timeframe[tf]
            print(f"      ⏰ {timeframe_names[tf]:<8} ({tf}): {data['total']:2d} signals ({data['buy']} BUY, {data['sell']} SELL)")
        else:
            print(f"      ⏰ {timeframe_names[tf]:<8} ({tf}):  0 signals")
    
    return all_signals
    """Analyze stocks across multiple timeframes simultaneously"""
    
    timeframes = ['5m', '15m', '1h', '4h', '1d']
    timeframe_names = {
        '5m': '5-Min',
        '15m': '15-Min',
        '1h': '1-Hour',
        '4h': '4-Hour',
        '1d': 'Daily'
    }
    
    # Use fewer stocks for multi-timeframe analysis to avoid API limits
    test_tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS[:20]]  # First 20 stocks
    
    print(f"\n🚀 MULTI-TIMEFRAME SWING CALLS ANALYSIS")
    print(f"📊 Analyzing {len(test_tickers)} stocks across {len(timeframes)} timeframes")
    print(f"📈 Strategy: EMA({ema_value}) vs SMA({sma_value}) + RSI({rsi_overbought}/{rsi_oversold})")
    print(f"⏰ Timeframes: {', '.join([f'{timeframe_names[tf]} ({tf})' for tf in timeframes])}")
    print("="*80)
    
    all_signals = []
    
    for timeframe in timeframes:
        print(f"\n📊 Analyzing {timeframe_names[timeframe]} ({timeframe}) timeframe...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ticker = {
                executor.submit(analyze_stock_swing_calls, ticker, ema_value, sma_value, rsi_overbought, rsi_oversold, timeframe, False): ticker 
                for ticker in test_tickers
            }
            
            timeframe_signals = []
            completed = 0
            
            for future in concurrent.futures.as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                completed += 1
                
                try:
                    result = future.result(timeout=30)
                    if result and result['signal'] in ['BUY', 'SELL']:
                        timeframe_signals.append(result)
                        all_signals.append(result)
                        signal_display = result['signal']
                        price_display = f"₹{result['current_price']:.2f}"
                        print(f"   ✅ {ticker}: {signal_display} @ {price_display}")
                except Exception:
                    continue
            
            print(f"   📊 {timeframe_names[timeframe]} Results: {len(timeframe_signals)} signals from {len(test_tickers)} stocks")
    
    print(f"\n📊 MULTI-TIMEFRAME SUMMARY:")
    print(f"   📈 Total signals found: {len(all_signals)}")
    
    # Group by timeframe
    by_timeframe = {}
    for signal in all_signals:
        tf = signal.get('interval', '1d')
        if tf not in by_timeframe:
            by_timeframe[tf] = []
        by_timeframe[tf].append(signal)
    
    for tf in timeframes:
        if tf in by_timeframe:
            signals = by_timeframe[tf]
            buy_count = sum(1 for s in signals if s['signal'] == 'BUY')
            sell_count = sum(1 for s in signals if s['signal'] == 'SELL')
            print(f"   ⏰ {timeframe_names[tf]} ({tf}): {len(signals)} signals ({buy_count} BUY, {sell_count} SELL)")
        else:
            print(f"   ⏰ {timeframe_names[tf]} ({tf}): 0 signals")
    
    return all_signals


def compare_configurations_multi_timeframe():
    """Compare original vs suggested across multiple timeframes"""
    
    print("🎯 MULTI-TIMEFRAME CONFIGURATION COMPARISON")
    print("📊 Testing Original EMA(5)/SMA(50) vs Suggested EMA(2)/SMA(200)")
    print("⏰ Across multiple timeframes: 5m, 15m, 1h, 4h, 1d")
    print("="*80)
    
    timeframes = ['5m', '15m', '1h', '4h', '1d']
    timeframe_names = {
        '5m': '5-Min', '15m': '15-Min', '1h': '1-Hour', '4h': '4-Hour', '1d': 'Daily'
    }
    
    configs = [
        {'ema': 5, 'sma': 50, 'name': 'Original EMA(5)/SMA(50)'},
        {'ema': 2, 'sma': 200, 'name': 'Suggested EMA(2)/SMA(200)'}
    ]
    
    test_tickers = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ITC', 'KOTAKBANK']
    
    results = {}
    
    for config in configs:
        print(f"\n📈 Testing {config['name']}...")
        print("-" * 50)
        
        config_results = {}
        total_signals = 0
        
        for timeframe in timeframes:
            timeframe_signals = []
            
            for ticker in test_tickers:
                result = analyze_stock_swing_calls(
                    ticker, config['ema'], config['sma'], 80, 20, timeframe, debug=False
                )
                if result and result['signal'] in ['BUY', 'SELL']:
                    timeframe_signals.append(result)
                    total_signals += 1
            
            config_results[timeframe] = timeframe_signals
            buy_count = sum(1 for r in timeframe_signals if r['signal'] == 'BUY')
            sell_count = sum(1 for r in timeframe_signals if r['signal'] == 'SELL')
            
            print(f"   {timeframe_names[timeframe]:<8} ({timeframe}): {len(timeframe_signals):2d} signals ({buy_count} BUY, {sell_count} SELL)")
        
        results[config['name']] = {
            'by_timeframe': config_results,
            'total_signals': total_signals
        }
        
        print(f"   📊 Total: {total_signals} signals across all timeframes")
    
    # Comparison
    original = results['Original EMA(5)/SMA(50)']
    suggested = results['Suggested EMA(2)/SMA(200)']
    
    print(f"\n🏆 MULTI-TIMEFRAME COMPARISON:")
    print("="*60)
    
    # Detailed comparison by timeframe
    print(f"{'Timeframe':<12} | {'Original':<10} | {'Suggested':<10} | {'Difference':<12}")
    print("-" * 60)
    
    total_original = 0
    total_suggested = 0
    
    for tf in timeframes:
        orig_count = len(original['by_timeframe'].get(tf, []))
        sugg_count = len(suggested['by_timeframe'].get(tf, []))
        diff = sugg_count - orig_count
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        
        total_original += orig_count
        total_suggested += sugg_count
        
        print(f"{timeframe_names[tf]:<12} | {orig_count:<10} | {sugg_count:<10} | {diff_str:<12}")
    
    print("-" * 60)
    print(f"{'TOTAL':<12} | {total_original:<10} | {total_suggested:<10} | {'+' if total_suggested > total_original else ''}{total_suggested - total_original:<12}")
    
    if total_suggested > total_original:
        improvement = total_suggested - total_original
        print(f"\n✅ SURAJKUMARSADHAPHULE WAS RIGHT!")
        print(f"   🎉 EMA(2)/SMA(200) gives +{improvement} more signals across all timeframes!")
        print(f"   📊 Total improvement: {improvement} additional signals")
        
        # Find best performing timeframes
        best_improvements = []
        for tf in timeframes:
            orig_count = len(original['by_timeframe'].get(tf, []))
            sugg_count = len(suggested['by_timeframe'].get(tf, []))
            if sugg_count > orig_count:
                best_improvements.append((tf, sugg_count - orig_count))
        
        if best_improvements:
            best_improvements.sort(key=lambda x: x[1], reverse=True)
            print(f"\n🚀 BEST PERFORMING TIMEFRAMES FOR EMA(2)/SMA(200):")
            for tf, improvement in best_improvements[:3]:
                print(f"   {timeframe_names[tf]} ({tf}): +{improvement} more signals")
    
    elif total_suggested < total_original:
        decrease = total_original - total_suggested
        print(f"\n📉 Original EMA(5)/SMA(50) performs better overall")
        print(f"   📊 Original has {decrease} more signals than suggested")
    else:
        print(f"\n➡️  Both configurations give same total number of signals")
    
    print(f"\n🚀 RECOMMENDED COMMANDS:")
    print(f"   # Test best performing timeframe")
    if total_suggested > total_original:
        print(f"   python swing.py --suggested --15min --debug")
        print(f"   python swing.py --suggested --5min --debug")
    else:
        print(f"   python swing.py --hourly --debug")
    print(f"   # Run multi-timeframe analysis")
    print(f"   python swing.py --multi-timeframe --suggested")
    """Compare original EMA(5)/SMA(50) vs suggested EMA(2)/SMA(200)"""
    
    timeframe_name = {
        '5m': '5-Minute',
        '15m': '15-Minute',
        '1h': 'Hourly', 
        '4h': '4-Hour',
        '1d': 'Daily',
        '1wk': 'Weekly',
        '1mo': 'Monthly'
    }.get(interval, interval)
    
    print("🎯 COMPARING CONFIGURATIONS: Original vs Suggested")
    print("📊 Testing surajkumarsadhaphule's EMA(2)/SMA(200) suggestion")
    print(f"⏰ Timeframe: {timeframe_name} ({interval})")
    print("="*70)
    
    test_tickers = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ITC', 'KOTAKBANK']
    
    configs = [
        {'ema': 5, 'sma': 50, 'name': 'Original EMA(5)/SMA(50)'},
        {'ema': 2, 'sma': 200, 'name': 'Suggested EMA(2)/SMA(200)'}
    ]
    
    results = {}
    
    for config in configs:
        print(f"\n📈 Testing {config['name']} on {timeframe_name}...")
        print("-" * 40)
        
        config_signals = []
        
        for ticker in test_tickers:
            result = analyze_stock_swing_calls(
                ticker, config['ema'], config['sma'], 80, 20, interval, debug=False
            )
            if result:
                config_signals.append(result)
                if result['signal'] in ['BUY', 'SELL']:
                    print(f"   ✅ {ticker}: {result['signal']} @ ₹{result['current_price']:.2f}")
        
        buy_count = sum(1 for r in config_signals if r['signal'] == 'BUY')
        sell_count = sum(1 for r in config_signals if r['signal'] == 'SELL')
        total_signals = buy_count + sell_count
        
        results[config['name']] = {
            'signals': config_signals,
            'buy_count': buy_count,
            'sell_count': sell_count,
            'total_signals': total_signals
        }
        
        print(f"   📊 Results: {buy_count} BUY, {sell_count} SELL = {total_signals} total signals")
    
    # Comparison
    original = results['Original EMA(5)/SMA(50)']
    suggested = results['Suggested EMA(2)/SMA(200)']
    
    print(f"\n🏆 COMPARISON RESULTS ({timeframe_name} timeframe):")
    print("="*50)
    print(f"   Original  EMA(5)/SMA(50):  {original['total_signals']} signals")
    print(f"   Suggested EMA(2)/SMA(200): {suggested['total_signals']} signals")
    
    if suggested['total_signals'] > original['total_signals']:
        improvement = suggested['total_signals'] - original['total_signals']
        print(f"\n✅ SURAJKUMARSADHAPHULE WAS RIGHT!")
        print(f"   🎉 EMA(2)/SMA(200) gives +{improvement} more signals on {timeframe_name}!")
        print(f"   📊 Improvement: {improvement} additional signals found")
    elif suggested['total_signals'] < original['total_signals']:
        decrease = original['total_signals'] - suggested['total_signals']
        print(f"\n📉 Original performs better on {timeframe_name} timeframe")
        print(f"   📊 Original has {decrease} more signals than suggested")
    else:
        print(f"\n➡️  Both configurations give same number of signals on {timeframe_name}")
    
    print(f"\n🚀 Try the suggested config: python swing.py --suggested --timeframe {interval}")

def main():
    """Main function - SWING CALLS Strategy"""
    parser = argparse.ArgumentParser(description="SWING CALLS Strategy Analyzer (Pine Script)")
    
    # Pine Script parameters
    parser.add_argument('--ema-value', type=int, default=5, 
                       help='EMA period (default: 5)')
    parser.add_argument('--sma-value', type=int, default=50, 
                       help='SMA period (default: 50)')
    parser.add_argument('--rsi-overbought', type=int, default=80, 
                       help='RSI overbought level (default: 80)')
    parser.add_argument('--rsi-oversold', type=int, default=20, 
                       help='RSI oversold level (default: 20)')
    parser.add_argument('--top', type=int, default=15, 
                       help='Top N signals to display (default: 15)')
    parser.add_argument('--output', type=str, 
                       help='Output directory (default: output)')
    parser.add_argument('--workers', type=int, default=3, 
                       help='Max concurrent workers (default: 3)')
    parser.add_argument('--test-single', type=str, 
                       help='Test analysis on a single ticker')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug output')
    parser.add_argument('--show-all', action='store_true', 
                       help='Show all signals (default behavior)')
    parser.add_argument('--buy-only', action='store_true', 
                       help='Show only BUY signals')
    parser.add_argument('--sell-only', action='store_true', 
                       help='Show only SELL signals')
    parser.add_argument('--quick-test', action='store_true',
                       help='Quick test with popular stocks')
    
    # NEW: Add suggested configuration option
    parser.add_argument('--suggested', action='store_true',
                       help='Use surajkumarsadhaphule suggestion: EMA(2)/SMA(200)')
    parser.add_argument('--compare', action='store_true',
                       help='Compare original vs suggested configurations')
    parser.add_argument('--multi-timeframe', action='store_true',
                       help='Analyze across multiple timeframes (5m, 15m, 1h, 4h, 1d)')
    parser.add_argument('--compare-multi', action='store_true',
                       help='Compare configurations across multiple timeframes')
    
    # NEW: Add timeframe options
    parser.add_argument('--timeframe', type=str, default='1d',
                       choices=['5m', '15m', '1h', '4h', '1d', '1wk', '1mo'],
                       help='Timeframe: 5m, 15m, 1h, 4h, 1d (default), 1wk, 1mo')
    parser.add_argument('--5min', action='store_true', dest='min5',
                       help='Use 5-minute timeframe (shortcut for --timeframe 5m)')
    parser.add_argument('--15min', action='store_true', dest='min15',
                       help='Use 15-minute timeframe (shortcut for --timeframe 15m)')
    parser.add_argument('--hourly', action='store_true',
                       help='Use 1-hour timeframe (shortcut for --timeframe 1h)')
    parser.add_argument('--4hour', action='store_true', dest='hour4',
                       help='Use 4-hour timeframe (shortcut for --timeframe 4h)')
    parser.add_argument('--weekly', action='store_true',
                       help='Use weekly timeframe (shortcut for --timeframe 1wk)')
    
    args = parser.parse_args()
    
    # Handle timeframe shortcuts
    if args.min5:
        args.timeframe = '5m'
    elif args.min15:
        args.timeframe = '15m'
    elif args.hourly:
        args.timeframe = '1h'
    elif args.hour4:
        args.timeframe = '4h'  
    elif args.weekly:
        args.timeframe = '1wk'
    
    timeframe_name = {
        '5m': '5-Minute',
        '15m': '15-Minute',
        '1h': 'Hourly',
        '4h': '4-Hour',
        '1d': 'Daily',
        '1wk': 'Weekly',
        '1mo': 'Monthly'
    }.get(args.timeframe, args.timeframe)
    
    # Handle suggested configuration
    if args.suggested:
        args.ema_value = 2
        args.sma_value = 200
        print("🎯 Using SUGGESTED CONFIGURATION: EMA(2)/SMA(200)")
        print("💡 Based on surajkumarsadhaphule's comment: 'Results are far better'")
    
    print(f"⏰ Timeframe: {timeframe_name} ({args.timeframe})")
    
    # Compare configurations mode
    if args.compare:
        compare_configurations(args.timeframe)
        return
    
    # Multi-timeframe comparison mode
    if args.compare_multi:
        compare_configurations_multi_timeframe()
        return
    
    # Multi-timeframe analysis mode
    if args.multi_timeframe:
        print("🚀 MULTI-TIMEFRAME ANALYSIS MODE")
        all_signals = analyze_multiple_timeframes(
            ema_value=args.ema_value,
            sma_value=args.sma_value,
            rsi_overbought=args.rsi_overbought,
            rsi_oversold=args.rsi_oversold,
            max_workers=args.workers,
            debug=args.debug
        )
        
        if all_signals:
            # Show combined results from all timeframes
            buy_signals = [s for s in all_signals if s['signal'] == 'BUY']
            sell_signals = [s for s in all_signals if s['signal'] == 'SELL']
            
            if buy_signals:
                display_swing_signals(buy_signals, "BUY (All Timeframes)", args.top)
            if sell_signals:
                display_swing_signals(sell_signals, "SELL (All Timeframes)", args.top)
            
            print(f"\n📊 MULTI-TIMEFRAME FINAL SUMMARY:")
            print(f"   🟢 Total BUY signals: {len(buy_signals)}")
            print(f"   🔴 Total SELL signals: {len(sell_signals)}")
            print(f"   📈 Total signals across all timeframes: {len(all_signals)}")
        else:
            print("\n❌ No signals found across any timeframes!")
        
        return
    
    # Quick test mode
    if args.quick_test:
        print("🧪 QUICK TEST MODE - SWING CALLS Strategy")
        if args.suggested:
            print("🎯 Using SUGGESTED EMA(2)/SMA(200) parameters")
        test_tickers = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ITC']
        print("="*50)
        
        for ticker in test_tickers:
            print(f"\n🔍 Testing {ticker}...")
            result = analyze_stock_swing_calls(
                ticker, args.ema_value, args.sma_value, args.rsi_overbought, args.rsi_oversold, args.timeframe, debug=True
            )
            if result:
                signal = result['signal']
                price = f"₹{result['current_price']:.2f}"
                rsi = f"RSI:{result['rsi']:.0f}"
                color = result['sma_color']
                print(f"✅ {ticker}: {signal} | {price} | {rsi} | {color}")
            else:
                print(f"❌ {ticker}: Failed")
        return
    
    # Test single ticker
    if args.test_single:
        config_name = f"EMA({args.ema_value})/SMA({args.sma_value})"
        if args.suggested:
            config_name += " - SUGGESTED CONFIG"
        
        print(f"🧪 TESTING SINGLE TICKER: {args.test_single}")
        print(f"📊 SWING CALLS: {config_name} + RSI({args.rsi_overbought}/{args.rsi_oversold})")
        print(f"⏰ Timeframe: {timeframe_name} ({args.timeframe})")
        print("="*50)
        result = analyze_stock_swing_calls(
            args.test_single, 
            args.ema_value, args.sma_value, args.rsi_overbought, args.rsi_oversold, args.timeframe,
            debug=True
        )
        if result:
            print(f"\n✅ SWING CALLS Analysis:")
            print(f"   🎯 Signal: {result['signal']}")
            if result['signal_type'] != 'None':
                print(f"   📊 Type: {result['signal_type']}")
            if result['rsi_alert'] != 'None':
                print(f"   🔔 RSI Alert: {result['rsi_alert']}")
            print(f"   💰 Price: ₹{result['current_price']:.2f}")
            print(f"   📈 EMA({args.ema_value}): ₹{result['ema_5']:.2f}")
            print(f"   📊 SMA({args.sma_value}): ₹{result['sma_50']:.2f}")
            print(f"   📈 RSI: {result['rsi']:.1f}")
            print(f"   🎨 SMA Color: {result['sma_color']}")
            print(f"   🕯️  Candle: {result['candle_type']}")
        else:
            print(f"\n❌ No result for {args.test_single}")
        return
    
    config_name = f"EMA({args.ema_value})/SMA({args.sma_value})"
    if args.suggested:
        config_name += " - SUGGESTED"
    
    print("🎯 SWING CALLS STRATEGY ANALYZER")
    print("📊 Pine Script: SMA/EMA Crossover + RSI System")
    print("="*50)
    print(f"📈 Configuration: {config_name}")
    print(f"📈 RSI: {args.rsi_overbought}/{args.rsi_oversold} levels")
    if args.suggested:
        print(f"💡 Using surajkumarsadhaphule's suggestion")
    print(f"🎯 Pine Script faithful implementation")
    print("="*50)
    
    # Set output directory
    output_dir = args.output or getattr(config, 'OUTPUT_DIR', 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Analyze all stocks
    all_signals = analyze_all_stocks_swing_calls(
        ema_value=args.ema_value,
        sma_value=args.sma_value,
        rsi_overbought=args.rsi_overbought,
        rsi_oversold=args.rsi_oversold,
        interval=args.timeframe,
        max_workers=args.workers,
        debug=args.debug
    )
    
    if not all_signals:
        print("\n❌ No signals generated!")
        print("\n💡 TROUBLESHOOTING:")
        print("   🧪 Try: --quick-test")
        print("   🎯 Try: --suggested (EMA2/SMA200)")
        print("   🚀 Try: --multi-timeframe --suggested")
        print("   ⚡ Try: --5min (5-minute timeframe - many signals)")
        print("   🎯 Try: --15min (15-minute timeframe - frequent signals)")
        print("   ⚡ Try: --hourly (1h timeframe)")
        print("   🎯 Try: --4hour (4h timeframe)")
        print("   🔧 Try: --test-single RELIANCE --debug")
        print("   📊 Try: --compare-multi (compare across all timeframes)")
        print("   📊 Try: --compare --timeframe 5m")
        print("   📊 Try: --compare --timeframe 15m")
        print("   💡 Shorter timeframes usually give MORE signals!")
        return
    
    # Display results
    if args.buy_only:
        buy_signals = filter_signals_by_type(all_signals, ['BUY'])
        display_swing_signals(buy_signals, "BUY", args.top)
    elif args.sell_only:
        sell_signals = filter_signals_by_type(all_signals, ['SELL'])
        display_swing_signals(sell_signals, "SELL", args.top)
    else:
        # Show all by default
        buy_signals = filter_signals_by_type(all_signals, ['BUY'])
        sell_signals = filter_signals_by_type(all_signals, ['SELL'])
        hold_signals = filter_signals_by_type(all_signals, ['HOLD'])
        
        if buy_signals:
            display_swing_signals(buy_signals, "BUY", args.top)
        if sell_signals:
            display_swing_signals(sell_signals, "SELL", args.top)
        
        print(f"\n📊 SWING CALLS SUMMARY:")
        print(f"   🟢 BUY signals: {len(buy_signals)}")
        print(f"   🔴 SELL signals: {len(sell_signals)}")
        print(f"   ⚪ HOLD (no signal): {len(hold_signals)}")
        print(f"   📈 Total analyzed: {len(all_signals)}")
    
    print(f"\n✅ SWING CALLS Analysis Complete!")
    
    # Strategy notes
    print(f"\n💡 SWING CALLS STRATEGY NOTES:")
    print(f"   📊 Configuration: {config_name}")
    print(f"   🟢 BUY: SMA crosses under EMA + high > SMA (bullish breakout)")
    print(f"   🔴 SELL: SMA crosses over EMA + red candle (bearish breakdown)")
    print(f"   🔔 RSI Alerts: Exit signals at {args.rsi_overbought}/{args.rsi_oversold} levels")
    print(f"   🎨 SMA Colors: Green=Bullish, Red=Bearish, Yellow=Neutral/Extreme")
    if args.suggested:
        print(f"   🎯 Using surajkumarsadhaphule's suggestion for better results")
    
    print(f"\n🎯 USAGE EXAMPLES:")
    print(f"   # Test suggested EMA(2)/SMA(200) on daily timeframe")
    print(f"   python {sys.argv[0]} --suggested --debug")
    print(f"   ")
    print(f"   # Multi-timeframe analysis (5m, 15m, 1h, 4h, 1d)")
    print(f"   python {sys.argv[0]} --multi-timeframe --suggested")
    print(f"   python {sys.argv[0]} --multi-timeframe --debug")
    print(f"   ")
    print(f"   # Compare configurations across all timeframes")
    print(f"   python {sys.argv[0]} --compare-multi")
    print(f"   ")
    print(f"   # Intraday timeframes (more signals, more noise)")
    print(f"   python {sys.argv[0]} --5min --suggested --debug")
    print(f"   python {sys.argv[0]} --15min --suggested --debug")
    print(f"   python {sys.argv[0]} --timeframe 5m --debug")
    print(f"   ")
    print(f"   # Test on 1-hour timeframe (as recommended in Pine Script)")
    print(f"   python {sys.argv[0]} --hourly --debug")
    print(f"   python {sys.argv[0]} --timeframe 1h --suggested")
    print(f"   ")
    print(f"   # Test on 4-hour timeframe")
    print(f"   python {sys.argv[0]} --4hour --suggested --debug")
    print(f"   ")
    print(f"   # Compare configurations on different timeframes")
    print(f"   python {sys.argv[0]} --compare")
    print(f"   python {sys.argv[0]} --compare --timeframe 5m")
    print(f"   python {sys.argv[0]} --compare --timeframe 15m")
    print(f"   python {sys.argv[0]} --compare --timeframe 1h")
    print(f"   python {sys.argv[0]} --compare --timeframe 4h")
    print(f"   ")
    print(f"   # Single stock analysis")
    print(f"   python {sys.argv[0]} --test-single RELIANCE --suggested --5min --debug")
    print(f"   python {sys.argv[0]} --test-single KOTAKBANK --15min --debug")
    print(f"   python {sys.argv[0]} --test-single INFY --hourly --suggested --debug")
    print(f"   ")
    print(f"   # Quick tests")
    print(f"   python {sys.argv[0]} --quick-test --suggested --5min")
    print(f"   python {sys.argv[0]} --quick-test --15min")
    
    print(f"\n💡 TIMEFRAME RECOMMENDATIONS:")
    print(f"   ⚡ 5-Minute (5m): Scalping, very frequent signals, high noise")
    print(f"   🎯 15-Minute (15m): Intraday trading, good signal frequency")
    print(f"   📊 1-Hour (1h): Pine Script recommended, balanced approach")
    print(f"   🎯 4-Hour (4h): Swing trading, quality signals")
    print(f"   📈 Daily (1d): Position trading, less noise, fewer signals")
    print(f"   📊 Weekly (1wk): Long-term trend following")
    print(f"   ")
    print(f"   🚨 INTRADAY NOTES:")
    print(f"   • 5m & 15m have limited historical data (~60 days)")
    print(f"   • More signals = more opportunities but also more noise")
    print(f"   • EMA(2)/SMA(200) might work especially well on shorter timeframes")
    print(f"   ")
    print(f"   🎯 BEST COMMANDS TO TRY:")
    print(f"   python {sys.argv[0]} --multi-timeframe --suggested")
    print(f"   python {sys.argv[0]} --compare-multi")
    print(f"   python {sys.argv[0]} --15min --suggested --debug")
    print(f"   ")
    print(f"   💡 Pine Script author says: 'Best work with 1h+ timeframes'")
    print(f"   🎯 surajkumarsadhaphule suggests: EMA(2)/SMA(200) for better results")
    print(f"   ⚡ Try EMA(2)/SMA(200) on 15m for frequent intraday signals!")

if __name__ == "__main__":
    main()