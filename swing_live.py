#!/usr/bin/env python
# live_comprehensive_trading_fixed.py - Live Multi-Indicator Trading System for Indian Market

import os
import sys
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta, time as dt_time
import warnings
import concurrent.futures
import argparse
from tabulate import tabulate
import json
import logging
from dataclasses import dataclass
import time
import pytz

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Configuration
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from app import config
    print("Successfully loaded config with tickers")
except ImportError:
    print("Config not found! Using default tickers")
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

def get_sector_for_ticker(ticker):
    try:
        for stock in config.TOP_STOCKS:
            if stock['symbol'].replace('.NS', '') == ticker.replace('.NS', ''):
                return stock.get('sector', 'Unknown')
        return 'Unknown'
    except:
        return 'Unknown'

@dataclass
class TradingPosition:
    ticker: str
    position_type: str  # 'long', 'short', 'none'
    entry_price: float
    entry_time: datetime
    current_price: float
    stop_loss: float
    target_price: float
    position_size: float = 1.0
    unrealized_pnl: float = 0.0
    signal_strength: float = 0.0

class PositionManager:
    def __init__(self):
        self.positions = {}  # ticker -> TradingPosition
        self.position_history = []
        self.all_positions_tracking = []
        
    def enter_position(self, ticker, position_type, entry_price, stop_loss, target_price, signal_strength=0):
        if ticker in self.positions:
            self.close_position(ticker, entry_price, f"New {position_type} signal")
            
        position = TradingPosition(
            ticker=ticker,
            position_type=position_type,
            entry_price=entry_price,
            entry_time=datetime.now(),
            current_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price,
            signal_strength=signal_strength
        )
        
        self.positions[ticker] = position
        
        # Track this position for ongoing monitoring
        self.all_positions_tracking.append({
            'ticker': ticker,
            'position_type': position_type,
            'entry_price': entry_price,
            'entry_time': datetime.now(),
            'status': 'ACTIVE',
            'signal_strength': signal_strength
        })
        
        logger.info(f"ENTERED {position_type.upper()} position for {ticker} at Rs{entry_price:.2f} (Strength: {signal_strength:.2f})")
        
    def close_position(self, ticker, exit_price, reason):
        if ticker not in self.positions:
            return
            
        position = self.positions[ticker]
        
        if position.position_type == 'long':
            pnl = (exit_price - position.entry_price) * position.position_size
        else:
            pnl = (position.entry_price - exit_price) * position.position_size
            
        self.position_history.append({
            'ticker': ticker,
            'position_type': position.position_type,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'entry_time': position.entry_time,
            'exit_time': datetime.now(),
            'pnl': pnl,
            'reason': reason,
            'signal_strength': position.signal_strength
        })
        
        # Update tracking status
        for pos in self.all_positions_tracking:
            if pos['ticker'] == ticker and pos['status'] == 'ACTIVE':
                pos['status'] = 'CLOSED'
                pos['exit_price'] = exit_price
                pos['exit_time'] = datetime.now()
                pos['pnl'] = pnl
                pos['reason'] = reason
                break
        
        logger.info(f"CLOSED {position.position_type.upper()} position for {ticker} at Rs{exit_price:.2f} | PnL: Rs{pnl:.2f} | Reason: {reason}")
        
        del self.positions[ticker]
        
    def update_position_prices(self, ticker, current_price):
        if ticker not in self.positions:
            return False
            
        position = self.positions[ticker]
        position.current_price = current_price
        
        # Calculate unrealized PnL
        if position.position_type == 'long':
            position.unrealized_pnl = (current_price - position.entry_price) * position.position_size
            if current_price <= position.stop_loss:
                self.close_position(ticker, current_price, "Stop Loss Hit")
                return True
            elif current_price >= position.target_price:
                self.close_position(ticker, current_price, "Target Reached")
                return True
        else:
            position.unrealized_pnl = (position.entry_price - current_price) * position.position_size
            if current_price >= position.stop_loss:
                self.close_position(ticker, current_price, "Stop Loss Hit")
                return True
            elif current_price <= position.target_price:
                self.close_position(ticker, current_price, "Target Reached")
                return True
                
        return False
    
    def get_position_direction_status(self, ticker, current_price):
        """Get position direction and status for reporting"""
        if ticker in self.positions:
            position = self.positions[ticker]
            if position.position_type == 'long':
                if current_price > position.entry_price:
                    return "PROFIT", f"+{((current_price/position.entry_price - 1) * 100):.1f}%"
                else:
                    return "LOSS", f"-{((1 - current_price/position.entry_price) * 100):.1f}%"
            else:  # short
                if current_price < position.entry_price:
                    return "PROFIT", f"+{((position.entry_price/current_price - 1) * 100):.1f}%"
                else:
                    return "LOSS", f"-{((current_price/position.entry_price - 1) * 100):.1f}%"
        return "NONE", "0%"

