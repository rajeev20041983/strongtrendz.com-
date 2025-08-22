#!/usr/bin/env python
# inside_bar_analyzer.py - Complete Inside Bar Strategy with Sector Information

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
            print(f"   {ticker}: Insufficient data ({len(data)} days)")
            return None
        
        # Clean data
        data = data.dropna()
        
        if len(data) < lookback_days + 5:
            print(f"   {ticker}: Insufficient clean data ({len(data)} days)")
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

def analyze_stock_comprehensive(ticker, lookback_bars=3, volume_days=20, momentum_days=5, ema_period=50, debug=False):
    """
    Comprehensive stock analysis with Inside Bar strategy including sector information
    """
    try:
        # Get sector information
        sector = get_sector_for_ticker(ticker)
        
        print(f"Analyzing {ticker} (Inside Bar Strategy) - Sector: {sector}...")
        
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
            if debug:
                print(f"   DEBUG: Volume analysis successful - {volume_analysis}")
        except Exception as e:
            if debug:
                print(f"   DEBUG: Volume analysis error: {e}")
            volume_analysis = {'volume_strength': 'NORMAL', 'volume_trend': 'NEUTRAL', 'volume_sma_ratio': 1.0}
        
        print(f"   Volume: Current {current_volume:,.0f} vs {volume_days}-day avg = {volume_ratio:.1f}x ({volume_analysis['volume_strength']})")
        print(f"   Momentum: {momentum:+.1f}% ({momentum_days} trading days)")
        
        # Calculate advanced signals with EMA
        try:
            advanced = calculate_advanced_signals(data, current_price, ema_period)
            if debug:
                print(f"   DEBUG: Advanced signals successful - RSI: {advanced['rsi']:.1f}, EMA Trend: {advanced['ema_trend']}")
            print(f"   RSI: {advanced['rsi']:.1f}")
            print(f"   EMA Trend: {advanced['ema_trend']} (Price vs {ema_period}-EMA: {current_price:.2f} vs {advanced['ema_50']:.2f})")
            
        except Exception as e:
            if debug:
                print(f"   DEBUG: Advanced analysis error: {e}")
            print(f"   RSI: {advanced['rsi']:.1f} (using defaults)")
        
        if debug:
            print(f"   DEBUG: Inside Bar Data - {inside_bar_data}")
        
        # Determine signal type and strength based on Inside Bar + EMA
        signal_type = 'HOLD'
        buy_strength = 0
        sell_strength = 0
        stop_loss = current_price
        target_price = current_price
        
        # Inside Bar Strategy Logic
        if inside_bar_data['has_inside_bar']:
            print(f"   Inside Bar: {inside_bar_data['inside_bar_type']} ({inside_bar_data['bars_since_inside']} bars ago)")
            print(f"   Breakout Status: {inside_bar_data['breakout_signal']}")
            
            # STRONG BUY: Bullish breakout above mother bar high + bullish EMA trend
            if (inside_bar_data['breakout_signal'] == 'BULLISH_BREAKOUT' and 
                advanced['ema_trend'] == 'BULLISH'):
                signal_type = 'STRONG_BUY'
                buy_strength = ((current_price - inside_bar_data['mother_bar_high']) / inside_bar_data['mother_bar_high']) * 100
                stop_loss = inside_bar_data['mother_bar_low']
                target_price = current_price + (current_price - stop_loss) * 2  # 2:1 R/R
                
            # WEAK BUY: Bullish breakout but bearish EMA trend, or pending bullish with strong bullish trend
            elif (inside_bar_data['breakout_signal'] == 'BULLISH_BREAKOUT' or 
                  (inside_bar_data['breakout_signal'] == 'PENDING' and 
                   inside_bar_data['inside_bar_type'] == 'BULLISH' and 
                   advanced['ema_trend'] == 'BULLISH')):
                signal_type = 'WEAK_BUY'
                buy_strength = ((current_price - inside_bar_data['mother_bar_low']) / inside_bar_data['mother_bar_low']) * 100 * 0.5
                stop_loss = inside_bar_data['mother_bar_low']
                target_price = inside_bar_data['mother_bar_high']
                
            # STRONG SELL: Bearish breakout below mother bar low + bearish EMA trend
            elif (inside_bar_data['breakout_signal'] == 'BEARISH_BREAKOUT' and 
                  advanced['ema_trend'] == 'BEARISH'):
                signal_type = 'STRONG_SELL'
                sell_strength = ((inside_bar_data['mother_bar_low'] - current_price) / inside_bar_data['mother_bar_low']) * 100
                stop_loss = inside_bar_data['mother_bar_high']
                target_price = current_price - (stop_loss - current_price) * 2  # 2:1 R/R
                
            # WEAK SELL: Bearish breakout but bullish EMA trend, or pending bearish with strong bearish trend
            elif (inside_bar_data['breakout_signal'] == 'BEARISH_BREAKOUT' or 
                  (inside_bar_data['breakout_signal'] == 'PENDING' and 
                   inside_bar_data['inside_bar_type'] == 'BEARISH' and 
                   advanced['ema_trend'] == 'BEARISH')):
                signal_type = 'WEAK_SELL'
                sell_strength = ((inside_bar_data['mother_bar_high'] - current_price) / inside_bar_data['mother_bar_high']) * 100 * 0.5
                stop_loss = inside_bar_data['mother_bar_high']
                target_price = inside_bar_data['mother_bar_low']
        
        # Risk management and position sizing
        if signal_type in ['STRONG_BUY', 'WEAK_BUY']:
            risk_per_share = current_price - stop_loss
        else:
            risk_per_share = stop_loss - current_price
        
        # Position sizing (1% risk on 100k capital)
        capital = 100000
        risk_amount = capital * 0.01
        position_size = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
        
        result = {
            'ticker': ticker,
            'sector': sector,  # Added sector information
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
        
        print(f"   Signal: {signal_type}")
        
        return result
        
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return None

def analyze_all_stocks(lookback_bars=3, volume_days=20, momentum_days=5, ema_period=50, max_workers=3, debug=False):
    """Analyze all stocks with Inside Bar strategy"""
    
    # Get tickers from config
    tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
    
    print(f"\nCOMPREHENSIVE INSIDE BAR ANALYSIS WITH SECTOR INFORMATION")
    print(f"Analyzing {len(tickers)} stocks")
    print(f"Inside Bar Lookback: {lookback_bars} bars")
    print(f"Volume Period: {volume_days} trading days")
    print(f"Momentum Period: {momentum_days} trading days")
    print(f"EMA Period: {ema_period} days")
    print("="*70)
    
    all_signals = []
    
    # Analyze stocks (reduced workers to avoid rate limits)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(analyze_stock_comprehensive, ticker, lookback_bars, volume_days, momentum_days, ema_period, debug): ticker 
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
                    print(f"{ticker} ({completed}/{len(tickers)}) - {result['signal_type']} - {result['sector']}")
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

def filter_signals_by_sector(all_signals, sector):
    """Filter signals by sector"""
    return [signal for signal in all_signals if signal['sector'].upper() == sector.upper()]

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
    """Display top N signals with sector information"""
    
    if not signals:
        print(f"\nNo {signal_title} signals found!")
        return
    
    # Signals should already be sorted by sort_signals_properly function
    signals = sort_signals_properly(signals)
    
    # Get top N
    top_signals = signals[:top_n]
    
    print(f"\nTOP {len(top_signals)} {signal_title} SIGNALS")
    print(f"Inside Bar + EMA Strategy with Sector Analysis")
    print("="*90)
    
    # Prepare table with sector column
    table_data = []
    headers = ['Rank', 'Ticker', 'Sector', 'Signal', 'Price', 'Target', 'Strength%', 
              'Volume', 'RSI', 'EMA Trend', 'Momentum%', 'Stop Loss', 'Qty']
    
    for i, signal in enumerate(top_signals, 1):
        target_price = signal['target_price']
        
        if 'BUY' in signal['signal_type']:
            strength = signal['buy_strength']
        else:
            strength = signal['sell_strength']
        
        # RSI interpretation
        try:
            rsi_value = signal.get('rsi', 50)
            rsi_display = f"{rsi_value:.0f}"
        except:
            rsi_display = "50"
        
        # Volume with strength indicator
        try:
            volume_strength = signal['volume_analysis']['volume_strength']
            volume_display = f"{signal['volume_ratio']:.1f}x"
        except:
            volume_display = f"{signal['volume_ratio']:.1f}x"
        
        # EMA trend display
        ema_trend = signal.get('ema_trend', 'NEUTRAL')
        
        table_data.append([
            i,
            signal['ticker'],
            signal['sector'],  # Added sector column
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
    
    # Sector-wise breakdown
    sector_counts = {}
    sector_strengths = {}
    
    for signal in top_signals:
        sector = signal['sector']
        if sector not in sector_counts:
            sector_counts[sector] = 0
            sector_strengths[sector] = []
        
        sector_counts[sector] += 1
        if 'BUY' in signal['signal_type']:
            sector_strengths[sector].append(signal['buy_strength'])
        else:
            sector_strengths[sector].append(signal['sell_strength'])
    
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
    
    print(f"\nSECTOR BREAKDOWN:")
    for sector, count in sorted(sector_counts.items(), key=lambda x: x[1], reverse=True):
        avg_sector_strength = sum(sector_strengths[sector]) / len(sector_strengths[sector])
        print(f"   {sector}: {count} signals (avg strength: {avg_sector_strength:.2f}%)")

def main():
    """Main function with comprehensive analysis"""
    parser = argparse.ArgumentParser(description="Comprehensive Inside Bar Strategy Analyzer with Sector Information")
    
    parser.add_argument('--bars', type=int, default=3, 
                       help='Inside bar lookback bars (default: 3)')
    parser.add_argument('--volume-days', type=int, default=20, 
                       help='Volume average days (default: 20)')
    parser.add_argument('--momentum-days', type=int, default=5, 
                       help='Momentum calculation days (default: 5)')
    parser.add_argument('--ema-period', type=int, default=50, 
                       help='EMA period for trend filter (default: 50)')
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
    parser.add_argument('--sector', type=str, 
                       help='Filter by specific sector (e.g., Banking, IT, FMCG)')
    
    args = parser.parse_args()
    
    # Test single ticker if requested
    if args.test_single:
        print(f"TESTING SINGLE TICKER: {args.test_single}")
        print("="*50)
        result = analyze_stock_comprehensive(
            args.test_single, 
            args.bars, 
            args.volume_days, 
            args.momentum_days, 
            args.ema_period,
            debug=True
        )
        if result:
            print(f"\nSUCCESS! Signal: {result['signal_type']}")
            print(f"Sector: {result['sector']}")
            print(f"Inside Bar Data: {result['inside_bar_data']}")
        else:
            print(f"\nNo result for {args.test_single}")
        return
    
    print("COMPREHENSIVE INSIDE BAR STRATEGY ANALYZER")
    print("Enhanced with Sector Information")
    print("="*60)
    print(f"Inside Bar Lookback: {args.bars} bars")
    print(f"Volume Period: {args.volume_days} trading days") 
    print(f"Momentum Period: {args.momentum_days} trading days")
    print(f"EMA Period: {args.ema_period} days")
    print(f"Top Signals: {args.top}")
    print(f"Workers: {args.workers}")
    if args.sector:
        print(f"Sector Filter: {args.sector}")
    print("="*60)
    
    # Set output directory
    output_dir = args.output or getattr(config, 'OUTPUT_DIR', 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Analyze all stocks
    all_signals = analyze_all_stocks(
        lookback_bars=args.bars,
        volume_days=args.volume_days, 
        momentum_days=args.momentum_days,
        ema_period=args.ema_period,
        max_workers=args.workers,
        debug=args.debug
    )
    
    if not all_signals:
        print("\nNo signals generated!")
        print("TROUBLESHOOTING TIPS:")
        print("   Try shorter lookback period: --bars 2")
        print("   Check if markets are open and data is available")
        print("   Enable debug mode: --debug")
        return
    
    # Filter by sector if requested
    if args.sector:
        sector_filtered = filter_signals_by_sector(all_signals, args.sector)
        if sector_filtered:
            all_signals = sector_filtered
            print(f"\nFiltered to {len(all_signals)} signals in {args.sector} sector")
        else:
            print(f"\nNo signals found in {args.sector} sector!")
            available_sectors = list(set([s['sector'] for s in all_signals]))
            print(f"Available sectors: {', '.join(available_sectors)}")
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
        
        # Overall sector breakdown
        if all_signals:
            all_sectors = {}
            for signal in all_signals:
                sector = signal['sector']
                if sector not in all_sectors:
                    all_sectors[sector] = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
                if 'BUY' in signal['signal_type']:
                    all_sectors[sector]['BUY'] += 1
                elif 'SELL' in signal['signal_type']:
                    all_sectors[sector]['SELL'] += 1
                else:
                    all_sectors[sector]['HOLD'] += 1
            
            print(f"\nSECTOR-WISE SIGNAL DISTRIBUTION:")
            for sector, counts in sorted(all_sectors.items()):
                total = sum(counts.values())
                print(f"   {sector}: {counts['BUY']} BUY, {counts['SELL']} SELL, {counts['HOLD']} HOLD (Total: {total})")
                
    else:
        # Default: Show BUY signals only
        buy_signals = filter_signals_by_type(all_signals, ['STRONG_BUY', 'WEAK_BUY'])
        buy_signals = sort_signals_properly(buy_signals) if buy_signals else []
        display_top_signals(buy_signals, "BUY", args.top)
    
    print(f"\nAnalysis Complete!")
    
    # Trading notes
    print(f"\nTRADING NOTES:")
    print(f"   STRONG BUY: Inside bar + bullish breakout + bullish EMA trend")
    print(f"   WEAK BUY: Inside bar + bullish bias or breakout without full trend confirmation")
    print(f"   STRONG SELL: Inside bar + bearish breakout + bearish EMA trend")
    print(f"   WEAK SELL: Inside bar + bearish bias or breakout without full trend confirmation")
    print(f"   STOP LOSS: Opposite end of inside bar range")
    print(f"   POSITION SIZE: 1% risk-based sizing")
    
    print(f"\nNEW SECTOR FEATURES:")
    print(f"   ✓ Sector information displayed for each stock")
    print(f"   ✓ Sector-wise signal breakdown and analysis")
    print(f"   ✓ Sector filtering: --sector Banking")
    print(f"   ✓ Average sector strength calculations")
    
    print(f"\nUSAGE EXAMPLES:")
    print(f"   python {sys.argv[0]} --test-single RELIANCE --debug")
    print(f"   python {sys.argv[0]} --sector Banking --buy-only")
    print(f"   python {sys.argv[0]} --sector IT --show-all")
    print(f"   python {sys.argv[0]} --bars 2 --debug")

if __name__ == "__main__":
    main()