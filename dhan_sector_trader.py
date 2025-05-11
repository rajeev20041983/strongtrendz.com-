#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Dhan Sector-Based Trading Program with Sector Ranking
----------------------------------------------------
This program trades stocks based on sector ranking from sector.csv:
1. Checks for a sector.csv file created/updated today
2. Makes trading decisions based on sector ranking:
   - BUY positions only for stocks in TOP 3 positive sectors
   - SELL positions only for stocks in BOTTOM 3 sectors
3. Executes trades through Dhan trading API using provided credentials
4. After initial trades, only monitors and exits positions based on:
   - Stop loss price levels (1% loss)
   - Target price levels (1% profit)
   - Uses Yahoo Finance for price comparisons instead of Dhan API
   - No new trades initiated after the initial trade period
"""

# Standard library imports
import os
import time
import json
import logging
import traceback
import sys
from datetime import datetime, time as dt_time
import re

# Third-party imports
import pandas as pd
import numpy as np  # Explicit numpy import for np.select
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# Dhan API imports
from dhanhq import dhanhq

# Yahoo Finance import
import yfinance as yf

# =================================================================
# Logging Setup
# =================================================================

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Setup logging with both file and console output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/dhan_sector_trader_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

# =================================================================
# Global Variables and Constants
# =================================================================

# Configuration files
SECTOR_MAPPING_FILE = "sector_mapping.json"
TRADING_CONFIG_FILE = "trading_config.json"
SECURITY_IDS_FILE = "security_ids.xlsx"

# Input/Output files
SECTOR_PERFORMANCE_FILE = "sector.csv"  # Default value
POSITIONS_FILE = "dhan_positions.json"

# Default interval between checks (in seconds)
DEFAULT_CHECK_INTERVAL = 60

# Trading window constants
MARKET_OPEN_TIME = dt_time(9, 15)  # 9:15 AM
TRADING_END_TIME = dt_time(15, 30)  # 3:30 PM

# Number of top and bottom sectors to consider
TOP_SECTORS_COUNT = 3
BOTTOM_SECTORS_COUNT = 3

# Flags
INITIAL_TRADES_EXECUTED = False
SECTOR_DATA_CHECKED_TODAY = False

# Fixed profit/loss targets
PROFIT_TARGET_PERCENT = 1.0  # 1% profit target
STOP_LOSS_PERCENT = 1.0      # 1% stop loss

# Price check interval (in seconds)
PRICE_CHECK_INTERVAL = 60    # Check prices every 1 minute

# =================================================================
# Utility Functions
# =================================================================

def log_separator(message=""):
    """Print a separator line in the log for better readability"""
    separator = "=" * 50
    if message:
        logger.info(f"\n{separator}\n{message}\n{separator}")
    else:
        logger.info(f"\n{separator}")

def is_market_hours():
    """Check if current time is within market hours"""
    now = datetime.now().time()
    return MARKET_OPEN_TIME <= now <= TRADING_END_TIME

def is_fresh_sector_data_available():
    """Check if fresh sector data file exists for today's date"""
    global SECTOR_DATA_CHECKED_TODAY, SECTOR_PERFORMANCE_FILE
    
    # If we've already checked today, don't check again
    if SECTOR_DATA_CHECKED_TODAY:
        return False
    
    # Look for today's sector file
    today_file = f"sector_{datetime.now().strftime('%Y%m%d')}.csv"
    
    if os.path.exists(today_file):
        # Check when the file was created/modified
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(today_file))
        current_date = datetime.now().date()
        
        # If file was modified today
        if file_mod_time.date() == current_date:
            logger.info(f"Found fresh sector data for today: {today_file}")
            # Update global file path to today's file
            SECTOR_PERFORMANCE_FILE = today_file
            SECTOR_DATA_CHECKED_TODAY = True
            return True
    
    # Also check for generic sector.csv if it was modified today
    if os.path.exists("sector.csv"):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime("sector.csv"))
        current_date = datetime.now().date()
        
        if file_mod_time.date() == current_date:
            logger.info("Found fresh sector.csv file modified today")
            # Use the generic file
            SECTOR_PERFORMANCE_FILE = "sector.csv"
            SECTOR_DATA_CHECKED_TODAY = True
            return True
    
    logger.info("No fresh sector data found for today")
    return False

# =================================================================
# Yahoo Finance Functions
# =================================================================

def get_yahoo_current_price(symbol):
    """Get current market price from Yahoo Finance"""
    try:
        # Convert symbol to Yahoo Finance format if needed
        if symbol.endswith('.NS'):
            yf_symbol = symbol
        else:
            yf_symbol = symbol + '.NS'
        
        logger.info(f"Getting price for {symbol} from Yahoo Finance (using {yf_symbol})")
        
        # Create the ticker object
        ticker = yf.Ticker(yf_symbol)
        
        # Try to get current data
        info = ticker.info
        if info and 'currentPrice' in info:
            price = float(info['currentPrice'])
            logger.info(f"Got current price for {symbol}: {price}")
            return price
        
        # Fallback: Get recent data from history
        history = ticker.history(period="1d", interval="1m")
        if not history.empty:
            price = float(history['Close'].iloc[-1])
            logger.info(f"Got price from history for {symbol}: {price}")
            return price
        
        logger.warning(f"Could not get price for {symbol} from Yahoo Finance")
        return None
    except Exception as e:
        logger.error(f"Error getting Yahoo Finance price for {symbol}: {str(e)}")
        return None

def get_current_market_price(symbol):
    """Get the current market price for a symbol from Yahoo Finance"""
    return get_yahoo_current_price(symbol)

# =================================================================
# Web Scraping Functions
# =================================================================

