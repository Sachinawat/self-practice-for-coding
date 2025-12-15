import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

def fetch_stock_data(symbol):
    """Fetch simplified stock data using yfinance"""
    
    print(f"Fetching 10 years of data for {symbol}...")
    ticker = yf.Ticker(symbol)
    
    # Get 10 years of historical data
    df = ticker.history(period="10y")
    
    if df.empty:
        print(f"Error: No data found for {symbol}")
        return None
    
    # Rename columns to lowercase
    df.columns = [col.lower() for col in df.columns]
    
    # Drop dividends and stock splits columns
    columns_to_drop = ['dividends', 'stock splits']
    df = df.drop(columns=[col for col in columns_to_drop if col in df.columns], errors='ignore')
    
    # Add only selected Technical Indicators
    
    # Exponential Moving Averages (keeping only EMA 12, 26, 50)
    df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    # MACD
    df['macd'] = df['ema_12'] - df['ema_26']
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_histogram'] = df['macd'] - df['macd_signal']
    
    # On-Balance Volume (OBV)
    df['obv'] = (df['volume'] * (~df['close'].diff().le(0) * 2 - 1)).cumsum()
    
    # Price range and patterns
    df['price_range'] = df['high'] - df['low']
    df['price_range_pct'] = ((df['high'] - df['low']) / df['close']) * 100
    df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)
    df['lower_shadow'] = df[['open', 'close']].min(axis=1) - df['low']
    df['body'] = abs(df['close'] - df['open'])
    
    # Date features (for seasonality)
    df['year'] = df.index.year
    df['month'] = df.index.month
    df['day'] = df.index.day
    df['day_of_week'] = df.index.dayofweek
    df['day_of_year'] = df.index.dayofyear  # NEW: Day of year (1-365/366)
    df['quarter'] = df.index.quarter
    df['is_month_start'] = df.index.is_month_start.astype(int)
    df['is_month_end'] = df.index.is_month_end.astype(int)
    df['is_quarter_start'] = df.index.is_quarter_start.astype(int)
    df['is_quarter_end'] = df.index.is_quarter_end.astype(int)
    
    # Try to fetch quarterly earnings data
    try:
        print("\nFetching quarterly earnings data...")
        quarterly_earnings = ticker.quarterly_earnings
        
        if quarterly_earnings is not None and not quarterly_earnings.empty:
            # Create a mapping of quarter end dates to earnings
            earnings_dict = {}
            
            for idx, row in quarterly_earnings.iterrows():
                # Convert index to datetime if it's not already
                if isinstance(idx, str):
                    quarter_date = pd.to_datetime(idx)
                else:
                    quarter_date = idx
                
                earnings_dict[quarter_date] = {
                    'revenue': row.get('Revenue', np.nan),
                    'earnings': row.get('Earnings', np.nan)
                }
            
            # Add columns for quarterly results
            df['quarterly_revenue'] = np.nan
            df['quarterly_earnings'] = np.nan
            df['days_since_result'] = np.nan
            df['days_to_next_result'] = np.nan
            
            # Map earnings to the dataframe based on proximity to announcement dates
            for quarter_date, earnings in earnings_dict.items():
                # Find the closest date in the dataframe (within 5 days)
                mask = (df.index >= quarter_date - pd.Timedelta(days=5)) & \
                       (df.index <= quarter_date + pd.Timedelta(days=30))
                
                df.loc[mask, 'quarterly_revenue'] = earnings['revenue']
                df.loc[mask, 'quarterly_earnings'] = earnings['earnings']
            
            # Forward fill the quarterly results to apply to all days in that quarter
            df['quarterly_revenue'] = df['quarterly_revenue'].fillna(method='ffill')
            df['quarterly_earnings'] = df['quarterly_earnings'].fillna(method='ffill')
            
            # Calculate days since last result and days to next result
            result_dates = sorted(earnings_dict.keys())
            for i, date in enumerate(df.index):
                # Find days since last result
                past_results = [rd for rd in result_dates if rd <= date]
                if past_results:
                    df.loc[date, 'days_since_result'] = (date - max(past_results)).days
                
                # Find days to next result
                future_results = [rd for rd in result_dates if rd > date]
                if future_results:
                    df.loc[date, 'days_to_next_result'] = (min(future_results) - date).days
            
            print(f"✓ Added quarterly earnings data ({len(earnings_dict)} quarters)")
            print(f"  - Revenue range: {df['quarterly_revenue'].min():.2e} to {df['quarterly_revenue'].max():.2e}")
            print(f"  - Earnings range: {df['quarterly_earnings'].min():.2e} to {df['quarterly_earnings'].max():.2e}")
        else:
            print("✗ No quarterly earnings data available")
            df['quarterly_revenue'] = np.nan
            df['quarterly_earnings'] = np.nan
            df['days_since_result'] = np.nan
            df['days_to_next_result'] = np.nan
            
    except Exception as e:
        print(f"✗ Error fetching quarterly earnings: {str(e)}")
        df['quarterly_revenue'] = np.nan
        df['quarterly_earnings'] = np.nan
        df['days_since_result'] = np.nan
        df['days_to_next_result'] = np.nan
    
    return df

def main():
    symbol = "TCS.NS"  # TCS stock symbol on NSE
    
    # Fetch data
    df = fetch_stock_data(symbol)
    
    if df is not None:
        # Save to CSV
        filename = f"{symbol.split('.')[0]}_10yr_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(filename)
        
        print(f"\n✓ Data saved to {filename}")
        print(f"✓ Total records: {len(df)}")
        print(f"✓ Date range: {df.index.min().strftime('%Y-%m-%d')} to {df.index.max().strftime('%Y-%m-%d')}")
        print(f"✓ Total columns: {len(df.columns)}")
        
        print(f"\nColumns ({len(df.columns)}):")
        print(", ".join(df.columns))
        
        # Display first few rows
        print("\nFirst 5 rows:")
        print(df.head())
        
        # Display basic statistics
        print("\nBasic Statistics:")
        print(df[['open', 'high', 'low', 'close', 'volume']].describe())
        
        # Check for missing values
        print(f"\nMissing values per column:")
        missing_counts = df.isnull().sum()
        print(missing_counts[missing_counts > 0])
        print(f"\nTotal missing values: {df.isnull().sum().sum()}")
        print(f"(Note: Some NaN values are expected for indicators at the start and quarterly data)")
    else:
        print("Failed to fetch data")

if __name__ == "__main__":
    main()