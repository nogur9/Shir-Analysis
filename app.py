# streamlit_app.py
import streamlit as st
import pandas as pd
from churn_analysis import ChurnAnalyzer
from filtering_handler import FilteringHandler
from exclusion_criteria import RemoveTestInstances, RemoveSpecificCustomers
from consts import start_at_col, canceled_at_col, ended_at_col


st.set_page_config(page_title="Churn Dashboard", layout="wide")
st.title("Churn Dashboard")

uploaded = st.file_uploader("Upload subscriptions CSV", type=["csv"])
use_sample = st.checkbox("Use sample file (data/subscriptions.csv)")

if not uploaded and not use_sample:
    st.info("Upload a CSV or tick 'Use sample file' to proceed.")
    st.stop()

source = "data/subscriptions.csv" if use_sample and not uploaded else uploaded

st.sidebar.header("Filters")
enable_test_instances = st.sidebar.checkbox("Exclude test instances (shir*)", value=True)

id_col = st.sidebar.text_input("ID column (for explicit removals)", value="Customer ID")
ids_to_remove_txt = st.sidebar.text_area("IDs to remove (one per line)", value="")
ids_to_remove = [s.strip() for s in ids_to_remove_txt.splitlines() if s.strip()]

ending_column = st.sidebar.selectbox(label = "select canceled column", options=[canceled_at_col, ended_at_col])

# Build FilteringHandler dynamically
rules = []
if enable_test_instances:
    rules.append(RemoveTestInstances())
if ids_to_remove and id_col:
    rules.append(RemoveSpecificCustomers(id_col=id_col, ids_to_remove=ids_to_remove))
fh = FilteringHandler(rules)

with st.spinner("Analyzing..."):
    an = ChurnAnalyzer(filtering=fh, use_end_col=ending_column).load(source)
    summary = an.compute_monthly_churn_summary()

st.subheader("Monthly Churn (Base + Cancels + Rate)")
st.dataframe(summary, use_container_width=True)

fig = an.plot_monthly_churn_summary(summary)
st.plotly_chart(fig, use_container_width=True)

with st.expander("Diagnostics"):
    st.write("Active rules:", [r.__class__.__name__ for r in fh.rules] or "None")
    st.write("Columns present:", list(an.get_df().columns))

