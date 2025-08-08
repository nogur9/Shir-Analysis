import pandas as pd
from consts import email_col, name_col
from exclusion_criteria import RemoveTestInstances
from filtering_handler import FilteringHandler
from consts import duplicated_customers_path

class DuplicationAnalysis:

    def __init__(self, df: pd.DataFrame, write_at_init=True):
        self.filtering = FilteringHandler([RemoveTestInstances()])
        self.duplicated_customers = None
        self._df = df
        if write_at_init:
            self.load()
            self.write()



    def load(self):
        df = self.filtering.filter(self._df)
        df['customer_id'] = df[email_col] + '-' + df[name_col]

        duplicated_emails = df[df[email_col].duplicated(keep=False)]['customer_id'].to_list()
        duplicated_names = df[df[name_col].duplicated(keep=False)]['customer_id'].to_list()
        self.duplicated_customers = duplicated_emails + duplicated_names

    def write(self):
        dup_df = pd.DataFrame(self.duplicated_customers, columns=['customer_id'])
        dup_df.to_csv(duplicated_customers_path, index = False)





if __name__ == "__main__":
    df = pd.read_csv("data/subscriptions.csv")

    da = DuplicationAnalysis(df, write_at_init=False)
    da.load()

    print(1)