def get_live_price(ticker):
    """Get current live price from Yahoo Finance"""
    try:
        symbol = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
        stock = yf.Ticker(symbol)
        
        info = stock.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
        
        if current_price is None:
            hist = stock.history(period="1d", interval="1m")
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
                
        return float(current_price) if current_price else None
        
    except Exception as e:
        logger.error(f"Error getting live price for {ticker}: {e}")
        return None

def get_stock_data(ticker, interval="15m"):
    """Get stock data with proper error handling and period adjustment"""
    try:
        symbol = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
        stock = yf.Ticker(symbol)
        
        # Adjust period based on interval to get sufficient data
        if interval in ['1d', '1D']:
            period = "5y"  # 5 years for daily data
            min_bars = 100
        elif interval in ['1wk', '1W', '1w']:
            period = "10y"  # 10 years for weekly data  
            min_bars = 50
        elif interval in ['1h', '1H']:
            period = "3mo"  # 3 months for hourly data
            min_bars = 100
        elif interval in ['30m']:
            period = "2mo"  # 2 months for 30min data
            min_bars = 80
        else:  # 5m, 15m
            period = "2mo"  # 2 months for intraday
            min_bars = 50
        
        data = stock.history(period=period, interval=interval)
        
        if data.empty or len(data) < min_bars:
            logger.warning(f"Insufficient data for {ticker}: {len(data)} bars (need {min_bars})")
            return None
        
        data = data.dropna()
        return data if len(data) >= min_bars else None
        
    except Exception as e:
        logger.error(f"Error fetching data for {ticker} ({interval}): {e}")
        return None

def is_indian_trading_hours():
    """Check if current time is within Indian market hours"""
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    if now.weekday() > 4:  # Saturday = 5, Sunday = 6
        return False
        
    market_open = dt_time(9, 15)  # 9:15 AM
    market_close = dt_time(15, 30)  # 3:30 PM
    current_time = now.time()
    
    return market_open <= current_time <= market_close

# Technical Analysis Functions
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
            return {'macd': 0, 'signal': 0, 'histogram': 0, 'histogram_prev': 0}
        
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
            return {'squeeze_on': False, 'momentum_value': 0, 'momentum_prev': 0, 'momentum_color': 'neutral'}
        
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
        
        # Momentum calculation
        highest_high = data['High'].rolling(window=kc_length).max()
        lowest_low = data['Low'].rolling(window=kc_length).min()
        avg_hl = (highest_high + lowest_low) / 2
        avg_close = data['Close'].rolling(window=kc_length).mean()
        momentum_source = data['Close'] - (avg_hl + avg_close) / 2
        
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
            'momentum_color': momentum_color
        }
    except Exception as e:
        return {'squeeze_on': False, 'momentum_value': 0, 'momentum_prev': 0, 'momentum_color': 'neutral'}

