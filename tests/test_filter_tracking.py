#!/usr/bin/env python3
"""
Test script for the new filter tracking functionality
"""

import pandas as pd
from datetime import datetime

from filters import FilterChain, AmountRangeFilter, DurationFilter, LessonTypeFilter
from config import Config


def create_test_data():
    """Create test data for filter testing"""
    
    # Create test subscriptions data
    subscriptions_data = {
        'Customer Email': [
            'test1@example.com', 'test2@example.com', 'test3@example.com',
            'test4@example.com', 'test5@example.com', 'test6@example.com'
        ],
        'Customer Name': [
            'Test User 1', 'Test User 2', 'Test User 3',
            'Test User 4', 'Test User 5', 'Test User 6'
        ],
        'Start Date (UTC)': [
            datetime(2023, 1, 1), datetime(2023, 2, 1), datetime(2023, 3, 1),
            datetime(2023, 4, 1), datetime(2023, 5, 1), datetime(2023, 6, 1)
        ],
        'Canceled At (UTC)': [
            datetime(2023, 6, 30), datetime(2023, 7, 31), None,
            datetime(2023, 8, 31), None, None
        ],
        'Ended At (UTC)': [
            datetime(2023, 6, 30), datetime(2023, 7, 31), None,
            datetime(2023, 8, 31), None, None
        ],
        'Status': ['canceled', 'canceled', 'active', 'canceled', 'active', 'active'],
        'Amount': [129, 150, 180, 220, 300, 400],
        'cust_id': [
            'Test User 1-test1@example.com', 'Test User 2-test2@example.com', 
            'Test User 3-test3@example.com', 'Test User 4-test4@example.com',
            'Test User 5-test5@example.com', 'Test User 6-test6@example.com'
        ]
    }
    
    return pd.DataFrame(subscriptions_data)


def test_filter_tracking():
    """Test the filter tracking functionality"""
    
    print("🧪 Testing Filter Tracking...")
    
    # Create test data
    df = create_test_data()
    print(f"✅ Test data created: {len(df)} rows")
    
    # Create filter chain
    filter_chain = FilterChain()
    filter_chain.add_filter(AmountRangeFilter(100, 200))  # Should exclude rows with Amount > 200
    filter_chain.add_filter(DurationFilter(3, 12))        # Should exclude rows with duration < 3 months
    
    print(f"✅ Filters created: {filter_chain.get_active_filters()}")
    
    # Apply filters
    filtered_df = filter_chain.apply(df)
    print(f"✅ Filters applied. Result: {len(filtered_df)} rows")
    
    # Get filter statistics
    filter_stats = filter_chain.get_filter_stats()
    summary_stats = filter_chain.get_summary_stats()
    
    print("\n📊 Filter Statistics:")
    print("=" * 50)
    
    # Display detailed stats
    for filter_name, stats in filter_stats.items():
        print(f"\n🔍 {filter_name}:")
        print(f"   Rows Excluded: {stats['excluded']}")
        print(f"   Rows Included: {stats['included']}")
        print(f"   Excluded %: {stats['excluded_percentage']}%")
        print(f"   Included %: {stats['included_percentage']}%")
    
    # Display summary stats
    print(f"\n📋 Summary Statistics:")
    print(f"   Total Filters: {summary_stats['total_filters']}")
    print(f"   Original Rows: {summary_stats['total_original']}")
    print(f"   Total Excluded: {summary_stats['total_excluded']}")
    print(f"   Total Included: {summary_stats['total_included']}")
    
    # Test filter efficiency
    total_original = summary_stats['total_original']
    total_excluded = summary_stats['total_excluded']
    efficiency = ((total_original - total_excluded) / total_original) * 100
    
    print(f"\n⚡ Filter Efficiency:")
    print(f"   Data Retention Rate: {efficiency:.1f}%")
    print(f"   Data Exclusion Rate: {100 - efficiency:.1f}%")
    
    print("\n🎉 Filter tracking test completed!")


def test_filter_chain_methods():
    """Test all filter chain methods"""
    
    print("\n🔧 Testing Filter Chain Methods...")
    
    # Create filter chain
    filter_chain = FilterChain()
    
    # Test empty chain
    print("✅ Empty chain created")
    print(f"   Active filters: {filter_chain.get_active_filters()}")
    print(f"   Filter stats: {filter_chain.get_filter_stats()}")
    print(f"   Summary stats: {filter_chain.get_summary_stats()}")
    
    # Add filters
    filter_chain.add_filter(AmountRangeFilter(100, 200))
    filter_chain.add_filter(DurationFilter(3, 12))
    
    print(f"\n✅ Filters added: {filter_chain.get_active_filters()}")
    
    # Test with data
    df = create_test_data()
    filtered_df = filter_chain.apply(df)
    
    print(f"✅ Filters applied to {len(df)} rows, result: {len(filtered_df)} rows")
    
    # Test all methods
    print(f"\n📊 Method Results:")
    print(f"   get_active_filters(): {filter_chain.get_active_filters()}")
    print(f"   get_filter_stats(): {len(filter_chain.get_filter_stats())} filter stats")
    print(f"   get_summary_stats(): {filter_chain.get_summary_stats()}")
    
    print("✅ Filter chain methods test completed!")


if __name__ == "__main__":
    print("🚀 Starting Filter Tracking Tests...")
    print("=" * 60)
    
    test_filter_tracking()
    test_filter_chain_methods()
    
    print("\n" + "=" * 60)
    print("🎯 All filter tracking tests completed!")
