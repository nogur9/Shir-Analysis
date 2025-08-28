# Churn Analysis System - Refactored Architecture

## Overview

This is a refactored version of the original churn analysis system, designed with clean architecture principles, better separation of concerns, and improved maintainability. The system analyzes customer churn patterns and computes churned revenue for business analytics.

## Key Improvements

### 1. **Clean Architecture**
- **Separation of Concerns**: Each component has a single, well-defined responsibility
- **Dependency Inversion**: High-level modules don't depend on low-level modules
- **Interface Segregation**: Clean interfaces between components

### 2. **Better Code Organization**
- **Modular Design**: Functionality split into focused, reusable services
- **Clear Data Flow**: Predictable data transformation pipeline
- **Consistent Naming**: Standardized naming conventions throughout

### 3. **Improved Maintainability**
- **Single Responsibility**: Each class has one reason to change
- **Open/Closed Principle**: Easy to extend without modifying existing code
- **Dependency Injection**: Services can be easily swapped or mocked

### 4. **Enhanced Error Handling**
- **Validation**: Input validation at multiple levels
- **Graceful Degradation**: System continues to work even with partial data
- **Clear Error Messages**: Helpful error messages for debugging

## Architecture Components

### Core Services

#### 1. **ChurnAnalyzer** (`churn_analyzer.py`)
- **Purpose**: Main orchestrator that coordinates all analysis components
- **Responsibilities**: 
  - Data loading and preprocessing
  - Filter application
  - Analysis execution
  - Result aggregation
- **Usage**: Primary interface for the entire system

#### 2. **DataProcessor** (`data_processor.py`)
- **Purpose**: Handles data loading, cleaning, and preprocessing
- **Responsibilities**:
  - CSV file loading
  - Data validation
  - Data cleaning and standardization
  - Data fixes application

#### 3. **DuplicationHandler** (`duplication_handler.py`)
- **Purpose**: Manages customer duplication detection and resolution
- **Responsibilities**:
  - Duplicate group identification
  - Duplication resolution strategies
  - Clean data output

#### 4. **LessonPlanService** (`lesson_plan_service.py`)
- **Purpose**: Handles lesson plan matching and monthly payment calculations
- **Responsibilities**:
  - Lesson plan identification by amount
  - Contract period calculations
  - Monthly payment expansion

#### 5. **ChurnAnalysisService** (`churn_analysis_service.py`)
- **Purpose**: Computes churn analysis metrics
- **Responsibilities**:
  - Monthly churn calculations
  - Active customer counting
  - Churned revenue analysis

#### 6. **RevenueAnalysisService** (`revenue_analysis_service.py`) ⭐ **NEW**
- **Purpose**: Computes revenue analysis metrics
- **Responsibilities**:
  - Monthly revenue calculations
  - Churned revenue analysis (RRL)
  - Customer lifetime value (LTV)
  - Revenue metrics by lesson type and duration
  - Revenue distribution analysis

#### 7. **FilterChain** (`filters.py`)
- **Purpose**: Manages data filtering with a chain of filter objects
- **Responsibilities**:
  - Filter composition
  - Filter application
  - Filter description and documentation

### Data Models

#### 1. **Models** (`models.py`)
- **Purpose**: Defines data structures and enums
- **Components**:
  - `Customer`: Customer data structure
  - `LessonPlan`: Lesson plan configuration
  - `MonthlyMetrics`: Monthly analysis results
  - `ChurnAnalysisResult`: Complete analysis output

#### 2. **Configuration** (`config.py`)
- **Purpose**: Centralized configuration management
- **Components**:
  - File paths
  - Column mappings
  - Business rules
  - Lesson plan definitions

## Revenue Analysis Features ⭐ **NEW**

### Core Revenue Calculations

The `RevenueAnalysisService` provides comprehensive revenue analysis capabilities:

#### 1. **Monthly Revenue Analysis**
```python
# Compute total and monthly revenue
avg_monthly_rev, revenue_by_month = analyzer.compute_revenue_analysis()
total_revenue = revenue_by_month.sum()
```

