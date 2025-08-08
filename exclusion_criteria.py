# exclusion_criteria.py
from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd
from consts import email_col, name_col, customer_id_col  # you already have these


class ExclusionCriteria(ABC):
    """Return True for rows that should be EXCLUDED."""
    @abstractmethod
    def filter(self, row: pd.Series) -> bool:
        raise NotImplementedError


class RemoveTestInstances(ExclusionCriteria):
    """Exclude customers with 'shir' in name/email, except one email."""
    def filter(self, row: pd.Series) -> bool:
        # Guard for missing cols
        em = str(row.get(email_col, "") or "")
        nm = str(row.get(name_col, "") or "")

        if em == "kshirjarohannaik@gmail.com":
            return False
        return ("shir" in em.lower()) or ("shir" in nm.lower())


# Example: exclude specific customers by id/email (vectorizable-ish helper)
class RemoveSpecificCustomers(ExclusionCriteria):
    def __init__(self, ids_to_remove: list[str] | None = None):
        self.ids_to_remove = set(map(str, ids_to_remove or []))

    def filter(self, row: pd.Series) -> bool:
        val = str(row.get(customer_id_col, "") or "")
        return val in self.ids_to_remove


"""

# Example: exclude free/internal domains
class RemoveInternalEmails(ExclusionCriteria):
    def __init__(self, domains: Optional[list[str]] = None):
        self.domains = set((domains or ["example.com", "internal.acme"]).map(str))

    def filter(self, row: pd.Series) -> bool:
        em = str(row.get(email_col, "") or "")
        dom = em.split("@")[-1].lower() if "@" in em else ""
        return dom in self.domains


"""