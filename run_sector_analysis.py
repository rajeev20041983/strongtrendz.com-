#!/usr/bin/env python
# run_simplified_arima_analysis.py - Pure ARIMA-based stock analysis

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

from datetime import datetime, timedelta
import pytz

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
import numpy as np
from app.services.market_analyzer import MarketAnalysisService
from app.services.sector_analyzer import SectorAnalyzer
from app import config

# Import or patch yfinance with curl_cffi if available
if CURL_CFFI_AVAILABLE:
    try:
        import yfinance as yf
        from curl_cffi import requests as curl_requests
        
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
    zip_filename = f"arima_stock_analysis_package_{timestamp}.zip"
    zip_path = os.path.join(output_dir, zip_filename)
    
    # Create instructions file
    instructions_content = f"""
📊 ARIMA STOCK ANALYSIS REPORT PACKAGE
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
• Pure ARIMA technical analysis
• Sector-based stock organization
• Strong Buy/Strong Sell recommendations only
• ARIMA error < 30% filter
• Current price, ARIMA prediction, combined prediction
• ARIMA error percentage and sector information

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

def show_sharing_menu(html_file_path, output_dir):
    """Show interactive sharing menu"""
    
    print(f"\n🤝 ====== SHARING OPTIONS MENU ======")
    print(f"📄 Report: {os.path.basename(html_file_path)}")
    print(f"📍 Location: {html_file_path}")
    print(f"\nChoose how to share your report:")
    print(f"1. 📦 Create ZIP package (Email/WhatsApp friendly)")
    print(f"2. 🌐 Start local server (Network sharing)")
    print(f"0. ⏭️  Skip sharing")
    
    while True:
        try:
            choice = input(f"\nEnter your choice (0-2): ").strip()
            
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
                
            else:
                print("❌ Invalid choice. Please enter 0-2.")
                continue
                
        except KeyboardInterrupt:
            print("\n🛑 Sharing menu cancelled.")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            continue

# ======= ANALYSIS FUNCTIONS =======

def setup_logging():
    """Set up logging configuration"""
    log_dir = os.path.join(config.OUTPUT_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f'arima_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also log to console
        ]
    )
    return log_file

def calculate_arima_error(result):
    """Calculate ARIMA error percentage"""
    try:
        current_price = result.get('current_price', 0)
        arima_prediction = result.get('arima_prediction', 0)
        
        if current_price <= 0 or arima_prediction <= 0:
            return 100.0  # Return high error if invalid data
        
        # Calculate absolute percentage error
        arima_error = abs((arima_prediction - current_price) / current_price) * 100
        return arima_error
        
    except Exception as e:
        print(f"Error calculating ARIMA error: {e}")
        return 100.0

def filter_strong_recommendations(result, max_arima_error=30.0):
    """
    Filter for Strong Buy/Strong Sell recommendations with ARIMA error < 30%
    """
    try:
        # Check if recommendation exists
        recommendation = result.get('recommendation', 'HOLD')
        
        # Only allow Strong Buy or Strong Sell
        if recommendation not in ['STRONG BUY', 'STRONG SELL']:
            return False
        
        # Calculate and check ARIMA error
        arima_error = calculate_arima_error(result)
        result['arima_error'] = arima_error
        
        # Filter by ARIMA error threshold
        if arima_error >= max_arima_error:
            return False
        
        return True
        
    except Exception as e:
        print(f"Error in filtering: {e}")
        return False

def analyze_stock_simplified(market_analyzer, ticker, company_name):
    """
    Simplified stock analysis with only ARIMA technical analysis
    """
    try:
        base_ticker = ticker.replace('.NS', '')
        
        print(f"🔍 Analyzing {base_ticker} with ARIMA analysis only...")
        
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
                'arima_error': 100.0,
                'sector': 'UNKNOWN'
            }
        
        # Calculate ARIMA error
        arima_error = calculate_arima_error(technical_result)
        technical_result['arima_error'] = arima_error
        
        # Calculate percentage changes for display
        current_price = technical_result.get('current_price', 0)
        arima_prediction = technical_result.get('arima_prediction', 0)
        
        if current_price > 0 and arima_prediction > 0:
            arima_change_pct = ((arima_prediction - current_price) / current_price) * 100
            technical_result['arima_change_pct'] = arima_change_pct
        else:
            technical_result['arima_change_pct'] = 0
        
        print(f"   📊 Current: ₹{current_price:.2f}, ARIMA: ₹{arima_prediction:.2f}")
        print(f"   📈 Change: {technical_result.get('arima_change_pct', 0):.1f}%")
        print(f"   🎯 ARIMA Error: {arima_error:.1f}%")
        print(f"   🏷️ Recommendation: {technical_result.get('recommendation', 'HOLD')}")
        
        return technical_result
        
    except Exception as e:
        print(f"❌ Error in analysis for {ticker}: {e}")
        return {
            'ticker': ticker.replace('.NS', ''),
            'company_name': company_name or ticker,
            'error': str(e),
            'recommendation': 'HOLD',
            'confidence': 0.0,
            'arima_error': 100.0,
            'sector': 'UNKNOWN'
        }

def organize_stocks_by_sector_simplified(results):
    """
    Organize filtered stocks by sector (Strong Buy/Sell only, ARIMA error < 30%)
    """
    # Group by sector
    sector_groups = {}
    for stock in results:
        sector = stock.get('sector', 'UNKNOWN')
        if sector not in sector_groups:
            sector_groups[sector] = {'STRONG BUY': [], 'STRONG SELL': []}
        
        recommendation = stock.get('recommendation', 'HOLD')
        if recommendation == 'STRONG BUY':
            sector_groups[sector]['STRONG BUY'].append(stock)
        elif recommendation == 'STRONG SELL':
            sector_groups[sector]['STRONG SELL'].append(stock)
    
    # Sort within each sector by ARIMA change percentage
    for sector in sector_groups:
        for rec_type in ['STRONG BUY', 'STRONG SELL']:
            sector_groups[sector][rec_type].sort(
                key=lambda x: abs(x.get('arima_change_pct', 0)), 
                reverse=True
            )
    
    # Sort sectors by average performance
    sector_performance = []
    for sector, stocks in sector_groups.items():
        all_stocks = stocks['STRONG BUY'] + stocks['STRONG SELL']
        if all_stocks:
            avg_change = sum(s.get('arima_change_pct', 0) for s in all_stocks) / len(all_stocks)
            sector_performance.append((sector, avg_change, stocks))
    
    # Sort sectors by performance (descending)
    sector_performance.sort(key=lambda x: x[1], reverse=True)
    
    return sector_performance

def generate_simplified_html_report(results, output_dir):
    """Generate simplified HTML report with only ARIMA data"""
    
    # Get filtered results (Strong Buy/Sell with ARIMA error < 30%)
    filtered_results = [r for r in results if filter_strong_recommendations(r)]
    
    # Organize by sector
    sector_performance = organize_stocks_by_sector_simplified(filtered_results)
    
    # Calculate statistics
    total_analyzed = len(results)
    strong_recommendations = len(filtered_results)
    strong_buy_count = sum(1 for r in filtered_results if r.get('recommendation') == 'STRONG BUY')
    strong_sell_count = sum(1 for r in filtered_results if r.get('recommendation') == 'STRONG SELL')
    avg_arima_error = sum(r.get('arima_error', 0) for r in filtered_results) / len(filtered_results) if filtered_results else 0
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ARIMA Stock Analysis - {datetime.now().strftime('%Y-%m-%d')}</title>
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
            .arima-banner {{
                background: linear-gradient(145deg, #007bff, #0056b3);
                color: white;
                padding: 15px;
                border-radius: 10px;
                text-align: center;
                margin: 20px 0;
                font-weight: bold;
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
                background: linear-gradient(135deg, #007bff, #0056b3);
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
            .strong-buy-header {{
                background: linear-gradient(145deg, #d4edda, #c3e6cb);
                color: #155724;
                border-left: 5px solid #28a745;
            }}
            .strong-sell-header {{
                background: linear-gradient(145deg, #f8d7da, #f5c6cb);
                color: #721c24;
                border-left: 5px solid #dc3545;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 3px 10px rgba(0,0,0,0.06);
                font-size: 0.9em;
            }}
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #e9ecef;
            }}
            th {{
                background: linear-gradient(145deg, #f8f9fa, #e9ecef);
                font-weight: 600;
                color: #333;
                font-size: 0.85em;
            }}
            tr:hover {{
                background-color: #f8f9fa;
            }}
            .strong-buy {{ color: #155724; font-weight: bold; background: #d4edda; padding: 4px 8px; border-radius: 4px; }}
            .strong-sell {{ color: #721c24; font-weight: bold; background: #f8d7da; padding: 4px 8px; border-radius: 4px; }}
            .low-error {{ color: #28a745; font-weight: 600; }}
            .sector-tag {{ background: #007bff; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; }}
            .price {{ font-weight: 600; color: #333; }}
            .change-positive {{ color: #28a745; font-weight: 600; }}
            .change-negative {{ color: #dc3545; font-weight: 600; }}
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
                <h1>📈 Pure ARIMA Stock Analysis</h1>
                <p><strong>Strong Buy/Sell Recommendations Only</strong></p>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>ARIMA Error < 30% Filter Applied</p>
            </div>
            
            <div class="arima-banner">
                📊 PURE ARIMA STRATEGY: Technical analysis using ARIMA predictions only<br>
                🎯 Strong Recommendations: STRONG BUY & STRONG SELL only<br>
                ⚡ Quality Filter: ARIMA Error < 30% for reliable predictions
            </div>
            
            <div class="summary-grid">
                <div class="summary-card">
                    <h3>📈 Total Stocks Analyzed</h3>
                    <div class="value">{total_analyzed}</div>
                    <div class="subtitle">Complete analysis attempted</div>
                </div>
                <div class="summary-card">
                    <h3>⚡ Strong Recommendations</h3>
                    <div class="value">{strong_recommendations}</div>
                    <div class="subtitle">ARIMA Error < 30%</div>
                </div>
                <div class="summary-card">
                    <h3>🚀 Strong Buy</h3>
                    <div class="value">{strong_buy_count}</div>
                    <div class="subtitle">Buy recommendations</div>
                </div>
                <div class="summary-card">
                    <h3>📉 Strong Sell</h3>
                    <div class="value">{strong_sell_count}</div>
                    <div class="subtitle">Sell recommendations</div>
                </div>
            </div>
    """
    
    # Add sector-based sections
    for sector_name, avg_performance, sector_stocks in sector_performance:
        total_sector_stocks = len(sector_stocks['STRONG BUY']) + len(sector_stocks['STRONG SELL'])
        
        html_content += f"""
            <div class="sector-section">
                <div class="sector-header">
                    <h2>🏭 {sector_name}</h2>
                    <div class="sector-performance">{avg_performance:+.2f}%</div>
                </div>
                <p><strong>Strong Recommendations:</strong> {total_sector_stocks} stocks</p>
        """
        
        # Add STRONG BUY recommendations
        if sector_stocks['STRONG BUY']:
            html_content += f"""
                <div class="recommendation-group">
                    <div class="recommendation-header strong-buy-header">
                        🚀 STRONG BUY Recommendations ({len(sector_stocks['STRONG BUY'])} stocks)
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th>Ticker</th>
                                <th>Company</th>
                                <th>Sector</th>
                                <th>Current Price</th>
                                <th>ARIMA Prediction</th>
                                <th>Combined Prediction</th>
                                <th>ARIMA Change %</th>
                                <th>ARIMA Error %</th>
                                <th>Signal</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            for stock in sector_stocks['STRONG BUY']:
                arima_change = stock.get('arima_change_pct', 0)
                change_class = 'change-positive' if arima_change > 0 else 'change-negative'
                
                html_content += f"""
                            <tr>
                                <td><strong>{stock.get('ticker', 'N/A')}</strong></td>
                                <td>{stock.get('company_name', 'N/A')[:30]}...</td>
                                <td><span class="sector-tag">{stock.get('sector', 'N/A')}</span></td>
                                <td class="price">₹{stock.get('current_price', 0):,.2f}</td>
                                <td class="price">₹{stock.get('arima_prediction', 0):,.2f}</td>
                                <td class="price">₹{stock.get('combined_prediction', stock.get('arima_prediction', 0)):,.2f}</td>
                                <td class="{change_class}">{arima_change:+.1f}%</td>
                                <td class="low-error">{stock.get('arima_error', 0):.1f}%</td>
                                <td class="strong-buy">STRONG BUY</td>
                            </tr>
                """
            
            html_content += """
                        </tbody>
                    </table>
                </div>
            """
        
        # Add STRONG SELL recommendations
        if sector_stocks['STRONG SELL']:
            html_content += f"""
                <div class="recommendation-group">
                    <div class="recommendation-header strong-sell-header">
                        📉 STRONG SELL Recommendations ({len(sector_stocks['STRONG SELL'])} stocks)
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th>Ticker</th>
                                <th>Company</th>
                                <th>Sector</th>
                                <th>Current Price</th>
                                <th>ARIMA Prediction</th>
                                <th>Combined Prediction</th>
                                <th>ARIMA Change %</th>
                                <th>ARIMA Error %</th>
                                <th>Signal</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            for stock in sector_stocks['STRONG SELL']:
                arima_change = stock.get('arima_change_pct', 0)
                change_class = 'change-positive' if arima_change > 0 else 'change-negative'
                
                html_content += f"""
                            <tr>
                                <td><strong>{stock.get('ticker', 'N/A')}</strong></td>
                                <td>{stock.get('company_name', 'N/A')[:30]}...</td>
                                <td><span class="sector-tag">{stock.get('sector', 'N/A')}</span></td>
                                <td class="price">₹{stock.get('current_price', 0):,.2f}</td>
                                <td class="price">₹{stock.get('arima_prediction', 0):,.2f}</td>
                                <td class="price">₹{stock.get('combined_prediction', stock.get('arima_prediction', 0)):,.2f}</td>
                                <td class="{change_class}">{arima_change:+.1f}%</td>
                                <td class="low-error">{stock.get('arima_error', 0):.1f}%</td>
                                <td class="strong-sell">STRONG SELL</td>
                            </tr>
                """
            
            html_content += """
                        </tbody>
                    </table>
                </div>
            """
        
        # Show message if no stocks in this sector
        if total_sector_stocks == 0:
            html_content += """
                <div style="text-align: center; padding: 20px; color: #6c757d; font-style: italic;">
                    No strong recommendations in this sector with ARIMA error < 30%
                </div>
            """
        
        html_content += """
            </div>
        """
    
    # Add footer
    html_content += f"""
            <div class="footer">
                <p><strong>📊 ARIMA Analysis Report generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}</strong></p>
                <p><em>🎯 Only Strong Buy/Strong Sell recommendations shown</em></p>
                <p><em>📈 ARIMA Error < 30% filter applied for quality predictions</em></p>
                <p><em>💼 Organized by sector for better analysis</em></p>
                <p><em>📊 Average ARIMA Error: {avg_arima_error:.1f}%</em></p>
                <p style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #dee2e6;">
                    <strong>⚠️ Disclaimer:</strong> This is for educational purposes only. Always consult with financial advisors before making investment decisions.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Save HTML file
    html_filename = f"arima_stock_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    html_path = os.path.join(output_dir, html_filename)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return html_path

def save_results(results, base_output_dir):
    """Save stock analysis results in JSON file"""
    # Ensure output directory exists
    os.makedirs(base_output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"arima_analysis_{timestamp}.json"
    
    # Full path for saving
    json_path = os.path.join(base_output_dir, filename)
    
    try:
        # Create consolidated data structure
        consolidated_data = {
            'timestamp': timestamp,
            'analysis_date': datetime.now().strftime('%Y-%m-%d'),
            'arima_only': True,
            'strong_recommendations_only': True,
            'arima_error_threshold': 30.0,
            'results': results
        }
        
        # Save results
        with open(json_path, 'w') as f:
            json.dump(consolidated_data, f, indent=2)
        
        logging.info(f"Saved ARIMA analysis results to {json_path}")
        return json_path
    
    except Exception as e:
        logging.error(f"Error saving results: {str(e)}")
        return None

def display_simplified_summary(results):
    """Display simplified summary with only strong recommendations"""
    
    # Filter results
    filtered_results = [r for r in results if filter_strong_recommendations(r)]
    strong_buy = [r for r in filtered_results if r.get('recommendation') == 'STRONG BUY']
    strong_sell = [r for r in filtered_results if r.get('recommendation') == 'STRONG SELL']
    
    # Display STRONG BUY recommendations
    print("\n=== STRONG BUY RECOMMENDATIONS ===")
    if strong_buy:
        buy_data = []
        for i, stock in enumerate(strong_buy):
            buy_data.append([
                i+1,
                stock.get('ticker', 'N/A'),
                stock.get('company_name', 'N/A')[:25],
                stock.get('sector', 'N/A'),
                f"₹{stock.get('current_price', 0):.2f}",
                f"₹{stock.get('arima_prediction', 0):.2f}",
                f"{stock.get('arima_change_pct', 0):+.1f}%",
                f"{stock.get('arima_error', 0):.1f}%"
            ])
        
        buy_headers = ['#', 'Ticker', 'Company', 'Sector', 'Current', 'ARIMA Pred', 'Change%', 'Error%']
        print(tabulate(buy_data, headers=buy_headers, tablefmt="grid"))
    else:
        print("No STRONG BUY recommendations found")
    
    # Display STRONG SELL recommendations
    print("\n=== STRONG SELL RECOMMENDATIONS ===")  
    if strong_sell:
        sell_data = []
        for i, stock in enumerate(strong_sell):
            sell_data.append([
                i+1,
                stock.get('ticker', 'N/A'),
                stock.get('company_name', 'N/A')[:25],
                stock.get('sector', 'N/A'),
                f"₹{stock.get('current_price', 0):.2f}",
                f"₹{stock.get('arima_prediction', 0):.2f}",
                f"{stock.get('arima_change_pct', 0):+.1f}%",
                f"{stock.get('arima_error', 0):.1f}%"
            ])
        
        sell_headers = ['#', 'Ticker', 'Company', 'Sector', 'Current', 'ARIMA Pred', 'Change%', 'Error%']
        print(tabulate(sell_data, headers=sell_headers, tablefmt="grid"))
    else:
        print("No STRONG SELL recommendations found")

def run_simplified_arima_analysis(num_stocks=None, output_dir=None):
    """
    Run simplified ARIMA-only analysis with strong recommendations filter
    """
    # Setup logging
    setup_logging()
    logging.info(f"Starting simplified ARIMA analysis - {datetime.now().strftime('%Y-%m-%d')}")
    
    # Set output directory
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    
    # Create analyzer services
    market_analyzer = MarketAnalysisService(output_dir=output_dir)
    sector_analyzer = SectorAnalyzer(market_analyzer, output_dir=output_dir)
    
    print(f"✅ Simplified ARIMA analysis initialized")
    
    # Get stocks to analyze
    stocks_to_analyze = config.TOP_STOCKS
    if num_stocks and num_stocks > 0:
        stocks_to_analyze = stocks_to_analyze[:num_stocks]
    
    print(f"\nAnalyzing {len(stocks_to_analyze)} stocks for ARIMA analysis...")
    
    # Track results
    results = []
    failed_stocks = []
    
    # Analyze each stock
    for idx, stock in enumerate(stocks_to_analyze):
        try:
            print(f"\n[{idx+1}/{len(stocks_to_analyze)}] Analyzing {stock['name']} ({stock['symbol']})...")
            
            # Use simplified analysis
            result = analyze_stock_simplified(market_analyzer, stock['symbol'], stock['name'])
            
            if 'sector' not in result:
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
    
    # Filter for strong recommendations
    filtered_results = [r for r in results if filter_strong_recommendations(r)]
    
    # Print summary
    print(f"\n📊 SIMPLIFIED ARIMA ANALYSIS SUMMARY:")
    print(f"   Total stocks analyzed: {len(results)}")
    print(f"   Strong recommendations (ARIMA error < 30%): {len(filtered_results)}")
    strong_buy_count = sum(1 for r in filtered_results if r.get('recommendation') == 'STRONG BUY')
    strong_sell_count = sum(1 for r in filtered_results if r.get('recommendation') == 'STRONG SELL')
    print(f"   Strong Buy: {strong_buy_count}")
    print(f"   Strong Sell: {strong_sell_count}")
    
    if len(filtered_results) == 0:
        print(f"\n⚠️ No stocks meet the criteria (Strong Buy/Sell + ARIMA error < 30%)")
        return None, results, {}
    
    # Save reports
    report_files = {}
    report_files['json'] = save_results(results, output_dir)
    
    # Generate HTML report
    report_files['html_report'] = generate_simplified_html_report(results, output_dir)
    
    # Display results
    display_simplified_summary(results)
    
    # Print report paths
    print("\n=== ARIMA ANALYSIS REPORT FILES ===")
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
        print(f"🎉 ARIMA ANALYSIS COMPLETE! Now let's share your report...")
        print(f"="*60)
        
        # Show sharing menu
        show_sharing_menu(report_files['html_report'], output_dir)
    
    return filtered_results, results, report_files

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simplified ARIMA Stock Analysis Tool")
    
    parser.add_argument('--top', type=int, help='Analyze top N stocks from the configured list')
    parser.add_argument('--output', type=str, help='Output directory for reports')
    parser.add_argument('--auto-share', action='store_true', help='Automatically show sharing menu after analysis')
    
    args = parser.parse_args()
    
    print("🚀 SIMPLIFIED ARIMA STOCK ANALYSIS TOOL")
    print("="*60)
    print(f"📊 Pure ARIMA Technical Analysis")
    print(f"⚡ Strong Buy/Strong Sell Only")
    print(f"🎯 ARIMA Error < 30% Filter")
    print(f"🏭 Sector-Based Organization")
    print(f"🤝 Sharing Features Included")
    print("="*60)
    
    # Run simplified analysis
    filtered_results, all_results, report_files = run_simplified_arima_analysis(args.top, args.output)
    
    # Final summary
    if filtered_results is not None:
        print(f"\n✅ FINAL ARIMA ANALYSIS SUMMARY:")
        print(f"   📊 {len(all_results)} stocks analyzed")
        print(f"   ⚡ {len(filtered_results)} strong recommendations (error < 30%)")
        strong_buy_count = sum(1 for r in filtered_results if r.get('recommendation') == 'STRONG BUY')
        strong_sell_count = sum(1 for r in filtered_results if r.get('recommendation') == 'STRONG SELL')
        print(f"   🚀 {strong_buy_count} Strong Buy")
        print(f"   📉 {strong_sell_count} Strong Sell")
        
        if 'html_report' in report_files:
            print(f"\n🌐 ARIMA HTML REPORT:")
            print(f"📄 File: {report_files['html_report']}")
            print(f"🔗 Local: file://{os.path.abspath(report_files['html_report'])}")
            
        # Final sharing reminder
        if args.auto_share or input(f"\n🤝 Want to share your ARIMA report now? (y/n): ").lower().startswith('y'):
            if 'html_report' in report_files:
                show_sharing_menu(report_files['html_report'], args.output or config.OUTPUT_DIR)
        
    print(f"\n🏁 Simplified ARIMA analysis complete!")