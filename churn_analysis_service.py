import pandas as pd
from typing import Dict, Optional, Tuple
from config import Config


class ChurnAnalysisService:
    """Service for computing churn analysis metrics"""

    def __init__(self, end_column: str = None):
        self.config = Config()
        self.end_column = end_column or self.config.get_column('canceled_date')
        self._subscriptions_df: Optional[pd.DataFrame] = None
        self._monthly_payments_df: Optional[pd.DataFrame] = None


    def set_data(self,
                 subscriptions_df: pd.DataFrame,
                 monthly_payments_df: pd.DataFrame) -> 'ChurnAnalysisService':
        """Set the data for analysis"""
        self._subscriptions_df = subscriptions_df.copy()
        self._monthly_payments_df = monthly_payments_df.copy()
        return self

    def compute_monthly_churn_summary(self):
        """
        Compute monthly churn summary metrics

        Returns:
            Tuple of (summary_dataframe, revenue_by_month)
        """
        if self._subscriptions_df is None:
            raise ValueError("No subscriptions data set. Call set_data() first.")

        df = self._subscriptions_df.copy()
        # Get monthly ranges and counts
        starts, cancellations, all_months = self.get_monthly_counts(df)

        # Calculate active customers per month
        actives_per_month = self._calculate_active_customers(df, all_months)

        # Build summary dataframe
        summary_df = self._build_summary(starts, cancellations, actives_per_month)

        return summary_df


    def get_monthly_counts(self,
                           df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.PeriodIndex]:
        """Get monthly start and cancellation counts"""

        start_col = self.config.get_column('start_date')
        end_col = self.end_column

        # Period[M] columns
        df = df.copy()
        df['start_month'] = df[start_col].dt.to_period('M')
        df['cancel_month'] = df[end_col].dt.to_period('M')

        # Analysis window: from FIRST start to LAST of (start or cancel)
        # (dropping NaT before max makes sense)
        from_month = df['start_month'].min()
        last_part = pd.concat([df['start_month'].dropna(), df['cancel_month'].dropna()], ignore_index=True)
        to_month = last_part.max() if not last_part.empty else from_month

        if pd.isna(from_month) or pd.isna(to_month):
            # No usable dates at all
            raise ValueError("no data")

        # Create month range
        all_months = pd.period_range(from_month, to_month, freq='M')

        starts = df['start_month'].value_counts().reindex(all_months, fill_value=0).sort_index()
        cancellations = df['cancel_month'].value_counts().reindex(all_months, fill_value=0).sort_index()

        return starts, cancellations, all_months


    def _calculate_active_customers(self, df: pd.DataFrame, all_months: pd.PeriodIndex):
        """Calculate active customers at the start of each month (inclusive start, open-ended end)."""
        start_col = self.config.get_column('start_date')
        end_col = self.end_column

        actives_per_month = []
        for month in all_months:
            m_start = month.start_time  # Timestamp at month start
            active_mask = (
                    (df[start_col] <= m_start) &
                    (df[end_col].isna() | (df[end_col] >= m_start))
            )
            actives_per_month.append(int(active_mask.sum()))
        return actives_per_month


    def get_analysis_summary(self) -> Dict:
        """Get summary of the analysis configuration and data"""
        return {
            'end_column': self.end_column,
            'total_subscriptions': len(self._subscriptions_df) if self._subscriptions_df is not None else 0,
            'total_monthly_records': len(self._monthly_payments_df) if self._monthly_payments_df is not None else 0,
            'analysis_date_range': {
                'start': self._subscriptions_df[self.config.get_column('start_date')].min() if self._subscriptions_df is not None else None,
                'end': self._subscriptions_df[self.end_column].max() if self._subscriptions_df is not None else None
            } if self._subscriptions_df is not None else None
        }


    def get_customer_data_by_month(self,
                                   df: pd.DataFrame,
                                   all_months: pd.PeriodIndex) -> Tuple[Dict, Dict]:
        """Get customer data organized by month"""
        start_col = self.config.get_column('start_date')
        end_col = self.end_column

        started_customers = {}
        canceled_customers = {}
        df = df.copy()
        df['start_month'] = df[start_col].dt.to_period('M')
        df['cancel_month'] = df[end_col].dt.to_period('M')

        for month in all_months:
            # Customers who started this month
            start_mask = df['start_month'] == month
            started_customers[month] = df[start_mask][
                ['start_month', self.config.get_column('email'),
                 self.config.get_column('name'), 'cust_id']
            ]

            # Customers who canceled this month
            cancel_mask = df['cancel_month'] == month
            canceled_customers[month] = df[cancel_mask][
                ['cancel_month', self.config.get_column('email'),
                 self.config.get_column('name'), 'cust_id']
            ]

        return started_customers, canceled_customers


    @staticmethod
    def _build_summary(starts, cancellations, actives_per_month):

        summary_df = pd.DataFrame({
            'Month': starts.index,
            'Starts': starts.values,
            'Cancellations': cancellations.values,
            'Actives': actives_per_month,
        })

        # --- Trim leading/trailing months with Actives == 0 to avoid div/0 ---
        if (summary_df['Actives'] == 0).any():
            nonzero_idx = summary_df.index[summary_df['Actives'] > 0]

            first_keep = nonzero_idx.min()
            last_keep = nonzero_idx.max()
            # If there are zero-active months outside [first_keep, last_keep], trim them
            trimmed = False
            if first_keep > summary_df.index.min():
                trimmed = True
            if last_keep < summary_df.index.max():
                trimmed = True

            if trimmed:
                first_month_str = str(summary_df.loc[first_keep, 'Month'])
                last_month_str = str(summary_df.loc[last_keep, 'Month'])
                print(f"[churn] Trimmed months with Actives == 0. "
                      f"New analysis window: {first_month_str} → {last_month_str}.")
                summary_df = summary_df.loc[first_keep:last_keep].reset_index(drop=True)

        # --- Churn Rate (safe division) ---
        # (Actives now guaranteed > 0 within the trimmed window)
        summary_df['Churn_Rate'] = summary_df['Cancellations'] / summary_df['Actives']

        # Present Month as Timestamp (month start) or string, up to you:
        # summary_df['Month'] = summary_df['Month'].astype(str)
        summary_df['Month'] = summary_df['Month'].dt.to_timestamp(how='S')  # month start Timestamp
        return summary_df



