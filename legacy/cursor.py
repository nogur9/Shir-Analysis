import pandas as pd

# Load the data
df = pd.read_csv('../subscriptions.csv')

# Parse date columns
df['Canceled At (UTC)'] = pd.to_datetime(df['Canceled At (UTC)'], errors='coerce')
df['Ended At (UTC)'] = pd.to_datetime(df['Ended At (UTC)'], errors='coerce')

# Filter churned subscriptions: status is 'canceled' and has a churn date
churned = df[df['Status'] == 'canceled'].copy()

# Use 'Ended At (UTC)' as the churn date if available, otherwise 'Canceled At (UTC)'
churned['Churn Date'] = churned['Ended At (UTC)'].combine_first(churned['Canceled At (UTC)'])

# Drop rows without a churn date
churned = churned.dropna(subset=['Churn Date'])

# Extract year and month for grouping
churned['Churn Month'] = churned['Churn Date'].dt.to_period('M')

# Calculate monthly churn count
monthly_churn = churned.groupby('Churn Month').size().reset_index(name='Churn Count')

# Display the result
print(monthly_churn)
