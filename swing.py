#!/usr/bin/env python
# comprehensive_strategy_analyzer.py - Multi-Indicator Strategy (Squeeze Momentum + EMA + RSI + MACD)

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
    print("Successfully loaded config with tickers")
except ImportError:
    print("Config not found! Using default tickers")
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

def get_stock_data(ticker, lookback_days=50):
    """Get stock data for analysis with proper error handling"""
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
        
        if data.empty or len(data) < lookback_days:
            print(f"   {ticker}: Insufficient data ({len(data)} days)")
            return None
        
        # Clean data
        data = data.dropna()
        
        if len(data) < lookback_days:
            print(f"   {ticker}: Insufficient clean data ({len(data)} days)")
            return None
        
        return data
        
    except Exception as e:
        print(f"   {ticker}: Data fetch error - {str(e)}")
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

def calculate_ema(prices, period):
    """Calculate Exponential Moving Average"""
    try:
        if len(prices) < period:
            return prices.mean() if len(prices) > 0 else 0
        
        ema = prices.ewm(span=period).mean()
        return ema.iloc[-1] if not pd.isna(ema.iloc[-1]) else prices.iloc[-1]
    except:
        return prices.iloc[-1] if len(prices) > 0 else 0

def calculate_sma(prices, period):
    """Calculate Simple Moving Average"""
    try:
        if len(prices) < period:
            return prices.mean() if len(prices) > 0 else 0
        
        sma = prices.rolling(window=period).mean()
        return sma.iloc[-1] if not pd.isna(sma.iloc[-1]) else prices.iloc[-1]
    except:
        return prices.iloc[-1] if len(prices) > 0 else 0

def calculate_atr(data, period=14):
    """Calculate Average True Range"""
    try:
        if len(data) < period + 1:
            return 0
        
        high_low = data['High'] - data['Low']
        high_close = abs(data['High'] - data['Close'].shift(1))
        low_close = abs(data['Low'] - data['Close'].shift(1))
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 0
    except:
        return 0

def calculate_macd(prices, fast_length=16, slow_length=26, signal_length=8):
    """Calculate MACD with custom parameters"""
    try:
        if len(prices) < slow_length + signal_length:
            return {'macd': 0, 'signal': 0, 'histogram': 0}
        
        fast_ema = prices.ewm(span=fast_length).mean()
        slow_ema = prices.ewm(span=slow_length).mean()
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=signal_length).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line.iloc[-1] if not pd.isna(macd_line.iloc[-1]) else 0,
            'signal': signal_line.iloc[-1] if not pd.isna(signal_line.iloc[-1]) else 0,
            'histogram': histogram.iloc[-1] if not pd.isna(histogram.iloc[-1]) else 0,
            'histogram_prev': histogram.iloc[-2] if len(histogram) > 1 and not pd.isna(histogram.iloc[-2]) else 0
        }
    except:
        return {'macd': 0, 'signal': 0, 'histogram': 0, 'histogram_prev': 0}

