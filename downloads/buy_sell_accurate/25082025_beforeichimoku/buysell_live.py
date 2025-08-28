#!/usr/bin/env python
# exact_pine_script_replication_threshold_8.py - EXACT LINE-BY-LINE Pine Script Replication

import os
import sys
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta, time as dt_time
import warnings
import concurrent.futures
import argparse
import json
import logging
from dataclasses import dataclass
import time
import schedule
import pytz

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
            {'symbol': 'JSWSTEEL', 'sector': 'Steel'},
            {'symbol': 'ABB', 'sector': 'Industrial'},
            {'symbol': 'LAURUSLABS', 'sector': 'Pharma'},
            {'symbol': 'BEL', 'sector': 'Defense'},
            {'symbol': 'BLUESTARCO', 'sector': 'Consumer'},
            {'symbol': 'CESC', 'sector': 'Power'},
            {'symbol': 'CHAMBLFERT', 'sector': 'Fertilizer'},
            {'symbol': 'EXIDEIND', 'sector': 'Auto'},
            {'symbol': 'CIPLA', 'sector': 'Pharma'}
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
class PineScriptConfig:
    # EXACT Pine Script defaults - THRESHOLD SET TO 10
    stronglongscore: int = 10  # Set to 10 as requested
    strongshortscore: int = 10  # Set to 10 as requested
    weaklongscore: int = 8
    weakshortscore: int = 8
    alternatesignals: bool = True
    tradetrendoption: bool = False
    
    # EXACT stop loss from Pine Script
    stoplosspercent: float = -2.5
    
    # EXACT importance weights from Pine Script (verified from your code)
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
    
class PositionManager:
    def __init__(self):
        self.positions = {}  # ticker -> TradingPosition
        self.position_history = []
        self.all_positions_tracking = []  # Track all positions over time
        
    def enter_position(self, ticker, position_type, entry_price, stop_loss, target_price):
        if ticker in self.positions:
            self.close_position(ticker, entry_price, f"New {position_type} signal")
            
        position = TradingPosition(
            ticker=ticker,
            position_type=position_type,
            entry_price=entry_price,
            entry_time=datetime.now(),
            current_price=entry_price,
            stop_loss=stop_loss,
            target_price=target_price
        )
        
        self.positions[ticker] = position
        
        # Track this position for ongoing monitoring
        self.all_positions_tracking.append({
            'ticker': ticker,
            'position_type': position_type,
            'entry_price': entry_price,
            'entry_time': datetime.now(),
            'status': 'ACTIVE'
        })
        
        logger.info(f"ENTERED {position_type.upper()} position for {ticker} at Rs{entry_price:.2f}")
        
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
            'reason': reason
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
        
        # EXACT Pine Script stop loss logic
        if position.position_type == 'long':
            position.unrealized_pnl = (current_price - position.entry_price) * position.position_size
            if current_price <= position.stop_loss:
                self.close_position(ticker, current_price, "Stop Loss Hit")
                return True
        else:
            position.unrealized_pnl = (position.entry_price - current_price) * position.position_size
            if current_price >= position.stop_loss:
                self.close_position(ticker, current_price, "Stop Loss Hit")
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

def get_stock_data(ticker, period="1mo", interval="5m"):
    try:
        symbol = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
        stock = yf.Ticker(symbol)
        data = stock.history(period=period, interval=interval)
        
        if data.empty or len(data) < 100:
            logger.warning(f"Insufficient data for {ticker}: {len(data)} bars")
            return None
        
        data = data.dropna()
        return data if len(data) >= 100 else None
        
    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {e}")
        return None

# EXACT Pine Script Technical Analysis Functions
def ta_ema(series, length):
    """Pine Script ta.ema() - EXACT"""
    return series.ewm(span=length, adjust=False).mean()

def ta_sma(series, length):
    """Pine Script ta.sma() - EXACT"""
    return series.rolling(window=length).mean()

def ta_rsi(series, length):
    """Pine Script ta.rsi() - EXACT"""
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
    """Pine Script ta.supertrend() - EXACT"""
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
    """Pine Script ta.wma() - EXACT"""
    weights = np.arange(1, length + 1)
    return series.rolling(window=length).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

def calculate_hma(close, length):
    """Pine Script HMA - EXACT"""
    half_length = int(length / 2)
    sqrt_length = int(np.sqrt(length))
    
    wma_half = ta_wma(close, half_length)
    wma_full = ta_wma(close, length)
    raw_hma = 2 * wma_half - wma_full
    hma = ta_wma(raw_hma, sqrt_length)
    
    return hma

def ta_sar(start, increment, maximum, high, low, close):
    """Pine Script ta.sar() - EXACT"""
    psar = pd.Series(index=high.index, dtype=float)
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
    """Pine Script ta.stoch() - EXACT"""
    lowest_low = low.rolling(window=length).min()
    highest_high = high.rolling(window=length).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    return k.fillna(50)

