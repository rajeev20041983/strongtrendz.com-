# 50 High-Activity NSE Stocks for Ichimoku Trading
STOCKS_50 = [
    # Banking & Financial Services (10 stocks)
    "HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK",
    "BAJFINANCE", "BAJAJFINSV", "HDFCLIFE", "SBILIFE", "INDUSINDBK",
    
    # IT & Technology (8 stocks)
    "TCS", "INFY", "HCLTECH", "WIPRO", "TECHM", 
    "LTI", "MPHASIS", "COFORGE",
    
    # FMCG & Consumer (6 stocks)
    "HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", 
    "DABUR", "MARICO",
    
    # Automotive (5 stocks)
    "MARUTI", "TATAMOTORS", "M&M", "BAJAJ-AUTO", "EICHERMOT",
    
    # Energy & Oil (5 stocks)
    "RELIANCE", "ONGC", "BPCL", "IOCL", "GAIL",
    
    # Metals & Mining (4 stocks)
    "TATASTEEL", "JSWSTEEL", "HINDALCO", "VEDL",
    
    # Pharma (4 stocks)
    "SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB",
    
    # Infrastructure & Utilities (4 stocks)
    "LT", "POWERGRID", "NTPC", "COALINDIA",
    
    # Telecom & Others (4 stocks)
    "BHARTIARTL", "ULTRACEMCO", "ASIANPAINT", "SHREECEM"
]

def print_stock_list():
    print("50 Stocks for Ichimoku Trading:")
    for i, stock in enumerate(STOCKS_50, 1):
        print(f"{i:2d}. {stock}")

if __name__ == "__main__":
    print_stock_list()