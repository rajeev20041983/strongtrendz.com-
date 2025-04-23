
"""
Multi-Strategy Trading System
------------------------------------------
This program automates intraday trading using the Dhan API with two strategies:

1. Sector-Based Strategy:
   - Buy when a stock's sector is in the top 3 performing sectors
   - Sell when a stock's sector is in the bottom 3 performing sectors

2. Price Level Strategy:
   - Buy when a stock reaches a specific price level
   - Sell when either target price or stop loss is hit
"""

# Standard library imports
import time
import json
import os
import logging
import re
import ssl
import threading
from datetime import datetime
from urllib.request import Request, urlopen, build_opener, HTTPCookieProcessor, install_opener
from urllib.parse import urlencode
from urllib.error import URLError

# Third-party imports
import pandas as pd

# Dhan API imports
from dhanhq import dhanhq

# =================================================================
# Logging Setup
# =================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_log.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

# =================================================================
# Constants
# =================================================================

# Configuration files
CONFIG_FILE = "trading_config.json"
SECURITY_IDS_FILE = "security_ids.json"
SECTOR_MAPPING_FILE = "sector_mapping.json"
PRICE_LEVELS_FILE = "price_levels.json"
CREDENTIALS_FILE = "credentials.json"

# Tracking files
ORDER_TRACKER_FILE = "order_tracker.csv"
PRICE_LEVEL_TRADES_FILE = "price_level_trades.json"

# Other constants
NIFTY_SECURITY_ID = "1333"  # Security ID for Nifty 50
NIFTY_SWITCH_POINTS = 50    # Points change to switch positions

# =================================================================
# Configuration and Setup Functions
# =================================================================