def detect_live_trading_signals(data, current_price, debug=False):
    """
    Detect live trading signals using multi-indicator strategy
    Only return signals with at least 1% target potential
    """
    try:
        if len(data) < 50:
            return {
                'signal_type': 'HOLD',
                'signal_strength': 0,
                'stop_loss': current_price,
                'target_price': current_price,
                'entry_reason': 'Insufficient data',
                'target_percent': 0
            }
        
        # Calculate all indicators
        ema_200 = calculate_ema(data['Close'], 200)
        rsi = calculate_rsi(data['Close'], 5)  # Fast RSI
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
        
        # Signal conditions
        
        # Squeeze momentum signal (trend crossover)
        trend_buy_signal_sqz = (
            squeeze_data['momentum_value'] > 0 and squeeze_data['momentum_prev'] <= 0
        ) or (
            squeeze_data['momentum_value'] > 0 and 
            squeeze_data['momentum_value'] > squeeze_data['momentum_prev'] and 
            squeeze_data['momentum_prev'] < 0
        )
        
        trend_sell_signal_sqz = squeeze_data['momentum_value'] < 0 and squeeze_data['momentum_prev'] >= 0
        
        # MACD signal
        macd_buy_signal = (
            macd_data['histogram'] > macd_data['histogram_prev'] and
            data['Close'].iloc[-1] > data['Close'].iloc[-2] and
            macd_data['histogram'] < 0 and
            squeeze_data['momentum_value'] < 0 and
            data['Open'].iloc[-2] > ema_200  # Previous open above EMA
        )
        
        # RSI signals
        rsi_buy_signal = rsi < 30 and squeeze_data['momentum_value'] < 0 and bearish_trend
        rsi_sell_signal = rsi > 70 and squeeze_data['momentum_value'] > 0
        
        # Determine signal type and strength
        signal_type = 'HOLD'
        signal_strength = 0
        stop_loss = current_price
        target_price = current_price
        entry_reason = 'No signal'
        target_percent = 0
        
        # STRONG BUY: Squeeze momentum buy + bullish trend
        if trend_buy_signal_sqz and bullish_trend:
            signal_type = 'STRONG_BUY'
            signal_strength = abs(squeeze_data['momentum_value']) * 100
            stop_loss = long_stop_loss
            target_price = current_price + (current_price - stop_loss) * 2  # 2:1 R/R
            entry_reason = 'Squeeze momentum crossover + bullish trend'
            target_percent = ((target_price - current_price) / current_price) * 100
            
        # WEAK BUY: MACD signal + bullish trend
        elif macd_buy_signal and bullish_trend:
            signal_type = 'WEAK_BUY'
            signal_strength = abs(macd_data['histogram']) * 50
            stop_loss = long_stop_loss
            target_price = current_price + (current_price - stop_loss) * 1.5  # 1.5:1 R/R
            entry_reason = 'MACD histogram reversal + bullish trend'
            target_percent = ((target_price - current_price) / current_price) * 100
            
        # STRONG SELL: Squeeze momentum sell + bearish trend
        elif trend_sell_signal_sqz and bearish_trend:
            signal_type = 'STRONG_SELL'
            signal_strength = abs(squeeze_data['momentum_value']) * 100
            stop_loss = short_stop_loss
            target_price = current_price - (stop_loss - current_price) * 2  # 2:1 R/R
            entry_reason = 'Squeeze momentum crossunder + bearish trend'
            target_percent = ((current_price - target_price) / current_price) * 100
            
        # WEAK SELL: RSI overbought + momentum conditions
        elif rsi_sell_signal:
            signal_type = 'WEAK_SELL'
            signal_strength = (rsi - 70) * 2
            stop_loss = short_stop_loss
            target_price = current_price - (stop_loss - current_price) * 1.5  # 1.5:1 R/R
            entry_reason = 'RSI overbought + momentum conditions'
            target_percent = ((current_price - target_price) / current_price) * 100
        
        # RSI oversold buy signal
        elif rsi_buy_signal:
            signal_type = 'WEAK_BUY'
            signal_strength = (30 - rsi) * 2
            stop_loss = long_stop_loss
            target_price = current_price + (current_price - stop_loss) * 1.5  # 1.5:1 R/R
            entry_reason = 'RSI oversold + bearish momentum'
            target_percent = ((target_price - current_price) / current_price) * 100
        
        # FILTER: Only return signals with at least 1% target potential
        if signal_type != 'HOLD' and target_percent < 1.0:
            if debug:
                print(f"   DEBUG: Signal filtered out - Target only {target_percent:.2f}% (need min 1%)")
            signal_type = 'HOLD'
            signal_strength = 0
            entry_reason = f'Target too low ({target_percent:.2f}% < 1.0%)'
            target_percent = 0
        
        if debug:
            print(f"   DEBUG: EMA200: {ema_200:.2f}, Current: {current_price:.2f}")
            print(f"   DEBUG: RSI: {rsi:.1f}")
            print(f"   DEBUG: Target %: {target_percent:.2f}%")
            print(f"   DEBUG: Squeeze: {squeeze_data}")
            print(f"   DEBUG: MACD: {macd_data}")
            print(f"   DEBUG: Signals - SqzBuy: {trend_buy_signal_sqz}, MacdBuy: {macd_buy_signal}")
        
        return {
            'signal_type': signal_type,
            'signal_strength': float(signal_strength),
            'stop_loss': float(stop_loss),
            'target_price': float(target_price),
            'target_percent': float(target_percent),
            'entry_reason': entry_reason,
            'squeeze_data': squeeze_data,
            'macd_data': macd_data,
            'ema_200': ema_200,
            'rsi': rsi,
            'atr': atr,
            'bullish_trend': bullish_trend,
            'bearish_trend': bearish_trend
        }
        
    except Exception as e:
        if debug:
            print(f"   DEBUG: Signal detection error: {e}")
        return {
            'signal_type': 'HOLD',
            'signal_strength': 0,
            'stop_loss': current_price,
            'target_price': current_price,
            'target_percent': 0,
            'entry_reason': f'Error: {str(e)[:50]}'
        }

