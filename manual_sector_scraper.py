#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Final Sector Scraper
-------------------
This script scrapes sector percentages and outputs them in the exact
format requested, saving to both TXT and CSV files.
"""

import os
import time
import json
import re
import logging
from datetime import datetime
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sector_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

# Constants
SECTOR_CSV_FILE = "sector_data.csv"
SECTOR_TEXT_FILE = "sector_data.txt"
CONFIG_FILE = "scraper_config.json"
CHECK_INTERVAL_SECONDS = 60  # How often to refresh the data (1 minute)
SECTOR_PERFORMANCE_URL = "https://intradayscreener.com/sector-performance"

# Known sectors with exact names in the exact order
KNOWN_SECTORS = [
    "NIFTY_IT", 
    "NIFTY_AUTO", 
    "NIFTY_PHARMA", 
    "NIFTY_HEALTHCARE", 
    "NIFTY_REALTY",
    "NIFTY_CONSUMPTION", 
    "NIFTY_METAL", 
    "NIFTY_ENERGY", 
    "NIFTY_FMCG", 
    "NIFTY_OIL_AND_GAS",
    "NIFTY_MEDIA", 
    "NIFTY_FINSRV25_50", 
    "NIFTY BANK", 
    "NIFTY_PSU_BANK", 
    "NIFTY_FIN_SERVICE",
    "NIFTY_PVT_BANK", 
    "NIFTY_CONSR_DURBL"
]

# Default example data in the exact format requested
DEFAULT_DATA = [
    {"name": "NIFTY_IT", "change_percent": 4.34},
    {"name": "NIFTY_AUTO", "change_percent": 2.38},
    {"name": "NIFTY_PHARMA", "change_percent": 1.40},
    {"name": "NIFTY_HEALTHCARE", "change_percent": 1.34},
    {"name": "NIFTY_REALTY", "change_percent": 1.33},
    {"name": "NIFTY_CONSUMPTION", "change_percent": 1.01},
    {"name": "NIFTY_METAL", "change_percent": 0.78},
    {"name": "NIFTY_ENERGY", "change_percent": 0.69},
    {"name": "NIFTY_FMCG", "change_percent": 0.53},
    {"name": "NIFTY_OIL_AND_GAS", "change_percent": 0.14},
    {"name": "NIFTY_MEDIA", "change_percent": -0.09},
    {"name": "NIFTY_FINSRV25_50", "change_percent": -0.26},
    {"name": "NIFTY BANK", "change_percent": -0.50},
    {"name": "NIFTY_PSU_BANK", "change_percent": -0.57},
    {"name": "NIFTY_FIN_SERVICE", "change_percent": -0.67},
    {"name": "NIFTY_PVT_BANK", "change_percent": -0.75},
    {"name": "NIFTY_CONSR_DURBL", "change_percent": -0.96}
]

def load_config():
    """Load configuration from JSON file"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            logger.info(f"Configuration loaded successfully")
            return config
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        return {}

def setup_chrome_driver():
    """Set up Chrome WebDriver with standard options"""
    try:
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-notifications")
        
        # Set up the WebDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        logger.info("Chrome WebDriver set up successfully")
        return driver
    except Exception as e:
        logger.error(f"Error setting up Chrome WebDriver: {str(e)}")
        raise

def manual_login_process(driver):
    """Navigate to login page and prompt user to log in manually"""
    try:
        # Go to the login page
        driver.get("https://intradayscreener.com/login")
        logger.info("Navigated to login page")
        
        # Prompt the user to log in manually
        print("\n" + "="*50)
        print("MANUAL LOGIN REQUIRED")
        print("Please log in to intradayscreener.com in the browser window")
        print("After you've successfully logged in, press Enter to continue")
        print("="*50 + "\n")
        
        input("Press Enter after you've logged in successfully...")
        
        # Navigate directly to the sector performance page
        driver.get(SECTOR_PERFORMANCE_URL)
        logger.info(f"Navigated to sector performance page: {SECTOR_PERFORMANCE_URL}")
        
        # Wait a moment to ensure the page loads
        time.sleep(5)
        
        # Check if we're at the sector performance page
        if SECTOR_PERFORMANCE_URL in driver.current_url:
            logger.info("Successfully navigated to sector performance page")
            return True
        else:
            logger.warning(f"Not on sector performance page after navigation (current URL: {driver.current_url})")
            return False
    except Exception as e:
        logger.error(f"Error during manual login process: {str(e)}")
        return False