def scrape_nuvama_sectors():
    """Scrape sector performance data from Nuvama Wealth"""
    url = "https://www.nuvamawealth.com/market/stock-market-index/#key-indices"
    
    logger.info("Setting up Chrome driver...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-cache")  # Disable browser cache
    chrome_options.add_argument("--incognito")  # Use incognito mode to avoid caching
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36")
    
    try:
        # Use ChromeDriverManager to handle driver installation
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        
        logger.info(f"Navigating to {url}")
        driver.get(url)
        
        # Wait for page to load
        logger.info("Waiting for page to load...")
        time.sleep(15)
        
        # Clear cache and cookies to ensure fresh data
        driver.delete_all_cookies()
        driver.execute_script("window.localStorage.clear();")
        driver.execute_script("window.sessionStorage.clear();")
        
        # Refresh the page to ensure we get fresh data
        driver.refresh()
        logger.info("Refreshed page to get latest data")
        time.sleep(10)
        
        # Click on SECTOR INDICES tab
        try:
            sector_tab = driver.find_element(By.XPATH, "//a[text()='SECTOR INDICES']")
            sector_tab.click()
            logger.info("Clicked on SECTOR INDICES tab")
            time.sleep(5)
        except Exception as e1:
            logger.warning(f"Could not click on SECTOR INDICES tab: {e1}")
            try:
                sector_tab = driver.find_element(By.CSS_SELECTOR, ".tab-links li:nth-child(2) a")
                sector_tab.click()
                logger.info("Clicked on second tab")
                time.sleep(5)
            except Exception as e2:
                logger.warning(f"Could not click on second tab: {e2}")
        
        # Take a screenshot for debugging
        driver.save_screenshot("nuvama_sector_tab.png")
        logger.info("Saved screenshot of sector tab")
        
        # Find the table with sector data
        tables = driver.find_elements(By.TAG_NAME, "table")
        logger.info(f"Found {len(tables)} tables on page")
        
        sector_data = []
        
        # Looking for the right table - it should have "Nifty IT", "Nifty FMCG", etc.
        for table_idx, table in enumerate(tables):
            logger.info(f"Checking table {table_idx+1}")
            table_html = table.get_attribute('outerHTML')
            
            # Check if this looks like the sector table
            if "Nifty IT" in table_html or "Nifty FMCG" in table_html:
                logger.info(f"Found likely sector table (table #{table_idx+1})")
                rows = table.find_elements(By.TAG_NAME, "tr")
                
                # Skip header row
                for row in rows[1:]:
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        
                        if len(cells) >= 3:  # We need at least index name and % change cells
                            sector_name = cells[0].text.strip()
                            
                            # Look specifically for % change column
                            # Based on the image, we need to find the cell that contains percentages in parentheses
                            percent_change_cell = None
                            percent_change_value = None
                            
                            # Check each cell for percentage values in parentheses: (x.xx%)
                            for cell in cells:
                                cell_text = cell.text.strip()
                                # Look for pattern like (0.59%), (-1.26%), etc.
                                if '(' in cell_text and ')' in cell_text and '%' in cell_text:
                                    percent_change_cell = cell
                                    # Extract just the percentage value
                                    match = re.search(r'\(([-+]?\d+\.\d+)%\)', cell_text)
                                    if match:
                                        percent_change_value = float(match.group(1))
                                        logger.info(f"Found percent change: {percent_change_value}% in '{cell_text}'")
                                        break
                            
                            if percent_change_value is None:
                                logger.warning(f"Could not find percent change for {sector_name}")
                                continue
                                
                            # Clean up sector name (remove "Nifty " prefix if present)
                            clean_sector = sector_name.replace("Nifty ", "")
                            
                            # Determine if positive
                            is_positive = percent_change_value >= 0
                            
                            sector_data.append({
                                'sector': clean_sector,
                                'sector_percent_change': percent_change_value,
                                'is_positive': is_positive
                            })
                            
                            logger.info(f"Added sector: {clean_sector}, Change: {percent_change_value}%")
                    except Exception as e:
                        logger.error(f"Error processing row: {str(e)}")
                
                # We found and processed the sector table, no need to check other tables
                break
        
        # Close browser
        driver.quit()
        
        if not sector_data:
            logger.error("No sector data found in the table")
            return None
            
        # Create DataFrame
        df = pd.DataFrame(sector_data)
        
        # Add timestamp
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        df['timestamp'] = current_time
        
        # Add rank columns
        df = add_sector_rankings(df)
        
        return df
        
    except Exception as e:
        logger.error(f"Error during scraping: {str(e)}")
        logger.error(traceback.format_exc())
        if 'driver' in locals():
            try:
                driver.quit()
            except:
                pass
        return None

def add_sector_rankings(df):
    """Add ranking information to the sector DataFrame"""
    try:
        # Sort by performance for ranking
        df = df.sort_values('sector_percent_change', ascending=False)
        
        # Add numeric rank (1 = best performing)
        df['rank'] = range(1, len(df) + 1)
        
        # Add sector ranking category
        conditions = [
            (df['rank'] <= TOP_SECTORS_COUNT),                         # Top N sectors
            (df['rank'] > len(df) - BOTTOM_SECTORS_COUNT)              # Bottom N sectors
        ]
        
        choices = [
            'TOP',                                                     # Top N label
            'BOTTOM'                                                   # Bottom N label
        ]
        
        df['ranking_category'] = 'MIDDLE'                              # Default value
        # Use np.select instead of pd.np.select
        df['ranking_category'] = np.select(conditions, choices, default='MIDDLE')
        
        # Print ranking summary
        logger.info("Sector rankings:")
        for _, row in df.iterrows():
            sign = "+" if row['is_positive'] else "-"
            value = abs(row['sector_percent_change'])
            logger.info(f"Rank {row['rank']}: {row['sector']} ({sign}{value:.2f}%) - {row['ranking_category']}")
        
        return df
    except Exception as e:
        logger.error(f"Error adding sector rankings: {str(e)}")
        logger.error(traceback.format_exc())
        return df

def run_sector_scraper():
    """Execute the scraper and save results to sector.csv"""
    global SECTOR_PERFORMANCE_FILE, SECTOR_DATA_CHECKED_TODAY
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f"Running Nuvama sector data scraper job at {current_time}")
    
    df = scrape_nuvama_sectors()
    
    if df is not None:
        try:
            # Save to today's dated CSV file
            today_file = f"sector_{datetime.now().strftime('%Y%m%d')}.csv"
            
            # Make sure we have write permission
            logger.info(f"Saving to file {today_file}...")
            df.to_csv(today_file, index=False)
            
            # Verify the file was created
            if os.path.exists(today_file):
                logger.info(f"Successfully saved sector data to {today_file}")
                file_size = os.path.getsize(today_file)
                logger.info(f"File size: {file_size} bytes")
            else:
                logger.error(f"Failed to create {today_file} - file not found after saving")
            
            # Also save to generic sector.csv for compatibility
            logger.info("Saving to sector.csv...")
            df.to_csv("sector.csv", index=False)
            
            # Verify the file was created
            if os.path.exists("sector.csv"):
                logger.info(f"Successfully saved sector data to sector.csv")
                file_size = os.path.getsize("sector.csv")
                logger.info(f"File size: {file_size} bytes")
            else:
                logger.error("Failed to create sector.csv - file not found after saving")
            
            # Set global variables since we've just generated fresh sector data
            SECTOR_PERFORMANCE_FILE = today_file
            SECTOR_DATA_CHECKED_TODAY = True
            
            # Print simplified output as a summary
            print(f"\nSUMMARY - NUVAMA SECTOR RANKINGS ({current_time}):")
            print("------------------------------")
            for _, row in df.iterrows():
                symbol = "+" if row['is_positive'] else "-"
                value = abs(row['sector_percent_change'])
                category = row['ranking_category'] if 'ranking_category' in df.columns else 'N/A'
                print(f"Rank {row['rank'] if 'rank' in df.columns else 'N/A'}: {row['sector']} ({symbol}{value:.2f}%) - {category}")
            
            return df
        except Exception as e:
            logger.error(f"Error saving sector data to file: {str(e)}")
            logger.error(traceback.format_exc())
            return df
    else:
        logger.error("Failed to scrape sector data")
        return None

# =================================================================
# Configuration and Setup Functions
# =================================================================

def load_config():
    """Load trading configuration from JSON file"""
    try:
        logger.info(f"Loading trading configuration from {TRADING_CONFIG_FILE}")
        if os.path.exists(TRADING_CONFIG_FILE):
            with open(TRADING_CONFIG_FILE, 'r') as f:
                config = json.load(f)
                
                # Validate required fields
                required_fields = ['client_id', 'access_token', 'place_new_orders']
                missing_fields = [field for field in required_fields if field not in config]
                
                if missing_fields:
                    logger.error(f"Trading config missing required fields: {missing_fields}")
                    return None
                
                logger.info(f"Configuration loaded successfully")
                
                # Check for active tickers
                tickers = config.get('tickers', [])
                active_tickers = [t for t in tickers if t.get('active', False)]
                
                if len(active_tickers) == 0:
                    logger.warning(f"No active tickers found in configuration! All {len(tickers)} tickers are inactive.")
                    logger.warning("IMPORTANT: Set 'active': true for tickers you want to trade.")
                else:
                    logger.info(f"Found {len(active_tickers)} active tickers out of {len(tickers)} total")
                
                return config
        else:
            logger.error(f"Config file {TRADING_CONFIG_FILE} not found")
            return None
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def load_sector_mapping():
    """Load sector mapping from JSON file"""
    try:
        logger.info(f"Loading sector mapping from {SECTOR_MAPPING_FILE}")
        with open(SECTOR_MAPPING_FILE, 'r') as f:
            mapping = json.load(f)
            logger.info(f"Sector mapping loaded successfully with {len(mapping)} tickers")
            
            # Get unique sectors for reference
            unique_sectors = set(mapping.values())
            logger.info(f"Found {len(unique_sectors)} unique sectors")
            
            return mapping
    except Exception as e:
        logger.error(f"Error loading sector mapping: {str(e)}")
        logger.error(traceback.format_exc())
        # Return empty dict if file not found or other error
        return {}

