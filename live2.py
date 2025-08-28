#!/usr/bin/env python
# complete_trading_system_inside_bar_optimized.py - Complete Optimized Trading System

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
from enum import Enum
import requests

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

# Enhanced Strategy Configuration with Inside Bar Strategy
@dataclass
class EnhancedStrategyConfig:
    # Strategy Selection (REPLACED breakout_mode with inside_bar_mode)
    inside_bar_mode: bool = True
    consecutive_mode: bool = False
    range_15m_mode: bool = False
    ma_cross_mode: bool = False
    macd_cross_mode: bool = False
    
    # Inside Bar Strategy Parameters
    inside_bar_n_bars: int = 1  # Number of inside bars (1-4)
    inside_bar_direction_filter: bool = False  # Only trade complete bull/bear patterns
    inside_bar_ma_filter: bool = True  # Use MA trend filter
    inside_bar_ma_length: int = 65  # MA length for trend filter
    
    # Confirmation Modes
    macd_confirm: bool = False
    rsi_confirm: bool = False
    ma_confirm: bool = False
    ichimoku_confirm: bool = False
    aroon_confirm: bool = False
    stoch_confirm: bool = False
    volume_confirm: bool = False
    bb_confirm: bool = False
    
    # TP/SL Modes
    swing_stop: bool = False
    atr_trailing: bool = True
    callback_trailing: bool = False
    percent_tpsl: bool = False
    
    # Strategy Parameters
    consecutive_bars_up: int = 3
    consecutive_bars_down: int = 3
    range_lookback: int = 2
    range_length: int = 10
    range_mult: float = 2.0
    
    # TP/SL Parameters
    tp_long_percent: float = 99999.0
    tp_short_percent: float = 33.3
    sl_percent: float = 2.5
    callback_percent: float = 25.0
    
    # MA Parameters
    fast_ma_length: int = 12
    slow_ma_length: int = 26
    fast_ma_type: str = 'EMA'
    slow_ma_type: str = 'EMA'
    
    # MACD Parameters
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    # RSI Parameters
    rsi_length: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    
    # Aroon Parameters
    aroon_length: int = 14
    
    # Stochastic Parameters
    stoch_k_length: int = 14
    stoch_d_length: int = 3
    stoch_overbought: float = 80.0
    stoch_oversold: float = 20.0
    
    # Volume Parameters
    volume_period: int = 20
    volume_threshold: float = 1.2
    
    # Bollinger Bands Parameters
    bb_length: int = 20
    bb_mult: float = 2.0

@dataclass
class TradingPosition:
    ticker: str
    position_type: str
    entry_price: float
    entry_time: datetime
    current_price: float
    stop_loss: float
    target_price: float
    position_size: float = 1.0
    unrealized_pnl: float = 0.0
    signal_strength: float = 0.0
    strategy_source: str = "unknown"

class PositionManager:
    def __init__(self):
        self.positions = {}
        self.position_history = []
        self.all_positions_tracking = []
        
    def enter_position(self, ticker, position_type, entry_price, stop_loss, target_price, signal_strength=0, strategy_source="unknown"):
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
            signal_strength=signal_strength,
            strategy_source=strategy_source
        )
        
        self.positions[ticker] = position
        logger.info(f"ENTERED {position_type.upper()} position for {ticker} at Rs{entry_price:.2f} (Strength: {signal_strength:.2f}) via {strategy_source}")
        
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
            'signal_strength': position.signal_strength,
            'strategy_source': position.strategy_source
        })
        
        logger.info(f"CLOSED {position.position_type.upper()} position for {ticker} at Rs{exit_price:.2f} | PnL: Rs{pnl:.2f} | Reason: {reason}")
        del self.positions[ticker]
        
    def update_position_prices(self, ticker, current_price):
        if ticker not in self.positions:
            return False
            
        position = self.positions[ticker]
        position.current_price = current_price
        
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
        if ticker in self.positions:
            position = self.positions[ticker]
            if position.position_type == 'long':
                if current_price > position.entry_price:
                    return "PROFIT", f"+{((current_price/position.entry_price - 1) * 100):.1f}%"
                else:
                    return "LOSS", f"-{((1 - current_price/position.entry_price) * 100):.1f}%"
            else:
                if current_price < position.entry_price:
                    return "PROFIT", f"+{((position.entry_price/current_price - 1) * 100):.1f}%"
                else:
                    return "LOSS", f"-{((current_price/position.entry_price - 1) * 100):.1f}%"
        return "NONE", "0%"

def get_live_price_from_nse(ticker):
    """Get current live price from NSE API"""
    try:
        clean_ticker = ticker.replace('.NS', '').upper()
        
        nse_urls = [
            f"https://www.nseindia.com/api/quote-equity?symbol={clean_ticker}",
            f"https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050&symbol={clean_ticker}"
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
        }
        
        for url in nse_urls:
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    
                    current_price = None
                    if 'priceInfo' in data and 'lastPrice' in data['priceInfo']:
                        current_price = float(data['priceInfo']['lastPrice'])
                    elif 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
                        if 'lastPrice' in data['data'][0]:
                            current_price = float(data['data'][0]['lastPrice'])
                    elif 'lastPrice' in data:
                        current_price = float(data['lastPrice'])
                    
                    if current_price and current_price > 0:
                        return current_price
                        
            except Exception:
                continue
        
        return None
        
    except Exception:
        return None

def get_live_price_from_yahoo(ticker):
    """Get current live price from Yahoo Finance (fallback)"""
    try:
        symbol = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
        stock = yf.Ticker(symbol)
        
        methods = [
            lambda: stock.info.get('currentPrice'),
            lambda: stock.info.get('regularMarketPrice'),
            lambda: stock.info.get('previousClose'),
            lambda: stock.history(period="1d", interval="1m")['Close'].iloc[-1] if not stock.history(period="1d", interval="1m").empty else None
        ]
        
        for method in methods:
            try:
                price = method()
                if price and price > 0:
                    return float(price)
            except:
                continue
                
        return None
        
    except Exception:
        return None

def get_live_price(ticker):
    """Get current live price - NSE first, then Yahoo Finance fallback"""
    try:
        nse_price = get_live_price_from_nse(ticker)
        if nse_price:
            return nse_price
        
        yahoo_price = get_live_price_from_yahoo(ticker)
        if yahoo_price:
            return yahoo_price
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting live price for {ticker}: {e}")
        return None

def get_stock_data(ticker, interval="15m"):
    """Get stock data with proper error handling"""
    try:
        symbol = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
        stock = yf.Ticker(symbol)
        
        if interval in ['1d', '1D']:
            period = "2y"
            min_bars = 100
        elif interval in ['1h', '1H']:
            period = "3mo"
            min_bars = 100
        elif interval in ['30m']:
            period = "3mo"
            min_bars = 100
        elif interval in ['15m']:
            period = "2mo"
            min_bars = 100
        else:  # 5m
            period = "1mo"
            min_bars = 100
        
        data = stock.history(period=period, interval=interval)
        
        if data.empty or len(data) < min_bars:
            if interval in ['5m', '15m', '30m']:
                fallback_periods = ["3mo", "6mo", "1y"]
                for fallback_period in fallback_periods:
                    try:
                        data = stock.history(period=fallback_period, interval=interval)
                        if len(data) >= min_bars:
                            break
                    except:
                        continue
        
        if data.empty or len(data) < 80:
            return None
            
        return data.dropna()
        
    except Exception as e:
        logger.error(f"Error fetching data for {ticker} ({interval}): {e}")
        return None

def is_indian_trading_hours():
    """Check if current time is within Indian market hours"""
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    if now.weekday() > 4:
        return False
        
    market_open = dt_time(9, 15)
    market_close = dt_time(15, 30)
    current_time = now.time()
    
    return market_open <= current_time <= market_close

def get_next_market_open():
    """Get the next market open time"""
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    # If it's a weekend or after market close, move to next trading day
    next_market = now.replace(hour=9, minute=15, second=0, microsecond=0)
    
    # If it's already past market close today, move to tomorrow
    if now.time() > dt_time(15, 30):
        next_market += timedelta(days=1)
    
    # Skip weekends
    while next_market.weekday() > 4:  # 5=Saturday, 6=Sunday
        next_market += timedelta(days=1)
    
    return next_market

def wait_for_market_open():
    """Wait until market opens"""
    ist = pytz.timezone('Asia/Kolkata')
    next_market = get_next_market_open()
    now = datetime.now(ist)
    
    wait_time = (next_market - now).total_seconds()
    
    if wait_time > 0:
        print(f"\nMarket CLOSED | Current: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Next market opens: {next_market.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Waiting {wait_time/3600:.1f} hours for market to open...")
        
        # Sleep in chunks to allow for interruption
        sleep_chunk = 300  # 5 minutes
        while wait_time > 0:
            sleep_time = min(sleep_chunk, wait_time)
            time.sleep(sleep_time)
            wait_time -= sleep_time
            
            # Update time display every 30 minutes
            if wait_time % 1800 == 0 and wait_time > 0:
                now = datetime.now(ist)
                print(f"Still waiting... Current: {now.strftime('%H:%M:%S')} | Hours remaining: {wait_time/3600:.1f}")

# Technical Analysis Functions
def calculate_ma(prices, period, ma_type="EMA"):
    """Calculate different types of moving averages"""
    try:
        if len(prices) < period:
            return prices.mean() if len(prices) > 0 else 0
        
        if ma_type == "EMA":
            return prices.ewm(span=period).mean()
        elif ma_type == "SMA":
            return prices.rolling(window=period).mean()
        elif ma_type == "WMA":
            weights = np.arange(1, period + 1)
            return prices.rolling(window=period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)
        else:
            return prices.ewm(span=period).mean()
    except:
        return prices.ewm(span=period).mean() if len(prices) >= period else prices.mean()

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
        
        final_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
        return max(0, min(100, final_rsi))
    except:
        return 50

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

