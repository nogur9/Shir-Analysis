import pandas as pd
from consts import email_col, name_col
from exclusion_criteria import RemoveTestInstances
from filtering_handler import FilteringHandler
from consts import duplicated_customers_path, canceled_at_col, start_at_col
from collections import defaultdict



class DuplicationAnalysis:

    def __init__(self, df: pd.DataFrame,
                 end_col: str = canceled_at_col,
                 create:bool=False):

        self.end_col = end_col
        self._df = df
        self.clean_df = None
        self.filtering = FilteringHandler([RemoveTestInstances()])

        if create:
            self.duplications_guide = self.assign_duplicate_group_ids()
        else:
            dup_handler = pd.read_excel("../data/handling duplicates.xlsx")
            self.guide = dup_handler.groupby("group_id")["Unnamed: 3"].apply(lambda x: x[x != ""].iloc[0]).to_dict()

    def collapse_duplicate_groups(self,
            df: pd.DataFrame,
            group_col: str = "group_id",
            min_col: str = "column 1",
            max_col: str = "column 2",
            sort_keys=None,  # e.g., ["some_priority_col", "created_at"]
    ) -> pd.DataFrame:
        """
        For each group in `group_col`, collapse to a single row:
          - min of `min_col`
          - max of `max_col`
          - first for all other columns
        If `sort_keys` is provided, we sort before taking 'first' to make it deterministic.
        """
        if sort_keys is not None:
            df = df.sort_values(sort_keys).copy()
        else:
            df = df.copy()  # keep current order; 'first' will follow this order

        # Build the aggregation map
        agg_map = {min_col: "min", max_col: "max"}

        for c in df.columns:
            if c not in (group_col, min_col, max_col):
                agg_map[c] = "first"

        out = df.groupby(group_col, as_index=False).agg(agg_map)
        return out


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


    def handle_duplications(self):
        dup_groups = self.assign_duplicate_group_ids()

        non_duplicates = dup_groups[~dup_groups['group_id'].isin(self.guide.keys())]
        duplicates = dup_groups[dup_groups['group_id'].isin(self.guide.keys())]

        multiple_start_end = duplicates[duplicates['group_id'].map(self.guide) == "multiple start - end"]
        didnt_quit = duplicates[duplicates['group_id'].map(self.guide) == "didn't_quit"]
        single_start_end = duplicates[duplicates['group_id'].map(self.guide) == "single_start-end"]

        clean_single_start_end = self.collapse_duplicate_groups(
            df = single_start_end,
            group_col = "group_id",
            min_col = start_at_col,
            max_col = self.end_col
        )
        clean_didnt_quit = self.collapse_duplicate_groups(
            df = didnt_quit,
            group_col = "group_id",
            min_col = start_at_col,
            max_col = self.end_col
        )
        clean_didnt_quit[canceled_at_col] = pd.NaT

        self.clean_df = pd.concat([non_duplicates, multiple_start_end, clean_single_start_end, clean_didnt_quit])
        return self.clean_df


if __name__ == "__main__":
    df = pd.read_csv("data/subscriptions.csv")

    da = DuplicationAnalysis(df, write_at_init=False)
    da.load()

    print(1)