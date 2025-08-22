#!/usr/bin/env python
# strong_signals_inside_bar_analyzer.py - Only STRONG BUY/SELL signals

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
    # Default configuration with sector information
    class DefaultConfig:
        TOP_STOCKS = [
            {'symbol': 'RELIANCE', 'sector': 'Energy'},
            {'symbol': 'TCS', 'sector': 'IT'},
            {'symbol': 'HDFCBANK', 'sector': 'Banking'},
            {'symbol': 'INFY', 'sector': 'IT'},
            {'symbol': 'HINDUNILVR', 'sector': 'FMCG'},
            {'symbol': 'ICICIBANK', 'sector': 'Banking'},
            {'symbol': 'KOTAKBANK', 'sector': 'Banking'},
            {'symbol': 'ITC', 'sector': 'FMCG'},
            {'symbol': 'LT', 'sector': 'Infrastructure'},
            {'symbol': 'SBIN', 'sector': 'Banking'},
            {'symbol': 'BHARTIARTL', 'sector': 'Telecom'},
            {'symbol': 'ASIANPAINT', 'sector': 'Paints'},
            {'symbol': 'MARUTI', 'sector': 'Auto'},
            {'symbol': 'AXISBANK', 'sector': 'Banking'},
            {'symbol': 'BAJFINANCE', 'sector': 'NBFC'},
            {'symbol': 'WIPRO', 'sector': 'IT'},
            {'symbol': 'NESTLEIND', 'sector': 'FMCG'},
            {'symbol': 'ULTRACEMCO', 'sector': 'Cement'},
            {'symbol': 'TITAN', 'sector': 'Jewelry'},
            {'symbol': 'POWERGRID', 'sector': 'Power'}
        ]
        OUTPUT_DIR = 'output'
    
    config = DefaultConfig()

warnings.filterwarnings("ignore")

def get_sector_for_ticker(ticker):
    """Get sector information for ticker from config"""
    try:
        for stock in config.TOP_STOCKS:
            if stock['symbol'].replace('.NS', '') == ticker.replace('.NS', ''):
                return stock.get('sector', 'Unknown')
        return 'Unknown'
    except:
        return 'Unknown'

def get_stock_data(ticker, lookback_days=10):
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
            return None
        
        # Clean data
        data = data.dropna()
        
        if len(data) < lookback_days + 5:
            return None
        
        return data
        
    except Exception as e:
        print(f"   {ticker}: Data fetch error - {str(e)}")
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

def calculate_ema(prices, period):
    """Calculate Exponential Moving Average"""
    try:
        if len(prices) < period:
            return prices.mean() if len(prices) > 0 else 0
        
        ema = prices.ewm(span=period).mean()
        return ema.iloc[-1] if not pd.isna(ema.iloc[-1]) else prices.iloc[-1]
    except:
        return prices.iloc[-1] if len(prices) > 0 else 0