def calculate_macd(prices, fast_length=12, slow_length=26, signal_length=9):
    """Calculate MACD"""
    try:
        if len(prices) < slow_length + signal_length:
            return {'macd': 0, 'signal': 0, 'histogram': 0, 'cross_above': False, 'cross_below': False, 'bull_trend': False, 'bear_trend': False}
        
        fast_ema = prices.ewm(span=fast_length).mean()
        slow_ema = prices.ewm(span=slow_length).mean()
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=signal_length).mean()
        histogram = macd_line - signal_line
        
        cross_above = False
        cross_below = False
        if len(histogram) > 1:
            cross_above = histogram.iloc[-1] > 0 and histogram.iloc[-2] <= 0
            cross_below = histogram.iloc[-1] < 0 and histogram.iloc[-2] >= 0
        
        return {
            'macd': macd_line.iloc[-1] if not pd.isna(macd_line.iloc[-1]) else 0,
            'signal': signal_line.iloc[-1] if not pd.isna(signal_line.iloc[-1]) else 0,
            'histogram': histogram.iloc[-1] if not pd.isna(histogram.iloc[-1]) else 0,
            'cross_above': cross_above,
            'cross_below': cross_below,
            'bull_trend': histogram.iloc[-1] > 0,
            'bear_trend': histogram.iloc[-1] < 0
        }
    except:
        return {'macd': 0, 'signal': 0, 'histogram': 0, 'cross_above': False, 'cross_below': False, 'bull_trend': False, 'bear_trend': False}

def calculate_aroon(data, period=14):
    """Calculate Aroon indicator"""
    try:
        if len(data) < period + 1:
            return {'aroon_up': 50, 'aroon_down': 50, 'cross_up': False, 'cross_down': False, 'bull_trend': False, 'bear_trend': False}
            
        aroon_up = ((period - data['High'].rolling(window=period).apply(lambda x: period - 1 - x.argmax())) / period) * 100
        aroon_down = ((period - data['Low'].rolling(window=period).apply(lambda x: period - 1 - x.argmin())) / period) * 100
        
        cross_up = False
        cross_down = False
        if len(aroon_up) > 1 and len(aroon_down) > 1:
            cross_up = aroon_up.iloc[-1] > aroon_down.iloc[-1] and aroon_up.iloc[-2] <= aroon_down.iloc[-2]
            cross_down = aroon_up.iloc[-1] < aroon_down.iloc[-1] and aroon_up.iloc[-2] >= aroon_down.iloc[-2]
        
        return {
            'aroon_up': aroon_up.iloc[-1] if not pd.isna(aroon_up.iloc[-1]) else 50,
            'aroon_down': aroon_down.iloc[-1] if not pd.isna(aroon_down.iloc[-1]) else 50,
            'cross_up': cross_up,
            'cross_down': cross_down,
            'bull_trend': aroon_up.iloc[-1] > aroon_down.iloc[-1],
            'bear_trend': aroon_up.iloc[-1] < aroon_down.iloc[-1]
        }
    except:
        return {'aroon_up': 50, 'aroon_down': 50, 'cross_up': False, 'cross_down': False, 'bull_trend': False, 'bear_trend': False}

def calculate_stochastic(data, k_length=14, d_length=3):
    """Calculate Stochastic Oscillator"""
    try:
        if len(data) < k_length + d_length:
            return {'stoch_k': 50, 'stoch_d': 50, 'cross_up': False, 'cross_down': False, 'bull_trend': False, 'bear_trend': False}
        
        high = data['High']
        low = data['Low'] 
        close = data['Close']
        
        lowest_low = low.rolling(window=k_length).min()
        highest_high = high.rolling(window=k_length).max()
        stoch_k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        stoch_d = stoch_k.rolling(window=d_length).mean()
        
        cross_up = False
        cross_down = False
        if len(stoch_k) > 1 and len(stoch_d) > 1:
            cross_up = stoch_k.iloc[-1] > stoch_d.iloc[-1] and stoch_k.iloc[-2] <= stoch_d.iloc[-2]
            cross_down = stoch_k.iloc[-1] < stoch_d.iloc[-1] and stoch_k.iloc[-2] >= stoch_d.iloc[-2]
        
        return {
            'stoch_k': stoch_k.iloc[-1] if not pd.isna(stoch_k.iloc[-1]) else 50,
            'stoch_d': stoch_d.iloc[-1] if not pd.isna(stoch_d.iloc[-1]) else 50,
            'cross_up': cross_up,
            'cross_down': cross_down,
            'bull_trend': stoch_k.iloc[-1] > stoch_d.iloc[-1],
            'bear_trend': stoch_k.iloc[-1] < stoch_d.iloc[-1]
        }
    except:
        return {'stoch_k': 50, 'stoch_d': 50, 'cross_up': False, 'cross_down': False, 'bull_trend': False, 'bear_trend': False}

def calculate_bollinger_bands(data, length=20, mult=2.0):
    """Calculate Bollinger Bands"""
    try:
        if len(data) < length:
            close = data['Close'].iloc[-1]
            return {'upper_band': close, 'middle_band': close, 'lower_band': close, 'squeeze': False, 'expansion': False}
        
        close = data['Close']
        middle_band = close.rolling(window=length).mean()
        std = close.rolling(window=length).std()
        upper_band = middle_band + (std * mult)
        lower_band = middle_band - (std * mult)
        
        current_width = upper_band.iloc[-1] - lower_band.iloc[-1]
        prev_width = upper_band.iloc[-2] - lower_band.iloc[-2] if len(upper_band) > 1 else current_width
        
        squeeze = current_width < prev_width * 0.95
        expansion = current_width > prev_width * 1.05
        
        return {
            'upper_band': upper_band.iloc[-1] if not pd.isna(upper_band.iloc[-1]) else close.iloc[-1],
            'middle_band': middle_band.iloc[-1] if not pd.isna(middle_band.iloc[-1]) else close.iloc[-1],
            'lower_band': lower_band.iloc[-1] if not pd.isna(lower_band.iloc[-1]) else close.iloc[-1],
            'squeeze': squeeze,
            'expansion': expansion,
            'near_upper': close.iloc[-1] > upper_band.iloc[-1] * 0.98,
            'near_lower': close.iloc[-1] < lower_band.iloc[-1] * 1.02
        }
    except:
        close = data['Close'].iloc[-1]
        return {'upper_band': close, 'middle_band': close, 'lower_band': close, 'squeeze': False, 'expansion': False}

def calculate_volume_confirmation(data, period=20, threshold=1.2):
    """Calculate Volume Confirmation"""
    try:
        if len(data) < period:
            return {'volume_ratio': 1.0, 'high_volume': False, 'above_avg': False}
        
        volume = data['Volume']
        avg_volume = volume.rolling(window=period).mean()
        current_volume = volume.iloc[-1]
        avg_vol = avg_volume.iloc[-1] if not pd.isna(avg_volume.iloc[-1]) else current_volume
        
        volume_ratio = current_volume / avg_vol if avg_vol > 0 else 1.0
        high_volume = volume_ratio >= threshold
        above_avg = volume_ratio > 1.0
        
        return {
            'volume_ratio': float(volume_ratio),
            'high_volume': high_volume,
            'above_avg': above_avg
        }
    except:
        return {'volume_ratio': 1.0, 'high_volume': False, 'above_avg': False}

def calculate_ichimoku(data, conversion_periods=9, base_periods=26, lagging_span2_periods=52, displacement=26):
    """Calculate Ichimoku Cloud indicators"""
    try:
        min_required = max(conversion_periods, base_periods, lagging_span2_periods) + displacement
        if len(data) < min_required:
            return {
                'conversion_line': 0,
                'base_line': 0,
                'lead_line1': 0,
                'lead_line2': 0,
                'lagging_span': 0,
                'long_condition': False,
                'short_condition': False,
                'cloud_color': 'neutral',
                'tenkan_kijun_cross_up': False,
                'tenkan_kijun_cross_down': False,
                'tenkan_above_kijun': False,
                'tenkan_below_kijun': False
            }
        
        high = data['High']
        low = data['Low']
        close = data['Close']
        open_price = data['Open']
        
        def donchian(length, series_high, series_low):
            highest = series_high.rolling(window=length).max()
            lowest = series_low.rolling(window=length).min()
            return (highest + lowest) / 2
        
        conversion_line = donchian(conversion_periods, high, low)
        base_line = donchian(base_periods, high, low)
        
        tenkan_kijun_cross_up = False
        tenkan_kijun_cross_down = False
        if len(conversion_line) > 1 and len(base_line) > 1:
            tenkan_kijun_cross_up = (conversion_line.iloc[-1] > base_line.iloc[-1] and 
                                   conversion_line.iloc[-2] <= base_line.iloc[-2])
            tenkan_kijun_cross_down = (conversion_line.iloc[-1] < base_line.iloc[-1] and 
                                     conversion_line.iloc[-2] >= base_line.iloc[-2])
        
        lead_line1 = ((conversion_line + base_line) / 2).shift(displacement)
        lead_line2 = donchian(lagging_span2_periods, high, low).shift(displacement)
        
        cloud_idx = max(-1-displacement, -len(data))
        
        try:
            current_conversion = conversion_line.iloc[-1]
            current_base = base_line.iloc[-1]
            current_lead1 = lead_line1.iloc[cloud_idx] if abs(cloud_idx) < len(lead_line1) else lead_line1.iloc[-1]
            current_lead2 = lead_line2.iloc[cloud_idx] if abs(cloud_idx) < len(lead_line2) else lead_line2.iloc[-1]
            current_price = close.iloc[-1]
            current_open = open_price.iloc[-1]
        except (IndexError, KeyError):
            current_conversion = conversion_line.dropna().iloc[-1] if not conversion_line.dropna().empty else 0
            current_base = base_line.dropna().iloc[-1] if not base_line.dropna().empty else 0
            current_lead1 = lead_line1.dropna().iloc[-1] if not lead_line1.dropna().empty else 0
            current_lead2 = lead_line2.dropna().iloc[-1] if not lead_line2.dropna().empty else 0
            current_price = close.iloc[-1]
            current_open = open_price.iloc[-1]
        
        lagging_idx = max(-displacement-1, -len(close))
        try:
            lagging_value = close.iloc[lagging_idx]
        except IndexError:
            lagging_value = close.iloc[0] if len(close) > 0 else current_price
        
        con_abv_base = current_conversion > current_base
        cloud_green = current_lead1 > current_lead2
        close_abv_cloud = current_open > current_lead1 and current_open > current_lead2
        lag_span_abv_cloud = lagging_value > current_lead1 and lagging_value > current_lead2
        
        long_condition = con_abv_base and cloud_green and close_abv_cloud and lag_span_abv_cloud
        
        con_blw_base = current_conversion < current_base
        cloud_red = current_lead2 > current_lead1
        close_blw_cloud = current_open < current_lead1 and current_open < current_lead2
        lag_span_blw_cloud = lagging_value < current_lead1 and lagging_value < current_lead2
        
        short_condition = con_blw_base and cloud_red and close_blw_cloud and lag_span_blw_cloud
        
        cloud_color = 'green' if cloud_green else 'red' if cloud_red else 'neutral'
        
        return {
            'conversion_line': float(current_conversion),
            'base_line': float(current_base),
            'lead_line1': float(current_lead1),
            'lead_line2': float(current_lead2),
            'lagging_span': float(lagging_value),
            'long_condition': bool(long_condition),
            'short_condition': bool(short_condition),
            'cloud_color': cloud_color,
            'tenkan_kijun_cross_up': tenkan_kijun_cross_up,
            'tenkan_kijun_cross_down': tenkan_kijun_cross_down,
            'tenkan_above_kijun': con_abv_base,
            'tenkan_below_kijun': con_blw_base
        }
        
    except Exception as e:
        logger.error(f"Error calculating Ichimoku: {e}")
        return {
            'conversion_line': 0,
            'base_line': 0,
            'lead_line1': 0,
            'lead_line2': 0,
            'lagging_span': 0,
            'long_condition': False,
            'short_condition': False,
            'cloud_color': 'neutral',
            'tenkan_kijun_cross_up': False,
            'tenkan_kijun_cross_down': False,
            'tenkan_above_kijun': False,
            'tenkan_below_kijun': False
        }

