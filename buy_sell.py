#!/usr/bin/env python
# optimized_yahoo_prediction.py - Optimized Yahoo Finance Multi-Timeframe Scanner

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
import logging
from dataclasses import dataclass
import time
from typing import Dict, Optional, List

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Configuration
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
            {'symbol': 'POWERGRID', 'sector': 'Power'},
            {'symbol': 'JSWSTEEL', 'sector': 'Steel'}
        ]
        OUTPUT_DIR = 'output'
    config = DefaultConfig()

@dataclass
class TimeframeData:
    """Optimized timeframe configuration"""
    interval: str
    period: str
    name: str
    weight: float
    min_bars: int

# Optimized timeframe configurations
TIMEFRAMES = {
    '5m': TimeframeData('5m', '5d', '5-Min', 0.2, 50),
    '15m': TimeframeData('15m', '5d', '15-Min', 0.3, 40),
    '1h': TimeframeData('1h', '1mo', '1-Hour', 0.35, 30),
    '1d': TimeframeData('1d', '3mo', 'Daily', 0.4, 20)
}

@dataclass
class PineScriptConfig:
    stronglongscore: int = 4
    strongshortscore: int = 4
    weaklongscore: int = 2
    weakshortscore: int = 2
    alternatesignals: bool = False  # Changed default to False for more signals
    tradetrendoption: bool = False
    
    # Pine Script importance weights
    emadirectionimportance: int = 2
    emapushpullimportance: int = 2
    supertrenddirimportance: int = 0
    supertrendrevimportance: int = 4
    psardirimportance: int = 0
    psarrevimportance: int = 3
    hmacloseposimportance: int = 1
    hmapivotimportance: int = 3
    rsidivimportance: int = 4
    rsilevelimportance: int = 0
    rsidirectionimportance: int = 1
    macddivimportance: int = 0
    histpivotimportance: int = 1
    macdcrosssignalimportance: int = 1
    wtdivimportance: int = 0
    wtcrosssignalimportance: int = 4
    sdivimportance: int = 1
    scrosssignalimportance: int = 1
    bbcontimportance: int = 0
    atrrevimportance: int = 1
    rviposimportance: int = 3
    rvidivimportance: int = 4
    srcrossimportance: int = 0
    obvdivimportance: int = 0
    cmfcrossimportance: int = 0
    cmflevimportance: int = 0
    vwapcrossimportance: int = 0
    vwaptrendimportance: int = 0
    engulfingcandleimportance: int = 0

def get_sector_for_ticker(ticker):
    try:
        for stock in config.TOP_STOCKS:
            if stock['symbol'].replace('.NS', '') == ticker.replace('.NS', ''):
                return stock.get('sector', 'Unknown')
        return 'Unknown'
    except:
        return 'Unknown'

def get_optimized_yahoo_data(ticker: str, timeframe: TimeframeData) -> Optional[pd.DataFrame]:
    """Optimized Yahoo Finance data fetching with retry logic"""
    try:
        symbol = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
        
        # Multiple attempts with different periods for robustness
        periods_to_try = [timeframe.period]
        
        # Add alternative periods based on timeframe
        if timeframe.interval == '1d':
            periods_to_try.extend(['6mo', '1y'])
        elif timeframe.interval == '1h':
            periods_to_try.extend(['2mo', '3mo'])
        elif timeframe.interval in ['5m', '15m']:
            periods_to_try.extend(['3d', '7d'])
        
        for period in periods_to_try:
            try:
                stock = yf.Ticker(symbol)
                data = stock.history(period=period, interval=timeframe.interval, auto_adjust=True, prepost=False)
                
                if data.empty:
                    continue
                
                # Clean the data
                data = data.dropna()
                
                # Check if we have enough data
                if len(data) >= timeframe.min_bars:
                    logger.debug(f"✓ {ticker} {timeframe.name}: {len(data)} bars (period: {period})")
                    return data
                else:
                    logger.debug(f"Insufficient data for {ticker} {timeframe.name}: {len(data)} bars (period: {period})")
                    
            except Exception as e:
                logger.debug(f"Failed to get {ticker} data for period {period}: {e}")
                continue
        
        logger.warning(f"Could not get sufficient data for {ticker} on {timeframe.name}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching data for {ticker} on {timeframe.name}: {e}")
        return None

# Technical Analysis Functions (same as before but optimized)
def ta_ema(series, length):
    return series.ewm(span=length, adjust=False).mean()

def ta_sma(series, length):
    return series.rolling(window=length).mean()

def ta_rsi(series, length):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    alpha = 1.0 / length
    avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
    avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def ta_supertrend(factor, atrPeriod, high, low, close):
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/atrPeriod, adjust=False).mean()
    
    hl2 = (high + low) / 2
    upper_band = hl2 + factor * atr
    lower_band = hl2 - factor * atr
    
    supertrend = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=int)
    
    supertrend.iloc[0] = lower_band.iloc[0]
    direction.iloc[0] = -1
    
    for i in range(1, len(close)):
        if lower_band.iloc[i] > lower_band.iloc[i-1] or close.iloc[i-1] < lower_band.iloc[i-1]:
            lower_band.iloc[i] = lower_band.iloc[i]
        else:
            lower_band.iloc[i] = lower_band.iloc[i-1]
            
        if upper_band.iloc[i] < upper_band.iloc[i-1] or close.iloc[i-1] > upper_band.iloc[i-1]:
            upper_band.iloc[i] = upper_band.iloc[i]
        else:
            upper_band.iloc[i] = upper_band.iloc[i-1]
        
        if close.iloc[i] <= lower_band.iloc[i]:
            direction.iloc[i] = 1
            supertrend.iloc[i] = upper_band.iloc[i]
        elif close.iloc[i] >= upper_band.iloc[i]:
            direction.iloc[i] = -1
            supertrend.iloc[i] = lower_band.iloc[i]
        else:
            direction.iloc[i] = direction.iloc[i-1]
            if direction.iloc[i] == -1:
                supertrend.iloc[i] = lower_band.iloc[i]
            else:
                supertrend.iloc[i] = upper_band.iloc[i]
    
    return supertrend, direction

