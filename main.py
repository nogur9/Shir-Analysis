from churn_analyzer import ChurnAnalyzer
from filters import FilterChain, AmountRangeFilter

# Initialize and load data
analyzer = ChurnAnalyzer()
analyzer = analyzer.load_data("subscriptions_new.csv")

# Apply filters
filters = FilterChain().add_filter(AmountRangeFilter(100, 1000))
analyzer.set_filters(filters)

# Compute analysis
analyzer.compute_churn_analysis()
churn_summary = analyzer.get_churn_summary()

# Get churned revenue
total_rrl, rrl_by_month = analyzer.compute_churned_revenue("in_advance")