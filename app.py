import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import Config
from analysis_manager import AnalysisManager
from filters import (FilterChain, AmountRangeFilter, DurationFilter, 
                    WeeklyFrequencyFilter, LessonTypeFilter)


def main():
    st.set_page_config(page_title="Business Analytics Dashboard", layout="wide")
    st.title("📊 Business Analytics Dashboard")
    st.markdown("**Customer Churn & Revenue Analysis**")
    
    config = Config()
    
    st.sidebar.header("⚙️ Analysis Configuration")

    st.sidebar.subheader("🔍 Data Filters")
    min_dur_months, max_dur_months = st.sidebar.slider(
        "Filter by Subscription Duration (Months)", 
        min_value=1,
        max_value=12,
        value=(1, 12),
        help="Only include customers with subscription duration in this range"
    )
    min_amount, max_amount = st.sidebar.slider(
        "Filter by Payment Amount ($)", 
        min_value=60, 
        max_value=2000,
        value=(60, 2000),
        help="Only include customers with payment amounts in this range",

    )
    times_a_week = st.sidebar.selectbox(
        "Weekly Lesson Frequency", 
        ['all', 1, 2], 
        index=0,
        help="Filter by how many times per week customers have lessons"
    )
    lesson_type = st.sidebar.selectbox(
        "Lesson Type", 
        ['all', 'Group', 'Private'], 
        index=0,
        help="Filter by lesson type (Group or Private lessons)"
    )
    from_month_input = st.sidebar.text_input(
        "From month (YYYY-MM)",
        value="2023-09",
        help="Trim charts and tables to show months from this month onward (display only)"
    )
    try:
        from_month_ts = pd.to_datetime(from_month_input + "-01")
    except Exception:
        from_month_ts = None

    filters = [AmountRangeFilter(min_amount, max_amount), DurationFilter(min_dur_months, max_dur_months)]
    if times_a_week != 'all':
        filters.append(WeeklyFrequencyFilter(times_a_week))
    if lesson_type != 'all':
        filters.append(LessonTypeFilter(lesson_type))

    with st.spinner("🔄 Loading and analyzing data..."):
        try:
            analyzer = AnalysisManager(filters)
            analyzer.load_data()
            analyzer.compute_churn_analysis()
            analyzer.compute_revenue_analysis()
 
            churn_summary = analyzer.get_churn_summary()
            revenue_by_month = analyzer.get_revenue_by_month()
            _, rrl_by_month = analyzer.compute_churned_revenue()

            analysis_summary = analyzer.get_analysis_summary()
            monthly_pay = analyzer.revenue_analysis_service._monthly_payments_df
            monthly_pay = monthly_pay[monthly_pay['month'] >= from_month_ts]

            lesson_summary = analyzer.get_lesson_plan_summary(monthly_pay)
            revenue_summary = analyzer.get_revenue_summary(monthly_pay)

            canceled_ids = set()
            # reconstruct canceled ids from rrl inputs by collecting all canceled map entries
            started_map, canceled_map = analyzer.churn_analysis_service.get_customer_data_by_month(
                analyzer._subscriptions_df,
                analyzer.churn_analysis_service.get_monthly_counts(analyzer._subscriptions_df)[2]
            )

            # Presentation-only trims (apply early as requested)
            if from_month_ts is not None:
                if not churn_summary.empty:
                    churn_summary = churn_summary[churn_summary['Month'] >= from_month_ts]
                if not revenue_by_month.empty:
                    revenue_by_month = revenue_by_month[revenue_by_month.index >= from_month_ts]
                if rrl_by_month is not None and not rrl_by_month.empty:
                    rrl_by_month = rrl_by_month[rrl_by_month['loss_month'] >= from_month_ts]
 
 
 
            st.sidebar.subheader("✅ Active Filters")
            for filter_desc in analyzer._filter_chain.get_active_filters():
                st.sidebar.write(f"• {filter_desc}")
 
            st.success("✅ Analysis completed successfully!")
 
            st.subheader("📈 Analysis Overview")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Customers", analysis_summary['total_subscriptions'])
            with col2:
                st.metric("Total Monthly Records", analysis_summary['total_monthly_records'])
            with col3:
                st.metric("Total New Customers", analysis_summary['total_starts'])
            with col4:
                st.metric("Total Cancellations", analysis_summary['total_cancellations'])
 
            st.subheader("📉 Customer Churn Analysis")
            tabs = st.tabs(["📊 Full Overview", "🔄 Starts vs Cancellations", "📈 Churn Rate & Active Customers", "💸 Churned Revenue", "💵 Revenue Chart"])
            
            with tabs[0]:
                fig = create_full_overview_chart(churn_summary)
                st.plotly_chart(fig, use_container_width=True)
                try:
                    st.download_button(
                        label="📥 Download Full Overview Chart (PNG)",
                        data=fig.to_image(format="png"),
                        file_name="churn_full_overview.png",
                        mime="image/png"
                    )
                except Exception:
                    st.info("📥 Chart download requires: `pip install kaleido`")

            with tabs[1]:
                fig = create_starts_cancellations_chart(churn_summary)
                st.plotly_chart(fig, use_container_width=True)

            with tabs[2]:
                fig = create_churn_rate_chart(churn_summary)
                st.plotly_chart(fig, use_container_width=True)

            with tabs[3]:
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                if rrl_by_month is not None and not rrl_by_month.empty:
                    x = rrl_by_month['loss_month'].dt.strftime('%Y-%m')
                    fig.add_trace(go.Bar(name='Revenue Lost', x=x, y=rrl_by_month['churned_rrl'], marker_color='#ef553b'), secondary_y=False)
                if not churn_summary.empty:
                    cs = churn_summary.copy()
                    cs['MonthStr'] = cs['Month'].dt.strftime('%Y-%m')
                    if rrl_by_month is not None and not rrl_by_month.empty:
                        cs = cs[cs['Month'] >= rrl_by_month['loss_month'].min()]
                    fig.add_trace(go.Scatter(name='Churn Rate', x=cs['MonthStr'], y=cs['Churn_Rate'], mode='lines+markers'), secondary_y=True)
                fig.update_layout(title="Churned Revenue and Churn Rate", barmode='group', height=450)
                fig.update_yaxes(title_text="Revenue Lost ($)", secondary_y=False)
                fig.update_yaxes(title_text="Churn Rate", tickformat=".0%", secondary_y=True)
                st.plotly_chart(fig, use_container_width=True)

            with tabs[4]:
                if not revenue_by_month.empty:
                    rev_df = revenue_by_month.reset_index()
                    rev_df.columns = ['Month', 'Revenue']
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=rev_df['Month'].dt.strftime('%Y-%m'), y=rev_df['Revenue'], marker_color='#00cc96', name='Revenue'))
                    fig.update_layout(title="Monthly Revenue", yaxis_title="Revenue ($)", height=400)
                    st.plotly_chart(fig, use_container_width=True)

            # Revenue analysis
            st.subheader("💰 Revenue Analysis")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Revenue", f"${revenue_summary['total_revenue']:,.2f}")
            with col2:
                st.metric("Average Monthly Revenue", f"${revenue_summary['revenue_range']['average']:,.2f}")
            with col3:
                st.metric("Total Customers", revenue_summary['total_customers'])
            with col4:
                st.metric("Analysis Months", revenue_summary['total_months'])
            col1, col2 = st.columns(2)
            with col1:
                st.write("**📊 Monthly Revenue Statistics**")
                st.write(f"• **Highest Monthly Revenue:** ${revenue_summary['revenue_range']['max']:,.2f}")
                st.write(f"• **Lowest Monthly Revenue:** ${revenue_summary['revenue_range']['min']:,.2f}")
                st.write(f"• **Average Monthly Revenue:** ${revenue_summary['revenue_range']['average']:,.2f}")
                st.write(f"• **Revenue Variability:** ${revenue_summary['revenue_range']['std']:,.2f}")
                st.write(f"\n• **Average Monthly Price:** ${revenue_summary['avg_monthly_price']:,.2f}")
            with col2:
                st.write("**📈 Revenue by Month (with Churned)**")
                rev_df = revenue_by_month.reset_index(); rev_df.columns = ['Month', 'Revenue']
                if rrl_by_month is not None and not rrl_by_month.empty:
                    cr = rrl_by_month.rename(columns={'loss_month':'Month','churned_rrl':'Churned_Revenue'})[['Month','Churned_Revenue']]
                    rev_df = rev_df.merge(cr, on='Month', how='left').fillna({'Churned_Revenue': 0.0})
                else:
                    rev_df['Churned_Revenue'] = 0.0
                st.dataframe(rev_df, use_container_width=True)
                st.download_button("Download Revenue Table (CSV)", data=rev_df.to_csv(index=False).encode('utf-8'), file_name="revenue_by_month.csv")


            # Revenue by lesson type (mean)
            with st.expander("🎯 Revenue by Lesson Type"):
                try:
                    mean_rev_by_lt = monthly_pay.groupby('lesson_type')['monthly_price'].sum().round(2).rename('Monthly_Revenue').reset_index()
                    st.dataframe(mean_rev_by_lt, use_container_width=True)
                    st.download_button("Download Revenue by Lesson Type (CSV)", data=mean_rev_by_lt.to_csv(index=False).encode('utf-8'), file_name="revenue_by_lesson_type.csv")
                except Exception:
                    st.write("Lesson type revenue unavailable.")

            # Churned revenue summary
            st.subheader("💸 Churned Revenue Summary")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Churned Revenue", f"${float(rrl_by_month['churned_rrl'].sum()):,.2f}")
                if rrl_by_month is not None and not rrl_by_month.empty:
                    st.write(f"• **Max Month:** ${rrl_by_month['churned_rrl'].max():,.2f}")
                    st.write(f"• **Min Month:** ${rrl_by_month['churned_rrl'].min():,.2f}")
                    st.write(f"• **Avg Month:** ${rrl_by_month['churned_rrl'].mean():,.2f}")
                    st.download_button("Download Churned Revenue by Month (CSV)", data=rrl_by_month.to_csv(index=False).encode('utf-8'), file_name="churned_revenue_by_month.csv")
            with col2:
                try:
                    canceled_ids.update([cid for dfm in canceled_map.values() for cid in dfm['cust_id'].dropna().unique()])
                    mp_canceled = monthly_pay[monthly_pay['cust_id'].isin(list(canceled_ids))]
                    churn_mean_by_lesson = mp_canceled.groupby('lesson_type')['monthly_price'].mean().round(2).rename('Avg_Monthly_Spend').reset_index()
                    st.write("**Mean Churned Revenue by Lesson Type**")
                    st.dataframe(churn_mean_by_lesson, use_container_width=True)
                    st.download_button("Download Churned Revenue by Lesson (CSV)", data=churn_mean_by_lesson.to_csv(index=False).encode('utf-8'), file_name="churned_revenue_by_lesson_type.csv")
                except Exception:
                    st.write("Lesson type stats unavailable.")

            # Churn summary section
            st.subheader("📜 Churn Summary (Key Stats)")
            if not churn_summary.empty:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Avg Churn Rate", f"{(churn_summary['Churn_Rate'].mean()*100):.2f}%")
                with col2:
                    st.metric("Max Churn Rate", f"{(churn_summary['Churn_Rate'].max()*100):.2f}%")
                with col3:
                    st.metric("Min Churn Rate", f"{(churn_summary['Churn_Rate'].min()*100):.2f}%")


            with st.expander("📄 Monthly Churn Summary (dataframe)"):
                nice_churn = churn_summary[['Month', 'Starts', 'Cancellations', 'Actives', 'Churn_Rate']].copy()
                nice_churn['Churn_Rate'] = (nice_churn['Churn_Rate'] * 100).round(2).astype(str) + '%'
                st.dataframe(nice_churn, use_container_width=True)
                st.download_button("Download Churn Summary (CSV)", data=churn_summary.to_csv(index=False).encode('utf-8'), file_name="churn_summary.csv")


            with st.expander("📄 Revenue Summary (dataframe)"):
                nice_revenue = rrl_by_month.merge(revenue_by_month, left_on='loss_month', right_on='month')
                st.dataframe(nice_revenue, use_container_width=True)
                st.download_button("Download Revenue Summary (CSV)", data=nice_revenue.to_csv(index=False).encode('utf-8'), file_name="revenue_summary.csv")


            # Started & Cancelled customers (separate expanders)
            with st.expander("👤 Started Customers by Month"):
                if from_month_ts is not None:
                    started_map = {k: v for k, v in started_map.items() if k.to_timestamp() >= from_month_ts}
                for m, dfm in started_map.items():
                    st.write(str(m), dfm[['cust_id', 'Customer Name', 'Customer Email']])
                if started_map:
                    all_started = pd.concat(started_map.values(), ignore_index=True)
                    st.download_button("Download Started Customers (CSV)", data=all_started[['cust_id','Customer Name','Customer Email']].to_csv(index=False).encode('utf-8'), file_name="started_customers.csv")
 
            with st.expander("🛑 Cancelled Customers by Month"):
                if from_month_ts is not None:
                    canceled_map = {k: v for k, v in canceled_map.items() if k.to_timestamp() >= from_month_ts}
                for m, dfm in canceled_map.items():
                    st.write(str(m), dfm[['cust_id', 'Customer Name', 'Customer Email']])
                if canceled_map:
                    all_canceled = pd.concat(canceled_map.values(), ignore_index=True)
                    st.download_button("Download Cancelled Customers (CSV)", data=all_canceled[['cust_id','Customer Name','Customer Email']].to_csv(index=False).encode('utf-8'), file_name="cancelled_customers.csv")

        except Exception as e:
            st.error(f"❌ Error during analysis: {str(e)}")
            st.exception(e)


            with st.expander("Lesson Plan Summary"):
                if lesson_summary:
                    st.write(f"Count of monthly payments: {lesson_summary['lesson_type_distribution']}")
                    st.write(f"Count of monthly payments: {lesson_summary['duration_distribution']}")
                    st.write(f"Count of monthly payments: {lesson_summary['frequency_distribution']}")
                    st.write(f"Average monthly price: ${lesson_summary['average_monthly_price']:.2f}")
                    st.write(f"Total monthly revenue: ${lesson_summary['total_monthly_revenue']:.2f}")
                    st.write(f"Count of monthly payments: {lesson_summary['total_monthly_payments']}")
                    fig =  payment_hist(lesson_summary['monthly_price_distribution'])
                    st.plotly_chart(fig, use_container_width=True)

                else:
                    st.write("No lesson plan data available")



        with st.expander("Duplication Summary"):
            dup_summary = analyzer.duplication_handler.get_duplication_summary()
            st.dataframe(dup_summary, use_container_width=True)

        st.subheader("📜 Analytical Raw Data")
        with st.expander("📄 Churn dataframe"):
            st.dataframe(analyzer._subscriptions_df, use_container_width=True)
            st.download_button("Download Churn Raw Data (CSV)", data=analyzer._subscriptions_df.to_csv(index=False).encode('utf-8'), file_name="churn_raw_data.csv")


        with st.expander("📄 Revenue Raw Data"):
            st.dataframe(analyzer._monthly_payments_df, use_container_width=True)
            st.download_button("Download Revenue Raw Data (CSV)", data=analyzer._monthly_payments_df.to_csv(index=False).encode('utf-8'), file_name="revenue_raw_data.csv")