def analyze_stock_live_trading(ticker, interval="15m", position_manager=None, debug=False):
    """Analyze stock for live trading with position management"""
    try:
        sector = get_sector_for_ticker(ticker)
        
        # Use automatic period selection based on interval
        data = get_stock_data(ticker, interval=interval)
        if data is None:
            if debug:
                print(f"   {ticker}: No data available for {interval} interval")
            logger.warning(f"Insufficient data for {ticker}")
            return None
        
        # Get current price (live if possible for intraday, last close for daily+)
        current_price = data['Close'].iloc[-1]
        
        # Only get live price for intraday intervals
        if interval in ['5m', '15m', '30m', '1h']:
            live_price = get_live_price(ticker)
            if live_price:
                current_price = live_price
        else:
            live_price = None  # For daily/weekly, use last close
        
        # Update positions if position manager provided
        if position_manager:
            position_manager.update_position_prices(ticker, current_price)
        
        # Detect trading signals
        signal_data = detect_live_trading_signals(data, current_price, debug)
        
        # ONLY enter positions for STRONG signals (not WEAK)
        if position_manager and ticker not in position_manager.positions:
            if signal_data['signal_type'] == 'STRONG_BUY':
                position_manager.enter_position(
                    ticker, 'long', current_price, 
                    signal_data['stop_loss'], signal_data['target_price'],
                    signal_data['signal_strength']
                )
                logger.info(f"ENTERED LONG position for {ticker} - {signal_data['entry_reason']}")
            elif signal_data['signal_type'] == 'STRONG_SELL':
                position_manager.enter_position(
                    ticker, 'short', current_price,
                    signal_data['stop_loss'], signal_data['target_price'],
                    signal_data['signal_strength']
                )
                logger.info(f"ENTERED SHORT position for {ticker} - {signal_data['entry_reason']}")
        
        # Calculate volume metrics
        volume_lookback = min(20, len(data) - 1)
        if volume_lookback > 0:
            avg_volume = data['Volume'].rolling(volume_lookback).mean().iloc[-1]
            volume_ratio = data['Volume'].iloc[-1] / avg_volume if avg_volume > 0 else 1.0
        else:
            volume_ratio = 1.0
        
        position_info = None
        if position_manager and ticker in position_manager.positions:
            pos = position_manager.positions[ticker]
            position_info = {
                'position_type': pos.position_type,
                'entry_price': pos.entry_price,
                'current_price': pos.current_price,
                'stop_loss': pos.stop_loss,
                'target_price': pos.target_price,
                'unrealized_pnl': pos.unrealized_pnl,
                'entry_time': pos.entry_time,
                'signal_strength': pos.signal_strength
            }
        
        result = {
            'ticker': ticker,
            'sector': sector,
            'signal_type': signal_data['signal_type'],
            'signal_strength': signal_data['signal_strength'],
            'current_price': float(current_price),
            'live_price': live_price,
            'target_price': signal_data['target_price'],
            'stop_loss': signal_data['stop_loss'],
            'target_percent': signal_data.get('target_percent', 0),
            'entry_reason': signal_data['entry_reason'],
            'volume_ratio': float(volume_ratio),
            'rsi': signal_data['rsi'],
            'ema_200': signal_data['ema_200'],
            'trend_direction': 'BULLISH' if signal_data['bullish_trend'] else 'BEARISH',
            'squeeze_on': signal_data['squeeze_data']['squeeze_on'],
            'momentum_value': signal_data['squeeze_data']['momentum_value'],
            'macd_histogram': signal_data['macd_data']['histogram'],
            'atr': signal_data['atr'],
            'bars_analyzed': len(data),
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'position': position_info,
            'is_trading_hours': is_indian_trading_hours(),
            'interval': interval,
            'data_period': f"Last {len(data)} {interval} bars"
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing {ticker} ({interval}): {e}")
        return None

def analyze_all_stocks_live(interval="15m", position_manager=None, max_workers=4, debug=False):
    """Analyze all stocks for live trading"""
    if position_manager is None:
        position_manager = PositionManager()
    
    tickers = [stock['symbol'] for stock in config.TOP_STOCKS]
    logger.info(f"Live analysis of {len(tickers)} stocks with Multi-Indicator Strategy ({interval} intervals)...")
    
    all_signals = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(analyze_stock_live_trading, ticker, interval, position_manager, debug): ticker 
            for ticker in tickers
        }
        
        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                result = future.result(timeout=60)  # Longer timeout for all intervals
                if result:
                    all_signals.append(result)
                    logger.info(f"✓ {ticker}: {result['signal_type']} (Strength: {result['signal_strength']:.2f})")
                else:
                    logger.warning(f"✗ {ticker}: No signal generated")
            except Exception as e:
                logger.error(f"✗ {ticker}: {str(e)[:50]}")
    
    return all_signals, position_manager

