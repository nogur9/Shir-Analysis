import os
import datetime
import pandas as pd


# paths
dup_handle_path =os.path.join("data", "handling duplicates.xlsx")
duplicated_customers_path = "duplicates.csv"
payment_customers_path = os.path.join("data", "payments.csv")


# names
email_col = 'Customer Email'
name_col = 'Customer Name'
customer_id_col = 'Customer ID'
canceled_at_col = "Canceled At (UTC)"
ended_at_col = "Ended At (UTC)"
start_at_col = "Start Date (UTC)"
status_col = "Status"
cust_id = "cust_id"

# errors
fixes = [{
    'email': 'mcbride.alan@gmail.com',
    'start_date': datetime.datetime.strptime("01/10/2023", "%d/%m/%Y")
},
    {
        'email': 'loredanamirea05@yahoo.com	', # name = gabriel amariutei
        'end_date': datetime.datetime.strptime("01/08/2025", "%d/%m/%Y")
    }
]

new_cust = {
    name_col: 'Dominic Church',
    email_col: 'dominicchurch@wacomms.co.uk',
    start_at_col: datetime.datetime.strptime("01/12/2024", "%d/%m/%Y"),
    ended_at_col: pd.NaT,
    canceled_at_col: pd.NaT
}