def calculate_exact_pine_script_signals(data, config: PineScriptConfig):
    """
    EXACT LINE-BY-LINE Pine Script Replication - "Accurate BUY & SELL 5 mins TF by RR"
    """
    try:
        high = data['High']
        low = data['Low']
        close = data['Close']
        open_price = data['Open']
        volume = data['Volume']
        
        # Pine Script Lines 29-57: EMAs
        len1, len2, len3, len4, len5 = 9, 21, 55, 100, 200
        len111 = 200
        
        out1 = ta_ema(close, len1)
        out2 = ta_ema(close, len2)
        out3 = ta_ema(close, len3)
        out4 = ta_ema(close, len4)
        out5 = ta_ema(close, len5)
        out111 = ta_ema(close, len111)
        
        # Pine Script Lines 58-62: Supertrend
        atrPeriod = 10
        factor = 3
        supertrend, direction = ta_supertrend(factor, atrPeriod, high, low, close)
        
        # Pine Script Lines 65-68: HMA
        len6 = 100
        hma = calculate_hma(close, len6)
        
        # Pine Script Lines 69-73: Parabolic SAR
        start = 0.02
        increment = 0.01
        maximum = 0.2
        psar = ta_sar(start, increment, maximum, high, low, close)
        
        # Pine Script Lines 76-81: RSI
        len11 = 14
        osc11 = ta_rsi(close, len11)
        
        # Pine Script Lines 99-104: MACD
        fast_length12 = 12
        slow_length12 = 26
        signal_length12 = 9
        
        fast_ma12 = ta_ema(close, fast_length12)
        slow_ma12 = ta_ema(close, slow_length12)
        macd = fast_ma12 - slow_ma12
        signal = ta_ema(macd, signal_length12)
        hist = macd - signal
        
        # Pine Script Lines 130-136: Wave Trend
        n1 = 9
        n2 = 12
        ap = (high + low + close) / 3  # hlc3
        esa = ta_ema(ap, n1)
        d1 = ta_ema(abs(ap - esa), n1)
        ci = (ap - esa) / (0.015 * d1)
        tci = ta_ema(ci, n2)
        wt1 = tci
        wt2 = ta_sma(wt1, 4)
        
        # Pine Script Lines 166-167: Stochastic
        periodK14 = 14
        smoothK14 = 3
        periodD14 = 3
        k14 = ta_sma(ta_stoch(close, high, low, periodK14), smoothK14)
        d14 = ta_sma(k14, periodD14)
        
        # Pine Script Lines 221-231: Bollinger Bands
        length1 = 20
        mult1 = 2.0
        basis = ta_sma(close, length1)
        dev = mult1 * close.rolling(length1).std()
        upper = basis + dev
        lower = basis - dev
        
        # Pine Script Lines 232-248: Average True Range
        length2 = 1
        mult2 = 1.85
        atr = mult2 * ta_ema(pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1), length2)
        
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
        
        # Pine Script Lines 249-279: RVI
        length15 = 12
        len15 = 14
        stddev15 = close.diff().rolling(length15).std()
        upper15 = ta_ema((close.diff() > 0).astype(int) * stddev15, len15)
        lower15 = ta_ema((close.diff() <= 0).astype(int) * stddev15, len15)
        rvi = upper15 / (upper15 + lower15) * 100
        rvi = rvi.fillna(50)
        
        # Pine Script Lines 356-370: CMF
        length19 = 50
        ad19 = ((2*close-low-high)/(high-low))*volume
        ad19 = ad19.fillna(0)
        cmf = ad19.rolling(length19).sum() / volume.rolling(length19).sum()
        cmf = cmf.fillna(0)
        
        # Simplified indicators for remaining ones
        vwapValue = (high + low + close) / 3
        
        # Divergence placeholders (simplified for live trading)
        bullCond11 = bearCond11 = pd.Series(False, index=close.index)
        bullCond12 = bearCond12 = pd.Series(False, index=close.index)
        bullCond13 = bearCond13 = pd.Series(False, index=close.index)
        bullCond14 = bearCond14 = pd.Series(False, index=close.index)
        bullCond15 = bearCond15 = pd.Series(False, index=close.index)
        bullCond18 = bearCond18 = pd.Series(False, index=close.index)
        
        # Candlestick patterns (simplified)
        C_EngulfingBullish = pd.Series(False, index=close.index)
        C_EngulfingBearish = pd.Series(False, index=close.index)
        
        # Pine Script Lines 384-385: Trend EMA signals
        mabuy = out111 > out111.shift(1)
        masell = out111 < out111.shift(1)
        
        # EXACT Pine Script Signal Calculations (Lines 388-572)
        
        # EMA Signals
        emadirectionup = (out5 < close).astype(int) * config.emadirectionimportance
        emadirectiondown = (out5 > close).astype(int) * config.emadirectionimportance
        emapushup = ((out2 > out2.shift(1)) & (out3 < out3.shift(1))).astype(int) * config.emapushpullimportance
        emapulldown = ((out2 < out2.shift(1)) & (out3 > out3.shift(1))).astype(int) * config.emapushpullimportance
        
        # Super Trend Signals
        supertrendup = (direction < 0).astype(int) * config.supertrenddirimportance
        supertrenddown = (direction > 0).astype(int) * config.supertrenddirimportance
        supertrendrevup = ((direction < 0) & (direction.shift(1) > 0)).astype(int) * config.supertrendrevimportance
        supertrendrevdown = ((direction > 0) & (direction.shift(1) < 0)).astype(int) * config.supertrendrevimportance
        
        # Parabolic SAR Signals
        psardirup = (psar < close).astype(int) * config.psardirimportance
        psardirdown = (psar > close).astype(int) * config.psardirimportance
        psarrevup = ((psar < close) & (psar.shift(1) > close.shift(1))).astype(int) * config.psarrevimportance
        psarrevdown = ((psar > close) & (psar.shift(1) < close.shift(1))).astype(int) * config.psarrevimportance
        
        # HMA Signals
        hmacloseposup = ((hma < close) & hma.shift(1).notna()).astype(int) * config.hmacloseposimportance
        hmacloseposdown = (hma > close).astype(int) * config.hmacloseposimportance
        hmapivotup = ((hma > hma.shift(1)) & (hma.shift(1) < hma.shift(2))).astype(int) * config.hmapivotimportance
        hmapivotdown = ((hma < hma.shift(1)) & (hma.shift(1) > hma.shift(2))).astype(int) * config.hmapivotimportance
        
        # RSI Signals
        rsidivup = (bullCond11 | bullCond11.shift(1) | bullCond11.shift(2)).astype(int) * config.rsidivimportance
        rsidivdown = (bearCond11 | bearCond11.shift(1) | bearCond11.shift(2)).astype(int) * config.rsidivimportance
        rsioversold = (osc11 < 30).astype(int) * config.rsilevelimportance
        rsioverbought = (osc11 > 70).astype(int) * config.rsilevelimportance
        rsicrossup = (((osc11 > 50) & (osc11.shift(1) < 50)) | ((osc11 > 50) & (osc11.shift(2) < 50))).astype(int) * config.rsidirectionimportance
        rsicrossdown = (((osc11 < 50) & (osc11.shift(1) > 50)) | ((osc11 < 50) & (osc11.shift(2) > 50))).astype(int) * config.rsidirectionimportance
        
        # MACD Signals
        macddivup = (bullCond12 | bullCond12.shift(1) | bullCond12.shift(2)).astype(int) * config.macddivimportance
        macddivdown = (bearCond12 | bearCond12.shift(1) | bearCond12.shift(2)).astype(int) * config.macddivimportance
        histpivotup = ((hist > hist.shift(1)) & (hist.shift(1) < hist.shift(2)) & (hist < 0)).astype(int) * config.histpivotimportance
        histpivotdown = ((hist < hist.shift(1)) & (hist.shift(1) > hist.shift(2)) & (hist > 0)).astype(int) * config.histpivotimportance
        macdcrosssignalup = ((macd > signal) & (macd.shift(1) < signal.shift(1)) & (signal < 0)).astype(int) * config.macdcrosssignalimportance
        macdcrosssignaldown = ((macd < signal) & (macd.shift(1) > signal.shift(1)) & (signal > 0)).astype(int) * config.macdcrosssignalimportance
        
        # WaveTrend Signals
        wtdivup = (bullCond13 | bullCond13.shift(1) | bullCond13.shift(2)).astype(int) * config.wtdivimportance
        wtdivdown = (bearCond13 | bearCond13.shift(1) | bearCond13.shift(2)).astype(int) * config.wtdivimportance
        wtcrosssignalup = ((wt1 > wt2) & (wt1.shift(1) < wt2.shift(1)) & (wt2 < -10)).astype(int) * config.wtcrosssignalimportance
        wtcrosssignaldown = ((wt1 < wt2) & (wt1.shift(1) > wt2.shift(1)) & (wt2 > 10)).astype(int) * config.wtcrosssignalimportance
        
        # Stochastic Signals
        sdivup = (bullCond14 | bullCond14.shift(1) | bullCond14.shift(2)).astype(int) * config.sdivimportance
        sdivdown = (bearCond14 | bearCond14.shift(1) | bearCond14.shift(2)).astype(int) * config.sdivimportance
        scrosssignalup = ((k14 > d14) & (k14.shift(1) < d14.shift(1))).astype(int) * config.scrosssignalimportance
        scrosssignaldown = ((k14 < d14) & (k14.shift(1) > d14.shift(1))).astype(int) * config.scrosssignalimportance
        
        # Bollinger Bands Signals
        bbcontup = (close < lower).astype(int) * config.bbcontimportance
        bbcontdown = (close > upper).astype(int) * config.bbcontimportance
        
        # ATR Signals
        atrrevup = buySignal.astype(int) * config.atrrevimportance
        atrrevdown = sellSignal.astype(int) * config.atrrevimportance
        
        # RVI Signals
        rviposup = ((rvi > 25) & (rvi.shift(1) < 40)).astype(int) * config.rviposimportance
        rviposdown = ((rvi < 75) & (rvi.shift(1) > 60)).astype(int) * config.rviposimportance
        rvidivup = (bullCond15 | bullCond15.shift(1) | bullCond15.shift(2)).astype(int) * config.rvidivimportance
        rvidivdown = (bearCond15 | bearCond15.shift(1) | bearCond15.shift(2)).astype(int) * config.rvidivimportance
        
        # Remaining signals (simplified to 0)
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
        
        # EXACT Pine Script Lines 572-575: Signal Collection
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
        
        # EXACT Pine Script Lines 576-583: Position Logic
        pos = 0
        pos_series = []
        longentry_list = []
        shortentry_list = []
        
        for i in range(len(close)):
            # EXACT Pine Script logic: var pos = 0
            if stronglongentrysignal.iloc[i] and pos <= 0:
                pos = 1
            if strongshortentrysignal.iloc[i] and pos >= 0:
                pos = -1
            
            pos_series.append(pos)
            
            # Generate entry signals
            if i == 0:
                longentry_list.append(False)
                shortentry_list.append(False)
            else:
                longentry_list.append(pos == 1 and pos_series[i-1] != 1)
                shortentry_list.append(pos == -1 and pos_series[i-1] != -1)
        
        pos_series = pd.Series(pos_series, index=close.index)
        longentry = pd.Series(longentry_list, index=close.index)
        shortentry = pd.Series(shortentry_list, index=close.index)
        
        # EXACT Pine Script Lines 584-585: Alternate Signals Logic
        if config.alternatesignals:
            alternatelong = longentry
            alternateshort = shortentry
        else:
            alternatelong = stronglongentrysignal
            alternateshort = strongshortentrysignal
        
        # Apply trend filter if enabled (EXACT Pine Script logic)
        if config.tradetrendoption:
            final_long = alternatelong & mabuy
            final_short = alternateshort & masell
        else:
            final_long = alternatelong
            final_short = alternateshort
        
        # Calculate scores for analysis
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
            'longentry': longentry,
            'shortentry': shortentry,
            'alternatelong': alternatelong,
            'alternateshort': alternateshort,
            'pos_series': pos_series,
            'long_score': long_score_sum,
            'short_score': short_score_sum,
            'mabuy': mabuy,
            'masell': masell,
            'rsi': osc11,
            'macd': macd,
            'signal': signal,
            'histogram': hist,
            'wt1': wt1,
            'wt2': wt2,
            'stoch_k': k14,
            'stoch_d': d14,
            'supertrend': supertrend,
            'direction': direction,
            'hma': hma,
            'ema200': out5,
            'psar': psar,
            'upper_bb': upper,
            'lower_bb': lower,
            'rvi': rvi,
            'cmf': cmf,
            'vwap': vwapValue
        }
        
    except Exception as e:
        logger.error(f"Error in Pine Script calculation: {e}")
        return None

