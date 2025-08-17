# filtering_handler.py
from __future__ import annotations
from typing import Iterable, List, Optional
import pandas as pd

from consts import payment_customers_path, cust_id, email_col, name_col
from exclusion_criteria import ExclusionCriteria, RemoveTestInstances, RemoveByStatus, RemoveNonPayments
from lesson_types import find_class_type


class FilteringHandler:
    """
    Applies a list of ExclusionCriteria to a DataFrame.
    Rows are EXCLUDED if ANY rule returns True.
    """
    def __init__(self, exclusion_rules: Optional[Iterable[ExclusionCriteria]] = None):
        self.rules: List[ExclusionCriteria] = list(exclusion_rules or [])
        self.pay_df = pd.read_csv(payment_customers_path)

        self.pay_df['Email'] = self.pay_df['Email'].str.lower()
        self.pay_df['Name'] = self.pay_df['Name'].str.lower()
        self.pay_df[cust_id] = self.pay_df['Name'] + '-' + self.pay_df['Email']


    def apply_lesson_types(self, df: pd.DataFrame):
        df['Lesson'] = df['Amount'].apply(find_class_type)
        return df


    def add_rule(self, rule: ExclusionCriteria) -> "FilteringHandler":
        self.rules.append(rule)
        return self

    def clear(self) -> "FilteringHandler":
        self.rules.clear()
        return self

    def filter(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self.rules or df.empty:
            return df
        df = df.copy()
        df = self.apply_lesson_types(df)


        # Start with "include everything"
        keep_mask = pd.Series(True, index=df.index)

        # For each rule: compute an EXCLUDE mask, then AND with ~exclude
        # Default path: row-wise .apply using rule.filter(row)->bool
        # (If you later add vectorized rules, you can override to return a boolean Series directly.)
        for rule in self.rules:
            if type(rule) ==  RemoveNonPayments:
                 exclude_mask = df.apply(lambda x: rule.filter(x, self.pay_df), axis=1)
            else:
                exclude_mask = df.apply(rule.filter, axis=1)
            if not isinstance(exclude_mask, pd.Series) or exclude_mask.dtype != bool:
                raise ValueError(f"Rule {rule.__class__.__name__} must return a boolean per row.")
            keep_mask &= ~exclude_mask

        return df.loc[keep_mask].copy()



if __name__ == "__main__":
    fh = FilteringHandler(exclusion_rules=[RemoveTestInstances(), RemoveByStatus()])
    df = pd.read_csv("subscriptions.csv")
    clean_df = fh.filter(df)
    print(1)
