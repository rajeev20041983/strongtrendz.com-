#!/usr/bin/env python
# swing_live_trader.py - SWING CALLS Live Trading Monitor
# Runs every 5 minutes during market hours (9:30 AM - 3:30 PM IST)

import os
import sys
import json
import time
import schedule
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import pytz
import warnings
import concurrent.futures
from typing import List, Dict, Optional

warnings.filterwarnings("ignore")

# Add your project directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import your existing configurations
try:
    from app import config
    print("✅ Successfully loaded config with tickers")
except ImportError:
    print("❌ Config not found! Using default tickers")
    class DefaultConfig:
        TOP_STOCKS = [
            {'symbol': 'RELIANCE'}, {'symbol': 'TCS'}, {'symbol': 'HDFCBANK'},
            {'symbol': 'INFY'}, {'symbol': 'HINDUNILVR'}, {'symbol': 'ICICIBANK'},
            {'symbol': 'KOTAKBANK'}, {'symbol': 'ITC'}, {'symbol': 'LT'},
            {'symbol': 'SBIN'}, {'symbol': 'BHARTIARTL'}, {'symbol': 'ASIANPAINT'},
            {'symbol': 'MARUTI'}, {'symbol': 'AXISBANK'}, {'symbol': 'BAJFINANCE'},
            {'symbol': 'WIPRO'}, {'symbol': 'NESTLEIND'}, {'symbol': 'ULTRACEMCO'},
            {'symbol': 'TITAN'}, {'symbol': 'POWERGRID'}, {'symbol': 'SUNPHARMA'},
            {'symbol': 'NTPC'}, {'symbol': 'ONGC'}, {'symbol': 'TECHM'},
            {'symbol': 'TATAMOTORS'}, {'symbol': 'COALINDIA'}, {'symbol': 'HCLTECH'},
            {'symbol': 'BAJAJFINSV'}, {'symbol': 'DRREDDY'}, {'symbol': 'EICHERMOT'}
        ]
        OUTPUT_DIR = 'output'
    config = DefaultConfig()

