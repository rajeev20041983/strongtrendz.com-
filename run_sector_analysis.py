#!/usr/bin/env python
# run_sector_analysis.py - Sector analysis with integrated sharing features

import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(current_dir)

# Add sharing-related imports
import http.server
import socketserver
import threading
import webbrowser
import socket
import zipfile
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Add curl_cffi installation to bypass Yahoo Finance rate limits
def install_curl_cffi():
    """Install curl_cffi package if not already installed"""
    try:
        import curl_cffi
        print("curl_cffi is already installed. Will use it to bypass Yahoo Finance rate limits.")
        return True
    except ImportError:
        print("curl_cffi not found. Installing curl_cffi to bypass Yahoo Finance rate limits...")
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "curl_cffi"])
            print("curl_cffi successfully installed.")
            return True
        except Exception as e:
            print(f"Failed to install curl_cffi: {str(e)}")
            print("You may need to manually install it with: pip install curl_cffi")
            return False

# Attempt to install curl_cffi at startup
CURL_CFFI_AVAILABLE = install_curl_cffi()

import json
import argparse
import logging
from datetime import datetime
import pandas as pd
from tabulate import tabulate
import warnings
from app.services.market_analyzer import MarketAnalysisService
from app.services.sector_analyzer import SectorAnalyzer
from app import config

# ======= YOUR EXISTING SENTIMENT SERVICE INTEGRATION =======
try:
    from enhanced_sentiment_service import SentimentAnalysisService, enhanced_analyze_stock
    SENTIMENT_AVAILABLE = True
    print("✅ Your sentiment service loaded successfully")
except ImportError as e:
    SENTIMENT_AVAILABLE = False
    print(f"⚠️ Enhanced sentiment service not available: {e}")
    print("   Make sure enhanced_sentiment_service.py is in the same directory")
# ============================================

# Import or patch yfinance with curl_cffi if available
if CURL_CFFI_AVAILABLE:
    try:
        import yfinance as yf
        from curl_cffi import requests as curl_requests
        
        # Create a function to get a patched yfinance Ticker with curl_cffi session
        def get_ticker_with_curl_cffi(ticker_symbol):
            """Create a yfinance Ticker object with curl_cffi session to bypass rate limits"""
            session = curl_requests.Session(impersonate="chrome")
            return yf.Ticker(ticker_symbol, session=session)
        
        print("yfinance configured to use curl_cffi for bypassing rate limits")
    except Exception as e:
        print(f"Warning: Could not configure yfinance with curl_cffi: {str(e)}")

# Suppress warnings
warnings.filterwarnings("ignore")

# ======= SHARING FUNCTIONS =======

def start_local_server(html_file_path, port=8000):
    """Start a simple HTTP server to serve the HTML file"""
    import os
    
    # Get the directory containing the HTML file
    html_dir = os.path.dirname(html_file_path)
    html_filename = os.path.basename(html_file_path)
    
    # Change to the HTML directory
    original_dir = os.getcwd()
    os.chdir(html_dir)
    
    try:
        # Find available port
        while port < 8010:
            try:
                with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as httpd:
                    print(f"\n🌐 HTTP Server started!")
                    print(f"📍 Local access: http://localhost:{port}/{html_filename}")
                    
                    # Get local IP for network access
                    hostname = socket.gethostname()
                    local_ip = socket.gethostbyname(hostname)
                    print(f"🌍 Network access: http://{local_ip}:{port}/{html_filename}")
                    print(f"📤 Share this URL with your friend: http://{local_ip}:{port}/{html_filename}")
                    print(f"⏹️  Press Ctrl+C to stop the server")
                    
                    # Auto-open in browser
                    webbrowser.open(f"http://localhost:{port}/{html_filename}")
                    
                    # Start server in background
                    server_thread = threading.Thread(target=httpd.serve_forever)
                    server_thread.daemon = True
                    server_thread.start()
                    
                    return httpd, port
            except OSError:
                port += 1
                continue
    finally:
        os.chdir(original_dir)
    
    return None, None

def create_shareable_package(html_file_path, output_dir):
    """Create a ZIP package with the report and instructions"""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = f"stock_analysis_report_package_{timestamp}.zip"
    zip_path = os.path.join(output_dir, zip_filename)
    
    # Create instructions file
    instructions_content = f"""
📊 STOCK ANALYSIS REPORT PACKAGE
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📁 CONTENTS:
• {os.path.basename(html_file_path)} - Main analysis report (open in any browser)
• README.txt - This file

🌐 HOW TO VIEW:
1. Extract this ZIP file
2. Double-click the HTML file
3. It will open in your default browser
4. Works offline - no internet required!

📊 REPORT FEATURES:
• Sector-based stock organization
• ARIMA & LSTM model agreement analysis
• Fresh news sentiment data
• Contrarian investment logic
• Interactive tables and charts

⚠️ DISCLAIMER:
This analysis is for educational purposes only.
Always consult financial advisors before making investment decisions.

🔄 UPDATES:
For fresh analysis, request a new report as market data changes daily.
    """
    
    instructions_path = os.path.join(output_dir, "README.txt")
    with open(instructions_path, 'w') as f:
        f.write(instructions_content)
    
    # Create ZIP package
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        zipf.write(html_file_path, os.path.basename(html_file_path))
        zipf.write(instructions_path, "README.txt")
    
    # Clean up temporary instructions file
    os.remove(instructions_path)
    
    print(f"📦 Shareable package created: {zip_path}")
    print(f"📤 Send this ZIP file to your friend via email, WhatsApp, or cloud storage")
    
    return zip_path

def create_github_pages_instructions(html_file_path):
    """Generate instructions for hosting on GitHub Pages"""
    
    instructions = f"""
📚 GITHUB PAGES HOSTING INSTRUCTIONS (FREE PERMANENT HOSTING):

1. 📁 Create a new GitHub repository:
   - Go to github.com and sign in
   - Click "New repository" (green button)
   - Name it: "stock-analysis-reports"
   - Make it PUBLIC (important!)
   - Check "Add a README file"
   - Click "Create repository"

2. 📤 Upload your HTML file:
   - Click "Add file" → "Upload files"
   - Drag your HTML file: {os.path.basename(html_file_path)}
   - RENAME it to: index.html (very important!)
   - Write commit message: "Add stock analysis report"
   - Click "Commit new file"

3. 🌐 Enable GitHub Pages:
   - Go to repository "Settings" tab
   - Scroll down to "Pages" section (left sidebar)
   - Source: "Deploy from a branch"
   - Branch: "main" (or "master")
   - Folder: "/ (root)"
   - Click "Save"

4. 🔗 Get your public link:
   - Wait 2-3 minutes for deployment
   - Your report will be available at:
   - https://yourusername.github.io/stock-analysis-reports/
   - Share this link with anyone worldwide!

✅ Benefits: 
   • Completely free
   • Permanent hosting
   • Accessible worldwide
   • HTTPS secure
   • No file size limits
   • Professional URL

📱 Your friend can access it on any device with internet!
"""
    
    print(instructions)
    
    # Also save instructions to file
    instructions_file = os.path.join(os.path.dirname(html_file_path), "github_pages_instructions.txt")
    with open(instructions_file, 'w') as f:
        f.write(instructions)
    
    print(f"📄 Instructions saved to: {instructions_file}")
    return instructions