def calculate_squeeze_momentum(data, bb_length=20, bb_mult=2.0, kc_length=20, kc_mult=1.5):
    """Calculate Squeeze Momentum indicator"""
    try:
        if len(data) < max(bb_length, kc_length) + 1:
            return {'squeeze_on': False, 'momentum_value': 0, 'momentum_color': 'neutral'}
        
        # Bollinger Bands
        bb_basis = data['Close'].rolling(window=bb_length).mean()
        bb_dev = data['Close'].rolling(window=bb_length).std() * bb_mult
        bb_upper = bb_basis + bb_dev
        bb_lower = bb_basis - bb_dev
        
        # Keltner Channels
        kc_basis = data['Close'].rolling(window=kc_length).mean()
        tr = pd.concat([
            data['High'] - data['Low'],
            abs(data['High'] - data['Close'].shift(1)),
            abs(data['Low'] - data['Close'].shift(1))
        ], axis=1).max(axis=1)
        kc_range = tr.rolling(window=kc_length).mean() * kc_mult
        kc_upper = kc_basis + kc_range
        kc_lower = kc_basis - kc_range
        
        # Squeeze condition
        squeeze_on = (bb_lower.iloc[-1] > kc_lower.iloc[-1]) and (bb_upper.iloc[-1] < kc_upper.iloc[-1])
        
        # Momentum calculation (simplified linear regression)
        highest_high = data['High'].rolling(window=kc_length).max()
        lowest_low = data['Low'].rolling(window=kc_length).min()
        avg_hl = (highest_high + lowest_low) / 2
        avg_close = data['Close'].rolling(window=kc_length).mean()
        momentum_source = data['Close'] - (avg_hl + avg_close) / 2
        
        # Simple momentum value (last value)
        momentum_value = momentum_source.iloc[-1] if not pd.isna(momentum_source.iloc[-1]) else 0
        momentum_prev = momentum_source.iloc[-2] if len(momentum_source) > 1 and not pd.isna(momentum_source.iloc[-2]) else 0
        
        # Momentum color/direction
        if momentum_value > 0:
            momentum_color = 'green' if momentum_value > momentum_prev else 'dark_green'
        else:
            momentum_color = 'red' if momentum_value < momentum_prev else 'dark_red'
        
        return {
            'squeeze_on': squeeze_on,
            'momentum_value': momentum_value,
            'momentum_prev': momentum_prev,
            'momentum_color': momentum_color,
            'is_green_momentum': momentum_value > 0,
            'is_red_momentum': momentum_value < 0
        }
    except Exception as e:
        return {'squeeze_on': False, 'momentum_value': 0, 'momentum_prev': 0, 'momentum_color': 'neutral', 'is_green_momentum': False, 'is_red_momentum': False}