class SwingCallsLiveTrader:
    """Live SWING CALLS Trading Monitor"""
    
    def __init__(self, ema_value=2, sma_value=200, rsi_overbought=80, rsi_oversold=20, output_dir='output'):
        self.ema_value = ema_value
        self.sma_value = sma_value
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.rsi_period = 14
        self.output_dir = output_dir
        self.ist = pytz.timezone('Asia/Kolkata')
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Market hours (IST)
        self.market_open = 9, 30  # 9:30 AM
        self.market_close = 15, 30  # 3:30 PM
        
        print(f"🎯 SWING CALLS Live Trading Monitor Initialized")
        print(f"📈 Strategy: EMA({self.ema_value}) vs SMA({self.sma_value}) + RSI({self.rsi_overbought}/{self.rsi_oversold})")
        print(f"⏰ Timeframe: 5 minutes")
        print(f"🕘 Market Hours: 9:30 AM - 3:30 PM IST")
        print(f"📁 Output Directory: {self.output_dir}")
    
    def is_market_open(self) -> bool:
        """Check if market is currently open"""
        now = datetime.now(self.ist)
        current_time = now.time()
        
        # Check if it's a weekday (Monday=0, Sunday=6)
        if now.weekday() > 4:  # Saturday or Sunday
            return False
        
        # Check if within market hours
        market_open_time = now.replace(hour=self.market_open[0], minute=self.market_open[1], second=0, microsecond=0).time()
        market_close_time = now.replace(hour=self.market_close[0], minute=self.market_close[1], second=0, microsecond=0).time()
        
        return market_open_time <= current_time <= market_close_time
    
    def get_stock_data_5m(self, ticker: str, periods: int = 100) -> Optional[pd.DataFrame]:
        """Get 5-minute stock data for live analysis"""
        try:
            if ticker.endswith('.NS'):
                symbol = ticker
            else:
                symbol = f"{ticker}.NS"
            
            # For 5-minute data, we need recent data (last few days)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5)  # 5 days should give us enough 5m periods
            
            stock = yf.Ticker(symbol)
            data = stock.history(start=start_date, end=end_date, interval='5m', 
                               auto_adjust=True, prepost=True)
            
            if data.empty or len(data) < max(self.sma_value, 50):
                return None
            
            data = data.dropna()
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in data.columns for col in required_columns):
                return None
            
            return data.sort_index().tail(periods)  # Get recent periods
            
        except Exception as e:
            print(f"❌ Error fetching {ticker}: {str(e)[:50]}...")
            return None
    
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
    
    def calculate_indicators(self, data: pd.DataFrame) -> dict:
        """Calculate SWING CALLS indicators"""
        try:
            # Pine Script: ema1=ema(close,ema_value)
            ema1 = data['Close'].ewm(span=self.ema_value).mean()
            
            # Pine Script: sma2=sma(close,sma_value)  
            sma2 = data['Close'].rolling(window=self.sma_value).mean()
            
            # Pine Script: rs=rsi(close,14)
            rs = self.calculate_rsi(data['Close'], self.rsi_period)
            
            # Pine Script color logic
            sma_color = []
            for i in range(len(data)):
                if i < len(rs) and not pd.isna(rs.iloc[i]) and not pd.isna(sma2.iloc[i]):
                    rsi_val = rs.iloc[i]
                    if rsi_val >= 85 or rsi_val <= 15:
                        sma_color.append('yellow')  # Extreme RSI
                    elif data['Low'].iloc[i] > sma2.iloc[i]:
                        sma_color.append('green')   # Bullish
                    elif data['High'].iloc[i] < sma2.iloc[i]:
                        sma_color.append('red')     # Bearish
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
            print(f"❌ Error calculating indicators: {e}")
            return {}
    
    def detect_live_signals(self, data: pd.DataFrame, ticker: str) -> Optional[dict]:
        """Detect SWING CALLS signals for live trading"""
        
        if len(data) < max(self.sma_value, self.rsi_period) + 5:
            return None
        
        # Calculate indicators
        indicators = self.calculate_indicators(data)
        if not indicators:
            return None
        
        try:
            # Get latest values
            ema1 = indicators['ema1']
            sma2 = indicators['sma2']
            rsi = indicators['rsi']
            sma_color = indicators['sma_color']
            
            # Current bar values (most recent 5-minute candle)
            current_close = float(data['Close'].iloc[-1])
            current_open = float(data['Open'].iloc[-1])
            current_high = float(data['High'].iloc[-1])
            current_low = float(data['Low'].iloc[-1])
            current_volume = float(data['Volume'].iloc[-1])
            current_ema = float(ema1.iloc[-1])
            current_sma = float(sma2.iloc[-1])
            current_rsi = float(rsi.iloc[-1])
            current_color = sma_color[-1]
            
            # Previous bar values for crossover detection
            prev_ema = float(ema1.iloc[-2]) if len(ema1) > 1 else current_ema
            prev_sma = float(sma2.iloc[-2]) if len(sma2) > 1 else current_sma
            prev_rsi = float(rsi.iloc[-2]) if len(rsi) > 1 else current_rsi
            
            # Check for NaN values
            values_to_check = [current_ema, current_sma, current_rsi, prev_ema, prev_sma, prev_rsi]
            if any(pd.isna(v) for v in values_to_check):
                return None
            
            signal = 'HOLD'
            signal_type = 'None'
            rsi_alert = 'None'
            confidence = 0
            
            # Pine Script RSI alerts
            if current_rsi < self.rsi_overbought and prev_rsi >= self.rsi_overbought:
                rsi_alert = 'RSI_BEARISH'  # Exit buy positions
            elif current_rsi > self.rsi_oversold and prev_rsi <= self.rsi_oversold:
                rsi_alert = 'RSI_BULLISH'  # Exit sell positions
            
            # Pine Script main signals
            # buycall=crossunder(sma2,ema1) and high>sma2
            crossunder_sma_ema = (current_sma < current_ema and prev_sma >= prev_ema)
            high_above_sma = current_high > current_sma
            
            if crossunder_sma_ema and high_above_sma:
                signal = 'BUY'
                signal_type = 'SWING_BUY'
                confidence = 85
                
                # Boost confidence with additional factors
                if current_rsi < 70:  # Not overbought
                    confidence += 5
                if current_volume > data['Volume'].iloc[-20:-1].mean():  # Above average volume
                    confidence += 10
            
            # sellcall=crossover(sma2,ema1) and open>close
            crossover_sma_ema = (current_sma > current_ema and prev_sma <= prev_ema)
            red_candle = current_open > current_close
            
            if crossover_sma_ema and red_candle:
                signal = 'SELL'
                signal_type = 'SWING_SELL'
                confidence = 85
                
                # Boost confidence with additional factors
                if current_rsi > 30:  # Not oversold
                    confidence += 5
                if current_volume > data['Volume'].iloc[-20:-1].mean():  # Above average volume
                    confidence += 10
            
            # Only return actionable signals
            if signal in ['BUY', 'SELL']:
                # Calculate additional metrics
                volume_ratio = 1.0
                if len(data) >= 21:
                    avg_volume = data['Volume'].iloc[-21:-1].mean()
                    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
                
                momentum = 0.0
                if len(data) >= 6:
                    past_price = float(data['Close'].iloc[-6])
                    momentum = ((current_close - past_price) / past_price) * 100
                
                # Calculate target price (simple projection)
                if signal == 'BUY':
                    # Target is current price + (price - SMA) for momentum continuation
                    price_above_sma = current_close - current_sma
                    target_price = current_close + price_above_sma * 0.5
                    stop_loss = current_sma * 0.995  # Slightly below SMA
                else:  # SELL
                    # Target is current price - (SMA - price) for momentum continuation  
                    price_below_sma = current_sma - current_close
                    target_price = current_close - price_below_sma * 0.5
                    stop_loss = current_sma * 1.005  # Slightly above SMA
                
                return {
                    'ticker': ticker,
                    'signal_type': signal,
                    'timestamp': datetime.now(self.ist).isoformat(),
                    'timeframe': '5m',
                    'current_price': current_close,
                    'target_price': target_price,
                    'stop_loss': stop_loss,
                    'ema_value': current_ema,
                    'sma_value': current_sma,
                    'rsi': current_rsi,
                    'rsi_alert': rsi_alert,
                    'sma_color': current_color,
                    'candle_type': 'Green' if current_close > current_open else 'Red',
                    'volume_ratio': volume_ratio,
                    'momentum': momentum,
                    'confidence': min(confidence, 100),
                    'conditions': {
                        'crossunder_sma_ema': crossunder_sma_ema,
                        'high_above_sma': high_above_sma,
                        'crossover_sma_ema': crossover_sma_ema,
                        'red_candle': red_candle
                    },
                    'strategy_params': {
                        'ema_period': self.ema_value,
                        'sma_period': self.sma_value,
                        'rsi_overbought': self.rsi_overbought,
                        'rsi_oversold': self.rsi_oversold
                    }
                }
                
            return None
            
        except Exception as e:
            print(f"❌ Error detecting signals for {ticker}: {e}")
            return None
    
    def analyze_all_stocks_live(self) -> List[dict]:
        """Analyze all stocks for live signals"""
        
        current_time = datetime.now(self.ist)
        print(f"\n🚀 LIVE SWING CALLS ANALYSIS - {current_time.strftime('%Y-%m-%d %H:%M:%S IST')}")
        print(f"📊 Strategy: EMA({self.ema_value})/SMA({self.sma_value}) on 5-minute timeframe")
        print("="*70)
        
        tickers = [stock['symbol'].replace('.NS', '') for stock in config.TOP_STOCKS]
        all_signals = []
        successful = 0
        failed = 0
        
        # Use fewer workers for live trading to avoid rate limits
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_to_ticker = {
                executor.submit(self.analyze_single_stock_live, ticker): ticker 
                for ticker in tickers
            }
            
            for future in concurrent.futures.as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                
                try:
                    signal = future.result(timeout=15)
                    if signal:
                        all_signals.append(signal)
                        successful += 1
                        print(f"🎯 {ticker}: {signal['signal_type']} @ ₹{signal['current_price']:.2f} | RSI:{signal['rsi']:.0f} | Conf:{signal['confidence']}%")
                    else:
                        failed += 1
                        print(f"⚪ {ticker}: HOLD")
                        
                except Exception as e:
                    failed += 1
                    print(f"❌ {ticker}: Error - {str(e)[:30]}...")
        
        print(f"\n📊 LIVE ANALYSIS COMPLETE:")
        print(f"   ✅ Analyzed: {successful + failed} stocks")
        print(f"   🎯 Signals found: {len(all_signals)}")
        print(f"   📈 BUY signals: {sum(1 for s in all_signals if s['signal_type'] == 'BUY')}")
        print(f"   📉 SELL signals: {sum(1 for s in all_signals if s['signal_type'] == 'SELL')}")
        
        return all_signals
    
    def analyze_single_stock_live(self, ticker: str) -> Optional[dict]:
        """Analyze single stock for live signals"""
        try:
            data = self.get_stock_data_5m(ticker)
            if data is None:
                return None
            
            return self.detect_live_signals(data, ticker)
            
        except Exception as e:
            return None
    
    def save_live_signals(self, signals: List[dict]) -> str:
        """Save live signals to JSON file"""
        
        current_time = datetime.now(self.ist)
        date_str = current_time.strftime('%Y%m%d')
        time_str = current_time.strftime('%H%M')
        
        filename = f"swing_calls_live_{date_str}_{time_str}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        # Prepare data structure similar to your template
        data = {
            'metadata': {
                'strategy': 'SWING_CALLS_LIVE',
                'timeframe': '5m',
                'timestamp': current_time.isoformat(),
                'market_session': 'LIVE',
                'total_stocks_analyzed': len(config.TOP_STOCKS),
                'signals_found': len(signals),
                'buy_signals': sum(1 for s in signals if s['signal_type'] == 'BUY'),
                'sell_signals': sum(1 for s in signals if s['signal_type'] == 'SELL'),
                'strategy_params': {
                    'ema_period': self.ema_value,
                    'sma_period': self.sma_value,
                    'rsi_overbought': self.rsi_overbought,
                    'rsi_oversold': self.rsi_oversold
                },
                'market_hours': f"{self.market_open[0]}:{self.market_open[1]:02d} - {self.market_close[0]}:{self.market_close[1]:02d} IST"
            },
            'signals': signals
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Signals saved: {filename}")
            return filepath
            
        except Exception as e:
            print(f"❌ Error saving file: {e}")
            return ""
    
    def run_live_analysis(self):
        """Run live analysis (called every 5 minutes)"""
        
        # Check if market is open
        if not self.is_market_open():
            current_time = datetime.now(self.ist)
            print(f"⏰ Market is closed at {current_time.strftime('%H:%M:%S IST')}")
            return
        
        try:
            # Run analysis
            signals = self.analyze_all_stocks_live()
            
            # Save results
            if signals:
                filepath = self.save_live_signals(signals)
                
                # Print actionable signals
                print(f"\n🔥 ACTIONABLE SIGNALS:")
                for signal in signals:
                    print(f"   {signal['signal_type']} {signal['ticker']}: "
                          f"₹{signal['current_price']:.2f} → ₹{signal['target_price']:.2f} "
                          f"(SL: ₹{signal['stop_loss']:.2f}) | Conf: {signal['confidence']}%")
            else:
                print("⚪ No actionable signals at this time")
                
                # Still save the metadata for tracking
                self.save_live_signals([])
        
        except Exception as e:
            print(f"❌ Error in live analysis: {e}")
    
    def start_live_monitoring(self):
        """Start live monitoring with scheduler"""
        
        print(f"🚀 STARTING SWING CALLS LIVE MONITORING")
        print(f"⏰ Running every 5 minutes during market hours")
        print(f"🕘 Market Hours: 9:30 AM - 3:30 PM IST")
        print(f"📈 Strategy: EMA({self.ema_value})/SMA({self.sma_value}) + 5-minute timeframe")
        print("="*70)
        
        # Schedule every 5 minutes
        schedule.every(5).minutes.do(self.run_live_analysis)
        
        # Run immediately if market is open
        if self.is_market_open():
            print("🟢 Market is OPEN - Running initial analysis...")
            self.run_live_analysis()
        else:
            print("🔴 Market is CLOSED - Waiting for market open...")
        
        # Keep running
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            print(f"\n⏹️  Live monitoring stopped by user")
            current_time = datetime.now(self.ist)
            print(f"📅 Stopped at: {current_time.strftime('%Y-%m-%d %H:%M:%S IST')}")

def main():
    """Main function"""
    
    # Configuration
    ema_value = 2      # surajkumarsadhaphule's suggestion
    sma_value = 200    # surajkumarsadhaphule's suggestion  
    rsi_overbought = 80
    rsi_oversold = 20
    output_dir = getattr(config, 'OUTPUT_DIR', 'output')
    
    # Create live trader
    live_trader = SwingCallsLiveTrader(
        ema_value=ema_value,
        sma_value=sma_value, 
        rsi_overbought=rsi_overbought,
        rsi_oversold=rsi_oversold,
        output_dir=output_dir
    )
    
    # Start live monitoring
    live_trader.start_live_monitoring()

if __name__ == "__main__":
    print("🎯 SWING CALLS LIVE TRADING MONITOR")
    print("📊 Based on surajkumarsadhaphule's EMA(2)/SMA(200) suggestion")
    print("⏰ 5-minute timeframe | Market Hours: 9:30 AM - 3:30 PM IST")
    print()
    
    main()