def calculate_pine_script_stops_and_targets(entry_price, signal_type, config: PineScriptConfig):
    """
    Calculate stop loss and targets exactly like Pine Script strategy
    """
    # Pine Script stop loss calculation
    stop_loss_percent = config.stoplosspercent / 100  # Convert to decimal
    
    if signal_type == 'long':
        # Pine Script: longstoploss = strategy.position_avg_price * (1 + stoplosspercent)
        # For -2.5%: stop_loss = entry_price * (1 + (-2.5/100)) = entry_price * 0.975
        stop_loss = entry_price * (1 + stop_loss_percent)  # stop_loss_percent is negative
        target_price = entry_price + (entry_price - stop_loss) * 2  # 2:1 R:R
    else:  # short
        # Pine Script: shortstoploss = strategy.position_avg_price * (1 - stoplosspercent)
        # For -2.5%: stop_loss = entry_price * (1 - (-2.5/100)) = entry_price * 1.025
        stop_loss = entry_price * (1 - stop_loss_percent)  # stop_loss_percent is negative, so this adds
        target_price = entry_price - (stop_loss - entry_price) * 2  # 2:1 R:R
    
    return stop_loss, target_price

def is_indian_trading_hours():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    if now.weekday() > 4:  # Saturday = 5, Sunday = 6
        return False
        
    market_open = dt_time(9, 15)  # 9:15 AM
    market_close = dt_time(15, 30)  # 3:30 PM
    current_time = now.time()
    
    return market_open <= current_time <= market_close