def load_security_ids():
    """Load security IDs mapping from Excel file with correct column mapping"""
    try:
        logger.info(f"Loading security IDs from {SECURITY_IDS_FILE}")
        
        if not os.path.exists(SECURITY_IDS_FILE):
            logger.error(f"Security IDs file {SECURITY_IDS_FILE} not found")
            return {}
        
        # Read Excel file using pandas
        df = pd.read_excel(SECURITY_IDS_FILE)
        logger.info(f"Successfully read Excel file with {len(df)} rows")
        
        # Log the column names to verify format
        logger.info(f"Excel columns: {df.columns.tolist()}")
        
        # Use the specific column names from the Excel file
        symbol_col = 'SEM_TRADING_SYMBOL'
        id_col = 'SEM_SMST_SECURITY_ID'
        
        if symbol_col not in df.columns:
            logger.error(f"Symbol column '{symbol_col}' not found in Excel file.")
            return {}
            
        if id_col not in df.columns:
            logger.error(f"Security ID column '{id_col}' not found in Excel file.")
            return {}
            
        logger.info(f"Using columns: Symbol='{symbol_col}', ID='{id_col}'")
        
        # Create dictionary from DataFrame
        security_ids = {}
        for _, row in df.iterrows():
            # Skip rows with NaN values
            if pd.isna(row[symbol_col]) or pd.isna(row[id_col]):
                continue
                
            symbol = str(row[symbol_col]).strip()
            # Convert to int first to remove decimals, then to string
            try:
                security_id = str(int(row[id_col])).strip()
            except:
                # If conversion fails, use as is
                security_id = str(row[id_col]).strip()
            
            # Skip rows with empty symbols or IDs
            if not symbol or symbol == 'nan' or not security_id or security_id == 'nan':
                continue
                
            # Add to mapping - include both formats (with and without .NS)
            security_ids[symbol] = security_id  # Base symbol
            security_ids[f"{symbol}.NS"] = security_id  # With .NS suffix
                
        logger.info(f"Security IDs mapping created with {len(security_ids)} entries")
        
        # Check for key stocks
        test_symbols = ["SYNGENE", "SYNGENE.NS", "GRANULES", "GRANULES.NS", "ZEEL", "ZEEL.NS", "SBILIFE", "SBILIFE.NS", "RBLBANK", "RBLBANK.NS"]
        logger.info("Checking for critical symbols:")
        for sym in test_symbols:
            if sym in security_ids:
                logger.info(f"Found ID for {sym}: {security_ids[sym]}")
            else:
                logger.warning(f"No ID found for {sym}")
        
        return security_ids
        
    except Exception as e:
        logger.error(f"Error loading security IDs from Excel: {str(e)}")
        logger.error(traceback.format_exc())
        return {}

def validate_security_ids(security_ids, config):
    """Validate that all configured tickers have security IDs"""
    log_separator("VALIDATING SECURITY IDS")
    
    if not config or 'tickers' not in config:
        logger.warning("No tickers found in configuration")
        return
        
    tickers = [t['symbol'] for t in config['tickers'] if t.get('active', False)]
    
    if not tickers:
        logger.warning("No active tickers to validate. Make sure to set 'active': true for tickers you want to trade.")
        return
        
    logger.info(f"Found {len(tickers)} active tickers to validate")
    
    missing_ids = []
    found_ids = []
    
    for symbol in tickers:
        # Try different variations
        found = False
        variations = [
            symbol,
            symbol.replace('.NS', ''),
            symbol.replace('.NS', '') + '.NS'
        ]
        
        for var in variations:
            if var in security_ids:
                logger.info(f"Found security ID for {symbol} via {var}: {security_ids[var]}")
                found = True
                found_ids.append((symbol, var, security_ids[var]))
                break
                
        if not found:
            missing_ids.append(symbol)
            logger.error(f"No security ID found for {symbol}")
    
    if missing_ids:
        logger.error(f"Missing security IDs for {len(missing_ids)} tickers: {missing_ids}")
    else:
        logger.info("All active tickers have security IDs")
        
    # Return the validation results
    return {
        "missing": missing_ids,
        "found": found_ids
    }

def load_positions():
    """Load current trading positions from JSON file"""
    try:
        if os.path.exists(POSITIONS_FILE):
            with open(POSITIONS_FILE, 'r') as f:
                positions = json.load(f)
                logger.info(f"Loaded {len(positions)} existing positions")
                
                # Count positions by status
                open_positions = [p for p in positions if p.get('status') == 'OPEN']
                closed_positions = [p for p in positions if p.get('status') == 'CLOSED']
                logger.info(f"Positions: {len(open_positions)} open, {len(closed_positions)} closed")
                
                # Log open positions for reference
                if open_positions:
                    logger.info("Open positions:")
                    for p in open_positions:
                        logger.info(f"  {p.get('transaction_type')} {p.get('symbol')} (Order ID: {p.get('order_id')})")
                
                return positions
        else:
            logger.info(f"No existing positions file found, starting fresh")
            return []
    except Exception as e:
        logger.error(f"Error loading positions: {str(e)}")
        logger.error(traceback.format_exc())
        return []

def save_positions(positions):
    """Save current trading positions to JSON file"""
    try:
        with open(POSITIONS_FILE, 'w') as f:
            json.dump(positions, f, indent=4)
        logger.info(f"Saved {len(positions)} positions to {POSITIONS_FILE}")
    except Exception as e:
        logger.error(f"Error saving positions: {str(e)}")
        logger.error(traceback.format_exc())

# =================================================================
# Dhan API Functions
# =================================================================