def display_live_trading_results(all_signals, position_manager, cycle_number, interval="15m"):
    """Display live trading results with position tracking - STRONG signals only"""
    if not all_signals:
        print("\nNo signals found!")
        return
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    is_trading = is_indian_trading_hours()
    
    # Filter for STRONG signals only (we only trade these)
    strong_signals = [s for s in all_signals if s['signal_type'] in ['STRONG_BUY', 'STRONG_SELL']]
    
    print(f"\n{'='*180}")
    print(f"CYCLE #{cycle_number} - LIVE MULTI-INDICATOR TRADING SYSTEM ({interval} intervals)")
    print(f"Time: {current_time} | Market: {'OPEN' if is_trading else 'CLOSED'}")
    print(f"Strategy: Squeeze Momentum + EMA200 + RSI + MACD + ATR (STRONG SIGNALS ONLY)")
    print(f"{'='*180}")
    
    # Show active positions first if any exist
    if position_manager and position_manager.positions:
        print(f"\nACTIVE POSITIONS ({len(position_manager.positions)}):")
        print("-" * 150)
        pos_header = "{:<10} | {:<5} | {:<9} | {:<9} | {:<9} | {:<9} | {:<8} | {:<10} | {:<8} | {:<15}"
        print(pos_header.format(
            "Ticker", "Type", "Entry", "Current", "Stop", "Target", "PnL%", "Direction", "Strength", "Entry Time"
        ))
        print("-" * 150)
        
        for ticker, pos in position_manager.positions.items():
            direction, pnl_percent = position_manager.get_position_direction_status(ticker, pos.current_price)
            entry_time_str = pos.entry_time.strftime('%H:%M:%S')
            
            print(pos_header.format(
                ticker[:10],
                pos.position_type.upper(),
                f"Rs{pos.entry_price:.2f}",
                f"Rs{pos.current_price:.2f}",
                f"Rs{pos.stop_loss:.2f}",
                f"Rs{pos.target_price:.2f}",
                pnl_percent,
                direction,
                f"{pos.signal_strength:.1f}",
                entry_time_str
            ))
    
    # Show new STRONG signals
    if strong_signals:
        print(f"\nNEW STRONG SIGNALS FOUND ({len(strong_signals)}) - Min 1% Target:")
        print("-" * 200)
        header_format = "{:<10} | {:<8} | {:<12} | {:<9} | {:<9} | {:<9} | {:<7} | {:<8} | {:<4} | {:<7} | {:<5} | {:<5} | {:<7} | {:<15}"
        print(header_format.format(
            "Ticker", "Sector", "Signal", "Current", "Stop", "Target", "Tgt%", "Strength", "RSI", "Trend", "Vol", "Sqz", "MACD-H", "Timestamp"
        ))
        print("-" * 200)
        
        for result in strong_signals:
            squeeze_status = "ON" if result['squeeze_on'] else "OFF"
            
            print(header_format.format(
                result['ticker'][:10],
                result['sector'][:8],
                result['signal_type'][:12],
                f"Rs{result['current_price']:.2f}",
                f"Rs{result['stop_loss']:.2f}",
                f"Rs{result['target_price']:.2f}",
                f"{result['target_percent']:.1f}%",
                f"{result['signal_strength']:.1f}",
                f"{result['rsi']:.0f}",
                result['trend_direction'][:7],
                f"{result['volume_ratio']:.1f}x",
                squeeze_status,
                f"{result['macd_histogram']:.3f}",
                result['timestamp']
            ))
    else:
        print(f"\nNo NEW STRONG signals found with min 1% target in this cycle!")
        
        # Show debugging info for why no strong signals
        weak_signals = [s for s in all_signals if s['signal_type'] in ['WEAK_BUY', 'WEAK_SELL']]
        filtered_signals = [s for s in all_signals if 'Target too low' in s.get('entry_reason', '')]
        
        if weak_signals:
            print(f"Found {len(weak_signals)} WEAK signals (not traded):")
            for s in weak_signals[:3]:
                target_pct = s.get('target_percent', 0)
                if target_pct >= 1.0:
                    print(f"  {s['ticker']}: {s['signal_type']} - Target: {target_pct:.1f}% (Strength: {s['signal_strength']:.1f})")
        
        if filtered_signals:
            print(f"Found {len(filtered_signals)} signals filtered out due to <1% target:")
            for s in filtered_signals[:3]:
                target_pct = s.get('target_percent', 0)
                print(f"  {s['ticker']}: Target only {target_pct:.2f}%")
        
        hold_signals = [s for s in all_signals if s['signal_type'] == 'HOLD']
        if hold_signals:
            print(f"Found {len(hold_signals)} HOLD signals")
    
    # Show recent closed positions summary
    if position_manager and position_manager.position_history:
        recent_history = position_manager.position_history[-3:]  # Last 3 closed positions
        if recent_history:
            print(f"\nRECENT CLOSED POSITIONS ({len(recent_history)}):")
            print("-" * 120)
            hist_header = "{:<10} | {:<5} | {:<9} | {:<9} | {:<8} | {:<15} | {:<15}"
            print(hist_header.format(
                "Ticker", "Type", "Entry", "Exit", "PnL", "Reason", "Close Time"
            ))
            print("-" * 120)
            
            for hist in recent_history:
                close_time = hist['exit_time'].strftime('%H:%M:%S')
                print(hist_header.format(
                    hist['ticker'][:10],
                    hist['position_type'].upper(),
                    f"Rs{hist['entry_price']:.2f}",
                    f"Rs{hist['exit_price']:.2f}",
                    f"Rs{hist['pnl']:.2f}",
                    hist['reason'][:15],
                    close_time
                ))
    
    # Summary
    total_active = len(position_manager.positions) if position_manager else 0
    total_closed = len(position_manager.position_history) if position_manager else 0
    total_unrealized_pnl = sum([p.unrealized_pnl for p in position_manager.positions.values()]) if position_manager else 0
    
    print(f"\nCYCLE #{cycle_number} SUMMARY:")
    if strong_signals:
        strong_buy = len([s for s in strong_signals if s['signal_type'] == 'STRONG_BUY'])
        strong_sell = len([s for s in strong_signals if s['signal_type'] == 'STRONG_SELL'])
        print(f"   NEW STRONG SIGNALS: Buy: {strong_buy}, Sell: {strong_sell}")
    print(f"   Active Positions: {total_active} | Closed Positions: {total_closed}")
    print(f"   Total Unrealized PnL: Rs{total_unrealized_pnl:.2f}")
    print(f"   Market Status: {'TRADING' if is_trading else 'POST-MARKET'}")
    
    # Show next scan time differently for different intervals
    if interval in ['1d', '1w']:
        print(f"   Next analysis: Run manually when needed ({interval} analysis)")
    else:
        next_scan_minutes = int(interval.replace('m', '').replace('h', ''))
        if 'h' in interval:
            next_scan_minutes *= 60
        print(f"   Next scan: {(datetime.now() + timedelta(minutes=next_scan_minutes)).strftime('%H:%M:%S')}")
    
    return strong_signals

