import json
from datetime import datetime

# Dynamic filename with today's date
filename = f"data/range_{datetime.now().strftime('%Y%m%d')}.json"

# Get user input
symbol = input("Enter symbol to remove from positions (or 'SHOW' to see all positions): ").upper()

try:
    # Load the file
    with open(filename, 'r') as f:
        data = json.load(f)
    
    # Show current positions
    current_positions = data.get('positions', {})
    print(f"\nCurrent positions: {list(current_positions.keys())}")
    
    if symbol == 'SHOW':
        print("\nDetailed positions:")
        for sym, details in current_positions.items():
            print(f"  {sym}: {details}")
    elif symbol in current_positions:
        # Remove the symbol
        removed = current_positions.pop(symbol)
        
        # Save back
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n✅ Removed {symbol} from positions")
        print(f"Was: {removed}")
        print(f"Remaining positions: {list(current_positions.keys())}")
    else:
        print(f"\n❌ {symbol} not found in positions")
        if current_positions:
            print(f"Available positions: {list(current_positions.keys())}")
        else:
            print("No open positions")
            
except FileNotFoundError:
    print(f"❌ File not found: {filename}")
    print("No trades for today yet")
except Exception as e:
    print(f"❌ Error: {e}")