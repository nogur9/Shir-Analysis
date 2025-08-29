import pandas as pd
from typing import Dict, Optional, Tuple
from config import Config


class RevenueAnalysisService:
    """Service for computing revenue analysis metrics"""
    
    def __init__(self, end_column: str = None):
        self.config = Config()
        self.end_column = end_column or self.config.get_column('canceled_date')
        self._subscriptions_df: Optional[pd.DataFrame] = None
        self._monthly_payments_df: Optional[pd.DataFrame] = None

    def set_data(self, 
                 subscriptions_df: pd.DataFrame, 
                 monthly_payments_df: pd.DataFrame) -> 'RevenueAnalysisService':
        """Set the data for analysis"""
        self._subscriptions_df = subscriptions_df.copy()
        self._monthly_payments_df = monthly_payments_df.copy()
        return self

    
    def compute_monthly_revenue(self) -> Tuple[float, pd.Series]:
        """
        Compute monthly revenue metrics
        
        Returns:
            Tuple of (average_monthly_revenue, revenue_by_month_series)
        """
        if self._monthly_payments_df is None:
            raise ValueError("No monthly payments data set. Call set_data() first.")


        # Calculate revenue by month
        revenue_by_month = self._monthly_payments_df.groupby('month')['monthly_price'].sum()
        
        # Calculate average monthly revenue
        avg_monthly_revenue = revenue_by_month.mean()
        
        return avg_monthly_revenue, revenue_by_month
    
    def compute_churned_revenue(self, 
                               canceled_customers: Dict) -> Tuple[float, pd.DataFrame]:
        """
        Compute churned revenue as the sum of each churned customer's average monthly spend.
        Assign loss to the customer's cancellation month.
        
        Args:
            canceled_customers: Dictionary mapping pd.Period('M') -> dataframe of customers (must include 'cust_id')
        Returns:
            Tuple of (total_churned_revenue, dataframe with columns ['loss_month','churned_rrl'])
        """
        if self._monthly_payments_df is None:
            raise ValueError("No monthly payments data set. Call set_data() first.")
        
        # Precompute each customer's average monthly spend
        last_idx = self._monthly_payments_df.groupby('cust_id')['month'].idxmax()
        last_payments = self._monthly_payments_df.loc[last_idx, ['cust_id', 'month', 'monthly_price']]

        rows = []
        for month_period, customers_df in canceled_customers.items():
            if customers_df is None or customers_df.empty:
                continue
            cust_ids = customers_df['cust_id'].dropna().unique()
            # Map to average; missing customers default to 0
            churned_values = last_payments[last_payments['cust_id'].isin(cust_ids)]['monthly_price']
            month_total = float(churned_values.sum())
            rows.append({
                'loss_month': month_period.to_timestamp(),
                'churned_rrl': month_total
            })
        
        rrl_by_month = pd.DataFrame(rows)
        if rrl_by_month.empty:
            return 0.0, pd.DataFrame(columns=["loss_month", "churned_rrl"])
        
        rrl_by_month = rrl_by_month.groupby('loss_month', as_index=False)['churned_rrl'].sum().sort_values('loss_month')
        total_rrl = float(rrl_by_month['churned_rrl'].sum())
        return total_rrl, rrl_by_month
    
    def compute_total_revenue(self) -> float:
        """
        Compute total revenue across all customers and months
        
        Returns:
            Total revenue amount
        """
        if self._monthly_payments_df is None:
            raise ValueError("No monthly payments data set. Call set_data() first.")
        
        total_revenue = self._monthly_payments_df['monthly_price'].sum()
        
        return float(total_revenue)
    
    def compute_revenue_by_lesson_type(self) -> Dict[str, Dict]:
        """
        Compute revenue metrics grouped by lesson type
        
        Returns:
            Dictionary with lesson type as key and revenue metrics as value
        """
        if self._monthly_payments_df is None:
            raise ValueError("No monthly payments data set. Call set_data() first.")

        # Group by lesson type and calculate metrics
        lesson_type_revenue = self._monthly_payments_df.groupby('lesson_type').agg({
            'monthly_price': ['sum', 'mean', 'count'],
            'cust_id': 'nunique'
        }).round(2)
        
        # Flatten column names
        lesson_type_revenue.columns = ['total_revenue', 'avg_monthly_price', 'total_payments', 'unique_customers']
        
        # Convert to dictionary format
        result = {}
        for lesson_type, metrics in lesson_type_revenue.iterrows():
            result[lesson_type] = {
                'total_revenue': float(metrics['total_revenue']),
                'average_monthly_price': float(metrics['avg_monthly_price']),
                'total_payments': int(metrics['total_payments']),
                'unique_customers': int(metrics['unique_customers'])
            }
        
        return result
    
    def compute_revenue_by_duration(self) -> Dict[str, Dict]:
        """
        Compute revenue metrics grouped by subscription duration
        
        Returns:
            Dictionary with duration as key and revenue metrics as value
        """
        if self._monthly_payments_df is None:
            raise ValueError("No monthly payments data set. Call set_data() first.")

        # Group by duration and calculate metrics
        duration_revenue = self._monthly_payments_df.groupby('duration_months').agg({
            'monthly_price': ['sum', 'mean', 'count'],
            'cust_id': 'nunique'
        }).round(2)
        
        # Flatten column names
        duration_revenue.columns = ['total_revenue', 'avg_monthly_price', 'total_payments', 'unique_customers']
        
        # Convert to dictionary format
        result = {}
        for duration, metrics in duration_revenue.iterrows():
            result[f"{duration}_months"] = {
                'total_revenue': float(metrics['total_revenue']),
                'average_monthly_price': float(metrics['avg_monthly_price']),
                'total_payments': int(metrics['total_payments']),
                'unique_customers': int(metrics['unique_customers'])
            }
        
        return result
    
    def compute_customer_lifetime_value(self, customer_id: str) -> Dict[str, float]:
        """
        Compute lifetime value metrics for a specific customer
        
        Args:
            customer_id: Customer ID to analyze
            
        Returns:
            Dictionary with LTV metrics
        """
        if self._monthly_payments_df is None:
            raise ValueError("No monthly payments data set. Call set_data() first.")

        # Filter to specific customer
        customer_data = self._monthly_payments_df[self._monthly_payments_df['cust_id'] == customer_id]
        
        if customer_data.empty:
            return {
                'total_revenue': 0.0,
                'average_monthly_revenue': 0.0,
                'total_months': 0,
                'total_payments': 0
            }
        
        total_revenue = customer_data['monthly_price'].sum()
        total_months = len(customer_data)
        avg_monthly_revenue = total_revenue / total_months if total_months > 0 else 0.0
        
        return {
            'total_revenue': float(total_revenue),
            'average_monthly_revenue': float(avg_monthly_revenue),
            'total_months': total_months,
            'total_payments': len(customer_data)
        }
    
    def get_revenue_summary(self, monthly_pay_df: Optional[pd.DataFrame] = None) -> Dict[str, any]:
        """
        Get comprehensive revenue summary
        
        Returns:
            Dictionary with complete revenue overview
        """
        if self._monthly_payments_df is None:
            return {}
        if monthly_pay_df is None:
            monthly_pay_df =  self._monthly_payments_df.copy()

        # Basic revenue metrics
        total_revenue = monthly_pay_df['monthly_price'].sum()
        avg_monthly_revenue = monthly_pay_df['monthly_price'].mean()
        total_customers = monthly_pay_df['cust_id'].nunique()
        total_months = monthly_pay_df['month'].nunique()
        
        # Revenue distribution
        revenue_by_month = monthly_pay_df.groupby('month')['monthly_price'].sum()
        revenue_range = {
            'min': float(revenue_by_month.min()),
            'max': float(revenue_by_month.max()),
            'std': float(revenue_by_month.std())
        }

        # Lesson type distribution
        lesson_type_distribution = monthly_pay_df['lesson_type'].value_counts().to_dict()

        # Duration distribution
        duration_distribution = monthly_pay_df['duration_months'].value_counts().to_dict()
        
        return {
            'total_revenue': float(total_revenue),
            'average_monthly_revenue': float(avg_monthly_revenue),
            'total_customers': int(total_customers),
            'total_months': int(total_months),
            'revenue_range': revenue_range,
            'lesson_type_distribution': lesson_type_distribution,
            'duration_distribution': duration_distribution,
            'monthly_revenue_series': revenue_by_month
        }
    
    def get_analysis_summary(self) -> Dict:
        """Get summary of the revenue analysis configuration and data"""
        return {
            'end_column': self.end_column,
            'total_subscriptions': len(self._subscriptions_df) if self._subscriptions_df is not None else 0,
            'total_monthly_records': len(self._monthly_payments_df) if self._monthly_payments_df is not None else 0,
            'analysis_date_range': {
                'start': self._subscriptions_df[self.config.get_column('start_date')].min() if self._subscriptions_df is not None else None,
                'end': self._subscriptions_df[self.end_column].max() if self._subscriptions_df is not None else None
            } if self._subscriptions_df is not None else None
        }
