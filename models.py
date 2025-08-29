from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from enum import Enum


class LessonType(Enum):
    """Enum for lesson types"""
    PRIVATE = "Private"
    GROUP = "Group"


class BillingFrequency(Enum):
    """Enum for billing frequency"""
    MONTHLY = 1
    TWICE_WEEKLY = 2


@dataclass
class LessonPlan:
    """Data class representing a lesson plan"""
    label: str
    lesson_type: LessonType
    duration_months: int
    times_per_week: int
    cost_options: List[float]
    
    def includes_amount(self, amount: float) -> bool:
        """Check if amount matches this lesson plan"""
        return amount in self.cost_options
    


@dataclass
class Customer:
    """Data class representing a customer"""
    customer_id: str
    name: str
    email: str
    start_date: datetime
    end_date: Optional[datetime] = None
    canceled_date: Optional[datetime] = None
    status: str = "active"
    amount: Optional[float] = None
    lesson_plan: Optional[LessonPlan] = None


@dataclass
class MonthlyMetrics:
    """Data class for monthly churn metrics"""
    month: datetime
    starts: int
    cancellations: int
    actives: int
    churn_rate: float
    revenue: float
    churned_revenue: float


@dataclass
class ChurnAnalysisResult:
    """Data class for churn analysis results"""
    monthly_metrics: List[MonthlyMetrics]
    total_customers: int
    total_churned: int
    average_churn_rate: float
    total_revenue_lost: float





