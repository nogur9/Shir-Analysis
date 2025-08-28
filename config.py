from pathlib import Path
from typing import Dict, Any
import os


class Config:
    """Centralized configuration for the churn analysis system"""
    
    # File paths
    SUBSCRIPTIONS_FILE = "legacy/24-8/subscriptions.csv"
    PAYMENTS_FILE = "legacy/24-8/payments.csv"
    NEW_PAYMENTS_FILE = "legacy/24-8/subscriptions_new.csv"
    DUPLICATES_HANDLING_FILE = "legacy/24-8/handling_duplicates.xlsx"
    DUPLICATES_OUTPUT_FILE = "legacy/24-8/duplicates.csv"
    
    # Column names
    COLUMNS = {
        "email": "Customer Email",
        "name": "Customer Name", 
        "customer_id": "Customer ID",
        "start_date": "Start Date (UTC)",
        "canceled_date": "Canceled At (UTC)",
        "ended_date": "Ended At (UTC)",
        "status": "Status",
        "amount": "Amount"
    }
    
    # Analysis parameters
    MIN_SUBSCRIPTION_DURATION_DAYS = 30
    MIN_PAYMENT_AMOUNT = 60
    MAX_ANALYSIS_DATE = "31/7/2025"
    
    # Lesson plan definitions
    LESSON_PLANS = {
        "Private_Month": {
            "label": "Private-Month",
            "lesson_type": "Private",
            "duration_months": 1,
            "times_per_week": 1,
            "cost_options": [129, 150, 160, 180, 220]
        },
        "Private_Month_Twice": {
            "label": "Private-Month_Twice_week",
            "lesson_type": "Private", 
            "duration_months": 1,
            "times_per_week": 2,
            "cost_options": [110]
        },
        "Private_Three_Months": {
            "label": "Private_3_Months",
            "lesson_type": "Private",
            "duration_months": 3,
            "times_per_week": 1,
            "cost_options": [504, 540]
        },
        "Private_Six_Months": {
            "label": "Private_6_Months",
            "lesson_type": "Private",
            "duration_months": 6,
            "times_per_week": 1,
            "cost_options": [1080, 840, 960]
        },
        "Private_Six_Months_Twice": {
            "label": "Private_6_Months_Twice_week",
            "lesson_type": "Private",
            "duration_months": 6,
            "times_per_week": 2,
            "cost_options": [2180]
        },
        "Private_Year": {
            "label": "Private-Year",
            "lesson_type": "Private",
            "duration_months": 12,
            "times_per_week": 1,
            "cost_options": [1920]
        },
        "Group_Month": {
            "label": "Group-Month",
            "lesson_type": "Group",
            "duration_months": 1,
            "times_per_week": 1,
            "cost_options": [60, 80, 160, 240, 129, 120, 149]
        },
        "Group_Month_Twice": {
            "label": "Group-Month_Twice_week",
            "lesson_type": "Group",
            "duration_months": 1,
            "times_per_week": 2,
            "cost_options": [99]
        },
        "Group_Six_Months": {
            "label": "Group_6_Months",
            "lesson_type": "Group",
            "duration_months": 6,
            "times_per_week": 1,
            "cost_options": [420, 225]
        },
        "Group_Six_Months_Twice": {
            "label": "Group_6_Months_Twice_week",
            "lesson_type": "Group",
            "duration_months": 6,
            "times_per_week": 2,
            "cost_options": [534]
        }
    }
    
    # Data fixes and exceptions
    DATA_FIXES = [
        {
            'email': 'mcbride.alan@gmail.com',
            'start_date': '01/10/2023',
            'end_date': None
        },
        {
            'email': 'loredanamirea05@yahoo.com',
            'end_date': None
        },
        {
            'email': 'skravin@rediffmail.com',
            'end_date': None
        },
        {
            'email': 'mertiti@gmail.com',
            'end_date': None
        },
        {
            'email': 'nicolerabiespeech@gmail.com',
            'end_date': None
        },
        {
            'email': 'briansamuelwalker@yahoo.co.uk',
            'end_date': None
        }
    ]
    
    NEW_CUSTOMER = {
        'name': 'Dominic Church',
        'email': 'dominicchurch@wacomms.co.uk',
        'start_date': '01/12/2024',
        'end_date': None,
        'canceled_date': None
    }
    
    # Test instance exceptions
    TEST_INSTANCE_EXCEPTIONS = ["kshirjarohannaik@gmail.com"]
    
    # Irrelevant statuses
    IRRELEVANT_STATUSES = ['trialing', 'incomplete_expired']
    
    @classmethod
    def get_column(cls, key: str) -> str:
        """Get column name by key"""
        return cls.COLUMNS.get(key, key)
    
    @classmethod
    def get_lesson_plan_by_amount(cls, amount: float) -> Dict[str, Any]:
        """Get lesson plan configuration by amount"""
        for plan_name, plan_config in cls.LESSON_PLANS.items():
            if amount in plan_config["cost_options"]:
                return plan_config
        return None

