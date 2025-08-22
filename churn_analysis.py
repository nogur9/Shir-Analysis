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
from lesson_types import find_class_type
from pandas.tseries.offsets import DateOffset



@dataclass
class ChurnAnalyzer:
    # Columns
    end_col: str = "Canceled At (UTC)",   # or "Ended At (UTC)"
    filtering: FilteringHandler = field(default_factory=FilteringHandler)
    duplicates_analyser: Optional[DuplicationAnalysis] = None
    started_custs: Optional[Dict] = None
    canceled_custs: Optional[Dict] = None
    _df: Optional[pd.DataFrame] = None
    monthly_payment_df: Optional[pd.DataFrame] = None

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

        df = self.filtering.load(df)
        self.duplicates_analyser = DuplicationAnalysis(df=df, end_col=self.end_col)
        self._df = self.duplicates_analyser.handle_duplications()
        self.cm = self.build_payments_monthly(self.filtering.new_pay_df, df)
        return self

    # Assumptions about columns; rename if yours differ
    # new_pay_df columns: [cust_id, payment_date, Amount, ...]
    # customers_df (after your duplication-cleaner): [customer_id, start_at_col, canceled_at_col, ...]
    # Your enums: lesson.months  (int). We'll use your `find_class_type(amount)`.

    def _clip_periods_to_next_start(self, df: pd.DataFrame, by: list):
        """
        Ensure no overlap across consecutive plans in the same group (e.g., per customer).
        For each group, set end = min(original_end, next_start - 1 day).
        """
        df = df.sort_values(by + [start_at_col]).copy()
        next_start = df.groupby(by)[start_at_col].shift(-1)
        df[canceled_at_col] = pd.to_datetime(df[canceled_at_col])

        # If a next plan starts earlier than our end, clip
        mask = next_start.notna() & (df[canceled_at_col].notna())
        df.loc[mask, canceled_at_col] = df.loc[mask, [canceled_at_col]].min(axis=1)
        # But also clip to the day before next_start if that is earlier
        df.loc[mask, canceled_at_col] = pd.concat([
            df.loc[mask, canceled_at_col],
            (pd.to_datetime(next_start[mask]) - pd.Timedelta(days=1))
        ], axis=1).min(axis=1)

        return df

    def _month_floor(self, ts):  # normalize to month start
        return pd.to_datetime(ts).values.astype('datetime64[M]').astype('datetime64[ns]')

    def build_payments_monthly(self,
            new_pay_df: pd.DataFrame,
            customers_df: Optional[pd.DataFrame] = None,
            cust_col: str = "cust_id",
            payment_date_col: str = start_at_col,
            amount_col: str = "Amount",
    ):
        """
        1) Map each payment to (Lesson, months, monthly_price)
        2) Build a contract period per payment: [contract_start, contract_end]
        3) Clip contract_end to either next plan start (same customer) - 1 day, or to customer cancel date (if provided)
        4) Expand to months per customer with the monthly price in effect for that month
        """
        pay = new_pay_df.copy()

        # 1) lesson & monthly price
        pay["Lesson"] = pay[amount_col].apply(find_class_type)  # your function
        pay = pay[pay["Lesson"].notna()]
        pay["months"] = pay["Lesson"].apply(lambda L: L.months if pd.notna(L) else None)
        pay["monthly_price"] = pay[amount_col] / pay["months"]

        # 2) contract period bounds
        pay["contract_start"] = pd.to_datetime(pay[payment_date_col])
        # end = start + months - 1 day
        pay["contract_end"] = pay["contract_start"] + pay["months"].apply(
            lambda m: DateOffset(months=m)) - pd.Timedelta(days=1)

        # 3) clip to cancellation if provided
        if customers_df is not None and canceled_at_col in customers_df.columns:
            cancels = customers_df[[cust_col, canceled_at_col]].drop_duplicates()
            cancels = cancels.rename(columns={canceled_at_col: "cancel_at"})
            pay = pay.merge(cancels, on=cust_col, how="left")
            pay["cancel_at"] = pd.to_datetime(pay["cancel_at"])
            # if canceled earlier than contract_end, clip
            mask_cancel = pay["cancel_at"].notna()
            pay.loc[mask_cancel, "contract_end"] = pd.concat([
                pay.loc[mask_cancel, "contract_end"],
                pay.loc[mask_cancel, "cancel_at"]
            ], axis=1).min(axis=1)
        else:
            pay["cancel_at"] = pd.NaT

        # Clip to next plan switch in the same customer
        pay = self._clip_periods_to_next_start(
            pay, by=[cust_col]
        )

        # Remove any rows with inverted periods (e.g., switch+cancel same day)
        pay = pay[pay["contract_end"] >= pay["contract_start"]].copy()

        # 4) expand to months
        # Build month index per row
        pay["month_start"] = self._month_floor(pay["contract_start"])
        pay["month_end"] = self._month_floor(pay["contract_end"])

        # period_range inclusive: we include both month_start and month_end
        pay["month_list"] = pay.apply(
            lambda r: pd.period_range(
                pd.Period(r["month_start"], freq="M"),
                pd.Period(r["month_end"], freq="M"),
                freq="M"
            ).to_timestamp(),
            axis=1
        )
        exploded = pay.explode("month_list", ignore_index=True)
        exploded = exploded.rename(columns={"month_list": "month"})
        exploded = exploded[[cust_col, "month", "Lesson", "monthly_price", "contract_start"]]

        # In rare cases with multiple rows for same customer×month (e.g., 2 payments in same month),
        # keep the one with the latest contract_start (the newer plan in effect).
        exploded = exploded.sort_values([cust_col, "month", "contract_start"])
        exploded = exploded.groupby([cust_col, "month"], as_index=False).tail(1)

        return exploded  # columns: customer_id, month, Lesson, monthly_price


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

            started_custs[month] = df[df['start_month'] == month][['start_month', email_col, name_col, 'cust_id']]
            canceled_custs[month] = df[df['cancel_month'] == month][['cancel_month' ,email_col, name_col, 'cust_id']]

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
        avg_monthly_rev, rev_by_month = self.average_monthly_revenue()

        #out["rev_by_month"] = rev_by_month

        out = out.sort_values("Month")

        return out, rev_by_month


    def average_monthly_revenue(self):
        rev_by_month = self.cm.groupby("month")["monthly_price"].sum()
        return rev_by_month.mean(), rev_by_month

    import pandas as pd

    def churned_revenue_rrl(
            self,
            canceled_custs: dict,
            cust_col: str = "cust_id",
            month_col: str = "month",
            price_col: str = "monthly_price",
            bill_timing: str = "in_advance",  # "in_advance" -> loss next month; "in_arrears" -> loss same month
    ):
        """
        Compute Recurring Revenue Lost (RRL) by month, given:
          - cm: customer×month table with a row per active month and the price in effect
          - canceled_custs: {Timestamp('YYYY-MM-01'): [cust_id, ...], ...}

        Returns:
          total_rrl, rrl_by_month (DataFrame with ['loss_month','churned_rrl'])
        """

        # 1) Build a (customer, cancel_month) DataFrame from your dict
        #    Ensure month is normalized to month-begin Timestamp (ns):
        cancel_rows = []
        for m, custs in canceled_custs.items():
            m_norm = m.to_timestamp()

            for cid in custs:
                cancel_rows.append({cust_col: cid, "cancel_month": m_norm})
        cancels = pd.DataFrame(cancel_rows)
        if cancels.empty:
            return 0.0, pd.DataFrame(columns=["loss_month", "churned_rrl"])

        # 2) Join cm to bring in each customer's monthly prices
        #    We'll match each cancel record to all months for that customer, then filter to months <= cancel_month
        cm_sub = self.cm[[cust_col, month_col, price_col]].copy()
        cancels = cancels.merge(cm_sub, on=cust_col, how="left")

        # 3) Keep only the months at or before the cancel month
        cancels = cancels[cancels[month_col] <= cancels["cancel_month"]]

        # If a customer somehow has no price history up to cancel (data gap), drop or impute 0
        if cancels.empty:
            return 0.0, pd.DataFrame(columns=["loss_month", "churned_rrl"])

        # 4) For each (customer, cancel_month), take the *last* (max) month row ⇒ last known price at/ before cancel
        cancels = cancels.sort_values([cust_col, "cancel_month", month_col])
        last_price_at_cancel = (
            cancels.groupby([cust_col, "cancel_month"], as_index=False)
            .tail(1)[[cust_col, "cancel_month", price_col]]
        )

        # 5) Decide which month gets the loss
        if bill_timing == "in_advance":
            # customers pay at the beginning of the month ⇒ losing them affects the *next* month’s recurring revenue
            last_price_at_cancel["loss_month"] = (
                    last_price_at_cancel["cancel_month"] + pd.offsets.MonthBegin(1)
            )
        elif bill_timing == "in_arrears":
            # billed at the end of the month ⇒ losing them affects the *same* month
            last_price_at_cancel["loss_month"] = last_price_at_cancel["cancel_month"]
        else:
            raise ValueError("bill_timing must be 'in_advance' or 'in_arrears'")

        # 6) Aggregate
        rrl_by_month = (
            last_price_at_cancel.groupby("loss_month")[price_col]
            .sum()
            .rename("churned_rrl")
            .reset_index()
            .sort_values("loss_month")
        )
        rrl_by_month["loss_month"] = rrl_by_month["loss_month"].dt.to_period('M').dt.to_timestamp()
        total_rrl = float(rrl_by_month["churned_rrl"].sum())

        return total_rrl, rrl_by_month

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