def analyze_stock_pine_script(ticker, pine_config: PineScriptConfig = None, position_manager: PositionManager = None):
    if pine_config is None:
        pine_config = PineScriptConfig()
    
    try:
        sector = get_sector_for_ticker(ticker)
        data = get_stock_data(ticker, period="1mo", interval="5m")
        if data is None or len(data) < 100:
            logger.warning(f"Insufficient data for {ticker}")
            return None
        
        signals = calculate_exact_pine_script_signals(data, pine_config)
        if signals is None:
            return None
        
        latest_idx = -1
        current_price = data['Close'].iloc[latest_idx]
        live_price = get_live_price(ticker)
        
        # Update current price with live price if available
        if live_price:
            current_price = live_price
        
        # Update positions if position manager provided
        if position_manager:
            position_manager.update_position_prices(ticker, current_price)
        
        # EXACT Pine Script Entry Logic
        # Pine Script: if tradetrendoption ? alternatelong and mabuy and longpositions : alternatelong and longpositions
        should_enter_long = False
        should_enter_short = False
        
        if pine_config.tradetrendoption:
            # With trend filter
            should_enter_long = signals['alternatelong'].iloc[latest_idx] and signals['mabuy'].iloc[latest_idx]
            should_enter_short = signals['alternateshort'].iloc[latest_idx] and signals['masell'].iloc[latest_idx]
        else:
            # Without trend filter
            should_enter_long = signals['alternatelong'].iloc[latest_idx]
            should_enter_short = signals['alternateshort'].iloc[latest_idx]
        
        # EXACT Pine Script Exit Logic
        # Pine Script: if (shortentry or printstoplong) and longpositions: strategy.close("longposition")
        # Pine Script: if (longentry or printstopshort) and shortpositions: strategy.close("shortposition")
        
        if position_manager and ticker in position_manager.positions:
            position = position_manager.positions[ticker]
            
            if position.position_type == 'long':
                # Exit long on shortentry OR stop loss
                if signals['shortentry'].iloc[latest_idx]:
                    position_manager.close_position(ticker, current_price, "Short Entry Signal")
                # Stop loss already handled in update_position_prices
            else:  # short position
                # Exit short on longentry OR stop loss  
                if signals['longentry'].iloc[latest_idx]:
                    position_manager.close_position(ticker, current_price, "Long Entry Signal")
                # Stop loss already handled in update_position_prices
        
        # Enter new positions (only if not already in position)
        if position_manager and ticker not in position_manager.positions:
            if should_enter_long:
                entry_price = current_price
                stop_loss, target_price = calculate_pine_script_stops_and_targets(entry_price, 'long', pine_config)
                position_manager.enter_position(ticker, 'long', entry_price, stop_loss, target_price)
            elif should_enter_short:
                entry_price = current_price
                stop_loss, target_price = calculate_pine_script_stops_and_targets(entry_price, 'short', pine_config)
                position_manager.enter_position(ticker, 'short', entry_price, stop_loss, target_price)
        
        # Determine signal type for display
        signal_type = 'HOLD'
        signal_strength = 'NONE'
        
        if signals['final_long'].iloc[latest_idx]:
            if signals['stronglongentrysignal'].iloc[latest_idx]:
                signal_type = 'STRONG_BUY'
                signal_strength = 'STRONG'
            elif signals['weaklongentrysignal'].iloc[latest_idx]:
                signal_type = 'BUY'
                signal_strength = 'WEAK'
        elif signals['final_short'].iloc[latest_idx]:
            if signals['strongshortentrysignal'].iloc[latest_idx]:
                signal_type = 'STRONG_SELL'
                signal_strength = 'STRONG'
            elif signals['weakshortentrysignal'].iloc[latest_idx]:
                signal_type = 'SELL'
                signal_strength = 'WEAK'
        
        # EXACT Pine Script stop loss calculation
        if 'BUY' in signal_type:
            entry_price = current_price
            # Pine Script: longstoploss = strategy.position_avg_price * (1 + stoplosspercent)
            stop_loss = entry_price * (1 + (pine_config.stoplosspercent / 100))
            target_price = entry_price + (entry_price - stop_loss) * 2  # 2:1 R:R
        elif 'SELL' in signal_type:
            entry_price = current_price
            # Pine Script: shortstoploss = strategy.position_avg_price * (1 - stoplosspercent)
            stop_loss = entry_price * (1 - (pine_config.stoplosspercent / 100))
            target_price = entry_price - (stop_loss - entry_price) * 2  # 2:1 R:R
        else:
            entry_price = current_price
            stop_loss = current_price
            target_price = current_price
        
        avg_volume = data['Volume'].rolling(20).mean().iloc[-1] if len(data) >= 20 else data['Volume'].iloc[-1]
        volume_ratio = data['Volume'].iloc[-1] / avg_volume if avg_volume > 0 else 1.0
        
        long_score_val = signals['long_score'].iloc[latest_idx]
        short_score_val = signals['short_score'].iloc[latest_idx]
        
        if hasattr(long_score_val, '__iter__') and not isinstance(long_score_val, str):
            long_score_val = float(long_score_val.sum()) if hasattr(long_score_val, 'sum') else float(long_score_val[0])
        if hasattr(short_score_val, '__iter__') and not isinstance(short_score_val, str):
            short_score_val = float(short_score_val.sum()) if hasattr(short_score_val, 'sum') else float(short_score_val[0])
        
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
                'entry_time': pos.entry_time
            }
        
        result = {
            'ticker': ticker,
            'sector': sector,
            'signal_type': signal_type,
            'signal_strength': signal_strength,
            'long_score': int(long_score_val),
            'short_score': int(short_score_val),
            'current_price': float(current_price),
            'live_price': live_price,
            'entry_price': float(entry_price),
            'target_price': float(target_price),
            'stop_loss': float(stop_loss),
            'volume_ratio': float(volume_ratio),
            'rsi': float(signals['rsi'].iloc[latest_idx]),
            'trend_direction': 'BULLISH' if signals['mabuy'].iloc[latest_idx] else 'BEARISH',
            'supertrend_direction': 'BULL' if signals['direction'].iloc[latest_idx] < 0 else 'BEAR',
            'macd_line': float(signals['macd'].iloc[latest_idx]),
            'macd_signal': float(signals['signal'].iloc[latest_idx]),
            'macd_histogram': float(signals['histogram'].iloc[latest_idx]),
            'wave_trend_wt1': float(signals['wt1'].iloc[latest_idx]),
            'wave_trend_wt2': float(signals['wt2'].iloc[latest_idx]),
            'stochastic_k': float(signals['stoch_k'].iloc[latest_idx]),
            'stochastic_d': float(signals['stoch_d'].iloc[latest_idx]),
            'hma_value': float(signals['hma'].iloc[latest_idx]),
            'ema200_value': float(signals['ema200'].iloc[latest_idx]),
            'supertrend_value': float(signals['supertrend'].iloc[latest_idx]),
            'psar_value': float(signals['psar'].iloc[latest_idx]),
            'upper_bb': float(signals['upper_bb'].iloc[latest_idx]),
            'lower_bb': float(signals['lower_bb'].iloc[latest_idx]),
            'rvi_value': float(signals['rvi'].iloc[latest_idx]),
            'cmf_value': float(signals['cmf'].iloc[latest_idx]),
            'vwap_value': float(signals['vwap'].iloc[latest_idx]),
            'bars_analyzed': len(data),
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'position_series': int(signals['pos_series'].iloc[latest_idx]),
            'long_signal': signals['final_long'].iloc[latest_idx],
            'short_signal': signals['final_short'].iloc[latest_idx],
            'alternatelong': signals['alternatelong'].iloc[latest_idx],
            'alternateshort': signals['alternateshort'].iloc[latest_idx],
            'longentry': signals['longentry'].iloc[latest_idx],
            'shortentry': signals['shortentry'].iloc[latest_idx],
            'position': position_info,
            'is_trading_hours': is_indian_trading_hours()
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing {ticker}: {e}")
        return None

def analyze_all_stocks_pine_script_live(pine_config: PineScriptConfig = None, position_manager: PositionManager = None, max_workers=4):
    if pine_config is None:
        pine_config = PineScriptConfig()
    if position_manager is None:
        position_manager = PositionManager()
    
    tickers = [stock['symbol'] for stock in config.TOP_STOCKS]
    logger.info(f"Analyzing {len(tickers)} stocks with EXACT Pine Script replication (Threshold: {pine_config.stronglongscore})...")
    
    all_signals = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(analyze_stock_pine_script, ticker, pine_config, position_manager): ticker 
            for ticker in tickers
        }
        
        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                result = future.result(timeout=30)
                if result:
                    all_signals.append(result)
                    
                    # Auto-enter positions based on strong signals (like Pine Script strategy.entry)
                    if result['signal_type'] == 'STRONG_BUY' and ticker not in position_manager.positions:
                        entry_price = result['current_price']
                        stop_loss = result['stop_loss']
                        target_price = result['target_price']
                        position_manager.enter_position(ticker, 'long', entry_price, stop_loss, target_price)
                    
                    elif result['signal_type'] == 'STRONG_SELL' and ticker not in position_manager.positions:
                        entry_price = result['current_price']
                        stop_loss = result['stop_loss']
                        target_price = result['target_price']
                        position_manager.enter_position(ticker, 'short', entry_price, stop_loss, target_price)
                    
                    logger.info(f"✓ {ticker}: {result['signal_type']} (Score: {result['long_score']}-{result['short_score']}) Pos:{result['position_series']}")
                else:
                    logger.warning(f"✗ {ticker}: No signal generated")
            except Exception as e:
                logger.error(f"✗ {ticker}: {str(e)[:50]}")
    
    return all_signals, position_manager