def run_live_trading_cycle(position_manager, cycle_number, interval="15m"):
    """Run one trading cycle"""
    logger.info(f"Running live trading cycle #{cycle_number} ({interval} intervals)...")
    
    # Analyze all stocks
    all_signals, updated_position_manager = analyze_all_stocks_live(interval, position_manager)
    
    # Display results
    strong_signals = display_live_trading_results(all_signals, updated_position_manager, cycle_number, interval)
    
    # Save cycle data
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    
    # Save all results
    if all_signals:
        df_all = pd.DataFrame(all_signals)
        df_all.to_csv(f"live_{interval}_cycle_{cycle_number}_all_signals_{timestamp}.csv", index=False)
    
    # Save strong signals only
    if strong_signals:
        df_strong = pd.DataFrame(strong_signals)
        df_strong.to_csv(f"live_{interval}_cycle_{cycle_number}_strong_signals_{timestamp}.csv", index=False)
    
    # Save position status
    if updated_position_manager.positions:
        positions_data = []
        for ticker, pos in updated_position_manager.positions.items():
            direction, pnl_percent = updated_position_manager.get_position_direction_status(ticker, pos.current_price)
            positions_data.append({
                'cycle': cycle_number,
                'ticker': ticker,
                'position_type': pos.position_type,
                'entry_price': pos.entry_price,
                'current_price': pos.current_price,
                'stop_loss': pos.stop_loss,
                'target_price': pos.target_price,
                'unrealized_pnl': pos.unrealized_pnl,
                'signal_strength': pos.signal_strength,
                'direction': direction,
                'pnl_percent': pnl_percent,
                'entry_time': pos.entry_time,
                'update_time': datetime.now()
            })
        
        df_positions = pd.DataFrame(positions_data)
        df_positions.to_csv(f"live_{interval}_cycle_{cycle_number}_positions_{timestamp}.csv", index=False)
    
    return updated_position_manager

def should_continue_trading():
    """Check if we should continue trading (within market hours)"""
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    # Don't trade on weekends
    if now.weekday() > 4:  # Saturday = 5, Sunday = 6
        return False
    
    # Market hours: 9:15 AM to 3:30 PM IST
    market_open = dt_time(9, 15)
    market_close = dt_time(15, 30)
    current_time = now.time()
    
    return market_open <= current_time <= market_close

def wait_for_next_cycle(interval_minutes=15):
    """Wait until the next interval - adjusted for different timeframes"""
    
    # For daily/weekly intervals, don't wait in live mode - just run once
    if interval_minutes >= 1440:  # 1 day = 1440 minutes
        logger.info("Daily/Weekly analysis complete. Run again manually for next analysis.")
        return
    
    now = datetime.now()
    
    # For hourly and above, wait for next hour boundary
    if interval_minutes >= 60:
        minutes_to_wait = 60 - now.minute
        seconds_to_wait = 60 - now.second
        total_seconds = (minutes_to_wait - 1) * 60 + seconds_to_wait
    else:
        # For intraday intervals (5m, 15m, 30m)
        minutes_to_wait = interval_minutes - (now.minute % interval_minutes)
        seconds_to_wait = 60 - now.second
        
        if minutes_to_wait == interval_minutes and seconds_to_wait == 60:
            return
        
        total_seconds = (minutes_to_wait - 1) * 60 + seconds_to_wait
    
    next_run = now + timedelta(seconds=total_seconds)
    logger.info(f"Waiting {total_seconds} seconds until next cycle at {next_run.strftime('%H:%M:%S')} ({interval_minutes}min intervals)")
    
    time.sleep(total_seconds)

