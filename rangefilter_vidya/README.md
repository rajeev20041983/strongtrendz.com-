
During market hours (9:30 AM - 3:30 PM):

bash curl -X POST https://strongtrendz.ngrok.app/manual-override \
  -H "Content-Type: application/json" \
  -d '{"symbol": "PGEL", "action": "OPENED_BUY", "quantity": 150, "price": 125.50}'

Outside market hours (will get warning):
bash# This will show warning

curl -X POST https://strongtrendz.ngrok.app/manual-override \
  -H "Content-Type: application/json" \
  -d '{"symbol": "PGEL", "action": "OPENED_BUY", "quantity": 150, "price": 125.50}'

# Use force to override
curl -X POST https://strongtrendz.ngrok.app/manual-override \
  -H "Content-Type: application/json" \
  -d '{"symbol": "PGEL", "action": "OPENED_BUY", "quantity": 150, "price": 125.50, "force": true}'

TradingView Range Filter Automated Trading System
System Overview
Automated trading system that receives signals from TradingView's Range Filter indicator via webhooks and executes trades on Dhan broker.
Prerequisites

Dhan trading account with API credentials
TradingView Pro/Premium account (for webhooks)
Ngrok account with persistent domain
Python 3.8+

File Structure
trading_system/
│
├── range_webhook.py          # Main webhook server
├── stocks_config.json        # Stock configuration
├── dhan_credentials.json     # Dhan API credentials
├── security_ids.xlsx         # NSE security IDs from Dhan
├── logs/                     # Daily log files
└── data/                     # State persistence
Daily Operation Guide
🌅 Morning Startup (9:00 AM)
Step 1: Start Ngrok Tunnel
bash# Open Terminal 1
ngrok http 5000

ngrok http 5000 --domain=strongtrendz.ngrok.app    

# Verify ngrok is running at:
# https://strongtrendz.ngrok.app
Step 2: Start Python Server
bash# Open Terminal 2
cd /path/to/trading_system
python range_webhook.py

# Verify startup messages show:
# - Loaded 10 stocks
# - Trading hours: 09:30 - 15:30
Step 3: Verify System Health
bash# Open Terminal 3 (for commands)
curl https://strongtrendz.ngrok.app/health
Step 4: Check Current Status
bash curl https://strongtrendz.ngrok.app/status
📊 TradingView Alert Setup (One-time)
For each stock, create two alerts:
BUY Alert:

Condition: Range Filter → Buy alert on Range Filter
Message: BUY {{ticker}} at {{close}}
Webhook URL: https://strongtrendz.ngrok.app/webhook
Trigger: Once Per Bar Close

SELL Alert:

Condition: Range Filter → Sell alert on Range Filter
Message: SELL {{ticker}} at {{close}}
Webhook URL: https://strongtrendz.ngrok.app/webhook
Trigger: Once Per Bar Close

Manual Position Management
📈 Manual BUY Order
When you manually buy in Dhan, sync the system:
bash curl -X POST https://strongtrendz.ngrok.app/manual-override \
  -H "Content-Type: application/json" \
  -d '{"symbol": "PGEL", "action": "OPENED_BUY", "quantity": 150, "price": 125.50}'
📉 Manual SELL/SHORT Order
When you manually sell/short in Dhan:
bash curl -X POST https://strongtrendz.ngrok.app/manual-override \
  -H "Content-Type: application/json" \
  -d '{"symbol": "TATASTEEL", "action": "OPENED_SELL", "quantity": 250, "price": 450.00}'
❌ Manual Square Off
When you manually close a position:
bash curl -X POST https://strongtrendz.ngrok.app/manual-override \
  -H "Content-Type: application/json" \
  -d '{"symbol": "PGEL", "action": "CLOSED"}'
🔄 Clear All Positions
Start fresh (use carefully):
bash curl -X POST https://strongtrendz.ngrok.app/clear-all
Monitoring Commands
📊 Check Current Positions
bash curl https://strongtrendz.ngrok.app/status | python -m json.tool
📝 Watch Live Logs
bash# In separate terminal
tail -f logs/trading_*.log
🧪 Test Webhook (Without Placing Order)
bash curl -X POST https://strongtrendz.ngrok.app/test-parse \
  -H "Content-Type: text/plain" \
  -d "BUY NSE:PGEL at 125.50"
