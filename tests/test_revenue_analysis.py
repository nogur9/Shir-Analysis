#!/usr/bin/env python3
"""
Test script for the new RevenueAnalysisService
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from revenue_analysis_service import RevenueAnalysisService
from filters import FilterChain, AmountRangeFilter
from config import Config


def create_test_data():
    """Create test data for revenue analysis"""
    
    # Create test subscriptions data
    subscriptions_data = {
        'Customer Email': ['test1@example.com', 'test2@example.com', 'test3@example.com'],
        'Customer Name': ['Test User 1', 'Test User 2', 'Test User 3'],
        'Start Date (UTC)': [
            datetime(2023, 1, 1),
            datetime(2023, 2, 1),
            datetime(2023, 3, 1)
        ],
        'Canceled At (UTC)': [
            datetime(2023, 6, 30),
            datetime(2023, 7, 31),
            None
        ],
        'Ended At (UTC)': [
            datetime(2023, 6, 30),
            datetime(2023, 7, 31),
            None
        ],
        'Status': ['canceled', 'canceled', 'active'],
        'Amount': [129, 150, 180],
        'cust_id': ['Test User 1-test1@example.com', 'Test User 2-test2@example.com', 'Test User 3-test3@example.com']
    }
    
    subscriptions_df = pd.DataFrame(subscriptions_data)
    
    # Create test monthly payments data
    monthly_payments_data = {
        'cust_id': [
            'Test User 1-test1@example.com', 'Test User 1-test1@example.com', 'Test User 1-test1@example.com',
            'Test User 1-test1@example.com', 'Test User 1-test1@example.com', 'Test User 1-test1@example.com',
            'Test User 2-test2@example.com', 'Test User 2-test2@example.com', 'Test User 2-test2@example.com',
            'Test User 2-test2@example.com', 'Test User 2-test2@example.com', 'Test User 2-test2@example.com',
            'Test User 3-test3@example.com', 'Test User 3-test3@example.com', 'Test User 3-test3@example.com',
            'Test User 3-test3@example.com', 'Test User 3-test3@example.com', 'Test User 3-test3@example.com'
        ],
        'month': [
            datetime(2023, 1, 1), datetime(2023, 2, 1), datetime(2023, 3, 1),
            datetime(2023, 4, 1), datetime(2023, 5, 1), datetime(2023, 6, 1),
            datetime(2023, 2, 1), datetime(2023, 3, 1), datetime(2023, 4, 1),
            datetime(2023, 5, 1), datetime(2023, 6, 1), datetime(2023, 7, 1),
            datetime(2023, 3, 1), datetime(2023, 4, 1), datetime(2023, 5, 1),
            datetime(2023, 6, 1), datetime(2023, 7, 1), datetime(2023, 8, 1)
        ],
        'monthly_price': [129, 129, 129, 129, 129, 129,
                          150, 150, 150, 150, 150, 150,
                          180, 180, 180, 180, 180, 180],
        'lesson_type': ['Private'] * 18,
        'duration_months': [1] * 18,
        'times_per_week': [1] * 18
    }
    
    monthly_payments_df = pd.DataFrame(monthly_payments_data)
    
    return subscriptions_df, monthly_payments_df


def test_revenue_analysis():
    """Test the revenue analysis functionality"""
    
    print("🧪 Testing RevenueAnalysisService...")
    
    # Create test data
    subscriptions_df, monthly_payments_df = create_test_data()
    
    # Initialize service
    service = RevenueAnalysisService()
    service.set_data(subscriptions_df, monthly_payments_df)
    
    print(f"✅ Test data created: {len(subscriptions_df)} subscriptions, {len(monthly_payments_df)} monthly records")
    
    # Test 1: Monthly revenue calculation
    print("\n📊 Test 1: Monthly Revenue Calculation")
    try:
        avg_monthly_rev, revenue_by_month = service.compute_monthly_revenue()
        print(f"✅ Average monthly revenue: ${avg_monthly_rev:.2f}")
        print(f"✅ Revenue by month: {len(revenue_by_month)} months")
        print(f"✅ Total revenue: ${revenue_by_month.sum():.2f}")
    except Exception as e:
        print(f"❌ Monthly revenue calculation failed: {e}")
    
    # Test 2: Total revenue calculation
    print("\n💰 Test 2: Total Revenue Calculation")
    try:
        total_revenue = service.compute_total_revenue()
        print(f"✅ Total revenue: ${total_revenue:.2f}")
    except Exception as e:
        print(f"❌ Total revenue calculation failed: {e}")
    
    # Test 3: Revenue by lesson type
    print("\n🎯 Test 3: Revenue by Lesson Type")
    try:
        lesson_type_revenue = service.compute_revenue_by_lesson_type()
        print(f"✅ Revenue by lesson type: {lesson_type_revenue}")
    except Exception as e:
        print(f"❌ Revenue by lesson type calculation failed: {e}")
    
    # Test 4: Revenue by duration
    print("\n⏱️ Test 4: Revenue by Duration")
    try:
        duration_revenue = service.compute_revenue_by_duration()
        print(f"✅ Revenue by duration: {duration_revenue}")
    except Exception as e:
        print(f"❌ Revenue by duration calculation failed: {e}")
    
    # Test 5: Customer lifetime value
    print("\n👤 Test 5: Customer Lifetime Value")
    try:
        customer_id = 'Test User 1-test1@example.com'
        ltv = service.compute_customer_lifetime_value(customer_id)
        print(f"✅ LTV for {customer_id}: {ltv}")
    except Exception as e:
        print(f"❌ Customer LTV calculation failed: {e}")
    
    # Test 6: Revenue summary
    print("\n📋 Test 6: Revenue Summary")
    try:
        summary = service.get_revenue_summary()
        print(f"✅ Revenue summary: {len(summary)} metrics")
        print(f"✅ Total revenue: ${summary.get('total_revenue', 0):.2f}")
        print(f"✅ Total customers: {summary.get('total_customers', 0)}")
    except Exception as e:
        print(f"❌ Revenue summary failed: {e}")
    
    # Test 7: Churned revenue (with test cancellation data)
    print("\n📉 Test 7: Churned Revenue Calculation")
    try:
        # Create test cancellation data
        canceled_customers = {
            pd.Period('2023-06', freq='M'): pd.DataFrame({
                'cust_id': ['Test User 1-test1@example.com'],
                'cancel_month': [pd.Period('2023-06', freq='M')]
            }),
            pd.Period('2023-07', freq='M'): pd.DataFrame({
                'cust_id': ['Test User 2-test2@example.com'],
                'cancel_month': [pd.Period('2023-07', freq='M')]
            })
        }
        
        total_rrl, rrl_by_month = service.compute_churned_revenue("in_advance")
        print(f"✅ Total churned revenue: ${total_rrl:.2f}")
        print(f"✅ Churned revenue by month: {len(rrl_by_month)} months")
    except Exception as e:
        print(f"❌ Churned revenue calculation failed: {e}")
    
    print("\n🎉 Revenue analysis testing completed!")


def test_with_filters():
    """Test revenue analysis with filters applied"""
    
    print("\n🔍 Testing Revenue Analysis with Filters...")
    
    # Create test data
    subscriptions_df, monthly_payments_df = create_test_data()
    
    # Initialize service
    service = RevenueAnalysisService()
    service.set_data(subscriptions_df, monthly_payments_df)
    
    # Create and apply filters
    filter_chain = FilterChain()
    filter_chain.add_filter(AmountRangeFilter(100, 200))  # Only amounts between 100-200
    
    service.set_filters(filter_chain)
    
    print(f"✅ Filters applied: {filter_chain.get_active_filters()}")
    
    # Test filtered revenue calculation
    try:
        total_revenue = service.compute_total_revenue()
        print(f"✅ Filtered total revenue: ${total_revenue:.2f}")
        
        avg_monthly_rev, revenue_by_month = service.compute_monthly_revenue()
        print(f"✅ Filtered average monthly revenue: ${avg_monthly_rev:.2f}")
        
    except Exception as e:
        print(f"❌ Filtered revenue calculation failed: {e}")
    
    print("✅ Filter testing completed!")


if __name__ == "__main__":
    print("🚀 Starting Revenue Analysis Service Tests...")
    print("=" * 50)
    
    test_revenue_analysis()
    test_with_filters()
    
    print("\n" + "=" * 50)
    print("🎯 All tests completed!")