# Inside Bar Strategy Implementation - EXACT PINE SCRIPT REPLICATION
def calculate_inside_bar_strategy(data, n_bars=1, use_direction_filter=False, use_ma_filter=True, ma_length=65):
    """
    Calculate Inside Bar Strategy signals - EXACT PINE SCRIPT REPLICATION
    Entry: Breakout above/below inside bar range
    Stop: Opposite end of inside bar
    """
    try:
        if len(data) < max(n_bars + 2, ma_length + 10, 40):
            return {
                'inside_bar_long': False,
                'inside_bar_short': False,
                'inside_bar_detected': False,
                'ma_trend_up': False,
                'consecutive_bull_bars': 0,
                'consecutive_bear_bars': 0,
                'inside_bar_high': 0,
                'inside_bar_low': 0,
                'entry_price_long': 0,
                'entry_price_short': 0,
                'stop_loss_long': 0,
                'stop_loss_short': 0,
                'inside_bar_range': 0
            }
        
        high = data['High']
        low = data['Low']
        close = data['Close']
        open_price = data['Open']
        
        # Calculate moving average for trend filter
        if use_ma_filter:
            ma = close.rolling(window=ma_length).mean()
            ma_trend_up = close.iloc[-1] > ma.iloc[-1]
        else:
            ma_trend_up = True
        
        # Determine bullish/bearish bars
        bull_bar = close > open_price
        bear_bar = close < open_price
        
        # Calculate consecutive bars
        def bars_since_condition(condition_series):
            result = []
            count = 0
            for val in condition_series:
                if val:
                    count += 1
                else:
                    count = 0
                result.append(count)
            return pd.Series(result, index=condition_series.index)
        
        consecutive_bull_bars = bars_since_condition(bull_bar).iloc[-1]
        consecutive_bear_bars = bars_since_condition(bear_bar).iloc[-1]
        
        # Inside bar detection
        def detect_inside_bars(n_bars_param):
            current_idx = len(data) - 1
            
            if current_idx < n_bars_param:
                return False, 0, 0
            
            # Reference bar (the "mother bar")
            ref_idx = current_idx - n_bars_param
            ref_high = high.iloc[ref_idx]
            ref_low = low.iloc[ref_idx]
            
            # Check if subsequent bars are inside the reference bar
            for i in range(ref_idx + 1, current_idx + 1):
                current_high = high.iloc[i]
                current_low = low.iloc[i]
                
                if not (current_high < ref_high and current_low > ref_low):
                    return False, 0, 0
            
            return True, ref_high, ref_low
        
        inside_bar_detected, inside_bar_high, inside_bar_low = detect_inside_bars(n_bars)
        inside_bar_range = inside_bar_high - inside_bar_low if inside_bar_detected else 0
        
        # Current price (for breakout detection)
        current_price = close.iloc[-1]
        current_bull_bar = bull_bar.iloc[-1]
        current_bear_bar = bear_bar.iloc[-1]
        
        # PINE SCRIPT BREAKOUT LOGIC
        breakout_long = False
        breakout_short = False
        entry_price_long = 0
        entry_price_short = 0
        stop_loss_long = 0
        stop_loss_short = 0
        
        if inside_bar_detected:
            # LONG ENTRY: Price breaks ABOVE inside bar high
            if current_price > inside_bar_high:
                breakout_long = True
                entry_price_long = inside_bar_high  # Entry at breakout level
                stop_loss_long = inside_bar_low     # Stop at opposite end
            
            # SHORT ENTRY: Price breaks BELOW inside bar low
            elif current_price < inside_bar_low:
                breakout_short = True
                entry_price_short = inside_bar_low   # Entry at breakout level
                stop_loss_short = inside_bar_high    # Stop at opposite end
        
        # Direction filter conditions (if enabled)
        if use_direction_filter:
            cont_bull_condition = consecutive_bull_bars >= (n_bars + 1)
            cont_bear_condition = consecutive_bear_bars >= (n_bars + 1)
        else:
            cont_bull_condition = True
            cont_bear_condition = True
        
        # Entry conditions - PINE SCRIPT STYLE
        stability_condition = len(data) > 40
        
        # FINAL ENTRY DECISION
        bull_inside_bar = (stability_condition and 
                          inside_bar_detected and 
                          breakout_long and           # Must break above high
                          cont_bull_condition and
                          (ma_trend_up if use_ma_filter else True))
        
        bear_inside_bar = (stability_condition and 
                          inside_bar_detected and 
                          breakout_short and          # Must break below low
                          cont_bear_condition and
                          (not ma_trend_up if use_ma_filter else True))
        
        return {
            'inside_bar_long': bool(bull_inside_bar),
            'inside_bar_short': bool(bear_inside_bar),
            'inside_bar_detected': bool(inside_bar_detected),
            'ma_trend_up': bool(ma_trend_up),
            'consecutive_bull_bars': int(consecutive_bull_bars),
            'consecutive_bear_bars': int(consecutive_bear_bars),
            'current_bull_bar': bool(current_bull_bar),
            'current_bear_bar': bool(current_bear_bar),
            'n_bars_used': n_bars,
            # PINE SCRIPT SPECIFIC VALUES
            'inside_bar_high': float(inside_bar_high),
            'inside_bar_low': float(inside_bar_low),
            'entry_price_long': float(entry_price_long),
            'entry_price_short': float(entry_price_short),
            'stop_loss_long': float(stop_loss_long),
            'stop_loss_short': float(stop_loss_short),
            'inside_bar_range': float(inside_bar_range),
            'breakout_long': bool(breakout_long),
            'breakout_short': bool(breakout_short),
            'current_price': float(current_price)
        }
        
    except Exception as e:
        logger.error(f"Error calculating inside bar strategy: {e}")
        return {
            'inside_bar_long': False,
            'inside_bar_short': False,
            'inside_bar_detected': False,
            'ma_trend_up': False,
            'consecutive_bull_bars': 0,
            'consecutive_bear_bars': 0,
            'inside_bar_high': 0,
            'inside_bar_low': 0,
            'entry_price_long': 0,
            'entry_price_short': 0,
            'stop_loss_long': 0,
            'stop_loss_short': 0,
            'inside_bar_range': 0
        }

# Other Pine Script Strategies
def calculate_consecutive_bars(data, up_bars=3, down_bars=3):
    """Calculate Consecutive Bars signals"""
    try:
        if len(data) < max(up_bars, down_bars) + 1:
            return {'consecutive_up': False, 'consecutive_down': False, 'up_count': 0, 'down_count': 0}
        
        closes = data['Close']
        
        up_count = 0
        for i in range(1, min(up_bars + 1, len(closes))):
            if closes.iloc[-i] > closes.iloc[-i-1]:
                up_count += 1
            else:
                break
        
        down_count = 0
        for i in range(1, min(down_bars + 1, len(closes))):
            if closes.iloc[-i] < closes.iloc[-i-1]:
                down_count += 1
            else:
                break
        
        consecutive_up = up_count >= up_bars
        consecutive_down = down_count >= down_bars
        
        return {
            'consecutive_up': consecutive_up,
            'consecutive_down': consecutive_down,
            'up_count': up_count,
            'down_count': down_count
        }
    except:
        return {'consecutive_up': False, 'consecutive_down': False, 'up_count': 0, 'down_count': 0}

def calculate_range_breakout(data, lookback=2, length=10, mult=2.0):
    """Calculate Range Breakout signals"""
    try:
        if len(data) < length + lookback + 1:
            return {'range_breakout_long': False, 'range_breakout_short': False, 'range_condition': False}
        
        price_range = data['High'] - data['Low']
        range_std = price_range.rolling(window=length).std()
        range_mean = price_range.rolling(window=length).mean()
        
        computation = mult * range_std.iloc[-1] + range_mean.iloc[-1]
        current_range = price_range.iloc[-1]
        
        range_condition = current_range > computation
        
        current_close = data['Close'].iloc[-1]
        lookback_close = data['Close'].iloc[-lookback-1] if len(data) > lookback else current_close
        
        range_breakout_long = range_condition and current_close > lookback_close
        range_breakout_short = range_condition and current_close < lookback_close
        
        return {
            'range_breakout_long': range_breakout_long,
            'range_breakout_short': range_breakout_short,
            'range_condition': range_condition,
            'current_range': current_range,
            'threshold': computation
        }
    except:
        return {'range_breakout_long': False, 'range_breakout_short': False, 'range_condition': False}

