import time
import pandas as pd
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import schedule
import sys
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("nuvama_scraper.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

def scrape_nuvama_sectors():
    """Scrape sector performance data from Nuvama Wealth"""
    url = "https://www.nuvamawealth.com/market/stock-market-index/#key-indices"
    
    logger.info("Setting up Chrome driver...")
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # Comment this out to see the browser
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
        
        # Sort by performance
        df = df.sort_values('sector_percent_change', ascending=False)
        
        # Print a clean output with only sectors and their change% with symbols
        print("\nNUVAMA SECTOR CHANGE%:")
        print("---------------------")
        for _, row in df.iterrows():
            symbol = "+" if row['is_positive'] else "-"
            # Don't show negative sign twice for negative values
            value = abs(row['sector_percent_change'])
            print(f"{row['sector']}: {symbol}{value:.2f}%")
            
        return df
        
    except Exception as e:
        logger.error(f"Error during scraping: {str(e)}")
        if 'driver' in locals():
            driver.quit()
        return None

def run_scraper():
    """Execute the scraper and save results to sector.csv"""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f"Running Nuvama sector data scraper job at {current_time}")
    
    df = scrape_nuvama_sectors()
    
    if df is not None:
        # Save to CSV - overwrites the existing file
        df.to_csv("sector.csv", index=False)
        logger.info("Saved sector data to sector.csv")
        
        # Print simplified output again as a summary
        print(f"\nSUMMARY - NUVAMA SECTOR CHANGE% ({current_time}):")
        print("------------------------------")
        for _, row in df.iterrows():
            symbol = "+" if row['is_positive'] else "-"
            value = abs(row['sector_percent_change'])
            print(f"{row['sector']}: {symbol}{value:.2f}%")
    else:
        logger.error("Failed to scrape sector data")

def main():
    """Main function with scheduling"""
    logger.info("Starting Nuvama sector data scraper with 30-minute refresh")
    
    # Run immediately on startup
    run_scraper()
    
    # Schedule to run every 1 minute
    schedule.every(1).minutes.do(run_scraper)
    
    # Keep the script running and execute scheduled jobs
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Scraper stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error in main loop: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()