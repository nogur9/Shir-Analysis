from typing import Optional, Dict, Tuple
import pandas as pd
from data_processor import DataProcessor
from duplication_handler import DuplicationHandler
from lesson_plan_service import LessonPlanService
from churn_analysis_service import ChurnAnalysisService
from revenue_analysis_service import RevenueAnalysisService
from filters import FilterChain, Filter
from config import Config


class AnalysisManager:
    """
    Main orchestrator class for churn analysis

    This class coordinates all the components of the churn analysis system:
    - Data loading and preprocessing
    - Duplication handling
    - Lesson plan matching
    - Filtering
    - Churn analysis calculations
    - Revenue analysis calculations
    """
    end_column = "Canceled At (UTC)"

    def __init__(self, filters: Optional[list[Filter]] = None,
                 end_column: Optional[str] = None,
                 add_default_filters: Optional[bool] = True):

        self.config = Config()
        self.end_column = end_column or self.config.get_column('canceled_date')

        # Initialize services
        self.data_processor = DataProcessor()
        self.duplication_handler = DuplicationHandler(end_column=self.end_column)
        self.lesson_plan_service = LessonPlanService()
        self.churn_analysis_service = ChurnAnalysisService(end_column=self.end_column)
        self.revenue_analysis_service = RevenueAnalysisService(end_column=self.end_column)
        self._filter_chain = FilterChain(filters, add_default_filters=add_default_filters)

        # Data storage
        self._subscriptions_df: Optional[pd.DataFrame] = None
        self._monthly_payments_df: Optional[pd.DataFrame] = None

        # Analysis results
        self._churn_summary: Optional[pd.DataFrame] = None
        self._revenue_by_month: Optional[pd.Series] = None
        self._started_customers: Optional[Dict] = None
        self._canceled_customers: Optional[Dict] = None
        self.churned_revenue:Optional[float] = None
        self.rrl_by_month: Optional[pd.DataFrame] = None

    def load_data(self, subscriptions_file: str = None) -> 'AnalysisManager':
        """
        Load and preprocess all data

        Args:
            subscriptions_file: Path to subscriptions CSV file

        Returns:
            Self for method chaining
        """
        # Load subscriptions data
        file_path = subscriptions_file or self.config.SUBSCRIPTIONS_FILE
        self._subscriptions_df = self.data_processor.load_subscriptions(file_path)

        # Handle duplications
        self._subscriptions_df = self.duplication_handler.handle_duplications(self._subscriptions_df)

        # Build monthly payments dataframe
        self._monthly_payments_df = self.lesson_plan_service.build_monthly_payments_dataframe(
            self._subscriptions_df,
            self.duplication_handler.plan_switch,
        )

        self._subscriptions_df = self._filter_chain.apply(self._subscriptions_df, self._monthly_payments_df)
        self._monthly_payments_df = self._apply_filters_to_monthly_data(self._monthly_payments_df)

        # Set data in services
        self.churn_analysis_service.set_data(self._subscriptions_df, self._monthly_payments_df)
        self.revenue_analysis_service.set_data(self._subscriptions_df, self._monthly_payments_df)

        return self
        #
        # self.churn_analysis_service.set_filters(filter_chain)
        # self.revenue_analysis_service.set_filters(filter_chain)

    def _apply_filters_to_monthly_data(self, monthly_payments_df: pd.DataFrame) -> pd.DataFrame:
        """Apply filters to monthly payments data"""
        if self._filter_chain is None:
            return monthly_payments_df

        # Filter monthly payments to only include filtered customers
        filtered_customers = self._subscriptions_df['cust_id'].unique()
        filtered_monthly_df = monthly_payments_df[
            monthly_payments_df['cust_id'].isin(filtered_customers)
        ].copy()

        return filtered_monthly_df

    def compute_churn_analysis(self) -> 'AnalysisManager':
        """
        Compute churn analysis metrics

        Returns:
            Self for method chaining
        """
        self._churn_summary = (
            self.churn_analysis_service.compute_monthly_churn_summary()
        )

        # Get customer data by month
        _, _, all_months = self.churn_analysis_service.get_monthly_counts(self._subscriptions_df)
        self._started_customers, self._canceled_customers = (
            self.churn_analysis_service.get_customer_data_by_month(self._subscriptions_df, all_months))

        return self


    def compute_revenue_analysis(self) -> 'AnalysisManager':
        """
        Compute revenue analysis metrics

        Returns:
            Self for method chaining
        """

        if self._canceled_customers is None:
            raise ValueError("Must compute churn analysis first. Call compute_churn_analysis() before this method.")

        # Compute monthly revenue
        _, self._revenue_by_month = (
            self.revenue_analysis_service.compute_monthly_revenue()
        )

        return self

    def compute_churned_revenue(self) -> Tuple[float, pd.DataFrame]:
        """
        Compute churned revenue totals and monthly breakdown using average monthly spend per churned customer.
        """
        if self._canceled_customers is None:
            raise ValueError("Must compute churn analysis first. Call compute_churn_analysis() before this method.")
        return self.revenue_analysis_service.compute_churned_revenue(self._canceled_customers)

    def get_churn_summary(self) -> pd.DataFrame:
        """Get the computed churn summary"""
        if self._churn_summary is None:
            raise ValueError("Must compute churn analysis first. Call compute_churn_analysis() before this method.")
        return self._churn_summary


    def get_revenue_by_month(self) -> pd.Series:
        """Get revenue by month"""
        if self._revenue_by_month is None:
            raise ValueError("Must compute revenue analysis first. Call compute_revenue_analysis() before this method.")
        return self._revenue_by_month

    def get_customer_data(self) -> Tuple[pd.DataFrame, Dict, Dict]:
        """Get customer data for analysis"""
        if self._subscriptions_df is None:
            raise ValueError("Must load data first. Call load_data() before this method.")

        return self._subscriptions_df, self._started_customers, self._canceled_customers

    def get_revenue_summary(self, monthly_pay_df: Optional[pd.DataFrame] = None) -> Dict:
        """Get comprehensive revenue summary"""
        return self.revenue_analysis_service.get_revenue_summary(monthly_pay_df)

    def get_customer_lifetime_value(self, customer_id: str) -> Dict[str, float]:
        """Get lifetime value metrics for a specific customer"""
        return self.revenue_analysis_service.compute_customer_lifetime_value(customer_id)

    def get_revenue_metrics_by_lesson_type(self) -> Dict[str, Dict]:
        """Get revenue metrics grouped by lesson type"""
        return self.revenue_analysis_service.compute_revenue_by_lesson_type()

    def get_revenue_metrics_by_duration(self) -> Dict[str, Dict]:
        """Get revenue metrics grouped by subscription duration"""
        return self.revenue_analysis_service.compute_revenue_by_duration()

    def get_filter_statistics(self) -> Tuple[Dict, Dict]:
        """
        Get filter statistics showing how many rows are filtered vs included

        Returns:
            Tuple of (filter_stats, summary_stats)
        """
        if self._filter_chain is None:
            return {}, {}

        return (
            self._filter_chain.get_filter_stats(),
            self._filter_chain.get_summary_stats()
        )

    def get_analysis_summary(self) -> Dict:
        """Get comprehensive summary of the analysis"""
        summary = {
            'data_loaded': self._subscriptions_df is not None,
            'churn_analysis_computed': self._churn_summary is not None,
            'revenue_analysis_computed': self._revenue_by_month is not None,
            'total_subscriptions': len(self._subscriptions_df) if self._subscriptions_df is not None else 0,
            'total_monthly_records': len(self._monthly_payments_df) if self._monthly_payments_df is not None else 0,
            'active_filters': self._filter_chain.get_active_filters() if self._filter_chain else [],
            'end_column_used': self.end_column
        }

        if self._subscriptions_df is not None:
            summary.update({
                'date_range': {
                    'start': self._subscriptions_df[self.config.get_column('start_date')].min(),
                    'end': self._subscriptions_df[self.end_column].max()
                }
            })

        if self._churn_summary is not None:
            summary.update({
                'analysis_period': {
                    'start': self._churn_summary['Month'].min(),
                    'end': self._churn_summary['Month'].max()
                },
                'total_starts': self._churn_summary['Starts'].sum(),
                'total_cancellations': self._churn_summary['Cancellations'].sum(),
                'average_churn_rate': self._churn_summary['Churn_Rate'].mean()
            })

        if self._revenue_by_month is not None:
            summary.update({
                'total_revenue': self._revenue_by_month.sum(),
                'average_monthly_revenue': self._revenue_by_month.mean(),
                'revenue_range': {
                    'min': self._revenue_by_month.min(),
                    'max': self._revenue_by_month.max()
                }
            })

        return summary

    def get_duplication_summary(self) -> Dict:
        """Get summary of duplications found"""
        if self._subscriptions_df is None:
            raise ValueError("Must load data first. Call load_data() before this method.")

        return self.duplication_handler.get_duplication_summary(self._subscriptions_df)

    def get_lesson_plan_summary(self, monthly_pay:Optional[pd.DataFrame]=None) -> Dict:
        """Get summary of lesson plans in the data"""
        if self._monthly_payments_df is None:
            raise ValueError("Must load data first. Call load_data() before this method.")
        if monthly_pay is None:
            return self.lesson_plan_service.get_lesson_plan_summary(self._monthly_payments_df)
        else:
            return self.lesson_plan_service.get_lesson_plan_summary(monthly_pay)

    def export_data(self, base_filename: str = "churn_analysis") -> Dict[str, str]:
        """
        Export analysis results to CSV files

        Args:
            base_filename: Base name for exported files
            
        Returns:
            Dictionary mapping data type to file path
        """
        if self._subscriptions_df is None:
            raise ValueError("Must load data first. Call load_data() before this method.")
        
        exported_files = {}
        
        # Export main data
        if self._subscriptions_df is not None:
            filename = f"{base_filename}_subscriptions.csv"
            self._subscriptions_df.to_csv(filename, index=False)
            exported_files['subscriptions'] = filename
        
        # Export monthly payments
        if self._monthly_payments_df is not None:
            filename = f"{base_filename}_monthly_payments.csv"
            self._monthly_payments_df.to_csv(filename, index=False)
            exported_files['monthly_payments'] = filename
        
        # Export churn summary
        if self._churn_summary is not None:
            filename = f"{base_filename}_churn_summary.csv"
            self._churn_summary.to_csv(filename, index=False)
            exported_files['churn_summary'] = filename
        
        # Export revenue by month
        if self._revenue_by_month is not None:
            filename = f"{base_filename}_revenue_by_month.csv"
            self._revenue_by_month.to_csv(filename, index=False)
            exported_files['revenue_by_month'] = filename
        
        return exported_files


