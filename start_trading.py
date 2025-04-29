import subprocess
import sys
import os

def run_script(script_name):
    """Run a Python script in a separate process"""
    python_executable = sys.executable
    script_path = os.path.join(os.getcwd(), script_name)
    
    try:
        process = subprocess.Popen([python_executable, script_path], 
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   text=True,
                                   bufsize=1)
        
        # Return the process so we can read output later
        return process
    except Exception as e:
        print(f"Error starting {script_name}: {str(e)}")
        return None

def main():
    """Run both the scraper and trader scripts"""
    print("Starting Sector Analysis and Trading System...")
    
    # Start both scripts
    scraper_process = run_script("nuvama_scraper.py")
    trader_process = run_script("dhan_sector_trader.py")
    
    if not scraper_process or not trader_process:
        print("Failed to start one or both scripts.")
        return
    
    print("Both scripts are running!")
    print("Press Ctrl+C to stop both programs.")
    
    try:
        # Monitor output from both processes
        while True:
            # Check and display output from scraper
            scraper_output = scraper_process.stdout.readline()
            if scraper_output:
                print(f"[SCRAPER] {scraper_output.strip()}")
                
            # Check and display output from trader
            trader_output = trader_process.stdout.readline()
            if trader_output:
                print(f"[TRADER] {trader_output.strip()}")
                
            # Check if either process has ended
            if scraper_process.poll() is not None:
                print("Scraper process has ended.")
                break
                
            if trader_process.poll() is not None:
                print("Trader process has ended.")
                break
    
    except KeyboardInterrupt:
        print("Stopping both scripts...")
        # Try to terminate both processes gracefully
        scraper_process.terminate()
        trader_process.terminate()
    
    print("Done.")

if __name__ == "__main__":
    main()