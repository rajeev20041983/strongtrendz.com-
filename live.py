import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

class InsideBarRSIStrategy:
    def __init__(self, rsi_length=14, ma_length=65, n_bars=1, rsi_oversold=30, rsi_overbought=70):
        self.rsi_length = rsi_length
        self.ma_length = ma_length
        self.n_bars = n_bars
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
    
    def calculate_rsi(self, prices, period=14):
        """Calculate RSI exactly like Pine Script"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, 0.001)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)
    
    def detect_inside_bar(self, data, n_bars=1):
        """Exact Pine Script Inside Bar detection logic"""
        if len(data) < n_bars + 1:
            return False, 0, 0
        
        high = data['High']
        low = data['Low']
        
        current_high = high.iloc[-1]
        current_low = low.iloc[-1]
        
        if n_bars >= 1:
            high_1 = high.iloc[-2]
            low_1 = low.iloc[-2]
            inside_1_bar = current_high < high_1 and current_low > low_1
            if n_bars == 1:
                return inside_1_bar, high_1, low_1
            if not inside_1_bar:
                return False, 0, 0
        
        if n_bars >= 2:
            high_2 = high.iloc[-3]
            low_2 = low.iloc[-3]
            inside_2_bar = current_high < high_2 and current_low > low_2 and inside_1_bar
            if n_bars == 2:
                return inside_2_bar, high_2, low_2
            if not inside_2_bar:
                return False, 0, 0
        
        if n_bars >= 3:
            high_3 = high.iloc[-4]
            low_3 = low.iloc[-4]
            inside_3_bar = current_high < high_3 and current_low > low_3 and inside_1_bar and inside_2_bar
            if n_bars == 3:
                return inside_3_bar, high_3, low_3
            if not inside_3_bar:
                return False, 0, 0
        
        if n_bars == 4:
            high_4 = high.iloc[-5]
            low_4 = low.iloc[-5]
            inside_4_bar = current_high < high_4 and current_low > low_4 and inside_1_bar and inside_2_bar and inside_3_bar
            return inside_4_bar, high_4, low_4
        
        return False, 0, 0
    
    def detect_rsi_divergence(self, data, lookback_periods=[2,3,4,5]):
        """Detect RSI bullish divergence like Pine Script"""
        if len(data) < 50:
            return False, False, None
        
        rsi = self.calculate_rsi(data['Close'])
        low_prices = data['Low']
        
        # Check for bullish divergence in multiple lookback periods
        for lookback in lookback_periods:
            if len(data) < lookback + 10:
                continue
                
            try:
                # Find pivot lows in RSI and price
                current_rsi = rsi.iloc[-1]
                current_low = low_prices.iloc[-1]
                
                past_rsi = rsi.iloc[-(lookback+1)]
                past_low = low_prices.iloc[-(lookback+1)]
                
                # Bullish divergence: Price makes lower low, RSI makes higher low
                price_lower_low = current_low < past_low
                rsi_higher_low = current_rsi > past_rsi
                
                # Check if RSI was oversold recently
                recent_rsi_min = rsi.iloc[-lookback:].min()
                rsi_was_oversold = recent_rsi_min < self.rsi_oversold
                
                if price_lower_low and rsi_higher_low and rsi_was_oversold and current_rsi < self.rsi_overbought:
                    return True, False, lookback  # Regular bullish divergence
                
                # Hidden bullish divergence: Price makes higher low, RSI makes lower low
                price_higher_low = current_low > past_low
                rsi_lower_low = current_rsi < past_rsi
                
                if price_higher_low and rsi_lower_low and rsi_was_oversold and current_rsi < self.rsi_overbought:
                    return False, True, lookback  # Hidden bullish divergence
                    
            except (IndexError, ValueError):
                continue
        
        return False, False, None
    
    def analyze_stock(self, ticker, period="6mo", interval="1d"):
        """Analyze a single stock for Inside Bar + RSI patterns"""
        try:
            # Get stock data
            stock = yf.Ticker(f"{ticker}.NS")
            data = stock.history(period=period, interval=interval)
            
            if len(data) < 100:
                return None
            
            # Calculate indicators
            rsi = self.calculate_rsi(data['Close'], self.rsi_length)
            sma = data['Close'].rolling(window=self.ma_length).mean()
            
            current_price = data['Close'].iloc[-1]
            current_rsi = rsi.iloc[-1]
            current_sma = sma.iloc[-1]
            
            # Check Inside Bar pattern
            inside_bar_detected, ib_high, ib_low = self.detect_inside_bar(data, self.n_bars)
            
            if not inside_bar_detected:
                return None
            
            # Current bar type
            current_open = data['Open'].iloc[-1]
            current_close = data['Close'].iloc[-1]
            bull_bar = current_close > current_open
            bear_bar = current_close < current_open
            
            # MA trend filter
            ma_trend_up = current_price > current_sma
            
            # RSI Divergence detection
            bull_div, hidden_bull_div, div_lookback = self.detect_rsi_divergence(data)
            
            # Entry conditions (Pine Script logic)
            long_condition = (inside_bar_detected and bull_bar and ma_trend_up)
            short_condition = (inside_bar_detected and bear_bar and not ma_trend_up)
            
            # Signal strength based on multiple confirmations
            signal_strength = 0
            signal_type = "HOLD"
            entry_reason = []
            
            if long_condition:
                signal_strength = 60
                signal_type = "BUY"
                entry_reason.append("Inside Bar + Bull Bar + MA Up")
                
                # Add RSI divergence boost
                if bull_div:
                    signal_strength += 25
                    signal_type = "STRONG_BUY"
                    entry_reason.append(f"RSI Bull Divergence (LB:{div_lookback})")
                elif hidden_bull_div:
                    signal_strength += 15
                    entry_reason.append(f"RSI Hidden Bull Div (LB:{div_lookback})")
                
                # Oversold RSI boost
                if current_rsi < self.rsi_oversold:
                    signal_strength += 10
                    entry_reason.append("RSI Oversold")
                
            elif short_condition:
                signal_strength = 60
                signal_type = "SELL"
                entry_reason.append("Inside Bar + Bear Bar + MA Down")
                
                # Overbought RSI boost
                if current_rsi > self.rsi_overbought:
                    signal_strength += 10
                    entry_reason.append("RSI Overbought")
            
            # Calculate targets and stops
            ib_range = ib_high - ib_low
            
            if signal_type in ["BUY", "STRONG_BUY"]:
                entry_price = current_price
                stop_loss = ib_low * 0.998  # Pine Script style with small buffer
                target_price = entry_price + (ib_range * 2)  # 2:1 risk reward
                
            elif signal_type == "SELL":
                entry_price = current_price
                stop_loss = ib_high * 1.002
                target_price = entry_price - (ib_range * 2)
            else:
                entry_price = stop_loss = target_price = current_price
            
            return {
                'ticker': ticker,
                'signal_type': signal_type,
                'signal_strength': round(signal_strength, 1),
                'current_price': round(current_price, 2),
                'entry_price': round(entry_price, 2),
                'target_price': round(target_price, 2),
                'stop_loss': round(stop_loss, 2),
                'entry_reason': " | ".join(entry_reason),
                
                # Inside Bar data
                'inside_bar_detected': inside_bar_detected,
                'inside_bar_high': round(ib_high, 2),
                'inside_bar_low': round(ib_low, 2),
                'inside_bar_range': round(ib_range, 2),
                'current_bull_bar': bull_bar,
                'current_bear_bar': bear_bar,
                
                # RSI data
                'rsi': round(current_rsi, 1),
                'rsi_bullish_divergence': bull_div,
                'rsi_hidden_bull_divergence': hidden_bull_div,
                'rsi_divergence_lookback': div_lookback,
                'rsi_oversold': current_rsi < self.rsi_oversold,
                'rsi_overbought': current_rsi > self.rsi_overbought,
                
                # Technical data
                'ma_trend': 'UP' if ma_trend_up else 'DOWN',
                'sma_value': round(current_sma, 2),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            print(f"Error analyzing {ticker}: {e}")
            return None

def run_inside_bar_rsi_scanner():
    """Run the Inside Bar + RSI scanner on Indian stocks"""
    
    # Extended list of Indian stock symbols (100+ stocks)
    indian_stocks = [
        # Nifty 50
        'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'HINDUNILVR', 'ICICIBANK', 
        'KOTAKBANK', 'ITC', 'LT', 'SBIN', 'BHARTIARTL', 'ASIANPAINT',
        'MARUTI', 'AXISBANK', 'BAJFINANCE', 'WIPRO', 'NESTLEIND', 
        'ULTRACEMCO', 'TITAN', 'POWERGRID', 'TATAMOTORS', 'ADANIPORTS',
        'COALINDIA', 'NTPC', 'DIVISLAB', 'TECHM', 'HCLTECH', 'SUNPHARMA',
        'BAJAJFINSV', 'JSWSTEEL', 'APOLLOHOSP', 'CIPLA', 'GRASIM',
        'HINDALCO', 'INDUSINDBK', 'BRITANNIA', 'EICHERMOT', 'UPL',
        'DRREDDY', 'BPCL', 'TATASTEEL', 'HEROMOTOCO', 'SHREECEM',
        'BAJAJ-AUTO', 'TATACONSUM', 'ONGC', 'M&M', 'IOC',
        
        # Mid & Small Cap Popular stocks
        'ADANIENT', 'ADANIGREEN', 'ADANITRANS', 'GODREJCP', 'PIDILITIND',
        'DABUR', 'MARICO', 'COLPAL', 'MCDOWELL-N', 'AMBUJACEM',
        'ACC', 'VEDL', 'SAIL', 'NMDC', 'BHEL', 'RECLTD', 'PFC',
        'BANKBARODA', 'PNB', 'CANBK', 'IOCL', 'GAIL', 'HINDPETRO',
        'RELINFRA', 'RPOWER', 'SUZLON', 'YESBANK', 'IDEA', 'MOTHERSON',
        'ESCORTS', 'ASHOKLEY', 'TVSMOTOR', 'BAJAJHLDNG', 'SIEMENS',
        'ABB', 'HAVELLS', 'CROMPTON', 'VOLTAS', 'BLUESTAR', 'WHIRLPOOL',
        'GODREJIND', 'CUMMINSIND', 'BOSCHLTD', 'EXIDEIND', 'AMARON',
        'PAGEIND', 'HINDWARE', 'RAJESHEXPO', 'PCJEWELLER', 'GITANJALI',
        
        # Banking & Financial
        'HDFCLIFE', 'ICICIGI', 'SBILIFE', 'LICHSGFIN', 'BAJAJHFL',
        'CHOLAFIN', 'PEL', 'MUTHOOTFIN', 'MANAPPURAM', 'FEDERALBNK',
        'IDFCFIRSTB', 'RBLBANK', 'BANDHANBNK', 'AUBANK', 'EQUITAS',
        
        # IT & Tech
        'MINDTREE', 'MPHASIS', 'LTTS', 'COFORGE', 'PERSISTENT',
        'KPITTECH', 'RANEENGINE', 'SONATSOFTW', 'CYIENT', 'LTIM'
    ]
    
    strategy = InsideBarRSIStrategy(
        rsi_length=14,
        ma_length=65,
        n_bars=1,
        rsi_oversold=30,
        rsi_overbought=70
    )
    
    print("="*150)
    print("INSIDE BAR + RSI DIVERGENCE STRATEGY SCANNER")
    print("="*150)
    print(f"Scanning {len(indian_stocks)} Indian stocks...")
    print(f"Inside Bar Pattern: {strategy.n_bars} bar(s) | RSI Length: {strategy.rsi_length} | MA Length: {strategy.ma_length}")
    print("-"*150)
    
    results = []
    signals_found = 0
    
    for ticker in indian_stocks:
        result = strategy.analyze_stock(ticker, period="6mo", interval="1d")
        if result and result['signal_type'] != 'HOLD':
            results.append(result)
            signals_found += 1
            
            # Print signal details
            print(f"\n{ticker} - {result['signal_type']} (Strength: {result['signal_strength']})")
            print(f"  Price: ₹{result['current_price']} | Entry: ₹{result['entry_price']} | Target: ₹{result['target_price']} | SL: ₹{result['stop_loss']}")
            print(f"  Inside Bar: High=₹{result['inside_bar_high']}, Low=₹{result['inside_bar_low']}, Range=₹{result['inside_bar_range']}")
            print(f"  RSI: {result['rsi']} | Bull Div: {result['rsi_bullish_divergence']} | Hidden Div: {result['rsi_hidden_bull_divergence']}")
            if result['rsi_divergence_lookback']:
                print(f"  RSI Divergence Lookback: {result['rsi_divergence_lookback']} periods")
            print(f"  MA Trend: {result['ma_trend']} | Current Bar: {'Bull' if result['current_bull_bar'] else 'Bear'}")
            print(f"  Reason: {result['entry_reason']}")
        else:
            print(f"{ticker}: No signal")
    
    print("\n" + "="*150)
    print(f"SCAN COMPLETE: Found {signals_found} signals out of {len(indian_stocks)} stocks")
    
    if signals_found > 0:
        strong_signals = [r for r in results if r['signal_type'] == 'STRONG_BUY']
        rsi_div_signals = [r for r in results if r['rsi_bullish_divergence'] or r['rsi_hidden_bull_divergence']]
        
        print(f"Strong Buy Signals: {len(strong_signals)}")
        print(f"RSI Divergence Signals: {len(rsi_div_signals)}")
        
        # Show top signals
        results.sort(key=lambda x: x['signal_strength'], reverse=True)
        print(f"\nTOP SIGNALS:")
        for i, result in enumerate(results[:5], 1):
            rsi_status = ""
            if result['rsi_bullish_divergence']:
                rsi_status = " + RSI BULL DIV"
            elif result['rsi_hidden_bull_divergence']:
                rsi_status = " + RSI HIDDEN BULL"
            elif result['rsi_oversold']:
                rsi_status = " + RSI OVERSOLD"
            elif result['rsi_overbought']:
                rsi_status = " + RSI OVERBOUGHT"
                
            print(f"{i}. {result['ticker']} - {result['signal_type']} ({result['signal_strength']}){rsi_status}")
    
    print("="*150)
    return results

# Run the scanner
if __name__ == "__main__":
    signals = run_inside_bar_rsi_scanner()