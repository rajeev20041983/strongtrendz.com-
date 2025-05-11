#!/usr/bin/env python
# run_sector_analysis.py - Script for sector-based stock analysis with ARIMA-LSTM agreement

import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, '.vscode'))


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

#!/usr/bin/env python
# run_sector_analysis.py - Script for sector-based stock analysis with ARIMA-LSTM agreement

import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, '.vscode'))

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

def save_results(results, base_output_dir):
    """Save stock analysis results in JSON file"""
    # Ensure output directory exists
    os.makedirs(base_output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"sector_analysis_{timestamp}.json"
    
    # Full path for saving
    json_path = os.path.join(base_output_dir, filename)
    
    try:
        # Create consolidated data structure
        consolidated_data = {
            'timestamp': timestamp,
            'analysis_date': datetime.now().strftime('%Y-%m-%d'),
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

def save_sector_performance_for_powerbi(sector_report, output_dir):
    """
    Create a formatted CSV specifically for Power BI visualization
    """
    # Create output directory if it doesn't exist
    csv_dir = os.path.join(output_dir, 'csv')
    os.makedirs(csv_dir, exist_ok=True)
    
    # Create sector performance dataframe
    sector_data = []
    
    for sector_info in sector_report['sector_performance']:
        sector_data.append({
            'Sector': sector_info['sector'],
            'Performance': sector_info['avg_change'],
            'Direction': sector_info['direction']
        })
    
    # Convert to DataFrame and sort by performance
    df = pd.DataFrame(sector_data)
    df = df.sort_values(by='Performance', ascending=False)
    
    # Save to the specific location
    filepath = os.path.join(csv_dir, 'sector_performance.csv')
    df.to_csv(filepath, index=False)
    
    print(f"Sector performance CSV saved to: {os.path.abspath(filepath)}")
    return filepath

def save_stocks_for_powerbi(sector_report, results, output_dir):
    """
    Create formatted CSV of stocks with their sectors and predictions
    """
    # Create output directory if it doesn't exist
    csv_dir = os.path.join(output_dir, 'csv')
    os.makedirs(csv_dir, exist_ok=True)
    
    # Create dataframe with stock details
    stock_data = []
    
    for result in results:
        if 'arima_prediction' in result and 'lstm_prediction' in result and 'current_price' in result:
            # Calculate model agreement
            arima_change = result.get('arima_change_pct')
            lstm_change = result.get('lstm_change_pct')
            models_agree = False
            
            if arima_change is not None and lstm_change is not None:
                models_agree = (arima_change > 0 and lstm_change > 0) or (arima_change < 0 and lstm_change < 0)
            
            # Add to stock data
            stock_data.append({
                'Ticker': result.get('ticker', ''),
                'Company': result.get('company_name', ''),
                'Sector': result.get('sector', 'UNKNOWN'),
                'Current_Price': result.get('current_price', 0),
                'ARIMA_Prediction': result.get('arima_prediction', 0),
                'LSTM_Prediction': result.get('lstm_prediction', 0),
                'Combined_Prediction': result.get('combined_prediction', 0),
                'ARIMA_Change_Pct': arima_change,
                'LSTM_Change_Pct': lstm_change,
                'Combined_Change_Pct': result.get('combined_change_pct', 0),
                'Models_Agree': 'Yes' if models_agree else 'No',
                'Recommendation': result.get('recommendation', 'UNKNOWN'),
                'Confidence': result.get('confidence', 0)
            })
    
    # Convert to DataFrame
    df = pd.DataFrame(stock_data)
    
    # Save to CSV
    filepath = os.path.join(csv_dir, 'stock_predictions.csv')
    df.to_csv(filepath, index=False)
    
    print(f"Stock predictions CSV saved to: {os.path.abspath(filepath)}")
    return filepath

def save_top_picks_for_powerbi(sector_report, output_dir):
    """
    Create formatted CSV of top buy and sell picks
    """
    # Create output directory if it doesn't exist
    csv_dir = os.path.join(output_dir, 'csv')
    os.makedirs(csv_dir, exist_ok=True)
    
    # Create dataframes for buy and sell
    top_buy_data = []
    top_sell_data = []
    
    # Process top buy stocks
    for i, stock in enumerate(sector_report.get('top_buy', [])):
        top_buy_data.append({
            'Rank': i+1,
            'Ticker': stock.get('ticker', ''),
            'Company': stock.get('company_name', ''),
            'Sector': stock.get('sector', ''),
            'Current_Price': stock.get('current_price', 0),
            'Predicted_Price': stock.get('combined_prediction', 0),
            'Change_Pct': stock.get('combined_change_pct', 0),
            'Confidence': stock.get('confidence', 0),
            'Type': 'BUY'
        })
    
    # Process top sell stocks
    for i, stock in enumerate(sector_report.get('top_sell', [])):
        top_sell_data.append({
            'Rank': i+1,
            'Ticker': stock.get('ticker', ''),
            'Company': stock.get('company_name', ''),
            'Sector': stock.get('sector', ''),
            'Current_Price': stock.get('current_price', 0),
            'Predicted_Price': stock.get('combined_prediction', 0),
            'Change_Pct': stock.get('combined_change_pct', 0),
            'Confidence': stock.get('confidence', 0),
            'Type': 'SELL'
        })
    
    # Combine buy and sell picks
    combined_data = top_buy_data + top_sell_data
    df = pd.DataFrame(combined_data)
    
    # Save to CSV
    filepath = os.path.join(csv_dir, 'top_picks.csv')
    df.to_csv(filepath, index=False)
    
    print(f"Top picks CSV saved to: {os.path.abspath(filepath)}")
    return filepath

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
    """Display top BUY and SELL recommendations"""
    # Display top BUY recommendations
    print("\n=== TOP BUY RECOMMENDATIONS (ARIMA & LSTM AGREE) ===")
    if report_data['top_buy']:
        buy_data = []
        for i, stock in enumerate(report_data['top_buy']):
            buy_data.append([
                i+1,
                stock.get('ticker', 'N/A'),
                stock.get('company_name', 'N/A'),
                stock.get('sector', 'N/A'),
                f"{stock.get('current_price', 0):.2f}",
                f"{stock.get('combined_prediction', 0):.2f}",
                f"{stock.get('combined_change_pct', 0):.2f}%",
                f"{stock.get('confidence', 0):.1f}%"
            ])
        
        buy_headers = ['Rank', 'Ticker', 'Company', 'Sector', 'Current', 'Prediction', 'Change%', 'Confidence']
        print(tabulate(buy_data, headers=buy_headers, tablefmt="grid"))
    else:
        print("No BUY recommendations available")
    
    # Display top SELL recommendations
    print("\n=== TOP SELL RECOMMENDATIONS (ARIMA & LSTM AGREE) ===")
    if report_data['top_sell']:
        sell_data = []
        for i, stock in enumerate(report_data['top_sell']):
            sell_data.append([
                i+1,
                stock.get('ticker', 'N/A'),
                stock.get('company_name', 'N/A'),
                stock.get('sector', 'N/A'),
                f"{stock.get('current_price', 0):.2f}",
                f"{stock.get('combined_prediction', 0):.2f}",
                f"{stock.get('combined_change_pct', 0):.2f}%",
                f"{stock.get('confidence', 0):.1f}%"
            ])
        
        sell_headers = ['Rank', 'Ticker', 'Company', 'Sector', 'Current', 'Prediction', 'Change%', 'Confidence']
        print(tabulate(sell_data, headers=sell_headers, tablefmt="grid"))
    else:
        print("No SELL recommendations available")

def run_analysis(num_stocks=None, output_dir=None):
    """
    Run sector-based analysis with ARIMA-LSTM agreement focus
    
    Parameters:
    - num_stocks: Number of top stocks to analyze (optional)
    - output_dir: Directory to save output files (optional)
    
    Returns:
    - Tuple of (sector_report, results, report_files)
    """
    # Setup logging
    setup_logging()
    logging.info(f"Starting sector-based stock analysis - {datetime.now().strftime('%Y-%m-%d')}")
    
    # Set output directory
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    
    # Ensure the .vscode/output directory exists for PowerBI files
    powerbi_output = r"C:\Users\Rajee\OneDrive\stock\lab\strongtrendz.com-\.vscode\output"
    os.makedirs(powerbi_output, exist_ok=True)
    
    # Create analyzer services
    market_analyzer = MarketAnalysisService(output_dir=output_dir)
    sector_analyzer = SectorAnalyzer(market_analyzer, output_dir=output_dir)
    
    # Get stocks to analyze
    stocks_to_analyze = config.TOP_STOCKS
    if num_stocks and num_stocks > 0:
        stocks_to_analyze = stocks_to_analyze[:num_stocks]
    
    print(f"\nAnalyzing {len(stocks_to_analyze)} stocks for sector-based ARIMA-LSTM agreement...")
    
    # Track results
    results = []
    failed_stocks = []
    
    # Analyze each stock
    for idx, stock in enumerate(stocks_to_analyze):
        try:
            print(f"\n[{idx+1}/{len(stocks_to_analyze)}] Analyzing {stock['name']} ({stock['symbol']})...")
            
            # Perform stock analysis
            result = market_analyzer.analyze_stock(stock['symbol'], stock['name'])
            
            # Add sector information to result
            result['sector'] = sector_analyzer.get_stock_sector(stock['symbol'])
            
            # Check if analysis produced meaningful results
            if result.get('current_price') is None:
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
    
    # Generate sector-based report
    print("\nGenerating sector-based report with ARIMA-LSTM agreement...")
    sector_report = sector_analyzer.generate_agreement_report(results)
    
    # Save reports to CSV for regular analysis
    report_files = {}
    report_files['agreement_csv'] = sector_analyzer.save_report_csv(sector_report)
    report_files['top_picks_csv'] = sector_analyzer.save_top_picks_csv(sector_report)
    report_files['sector_csv'] = sector_analyzer.save_sector_performance_csv(sector_report)
    
    # Save specialized CSVs for Power BI at the specific location
    report_files['powerbi_sector_csv'] = save_sector_performance_for_powerbi(sector_report, powerbi_output)
    report_files['powerbi_stocks_csv'] = save_stocks_for_powerbi(sector_report, results, powerbi_output)
    report_files['powerbi_top_picks_csv'] = save_top_picks_for_powerbi(sector_report, powerbi_output)
    
    # Save consolidated results
    report_files['json'] = save_results(results, output_dir)
    
    # Display results
    display_sector_summary(sector_report)
    display_top_picks(sector_report)
    
    # Print report paths
    print("\n=== REPORT FILES ===")
    for name, path in report_files.items():
        if path:
            print(f"{name.replace('_', ' ').title()}: {path}")
    
    return sector_report, results, report_files

def log_analysis_summary(results, failed_stocks, sector_report):
    """Log comprehensive analysis summary"""
    logging.info("\n--- Analysis Summary ---")
    logging.info(f"Total Stocks Analyzed: {len(results) + len(failed_stocks)}")
    logging.info(f"Successfully Analyzed: {len(results)}")
    logging.info(f"Failed Analyses: {len(failed_stocks)}")
    
    # Log agreement statistics
    agreement_count = len(sector_report['agreement_stocks'])
    agreement_pct = (agreement_count / len(results)) * 100 if results else 0
    logging.info(f"Stocks with ARIMA-LSTM agreement: {agreement_count} ({agreement_pct:.1f}%)")
    
    # Log buy/sell counts
    buy_count = len(sector_report['top_buy'])
    sell_count = len(sector_report['top_sell'])
    logging.info(f"Top BUY recommendations: {buy_count}")
    logging.info(f"Top SELL recommendations: {sell_count}")
    
    # Log sector performance
    logging.info("\nSector Performance:")
    for sector_info in sector_report['sector_performance']:
        sector = sector_info['sector']
        avg_change = sector_info['avg_change']
        direction = sector_info['direction']
        logging.info(f"{sector}: {avg_change:.2f}% ({direction})")
    
    # Log failed stock details if any
    if failed_stocks:
        logging.warning("\nFailed Stock Analyses:")
        for stock in failed_stocks:
            logging.warning(f"Symbol: {stock.get('symbol', 'Unknown')}, "
                           f"Name: {stock.get('name', 'Unknown')}, "
                           f"Reason: {stock.get('error', 'Unspecified error')}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sector-Based Stock Analysis Tool (ARIMA-LSTM Agreement)")
    
    parser.add_argument('--top', type=int, help='Analyze top N stocks from the configured list')
    parser.add_argument('--output', type=str, help='Output directory for reports')
    
    args = parser.parse_args()
    
    # Run sector analysis
    sector_report, results, report_files = run_analysis(args.top, args.output)
    
    # Log summary
    if sector_report and results:
        log_analysis_summary(results, [], sector_report)