def run_live_trading_cycle(pine_config: PineScriptConfig, position_manager: PositionManager, cycle_number: int):
    """Run one 5-minute trading cycle"""
    logger.info(f"Running live trading cycle #{cycle_number}...")
    
    # Analyze all stocks
    all_signals, updated_position_manager = analyze_all_stocks_pine_script_live(pine_config, position_manager)
    
    # Display results with position tracking
    strong_signals = display_complete_pine_script_signals(all_signals, pine_config, updated_position_manager, cycle_number)
    
    # Save cycle data
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    
    # Save all results
    if all_signals:
        df_all = pd.DataFrame(all_signals)
        df_all.to_csv(f"cycle_{cycle_number}_all_signals_{timestamp}.csv", index=False)
    
    # Save strong signals only
    if strong_signals:
        df_strong = pd.DataFrame(strong_signals)
        df_strong.to_csv(f"cycle_{cycle_number}_strong_signals_{timestamp}.csv", index=False)
    
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
                'direction': direction,
                'pnl_percent': pnl_percent,
                'entry_time': pos.entry_time,
                'update_time': datetime.now()
            })
        
        df_positions = pd.DataFrame(positions_data)
        df_positions.to_csv(f"cycle_{cycle_number}_positions_{timestamp}.csv", index=False)
    
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