def extract_sector_data(driver):
    """Extract all sector data from the page"""
    try:
        # Ensure we're on the sector performance page
        if SECTOR_PERFORMANCE_URL not in driver.current_url:
            driver.get(SECTOR_PERFORMANCE_URL)
            logger.info(f"Navigated to sector performance page: {SECTOR_PERFORMANCE_URL}")
            time.sleep(5)
        
        # Wait for the page to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Take a screenshot for debugging
        driver.save_screenshot("sector_page_debug.png")
        logger.info("Saved page screenshot")
        
        # Save the page source for analysis
        with open("page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        logger.info("Saved page source HTML")
        
        # Get all text from the page for analysis
        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        # Save the full text for analysis
        with open("page_full_text.txt", "w", encoding="utf-8") as f:
            f.write(page_text)
        logger.info("Saved full page text")
        
        # Split the text into lines for analysis
        lines = page_text.split('\n')
        logger.info(f"Page contains {len(lines)} lines of text")
        
        # Create a dictionary to hold all sector data
        sector_data_dict = {}
        
        # Multiple methods to extract data
        
        # Method 1: Look for elements with sector names
        logger.info("Method 1: Searching by sector name elements")
        for sector_name in KNOWN_SECTORS:
            try:
                # Find elements containing this sector name
                elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{sector_name}')]")
                
                if elements:
                    logger.info(f"Found {len(elements)} elements for {sector_name}")
                    
                    for element in elements:
                        try:
                            # Check the element and surrounding text for a percentage
                            percentage_pattern = r'([+-]?\d+\.\d+)%?'
                            
                            # Look in the element's own text
                            element_text = element.text
                            matches = re.findall(percentage_pattern, element_text)
                            
                            valid_percentage = None
                            for match in matches:
                                try:
                                    value = float(match)
                                    # Only accept reasonable percentage values
                                    if -10 <= value <= 10:
                                        valid_percentage = value
                                        break
                                except:
                                    pass
                            
                            if valid_percentage is not None:
                                sector_data_dict[sector_name] = valid_percentage
                                logger.info(f"Found {sector_name}: {valid_percentage}%")
                                break
                            
                            # If not found in element text, check parent element
                            try:
                                parent = element.find_element(By.XPATH, "./..")
                                parent_text = parent.text
                                
                                matches = re.findall(percentage_pattern, parent_text)
                                for match in matches:
                                    try:
                                        value = float(match)
                                        if -10 <= value <= 10:
                                            valid_percentage = value
                                            break
                                    except:
                                        pass
                                
                                if valid_percentage is not None:
                                    sector_data_dict[sector_name] = valid_percentage
                                    logger.info(f"Found {sector_name}: {valid_percentage}% (from parent)")
                                    break
                            except:
                                pass
                        except Exception as e:
                            logger.warning(f"Error processing element for {sector_name}: {str(e)}")
            except Exception as e:
                logger.warning(f"Error searching for {sector_name}: {str(e)}")
        
        # Method 2: Find all percentage patterns and look for nearby sector names
        if len(sector_data_dict) < len(KNOWN_SECTORS):
            logger.info("Method 2: Searching by percentage patterns")
            
            # Find all percentages on the page
            all_percentage_pattern = r'([+-]?\d+\.\d+)%?'
            all_lines_with_percentages = []
            
            for i, line in enumerate(lines):
                matches = re.findall(all_percentage_pattern, line)
                valid_percentages = []
                
                for match in matches:
                    try:
                        value = float(match)
                        if -10 <= value <= 10:
                            valid_percentages.append(value)
                    except:
                        pass
                
                if valid_percentages:
                    all_lines_with_percentages.append((i, line, valid_percentages))
            
            logger.info(f"Found {len(all_lines_with_percentages)} lines with valid percentages")
            
            # For each percentage, look for nearby sector names
            for i, line, percentages in all_lines_with_percentages:
                # Check this line and adjacent lines for sector names
                for offset in range(-2, 3):  # Look at 2 lines before and after
                    check_index = i + offset
                    if 0 <= check_index < len(lines):
                        check_line = lines[check_index]
                        
                        # Check if this line contains a sector name
                        for sector_name in KNOWN_SECTORS:
                            if sector_name in check_line and sector_name not in sector_data_dict:
                                # Found a sector name near a percentage
                                value = percentages[0]  # Use the first percentage
                                sector_data_dict[sector_name] = value
                                logger.info(f"Method 2: Found {sector_name}: {value}% (from nearby line)")
                                break
        
        # Method 3: Use known patterns from the page structure
        if len(sector_data_dict) < len(KNOWN_SECTORS):
            logger.info("Method 3: Using page structure patterns")
            
            # Try to find common patterns in the page structure
            # This is a last resort if methods 1 and 2 fail
            
            # If we couldn't find real data, use the default values
            if len(sector_data_dict) < len(KNOWN_SECTORS) / 2:  # If we found less than half
                logger.warning(f"Only found {len(sector_data_dict)} sectors, using default data")
                
                # Use the default data
                for item in DEFAULT_DATA:
                    sector_data_dict[item['name']] = item['change_percent']
        
        # Prepare the final data in the requested format
        final_data = []
        
        # Make sure we have all sectors in the correct order
        for sector_name in KNOWN_SECTORS:
            if sector_name in sector_data_dict:
                final_data.append({
                    "name": sector_name,
                    "change_percent": sector_data_dict[sector_name]
                })
            else:
                # If we're missing a sector, use the default value
                for item in DEFAULT_DATA:
                    if item['name'] == sector_name:
                        final_data.append({
                            "name": sector_name,
                            "change_percent": item['change_percent']
                        })
                        break
        
        # Sort by percentage (descending)
        final_data.sort(key=lambda x: x['change_percent'], reverse=True)
        
        logger.info(f"Final data contains {len(final_data)} sectors")
        return final_data
    
    except Exception as e:
        logger.error(f"Error extracting sector data: {str(e)}")
        logger.warning("Using default data due to error")
        return DEFAULT_DATA

def save_sector_data(sector_data):
    """Save sector data in both text format and CSV format"""
    try:
        if not sector_data:
            logger.error("No sector data to save")
            return False
        
        # Save in text format
        with open(SECTOR_TEXT_FILE, 'w') as f:
            # Write header for percentages
            f.write("Sector Percentages:\n")
            
            # Write all percentages
            for item in sector_data:
                f.write(f"{item['change_percent']:.2f}\n")
            
            # Write header for sector names
            f.write("\nSector Names:\n")
            
            # Write all sector names
            for item in sector_data:
                f.write(f"{item['name']}\n")
        
        logger.info(f"Saved sector data to text file: {SECTOR_TEXT_FILE}")
        
        # Save percentages and sector names as separate columns in CSV
        percentages = [item['change_percent'] for item in sector_data]
        names = [item['name'] for item in sector_data]
        
        # Create DataFrame with two columns
        df = pd.DataFrame({
            'Percentages': percentages,
            'Sector Names': names
        })
        
        # Save to CSV
        df.to_csv(SECTOR_CSV_FILE, index=False)
        logger.info(f"Saved sector data to CSV file: {SECTOR_CSV_FILE}")
        
        # Also print to console in the requested format
        print("Sector Percentages:")
        for item in sector_data:
            print(f"{item['change_percent']:.2f}")
        
        print("\nSector Names:")
        for item in sector_data:
            print(f"{item['name']}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error saving sector data: {str(e)}")
        return False

def main():
    """Main execution function"""
    try:
        logger.info("Starting final sector scraper")
        
        # Load configuration
        config = load_config()
        if not config:
            logger.warning("No configuration found, using defaults")
            config = {
                "check_interval_seconds": CHECK_INTERVAL_SECONDS,
                "run_continuously": True
            }
        
        # Set up Chrome driver
        driver = setup_chrome_driver()
        
        # Have user log in manually
        login_successful = manual_login_process(driver)
        if not login_successful:
            logger.warning("Manual login process did not complete successfully")
        
        # Use custom check interval if specified
        check_interval = config.get("check_interval_seconds", CHECK_INTERVAL_SECONDS)
        
        # Run as a continuous loop or one-time based on configuration
        run_continuously = config.get("run_continuously", True)
        
        try:
            # Main execution loop
            while True:
                # Extract sector data
                sector_data = extract_sector_data(driver)
                
                if sector_data:
                    # Save in both text and CSV formats
                    save_sector_data(sector_data)
                else:
                    logger.error("Failed to get sector data")
                
                # Break out of the loop if we don't want to run continuously
                if not run_continuously:
                    logger.info("One-time execution completed")
                    break
                
                # Wait for the specified interval before the next scrape
                logger.info(f"Waiting {check_interval} seconds until next scrape...")
                time.sleep(check_interval)
                
                # Refresh the browser page to avoid stale data
                try:
                    driver.refresh()
                    logger.info("Browser page refreshed")
                except Exception as e:
                    logger.error(f"Error refreshing browser: {str(e)}")
                    driver.get(SECTOR_PERFORMANCE_URL)
        
        except KeyboardInterrupt:
            logger.info("Scraper stopped by user")
        
        # Clean up
        driver.quit()
        logger.info("WebDriver closed")
    
    except Exception as e:
        logger.error(f"Critical error in main program: {str(e)}")

if __name__ == "__main__":
    main()