#!/usr/bin/env python
# inside_bar_ichimoku_system.py - Inside Bar Detection + Ichimoku Direction System

import os
import sys
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta, time as dt_time
import warnings
import concurrent.futures
import argparse
import logging
import time
import pytz

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Configuration
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

config = DefaultConfig()

def get_sector_for_ticker(ticker):
    for stock in config.TOP_STOCKS:
        if stock['symbol'].replace('.NS', '') == ticker.replace('.NS', ''):
            return stock.get('sector', 'Unknown')
    return 'Unknown'

def get_stock_data(ticker, interval="15m"):
    """Get stock data"""
    try:
        symbol = f"{ticker}.NS" if not ticker.endswith('.NS') else ticker
        stock = yf.Ticker(symbol)
        
        if interval in ['1d', '1D']:
            period = "2y"
        elif interval in ['1h', '1H']:
            period = "3mo"
        elif interval in ['30m']:
            period = "3mo"
        elif interval in ['15m']:
            period = "2mo"
        else:  # 5m
            period = "1mo"
        
        data = stock.history(period=period, interval=interval)
        
        if data.empty or len(data) < 100:
            return None
            
        return data.dropna()
        
    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {e}")
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

def wait_for_market_open():
    """Wait until market opens"""
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    next_market = now.replace(hour=9, minute=15, second=0, microsecond=0)
    if now.time() > dt_time(15, 30):
        next_market += timedelta(days=1)
    
    while next_market.weekday() > 4:
        next_market += timedelta(days=1)
    
    wait_time = (next_market - now).total_seconds()
    
    if wait_time > 0:
        print(f"\nMarket CLOSED | Next opens: {next_market.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Waiting {wait_time/3600:.1f} hours...")
        
        while wait_time > 0:
            sleep_time = min(300, wait_time)
            time.sleep(sleep_time)
            wait_time -= sleep_time

# LOGIC 1: INSIDE BAR DETECTION
def detect_inside_bar(data, n_bars=1):
    """
    Simple Inside Bar Detection
    Inside bar = current bar's high < previous bar's high AND current bar's low > previous bar's low
    """
    try:
        if len(data) < n_bars + 2:
            return False, 0, 0
        
        high = data['High']
        low = data['Low']
        
        if n_bars == 1:
            # Current bar inside previous bar
            current_high = high.iloc[-1]
            current_low = low.iloc[-1]
            prev_high = high.iloc[-2]
            prev_low = low.iloc[-2]
            
            inside_bar = current_high < prev_high and current_low > prev_low
            
            return inside_bar, prev_high, prev_low
        
        # For multiple bars, check if all last n_bars are inside the reference bar
        reference_idx = -(n_bars + 1)
        ref_high = high.iloc[reference_idx]
        ref_low = low.iloc[reference_idx]
        
        for i in range(n_bars):
            bar_idx = -(i + 1)
            bar_high = high.iloc[bar_idx]
            bar_low = low.iloc[bar_idx]
            
            if not (bar_high < ref_high and bar_low > ref_low):
                return False, 0, 0
        
        return True, ref_high, ref_low
        
    except Exception:
        return False, 0, 0