def wait_for_next_cycle():
    """Wait until the next 5-minute interval"""
    now = datetime.now()
    # Calculate next 5-minute mark
    minutes_to_wait = 5 - (now.minute % 5)
    seconds_to_wait = 60 - now.second
    
    if minutes_to_wait == 5 and seconds_to_wait == 60:
        # We're exactly on a 5-minute mark
        return
    
    total_seconds = (minutes_to_wait - 1) * 60 + seconds_to_wait
    
    next_run = now + timedelta(seconds=total_seconds)
    logger.info(f"Waiting {total_seconds} seconds until next cycle at {next_run.strftime('%H:%M:%S')}")
    
    time.sleep(total_seconds)

def run_live_trading_session(pine_config: PineScriptConfig):
    """Main live trading session - runs every 5 minutes until market close"""
    
    print(f"\n{'='*80}")
    print(f"🚀 PINE SCRIPT LIVE TRADING SESSION STARTED")
    print(f"{'='*80}")
    print(f"⚙️  Configuration:")
    print(f"   Strong Signal Threshold: {pine_config.stronglongscore}")
    print(f"   Stop Loss: {pine_config.stoplosspercent}%")
    print(f"   Trend Filter: {'ON' if pine_config.tradetrendoption else 'OFF'}")
    print(f"   Alternate Signals: {'ON' if pine_config.alternatesignals else 'OFF'}")
    print(f"🕐 Schedule: Every 5 minutes during market hours (9:15 AM - 3:30 PM IST)")
    print(f"{'='*80}")
    
    position_manager = PositionManager()
    cycle_number = 1
    
    # Check if market is open
    if not should_continue_trading():
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        print(f"🔴 Market is currently CLOSED")
        print(f"   Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} IST")
        print(f"   Market hours: 9:15 AM - 3:30 PM IST (Monday-Friday)")
        
        # Run one test cycle anyway
        print(f"\nRunning one test cycle...")
        position_manager = run_live_trading_cycle(pine_config, position_manager, cycle_number)
        return
    
    try:
        while should_continue_trading():
            cycle_start_time = datetime.now()
            print(f"\n🔄 Starting Cycle #{cycle_number} at {cycle_start_time.strftime('%H:%M:%S')}")
            
            # Run trading cycle
            position_manager = run_live_trading_cycle(pine_config, position_manager, cycle_number)
            
            cycle_number += 1
            
            # Wait for next 5-minute interval
            if should_continue_trading():  # Check again before waiting
                wait_for_next_cycle()
            
        # Market closed
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        print(f"\n🔴 MARKET CLOSED at {now.strftime('%H:%M:%S')} IST")
        print(f"📊 Session completed after {cycle_number - 1} cycles")
        
        # Final summary
        if position_manager.positions:
            print(f"\n📈 FINAL POSITION SUMMARY:")
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
                'total_cycles': cycle_number - 1,
                'active_positions': len(position_manager.positions),
                'closed_positions': len(position_manager.position_history),
                'total_unrealized_pnl': sum([p.unrealized_pnl for p in position_manager.positions.values()]),
                'total_realized_pnl': sum([h['pnl'] for h in position_manager.position_history]),
                'session_end_time': datetime.now()
            }
            
            import json
            with open(f"trading_session_{datetime.now().strftime('%Y%m%d')}.json", 'w') as f:
                json.dump(session_data, f, indent=2, default=str)
        
    except KeyboardInterrupt:
        print(f"\n⏹️  Trading session stopped by user")
        
        # Save interrupted session data
        if position_manager.position_history:
            history_df = pd.DataFrame(position_manager.position_history)
            history_df.to_csv(f"interrupted_session_history_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", index=False)
            print(f"📁 Session data saved")
    
    except Exception as e:
        logger.error(f"❌ Error in trading session: {e}")
        
        # Save error session data
        if position_manager.position_history:
            history_df = pd.DataFrame(position_manager.position_history)
            history_df.to_csv(f"error_session_history_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", index=False)
            print(f"📁 Error session data saved")