Web Monitoring
Option 1: Ngrok Inspector

Open browser: http://127.0.0.1:4040
View all incoming webhooks
See request/response details

Option 2: Direct API Status

Open browser: https://strongtrendz.ngrok.app/status
Refresh to see current positions
Shows JSON data of system state

Option 3: Create HTML Dashboard
Save as dashboard.html:
html<!DOCTYPE html>
<html>
<head>
    <title>Trading Dashboard</title>
    <meta http-equiv="refresh" content="30">
</head>
<body>
    <h1>Trading System Status</h1>
    <div id="status"></div>
    <script>
        fetch('https://strongtrendz.ngrok.app/status')
            .then(r => r.json())
            .then(data => {
                document.getElementById('status').innerHTML = `
                    <p>Time: ${data.time}</p>
                    <p>Trading: ${data.trading_allowed ? 'ACTIVE' : 'CLOSED'}</p>
                    <p>Positions: ${data.positions_count}</p>
                    <pre>${JSON.stringify(data.positions, null, 2)}</pre>
                `;
            });
    </script>
</body>
</html>
Quick Reference Commands
bash# Morning Check
curl https://strongtrendz.ngrok.app/health

# Position Status
curl https://strongtrendz.ngrok.app/status

# Manual Buy
curl -X POST https://strongtrendz.ngrok.app/manual-override \
  -H "Content-Type: application/json" \
  -d '{"symbol": "PGEL", "action": "OPENED_BUY", "quantity": 150}'

# Manual Sell
curl -X POST https://strongtrendz.ngrok.app/manual-override \
  -H "Content-Type: application/json" \
  -d '{"symbol": "PGEL", "action": "OPENED_SELL", "quantity": 150}'

# Close Position
curl -X POST https://strongtrendz.ngrok.app/manual-override \
  -H "Content-Type: application/json" \
  -d '{"symbol": "PGEL", "action": "CLOSED"}'

# Test Signal
curl -X POST https://strongtrendz.ngrok.app/webhook \
  -d "BUY NSE:PGEL at 125.50"
System Behavior
Signal Processing

Receives BUY/SELL {{ticker}} at {{close}} from TradingView
Removes NSE: prefix automatically
Checks if stock is in config
Validates trading hours (9:30-15:30)

Position Management

New Signal + No Position = Opens position
Opposite Signal + Existing Position = Squares off, then re-enters
Same Signal + Existing Position = Ignored

Re-entry Logic

Squares off with ACTUAL position quantity
Re-enters with CONFIG quantity
Ensures clean position sizing

Troubleshooting
Webhook Not Working
bash# Check ngrok
curl http://127.0.0.1:4040/api/tunnels

# Test webhook
curl -X POST https://strongtrendz.ngrok.app/webhook \
  -d "BUY NSE:PGEL at 125"
Position Mismatch
bash# View current state
cat data/state_$(date +%Y%m%d).json

# Manually sync
curl -X POST https://strongtrendz.ngrok.app/manual-override \
  -H "Content-Type: application/json" \
  -d '{"symbol": "PGEL", "action": "OPENED_BUY", "quantity": 150}'
Emergency Stop
bash# Clear all positions
curl -X POST https://strongtrendz.ngrok.app/clear-all

# Stop Python: Press Ctrl+C in python terminal
# Stop Ngrok: Press Ctrl+C in ngrok terminal
Daily Checklist

 9:00 AM - Start ngrok
 9:05 AM - Start Python server
 9:10 AM - Verify health check
 9:15 AM - Check TradingView alerts active
 9:25 AM - Sync any manual pre-market positions
 9:30 AM - Monitor first signals
 3:25 PM - Check end-of-day positions
 3:30 PM - Backup state file

Safety Rules

Always use "Once Per Bar Close" for alerts
Test commands outside market hours first
Keep manual override commands handy
Monitor logs during first few trades
Sync manual trades immediately

Support Files
stocks_config.json
Contains stock symbols and quantities
dhan_credentials.json
Contains API credentials (keep secure)
security_ids.xlsx
NSE security IDs from Dhan (required)

System Version: 1.0 | Pine Script: Range Filter with State TrackingRetry