#### 2. **Churned Revenue Analysis (RRL)**
```python
# Calculate recurring revenue lost due to churn
total_rrl, rrl_by_month = analyzer.compute_churned_revenue("in_advance")
```

#### 3. **Customer Lifetime Value (LTV)**
```python
# Analyze individual customer value
ltv_metrics = analyzer.get_customer_lifetime_value("customer_id")
# Returns: total_revenue, average_monthly_revenue, total_months, monthly_trend
```

#### 4. **Revenue Metrics by Category**
```python
# Revenue by lesson type (Private/Group)
lesson_type_metrics = analyzer.get_revenue_metrics_by_lesson_type()

# Revenue by subscription duration
duration_metrics = analyzer.get_revenue_metrics_by_duration()
```

#### 5. **Comprehensive Revenue Summary**
```python
# Get complete revenue overview
revenue_summary = analyzer.get_revenue_summary()
# Includes: total revenue, averages, distributions, statistics
```

### Revenue Calculation Logic

The system calculates revenue based on the **LessonPlan** monthly prices:

- **Monthly Payment**: Calculated from `LessonPlan.monthly_price`
- **Revenue**: `sum(each customer's monthly payment)`
- **Churned Revenue**: `sum(each churned customer's monthly payment)`

## Usage Examples

### Basic Usage

```python
from analysis_manager import AnalysisManager
from filters import FilterChain, AmountRangeFilter

# Initialize analyzer
analyzer = AnalysisManager()

# Load data
analyzer.load_data("subscriptions.csv")

# Apply filters
filters = FilterChain()
filters.add_filter(AmountRangeFilter(100, 1000))
analyzer.set_filters(filters)

# Compute both churn and revenue analysis
analyzer.compute_churn_analysis()
analyzer.compute_revenue_analysis()

# Get results
churn_summary = analyzer.get_churn_summary()
revenue_by_month = analyzer.get_revenue_by_month()

# Compute churned revenue
total_rrl, rrl_by_month = analyzer.compute_churned_revenue("in_advance")
```

### Advanced Revenue Analysis

```python
# Get comprehensive revenue metrics
revenue_summary = analyzer.get_revenue_summary()

# Analyze revenue by lesson type
lesson_metrics = analyzer.get_revenue_metrics_by_lesson_type()
for lesson_type, metrics in lesson_metrics.items():
    print(f"{lesson_type}: ${metrics['total_revenue']:,.2f}")

# Customer lifetime value analysis
ltv = analyzer.get_customer_lifetime_value("customer_123")
print(f"Total LTV: ${ltv['total_revenue']:,.2f}")
```

### Advanced Filtering

```python
from filters import (FilterChain, AmountRangeFilter, DurationFilter, 
                    WeeklyFrequencyFilter, LessonTypeFilter)

# Create complex filter chain
filters = FilterChain()
filters.add_filter(AmountRangeFilter(100, 1000))
filters.add_filter(DurationFilter(3, 12))
filters.add_filter(WeeklyFrequencyFilter(2))
filters.add_filter(LessonTypeFilter("Private"))

analyzer.set_filters(filters)
```

### Custom Analysis Period

```python
import pandas as pd

# Analyze specific time period
from_month = pd.Period('2023-01', freq='M')
to_month = pd.Period('2023-12', freq='M')

analyzer.compute_churn_analysis(from_month, to_month)
```

## Data Flow

```
1. Data Loading (DataProcessor)
   ↓
2. Duplication Handling (DuplicationHandler)
   ↓
3. Lesson Plan Matching (LessonPlanService)
   ↓
4. Filter Application (FilterChain)
   ↓
5. Churn Analysis (ChurnAnalysisService)
   ↓
6. Revenue Analysis (RevenueAnalysisService) ⭐ NEW
   ↓
7. Results Aggregation (ChurnAnalyzer)
```

## File Structure

