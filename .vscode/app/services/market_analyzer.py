# app/services/market_analyzer.py

import os
import math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import warnings
import traceback
from datetime import datetime
import yfinance as yf

# Time Series Models
from statsmodels.tsa.arima.model import ARIMA

# Machine Learning Models
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import MinMaxScaler

# Deep Learning (LSTM)
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM, Dropout

# Suppress Warnings
warnings.filterwarnings("ignore")
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow warnings

class MarketAnalysisService:
    def __init__(self, output_dir='.'):
        self.output_dir = output_dir
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'plots'), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'data'), exist_ok=True)
    
    def get_historical_data(self, ticker, years=2):
        """
        Download historical data for the given ticker
        """
        print(f"Downloading historical data for {ticker}...")
        
        # Define date range
        end = datetime.now()
        start = datetime(end.year-years, end.month, end.day)
        
        # Download data
        data = yf.download(ticker, start=start, end=end)
        
        # Save to CSV
        csv_path = os.path.join(self.output_dir, 'data', f"{ticker}.csv")
        data.to_csv(csv_path)
        
        print(f"Data saved to {csv_path}")
        return data
    
    def run_arima_model(self, df, ticker):
        """ARIMA model implementation"""
        print("\n===== RUNNING ARIMA MODEL =====")
            
        try:
            # Prepare data
            data = df.copy()
            data['Price'] = data['Close']
                
            # Create Quantity_date DataFrame
            Quantity_date = pd.DataFrame()
            Quantity_date['Price'] = data['Price']
            Quantity_date.index = data.index
                
            # Make sure price is float
            Quantity_date['Price'] = Quantity_date['Price'].astype(float)
            Quantity_date = Quantity_date.fillna(Quantity_date.bfill())
                
            # Plot trends
            fig = plt.figure(figsize=(7.2,4.8), dpi=65)
            plt.plot(Quantity_date)
            plt.title(f'{ticker} Price Trends')
            plt.xlabel('Date')
            plt.ylabel('Price')
            plt.savefig(os.path.join(self.output_dir, 'plots', f'{ticker}_price_trends.png'))
            plt.close(fig)
                
            # Prepare training data
            quantity = Quantity_date.values
            size = int(len(quantity) * 0.80)
            train, test = quantity[0:size], quantity[size:len(quantity)]
                
            # Create prediction function
            def arima_model(train, test):
                history = [float(x) for x in train]
                predictions = []
                for t in range(len(test)):
                    model = ARIMA(history, order=(6,1,0))
                    model_fit = model.fit()
                    output = model_fit.forecast()
                    yhat = float(output[0])
                    predictions.append(yhat)
                    obs = float(test[t])
                    history.append(obs)
                return predictions
                
            # Make predictions
            predictions = arima_model(train, test)
                
            # Plot predictions
            fig = plt.figure(figsize=(7.2,4.8), dpi=65)
            plt.plot(test, label='Actual Price')
            plt.plot(predictions, label='Predicted Price')
            plt.title(f'{ticker} ARIMA Prediction')
            plt.xlabel('Time Steps')
            plt.ylabel('Price')
            plt.legend(loc=4)
            plt.savefig(os.path.join(self.output_dir, 'plots', f'{ticker}_arima_prediction.png'))
            plt.close(fig)
                
            # Get prediction and error
            arima_pred = predictions[-2] if len(predictions) > 1 else predictions[-1]
            error_arima = math.sqrt(mean_squared_error(test, predictions))
                
            print(f"Tomorrow's {ticker} Closing Price Prediction by ARIMA: {arima_pred:.2f}")
            print(f"ARIMA RMSE: {error_arima:.2f}")
                
            return arima_pred, error_arima
                
        except Exception as e:
            print(f"Error in ARIMA model: {str(e)}")
            import traceback
            traceback.print_exc()
            return None, None
        
    def run_lstm_model(self, df, ticker):
        """LSTM model implementation"""
        print("\n===== RUNNING LSTM MODEL =====")
        
        try:
            # Split data
            dataset_train = df.iloc[0:int(0.8*len(df)), :]
            dataset_test = df.iloc[int(0.8*len(df)):, :]
            
            # Prepare training data
            training_set = df.iloc[:, df.columns.get_loc('Close')].values.reshape(-1, 1)
            
            # Feature Scaling
            sc = MinMaxScaler(feature_range=(0, 1))
            training_set_scaled = sc.fit_transform(training_set)
            
            # Create sequences with 7 timesteps
            X_train = []
            y_train = []
            for i in range(7, len(training_set_scaled)):
                X_train.append(training_set_scaled[i-7:i, 0])
                y_train.append(training_set_scaled[i, 0])
            
            X_train = np.array(X_train)
            y_train = np.array(y_train)
            
            # Reshape for LSTM
            X_train = np.reshape(X_train, (X_train.shape[0], X_train.shape[1], 1))
            
            # Build LSTM
            model = Sequential()
            model.add(LSTM(units=50, return_sequences=True, input_shape=(7, 1)))
            model.add(Dropout(0.1))
            model.add(LSTM(units=50, return_sequences=True))
            model.add(Dropout(0.1))
            model.add(LSTM(units=50, return_sequences=True))
            model.add(Dropout(0.1))
            model.add(LSTM(units=50))
            model.add(Dropout(0.1))
            model.add(Dense(units=1))
            
            model.compile(optimizer='adam', loss='mean_squared_error')
            print("Training LSTM model...")
            model.fit(X_train, y_train, epochs=25, batch_size=32, verbose=0)
            
            # Prepare test data
            test_set = df.iloc[int(0.8*len(df)):, df.columns.get_loc('Close')].values.reshape(-1, 1)
            total_dataset = pd.concat((
                dataset_train['Close'],
                dataset_test['Close']), axis=0)
            test_inputs = total_dataset[len(total_dataset)-len(test_set)-7:].values.reshape(-1, 1)
            test_inputs = sc.transform(test_inputs)
            
            # Create test sequences
            X_test = []
            for i in range(7, len(test_inputs)):
                X_test.append(test_inputs[i-7:i, 0])
            X_test = np.array(X_test)
            X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))
            
            # Predict
            pred_price = model.predict(X_test)
            pred_price = sc.inverse_transform(pred_price)
            
            # Plot results
            plt.figure(figsize=(7.2,4.8), dpi=65)
            plt.plot(test_set, label='Actual Price')
            plt.plot(pred_price, label='Predicted Price')
            plt.title(f'{ticker} LSTM Prediction')
            plt.xlabel('Time Steps')
            plt.ylabel('Price')
            plt.legend(loc=4)
            plt.savefig(os.path.join(self.output_dir, 'plots', f'{ticker}_lstm_prediction.png'))
            plt.close()
            
            # Calculate error
            error_lstm = math.sqrt(mean_squared_error(test_set, pred_price))
            
            # Predict next day
            last_7_days = training_set_scaled[-7:].reshape((1, 7, 1))
            next_day = model.predict(last_7_days)
            lstm_pred = float(sc.inverse_transform(next_day)[0, 0])
            
            print(f"Tomorrow's {ticker} Closing Price Prediction by LSTM: {lstm_pred:.2f}")
            print(f"LSTM RMSE: {error_lstm:.2f}")
            
            return lstm_pred, error_lstm
            
        except Exception as e:
            print(f"Error in LSTM model: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None, None

    def calculate_arima_lstm_confidence(self, arima_pred, lstm_pred, current_price):
        """
        Calculate confidence and recommendation based on combined ARIMA and LSTM predictions
        """
        print("\n===== COMBINED ARIMA-LSTM RECOMMENDATION =====")
        
        # Check if we have valid predictions
        if arima_pred is None or lstm_pred is None or current_price is None:
            return {
                "combined_recommendation": "UNKNOWN",
                "combined_confidence": 0.0,
                "combined_explanation": "Insufficient prediction data",
                "combined_change_pct": None,
                "combined_price": None,
                "models_agree": False
            }
        
        # Calculate percentage changes from current price
        arima_change = ((arima_pred - current_price) / current_price) * 100
        lstm_change = ((lstm_pred - current_price) / current_price) * 100
        
        # Calculate weighted mean prediction (equal weights)
        mean_pred = (arima_pred + lstm_pred) / 2
        mean_change = ((mean_pred - current_price) / current_price) * 100
        
        # Define thresholds for recommendations
        strong_buy_threshold = 3.0    # >3% increase
        buy_threshold = 1.0           # 1-3% increase
        hold_upper_threshold = 1.0    # -1% to 1% change (hold zone)
        hold_lower_threshold = -1.0   
        sell_threshold = -3.0         # -1% to -3% decrease
                                    # <-3% decrease (strong sell)
        
        # Determine base recommendation and confidence from mean prediction
        if mean_change > strong_buy_threshold:
            base_recommendation = "STRONG BUY"
            base_confidence = 85.0
            explanation = f"Combined models predict a significant {mean_change:.2f}% price increase"
        elif mean_change > buy_threshold:
            base_recommendation = "BUY"
            base_confidence = 75.0
            explanation = f"Combined models predict a moderate {mean_change:.2f}% price increase"
        elif mean_change > hold_lower_threshold and mean_change < hold_upper_threshold:
            base_recommendation = "HOLD"
            base_confidence = 70.0
            explanation = f"Combined models predict relatively stable price (change: {mean_change:.2f}%)"
        elif mean_change > sell_threshold:
            base_recommendation = "SELL"
            base_confidence = 75.0
            explanation = f"Combined models predict a moderate {abs(mean_change):.2f}% price decrease"
        else:
            base_recommendation = "STRONG SELL"
            base_confidence = 85.0
            explanation = f"Combined models predict a significant {abs(mean_change):.2f}% price decrease"
        
        # Check if models agree on direction
        models_agree = (arima_change > 0 and lstm_change > 0) or (arima_change < 0 and lstm_change < 0)
        
        # Adjust confidence based on model agreement
        agreement_adjustment = 0
        if models_agree:
            agreement_adjustment = 10.0
            explanation += f" (ARIMA: {arima_change:.2f}%, LSTM: {lstm_change:.2f}% - both models agree on direction)"
        else:
            agreement_adjustment = -5.0
            explanation += f" (ARIMA: {arima_change:.2f}%, LSTM: {lstm_change:.2f}% - models disagree on direction)"
        
        # Calculate final confidence (cap at 95%)
        final_confidence = min(base_confidence + agreement_adjustment, 95.0)
        
        # Print combined recommendation summary
        print(f"ARIMA Prediction: ₹{arima_pred:.2f} (Change: {arima_change:.2f}%)")
        print(f"LSTM Prediction: ₹{lstm_pred:.2f} (Change: {lstm_change:.2f}%)")
        print(f"Combined Mean Prediction: ₹{mean_pred:.2f} (Change: {mean_change:.2f}%)")
        print(f"Combined Recommendation: {base_recommendation}")
        print(f"Combined Confidence: {final_confidence:.1f}%")
        print(f"Models Agree: {'Yes' if models_agree else 'No'}")
        print(f"Explanation: {explanation}")
        
        # Return combined results with additional data needed for sector analysis
        return {
            "combined_recommendation": base_recommendation,
            "combined_confidence": final_confidence,
            "combined_explanation": explanation,
            "combined_change_pct": mean_change,
            "combined_price": mean_pred,
            "models_agree": models_agree,
            "arima_change_pct": arima_change,
            "lstm_change_pct": lstm_change
        }

    def analyze_stock(self, ticker, company_name=None):
        """
        Perform comprehensive analysis of a stock with focus on ARIMA-LSTM agreement
        """
        print(f"\n{'='*80}")
        print(f"STARTING ANALYSIS FOR {ticker}")
        print(f"{'='*80}")
        
        if company_name is None:
            company_name = ticker.replace('.NS', '')
        
        try:
            # Get historical data
            df = self.get_historical_data(ticker)
            
            # Check if dataframe is empty
            if df.empty:
                print(f"No data available for {ticker}. Skipping analysis.")
                return {
                    'ticker': ticker,
                    'company_name': company_name,
                    'current_price': None,
                    'arima_prediction': None,
                    'lstm_prediction': None,
                    'recommendation': "UNKNOWN",
                    'confidence': 0
                }
            
            # Display current stock info
            latest_data = df.iloc[-1]
            date_str = latest_data.name.strftime('%Y-%m-%d') if hasattr(latest_data.name, 'strftime') else str(latest_data.name)
            
            print(f"\nLatest Stock Data ({date_str}):")
            print(f"Open: {float(latest_data['Open']):.2f}")
            print(f"High: {float(latest_data['High']):.2f}")
            print(f"Low: {float(latest_data['Low']):.2f}")
            print(f"Close: {float(latest_data['Close']):.2f}")
            print(f"Volume: {int(latest_data['Volume'])}")
            
            # Run ARIMA and LSTM models
            arima_pred, error_arima = self.run_arima_model(df, ticker)
            lstm_pred, error_lstm = self.run_lstm_model(df, ticker)
            
            # Ensure we have numeric values, use None if models failed
            arima_pred = float(arima_pred) if arima_pred is not None else None
            lstm_pred = float(lstm_pred) if lstm_pred is not None else None
            error_arima = float(error_arima) if error_arima is not None else float('inf')
            error_lstm = float(error_lstm) if error_lstm is not None else float('inf')
            
            # Get current price
            current_price = float(latest_data['Close'])
            
            # Calculate ARIMA-LSTM combined information
            if arima_pred is not None and lstm_pred is not None:
                combined_info = self.calculate_arima_lstm_confidence(arima_pred, lstm_pred, current_price)
                recommendation = combined_info["combined_recommendation"]
                confidence = combined_info["combined_confidence"]
                explanation = combined_info["combined_explanation"]
                models_agree = combined_info["models_agree"]
                combined_change_pct = combined_info["combined_change_pct"]
                combined_pred = combined_info["combined_price"]
            else:
                # Default values if we don't have both ARIMA and LSTM predictions
                combined_pred = None
                combined_change_pct = None
                recommendation = "UNKNOWN"
                confidence = 0.0
                explanation = "Insufficient model predictions"
                models_agree = False
            
            # Final summary with safe formatting
            print(f"\n{'='*80}")
            print(f"ANALYSIS SUMMARY FOR {ticker} ({company_name})")
            print(f"{'='*80}")
            print(f"Current Price: {current_price:.2f}")
            
            if arima_pred is not None:
                arima_change = ((arima_pred - current_price) / current_price) * 100
                print(f"ARIMA Prediction: {arima_pred:.2f} ({arima_change:.2f}%)")
            else:
                print(f"ARIMA Prediction: N/A")
                arima_change = None
            
            if lstm_pred is not None:
                lstm_change = ((lstm_pred - current_price) / current_price) * 100
                print(f"LSTM Prediction: {lstm_pred:.2f} ({lstm_change:.2f}%)")
            else:
                print(f"LSTM Prediction: N/A")
                lstm_change = None
            
            if combined_pred is not None:
                print(f"Combined ARIMA-LSTM Prediction: {combined_pred:.2f} ({combined_change_pct:.2f}%)")
            
            print(f"Recommendation: {recommendation}")
            print(f"Confidence: {confidence:.1f}%")
            print(f"Models Agree: {'Yes' if models_agree else 'No'}")
            print(f"Explanation: {explanation}")
            print(f"{'='*80}")
            
            # Return results with consistent types and focused on ARIMA-LSTM agreement
            return {
                'ticker': ticker,
                'company_name': company_name,
                'current_price': current_price,
                'arima_prediction': arima_pred,
                'lstm_prediction': lstm_pred,
                'combined_prediction': combined_pred,
                'recommendation': recommendation,
                'confidence': confidence,
                'arima_error': error_arima if error_arima != float('inf') else None,
                'lstm_error': error_lstm if error_lstm != float('inf') else None,
                'arima_change_pct': arima_change,
                'lstm_change_pct': lstm_change,
                'combined_change_pct': combined_change_pct,
                'combined_explanation': explanation,
                'models_agree': models_agree
            }

        except Exception as e:
            print(f"Error during analysis of {ticker}: {str(e)}")
            import traceback
            traceback.print_exc()  # Add full traceback for better debugging
            return {
                'ticker': ticker,
                'company_name': company_name,
                'current_price': None,
                'arima_prediction': None,
                'lstm_prediction': None,
                'combined_prediction': None,
                'recommendation': "ERROR",
                'confidence': 0,
                'error': str(e)
            }