def check_confirmations(config, macd_data, rsi, ma_trend, ichimoku_data, aroon_data, stoch_data, volume_data, bb_data, is_long_signal):
    """Check confirmation indicators based on configuration - LENIENT THRESHOLDS FOR 75% PASS RATE"""
    confirmations_passed = True
    
    if not any([config.macd_confirm, config.rsi_confirm, config.ma_confirm, 
                config.ichimoku_confirm, config.aroon_confirm, config.stoch_confirm,
                config.volume_confirm, config.bb_confirm]):
        return True
    
    # MACD Confirmation - LENIENT: Allow slightly negative MACD for longs, slightly positive for shorts
    if config.macd_confirm:
        if is_long_signal:
            confirmations_passed &= macd_data['histogram'] >= -0.5  # Allow small negative values
        else:
            confirmations_passed &= macd_data['histogram'] <= 0.5   # Allow small positive values
    
    # RSI Confirmation - LENIENT: Use 80/20 instead of 70/30
    if config.rsi_confirm:
        if is_long_signal:
            confirmations_passed &= rsi <= 80.0  # More lenient than 70
        else:
            confirmations_passed &= rsi >= 20.0  # More lenient than 30
    
    # MA Confirmation - LENIENT: Add small buffer for trend detection
    if config.ma_confirm:
        if is_long_signal:
            confirmations_passed &= ma_trend  # Keep as is - this is already ~50/50, hard to make more lenient
        else:
            confirmations_passed &= not ma_trend
    
    # Ichimoku Confirmation - LENIENT: Allow close values with small buffer
    if config.ichimoku_confirm:
        conversion_line = ichimoku_data['conversion_line']
        base_line = ichimoku_data['base_line']
        
        if is_long_signal:
            # Allow tenkan to be slightly below kijun (within 0.5%)
            confirmations_passed &= conversion_line >= base_line * 0.995
        else:
            # Allow tenkan to be slightly above kijun (within 0.5%)  
            confirmations_passed &= conversion_line <= base_line * 1.005
    
    # Aroon Confirmation - LENIENT: Reduce threshold from 10 to 5 point difference
    if config.aroon_confirm:
        aroon_up = aroon_data['aroon_up']
        aroon_down = aroon_data['aroon_down']
        
        if is_long_signal:
            confirmations_passed &= aroon_up > aroon_down - 5  # More lenient threshold
        else:
            confirmations_passed &= aroon_down > aroon_up - 5  # More lenient threshold
    
    # Stochastic Confirmation - LENIENT: Use 90/10 instead of 80/20
    if config.stoch_confirm:
        stoch_k = stoch_data.get('stoch_k', 50)
        if is_long_signal:
            confirmations_passed &= stoch_k <= 90.0  # More lenient overbought
        else:
            confirmations_passed &= stoch_k >= 10.0  # More lenient oversold
    
    # Volume Confirmation - LENIENT: Reduce threshold from 1.2x to 1.0x (any above average)
    if config.volume_confirm:
        confirmations_passed &= volume_data.get('volume_ratio', 1.0) >= 1.0  # Just above average
    
    # Bollinger Bands Confirmation - LENIENT: Increase near-band threshold
    if config.bb_confirm:
        upper_band = bb_data.get('upper_band', 0)
        lower_band = bb_data.get('lower_band', 0)
        current_price = bb_data.get('middle_band', 0)  # Use middle as proxy for current
        
        if is_long_signal:
            # Allow price closer to upper band (within 5% instead of 2%)
            confirmations_passed &= current_price <= upper_band * 0.95
        else:
            # Allow price closer to lower band (within 5% instead of 2%)
            confirmations_passed &= current_price >= lower_band * 1.05
    
    return confirmations_passed

def calculate_stop_loss_target(current_price, signal_type, atr, config, data):
    """Calculate stop loss and target price"""
    try:
        if signal_type == 'HOLD':
            return current_price, current_price
        
        atr_multiplier = 1.6
        
        if signal_type in ['STRONG_BUY', 'BUY']:
            if config.atr_trailing:
                stop_loss = current_price - (atr * atr_multiplier)
                target_price = current_price + (current_price - stop_loss) * 2
            else:
                stop_loss = current_price - (atr * atr_multiplier)
                target_price = current_price + (current_price - stop_loss) * 2
                
        else:  # STRONG_SELL, SELL
            if config.atr_trailing:
                stop_loss = current_price + (atr * atr_multiplier)
                target_price = current_price - (stop_loss - current_price) * 2
            else:
                stop_loss = current_price + (atr * atr_multiplier)
                target_price = current_price - (stop_loss - current_price) * 2
        
        return stop_loss, target_price
        
    except Exception as e:
        logger.error(f"Error calculating stop loss/target: {e}")
        return current_price, current_price