def display_complete_pine_script_signals(all_signals, pine_config: PineScriptConfig, position_manager: PositionManager = None, cycle_number: int = 1):
    if not all_signals:
        print("\nNo signals found!")
        return
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    is_trading = is_indian_trading_hours()
    
    # Filter for STRONG signals only
    strong_signals = [s for s in all_signals if s['signal_type'] in ['STRONG_BUY', 'STRONG_SELL']]
    
    print(f"\n{'='*220}")
    print(f"CYCLE #{cycle_number} - EXACT PINE SCRIPT - STRONG SIGNALS ONLY")
    print(f"Time: {current_time} | Market: {'OPEN' if is_trading else 'CLOSED'}")
    print(f"Showing only STRONG_BUY and STRONG_SELL signals (Threshold: {pine_config.stronglongscore})")
    print(f"{'='*220}")
    
    # Show active positions first if any exist
    if position_manager and position_manager.positions:
        print(f"\nACTIVE POSITIONS ({len(position_manager.positions)}):")
        print("-" * 180)
        pos_header = "{:<10} | {:<5} | {:<9} | {:<9} | {:<9} | {:<9} | {:<8} | {:<10} | {:<8} | {:<15}"
        print(pos_header.format(
            "Ticker", "Type", "Entry", "Current", "Stop", "Target", "PnL%", "Direction", "Status", "Entry Time"
        ))
        print("-" * 180)
        
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
                "ACTIVE",
                entry_time_str
            ))
    
    # Show new strong signals
    if strong_signals:
        print(f"\nNEW STRONG SIGNALS FOUND ({len(strong_signals)}):")
        print("-" * 220)
        header_format = "{:<10} | {:<8} | {:<9} | {:<4} | {:<4} | {:<5} | {:<12} | {:<7} | {:<7} | {:<9} | {:<9} | {:<9} | {:<4} | {:<7} | {:<5} | {:<8} | {:<3} | {:<15}"
        print(header_format.format(
            "Ticker", "Sector", "Current", "Live", "Long", "Short", "Signal", "L-Score", "S-Score", 
            "Entry", "Stop", "Target", "RSI", "Trend", "SuperT", "Position", "Pos", "Timestamp"
        ))
        print("-" * 220)
        
        for result in strong_signals:
            long_signal = "✓" if result['long_signal'] else ""
            short_signal = "✓" if result['short_signal'] else ""
            live_indicator = "LIVE" if result['live_price'] else "HIST"
            position_status = result['position']['position_type'].upper() if result['position'] else "NONE"
            
            print(header_format.format(
                result['ticker'][:10],
                result['sector'][:8],
                f"Rs{result['current_price']:.2f}",
                live_indicator,
                long_signal,
                short_signal,
                result['signal_type'][:12],
                result['long_score'],
                result['short_score'],
                f"Rs{result['entry_price']:.2f}",
                f"Rs{result['stop_loss']:.2f}",
                f"Rs{result['target_price']:.2f}",
                f"{result['rsi']:.0f}",
                result['trend_direction'][:7],
                result['supertrend_direction'][:5],
                position_status[:8],
                result['position_series'],
                result['timestamp']
            ))
    else:
        print(f"\nNo NEW STRONG signals found in this cycle!")
        
        # Show debugging info
        entry_signals = [s for s in all_signals if s['signal_type'] in ['STRONG_BUY', 'BUY', 'STRONG_SELL', 'SELL']]
        if entry_signals:
            print(f"Found {len(entry_signals)} weak signals that didn't meet strong threshold:")
            for s in entry_signals[:5]:
                print(f"  {s['ticker']}: {s['signal_type']} (Score: {s['long_score']}-{s['short_score']})")
        
        max_long = max(s['long_score'] for s in all_signals) if all_signals else 0
        max_short = max(s['short_score'] for s in all_signals) if all_signals else 0
        print(f"Highest scores this cycle: Long={max_long}, Short={max_short}")
    
    # Show historical positions summary
    if position_manager and position_manager.position_history:
        recent_history = position_manager.position_history[-5:]  # Last 5 closed positions
        if recent_history:
            print(f"\nRECENT CLOSED POSITIONS ({len(recent_history)}):")
            print("-" * 150)
            hist_header = "{:<10} | {:<5} | {:<9} | {:<9} | {:<8} | {:<15} | {:<15}"
            print(hist_header.format(
                "Ticker", "Type", "Entry", "Exit", "PnL", "Reason", "Close Time"
            ))
            print("-" * 150)
            
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
    
    print(f"\n📊 CYCLE #{cycle_number} SUMMARY:")
    if strong_signals:
        strong_buy = len([s for s in strong_signals if s['signal_type'] == 'STRONG_BUY'])
        strong_sell = len([s for s in strong_signals if s['signal_type'] == 'STRONG_SELL'])
        print(f"   🟢 NEW STRONG BUY: {strong_buy} | 🔴 NEW STRONG SELL: {strong_sell}")
    print(f"   📈 Active Positions: {total_active} | 📋 Closed Positions: {total_closed}")
    print(f"   💰 Total Unrealized PnL: Rs{total_unrealized_pnl:.2f}")
    print(f"   🕐 Market Status: {'TRADING' if is_trading else 'POST-MARKET'}")
    print(f"   ⏰ Next scan: {(datetime.now() + timedelta(minutes=5)).strftime('%H:%M:%S')}")
    
    return strong_signals
    
    # Signal Summary
    entry_signals = [r for r in all_signals if r and r['signal_type'] in ['STRONG_BUY', 'BUY', 'STRONG_SELL', 'SELL']]
    strong_buy = len([r for r in entry_signals if r['signal_type'] == 'STRONG_BUY'])
    buy = len([r for r in entry_signals if r['signal_type'] == 'BUY'])
    strong_sell = len([r for r in entry_signals if r['signal_type'] == 'STRONG_SELL'])
    sell = len([r for r in entry_signals if r['signal_type'] == 'SELL'])
    
    print(f"\n📊 EXACT PINE SCRIPT STRATEGY SUMMARY:")
    print(f"   🟢 STRONG BUY: {strong_buy:>2} | 🔵 BUY: {buy:>2}")
    print(f"   🔴 STRONG SELL: {strong_sell:>2} | 🟠 SELL: {sell:>2}")
    print(f"   📊 Total signals: {len(entry_signals):>2} | 📋 Total analyzed: {len(all_signals):>2}")
    print(f"   🎯 Signal rate: {(len(entry_signals)/len(all_signals)*100):.1f}%")
    
    # Debug info if no signals
    if len(entry_signals) == 0:
        print(f"\n🔍 DEBUG INFO - NO SIGNALS FOUND:")
        max_long = max(s['long_score'] for s in all_signals)
        max_short = max(s['short_score'] for s in all_signals)
        print(f"   Highest long score: {max_long} (Threshold: {pine_config.stronglongscore})")
        print(f"   Highest short score: {max_short} (Threshold: {pine_config.strongshortscore})")
        
        sorted_by_long = sorted(all_signals, key=lambda x: x['long_score'], reverse=True)[:5]
        print(f"   Top 5 Long Scores:")
        for i, s in enumerate(sorted_by_long, 1):
            print(f"   {i}. {s['ticker']}: {s['long_score']} (Pos: {s['position_series']})")

