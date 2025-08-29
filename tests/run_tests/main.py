from analysis_manager import AnalysisManager
from filters import AmountRangeFilter, DurationFilter, LessonTypeFilter

# Add filters based on user selection
filters = [AmountRangeFilter(60, 2000), DurationFilter(0, 13), LessonTypeFilter('Private')]

# Initialize and load data
analyzer = AnalysisManager(filters)
analyzer = analyzer.load_data()

analyzer.compute_churn_analysis()
analyzer.compute_revenue_analysis()

# Get all metrics
churn_summary = analyzer.get_churn_summary()
revenue_summary = analyzer.get_revenue_summary()

# analyzer.get_analysis_summary()
# analyzer.get_duplication_summary()
lesson_summary = analyzer.get_lesson_plan_summary()