def detect_enhanced_trading_signals(data, current_price, config: EnhancedStrategyConfig, debug=False):
    """Enhanced multi-strategy signal detection with Inside Bar Strategy"""
    try:
        if len(data) < 80:
            return {
                'signal_type': 'HOLD',
                'signal_strength': 0,
                'stop_loss': current_price,
                'target_price': current_price,
                'entry_reason': 'Insufficient data',
                'target_percent': 0,
                'strategy_source': 'insufficient_data'
            }
        
        # Calculate all indicators
        rsi = calculate_rsi(data['Close'], config.rsi_length)
        macd_data = calculate_macd(data['Close'], config.macd_fast, config.macd_slow, config.macd_signal)
        ichimoku_data = calculate_ichimoku(data)
        aroon_data = calculate_aroon(data, config.aroon_length)
        stoch_data = calculate_stochastic(data, config.stoch_k_length, config.stoch_d_length)
        volume_data = calculate_volume_confirmation(data, config.volume_period, config.volume_threshold)
        bb_data = calculate_bollinger_bands(data, config.bb_length, config.bb_mult)
        atr = calculate_atr(data)
        
        # Calculate moving averages
        fast_ma = calculate_ma(data['Close'], config.fast_ma_length, config.fast_ma_type)
        slow_ma = calculate_ma(data['Close'], config.slow_ma_length, config.slow_ma_type)
        
        # Inside Bar Strategy
        inside_bar_data = calculate_inside_bar_strategy(
            data, 
            config.inside_bar_n_bars, 
            config.inside_bar_direction_filter,
            config.inside_bar_ma_filter,
            config.inside_bar_ma_length
        )
        
        # Other strategies
        consecutive_data = calculate_consecutive_bars(data, config.consecutive_bars_up, config.consecutive_bars_down)
        range_data = calculate_range_breakout(data, config.range_lookback, config.range_length, config.range_mult)
        
        # MA crossover signals
        fast_ma_current = fast_ma.iloc[-1] if hasattr(fast_ma, 'iloc') else fast_ma
        slow_ma_current = slow_ma.iloc[-1] if hasattr(slow_ma, 'iloc') else slow_ma
        fast_ma_prev = fast_ma.iloc[-2] if hasattr(fast_ma, 'iloc') and len(fast_ma) > 1 else fast_ma_current
        slow_ma_prev = slow_ma.iloc[-2] if hasattr(slow_ma, 'iloc') and len(slow_ma) > 1 else slow_ma_current
        
        ma_cross_up = fast_ma_current > slow_ma_current and fast_ma_prev <= slow_ma_prev
        ma_cross_down = fast_ma_current < slow_ma_current and fast_ma_prev >= slow_ma_prev
        ma_bull_trend = fast_ma_current > slow_ma_current
        ma_bear_trend = fast_ma_current < slow_ma_current
        
        # Signal collection and scoring
        signal_type = 'HOLD'
        signal_strength = 0
        strategy_source = 'none'
        entry_reason = 'No signal'
        
        # Strategy 1: Inside Bar Strategy
        if config.inside_bar_mode:
            if inside_bar_data['inside_bar_long']:
                confirmations_passed = check_confirmations(config, macd_data, rsi, ma_bull_trend, 
                                                         ichimoku_data, aroon_data, stoch_data, volume_data, bb_data, True)
                if confirmations_passed:
                    signal_type = 'STRONG_BUY'
                    signal_strength = 80
                    strategy_source = 'Inside_Bar_Long'
                    entry_reason = f'Inside bar bullish pattern ({inside_bar_data["n_bars_used"]} bars, {inside_bar_data["consecutive_bull_bars"]} bull bars)'
                    
            elif inside_bar_data['inside_bar_short']:
                confirmations_passed = check_confirmations(config, macd_data, rsi, ma_bear_trend, 
                                                         ichimoku_data, aroon_data, stoch_data, volume_data, bb_data, False)
                if confirmations_passed:
                    signal_type = 'STRONG_SELL'
                    signal_strength = 80
                    strategy_source = 'Inside_Bar_Short'
                    entry_reason = f'Inside bar bearish pattern ({inside_bar_data["n_bars_used"]} bars, {inside_bar_data["consecutive_bear_bars"]} bear bars)'
        
        # Strategy 2: Consecutive Bars
        if config.consecutive_mode and signal_type == 'HOLD':
            if consecutive_data['consecutive_up']:
                confirmations_passed = check_confirmations(config, macd_data, rsi, ma_bull_trend, 
                                                         ichimoku_data, aroon_data, stoch_data, volume_data, bb_data, True)
                if confirmations_passed:
                    signal_type = 'BUY'
                    signal_strength = 70
                    strategy_source = 'Consecutive_Bars_Up'
                    entry_reason = f'{consecutive_data["up_count"]} consecutive up bars'
                    
            elif consecutive_data['consecutive_down']:
                confirmations_passed = check_confirmations(config, macd_data, rsi, ma_bear_trend, 
                                                         ichimoku_data, aroon_data, stoch_data, volume_data, bb_data, False)
                if confirmations_passed:
                    signal_type = 'SELL'
                    signal_strength = 70
                    strategy_source = 'Consecutive_Bars_Down'
                    entry_reason = f'{consecutive_data["down_count"]} consecutive down bars'
        
        # Strategy 3: Range Breakout
        if config.range_15m_mode and signal_type == 'HOLD':
            if range_data['range_breakout_long']:
                confirmations_passed = check_confirmations(config, macd_data, rsi, ma_bull_trend, 
                                                         ichimoku_data, aroon_data, stoch_data, volume_data, bb_data, True)
                if confirmations_passed:
                    signal_type = 'BUY'
                    signal_strength = 75
                    strategy_source = 'Range_Breakout_Long'
                    entry_reason = f'Range breakout long (range: {range_data["current_range"]:.2f})'
        
        # Strategy 4: MA Crossover
        if config.ma_cross_mode and signal_type == 'HOLD':
            if ma_cross_up:
                confirmations_passed = check_confirmations(config, macd_data, rsi, True, 
                                                         ichimoku_data, aroon_data, stoch_data, volume_data, bb_data, True)
                if confirmations_passed:
                    signal_type = 'BUY'
                    signal_strength = 65
                    strategy_source = 'MA_Cross_Up'
                    entry_reason = f'{config.fast_ma_type}{config.fast_ma_length} crossed above {config.slow_ma_type}{config.slow_ma_length}'
                    
            elif ma_cross_down:
                confirmations_passed = check_confirmations(config, macd_data, rsi, False, 
                                                         ichimoku_data, aroon_data, stoch_data, volume_data, bb_data, False)
                if confirmations_passed:
                    signal_type = 'SELL'
                    signal_strength = 65
                    strategy_source = 'MA_Cross_Down'
                    entry_reason = f'{config.fast_ma_type}{config.fast_ma_length} crossed below {config.slow_ma_type}{config.slow_ma_length}'
        
        # Strategy 5: MACD Crossover
        if config.macd_cross_mode and signal_type == 'HOLD':
            if macd_data['cross_above']:
                confirmations_passed = check_confirmations(config, macd_data, rsi, ma_bull_trend, 
                                                         ichimoku_data, aroon_data, stoch_data, volume_data, bb_data, True)
                if confirmations_passed:
                    signal_type = 'BUY'
                    signal_strength = 60
                    strategy_source = 'MACD_Cross_Up'
                    entry_reason = 'MACD histogram crossed above zero'
                    
            elif macd_data['cross_below']:
                confirmations_passed = check_confirmations(config, macd_data, rsi, ma_bear_trend, 
                                                         ichimoku_data, aroon_data, stoch_data, volume_data, bb_data, False)
                if confirmations_passed:
                    signal_type = 'SELL'
                    signal_strength = 60
                    strategy_source = 'MACD_Cross_Down'
                    entry_reason = 'MACD histogram crossed below zero'
        
        # Calculate stop loss and target price - HANDLE PINE SCRIPT PRICES
        if not (signal_type in ['STRONG_BUY', 'STRONG_SELL'] and strategy_source.startswith('Inside_Bar')):
            # Use ATR-based calculation for other strategies
            stop_loss, target_price = calculate_stop_loss_target(current_price, signal_type, atr, config, data)
            entry_price = current_price
        
        # Calculate target percentage using proper entry price
        target_percent = 0
        if signal_type in ['STRONG_BUY', 'BUY']:
            target_percent = ((target_price - entry_price) / entry_price) * 100
        elif signal_type in ['STRONG_SELL', 'SELL']:
            target_percent = ((entry_price - target_price) / entry_price) * 100
        
        # Filter out low target signals
        if signal_type != 'HOLD' and target_percent < 0.5:
            if debug:
                print(f"   DEBUG: Signal filtered out - Target only {target_percent:.2f}% (need min 0.5%)")
            signal_type = 'HOLD'
            signal_strength = 0
            strategy_source = 'filtered_low_target'
            entry_reason = f'Target too low ({target_percent:.2f}% < 0.5%)'
            target_percent = 0
        
        if debug:
            print(f"   DEBUG: Strategy: {strategy_source}")
            print(f"   DEBUG: Inside Bar Detected: {inside_bar_data['inside_bar_detected']}")
            print(f"   DEBUG: MA Trend Up: {inside_bar_data['ma_trend_up']}")
            print(f"   DEBUG: Signal Strength: {signal_strength}")
        
        return {
            'signal_type': signal_type,
            'signal_strength': float(signal_strength),
            'stop_loss': float(stop_loss),
            'target_price': float(target_price),
            'target_percent': float(target_percent),
            'entry_reason': entry_reason,
            'strategy_source': strategy_source,
            'rsi': rsi,
            'macd_data': macd_data,
            'ichimoku_data': ichimoku_data,
            'aroon_data': aroon_data,
            'stoch_data': stoch_data,
            'volume_data': volume_data,
            'bb_data': bb_data,
            'inside_bar_data': inside_bar_data,
            'consecutive_data': consecutive_data,
            'range_data': range_data,
            'ma_bull_trend': ma_bull_trend,
            'ma_bear_trend': ma_bear_trend,
            'atr': atr,
            'fast_ma': float(fast_ma_current),
            'slow_ma': float(slow_ma_current)
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
            'entry_reason': f'Error: {str(e)[:50]}',
            'strategy_source': 'error'
        }

def analyze_stock_enhanced(ticker, interval="15m", config=None, position_manager=None, debug=False):
    """Enhanced stock analysis with Inside Bar Strategy"""
    if config is None:
        config = EnhancedStrategyConfig()
        
    try:
        sector = get_sector_for_ticker(ticker)
        
        data = get_stock_data(ticker, interval=interval)
        if data is None or len(data) < 80:
            if debug:
                print(f"   {ticker}: Insufficient data for analysis - got {len(data) if data is not None else 0} bars, need 80+")
            return None
        
        current_price = data['Close'].iloc[-1]
        
        if interval in ['5m', '15m', '30m', '1h']:
            live_price = get_live_price(ticker)
            if live_price:
                current_price = live_price
        else:
            live_price = None
        
        if position_manager:
            position_manager.update_position_prices(ticker, current_price)
        
        signal_data = detect_enhanced_trading_signals(data, current_price, config, debug)
        
        if position_manager and ticker not in position_manager.positions:
            if signal_data['signal_type'] in ['STRONG_BUY', 'BUY']:
                position_manager.enter_position(
                    ticker, 'long', current_price, 
                    signal_data['stop_loss'], signal_data['target_price'],
                    signal_data['signal_strength'], signal_data['strategy_source']
                )
            elif signal_data['signal_type'] in ['STRONG_SELL', 'SELL']:
                position_manager.enter_position(
                    ticker, 'short', current_price,
                    signal_data['stop_loss'], signal_data['target_price'],
                    signal_data['signal_strength'], signal_data['strategy_source']
                )
        
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
                'signal_strength': pos.signal_strength,
                'strategy_source': pos.strategy_source
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
            'strategy_source': signal_data['strategy_source'],
            'volume_ratio': float(volume_ratio),
            'rsi': signal_data['rsi'],
            'fast_ma': signal_data['fast_ma'],
            'slow_ma': signal_data['slow_ma'],
            'trend_direction': 'BULLISH' if signal_data['ma_bull_trend'] else 'BEARISH',
            'macd_bull': signal_data['macd_data']['bull_trend'],
            'macd_histogram': signal_data['macd_data']['histogram'],
            'aroon_up': signal_data['aroon_data']['aroon_up'],
            'aroon_down': signal_data['aroon_data']['aroon_down'],
            'stoch_k': signal_data['stoch_data']['stoch_k'],
            'stoch_d': signal_data['stoch_data']['stoch_d'],
            'bb_upper': signal_data['bb_data']['upper_band'],
            'bb_middle': signal_data['bb_data']['middle_band'],
            'bb_lower': signal_data['bb_data']['lower_band'],
            'atr': signal_data['atr'],
            'bars_analyzed': len(data),
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'position': position_info,
            'is_trading_hours': is_indian_trading_hours(),
            'interval': interval,
            'data_period': f"Last {len(data)} {interval} bars",
            'ichimoku_long': signal_data['ichimoku_data']['long_condition'],
            'ichimoku_short': signal_data['ichimoku_data']['short_condition'],
            'cloud_color': signal_data['ichimoku_data']['cloud_color'],
            'conversion_line': signal_data['ichimoku_data']['conversion_line'],
            'base_line': signal_data['ichimoku_data']['base_line'],
            'inside_bar_long': signal_data['inside_bar_data']['inside_bar_long'],
            'inside_bar_short': signal_data['inside_bar_data']['inside_bar_short'],
            'inside_bar_detected': signal_data['inside_bar_data']['inside_bar_detected'],
            'inside_bar_ma_trend': signal_data['inside_bar_data']['ma_trend_up'],
            'inside_bar_consecutive_bull': signal_data['inside_bar_data']['consecutive_bull_bars'],
            'inside_bar_consecutive_bear': signal_data['inside_bar_data']['consecutive_bear_bars'],
            'consecutive_up': signal_data['consecutive_data']['consecutive_up'],
            'consecutive_down': signal_data['consecutive_data']['consecutive_down'],
            'up_count': signal_data['consecutive_data']['up_count'],
            'down_count': signal_data['consecutive_data']['down_count']
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing {ticker} ({interval}): {e}")
        return None