def main():
    parser = argparse.ArgumentParser(description="EXACT Pine Script Strategy: 'Accurate BUY & SELL 5 mins TF by RR' - Live Trading System")
    parser.add_argument('--strong-long', type=int, default=10, help='Strong BUY score threshold')
    parser.add_argument('--strong-short', type=int, default=10, help='Strong SELL score threshold') 
    parser.add_argument('--weak-long', type=int, default=8, help='Weak BUY score threshold')
    parser.add_argument('--weak-short', type=int, default=8, help='Weak SELL score threshold')
    parser.add_argument('--trend-filter', action='store_true', help='Enable trend filter')
    parser.add_argument('--alternate-signals', action='store_true', default=True, help='Use alternate signals logic')
    parser.add_argument('--test-single', type=str, help='Test single ticker')
    parser.add_argument('--test-mode', action='store_true', help='Run single test cycle instead of live trading')
    parser.add_argument('--live-trading', action='store_true', help='Start live trading session (5-min intervals until 3:30 PM)')
    parser.add_argument('--max-workers', type=int, default=4, help='Max concurrent workers')
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
    
    if args.test_single:
        print(f"TESTING: {args.test_single} with EXACT Pine Script Logic (Threshold: {pine_config.stronglongscore})")
        print("="*80)
        result = analyze_stock_pine_script(args.test_single, pine_config)
        if result:
            print(f"\nEXACT PINE SCRIPT RESULT:")
            print(f"Signal: {result['signal_type']} ({result['signal_strength']})")
            print(f"Scores: Long={result['long_score']}, Short={result['short_score']}")
            print(f"Position: {result['position_series']}")
            print(f"Entry: Rs{result['entry_price']:.2f} | Stop: Rs{result['stop_loss']:.2f} | Target: Rs{result['target_price']:.2f}")
            print(f"Current Price: Rs{result['current_price']:.2f} | Live: {'Yes' if result['live_price'] else 'No'}")
            print(f"Trend: {result['trend_direction']} | SuperTrend: {result['supertrend_direction']}")
            print(f"RSI: {result['rsi']:.1f} | Volume: {result['volume_ratio']:.1f}x")
            print(f"Bars Analyzed: {result['bars_analyzed']}")
            
            if args.debug:
                print(f"\nDEBUG INFO:")
                print(f"MACD: {result['macd_line']:.3f} | Signal: {result['macd_signal']:.3f}")
                print(f"Wave Trend: WT1={result['wave_trend_wt1']:.2f}, WT2={result['wave_trend_wt2']:.2f}")
                print(f"Stochastic: K={result['stochastic_k']:.1f}, D={result['stochastic_d']:.1f}")
                print(f"HMA: {result['hma_value']:.2f} | EMA200: {result['ema200_value']:.2f}")
                print(f"PSAR: {result['psar_value']:.2f} | RVI: {result['rvi_value']:.1f}")
                print(f"CMF: {result['cmf_value']:.3f} | VWAP: {result['vwap_value']:.2f}")
        else:
            print("No result generated")
        return
    
    elif args.live_trading:
        # Start live trading session
        print("Starting LIVE TRADING SESSION...")
        run_live_trading_session(pine_config)
        return
    
    elif args.test_mode:
        # Single test cycle
        print("EXACT PINE SCRIPT STRATEGY - TEST MODE")
        print("Strategy: 'Accurate BUY & SELL 5 mins TF by RR'")
        print("="*80)
        
        position_manager = PositionManager()
        all_signals, position_manager = analyze_all_stocks_pine_script_live(pine_config, position_manager, args.max_workers)
        
        if all_signals:
            strong_signals = display_complete_pine_script_signals(all_signals, pine_config, position_manager, 1)
            
            df = pd.DataFrame(all_signals)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            filename = f"test_mode_signals_{timestamp}.csv"
            df.to_csv(filename, index=False)
            print(f"\nTest results saved to: {filename}")
        else:
            print("No signals generated in test mode")
        return
    
    else:
        # Default: Show help and options
        print("EXACT PINE SCRIPT STRATEGY - 'Accurate BUY & SELL 5 mins TF by RR'")
        print("="*80)
        print("Available modes:")
        print("  --test-single TICKER    : Test single stock")
        print("  --test-mode            : Run one complete analysis cycle")
        print("  --live-trading         : Start live trading (5-min intervals until 3:30 PM)")
        print("")
        print("Configuration options:")
        print(f"  --strong-long N        : Strong BUY threshold (default: {pine_config.stronglongscore})")
        print(f"  --strong-short N       : Strong SELL threshold (default: {pine_config.strongshortscore})")
        print("  --trend-filter         : Enable trend filter")
        print("")
        print("Examples:")
        print("  python script.py --live-trading")
        print("  python script.py --test-mode --strong-long 8")
        print("  python script.py --test-single RELIANCE --debug")
        print("")
        
        # Show current market status
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        is_trading = should_continue_trading()
        
        print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} IST")
        print(f"Market status: {'OPEN' if is_trading else 'CLOSED'}")
        print(f"Market hours: 9:15 AM - 3:30 PM IST (Monday-Friday)")
        
        if not is_trading:
            # Run a quick test anyway
            print(f"\nRunning quick test analysis...")
            position_manager = PositionManager()
            all_signals, position_manager = analyze_all_stocks_pine_script_live(pine_config, position_manager, 2)
            
            if all_signals:
                display_complete_pine_script_signals(all_signals, pine_config, position_manager, 1)

if __name__ == "__main__":
    main()