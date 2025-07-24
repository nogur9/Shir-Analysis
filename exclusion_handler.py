from typing import List
import pandas as pd
from exclusion_criteria import ExclusionCriteria


class ExclusionHandler:

    def __init__(self, exclusion_rules:List[ExclusionCriteria]):
        pass


    def filter(self, df: pd.DataFrame) -> pd.DataFrame:
        pass