```
├── churn_analyzer.py          # Main orchestrator
├── data_processor.py          # Data loading and preprocessing
├── duplication_handler.py     # Duplication management
├── lesson_plan_service.py     # Lesson plan operations
├── churn_analysis_service.py  # Churn calculations
├── revenue_analysis_service.py # Revenue calculations ⭐ NEW
├── filters.py                 # Data filtering system
├── models.py                  # Data structures and enums
├── config.py                  # Configuration management
├── app_refactored.py          # Refactored Streamlit app
├── test_revenue_analysis.py   # Test script for revenue analysis ⭐ NEW
├── requirements_refactored.txt # Dependencies
└── README_REFACTORED.md       # This file
```

## Configuration

### Column Mappings

The system automatically maps between logical column names and actual CSV column names:

```python
# In config.py
COLUMNS = {
    "email": "Customer Email",
    "name": "Customer Name", 
    "start_date": "Start Date (UTC)",
    "canceled_date": "Canceled At (UTC)",
    # ... more mappings
}
```

### Lesson Plan Configuration

Lesson plans are defined in the configuration with their characteristics:

```python
LESSON_PLANS = {
    "Private_Month": {
        "label": "Private-Month",
        "lesson_type": "Private",
        "duration_months": 1,
        "times_per_week": 1,
        "cost_options": [129, 150, 160, 180, 220]
    },
    # ... more plans
}
```

## Error Handling

The system includes comprehensive error handling:

- **Data Validation**: Checks for required columns and data types
- **Graceful Degradation**: Continues operation with partial data when possible
- **Clear Error Messages**: Descriptive error messages for debugging
- **Exception Propagation**: Proper exception handling throughout the pipeline

## Testing and Validation

### Running Tests

```bash
# Test the revenue analysis functionality
python test_revenue_analysis.py
```

### Data Validation

- Column existence validation
- Data type validation
- Date range validation
- Business rule validation

### Result Validation

- Churn rate bounds checking
- Revenue calculation verification
- Data consistency validation

## Performance Considerations

- **Lazy Loading**: Data loaded only when needed
- **Efficient Filtering**: Vectorized operations where possible
- **Memory Management**: Proper cleanup of large dataframes
- **Caching**: Lesson plan objects cached for reuse

## Migration from Original System

### Key Changes

1. **Class Names**: `ChurnAnalyzer` → `ChurnAnalyzer` (refactored)
2. **Method Names**: More descriptive and consistent
3. **Data Flow**: Clearer separation between data processing and analysis
4. **Configuration**: Centralized configuration management
5. **Error Handling**: Comprehensive error handling and validation
6. **Revenue Analysis**: Separated into dedicated service ⭐ **NEW**

### Compatibility

The refactored system maintains the same external interface for basic operations while providing enhanced functionality and better error handling.

## Future Enhancements

### Planned Improvements

1. **Database Integration**: Support for database sources
2. **Real-time Analysis**: Streaming data processing
3. **Advanced Analytics**: Machine learning integration
4. **API Interface**: REST API for external integration
5. **Performance Optimization**: Parallel processing for large datasets

### Extension Points

The architecture is designed to be easily extensible:

- New filter types can be added by implementing the `Filter` interface
- New lesson plan types can be added to the configuration
- New analysis metrics can be added to the services
- New data sources can be integrated through the data processor
- New revenue analysis methods can be added to `RevenueAnalysisService`

## Support and Maintenance

### Code Quality

- **Type Hints**: Full type annotation for better IDE support
- **Documentation**: Comprehensive docstrings and comments
- **Code Style**: Consistent formatting and naming conventions
- **Error Handling**: Robust error handling throughout

### Maintenance

- **Modular Design**: Easy to modify individual components
- **Clear Interfaces**: Well-defined boundaries between components
- **Configuration Driven**: Business logic separated from code
- **Testing Ready**: Architecture supports unit and integration testing

## Conclusion

The refactored churn analysis system provides a solid foundation for business analytics with:

- **Better Maintainability**: Clean, modular architecture
- **Enhanced Functionality**: More robust error handling and validation
- **Improved Performance**: Efficient data processing and caching
- **Future-Proof Design**: Easy to extend and modify
- **Comprehensive Revenue Analysis**: Dedicated service for revenue calculations ⭐ **NEW**

This architecture supports the core business requirements of churn analysis and churned revenue calculation while providing a foundation for future enhancements and integrations.