def detect_comprehensive_signals(data, current_price, debug=False):
    """
    Detect signals using comprehensive multi-indicator strategy
    Based on: Squeeze Momentum + EMA + RSI + MACD + ATR
    """
    try:
        if len(data) < 50:
            return {
                'signal_type': 'HOLD',
                'signal_strength': 0,
                'squeeze_data': {},
                'macd_data': {},
                'ema_data': {},
                'rsi_data': {},
                'atr_data': {},
                'stop_loss': current_price,
                'target_price': current_price,
                'breakout_signal': 'NONE'
            }
        
        # Calculate all indicators
        ema_200 = calculate_ema(data['Close'], 200)
        rsi = calculate_rsi(data['Close'], 5)  # Fast RSI like in Pine Script
        macd_data = calculate_macd(data['Close'])
        squeeze_data = calculate_squeeze_momentum(data)
        atr = calculate_atr(data)
        
        # ATR-based stop loss
        atr_multiplier = 1.6
        long_stop_loss = current_price - (atr * atr_multiplier)
        short_stop_loss = current_price + (atr * atr_multiplier)
        
        # Trend conditions
        bullish_trend = current_price > ema_200
        bearish_trend = current_price < ema_200
        
        # Signal conditions from Pine Script strategy
        
        # Squeeze momentum signal (trend crossover)
        trend_buy_signal_sqz = (
            squeeze_data['momentum_value'] > 0 and squeeze_data['momentum_prev'] <= 0
        ) or (
            squeeze_data['momentum_value'] > 0 and 
            squeeze_data['momentum_value'] > squeeze_data['momentum_prev'] and 
            squeeze_data['momentum_prev'] < 0
        )
        
        trend_sell_signal_sqz = squeeze_data['momentum_value'] < 0 and squeeze_data['momentum_prev'] >= 0
        
        # MACD signal (specific pattern from Pine Script)
        macd_buy_signal = (
            macd_data['histogram'] > macd_data['histogram_prev'] and
            data['Close'].iloc[-1] > data['Close'].iloc[-2] and
            macd_data['histogram'] < 0 and
            squeeze_data['is_red_momentum'] and
            data['Open'].iloc[-2] > ema_200  # Previous open above EMA
        )
        
        # RSI signals
        rsi_buy_signal = rsi < 30 and squeeze_data['is_red_momentum'] and bearish_trend
        rsi_sell_signal = rsi > 70 and squeeze_data['is_green_momentum']
        
        # Determine signal type and strength
        signal_type = 'HOLD'
        signal_strength = 0
        stop_loss = current_price
        target_price = current_price
        
        # STRONG BUY: Squeeze momentum buy + bullish trend
        if trend_buy_signal_sqz and bullish_trend:
            signal_type = 'STRONG_BUY'
            signal_strength = abs(squeeze_data['momentum_value']) * 100
            stop_loss = long_stop_loss
            target_price = current_price + (current_price - stop_loss) * 2  # 2:1 R/R
            
        # WEAK BUY: MACD signal + bullish trend
        elif macd_buy_signal and bullish_trend:
            signal_type = 'WEAK_BUY'
            signal_strength = abs(macd_data['histogram']) * 50
            stop_loss = long_stop_loss
            target_price = current_price + (current_price - stop_loss) * 1.5  # 1.5:1 R/R
            
        # STRONG SELL: Squeeze momentum sell + bearish trend
        elif trend_sell_signal_sqz and bearish_trend:
            signal_type = 'STRONG_SELL'
            signal_strength = abs(squeeze_data['momentum_value']) * 100
            stop_loss = short_stop_loss
            target_price = current_price - (stop_loss - current_price) * 2  # 2:1 R/R
            
        # WEAK SELL: RSI overbought + momentum conditions
        elif rsi_sell_signal:
            signal_type = 'WEAK_SELL'
            signal_strength = (rsi - 70) * 2
            stop_loss = short_stop_loss
            target_price = current_price - (stop_loss - current_price) * 1.5  # 1.5:1 R/R
        
        # AGAINST TREND signals (if enabled)
        elif trend_buy_signal_sqz and bearish_trend:
            signal_type = 'WEAK_BUY'  # Against trend
            signal_strength = abs(squeeze_data['momentum_value']) * 50
            stop_loss = long_stop_loss
            target_price = current_price + (current_price - stop_loss) * 1.0  # 1:1 R/R
        
        if debug:
            print(f"   DEBUG: EMA200: {ema_200:.2f}, Current: {current_price:.2f}")
            print(f"   DEBUG: RSI: {rsi:.1f}")
            print(f"   DEBUG: Squeeze: {squeeze_data}")
            print(f"   DEBUG: MACD: {macd_data}")
            print(f"   DEBUG: Signals - SqzBuy: {trend_buy_signal_sqz}, MacdBuy: {macd_buy_signal}")
        
        return {
            'signal_type': signal_type,
            'signal_strength': float(signal_strength),
            'squeeze_data': squeeze_data,
            'macd_data': macd_data,
            'ema_data': {'ema_200': ema_200, 'bullish_trend': bullish_trend, 'bearish_trend': bearish_trend},
            'rsi_data': {'rsi': rsi},
            'atr_data': {'atr': atr},
            'stop_loss': float(stop_loss),
            'target_price': float(target_price),
            'breakout_signal': signal_type if signal_type != 'HOLD' else 'NONE'
        }
        
    except Exception as e:
        if debug:
            print(f"   DEBUG: Signal detection error: {e}")
        return {
            'signal_type': 'HOLD',
            'signal_strength': 0,
            'squeeze_data': {},
            'macd_data': {},
            'ema_data': {},
            'rsi_data': {},
            'atr_data': {},
            'stop_loss': current_price,
            'target_price': current_price,
            'breakout_signal': 'NONE'
        }

def enhanced_volume_confirmation(data, current_volume, lookback_days):
    """Enhanced volume analysis for breakout confirmation"""
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
    except Exception as e:
        return {'volume_strength': 'WEAK', 'volume_trend': 'NEUTRAL', 'volume_sma_ratio': 1.0}