def load_config():
    """Load trading configuration from JSON file"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            logger.info(f"Configuration loaded successfully from {CONFIG_FILE}")
            return config
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        raise
def get_sector_performance_without_auth():
    """
    Fetch sector performance data from intradayscreener.com without authentication
    Returns a dictionary with sector names and their performance data
    """
    try:
        # Create a context that doesn't verify SSL certificates (use with caution)
        context = ssl._create_unverified_context()
        
        # Set up browser-like headers for all requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://intradayscreener.com/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        # Try to directly access the sector performance page
        sector_url = "https://intradayscreener.com/sector-performance"
        logger.info("Attempting to access sector performance data without authentication")
        
        sector_req = Request(sector_url, headers=headers)
        with urlopen(sector_req, context=context) as response:
            html_content = response.read().decode('utf-8')
            
            # Check if we're redirected to login page
            if "/login" in response.geturl():
                logger.error("Access to sector performance requires login")
                return None
            
            # Process the HTML to extract sector performance data
            sector_data = parse_sector_performance_html(html_content)
            
            if sector_data:
                # Log the sector performance
                for sector, data in sector_data.items():
                    change_str = f"+{data['change_percent']:.2f}%" if data['is_positive'] else f"{data['change_percent']:.2f}%"
                    logger.info(f"Sector: {sector} - Change: {change_str}")
                
                return sector_data
            else:
                logger.warning("Failed to parse sector performance data")
                return None
    
    except URLError as e:
        logger.error(f"Network error accessing intradayscreener.com: {e}")
        return None
    except Exception as e:
        logger.error(f"Error getting sector performance data: {str(e)}")
        return None#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Add this function in the "Sector Performance Data Functions" section:

def get_sector_performance_from_csv():
    """
    Read sector performance data from CSV file generated by sector_scraper.py
    Returns a dictionary with sector names and their performance data
    """
    try:
        # Check if the sector data file exists
        sector_file = "sector_data.csv"
        if not os.path.exists(sector_file):
            logger.warning(f"Sector data file {sector_file} does not exist. Run sector_scraper.py first.")
            return None
        
        # Check if the file was modified in the last 5 minutes
        file_mod_time = os.path.getmtime(sector_file)
        current_time = time.time()
        if current_time - file_mod_time > 300:  # 5 minutes = 300 seconds
            logger.warning(f"Sector data file is older than 5 minutes. It might be stale.")
        
        # Read the CSV file using pandas
        df = pd.read_csv(sector_file)
        
        if df.empty:
            logger.warning("Sector data file is empty")
            return None
        
        # Convert the dataframe to our expected format
        sectors = {}
        for _, row in df.iterrows():
            sectors[row['name']] = {
                'name': row['name'],
                'change_percent': row['change_percent'],
                'is_positive': row['is_positive']
            }
        
        logger.info(f"Successfully loaded {len(sectors)} sectors from CSV file")
        
        # Log the sector performance
        for sector_name, data in list(sectors.items())[:5]:  # Show only first 5 sectors
            change_str = f"+{data['change_percent']:.2f}%" if data['is_positive'] else f"{data['change_percent']:.2f}%"
            logger.info(f"Sector: {sector_name} - Change: {change_str}")
        
        return sectors
    
    except Exception as e:
        logger.error(f"Error reading sector data from CSV: {str(e)}")
        return None

def load_security_ids():
    """Load security ID mappings from JSON file"""
    try:
        with open(SECURITY_IDS_FILE, 'r') as f:
            security_ids = json.load(f)
            logger.info(f"Security IDs loaded successfully from {SECURITY_IDS_FILE}")
            return security_ids
    except Exception as e:
        logger.error(f"Error loading security IDs: {str(e)}")
        # Return empty dict if file not found or other error
        return {}

def load_sector_mapping():
    """Load sector mapping from JSON file"""
    try:
        with open(SECTOR_MAPPING_FILE, 'r') as f:
            mapping = json.load(f)
            logger.info(f"Sector mapping loaded successfully with {len(mapping)} tickers")
            return mapping
    except Exception as e:
        logger.error(f"Error loading sector mapping: {str(e)}")
        # Return empty dict if file not found or other error
        return {}

def load_price_levels():
    """Load price level trading configuration from JSON file"""
    try:
        with open(PRICE_LEVELS_FILE, 'r') as f:
            price_levels = json.load(f)
            logger.info(f"Price levels configuration loaded successfully with {len(price_levels.get('stocks', []))} stocks")
            return price_levels
    except Exception as e:
        logger.error(f"Error loading price levels: {str(e)}")
        # Return empty dict if file not found or other error
        return {'enabled': False, 'stocks': []}

def load_credentials():
    """Load credentials from JSON file"""
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            credentials = json.load(f)
            logger.info(f"Credentials loaded successfully")
            return credentials
    except Exception as e:
        logger.error(f"Error loading credentials: {str(e)}")
        # Return empty dict if file not found or other error
        return {}

def initialize_dhan_client(config):
    """Initialize the Dhan API client"""
    try:
        dhan = dhanhq(config['client_id'], config['access_token'])
        logger.info("Dhan API client initialized successfully")
        return dhan
    except Exception as e:
        logger.error(f"Error initializing Dhan client: {str(e)}")
        raise

def get_security_id(ticker, security_ids_mapping, dhan=None):
    """
    Get security ID for a ticker symbol
    First checks the security_ids.json mapping, then tries API lookup if needed
    """
    ticker = ticker.strip()
    
    # First try to get from the loaded mapping
    security_id = security_ids_mapping.get(ticker)
    
    if security_id and security_id.strip():
        logger.info(f"Found security ID {security_id} for {ticker} from mapping file")
        return security_id
    
    # If not in mapping and we have a Dhan client, try API lookup as fallback
    if dhan and ticker:
        try:
            # Remove the exchange suffix (.NS) if present for lookup
            if "." in ticker:
                clean_symbol = ticker.split(".")[0]
            else:
                clean_symbol = ticker
                
            logger.info(f"Looking up security ID for ticker: {clean_symbol} via API")
            
            # Fetch the security list
            securities = dhan.fetch_security_list("compact")
            
            # Check if we got a list of securities
            if isinstance(securities, list):
                logger.info(f"Found {len(securities)} securities in the list")
                
                # Save the first 5 securities to a file for inspection
                with open('sample_securities.json', 'w') as f:
                    json.dump(securities[:5] if len(securities) > 5 else securities, f, indent=4)
                
                # Process based on the format
                for security in securities:
                    if isinstance(security, dict):
                        # Try different field names that might contain the symbol
                        symbol_fields = ['SYMBOL_NAME', 'symbolName', 'tradingSymbol', 'TRADING_SYMBOL', 'symbol']
                        for field in symbol_fields:
                            if field in security and security[field]:
                                symbol_value = str(security[field]).upper()
                                if clean_symbol.upper() == symbol_value:
                                    # Found a match, get the security ID
                                    id_fields = ['SECURITY_ID', 'securityId', 'security_id']
                                    for id_field in id_fields:
                                        if id_field in security and security[id_field]:
                                            security_id = str(security[id_field])
                                            logger.info(f"Found security ID {security_id} for {ticker} via API lookup")
                                            
                                            # Update the mapping file with this new ID for future use
                                            try:
                                                security_ids_mapping[ticker] = security_id
                                                with open(SECURITY_IDS_FILE, 'w') as f:
                                                    json.dump(security_ids_mapping, f, indent=4)
                                                logger.info(f"Updated {SECURITY_IDS_FILE} with new mapping for {ticker}")
                                            except Exception as e:
                                                logger.error(f"Error updating security IDs file: {str(e)}")
                                                
                                            return security_id
            
                        # Try name fields if symbol fields didn't match
                        name_fields = ['DISPLAY_NAME', 'displayName', 'name', 'NAME']
                        for field in name_fields:
                            if field in security and security[field]:
                                name_value = str(security[field]).upper()
                                if clean_symbol.upper() in name_value:
                                    # Found a partial match, get the security ID
                                    id_fields = ['SECURITY_ID', 'securityId', 'security_id']
                                    for id_field in id_fields:
                                        if id_field in security and security[id_field]:
                                            security_id = str(security[id_field])
                                            logger.info(f"Found security ID {security_id} for {ticker} via name match")
                                            
                                            # Update the mapping file with this new ID for future use
                                            try:
                                                security_ids_mapping[ticker] = security_id
                                                with open(SECURITY_IDS_FILE, 'w') as f:
                                                    json.dump(security_ids_mapping, f, indent=4)
                                                logger.info(f"Updated {SECURITY_IDS_FILE} with new mapping for {ticker}")
                                            except Exception as e:
                                                logger.error(f"Error updating security IDs file: {str(e)}")
                                                
                                            return security_id
            
            logger.warning(f"Could not find security ID for {ticker}")
            return None
        
        except Exception as e:
            logger.error(f"Error looking up security ID for {ticker}: {str(e)}")
            return None
    
    logger.warning(f"No security ID found for {ticker} and no API lookup available")
    return None

# =================================================================
# Market Data Functions
# =================================================================

def get_current_price(dhan, symbol, security_id, security_ids_mapping=None):
    """
    Get current market price for a stock
    
    Args:
        dhan: Dhan API client
        symbol: Stock symbol
        security_id: Security ID if known, otherwise None
        security_ids_mapping: Optional mapping of symbols to security IDs
        
    Returns:
        Current price as float or None if not available
    """
    try:
        # Get security ID if not provided
        if not security_id and security_ids_mapping:
            security_id = security_ids_mapping.get(symbol)
        
        if not security_id:
            security_id = get_security_id(symbol, security_ids_mapping, dhan)
            
        if not security_id:
            logger.error(f"Could not find security ID for {symbol}")
            return None
            
        # Get current price using OHLC data
        securities = {"NSE_EQ": [security_id]}
        market_data = dhan.ohlc_data(securities=securities)
        
        # Extract price based on response format
        current_price = None
        
        # Handle different possible data formats
        if isinstance(market_data, list):
            for data in market_data:
                if isinstance(data, dict) and str(data.get('securityId', data.get('SECURITY_ID', ''))) == str(security_id):
                    for price_field in ['ltp', 'lastPrice', 'last', 'close', 'LTP']:
                        if price_field in data:
                            current_price = float(data[price_field])
                            break
        
        elif isinstance(market_data, dict):
            for exchange, securities_data in market_data.items():
                if str(security_id) in securities_data:
                    for price_field in ['ltp', 'lastPrice', 'last', 'close', 'LTP']:
                        if price_field in securities_data[str(security_id)]:
                            current_price = float(securities_data[str(security_id)][price_field])
                            break
        
        if current_price:
            logger.info(f"Current price for {symbol}: {current_price}")
            return current_price
        else:
            logger.warning(f"Could not determine current price for {symbol}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting current price for {symbol}: {str(e)}")
        return None

# =================================================================
# Sector Performance Data Functions
# =================================================================

def get_sector_performance_with_dhan_auth(dhan_client, credentials=None):
    """
    Fetch sector performance data from intradayscreener.com using Dhan authentication
    
    Args:
        dhan_client: Initialized Dhan API client
        credentials: Optional additional credentials
        
    Returns a dictionary with sector names and their performance data
    """
    try:
        # Create a context that doesn't verify SSL certificates (use with caution)
        context = ssl._create_unverified_context()
        
        # Set up common headers for all requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Create an opener to maintain cookies between requests
        opener = build_opener(HTTPCookieProcessor())
        install_opener(opener)
        
        # Step 1: Visit the login page
        login_page_url = "https://intradayscreener.com/login"
        login_page_req = Request(login_page_url, headers=headers)
        with urlopen(login_page_req, context=context) as login_page_response:
            login_page_content = login_page_response.read().decode('utf-8')
        
        # Step 2: Click on the Dhan login option
        # This is tricky to simulate without JavaScript, but we can try to directly hit the endpoint
        
        # The URL for Dhan broker login might be something like:
        dhan_auth_url = "https://intradayscreener.com/auth/broker/dhan"
        logger.info(f"Attempting to authenticate with intradayscreener.com via Dhan")
        
        # We need to figure out what parameters are needed here
        # This might include Dhan credentials or tokens
        # For now, let's try a simple GET request to this URL
        dhan_auth_req = Request(dhan_auth_url, headers=headers)
        
        with urlopen(dhan_auth_req, context=context) as dhan_auth_response:
            # This will likely redirect to Dhan for authentication
            # or return JSON with next steps
            dhan_auth_content = dhan_auth_response.read().decode('utf-8')
            auth_url = dhan_auth_response.geturl()
            
            logger.info(f"Dhan auth redirected to: {auth_url}")
            
            # We might get a redirect URL or authentication instructions
            # The exact flow depends on how their integration works
        
        # After authentication (which might require more steps),
        # we should have cookies that allow access to sector performance
        
        # Try to access sector performance page
        sector_url = "https://intradayscreener.com/sector-performance"
        sector_req = Request(sector_url, headers=headers)
        
        with urlopen(sector_req, context=context) as response:
            html_content = response.read().decode('utf-8')
            
            # Check if we're redirected to login page
            if "/login" in response.geturl():
                logger.error("Authentication with Dhan failed. Unable to access sector performance.")
                return None
            
            # Process the HTML to extract sector performance data
            sector_data = parse_sector_performance_html(html_content)
            
            if sector_data:
                logger.info(f"Successfully fetched sector performance data via Dhan auth")
                return sector_data
            else:
                logger.warning("Failed to parse sector performance data")
                return None
    
    except URLError as e:
        logger.error(f"Network error during Dhan authentication: {e}")
        return None
    except Exception as e:
        logger.error(f"Error in Dhan authentication flow: {str(e)}")
        return None

def get_sector_performance(credentials=None):
    """
    Fetch sector performance data from intradayscreener.com
    Handles login if credentials are provided
    
    Args:
        credentials (dict): Optional login credentials with 'username' and 'password' keys
        
    Returns a dictionary with sector names and their performance data
    """
    try:
        # Create a context that doesn't verify SSL certificates (use with caution)
        context = ssl._create_unverified_context()
        
        # Set up common headers for all requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        # Create an opener to maintain cookies between requests
        opener = build_opener(HTTPCookieProcessor())
        install_opener(opener)
        
        # Handle login if credentials are provided
        if credentials and 'username' in credentials and 'password' in credentials:
            logger.info(f"Logging in to intradayscreener.com as {credentials['username']}")
            
            # Step 1: Visit the login page to get any necessary cookies or tokens
            login_page_url = "https://intradayscreener.com/login"
            login_page_req = Request(login_page_url, headers=headers)
            with urlopen(login_page_req, context=context) as login_page_response:
                login_page_content = login_page_response.read().decode('utf-8')
                
                # Optional: Extract CSRF token if needed
                # csrf_token_match = re.search(r'<input[^>]*name="csrf_token"[^>]*value="([^"]*)"', login_page_content)
                # csrf_token = csrf_token_match.group(1) if csrf_token_match else ""
            
            # Step 2: Submit login form
            login_data = {
                'username': credentials['username'],
                'password': credentials['password'],
                'remember_me': 'true'
                # Add CSRF token if needed
                # 'csrf_token': csrf_token
            }
            
            # Encode login data for POST request
            login_data_encoded = urlencode(login_data).encode('utf-8')
            
            # Set up login request
            login_url = "https://intradayscreener.com/login"  # Actual login form action URL
            login_req = Request(login_url, data=login_data_encoded, headers={
                **headers,
                'Content-Type': 'application/x-www-form-urlencoded'
            })
            
            # Submit login form
            with urlopen(login_req, context=context) as login_response:
                # Check if login was successful
                if login_response.geturl().endswith('/login'):
                    logger.error("Login failed. Check your credentials.")
                    return None
                else:
                    logger.info("Login successful")
        
        # Fetch sector performance page
        sector_url = "https://intradayscreener.com/sector-performance"
        logger.info("Fetching sector performance data from intradayscreener.com")
        
        sector_req = Request(sector_url, headers=headers)
        with urlopen(sector_req, context=context) as response:
            html_content = response.read().decode('utf-8')
            
            # Check if we're redirected to login page
            if "/login" in response.geturl():
                logger.error("Access to sector performance requires login. Please provide credentials.")
                return None
            
            # Process the HTML to extract sector performance data
            sector_data = parse_sector_performance_html(html_content)
            
            if sector_data:
                # Log the sector performance
                for sector, data in sector_data.items():
                    change_str = f"+{data['change_percent']:.2f}%" if data['is_positive'] else f"{data['change_percent']:.2f}%"
                    logger.info(f"Sector: {sector} - Change: {change_str}")
                
                return sector_data
            else:
                logger.warning("Failed to parse sector performance data")
                return None
    
    except URLError as e:
        logger.error(f"Network error accessing intradayscreener.com: {e}")
        return None
    except Exception as e:
        logger.error(f"Error getting sector performance data: {str(e)}")
        return None

def parse_sector_performance_html(html_content):
    """
    Parse the HTML content from intradayscreener.com to extract sector performance data
    """
    try:
        # Extract sector data using regex patterns
        sectors = {}
        
        # Pattern to find sector table rows
        pattern = r'<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>'
        
        # Find all matches in the HTML
        matches = re.finditer(pattern, html_content, re.DOTALL)
        
        for match in matches:
            # Extract sector name and change percentage
            sector_name = re.sub(r'<[^>]+>', '', match.group(1)).strip()
            change_text = re.sub(r'<[^>]+>', '', match.group(3)).strip()
            
            # Skip header row or empty rows
            if not sector_name or sector_name == "Sector" or "thead" in match.group(0):
                continue
            
            # Extract change percentage
            change_match = re.search(r'([-+]?\d+\.\d+)%', change_text)
            if change_match:
                change_percent = float(change_match.group(1))
                is_positive = change_percent > 0
                
                sectors[sector_name] = {
                    'name': sector_name,
                    'change_percent': change_percent,
                    'is_positive': is_positive
                }
        
        logger.info(f"Found {len(sectors)} sectors in performance data")
        return sectors
    
    except Exception as e:
        logger.error(f"Error parsing sector performance HTML: {str(e)}")
        return {}

def get_top_and_bottom_sectors(sector_data, top_count=3, bottom_count=3):
    """
    Get the top and bottom performing sectors
    Returns two lists: top sectors and bottom sectors
    """
    if not sector_data:
        return [], []
    
    # Convert to list and sort by change percentage
    sectors_list = list(sector_data.values())
    sectors_list.sort(key=lambda x: x['change_percent'], reverse=True)
    
    # Get top and bottom sectors
    top_sectors = sectors_list[:top_count]
    bottom_sectors = sectors_list[-bottom_count:]
    
    logger.info("Top performing sectors:")
    for sector in top_sectors:
        logger.info(f"  {sector['name']}: +{sector['change_percent']:.2f}%")
    
    logger.info("Bottom performing sectors:")
    for sector in bottom_sectors:
        logger.info(f"  {sector['name']}: {sector['change_percent']:.2f}%")
    
    return top_sectors, bottom_sectors

def get_sector_for_ticker(ticker, sector_mapping):
    """Get the sector for a given ticker symbol from the mapping"""
    return sector_mapping.get(ticker, "Unknown")

def determine_trading_action_by_sector(top_sectors, bottom_sectors):
    """
    Determine which sectors to buy and sell based on top and bottom sectors
    Returns:
    - buy_sectors: List of sector names to buy
    - sell_sectors: List of sector names to sell
    """
    buy_sectors = [sector['name'] for sector in top_sectors]
    sell_sectors = [sector['name'] for sector in bottom_sectors]
    
    return buy_sectors, sell_sectors

# =================================================================
# Order Management Functions
# =================================================================

def place_sector_based_orders(dhan, tickers_config, buy_sectors, sell_sectors, security_ids_mapping, sector_mapping):
    """
    Place orders based on sector performance
    - Buy tickers in top performing sectors
    - Sell tickers in bottom performing sectors
    Only places orders for tickers with active=true
    """
    order_responses = []
    
    logger.info(f"Processing {len(tickers_config)} tickers from config")
    logger.info(f"Buy sectors: {buy_sectors}")
    logger.info(f"Sell sectors: {sell_sectors}")
    
    for ticker in tickers_config:
        try:
            # STRICT check for active flag - default to FALSE if not present
            if not ticker.get('active', False):
                logger.info(f"Skipping inactive ticker: {ticker.get('symbol', 'Unknown')}")
                continue
                
            symbol = ticker.get('symbol')
            logger.info(f"Processing active ticker: {symbol}")
            
            # Get sector for this ticker using the loaded mapping
            sector = get_sector_for_ticker(symbol, sector_mapping)
            logger.info(f"Ticker {symbol} belongs to sector: {sector}")
            
            # Determine if we should buy or sell based on sector performance
            transaction_type = None
            if sector in buy_sectors:
                transaction_type = 'BUY'
                logger.info(f"BUY signal for {symbol} - sector {sector} is in top performers")
            elif sector in sell_sectors:
                transaction_type = 'SELL'
                logger.info(f"SELL signal for {symbol} - sector {sector} is in bottom performers")
            else:
                logger.info(f"No action for {symbol} - sector {sector} is not in top/bottom performers")
                continue
            
            # Check if the ticker's configured transaction type matches
            configured_type = ticker.get('transaction_type', '').upper()
            if configured_type and configured_type != transaction_type:
                logger.info(f"Skipping {symbol}: configured for {configured_type} but sector signal is {transaction_type}")
                continue
            
            # Get the security ID - first check if it's directly in the config
            security_id = ticker.get('security_id')
            
            # If not in config, look it up from the symbol
            if not security_id and 'symbol' in ticker:
                security_id = get_security_id(ticker['symbol'], security_ids_mapping, dhan)
                
            if not security_id:
                logger.error(f"Could not find security ID for {ticker.get('symbol', 'Unknown')}. Skipping this ticker.")
                continue
            
            # Check if entry price is specified, otherwise get current market price
            entry_price = ticker.get('entry_price')
            if not entry_price:
                logger.info(f"No entry price specified for {symbol}, using current market price")
                entry_price = get_current_price(dhan, symbol, security_id, security_ids_mapping)
                if not entry_price:
                    logger.error(f"Failed to get current market price for {symbol}. Skipping this ticker.")
                    continue
            
            logger.info(f"Executing {transaction_type} order for {ticker['symbol']} at price: {entry_price}")
            
            # Get stop loss and target percentages
            stop_loss_percent = ticker.get('stop_loss_percent', 0.75)  # Default 0.75% stop loss
            target_percent = ticker.get('target_percent', 1.0)        # Default 1.0% target
            
            # Calculate actual stop loss and target prices based on percentages
            if transaction_type == 'BUY':
                # For BUY orders: stop loss below entry, target above entry
                stop_loss_price = round(entry_price * (1 - stop_loss_percent/100), 2)
                target_price = round(entry_price * (1 + target_percent/100), 2)
            else:  # SELL orders
                # For SELL orders: stop loss above entry, target below entry
                stop_loss_price = round(entry_price * (1 + stop_loss_percent/100), 2)
                target_price = round(entry_price * (1 - target_percent/100), 2)
            
            # Update ticker with calculated values
            ticker['stop_loss'] = stop_loss_price
            ticker['target_price'] = target_price
            ticker['security_id'] = security_id  # Ensure security_id is in the ticker object
            ticker['transaction_type'] = transaction_type  # Update the transaction type
            ticker['entry_price'] = entry_price  # Update with current price if it was fetched
            
            logger.info(f"Setting {transaction_type} order for {ticker['symbol']} (ID: {security_id})")
            logger.info(f"Entry: {entry_price}")
            logger.info(f"Stop Loss: {stop_loss_price} ({stop_loss_percent}% {'below' if transaction_type == 'BUY' else 'above'} entry)")
            logger.info(f"Target: {target_price} ({target_percent}% {'above' if transaction_type == 'BUY' else 'below'} entry)")
            
            # Get the correct transaction type constant from dhan
            dhan_transaction_type = dhan.BUY if transaction_type == 'BUY' else dhan.SELL
            
            # Check if we need to use after market orders
            use_amo = ticker.get('after_market_order', False)
            
            # Place order
            order_params = {
                'security_id': security_id,
                'exchange_segment': dhan.NSE,
                'transaction_type': dhan_transaction_type,
                'quantity': ticker['quantity'],
                'order_type': dhan.LIMIT if entry_price > 0 else dhan.MARKET,
                'product_type': dhan.INTRA,  # Intraday order
                'price': entry_price if entry_price > 0 else 0
            }
            
            # Add AMO parameter if needed
            if use_amo:
                try:
                    # First try with afterMarketOrder
                    order_params_copy = order_params.copy()
                    order_params_copy['afterMarketOrder'] = True
                    response = dhan.place_order(**order_params_copy)
                except TypeError:
                    try:
                        # Then try with after_market_order
                        order_params_copy = order_params.copy()
                        order_params_copy['after_market_order'] = True
                        response = dhan.place_order(**order_params_copy)
                    except TypeError:
                        # If both fail, just place without AMO
                        logger.warning("Could not set after market order parameter, placing without AMO")
                        response = dhan.place_order(**order_params)
            else:
                response = dhan.place_order(**order_params)
            
            logger.info(f"Order placed: {response}")
            order_responses.append(response)
            
            # Save order details for tracking if order was successful
            if 'orderId' in response or ('status' in response and response['status'] == 'success'):
                # Extract order ID based on response format
                order_id = response.get('orderId', response.get('data', {}).get('orderId', 'unknown'))
                
                # Add ticker_name key for backward compatibility
                ticker['ticker_name'] = ticker['symbol'].split('.')[0] if '.' in ticker['symbol'] else ticker['symbol']
                save_order_details(order_id, ticker)
            elif 'remarks' in response:
                logger.warning(f"Order failed with remarks: {response['remarks']}")
        
        except Exception as e:
            logger.error(f"Error placing order for {ticker.get('symbol', 'Unknown')}: {str(e)}")
    
    return order_responses

def check_price_conditions(dhan, active_orders):
    """Check current prices against target and stop-loss for active orders"""
    if not active_orders:
        return
    
    # Get security IDs for all active orders
    securities = {}
    for order in active_orders:
        if order['status'] == 'OPEN':
            exchange = "NSE_EQ"
            if order['security_id'] not in securities.get(exchange, []):
                if exchange not in securities:
                    securities[exchange] = []
                securities[exchange].append(order['security_id'])
    
    if not securities:
        return
    
    # Get current prices
    try:
        market_data = dhan.ohlc_data(securities=securities)
        
        for order in active_orders:
            if order['status'] != 'OPEN':
                continue
                
            # Find this security in market data
            security_id = order['security_id']
            current_price = None
            
            # Handle different possible data formats
            if isinstance(market_data, list):
                for exchange_data in market_data:
                    if isinstance(exchange_data, dict):
                        data_security_id = str(exchange_data.get('securityId', exchange_data.get('SECURITY_ID')))
                        if data_security_id == str(security_id):
                            current_price = exchange_data.get('ltp', exchange_data.get('LTP'))
                            break
            elif isinstance(market_data, dict):
                for exchange, securities_data in market_data.items():
                    if str(security_id) in securities_data:
                        current_price = securities_data[str(security_id)].get('ltp', securities_data[str(security_id)].get('LTP'))
                        break
            
            if current_price:
                transaction_type = order.get('transaction_type', 'BUY').upper()
                
                if transaction_type == 'BUY':
                    # For BUY orders: target is above entry, stop loss is below
                    if current_price >= order['target_price']:
                        # Exit trade with profit
                        logger.info(f"TARGET REACHED for {order['ticker']} - Selling at {current_price}")
                        exit_order_id = exit_position(dhan, order, "SELL", reason="TARGET")
                        update_order_status(order['order_id'], 'CLOSED_TARGET', exit_order_id)
                    
                    elif current_price <= order['stop_loss']:
                        # Exit trade with loss
                        logger.info(f"STOP LOSS TRIGGERED for {order['ticker']} - Selling at {current_price}")
                        exit_order_id = exit_position(dhan, order, "SELL", reason="STOPLOSS")
                        update_order_status(order['order_id'], 'CLOSED_STOPLOSS', exit_order_id)
                
                else:  # SELL orders
                    # For SELL orders: target is below entry, stop loss is above
                    if current_price <= order['target_price']:
                        # Exit trade with profit
                        logger.info(f"TARGET REACHED for {order['ticker']} - Buying at {current_price}")
                        exit_order_id = exit_position(dhan, order, "BUY", reason="TARGET")
                        update_order_status(order['order_id'], 'CLOSED_TARGET', exit_order_id)
                    
                    elif current_price >= order['stop_loss']:
                        # Exit trade with loss
                        logger.info(f"STOP LOSS TRIGGERED for {order['ticker']} - Buying at {current_price}")
                        exit_order_id = exit_position(dhan, order, "BUY", reason="STOPLOSS")
                        update_order_status(order['order_id'], 'CLOSED_STOPLOSS', exit_order_id)
    
    except Exception as e:
        logger.error(f"Error checking price conditions: {str(e)}")

def check_price_levels(dhan, price_levels_config, security_ids_mapping):
    """
    Check current prices against defined price levels and execute trades
    
    Args:
        dhan: Dhan API client
        price_levels_config: Price levels configuration
        security_ids_mapping: Mapping of symbols to security IDs
    """
    if not price_levels_config.get('enabled', False):
        logger.info("Price level trading is disabled")
        return
        
    stocks = price_levels_config.get('stocks', [])
    if not stocks:
        logger.info("No stocks defined for price level trading")
        return
        
    logger.info(f"Checking price levels for {len(stocks)} stocks")
    
    # Track active trades to avoid duplicate orders
    active_trades_file = PRICE_LEVEL_TRADES_FILE
    active_trades = {}
    
    # Load existing active trades
    if os.path.exists(active_trades_file):
        try:
            with open(active_trades_file, 'r') as f:
                active_trades = json.load(f)
        except:
            active_trades = {}
    
    for stock in stocks:
        if not stock.get('active', False):
            continue
            
        symbol = stock.get('symbol')
        security_id = stock.get('security_id')
        
        # Skip if already have an active trade for this stock
        if symbol in active_trades:
            logger.info(f"Already have an active trade for {symbol}, skipping price check")
            continue
            
        # Get current price
        current_price = get_current_price(dhan, symbol, security_id, security_ids_mapping)
        if not current_price:
            continue
            
        buy_price = stock.get('buy_price')
        
        # If current price is near buy price (within 0.1%), place buy order
        if buy_price and current_price <= buy_price * 1.001 and current_price >= buy_price * 0.999:
            logger.info(f"Price trigger reached for {symbol}: current {current_price}, buy level {buy_price}")
            
            # Place buy order
            try:
                order_params = {
                    'security_id': security_id,
                    'exchange_segment': dhan.NSE,
                    'transaction_type': dhan.BUY,
                    'quantity': stock.get('quantity', 1),
                    'order_type': dhan.LIMIT,
                    'product_type': dhan.INTRA,
                    'price': buy_price
                }
                
                response = dhan.place_order(**order_params)
                logger.info(f"Buy order placed for {symbol}: {response}")
                
                if 'orderId' in response or ('status' in response and response['status'] == 'success'):
                    # Record the trade
                    order_id = response.get('orderId', response.get('data', {}).get('orderId', 'unknown'))
                    
                    active_trades[symbol] = {
                        'symbol': symbol,
                        'security_id': security_id,
                        'order_id': order_id,
                        'buy_price': buy_price,
                        'quantity': stock.get('quantity', 1),
                        'target_price': stock.get('target_price'),
                        'stop_loss': stock.get('stop_loss'),
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    # Save updated active trades
                    with open(active_trades_file, 'w') as f:
                        json.dump(active_trades, f, indent=4)
            
            except Exception as e:
                logger.error(f"Error placing buy order for {symbol}: {str(e)}")
    
    # Check for exit conditions (target or stop loss) for active trades
    trades_to_remove = []
    
    for symbol, trade in active_trades.items():
        security_id = trade.get('security_id')
        target_price = trade.get('target_price')
        stop_loss = trade.get('stop_loss')
        
        # Get current price
        current_price = get_current_price(dhan, symbol, security_id, security_ids_mapping)
        if not current_price:
            continue
            
        # Check if target or stop loss reached
        if target_price and current_price >= target_price:
            logger.info(f"Target price reached for {symbol}: current {current_price}, target {target_price}")
            
            # Place sell order
            try:
                order_params = {
                    'security_id': security_id,
                    'exchange_segment': dhan.NSE,
                    'transaction_type': dhan.SELL,
                    'quantity': trade.get('quantity', 1),
                    'order_type': dhan.LIMIT,
                    'product_type': dhan.INTRA,
                    'price': target_price
                }
                
                response = dhan.place_order(**order_params)
                logger.info(f"Sell order placed for {symbol} at target: {response}")
                
                if 'orderId' in response or ('status' in response and response['status'] == 'success'):
                    trades_to_remove.append(symbol)
            
            except Exception as e:
                logger.error(f"Error placing sell order at target for {symbol}: {str(e)}")
        
        elif stop_loss and current_price <= stop_loss:
            logger.info(f"Stop loss reached for {symbol}: current {current_price}, stop loss {stop_loss}")
            
            # Place sell order
            try:
                order_params = {
                    'security_id': security_id,
                    'exchange_segment': dhan.NSE,
                    'transaction_type': dhan.SELL,
                    'quantity': trade.get('quantity', 1),
                    'order_type': dhan.LIMIT,
                    'product_type': dhan.INTRA,
                    'price': stop_loss
                }
                
                response = dhan.place_order(**order_params)
                logger.info(f"Sell order placed for {symbol} at stop loss: {response}")
                
                if 'orderId' in response or ('status' in response and response['status'] == 'success'):
                    trades_to_remove.append(symbol)
            
            except Exception as e:
                logger.error(f"Error placing sell order at stop loss for {symbol}: {str(e)}")
    
    # Remove completed trades
    for symbol in trades_to_remove:
        if symbol in active_trades:
            del active_trades[symbol]
    
    # Save updated active trades
    if trades_to_remove:
        with open(active_trades_file, 'w') as f:
            json.dump(active_trades, f, indent=4)

def exit_position(dhan, order, exit_type, reason=""):
    """Exit a position (buy or sell depending on initial position)"""
    try:
        # For a BUY order, we exit with SELL; for a SELL order, we exit with BUY
        dhan_transaction_type = dhan.SELL if exit_type == "SELL" else dhan.BUY
        
        exit_order = dhan.place_order(
            security_id=order['security_id'],
            exchange_segment=dhan.NSE,
            transaction_type=dhan_transaction_type,
            quantity=order['quantity'],
            order_type=dhan.MARKET,
            product_type=dhan.INTRA,
            price=0
        )
        
        logger.info(f"Exited position for {order['ticker']} - Reason: {reason}")
        logger.info(f"Exit order details: {exit_order}")
        
        # Extract order ID based on response format
        if isinstance(exit_order, dict):
            return exit_order.get('orderId', exit_order.get('data', {}).get('orderId', 'unknown'))
        return 'unknown'
    
    except Exception as e:
        logger.error(f"Error exiting position: {str(e)}")
        return 'error'

def close_positions_by_type(dhan, active_orders, transaction_type):
    """
    Close positions of a specific type (BUY or SELL)
    """
    orders_to_close = [order for order in active_orders if order['transaction_type'].upper() == transaction_type]
    
    if not orders_to_close:
        logger.info(f"No {transaction_type} positions to close")
        return []
    
    logger.info(f"Closing {len(orders_to_close)} {transaction_type} positions due to Nifty movement")
    
    exit_responses = []
    for order in orders_to_close:
        try:
            # For BUY positions, we exit with SELL; for SELL positions, we exit with BUY
            exit_type = "SELL" if transaction_type == "BUY" else "BUY"
            
            logger.info(f"Closing {transaction_type} position for {order['ticker']} due to Nifty movement")
            exit_order_id = exit_position(dhan, order, exit_type, reason="NIFTY_MOVEMENT")
            
            if exit_order_id != 'error':
                update_order_status(order['order_id'], 'CLOSED_NIFTY_MOVEMENT', exit_order_id)
                exit_responses.append(exit_order_id)
        
        except Exception as e:
            logger.error(f"Error closing position for {order['ticker']}: {str(e)}")
    
    return exit_responses

# =================================================================
# Order Tracking Functions
# =================================================================

def save_order_details(order_id, ticker_info):
    """Save order details for tracking"""
    transaction_type = ticker_info.get('transaction_type', 'BUY')
    
    order_data = {
        'order_id': order_id,
        'ticker': ticker_info.get('ticker_name', ticker_info.get('symbol', 'Unknown')),
        'security_id': ticker_info['security_id'],
        'transaction_type': transaction_type,
        'entry_price': ticker_info['entry_price'],
        'quantity': ticker_info['quantity'],
        'target_price': ticker_info['target_price'],
        'stop_loss': ticker_info['stop_loss'],
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'OPEN'
    }
    
    try:
        if os.path.exists(ORDER_TRACKER_FILE):
            orders_df = pd.read_csv(ORDER_TRACKER_FILE)
            if len(orders_df) == 0:
                orders_df = pd.DataFrame([order_data])
            else:
                orders_df = pd.concat([orders_df, pd.DataFrame([order_data])], ignore_index=True)
        else:
            orders_df = pd.DataFrame([order_data])
        
        orders_df.to_csv(ORDER_TRACKER_FILE, index=False)
    except Exception as e:
        logger.error(f"Error saving order details: {str(e)}")
    return

def update_order_status(order_id, new_status, exit_order_id=None):
    """Update the status of an order in the tracker"""
    try:
        if os.path.exists(ORDER_TRACKER_FILE):
            orders_df = pd.read_csv(ORDER_TRACKER_FILE)
            idx = orders_df.index[orders_df['order_id'] == order_id].tolist()
            
            if idx:
                orders_df.at[idx[0], 'status'] = new_status
                if exit_order_id:
                    orders_df.at[idx[0], 'exit_order_id'] = exit_order_id
                orders_df.at[idx[0], 'exit_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
            orders_df.to_csv(ORDER_TRACKER_FILE, index=False)
    except Exception as e:
        logger.error(f"Error updating order status: {str(e)}")

def get_active_orders():
    """Get list of active orders from tracker"""
    try:
        if os.path.exists(ORDER_TRACKER_FILE):
            orders_df = pd.read_csv(ORDER_TRACKER_FILE)
            active = orders_df[orders_df['status'] == 'OPEN'].to_dict('records')
            return active
        else:
            return []
    except:
        return []

# =================================================================
# Main Program
# =================================================================

def main():
    """Main program execution"""
    try:
        # Clear previous order tracking at startup
        if os.path.exists(ORDER_TRACKER_FILE):
            # Backup the old file first
            backup_time = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f'order_tracker_backup_{backup_time}.csv'
            os.rename(ORDER_TRACKER_FILE, backup_filename)
            logger.info(f"Previous order tracker backed up to {backup_filename}")
            logger.info("Starting with fresh order tracking")
        
        # Load configurations
        config = load_config()
        security_ids_mapping = load_security_ids()
        sector_mapping = load_sector_mapping()
        price_levels_config = load_price_levels()
        
        # Validate configurations
        if not sector_mapping:
            logger.error("Failed to load sector mapping. Sector-based trading will be disabled.")
        
        # Initialize Dhan client with the loaded config
        dhan = initialize_dhan_client(config)
        
        logger.info("Starting trading program with multiple strategies")
        
        # Log configuration details for debugging
        place_new_orders = config.get('place_new_orders', False)
        logger.info(f"place_new_orders setting: {place_new_orders}")
        
        # Log active tickers from configuration
        active_tickers = [t.get('symbol') for t in config.get('tickers', []) if t.get('active', False)]
        logger.info(f"Active tickers in sector-based config: {active_tickers}")
        
        # Log price level strategy status
        price_level_enabled = price_levels_config.get('enabled', False)
        logger.info(f"Price level strategy enabled: {price_level_enabled}")
        if price_level_enabled:
            active_price_tickers = [t.get('symbol') for t in price_levels_config.get('stocks', []) if t.get('active', False)]
            logger.info(f"Active tickers in price level config: {active_price_tickers}")
        
        # Initialize variables for sector-based strategy
        sector_data = None
        top_sectors = []
        bottom_sectors = []
        buy_sectors = []
        sell_sectors = []
        
        # Get sector performance data from CSV file
        if sector_mapping:
            # Get sector data from CSV
            sector_data = get_sector_performance_from_csv()
            
            if sector_data:
                # Get top and bottom sectors
                sectors_list = list(sector_data.values())
                sectors_list.sort(key=lambda x: x['change_percent'], reverse=True)
                
                top_sectors = sectors_list[:3]  # Top 3 sectors
                bottom_sectors = sectors_list[-3:]  # Bottom 3 sectors
                
                # Determine which sectors to buy and sell
                buy_sectors = [sector['name'] for sector in top_sectors]
                sell_sectors = [sector['name'] for sector in bottom_sectors]
                
                logger.info("Top performing sectors:")
                for sector in top_sectors:
                    logger.info(f"  {sector['name']}: +{sector['change_percent']:.2f}%")
                
                logger.info("Bottom performing sectors:")
                for sector in bottom_sectors:
                    logger.info(f"  {sector['name']}: {sector['change_percent']:.2f}%")
            else:
                logger.error("Failed to get sector data from CSV. Sector-based strategy will be disabled.")
        
        # Initial trading setup
        active_orders = get_active_orders()
        
        # Execute sector-based strategy if configured and we have sector data
        if sector_mapping and sector_data and place_new_orders:
            logger.info("Placing orders based on sector performance")
            place_sector_based_orders(dhan, config['tickers'], buy_sectors, sell_sectors, security_ids_mapping, sector_mapping)
        
        # Execute price level strategy if enabled
        if price_level_enabled:
            logger.info("Checking price levels for trading")
            check_price_levels(dhan, price_levels_config, security_ids_mapping)
        
        # Continuous monitoring loop
        logger.info("Starting continuous monitoring with 1-minute refresh interval...")
        
        try:
            while True:
                # Get active orders
                active_orders = get_active_orders()
                
                # Execute sector-based strategy if we have sector mapping
                if sector_mapping:
                    # Get updated sector data from CSV
                    new_sector_data = get_sector_performance_from_csv()
                    
                    if new_sector_data:
                        # Update our sector data
                        sector_data = new_sector_data
                        
                        # Get updated top and bottom sectors
                        sectors_list = list(sector_data.values())
                        sectors_list.sort(key=lambda x: x['change_percent'], reverse=True)
                        
                        top_sectors = sectors_list[:3]  # Top 3 sectors
                        bottom_sectors = sectors_list[-3:]  # Bottom 3 sectors
                        
                        # Determine which sectors to buy and sell
                        buy_sectors = [sector['name'] for sector in top_sectors]
                        sell_sectors = [sector['name'] for sector in bottom_sectors]
                        
                        if place_new_orders:
                            logger.info("Placing orders based on updated sector performance")
                            place_sector_based_orders(dhan, config['tickers'], buy_sectors, sell_sectors, security_ids_mapping, sector_mapping)
                    else:
                        logger.warning("Failed to get updated sector performance data from CSV")
                
                # Execute price level strategy
                if price_level_enabled:
                    logger.info("Checking price levels for trading")
                    check_price_levels(dhan, price_levels_config, security_ids_mapping)
                
                # Check target/stop-loss conditions for active orders
                if active_orders:
                    logger.info(f"Monitoring {len(active_orders)} active orders...")
                    check_price_conditions(dhan, active_orders)
                
                # Wait exactly 1 minute before next refresh
                logger.info("Waiting 60 seconds for next refresh...")
                time.sleep(60)
        
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user.")
        
        # Check final positions at end of day
        logger.info("Current positions:")
        positions = dhan.get_positions()
        logger.info(positions)
        
    except Exception as e:
        logger.error(f"Critical error in main program: {str(e)}")
        
if __name__ == "__main__":
    main()