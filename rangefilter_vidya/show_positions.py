import json
from datetime import datetime

# Dynamic filename with today's date
filename = f"data/range_{datetime.now().strftime('%Y%m%d')}.json"

try:
    # Load the file
    with open(filename, 'r') as f:
        data = json.load(f)
    
    positions = data.get('positions', {})
    
    if not positions:
        print("No open positions")
    else:
        print(f"\n{'='*60}")
        print(f"OPEN POSITIONS: {len(positions)} Total")
        print(f"{'='*60}\n")
        
        # Print header
        print(f"{'Symbol':<12} {'Side':<6} {'Qty':<6} {'Entry Price':<12}")
        print("-" * 40)
        
        # Print each position
        for symbol, details in positions.items():
            side = details.get('side', 'N/A')
            qty = details.get('quantity', 0)
            entry = details.get('entry_price', 0)
            
            print(f"{symbol:<12} {side:<6} {qty:<6} {entry:<12.2f}")
        
        print(f"\n{'='*60}")
        
        # Summary
        print(f"\nPositions List: {', '.join(positions.keys())}")
        
        # Option to remove
        remove = input("\nEnter symbol to remove (or press Enter to skip): ").upper()
        if remove and remove in positions:
            removed = positions.pop(remove)
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"✅ Removed {remove}")
            print(f"Remaining: {', '.join(positions.keys())}")
        
except FileNotFoundError:
    print(f"No file found: {filename}")
except Exception as e:
    print(f"Error: {e}")