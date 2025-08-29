import datetime

import pandas as pd
from typing import Optional, Dict, Any
from pandas.tseries.offsets import DateOffset

from config import Config
from models import LessonPlan, LessonType


class LessonPlanService:
    """Service for handling lesson plan operations"""
    
    def __init__(self):
        self.config = Config()
        self._lesson_plans_cache: Optional[Dict[str, LessonPlan]] = None
    
    def _build_lesson_plans(self) -> Dict[str, LessonPlan]:
        """Build lesson plan objects from configuration"""
        if self._lesson_plans_cache is not None:
            return self._lesson_plans_cache
        
        lesson_plans = {}
        
        for plan_name, plan_config in self.config.LESSON_PLANS.items():
            lesson_type = LessonType(plan_config["lesson_type"])
            
            lesson_plan = LessonPlan(
                label=plan_config["label"],
                lesson_type=lesson_type,
                duration_months=plan_config["duration_months"],
                times_per_week=plan_config["times_per_week"],
                cost_options=plan_config["cost_options"]
            )
            
            lesson_plans[plan_name] = lesson_plan
        
        self._lesson_plans_cache = lesson_plans
        return lesson_plans
    
    def find_lesson_plan_by_amount(self, amount: float) -> Optional[LessonPlan]:
        """Find lesson plan by payment amount"""
        lesson_plans = self._build_lesson_plans()
        
        for plan in lesson_plans.values():
            if plan.includes_amount(amount):
                return plan
        
        return None
    
    def apply_lesson_plans_to_dataframe(self, df: pd.DataFrame, amount_column: str = 'Amount') -> pd.DataFrame:
        """Apply lesson plan information to dataframe"""
        df = df.copy()
        
        # Map amounts to lesson plans
        df['Lesson'] = df[amount_column].apply(self.find_lesson_plan_by_amount)
        
        # Add lesson plan metadata
        df['lesson_label'] = df['Lesson'].apply(lambda x: x.label if x else None)
        df['lesson_type'] = df['Lesson'].apply(lambda x: x.lesson_type.value if x else None)
        df['duration_months'] = df['Lesson'].apply(lambda x: x.duration_months if x else None)
        df['times_per_week'] = df['Lesson'].apply(lambda x: x.times_per_week if x else None)
        df['monthly_price'] = df['Lesson'].apply(lambda x: x.monthly_price if x else None)

        return df
    
    def build_monthly_payments_dataframe(self, 
                                       subscriptions_df: pd.DataFrame,
                                       plan_switch: Dict[str, pd.DataFrame],
                                       customer_id_col: str = 'cust_id',
                                       amount_col: str = 'Amount') -> pd.DataFrame:
        """
        Build customer-per-month dataframe for revenue analysis
        
        This creates a monthly view where each row represents a customer in a specific month
        with their active lesson plan and monthly price.
        """
        payments = subscriptions_df.copy()
        
        payments = self._apply_plan_switch(payments, plan_switch)
        # Apply lesson plans
        payments = self.apply_lesson_plans_to_dataframe(payments, amount_col)
        
        # Remove rows without lesson plans
        payments = payments[payments['Lesson'].notna()].copy()

        # Calculate contract periods
        payments = self._calculate_contract_periods(payments)
        
        # Clip periods to avoid overlaps and cancellations

        #payments = self._clip_contract_periods(payments, customer_id_col)
        
        # Expand to monthly view
        monthly_df = self._expand_to_monthly_view(payments, customer_id_col)
        
        return monthly_df
    
    def _calculate_contract_periods(self, payments: pd.DataFrame) -> pd.DataFrame:
        """Calculate contract start and end dates"""
        payments = payments.copy()
        start = self.config.get_column('start_date')
        end = self.config.get_column('ended_date')

        # Contract end = start + duration - 1 day
        max_date = datetime.datetime.strptime(self.config.MAX_ANALYSIS_DATE, "%d/%m/%Y")
        payments['contract_end'] = payments[end].fillna(max_date)

        payments['contract_should_end'] = payments.apply(
            lambda row: row[start] + DateOffset(months=row['duration_months']) - pd.Timedelta(days=1),
            axis=1
        )
        
        return payments
    
    def _clip_contract_periods(self, 
                              payments: pd.DataFrame, 
                              customer_id_col: str) -> pd.DataFrame:
        """Clip contract periods to avoid overlaps and respect cancellations"""
        payments = payments.copy()
        
        # Handle cancellations
        cancel_data = payments[[customer_id_col, self.config.get_column('canceled_date')]].drop_duplicates()
        cancel_data = cancel_data.rename(columns={self.config.get_column('canceled_date'): 'cancel_at'})

        payments = payments.merge(cancel_data, on=customer_id_col, how='left')
        payments['cancel_at'] = pd.to_datetime(payments['cancel_at'])

        # Clip to cancellation date if earlier
        mask_cancel = payments['cancel_at'].notna()
        payments.loc[mask_cancel, 'contract_end'] = payments.loc[mask_cancel, ['contract_end', 'cancel_at']].min(axis=1)
        
        # Clip to next plan start (avoid overlaps)
        payments = self._clip_periods_to_next_start(payments, [customer_id_col])
        
        # Remove invalid periods
        payments = payments[payments['contract_end'] >= payments['contract_start']].copy()
        
        return payments
    
    def _clip_periods_to_next_start(self, df: pd.DataFrame, group_by: list) -> pd.DataFrame:
        """Ensure no overlap across consecutive plans for the same customer"""
        df = df.sort_values(group_by + ['contract_start']).copy()
        
        # Find next start date for each customer
        next_start = df.groupby(group_by)['contract_start'].shift(-1)
        
        # If next plan starts before current ends, clip current
        mask = next_start.notna() & df['contract_end'].notna()
        df.loc[mask, 'contract_end'] = pd.concat([
            df.loc[mask, 'contract_end'],
            (pd.to_datetime(next_start[mask]) - pd.Timedelta(days=1))
        ], axis=1).min(axis=1)
        
        return df
    
    def _expand_to_monthly_view(self, payments: pd.DataFrame, customer_id_col: str) -> pd.DataFrame:
        """Expand contract periods to monthly view"""
        # Normalize to month boundaries
        start = self.config.get_column('start_date')

        payments['month_start'] = self._month_floor(payments[start])
        payments['month_end'] = self._month_floor(payments['contract_end'])
        
        # Create list of months for each contract
        payments['month_list'] = payments.apply(
            lambda row: pd.period_range(
                pd.Period(row['month_start'], freq='M'),
                pd.Period(row['month_end'], freq='M'),
                freq='M'
            ).to_timestamp(),
            axis=1
        )
        
        # Explode to monthly rows
        exploded = payments.explode('month_list', ignore_index=True)
        exploded = exploded.rename(columns={'month_list': 'month'})

        columns = [customer_id_col, 'month', start, 'lesson_label', 'lesson_type',
                   'duration_months', 'times_per_week', 'monthly_price', 'Lesson']
        # Select relevant columns
        result = exploded[columns]
        
        # Handle multiple rows per customer-month (keep latest plan)
        result = result.sort_values([customer_id_col, 'month', start])
        result = result.groupby([customer_id_col, 'month'], as_index=False).tail(1)
        
        return result
    
    def _month_floor(self, ts) -> pd.Timestamp:
        """Normalize timestamp to month start"""
        return pd.to_datetime(ts).values.astype('datetime64[M]').astype('datetime64[ns]')
    
    def get_lesson_plan_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get summary statistics of lesson plans in the data"""
        if 'Lesson' not in df.columns:
            return {}
        df = df.copy()
        lesson_counts = df['lesson_label'].value_counts()
        lesson_type_counts = df['lesson_type'].value_counts()
        duration_counts = df['duration_months'].value_counts()
        frequency_counts = df['times_per_week'].value_counts()
        
        return {
            'total_monthly_payments': len(df),
            'lesson_type_distribution': lesson_type_counts.to_dict(),
            'duration_distribution': duration_counts.to_dict(),
            'frequency_distribution': frequency_counts.to_dict(),
            'average_monthly_price': df['monthly_price'].mean(),
            'total_monthly_revenue': df['monthly_price'].sum(),
            'lesson_plan_distribution': lesson_counts.to_dict(),
            'monthly_price_distribution': df['monthly_price']
        }

    def _apply_plan_switch(self, payments, plan_switch):
        payments = payments.copy()
        start = self.config.get_column('start_date')
        end = self.config.get_column('ended_date')

        plan_entries = []
        for idx, plans in plan_switch.items():

            for i, row in plans.iterrows():
                cust_row = payments[payments['cust_id'] == idx].iloc[0]
                cust_row[start] = row[start]
                cust_row[end] = row[end]
                cust_row['Amount'] = row['Amount']
                plan_entries.append(cust_row)

            payments = payments[payments['cust_id']!= idx]
        new_entries = pd.DataFrame([i.to_dict() for i in plan_entries])
        return pd.concat([payments, new_entries])