# LOGIC 2: ICHIMOKU DIRECTION (EXACT PINE SCRIPT)
def calculate_ichimoku_direction(data, conversion_periods=9, base_periods=26, lagging_span2_periods=52, displacement=26, risk_reward=2):
    """
    EXACT Pine Script Ichimoku Direction Logic
    """
    try:
        if len(data) < lagging_span2_periods + displacement + 10:
            return {
                'direction': 'HOLD',
                'entry_price': 0,
                'stop_loss': 0,
                'target_price': 0,
                'conditions_met': {},
                'ichimoku_lines': {}
            }
        
        high = data['High']
        low = data['Low']
        close = data['Close']
        open_price = data['Open']
        current_price = close.iloc[-1]
        current_open = open_price.iloc[-1]
        
        # Pine Script Donchian function: avg(lowest(len), highest(len))
        def donchian(length):
            highest = high.rolling(window=length).max()
            lowest = low.rolling(window=length).min()
            return (highest + lowest) / 2
        
        # Pine Script Ichimoku lines
        conversion_line = donchian(conversion_periods)  # Tenkan-sen
        base_line = donchian(base_periods)              # Kijun-sen  
        lead_line1 = (conversion_line + base_line) / 2  # Senkou Span A
        lead_line2 = donchian(lagging_span2_periods)    # Senkou Span B
        
        # Current values
        current_conversion = conversion_line.iloc[-1]
        current_base = base_line.iloc[-1]
        current_lead1 = lead_line1.iloc[-1]
        current_lead2 = lead_line2.iloc[-1]
        
        # EXACT Pine Script conditions
        
        # LONG conditions
        con_abv_base = current_conversion > current_base
        cloud_green = current_lead1 > current_lead2
        
        # closeAbvCloud = open > leadLine1[displacement] and open > leadLine2[displacement]
        try:
            lead1_at_displacement = lead_line1.iloc[-displacement-1] if len(lead_line1) > displacement else current_lead1
            lead2_at_displacement = lead_line2.iloc[-displacement-1] if len(lead_line2) > displacement else current_lead2
        except:
            lead1_at_displacement = current_lead1
            lead2_at_displacement = current_lead2
        
        close_abv_cloud = current_open > lead1_at_displacement and current_open > lead2_at_displacement
        
        # lagSpanAbvCloud = close > leadLine1[displacement*2] and close > leadLine2[displacement*2]
        try:
            lead1_at_2x_displacement = lead_line1.iloc[-displacement*2-1] if len(lead_line1) > displacement*2 else current_lead1
            lead2_at_2x_displacement = lead_line2.iloc[-displacement*2-1] if len(lead_line2) > displacement*2 else current_lead2
        except:
            lead1_at_2x_displacement = current_lead1
            lead2_at_2x_displacement = current_lead2
            
        lag_span_abv_cloud = current_price > lead1_at_2x_displacement and current_price > lead2_at_2x_displacement
        
        condition_long = con_abv_base and cloud_green and close_abv_cloud and lag_span_abv_cloud
        
        # SHORT conditions
        con_blw_base = current_conversion < current_base
        cloud_red = current_lead2 > current_lead1
        close_blw_cloud = current_open < lead1_at_displacement and current_open < lead2_at_displacement
        lag_span_blw_cloud = current_price < lead1_at_2x_displacement and current_price < lead2_at_2x_displacement
        
        condition_short = con_blw_base and cloud_red and close_blw_cloud and lag_span_blw_cloud
        
        # Direction and Entry/Exit logic
        direction = 'HOLD'
        entry_price = current_price
        stop_loss = current_price
        target_price = current_price
        
        if condition_long:
            direction = 'LONG'
            entry_price = current_open
            # Pine Script: loss := leadLine2[displacement] < leadLine1[displacement] ? leadLine2[displacement] : leadLine1[displacement]
            stop_loss = min(lead1_at_displacement, lead2_at_displacement)
            # Pine Script: profit := open + ((open - loss) * riskReward)
            target_price = entry_price + ((entry_price - stop_loss) * risk_reward)
            
        elif condition_short:
            direction = 'SHORT'
            entry_price = current_open
            # Pine Script: loss := leadLine2[displacement] > leadLine1[displacement] ? leadLine2[displacement] : leadLine1[displacement]
            stop_loss = max(lead1_at_displacement, lead2_at_displacement)
            # Pine Script: profit := open - ((loss - open) * riskReward)
            target_price = entry_price - ((stop_loss - entry_price) * risk_reward)
        
        return {
            'direction': direction,
            'entry_price': float(entry_price),
            'stop_loss': float(stop_loss),
            'target_price': float(target_price),
            'conditions_met': {
                'con_abv_base': con_abv_base,
                'cloud_green': cloud_green,
                'close_abv_cloud': close_abv_cloud,
                'lag_span_abv_cloud': lag_span_abv_cloud,
                'condition_long': condition_long,
                'con_blw_base': con_blw_base,
                'cloud_red': cloud_red,
                'close_blw_cloud': close_blw_cloud,
                'lag_span_blw_cloud': lag_span_blw_cloud,
                'condition_short': condition_short
            },
            'ichimoku_lines': {
                'conversion_line': float(current_conversion),
                'base_line': float(current_base),
                'lead_line1': float(current_lead1),
                'lead_line2': float(current_lead2),
                'cloud_color': 'green' if cloud_green else 'red'
            }
        }
        
    except Exception as e:
        logger.error(f"Error calculating Ichimoku: {e}")
        return {
            'direction': 'HOLD',
            'entry_price': 0,
            'stop_loss': 0,
            'target_price': 0,
            'conditions_met': {},
            'ichimoku_lines': {}
        }

