import pandas as pd
import datetime
from typing import Optional, Dict, Any
from config import Config


class DataProcessor:
    """Handles data loading, cleaning, and preprocessing"""
    
    def __init__(self):
        self.config = Config()
        self._subscriptions_df: Optional[pd.DataFrame] = None
        self._payments_df: Optional[pd.DataFrame] = None

    def load_subscriptions(self, file_path: str) -> pd.DataFrame:
        """Load and preprocess subscriptions data"""
        df = pd.read_csv(file_path).copy()
        
        # Validate required columns
        self._validate_columns(df)
        
        # Clean and standardize data
        df = self._clean_subscriptions_data(df)
        
        # Apply data fixes
        df = self._apply_data_fixes(df)
        
        # Add new customer
        df = self._add_new_customer(df)
        
        # Create customer ID
        df['cust_id'] = df[self.config.get_column('name')] + '-' + df[self.config.get_column('email')]
        
        # Process datetime columns
        df = self._process_datetime_columns(df)
        
        # Filter by analysis date
        df = self._filter_by_analysis_date(df)
        
        self._subscriptions_df = df
        return df
    
    def load_payments(self) -> pd.DataFrame:
        """Load payments data"""
        if self._payments_df is None:
            self._payments_df = pd.read_csv(self.config.PAYMENTS_FILE)
            self._payments_df['Email'] = self._payments_df['Email'].str.lower()
            self._payments_df['Name'] = self._payments_df['Name'].str.lower()
            self._payments_df['cust_id'] = self._payments_df['Name'] + '-' + self._payments_df['Email']
        
        return self._payments_df


    def _validate_columns(self, df: pd.DataFrame) -> None:
        """Validate that required columns exist"""
        required_columns = [
            self.config.get_column('start_date'),
            self.config.get_column('canceled_date'),
            self.config.get_column('email'),
            self.config.get_column('name'),
            self.config.get_column('status')
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
    
    def _clean_subscriptions_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize subscriptions data"""
        # Convert email and name to lowercase
        df[self.config.get_column('email')] = df[self.config.get_column('email')].str.lower()
        df[self.config.get_column('name')] = df[self.config.get_column('name')].str.lower()
        
        return df
    
    def _apply_data_fixes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply predefined data fixes"""
        for fix in self.config.DATA_FIXES:
            email = fix['email']
            mask = df[self.config.get_column('email')] == email
            
            if 'start_date' in fix and fix['start_date']:
                start_date = datetime.datetime.strptime(fix['start_date'], "%d/%m/%Y")
                df.loc[mask, self.config.get_column('start_date')] = start_date
            
            if 'end_date' in fix and fix['end_date']:
                end_date = datetime.datetime.strptime(fix['end_date'], "%d/%m/%Y")
                # df.loc[mask, self.config.get_column('ended_date')] = end_date
                df.loc[mask, self.config.get_column('canceled_date')] = end_date
            elif 'end_date' in fix and fix['end_date'] is None:
                # df.loc[mask, self.config.get_column('ended_date')] = pd.NaT
                df.loc[mask, self.config.get_column('canceled_date')] = pd.NaT
        
        return df
    
    def _add_new_customer(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add new customer to the dataset"""
        new_customer_data = self.config.NEW_CUSTOMER
        new_customer_row = {
            self.config.get_column('name'): new_customer_data['name'],
            self.config.get_column('email'): new_customer_data['email'],
            self.config.get_column('start_date'): datetime.datetime.strptime(new_customer_data['start_date'], "%d/%m/%Y"),
            #self.config.get_column('ended_date'): pd.NaT,
            self.config.get_column('canceled_date'): pd.NaT,
            self.config.get_column('status'): 'active'
        }
        
        new_customer_df = pd.DataFrame([new_customer_row])
        return pd.concat([df, new_customer_df], ignore_index=True)
    
    def _process_datetime_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process datetime columns"""
        datetime_columns = [
            self.config.get_column('start_date'),
            self.config.get_column('canceled_date'),
            #self.config.get_column('ended_date')
        ]
        
        for col in datetime_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        
        return df
    
    def _filter_by_analysis_date(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter data by maximum analysis date"""
        max_date = datetime.datetime.strptime(self.config.MAX_ANALYSIS_DATE, "%d/%m/%Y")
        
        # Filter start dates
        df = df[df[self.config.get_column('start_date')] <= max_date]
        
        # Filter end dates
        end_columns = [self.config.get_column('canceled_date')]#, self.config.get_column('ended_date')]
        for col in end_columns:
            if col in df.columns:
                df.loc[df[col] > max_date, col] = pd.NaT
        
        return df
    
    def get_subscriptions_df(self) -> pd.DataFrame:
        """Get the processed subscriptions dataframe"""
        if self._subscriptions_df is None:
            raise ValueError("Subscriptions data not loaded. Call load_subscriptions() first.")
        return self._subscriptions_df
    
    def get_payments_df(self) -> pd.DataFrame:
        """Get the payments dataframe"""
        return self.load_payments()
