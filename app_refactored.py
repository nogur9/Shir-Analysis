

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

from analysis_manager import AnalysisManager
from filters import (FilterChain, AmountRangeFilter, DurationFilter, 
                    WeeklyFrequencyFilter, LessonTypeFilter)
from config import Config


def main():
    st.set_page_config(page_title="Churn Dashboard - Refactored", layout="wide")
    st.title("Churn Dashboard - Refactored Architecture")
    
    # Initialize configuration
    config = Config()
    
    # Sidebar configuration
    st.sidebar.header("Analysis Configuration")
    
    # Column selection
    ending_column = st.sidebar.selectbox(
        label="Select cancellation column", 
        options=[config.get_column('canceled_date'), config.get_column('ended_date')]
    )
    
    # Filter configuration
    st.sidebar.subheader("Data Filters")
    
    min_dur_months, max_dur_months = st.sidebar.slider(
        "Filter by Months", 
        min_value=0, 
        max_value=13,
        value=(0, 13)
    )
    
    min_amount, max_amount = st.sidebar.slider(
        "Filter by Amount", 
        min_value=60, 
        max_value=2000,
        value=(60, 2000)
    )
    
    times_a_week = st.sidebar.selectbox("Weekly Times", ['all', 1, 2], index=0)
    lesson_type = st.sidebar.selectbox("Lesson Type", ['all', 'Group', 'Private'], index=0)
    
    # Build filter chain
    filter_chain = FilterChain()
    
    # Add filters based on user selection
    filter_chain.add_filter(AmountRangeFilter(min_amount, max_amount))
    filter_chain.add_filter(DurationFilter(min_dur_months, max_dur_months))
    
    if times_a_week != 'all':
        filter_chain.add_filter(WeeklyFrequencyFilter(times_a_week))
    
    if lesson_type != 'all':
        filter_chain.add_filter(LessonTypeFilter(lesson_type))
    
    # Display active filters
    st.sidebar.subheader("Active Filters")
    for filter_desc in filter_chain.get_active_filters():
        st.sidebar.write(f"• {filter_desc}")
    
    # Main analysis
    with st.spinner("Loading and analyzing data..."):
        try:
            # Initialize analyzer
            analyzer = AnalysisManager(end_column=ending_column)
            
            # Load data
            analyzer.load_data()
            
            # Apply filters
            analyzer.set_filters(filter_chain)
            
            # Compute analysis
            analyzer.compute_churn_analysis()
            analyzer.compute_revenue_analysis()
            
            # Get results
            churn_summary = analyzer.get_churn_summary()
            revenue_by_month = analyzer.get_revenue_by_month()
            
            # Display success message
            st.success("Analysis completed successfully!")
            
            # Display analysis summary
            analysis_summary = analyzer.get_analysis_summary()
            st.subheader("Analysis Summary")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Subscriptions", analysis_summary['total_subscriptions'])
            with col2:
                st.metric("Total Monthly Records", analysis_summary['total_monthly_records'])
            with col3:
                st.metric("Total Starts", analysis_summary['total_starts'])
            with col4:
                st.metric("Total Cancellations", analysis_summary['total_cancellations'])
            
            # Display date ranges
            if analysis_summary.get('date_range'):
                st.write(f"**Data Date Range:** {analysis_summary['date_range']['start'].strftime('%Y-%m-%d')} to {analysis_summary['date_range']['end'].strftime('%Y-%m-%d')}")
            
            if analysis_summary.get('analysis_period'):
                st.write(f"**Analysis Period:** {analysis_summary['analysis_period']['start']} to {analysis_summary['analysis_period']['end']}")
            
            # Display churn summary
            st.subheader("Monthly Churn Analysis")
            
            # Tabs for different visualizations
            tabs = st.tabs(["Full Overview", "Starts vs Cancellations", "Churn Rate & Actives"])
            
            with tabs[0]:
                fig = create_full_overview_chart(churn_summary)
                st.plotly_chart(fig, use_container_width=True)
            
            with tabs[1]:
                fig = create_starts_cancellations_chart(churn_summary)
                st.plotly_chart(fig, use_container_width=True)
            
            with tabs[2]:
                fig = create_churn_rate_chart(churn_summary)
                st.plotly_chart(fig, use_container_width=True)
            
            # Filter Statistics Section - NEW!
            st.subheader("📊 Filter Statistics & Row Tracking")
            
            # Get filter statistics
            filter_stats, summary_stats = analyzer.get_filter_statistics()
            
            if filter_stats:
                # Display summary metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Filters Applied", summary_stats.get('total_filters', 0))
                with col2:
                    st.metric("Original Rows", summary_stats.get('total_original', 0))
                with col3:
                    st.metric("Rows Excluded", summary_stats.get('total_excluded', 0))
                with col4:
                    st.metric("Rows Included", summary_stats.get('total_included', 0))
                
                # Display detailed filter breakdown
                st.write("**Detailed Filter Breakdown:**")
                
                # Create a DataFrame for better display
                filter_data = []
                for filter_name, stats in filter_stats.items():
                    filter_data.append({
                        'Filter': filter_name,
                        'Rows Excluded': stats['excluded'],
                        'Rows Included': stats['included'],
                        'Excluded %': f"{stats['excluded_percentage']}%",
                        'Included %': f"{stats['included_percentage']}%"
                    })
                
                filter_df = pd.DataFrame(filter_data)
                st.dataframe(filter_df, use_container_width=True)
                
                # Visual representation
                st.write("**Filter Impact Visualization:**")
                
                # Create a stacked bar chart showing filter impact
                fig = go.Figure()
                
                filter_names = list(filter_stats.keys())
                excluded_counts = [filter_stats[name]['excluded'] for name in filter_names]
                included_counts = [filter_stats[name]['included'] for name in filter_names]
                
                fig.add_trace(go.Bar(
                    name='Excluded Rows',
                    x=filter_names,
                    y=excluded_counts,
                    marker_color='#ef553b'
                ))
                
                fig.add_trace(go.Bar(
                    name='Included Rows',
                    x=filter_names,
                    y=included_counts,
                    marker_color='#00cc96'
                ))
                
                fig.update_layout(
                    title="Filter Impact on Data Rows",
                    xaxis_title="Filters Applied",
                    yaxis_title="Number of Rows",
                    barmode='stack',
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Filter efficiency metrics
                st.write("**Filter Efficiency:**")
                total_original = summary_stats.get('total_original', 1)
                total_excluded = summary_stats.get('total_excluded', 0)
                total_included = summary_stats.get('total_included', 0)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    efficiency = ((total_original - total_excluded) / total_original) * 100
                    st.metric("Data Retention Rate", f"{efficiency:.1f}%")
                
                with col2:
                    exclusion_rate = (total_excluded / total_original) * 100
                    st.metric("Data Exclusion Rate", f"{exclusion_rate:.1f}%")
                
                with col3:
                    if summary_stats.get('total_filters', 0) > 0:
                        avg_exclusion_per_filter = total_excluded / summary_stats['total_filters']
                        st.metric("Avg Rows Excluded per Filter", f"{avg_exclusion_per_filter:.0f}")
                    else:
                        st.metric("Avg Rows Excluded per Filter", "N/A")
                
            else:
                st.info("No filters have been applied yet. Apply filters to see statistics.")
            
            # Revenue analysis
            st.subheader("Revenue Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Revenue by Month**")
                st.dataframe(revenue_by_month.reset_index().rename(columns={'index': 'Month', 0: 'Revenue'}))
            
            with col2:
                st.write("**Revenue Statistics**")
                st.write(f"Average Monthly Revenue: ${revenue_by_month.mean():.2f}")
                st.write(f"Total Revenue: ${revenue_by_month.sum():.2f}")
                st.write(f"Revenue Range: ${revenue_by_month.min():.2f} - ${revenue_by_month.max():.2f}")
            
            # Advanced revenue metrics
            st.subheader("Advanced Revenue Metrics")
            
            # Revenue by lesson type
            lesson_type_metrics = analyzer.get_revenue_metrics_by_lesson_type()
            if lesson_type_metrics:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Revenue by Lesson Type**")
                    lesson_type_df = pd.DataFrame(lesson_type_metrics).T
                    st.dataframe(lesson_type_df)
                
                with col2:
                    st.write("**Revenue by Duration**")
                    duration_metrics = analyzer.get_revenue_metrics_by_duration()
                    if duration_metrics:
                        duration_df = pd.DataFrame(duration_metrics).T
                        st.dataframe(duration_df)
            
            # Churned revenue analysis
            st.subheader("Churned Revenue Analysis")
            
            billing_timing = st.selectbox(
                "Billing Timing",
                ["in_advance", "in_arrears"],
                help="in_advance: customers pay at beginning of month, in_arrears: customers pay at end of month"
            )
            
            if st.button("Calculate Churned Revenue"):
                with st.spinner("Calculating churned revenue..."):
                    total_rrl, rrl_by_month = analyzer.compute_churned_revenue(billing_timing)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("Total Revenue Lost", f"${total_rrl:,.2f}")
                    
                    with col2:
                        st.write("**Revenue Lost by Month**")
                        if not rrl_by_month.empty:
                            st.dataframe(rrl_by_month)
                        else:
                            st.write("No churned revenue data available")
            
            # Customer lifetime value analysis
            st.subheader("Customer Lifetime Value Analysis")
            
            # Get unique customer IDs for selection
            if analyzer._monthly_payments_df is not None:
                unique_customers = analyzer._monthly_payments_df['cust_id'].unique()
                selected_customer = st.selectbox("Select Customer for LTV Analysis", unique_customers[:10])
                
                if st.button("Calculate Customer LTV"):
                    ltv_metrics = analyzer.get_customer_lifetime_value(selected_customer)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Revenue", f"${ltv_metrics['total_revenue']:,.2f}")
                    with col2:
                        st.metric("Avg Monthly Revenue", f"${ltv_metrics['average_monthly_revenue']:,.2f}")
                    with col3:
                        st.metric("Total Months", ltv_metrics['total_months'])
                    with col4:
                        st.metric("Revenue per Month", f"${ltv_metrics['total_revenue'] / ltv_metrics['total_months']:,.2f}" if ltv_metrics['total_months'] > 0 else "$0.00")
            
            # Data export
            st.subheader("Data Export")
            
            if st.button("Export Analysis Results"):
                exported_files = analyzer.export_data("churn_analysis_refactored")
                st.success(f"Data exported successfully! Files created: {', '.join(exported_files.values())}")
                
                for data_type, filepath in exported_files.items():
                    with open(filepath, 'r') as f:
                        st.download_button(
                            label=f"Download {data_type}",
                            data=f.read(),
                            file_name=filepath,
                            mime="text/csv"
                        )
            
            # Additional insights
            st.subheader("Additional Insights")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Duplication Summary**")
                dup_summary = analyzer.get_duplication_summary()
                st.write(f"Total customers: {dup_summary['total_customers']}")
                st.write(f"Unique customers: {dup_summary['unique_customers']}")
                st.write(f"Duplicate groups: {dup_summary['duplicate_groups']}")
                st.write(f"Customers in duplicates: {dup_summary['customers_in_duplicates']}")
            
            with col2:
                st.write("**Lesson Plan Summary**")
                lesson_summary = analyzer.get_lesson_plan_summary()
                if lesson_summary:
                    st.write(f"Total lessons: {lesson_summary['total_lessons']}")
                    st.write(f"Average monthly price: ${lesson_summary['average_monthly_price']:.2f}")
                    st.write(f"Total monthly revenue: ${lesson_summary['total_monthly_revenue']:.2f}")
                else:
                    st.write("No lesson plan data available")
            
        except Exception as e:
            st.error(f"Error during analysis: {str(e)}")
            st.exception(e)


def create_full_overview_chart(summary_df: pd.DataFrame) -> go.Figure:
    """Create full overview chart with all metrics"""
    fig = make_subplots(
        specs=[[{"secondary_y": True}]],
        subplot_titles=("Monthly Overview")
    )
    
    x = summary_df["Month"].astype(str)
    
    # Primary axis: Counts
    fig.add_trace(
        go.Scatter(
            name="Actives (start of month)",
            x=x, y=summary_df["Actives"],
            mode="lines+markers",
            hovertemplate="Month: %{x}<br>Actives: %{y:.0f}<extra></extra>",
        ),
        secondary_y=False,
    )
    
    fig.add_bar(name="Cancellations", x=x, y=summary_df["Cancellations"])
    fig.add_bar(name="Starts", x=x, y=summary_df["Starts"])
    
    # Secondary axis: Churn Rate
    churn_rate = summary_df["Churn_Rate"].astype(float)
    churn_rate = churn_rate.where(np.isfinite(churn_rate))
    
    fig.add_trace(
        go.Scatter(
            name="Churn Rate",
            x=x, y=churn_rate,
            mode="lines+markers",
            hovertemplate="Month: %{x}<br>Churn Rate: %{y:.2%}<extra></extra>",
        ),
        secondary_y=True,
    )
    
    fig.update_layout(
        barmode="group", 
        title="Monthly Overview: Starts, Cancellations, Actives, and Churn Rate"
    )
    
    fig.update_yaxes(title_text="Count", secondary_y=False)
    fig.update_yaxes(title_text="Churn Rate", tickformat=".0%", secondary_y=True)
    
    return fig


def create_starts_cancellations_chart(summary_df: pd.DataFrame) -> go.Figure:
    """Create chart showing starts vs cancellations"""
    fig = go.Figure()
    
    x = summary_df["Month"].astype(str)
    
    fig.add_bar(name="Cancellations", x=x, y=summary_df["Cancellations"])
    fig.add_bar(name="Starts", x=x, y=summary_df["Starts"])
    
    fig.update_layout(
        barmode="group", 
        title="Monthly Starts vs Cancellations",
        yaxis_title="Count"
    )
    
    return fig


def create_churn_rate_chart(summary_df: pd.DataFrame) -> go.Figure:
    """Create chart showing churn rate and actives"""
    fig = make_subplots(
        specs=[[{"secondary_y": True}]],
        subplot_titles=("Churn Rate & Actives")
    )
    
    x = summary_df["Month"].astype(str)
    
    # Primary axis: Actives
    fig.add_trace(
        go.Scatter(
            name="Actives (start of month)",
            x=x, y=summary_df["Actives"],
            mode="lines+markers",
            hovertemplate="Month: %{x}<br>Actives: %{y:.0f}<extra></extra>",
        ),
        secondary_y=False,
    )
    
    # Secondary axis: Churn Rate
    churn_rate = summary_df["Churn_Rate"].astype(float)
    churn_rate = churn_rate.where(np.isfinite(churn_rate))
    
    fig.add_trace(
        go.Scatter(
            name="Churn Rate",
            x=x, y=churn_rate,
            mode="lines+markers",
            hovertemplate="Month: %{x}<br>Churn Rate: %{y:.2%}<extra></extra>",
        ),
        secondary_y=True,
    )
    
    fig.update_layout(
        title="Monthly Churn Rate & Active Customers",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(t=60, r=20, b=40, l=50),
    )
    
    fig.update_yaxes(title_text="Actives", secondary_y=False)
    fig.update_yaxes(title_text="Churn Rate", tickformat=".0%", secondary_y=True)
    
    return fig


if __name__ == "__main__":
    main()
