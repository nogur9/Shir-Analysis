import pandas as pd
import streamlit as st
from churn_analysis import ChurnAnalyzer
from filtering_handler import FilteringHandler
from exclusion_criteria import (RemoveTestInstances, RemoveSpecificCustomers, RemoveByStatus,
                                RemoveShortPeriod, RemoveNonPayments, RemoveByDuration, RemoveByAmount,
                                RemoveByWeekTimes, RemoveByLessonType)
from consts import start_at_col, canceled_at_col, ended_at_col


st.set_page_config(page_title="Churn Dashboard", layout="wide")
st.title("Churn Dashboard")

source = r"subscriptions.csv"

st.sidebar.header("Filters")
# enable_test_instances = st.sidebar.checkbox("Exclude test instances (shir*)", value=True)
# enable_remove_short_period = st.sidebar.checkbox("Exclude short period instances", value=True)
# enable_remove_by_status = st.sidebar.checkbox("Exclude non - active\ cancelled instances", value=True)
# enable_remove_non_payments = st.sidebar.checkbox("Exclude customers paid < 60", value=True)

min_dur_months, max_dur_months = st.sidebar.slider("Filter by Months", min_value=0, max_value=13,
                                                   value=(0, 13))
min_amount, max_amount = st.sidebar.slider("Filter by Amount", min_value=60, max_value=2000,
                                           value=(60, 2000))
times_a_week = st.sidebar.selectbox("Weekly Times", ['all', 1, 2], index=0)
l_type = st.sidebar.selectbox("Lesson Type", ['all', 'Group', 'Private'], index=0)

# id_col = st.sidebar.text_input("ID column (for explicit removals)", value="Customer ID")
# ids_to_remove_txt = st.sidebar.text_area("IDs to remove (one per line)", value="")
# ids_to_remove = [s.strip() for s in ids_to_remove_txt.splitlines() if s.strip()]

ending_column = st.sidebar.selectbox(label = "select canceled column", options=[canceled_at_col, ended_at_col])

# Build FilteringHandler dynamically
rules = [
    RemoveByAmount(min_amount, max_amount),
    RemoveByDuration(min_dur_months, max_dur_months)
]
# if enable_test_instances:
#     rules.append(RemoveTestInstances())
# if enable_remove_short_period:
#     rules.append(RemoveShortPeriod())
# if enable_remove_by_status:
#     rules.append(RemoveByStatus())
# if enable_remove_non_payments:
#     rules.append(RemoveNonPayments())
if times_a_week != 'all':
    rules.append(RemoveByWeekTimes(times_a_week))
if l_type != 'all':
    rules.append(RemoveByLessonType(l_type))


fh = FilteringHandler(rules)

with st.spinner("Analyzing..."):
    churn_analyser = ChurnAnalyzer(end_col=ending_column, filtering=fh).load(source)
    summary, rev_by_month = churn_analyser.compute_monthly_churn_summary()

st.subheader("Monthly Churn (Base + Cancels + Rate)")


# Tabs for each analysis
tabs = st.tabs(["Full Data", "Start-End", "Churn & Active"])

with tabs[0]:
    fig = churn_analyser.plot_full_monthly_churn_summary_full(summary)
    st.plotly_chart(fig, use_container_width=True)
with tabs[1]:
    fig = churn_analyser.plot_monthly_churn_summary_start_end(summary)
    st.plotly_chart(fig, use_container_width=True)
with tabs[2]:
    fig = churn_analyser.plot_monthly_churn_summary(summary)
    st.plotly_chart(fig, use_container_width=True)


churn_df, started_custs, canceled_custs = churn_analyser.get_data()
churned_revenue = churn_analyser.churned_revenue_rrl(canceled_custs)

with st.expander("Rev By Month"):
    st.dataframe(rev_by_month, use_container_width=True)

with st.expander("churned_revenue"):
    st.dataframe(churned_revenue, use_container_width=True)

coll = []
for month in canceled_custs.keys():
    coll.append(canceled_custs[month])
#pd.concat(coll).to_csv("canceled.csv", index=0)


# Cumulative sum (sum of all previous + current)
summary["Sum Started"] = summary["Starts"].expanding().sum()
summary["Sum Canceled"] = summary["Cancels"].expanding().sum()
summary["Average Churn Rate"] = summary["Churn_Rate"].expanding().mean()

#
# churn_analyser._df.to_csv("total_data.csv", index=0)
# churn_analyser.cm.to_csv("monthly_data.csv", index=0)
# summary.to_csv("summary_data.csv", index=0)

with st.expander("Diagnostics"):
    st.write("Number Of Instances:", churn_df.shape[0])
    st.dataframe(summary, use_container_width=True)

with st.expander("Describe"):
    st.write("Descriptive", churn_df.shape[0])

    st.dataframe(summary.describe(), use_container_width=True)


with st.expander("Cancelled List:"):
    for month in canceled_custs.keys():
        st.write("Canceled at :", month)
        st.dataframe(pd.DataFrame(canceled_custs[month]), use_container_width=True)


with st.expander("Started List:"):
    for month in started_custs.keys():
        st.write("Started at :", month)
        st.dataframe(pd.DataFrame(started_custs[month]), use_container_width=True)