def show_cloud_storage_options(html_file_path):
    """Show cloud storage sharing options"""
    
    instructions = f"""
☁️ CLOUD STORAGE SHARING OPTIONS:

📁 GOOGLE DRIVE (Recommended):
   1. Go to drive.google.com
   2. Click "New" → "File upload"
   3. Upload: {os.path.basename(html_file_path)}
   4. Right-click uploaded file → "Get link"
   5. Change permissions: "Anyone with the link can view"
   6. Copy and share the link

📁 MICROSOFT ONEDRIVE:
   1. Go to onedrive.live.com
   2. Upload your HTML file
   3. Right-click file → "Share"
   4. Set to "Anyone with the link can view"
   5. Copy and share the generated link

📁 DROPBOX:
   1. Go to dropbox.com
   2. Upload your HTML file
   3. Click "Share" button
   4. Click "Create link"
   5. Copy and share the link

📁 WETRANSFER (No account needed):
   1. Go to wetransfer.com
   2. Click "Add your files"
   3. Upload: {os.path.basename(html_file_path)}
   4. Enter your friend's email
   5. Add message and send
   6. They'll get a download link

✅ All these services allow your friend to download and view the report!
💡 Tip: Google Drive and OneDrive can preview HTML files directly in browser!
"""
    
    print(instructions)
    return instructions

def send_report_by_email(html_file_path, recipient_email, sender_email=None, sender_password=None):
    """Send the HTML report by email"""
    
    if not sender_email or not sender_password:
        print("\n📧 EMAIL SETUP REQUIRED:")
        print("To send emails automatically, you need to:")
        print("1. Use Gmail with 'App Password' (not regular password)")
        print("2. Go to Gmail Settings → Security → 2-Step Verification → App Passwords")
        print("3. Generate an app password for this script")
        print("4. Update the script with your credentials")
        print("\nFor now, please use other sharing methods.")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"Stock Analysis Report - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Email body
        body = f"""
Hi!

I've generated a comprehensive stock analysis report using advanced ARIMA-LSTM models with sentiment analysis.

📊 THE REPORT INCLUDES:
• Sector-based organization of stocks
• Model agreement analysis (ARIMA & LSTM)
• Fresh news sentiment data
• Contrarian logic insights
• Interactive HTML format

🔧 HOW TO VIEW:
1. Download the attached HTML file
2. Double-click to open in any browser
3. Works offline - no internet required!

📅 Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⚠️ DISCLAIMER: This analysis is for educational purposes only. Always consult with financial advisors before making investment decisions.

Best regards!
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach HTML file
        with open(html_file_path, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename= {os.path.basename(html_file_path)}'
        )
        
        msg.attach(part)
        
        # Send email (Gmail example)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        
        print(f"✅ Report sent successfully to {recipient_email}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        print("💡 Try using cloud storage or ZIP package sharing instead")
        return False

def show_ngrok_instructions():
    """Show ngrok setup instructions for worldwide instant sharing"""
    
    instructions = """
🌍 NGROK - INSTANT WORLDWIDE SHARING (Advanced Option):

📥 SETUP (One-time):
   1. Go to ngrok.com and create free account
   2. Download ngrok for your operating system
   3. Unzip and place ngrok.exe in your project folder
   4. Get your auth token from ngrok dashboard
   5. Run: ngrok authtoken YOUR_AUTH_TOKEN

🚀 SHARE YOUR REPORT:
   1. Keep your analysis server running
   2. Open new terminal/command prompt
   3. Run: ngrok http 8000
   4. Copy the https://xxxxx.ngrok.io URL
   5. Share this URL - works worldwide instantly!

✅ BENEFITS:
   • Instant worldwide access
   • HTTPS secure connection
   • No file uploads needed
   • Works on any device/browser
   • Real-time updates

