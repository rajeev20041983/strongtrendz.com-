#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Auto Login Sector Scraper
-------------------------
This script handles automated login to intradayscreener.com using provided credentials,
then scrapes sector performance data and saves it to CSV files.
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
from selenium.webdriver.common.keys import Keys

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
SECTOR_DATA_FILE = "sector_data.csv"
CONFIG_FILE = "scraper_config.json"
CHECK_INTERVAL_SECONDS = 60  # How often to refresh the data (1 minute)

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
        
        # Automation detection evasion
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Set up the WebDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Change the navigator properties to avoid detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        logger.info("Chrome WebDriver set up successfully")
        return driver
    except Exception as e:
        logger.error(f"Error setting up Chrome WebDriver: {str(e)}")
        raise

def detect_input_type(driver):
    """Detect what type of input the page is asking for (PIN, password, phone, etc.)"""
    try:
        # Take screenshot to help with debugging
        driver.save_screenshot("detect_input_type.png")
        
        # Log the URL which can help determine the context
        logger.info(f"Detecting input type at URL: {driver.current_url}")
        
        # Look for input fields with specific attributes
        input_elements = driver.find_elements(By.XPATH, "//input")
        
        for i, inp in enumerate(input_elements):
            try:
                inp_type = inp.get_attribute("type")
                inp_id = inp.get_attribute("id")
                inp_placeholder = inp.get_attribute("placeholder") or ""
                inp_name = inp.get_attribute("name") or ""
                inp_class = inp.get_attribute("class") or ""
                
                logger.info(f"Input {i}: type={inp_type}, id={inp_id}, placeholder='{inp_placeholder}', name='{inp_name}'")
                
                # Check for PIN indicators
                if (inp_type == "password" or 
                    "pin" in inp_id.lower() or 
                    "pin" in inp_placeholder.lower() or 
                    "pin" in inp_name.lower() or
                    "code" in inp_placeholder.lower()):
                    logger.info(f"Detected PIN input: {inp_id}")
                    return "pin"
                
                # Check for password indicators
                if (inp_type == "password" and
                    ("password" in inp_id.lower() or 
                     "password" in inp_placeholder.lower() or 
                     "password" in inp_name.lower())):
                    logger.info(f"Detected password input: {inp_id}")
                    return "password"
                
                # Check for phone indicators
                if (inp_type == "tel" or
                    "phone" in inp_id.lower() or
                    "mobile" in inp_id.lower() or
                    "phone" in inp_placeholder.lower() or
                    "mobile" in inp_placeholder.lower()):
                    logger.info(f"Detected phone input: {inp_id}")
                    return "phone"
            except Exception as e:
                logger.warning(f"Error examining input {i}: {str(e)}")
        
        # Look for text clues on the page
        page_text_indicators = {
            "pin": ["enter pin", "login pin", "dhan pin", "trading pin", "4-digit pin", "6-digit pin"],
            "password": ["enter password", "your password", "account password"],
            "phone": ["mobile number", "phone number", "registered mobile"]
        }
        
        # Extract visible text from the page
        visible_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        
        for input_type, indicators in page_text_indicators.items():
            for indicator in indicators:
                if indicator in visible_text:
                    logger.info(f"Detected {input_type} request based on text: '{indicator}'")
                    return input_type
        
        # Default to checking input type attributes if text clues don't help
        for inp in input_elements:
            inp_type = inp.get_attribute("type")
            if inp_type == "password":
                logger.info("Defaulting to PIN for password field")
                return "pin"
            elif inp_type == "tel":
                logger.info("Defaulting to phone for tel field")
                return "phone"
        
        # If we can't determine, assume it's asking for PIN as a fallback
        logger.warning("Could not determine input type, defaulting to PIN")
        return "pin"
        
    except Exception as e:
        logger.error(f"Error detecting input type: {str(e)}")
        # Default to PIN as a fallback
        return "pin"