def calculate_proper_metrics(data, volume_days=20, momentum_days=5):
    """Calculate volume and momentum using ONLY trading days"""
    latest = data.iloc[-1]
    current_price = latest['Close']
    current_volume = latest['Volume']
    
    if len(data) >= volume_days + 1:
        volume_period = data['Volume'].iloc[-(volume_days+1):-1]
        avg_volume = volume_period.mean()
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
    else:
        avg_volume = data['Volume'].mean()
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
    
    if len(data) >= momentum_days + 1:
        price_n_days_ago = data['Close'].iloc[-(momentum_days+1)]
        momentum = ((current_price - price_n_days_ago) / price_n_days_ago) * 100
    else:
        momentum = 0
    
    return volume_ratio, momentum, len(data)

def analyze_stock_comprehensive(ticker, volume_days=20, momentum_days=5, debug=False):
    """
    Comprehensive stock analysis with multi-indicator strategy
    """
    try:
        print(f"Analyzing {ticker} (Multi-Indicator Strategy)...")
        
        # Get data
        data = get_stock_data(ticker, max(50, volume_days + 10))
        if data is None:
            return None
        
        print(f"   Data: {len(data)} trading days available")
        
        # Get latest values
        latest = data.iloc[-1]
        current_price = latest['Close']
        current_volume = latest['Volume']
        
        # Detect comprehensive signals
        signal_data = detect_comprehensive_signals(data, current_price, debug)
        
        # Calculate metrics using proper trading days
        volume_ratio, momentum, trading_days_used = calculate_proper_metrics(
            data, volume_days, momentum_days
        )
        
        # Enhanced volume confirmation
        volume_analysis = enhanced_volume_confirmation(data, current_volume, volume_days)
        
        print(f"   Volume: Current {current_volume:,.0f} vs {volume_days}-day avg = {volume_ratio:.1f}x ({volume_analysis['volume_strength']})")
        print(f"   Momentum: {momentum:+.1f}% ({momentum_days} trading days)")
        print(f"   RSI: {signal_data['rsi_data'].get('rsi', 50):.1f}")
        print(f"   EMA Trend: {'BULLISH' if signal_data['ema_data'].get('bullish_trend') else 'BEARISH'}")
        print(f"   Squeeze: {'ON' if signal_data['squeeze_data'].get('squeeze_on') else 'OFF'}")
        
        # Risk management and position sizing
        if signal_data['signal_type'] in ['STRONG_BUY', 'WEAK_BUY']:
            risk_per_share = current_price - signal_data['stop_loss']
            buy_strength = signal_data['signal_strength']
            sell_strength = 0
        elif signal_data['signal_type'] in ['STRONG_SELL', 'WEAK_SELL']:
            risk_per_share = signal_data['stop_loss'] - current_price
            buy_strength = 0
            sell_strength = signal_data['signal_strength']
        else:
            risk_per_share = 0
            buy_strength = 0
            sell_strength = 0
        
        # Position sizing (1% risk on 100k capital)
        capital = 100000
        risk_amount = capital * 0.01
        position_size = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
        
        result = {
            'ticker': ticker,
            'signal_type': signal_data['signal_type'],
            'current_price': float(current_price),
            'target_price': signal_data['target_price'],
            'stop_loss': signal_data['stop_loss'],
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
            'ema_200': signal_data['ema_data'].get('ema_200', 0),
            'ema_trend': 'BULLISH' if signal_data['ema_data'].get('bullish_trend') else 'BEARISH',
            'volatility_score': signal_data['atr_data'].get('atr', 0),
            'rsi': signal_data['rsi_data'].get('rsi', 50),
            'squeeze_data': signal_data['squeeze_data'],
            'macd_data': signal_data['macd_data']
        }
        
        print(f"   Signal: {signal_data['signal_type']}")
        
        return result
        
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return None

