from dataclasses import dataclass, field
from typing import Optional, Union, Tuple, Dict
import pandas as pd
from filtering_handler import FilteringHandler
from consts import (start_at_col, canceled_at_col, ended_at_col,  email_col,
                    name_col, status_col, fixes)
from consts import new_cust
from duplication_analysis import DuplicationAnalysis
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime

@dataclass
class ChurnAnalyzer:
    # Columns
    end_col: str = "Canceled At (UTC)",   # or "Ended At (UTC)"
    filtering: FilteringHandler = field(default_factory=FilteringHandler)
    duplicates_analyser: Optional[DuplicationAnalysis] = None
    started_custs: Optional[Dict] = None
    canceled_custs: Optional[Dict] = None
    _df: Optional[pd.DataFrame] = None


    def load(self, source: Union[str, pd.DataFrame]) -> "ChurnAnalyzer":
        df = pd.read_csv(source).copy()
        self._assert(df)
        df[email_col] = df[email_col].str.lower()
        df[name_col] = df[name_col].str.lower()
        df = self.fix_and_add(df)

        df['cust_id'] = df[name_col] + '-' + df[email_col]


        for col in [start_at_col, canceled_at_col, ended_at_col]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        df = df[df[start_at_col] <= datetime.datetime.strptime("31/7/2025", "%d/%m/%Y")]
        df.loc[df[canceled_at_col] > datetime.datetime.strptime("31/7/2025", "%d/%m/%Y"), canceled_at_col] = pd.NaT
        df.loc[df[ended_at_col] > datetime.datetime.strptime("31/7/2025", "%d/%m/%Y"), ended_at_col] = pd.NaT
        self.duplicates_analyser = DuplicationAnalysis(df=df, end_col=self.end_col)
        self._df = self.duplicates_analyser.handle_duplications()

        return self

    def fix_and_add(self, df):
        df_new_cust = pd.DataFrame([new_cust])
        for cust in fixes:
            if 'start_date' in cust.keys():
                df.loc[df[email_col] == cust['email'], start_at_col] = cust['start_date']
            elif 'end_date' in cust.keys():
                df.loc[df[email_col] == cust['email'], ended_at_col] = cust['end_date']
                df.loc[df[email_col] == cust['email'], canceled_at_col] = cust['end_date']

        return pd.concat([df, df_new_cust])

    def _assert(self, df: pd.DataFrame):
        if df.empty:
            raise ValueError("empty DataFrame")
        # guard for columns
        required_cols = [start_at_col, canceled_at_col,
                         email_col, name_col, status_col] + [self.end_col]
        for col in required_cols:
            if col not in df.columns:
                raise KeyError(f"Missing column '{col}'.")

    @staticmethod
    def is_active(row, month):
        started_before = row['Start Date (UTC)'] <= month.start_time
        ended_after = row['Canceled At (UTC)'] >= month.start_time or \
                      pd.isnull(row['Canceled At (UTC)'])
        return started_before and ended_after


    def _get_data_per_month(self, df: pd.DataFrame, all_months):
        started_custs = {}
        canceled_custs = {}
        actives_per_months = []

        for month in all_months:
            active_amount = df.apply(self.is_active, args=[month], axis=1)
            actives_per_months.append(active_amount.sum())

            started_custs[month] = df[df['start_month'] == month][['start_month', email_col, name_col]]
            canceled_custs[month] = df[df['cancel_month'] == month][['cancel_month' ,email_col, name_col]]

        self.started_custs = started_custs
        self.canceled_custs = canceled_custs
        return actives_per_months


    def _get_months_range(self, df: pd.DataFrame,
                          from_month: Optional[pd.Period] = None,
                          to_month: Optional[pd.Period] = None):
        # derive monthly periods
        df['start_month'] = df[start_at_col].dt.to_period('M')
        start_month = df[start_at_col].dt.to_period("M")

        df['cancel_month'] = df[self.end_col].dt.to_period('M')
        cancel_month = df[self.end_col].dt.to_period("M")

        # bounds
        min_month = start_month.min()
        max_month = pd.concat([start_month.dropna(), cancel_month.dropna()]).max()

        if from_month is None: from_month = min_month
        if to_month   is None: to_month   = max_month

        analysis_range = {
            "start": min(df['start_month'].min(), df['cancel_month'].min()),
            "end": max(df['start_month'].max(), df['cancel_month'].max())
        }
        all_months = pd.period_range(analysis_range["start"], analysis_range["end"])

        # monthly histograms
        cn_miss_months = [i for i in all_months if i not in cancel_month.value_counts().index]
        cn_miss_df = pd.Series(index=cn_miss_months, data=[0] * len(cn_miss_months))

        # monthly histograms
        st_miss_months = [i for i in all_months if i not in start_month.value_counts().index]
        st_miss_df = pd.Series(index=st_miss_months, data=[0] * len(st_miss_months))


        cancels = pd.concat([cn_miss_df, cancel_month.value_counts()]).sort_index()
        starts = pd.concat([st_miss_df, start_month.value_counts()]).sort_index()

        self._df = df
        return cancels, starts, all_months


    # ---- New: business-friendly base + cancels + churn rate ----
    def compute_monthly_churn_summary(
        self,
        from_month: Optional[pd.Period] = None,
        to_month: Optional[pd.Period] = None,
    ) -> pd.DataFrame:
        """
        Returns monthly:
        ["Month", "start_count", "cancel_count", "actives", "churn_rate"]

        Definitions:
        - start_count: number of subscriptions with start_at in that month
        - cancel_count: number of subscriptions with end_at in that month
        - actives: active base at the *start* of the month
                   = cumulative_starts_through_prev_month - cumulative_cancels_through_prev_month
        - churn_rate: cancel_count / actives  (NaN if actives==0)

        Notes:
        - 'use_end_col' can be 'Canceled At (UTC)' or 'Ended At (UTC)' depending on your export semantics.
        - Applies FilteringHandler before computing metrics.
        """
        df = self.filtering.filter(self._df)
        cancels, starts, all_months = self._get_months_range(df, from_month, to_month)

        actives_per_months = self._get_data_per_month(df, all_months)

        out = pd.DataFrame({
            "Month": starts.index,
            "Starts": starts.values,
            "Cancels": cancels.values,
            "Actives": actives_per_months,
        })

        out['Churn_Rate'] = (out["Cancels"] / out["Actives"])
        out = out.sort_values("Month")
        return out

    def get_data(self) -> Tuple[pd.DataFrame, Dict, Dict]:
        return (self.filtering.filter(self._df),
                self.started_custs,
                self.canceled_custs)


    def plot_full_monthly_churn_summary_full(self, summary_df: Optional[pd.DataFrame] = None):
        """Plot cancels and actives (bars/line) + show churn rate as text."""

        if summary_df is None:
            summary_df = self.compute_monthly_churn_summary()

        # Ensure numeric + handle NA for plotting
        actives = summary_df["Actives"].astype(float)
        churn_rate = summary_df["Churn_Rate"].astype(float)  # Float64 -> float
        churn_rate = churn_rate.where(np.isfinite(churn_rate))  # keep NaN for gaps

        x = summary_df["Month"].astype(str)

        fig = make_subplots(
            specs=[[{"secondary_y": True}]],
            # subplot_titles=("Monthly Actives and Churn Rate",)
        )

        # Left axis: Actives (line)
        fig.add_trace(
            go.Scatter(
                name="Actives (start of month)",
                x=x, y=actives,
                mode="lines+markers",
                hovertemplate="Month: %{x|%Y-%m}<br>Actives: %{y:.0f}<extra></extra>",
            ),
            secondary_y=False,
        )

        # Right axis: Churn Rate (line, %)
        fig.add_trace(
            go.Scatter(
                name="Churn Rate",
                x=x, y=churn_rate,
                mode="lines+markers",
                hovertemplate="Month: %{x|%Y-%m}<br>Churn Rate: %{y:.2%}<extra></extra>",
            ),
            secondary_y=True,
        )

        fig.add_bar(name="Cancels", x=x, y=summary_df["Cancels"])
        fig.add_bar(name="Starts", x=x, y=summary_df["Starts"])
        # Optional: annotate churn rate on top
        fig.update_layout(barmode="group", title="Monthly Starts, Cancels, Actives (and Churn Rate)")
        return fig



    def plot_monthly_churn_summary_start_end(self, summary_df: Optional[pd.DataFrame] = None):
        """Plot cancels and actives (bars/line) + show churn rate as text."""

        if summary_df is None:
            summary_df = self.compute_monthly_churn_summary()

        x = summary_df["Month"].astype(str)
        fig = go.Figure()
        fig.add_bar(name="Cancels", x=x, y=summary_df["Cancels"])
        fig.add_bar(name="Starts", x=x, y=summary_df["Starts"])
        #fig.add_scatter(name="Churn-Rate", x=x, y=summary_df["churn_rate"], mode="lines+markers")
        # Optional: annotate churn rate on top
        fig.update_layout(barmode="group", title="Monthly Starts, Cancels")
        return fig


    def plot_monthly_churn_summary(self, summary_df: Optional[pd.DataFrame] = None):
        """Plot Actives (left y-axis) and Churn Rate (right y-axis)."""

        if summary_df is None:
            summary_df = self.compute_monthly_churn_summary()

        # Ensure numeric + handle NA for plotting
        actives = summary_df["Actives"].astype(float)
        churn_rate = summary_df["Churn_Rate"].astype(float)  # Float64 -> float
        churn_rate = churn_rate.where(np.isfinite(churn_rate))  # keep NaN for gaps

        x = summary_df["Month"].astype(str)

        fig = make_subplots(
            specs=[[{"secondary_y": True}]],
            #subplot_titles=("Monthly Actives and Churn Rate",)
        )

        # Left axis: Actives (line)
        fig.add_trace(
            go.Scatter(
                name="Actives (start of month)",
                x=x, y=actives,
                mode="lines+markers",
                hovertemplate="Month: %{x|%Y-%m}<br>Actives: %{y:.0f}<extra></extra>",
            ),
            secondary_y=False,
        )

        # Right axis: Churn Rate (line, %)
        fig.add_trace(
            go.Scatter(
                name="Churn Rate",
                x=x, y=churn_rate,
                mode="lines+markers",
                hovertemplate="Month: %{x|%Y-%m}<br>Churn Rate: %{y:.2%}<extra></extra>",
            ),
            secondary_y=True,
        )

        fig.update_layout(
            title="Monthly Actives and Churn Rate",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(t=60, r=20, b=40, l=50),
        )

        fig.update_yaxes(title_text="Actives", secondary_y=False)
        fig.update_yaxes(title_text="Churn Rate", tickformat=".0%", secondary_y=True)

        return fig