def detect_inside_bar(data, lookback_bars=3):
    """
    Detect Inside Bar patterns
    Returns: dict with inside bar info and breakout signals
    """
    try:
        if len(data) < lookback_bars + 2:
            return {
                'has_inside_bar': False,
                'inside_bar_type': 'NONE',
                'mother_bar_high': 0,
                'mother_bar_low': 0,
                'inside_bar_high': 0,
                'inside_bar_low': 0,
                'breakout_signal': 'NONE',
                'bars_since_inside': 999
            }
        
        # Look for inside bars in recent history
        for i in range(1, min(lookback_bars + 1, len(data))):
            current_bar = data.iloc[-i]
            mother_bar = data.iloc[-i-1]
            
            # Inside bar condition: current bar completely within previous bar
            is_inside = (current_bar['High'] < mother_bar['High'] and 
                        current_bar['Low'] > mother_bar['Low'])
            
            if is_inside:
                # Determine inside bar type (bullish or bearish)
                inside_bar_type = 'BULLISH' if current_bar['Close'] >= current_bar['Open'] else 'BEARISH'
                
                # Check for breakout on subsequent bars
                latest_bar = data.iloc[-1]
                breakout_signal = 'NONE'
                
                # Bullish breakout: price breaks above mother bar high
                if latest_bar['Close'] > mother_bar['High']:
                    breakout_signal = 'BULLISH_BREAKOUT'
                # Bearish breakout: price breaks below mother bar low
                elif latest_bar['Close'] < mother_bar['Low']:
                    breakout_signal = 'BEARISH_BREAKOUT'
                # Pending breakout: still within range
                elif (latest_bar['Close'] <= mother_bar['High'] and 
                      latest_bar['Close'] >= mother_bar['Low']):
                    breakout_signal = 'PENDING'
                
                return {
                    'has_inside_bar': True,
                    'inside_bar_type': inside_bar_type,
                    'mother_bar_high': float(mother_bar['High']),
                    'mother_bar_low': float(mother_bar['Low']),
                    'inside_bar_high': float(current_bar['High']),
                    'inside_bar_low': float(current_bar['Low']),
                    'breakout_signal': breakout_signal,
                    'bars_since_inside': i
                }
        
        # No inside bar found
        return {
            'has_inside_bar': False,
            'inside_bar_type': 'NONE',
            'mother_bar_high': 0,
            'mother_bar_low': 0,
            'inside_bar_high': 0,
            'inside_bar_low': 0,
            'breakout_signal': 'NONE',
            'bars_since_inside': 999
        }
        
    except Exception as e:
        # Return safe defaults on any error
        return {
            'has_inside_bar': False,
            'inside_bar_type': 'NONE',
            'mother_bar_high': 0,
            'mother_bar_low': 0,
            'inside_bar_high': 0,
            'inside_bar_low': 0,
            'breakout_signal': 'NONE',
            'bars_since_inside': 999
        }

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
    """
    Calculate volume and momentum using ONLY trading days (Fixed version)
    """
    # Get latest values
    latest = data.iloc[-1]
    current_price = latest['Close']
    current_volume = latest['Volume']
    
    # Volume ratio - Last N TRADING DAYS
    if len(data) >= volume_days + 1:
        # Get exactly N trading days (excluding current day)
        volume_period = data['Volume'].iloc[-(volume_days+1):-1]  # Last N trading sessions
        avg_volume = volume_period.mean()
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
    else:
        # Fallback if less than N days of data
        avg_volume = data['Volume'].mean()
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
    
    # Momentum - Last N TRADING DAYS
    if len(data) >= momentum_days + 1:
        # Get price from N trading days ago
        price_n_days_ago = data['Close'].iloc[-(momentum_days+1)]  # N+1 rows back = N days ago
        momentum = ((current_price - price_n_days_ago) / price_n_days_ago) * 100
    else:
        momentum = 0
    
    return volume_ratio, momentum, len(data)

def calculate_advanced_signals(data, current_price, ema_period=50):
    """Calculate advanced trading signals with EMA trend filter"""
    
    # EMA trend filter
    ema_50 = calculate_ema(data['Close'], ema_period)
    ema_trend = 'BULLISH' if current_price > ema_50 else 'BEARISH'
    
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
    
    return {
        'ema_50': ema_50,
        'ema_trend': ema_trend,
        'volatility_score': volatility_score,
        'sma_trend': sma_trend,
        'rsi': rsi
    }

