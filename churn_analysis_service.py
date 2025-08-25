import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pandas.tseries.offsets as offsets

from config import Config
from models import MonthlyMetrics, ChurnAnalysisResult, Customer
from filters import FilterChain


class ChurnAnalysisService:
    """Service for computing churn analysis metrics"""
    
    def __init__(self, end_column: str = None):
        self.config = Config()
        self.end_column = end_column or self.config.get_column('canceled_date')
        self._subscriptions_df: Optional[pd.DataFrame] = None
        self._monthly_payments_df: Optional[pd.DataFrame] = None
        self._filter_chain: Optional[FilterChain] = None
        
    def set_data(self, 
                 subscriptions_df: pd.DataFrame, 
                 monthly_payments_df: pd.DataFrame) -> 'ChurnAnalysisService':
        """Set the data for analysis"""
        self._subscriptions_df = subscriptions_df.copy()
        self._monthly_payments_df = monthly_payments_df.copy()
        return self
    
    def set_filters(self, filter_chain: FilterChain) -> 'ChurnAnalysisService':
        """Set the filters to apply to the data"""
        self._filter_chain = filter_chain
        return self
    
    def compute_monthly_churn_summary(self, 
                                    from_month: Optional[pd.Period] = None,
                                    to_month: Optional[pd.Period] = None) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Compute monthly churn summary metrics
        
        Returns:
            Tuple of (summary_dataframe, revenue_by_month)
        """
        if self._subscriptions_df is None:
            raise ValueError("No subscriptions data set. Call set_data() first.")
        
        # Apply filters
        filtered_df = self._apply_filters()
        
        # Get monthly ranges and counts
        starts, cancellations, all_months = self._get_monthly_counts(filtered_df, from_month, to_month)
        
        # Calculate active customers per month
        actives_per_month = self._calculate_active_customers(filtered_df, all_months)
        
        # Build summary dataframe
        summary_df = pd.DataFrame({
            'Month': starts.index,
            'Starts': starts.values,
            'Cancellations': cancellations.values,
            'Actives': actives_per_month,
        })
        
        # Calculate churn rate
        summary_df['Churn_Rate'] = summary_df['Cancellations'] / summary_df['Actives']
        
        # Calculate revenue metrics
        avg_monthly_rev, rev_by_month = self._calculate_revenue_metrics()
        
        # Sort by month
        summary_df = summary_df.sort_values('Month')
        
        return summary_df, rev_by_month
    
    def compute_churned_revenue(self, 
                               canceled_customers: Dict,
                               billing_timing: str = "in_advance") -> Tuple[float, pd.DataFrame]:
        """
        Compute Recurring Revenue Lost (RRL) due to churn
        
        Args:
            canceled_customers: Dictionary mapping months to customer dataframes
            billing_timing: "in_advance" or "in_arrears"
        
        Returns:
            Tuple of (total_rrl, rrl_by_month_dataframe)
        """
        if self._monthly_payments_df is None:
            raise ValueError("No monthly payments data set. Call set_data() first.")
        
        # Build cancellation records
        cancel_records = self._build_cancellation_records(canceled_customers)
        
        if cancel_records.empty:
            return 0.0, pd.DataFrame(columns=["loss_month", "churned_rrl"])
        
        # Join with monthly payments data
        cancel_records = self._join_with_monthly_payments(cancel_records)
        
        # Calculate revenue loss by month
        rrl_by_month = self._calculate_revenue_loss_by_month(cancel_records, billing_timing)
        
        total_rrl = float(rrl_by_month["churned_rrl"].sum())
        
        return total_rrl, rrl_by_month
    
    def get_customer_data_by_month(self, 
                                  filtered_df: pd.DataFrame, 
                                  all_months: pd.PeriodIndex) -> Tuple[Dict, Dict]:
        """Get customer data organized by month"""
        started_customers = {}
        canceled_customers = {}
        
        for month in all_months:
            # Customers who started this month
            start_mask = filtered_df['start_month'] == month
            started_customers[month] = filtered_df[start_mask][
                ['start_month', self.config.get_column('email'), 
                 self.config.get_column('name'), 'cust_id']
            ]
            
            # Customers who canceled this month
            cancel_mask = filtered_df['cancel_month'] == month
            canceled_customers[month] = filtered_df[cancel_mask][
                ['cancel_month', self.config.get_column('email'), 
                 self.config.get_column('name'), 'cust_id']
            ]
        
        return started_customers, canceled_customers
    
    def _apply_filters(self) -> pd.DataFrame:
        """Apply filters to the subscriptions data"""
        if self._filter_chain is None:
            return self._subscriptions_df
        
        return self._filter_chain.apply(self._subscriptions_df)
    
    def _get_monthly_counts(self, 
                           df: pd.DataFrame, 
                           from_month: Optional[pd.Period] = None,
                           to_month: Optional[pd.Period] = None) -> Tuple[pd.Series, pd.Series, pd.PeriodIndex]:
        """Get monthly start and cancellation counts"""
        # Convert to monthly periods
        df['start_month'] = df[self.config.get_column('start_date')].dt.to_period('M')
        df['cancel_month'] = df[self.end_column].dt.to_period('M')
        
        # Determine analysis range
        min_month = df['start_month'].min()
        max_month = pd.concat([df['start_month'].dropna(), df['cancel_month'].dropna()]).max()
        
        if from_month is None:
            from_month = min_month
        if to_month is None:
            to_month = max_month
        
        # Create month range
        all_months = pd.period_range(from_month, to_month, freq='M')
        
        # Count starts and cancellations by month
        starts = df['start_month'].value_counts().reindex(all_months, fill_value=0)
        cancellations = df['cancel_month'].value_counts().reindex(all_months, fill_value=0)
        
        return starts, cancellations, all_months
    
    def _calculate_active_customers(self, 
                                   df: pd.DataFrame, 
                                   all_months: pd.PeriodIndex) -> List[int]:
        """Calculate active customers at the start of each month"""
        actives_per_month = []
        
        for month in all_months:
            # Customers active at start of month
            active_mask = (
                (df[self.config.get_column('start_date')] <= month.start_time) &
                ((df[self.end_column] >= month.start_time) | pd.isna(df[self.end_column]))
            )
            actives_per_month.append(active_mask.sum())
        
        return actives_per_month
    
    def _calculate_revenue_metrics(self) -> Tuple[float, pd.Series]:
        """Calculate revenue metrics from monthly payments data"""
        if self._monthly_payments_df is None:
            return 0.0, pd.Series()
        
        revenue_by_month = self._monthly_payments_df.groupby('month')['monthly_price'].sum()
        avg_monthly_revenue = revenue_by_month.mean()
        
        return avg_monthly_revenue, revenue_by_month
    
    def _build_cancellation_records(self, canceled_customers: Dict) -> pd.DataFrame:
        """Build cancellation records from customer data"""
        cancel_rows = []
        
        for month, customers_df in canceled_customers.items():
            month_timestamp = month.to_timestamp()
            
            for _, row in customers_df.iterrows():
                cancel_rows.append({
                    'cust_id': row['cust_id'],
                    'cancel_month': month_timestamp
                })
        
        return pd.DataFrame(cancel_rows)
    
    def _join_with_monthly_payments(self, cancel_records: pd.DataFrame) -> pd.DataFrame:
        """Join cancellation records with monthly payments data"""
        monthly_data = self._monthly_payments_df[['cust_id', 'month', 'monthly_price']].copy()
        
        # Join and filter to months up to cancellation
        joined = cancel_records.merge(monthly_data, on='cust_id', how='left')
        joined = joined[joined['month'] <= joined['cancel_month']]
        
        if joined.empty:
            return joined
        
        # Get last known price before cancellation
        joined = joined.sort_values(['cust_id', 'cancel_month', 'month'])
        last_price = joined.groupby(['cust_id', 'cancel_month'], as_index=False).tail(1)
        
        return last_price[['cust_id', 'cancel_month', 'monthly_price']]
    
    def _calculate_revenue_loss_by_month(self, 
                                        cancel_records: pd.DataFrame, 
                                        billing_timing: str) -> pd.DataFrame:
        """Calculate revenue loss by month based on billing timing"""
        if cancel_records.empty:
            return pd.DataFrame(columns=["loss_month", "churned_rrl"])
        
        # Determine which month gets the revenue loss
        if billing_timing == "in_advance":
            # Customers pay at beginning of month -> loss affects next month
            cancel_records["loss_month"] = (
                cancel_records["cancel_month"] + offsets.MonthBegin(1)
            )
        elif billing_timing == "in_arrears":
            # Billed at end of month -> loss affects same month
            cancel_records["loss_month"] = cancel_records["cancel_month"]
        else:
            raise ValueError("billing_timing must be 'in_advance' or 'in_arrears'")
        
        # Aggregate by loss month
        rrl_by_month = (
            cancel_records.groupby("loss_month")["monthly_price"]
            .sum()
            .rename("churned_rrl")
            .reset_index()
            .sort_values("loss_month")
        )
        
        # Convert to period for consistency
        rrl_by_month["loss_month"] = (
            rrl_by_month["loss_month"].dt.to_period('M').dt.to_timestamp()
        )
        
        return rrl_by_month
    
    def get_analysis_summary(self) -> Dict:
        """Get summary of the analysis configuration and data"""
        return {
            'end_column': self.end_column,
            'total_subscriptions': len(self._subscriptions_df) if self._subscriptions_df is not None else 0,
            'total_monthly_records': len(self._monthly_payments_df) if self._monthly_payments_df is not None else 0,
            'active_filters': self._filter_chain.get_active_filters() if self._filter_chain else [],
            'analysis_date_range': {
                'start': self._subscriptions_df[self.config.get_column('start_date')].min() if self._subscriptions_df is not None else None,
                'end': self._subscriptions_df[self.end_column].max() if self._subscriptions_df is not None else None
            } if self._subscriptions_df is not None else None
        }

