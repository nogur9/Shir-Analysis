from analysis_manager import AnalysisManager
from filters import AmountRangeFilter, DurationFilter

# Add filters based on user selection
filters = [AmountRangeFilter(60, 2000), DurationFilter(0, 13)]

# Initialize and load data
analyzer = AnalysisManager(filters)
analyzer = analyzer.load_data()

analyzer.compute_churn_analysis()
analyzer.compute_revenue_analysis()

# Get revenue metrics
revenue_summary = analyzer.get_revenue_summary()
churn_summary = analyzer.get_churn_summary()