def run_live_trading_session(interval="15m"):
    """Main trading session - behavior depends on timeframe"""
    
    # Parse interval to get minutes properly
    if interval.endswith('m'):
        interval_minutes = int(interval[:-1])
        is_intraday = True
    elif interval.endswith('h'):
        interval_minutes = int(interval[:-1]) * 60
        is_intraday = True
    elif interval.endswith('d'):
        interval_minutes = int(interval[:-1]) * 1440
        is_intraday = False
    elif interval.endswith('w'):
        interval_minutes = int(interval[:-1]) * 10080
        is_intraday = False
    else:
        interval_minutes = 15
        is_intraday = True
    
    print(f"\n{'='*80}")
    print(f"MULTI-INDICATOR TRADING SYSTEM STARTED")
    print(f"{'='*80}")
    print(f"Strategy: Squeeze Momentum + EMA200 + RSI + MACD + ATR")
    
    if is_intraday:
        print(f"Mode: LIVE TRADING - Every {interval_minutes} minutes during market hours")
        print(f"Schedule: 9:15 AM - 3:30 PM IST (Monday-Friday)")
    else:
        print(f"Mode: {interval.upper()} ANALYSIS - Run manually when needed")
        print(f"Data: Uses {interval} timeframe for position analysis")
    
    print(f"Signals: STRONG_BUY/SELL only (auto-enter positions)")
    print(f"Risk: ATR-based stop loss, min 1% target")
    print(f"Data: {interval} timeframe")
    print(f"{'='*80}")
    
    position_manager = PositionManager()
    cycle_number = 1
    
    # For daily/weekly analysis, just run once
    if not is_intraday:
        print(f"\nRunning {interval.upper()} analysis cycle...")
        position_manager = run_live_trading_cycle(position_manager, cycle_number, interval)
        
        print(f"\n{interval.upper()} ANALYSIS COMPLETE!")
        print(f"For continuous monitoring, use shorter timeframes (5m, 15m, 30m, 1h)")
        print(f"Re-run this command when you want fresh {interval} analysis")
        return
    
    # Check if market is open for intraday trading
    if not should_continue_trading():
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        print(f"Market is currently CLOSED")
        print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} IST")
        print(f"Market hours: 9:15 AM - 3:30 PM IST (Monday-Friday)")
        
        # Run one test cycle anyway
        print(f"\nRunning one test cycle with {interval} data...")
        position_manager = run_live_trading_cycle(position_manager, cycle_number, interval)
        return
    
    try:
        while should_continue_trading():
            cycle_start_time = datetime.now()
            print(f"\nStarting Cycle #{cycle_number} at {cycle_start_time.strftime('%H:%M:%S')} ({interval} intervals)")
            
            # Run trading cycle
            position_manager = run_live_trading_cycle(position_manager, cycle_number, interval)
            
            cycle_number += 1
            
            # Wait for next interval
            if should_continue_trading():
                wait_for_next_cycle(interval_minutes)
            
        # Market closed
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        print(f"\nMARKET CLOSED at {now.strftime('%H:%M:%S')} IST")
        print(f"Session completed after {cycle_number - 1} cycles ({interval} intervals)")
        
        # Final summary
        if position_manager.positions:
            print(f"\nFINAL POSITION SUMMARY:")
            total_unrealized = sum([p.unrealized_pnl for p in position_manager.positions.values()])
            print(f"   Active Positions: {len(position_manager.positions)}")
            print(f"   Total Unrealized PnL: Rs{total_unrealized:.2f}")
            
        if position_manager.position_history:
            total_realized = sum([h['pnl'] for h in position_manager.position_history])
            print(f"   Closed Positions: {len(position_manager.position_history)}")
            print(f"   Total Realized PnL: Rs{total_realized:.2f}")
            
            # Save final session report
            session_data = {
                'session_date': datetime.now().strftime('%Y-%m-%d'),
                'interval': interval,
                'total_cycles': cycle_number - 1,
                'active_positions': len(position_manager.positions),
                'closed_positions': len(position_manager.position_history),
                'total_unrealized_pnl': sum([p.unrealized_pnl for p in position_manager.positions.values()]),
                'total_realized_pnl': sum([h['pnl'] for h in position_manager.position_history]),
                'session_end_time': datetime.now()
            }
            
            with open(f"trading_session_{interval}_{datetime.now().strftime('%Y%m%d')}.json", 'w') as f:
                json.dump(session_data, f, indent=2, default=str)
        
    except KeyboardInterrupt:
        print(f"\nTrading session stopped by user")
        
        # Save interrupted session data
        if position_manager.position_history:
            history_df = pd.DataFrame(position_manager.position_history)
            history_df.to_csv(f"interrupted_session_{interval}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", index=False)
            print(f"Session data saved")
    
    except Exception as e:
        logger.error(f"Error in trading session: {e}")
        
        # Save error session data
        if position_manager.position_history:
            history_df = pd.DataFrame(position_manager.position_history)
            history_df.to_csv(f"error_session_{interval}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", index=False)
            print(f"Error session data saved")