def analyze_stock_combined(ticker, interval="15m", n_bars=1, debug=False):
    """
    Combined Analysis: Inside Bar Detection + Ichimoku Direction
    """
    try:
        sector = get_sector_for_ticker(ticker)
        
        data = get_stock_data(ticker, interval=interval)
        if data is None or len(data) < 100:
            if debug:
                print(f"   {ticker}: Insufficient data - got {len(data) if data is not None else 0} bars")
            return None
        
        current_price = data['Close'].iloc[-1]
        
        # LOGIC 1: Inside Bar Detection
        inside_bar_detected, inside_bar_high, inside_bar_low = detect_inside_bar(data, n_bars)
        
        # LOGIC 2: Ichimoku Direction (only if inside bar detected)
        if inside_bar_detected:
            ichimoku_result = calculate_ichimoku_direction(data)
        else:
            ichimoku_result = {
                'direction': 'HOLD',
                'entry_price': current_price,
                'stop_loss': current_price,
                'target_price': current_price,
                'conditions_met': {},
                'ichimoku_lines': {}
            }
        
        # Calculate target percentage
        target_percent = 0
        if ichimoku_result['direction'] == 'LONG':
            target_percent = ((ichimoku_result['target_price'] - ichimoku_result['entry_price']) / ichimoku_result['entry_price']) * 100
        elif ichimoku_result['direction'] == 'SHORT':
            target_percent = ((ichimoku_result['entry_price'] - ichimoku_result['target_price']) / ichimoku_result['entry_price']) * 100
        
        result = {
            'ticker': ticker,
            'sector': sector,
            'current_price': float(current_price),
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'interval': interval,
            
            # Inside Bar Data
            'inside_bar_detected': inside_bar_detected,
            'inside_bar_high': float(inside_bar_high) if inside_bar_detected else 0.0,
            'inside_bar_low': float(inside_bar_low) if inside_bar_detected else 0.0,
            'inside_bar_range': float(inside_bar_high - inside_bar_low) if inside_bar_detected else 0.0,
            'n_bars_used': n_bars,
            
            # Ichimoku Direction (only matters if inside bar detected)
            'ichimoku_direction': ichimoku_result['direction'],
            'entry_price': ichimoku_result['entry_price'],
            'stop_loss': ichimoku_result['stop_loss'],
            'target_price': ichimoku_result['target_price'],
            'target_percent': float(target_percent),
            
            # Ichimoku Conditions
            'ichimoku_conditions': ichimoku_result['conditions_met'],
            'ichimoku_lines': ichimoku_result['ichimoku_lines'],
            
            # Final Signal
            'final_signal': ichimoku_result['direction'] if inside_bar_detected else 'NO_INSIDE_BAR'
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing {ticker}: {e}")
        return None

def analyze_all_stocks_combined(interval="15m", n_bars=1, max_workers=4, debug=False):
    """Analyze all stocks with combined logic"""
    
    tickers = [stock['symbol'] for stock in config.TOP_STOCKS]
    logger.info(f"Analyzing {len(tickers)} stocks with Inside Bar + Ichimoku ({interval} intervals)...")
    
    all_signals = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(analyze_stock_combined, ticker, interval, n_bars, debug): ticker 
            for ticker in tickers
        }
        
        for future in concurrent.futures.as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                result = future.result(timeout=60)
                if result:
                    all_signals.append(result)
                    if result['inside_bar_detected']:
                        logger.info(f"✓ {ticker}: Inside Bar + {result['ichimoku_direction']}")
                    else:
                        logger.info(f"✓ {ticker}: No Inside Bar")
                else:
                    logger.warning(f"✗ {ticker}: No data")
            except Exception as e:
                logger.error(f"✗ {ticker}: {str(e)[:50]}")
    
    return all_signals