def analyze_stock_strong_signals_only(ticker, lookback_bars=3, volume_days=20, momentum_days=5, ema_period=50, debug=False):
    """
    Stock analysis with ONLY STRONG BUY/SELL signals
    STRONG BUY: inside_bar_data['breakout_signal'] == 'BULLISH_BREAKOUT' and advanced['ema_trend'] == 'BULLISH'
    STRONG SELL: inside_bar_data['breakout_signal'] == 'BEARISH_BREAKOUT' and advanced['ema_trend'] == 'BEARISH'
    """
    try:
        # Get sector information
        sector = get_sector_for_ticker(ticker)
        
        if debug:
            print(f"Analyzing {ticker} (STRONG Signals Only) - Sector: {sector}...")
        
        # Initialize variables with safe defaults
        volume_analysis = {'volume_strength': 'NORMAL', 'volume_trend': 'NEUTRAL', 'volume_sma_ratio': 1.0}
        advanced = {
            'ema_50': 0,
            'ema_trend': 'NEUTRAL',
            'volatility_score': 0,
            'sma_trend': 0,
            'rsi': 50
        }
        
        # Get data
        data = get_stock_data(ticker, max(lookback_bars + 10, volume_days + 10))
        if data is None:
            return None
        
        if debug:
            print(f"   Data: {len(data)} trading days available")
        
        # Detect Inside Bar patterns
        inside_bar_data = detect_inside_bar(data, lookback_bars)
        
        # Get latest values
        latest = data.iloc[-1]
        current_price = latest['Close']
        current_volume = latest['Volume']
        
        # Calculate metrics using proper trading days
        volume_ratio, momentum, trading_days_used = calculate_proper_metrics(
            data, volume_days, momentum_days
        )
        
        # Enhanced volume confirmation
        try:
            volume_analysis = enhanced_volume_confirmation(data, current_volume, volume_days)
        except Exception as e:
            if debug:
                print(f"   DEBUG: Volume analysis error: {e}")
            volume_analysis = {'volume_strength': 'NORMAL', 'volume_trend': 'NEUTRAL', 'volume_sma_ratio': 1.0}
        
        # Calculate advanced signals with EMA
        try:
            advanced = calculate_advanced_signals(data, current_price, ema_period)
        except Exception as e:
            if debug:
                print(f"   DEBUG: Advanced analysis error: {e}")
        
        if debug:
            print(f"   Inside Bar Type: {inside_bar_data['inside_bar_type']}")
            print(f"   Breakout Signal: {inside_bar_data['breakout_signal']}")
            print(f"   EMA Trend: {advanced['ema_trend']}")
            print(f"   Checking STRONG BUY: {inside_bar_data['inside_bar_type'] == 'BULLISH'} AND {inside_bar_data['breakout_signal'] == 'BULLISH_BREAKOUT'} AND {advanced['ema_trend'] == 'BULLISH'}")
            print(f"   Checking STRONG SELL: {inside_bar_data['inside_bar_type'] == 'BEARISH'} AND {inside_bar_data['breakout_signal'] == 'BEARISH_BREAKOUT'} AND {advanced['ema_trend'] == 'BEARISH'}")
        
        # STRICT FILTERING - ONLY STRONG SIGNALS WITH MATCHING INSIDE BAR TYPE
        signal_type = 'NO_SIGNAL'
        buy_strength = 0
        sell_strength = 0
        stop_loss = current_price
        target_price = current_price
        
        # STRONG BUY: BULLISH inside bar + BULLISH breakout + BULLISH EMA (ALL MUST MATCH)
        if (inside_bar_data['inside_bar_type'] == 'BULLISH' and
            inside_bar_data['breakout_signal'] == 'BULLISH_BREAKOUT' and 
            advanced['ema_trend'] == 'BULLISH'):
            signal_type = 'STRONG_BUY'
            buy_strength = ((current_price - inside_bar_data['mother_bar_high']) / inside_bar_data['mother_bar_high']) * 100
            stop_loss = inside_bar_data['mother_bar_low']
            target_price = current_price + (current_price - stop_loss) * 2  # 2:1 R/R
            
        # STRONG SELL: BEARISH inside bar + BEARISH breakout + BEARISH EMA (ALL MUST MATCH)
        elif (inside_bar_data['inside_bar_type'] == 'BEARISH' and
              inside_bar_data['breakout_signal'] == 'BEARISH_BREAKOUT' and 
              advanced['ema_trend'] == 'BEARISH'):
            signal_type = 'STRONG_SELL'
            sell_strength = ((inside_bar_data['mother_bar_low'] - current_price) / inside_bar_data['mother_bar_low']) * 100
            stop_loss = inside_bar_data['mother_bar_high']
            target_price = current_price - (stop_loss - current_price) * 2  # 2:1 R/R
        
        # If no strong signal found, return None (don't include in results)
        if signal_type == 'NO_SIGNAL':
            return None
        
        # Risk management and position sizing for strong signals only
        if signal_type == 'STRONG_BUY':
            risk_per_share = current_price - stop_loss
        else:  # STRONG_SELL
            risk_per_share = stop_loss - current_price
        
        # Position sizing (1% risk on 100k capital)
        capital = 100000
        risk_amount = capital * 0.01
        position_size = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
        
        result = {
            'ticker': ticker,
            'sector': sector,
            'signal_type': signal_type,
            'current_price': float(current_price),
            'target_price': float(target_price),
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
            'lookback_bars': int(lookback_bars),
            'ema_50': float(advanced.get('ema_50', 0)),
            'ema_trend': advanced.get('ema_trend', 'NEUTRAL'),
            'volatility_score': float(advanced.get('volatility_score', 0)),
            'sma_trend': float(advanced.get('sma_trend', 0)),
            'rsi': float(advanced.get('rsi', 50)),
            'inside_bar_data': inside_bar_data
        }
        
        if debug:
            print(f"   Signal: {signal_type}")
        
        return result
        
    except Exception as e:
        if debug:
            print(f"Error analyzing {ticker}: {e}")
        return None