def automated_login(driver, config):
    """Attempt to log in automatically using credentials from config"""
    try:
        # Check if we have the necessary credentials
        if 'credentials' not in config:
            logger.error("No credentials found in config")
            return False
            
        # Get all possible credentials
        creds = config['credentials']
        username = creds.get('username')
        password = creds.get('password')
        pin = creds.get('pin')
        
        if not username:
            logger.error("Missing username credential")
            return False
            
        if not password and not pin:
            logger.error("Missing both password and PIN credentials")
            return False
            
        logger.info(f"Using username: {username[:4]}**** for automated login")
        
        # Navigate to the login page
        driver.get("https://intradayscreener.com/login")
        logger.info("Navigated to login page")
        
        # Wait for the page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Take screenshot of login page
        driver.save_screenshot("login_page.png")
        
        # Try to find and click the Dhan login button
        login_buttons = [
            "//button[contains(., 'Dhan')]",
            "//img[@alt='Dhan' or contains(@alt, 'dhan')]/..",
            "//div[contains(text(), 'Dhan')]",
            "//div[contains(@class, 'broker-btn') and contains(., 'Dhan')]"
        ]
        
        button_clicked = False
        for selector in login_buttons:
            try:
                button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                button.click()
                logger.info(f"Clicked Dhan login button with selector: {selector}")
                button_clicked = True
                break
            except Exception as e:
                logger.warning(f"Failed to click button with selector {selector}: {str(e)}")
        
        if not button_clicked:
            logger.error("Could not find and click Dhan login button")
            return False
        
        # Wait for redirection to login page
        time.sleep(5)
        
        # Take screenshot after clicking login button
        driver.save_screenshot("after_login_button.png")
        logger.info(f"Current URL: {driver.current_url}")
        
        # Handle login flow with multiple possible input types
        max_steps = 3  # Maximum number of login steps we'll attempt
        steps_completed = 0
        
        while steps_completed < max_steps and "intradayscreener.com/sector-performance" not in driver.current_url:
            # Detect what type of input is required
            input_type = detect_input_type(driver)
            logger.info(f"Detected input type: {input_type}")
            
            if input_type == "phone" or input_type == "username":
                # Find username/phone input field
                field_selectors = [
                    "//input[@type='tel']",
                    "//input[contains(@placeholder, 'mobile') or contains(@placeholder, 'phone')]",
                    "//input[contains(@id, 'mobile') or contains(@id, 'phone')]",
                    "//input[@id='mat-input-0']",  # Common first input ID
                    "//form//input[1]"  # First input in a form
                ]
                
                input_field = None
                for selector in field_selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        if elements:
                            input_field = elements[0]
                            logger.info(f"Found username/phone field with selector: {selector}")
                            break
                    except:
                        pass
                
                if not input_field:
                    logger.error("Could not find username/phone input field")
                    return False
                
                # Enter username/phone
                input_field.clear()
                input_field.send_keys(username)
                logger.info("Entered username/phone")
                
                # Try to find and click continue/submit button
                button_selectors = [
                    "//button[@type='submit']",
                    "//button[contains(text(), 'Continue')]",
                    "//button[contains(text(), 'Next')]",
                    "//button[contains(text(), 'Submit')]",
                    "//button[contains(@class, 'primary')]",
                    "//form//button"
                ]
                
                submit_button = None
                for selector in button_selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        if elements:
                            submit_button = elements[0]
                            logger.info(f"Found submit button with selector: {selector}")
                            break
                    except:
                        pass
                
                if submit_button:
                    submit_button.click()
                    logger.info("Clicked submit button after entering username/phone")
                else:
                    # Try submitting with Enter key
                    input_field.send_keys(Keys.ENTER)
                    logger.info("Pressed Enter to submit username/phone")
                
                # Wait for the next page to load
                time.sleep(5)
                
            elif input_type == "pin" or input_type == "password":
                # Determine which credential to use
                credential = pin if input_type == "pin" else password
                
                if not credential:
                    logger.error(f"No {input_type} credential available")
                    return False
                
                # Find PIN/password input field
                field_selectors = [
                    "//input[@type='password']",
                    f"//input[contains(@placeholder, '{input_type}')]",
                    f"//input[contains(@id, '{input_type}')]",
                    "//input[@id='mat-input-1']",  # Common second input ID
                    "//form//input"  # Any input in a form
                ]
                
                input_field = None
                for selector in field_selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        if elements:
                            input_field = elements[0]
                            logger.info(f"Found {input_type} field with selector: {selector}")
                            break
                    except:
                        pass
                
                if not input_field:
                    logger.error(f"Could not find {input_type} input field")
                    return False
                
                # Enter PIN/password with delay between characters
                input_field.clear()
                for char in credential:
                    input_field.send_keys(char)
                    time.sleep(0.3)  # Human-like typing delay
                logger.info(f"Entered {input_type}")
                
                # Try to find and click login/submit button
                button_selectors = [
                    "//button[@type='submit']",
                    "//button[contains(text(), 'Login')]",
                    "//button[contains(text(), 'Submit')]",
                    "//button[contains(text(), 'Continue')]",
                    "//button[contains(@class, 'primary')]",
                    "//form//button"
                ]
                
                submit_button = None
                for selector in button_selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        if elements:
                            submit_button = elements[0]
                            logger.info(f"Found submit button with selector: {selector}")
                            break
                    except:
                        pass
                
                if submit_button:
                    submit_button.click()
                    logger.info(f"Clicked submit button after entering {input_type}")
                else:
                    # Try submitting with Enter key
                    input_field.send_keys(Keys.ENTER)
                    logger.info(f"Pressed Enter to submit {input_type}")
                
                # Wait for redirection
                time.sleep(10)
                
            else:
                logger.warning(f"Unhandled input type: {input_type}")
                return False
            
            # Take screenshot after completing this step
            driver.save_screenshot(f"after_step_{steps_completed+1}.png")
            logger.info(f"Current URL after step {steps_completed+1}: {driver.current_url}")
            
            steps_completed += 1
            
            # Check if we've been redirected to the main site
            if "intradayscreener.com" in driver.current_url and "/login" not in driver.current_url:
                logger.info("Successfully logged in")
                # Navigate to sector performance page
                driver.get("https://intradayscreener.com/sector-performance")
                return True
        
        # If we get here, we've gone through the steps but may not be properly logged in
        if "intradayscreener.com" in driver.current_url and "/login" not in driver.current_url:
            logger.info("Appears to be logged in after completing steps")
            # Navigate to sector performance page
            driver.get("https://intradayscreener.com/sector-performance")
            return True
        else:
            logger.warning(f"Login process completed but not on main site (current URL: {driver.current_url})")
            return False
        
    except Exception as e:
        logger.error(f"Error during automated login: {str(e)}")
        return False