def display_combined_results(all_signals, cycle_number, interval="15m"):
    """Display combined Inside Bar + Ichimoku results"""
    if not all_signals:
        print("\nNo signals found!")
        return []
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    is_trading = is_indian_trading_hours()
    
    # Filter data
    inside_bar_stocks = [s for s in all_signals if s['inside_bar_detected']]
    long_signals = [s for s in inside_bar_stocks if s['ichimoku_direction'] == 'LONG']
    short_signals = [s for s in inside_bar_stocks if s['ichimoku_direction'] == 'SHORT']
    hold_signals = [s for s in inside_bar_stocks if s['ichimoku_direction'] == 'HOLD']
    
    print(f"\n{'='*180}")
    print(f"CYCLE #{cycle_number} - INSIDE BAR + ICHIMOKU DIRECTION SYSTEM ({interval})")
    print(f"Time: {current_time} | Market: {'OPEN' if is_trading else 'CLOSED'}")
    print(f"Total Analyzed: {len(all_signals)} | Inside Bars Detected: {len(inside_bar_stocks)}")
    print(f"LONG Signals: {len(long_signals)} | SHORT Signals: {len(short_signals)} | HOLD: {len(hold_signals)}")
    print(f"{'='*180}")
    
    # Show LONG signals
    if long_signals:
        print(f"\nLONG SIGNALS ({len(long_signals)} stocks):")
        print("-" * 160)
        
        header = "{:<10} | {:<8} | {:<9} | {:<9} | {:<9} | {:<9} | {:<8} | {:<8} | {:<15} | {:<20}"
        print(header.format("Ticker", "Sector", "Price", "Entry", "Target", "Stop", "Target%", "IB_Range", "Cloud", "Ichimoku_Status"))
        print("-" * 160)
        
        for result in sorted(long_signals, key=lambda x: x.get('target_percent', 0), reverse=True):
            cloud_color = result['ichimoku_lines'].get('cloud_color', 'unknown')
            conditions = result['ichimoku_conditions']
            
            # Ichimoku status
            status_parts = []
            if conditions.get('con_abv_base'): status_parts.append("T>K")
            if conditions.get('cloud_green'): status_parts.append("GreenCloud")
            if conditions.get('close_abv_cloud'): status_parts.append("P>Cloud")
            if conditions.get('lag_span_abv_cloud'): status_parts.append("Lag>Cloud")
            ichimoku_status = "|".join(status_parts)
            
            print(header.format(
                result['ticker'][:10], result['sector'][:8], 
                f"Rs{result['current_price']:.0f}", f"Rs{result['entry_price']:.0f}",
                f"Rs{result['target_price']:.0f}", f"Rs{result['stop_loss']:.0f}",
                f"{result['target_percent']:.1f}%", f"Rs{result['inside_bar_range']:.1f}",
                cloud_color.upper(), ichimoku_status[:20]
            ))
    
    # Show SHORT signals
    if short_signals:
        print(f"\nSHORT SIGNALS ({len(short_signals)} stocks):")
        print("-" * 160)
        
        header = "{:<10} | {:<8} | {:<9} | {:<9} | {:<9} | {:<9} | {:<8} | {:<8} | {:<15} | {:<20}"
        print(header.format("Ticker", "Sector", "Price", "Entry", "Target", "Stop", "Target%", "IB_Range", "Cloud", "Ichimoku_Status"))
        print("-" * 160)
        
        for result in sorted(short_signals, key=lambda x: x.get('target_percent', 0), reverse=True):
            cloud_color = result['ichimoku_lines'].get('cloud_color', 'unknown')
            conditions = result['ichimoku_conditions']
            
            # Ichimoku status
            status_parts = []
            if conditions.get('con_blw_base'): status_parts.append("T<K")
            if conditions.get('cloud_red'): status_parts.append("RedCloud")
            if conditions.get('close_blw_cloud'): status_parts.append("P<Cloud")
            if conditions.get('lag_span_blw_cloud'): status_parts.append("Lag<Cloud")
            ichimoku_status = "|".join(status_parts)
            
            print(header.format(
                result['ticker'][:10], result['sector'][:8],
                f"Rs{result['current_price']:.0f}", f"Rs{result['entry_price']:.0f}",
                f"Rs{result['target_price']:.0f}", f"Rs{result['stop_loss']:.0f}",
                f"{result['target_percent']:.1f}%", f"Rs{result['inside_bar_range']:.1f}",
                cloud_color.upper(), ichimoku_status[:20]
            ))
    
    # Show HOLD signals (Inside bar detected but Ichimoku conditions not met)
    if hold_signals:
        print(f"\nINSIDE BAR DETECTED - ICHIMOKU HOLD ({len(hold_signals)} stocks):")
        print("-" * 120)
        
        hold_header = "{:<10} | {:<8} | {:<9} | {:<8} | {:<9} | {:<9} | {:<15} | {:<20}"
        print(hold_header.format("Ticker", "Sector", "Price", "IB_Range", "IB_High", "IB_Low", "Cloud", "Missing_Conditions"))
        print("-" * 120)
        
        for result in hold_signals:
            cloud_color = result['ichimoku_lines'].get('cloud_color', 'unknown')
            conditions = result['ichimoku_conditions']
            
            # Missing conditions
            missing = []
            if not conditions.get('con_abv_base') and not conditions.get('con_blw_base'): 
                missing.append("T/K_Cross")
            if not conditions.get('cloud_green') and not conditions.get('cloud_red'): 
                missing.append("Cloud_Weak")
            if not conditions.get('close_abv_cloud') and not conditions.get('close_blw_cloud'): 
                missing.append("P_In_Cloud")
            if not conditions.get('lag_span_abv_cloud') and not conditions.get('lag_span_blw_cloud'): 
                missing.append("Lag_In_Cloud")
            missing_conditions = "|".join(missing) if missing else "All_Weak"
            
            print(hold_header.format(
                result['ticker'][:10], result['sector'][:8], 
                f"Rs{result['current_price']:.0f}", f"Rs{result['inside_bar_range']:.1f}",
                f"Rs{result['inside_bar_high']:.0f}", f"Rs{result['inside_bar_low']:.0f}",
                cloud_color.upper(), missing_conditions[:20]
            ))
    
    # Summary
    print(f"\nCYCLE #{cycle_number} SUMMARY:")
    print(f"Total Stocks: {len(all_signals)} | Inside Bar Detected: {len(inside_bar_stocks)}")
    print(f"Actionable Signals: LONG {len(long_signals)} | SHORT {len(short_signals)}")
    print(f"Inside Bar but HOLD: {len(hold_signals)} (Ichimoku conditions not met)")
    
    if len(long_signals) == 0 and len(short_signals) == 0:
        print("No actionable signals - waiting for next scan...")
    
    return inside_bar_stocks

