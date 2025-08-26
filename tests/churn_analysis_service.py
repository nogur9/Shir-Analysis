# Simple, runnable test for the uploaded dataset at /mnt/data/subscriptions.csv
# It builds a minimal churn-analysis service using your column mapping,
# runs the month-by-month churn summary, prints key checks,
# and saves the result to /mnt/data/churn_summary.csv for download.

import pandas as pd
import numpy as np

# ---- Minimal config helper matching your interface ----
class DummyConfig:
    def __init__(self, columns_map: dict):
        self.columns_map = columns_map

    def get_column(self, key: str) -> str:
        # Mirror the "logical -> physical" behavior
        if key not in self.columns_map:
            raise KeyError(f"Config missing key: {key}")
        return self.columns_map[key]



# ---- Load the uploaded dataset ----
csv_path = "/mnt/data/subscriptions.csv"
df = pd.read_csv(csv_path)

# Parse dates if columns exist
for c in [COLUMNS["start_date"], COLUMNS["canceled_date"], COLUMNS["ended_date"]]:
    if c in df.columns:
        df[c] = pd.to_datetime(df[c], errors='coerce')

# ---- Run the test ----
service = ChurnAnalysisService(DummyConfig(COLUMNS))
service.set_data(df)

summary_df, revenue_by_month = service.compute_monthly_churn_summary()

# ---- Lightweight sanity checks ----
print("\n[checks] Summary rows:", len(summary_df))
if len(summary_df) > 0:
    min_actives = int(summary_df["Actives"].min())
    print("[checks] Min Actives in window:", min_actives)
    if (summary_df["Actives"] <= 0).any():
        print("[warn] Found non-positive Actives inside trimmed window.")

    # Basic churn bounds check (not strict, but informative)
    over_one = summary_df.loc[summary_df["Churn_Rate"] > 1, "Churn_Rate"]
    if not over_one.empty:
        print(f"[warn] {len(over_one)} month(s) have churn rate > 1. Investigate data quality.")

# Show a preview
print("\n[preview] Head of monthly summary:")
print(summary_df.head(10))

# Save result for download and display full table
out_path = "/mnt/data/churn_summary.csv"
summary_df.to_csv(out_path, index=False)
display_dataframe_to_user("Monthly Churn Summary", summary_df)

if revenue_by_month is not None:
    # save revenue as well
    rev_path = "/mnt/data/revenue_by_month.csv"
    revenue_by_month.to_csv(rev_path, header=["Revenue"])
    print(f"\nSaved revenue_by_month to {rev_path}")

print(f"\nSaved summary to {out_path}")