def initialize_dhan_client(config):
    """Initialize the Dhan API client"""
    try:
        # Direct initialization with client_id and access_token
        logger.info(f"Initializing Dhan client with client_id: {config['client_id']}")
        dhan = dhanhq(config['client_id'], config['access_token'])
        logger.info("Dhan API client initialized successfully")
        
        # Test the connection
        try:
            orders = dhan.get_order_list()
            if isinstance(orders, dict) and 'status' in orders and orders['status'] == 'success':
                logger.info("Dhan API connection test successful")
            else:
                logger.info(f"Connection test returned: {orders}")
        except Exception as e:
            logger.warning(f"Connection test error: {str(e)}")
        
        return dhan
    except Exception as e:
        logger.error(f"Error initializing Dhan client: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def get_security_id(symbol, security_ids_mapping):
    """Get security ID for a ticker symbol with enhanced diagnostics"""
    try:
        logger.info(f"SECURITY ID LOOKUP: Searching for {symbol}")
        
        # Create standardized versions of the symbol
        clean_symbol = symbol.replace('.NS', '')
        ns_symbol = clean_symbol + '.NS'
        
        # Try direct matches first
        logger.info(f"Trying exact match for '{symbol}'")
        if symbol in security_ids_mapping:
            security_id = security_ids_mapping[symbol]
            logger.info(f"FOUND EXACT MATCH: ID {security_id} for {symbol}")
            return security_id
            
        logger.info(f"Trying with .NS: '{ns_symbol}'")
        if ns_symbol in security_ids_mapping:
            security_id = security_ids_mapping[ns_symbol]
            logger.info(f"FOUND WITH .NS: ID {security_id} for {symbol} via {ns_symbol}")
            return security_id
            
        logger.info(f"Trying without .NS: '{clean_symbol}'")
        if clean_symbol in security_ids_mapping:
            security_id = security_ids_mapping[clean_symbol]
            logger.info(f"FOUND WITHOUT .NS: ID {security_id} for {symbol} via {clean_symbol}")
            return security_id
        
        # Try case-insensitive matching as last resort
        symbol_lower = clean_symbol.lower()
        for key, value in security_ids_mapping.items():
            if key.lower() == symbol_lower or key.lower().replace('.ns', '') == symbol_lower:
                logger.info(f"FOUND via case-insensitive match: ID {value} for {symbol} via {key}")
                return value
        
        logger.error(f"SECURITY ID NOT FOUND for {symbol}")
        return None
    except Exception as e:
        logger.error(f"Error getting security ID for {symbol}: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def get_order_execution_price(dhan, order_id):
    """Get the execution price of an order"""
    try:
        logger.info(f"Getting execution price for order ID: {order_id}")
        
        # Get order details
        order_details = dhan.get_order_by_id(order_id)
        
        if isinstance(order_details, dict):
            # Check if order is executed
            if 'status' in order_details and order_details['status'] in ['COMPLETED', 'EXECUTED']:
                # Try to extract execution price
                if 'average_price' in order_details:
                    price = float(order_details['average_price'])
                    logger.info(f"Order {order_id} executed at price: {price}")
                    return price
                elif 'price' in order_details:
                    price = float(order_details['price'])
                    logger.info(f"Order {order_id} executed at price: {price}")
                    return price
            else:
                logger.warning(f"Order {order_id} not executed yet. Status: {order_details.get('status', 'unknown')}")
        else:
            logger.warning(f"Could not get details for order {order_id}")
        
        return None
    except Exception as e:
        logger.error(f"Error getting execution price for order {order_id}: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def place_order(dhan, symbol, transaction_type, quantity, price=None, security_id=None):
    """Place an order through Dhan API with enhanced diagnostics"""
    try:
        logger.info(f"ORDER ATTEMPT: {transaction_type} {quantity} shares of {symbol}")
        
        if not security_id:
            logger.error(f"ORDER FAILED: No security ID provided for {symbol}")
            return None, None
            
        logger.info(f"Using security ID: {security_id}")
        
        # Get the correct transaction type constant from dhan
        dhan_transaction_type = dhan.BUY if transaction_type == 'BUY' else dhan.SELL
        
        # Place order
        order_params = {
            'security_id': security_id,
            'exchange_segment': dhan.NSE,
            'transaction_type': dhan_transaction_type,
            'quantity': quantity,
            'order_type': dhan.LIMIT if price is not None and price > 0 else dhan.MARKET,
            'product_type': dhan.INTRA,  # Intraday order
            'price': price if price is not None and price > 0 else 0
        }
        
        # Convert to a string representation for logging
        params_str = ", ".join([f"{k}: {v}" for k, v in order_params.items()])
        logger.info(f"ORDER PARAMS: {params_str}")
        
        # Place the order
        response = dhan.place_order(**order_params)
        
        # Log response type and details
        logger.info(f"Response type: {type(response)}")
        
        if isinstance(response, dict):
            try:
                # Try to log the complete response as JSON
                response_str = json.dumps(response, indent=2)
                logger.info(f"COMPLETE ORDER RESPONSE:\n{response_str}")
            except:
                # Fallback if not JSON serializable
                logger.info(f"ORDER RESPONSE (non-serializable):")
                for key, value in response.items():
                    logger.info(f"  Response[{key}] = {value}")
        else:
            logger.info(f"Non-dict response: {response}")
        
        # Extract order ID if available
        order_id = None
        if isinstance(response, dict):
            # Try all possible paths for order ID
            if 'orderId' in response:
                order_id = response['orderId']
            elif 'order_id' in response:
                order_id = response['order_id']
            elif 'data' in response and isinstance(response['data'], dict):
                data = response['data']
                if 'orderId' in data:
                    order_id = data['orderId']
                elif 'order_id' in data:
                    order_id = data['order_id']
                
        if order_id:
            logger.info(f"SUCCESS: Got order ID {order_id} for {symbol}")
        else:
            logger.warning(f"WARNING: No order ID found in response for {symbol}")
            
            # Check if the response indicates success despite no order ID
            if isinstance(response, dict) and 'status' in response and response['status'] == 'success':
                logger.info(f"Response indicates success for {symbol} despite no order ID")
                order_id = f"unknown-{int(time.time())}"  # Generate a fallback ID
            else:
                logger.error(f"Order placement likely failed for {symbol}")
                return None, None
        
        return response, order_id
    except Exception as e:
        logger.error(f"ERROR placing order for {symbol}: {str(e)}")
        logger.error(traceback.format_exc())
        return None, None

def execute_order_with_retries(dhan, symbol, transaction_type, quantity, price, security_id, max_retries=3):
    """Place an order with retries and enhanced error handling"""
    logger.info(f"Executing {transaction_type} order for {quantity} shares of {symbol} with up to {max_retries} retries")
    
    retry_count = 0
    while retry_count <= max_retries:
        if retry_count > 0:
            logger.info(f"Retry {retry_count}/{max_retries} for {symbol}")
            time.sleep(5)  # Wait before retry
            
        # Attempt to place the order
        order_response, order_id = place_order(dhan, symbol, transaction_type, quantity, price, security_id)
        
        # Check if we got a valid response
        if order_response is not None and order_id is not None:
            logger.info(f"Order executed successfully for {symbol}, order ID: {order_id}")
            
            # Try to get the execution price
            execution_price = None
            
            # If it was a market order, try to get the current market price
            if price is None or price == 0:
                execution_price = get_current_market_price(symbol)
                if execution_price:
                    logger.info(f"Using current market price as execution price: {execution_price}")
                else:
                    logger.warning(f"Could not determine execution price for {symbol}")
            else:
                # For limit orders, use the limit price as execution price
                execution_price = price
                logger.info(f"Using limit price as execution price: {execution_price}")
            
            # Wait a bit and try to get the actual execution price from the order details
            if order_id and not order_id.startswith("unknown-"):
                logger.info(f"Waiting 2 seconds for order execution...")
                time.sleep(2)
                actual_price = get_order_execution_price(dhan, order_id)
                if actual_price:
                    execution_price = actual_price
                    logger.info(f"Updated with actual execution price: {execution_price}")
            
            return order_response, order_id, execution_price
            
        retry_count += 1
    
    logger.error(f"Order execution failed for {symbol} after {max_retries} retries")
    return None, None, None

# =================================================================
# Sector Analysis Functions
# =================================================================

def get_latest_sector_performance():
    """Read the latest sector performance data from sector.csv"""
    global SECTOR_PERFORMANCE_FILE  # Declare global variable
    
    log_separator("READING SECTOR PERFORMANCE DATA")
    try:
        logger.info(f"Reading sector performance data from {SECTOR_PERFORMANCE_FILE}")
        
        if not os.path.exists(SECTOR_PERFORMANCE_FILE):
            # Try the generic file if dated file not found
            if os.path.exists("sector.csv"):
                logger.info(f"Using generic sector.csv instead of dated file")
                SECTOR_PERFORMANCE_FILE = "sector.csv"
            else:
                logger.warning(f"Sector performance file not found")
                log_separator("SECTOR DATA READ FAILED")
                return None
            
        # Get file modification time
        mod_time = datetime.fromtimestamp(os.path.getmtime(SECTOR_PERFORMANCE_FILE))
        logger.info(f"File last modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
        # Read the sector performance file
        df = pd.read_csv(SECTOR_PERFORMANCE_FILE)
        
        if df.empty:
            logger.warning("Sector performance file is empty")
            log_separator("SECTOR DATA READ FAILED")
            return None
            
        # Check if required columns exist
        required_columns = ['sector', 'sector_percent_change', 'is_positive']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.warning(f"Required columns missing in sector performance file: {missing_columns}")
            logger.info(f"Available columns: {df.columns.tolist()}")
            log_separator("SECTOR DATA READ FAILED")
            return None
        
        # Ensure we have ranking data - add it if not present
        if 'rank' not in df.columns or 'ranking_category' not in df.columns:
            logger.info("Adding sector rankings to data")
            df = add_sector_rankings(df)
        
        # Get the latest timestamp if available
        latest_time = None
        if 'timestamp' in df.columns:
            latest_time = df['timestamp'].max() if not df['timestamp'].empty else "unknown"
            logger.info(f"Latest timestamp in data: {latest_time}")
        
        # Log sector performance summary
        logger.info(f"Loaded data for {len(df)} sectors")
        
        # Log detailed sector performance for debugging
        logger.info("Sector performance details:")
        for _, row in df.iterrows():
            sector = row['sector']
            is_positive = bool(row['is_positive'])
            percent_change = float(row['sector_percent_change'])
            rank = row['rank'] if 'rank' in df.columns else 'N/A'
            category = row['ranking_category'] if 'ranking_category' in df.columns else 'N/A'
            
            logger.info(f"  Rank {rank}: {sector} - {'POSITIVE' if is_positive else 'NEGATIVE'} "
                        f"({percent_change:.2f}%) - {category}")
        
        log_separator("SECTOR DATA READ COMPLETE")
        return df
    
    except Exception as e:
        logger.error(f"Error reading sector performance data: {str(e)}")
        logger.error(traceback.format_exc())
        log_separator("SECTOR DATA READ FAILED")
        return None

def get_sector_for_ticker(symbol, sector_mapping):
    """Get sector for a ticker with robust handling of symbol variations"""
    # Try the exact symbol
    if symbol in sector_mapping:
        return sector_mapping[symbol]
        
    # Try without .NS suffix
    if symbol.endswith('.NS'):
        clean_symbol = symbol[:-3]
        if clean_symbol in sector_mapping:
            return sector_mapping[clean_symbol]
    
    # Try with .NS suffix
    if not symbol.endswith('.NS'):
        ns_symbol = symbol + '.NS'
        if ns_symbol in sector_mapping:
            return sector_mapping[ns_symbol]
    
    # Case-insensitive matching as last resort
    symbol_lower = symbol.lower().replace('.ns', '')
    for key, value in sector_mapping.items():
        if key.lower().replace('.ns', '') == symbol_lower:
            return value
    
    # Not found
    return None

def process_sector_data(dhan, sector_df, config, sector_mapping, positions, security_ids_mapping):
    """
    Process sector performance data to make trading decisions
    
    Args:
        dhan: Initialized Dhan API client
        sector_df: DataFrame with sector performance data
        config: Trading configuration
        sector_mapping: Mapping of tickers to sectors
        positions: Current positions
        security_ids_mapping: Mapping of symbols to security IDs
        
    Returns:
        Updated positions
    """
    global INITIAL_TRADES_EXECUTED
    
    log_separator("PROCESSING SECTOR DATA")
    if sector_df is None or sector_df.empty:
        logger.warning("No sector data available for processing")
        log_separator("SECTOR PROCESSING SKIPPED")
        return positions
    
    try:
        # Process existing positions first - this happens regardless of whether 
        # initial trades have been executed or not
        logger.info("Processing existing positions for potential exits...")
        updated_positions = process_existing_positions(dhan, positions, sector_df, security_ids_mapping)
        
        # Only place new trades if initial trades have not been executed yet
        # and we have fresh sector data for today
        if not INITIAL_TRADES_EXECUTED and config.get('place_new_orders', False):
            # Check if there are any active tickers in the config
            active_tickers = [t for t in config.get('tickers', []) if t.get('active', False)]
            
            if not active_tickers:
                logger.warning("No active tickers found in configuration! Set 'active': true for tickers you want to trade.")
                logger.warning("Skipping new trades due to no active tickers.")
            else:
                logger.info("First run of the day - looking for sector-based trading opportunities...")
                updated_positions = find_new_trading_opportunities(
                    dhan, updated_positions, sector_df, sector_mapping, config, security_ids_mapping
                )
            
            # Mark that we've done the initial trades for today
            INITIAL_TRADES_EXECUTED = True
            logger.info("Initial trades have been executed - no more new trades will be placed today")
        else:
            if INITIAL_TRADES_EXECUTED:
                logger.info("Initial trades already executed today - skipping new trade opportunities")
            else:
                logger.info("Skipping new order opportunities (place_new_orders=False)")
        
        log_separator("SECTOR PROCESSING COMPLETE")
        return updated_positions
        
    except Exception as e:
        logger.error(f"Error processing sector data: {str(e)}")
        logger.error(traceback.format_exc())
        log_separator("SECTOR PROCESSING FAILED")
        return positions

def process_existing_positions(dhan, positions, sector_df, security_ids_mapping):
    """
    Process existing positions to check if any need to be exited based on:
    1. Stop loss price levels (1% loss)
    2. Target price levels (1% profit)
    Prices are fetched from Yahoo Finance
    
    Args:
        dhan: Initialized Dhan API client
        positions: List of current positions
        sector_df: DataFrame with sector performance data (not used for exit decisions)
        security_ids_mapping: Mapping of symbols to security IDs
        
    Returns:
        Updated positions
    """
    log_separator("PROCESSING EXISTING POSITIONS")
    if not positions:
        logger.info("No existing positions to process")
        log_separator("POSITION PROCESSING COMPLETE")
        return positions
        
    logger.info(f"Processing {len(positions)} existing positions")
    
    try:
        updated_positions = []
        squared_off_count = 0
        
        for position in positions:
            try:
                # Skip positions that are already closed
                if position.get('status') == 'CLOSED':
                    logger.info(f"Skipping already closed position for {position.get('symbol')}")
                    updated_positions.append(position)
                    continue
                    
                ticker = position['symbol']
                sector = position['sector']
                position_type = position['transaction_type']  # 'BUY' or 'SELL'
                
                logger.info(f"Checking position: {position_type} {ticker} (Sector: {sector})")
                
                # Get security ID
                security_id = get_security_id(ticker, security_ids_mapping)
                if not security_id:
                    logger.error(f"Could not find security ID for {ticker}. Skipping position check.")
                    updated_positions.append(position)
                    continue
                
                # Initialize exit flags
                exit_position = False
                exit_reason = ""
                
                # Check for price-based exit conditions (stop loss and target)
                # Get current market price from Yahoo Finance
                current_price = get_current_market_price(ticker)
                
                if current_price:
                    logger.info(f"Current market price for {ticker}: {current_price}")
                    
                    # Check if we have an entry price
                    entry_price = position.get('entry_price')
                    if entry_price:
                        entry_price = float(entry_price)
                        
                        # Check for stop loss (override any custom value and use fixed 1%)
                        stop_loss_percent = STOP_LOSS_PERCENT
                        
                        if position_type == 'BUY':
                            # For BUY positions, stop loss is below entry price
                            stop_loss_price = entry_price * (1 - stop_loss_percent/100)
                            logger.info(f"Stop loss for {ticker} BUY position: {stop_loss_price} (Entry: {entry_price}, SL%: {stop_loss_percent}%)")
                            
                            if current_price <= stop_loss_price:
                                exit_position = True
                                exit_reason = f"Stop loss triggered at {current_price} (Stop: {stop_loss_price})"
                                logger.info(f"Stop loss triggered for {ticker} BUY position: Current: {current_price} <= Stop: {stop_loss_price}")
                        
                        elif position_type == 'SELL':
                            # For SELL positions, stop loss is above entry price
                            stop_loss_price = entry_price * (1 + stop_loss_percent/100)
                            logger.info(f"Stop loss for {ticker} SELL position: {stop_loss_price} (Entry: {entry_price}, SL%: {stop_loss_percent}%)")
                            
                            if current_price >= stop_loss_price:
                                exit_position = True
                                exit_reason = f"Stop loss triggered at {current_price} (Stop: {stop_loss_price})"
                                logger.info(f"Stop loss triggered for {ticker} SELL position: Current: {current_price} >= Stop: {stop_loss_price}")
                        
                        # Check for target (override any custom value and use fixed 1%)
                        if not exit_position:
                            target_percent = PROFIT_TARGET_PERCENT
                            
                            if position_type == 'BUY':
                                # For BUY positions, target is above entry price
                                target_price = entry_price * (1 + target_percent/100)
                                logger.info(f"Target for {ticker} BUY position: {target_price} (Entry: {entry_price}, Target%: {target_percent}%)")
                                
                                if current_price >= target_price:
                                    exit_position = True
                                    exit_reason = f"Target reached at {current_price} (Target: {target_price})"
                                    logger.info(f"Target reached for {ticker} BUY position: Current: {current_price} >= Target: {target_price}")
                            
                            elif position_type == 'SELL':
                                # For SELL positions, target is below entry price
                                target_price = entry_price * (1 - target_percent/100)
                                logger.info(f"Target for {ticker} SELL position: {target_price} (Entry: {entry_price}, Target%: {target_percent}%)")
                                
                                if current_price <= target_price:
                                    exit_position = True
                                    exit_reason = f"Target reached at {current_price} (Target: {target_price})"
                                    logger.info(f"Target reached for {ticker} SELL position: Current: {current_price} <= Target: {target_price}")
                    else:
                        logger.warning(f"No entry price available for {ticker}, cannot check stop loss/target")
                        
                        # Try to get and save the entry price for this position
                        if 'order_id' in position:
                            order_id = position['order_id']
                            if not order_id.startswith("unknown-"):
                                entry_price = get_order_execution_price(dhan, order_id)
                                if entry_price:
                                    logger.info(f"Retrieved entry price for {ticker}: {entry_price}")
                                    position['entry_price'] = entry_price
                                    
                                    # Also get current market price to save for future reference
                                    position['last_price'] = current_price
                else:
                    logger.warning(f"Could not get current market price for {ticker}")
                
                # If we need to exit the position
                if exit_position:
                    # Square off the position
                    opposite_type = 'SELL' if position_type == 'BUY' else 'BUY'
                    quantity = position['quantity']
                    
                    logger.info(f"Placing {opposite_type} order to exit position for {ticker}: {exit_reason}")
                    
                    # Place the exit order with retries
                    exit_order, exit_order_id, exit_price = execute_order_with_retries(
                        dhan,
                        ticker,
                        opposite_type,
                        quantity,
                        None,  # Market order
                        security_id,
                        max_retries=3
                    )
                    
                    if exit_order:
                        # Update position status
                        position['exit_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        position['exit_reason'] = exit_reason
                        position['exit_order_id'] = exit_order_id or 'unknown'
                        position['status'] = 'CLOSED'
                        
                        # Save exit price if available
                        if exit_price:
                            position['exit_price'] = exit_price
                            
                            # Calculate P&L if both entry and exit prices are available
                            if 'entry_price' in position:
                                entry_price = float(position['entry_price'])
                                pnl = 0
                                
                                if position_type == 'BUY':
                                    # For BUY, profit = sell_price - buy_price
                                    pnl = (exit_price - entry_price) * position['quantity']
                                else:
                                    # For SELL, profit = buy_price - sell_price
                                    pnl = (entry_price - exit_price) * position['quantity']
                                    
                                position['pnl'] = pnl
                                logger.info(f"P&L for {ticker}: {pnl}")
                        
                        logger.info(f"Exited {position_type} position for {ticker}: {exit_reason}")
                        squared_off_count += 1
                    else:
                        logger.warning(f"Failed to place exit order for {ticker}")
                else:
                    # If we didn't exit but got a current price, update the position with it
                    if current_price:
                        position['last_price'] = current_price
                        logger.info(f"Updated last price for {ticker}: {current_price}")
                
                updated_positions.append(position)
                
            except Exception as e:
                logger.error(f"Error processing position for {position.get('symbol', 'unknown')}: {str(e)}")
                logger.error(traceback.format_exc())
                # Add the position anyway to avoid losing it
                updated_positions.append(position)
        
        if squared_off_count > 0:
            logger.info(f"Squared off {squared_off_count} positions")
        else:
            logger.info("No positions needed to be exited")
        
        log_separator("POSITION PROCESSING COMPLETE")
        return updated_positions
        
    except Exception as e:
        logger.error(f"Error processing existing positions: {str(e)}")
        logger.error(traceback.format_exc())
        log_separator("POSITION PROCESSING FAILED")
        return positions

def find_new_trading_opportunities(dhan, positions, sector_df, sector_mapping, config, security_ids_mapping):
    """
    Find new trading opportunities based on sector rankings
    
    Args:
        dhan: Initialized Dhan API client  
        positions: List of current positions
        sector_df: DataFrame with sector performance and ranking data
        sector_mapping: Mapping of tickers to sectors
        config: Trading configuration
        security_ids_mapping: Mapping of symbols to security IDs
        
    Returns:
        Updated positions
    """
    log_separator("FINDING NEW TRADING OPPORTUNITIES")
    
    try:
        # Get the tickers from the config
        tickers_config = config.get('tickers', [])
        if not tickers_config:
            logger.warning("No tickers found in configuration")
            log_separator("NEW OPPORTUNITIES SKIPPED")
            return positions
        
        # Get all active tickers (where active is true)
        active_tickers = [t for t in tickers_config if t.get('active', False)]
        if not active_tickers:
            logger.warning("No active tickers found. Set 'active': true for tickers you want to trade.")
            log_separator("NEW OPPORTUNITIES SKIPPED")
            return positions
            
        logger.info(f"Found {len(active_tickers)} active tickers out of {len(tickers_config)} total")
        
        # Check if we have the required ranking columns
        required_columns = ['sector', 'ranking_category', 'rank', 'is_positive']
        missing_columns = [col for col in required_columns if col not in sector_df.columns]
        
        if missing_columns:
            logger.warning(f"Sector data missing required ranking columns: {missing_columns}")
            logger.warning("Adding ranking data to sectors...")
            sector_df = add_sector_rankings(sector_df)
        
        # Create a mapping of sectors to their performance and ranking
        sector_data = {}
        for _, row in sector_df.iterrows():
            sector = row['sector']
            sector_data[sector] = {
                'is_positive': bool(row['is_positive']),
                'percent_change': float(row['sector_percent_change']),
                'rank': int(row['rank']),
                'category': row['ranking_category']
            }
        
        logger.info(f"Processed sector data for {len(sector_data)} sectors")
        
        # Debug counters for each processing stage
        tickers_considered = 0
        tickers_with_sector_data = 0
        tickers_matching_strategy = 0
        tickers_with_security_id = 0
        tickers_ordered = 0
        
        # Process tickers in original order
        ordered_tickers = active_tickers
        logger.info(f"Processing tickers in order: {[t['symbol'] for t in ordered_tickers]}")
        
        # Check if we already have positions in these tickers
        existing_position_tickers = [p['symbol'] for p in positions if p.get('status') == 'OPEN']
        logger.info(f"Already have open positions for: {existing_position_tickers}")
        
        # Log all sector rankings for reference
        logger.info("Current sector rankings:")
        for sector, data in sector_data.items():
            is_positive = data['is_positive']
            percent_change = data['percent_change']
            rank = data['rank']
            category = data['category']
            logger.info(f"  Rank {rank}: {sector} - {'POSITIVE' if is_positive else 'NEGATIVE'} "
                        f"({percent_change:.2f}%) - {category}")
        
        new_positions_count = 0
        skipped_positions_count = 0
        error_positions_count = 0
        
        # Process each active ticker from the config
        for ticker_config in ordered_tickers:
            try:
                tickers_considered += 1
                symbol = ticker_config['symbol']
                
                logger.info(f"Processing ticker {tickers_considered}: {symbol}")
                
                # Skip if we already have an open position for this ticker
                if symbol in existing_position_tickers:
                    logger.info(f"Skipping {symbol} - already have an open position")
                    skipped_positions_count += 1
                    continue
                
                # Get the sector for this ticker
                sector = get_sector_for_ticker(symbol, sector_mapping)
                    
                if not sector:
                    logger.warning(f"Could not find sector for {symbol} in sector mapping")
                    skipped_positions_count += 1
                    continue
                    
                tickers_with_sector_data += 1
                logger.info(f"Found sector {sector} for {symbol}")
                    
                # Check if we have data for this sector
                if sector not in sector_data:
                    logger.warning(f"No data for sector {sector}")
                    skipped_positions_count += 1
                    continue
                    
                # Get the sector data
                s_data = sector_data[sector]
                is_positive = s_data['is_positive']
                percent_change = s_data['percent_change']
                rank = s_data['rank']
                category = s_data['category']
                
                logger.info(f"Evaluating {symbol} in sector {sector} - Rank {rank} ({category})")
                logger.info(f"  Performance: {'+' if is_positive else '-'}{abs(percent_change):.2f}%")
                
                # Get ticker configuration
                transaction_type = ticker_config['transaction_type']
                quantity = ticker_config['quantity']
                # Override any custom values with fixed 1%
                stop_loss_percent = STOP_LOSS_PERCENT
                target_percent = PROFIT_TARGET_PERCENT
                entry_price = ticker_config.get('entry_price', '')
                
                # Determine if we should trade based on sector ranking
                should_trade = False
                trade_reason = ""
                
                if transaction_type == 'BUY' and category == 'TOP' and is_positive:
                    # Only buy if sector is in the top 3 AND is positive
                    should_trade = True
                    trade_reason = f"TOP {TOP_SECTORS_COUNT} sector (Rank {rank}): {percent_change:.2f}%"
                    logger.info(f"Should BUY {symbol} - sector {sector} is in TOP {TOP_SECTORS_COUNT} (Rank {rank})")
                    
                elif transaction_type == 'SELL' and category == 'BOTTOM' and not is_positive:
                    # Only sell if sector is in the bottom 3
                    should_trade = True
                    trade_reason = f"BOTTOM {BOTTOM_SECTORS_COUNT} sector (Rank {rank}): {percent_change:.2f}%"
                    logger.info(f"Should SELL {symbol} - sector {sector} is in BOTTOM {BOTTOM_SECTORS_COUNT} (Rank {rank})")
                else:
                    logger.info(f"Not trading {symbol} - sector ranking doesn't match strategy")
                    logger.info(f"  Transaction type: {transaction_type}")
                    logger.info(f"  Sector category: {category}")
                    logger.info(f"  Sector is_positive: {is_positive}")
                    skipped_positions_count += 1
                
                if should_trade:
                    tickers_matching_strategy += 1
                    
                    # Get the security ID
                    security_id = get_security_id(symbol, security_ids_mapping)
                    
                    if not security_id:
                        logger.error(f"Could not find security ID for {symbol}. Skipping.")
                        skipped_positions_count += 1
                        continue
                        
                    tickers_with_security_id += 1
                    
                    # Place the order (market order if entry_price is empty)
                    price = None if entry_price == '' else float(entry_price)
                    
                    # Log trade decision
                    logger.info(f"Placing {transaction_type} order for {quantity} shares of {symbol}: {trade_reason}")
                    
                    # Place order using Dhan client with retries
                    order, order_id, execution_price = execute_order_with_retries(
                        dhan,
                        symbol,
                        transaction_type,
                        quantity,
                        price,
                        security_id,
                        max_retries=3
                    )
                    
                    if order:
                        tickers_ordered += 1
                        
                        # Create new position record
                        new_position = {
                            'symbol': symbol,
                            'sector': sector,
                            'transaction_type': transaction_type,
                            'quantity': quantity,
                            'entry_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'entry_reason': trade_reason,
                            'order_id': order_id or f"unknown-{int(time.time())}",
                            'stop_loss_percent': stop_loss_percent,
                            'target_percent': target_percent,
                            'status': 'OPEN'
                        }
                        
                        # Add execution price if available
                        if execution_price:
                            new_position['entry_price'] = execution_price
                        
                        # If we specified a price in the order, use that as the entry price
                        if price is not None:
                            new_position['entry_price'] = price
                        
                        positions.append(new_position)
                        existing_position_tickers.append(symbol)
                        new_positions_count += 1
                        
                        logger.info(f"New {transaction_type} position for {symbol}: {trade_reason}")
                        
                        # Add a delay between orders to avoid rate limiting
                        if new_positions_count < len(ordered_tickers):  # Don't wait after last order
                            wait_time = 10  # 10 seconds between orders
                            logger.info(f"Waiting {wait_time} seconds before next order to avoid rate limiting...")
                            time.sleep(wait_time)
                    else:
                        logger.error(f"Failed to place order for {symbol}")
                        error_positions_count += 1
            
            except Exception as e:
                logger.error(f"Error processing ticker {ticker_config.get('symbol', 'unknown')}: {str(e)}")
                logger.error(traceback.format_exc())
                error_positions_count += 1
        
        # Log summary
        logger.info(f"Ticker processing summary:")
        logger.info(f"  Total tickers considered: {tickers_considered}")
        logger.info(f"  Tickers with sector data: {tickers_with_sector_data}")
        logger.info(f"  Tickers matching sector ranking strategy: {tickers_matching_strategy}")
        logger.info(f"  Tickers with security ID: {tickers_with_security_id}")
        logger.info(f"  Orders successfully placed: {tickers_ordered}")
        
        logger.info(f"New positions added: {new_positions_count}")
        logger.info(f"Positions skipped: {skipped_positions_count}")
        logger.info(f"Positions with errors: {error_positions_count}")
        
        if new_positions_count > 0:
            logger.info(f"Added {new_positions_count} new positions based on sector rankings")
        
        log_separator("NEW OPPORTUNITIES PROCESSING COMPLETE")
        return positions
    
    except Exception as e:
        logger.error(f"Error finding new trading opportunities: {str(e)}")
        logger.error(traceback.format_exc())
        log_separator("NEW OPPORTUNITIES PROCESSING FAILED")
        return positions

def summarize_current_positions(positions):
    """Print a summary of current positions"""
    log_separator("POSITIONS SUMMARY")
    try:
        # Count positions by type and status
        open_buy = sum(1 for p in positions if p.get('transaction_type') == 'BUY' and p.get('status') == 'OPEN')
        open_sell = sum(1 for p in positions if p.get('transaction_type') == 'SELL' and p.get('status') == 'OPEN')
        closed = sum(1 for p in positions if p.get('status') == 'CLOSED')
        
        logger.info("Current positions summary:")
        logger.info(f"  Open BUY positions: {open_buy}")
        logger.info(f"  Open SELL positions: {open_sell}")
        logger.info(f"  Closed positions: {closed}")
        logger.info(f"  Total positions: {len(positions)}")
        
        # Print open positions
        if open_buy + open_sell > 0:
            logger.info("Open positions:")
            open_positions = [p for p in positions if p.get('status') == 'OPEN']
            
            for position in open_positions:
                ticker = position['symbol']
                pos_type = position['transaction_type']
                sector = position['sector']
                entry_time = position['entry_time']
                order_id = position.get('order_id', 'unknown')
                
                position_details = [
                    f"Entry: {entry_time}",
                    f"Order ID: {order_id}"
                ]
                
                if 'entry_price' in position:
                    position_details.append(f"Entry Price: {position['entry_price']}")
                
                if 'last_price' in position:
                    position_details.append(f"Last Price: {position['last_price']}")
                
                if 'stop_loss_percent' in position:
                    position_details.append(f"SL%: {position['stop_loss_percent']}%")
                
                if 'target_percent' in position:
                    position_details.append(f"Target%: {position['target_percent']}%")
                
                position_str = f"  {pos_type} {ticker} (Sector: {sector}, {', '.join(position_details)})"
                logger.info(position_str)
                
        # Calculate total P&L for closed positions
        closed_positions = [p for p in positions if p.get('status') == 'CLOSED']
        if closed_positions:
            total_pnl = sum(float(p.get('pnl', 0)) for p in closed_positions)
            logger.info(f"Total P&L for closed positions: {total_pnl}")
            
            # List recent closed positions
            logger.info("Recently closed positions:")
            # Sort by exit_time, most recent first
            recent_closed = sorted(
                closed_positions, 
                key=lambda p: p.get('exit_time', ''), 
                reverse=True
            )[:5]  # Show last 5
            
            for position in recent_closed:
                ticker = position['symbol']
                pos_type = position['transaction_type']
                exit_reason = position.get('exit_reason', 'Unknown')
                exit_time = position.get('exit_time', 'Unknown')
                pnl = position.get('pnl', 'Unknown')
                
                logger.info(f"  {pos_type} {ticker} - Closed at {exit_time}, Reason: {exit_reason}, P&L: {pnl}")
        
        log_separator("POSITIONS SUMMARY COMPLETE")
    except Exception as e:
        logger.error(f"Error summarizing positions: {str(e)}")
        logger.error(traceback.format_exc())
        log_separator("POSITIONS SUMMARY FAILED")

# =================================================================
# Main Program Logic
# =================================================================

def main():
    """Main program execution"""
    global SECTOR_PERFORMANCE_FILE, SECTOR_DATA_CHECKED_TODAY, INITIAL_TRADES_EXECUTED
    
    try:
        log_separator("PROGRAM START")
        logger.info("==========================================")
        logger.info("Starting Dhan Sector-Based Trading Program")
        logger.info("==========================================")
        
        # Log current time
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"Current time: {current_time}")
        
        # Check today's dated file first
        today_file = f"sector_{datetime.now().strftime('%Y%m%d')}.csv"
        if os.path.exists(today_file):
            logger.info(f"Found today's sector file: {today_file}")
            SECTOR_PERFORMANCE_FILE = today_file
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(today_file))
            if file_mod_time.date() == datetime.now().date():
                logger.info("File was modified today - marking as fresh data")
                SECTOR_DATA_CHECKED_TODAY = True
        elif os.path.exists("sector.csv"):
            logger.info("Found generic sector.csv file")
            SECTOR_PERFORMANCE_FILE = "sector.csv"
            file_mod_time = datetime.fromtimestamp(os.path.getmtime("sector.csv"))
            if file_mod_time.date() == datetime.now().date():
                logger.info("File was modified today - marking as fresh data")
                SECTOR_DATA_CHECKED_TODAY = True
        else:
            logger.info("No sector data file found - running sector scraper to generate fresh data")
            run_sector_scraper()
        
        # Step 1: Load configuration
        logger.info("Step 1: Loading trading configuration...")
        config = load_config()
        
        if not config:
            logger.error("Failed to load trading configuration. Exiting.")
            log_separator("PROGRAM TERMINATED")
            return
        
        # Check if there are any active tickers in the config
        active_tickers = [t for t in config.get('tickers', []) if t.get('active', False)]
        if not active_tickers:
            logger.warning("WARNING: No active tickers found in configuration!")
            logger.warning("You need to set 'active': true for the tickers you want to trade.")
            logger.warning("The program will continue but no trades will be placed.")
            
        # Step 2: Initialize Dhan client
        logger.info("Step 2: Initializing Dhan API client...")
        dhan = initialize_dhan_client(config)
        
        if not dhan:
            logger.error("Failed to initialize Dhan API client. Exiting.")
            log_separator("PROGRAM TERMINATED")
            return
            
        # Step 3: Load sector mapping
        logger.info("Step 3: Loading sector mapping...")
        sector_mapping = load_sector_mapping()
        
        if not sector_mapping:
            logger.error("Failed to load sector mapping. Exiting.")
            log_separator("PROGRAM TERMINATED")
            return
            
        # Step 4: Load security IDs mapping from Excel
        logger.info("Step 4: Loading security IDs mapping from Excel...")
        security_ids_mapping = load_security_ids()
        
        if not security_ids_mapping:
            logger.error("Failed to load security IDs mapping. Cannot place orders without security IDs.")
            log_separator("PROGRAM TERMINATED")
            return
            
        # Step 4.5: Validate security IDs for all configured tickers
        logger.info("Step 4.5: Validating security IDs for active tickers...")
        validation_results = validate_security_ids(security_ids_mapping, config)
        
        if validation_results and validation_results.get("missing"):
            logger.warning(f"Some tickers are missing security IDs: {validation_results['missing']}")
            logger.warning("These tickers will be skipped during trading!")
        
        # Step 5: Load existing positions
        logger.info("Step 5: Loading existing positions...")
        positions = load_positions()
        
        # Step 6: Main trading loop (using separate intervals for sector and price checks)
        check_interval = config.get('check_interval_seconds', DEFAULT_CHECK_INTERVAL)
        logger.info(f"Step 6: Starting trading loop...")
        logger.info(f"  Sector check interval: {check_interval} seconds")
        logger.info(f"  Price check interval: {PRICE_CHECK_INTERVAL} seconds")
        
        # Reset daily flags at the start if needed
        INITIAL_TRADES_EXECUTED = False
        
        try:
            cycle_count = 0
            last_sector_check = 0
            last_price_check = 0
            
            while True:
                current_time = time.time()
                
                # Reset flags daily at market open
                now = datetime.now()
                if now.time() <= MARKET_OPEN_TIME and SECTOR_DATA_CHECKED_TODAY:
                    logger.info("New trading day - resetting flags for fresh sector data check")
                    INITIAL_TRADES_EXECUTED = False
                    SECTOR_DATA_CHECKED_TODAY = False
                
                # Check if it's time for a sector check (less frequent)
                if current_time - last_sector_check >= check_interval:
                    cycle_count += 1
                    log_separator(f"SECTOR CHECK CYCLE {cycle_count}")
                    current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    logger.info(f"Sector check cycle {cycle_count} started at {current_time_str}")
                    
                    # Check if we have fresh sector data today
                    fresh_sector_data = is_fresh_sector_data_available()
                    
                    if fresh_sector_data or SECTOR_DATA_CHECKED_TODAY:
                        # Get the latest sector performance data
                        sector_df = get_latest_sector_performance()
                        
                        if sector_df is not None:
                            # Process sector data for trading decisions
                            positions = process_sector_data(dhan, sector_df, config, sector_mapping, positions, security_ids_mapping)
                            
                            # Save updated positions
                            save_positions(positions)
                            
                            # Print summary of current positions
                            summarize_current_positions(positions)
                        else:
                            logger.warning("No sector data available, skipping this cycle")
                    else:
                        logger.info("No fresh sector data for today yet - waiting for sector.csv to be updated")
                    
                    logger.info(f"Sector check cycle {cycle_count} completed")
                    log_separator(f"SECTOR CYCLE {cycle_count} COMPLETE")
                    last_sector_check = current_time
                
                # Check if it's time for a price check (more frequent - every minute)
                if current_time - last_price_check >= PRICE_CHECK_INTERVAL:
                    log_separator("PRICE CHECK CYCLE")
                    logger.info("Checking prices for existing positions...")
                    
                    # Load current positions to ensure we have the latest
                    positions = load_positions()
                    
                    # Process existing positions for price-based exits only
                    positions = process_existing_positions(dhan, positions, None, security_ids_mapping)
                    
                    # Save updated positions
                    save_positions(positions)
                    
                    # Print summary of current positions
                    summarize_current_positions(positions)
                    
                    logger.info("Price check cycle completed")
                    log_separator("PRICE CHECK COMPLETE")
                    last_price_check = current_time
                
                # Wait a bit before next check
                time.sleep(1)  # Check every second to make timing more accurate
        
        except KeyboardInterrupt:
            logger.info("Trading program stopped by user")
            # Save positions before exiting
            save_positions(positions)
            log_separator("PROGRAM TERMINATED BY USER")
            
    except Exception as e:
        logger.error(f"Critical error in main program: {str(e)}")
        logger.error(traceback.format_exc())
        log_separator("PROGRAM TERMINATED DUE TO ERROR")

if __name__ == "__main__":
    try:
        # If the user passes "scrape" as command line argument, only run the scraper
        if len(sys.argv) > 1 and sys.argv[1].lower() == "scrape":
            logger.info("Running in scraper-only mode")
            run_sector_scraper()
            logger.info("Scraper execution completed")
            sys.exit(0)
        else:
            # Normal program execution
            main()
    except KeyboardInterrupt:
        logger.info("Program terminated by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception in main program: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)