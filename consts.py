import os

email_col = 'Customer Email'
name_col = 'Customer Name'
customer_id_col = 'Customer ID'
canceled_at_col = "Canceled At (UTC)"
ended_at_col = "Ended At (UTC)"
start_at_col = "Start Date (UTC)"
status_col = "Status"
inclusion_data_path = None
duplicated_customers_path = "duplicates.csv"
payment_customers_path = os.path.join("data", "payments.csv")
cust_id = "cust_id"