⚠️ NOTE: Free ngrok URLs expire when you close the tunnel
💡 Perfect for live sharing during presentations!
"""
    
    print(instructions)
    return instructions

# ======= EXISTING ANALYSIS FUNCTIONS (keeping all your original code) =======

def setup_logging():
    """Set up logging configuration"""
    log_dir = os.path.join(config.OUTPUT_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f'sector_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also log to console
        ]
    )
    return log_file

def check_model_agreement(result, min_agreement_threshold=0.5):
    """
    Check if ARIMA and LSTM models agree on direction
    Returns True only if both models predict the same direction (up or down)
    """
    try:
        current_price = result.get('current_price', 0)
        arima_prediction = result.get('arima_prediction', 0)
        lstm_prediction = result.get('lstm_prediction', 0)
        
        if current_price <= 0 or arima_prediction <= 0 or lstm_prediction <= 0:
            return False
        
        # Calculate percentage changes
        arima_change = ((arima_prediction - current_price) / current_price) * 100
        lstm_change = ((lstm_prediction - current_price) / current_price) * 100
        
        # Store changes in result for later use
        result['arima_change_pct'] = arima_change
        result['lstm_change_pct'] = lstm_change
        
        # Check if both models agree on direction
        models_agree = (arima_change > 0 and lstm_change > 0) or (arima_change < 0 and lstm_change < 0)
        
        # Additional check: changes should be significant enough (at least 0.5%)
        arima_significant = abs(arima_change) >= min_agreement_threshold
        lstm_significant = abs(lstm_change) >= min_agreement_threshold
        
        return models_agree and arima_significant and lstm_significant
        
    except Exception as e:
        print(f"Error checking model agreement: {e}")
        return False

def enhanced_contrarian_analysis(technical_result, sentiment_data, arima_error_threshold=30):
    """
    Enhanced contrarian sentiment analysis with proper ARIMA error checking
    FIXED: Only show sentiment if articles are actually found
    """
    
    # Extract technical analysis data
    current_price = technical_result.get('current_price', 0)
    arima_prediction = technical_result.get('arima_prediction', 0)
    lstm_prediction = technical_result.get('lstm_prediction', 0)
    original_recommendation = technical_result.get('recommendation', 'HOLD')
    original_confidence = technical_result.get('confidence', 70)
    
    # Calculate ARIMA error percentage
    if current_price > 0 and arima_prediction > 0:
        arima_error_pct = abs((arima_prediction - current_price) / current_price) * 100
    else:
        arima_error_pct = 100  # High error if no price data
    
    # Extract sentiment data with PROPER VALIDATION
    article_count = sentiment_data.get('article_count', 0)
    overall_sentiment = sentiment_data.get('overall_sentiment', 'neutral')
    sentiment_confidence = sentiment_data.get('confidence', 0.0)
    
    # Get fresh news articles for debugging
    recent_news = sentiment_data.get('recent_articles', [])
    
    # CRITICAL FIX: Only process sentiment if we actually have articles
    if article_count > 0 and recent_news:
        news_summary = f"{len(recent_news)} articles found"
        if recent_news:
            latest_date = max([article.get('date', '') for article in recent_news])
            news_summary += f", latest: {latest_date}"
        
        # Convert to expected format ONLY if we have articles
        if overall_sentiment == 'negative' and sentiment_confidence > 0.3:
            sentiment_signal = 'BEARISH'
        elif overall_sentiment == 'negative' and sentiment_confidence > 0.2:
            sentiment_signal = 'WEAK_BEARISH'
        elif overall_sentiment == 'positive' and sentiment_confidence > 0.4:
            sentiment_signal = 'BULLISH'
        elif overall_sentiment == 'positive' and sentiment_confidence > 0.2:
            sentiment_signal = 'WEAK_BULLISH'
        else:
            sentiment_signal = 'NEUTRAL'
    else:
        # NO ARTICLES = NO SENTIMENT DATA
        news_summary = f"0 articles found"
        sentiment_signal = 'NO_DATA'
        sentiment_confidence = 0.0
        article_count = 0
        recent_news = []
        overall_sentiment = 'no_data'
    
    sentiment_score = sentiment_confidence
    news_count = article_count
    
    # Initialize result
    result = {
        **technical_result,
        'sentiment_signal': sentiment_signal,
        'sentiment_score': sentiment_score,
        'sentiment_confidence': sentiment_confidence,
        'news_count': news_count,
        'news_summary': news_summary,
        'recent_articles': recent_news[:3],  # Keep top 3 for HTML display
        'arima_error_pct': arima_error_pct,
        'arima_error_threshold': arima_error_threshold,
        'original_recommendation': original_recommendation,
        'original_confidence': original_confidence
    }
    
    # Apply contrarian logic ONLY if we have actual sentiment data
    contrarian_applied = False
    contrarian_reason = ""
    
    print(f"   🔍 ARIMA Error: {arima_error_pct:.1f}% (threshold: {arima_error_threshold}%)")
    print(f"   📰 News: {news_summary}, Sentiment: {sentiment_signal} (conf: {sentiment_confidence:.1f}%)")
    
    # FIXED LOGIC: Only apply contrarian if we have actual articles AND sentiment
    if (arima_error_pct < arima_error_threshold and 
        news_count >= 1 and 
        sentiment_confidence > 50 and 
        sentiment_signal not in ['NO_DATA', 'NEUTRAL']):
        
        if sentiment_signal in ['BEARISH', 'WEAK_BEARISH']:
            # Bearish sentiment = Contrarian BUY
            result['recommendation'] = 'BUY'
            result['enhancement_status'] = 'CONTRARIAN_BUY'
            result['confidence'] = min(95, original_confidence + 15)
            contrarian_applied = True
            contrarian_reason = f"✅ CONTRARIAN BUY: Bearish sentiment ({sentiment_signal}) + Low ARIMA error ({arima_error_pct:.1f}%) = Market oversold, BUY opportunity"
            
        elif sentiment_signal in ['BULLISH', 'WEAK_BULLISH']:
            # Bullish sentiment = Contrarian SELL
            result['recommendation'] = 'SELL'
            result['enhancement_status'] = 'CONTRARIAN_SELL'
            result['confidence'] = min(95, original_confidence + 15)
            contrarian_applied = True
            contrarian_reason = f"✅ CONTRARIAN SELL: Bullish sentiment ({sentiment_signal}) + Low ARIMA error ({arima_error_pct:.1f}%) = Market overbought, SELL opportunity"
    else:
        # Conditions not met for contrarian approach
        result['confidence'] = original_confidence
        
        if sentiment_signal == 'NO_DATA':
            result['enhancement_status'] = 'NO_NEWS_DATA'
            contrarian_reason = f"ℹ️ NO NEWS: No articles found = Using technical analysis: {original_recommendation}"
        elif arima_error_pct >= arima_error_threshold:
            result['enhancement_status'] = 'HIGH_ARIMA_ERROR'
            contrarian_reason = f"⚠️ HIGH ERROR: ARIMA error too high ({arima_error_pct:.1f}% >= {arima_error_threshold}%) = Using technical analysis: {original_recommendation}"
        elif news_count < 1:
            result['enhancement_status'] = 'INSUFFICIENT_NEWS'
            contrarian_reason = f"⚠️ NO NEWS: Insufficient news data ({news_count} articles) = Using technical analysis: {original_recommendation}"
        elif sentiment_confidence <= 50:
            result['enhancement_status'] = 'LOW_SENTIMENT_CONFIDENCE'
            contrarian_reason = f"⚠️ LOW CONF: Sentiment confidence too low ({sentiment_confidence:.1f}% <= 50%) = Using technical analysis: {original_recommendation}"
        elif sentiment_signal == 'NEUTRAL':
            result['enhancement_status'] = 'NEUTRAL_SENTIMENT'
            contrarian_reason = f"➡️ NEUTRAL: Neutral sentiment + Low ARIMA error ({arima_error_pct:.1f}%) = Using technical analysis: {original_recommendation}"
        else:
            result['enhancement_status'] = 'TECHNICAL_ONLY'
            contrarian_reason = f"➡️ TECHNICAL: Conditions not met for contrarian approach = Using technical analysis: {original_recommendation}"
    
    # Add explanation
    result['contrarian_applied'] = contrarian_applied
    result['contrarian_reason'] = contrarian_reason
    
    return result

def enhanced_analyze_stock_with_contrarian(market_analyzer, sentiment_service, ticker, company_name, arima_error_threshold=30):
    """
    Enhanced stock analysis with contrarian sentiment logic
    """
    try:
        base_ticker = ticker.replace('.NS', '')
        
        print(f"🔍 Analyzing {base_ticker} with CONTRARIAN sentiment logic...")
        
        # Get technical analysis first
        try:
            nse_ticker = f"{base_ticker}.NS"
            technical_result = market_analyzer.analyze_stock(nse_ticker, company_name)
        except:
            technical_result = market_analyzer.analyze_stock(base_ticker, company_name)
        
        if not technical_result or technical_result.get('current_price') is None:
            return {
                'ticker': base_ticker,
                'company_name': company_name or base_ticker,
                'error': 'No technical analysis data available',
                'recommendation': 'HOLD',
                'confidence': 0.0,
                'enhancement_status': 'TECHNICAL_FAILED',
                'models_agree': False
            }
        
        # Check model agreement
        models_agree = check_model_agreement(technical_result)
        technical_result['models_agree'] = models_agree
        
        # Clear sentiment cache to get fresh news
        if sentiment_service and hasattr(sentiment_service, 'news_cache'):
            sentiment_service.news_cache = {}
        if sentiment_service and hasattr(sentiment_service, 'cache_timestamp'):
            sentiment_service.cache_timestamp = None
        
        # Get sentiment data
        if sentiment_service:
            sentiment_data = sentiment_service.get_sentiment_analysis(base_ticker)
            
            # Apply contrarian logic
            enhanced_result = enhanced_contrarian_analysis(
                technical_result, 
                sentiment_data, 
                arima_error_threshold
            )
        else:
            enhanced_result = technical_result
            enhanced_result['enhancement_status'] = 'NO_SENTIMENT_SERVICE'
        
        # Add sector info
        if sentiment_service and hasattr(sentiment_service, 'sector_mapping'):
            enhanced_result['sector'] = sentiment_service.sector_mapping.get(base_ticker, 'UNKNOWN')
        else:
            enhanced_result['sector'] = 'UNKNOWN'
        
        print(f"   {enhanced_result.get('contrarian_reason', 'Technical analysis only')}")
        print(f"   📊 Final: {enhanced_result['recommendation']} (confidence: {enhanced_result['confidence']:.1f}%)")
        
        return enhanced_result
        
    except Exception as e:
        print(f"❌ Error in contrarian analysis for {ticker}: {e}")
        return {
            'ticker': ticker.replace('.NS', ''),
            'company_name': company_name or ticker,
            'error': str(e),
            'recommendation': 'HOLD',
            'confidence': 0.0,
            'enhancement_status': 'ERROR',
            'models_agree': False
        }

def organize_stocks_by_sector(results):
    """
    Organize stocks by sector with BUY and SELL recommendations in descending order
    Only include stocks where models agree
    """
    # Filter only stocks where models agree
    agreed_stocks = [r for r in results if r.get('models_agree', False)]
    
    # Group by sector
    sector_groups = {}
    for stock in agreed_stocks:
        sector = stock.get('sector', 'UNKNOWN')
        if sector not in sector_groups:
            sector_groups[sector] = {'BUY': [], 'SELL': [], 'HOLD': []}
        
        recommendation = stock.get('recommendation', 'HOLD')
        if recommendation in ['BUY', 'SELL', 'HOLD']:
            sector_groups[sector][recommendation].append(stock)
    
    # Sort within each sector by change percentage (descending)
    for sector in sector_groups:
        for rec_type in ['BUY', 'SELL', 'HOLD']:
            sector_groups[sector][rec_type].sort(
                key=lambda x: abs(x.get('combined_change_pct', 0)), 
                reverse=True
            )
    
    # Sort sectors by average performance
    sector_performance = []
    for sector, stocks in sector_groups.items():
        all_stocks = stocks['BUY'] + stocks['SELL'] + stocks['HOLD']
        if all_stocks:
            avg_change = sum(s.get('combined_change_pct', 0) for s in all_stocks) / len(all_stocks)
            sector_performance.append((sector, avg_change, stocks))
    
    # Sort sectors by performance (descending)
    sector_performance.sort(key=lambda x: x[1], reverse=True)
    
    return sector_performance

def generate_sector_based_html_report(sector_report, results, output_dir, arima_threshold=30):
    """Generate sector-based HTML report with only model-agreed stocks and fresh news"""
    
    # Get only stocks where models agree
    agreed_stocks = [r for r in results if r.get('models_agree', False)]
    total_analyzed = len(results)
    models_agreed = len(agreed_stocks)
    
    # Organize by sector
    sector_performance = organize_stocks_by_sector(results)
    
    # Calculate statistics
    sentiment_enhanced = sum(1 for r in agreed_stocks if 'sentiment_signal' in r and r.get('news_count', 0) > 0)
    contrarian_signals = sum(1 for r in agreed_stocks if r.get('contrarian_applied', False))
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sector-Based Stock Analysis - {datetime.now().strftime('%Y-%m-%d')}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
                background-color: white;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }}
            .header {{
                text-align: center;
                margin-bottom: 40px;
                padding: 30px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 15px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }}
            .header h1 {{
                margin: 0 0 10px 0;
                font-size: 2.5em;
                font-weight: 700;
            }}
            .header p {{
                margin: 5px 0;
                font-size: 1.1em;
                opacity: 0.9;
            }}
            .summary-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 25px;
                margin-bottom: 40px;
            }}
            .summary-card {{
                background: linear-gradient(145deg, #f8f9fa, #e9ecef);
                padding: 25px;
                border-radius: 15px;
                border-left: 5px solid #007bff;
                box-shadow: 0 5px 15px rgba(0,0,0,0.08);
                transition: transform 0.3s ease;
            }}
            .summary-card:hover {{
                transform: translateY(-5px);
            }}
            .summary-card h3 {{
                margin: 0 0 15px 0;
                color: #333;
                font-size: 1.1em;
            }}
            .summary-card .value {{
                font-size: 2.2em;
                font-weight: bold;
                color: #007bff;
                margin-bottom: 5px;
            }}
            .summary-card .subtitle {{
                color: #6c757d;
                font-size: 0.9em;
            }}
            .sector-section {{
                margin: 40px 0;
                padding: 30px;
                border: 2px solid #e9ecef;
                border-radius: 15px;
                background: linear-gradient(145deg, #ffffff, #f8f9fa);
                box-shadow: 0 5px 15px rgba(0,0,0,0.05);
            }}
            .sector-header {{
                margin-bottom: 25px;
                padding: 20px;
                background: linear-gradient(135deg, #28a745, #20c997);
                color: white;
                border-radius: 10px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .sector-header h2 {{
                margin: 0;
                font-size: 1.8em;
                font-weight: 600;
            }}
            .sector-performance {{
                font-size: 1.2em;
                font-weight: bold;
                background: rgba(255,255,255,0.2);
                padding: 8px 16px;
                border-radius: 20px;
            }}
            .recommendation-group {{
                margin: 25px 0;
            }}
            .recommendation-header {{
                margin-bottom: 15px;
                padding: 15px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 1.1em;
            }}
            .buy-header {{
                background: linear-gradient(145deg, #d4edda, #c3e6cb);
                color: #155724;
                border-left: 5px solid #28a745;
            }}
            .sell-header {{
                background: linear-gradient(145deg, #f8d7da, #f5c6cb);
                color: #721c24;
                border-left: 5px solid #dc3545;
            }}
            .hold-header {{
                background: linear-gradient(145deg, #fff3cd, #ffeaa7);
                color: #856404;
                border-left: 5px solid #ffc107;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 3px 10px rgba(0,0,0,0.06);
            }}
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #e9ecef;
                font-size: 0.9em;
            }}
            th {{
                background: linear-gradient(145deg, #f8f9fa, #e9ecef);
                font-weight: 600;
                color: #333;
            }}
            tr:hover {{
                background-color: #f8f9fa;
            }}
            .buy {{ color: #28a745; font-weight: bold; }}
            .sell {{ color: #dc3545; font-weight: bold; }}
            .hold {{ color: #6c757d; font-weight: bold; }}
            .sentiment-bullish {{ color: #28a745; font-weight: 600; }}
            .sentiment-bearish {{ color: #dc3545; font-weight: 600; }}
            .sentiment-neutral {{ color: #6c757d; font-weight: 600; }}
            .sentiment-no_data {{ color: #6c757d; font-weight: 400; font-style: italic; }}
            .contrarian-badge {{
                background: linear-gradient(145deg, #ff6b35, #f7931e);
                color: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 10px;
                font-weight: bold;
                text-transform: uppercase;
            }}
            .technical-badge {{
                background: linear-gradient(145deg, #6c757d, #495057);
                color: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 10px;
                font-weight: bold;
                text-transform: uppercase;
            }}
            .error-high {{
                background: #fff3cd;
                color: #856404;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: 600;
                font-size: 11px;
            }}
            .error-low {{
                background: #d4edda;
                color: #155724;
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: 600;
                font-size: 11px;
            }}
            .news-preview {{
                font-size: 11px;
                color: #6c757d;
                max-width: 200px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }}
            .no-stocks {{
                text-align: center;
                padding: 20px;
                color: #6c757d;
                font-style: italic;
            }}
            .agreement-stats {{
                background: linear-gradient(145deg, #e3f2fd, #bbdefb);
                padding: 25px;
                border-radius: 15px;
                border-left: 5px solid #2196f3;
                margin: 25px 0;
            }}
            .news-headlines {{
                margin-top: 10px;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 5px;
                font-size: 11px;
            }}
            .news-headline {{
                padding: 3px 0;
                border-bottom: 1px solid #e9ecef;
            }}
            .footer {{
                text-align: center;
                margin-top: 40px;
                padding: 25px;
                background: linear-gradient(145deg, #f8f9fa, #e9ecef);
                border-radius: 15px;
                border: 1px solid #dee2e6;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏭 Sector-Based Stock Analysis</h1>
                <p><strong>ARIMA-LSTM Agreement + Contrarian Sentiment + Fresh News</strong></p>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Only showing stocks where ARIMA & LSTM models agree</p>
            </div>
            
            <div class="summary-grid">
                <div class="summary-card">
                    <h3>📈 Total Stocks Analyzed</h3>
                    <div class="value">{total_analyzed}</div>
                    <div class="subtitle">Complete analysis attempted</div>
                </div>
                <div class="summary-card">
                    <h3>🎯 Models Agree</h3>
                    <div class="value">{models_agreed}</div>
                    <div class="subtitle">ARIMA & LSTM agree on direction</div>
                </div>
                <div class="summary-card">
                    <h3>📰 Sentiment Enhanced</h3>
                    <div class="value">{sentiment_enhanced}</div>
                    <div class="subtitle">With fresh news data</div>
                </div>
                <div class="summary-card">
                    <h3>🔄 Contrarian Signals</h3>
                    <div class="value">{contrarian_signals}</div>
                    <div class="subtitle">Applied contrarian logic</div>
                </div>
            </div>
    """
    
    # Add model agreement explanation
    agreement_rate = (models_agreed / total_analyzed * 100) if total_analyzed > 0 else 0
    html_content += f"""
            <div class="agreement-stats">
                <h4>🎯 Model Agreement Statistics</h4>
                <p><strong>Agreement Rate:</strong> {agreement_rate:.1f}% ({models_agreed} out of {total_analyzed} stocks)</p>
                <p><strong>Filtering Logic:</strong> Only stocks where both ARIMA and LSTM predict the same direction (up or down) are included in this report.</p>
                <p><strong>Fresh News:</strong> News cache is cleared before each analysis to ensure current sentiment data.</p>
                <p><strong>Why Agreement Matters:</strong> When both models agree, predictions are more reliable and actionable.</p>
            </div>
    """
    
    # Add sector-based sections
    for sector_name, avg_performance, sector_stocks in sector_performance:
        total_sector_stocks = len(sector_stocks['BUY']) + len(sector_stocks['SELL']) + len(sector_stocks['HOLD'])
        
        html_content += f"""
            <div class="sector-section">
                <div class="sector-header">
                    <h2>🏭 {sector_name}</h2>
                    <div class="sector-performance">{avg_performance:+.2f}%</div>
                </div>
                <p><strong>Total Stocks with Model Agreement:</strong> {total_sector_stocks}</p>
        """
        
        # Add BUY recommendations
        if sector_stocks['BUY']:
            html_content += f"""
                <div class="recommendation-group">
                    <div class="recommendation-header buy-header">
                        🚀 BUY Recommendations ({len(sector_stocks['BUY'])} stocks) - Sorted by Expected Change
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th>Ticker</th>
                                <th>Company</th>
                                <th>Current Price</th>
                                <th>Predicted</th>
                                <th>Change %</th>
                                <th>Confidence</th>
                                <th>Sentiment</th>
                                <th>ARIMA Err</th>
                                <th>Logic</th>
                                <th>News Summary</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            for stock in sector_stocks['BUY']:
                sentiment_signal = stock.get('sentiment_signal', 'NO_DATA')
                if sentiment_signal == 'NO_DATA':
                    sentiment_class = "sentiment-no_data"
                    sentiment_display = "NO DATA"
                elif sentiment_signal.lower() in ['bullish', 'weak_bullish']:
                    sentiment_class = "sentiment-bullish"
                    sentiment_display = sentiment_signal
                elif sentiment_signal.lower() in ['bearish', 'weak_bearish']:
                    sentiment_class = "sentiment-bearish"
                    sentiment_display = sentiment_signal
                else:
                    sentiment_class = "sentiment-neutral"
                    sentiment_display = sentiment_signal
                    
                logic_badge = 'contrarian-badge' if stock.get('contrarian_applied', False) else 'technical-badge'
                logic_text = 'CONTRARIAN' if stock.get('contrarian_applied', False) else 'TECHNICAL'
                
                arima_error = stock.get('arima_error_pct', 0)
                error_class = 'error-high' if arima_error >= arima_threshold else 'error-low'
                
                news_summary = stock.get('news_summary', 'No news data')
                recent_articles = stock.get('recent_articles', [])
                
                html_content += f"""
                            <tr>
                                <td><strong>{stock.get('ticker', 'N/A')}</strong></td>
                                <td>{stock.get('company_name', 'N/A')}</td>
                                <td>₹{stock.get('current_price', 0):,.2f}</td>
                                <td>₹{stock.get('combined_prediction', 0):,.2f}</td>
                                <td class="buy">{stock.get('combined_change_pct', 0):.2f}%</td>
                                <td>{stock.get('confidence', 0):.1f}%</td>
                                <td class="{sentiment_class}">{sentiment_display}</td>
                                <td class="{error_class}">{arima_error:.1f}%</td>
                                <td><span class="{logic_badge}">{logic_text}</span></td>
                                <td class="news-preview">
                                    {news_summary}
                """
                
                # Add recent headlines if available
                if recent_articles:
                    html_content += """
                                    <div class="news-headlines">
                                        <strong>Recent Headlines:</strong>
                    """
                    for article in recent_articles[:2]:  # Show top 2 headlines
                        title = article.get('title', 'No title')[:60] + '...' if len(article.get('title', '')) > 60 else article.get('title', 'No title')
                        html_content += f"""
                                        <div class="news-headline">• {title}</div>
                        """
                    html_content += """
                                    </div>
                    """
                
                html_content += """
                                </td>
                            </tr>
                """
            
            html_content += """
                        </tbody>
                    </table>
                </div>
            """
        
        # Add SELL recommendations (similar structure)
        if sector_stocks['SELL']:
            html_content += f"""
                <div class="recommendation-group">
                    <div class="recommendation-header sell-header">
                        📉 SELL Recommendations ({len(sector_stocks['SELL'])} stocks) - Sorted by Expected Change
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th>Ticker</th>
                                <th>Company</th>
                                <th>Current Price</th>
                                <th>Predicted</th>
                                <th>Change %</th>
                                <th>Confidence</th>
                                <th>Sentiment</th>
                                <th>ARIMA Err</th>
                                <th>Logic</th>
                                <th>News Summary</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            for stock in sector_stocks['SELL']:
                sentiment_signal = stock.get('sentiment_signal', 'NO_DATA')
                if sentiment_signal == 'NO_DATA':
                    sentiment_class = "sentiment-no_data"
                    sentiment_display = "NO DATA"
                elif sentiment_signal.lower() in ['bullish', 'weak_bullish']:
                    sentiment_class = "sentiment-bullish"
                    sentiment_display = sentiment_signal
                elif sentiment_signal.lower() in ['bearish', 'weak_bearish']:
                    sentiment_class = "sentiment-bearish"
                    sentiment_display = sentiment_signal
                else:
                    sentiment_class = "sentiment-neutral"
                    sentiment_display = sentiment_signal
                    
                logic_badge = 'contrarian-badge' if stock.get('contrarian_applied', False) else 'technical-badge'
                logic_text = 'CONTRARIAN' if stock.get('contrarian_applied', False) else 'TECHNICAL'
                
                arima_error = stock.get('arima_error_pct', 0)
                error_class = 'error-high' if arima_error >= arima_threshold else 'error-low'
                
                news_summary = stock.get('news_summary', 'No news data')
                recent_articles = stock.get('recent_articles', [])
                
                html_content += f"""
                            <tr>
                                <td><strong>{stock.get('ticker', 'N/A')}</strong></td>
                                <td>{stock.get('company_name', 'N/A')}</td>
                                <td>₹{stock.get('current_price', 0):,.2f}</td>
                                <td>₹{stock.get('combined_prediction', 0):,.2f}</td>
                                <td class="sell">{stock.get('combined_change_pct', 0):.2f}%</td>
                                <td>{stock.get('confidence', 0):.1f}%</td>
                                <td class="{sentiment_class}">{sentiment_display}</td>
                                <td class="{error_class}">{arima_error:.1f}%</td>
                                <td><span class="{logic_badge}">{logic_text}</span></td>
                                <td class="news-preview">
                                    {news_summary}
                """
                
                # Add recent headlines if available
                if recent_articles:
                    html_content += """
                                    <div class="news-headlines">
                                        <strong>Recent Headlines:</strong>
                    """
                    for article in recent_articles[:2]:  # Show top 2 headlines
                        title = article.get('title', 'No title')[:60] + '...' if len(article.get('title', '')) > 60 else article.get('title', 'No title')
                        html_content += f"""
                                        <div class="news-headline">• {title}</div>
                        """
                    html_content += """
                                    </div>
                    """
                
                html_content += """
                                </td>
                            </tr>
                """
            
            html_content += """
                        </tbody>
                    </table>
                </div>
            """
        
        # Show message if no stocks in this sector have model agreement
        if total_sector_stocks == 0:
            html_content += """
                <div class="no-stocks">
                    No stocks in this sector have ARIMA-LSTM model agreement
                </div>
            """
        
        html_content += """
            </div>
        """
    
    # Add footer
    html_content += f"""
            <div class="footer">
                <p><strong>📅 Report generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}</strong></p>
                <p><em>This report shows only stocks where ARIMA and LSTM models agree on direction.</em></p>
                <p><em>Stocks are organized by sector with recommendations in descending order by expected change.</em></p>
                <p><em>Fresh news data is fetched for each analysis run to ensure current sentiment.</em></p>
                <p><em>Recent headlines are displayed for each stock with available news data.</em></p>
                <p style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #dee2e6;">
                    <strong>⚠️ Disclaimer:</strong> This is for educational purposes only. Always consult with financial advisors before making investment decisions.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Save HTML file
    html_filename = f"sector_based_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    html_path = os.path.join(output_dir, html_filename)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return html_path

# ======= INTERACTIVE SHARING MENU =======

def show_sharing_menu(html_file_path, output_dir):
    """Show interactive sharing menu"""
    
    print(f"\n🤝 ====== SHARING OPTIONS MENU ======")
    print(f"📄 Report: {os.path.basename(html_file_path)}")
    print(f"📍 Location: {html_file_path}")
    print(f"\nChoose how to share your report:")
    print(f"1. 📦 Create ZIP package (Email/WhatsApp friendly)")
    print(f"2. 🌐 Start local server (Network sharing)")
    print(f"3. ☁️ Cloud storage options (Google Drive, OneDrive)")
    print(f"4. 📚 GitHub Pages setup (Free permanent hosting)")
    print(f"5. 📧 Email setup instructions")
    print(f"6. 🌍 ngrok setup (Advanced worldwide sharing)")
    print(f"7. 📱 View all options")
    print(f"0. ⏭️  Skip sharing")
    
    while True:
        try:
            choice = input(f"\nEnter your choice (0-7): ").strip()
            
            if choice == "0":
                print("Skipping sharing options.")
                break
                
            elif choice == "1":
                print(f"\n📦 Creating ZIP package...")
                zip_path = create_shareable_package(html_file_path, output_dir)
                print(f"✅ ZIP package created successfully!")
                print(f"📤 Share this file: {zip_path}")
                print(f"💡 Send via email, WhatsApp, or any file sharing method")
                break
                
            elif choice == "2":
                print(f"\n🌐 Starting local web server...")
                httpd, port = start_local_server(html_file_path)
                if httpd:
                    try:
                        input(f"\n⏸️  Server is running! Press Enter to stop...")
                        httpd.shutdown()
                        print("🛑 Server stopped.")
                    except KeyboardInterrupt:
                        httpd.shutdown()
                        print("\n🛑 Server stopped.")
                break
                
            elif choice == "3":
                print(f"\n☁️ Cloud Storage Options:")
                show_cloud_storage_options(html_file_path)
                break
                
            elif choice == "4":
                print(f"\n📚 GitHub Pages Setup:")
                create_github_pages_instructions(html_file_path)
                break
                
            elif choice == "5":
                print(f"\n📧 Email Sharing:")
                recipient = input("Enter recipient email (or press Enter to skip): ").strip()
                if recipient:
                    print("📧 Email functionality requires setup of sender credentials.")
                    print("💡 For now, use ZIP package option and attach to your email client.")
                else:
                    print("Skipped email setup.")
                break
                
            elif choice == "6":
                print(f"\n🌍 ngrok Setup (Advanced):")
                show_ngrok_instructions()
                break
                
            elif choice == "7":
                print(f"\n📱 All Sharing Options:")
                print(f"1. ZIP Package: Best for email/messaging")
                print(f"2. Local Server: Best for same network sharing")
                print(f"3. Cloud Storage: Best for permanent links")
                print(f"4. GitHub Pages: Best for worldwide permanent hosting")
                print(f"5. Email: Direct sending (requires setup)")
                print(f"6. ngrok: Best for live worldwide sharing")
                continue
                
            else:
                print("❌ Invalid choice. Please enter 0-7.")
                continue
                
        except KeyboardInterrupt:
            print("\n🛑 Sharing menu cancelled.")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            continue

# ======= MODIFY YOUR EXISTING FUNCTIONS (keeping all original code) =======

def save_results(results, base_output_dir):
    """Save stock analysis results in JSON file"""
    # Ensure output directory exists
    os.makedirs(base_output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"sector_analysis_contrarian_{timestamp}.json"
    
    # Full path for saving
    json_path = os.path.join(base_output_dir, filename)
    
    try:
        # Create consolidated data structure
        consolidated_data = {
            'timestamp': timestamp,
            'analysis_date': datetime.now().strftime('%Y-%m-%d'),
            'sentiment_enhanced': any('sentiment_signal' in result for result in results),
            'contrarian_applied': any(result.get('contrarian_applied', False) for result in results),
            'results': results
        }
        
        # Save results
        with open(json_path, 'w') as f:
            json.dump(consolidated_data, f, indent=2)
        
        logging.info(f"Saved consolidated analysis results to {json_path}")
        return json_path
    
    except Exception as e:
        logging.error(f"Error saving results: {str(e)}")
        return None

def display_sector_summary(sector_analysis):
    """Display sector performance summary in a table"""
    sector_data = []
    headers = ['Sector', 'Avg Change%', 'Direction', 'Status']
    
    for sector_info in sector_analysis['sector_performance']:
        sector = sector_info['sector']
        avg_change = sector_info['avg_change']
        direction = sector_info['direction']
        color = sector_info['color']
        
        row = [
            sector,
            f"{avg_change:.2f}%",
            direction,
            color
        ]
        sector_data.append(row)
    
    # Print table
    print("\n=== SECTOR PERFORMANCE SUMMARY ===")
    if sector_data:
        print(tabulate(sector_data, headers=headers, tablefmt="grid"))
    else:
        print("No sector data available")

def display_top_picks(report_data):
    """Display top BUY and SELL recommendations with contrarian information"""
    # Display top BUY recommendations
    print("\n=== TOP BUY RECOMMENDATIONS (ARIMA & LSTM AGREE + CONTRARIAN LOGIC) ===")
    if report_data['top_buy']:
        buy_data = []
        for i, stock in enumerate(report_data['top_buy']):
            # Check if we have sentiment data
            sentiment_info = ""
            if 'sentiment_signal' in stock:
                sentiment_info = f" | {stock.get('sentiment_signal', 'N/A')}"
                if stock.get('contrarian_applied', False):
                    sentiment_info += " 🔄"
                elif stock.get('enhancement_status') in ['BULLISH_AGREEMENT', 'BEARISH_AGREEMENT']:
                    sentiment_info += " ✅"
                elif stock.get('enhancement_status') == 'CONFLICTING_SIGNALS':
                    sentiment_info += " ⚠️"
            
            # Add contrarian indicator
            logic_type = "CONTRARIAN" if stock.get('contrarian_applied', False) else "TECHNICAL"
            arima_error = stock.get('arima_error_pct', 0)
            
            buy_data.append([
                i+1,
                stock.get('ticker', 'N/A'),
                stock.get('company_name', 'N/A'),
                stock.get('sector', 'N/A'),
                f"{stock.get('current_price', 0):.2f}",
                f"{stock.get('combined_prediction', 0):.2f}",
                f"{stock.get('combined_change_pct', 0):.2f}%",
                f"{stock.get('confidence', 0):.1f}%",
                sentiment_info,
                f"{arima_error:.1f}%",
                logic_type
            ])
        
        buy_headers = ['Rank', 'Ticker', 'Company', 'Sector', 'Current', 'Prediction', 'Change%', 'Confidence', 'Sentiment', 'ARIMA Err%', 'Logic']
        print(tabulate(buy_data, headers=buy_headers, tablefmt="grid"))
    else:
        print("No BUY recommendations available")

def run_analysis(num_stocks=None, output_dir=None, enable_sentiment=True, arima_error_threshold=30):
    """
    Run sector-based analysis with ARIMA-LSTM agreement focus + contrarian sentiment enhancement + SHARING
    """
    # Setup logging
    setup_logging()
    logging.info(f"Starting sector-based stock analysis with CONTRARIAN logic + SHARING - {datetime.now().strftime('%Y-%m-%d')}")
    
    # Set output directory
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    
    # Create analyzer services
    market_analyzer = MarketAnalysisService(output_dir=output_dir)
    sector_analyzer = SectorAnalyzer(market_analyzer, output_dir=output_dir)
    
    # Initialize sentiment service if enabled
    sentiment_service = None
    if enable_sentiment and SENTIMENT_AVAILABLE:
        try:
            sentiment_service = SentimentAnalysisService(days_back=7, min_headlines=1)
            sentiment_service.news_cache = {}
            sentiment_service.cache_timestamp = None
            print(f"✅ Sentiment analysis service initialized with fresh news fetching")
        except Exception as e:
            print(f"⚠️ Failed to initialize sentiment service: {e}")
            sentiment_service = None
    
    # Get stocks to analyze
    stocks_to_analyze = config.TOP_STOCKS
    if num_stocks and num_stocks > 0:
        stocks_to_analyze = stocks_to_analyze[:num_stocks]
    
    print(f"\nAnalyzing {len(stocks_to_analyze)} stocks for sector-based analysis with sharing capabilities...")
    
    # Track results
    results = []
    failed_stocks = []
    
    # Analyze each stock
    for idx, stock in enumerate(stocks_to_analyze):
        try:
            print(f"\n[{idx+1}/{len(stocks_to_analyze)}] Analyzing {stock['name']} ({stock['symbol']})...")
            
            # Use contrarian enhanced analysis if sentiment is available
            if sentiment_service:
                result = enhanced_analyze_stock_with_contrarian(
                    market_analyzer, 
                    sentiment_service, 
                    stock['symbol'], 
                    stock['name'],
                    arima_error_threshold
                )
                if 'sector' not in result:
                    result['sector'] = sector_analyzer.get_stock_sector(stock['symbol'])
            else:
                # Regular technical analysis
                result = market_analyzer.analyze_stock(stock['symbol'], stock['name'])
                models_agree = check_model_agreement(result)
                result['models_agree'] = models_agree
                result['sector'] = sector_analyzer.get_stock_sector(stock['symbol'])
            
            # Check if analysis produced meaningful results
            if not result or result.get('current_price') is None:
                logging.warning(f"No meaningful data for {stock['symbol']}")
                failed_stocks.append({
                    'symbol': stock['symbol'],
                    'name': stock['name'],
                    'reason': 'No current price data'
                })
                continue
            
            # Add to results
            results.append(result)
        
        except Exception as e:
            # Log error
            logging.error(f"Error analyzing {stock['symbol']}: {str(e)}")
            
            # Track failed stocks
            failed_stocks.append({
                'symbol': stock['symbol'],
                'name': stock['name'],
                'error': str(e)
            })
            
            # Continue with next stock
            continue
    
    # Handle case where no stocks could be analyzed
    if not results:
        logging.critical("No stocks could be analyzed. Check your data sources and network connection.")
        print("No stocks could be analyzed. Please check logs for details.")
        return None, [], {}
    
    # Print enhancement summary if sentiment was used
    if sentiment_service:
        sentiment_enhanced = sum(1 for r in results if 'sentiment_signal' in r and r.get('news_count', 0) > 0)
        contrarian_applied = sum(1 for r in results if r.get('contrarian_applied', False))
        models_agreed = sum(1 for r in results if r.get('models_agree', False))
        
        print(f"\n📊 ANALYSIS SUMMARY:")
        print(f"   Total stocks analyzed: {len(results)}")
        print(f"   Models agreed: {models_agreed} ({models_agreed/len(results)*100:.1f}%)")
        print(f"   Stocks with fresh news: {sentiment_enhanced}")
        print(f"   Contrarian logic applied: {contrarian_applied}")
    
    # Generate sector-based report
    print("\nGenerating sector-based report with ARIMA-LSTM agreement...")
    sector_report = sector_analyzer.generate_agreement_report(results)
    
    # Save reports
    report_files = {}
    report_files['json'] = save_results(results, output_dir)
    
    # Generate SECTOR-BASED HTML report with SHARING capabilities
    report_files['html_report'] = generate_sector_based_html_report(sector_report, results, output_dir, arima_error_threshold)
    
    # Display results
    display_sector_summary(sector_report)
    display_top_picks(sector_report)
    
    # Print report paths
    print("\n=== REPORT FILES GENERATED ===")
    for name, path in report_files.items():
        if path:
            if name == 'html_report':
                print(f"🌐 {name.replace('_', ' ').title()}: {path}")
                print(f"🔗 Local access: file://{os.path.abspath(path)}")
            else:
                print(f"📄 {name.replace('_', ' ').title()}: {path}")
    
    # ======= INTEGRATED SHARING MENU =======
    if 'html_report' in report_files and report_files['html_report']:
        print(f"\n" + "="*60)
        print(f"🎉 ANALYSIS COMPLETE! Now let's share your report...")
        print(f"="*60)
        
        # Show sharing menu
        show_sharing_menu(report_files['html_report'], output_dir)
    
    return sector_report, results, report_files

def log_analysis_summary(results, failed_stocks, sector_report):
    """Log comprehensive analysis summary"""
    logging.info("\n--- Analysis Summary ---")
    logging.info(f"Total Stocks Analyzed: {len(results) + len(failed_stocks)}")
    logging.info(f"Successfully Analyzed: {len(results)}")
    logging.info(f"Failed Analyses: {len(failed_stocks)}")
    
    # Log sentiment enhancement statistics
    sentiment_enhanced = sum(1 for r in results if 'sentiment_signal' in r and r.get('news_count', 0) > 0)
    contrarian_applied = sum(1 for r in results if r.get('contrarian_applied', False))
    models_agreed = sum(1 for r in results if r.get('models_agree', False))
    
    if sentiment_enhanced > 0:
        enhancement_rate = (sentiment_enhanced / len(results)) * 100
        contrarian_rate = (contrarian_applied / len(results)) * 100
        agreement_rate = (models_agreed / len(results)) * 100
        
        logging.info(f"Model agreement rate: {models_agreed} ({agreement_rate:.1f}%)")
        logging.info(f"Stocks with sentiment enhancement: {sentiment_enhanced} ({enhancement_rate:.1f}%)")
        logging.info(f"Stocks with contrarian logic applied: {contrarian_applied} ({contrarian_rate:.1f}%)")
    
    # Log agreement statistics
    agreement_count = len(sector_report['agreement_stocks'])
    agreement_pct = (agreement_count / len(results)) * 100 if results else 0
    logging.info(f"Stocks with ARIMA-LSTM agreement: {agreement_count} ({agreement_pct:.1f}%)")
    
    # Log buy/sell counts
    buy_count = len(sector_report['top_buy'])
    sell_count = len(sector_report['top_sell'])
    logging.info(f"Top BUY recommendations: {buy_count}")
    logging.info(f"Top SELL recommendations: {sell_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enhanced Sector-Based Stock Analysis Tool with Sharing Capabilities")
    
    parser.add_argument('--top', type=int, help='Analyze top N stocks from the configured list')
    parser.add_argument('--output', type=str, help='Output directory for reports')
    parser.add_argument('--no-sentiment', action='store_true', help='Disable sentiment analysis enhancement')
    parser.add_argument('--arima-threshold', type=float, default=30, help='ARIMA error threshold percentage for contrarian logic (default: 30)')
    parser.add_argument('--auto-share', action='store_true', help='Automatically show sharing menu after analysis')
    
    args = parser.parse_args()
    
    # Determine sentiment flag
    enable_sentiment = not args.no_sentiment
    
    print("🚀 SECTOR-BASED STOCK ANALYSIS TOOL WITH SHARING")
    print("="*65)
    print(f"📊 Technical Analysis: ARIMA + LSTM Agreement")
    print(f"📰 Sentiment Analysis: {'Enabled' if enable_sentiment and SENTIMENT_AVAILABLE else 'Disabled'}")
    print(f"🔄 Contrarian Logic: {'Enabled' if enable_sentiment and SENTIMENT_AVAILABLE else 'Disabled'}")
    print(f"🏭 HTML Organization: SECTOR-BASED with model agreement filter")
    print(f"📅 News Data: FRESH (cache cleared each run)")
    print(f"🤝 Sharing Features: ZIP, Server, Cloud, GitHub Pages, Email")
    print(f"⚙️ ARIMA Error Threshold: {args.arima_threshold}%")
    print("="*65)
    
    # Run sector analysis with sharing
    sector_report, results, report_files = run_analysis(
        args.top, 
        args.output, 
        enable_sentiment,
        args.arima_threshold
    )
    
    # Log summary
    if sector_report and results:
        log_analysis_summary(results, [], sector_report)
        
        sentiment_enhanced = sum(1 for r in results if 'sentiment_signal' in r and r.get('news_count', 0) > 0)
        contrarian_applied = sum(1 for r in results if r.get('contrarian_applied', False))
        models_agreed = sum(1 for r in results if r.get('models_agree', False))
        
        print(f"\n✅ FINAL SUMMARY:")
        print(f"   📊 {len(results)} stocks analyzed")
        print(f"   🎯 {models_agreed} models agreed ({models_agreed/len(results)*100:.1f}%)")
        print(f"   📰 {sentiment_enhanced} enhanced with fresh news")
        print(f"   🔄 {contrarian_applied} with contrarian logic applied")
        print(f"   🎯 {len(sector_report.get('top_buy', []))} BUY recommendations")
        print(f"   🎯 {len(sector_report.get('top_sell', []))} SELL recommendations")
        
        if 'html_report' in report_files:
            print(f"\n🌐 SECTOR-BASED HTML REPORT:")
            print(f"📄 File: {report_files['html_report']}")
            print(f"🔗 Local: file://{os.path.abspath(report_files['html_report'])}")
            
        print(f"\n🎉 ALL FEATURES INTEGRATED:")
        print(f"   ✅ Fresh news data (cache cleared)")
        print(f"   ✅ Sector-based HTML organization")
        print(f"   ✅ Model agreement enforcement")
        print(f"   ✅ Descending order within sectors")
        print(f"   ✅ News headlines displayed in HTML")
        print(f"   ✅ Multiple sharing options integrated")
        print(f"   ✅ Interactive sharing menu")
        print(f"   ✅ ZIP packaging for easy sharing")
        print(f"   ✅ Local server for network access")
        print(f"   ✅ Cloud storage instructions")
        print(f"   ✅ GitHub Pages setup guide")
        
        # Final sharing reminder
        if args.auto_share or input(f"\n🤝 Want to share your report now? (y/n): ").lower().startswith('y'):
            if 'html_report' in report_files:
                show_sharing_menu(report_files['html_report'], args.output or config.OUTPUT_DIR)
        
    print(f"\n🏁 Analysis and sharing setup complete!")
    print(f"💡 Tip: Your friend can now easily access your analysis report!")
    print(f"📞 Need help? All sharing options include detailed instructions.")