def analyze_all_stocks_enhanced(interval="15m", strategy_config=None, position_manager=None, max_workers=4, debug=False):
    """Analyze all stocks with enhanced Inside Bar Strategy"""
    if strategy_config is None:
        strategy_config = EnhancedStrategyConfig()
    if position_manager is None:
        position_manager = PositionManager()
    
    tickers = [stock['symbol'] for stock in config.TOP_STOCKS]
    logger.info(f"Enhanced analysis of {len(tickers)} stocks with Inside Bar Strategy ({interval} intervals)...")
    
    all_signals = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(analyze_stock_enhanced, ticker, interval, strategy_config, position_manager, debug): ticker 
            for ticker in tickers
        }
        
        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                result = future.result(timeout=60)
                if result:
                    all_signals.append(result)
                    logger.info(f"✓ {ticker}: {result['signal_type']} (Strength: {result['signal_strength']:.1f}) via {result['strategy_source']}")
                else:
                    logger.warning(f"✗ {ticker}: No signal generated")
            except Exception as e:
                logger.error(f"✗ {ticker}: {str(e)[:50]}")
    
    return all_signals, position_manager

def display_combined_inside_bar_and_full_reports(all_signals, position_manager, cycle_number, interval="5m", config=None, min_threshold=10):
    """Combined display showing Inside Bar Strong Signals + Full comprehensive reports"""
    if not all_signals:
        print("\nNo signals found!")
        return []
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    is_trading = is_indian_trading_hours()
    
    # Filter data
    threshold_signals = [s for s in all_signals if s.get('signal_strength', 0) >= min_threshold]
    strong_buy_signals = [s for s in all_signals if s['signal_type'] == 'STRONG_BUY']
    strong_sell_signals = [s for s in all_signals if s['signal_type'] == 'STRONG_SELL']
    regular_buy = [s for s in threshold_signals if s['signal_type'] == 'BUY']
    regular_sell = [s for s in threshold_signals if s['signal_type'] == 'SELL']
    
    # Inside bar pattern analysis
    inside_bar_detected_stocks = [s for s in all_signals if s.get('inside_bar_detected', False)]
    inside_bar_long_patterns = [s for s in all_signals if s.get('inside_bar_long', False)]
    inside_bar_short_patterns = [s for s in all_signals if s.get('inside_bar_short', False)]
    
    print(f"\n{'='*250}")
    print(f"CYCLE #{cycle_number} - INSIDE BAR STRATEGY + COMPREHENSIVE ANALYSIS ({interval} intervals)")
    print(f"Time: {current_time} | Market: {'OPEN' if is_trading else 'CLOSED'}")
    print(f"Total Analyzed: {len(all_signals)} | Above {min_threshold}% Threshold: {len(threshold_signals)} | Inside Bar Detected: {len(inside_bar_detected_stocks)}")
    print(f"Strong Buy: {len(strong_buy_signals)} | Strong Sell: {len(strong_sell_signals)} | Regular Buy: {len(regular_buy)} | Regular Sell: {len(regular_sell)}")
    print(f"{'='*250}")
    
    # SECTION 1: INSIDE BAR STRONG SIGNALS ANALYSIS
    print(f"\nINSIDE BAR STRONG SIGNALS ANALYSIS")
    print("=" * 200)
    
    print(f"\nINSIDE BAR PATTERN DETECTION SUMMARY:")
    print(f"Inside Bar Patterns Detected: {len(inside_bar_detected_stocks)}")
    print(f"Inside Bar LONG Patterns: {len(inside_bar_long_patterns)} | SHORT Patterns: {len(inside_bar_short_patterns)}")
    print(f"Strong Buy Generated: {len(strong_buy_signals)} | Strong Sell Generated: {len(strong_sell_signals)}")
    
    # Show STRONG BUY signals with inside bar details
    if strong_buy_signals:
        print(f"\nSTRONG BUY SIGNALS ({len(strong_buy_signals)} stocks):")
        print("-" * 180)
        
        strong_header = "{:<10} | {:<8} | {:<9} | {:<3} | {:<5} | {:<8} | {:<6} | {:<8} | {:<12} | {:<25}"
        print(strong_header.format("Ticker", "Sector", "Price", "Str", "RSI", "Target%", "IB_Det", "MA_Trend", "Bull_Bars", "Strategy_Reason"))
        print("-" * 180)
        
        for result in sorted(strong_buy_signals, key=lambda x: x.get('signal_strength', 0), reverse=True):
            ib_detected = "YES" if result.get('inside_bar_detected', False) else "NO"
            ma_trend = "UP" if result.get('inside_bar_ma_trend', False) else "DOWN"
            bull_bars = result.get('inside_bar_consecutive_bull', 0)
            
            print(strong_header.format(
                result['ticker'][:10], result['sector'][:8], f"Rs{result['current_price']:.2f}",
                f"{result['signal_strength']:.0f}", f"{result['rsi']:.1f}", 
                f"{result['target_percent']:.1f}%", ib_detected, ma_trend, f"{bull_bars}B",
                result['entry_reason'][:25]
            ))
    
    # Show STRONG SELL signals with inside bar details  
    if strong_sell_signals:
        print(f"\nSTRONG SELL SIGNALS ({len(strong_sell_signals)} stocks):")
        print("-" * 180)
        
        print(strong_header.format("Ticker", "Sector", "Price", "Str", "RSI", "Target%", "IB_Det", "MA_Trend", "Bear_Bars", "Strategy_Reason"))
        print("-" * 180)
        
        for result in sorted(strong_sell_signals, key=lambda x: x.get('signal_strength', 0), reverse=True):
            ib_detected = "YES" if result.get('inside_bar_detected', False) else "NO"
            ma_trend = "UP" if result.get('inside_bar_ma_trend', False) else "DOWN"
            bear_bars = result.get('inside_bar_consecutive_bear', 0)
            
            print(strong_header.format(
                result['ticker'][:10], result['sector'][:8], f"Rs{result['current_price']:.2f}",
                f"{result['signal_strength']:.0f}", f"{result['rsi']:.1f}",
                f"{result['target_percent']:.1f}%", ib_detected, ma_trend, f"{bear_bars}B", 
                result['entry_reason'][:25]
            ))
    
    # Inside bar patterns that didn't generate strong signals - DETAILED TECHNICAL ANALYSIS
    if inside_bar_detected_stocks:
        ib_no_strong_signal = [s for s in inside_bar_detected_stocks if s['signal_type'] not in ['STRONG_BUY', 'STRONG_SELL']]
        
        if ib_no_strong_signal:
            print(f"\nINSIDE BAR PATTERNS - COMPLETE TECHNICAL ANALYSIS ({len(ib_no_strong_signal)} stocks):")
            print("=" * 220)
            
            # Comprehensive header with SECTOR and organized by signal type
            detailed_header = "{:<10} | {:<8} | {:<9} | {:<3} | {:<12} | {:<8} | {:<9} | {:<9} | {:<9} | {:<12} | {:<5} | {:<8} | {:<10} | {:<20}"
            print(detailed_header.format(
                "Ticker", "Sector", "Price", "Str", "IB_Pattern", "MA_Trend", "IB_High", "IB_Low", "IB_Range", "Breakout_Req", "RSI", "MACD", "Ichimoku", "Breakout_Status"
            ))
            print("-" * 220)
            
            # Sort by signal type: STRONG_SELL -> SELL -> STRONG_BUY -> BUY -> HOLD
            signal_priority = {
                'STRONG_SELL': 1,
                'SELL': 2, 
                'STRONG_BUY': 3,
                'BUY': 4,
                'HOLD': 5
            }
            
            sorted_results = sorted(ib_no_strong_signal, 
                                  key=lambda x: (signal_priority.get(x['signal_type'], 6), 
                                               -x.get('signal_strength', 0)))
            
            for result in sorted_results[:20]:  # Show top 20
                ib_pattern_type = "DETECTED"
                if result.get('inside_bar_long'): ib_pattern_type = "LONG"
                elif result.get('inside_bar_short'): ib_pattern_type = "SHORT"
                
                ma_trend = "UP" if result.get('inside_bar_ma_trend', False) else "DOWN"
                sector = result.get('sector', 'Unknown')[:8]  # Get sector, limit to 8 chars
                
                # Get inside bar breakout data
                current_price = result.get('current_price', 0)
                inside_bar_high = result.get('inside_bar_high', 0)
                inside_bar_low = result.get('inside_bar_low', 0)
                inside_bar_range = result.get('inside_bar_range', 0)
                
                # Determine breakout requirement and status
                if ma_trend == "UP":
                    breakout_req = f">{inside_bar_high:.1f}"
                    if current_price > inside_bar_high:
                        breakout_status = "BREAKOUT_LONG"
                    else:
                        distance_to_breakout = inside_bar_high - current_price
                        breakout_status = f"WAIT_L(-{distance_to_breakout:.1f})"
                else:
                    breakout_req = f"<{inside_bar_low:.1f}"
                    if current_price < inside_bar_low:
                        breakout_status = "BREAKOUT_SHORT"
                    else:
                        distance_to_breakout = current_price - inside_bar_low
                        breakout_status = f"WAIT_S(+{distance_to_breakout:.1f})"
                
                # Technical indicators
                rsi = result.get('rsi', 50)
                macd_dir = "BULL" if result.get('macd_bull', False) else "BEAR"
                
                # Ichimoku summary
                if result.get('ichimoku_long', False):
                    ichimoku_summary = "LONG"
                elif result.get('ichimoku_short', False):
                    ichimoku_summary = "SHORT"  
                else:
                    ichimoku_summary = "NEUTRAL"
                
                print(detailed_header.format(
                    result['ticker'][:10], sector, f"Rs{current_price:.0f}",
                    f"{result['signal_strength']:.0f}", ib_pattern_type, ma_trend,
                    f"Rs{inside_bar_high:.0f}", f"Rs{inside_bar_low:.0f}", f"Rs{inside_bar_range:.1f}",
                    breakout_req, f"{rsi:.0f}", f"{macd_dir[:4]}", ichimoku_summary,
                    breakout_status[:20]
                ))
    
    # SECTION 2: COMPREHENSIVE FULL REPORTS
    print(f"\nCOMPREHENSIVE MARKET ANALYSIS - ALL SIGNALS >= {min_threshold}% THRESHOLD")
    print("=" * 250)
    
    # Show active positions first
    if position_manager and position_manager.positions:
        print(f"\nACTIVE POSITIONS ({len(position_manager.positions)}):")
        print("-" * 160)
        pos_header = "{:<10} | {:<5} | {:<9} | {:<9} | {:<9} | {:<9} | {:<10} | {:<15} | {:<8}"
        print(pos_header.format("Ticker", "Type", "Entry", "Current", "Stop", "Target", "PnL%", "Strategy", "Time"))
        print("-" * 160)
        
        for ticker, pos in position_manager.positions.items():
            direction, pnl_percent = position_manager.get_position_direction_status(ticker, pos.current_price)
            entry_time = pos.entry_time.strftime('%H:%M')
            
            print(pos_header.format(
                ticker[:10], pos.position_type.upper(), f"Rs{pos.entry_price:.2f}",
                f"Rs{pos.current_price:.2f}", f"Rs{pos.stop_loss:.2f}", f"Rs{pos.target_price:.2f}",
                pnl_percent, pos.strategy_source[:15], entry_time
            ))
    
    # Show ALL signals above threshold (comprehensive table)
    if threshold_signals:
        print(f"\nALL SIGNALS ABOVE {min_threshold}% THRESHOLD ({len(threshold_signals)} stocks):")
        print("=" * 300)
        
        # Comprehensive table header
        header = "{:<10} | {:<8} | {:<9} | {:<12} | {:<3} | {:<5} | {:<8} | {:<8} | {:<10} | {:<8} | {:<5} | {:<6} | {:<15} | {:<20}"
        print(header.format(
            "Ticker", "Sector", "Price", "Signal", "Str", "RSI", "MACD", "MA_Trend", "Ichimoku", "Aroon", "Vol", "Target%", "Strategy", "Pine_Signals"
        ))
        print("-" * 300)
        
        sorted_signals = sorted(threshold_signals, key=lambda x: x.get('signal_strength', 0), reverse=True)
        
        for result in sorted_signals:
            # Pine Script signals summary
            pine_signals = []
            if result.get('inside_bar_long'): pine_signals.append("IB_L")
            if result.get('inside_bar_short'): pine_signals.append("IB_S")
            if result.get('consecutive_up'): pine_signals.append(f"CONS_U({result.get('up_count', 0)})")
            if result.get('consecutive_down'): pine_signals.append(f"CONS_D({result.get('down_count', 0)})")
            pine_summary = " ".join(pine_signals) if pine_signals else "NONE"
            
            macd_dir = "BULL" if result.get('macd_bull', False) else "BEAR"
            
            if result.get('ichimoku_long', False):
                ichimoku_summary = "LONG"
            elif result.get('ichimoku_short', False):
                ichimoku_summary = "SHORT"
            else:
                ichimoku_summary = "NEUTRAL"
            
            aroon_up = result.get('aroon_up', 50)
            aroon_down = result.get('aroon_down', 50)
            if aroon_up > aroon_down + 10:
                aroon_summary = "BULL"
            elif aroon_down > aroon_up + 10:
                aroon_summary = "BEAR"
            else:
                aroon_summary = "NEUT"
            
            strength_indicator = ""
            if result['signal_strength'] >= 75:
                strength_indicator = "***"
            elif result['signal_strength'] >= 50:
                strength_indicator = "**"
            elif result['signal_strength'] >= 25:
                strength_indicator = "*"
            
            print(header.format(
                result['ticker'][:10], result['sector'][:8], f"Rs{result['current_price']:.2f}",
                f"{result['signal_type'][:12]}{strength_indicator}", f"{result['signal_strength']:.0f}",
                f"{result['rsi']:.1f}", macd_dir, result['trend_direction'][:8],
                ichimoku_summary, aroon_summary, f"{result['volume_ratio']:.1f}x",
                f"{result['target_percent']:.1f}%", result['strategy_source'][:15], pine_summary[:20]
            ))
    
    # Detailed view for high-strength signals (60%+)
    high_strength_signals = [s for s in threshold_signals if s.get('signal_strength', 0) >= 60]
    
    if high_strength_signals:
        print(f"\nDETAILED VIEW - HIGH STRENGTH SIGNALS (>= 60%):")
        print("=" * 200)
        
        for result in high_strength_signals:
            print(f"\nTICKER: {result['ticker']} | SECTOR: {result['sector']} | SIGNAL: {result['signal_type']} | STRENGTH: {result['signal_strength']:.1f}")
            print(f"Price: Rs{result['current_price']:.2f} | Target: Rs{result['target_price']:.2f} ({result['target_percent']:.1f}%) | Stop: Rs{result['stop_loss']:.2f}")
            print(f"Strategy: {result['strategy_source']} | Reason: {result['entry_reason']}")
            
            print(f"MACD: {'BULLISH' if result['macd_bull'] else 'BEARISH'} ({result['macd_histogram']:.3f}) | RSI: {result['rsi']:.1f} | MA: {result['trend_direction']}")
            print(f"Ichimoku: {'LONG' if result['ichimoku_long'] else 'SHORT' if result['ichimoku_short'] else 'NEUTRAL'} | Cloud: {result['cloud_color'].upper()}")
            print(f"Aroon: UP{result['aroon_up']:.0f} DOWN{result['aroon_down']:.0f} | Stoch: K{result['stoch_k']:.1f} D{result['stoch_d']:.1f}")
            print(f"Volume: {result['volume_ratio']:.1f}x | ATR: {result['atr']:.2f}")
            
            # Inside Bar signals (detailed)
            inside_signals = []
            if result.get('inside_bar_long'): inside_signals.append("INSIDE BAR LONG")
            if result.get('inside_bar_short'): inside_signals.append("INSIDE BAR SHORT")
            if result.get('inside_bar_detected'): inside_signals.append(f"Inside Bar Pattern Detected")
            if result.get('consecutive_up'): inside_signals.append(f"CONSECUTIVE UP ({result.get('up_count', 0)} bars)")
            if result.get('consecutive_down'): inside_signals.append(f"CONSECUTIVE DOWN ({result.get('down_count', 0)} bars)")
            
            if inside_signals:
                print(f"Pine Script: {' | '.join(inside_signals)}")
            
            print("-" * 120)
    
    # Market direction summary
    print(f"\nMARKET DIRECTION SUMMARY:")
    print("-" * 100)
    
    bullish_macd = len([s for s in all_signals if s.get('macd_bull', False)])
    bearish_macd = len([s for s in all_signals if not s.get('macd_bull', False)])
    bullish_ma = len([s for s in all_signals if s.get('trend_direction') == 'BULLISH'])
    bearish_ma = len([s for s in all_signals if s.get('trend_direction') == 'BEARISH'])
    ichimoku_long = len([s for s in all_signals if s.get('ichimoku_long', False)])
    ichimoku_short = len([s for s in all_signals if s.get('ichimoku_short', False)])
    ichimoku_neutral = len(all_signals) - ichimoku_long - ichimoku_short
    rsi_oversold = len([s for s in all_signals if s.get('rsi', 50) <= 30])
    rsi_overbought = len([s for s in all_signals if s.get('rsi', 50) >= 70])
    rsi_neutral = len(all_signals) - rsi_oversold - rsi_overbought
    high_volume = len([s for s in all_signals if s.get('volume_ratio', 1.0) >= 1.5])
    
    print(f"MACD Direction: BULL {bullish_macd} | BEAR {bearish_macd}")
    print(f"MA Trend: BULLISH {bullish_ma} | BEARISH {bearish_ma}")  
    print(f"Ichimoku: LONG {ichimoku_long} | SHORT {ichimoku_short} | NEUTRAL {ichimoku_neutral}")
    print(f"RSI Levels: OVERSOLD {rsi_oversold} | OVERBOUGHT {rsi_overbought} | NEUTRAL {rsi_neutral}")
    print(f"High Volume: {high_volume} stocks (>1.5x average)")
    
    # Signal strength distribution
    print(f"\nSIGNAL STRENGTH DISTRIBUTION:")
    strength_80_plus = len([s for s in threshold_signals if s.get('signal_strength', 0) >= 80])
    strength_60_79 = len([s for s in threshold_signals if 60 <= s.get('signal_strength', 0) < 80])
    strength_40_59 = len([s for s in threshold_signals if 40 <= s.get('signal_strength', 0) < 60])
    strength_20_39 = len([s for s in threshold_signals if 20 <= s.get('signal_strength', 0) < 40])
    strength_10_19 = len([s for s in threshold_signals if 10 <= s.get('signal_strength', 0) < 20])
    
    print(f"80%+: {strength_80_plus} | 60-79%: {strength_60_79} | 40-59%: {strength_40_59} | 20-39%: {strength_20_39} | 10-19%: {strength_10_19}")
    
    # Strategy breakdown
    if config:
        print(f"\nSTRATEGY & CONFIRMATION STATUS:")
        enabled_strategies = []
        if config.inside_bar_mode: enabled_strategies.append("Inside Bar")
        if config.consecutive_mode: enabled_strategies.append("Consecutive Bars")
        if config.range_15m_mode: enabled_strategies.append("Range Break")
        if config.ma_cross_mode: enabled_strategies.append("MA Cross")
        if config.macd_cross_mode: enabled_strategies.append("MACD Cross")
        
        enabled_confirmations = []
        if config.macd_confirm: enabled_confirmations.append("MACD")
        if config.rsi_confirm: enabled_confirmations.append("RSI")
        if config.ma_confirm: enabled_confirmations.append("MA")
        if config.ichimoku_confirm: enabled_confirmations.append("Ichimoku")
        if config.aroon_confirm: enabled_confirmations.append("Aroon")
        if config.stoch_confirm: enabled_confirmations.append("Stochastic")
        if config.volume_confirm: enabled_confirmations.append("Volume")
        if config.bb_confirm: enabled_confirmations.append("Bollinger")
        
        print(f"ACTIVE STRATEGIES: {', '.join(enabled_strategies) if enabled_strategies else 'None'}")
        print(f"ACTIVE CONFIRMATIONS: {', '.join(enabled_confirmations) if enabled_confirmations else 'None'}")
    
    # Final summary
    total_active = len(position_manager.positions) if position_manager else 0
    total_closed = len(position_manager.position_history) if position_manager else 0
    total_unrealized_pnl = sum([p.unrealized_pnl for p in position_manager.positions.values()]) if position_manager else 0
    
    print(f"\nCYCLE #{cycle_number} FINAL SUMMARY:")
    print(f"Total Analyzed: {len(all_signals)} | Signals >= {min_threshold}%: {len(threshold_signals)}")
    print(f"Inside Bar Patterns: {len(inside_bar_detected_stocks)} | Strong Buy: {len(strong_buy_signals)} | Strong Sell: {len(strong_sell_signals)}")
    print(f"Active Positions: {total_active} | Closed: {total_closed} | Total PnL: Rs{total_unrealized_pnl:.2f}")
    print(f"Market Sentiment: {'BULLISH' if bullish_macd > bearish_macd else 'BEARISH'}")
    
    if len(strong_buy_signals) == 0 and len(strong_sell_signals) == 0:
        print(f"Next cycle in 5 minutes...")
    
    return threshold_signals

