# filtering_handler.py
from __future__ import annotations
from typing import Iterable, List, Optional
import pandas as pd
from exclusion_criteria import ExclusionCriteria

class FilteringHandler:
    """
    Applies a list of ExclusionCriteria to a DataFrame.
    Rows are EXCLUDED if ANY rule returns True.
    """
    def __init__(self, exclusion_rules: Optional[Iterable[ExclusionCriteria]] = None):
        self.rules: List[ExclusionCriteria] = list(exclusion_rules or [])

    def add_rule(self, rule: ExclusionCriteria) -> "FilteringHandler":
        self.rules.append(rule)
        return self

    def clear(self) -> "FilteringHandler":
        self.rules.clear()
        return self

    def filter(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self.rules or df.empty:
            return df

        # Start with "include everything"
        keep_mask = pd.Series(True, index=df.index)

        # For each rule: compute an EXCLUDE mask, then AND with ~exclude
        # Default path: row-wise .apply using rule.filter(row)->bool
        # (If you later add vectorized rules, you can override to return a boolean Series directly.)
        for rule in self.rules:
            exclude_mask = df.apply(rule.filter, axis=1)
            if not isinstance(exclude_mask, pd.Series) or exclude_mask.dtype != bool:
                raise ValueError(f"Rule {rule.__class__.__name__} must return a boolean per row.")
            keep_mask &= ~exclude_mask

        return df.loc[keep_mask].copy()