def ta_wma(series, length):
    weights = np.arange(1, length + 1)
    return series.rolling(window=length).apply(lambda x: np.dot(x, weights) / weights.sum() if len(x) == length else np.nan, raw=True)

def calculate_hma(close, length):
    half_length = max(1, int(length / 2))
    sqrt_length = max(1, int(np.sqrt(length)))
    
    wma_half = ta_wma(close, half_length)
    wma_full = ta_wma(close, length)
    raw_hma = 2 * wma_half - wma_full
    hma = ta_wma(raw_hma, sqrt_length)
    
    return hma

def ta_sar(start, increment, maximum, high, low, close):
    psar = pd.Series(index=high.index, dtype=float)
    if len(high) == 0:
        return psar
        
    psar.iloc[0] = low.iloc[0]
    
    af = start
    trend = 1
    ep = high.iloc[0]
    
    for i in range(1, len(high)):
        if trend == 1:
            psar.iloc[i] = psar.iloc[i-1] + af * (ep - psar.iloc[i-1])
            if low.iloc[i] < psar.iloc[i]:
                trend = -1
                psar.iloc[i] = ep
                ep = low.iloc[i]
                af = start
            else:
                if high.iloc[i] > ep:
                    ep = high.iloc[i]
                    af = min(af + increment, maximum)
        else:
            psar.iloc[i] = psar.iloc[i-1] + af * (ep - psar.iloc[i-1])
            if high.iloc[i] > psar.iloc[i]:
                trend = 1
                psar.iloc[i] = ep
                ep = high.iloc[i]
                af = start
            else:
                if low.iloc[i] < ep:
                    ep = low.iloc[i]
                    af = min(af + increment, maximum)
    
    return psar

def ta_stoch(close, high, low, length):
    lowest_low = low.rolling(window=length).min()
    highest_high = high.rolling(window=length).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    return k.fillna(50)