def analyze_all_stocks_strong_only(lookback_bars=3, volume_days=20, momentum_days=5, ema_period=50, max_workers=3, debug=False):
    """Analyze all stocks for STRONG signals only"""
    
    # Get tickers from config
    tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
    
    print(f"\nSTRONG SIGNALS ONLY - INSIDE BAR ANALYSIS")
    print(f"STRONG BUY: BULLISH inside bar + BULLISH breakout + BULLISH EMA")
    print(f"STRONG SELL: BEARISH inside bar + BEARISH breakout + BEARISH EMA")
    print(f"Analyzing {len(tickers)} stocks")
    print(f"Inside Bar Lookback: {lookback_bars} bars")
    print(f"Volume Period: {volume_days} trading days")
    print(f"EMA Period: {ema_period} days")
    print("="*70)
    
    all_signals = []
    
    # Analyze stocks
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(analyze_stock_strong_signals_only, ticker, lookback_bars, volume_days, momentum_days, ema_period, debug): ticker 
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
                if result:  # Only add if it's a strong signal
                    all_signals.append(result)
                    successful += 1
                    print(f"{ticker} ({completed}/{len(tickers)}) - {result['signal_type']} - {result['sector']}")
                else:
                    # No strong signal found
                    if debug:
                        print(f"{ticker} ({completed}/{len(tickers)}) - No strong signal")
            except concurrent.futures.TimeoutError:
                failed += 1
                print(f"{ticker} ({completed}/{len(tickers)}) - Timeout")
            except Exception as e:
                failed += 1
                print(f"{ticker} ({completed}/{len(tickers)}) - Error: {str(e)[:50]}")
        
        print(f"\nSTRONG SIGNALS ANALYSIS SUMMARY:")
        print(f"   Strong signals found: {successful}")
        print(f"   No strong signals: {len(tickers) - successful - failed}")
        print(f"   Failed: {failed}")
        print(f"   Total strong signals: {len(all_signals)}")
    
    return all_signals

