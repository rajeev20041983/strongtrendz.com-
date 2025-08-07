#!/usr/bin/env python
# check_json_contents.py - Check what's actually in your JSON files

import os
import json
import glob
from datetime import datetime

def check_file_contents(output_dir):
    print("🔍 CHECKING ACTUAL JSON FILE CONTENTS")
    print("="*60)
    
    # Look for files with recent dates
    dates_to_try = ['20250805', '20250804', datetime.now().strftime('%Y%m%d')]
    
    patterns = {
        'BREAKOUT': 'corrected_breakout_signals_*{}_*.json',
        'DONCHIAN': 'donchian_signals_*{}_*.json',
        'BOLLINGER': 'bollinger_signals_*{}_*.json'
    }
    
    for date_str in dates_to_try:
        print(f"\n📅 CHECKING DATE: {date_str}")
        print("-" * 40)
        
        files_found = 0
        
        for strategy_name, pattern_template in patterns.items():
            pattern = pattern_template.format(date_str)
            files = glob.glob(os.path.join(output_dir, pattern))
            
            if files:
                files_found += 1
                latest_file = max(files, key=os.path.getmtime)
                filename = os.path.basename(latest_file)
                
                print(f"\n📊 {strategy_name} FILE: {filename}")
                print("=" * 50)
                
                try:
                    with open(latest_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    signals = data.get('signals', [])
                    metadata = data.get('metadata', {})
                    
                    print(f"📈 Metadata:")
                    print(f"   Total stocks analyzed: {metadata.get('total_stocks_analyzed', 0)}")
                    print(f"   Strategy: {metadata.get('strategy', 'Unknown')}")
                    print(f"   Timestamp: {metadata.get('timestamp', 'Unknown')}")
                    
                    print(f"\n📊 Signals: {len(signals)} total")
                    
                    if len(signals) == 0:
                        print("   ❌ NO SIGNALS FOUND IN FILE!")
                    else:
                        print(f"   ✅ Found {len(signals)} signals:")
                        
                        for i, signal in enumerate(signals, 1):
                            ticker = signal.get('ticker', 'Unknown')
                            signal_type = signal.get('signal_type', 'Unknown')
                            current_price = signal.get('current_price', 0)
                            
                            # Try to find target price
                            target_price = None
                            target_fields = ['target_price', 'upper_channel', 'lower_channel', 'upper_band', 'lower_band', 'bb_upper', 'bb_lower']
                            
                            for field in target_fields:
                                if field in signal and signal[field]:
                                    target_price = signal[field]
                                    break
                            
                            print(f"      {i}. {ticker}: {signal_type}")
                            print(f"         Current: ₹{current_price}")
                            print(f"         Target: ₹{target_price} (from field: {field if target_price else 'NOT FOUND'})")
                            
                            # Show all available fields for first signal
                            if i == 1:
                                print(f"         Available fields: {list(signal.keys())}")
                    
                except Exception as e:
                    print(f"   ❌ Error reading file: {e}")
            else:
                print(f"\n❌ {strategy_name}: No files found for {date_str}")
        
        if files_found > 0:
            print(f"\n✅ Found {files_found}/3 strategy files for {date_str}")
            break
        else:
            print(f"❌ No files found for {date_str}")
    
    if files_found == 0:
        print(f"\n❌ NO STRATEGY FILES FOUND!")
        print(f"💡 Available JSON files in directory:")
        all_json = glob.glob(os.path.join(output_dir, "*.json"))
        if all_json:
            for file_path in sorted(all_json):
                filename = os.path.basename(file_path)
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                print(f"   📄 {filename} ({file_time.strftime('%Y-%m-%d %H:%M:%S')})")
        else:
            print(f"   📁 No JSON files found in {output_dir}")

def main():
    output_dir = r'C:\Users\PC\OneDrive\projects\strongtrendz.com-\output'
    
    print("🔍 JSON FILE CONTENT CHECKER")
    print("📁 Directory:", output_dir)
    print()
    
    check_file_contents(output_dir)

if __name__ == "__main__":
    main()