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
                               canceled_customers: Dict,
                               billing_timing: str = "in_arrears") -> Tuple[float, pd.DataFrame]:
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
    
    def get_revenue_summary(self) -> Dict[str, any]:
        """
        Get comprehensive revenue summary
        
        Returns:
            Dictionary with complete revenue overview
        """
        if self._monthly_payments_df is None:
            return {}

        # Basic revenue metrics
        total_revenue = self._monthly_payments_df['monthly_price'].sum()
        avg_monthly_revenue = self._monthly_payments_df['monthly_price'].mean()
        total_customers = self._monthly_payments_df['cust_id'].nunique()
        total_months = self._monthly_payments_df['month'].nunique()
        
        # Revenue distribution
        revenue_by_month = self._monthly_payments_df.groupby('month')['monthly_price'].sum()
        revenue_range = {
            'min': float(revenue_by_month.min()),
            'max': float(revenue_by_month.max()),
            'std': float(revenue_by_month.std())
        }
        
        # Lesson type distribution
        lesson_type_distribution = self._monthly_payments_df['lesson_type'].value_counts().to_dict()
        
        # Duration distribution
        duration_distribution = self._monthly_payments_df['duration_months'].value_counts().to_dict()
        
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


    @staticmethod
    def _calculate_revenue_loss_by_month(cancel_records: pd.DataFrame,
                                         billing_timing: str) -> pd.DataFrame:
        """Calculate revenue loss by month based on billing timing"""
        if cancel_records.empty:
            return pd.DataFrame(columns=["loss_month", "churned_rrl"])
        
        # Determine which month gets the revenue loss
        # if billing_timing == "in_advance":
        #     # Customers pay at beginning of month -> loss affects next month
        #     cancel_records["loss_month"] = (
        #         cancel_records["cancel_month"] + offsets.MonthBegin(1)
        #     )
        if billing_timing == "in_arrears":
            # Billed at end of month -> loss affects same month
            cancel_records["loss_month"] = cancel_records["cancel_month"]
        else:
            raise ValueError("billing_timing must be 'in_advance' or 'in_arrears'")
        
        # Aggregate by loss month
        #        churned = merged.groupby('churn_month', as_index=True)['monthly_payment_at_churn'].sum().sort_index()

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
