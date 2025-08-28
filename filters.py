from abc import ABC, abstractmethod
from typing import Union, Optional, Dict, List
import pandas as pd
import datetime

from config import Config
from models import LessonPlan, LessonType


class Filter(ABC):
    """Abstract base class for all filters"""
    
    @abstractmethod
    def should_exclude(self, row: pd.Series) -> bool:
        """Return True if the row should be excluded"""
        pass
    
    def get_description(self) -> str:
        """Get a human-readable description of this filter"""
        return self.__class__.__name__


class TestInstanceFilter(Filter):
    """Filter out test instances (customers with 'shir' in name/email)"""
    
    def __init__(self):
        self.config = Config()
        self.exceptions = self.config.TEST_INSTANCE_EXCEPTIONS
    
    def should_exclude(self, row: pd.Series) -> bool:
        email = str(row.get(self.config.get_column('email'), "") or "")
        name = str(row.get(self.config.get_column('name'), "") or "")
        
        # Specific exclusions
        if email in ["shir.bartal@gmail.com", "hassanstudentshir@gmail.com", 
                     "ola.khadijah.994@gmail.com", "briansamuelwalker@yahoo.co.uk",
                     "janecoppee@gmail.com"]:
            return True
        
        # Exceptions
        if email in self.exceptions:
            return False
        
        return ("shir" in email.lower()) or ("shir" in name.lower())
    
    def get_description(self) -> str:
        return "Exclude test instances (shir*)"


class ShortPeriodFilter(Filter):
    """Filter out subscriptions with duration less than minimum"""
    
    def __init__(self, min_duration_days: int = None):
        self.config = Config()
        self.min_duration = min_duration_days or self.config.MIN_SUBSCRIPTION_DURATION_DAYS
    
    def should_exclude(self, row: pd.Series) -> bool:
        start_date = row.get(self.config.get_column('start_date'))
        end_date = row.get(self.config.get_column('canceled_date'))
        
        if pd.isna(start_date) or pd.isna(end_date):
            return False  # Don't exclude if we can't determine duration
        
        duration = (end_date - start_date).days
        return duration < self.min_duration
    
    def get_description(self) -> str:
        return f"Exclude subscriptions shorter than {self.min_duration} days"


class StatusFilter(Filter):
    """Filter out customers with irrelevant statuses"""
    
    def __init__(self):
        self.config = Config()
        self.irrelevant_statuses = self.config.IRRELEVANT_STATUSES
    
    def should_exclude(self, row: pd.Series) -> bool:
        status = row.get(self.config.get_column('status'), "")
        return status in self.irrelevant_statuses
    
    def get_description(self) -> str:
        return f"Exclude statuses: {', '.join(self.irrelevant_statuses)}"


class PaymentAmountFilter(Filter):
    """Filter out customers with payments below minimum amount"""
    
    def __init__(self, min_amount: float = None):
        self.config = Config()
        self.min_amount = min_amount or self.config.MIN_PAYMENT_AMOUNT
        self.payments_df = None
    
    def set_payments_data(self, payments_df: pd.DataFrame):
        """Set the payments data for filtering"""
        self.payments_df = payments_df
    
    def should_exclude(self, row: pd.Series) -> bool:
        if self.payments_df is None:
            return False  # Can't filter without payments data
        
        cust_id = row.get('cust_id')
        if not cust_id:
            return False
        
        # Find payment amount for this customer
        customer_payments = self.payments_df[self.payments_df['cust_id'] == cust_id]
        if customer_payments.empty:
            return False
        
        total_spent = customer_payments['Total Spend'].sum()
        return total_spent < self.min_amount
    
    def get_description(self) -> str:
        return f"Exclude customers with payments < {self.min_amount}"


class LessonTypeFilter(Filter):
    """Filter by lesson type (Private/Group)"""
    
    def __init__(self, lesson_type: Union[str, LessonType]):
        self.lesson_type = lesson_type if isinstance(lesson_type, str) else lesson_type.value
    
    def should_exclude(self, row: pd.Series) -> bool:
        lesson_plan = row.get('Lesson')
        if lesson_plan is None:
            return True
        
        return lesson_plan.lesson_type != self.lesson_type
    
    def get_description(self) -> str:
        return f"Only include {self.lesson_type} lessons"