def live_trading_combined(interval="15m", n_bars=1, max_workers=4, debug=False):
    """Live trading with combined Inside Bar + Ichimoku system"""
    
    cycle_number = 0
    
    print(f"STARTING INSIDE BAR + ICHIMOKU DIRECTION LIVE SCANNER")
    print(f"Logic 1: Inside Bar Detection ({n_bars} bar pattern)")
    print(f"Logic 2: Ichimoku Direction (only for Inside Bar stocks)")
    print(f"Interval: {interval} | Workers: {max_workers}")
    print("Press Ctrl+C to stop")
    print("=" * 100)
    
    try:
        while True:
            cycle_number += 1
            is_trading = is_indian_trading_hours()
            
            try:
                print(f"\nCombined Analysis Scan #{cycle_number} at {datetime.now().strftime('%H:%M:%S')}")
                print(f"Market Status: {'OPEN' if is_trading else 'CLOSED'}")
                
                all_signals = analyze_all_stocks_combined(interval, n_bars, max_workers, debug)
                
                if all_signals:
                    inside_bar_signals = display_combined_results(all_signals, cycle_number, interval)
                    
                    # Save results
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
                    df = pd.DataFrame(all_signals)
                    filename = f"inside_bar_ichimoku_cycle_{cycle_number}_{timestamp}.csv"
                    df.to_csv(filename, index=False)
                    
                    if inside_bar_signals:
                        inside_bar_df = pd.DataFrame(inside_bar_signals)
                        inside_bar_filename = f"inside_bar_detected_cycle_{cycle_number}_{timestamp}.csv"
                        inside_bar_df.to_csv(inside_bar_filename, index=False)
                        print(f"Inside Bar signals saved: {inside_bar_filename}")
                
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
        print(f"\nInside Bar + Ichimoku scanner terminated")

