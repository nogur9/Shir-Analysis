import pandas as pd
import streamlit as st
from churn_analysis import ChurnAnalyzer
from filtering_handler import FilteringHandler
from exclusion_criteria import (RemoveTestInstances, RemoveSpecificCustomers, RemoveByStatus,
                                RemoveShortPeriod, RemoveNonPayments)
from consts import start_at_col, canceled_at_col, ended_at_col


st.set_page_config(page_title="Churn Dashboard", layout="wide")
st.title("Churn Dashboard")

source = "data/subscriptions.csv"

st.sidebar.header("Filters")
enable_test_instances = st.sidebar.checkbox("Exclude test instances (shir*)", value=False)
enable_remove_short_period = st.sidebar.checkbox("Exclude short period instances", value=False)
enable_remove_by_status = st.sidebar.checkbox("Exclude non - active\ cancelled instances", value=False)
enable_remove_non_payments = st.sidebar.checkbox("Exclude customers paid < 60", value=False)


id_col = st.sidebar.text_input("ID column (for explicit removals)", value="Customer ID")
ids_to_remove_txt = st.sidebar.text_area("IDs to remove (one per line)", value="")
ids_to_remove = [s.strip() for s in ids_to_remove_txt.splitlines() if s.strip()]

ending_column = st.sidebar.selectbox(label = "select canceled column", options=[canceled_at_col, ended_at_col])

# Build FilteringHandler dynamically
rules = []
if enable_test_instances:
    rules.append(RemoveTestInstances())
if enable_remove_short_period:
    rules.append(RemoveShortPeriod())
if enable_remove_by_status:
    rules.append(RemoveByStatus())
if ids_to_remove and id_col:
    rules.append(RemoveSpecificCustomers(ids_to_remove=ids_to_remove))
if enable_remove_non_payments:
    rules.append(RemoveNonPayments())

fh = FilteringHandler(rules)

with st.spinner("Analyzing..."):
    churn_analyser = ChurnAnalyzer(end_col=ending_column, filtering=fh).load(source)
    summary = churn_analyser.compute_monthly_churn_summary()

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

with st.expander("Diagnostics"):
    st.write("Number Of Instances:", churn_df.shape[0])
    st.dataframe(summary, use_container_width=True)

with st.expander("Describe"):
    summary.describe()

with st.expander("Cancelled List:"):
    for month in canceled_custs.keys():
        st.write("Canceled at :", month)
        st.dataframe(pd.DataFrame(canceled_custs[month]), use_container_width=True)


with st.expander("Started List:"):
    for month in started_custs.keys():
        st.write("Started at :", month)
        st.dataframe(pd.DataFrame(started_custs[month]), use_container_width=True)