def display_strong_signals(all_signals):
    """Display only strong signals"""
    
    if not all_signals:
        print(f"\nNo STRONG signals found!")
        print(f"STRONG BUY requires: BULLISH_BREAKOUT + BULLISH_EMA")
        print(f"STRONG SELL requires: BEARISH_BREAKOUT + BEARISH_EMA")
        return
    
    # Separate strong buy and sell signals
    strong_buy_signals = [s for s in all_signals if s['signal_type'] == 'STRONG_BUY']
    strong_sell_signals = [s for s in all_signals if s['signal_type'] == 'STRONG_SELL']
    
    # Sort by strength
    strong_buy_signals.sort(key=lambda x: x['buy_strength'], reverse=True)
    strong_sell_signals.sort(key=lambda x: x['sell_strength'], reverse=True)
    
    print(f"\n{'='*100}")
    print(f"STRONG SIGNALS ONLY - INSIDE BAR + EMA STRATEGY")
    print(f"Found {len(strong_buy_signals)} STRONG BUY and {len(strong_sell_signals)} STRONG SELL signals")
    print(f"{'='*100}")
    
    # Display STRONG BUY signals
    if strong_buy_signals:
        print(f"\nSTRONG BUY SIGNALS ({len(strong_buy_signals)} found)")
        print("="*90)
        
        table_data = []
        headers = ['#', 'Ticker', 'Sector', 'Price', 'Target', 'Stop Loss', 'Strength%', 
                  'Volume', 'RSI', 'EMA Trend', 'Momentum%', 'Qty']
        
        for i, signal in enumerate(strong_buy_signals, 1):
            table_data.append([
                i,
                signal['ticker'],
                signal['sector'],
                f"Rs{signal['current_price']:.2f}",
                f"Rs{signal['target_price']:.2f}",
                f"Rs{signal['stop_loss']:.2f}",
                f"{signal['buy_strength']:.2f}%",
                f"{signal['volume_ratio']:.1f}x",
                f"{signal['rsi']:.0f}",
                signal['ema_trend'],
                f"{signal['momentum']:+.1f}%",
                signal['position_size']
            ])
        
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Display STRONG SELL signals
    if strong_sell_signals:
        print(f"\nSTRONG SELL SIGNALS ({len(strong_sell_signals)} found)")
        print("="*90)
        
        table_data = []
        headers = ['#', 'Ticker', 'Sector', 'Price', 'Target', 'Stop Loss', 'Strength%', 
                  'Volume', 'RSI', 'EMA Trend', 'Momentum%', 'Qty']
        
        for i, signal in enumerate(strong_sell_signals, 1):
            table_data.append([
                i,
                signal['ticker'],
                signal['sector'],
                f"Rs{signal['current_price']:.2f}",
                f"Rs{signal['target_price']:.2f}",
                f"Rs{signal['stop_loss']:.2f}",
                f"{signal['sell_strength']:.2f}%",
                f"{signal['volume_ratio']:.1f}x",
                f"{signal['rsi']:.0f}",
                signal['ema_trend'],
                f"{signal['momentum']:+.1f}%",
                signal['position_size']
            ])
        
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Summary by sector
    sector_counts = {}
    for signal in all_signals:
        sector = signal['sector']
        signal_type = signal['signal_type']
        if sector not in sector_counts:
            sector_counts[sector] = {'STRONG_BUY': 0, 'STRONG_SELL': 0}
        sector_counts[sector][signal_type] += 1
    
    print(f"\nSTRONG SIGNALS BY SECTOR:")
    for sector, counts in sorted(sector_counts.items()):
        total = counts['STRONG_BUY'] + counts['STRONG_SELL']
        print(f"   {sector}: {counts['STRONG_BUY']} BUY, {counts['STRONG_SELL']} SELL (Total: {total})")