def live_trading_with_threshold(interval="5m", strategy_config=None, max_workers=4, debug=False, min_threshold=10):
    """Live trading session with combined inside bar strong signals + comprehensive reports"""
    if strategy_config is None:
        strategy_config = EnhancedStrategyConfig()
    
    position_manager = PositionManager()
    cycle_number = 0
    
    print(f"STARTING LIVE MARKET SCANNER WITH INSIDE BAR STRATEGY")
    print(f"Interval: {interval} | Workers: {max_workers} | Min Threshold: {min_threshold}%")
    print(f"Shows Inside Bar Strong Signals + Complete Market Analysis")
    print("Press Ctrl+C to stop")
    print("=" * 100)
    
    try:
        while True:
            cycle_number += 1
            is_trading = is_indian_trading_hours()
            
            try:
                print(f"\nInside Bar Strategy Scan #{cycle_number} at {datetime.now().strftime('%H:%M:%S')}")
                print(f"Market Status: {'OPEN' if is_trading else 'CLOSED'}")
                
                # Run analysis regardless of market hours
                all_signals, position_manager = analyze_all_stocks_enhanced(
                    interval, strategy_config, position_manager, max_workers, debug
                )
                
                if all_signals:
                    threshold_signals = display_combined_inside_bar_and_full_reports(
                        all_signals, position_manager, cycle_number, interval, strategy_config, min_threshold
                    )
                    
                    # Save results
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
                    df = pd.DataFrame(all_signals)
                    filename = f"inside_bar_scan_combined_cycle_{cycle_number}_{timestamp}.csv"
                    df.to_csv(filename, index=False)
                    
                    if threshold_signals:
                        threshold_df = pd.DataFrame(threshold_signals)
                        threshold_filename = f"inside_bar_signals_above_{min_threshold}_cycle_{cycle_number}_{timestamp}.csv"
                        threshold_df.to_csv(threshold_filename, index=False)
                        print(f"Signals >= {min_threshold}% saved: {threshold_filename}")
                        
                        # Log high strength signals
                        high_signals = [s for s in threshold_signals if s.get('signal_strength', 0) >= 60]
                        for signal in high_signals:
                            logger.info(f"HIGH SIGNAL: {signal['ticker']} {signal['signal_type']} - Strength: {signal['signal_strength']:.1f}")
                
                # Market hours logic
                if is_trading:
                    print(f"Next scan in 5 minutes...")
                    time.sleep(300)
                else:
                    print(f"Market closed. Waiting for next market open...")
                    wait_for_market_open()
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in cycle #{cycle_number}: {e}")
                print(f"ERROR: {str(e)[:100]}")
                time.sleep(300)
                
    except KeyboardInterrupt:
        print(f"\nInside Bar Strategy scanner terminated")

