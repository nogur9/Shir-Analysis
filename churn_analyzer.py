from typing import Optional, Dict, Tuple
import pandas as pd

from data_processor import DataProcessor
from duplication_handler import DuplicationHandler
from lesson_plan_service import LessonPlanService
from churn_analysis_service import ChurnAnalysisService
from filters import FilterChain, TestInstanceFilter, ShortPeriodFilter, StatusFilter, PaymentAmountFilter
from config import Config


class ChurnAnalyzer:
    """
    Main orchestrator class for churn analysis
    
    This class coordinates all the components of the churn analysis system:
    - Data loading and preprocessing
    - Duplication handling
    - Lesson plan matching
    - Filtering
    - Churn analysis calculations
    """
    end_column = "Canceled At (UTC)"
    def __init__(self, end_column: str = None):
        self.config = Config()

        # Initialize services
        self.data_processor = DataProcessor()
        self.duplication_handler = DuplicationHandler(end_column=self.end_column)
        self.lesson_plan_service = LessonPlanService()
        self.churn_analysis_service = ChurnAnalysisService(end_column=self.end_column)
        
        # Data storage
        self._subscriptions_df: Optional[pd.DataFrame] = None
        self._monthly_payments_df: Optional[pd.DataFrame] = None
        self._filter_chain: Optional[FilterChain] = None
        
        # Analysis results
        self._churn_summary: Optional[pd.DataFrame] = None
        self._revenue_by_month: Optional[pd.Series] = None
        self._started_customers: Optional[Dict] = None
        self._canceled_customers: Optional[Dict] = None
    
    def load_data(self, subscriptions_file: str = None) -> 'ChurnAnalyzer':
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
        
        # Set data in churn analysis service
        self.churn_analysis_service.set_data(self._subscriptions_df, self._monthly_payments_df)
        
        return self
    
    def set_filters(self, filter_chain: FilterChain) -> 'ChurnAnalyzer':
        """
        Set filters to apply to the data
        
        Args:
            filter_chain: Chain of filters to apply
            
        Returns:
            Self for method chaining
        """
        self._filter_chain = filter_chain
        
        # Set filters in churn analysis service
        self.churn_analysis_service.set_filters(filter_chain)
        
        return self
    
    def apply_default_filters(self) -> 'ChurnAnalyzer':
        """
        Apply default filters (test instances, short periods, irrelevant statuses)
        
        Returns:
            Self for method chaining
        """
        default_filters = FilterChain([
            TestInstanceFilter(),
            ShortPeriodFilter(),
            StatusFilter()
        ])
        
        return self.set_filters(default_filters)
    
    def compute_churn_analysis(self) -> 'ChurnAnalyzer':
        """
        Compute churn analysis metrics
        
        Args:
            from_month: Start month for analysis (optional)
            to_month: End month for analysis (optional)
            
        Returns:
            Self for method chaining
        """
        # Compute monthly churn summary
        self._churn_summary = (
            self.churn_analysis_service.compute_monthly_churn_summary()
        )

        # Get customer data by month
        filtered_df = self.churn_analysis_service._apply_filters()
        _, _, all_months = self.churn_analysis_service._get_monthly_counts(filtered_df)

        self._started_customers, self._canceled_customers = (
            self.churn_analysis_service.get_customer_data_by_month(filtered_df, all_months)
        )
        
        return self
    
    def compute_churned_revenue(self, billing_timing: str = "in_advance") -> Tuple[float, pd.DataFrame]:
        """
        Compute churned revenue analysis
        
        Args:
            billing_timing: "in_advance" or "in_arrears"
            
        Returns:
            Tuple of (total_rrl, rrl_by_month_dataframe)
        """
        if self._canceled_customers is None:
            raise ValueError("Must compute churn analysis first. Call compute_churn_analysis() before this method.")
        
        return self.churn_analysis_service.compute_churned_revenue(
            self._canceled_customers, billing_timing
        )
    
    def get_churn_summary(self) -> pd.DataFrame:
        """Get the computed churn summary"""
        if self._churn_summary is None:
            raise ValueError("Must compute churn analysis first. Call compute_churn_analysis() before this method.")
        return self._churn_summary
    
    def get_revenue_by_month(self) -> pd.Series:
        """Get revenue by month"""
        if self._revenue_by_month is None:
            raise ValueError("Must compute churn analysis first. Call compute_churn_analysis() before this method.")
        return self._revenue_by_month
    
    def get_customer_data(self) -> Tuple[pd.DataFrame, Dict, Dict]:
        """Get customer data for analysis"""
        if self._subscriptions_df is None:
            raise ValueError("Must load data first. Call load_data() before this method.")
        
        filtered_df = self.churn_analysis_service._apply_filters()
        return filtered_df, self._started_customers, self._canceled_customers
    
    def get_analysis_summary(self) -> Dict:
        """Get comprehensive summary of the analysis"""
        summary = {
            'data_loaded': self._subscriptions_df is not None,
            'churn_analysis_computed': self._churn_summary is not None,
            'total_subscriptions': len(self._subscriptions_df) if self._subscriptions_df is not None else 0,
            # 'total_monthly_records': len(self._monthly_payments_df) if self._monthly_payments_df is not None else 0,
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
        
        return summary
    
    def get_duplication_summary(self) -> Dict:
        """Get summary of duplications found"""
        if self._subscriptions_df is None:
            raise ValueError("Must load data first. Call load_data() before this method.")
        
        return self.duplication_handler.get_duplication_summary(self._subscriptions_df)
    
    def get_lesson_plan_summary(self) -> Dict:
        """Get summary of lesson plans in the data"""
        if self._monthly_payments_df is None:
            raise ValueError("Must load data first. Call load_data() before this method.")
        
        return self.lesson_plan_service.get_lesson_plan_summary(self._monthly_payments_df)
    
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
        #
        # # Export revenue by month
        # if self._revenue_by_month is not None:
        #     filename = f"{base_filename}_revenue_by_month.csv"
        #     self._revenue_by_month.to_csv(filename)
        #     exported_files['revenue_by_month'] = filename
        
        return exported_files