def create_full_overview_chart(summary_df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]], subplot_titles=("Monthly Business Overview"))
    x = summary_df["Month"].astype(str)
    fig.add_trace(go.Scatter(name="Active Customers (start of month)", x=x, y=summary_df["Actives"], mode="lines+markers", hovertemplate="Month: %{x}<br>Active Customers: %{y:.0f}<extra></extra>"), secondary_y=False)
    fig.add_bar(name="New Customers", x=x, y=summary_df["Starts"])
    fig.add_bar(name="Cancellations", x=x, y=summary_df["Cancellations"])
    churn_rate = summary_df["Churn_Rate"].astype(float)
    churn_rate = churn_rate.where(np.isfinite(churn_rate))
    fig.add_trace(go.Scatter(name="Monthly Churn Rate", x=x, y=churn_rate, mode="lines+markers", hovertemplate="Month: %{x}<br>Churn Rate: %{y:.2%}<extra></extra>"), secondary_y=True)
    fig.update_layout(barmode="group", title="Monthly Business Overview: Customer Activity & Churn Rate", height=500)
    fig.update_yaxes(title_text="Number of Customers", secondary_y=False)
    fig.update_yaxes(title_text="Churn Rate", tickformat=".0%", secondary_y=True)
    return fig


def create_starts_cancellations_chart(summary_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    x = summary_df["Month"].astype(str)
    fig.add_bar(name="New Customers", x=x, y=summary_df["Starts"], marker_color='#00cc96')
    fig.add_bar(name="Cancellations", x=x, y=summary_df["Cancellations"], marker_color='#ef553b')
    fig.update_layout(barmode="group", title="Monthly Customer Growth: New vs Cancellations", yaxis_title="Number of Customers", height=400)
    return fig


def create_churn_rate_chart(summary_df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]], subplot_titles=("Customer Retention & Churn Rate"))
    x = summary_df["Month"].astype(str)
    fig.add_trace(go.Scatter(name="Active Customers (start of month)", x=x, y=summary_df["Actives"], mode="lines+markers", hovertemplate="Month: %{x}<br>Active Customers: %{y:.0f}<extra></extra>"), secondary_y=False)
    churn_rate = summary_df["Churn_Rate"].astype(float)
    churn_rate = churn_rate.where(np.isfinite(churn_rate))
    fig.add_trace(go.Scatter(name="Monthly Churn Rate", x=x, y=churn_rate, mode="lines+markers", hovertemplate="Month: %{x}<br>Churn Rate: %{y:.2%}<extra></extra>"), secondary_y=True)
    fig.update_layout(title="Customer Retention & Churn Rate Over Time", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), margin=dict(t=60, r=20, b=40, l=50), height=400)
    fig.update_yaxes(title_text="Active Customers", secondary_y=False)
    fig.update_yaxes(title_text="Churn Rate", tickformat=".0%", secondary_y=True)
    return fig


def payment_hist(x: pd.Series):
    x = x.dropna().astype(float)
    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=x,
            nbinsx=30,
            histnorm=None,  # None | 'percent' | 'probability density'
            name="Monthly payment",
            hovertemplate="Payment: %{x:.2f}<br>Value: %{y:.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        title="Distribution of Monthly Payments",
        xaxis_title="Monthly payment",
        yaxis_title="Customers",
        bargap=0.05,
        template="plotly_white",
        xaxis=dict(rangeslider=dict(visible=False)),
    )
    return fig


if __name__ == "__main__":
    main()