def analyze_all_stocks(volume_days=20, momentum_days=5, max_workers=3, debug=False):
    """Analyze all stocks with multi-indicator strategy"""
    
    tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
    
    print(f"\nCOMPREHENSIVE MULTI-INDICATOR ANALYSIS")
    print(f"Analyzing {len(tickers)} stocks")
    print(f"Indicators: Squeeze Momentum + EMA200 + RSI + MACD + ATR")
    print(f"Volume Period: {volume_days} trading days")
    print(f"Momentum Period: {momentum_days} trading days")
    print("="*60)
    
    all_signals = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(analyze_stock_comprehensive, ticker, volume_days, momentum_days, debug): ticker 
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
                    print(f"{ticker} ({completed}/{len(tickers)}) - {result['signal_type']}")
                else:
                    failed += 1
                    print(f"{ticker} ({completed}/{len(tickers)}) - No data")
            except concurrent.futures.TimeoutError:
                failed += 1
                print(f"{ticker} ({completed}/{len(tickers)}) - Timeout")
            except Exception as e:
                failed += 1
                print(f"{ticker} ({completed}/{len(tickers)}) - Error: {str(e)[:50]}")
        
        print(f"\nANALYSIS SUMMARY:")
        print(f"   Successful: {successful}")
        print(f"   Failed: {failed}")
        print(f"   Total signals: {len(all_signals)}")
    
    return all_signals

def filter_signals_by_type(all_signals, signal_types):
    """Filter signals by type"""
    return [signal for signal in all_signals if signal['signal_type'] in signal_types]

def sort_signals_properly(signals):
    """Sort signals with STRONG first, then WEAK, by strength within each category"""
    
    if not signals:
        return signals
    
    strong_signals = [s for s in signals if 'STRONG' in s['signal_type']]
    weak_signals = [s for s in signals if 'WEAK' in s['signal_type']]
    
    is_buy_signals = any('BUY' in s['signal_type'] for s in signals)
    
    if is_buy_signals:
        strong_signals.sort(key=lambda x: x['buy_strength'], reverse=True)
        weak_signals.sort(key=lambda x: x['buy_strength'], reverse=True)
    else:
        strong_signals.sort(key=lambda x: x['sell_strength'], reverse=True)
        weak_signals.sort(key=lambda x: x['sell_strength'], reverse=True)
    
    return strong_signals + weak_signals

def display_top_signals(signals, signal_title, top_n=10):
    """Display top N signals"""
    
    if not signals:
        print(f"\nNo {signal_title} signals found!")
        return
    
    signals = sort_signals_properly(signals)
    top_signals = signals[:top_n]
    
    print(f"\nTOP {len(top_signals)} {signal_title} SIGNALS")
    print(f"Multi-Indicator Strategy (Squeeze + EMA + RSI + MACD)")
    print("="*80)
    
    table_data = []
    headers = ['Rank', 'Ticker', 'Signal', 'Price', 'Target', 'Strength%', 
              'Volume', 'RSI', 'EMA Trend', 'Momentum%', 'Stop Loss', 'Qty']
    
    for i, signal in enumerate(top_signals, 1):
        target_price = signal['target_price']
        
        if 'BUY' in signal['signal_type']:
            strength = signal['buy_strength']
        else:
            strength = signal['sell_strength']
        
        try:
            rsi_value = signal.get('rsi', 50)
            rsi_display = f"{rsi_value:.0f}"
        except:
            rsi_display = "50"
        
        try:
            volume_strength = signal['volume_analysis']['volume_strength']
            volume_display = f"{signal['volume_ratio']:.1f}x"
        except:
            volume_display = f"{signal['volume_ratio']:.1f}x"
        
        ema_trend = signal.get('ema_trend', 'NEUTRAL')
        
        table_data.append([
            i,
            signal['ticker'],
            signal['signal_type'].replace('_', ' '),
            f"Rs{signal['current_price']:.2f}",
            f"Rs{target_price:.2f}",
            f"{strength:.2f}%",
            volume_display,
            rsi_display,
            ema_trend,
            f"{signal['momentum']:+.1f}%",
            f"Rs{signal['stop_loss']:.2f}",
            signal['position_size']
        ])
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Summary statistics
    avg_strength = sum(strength for signal in top_signals 
                      for strength in [signal['buy_strength'] if 'BUY' in signal['signal_type'] 
                                     else signal['sell_strength']]) / len(top_signals)
    avg_volume = sum(signal['volume_ratio'] for signal in top_signals) / len(top_signals)
    avg_momentum = sum(signal['momentum'] for signal in top_signals) / len(top_signals)
    
    print(f"\nSUMMARY:")
    print(f"   {signal_title} signals: {len(signals)}")
    print(f"   Average strength: {avg_strength:.2f}%")
    print(f"   Average volume ratio: {avg_volume:.1f}x")
    print(f"   Average momentum: {avg_momentum:+.1f}%")