class DurationFilter(Filter):
    """Filter by subscription duration in months"""
    
    def __init__(self, min_months: int, max_months: int):
        self.min_months = min_months
        self.max_months = max_months
    
    def should_exclude(self, row: pd.Series) -> bool:
        lesson_plan = row.get('Lesson')
        if lesson_plan is None:
            return True
        
        return (lesson_plan.duration_months < self.min_months or 
                lesson_plan.duration_months > self.max_months)
    
    def get_description(self) -> str:
        return f"Only include {self.min_months}-{self.max_months} month subscriptions"


class WeeklyFrequencyFilter(Filter):
    """Filter by weekly lesson frequency"""
    
    def __init__(self, times_per_week: int):
        self.times_per_week = times_per_week
    
    def should_exclude(self, row: pd.Series) -> bool:
        lesson_plan = row.get('Lesson')
        if lesson_plan is None:
            return True
        
        return lesson_plan.times_per_week != self.times_per_week
    
    def get_description(self) -> str:
        return f"Only include {self.times_per_week}x per week lessons"


class AmountRangeFilter(Filter):
    """Filter by payment amount range"""
    
    def __init__(self, min_amount: float, max_amount: float):
        self.min_amount = min_amount
        self.max_amount = max_amount
    
    def should_exclude(self, row: pd.Series) -> bool:
        amount = row.get('Amount')
        if pd.isna(amount):
            return True
        
        return (amount < self.min_amount or amount > self.max_amount)
    
    def get_description(self) -> str:
        return f"Only include amounts between {self.min_amount} and {self.max_amount}"


class FilterChain:
    """Chain multiple filters together with row tracking"""
    
    def __init__(self, filters: Optional[list[Filter]] = None, add_default_filters: Optional[bool]=True):
        self.add_default_filters = add_default_filters
        self.filters = filters or []

        if self.add_default_filters:
            for d_filter in self.get_default_filters():
                self.add_filter(d_filter)

        self.filter_stats: Dict[str, Dict[str, int]] = {}


    @staticmethod
    def get_default_filters() -> List[Filter]:
        """
        Apply default filters (test instances, short periods, irrelevant statuses)

        Returns:
            Self for method chaining
        """
        default_filters = [
            TestInstanceFilter(),
            ShortPeriodFilter(),
            StatusFilter(),
            PaymentAmountFilter(),
        ]

        return default_filters


    def add_filter(self, filter_obj: Filter) -> 'FilterChain':
        """Add a filter to the chain"""
        self.filters.append(filter_obj)
        return self
    
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply all filters to the dataframe with detailed tracking"""
        if not self.filters:
            return df
        
        df = df.copy()
        keep_mask = pd.Series(True, index=df.index)
        total_rows = len(df)
        
        # Reset filter stats
        self.filter_stats = {}
        
        for i, filter_obj in enumerate(self.filters):
            filter_name = filter_obj.get_description()
            
            # Apply this filter
            exclude_mask = df.apply(filter_obj.should_exclude, axis=1)
            keep_mask &= ~exclude_mask
            
            # Calculate stats for this filter
            excluded_count = exclude_mask.sum()
            included_count = keep_mask.sum()
            
            self.filter_stats[filter_name] = {
                'excluded': int(excluded_count),
                'included': int(included_count),
                'excluded_percentage': round((excluded_count / total_rows) * 100, 1),
                'included_percentage': round((included_count / total_rows) * 100, 1)
            }
            
            # Update dataframe for next filter
            df = df.loc[keep_mask].copy()
        
        return df
    
    def get_active_filters(self) -> list[str]:
        """Get descriptions of all active filters"""
        return [f.get_description() for f in self.filters]
    
    def get_filter_stats(self) -> Dict[str, Dict[str, int]]:
        """Get detailed statistics for each filter"""
        return self.filter_stats
    
    def get_summary_stats(self) -> Dict[str, int]:
        """Get overall filtering summary"""
        if not self.filter_stats:
            return {}
        
        total_excluded = sum(stats['excluded'] for stats in self.filter_stats.values())
        total_included = list(self.filter_stats.values())[-1]['included'] if self.filter_stats else 0
        
        return {
            'total_filters': len(self.filters),
            'total_excluded': total_excluded,
            'total_included': total_included,
            'total_original': total_excluded + total_included
        }

