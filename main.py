from analysis_manager import AnalysisManager
from filters import AmountRangeFilter

# Initialize and load data
analyzer = AnalysisManager(filters=[AmountRangeFilter(100, 1000)])
analyzer = analyzer.load_data("subscriptions_new.csv")

analyzer.compute_churn_analysis()
analyzer.compute_revenue_analysis()

# Get revenue metrics
revenue_summary = analyzer.get_revenue_summary()
churn_summary = analyzer.get_churn_summary()
