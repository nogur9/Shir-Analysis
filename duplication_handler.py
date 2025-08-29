import pandas as pd
from typing import Dict, List, Optional
from collections import defaultdict
import numpy as np

from config import Config
from models import Customer


class DuplicationHandler:
    """Handles customer duplication analysis and resolution"""
    
    def __init__(self, end_column: str = None):
        self.config = Config()
        self.end_column = self.config.get_column('canceled_date')
        self.duplication_guide: Optional[Dict] = None
        self.plan_switch = {}
        self.duplication_summary = []
    
    def _load_duplication_guide(self, df_with_groups) -> None:
        """Load the duplication handling guide from Excel file"""
        try:
            dup_handler = pd.read_excel(self.config.DUPLICATES_HANDLING_FILE)
            self.dup_handler = self._align_maps(dup_handler, df_with_groups)
            self.duplication_guide = self.dup_handler.groupby("group_id")["Result"].apply(
                lambda x: x[x != ""].iloc[0]
            ).to_dict()
            return self.duplication_guide
        except FileNotFoundError:
            print(f"Warning: Duplication guide file {self.config.DUPLICATES_HANDLING_FILE} not found")
            self.duplication_guide = {}
    
    def assign_duplicate_group_ids(self, df: pd.DataFrame) -> pd.DataFrame:
        """Assign group IDs to duplicate customers based on email and name similarity"""
        df = df.copy().reset_index(drop=True)
        n = len(df)
        
        # Group by email and name
        email_groups = df.groupby(self.config.get_column('email')).ngroup().to_numpy()
        name_groups = df.groupby(self.config.get_column('name')).ngroup().to_numpy()
        
        # Build adjacency maps
        email_to_rows = defaultdict(list)
        name_to_rows = defaultdict(list)
        
        for i in range(n):
            email_to_rows[email_groups[i]].append(i)
            name_to_rows[name_groups[i]].append(i)
        
        # DFS to find connected components
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
                
                # Add rows sharing the same email
                for neighbor in email_to_rows[email_groups[cur]]:
                    if neighbor not in visited:
                        stack.append(neighbor)
                
                # Add rows sharing the same name
                for neighbor in name_to_rows[name_groups[cur]]:
                    if neighbor not in visited:
                        stack.append(neighbor)
            
            current_gid += 1
        
        df["group_id"] = group_id
        return df
    
    def collapse_duplicate_groups(self, 
                                df: pd.DataFrame,
                                group_col: str = "group_id",
                                min_col: str = None,
                                max_col: str = None,
                                sort_keys: Optional[List[str]] = None) -> pd.DataFrame:
        """Collapse duplicate groups into single rows"""
        if min_col is None:
            min_col = self.config.get_column('start_date')
        if max_col is None:
            max_col = self.end_column
            
        df = df.copy()

        start = self.config.get_column('start_date')
        end = self.config.get_column('canceled_date')
        df = df[~(df[end] - df[start] < pd.Timedelta(days=2))]

        if df.shape[0] < 2:
            return df
        
        # Build aggregation map
        agg_map = {min_col: "min", max_col: "max"}
        
        for col in df.columns:
            if col not in (group_col, min_col, max_col):
                agg_map[col] = "first"

        out_df =  df.groupby(group_col, as_index=False).agg(agg_map)
        if df['Amount'].nunique() > 1:
            self.plan_switch[out_df['cust_id'].iloc[0]] = df[[start, end, 'Amount']]

        return out_df
    
    def handle_duplications(self, df: pd.DataFrame) -> pd.DataFrame:
        """Main method to handle all duplications"""
        # Assign group IDs
        df_with_groups = self.assign_duplicate_group_ids(df)

        self._load_duplication_guide(df_with_groups)
        # Separate duplicates and non-duplicates
        non_duplicates = df_with_groups[~df_with_groups['group_id'].isin(self.duplication_guide.keys())]
        duplicates = df_with_groups[df_with_groups['group_id'].isin(self.duplication_guide.keys())]
        
        if duplicates.empty:
            return non_duplicates
        
        # Process different types of duplications
        processed_duplicates = self._process_duplication_types(duplicates)
        
        # Combine results
        clean_df = pd.concat([non_duplicates, processed_duplicates], ignore_index=True)
        
        # Save duplicates for reference
        df_with_groups.to_csv(self.config.DUPLICATES_OUTPUT_FILE, index=False)
        
        return clean_df
    
    def _process_duplication_types(self, duplicates: pd.DataFrame) -> pd.DataFrame:
        """Process different types of duplications based on the guide"""
        processed_rows = []

        for group_id, handling_type in self.duplication_guide.items():
            group_data = duplicates[duplicates['group_id'] == group_id]
            self.duplication_summary.append({
                'num_duplicated_rows': group_data.shape[0] - 1,
                'Customer Name': group_data.iloc[0]['Customer Name'],
                'Customer Email': group_data.iloc[0]['Customer Email'],
                'Handle method': handling_type
            })
            if handling_type == "multiple start - end":
                # Keep all rows for multiple start-end scenarios
                processed_rows.append(group_data)
                
            elif handling_type == "didn't_quit":
                # Collapse and set end date to None
                collapsed = self.collapse_duplicate_groups(
                    group_data,
                    min_col=self.config.get_column('start_date'),
                    max_col=self.end_column
                ).copy()
                collapsed[self.end_column] = pd.NaT
                processed_rows.append(collapsed)
                
            elif handling_type == "single_start-end":
                # Collapse to single row
                collapsed = self.collapse_duplicate_groups(
                    group_data,
                    min_col=self.config.get_column('start_date'),
                    max_col=self.end_column
                ).copy()
                processed_rows.append(collapsed)
        
        if processed_rows:
            return pd.concat(processed_rows, ignore_index=True)
        return pd.DataFrame()
    
    def get_duplication_summary(self) -> pd.DataFrame:
        """Get summary of duplications found"""
        return pd.DataFrame(self.duplication_summary)

    def _align_maps(self, dup_handler, df_with_groups):

        new_map = {i: None for i in dup_handler['group_id'].unique()}
        for _, row in dup_handler.iterrows():
            gid = row['group_id']
            new_gid = df_with_groups[df_with_groups['Customer Name'] == row['Customer Name']]['group_id'].iloc[0]

            new_map[gid] = new_gid

        dup_handler['original_group_id'] = dup_handler['group_id']
        dup_handler['group_id'] = dup_handler['original_group_id'].map(new_map)
        return dup_handler





