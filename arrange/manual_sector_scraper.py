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

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("tradingview_scraper.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

def scrape_tradingview_sectors():
    """Scrape sector performance data from TradingView using direct XPath selectors"""
    url = "https://www.tradingview.com/markets/stocks-india/sectorandindustry-sector/"
    
    logger.info("Setting up Chrome driver...")
    chrome_options = Options()
    #chrome_options.add_argument("--headless")  # Comment this out to see the browser
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36")
    
    try:
        # Use ChromeDriverManager to handle driver installation
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        
        logger.info(f"Navigating to {url}")
        driver.get(url)
        
        # Wait for page to load completely
        logger.info("Waiting for page to load...")
        time.sleep(15)  # Give plenty of time for JavaScript to execute
        
        # Take a screenshot to see what's loaded
        driver.save_screenshot("tradingview_screen.png")
        logger.info("Saved screenshot to tradingview_screen.png")
        
        # Get sector data using direct XPath
        sector_data = []
        
        # Direct approach: find all rows in the first table
        # The table structure should be consistent with columns for sector name and change %
        rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
        logger.info(f"Found {len(rows)} rows in table")
        
        for row in rows:
            try:
                # Get all cells in this row
                cells = row.find_elements(By.TAG_NAME, "td")
                
                if len(cells) >= 4:  # Need at least 4 columns to get sector and change%
                    sector_name = cells[0].text.strip()
                    
                    # The Change % column should be column index 3 (0-indexed)
                    change_cell = cells[3]
                    change_text = change_cell.text.strip()
                    
                    logger.info(f"Row data: {sector_name} | {change_text}")
                    
                    if '%' in change_text:
                        # Determine if positive or negative
                        is_positive = not ('-' in change_text)
                        
                        # Extract numeric value
                        change_value = float(change_text.replace('%', '').replace('+', '').replace('−', '-'))
                        
                        sector_data.append({
                            'sector': sector_name,
                            'sector_percent_change': change_value,
                            'is_positive': is_positive
                        })
                        
                        logger.info(f"Added sector: {sector_name}, Change: {change_value}%")
            except Exception as e:
                logger.error(f"Error processing row: {str(e)}")
        
        # Close browser
        driver.quit()
        
        if not sector_data:
            logger.error("No sector data found in the table")
            return None
            
        # Create DataFrame
        df = pd.DataFrame(sector_data)
        
        # Add timestamp and placeholder for advancing/declining stocks
        df['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        df['advancing'] = 0
        df['declining'] = 0
        
        # Sort by performance
        df = df.sort_values('sector_percent_change', ascending=False)
        
        # Log results
        logger.info(f"Successfully scraped data for {len(df)} sectors")
        for _, row in df.iterrows():
            sign = "+" if row['is_positive'] else ""
            logger.info(f"  {row['sector']}: {sign}{row['sector_percent_change']}%")
            
        return df
        
    except Exception as e:
        logger.error(f"Error during scraping: {str(e)}")
        if 'driver' in locals():
            driver.quit()
        return None

def main():
    """Main function"""
    logger.info("Starting TradingView sector data scraper")
    
    df = scrape_tradingview_sectors()
    
    if df is not None:
        # Save to CSV
        df.to_csv("sector.csv", index=False)
        logger.info("Saved sector data to sector.csv")
    else:
        logger.error("Failed to scrape sector data")

if __name__ == "__main__":
    main()