def main():
    """Main function with Inside Bar Strategy and comprehensive reports"""
    parser = argparse.ArgumentParser(description="Complete Inside Bar Strategy Market Scanner")
    
    parser.add_argument('--live-trading', action='store_true', help='Start live market scanner')
    parser.add_argument('--test-mode', action='store_true', help='Run single test scan')
    parser.add_argument('--test-single', type=str, help='Test single ticker')
    parser.add_argument('--min-threshold', type=int, default=10, help='Minimum signal strength threshold')
    parser.add_argument('--interval', type=str, default='5m', choices=['5m', '15m', '30m', '1h', '1d'], help='Trading interval')
    parser.add_argument('--workers', type=int, default=6, help='Max concurrent workers')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    
    # Strategy selection - Inside Bar Strategy (with backward compatibility)
    parser.add_argument('--inside-bar', action='store_true', default=True, help='Enable Inside Bar strategy (default)')
    parser.add_argument('--breakout', action='store_true', help='DEPRECATED: Use --inside-bar instead')
    parser.add_argument('--consecutive', action='store_true', help='Enable Consecutive Bars strategy')
    parser.add_argument('--range-15m', action='store_true', help='Enable Range Breakout strategy')
    parser.add_argument('--ma-cross', action='store_true', help='Enable MA Cross strategy')
    parser.add_argument('--macd-cross', action='store_true', help='Enable MACD Cross strategy')
    
    # Inside Bar Strategy Parameters
    parser.add_argument('--inside-bar-n-bars', type=int, default=1, choices=[1,2,3,4], help='Number of inside bars (1-4)')
    parser.add_argument('--inside-bar-direction-filter', action='store_true', help='Only trade complete bull/bear patterns')
    parser.add_argument('--inside-bar-ma-filter', action='store_true', default=True, help='Use MA trend filter')
    parser.add_argument('--inside-bar-ma-length', type=int, default=65, help='MA length for trend filter')
    
    # Confirmation modes
    parser.add_argument('--macd-confirm', action='store_true', help='Enable MACD confirmation')
    parser.add_argument('--rsi-confirm', action='store_true', help='Enable RSI confirmation')
    parser.add_argument('--ma-confirm', action='store_true', help='Enable MA confirmation')
    parser.add_argument('--ichimoku-confirm', action='store_true', help='Enable Ichimoku confirmation')
    parser.add_argument('--aroon-confirm', action='store_true', help='Enable Aroon confirmation')
    
    args = parser.parse_args()
    
    # Handle backward compatibility
    if args.breakout:
        print("WARNING: --breakout is deprecated. Using --inside-bar strategy instead.")
        args.inside_bar = True
    
    strategy_config = EnhancedStrategyConfig(
        inside_bar_mode=args.inside_bar,
        consecutive_mode=args.consecutive,
        range_15m_mode=args.range_15m,
        ma_cross_mode=args.ma_cross,
        macd_cross_mode=args.macd_cross,
        inside_bar_n_bars=args.inside_bar_n_bars,
        inside_bar_direction_filter=args.inside_bar_direction_filter,
        inside_bar_ma_filter=args.inside_bar_ma_filter,
        inside_bar_ma_length=args.inside_bar_ma_length,
        macd_confirm=args.macd_confirm,
        rsi_confirm=args.rsi_confirm,
        ma_confirm=args.ma_confirm,
        ichimoku_confirm=args.ichimoku_confirm,
        aroon_confirm=args.aroon_confirm
    )
    
    if args.test_single:
        print(f"SINGLE STOCK ANALYSIS: {args.test_single}")
        result = analyze_stock_enhanced(args.test_single, args.interval, strategy_config, debug=True)
        if result:
            print(f"\nCOMPLETE TECHNICAL ANALYSIS:")
            print(f"Signal: {result['signal_type']} | Strength: {result['signal_strength']:.1f}")
            print(f"Price: Rs{result['current_price']:.2f} | Target: Rs{result['target_price']:.2f} | Stop: Rs{result['stop_loss']:.2f}")
            print(f"Strategy: {result['strategy_source']} | Reason: {result['entry_reason']}")
            print(f"\nTECHNICAL INDICATORS:")
            print(f"RSI: {result['rsi']:.1f} | MACD: {'BULL' if result['macd_bull'] else 'BEAR'} | MA Trend: {result['trend_direction']}")
            print(f"Ichimoku: {'LONG' if result['ichimoku_long'] else 'SHORT' if result['ichimoku_short'] else 'NEUTRAL'}")
            print(f"Inside Bar: Long={result['inside_bar_long']} Short={result['inside_bar_short']} Detected={result['inside_bar_detected']}")
            print(f"Consecutive: Up={result['consecutive_up']}({result['up_count']}) Down={result['consecutive_down']}({result['down_count']})")
        else:
            print(f"No analysis possible for {args.test_single}")
        return

    elif args.test_mode:
        print(f"COMPLETE INSIDE BAR STRATEGY TEST SCAN - Signals >= {args.min_threshold}%")
        position_manager = PositionManager()
        all_signals, position_manager = analyze_all_stocks_enhanced(
            args.interval, strategy_config, position_manager, args.workers, args.debug
        )
        if all_signals:
            display_combined_inside_bar_and_full_reports(all_signals, position_manager, 1, args.interval, strategy_config, args.min_threshold)
        return

    elif args.live_trading:
        live_trading_with_threshold(args.interval, strategy_config, args.workers, args.debug, args.min_threshold)
        return

    else:
        print("COMPLETE OPTIMIZED INSIDE BAR STRATEGY MARKET SCANNER")
        print("=" * 70)
        print("Features:")
        print("• Inside Bar Pattern Recognition (replaces breakout)")
        print("• Complete technical analysis (MACD, RSI, Ichimoku, Aroon, etc.)")
        print("• Strong Buy/Sell signal focus + comprehensive reports")
        print("• Smart market hours handling")
        print("• Live NSE + Yahoo Finance price fetching")
        print("• Multiple confirmation filters")
        print("• Position management with P&L tracking")
        print("")
        print("Usage Examples:")
        print(f"Test: python {sys.argv[0]} --test-mode --inside-bar --macd-confirm --rsi-confirm")
        print(f"Live: python {sys.argv[0]} --live-trading --inside-bar --consecutive --macd-confirm")
        print("")
        print("Shows both: Inside Bar strong signals analysis + Full market reports")

if __name__ == "__main__":
    main()