def main():
    """Main function with combined Inside Bar + Ichimoku system"""
    parser = argparse.ArgumentParser(description="Inside Bar Detection + Ichimoku Direction System")
    
    parser.add_argument('--live-trading', action='store_true', help='Start live market scanner')
    parser.add_argument('--test-mode', action='store_true', help='Run single test scan')
    parser.add_argument('--test-single', type=str, help='Test single ticker')
    parser.add_argument('--interval', type=str, default='15m', choices=['5m', '15m', '30m', '1h', '1d'], help='Trading interval')
    parser.add_argument('--workers', type=int, default=6, help='Max concurrent workers')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--inside-bar-n-bars', type=int, default=1, choices=[1,2,3,4], help='Number of inside bars (1-4)')
    
    args = parser.parse_args()
    
    if args.test_single:
        print(f"SINGLE STOCK ANALYSIS: {args.test_single}")
        result = analyze_stock_combined(args.test_single, args.interval, args.inside_bar_n_bars, debug=True)
        if result:
            print(f"\nINSIDE BAR ANALYSIS:")
            print(f"Inside Bar Detected: {result['inside_bar_detected']}")
            print(f"Inside Bar High: Rs{result['inside_bar_high']:.2f}")
            print(f"Inside Bar Low: Rs{result['inside_bar_low']:.2f}")
            print(f"Inside Bar Range: Rs{result['inside_bar_range']:.2f}")
            
            print(f"\nICHIMOKU DIRECTION:")
            print(f"Direction: {result['ichimoku_direction']}")
            print(f"Entry Price: Rs{result['entry_price']:.2f}")
            print(f"Target Price: Rs{result['target_price']:.2f} ({result['target_percent']:.1f}%)")
            print(f"Stop Loss: Rs{result['stop_loss']:.2f}")
            
            print(f"\nICHIMOKU CONDITIONS:")
            conditions = result['ichimoku_conditions']
            for condition, status in conditions.items():
                print(f"{condition}: {status}")
            
            print(f"\nFINAL SIGNAL: {result['final_signal']}")
        else:
            print(f"No analysis possible for {args.test_single}")
        return

    elif args.test_mode:
        print(f"COMBINED INSIDE BAR + ICHIMOKU TEST SCAN")
        print(f"Interval: {args.interval} | Inside Bar: {args.inside_bar_n_bars} bars")
        print("="*80)
        
        all_signals = analyze_all_stocks_combined(args.interval, args.inside_bar_n_bars, args.workers, args.debug)
        if all_signals:
            display_combined_results(all_signals, 1, args.interval)
        return

    elif args.live_trading:
        print(f"STARTING COMBINED INSIDE BAR + ICHIMOKU LIVE TRADING")
        live_trading_combined(args.interval, args.inside_bar_n_bars, args.workers, args.debug)
        return

    else:
        print("INSIDE BAR DETECTION + ICHIMOKU DIRECTION SYSTEM")
        print("=" * 60)
        print("Two Simple Logics:")
        print("1. INSIDE BAR DETECTION - Identifies inside bar patterns")
        print("2. ICHIMOKU DIRECTION - Determines trade direction (only for inside bar stocks)")
        print("")
        print("Usage Examples:")
        print(f"Test: python {sys.argv[0]} --test-mode")
        print(f"Single: python {sys.argv[0]} --test-single RELIANCE")
        print(f"Live: python {sys.argv[0]} --live-trading --interval 5m")
        print("")
        print("Logic Flow:")
        print("• Scan all stocks for inside bar patterns")
        print("• For stocks with inside bars: check Ichimoku direction")
        print("• Generate LONG/SHORT/HOLD signals based on Ichimoku conditions")
        print("• No inside bar = no signal (simple filter)")

if __name__ == "__main__":
    main()