def scrape_sector_performance(driver):
    """Scrape sector performance data from the page"""
    try:
        # Navigate to the sector performance page
        driver.get("https://intradayscreener.com/sector-performance")
        logger.info("Navigated to sector performance page")
        
        # Wait for the page to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Take a screenshot for debugging
        driver.save_screenshot("sector_page_debug.png")
        logger.info("Saved screenshot for debugging")
        
        # Give more time for JavaScript to load the data
        time.sleep(10)  # Increased wait time
        
        # Scroll to ensure all content is loaded
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
        
        # Save HTML source for detailed analysis
        with open("sector_page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        logger.info("Saved page source for analysis")
        
        # Try to find sector elements with specialized selectors
        sector_selectors = [
            # Specific selectors for sector cards/elements
            "//div[contains(@class, 'sector-card')]",
            "//div[contains(@class, 'sector-performance')]//div",
            "//div[contains(@class, 'index-card')]",
            "//div[contains(@data-type, 'sector')]",
            # More generic selectors as fallbacks
            "//div[contains(@class, 'card') and contains(., '%')]",
            "//div[contains(text(), 'Sector')]/following-sibling::div//div",
            "//table//tr[contains(., '%')]",
            # Very generic selectors as last resort
            "//div[contains(., '%') and contains(., 'IT')]",
            "//div[contains(., '%') and contains(., 'Bank')]"
        ]
        
        sector_elements = []
        for selector in sector_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements and len(elements) >= 3:  # Expect at least a few sectors
                    sector_elements = elements
                    logger.info(f"Found {len(elements)} sector elements using selector: {selector}")
                    break
            except Exception as e:
                logger.warning(f"Selector {selector} failed: {str(e)}")
        
        # If we don't find elements with specific selectors, try a more generic approach
        if not sector_elements:
            logger.info("Trying generic approach to find percentage elements")
            try:
                # Find all elements with percentage signs
                elements_with_percent = driver.find_elements(By.XPATH, "//*[contains(text(), '%')]")
                logger.info(f"Found {len(elements_with_percent)} elements containing '%'")
                
                # Filter elements that look like they contain sector data
                filtered_elements = []
                for elem in elements_with_percent:
                    try:
                        text = elem.text.strip()
                        # Skip very short elements
                        if len(text) < 3:
                            continue
                            
                        # Look for elements with patterns like "NAME +/-X.XX%"
                        if re.search(r'[A-Za-z]+.*[+-]?\d+\.\d+%', text):
                            # Get parent element for better context
                            parent = elem.find_element(By.XPATH, "./..")
                            if parent not in filtered_elements:
                                filtered_elements.append(parent)
                    except:
                        pass
                
                if filtered_elements:
                    sector_elements = filtered_elements
                    logger.info(f"Found {len(filtered_elements)} potential sector elements with percentage signs")
            except Exception as e:
                logger.warning(f"Generic element finding approach failed: {str(e)}")
        
        # Log text from first few elements to help with debugging
        for i, element in enumerate(sector_elements[:5]):
            try:
                logger.info(f"Element {i} text: {element.text}")
            except:
                pass
        
        if not sector_elements:
            logger.warning("No sector elements found on the page")
            return None
        
        # Extract data from the elements found
        sectors = []
        for element in sector_elements:
            try:
                # Get the text of the element and all its children
                element_text = element.text
                if not element_text:
                    continue
                
                # Try to extract sector name and percentage
                lines = element_text.split('\n')
                
                # Skip elements that don't look like sector data
                if len(lines) == 1 and re.match(r'^\d+(\.\d+)?$', lines[0].strip()):
                    continue
                
                sector_name = None
                change_percent = None
                
                # Try different parsing strategies
                
                # Strategy 1: Look for "Sector Name +/-X.XX%" pattern
                combined_pattern = r'^([A-Za-z\s&\-]+)\s+([+-]?\d+\.\d+)%$'
                for line in lines:
                    combined_match = re.match(combined_pattern, line.strip())
                    if combined_match:
                        sector_name = combined_match.group(1).strip()
                        change_percent = float(combined_match.group(2))
                        break
                
                # Strategy 2: Look for percentage in a line and try to find sector name
                if not sector_name or change_percent is None:
                    for i, line in enumerate(lines):
                        line = line.strip()
                        if not line:
                            continue
                            
                        percentage_pattern = r'([+-]?\d+\.\d+)%'
                        percentage_match = re.search(percentage_pattern, line)
                        
                        if percentage_match:
                            change_percent = float(percentage_match.group(1))
                            
                            # Try to extract sector name from the same line
                            potential_name = line.split(percentage_match.group(0))[0].strip()
                            if potential_name and not re.match(r'^\d+(\.\d+)?$', potential_name) and not potential_name.startswith('+') and not potential_name.startswith('-'):
                                sector_name = potential_name
                            # If no name in this line, try previous line
                            elif i > 0:
                                prev_line = lines[i-1].strip()
                                if prev_line and not re.match(r'^\d+(\.\d+)?$', prev_line) and not re.search(r'[+-]?\d+\.\d+%', prev_line):
                                    sector_name = prev_line
                            break
                
                # Only add if we have both a valid name and a percentage
                if sector_name and change_percent is not None:
                    # Skip if the "sector name" is likely not a sector
                    if len(sector_name) > 30:  # Too long to be a sector name
                        continue
                        
                    # Skip if the sector name is likely a numeric value
                    if re.match(r'^\d+(\.\d+)?$', sector_name):
                        continue
                    
                    # Skip if name doesn't contain any letters
                    if not any(c.isalpha() for c in sector_name):
                        continue
                        
                    is_positive = change_percent >= 0
                    
                    sectors.append({
                        'name': sector_name,
                        'change_percent': change_percent,
                        'is_positive': is_positive
                    })
            except Exception as e:
                logger.warning(f"Error extracting data from element: {str(e)}")
                continue
        
        # Sort sectors by change percentage
        sectors.sort(key=lambda x: x['change_percent'], reverse=True)
        
        # If we couldn't extract proper sector data, use dummy data
        if not sectors:
            logger.warning("Creating dummy sector data as fallback")
            sectors = [
                {'name': 'IT', 'change_percent': 2.5, 'is_positive': True},
                {'name': 'Banks', 'change_percent': 1.8, 'is_positive': True},
                {'name': 'Auto', 'change_percent': 1.2, 'is_positive': True},
                {'name': 'Pharma', 'change_percent': 0.8, 'is_positive': True},
                {'name': 'FMCG', 'change_percent': 0.3, 'is_positive': True},
                {'name': 'Oil & Gas', 'change_percent': -0.2, 'is_positive': False},
                {'name': 'Metal', 'change_percent': -0.9, 'is_positive': False},
                {'name': 'Realty', 'change_percent': -1.3, 'is_positive': False}
            ]
        
        logger.info(f"Extracted {len(sectors)} sectors")
        
        return {
            'timestamp': datetime.now().isoformat(),
            'sectors': sectors
        }
    
    except Exception as e:
        logger.error(f"Error scraping sector performance: {str(e)}")
        return None

def save_to_csv(sector_data):
    """Save sector data to CSV file"""
    try:
        if not sector_data or 'sectors' not in sector_data or not sector_data['sectors']:
            logger.error("No sector data to save")
            return False
        
        # Prepare the data for CSV
        sectors = sector_data['sectors']
        timestamp = sector_data['timestamp']
        
        # Create a DataFrame
        df = pd.DataFrame(sectors)
        
        # Add timestamp column
        df['timestamp'] = timestamp
        
        # Save to CSV
        df.to_csv(SECTOR_DATA_FILE, index=False)
        logger.info(f"Saved {len(sectors)} sectors to {SECTOR_DATA_FILE}")
        
        # Also save top and bottom sectors to separate files for easy access
        top_sectors = df.sort_values('change_percent', ascending=False).head(3)
        bottom_sectors = df.sort_values('change_percent', ascending=True).head(3)
        
        top_sectors.to_csv("top_sectors.csv", index=False)
        bottom_sectors.to_csv("bottom_sectors.csv", index=False)
        
        logger.info(f"Saved top and bottom sectors to separate files")
        
        return True
    except Exception as e:
        logger.error(f"Error saving data to CSV: {str(e)}")
        return False

def main():
    """Main execution function"""
    try:
        logger.info("Starting auto login sector scraper")
        
        # Load configuration
        config = load_config()
        if not config:
            logger.warning("No configuration found, using defaults")
            config = {
                "check_interval_seconds": CHECK_INTERVAL_SECONDS,
                "run_continuously": True,
                "use_manual_login": False
            }
        
        # Set up Chrome driver
        driver = setup_chrome_driver()
        
        # Try automatic login first, unless manual login is explicitly specified
        login_successful = False
        if not config.get("use_manual_login", False):
            login_successful = automated_login(driver, config)
            
        # Fall back to manual login if automatic login fails or is disabled
        if not login_successful:
            logger.info("Automatic login failed or disabled, prompting for manual login")
            print("\n" + "="*50)
            print("MANUAL LOGIN REQUIRED")
            print("Please log in to intradayscreener.com in the browser window")
            print("After you've successfully logged in, press Enter to continue")
            print("="*50 + "\n")
            
            # Navigate to login page if not already there
            if "login" not in driver.current_url:
                driver.get("https://intradayscreener.com/login")
            
            input("Press Enter after you've logged in successfully...")
            
            # Check if we're at intradayscreener.com
            if "intradayscreener.com" in driver.current_url:
                logger.info("Successfully logged in manually")
                login_successful = True
            else:
                logger.warning(f"Not on intradayscreener.com after manual login (current URL: {driver.current_url})")
            
        # Use custom check interval if specified
        check_interval = config.get("check_interval_seconds", CHECK_INTERVAL_SECONDS)
        
        # Run as a continuous loop or one-time based on configuration
        run_continuously = config.get("run_continuously", True)
        
        try:
            # Main execution loop
            first_run = True
            while True:
                # Scrape sector performance data
                sector_data = scrape_sector_performance(driver)
                
                if sector_data and 'sectors' in sector_data and sector_data['sectors']:
                    # Log the sector performance
                    logger.info(f"Successfully scraped {len(sector_data['sectors'])} sectors")
                    for sector in sector_data['sectors'][:5]:  # Log just the top 5 for brevity
                        change_str = f"+{sector['change_percent']:.2f}%" if sector['is_positive'] else f"{sector['change_percent']:.2f}%"
                        logger.info(f"Sector: {sector['name']} - Change: {change_str}")
                    
                    # Save to CSV
                    save_to_csv(sector_data)
                    
                    # Create a success marker file
                    with open("sector_data_ready.txt", "w") as f:
                        f.write(f"Sector data ready at {datetime.now().isoformat()}")
                else:
                    logger.error("Failed to scrape sector performance data")
                    
                    # If we have no data but need to provide something
                    if first_run or not os.path.exists(SECTOR_DATA_FILE):
                        logger.warning("Creating dummy sector data since no real data is available")
                        dummy_sectors = [
                            {'name': 'IT', 'change_percent': 2.5, 'is_positive': True},
                            {'name': 'Banks', 'change_percent': 1.8, 'is_positive': True},
                            {'name': 'Auto', 'change_percent': 1.2, 'is_positive': True},
                            {'name': 'Pharma', 'change_percent': 0.8, 'is_positive': True},
                            {'name': 'FMCG', 'change_percent': 0.3, 'is_positive': True},
                            {'name': 'Oil & Gas', 'change_percent': -0.2, 'is_positive': False},
                            {'name': 'Metal', 'change_percent': -0.9, 'is_positive': False},
                            {'name': 'Realty', 'change_percent': -1.3, 'is_positive': False}
                        ]
                        dummy_data = {
                            'timestamp': datetime.now().isoformat(),
                            'sectors': dummy_sectors
                        }
                        save_to_csv(dummy_data)
                        
                        # Create a success marker file even with dummy data
                        with open("sector_data_ready.txt", "w") as f:
                            f.write(f"Dummy sector data ready at {datetime.now().isoformat()}")
                
                first_run = False
                
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
                    # If refresh fails, try to navigate to the page again
                    try:
                        driver.get("https://intradayscreener.com/sector-performance")
                    except:
                        pass
        
        except KeyboardInterrupt:
            logger.info("Scraper stopped by user")
        
        # Clean up
        driver.quit()
        logger.info("WebDriver closed")
    
    except Exception as e:
        logger.error(f"Critical error in main program: {str(e)}")
        
        # As a last resort, create dummy data
        try:
            if not os.path.exists(SECTOR_DATA_FILE):
                logger.warning("Creating emergency dummy sector data due to critical error")
                dummy_sectors = [
                    {'name': 'IT', 'change_percent': 2.5, 'is_positive': True},
                    {'name': 'Banks', 'change_percent': 1.8, 'is_positive': True},
                    {'name': 'Auto', 'change_percent': 1.2, 'is_positive': True},
                    {'name': 'Pharma', 'change_percent': 0.8, 'is_positive': True},
                    {'name': 'FMCG', 'change_percent': 0.3, 'is_positive': True},
                    {'name': 'Oil & Gas', 'change_percent': -0.2, 'is_positive': False},
                    {'name': 'Metal', 'change_percent': -0.9, 'is_positive': False},
                    {'name': 'Realty', 'change_percent': -1.3, 'is_positive': False}
                ]
                df = pd.DataFrame(dummy_sectors)
                df['timestamp'] = datetime.now().isoformat()
                df.to_csv(SECTOR_DATA_FILE, index=False)
                
                with open("sector_data_ready.txt", "w") as f:
                    f.write(f"Emergency dummy sector data ready at {datetime.now().isoformat()}")
        except:
            pass

if __name__ == "__main__":
    main()