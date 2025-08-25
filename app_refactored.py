import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

from churn_analyzer import ChurnAnalyzer
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
            analyzer = ChurnAnalyzer(end_column=ending_column)
            
            # Load data
            analyzer.load_data()
            
            # Apply filters
            analyzer.set_filters(filter_chain)
            
            # Compute analysis
            analyzer.compute_churn_analysis()
            
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