def calculate_optimized_pine_signals(data, config: PineScriptConfig):
    """Optimized Pine Script signal calculation"""
    try:
        high = data['High']
        low = data['Low']
        close = data['Close']
        open_price = data['Open']
        volume = data['Volume']
        
        # Adjust lengths based on available data
        data_len = len(data)
        
        # EMAs with dynamic adjustment
        len1 = min(9, data_len // 4)
        len2 = min(21, data_len // 3)
        len3 = min(55, data_len // 2)
        len4 = min(100, int(data_len * 0.8))
        len5 = min(200, data_len - 1)
        len111 = len5
        
        out1 = ta_ema(close, len1) if len1 > 0 else close
        out2 = ta_ema(close, len2) if len2 > 0 else close
        out3 = ta_ema(close, len3) if len3 > 0 else close
        out4 = ta_ema(close, len4) if len4 > 0 else close
        out5 = ta_ema(close, len5) if len5 > 0 else close
        out111 = ta_ema(close, len111) if len111 > 0 else close
        
        # Supertrend
        atrPeriod = min(10, data_len // 3)
        factor = 3
        if atrPeriod > 1:
            supertrend, direction = ta_supertrend(factor, atrPeriod, high, low, close)
        else:
            supertrend = close
            direction = pd.Series(-1, index=close.index)
        
        # HMA
        len6 = min(100, int(data_len * 0.7))
        if len6 > 3:
            hma = calculate_hma(close, len6)
        else:
            hma = close
        
        # Parabolic SAR
        psar = ta_sar(0.02, 0.01, 0.2, high, low, close)
        
        # RSI
        len11 = min(14, data_len // 3)
        if len11 > 1:
            osc11 = ta_rsi(close, len11)
        else:
            osc11 = pd.Series(50, index=close.index)
        
        # MACD
        fast_length12 = min(12, data_len // 4)
        slow_length12 = min(26, data_len // 3)
        signal_length12 = min(9, data_len // 5)
        
        if fast_length12 > 0 and slow_length12 > fast_length12:
            fast_ma12 = ta_ema(close, fast_length12)
            slow_ma12 = ta_ema(close, slow_length12)
            macd = fast_ma12 - slow_ma12
            if signal_length12 > 0:
                signal = ta_ema(macd, signal_length12)
            else:
                signal = macd
            hist = macd - signal
        else:
            macd = signal = hist = pd.Series(0, index=close.index)
        
        # Wave Trend
        n1 = min(9, data_len // 4)
        n2 = min(12, data_len // 3)
        if n1 > 0 and n2 > 0:
            ap = (high + low + close) / 3
            esa = ta_ema(ap, n1)
            d1 = ta_ema(abs(ap - esa), n1)
            ci = (ap - esa) / (0.015 * d1 + 1e-10)  # Avoid division by zero
            tci = ta_ema(ci, n2)
            wt1 = tci
            wt2 = ta_sma(wt1, 4) if len(wt1) >= 4 else wt1
        else:
            wt1 = wt2 = pd.Series(0, index=close.index)
        
        # Stochastic
        periodK14 = min(14, data_len // 3)
        smoothK14 = min(3, data_len // 10)
        periodD14 = min(3, data_len // 10)
        
        if periodK14 > 0:
            k14_raw = ta_stoch(close, high, low, periodK14)
            k14 = ta_sma(k14_raw, smoothK14) if smoothK14 > 0 else k14_raw
            d14 = ta_sma(k14, periodD14) if periodD14 > 0 else k14
        else:
            k14 = d14 = pd.Series(50, index=close.index)
        
        # Bollinger Bands
        length1 = min(20, data_len // 2)
        mult1 = 2.0
        if length1 > 1:
            basis = ta_sma(close, length1)
            dev = mult1 * close.rolling(length1).std()
            upper = basis + dev
            lower = basis - dev
        else:
            upper = lower = close
        
        # ATR
        length2 = min(1, data_len)
        mult2 = 1.85
        if length2 > 0:
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = mult2 * ta_ema(tr, length2)
            
            longStop = high.rolling(length2).max() - atr
            shortStop = low.rolling(length2).min() + atr
            
            dir_series = pd.Series(1, index=close.index)
            for i in range(1, len(close)):
                if close.iloc[i] > shortStop.iloc[i-1]:
                    dir_series.iloc[i] = 1
                elif close.iloc[i] < longStop.iloc[i-1]:
                    dir_series.iloc[i] = -1
                else:
                    dir_series.iloc[i] = dir_series.iloc[i-1]
            
            buySignal = (dir_series == 1) & (dir_series.shift(1) == -1)
            sellSignal = (dir_series == -1) & (dir_series.shift(1) == 1)
        else:
            buySignal = sellSignal = pd.Series(False, index=close.index)
        
        # RVI
        length15 = min(12, data_len // 3)
        len15 = min(14, data_len // 3)
        if length15 > 1 and len15 > 1:
            change = close.diff()
            stddev15 = change.rolling(length15).std()
            stddev15 = stddev15.fillna(0)
            upper15 = ta_ema((change > 0).astype(int) * stddev15, len15)
            lower15 = ta_ema((change <= 0).astype(int) * stddev15, len15)
            rvi = 100 * upper15 / (upper15 + lower15 + 1e-10)
            rvi = rvi.fillna(50)
        else:
            rvi = pd.Series(50, index=close.index)
        
        # CMF
        length19 = min(50, data_len)
        if length19 > 1:
            high_low_diff = high - low
            high_low_diff = high_low_diff.replace(0, 1e-10)  # Avoid division by zero
            ad19 = ((2*close-low-high)/high_low_diff)*volume
            ad19 = ad19.fillna(0)
            cmf = ad19.rolling(length19).sum() / (volume.rolling(length19).sum() + 1e-10)
            cmf = cmf.fillna(0)
        else:
            cmf = pd.Series(0, index=close.index)
        
        # VWAP approximation
        vwapValue = (high + low + close) / 3
        
        # Simplified divergence indicators
        bullCond11 = bearCond11 = pd.Series(False, index=close.index)
        bullCond12 = bearCond12 = pd.Series(False, index=close.index)
        bullCond13 = bearCond13 = pd.Series(False, index=close.index)
        bullCond14 = bearCond14 = pd.Series(False, index=close.index)
        bullCond15 = bearCond15 = pd.Series(False, index=close.index)
        bullCond18 = bearCond18 = pd.Series(False, index=close.index)
        
        # Candlestick patterns (simplified)
        C_EngulfingBullish = pd.Series(False, index=close.index)
        C_EngulfingBearish = pd.Series(False, index=close.index)
        
        # Trend signals
        mabuy = out111 > out111.shift(1)
        masell = out111 < out111.shift(1)
        
        # Calculate all signal components
        emadirectionup = (out5 < close).astype(int) * config.emadirectionimportance
        emadirectiondown = (out5 > close).astype(int) * config.emadirectionimportance
        emapushup = ((out2 > out2.shift(1)) & (out3 < out3.shift(1))).astype(int) * config.emapushpullimportance
        emapulldown = ((out2 < out2.shift(1)) & (out3 > out3.shift(1))).astype(int) * config.emapushpullimportance
        
        supertrendup = (direction < 0).astype(int) * config.supertrenddirimportance
        supertrenddown = (direction > 0).astype(int) * config.supertrenddirimportance
        supertrendrevup = ((direction < 0) & (direction.shift(1) > 0)).astype(int) * config.supertrendrevimportance
        supertrendrevdown = ((direction > 0) & (direction.shift(1) < 0)).astype(int) * config.supertrendrevimportance
        
        psardirup = (psar < close).astype(int) * config.psardirimportance
        psardirdown = (psar > close).astype(int) * config.psardirimportance
        psarrevup = ((psar < close) & (psar.shift(1) > close.shift(1))).astype(int) * config.psarrevimportance
        psarrevdown = ((psar > close) & (psar.shift(1) < close.shift(1))).astype(int) * config.psarrevimportance
        
        hmacloseposup = ((hma < close) & hma.shift(1).notna()).astype(int) * config.hmacloseposimportance
        hmacloseposdown = (hma > close).astype(int) * config.hmacloseposimportance
        hmapivotup = ((hma > hma.shift(1)) & (hma.shift(1) < hma.shift(2))).astype(int) * config.hmapivotimportance
        hmapivotdown = ((hma < hma.shift(1)) & (hma.shift(1) > hma.shift(2))).astype(int) * config.hmapivotimportance
        
        rsidivup = (bullCond11 | bullCond11.shift(1) | bullCond11.shift(2)).astype(int) * config.rsidivimportance
        rsidivdown = (bearCond11 | bearCond11.shift(1) | bearCond11.shift(2)).astype(int) * config.rsidivimportance
        rsioversold = (osc11 < 30).astype(int) * config.rsilevelimportance
        rsioverbought = (osc11 > 70).astype(int) * config.rsilevelimportance
        rsicrossup = (((osc11 > 50) & (osc11.shift(1) < 50)) | ((osc11 > 50) & (osc11.shift(2) < 50))).astype(int) * config.rsidirectionimportance
        rsicrossdown = (((osc11 < 50) & (osc11.shift(1) > 50)) | ((osc11 < 50) & (osc11.shift(2) > 50))).astype(int) * config.rsidirectionimportance
        
        macddivup = (bullCond12 | bullCond12.shift(1) | bullCond12.shift(2)).astype(int) * config.macddivimportance
        macddivdown = (bearCond12 | bearCond12.shift(1) | bearCond12.shift(2)).astype(int) * config.macddivimportance
        histpivotup = ((hist > hist.shift(1)) & (hist.shift(1) < hist.shift(2)) & (hist < 0)).astype(int) * config.histpivotimportance
        histpivotdown = ((hist < hist.shift(1)) & (hist.shift(1) > hist.shift(2)) & (hist > 0)).astype(int) * config.histpivotimportance
        macdcrosssignalup = ((macd > signal) & (macd.shift(1) < signal.shift(1)) & (signal < 0)).astype(int) * config.macdcrosssignalimportance
        macdcrosssignaldown = ((macd < signal) & (macd.shift(1) > signal.shift(1)) & (signal > 0)).astype(int) * config.macdcrosssignalimportance
        
        wtdivup = (bullCond13 | bullCond13.shift(1) | bullCond13.shift(2)).astype(int) * config.wtdivimportance
        wtdivdown = (bearCond13 | bearCond13.shift(1) | bearCond13.shift(2)).astype(int) * config.wtdivimportance
        wtcrosssignalup = ((wt1 > wt2) & (wt1.shift(1) < wt2.shift(1)) & (wt2 < -10)).astype(int) * config.wtcrosssignalimportance
        wtcrosssignaldown = ((wt1 < wt2) & (wt1.shift(1) > wt2.shift(1)) & (wt2 > 10)).astype(int) * config.wtcrosssignalimportance
        
        sdivup = (bullCond14 | bullCond14.shift(1) | bullCond14.shift(2)).astype(int) * config.sdivimportance
        sdivdown = (bearCond14 | bearCond14.shift(1) | bearCond14.shift(2)).astype(int) * config.sdivimportance
        scrosssignalup = ((k14 > d14) & (k14.shift(1) < d14.shift(1))).astype(int) * config.scrosssignalimportance
        scrosssignaldown = ((k14 < d14) & (k14.shift(1) > d14.shift(1))).astype(int) * config.scrosssignalimportance
        
        bbcontup = (close < lower).astype(int) * config.bbcontimportance
        bbcontdown = (close > upper).astype(int) * config.bbcontimportance
        
        atrrevup = buySignal.astype(int) * config.atrrevimportance
        atrrevdown = sellSignal.astype(int) * config.atrrevimportance
        
        rviposup = ((rvi > 25) & (rvi.shift(1) < 40)).astype(int) * config.rviposimportance
        rviposdown = ((rvi < 75) & (rvi.shift(1) > 60)).astype(int) * config.rviposimportance
        rvidivup = (bullCond15 | bullCond15.shift(1) | bullCond15.shift(2)).astype(int) * config.rvidivimportance
        rvidivdown = (bearCond15 | bearCond15.shift(1) | bearCond15.shift(2)).astype(int) * config.rvidivimportance
        
        srcrossup = srcrossdown = pd.Series(0, index=close.index)
        obvdivup = obvdivdown = pd.Series(0, index=close.index)
        cmfcrossup = ((cmf > 0) & (cmf.shift(1) < 0)).astype(int) * config.cmfcrossimportance
        cmfcrossdown = ((cmf < 0) & (cmf.shift(1) > 0)).astype(int) * config.cmfcrossimportance
        cmflevup = (cmf > 0).astype(int) * config.cmflevimportance
        cmflevdown = (cmf < 0).astype(int) * config.cmflevimportance
        vwapcrossup = ((hma < vwapValue) & (hma.shift(1) > vwapValue.shift(1))).astype(int) * config.vwapcrossimportance
        vwapcrossdown = ((hma > vwapValue) & (hma.shift(1) < vwapValue.shift(1))).astype(int) * config.vwapcrossimportance
        vwaptrendup = (out2 > vwapValue).astype(int) * config.vwaptrendimportance
        vwaptrenddown = (out2 < vwapValue).astype(int) * config.vwaptrendimportance
        bulleng = C_EngulfingBullish.astype(int) * config.engulfingcandleimportance
        beareng = C_EngulfingBearish.astype(int) * config.engulfingcandleimportance
        
        # Signal aggregation
        stronglongentrysignal = (
            emadirectionup + emapushup + supertrendup + supertrendrevup + psardirup + psarrevup + 
            hmacloseposup + hmapivotup + rsidivup + rsioversold + rsicrossup + macddivup + 
            histpivotup + macdcrosssignalup + wtdivup + wtcrosssignalup + sdivup + scrosssignalup + 
            bbcontup + atrrevup + rviposup + rvidivup + srcrossup + obvdivup + cmfcrossup + 
            cmflevup + vwapcrossup + vwaptrendup + bulleng
        ) >= config.stronglongscore
        
        strongshortentrysignal = (
            emadirectiondown + emapulldown + supertrenddown + supertrendrevdown + psardirdown + psarrevdown + 
            hmacloseposdown + hmapivotdown + rsidivdown + rsioverbought + rsicrossdown + macddivdown + 
            histpivotdown + macdcrosssignaldown + wtdivdown + wtcrosssignaldown + sdivdown + scrosssignaldown + 
            bbcontdown + atrrevdown + rviposdown + rvidivdown + srcrossdown + obvdivdown + cmfcrossdown + 
            cmflevdown + vwapcrossdown + vwaptrenddown + beareng
        ) >= config.strongshortscore
        
        weaklongentrysignal = (
            emadirectionup + emapushup + supertrendup + supertrendrevup + psardirup + psarrevup + 
            hmacloseposup + hmapivotup + rsidivup + rsioversold + rsicrossup + macddivup + 
            histpivotup + macdcrosssignalup + wtdivup + wtcrosssignalup + sdivup + scrosssignalup + 
            bbcontup + atrrevup + rviposup + rvidivup + srcrossup + obvdivup + cmfcrossup + 
            cmflevup + vwapcrossup + vwaptrendup + bulleng
        ) >= config.weaklongscore
        
        weakshortentrysignal = (
            emadirectiondown + emapulldown + supertrenddown + supertrendrevdown + psardirdown + psarrevdown + 
            hmacloseposdown + hmapivotdown + rsidivdown + rsioverbought + rsicrossdown + macddivdown + 
            histpivotdown + macdcrosssignaldown + wtdivdown + wtcrosssignaldown + sdivdown + scrosssignaldown + 
            bbcontdown + atrrevdown + rviposdown + rvidivdown + srcrossdown + obvdivdown + cmfcrossdown + 
            cmflevdown + vwapcrossdown + vwaptrenddown + beareng
        ) >= config.weakshortscore
        
        # Position tracking logic
        if config.alternatesignals:
            pos = 0
            pos_series = []
            longentry_list = []
            shortentry_list = []
            
            for i in range(len(close)):
                if stronglongentrysignal.iloc[i] and pos <= 0:
                    pos = 1
                if strongshortentrysignal.iloc[i] and pos >= 0:
                    pos = -1
                
                pos_series.append(pos)
                
                if i == 0:
                    longentry_list.append(False)
                    shortentry_list.append(False)
                else:
                    longentry_list.append(pos == 1 and pos_series[i-1] != 1)
                    shortentry_list.append(pos == -1 and pos_series[i-1] != -1)
            
            pos_series = pd.Series(pos_series, index=close.index)
            longentry = pd.Series(longentry_list, index=close.index)
            shortentry = pd.Series(shortentry_list, index=close.index)
            
            alternatelong = longentry
            alternateshort = shortentry
        else:
            alternatelong = stronglongentrysignal
            alternateshort = strongshortentrysignal
            pos_series = pd.Series(0, index=close.index)
        
        # Apply trend filter if enabled
        if config.tradetrendoption:
            final_long = alternatelong & mabuy
            final_short = alternateshort & masell
        else:
            final_long = alternatelong
            final_short = alternateshort
        
        # Calculate scores
        long_score_sum = (
            emadirectionup + emapushup + supertrendup + supertrendrevup + psardirup + psarrevup + 
            hmacloseposup + hmapivotup + rsidivup + rsioversold + rsicrossup + macddivup + 
            histpivotup + macdcrosssignalup + wtdivup + wtcrosssignalup + sdivup + scrosssignalup + 
            bbcontup + atrrevup + rviposup + rvidivup + srcrossup + obvdivup + cmfcrossup + 
            cmflevup + vwapcrossup + vwaptrendup + bulleng
        )
        
        short_score_sum = (
            emadirectiondown + emapulldown + supertrenddown + supertrendrevdown + psardirdown + psarrevdown + 
            hmacloseposdown + hmapivotdown + rsidivdown + rsioverbought + rsicrossdown + macddivdown + 
            histpivotdown + macdcrosssignaldown + wtdivdown + wtcrosssignaldown + sdivdown + scrosssignaldown + 
            bbcontdown + atrrevdown + rviposdown + rvidivdown + srcrossdown + obvdivdown + cmfcrossdown + 
            cmflevdown + vwapcrossdown + vwaptrenddown + beareng
        )
        
        return {
            'final_long': final_long,
            'final_short': final_short,
            'stronglongentrysignal': stronglongentrysignal,
            'strongshortentrysignal': strongshortentrysignal,
            'weaklongentrysignal': weaklongentrysignal,
            'weakshortentrysignal': weakshortentrysignal,
            'pos_series': pos_series,
            'long_score': long_score_sum,
            'short_score': short_score_sum,
            'mabuy': mabuy,
            'masell': masell,
            'rsi': osc11,
            'current_price': close.iloc[-1] if len(close) > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Error in optimized Pine Script calculation: {e}")
        return None

def analyze_stock_optimized_multi_timeframe(ticker, pine_config, timeframes_to_analyze):
    """Optimized multi-timeframe analysis"""
    try:
        sector = get_sector_for_ticker(ticker)
        results = {}
        
        for tf_key in timeframes_to_analyze:
            if tf_key not in TIMEFRAMES:
                continue
                
            timeframe = TIMEFRAMES[tf_key]
            data = get_optimized_yahoo_data(ticker, timeframe)
            
            if data is None or len(data) < timeframe.min_bars:
                results[tf_key] = None
                continue
            
            signals = calculate_optimized_pine_signals(data, pine_config)
            if signals is None:
                results[tf_key] = None
                continue
            
            latest_idx = -1
            
            signal_type = 'HOLD'
            signal_strength = 'NONE'
            signal_score = 0
            
            if signals['final_long'].iloc[latest_idx]:
                if signals['stronglongentrysignal'].iloc[latest_idx]:
                    signal_type = 'STRONG_BUY'
                    signal_strength = 'STRONG'
                    signal_score = 2
                elif signals['weaklongentrysignal'].iloc[latest_idx]:
                    signal_type = 'BUY'
                    signal_strength = 'WEAK'
                    signal_score = 1
            elif signals['final_short'].iloc[latest_idx]:
                if signals['strongshortentrysignal'].iloc[latest_idx]:
                    signal_type = 'STRONG_SELL'
                    signal_strength = 'STRONG'
                    signal_score = -2
                elif signals['weakshortentrysignal'].iloc[latest_idx]:
                    signal_type = 'SELL'
                    signal_strength = 'WEAK'
                    signal_score = -1
            
            long_score_val = signals['long_score'].iloc[latest_idx]
            short_score_val = signals['short_score'].iloc[latest_idx]
            
            if hasattr(long_score_val, '__iter__') and not isinstance(long_score_val, str):
                long_score_val = float(long_score_val.sum()) if hasattr(long_score_val, 'sum') else float(long_score_val[0])
            if hasattr(short_score_val, '__iter__') and not isinstance(short_score_val, str):
                short_score_val = float(short_score_val.sum()) if hasattr(short_score_val, 'sum') else float(short_score_val[0])
            
            results[tf_key] = {
                'timeframe': timeframe.name,
                'signal_type': signal_type,
                'signal_strength': signal_strength,
                'signal_score': signal_score,
                'long_score': int(long_score_val),
                'short_score': int(short_score_val),
                'rsi': float(signals['rsi'].iloc[latest_idx]),
                'current_price': float(signals['current_price']),
                'trend_direction': 'BULLISH' if signals['mabuy'].iloc[latest_idx] else 'BEARISH',
                'position_series': int(signals['pos_series'].iloc[latest_idx]),
                'bars_analyzed': len(data)
            }
        
        # Calculate weighted prediction
        total_weight = 0
        weighted_score = 0
        active_timeframes = []
        
        for tf_key, result in results.items():
            if result is not None:
                weight = TIMEFRAMES[tf_key].weight
                total_weight += weight
                weighted_score += result['signal_score'] * weight
                active_timeframes.append(tf_key)
        
        if total_weight > 0:
            final_prediction_score = weighted_score / total_weight
            
            if final_prediction_score >= 1.5:
                final_prediction = 'STRONG_BUY'
            elif final_prediction_score >= 0.5:
                final_prediction = 'BUY'
            elif final_prediction_score <= -1.5:
                final_prediction = 'STRONG_SELL'
            elif final_prediction_score <= -0.5:
                final_prediction = 'SELL'
            else:
                final_prediction = 'HOLD'
        else:
            final_prediction = 'NO_DATA'
            final_prediction_score = 0
        
        return {
            'ticker': ticker,
            'sector': sector,
            'final_prediction': final_prediction,
            'prediction_score': round(final_prediction_score, 2),
            'timeframes': results,
            'active_timeframes': active_timeframes,
            'confidence': min(len(active_timeframes) / len(timeframes_to_analyze), 1.0)
        }
        
    except Exception as e:
        logger.error(f"Error analyzing {ticker}: {e}")
        return None

def analyze_all_stocks_optimized(pine_config, timeframes_to_analyze, max_workers=6):
    """Optimized batch analysis"""
    tickers = [stock['symbol'] for stock in config.TOP_STOCKS]
    logger.info(f"Analyzing {len(tickers)} stocks across {len(timeframes_to_analyze)} timeframes...")
    
    all_predictions = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(analyze_stock_optimized_multi_timeframe, ticker, pine_config, timeframes_to_analyze): ticker 
            for ticker in tickers
        }
        
        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                result = future.result(timeout=60)
                if result:
                    all_predictions.append(result)
                    logger.info(f"✓ {ticker}: {result['final_prediction']} (Score: {result['prediction_score']:+.1f}) Conf: {result['confidence']:.0%}")
                else:
                    logger.warning(f"✗ {ticker}: No prediction generated")
            except Exception as e:
                logger.error(f"✗ {ticker}: {str(e)[:50]}")
    
    return all_predictions

def display_filtered_strong_signals(all_predictions, timeframes_analyzed):
    """Display only strong directional signals with trend alignment"""
    if not all_predictions:
        print("\nNo predictions found!")
        return
    
    # Filter for strong signals only
    strong_predictions = [p for p in all_predictions if p['final_prediction'] in ['STRONG_BUY', 'STRONG_SELL']]
    
    if not strong_predictions:
        print("\nNo strong directional signals found!")
        return
    
    # Further filter for trend-aligned signals
    clean_buy_signals = []
    clean_sell_signals = []
    
    for pred in strong_predictions:
        is_clean_signal = True
        trend_alignment = None
        
        # Check each timeframe for trend consistency
        for tf_key, tf_data in pred['timeframes'].items():
            if tf_data is not None:
                if pred['final_prediction'] == 'STRONG_BUY':
                    # For BUY signals, ensure no bearish trends
                    if tf_data['trend_direction'] == 'BEARISH':
                        is_clean_signal = False
                        break
                elif pred['final_prediction'] == 'STRONG_SELL':
                    # For SELL signals, ensure no bullish trends
                    if tf_data['trend_direction'] == 'BULLISH':
                        is_clean_signal = False
                        break
        
        if is_clean_signal:
            if pred['final_prediction'] == 'STRONG_BUY':
                clean_buy_signals.append(pred)
            else:
                clean_sell_signals.append(pred)
    
    # Sort by prediction score
    clean_buy_signals.sort(key=lambda x: x['prediction_score'], reverse=True)
    clean_sell_signals.sort(key=lambda x: abs(x['prediction_score']), reverse=True)
    
    # Display results
    print(f"\n{'='*170}")
    print(f"🎯 PINE SCRIPT SIGNALS (Top {min(8, len(clean_buy_signals + clean_sell_signals))} unique)")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Filtered for: Strong signals with consistent trend alignment")
    print(f"{'='*170}")
    
    all_clean_signals = clean_buy_signals + clean_sell_signals
    
    if not all_clean_signals:
        print("\nNo clean directional signals found!")
        print("(All strong signals have conflicting trend directions across timeframes)")
        return
    
    # Display header
    header_format = "{:>3} | {:>10} | {:>8} | {:>11} | {:>8} | {:>7} | {:>7} | {:>9} | {:>9} | {:>9} | {:>4} | {:>5} | {:>6} | {:>5} | {:>6} | {:>3}"
    print(header_format.format(
        "#", "Ticker", "Sector", "Signal", "Strength", "L-Score", "S-Score", 
        "Entry", "Stop", "Target", "RSI", "Trend", "SuperT", "WaveT", "Volume", "Pos"
    ))
    print("-" * 170)
    
    # Display data rows
    for i, pred in enumerate(all_clean_signals[:8], 1):
        # Get representative data from the primary timeframe
        rep_tf = None
        for tf in ['1d', '1h', '15m', '5m']:
            if tf in pred['timeframes'] and pred['timeframes'][tf] is not None:
                rep_tf = pred['timeframes'][tf]
                break
        
        if rep_tf:
            # Calculate entry/stop/target prices
            current_price = rep_tf['current_price']
            
            if pred['final_prediction'] == 'STRONG_BUY':
                entry_price = current_price + 1
                stop_loss = current_price * 0.98  # 2% stop loss
                target_price = current_price * 1.06  # 6% target
            else:  # STRONG_SELL
                entry_price = current_price - 1
                stop_loss = current_price * 1.02  # 2% stop loss
                target_price = current_price * 0.94  # 6% target
            
            # Get trend info
            trend = rep_tf['trend_direction'][:5]
            supertrend_dir = "BULL" if pred['final_prediction'] == 'STRONG_BUY' else "BEAR"
            wave_status = "UP" if pred['final_prediction'] == 'STRONG_BUY' else "DOWN"
            
            print(header_format.format(
                i,
                pred['ticker'][:10],
                pred['sector'][:8],
                pred['final_prediction'][:11],
                "STRONG",
                rep_tf['long_score'],
                rep_tf['short_score'],
                f"₹{entry_price:.2f}",
                f"₹{stop_loss:.2f}",
                f"₹{target_price:.2f}",
                f"{rep_tf['rsi']:.0f}",
                trend,
                supertrend_dir,
                wave_status,
                "1.0x",  # Simplified volume
                rep_tf['position_series']
            ))
    
    print("=" * 170)
    
    # Summary
    print(f"\n📈 FILTERED SIGNAL SUMMARY:")
    print(f"   🟢 Clean STRONG BUY: {len(clean_buy_signals):>2}")
    print(f"   🔴 Clean STRONG SELL: {len(clean_sell_signals):>2}")
    print(f"   📊 Total clean signals: {len(all_clean_signals):>2}")
    print(f"   📋 Total analyzed: {len(all_predictions):>2}")
    print(f"   🎯 Clean signal rate: {(len(all_clean_signals)/len(all_predictions)*100):.1f}%")
    
    # Sector breakdown for clean signals
    if all_clean_signals:
        sector_breakdown = {}
        for pred in all_clean_signals:
            sector = pred['sector']
            signal_type = pred['final_prediction']
            
            if sector not in sector_breakdown:
                sector_breakdown[sector] = {'STRONG_BUY': 0, 'STRONG_SELL': 0}
            
            sector_breakdown[sector][signal_type] += 1
        
        print(f"\n📊 SECTOR BREAKDOWN (Clean Signals Only):")
        for sector, signals in sorted(sector_breakdown.items()):
            if signals['STRONG_BUY'] > 0 or signals['STRONG_SELL'] > 0:
                print(f"   {sector:>12}: {signals['STRONG_BUY']} BUY, {signals['STRONG_SELL']} SELL")

def display_optimized_results(all_predictions, timeframes_analyzed):
    """Enhanced display with both filtered and full results"""
    if not all_predictions:
        print("\nNo predictions found!")
        return
    
    # First show the filtered clean signals
    display_filtered_strong_signals(all_predictions, timeframes_analyzed)
    
    # Then show summary of all signals
    signal_predictions = [p for p in all_predictions if p['final_prediction'] in ['STRONG_BUY', 'BUY', 'STRONG_SELL', 'SELL']]
    
    if signal_predictions:
        print(f"\n" + "="*80)
        print(f"FULL SIGNAL SUMMARY (Including Mixed Trends)")
        print(f"="*80)
        
        strong_buy = len([p for p in signal_predictions if p['final_prediction'] == 'STRONG_BUY'])
        buy = len([p for p in signal_predictions if p['final_prediction'] == 'BUY'])
        strong_sell = len([p for p in signal_predictions if p['final_prediction'] == 'STRONG_SELL'])
        sell = len([p for p in signal_predictions if p['final_prediction'] == 'SELL'])
        
        print(f"   All STRONG BUY: {strong_buy:>2} | All BUY: {buy:>2}")
        print(f"   All STRONG SELL: {strong_sell:>2} | All SELL: {sell:>2}")
        print(f"   Total all signals: {len(signal_predictions):>2}")
        
        # Show top 5 mixed signals that didn't make the clean list
        mixed_signals = [p for p in signal_predictions if p['final_prediction'] in ['STRONG_BUY', 'STRONG_SELL']]
        clean_tickers = set()
        
        # Get clean signal tickers
        for pred in all_predictions:
            if pred['final_prediction'] in ['STRONG_BUY', 'STRONG_SELL']:
                is_clean = True
                for tf_key, tf_data in pred['timeframes'].items():
                    if tf_data is not None:
                        if pred['final_prediction'] == 'STRONG_BUY' and tf_data['trend_direction'] == 'BEARISH':
                            is_clean = False
                            break
                        elif pred['final_prediction'] == 'STRONG_SELL' and tf_data['trend_direction'] == 'BULLISH':
                            is_clean = False
                            break
                if is_clean:
                    clean_tickers.add(pred['ticker'])
        
        mixed_signals = [p for p in mixed_signals if p['ticker'] not in clean_tickers]
        
        if mixed_signals:
            print(f"\nTop 5 Mixed Signals (Strong signal but conflicting trends):")
            for i, pred in enumerate(mixed_signals[:5], 1):
                print(f"  {i}. {pred['ticker']:>10}: {pred['final_prediction']} (Score: {pred['prediction_score']:+.1f})")
    
    else:
        # Show distribution if no signals
        prediction_counts = {}
        for p in all_predictions:
            pred = p['final_prediction']
            prediction_counts[pred] = prediction_counts.get(pred, 0) + 1
        
        print(f"\nAll Predictions Summary (Total: {len(all_predictions)}):")
        for pred, count in prediction_counts.items():
            percentage = (count / len(all_predictions)) * 100
            print(f"  {pred:>12}: {count:>3} ({percentage:>5.1f}%)")

def main():
    parser = argparse.ArgumentParser(description="Optimized Yahoo Finance Multi-Timeframe Scanner")
    parser.add_argument('--strong-long', type=int, default=4, help='Strong BUY score threshold')
    parser.add_argument('--strong-short', type=int, default=4, help='Strong SELL score threshold')
    parser.add_argument('--weak-long', type=int, default=2, help='Weak BUY score threshold')
    parser.add_argument('--weak-short', type=int, default=2, help='Weak SELL score threshold')
    parser.add_argument('--trend-filter', action='store_true', help='Enable trend filter')
    parser.add_argument('--alternate-signals', action='store_true', help='Use alternate signals logic (default: False)')
    parser.add_argument('--timeframes', nargs='+', choices=['5m', '15m', '1h', '1d'], default=['1h', '1d'], help='Timeframes to analyze')
    parser.add_argument('--test-single', type=str, help='Test single ticker')
    parser.add_argument('--max-workers', type=int, default=6, help='Max concurrent workers')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    
    args = parser.parse_args()
    
    pine_config = PineScriptConfig(
        stronglongscore=args.strong_long,
        strongshortscore=args.strong_short,
        weaklongscore=args.weak_long,
        weakshortscore=args.weak_short,
        tradetrendoption=args.trend_filter,
        alternatesignals=args.alternate_signals
    )
    
    timeframes_to_analyze = args.timeframes
    
    print(f"OPTIMIZED YAHOO FINANCE SCANNER")
    print(f"Thresholds: Strong={args.strong_long}/{args.strong_short}, Weak={args.weak_long}/{args.weak_short}")
    print(f"Alternate Signals: {args.alternate_signals}")
    print(f"Timeframes: {', '.join([TIMEFRAMES[tf].name for tf in timeframes_to_analyze])}")
    print("="*80)
    
    if args.test_single:
        print(f"TESTING: {args.test_single}")
        result = analyze_stock_optimized_multi_timeframe(args.test_single, pine_config, timeframes_to_analyze)
        if result:
            print(f"\nRESULT: {result['final_prediction']} (Score: {result['prediction_score']:+.2f})")
            print(f"Confidence: {result['confidence']:.0%}")
            
            print(f"\nTimeframe Breakdown:")
            for tf, data in result['timeframes'].items():
                if data:
                    print(f"  {TIMEFRAMES[tf].name:>8}: {data['signal_type']:>12} | L:{data['long_score']:>2} S:{data['short_score']:>2} | RSI:{data['rsi']:>5.1f} | {data['bars_analyzed']} bars")
                else:
                    print(f"  {TIMEFRAMES[tf].name:>8}: {'NO_DATA':>12}")
        else:
            print("No result generated")
        return
    
    all_predictions = analyze_all_stocks_optimized(pine_config, timeframes_to_analyze, args.max_workers)
    
    if all_predictions:
        display_optimized_results(all_predictions, timeframes_to_analyze)
        
        # Save results
        df_results = []
        for pred in all_predictions:
            row = {
                'ticker': pred['ticker'],
                'sector': pred['sector'],
                'final_prediction': pred['final_prediction'],
                'prediction_score': pred['prediction_score'],
                'confidence': pred['confidence']
            }
            
            for tf in timeframes_to_analyze:
                tf_data = pred['timeframes'].get(tf)
                if tf_data:
                    row[f'{tf}_signal'] = tf_data['signal_type']
                    row[f'{tf}_long_score'] = tf_data['long_score']
                    row[f'{tf}_short_score'] = tf_data['short_score']
                    row[f'{tf}_rsi'] = tf_data['rsi']
                    row[f'{tf}_trend'] = tf_data['trend_direction']
                    row[f'{tf}_bars'] = tf_data['bars_analyzed']
                else:
                    row[f'{tf}_signal'] = 'NO_DATA'
                    row[f'{tf}_long_score'] = 0
                    row[f'{tf}_short_score'] = 0
                    row[f'{tf}_rsi'] = 0
                    row[f'{tf}_trend'] = 'UNKNOWN'
                    row[f'{tf}_bars'] = 0
            
            df_results.append(row)
        
        df = pd.DataFrame(df_results)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filename = f"optimized_predictions_{timestamp}.csv"
        df.to_csv(filename, index=False)
        print(f"\nResults saved to: {filename}")
        
    else:
        print("No predictions generated")

if __name__ == "__main__":
    main()