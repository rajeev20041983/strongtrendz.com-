#!/usr/bin/env python
# multi_indicator_live.py - Complex Multi-Indicator Strategy

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
import time
import logging
import schedule
import pytz
from scipy.signal import argrelextrema

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("multi_indicator_live.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

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

# Timezone setup
IST = pytz.timezone('Asia/Kolkata')
UK_TZ = pytz.timezone('Europe/London')

def get_uk_time():
    """Get current UK time"""
    return datetime.now(UK_TZ)

def get_ist_time():
    """Get current IST time"""
    return datetime.now(IST)

def is_market_open():
    """Check if Indian market is open (converted to UK time)"""
    try:
        ist_now = get_ist_time()
        
        # Market hours in IST: 9:15 AM to 3:30 PM
        market_start = ist_now.replace(hour=9, minute=15, second=0, microsecond=0)
        market_end = ist_now.replace(hour=15, minute=30, second=0, microsecond=0)
        
        # Convert to UK time for display
        uk_now = get_uk_time()
        uk_market_start = market_start.astimezone(UK_TZ)
        uk_market_end = market_end.astimezone(UK_TZ)
        
        is_open = market_start <= ist_now <= market_end
        
        return {
            'is_open': is_open,
            'uk_time': uk_now.strftime('%H:%M:%S'),
            'ist_time': ist_now.strftime('%H:%M:%S'),
            'uk_market_start': uk_market_start.strftime('%H:%M'),
            'uk_market_end': uk_market_end.strftime('%H:%M'),
            'ist_market_start': market_start.strftime('%H:%M'),
            'ist_market_end': market_end.strftime('%H:%M')
        }
    except Exception as e:
        logger.error(f"Error checking market hours: {e}")
        return {'is_open': False}

def get_sector_for_ticker(ticker):
    """Get sector information for ticker from config"""
    try:
        for stock in config.TOP_STOCKS:
            if stock['symbol'].replace('.NS', '') == ticker.replace('.NS', ''):
                return stock.get('sector', 'Unknown')
        return 'Unknown'
    except:
        return 'Unknown'

def get_intraday_stock_data(ticker):
    """Get current day 5-minute data for analysis"""
    try:
        # Add .NS for NSE stocks
        symbol = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
        
        # Get current day data with 5-minute intervals
        stock = yf.Ticker(symbol)
        data = stock.history(period="5d", interval="5m")  # 5 days for more data
        
        if data.empty or len(data) < 50:
            return None
        
        # Clean data and ensure we have enough bars
        data = data.dropna()
        
        if len(data) < 50:
            return None
        
        return data
        
    except Exception as e:
        logger.error(f"Error fetching intraday data for {ticker}: {e}")
        return None

# Technical Indicators Implementation
def calculate_ema(prices, period):
    """Calculate Exponential Moving Average"""
    try:
        if len(prices) < period:
            return prices.ewm(span=len(prices)).mean()
        return prices.ewm(span=period).mean()
    except:
        return prices.copy()

def calculate_sma(prices, period):
    """Calculate Simple Moving Average"""
    try:
        return prices.rolling(window=period).mean()
    except:
        return prices.copy()

def calculate_rsi(prices, period=14):
    """Calculate RSI (Relative Strength Index)"""
    try:
        if len(prices) < period + 1:
            return pd.Series([50] * len(prices), index=prices.index)
        
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss.replace(0, 0.001)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.fillna(50)
    except Exception as e:
        return pd.Series([50] * len(prices), index=prices.index)

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD"""
    try:
        ema_fast = calculate_ema(prices, fast)
        ema_slow = calculate_ema(prices, slow)
        macd_line = ema_fast - ema_slow
        signal_line = calculate_ema(macd_line, signal)
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    except:
        return pd.Series([0] * len(prices)), pd.Series([0] * len(prices)), pd.Series([0] * len(prices))

def calculate_stochastic(high, low, close, k_period=14, d_period=3):
    """Calculate Stochastic Oscillator"""
    try:
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        k_percent = k_percent.fillna(50)
        
        d_percent = k_percent.rolling(window=d_period).mean()
        
        return k_percent, d_percent
    except:
        return pd.Series([50] * len(close)), pd.Series([50] * len(close))

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """Calculate Bollinger Bands"""
    try:
        sma = calculate_sma(prices, period)
        std = prices.rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return upper_band, lower_band, sma
    except:
        return prices.copy(), prices.copy(), prices.copy()

def calculate_atr(high, low, close, period=14):
    """Calculate Average True Range"""
    try:
        high_low = high - low
        high_close = np.abs(high - close.shift())
        low_close = np.abs(low - close.shift())
        
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = pd.Series(true_range).rolling(window=period).mean()
        
        return atr
    except:
        return pd.Series([1] * len(high))

def calculate_supertrend(high, low, close, period=10, multiplier=3):
    """Calculate Supertrend"""
    try:
        atr = calculate_atr(high, low, close, period)
        hl_avg = (high + low) / 2
        
        upper_band = hl_avg + (multiplier * atr)
        lower_band = hl_avg - (multiplier * atr)
        
        supertrend = pd.Series(index=close.index, dtype=float)
        direction = pd.Series(index=close.index, dtype=int)
        
        supertrend.iloc[0] = lower_band.iloc[0]
        direction.iloc[0] = 1
        
        for i in range(1, len(close)):
            if close.iloc[i] <= supertrend.iloc[i-1]:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1
            else:
                supertrend.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1
        
        return supertrend, direction
    except:
        return pd.Series([0] * len(close)), pd.Series([1] * len(close))

def calculate_hma(prices, period):
    """Calculate Hull Moving Average"""
    try:
        half_period = int(period / 2)
        sqrt_period = int(np.sqrt(period))
        
        wma1 = prices.rolling(window=half_period).apply(lambda x: np.average(x, weights=range(1, len(x)+1)))
        wma2 = prices.rolling(window=period).apply(lambda x: np.average(x, weights=range(1, len(x)+1)))
        
        raw_hma = 2 * wma1 - wma2
        hma = raw_hma.rolling(window=sqrt_period).apply(lambda x: np.average(x, weights=range(1, len(x)+1)))
        
        return hma.fillna(prices)
    except:
        return prices.copy()

def calculate_wave_trend(high, low, close, n1=9, n2=12):
    """Calculate Wave Trend Oscillator"""
    try:
        hlc3 = (high + low + close) / 3
        esa = calculate_ema(hlc3, n1)
        d = calculate_ema(abs(hlc3 - esa), n1)
        ci = (hlc3 - esa) / (0.015 * d)
        tci = calculate_ema(ci, n2)
        wt2 = calculate_sma(tci, 4)
        
        return tci, wt2
    except:
        return pd.Series([0] * len(close)), pd.Series([0] * len(close))

def detect_divergence(price_series, indicator_series, lookback=5):
    """Detect bullish/bearish divergence"""
    try:
        # Find local peaks and troughs
        price_peaks = argrelextrema(price_series.values, np.greater, order=lookback)[0]
        price_troughs = argrelextrema(price_series.values, np.less, order=lookback)[0]
        
        indicator_peaks = argrelextrema(indicator_series.values, np.greater, order=lookback)[0]
        indicator_troughs = argrelextrema(indicator_series.values, np.less, order=lookback)[0]
        
        bullish_div = False
        bearish_div = False
        
        # Check for bullish divergence (price lower low, indicator higher low)
        if len(price_troughs) >= 2 and len(indicator_troughs) >= 2:
            recent_price_trough = price_troughs[-1]
            prev_price_trough = price_troughs[-2]
            
            for ind_trough in indicator_troughs:
                if abs(ind_trough - recent_price_trough) <= lookback:
                    for prev_ind_trough in indicator_troughs:
                        if abs(prev_ind_trough - prev_price_trough) <= lookback:
                            if (price_series.iloc[recent_price_trough] < price_series.iloc[prev_price_trough] and
                                indicator_series.iloc[ind_trough] > indicator_series.iloc[prev_ind_trough]):
                                bullish_div = True
        
        # Check for bearish divergence (price higher high, indicator lower high)
        if len(price_peaks) >= 2 and len(indicator_peaks) >= 2:
            recent_price_peak = price_peaks[-1]
            prev_price_peak = price_peaks[-2]
            
            for ind_peak in indicator_peaks:
                if abs(ind_peak - recent_price_peak) <= lookback:
                    for prev_ind_peak in indicator_peaks:
                        if abs(prev_ind_peak - prev_price_peak) <= lookback:
                            if (price_series.iloc[recent_price_peak] > price_series.iloc[prev_price_peak] and
                                indicator_series.iloc[ind_peak] < indicator_series.iloc[prev_ind_peak]):
                                bearish_div = True
        
        return bullish_div, bearish_div
    except:
        return False, False

def calculate_obv(close, volume):
    """Calculate On Balance Volume"""
    try:
        obv = pd.Series(index=close.index, dtype=float)
        obv.iloc[0] = volume.iloc[0]
        
        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i-1]:
                obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]
        
        return obv
    except:
        return pd.Series([0] * len(close))

def calculate_vwap(high, low, close, volume):
    """Calculate Volume Weighted Average Price"""
    try:
        typical_price = (high + low + close) / 3
        cumulative_vol = volume.cumsum()
        cumulative_price_vol = (typical_price * volume).cumsum()
        
        vwap = cumulative_price_vol / cumulative_vol
        return vwap.fillna(close)
    except:
        return close.copy()

def calculate_multi_indicator_signals(data, debug=False):
    """
    Calculate all technical indicators and generate composite signals
    """
    try:
        high = data['High']
        low = data['Low']
        close = data['Close']
        volume = data['Volume']
        
        # Initialize signal scores
        long_score = 0
        short_score = 0
        signal_details = {}
        
        # 1. EMA Signals (Multiple timeframes)
        ema9 = calculate_ema(close, 9)
        ema21 = calculate_ema(close, 21)
        ema55 = calculate_ema(close, 55)
        ema100 = calculate_ema(close, 100)
        ema200 = calculate_ema(close, 200)
        
        # EMA Direction
        if close.iloc[-1] > ema200.iloc[-1]:
            long_score += 2
            signal_details['ema_trend'] = 'BULLISH'
        else:
            short_score += 2
            signal_details['ema_trend'] = 'BEARISH'
        
        # EMA Pressure (21 vs 55)
        if ema21.iloc[-1] > ema21.iloc[-2] and ema55.iloc[-1] < ema55.iloc[-2]:
            long_score += 2
        elif ema21.iloc[-1] < ema21.iloc[-2] and ema55.iloc[-1] > ema55.iloc[-2]:
            short_score += 2
        
        # 2. RSI Signals
        rsi = calculate_rsi(close)
        current_rsi = rsi.iloc[-1]
        
        # RSI Divergence
        rsi_bull_div, rsi_bear_div = detect_divergence(close[-20:], rsi[-20:])
        if rsi_bull_div:
            long_score += 4
            signal_details['rsi_divergence'] = 'BULLISH'
        elif rsi_bear_div:
            short_score += 4
            signal_details['rsi_divergence'] = 'BEARISH'
        
        # RSI Levels
        if current_rsi < 30:
            long_score += 1
        elif current_rsi > 70:
            short_score += 1
        
        # RSI 50 Cross
        if current_rsi > 50 and rsi.iloc[-2] < 50:
            long_score += 1
        elif current_rsi < 50 and rsi.iloc[-2] > 50:
            short_score += 1
        
        # 3. MACD Signals
        macd_line, signal_line, histogram = calculate_macd(close)
        
        # MACD Divergence
        macd_bull_div, macd_bear_div = detect_divergence(close[-20:], macd_line[-20:])
        if macd_bull_div:
            long_score += 3
        elif macd_bear_div:
            short_score += 3
        
        # MACD Histogram Pivot
        if (histogram.iloc[-1] > histogram.iloc[-2] and 
            histogram.iloc[-2] < histogram.iloc[-3] and 
            histogram.iloc[-1] < 0):
            long_score += 1
        elif (histogram.iloc[-1] < histogram.iloc[-2] and 
              histogram.iloc[-2] > histogram.iloc[-3] and 
              histogram.iloc[-1] > 0):
            short_score += 1
        
        # MACD Signal Cross
        if (macd_line.iloc[-1] > signal_line.iloc[-1] and 
            macd_line.iloc[-2] < signal_line.iloc[-2] and 
            signal_line.iloc[-1] < 0):
            long_score += 1
        elif (macd_line.iloc[-1] < signal_line.iloc[-1] and 
              macd_line.iloc[-2] > signal_line.iloc[-2] and 
              signal_line.iloc[-1] > 0):
            short_score += 1
        
        # 4. Supertrend Signals
        supertrend, st_direction = calculate_supertrend(high, low, close)
        
        # Supertrend Reversal
        if st_direction.iloc[-1] == 1 and st_direction.iloc[-2] == -1:
            long_score += 4
            signal_details['supertrend'] = 'REVERSAL_UP'
        elif st_direction.iloc[-1] == -1 and st_direction.iloc[-2] == 1:
            short_score += 4
            signal_details['supertrend'] = 'REVERSAL_DOWN'
        
        # 5. Wave Trend Signals
        wt1, wt2 = calculate_wave_trend(high, low, close)
        
        # Wave Trend Cross
        if (wt1.iloc[-1] > wt2.iloc[-1] and 
            wt1.iloc[-2] < wt2.iloc[-2] and 
            wt2.iloc[-1] < -10):
            long_score += 4
        elif (wt1.iloc[-1] < wt2.iloc[-1] and 
              wt1.iloc[-2] > wt2.iloc[-2] and 
              wt2.iloc[-1] > 10):
            short_score += 4
        
        # 6. Stochastic Signals
        stoch_k, stoch_d = calculate_stochastic(high, low, close)
        
        # Stochastic Cross
        if stoch_k.iloc[-1] > stoch_d.iloc[-1] and stoch_k.iloc[-2] < stoch_d.iloc[-2]:
            long_score += 1
        elif stoch_k.iloc[-1] < stoch_d.iloc[-1] and stoch_k.iloc[-2] > stoch_d.iloc[-2]:
            short_score += 1
        
        # 7. Bollinger Bands Signals
        bb_upper, bb_lower, bb_middle = calculate_bollinger_bands(close)
        
        if close.iloc[-1] < bb_lower.iloc[-1]:
            long_score += 1
        elif close.iloc[-1] > bb_upper.iloc[-1]:
            short_score += 1
        
        # 8. Hull Moving Average Signals
        hma = calculate_hma(close, 100)
        
        # HMA Cross
        if close.iloc[-1] > hma.iloc[-1] and close.iloc[-2] < hma.iloc[-2]:
            long_score += 1
        elif close.iloc[-1] < hma.iloc[-1] and close.iloc[-2] > hma.iloc[-2]:
            short_score += 1
        
        # HMA Pivot
        if hma.iloc[-1] > hma.iloc[-2] and hma.iloc[-2] < hma.iloc[-3]:
            long_score += 3
        elif hma.iloc[-1] < hma.iloc[-2] and hma.iloc[-2] > hma.iloc[-3]:
            short_score += 3
        
        # 9. Volume Indicators
        obv = calculate_obv(close, volume)
        vwap = calculate_vwap(high, low, close, volume)
        
        # OBV Divergence
        obv_bull_div, obv_bear_div = detect_divergence(close[-20:], obv[-20:])
        if obv_bull_div:
            long_score += 2
        elif obv_bear_div:
            short_score += 2
        
        # VWAP Trend
        if ema21.iloc[-1] > vwap.iloc[-1]:
            long_score += 1
        else:
            short_score += 1
        
        # 10. ATR Reversal
        atr = calculate_atr(high, low, close)
        
        # Determine final signal
        signal_details.update({
            'long_score': long_score,
            'short_score': short_score,
            'current_rsi': current_rsi,
            'current_price': close.iloc[-1],
            'ema200': ema200.iloc[-1],
            'supertrend_value': supertrend.iloc[-1],
            'supertrend_direction': st_direction.iloc[-1],
            'vwap_value': vwap.iloc[-1],
            'hma_value': hma.iloc[-1]
        })
        
        return signal_details
        
    except Exception as e:
        logger.error(f"Error in multi-indicator signals calculation: {e}")
        return None

def analyze_stock_multi_indicator(ticker, strong_threshold=10, weak_threshold=8, debug=False):
    """
    Multi-indicator stock analysis
    """
    try:
        # Get sector information
        sector = get_sector_for_ticker(ticker)
        
        if debug:
            print(f"Analyzing {ticker} (Multi-Indicator Strategy) - Sector: {sector}...")
        
        # Get current day 5-minute data
        data = get_intraday_stock_data(ticker)
        if data is None:
            return None
        
        # Calculate multi-indicator signals
        signals = calculate_multi_indicator_signals(data, debug)
        if signals is None:
            return None
        
        # Get latest values
        latest = data.iloc[-1]
        current_price = latest['Close']
        current_volume = latest['Volume']
        
        # Determine signal strength and type with trend filter
        long_score = signals['long_score']
        short_score = signals['short_score']
        ema_trend = signals.get('ema_trend', 'NEUTRAL')
        
        signal_type = 'HOLD'
        signal_strength = 'WEAK'
        
        # Apply trend filter: Only allow BUY signals in BULLISH trend, SELL signals in BEARISH trend
        if long_score >= strong_threshold and ema_trend == 'BULLISH':
            signal_type = 'STRONG_BUY'
            signal_strength = 'STRONG'
        elif long_score >= weak_threshold and ema_trend == 'BULLISH':
            signal_type = 'BUY'
            signal_strength = 'WEAK'
        elif short_score >= strong_threshold and ema_trend == 'BEARISH':
            signal_type = 'STRONG_SELL'
            signal_strength = 'STRONG'
        elif short_score >= weak_threshold and ema_trend == 'BEARISH':
            signal_type = 'SELL'
            signal_strength = 'WEAK'
        
        # Calculate position sizing and risk management
        entry_price = current_price
        
        if 'BUY' in signal_type:
            stop_loss = current_price * 0.97  # 3% stop loss
            target_price = current_price * 1.09  # 9% target (3:1 R:R)
        elif 'SELL' in signal_type:
            stop_loss = current_price * 1.03  # 3% stop loss
            target_price = current_price * 0.91  # 9% target (3:1 R:R)
        else:
            stop_loss = current_price
            target_price = current_price
        
        # Volume analysis
        if len(data) >= 20:
            avg_volume = data['Volume'].rolling(20).mean().iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        else:
            volume_ratio = 1.0
        
        # Position sizing (1% risk)
        capital = 100000
        risk_amount = capital * 0.01
        risk_per_share = abs(entry_price - stop_loss)
        position_size = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
        
        result = {
            'ticker': ticker,
            'sector': sector,
            'signal_type': signal_type,
            'signal_strength': signal_strength,
            'long_score': long_score,
            'short_score': short_score,
            'current_price': float(current_price),
            'entry_price': float(entry_price),
            'target_price': float(target_price),
            'stop_loss': float(stop_loss),
            'volume_ratio': float(volume_ratio),
            'rsi': float(signals['current_rsi']),
            'position_size': int(position_size),
            'risk_per_share': float(risk_per_share),
            'ema200': float(signals['ema200']),
            'supertrend': float(signals['supertrend_value']),
            'vwap': float(signals['vwap_value']),
            'hma': float(signals['hma_value']),
            'ema_trend': signals.get('ema_trend', 'NEUTRAL'),
            'supertrend_signal': signals.get('supertrend', 'NONE'),
            'rsi_divergence': signals.get('rsi_divergence', 'NONE'),
            'timestamp': get_uk_time().strftime('%H:%M:%S'),
            'ist_time': get_ist_time().strftime('%H:%M:%S'),
            'bars_in_session': len(data)
        }
        
        if debug:
            print(f"   Current Price: {current_price:.2f}")
            print(f"   Long Score: {long_score}, Short Score: {short_score}")
            print(f"   Signal: {signal_type} ({signal_strength})")
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing {ticker}: {e}")
        return None

def analyze_all_stocks_multi_indicator(strong_threshold=10, weak_threshold=8, max_workers=8, debug=False):
    """Analyze all stocks with Multi-Indicator strategy"""
    
    # Get tickers from config
    tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
    
    logger.info(f"Analyzing {len(tickers)} stocks with Multi-Indicator strategy...")
    
    all_signals = []
    
    # Analyze stocks
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(analyze_stock_multi_indicator, ticker, strong_threshold, weak_threshold, debug): ticker 
            for ticker in tickers
        }
        
        completed = 0
        successful = 0
        failed = 0
        
        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            completed += 1
            
            try:
                result = future.result(timeout=15)
                if result:
                    all_signals.append(result)
                    successful += 1
                else:
                    failed += 1
            except concurrent.futures.TimeoutError:
                failed += 1
                logger.warning(f"{ticker} - Timeout")
            except Exception as e:
                failed += 1
                logger.warning(f"{ticker} - Error: {str(e)[:30]}")
        
        logger.info(f"Completed: {successful} successful, {failed} failed")
    
    return all_signals

def display_multi_indicator_signals(all_signals):
    """Display Multi-Indicator signals"""
    
    if not all_signals:
        print(f"\nNo Multi-Indicator signals found!")
        return
    
    # Filter entry signals only
    entry_signals = [s for s in all_signals if s['signal_type'] in ['STRONG_BUY', 'BUY', 'STRONG_SELL', 'SELL']]
    
    if not entry_signals:
        print(f"\nNo entry signals found!")
        return
    
    # Sort by signal strength and score
    def sort_key(signal):
        strength_weight = 2 if signal['signal_strength'] == 'STRONG' else 1
        score = max(signal['long_score'], signal['short_score'])
        return strength_weight * score
    
    entry_signals.sort(key=sort_key, reverse=True)
    
    uk_time = get_uk_time().strftime('%Y-%m-%d %H:%M:%S')
    ist_time = get_ist_time().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n{'='*120}")
    print(f"MULTI-INDICATOR STRATEGY SIGNALS")
    print(f"UK Time: {uk_time} | IST Time: {ist_time}")
    print(f"5-Minute Charts | Strong Threshold: {entry_signals[0]['long_score'] if entry_signals[0]['signal_type'].startswith('STRONG') else 'N/A'}")
    print(f"{'='*120}")
    
    # Prepare table
    table_data = []
    headers = ['#', 'Ticker', 'Sector', 'Signal', 'Strength', 'Score', 'Current', 'Target', 
              'Stop', 'RSI', 'Volume', 'EMA Trend', 'Position', 'UK Time']
    
    for i, signal in enumerate(entry_signals[:25], 1):  # Show top 25
        
        score_display = f"{signal['long_score']}-{signal['short_score']}"
        
        table_data.append([
            i,
            signal['ticker'],
            signal['sector'],
            signal['signal_type'],
            signal['signal_strength'],
            score_display,
            f"Rs{signal['current_price']:.2f}",
            f"Rs{signal['target_price']:.2f}",
            f"Rs{signal['stop_loss']:.2f}",
            f"{signal['rsi']:.0f}",
            f"{signal['volume_ratio']:.1f}x",
            signal['ema_trend'],
            signal['position_size'],
            signal['timestamp']
        ])
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Summary
    strong_buy = [s for s in entry_signals if s['signal_type'] == 'STRONG_BUY']
    buy = [s for s in entry_signals if s['signal_type'] == 'BUY']
    strong_sell = [s for s in entry_signals if s['signal_type'] == 'STRONG_SELL']
    sell = [s for s in entry_signals if s['signal_type'] == 'SELL']
    
    print(f"\nMULTI-INDICATOR SUMMARY:")
    print(f"   STRONG BUY signals: {len(strong_buy)}")
    print(f"   BUY signals: {len(buy)}")
    print(f"   STRONG SELL signals: {len(strong_sell)}")
    print(f"   SELL signals: {len(sell)}")
    print(f"   Total entry signals: {len(entry_signals)}")
    print(f"   Total stocks analyzed: {len(all_signals)}")
    
    if entry_signals:
        avg_bars = sum(s['bars_in_session'] for s in all_signals) / len(all_signals)
        avg_volume = sum(s['volume_ratio'] for s in entry_signals) / len(entry_signals)
        avg_long_score = sum(s['long_score'] for s in entry_signals) / len(entry_signals)
        avg_short_score = sum(s['short_score'] for s in entry_signals) / len(entry_signals)
        print(f"   Average bars per stock: {avg_bars:.0f} (5-min candles)")
        print(f"   Average volume ratio: {avg_volume:.1f}x")
        print(f"   Average scores: Long {avg_long_score:.1f}, Short {avg_short_score:.1f}")

def run_multi_indicator_analysis(strong_threshold=10, weak_threshold=8):
    """Execute Multi-Indicator analysis and display results"""
    uk_time = get_uk_time().strftime('%Y-%m-%d %H:%M:%S')
    ist_time = get_ist_time().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f"Running Multi-Indicator analysis at UK: {uk_time} | IST: {ist_time}")
    
    # Clear screen for better display
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Check if market is open
    market_status = is_market_open()
    
    if not market_status['is_open']:
        print(f"Indian Stock Market is CLOSED")
        print(f"Current UK Time: {market_status.get('uk_time', 'N/A')}")
        print(f"Current IST Time: {market_status.get('ist_time', 'N/A')}")
        print(f"Market Hours (UK): {market_status.get('uk_market_start', 'N/A')} - {market_status.get('uk_market_end', 'N/A')}")
        print(f"Market Hours (IST): {market_status.get('ist_market_start', 'N/A')} - {market_status.get('ist_market_end', 'N/A')}")
        return
    
    print(f"Indian Stock Market is OPEN")
    print(f"Current UK Time: {market_status.get('uk_time', 'N/A')}")
    print(f"Current IST Time: {market_status.get('ist_time', 'N/A')}")
    
    # Analyze all stocks
    all_signals = analyze_all_stocks_multi_indicator(strong_threshold, weak_threshold, max_workers=8)
    
    if all_signals:
        # Display signals
        display_multi_indicator_signals(all_signals)
        
        # Save results to CSV
        df = pd.DataFrame(all_signals)
        df.to_csv("multi_indicator_signals.csv", index=False)
        logger.info("Saved Multi-Indicator signals to multi_indicator_signals.csv")
    else:
        logger.error("No signals generated")

def main():
    """Main function with Multi-Indicator monitoring"""
    parser = argparse.ArgumentParser(description="Multi-Indicator Strategy Analyzer")
    
    parser.add_argument('--strong-threshold', type=int, default=10, 
                       help='Strong signal threshold (default: 10)')
    parser.add_argument('--weak-threshold', type=int, default=8, 
                       help='Weak signal threshold (default: 8)')
    parser.add_argument('--interval', type=int, default=3, 
                       help='Update interval in minutes (default: 3)')
    parser.add_argument('--run-once', action='store_true', 
                       help='Run once and exit (no continuous monitoring)')
    parser.add_argument('--test-single', type=str, 
                       help='Test analysis on a single ticker for debugging')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug output')
    
    args = parser.parse_args()
    
    if args.test_single:
        print(f"TESTING SINGLE TICKER: {args.test_single}")
        print("Multi-Indicator Strategy")
        print("="*50)
        result = analyze_stock_multi_indicator(
            args.test_single, 
            args.strong_threshold, 
            args.weak_threshold,
            debug=True
        )
        if result:
            print(f"\nRESULT:")
            print(f"  Signal: {result['signal_type']} ({result['signal_strength']})")
            print(f"  Sector: {result['sector']}")
            print(f"  Scores: Long {result['long_score']}, Short {result['short_score']}")
            print(f"  Current Price: Rs{result['current_price']:.2f}")
            print(f"  EMA Trend: {result['ema_trend']}")
            print(f"  RSI: {result['rsi']:.1f}")
        else:
            print(f"\nNo result for {args.test_single}")
        return
    
    if args.run_once:
        print("Running Multi-Indicator analysis once...")
        run_multi_indicator_analysis(args.strong_threshold, args.weak_threshold)
        return
    
    # Continuous monitoring during market hours
    uk_time = get_uk_time().strftime('%H:%M:%S')
    ist_time = get_ist_time().strftime('%H:%M:%S')
    logger.info(f"Starting Multi-Indicator analyzer | UK: {uk_time} | IST: {ist_time} | Updates every {args.interval} minutes")
    print(f"Multi-Indicator Parameters: Strong Threshold={args.strong_threshold}, Weak Threshold={args.weak_threshold}")
    
    # Run immediately on startup
    run_multi_indicator_analysis(args.strong_threshold, args.weak_threshold)
    
    # Schedule to run every N minutes
    schedule.every(args.interval).minutes.do(lambda: run_multi_indicator_analysis(args.strong_threshold, args.weak_threshold))
    
    # Keep the script running and execute scheduled jobs
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds
    except KeyboardInterrupt:
        logger.info("Multi-Indicator analyzer stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error in main loop: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()