def main():
    """Main function for strong signals only analysis"""
    parser = argparse.ArgumentParser(description="STRONG Signals Only - Inside Bar Strategy Analyzer")
    
    parser.add_argument('--bars', type=int, default=3, 
                       help='Inside bar lookback bars (default: 3)')
    parser.add_argument('--volume-days', type=int, default=20, 
                       help='Volume average days (default: 20)')
    parser.add_argument('--momentum-days', type=int, default=5, 
                       help='Momentum calculation days (default: 5)')
    parser.add_argument('--ema-period', type=int, default=50, 
                       help='EMA period for trend filter (default: 50)')
    parser.add_argument('--workers', type=int, default=3, 
                       help='Max concurrent workers (default: 3)')
    parser.add_argument('--test-single', type=str, 
                       help='Test analysis on a single ticker for debugging')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug output for troubleshooting')
    
    args = parser.parse_args()
    
    # Test single ticker if requested
    if args.test_single:
        print(f"TESTING SINGLE TICKER: {args.test_single}")
        print("="*50)
        result = analyze_stock_strong_signals_only(
            args.test_single, 
            args.bars, 
            args.volume_days, 
            args.momentum_days, 
            args.ema_period,
            debug=True
        )
        if result:
            print(f"\nSTRONG SIGNAL FOUND: {result['signal_type']}")
            print(f"Sector: {result['sector']}")
            print(f"Breakout: {result['inside_bar_data']['breakout_signal']}")
            print(f"EMA Trend: {result['ema_trend']}")
            print(f"Strength: {result['buy_strength'] if result['signal_type'] == 'STRONG_BUY' else result['sell_strength']:.2f}%")
        else:
            print(f"\nNo STRONG signal for {args.test_single}")
            print("Requirements: BULLISH_BREAKOUT + BULLISH_EMA or BEARISH_BREAKOUT + BEARISH_EMA")
        return
    
    print("STRONG SIGNALS ONLY - INSIDE BAR STRATEGY ANALYZER")
    print("NO long entry, short entry, or weak signals - ONLY strong signals")
    print("="*60)
    print(f"STRONG BUY: BULLISH inside bar + BULLISH breakout + BULLISH EMA")
    print(f"STRONG SELL: BEARISH inside bar + BEARISH breakout + BEARISH EMA")
    print(f"Inside Bar Lookback: {args.bars} bars")
    print(f"Volume Period: {args.volume_days} trading days") 
    print(f"EMA Period: {args.ema_period} days")
    print(f"Workers: {args.workers}")
    print("="*60)
    
    # Analyze all stocks for strong signals only
    all_signals = analyze_all_stocks_strong_only(
        lookback_bars=args.bars,
        volume_days=args.volume_days, 
        momentum_days=args.momentum_days,
        ema_period=args.ema_period,
        max_workers=args.workers,
        debug=args.debug
    )
    
    if not all_signals:
        print("\nNo STRONG signals found!")
        print("\nREQUIREMENTS FOR STRONG SIGNALS:")
        print("   STRONG BUY: Inside bar + BULLISH_BREAKOUT + price > EMA")
        print("   STRONG SELL: Inside bar + BEARISH_BREAKOUT + price < EMA")
        print("\nTROUBLESHOOTING:")
        print("   Try shorter lookback: --bars 2")
        print("   Test single stock: --test-single RELIANCE --debug")
        return
    
    # Display strong signals
    display_strong_signals(all_signals)
    
    # Save results
    df = pd.DataFrame(all_signals)
    df.to_csv("strong_signals_only.csv", index=False)
    print(f"\nSaved {len(all_signals)} strong signals to strong_signals_only.csv")
    
    print(f"\nAnalysis Complete!")
    print(f"\nSIGNAL CRITERIA:")
    print(f"   STRONG BUY: Inside bar + BULLISH_BREAKOUT + BULLISH_EMA")
    print(f"   STRONG SELL: Inside bar + BEARISH_BREAKOUT + BEARISH_EMA")
    print(f"   All weak signals filtered out")

if __name__ == "__main__":
    main()