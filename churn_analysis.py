# churn_analysis.py (excerpt)
from dataclasses import dataclass, field
from typing import Iterable, Optional, Union
import pandas as pd
from filtering_handler import FilteringHandler
from consts import start_at_col, canceled_at_col, ended_at_col,  email_col, name_col, status_col
from utils.duplication_analysis import DuplicationAnalysis
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

@dataclass
class ChurnAnalyzer:
    # Columns
    use_end_col: str = "Canceled At (UTC)",   # or "Ended At (UTC)"

    _df: Optional[pd.DataFrame] = None
    filtering: FilteringHandler = field(default_factory=FilteringHandler)

    def load(self, source: Union[str, pd.DataFrame]) -> "ChurnAnalyzer":
        df = pd.read_csv(source) if isinstance(source, str) else source.copy()
        self._assert(df)
        df[email_col] = df[email_col].str.lower()
        df[name_col] = df[name_col].str.lower()

        DuplicationAnalysis(df=df, write_at_init=True)

        for col in [start_at_col, canceled_at_col, ended_at_col]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        self._df = df

        return self


    def _assert(self, df: pd.DataFrame):
        if df.empty:
            raise ValueError("empty DataFrame")
        # guard for columns
        required_cols = [start_at_col, canceled_at_col, email_col, name_col, status_col] + [self.use_end_col]
        for col in required_cols:
            if col not in df.columns:
                raise KeyError(f"Missing column '{col}'.")


    def _get_months_range(self, df: pd.DataFrame,
                          from_month: Optional[pd.Period] = None,
                          to_month: Optional[pd.Period] = None):

        # derive monthly periods
        start_month = df[start_at_col].dt.to_period("M")
        end_month = df[self.use_end_col].dt.to_period("M")

        # bounds
        min_month = start_month.min()
        max_month = pd.concat([start_month.dropna(), end_month.dropna()]).max()

        if pd.isna(min_month) or pd.isna(max_month):
            # no dates
            return pd.DataFrame(columns=["Month","start_count","cancel_count","actives","churn_rate"])

        if from_month is None: from_month = min_month
        if to_month   is None: to_month   = max_month
        all_months = pd.period_range(from_month, to_month, freq="M")

        return start_month, end_month, all_months


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
        start_month, end_month, all_months = self._get_months_range(df, from_month, to_month)

        # monthly histograms
        starts = start_month.value_counts().sort_index().reindex(all_months, fill_value=0)
        cancels = end_month.value_counts().sort_index().reindex(all_months, fill_value=0)

        # cumulative up to previous month (base at start of month)
        cum_starts_prev  = starts.cumsum().shift(1, fill_value=0)
        cum_cancels_prev = cancels.cumsum().shift(1, fill_value=0)
        actives = (cum_starts_prev - cum_cancels_prev).astype("int64")

        # churn rate for the month
        churn_rate = (cancels / actives.replace(0, pd.NA)).astype("Float64")

        out = pd.DataFrame({
            "Month": all_months.to_timestamp(),
            "start_count": starts.values,
            "cancel_count": cancels.values,
            "actives": actives.values,
            "churn_rate": churn_rate.values,
        })
        return out

    def get_df(self) -> pd.DataFrame:
        return self.filtering.filter(self._df)


    def plot_full_monthly_churn_summary_full(self, summary_df: Optional[pd.DataFrame] = None):
        """Plot cancels and actives (bars/line) + show churn rate as text."""

        if summary_df is None:
            summary_df = self.compute_monthly_churn_summary()

        # Ensure numeric + handle NA for plotting
        actives = summary_df["actives"].astype(float)
        churn_rate = summary_df["churn_rate"].astype(float)  # Float64 -> float
        churn_rate = churn_rate.where(np.isfinite(churn_rate))  # keep NaN for gaps

        x = summary_df["Month"]

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


        fig.add_bar(name="Cancels", x=x, y=summary_df["cancel_count"])
        fig.add_bar(name="Starts", x=x, y=summary_df["start_count"])
        # Optional: annotate churn rate on top
        fig.update_layout(barmode="group", title="Monthly Starts, Cancels, Actives (and Churn Rate)")
        return fig



    def plot_monthly_churn_summary_start_end(self, summary_df: Optional[pd.DataFrame] = None):
        """Plot cancels and actives (bars/line) + show churn rate as text."""

        if summary_df is None:
            summary_df = self.compute_monthly_churn_summary()

        x = summary_df["Month"]
        fig = go.Figure()
        fig.add_bar(name="Cancels", x=x, y=summary_df["cancel_count"])
        fig.add_bar(name="Starts", x=x, y=summary_df["start_count"])
        #fig.add_scatter(name="Churn-Rate", x=x, y=summary_df["churn_rate"], mode="lines+markers")
        # Optional: annotate churn rate on top
        fig.update_layout(barmode="group", title="Monthly Starts, Cancels")
        return fig


    def plot_monthly_churn_summary(self, summary_df: Optional[pd.DataFrame] = None):
        """Plot Actives (left y-axis) and Churn Rate (right y-axis)."""

        if summary_df is None:
            summary_df = self.compute_monthly_churn_summary()

        # Ensure numeric + handle NA for plotting
        actives = summary_df["actives"].astype(float)
        churn_rate = summary_df["churn_rate"].astype(float)  # Float64 -> float
        churn_rate = churn_rate.where(np.isfinite(churn_rate))  # keep NaN for gaps

        x = summary_df["Month"]

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