def main():
    """Main function with live trading capabilities"""
    parser = argparse.ArgumentParser(description="Live Multi-Indicator Trading System for Indian Market")
    
    parser.add_argument('--live-trading', action='store_true', 
                       help='Start live trading session')
    parser.add_argument('--test-mode', action='store_true', 
                       help='Run single test cycle instead of live trading')
    parser.add_argument('--test-single', type=str, 
                       help='Test analysis on a single ticker for debugging')
    parser.add_argument('--interval', type=str, default='15m', 
                       choices=['5m', '15m', '30m', '1h', '1d', '1w'],
                       help='Trading interval: 5m, 15m, 30m, 1h, 1d, 1w (default: 15m)')
    parser.add_argument('--workers', type=int, default=4, 
                       help='Max concurrent workers (default: 4)')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug output for troubleshooting')
    
    args = parser.parse_args()
    
    if args.test_single:
        print(f"TESTING SINGLE TICKER: {args.test_single} ({args.interval} intervals)")
        print("="*60)
        result = analyze_stock_live_trading(args.test_single, args.interval, debug=True)
        if result:
            print(f"\nSUCCESS! Signal: {result['signal_type']}")
            print(f"Reason: {result['entry_reason']}")
            print(f"Strength: {result['signal_strength']:.2f}")
            print(f"Current Price: Rs{result['current_price']:.2f}")
            print(f"Stop Loss: Rs{result['stop_loss']:.2f}")
            print(f"Target: Rs{result['target_price']:.2f}")
            print(f"Target %: {result['target_percent']:.2f}%")
            print(f"RSI: {result['rsi']:.1f}")
            print(f"EMA200: Rs{result['ema_200']:.2f}")
            print(f"Trend: {result['trend_direction']}")
            print(f"Squeeze: {'ON' if result['squeeze_on'] else 'OFF'}")
            print(f"Data: {result['data_period']}")
        else:
            print(f"\nNo result for {args.test_single}")
        return
    
    elif args.live_trading:
        # Start live trading session
        print(f"Starting LIVE MULTI-INDICATOR TRADING SESSION ({args.interval} intervals)...")
        run_live_trading_session(args.interval)
        return
    
    elif args.test_mode:
        # Single test cycle
        print(f"MULTI-INDICATOR STRATEGY - TEST MODE ({args.interval} intervals)")
        print("STRONG SIGNALS ONLY - Auto-entry enabled")
        print("="*80)
        
        position_manager = PositionManager()
        all_signals, position_manager = analyze_all_stocks_live(
            args.interval, position_manager, args.workers, args.debug
        )
        
        if all_signals:
            strong_signals = display_live_trading_results(
                all_signals, position_manager, 1, args.interval
            )
            
            df = pd.DataFrame(all_signals)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            filename = f"test_mode_{args.interval}_{timestamp}.csv"
            df.to_csv(filename, index=False)
            print(f"\nTest results saved to: {filename}")
        else:
            print("No signals generated in test mode")
        return
    
    else:
        # Default: Show help and options
        print("LIVE MULTI-INDICATOR TRADING SYSTEM")
        print("Strategy: Squeeze Momentum + EMA200 + RSI + MACD + ATR")
        print("STRONG SIGNALS ONLY (Auto-entry enabled)")
        print("="*80)
        print("Available modes:")
        print("  --test-single TICKER    : Test single stock")
        print("  --test-mode            : Run one complete analysis cycle")
        print("  --live-trading         : Start live trading session")
        print("")
        print("Configuration options:")
        print("  --interval {5m,15m,30m,1h,1d,1w} : Trading interval (default: 15m)")
        print("  --workers N            : Max concurrent workers (default: 4)")
        print("  --debug               : Enable debug output")
        print("")
        print("Examples:")
        print(f"  python {sys.argv[0]} --live-trading --interval 15m")
        print(f"  python {sys.argv[0]} --live-trading --interval 1d")
        print(f"  python {sys.argv[0]} --test-mode --interval 30m --debug")
        print(f"  python {sys.argv[0]} --test-single RELIANCE --interval 1w --debug")
        print("")
        
        # Show current market status
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        is_trading = should_continue_trading()
        
        print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} IST")
        print(f"Market status: {'OPEN' if is_trading else 'CLOSED'}")
        print(f"Market hours: 9:15 AM - 3:30 PM IST (Monday-Friday)")
        print(f"Default interval: {args.interval}")
        
        if not is_trading:
            # Run a quick test anyway
            print(f"\nRunning quick test analysis ({args.interval} intervals)...")
            position_manager = PositionManager()
            all_signals, position_manager = analyze_all_stocks_live(
                args.interval, position_manager, 2, args.debug
            )
            
            if all_signals:
                display_live_trading_results(all_signals, position_manager, 1, args.interval)

if __name__ == "__main__":
    main()