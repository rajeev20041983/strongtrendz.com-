# app/services/sector_analyzer.py

import os
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict
from app import config

class SectorAnalyzer:
    """
    Analyzes stocks by sector with focus on ARIMA and LSTM agreement
    """
    def __init__(self, market_analyzer=None, output_dir=None):
        """
        Initialize the sector analyzer
        
        Parameters:
        - market_analyzer: MarketAnalysisService instance for stock analysis
        - output_dir: Directory to save reports
        """
        self.market_analyzer = market_analyzer
        self.output_dir = output_dir
        self.sector_mapping = config.SECTOR_MAPPING
    
    def get_stock_sector(self, ticker):
        """Get the sector for a given stock ticker"""
        return self.sector_mapping.get(ticker, "UNKNOWN")
    
    def models_agree(self, arima_change, lstm_change):
        """
        Check if ARIMA and LSTM models agree on direction
        
        Parameters:
        - arima_change: Percentage change predicted by ARIMA
        - lstm_change: Percentage change predicted by LSTM
        
        Returns:
        - Boolean indicating whether models agree
        """
        # Both models must have valid predictions
        if arima_change is None or lstm_change is None:
            return False
            
        # Check if both are positive or both are negative
        return (arima_change > 0 and lstm_change > 0) or (arima_change < 0 and lstm_change < 0)
    
    def calculate_combined_prediction(self, arima_pred, lstm_pred):
        """Calculate combined prediction from ARIMA and LSTM models"""
        if arima_pred is not None and lstm_pred is not None:
            return (arima_pred + lstm_pred) / 2
        elif arima_pred is not None:
            return arima_pred
        elif lstm_pred is not None:
            return lstm_pred
        else:
            return None
    
    def get_recommendation(self, combined_change):
        """Get recommendation based on combined percentage change"""
        if combined_change is None:
            return "UNKNOWN"
            
        if combined_change > 3.0:
            return "STRONG BUY"
        elif combined_change > 1.0:
            return "BUY"
        elif combined_change > -1.0:
            return "HOLD"
        elif combined_change > -3.0:
            return "SELL"
        else:
            return "STRONG SELL"
    
    def calculate_confidence(self, arima_change, lstm_change):
        """
        Calculate confidence score based on model agreement and magnitude
        
        Parameters:
        - arima_change: Percentage change predicted by ARIMA
        - lstm_change: Percentage change predicted by LSTM
        
        Returns:
        - Confidence score (0-100)
        """
        # Start with a base confidence
        base_confidence = 70.0
        
        # Adjust for model agreement
        if self.models_agree(arima_change, lstm_change):
            base_confidence += 15.0
        else:
            base_confidence -= 10.0
        
        # Adjust for magnitude of prediction (avg of absolute changes)
        if arima_change is not None and lstm_change is not None:
            avg_magnitude = (abs(arima_change) + abs(lstm_change)) / 2
            
            if avg_magnitude > 5.0:
                base_confidence += 10.0
            elif avg_magnitude > 3.0:
                base_confidence += 5.0
            elif avg_magnitude < 1.0:
                base_confidence -= 5.0
        
        # Cap confidence between 40 and 95
        return max(min(base_confidence, 95.0), 40.0)
    
    def analyze_sectors(self, stock_results):
        """
        Analyze stocks grouped by sectors
        
        Parameters:
        - stock_results: List of stock analysis dictionaries
        
        Returns:
        - Dictionary with sector-based analysis
        """
        # Add sector to each result
        for result in stock_results:
            ticker = result.get('ticker', '')
            result['sector'] = self.get_stock_sector(ticker)
        
        # Group by sector
        sector_groups = defaultdict(list)
        for result in stock_results:
            sector = result.get('sector', 'UNKNOWN')
            sector_groups[sector].append(result)
        
        # Calculate sector averages for ARIMA-LSTM combined predictions
        sector_averages = {}
        for sector, stocks in sector_groups.items():
            # Filter to stocks with valid ARIMA and LSTM predictions
            valid_stocks = []
            for stock in stocks:
                arima_pred = stock.get('arima_prediction')
                lstm_pred = stock.get('lstm_prediction')
                current_price = stock.get('current_price')
                
                if arima_pred is not None and lstm_pred is not None and current_price is not None:
                    # Calculate combined prediction
                    combined_pred = self.calculate_combined_prediction(arima_pred, lstm_pred)
                    combined_change = ((combined_pred - current_price) / current_price) * 100
                    
                    # Add to stock data
                    stock['combined_prediction'] = combined_pred
                    stock['combined_change_pct'] = combined_change
                    
                    # Check if models agree
                    arima_change = ((arima_pred - current_price) / current_price) * 100
                    lstm_change = ((lstm_pred - current_price) / current_price) * 100
                    stock['arima_change_pct'] = arima_change
                    stock['lstm_change_pct'] = lstm_change
                    stock['models_agree'] = self.models_agree(arima_change, lstm_change)
                    
                    # Add to valid stocks
                    valid_stocks.append(stock)
            
            # Calculate sector average if we have valid stocks
            if valid_stocks:
                total_change = sum(stock['combined_change_pct'] for stock in valid_stocks)
                sector_averages[sector] = total_change / len(valid_stocks)
            else:
                sector_averages[sector] = 0.0
        
        # Update stock data with sector comparison
        for sector, stocks in sector_groups.items():
            sector_avg = sector_averages.get(sector, 0.0)
            
            for stock in stocks:
                if 'combined_change_pct' in stock:
                    # Calculate relative performance vs sector
                    stock['sector_avg_change'] = sector_avg
                    stock['relative_to_sector'] = stock['combined_change_pct'] - sector_avg
                    
                    # Set recommendation based on combined prediction
                    stock['recommendation'] = self.get_recommendation(stock['combined_change_pct'])
                    
                    # Calculate confidence
                    stock['confidence'] = self.calculate_confidence(
                        stock.get('arima_change_pct'), 
                        stock.get('lstm_change_pct')
                    )
        
        return {
            'sector_groups': dict(sector_groups),
            'sector_averages': sector_averages
        }
    
    def generate_agreement_report(self, stock_results):
        """
        Generate report focused on stocks where ARIMA and LSTM agree
        
        Parameters:
        - stock_results: List of stock analysis dictionaries
        
        Returns:
        - Dictionary with filtered results and recommendations
        """
        # Analyze sectors first
        sector_analysis = self.analyze_sectors(stock_results)
        
        # Flatten all stocks for filtering
        all_stocks = []
        for stocks in sector_analysis['sector_groups'].values():
            all_stocks.extend(stocks)
        
        # Filter for stocks where ARIMA and LSTM agree
        agreement_stocks = [
            stock for stock in all_stocks 
            if stock.get('models_agree', False) and 'combined_change_pct' in stock
        ]
        
        # Sort stocks by combined change percentage
        sorted_buy = sorted(
            [s for s in agreement_stocks if s.get('combined_change_pct', 0) > 0],
            key=lambda x: x.get('combined_change_pct', 0),
            reverse=True
        )
        
        sorted_sell = sorted(
            [s for s in agreement_stocks if s.get('combined_change_pct', 0) <= 0],
            key=lambda x: x.get('combined_change_pct', 0)
        )
        
        # Get top recommendations
        top_buy = sorted_buy[:10] if len(sorted_buy) > 10 else sorted_buy
        top_sell = sorted_sell[:10] if len(sorted_sell) > 10 else sorted_sell
        
        # Calculate sectoral performance
        sector_performance = []
        for sector, avg_change in sector_analysis['sector_averages'].items():
            direction = "UP" if avg_change > 0 else "DOWN"
            color = "GREEN" if avg_change > 0 else "RED"
            
            sector_performance.append({
                'sector': sector,
                'avg_change': avg_change,
                'direction': direction,
                'color': color
            })
        
        # Sort sectors by performance
        sorted_sectors = sorted(
            sector_performance,
            key=lambda x: x['avg_change'],
            reverse=True
        )
        
        return {
            'agreement_stocks': agreement_stocks,
            'top_buy': top_buy,
            'top_sell': top_sell,
            'sector_performance': sorted_sectors,
            'sector_averages': sector_analysis['sector_averages']
        }
    
    def save_report_csv(self, report_data, filename=None):
        """
        Save report to CSV
        
        Parameters:
        - report_data: Dictionary with report data
        - filename: Optional custom filename, defaults to timestamped name
        
        Returns:
        - Path to saved CSV file
        """
        # Create a timestamp for the filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"arima_lstm_agreement_{timestamp}.csv"
        
        # Ensure output directory exists
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)
            filepath = os.path.join(self.output_dir, filename)
        else:
            filepath = filename
        
        # Create a DataFrame from agreement stocks
        df = pd.DataFrame(report_data['agreement_stocks'])
        
        # Save to CSV
        df.to_csv(filepath, index=False)
        
        logging.info(f"Saved agreement report to {filepath}")
        return filepath
    
    def save_top_picks_csv(self, report_data, filename=None):
        """
        Save top buy/sell recommendations to CSV
        
        Parameters:
        - report_data: Dictionary with report data
        - filename: Optional custom filename, defaults to timestamped name
        
        Returns:
        - Path to saved CSV file
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"top_picks_{timestamp}.csv"
        
        # Ensure output directory exists
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)
            filepath = os.path.join(self.output_dir, filename)
        else:
            filepath = filename
        
        # Combine top buy and sell with a category column
        top_buy = pd.DataFrame(report_data['top_buy'])
        if not top_buy.empty:
            top_buy['category'] = 'BUY'
        
        top_sell = pd.DataFrame(report_data['top_sell'])
        if not top_sell.empty:
            top_sell['category'] = 'SELL'
        
        # Combine dataframes
        if not top_buy.empty and not top_sell.empty:
            combined_df = pd.concat([top_buy, top_sell])
        elif not top_buy.empty:
            combined_df = top_buy
        elif not top_sell.empty:
            combined_df = top_sell
        else:
            combined_df = pd.DataFrame()
        
        # Save to CSV if we have data
        if not combined_df.empty:
            combined_df.to_csv(filepath, index=False)
            logging.info(f"Saved top picks to {filepath}")
            return filepath
        else:
            logging.warning("No top picks data to save")
            return None
    
    def save_sector_performance_csv(self, report_data, filename=None):
        """
        Save sector performance to CSV with format optimized for Power BI
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"sector_performance_{timestamp}.csv"
        
        # Ensure output directory exists
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)
            filepath = os.path.join(self.output_dir, filename)
        else:
            filepath = filename
        
        # Create DataFrame with columns for Power BI
        sectors = []
        performances = []
        directions = []
        
        for sector_info in report_data['sector_performance']:
            sectors.append(sector_info['sector'])
            performances.append(sector_info['avg_change'])
            directions.append("UP" if sector_info['avg_change'] > 0 else "DOWN")
        
        df = pd.DataFrame({
            'Sector': sectors,
            'Performance': performances,
            'Direction': directions
        })
        
        # Sort by performance (descending)
        df = df.sort_values(by='Performance', ascending=False)
        
        # Save to CSV
        df.to_csv(filepath, index=False)
        logging.info(f"Saved sector performance to {filepath}")
        return filepath