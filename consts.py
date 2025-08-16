import os
import datetime
import pandas as pd


# paths
dup_handle_path ="handling duplicates.xlsx"
duplicated_customers_path = "duplicates.csv"
payment_customers_path = "payments.csv"


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
    'start_date': datetime.datetime.strptime("01/10/2023", "%d/%m/%Y"),
    'end_date': pd.NaT
    },
    {
        'email': 'loredanamirea05@yahoo.com', # name = gabriel amariutei
        'end_date': pd.NaT #datetime.datetime.strptime("01/08/2025", "%d/%m/%Y")
    },
    {
        'email': 'skravin@rediffmail.com',
        'end_date': pd.NaT
    },
    {
        'email': 'mertiti@gmail.com', #avinoam gal
        'end_date': pd.NaT
    },
    {
        'email': 'nicolerabiespeech@gmail.com',
        'end_date': pd.NaT
    },
    {
        'email': 'briansamuelwalker@yahoo.co.uk',
        'end_date': pd.NaT
    },
]

new_cust = {
    name_col: 'Dominic Church',
    email_col: 'dominicchurch@wacomms.co.uk',
    start_at_col: datetime.datetime.strptime("01/12/2024", "%d/%m/%Y"),
    ended_at_col: pd.NaT,
    canceled_at_col: pd.NaT
}

# 2024-06	mertiti@gmail.com	avinoam gal - Didn't Quit
# 2024-11	skravin@rediffmail.com	sathish ravindran - Didn't Quit
# 2025-05	nicolerabiespeech@gmail.com	daniel rabie - Didn't Quit
# 2025-05	mcbride.alan@gmail.com	mr alan mcbride - Didn't Quit