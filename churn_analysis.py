# churn_analysis.py (excerpt)
from dataclasses import dataclass, field
from typing import Iterable, Optional, Union
import pandas as pd
from filtering_handler import FilteringHandler
from consts import start_at_col, canceled_at_col, ended_at_col

@dataclass
class ChurnAnalyzer:
    # Columns
    use_end_col: str = "Canceled At (UTC)",   # or "Ended At (UTC)"

    _df: Optional[pd.DataFrame] = None
    filtering: FilteringHandler = field(default_factory=FilteringHandler)

    def load(self, source: Union[str, pd.DataFrame]) -> "ChurnAnalyzer":
        df = pd.read_csv(source) if isinstance(source, str) else source.copy()
        self._assert(df)

        for col in [start_at_col, canceled_at_col, ended_at_col]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        self._df = df

        return self
    def _assert(self, df: pd.DataFrame):
        if df.empty:
            raise ValueError("empty DataFrame")
        # guard for columns
        if start_at_col not in df.columns:
            raise KeyError(f"Missing start column '{start_at_col}'.")
        if self.use_end_col not in df.columns:
            raise KeyError(f"Missing end column '{self.use_end_col}'.")

    # ---- Your original counts-only (kept, optional) ----
    def compute_monthly_churn(self) -> pd.DataFrame:
        # ... (unchanged from last message)
        # returns ["Churn Month", "Churn Count"]
        ...

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

    def plot_monthly_churn_summary(self, summary_df: Optional[pd.DataFrame] = None):
        """Plot cancels and actives (bars/line) + show churn rate as text."""
        import plotly.graph_objects as go

        if summary_df is None:
            summary_df = self.compute_monthly_churn_summary()

        x = summary_df["Month"]
        fig = go.Figure()
        fig.add_bar(name="Cancels", x=x, y=summary_df["cancel_count"])
        fig.add_bar(name="Starts", x=x, y=summary_df["start_count"])
        fig.add_scatter(name="Actives (start of month)", x=x, y=summary_df["actives"], mode="lines+markers")
        # Optional: annotate churn rate on top
        fig.update_layout(barmode="group", title="Monthly Starts, Cancels, Actives (and Churn Rate)")
        return fig
