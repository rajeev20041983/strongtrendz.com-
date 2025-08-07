#!/usr/bin/env python
# cipla_zone_analyzer.py - Find exact dates of CIPLA's swing zone formation

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def analyze_cipla_zone():
    """Find when CIPLA formed the 1441-1536 zone"""
    
    print("🔍 ANALYZING CIPLA ZONE FORMATION TIMELINE")
    print("="*60)
    
    # Get CIPLA data
    ticker = "CIPLA.NS"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)  # 6 months of data
    
    data = yf.Ticker(ticker).history(start=start_date, end=end_date)
    
    if data.empty:
        print("❌ Could not fetch CIPLA data")
        return
    
    print(f"📅 Data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"📊 Total days: {len(data)}")
    
    # Find zone levels in recent data
    zone_top = 1536
    zone_bottom = 1441
    tolerance = 10  # ±10 rupees tolerance
    
    print(f"\n🎯 SEARCHING FOR ZONE LEVELS:")
    print(f"   Zone Top: ₹{zone_top} (±{tolerance})")
    print(f"   Zone Bottom: ₹{zone_bottom} (±{tolerance})")
    
    # Find when price was near zone top
    zone_top_dates = []
    for i, (date, row) in enumerate(data.iterrows()):
        if abs(row['High'] - zone_top) <= tolerance:
            zone_top_dates.append({
                'date': date.strftime('%Y-%m-%d'),
                'high': row['High'],
                'close': row['Close'],
                'days_ago': (end_date - date).days
            })
    
    # Find when price was near zone bottom  
    zone_bottom_dates = []
    for i, (date, row) in enumerate(data.iterrows()):
        if abs(row['Low'] - zone_bottom) <= tolerance:
            zone_bottom_dates.append({
                'date': date.strftime('%Y-%m-%d'),
                'low': row['Low'], 
                'close': row['Close'],
                'days_ago': (end_date - date).days
            })
    
    # Display results
    print(f"\n🏔️  ZONE TOP (~₹1,536) OCCURRENCES:")
    if zone_top_dates:
        for hit in zone_top_dates[-5:]:  # Last 5 occurrences
            print(f"   📅 {hit['date']}: High ₹{hit['high']:.2f}, Close ₹{hit['close']:.2f} ({hit['days_ago']} days ago)")
    else:
        print("   ❌ No recent highs near ₹1,536 found")
    
    print(f"\n🏞️  ZONE BOTTOM (~₹1,441) OCCURRENCES:")
    if zone_bottom_dates:
        for hit in zone_bottom_dates[-5:]:  # Last 5 occurrences
            print(f"   📅 {hit['date']}: Low ₹{hit['low']:.2f}, Close ₹{hit['close']:.2f} ({hit['days_ago']} days ago)")
    else:
        print("   ❌ No recent lows near ₹1,441 found")
    
    # Find most recent swing high and low
    print(f"\n📈 RECENT SWING ANALYSIS:")
    
    # Get recent swing high
    recent_high = data['High'].tail(30).max()
    recent_high_date = data['High'].tail(30).idxmax()
    days_ago_high = (end_date - recent_high_date).days
    
    # Get recent swing low  
    recent_low = data['Low'].tail(30).min()
    recent_low_date = data['Low'].tail(30).idxmin()
    days_ago_low = (end_date - recent_low_date).days
    
    print(f"   🏔️  Recent High: ₹{recent_high:.2f} on {recent_high_date.strftime('%Y-%m-%d')} ({days_ago_high} days ago)")
    print(f"   🏞️  Recent Low: ₹{recent_low:.2f} on {recent_low_date.strftime('%Y-%m-%d')} ({days_ago_low} days ago)")
    
    # Current price
    current_price = data['Close'].iloc[-1]
    print(f"\n💰 CURRENT STATUS:")
    print(f"   Current Price: ₹{current_price:.2f}")
    print(f"   Distance to Zone Top: ₹{zone_top - current_price:.2f} ({((zone_top - current_price)/current_price*100):+.1f}%)")
    print(f"   Distance to Zone Bottom: ₹{current_price - zone_bottom:.2f} ({((current_price - zone_bottom)/current_price*100):+.1f}%)")
    
    # Zone analysis
    if zone_top_dates and zone_bottom_dates:
        latest_top = zone_top_dates[-1]
        latest_bottom = zone_bottom_dates[-1]
        
        print(f"\n🎯 ZONE FORMATION TIMELINE:")
        print(f"   🏔️  Latest Zone Top: {latest_top['days_ago']} days ago")
        print(f"   🏞️  Latest Zone Bottom: {latest_bottom['days_ago']} days ago")
        
        zone_age = min(latest_top['days_ago'], latest_bottom['days_ago'])
        if zone_age < 30:
            freshness = "🟢 FRESH"
        elif zone_age < 60:
            freshness = "🟡 MODERATE"  
        else:
            freshness = "🔴 STALE"
            
        print(f"   ⏰ Zone Freshness: {freshness} ({zone_age} days)")

if __name__ == "__main__":
    analyze_cipla_zone()