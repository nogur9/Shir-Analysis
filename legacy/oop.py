# churn_analysis.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Union
import pandas as pd

# Type alias for a row-filter. It receives the current DataFrame and must return a BOOLEAN MASK (pd.Series[bool])
RowFilter = Callable[[pd.DataFrame], pd.Series]

@dataclass
class ChurnAnalyzer:
    # Column names (override if your CSV schema changes)
    status_col: str = "Status"
    canceled_at_col: str = "Canceled At (UTC)"
    ended_at_col: str = "Ended At (UTC)"
    churn_status_values: Iterable[str] = field(default_factory=lambda: ["canceled"])

    # Internal state
    df: Optional[pd.DataFrame] = None
    _filters: Dict[str, RowFilter] = field(default_factory=dict)

    # ------------- Data IO -------------
    def load(self, source: Union[str, pd.DataFrame]) -> "ChurnAnalyzer":
        """
        Load data either from a CSV path or from an existing DataFrame.
        """
        if isinstance(source, str):
            df = pd.read_csv(source)
        else:
            df = source.copy()

        # Parse datetime columns safely
        for col in [self.canceled_at_col, self.ended_at_col]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        self.df = df
        return self

    # ------------- Filters -------------
    def add_filter(self, name: str, func: RowFilter) -> "ChurnAnalyzer":
        """
        Register a named filter. Filters are AND-ed together.
        """
        self._filters[name] = func
        return self

    def remove_filter(self, name: str) -> "ChurnAnalyzer":
        self._filters.pop(name, None)
        return self

    def clear_filters(self) -> "ChurnAnalyzer":
        self._filters.clear()
        return self

    def remove_customers(self, customer_col: str, bad_customers: Iterable[str]) -> "ChurnAnalyzer":
        """
        Convenience helper: exclude a list of customers by ID/name.
        """
        def _f(df: pd.DataFrame) -> pd.Series:
            if customer_col not in df.columns:
                # If column missing, keep all
                return pd.Series(True, index=df.index)
            return ~df[customer_col].astype(str).isin(set(map(str, bad_customers)))
        return self.add_filter(f"exclude_{customer_col}", _f)

    def apply_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply all registered filters (logical AND). If no filters, returns df unchanged.
        """
        if not self._filters:
            return df
        mask = pd.Series(True, index=df.index)
        for name, f in self._filters.items():
            m = f(df)
            if not isinstance(m, pd.Series) or m.dtype != bool or len(m) != len(df):
                raise ValueError(f"Filter '{name}' must return a boolean Series aligned to df.")
            mask &= m
        return df.loc[mask].copy()

    # ------------- Core analysis -------------
    def compute_monthly_churn(self) -> pd.DataFrame:
        """
        Returns a DataFrame with ['Churn Month', 'Churn Count'] based on:
        - status in churn_status_values
        - churn date = Ended At if present else Canceled At
        - optional filters applied before computing churn
        """
        if self.df is None:
            raise RuntimeError("No data loaded. Call .load(...) first.")

        df = self.apply_filters(self.df)

        # Filter churned status
        churned = df[df[self.status_col].astype(str).str.lower().isin(
            {s.lower() for s in self.churn_status_values}
        )].copy()

        if churned.empty:
            # Return an empty but well-formed frame
            return pd.DataFrame(columns=["Churn Month", "Churn Count"])

        # Churn date: prefer Ended At, else Canceled At
        ended = churned.get(self.ended_at_col)
        canceled = churned.get(self.canceled_at_col)
        if ended is None and canceled is None:
            raise KeyError(
                f"Neither '{self.ended_at_col}' nor '{self.canceled_at_col}' exist in the dataset."
            )

        churned["Churn Date"] = (
            (ended if ended is not None else pd.Series(pd.NaT, index=churned.index))
            .combine_first(canceled if canceled is not None else pd.Series(pd.NaT, index=churned.index))
        )

        churned = churned.dropna(subset=["Churn Date"]).copy()
        if churned.empty:
            return pd.DataFrame(columns=["Churn Month", "Churn Count"])

        churned["Churn Month"] = churned["Churn Date"].dt.to_period("M")
        monthly = (
            churned.groupby("Churn Month", observed=True)
                   .size()
                   .reset_index(name="Churn Count")
                   .sort_values("Churn Month")
        )
        # Ensure a pandas Period is converted to Timestamp start-of-month for compatibility with plotting libs
        monthly["Churn Month"] = monthly["Churn Month"].dt.to_timestamp()
        return monthly

    # ------------- Convenience plotting (Plotly) -------------
    def plot_monthly_churn(self, monthly_df: Optional[pd.DataFrame] = None):
        """
        Returns a Plotly figure for monthly churn counts.
        """
        import plotly.express as px

        if monthly_df is None:
            monthly_df = self.compute_monthly_churn()

        fig = px.bar(
            monthly_df,
            x="Churn Month",
            y="Churn Count",
            title="Monthly Churn Count",
            labels={"Churn Month": "Month", "Churn Count": "Churned Subscriptions"},
            text="Churn Count",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(xaxis_title=None, yaxis_title=None)
        return fig