def main():
    """Main function with comprehensive analysis"""
    parser = argparse.ArgumentParser(description="Comprehensive Multi-Indicator Strategy Analyzer")
    
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
        print(f"TESTING SINGLE TICKER: {args.test_single}")
        print("="*50)
        result = analyze_stock_comprehensive(
            args.test_single, 
            args.volume_days, 
            args.momentum_days, 
            debug=True
        )
        if result:
            print(f"\nSUCCESS! Signal: {result['signal_type']}")
            print(f"Squeeze Data: {result['squeeze_data']}")
            print(f"MACD Data: {result['macd_data']}")
        else:
            print(f"\nNo result for {args.test_single}")
        return
    
    print("COMPREHENSIVE MULTI-INDICATOR STRATEGY ANALYZER")
    print("Using Squeeze Momentum + EMA + RSI + MACD + ATR")
    print("="*50)
    print(f"Volume Period: {args.volume_days} trading days") 
    print(f"Momentum Period: {args.momentum_days} trading days")
    print(f"Top Signals: {args.top}")
    print(f"Workers: {args.workers}")
    print("="*50)
    
    # Set output directory
    output_dir = args.output or getattr(config, 'OUTPUT_DIR', 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Analyze all stocks
    all_signals = analyze_all_stocks(
        volume_days=args.volume_days, 
        momentum_days=args.momentum_days,
        max_workers=args.workers,
        debug=args.debug
    )
    
    if not all_signals:
        print("\nNo signals generated!")
        print("TROUBLESHOOTING TIPS:")
        print("   Check if markets are open and data is available")
        print("   Enable debug mode: --debug")
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
        
        print(f"\nOVERALL SUMMARY:")
        print(f"   BUY signals: {len(buy_signals)}")
        print(f"   SELL signals: {len(sell_signals)}")
        print(f"   HOLD signals: {len(hold_signals)}")
        print(f"   Total analyzed: {len(all_signals)}")
    else:
        # Default: Show BUY signals only
        buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY', 'WEAK_BUY'])
        buy_signals = sort_signals_properly(buy_signals) if buy_signals else []
        display_top_signals(buy_signals, "BUY", args.top)
    
    print(f"\nAnalysis Complete!")
    
    # Trading notes
    print(f"\nTRADING NOTES:")
    print(f"   STRONG BUY: Squeeze momentum crossover + bullish EMA trend")
    print(f"   WEAK BUY: MACD reversal signal + bullish trend")
    print(f"   STRONG SELL: Squeeze momentum crossunder + bearish EMA trend")
    print(f"   WEAK SELL: RSI overbought + squeeze momentum conditions")
    print(f"   STOP LOSS: ATR-based (1.6x ATR)")
    print(f"   POSITION SIZE: 1% risk-based sizing")
    
    print(f"\nTROUBLESHOOTING COMMANDS:")
    print(f"   python {sys.argv[0]} --test-single RELIANCE --debug")
    print(f"   python {sys.argv[0]} --debug")

if __name__ == "__main__":
    main()