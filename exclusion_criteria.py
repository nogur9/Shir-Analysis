# exclusion_criteria.py
from abc import ABC, abstractmethod
from typing import Any
from consts import duplicated_customers_path

import pandas as pd
import datetime
from consts import *



class ExclusionCriteria(ABC):
    """Return True for rows that should be EXCLUDED."""
    @abstractmethod
    def filter(self, row: pd.Series, *args) -> bool:
        raise NotImplementedError


class RemoveTestInstances(ExclusionCriteria):
    """Exclude customers with 'shir' in name/email, except one email."""
    exceptions = ["kshirjarohannaik@gmail.com"]
    def filter(self, row: pd.Series, *args) -> bool:
        # Guard for missing cols
        em = str(row.get(email_col, "") or "")
        nm = str(row.get(name_col, "") or "")

        if em in self.exceptions:
            return False
        return ("shir" in em.lower()) or ("shir" in nm.lower())


class RemoveShortPeriod(ExclusionCriteria):
    min_durance = 30 # days
    def filter(self, row: pd.Series, *args) -> bool:
        delta = row['Canceled At (UTC)'] - row['Start Date (UTC)']
        return delta < datetime.timedelta(self.min_durance)

class RemoveByStatus(ExclusionCriteria):
    irrelevant_status = ['trialing', 'incomplete_expired']
    def filter(self, row: pd.Series, *args) -> bool:
        return row[status_col] in self.irrelevant_status


# Example: exclude specific customers by id/email (vectorizable-ish helper)
class RemoveSpecificCustomers(ExclusionCriteria):
    def __init__(self, ids_to_remove: list[str] | None = None):
        self.ids_to_remove = set(map(str, ids_to_remove or []))

    def filter(self, row: pd.Series, *args) -> bool:
        val = str(row.get(customer_id_col, "") or "")
        return val in self.ids_to_remove


class RemoveNonPayments(ExclusionCriteria):
    min_payment = 60
    def filter(self, row: pd.Series, pay_df, *args) -> bool:
        pay_dict = pay_df[['cust_id', 'Total Spend']].to_dict(orient='tight', index=False)
        pay_map = {i[0]: i[1] for i in pay_dict['data']}
        spent = pay_map['cust_id']
        return spent < self.min_payment




"""


דברים בסטטוס canceled שהם לא באמת canceled:

-	אנשים שעשו ביטול למנוי ויצרו מנוי אחר (כאילו, עברו לתכנית אחרת) אם יש פער גדול מידי בין הזמנים, אז זה לא נחשב (נניח עד חודשיים הפרש, אחרת זה פרישה ואז חזרה).
-	יש כמה כפילויות במשתמשים - להסיר אותם. (הם נמצאים תמיד ב- canceled)
-	אם גם השם והשם משפחה / מייל זהה, אז להסיר
-	לפעמים כפילויות זה יכול להיות 17 פעם.
-	יש כאלה שרצו לשנות מנוי, ויצאו ונכנסו מחדש לאתר
-	איך לדעת מי מהכפילויות אמיתי? זה תמיד הזה שהוא אקטיב.
-	יכול להיות כפילויות שכולן canceled, ואז תכלס זה אותו אחד 
-	המצב היחיד שמישהו הוא churn יותר מפעם אחת, זה אם הוא עשה מנוי, ביטל. אחרי חודשיים עשה מנוי שוב, ואז שוב פרש.
-	אם מישהו cancelled ולא שילמו כלום, אז לא נחשב גם כן




# Example: exclude free/internal domains
class RemoveInternalEmails(ExclusionCriteria):
    def __init__(self, domains: Optional[list[str]] = None):
        self.domains = set((domains or ["example.com", "internal.acme"]).map(str))

    def filter(self, row: pd.Series) -> bool:
        em = str(row.get(email_col, "") or "")
        dom = em.split("@")[-1].lower() if "@" in em else ""
        return dom in self.domains


"""