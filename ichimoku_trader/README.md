
Fix it:
Stop ngrok (Ctrl+C) and restart with the correct port:
bashngrok http 5000

Or if you have a custom domain:
bashngrok http 5000 --domain=strongtrendz.ngrok.app

Then your forwarding will be:
https://strongtrendz.ngrok.app -> http://localhost:5000

And your endpoints will work:

https://strongtrendz.ngrok.app/status
https://strongtrendz.ngrok.app/stocks
https://strongtrendz.ngrok.app/positions




Webhook URL:
https://strongtrendz.ngrok.app/ichimoku-alert
Alert Message:
{{strategy.order.alert_message}}
Steps for EACH Stock:

Add Pine Script to Chart

Open HDFCBANK chart (or any of your 9 stocks)
Add your Ichimoku Strategy indicator


Create Alert

Click Alert button (clock icon)
Condition: Select "Ichimoku Strategy - Order fills only"
Alert Name: "Ichimoku HDFCBANK" (or relevant stock name)
Message: {{strategy.order.alert_message}}
Webhook URL: https://strongtrendz.ngrok.app/ichimoku-alert
Check "Webhook URL" checkbox
Set expiration (e.g., "Open-ended")


Repeat for All 9 Stocks:

HDFCBANK
SHRIRAMFIN
LTF
BRITANNIA
NYKAA
EICHERMOT
VEDL
IREDA
BHARATFORG



What Will Happen:
When Ichimoku conditions trigger:

Long Signal: Sends "BUY HDFCBANK" to webhook
Exit/Short Signal: Sends "SELL HDFCBANK" to webhook
Webhook reads quantity from config (30 shares for HDFCBANK)
Places order through Dhan API

Important Notes:

Create ONE alert per stock (9 total alerts)
Each alert monitors that specific stock's Ichimoku signals
The {{strategy.order.alert_message}} automatically sends the correct BUY/SELL message from your Pine Script
Keep ngrok running for webhook to receive alerts

Test it first with one stock during market hours to ensure everything works before setting up all 9.RetryRhttps://strongtrendz.ngrok.app/ichimoku-alert   what is ichimoku-alert means where it comes fromEditDecoded webhook route's origin in Flask application.The user is asking about the /ichimoku-alert part of the webhook URL. They want to know what it means and where it comes from. This is a route/endpoint defined in their Flask application code.
Let me explain clearly where this comes from in their code./ichimoku-alert is the endpoint route you defined in your Flask webhook code.
Look at line 130 in your ichimoku_webhook.py:
python@app.route('/ichimoku-alert', methods=['POST'])
def handle_ichimoku_alert():
This creates the endpoint. Breaking it down:

https://strongtrendz.ngrok.app - Your ngrok domain
/ichimoku-alert - The specific route/endpoint that handles incoming webhooks

You could have named it anything:

/webhook
/tradingview
/alert
/trade-signal

But you (or the code) chose /ichimoku-alert to be descriptive.
Your Available Endpoints:
POST https://strongtrendz.ngrok.app/ichimoku-alert  - Receives trading signals
GET  https://strongtrendz.ngrok.app/status          - Shows current status
GET  https://strongtrendz.ngrok.app/stocks          - Lists your stocks
GET  https://strongtrendz.ngrok.app/positions       - Shows open positions with P&L
GET  https://strongtrendz.ngrok.app/position/HDFCBANK - Shows specific stock P&L
Each @app.route() in your code creates a different endpoint. The /ichimoku-alert is specifically for receiving POST requests from TradingView webhooks.