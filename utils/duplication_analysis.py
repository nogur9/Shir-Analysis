import pandas as pd
from consts import email_col, name_col
from exclusion_criteria import RemoveTestInstances
from filtering_handler import FilteringHandler
from consts import duplicated_customers_path
from collections import defaultdict



class DuplicationAnalysis:

    def __init__(self, df: pd.DataFrame, create=True):
        self.filtering = FilteringHandler([RemoveTestInstances()])
        self.duplicated_customers = None
        self._df = df
        if create:
            self.duplications_guide = self.assign_duplicate_group_ids()
        else:
            self.duplications_guide = pd.read_csv(duplicated_customers_path)


    def assign_duplicate_group_ids(self):
        df = self._df.copy()  # do not mutate caller
        df = self.filtering.filter(df)
        # df['customer_id'] = df[email_col] + '-' + df[name_col]

        # Ensure positional alignment 0..n-1
        df = df.reset_index(drop=True)
        n = len(df)

        # Group labels as arrays (positional)
        e_group = df.groupby(email_col).ngroup().to_numpy()
        n_group = df.groupby(name_col).ngroup().to_numpy()

        # Build adjacency by shared email OR shared name
        email_to_rows = defaultdict(list)
        name_to_rows = defaultdict(list)

        for i in range(n):
            email_to_rows[e_group[i]].append(i)
            name_to_rows[n_group[i]].append(i)

        # DFS over rows (0..n-1), using only positional indices
        visited = set()
        group_id = [-1] * n
        current_gid = 0

        for start in range(n):
            if start in visited:
                continue
            stack = [start]
            while stack:
                cur = stack.pop()
                if cur in visited:
                    continue
                visited.add(cur)
                group_id[cur] = current_gid

                # push all rows sharing this row's email
                for nbr in email_to_rows[e_group[cur]]:
                    if nbr not in visited:
                        stack.append(nbr)
                # push all rows sharing this row's name
                for nbr in name_to_rows[n_group[cur]]:
                    if nbr not in visited:
                        stack.append(nbr)

            current_gid += 1

        df["group_id"] = group_id
        df.to_csv(duplicated_customers_path, index = False)
        return df


if __name__ == "__main__":
    df = pd.read_csv("data/subscriptions.csv")

    da = DuplicationAnalysis(df, write_at_init=False)
    da.load()

    print(1)