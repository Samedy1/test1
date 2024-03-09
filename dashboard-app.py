import pandas as pd 
import streamlit as st 
import plotly.express as px
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import calendar 

st.title("My Personal Finance Overview")

@st.cache_data
def load_data(path: str): 
    data = pd.read_csv(path)
    
    return data

def cleaned_data(df): 
    if 'transaction_date' in df.columns: 
        df['transaction_date'] = pd.to_datetime(df['transaction_date'])
        
    return df
    
def handle_missing_values(df): 
    # Fill missing values in numeric columns with the mean
    numeric_cols = df.select_dtypes(include='number').columns
    df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())

    # Fill missing values in categorical columns with the mode
    categorical_cols = df.select_dtypes(include='object').columns
    df[categorical_cols] = df[categorical_cols].fillna(df[categorical_cols].mode().iloc[0])
    
    return df

def handle_duplicates(df):
    # Count the number of duplicated rows
    num_duplicated_rows = df.duplicated().sum()
    # print(num_duplicated_rows)

    if num_duplicated_rows > 0:
        # Remove duplicated rows
        df.drop_duplicates(inplace=True)
        print(f"Removed {num_duplicated_rows} duplicated row(s).")
    else:
        print("No duplicated rows found.")

    return df

def add_date_columns(df, date_column):
    """
    This function adds new columns for day, month, and year based on a given date column.
    """
    try:
        # Convert the date column to datetime format
        df[date_column] = pd.to_datetime(df[date_column])

        # Add new columns for day, month, and year
        df['day'] = df[date_column].dt.day
        df['month'] = df[date_column].dt.month
        df['year'] = df[date_column].dt.year

    except ValueError as e:
        print(f"Error: {e}. Failed to convert '{date_column}' to datetime.")

    return df

def sort_dataframe(df, columns):
    """
    This function sorts a DataFrame by the specified columns in ascending order.
    """
    try:
        df.sort_values(by=columns, ascending=True, inplace=True)
        df.reset_index(drop=True, inplace=True)
        print("DataFrame sorted successfully.")
    except KeyError as e:
        print(f"Error: {e}. One or more columns specified for sorting do not exist.")

    return df

def convert_to_month_name(month):
    """
    This function converts numeric month values to their respective month names.
    """
    month_names = {
        1: 'January',
        2: 'February',
        3: 'March',
        4: 'April',
        5: 'May',
        6: 'June',
        7: 'July',
        8: 'August',
        9: 'September',
        10: 'October',
        11: 'November',
        12: 'December'
    }

    return month_names.get(month, 'Invalid Month')


df = load_data("transactions_v2.csv")
df = cleaned_data(df)
df = handle_missing_values(df)
df = handle_duplicates(df)
df = add_date_columns(df, "transaction_date")

# Sort column
sort_columns = ['year', 'month', 'day']
df = sort_dataframe(df, sort_columns)

st.write(df)

# Convert month value to its corresponding name
# df['month'] = df['month'].apply(convert_to_month_name)

def generate_monthly_summary_pivot(df):
    """
    This function generates a monthly summary pivot table from the input DataFrame.
    """
    # Group by year, month, and transaction_type, calculate total_amount
    monthly_summary_pivot = df.groupby(['year', 'month', 'transaction_type']) \
        .agg(total_amount=('transaction_amount', 'sum')) \
        .pivot_table(index=['year', 'month'], columns='transaction_type', values='total_amount', fill_value=0) \
        .reset_index()

    # Rename 'transaction_type' column to 'id'
    monthly_summary_pivot.rename(columns={'transaction_type': 'id'}, inplace=True)

    # Calculate total balance for each month
    monthly_summary_pivot['net_balance'] = monthly_summary_pivot['Income'] - monthly_summary_pivot['Expense']

    # Calculate cumulative total balance starting from the first month
    monthly_summary_pivot['total_balance'] = monthly_summary_pivot['net_balance'].cumsum()

    return monthly_summary_pivot
    
# Generate monthly summary pivot table
monthly_summary_pivot = generate_monthly_summary_pivot(df)

st.write("Montly Summary Table")
st.write(monthly_summary_pivot)
print(monthly_summary_pivot.dtypes)

def plot_pattern_over_time(df, x_column_name, y_column_name, title):
    df['month_year'] = df['year'].astype(str) + '-' + df['month'].astype(str)
    
    fig = px.line(df, x=df['month_year'], y=y_column_name, 
                  title=f'{title} Pattern Over Time Series', markers=True, 
                  labels={
                      'month_year': "Time Series",
                      y_column_name: "Amount"
                  })
    st.write(fig)
    
def show_transaction_type_pattern_over_time(df, transaction_type):
    # Filter transactions by transaction type
    transactions = df[df['transaction_type'] == transaction_type]

    # Extract year and month from the transaction date
    transactions['year'] = pd.to_datetime(transactions['transaction_date']).dt.year
    transactions['month'] = pd.to_datetime(transactions['transaction_date']).dt.month

    # Group by year and month, and aggregate total amount spent
    transaction_summary_time = transactions.groupby(['year', 'month']).agg(
        total_amount=('transaction_amount', 'sum')
    ).reset_index()

    # Create line plot
    fig = px.line(transaction_summary_time, x='month', y='total_amount', color='year',
                  title=f'{transaction_type} Pattern over Time', markers=True)
    st.write(fig)

plot_pattern_over_time(monthly_summary_pivot, 'year', 'total_balance', 'Total Balance')
plot_pattern_over_time(monthly_summary_pivot, 'year', 'Expense', 'Total Expense')
plot_pattern_over_time(monthly_summary_pivot, 'year', 'Income', 'Total Income')

show_transaction_type_pattern_over_time(df, 'Expense')
# --------------------------------------------------------------------------------------

# Transaction Type Function 

def create_transaction_type_summary_df(df, transaction_type): 
    # Filter transactions by transaction_type
    transaction_type_transactions = df[df['transaction_type'] == transaction_type]

    # Check if there are any transactions of the specified transaction_type
    if transaction_type_transactions.empty:
        print(f"No transactions found for transaction type '{transaction_type}'.")
        return None

    # Group by month and category, then aggregate total amount and count
    monthly_transaction_type_summary = transaction_type_transactions.groupby(['year', 'month', 'category', 'subcategory']).agg(
        total_amount=('transaction_amount', 'sum'),
    ).reset_index()
    
    return monthly_transaction_type_summary 

def show_top_5_categories_donut_chart(df, year, transaction_type_str):
    # Filter expense transactions for the given year
    expense_transactions_year = df[(df['year'] == year)]

    # Sort the categories based on total amount spent in descending order
    expense_summary_sorted_year = expense_transactions_year.sort_values(by='total_amount', ascending=False)

    # Select the top 5 categories
    top_5_categories_year = expense_summary_sorted_year.head(5)
    
    # Create the donut chart
    fig = go.Figure(data=[go.Pie(labels=top_5_categories_year['category'], 
                                  values=top_5_categories_year['total_amount'], 
                                  hole=0.4,
                                  textinfo='label+percent'
                                  )])
    # Set layout options
    fig.update_layout(title=f'Top 5 {transaction_type_str} Categories in {year}',
                      showlegend=True)

    # Show the chart
    st.write(fig)
    
def show_top_5_categories_over_the_time_series(df, transaction_type_str):
    # Sort the transactions from high to low based on total amount
    transaction_sorted_descending = df.sort_values(by='total_amount', ascending=False)
    
    # find time series 
    unique_years = df['year'].unique()
    
    # Select the top 5 categories
    top_5_categories_year = transaction_sorted_descending.head(5)
    
    # Create the donut chart
    fig = go.Figure(data=[go.Pie(labels=top_5_categories_year['category'], 
                                  values=top_5_categories_year['total_amount'], 
                                  hole=0.4,
                                  textinfo='label+percent'
                                  )])
    # Set layout options
    fig.update_layout(title=f'Top 5 {transaction_type_str} Categories from {unique_years[0]} to {unique_years[-1]}',
                      showlegend=True)

    # Show the chart
    st.write(fig)
    
def show_top_5_categories_of_the_month(df, year, month, transaction_type_str):
    # Filter expense transactions for the given year
    expense_transactions_year = df[(df['year'] == year) & (df['month'] == month)]

    # Sort the categories based on total amount spent in descending order
    expense_summary_sorted_year = expense_transactions_year.sort_values(by='total_amount', ascending=False)

    # Select the top 5 categories
    top_5_categories_year = expense_summary_sorted_year.head(5)
    
    # Convert month number to month name
    month_name = calendar.month_name[month]
    
    # Create the donut chart
    fig = go.Figure(data=[go.Pie(labels=top_5_categories_year['category'], 
                                  values=top_5_categories_year['total_amount'], 
                                  hole=0.4,
                                  textinfo='label+percent'
                                  )])
    # Set layout options
    fig.update_layout(title=f'Top 5 {transaction_type_str} Categories in {month_name}, {year}',
                      showlegend=True)

    # Show the chart
    st.write(fig)
    
def compare_category_between_years(df, category, year1, year2):
    # Filter the DataFrame for the two specific years and the given category
    df_year1 = df[(df['year'] == year1) & (df['category'] == category)]
    df_year2 = df[(df['year'] == year2) & (df['category'] == category)]

    # Calculate the total amount for the specific category for each year
    total_amount_year1 = df_year1['total_amount'].sum()
    total_amount_year2 = df_year2['total_amount'].sum()

    # Create the Plotly bar chart
    fig = go.Figure(data=[
        go.Bar(name=str(year1), x=[category], y=[total_amount_year1], text=year1),
        go.Bar(name=str(year2), x=[category], y=[total_amount_year2], text=year2)
    ])

    # Set layout options
    fig.update_layout(barmode='group', title=f'Comparison of {category} between {year1} and {year2}',
                      xaxis_title='Category', yaxis_title='Total Amount')

    # Show the chart
    st.write(fig)
    
def compare_category_between_months(df, category, year, month1, month2):
    # Filter the DataFrame for the specific year and months, and the given category
    df_month1 = df[(df['year'] == year) & (df['month'] == month1) & (df['category'] == category)]
    df_month2 = df[(df['year'] == year) & (df['month'] == month2) & (df['category'] == category)]

    # Calculate the total amount for the specific category for each month
    total_amount_month1 = df_month1['total_amount'].sum()
    total_amount_month2 = df_month2['total_amount'].sum()

    # Create the Plotly bar chart
    fig = go.Figure(data=[
        go.Bar(name=str(month1), x=[str(month1)], y=[total_amount_month1]),
        go.Bar(name=str(month2), x=[str(month2)], y=[total_amount_month2])
    ])

    # Set layout options
    fig.update_layout(barmode='group', title=f'Comparison of {category} between {month1} and {month2} of {year}',
                      xaxis_title='Month', yaxis_title='Total Amount')

    # Show the chart
    st.write(fig)
    
    
def compare_total_expense_between_years(df, year1, year2):
    # Filter the DataFrame for the specific years
    df_year1 = df[df['year'] == year1]
    df_year2 = df[df['year'] == year2]
    

# Expense 
st.title("My Personal Finance - Expense")

# Filter income transactions
expense_transactions = create_transaction_type_summary_df(df, 'Expense')
st.write(expense_transactions)
show_top_5_categories_donut_chart(expense_transactions, 2023, 'Expense')
show_top_5_categories_over_the_time_series(expense_transactions, 'Expense')
show_top_5_categories_of_the_month(expense_transactions, 2023, 2, 'Expense')
compare_category_between_years(expense_transactions, 'Food and Beverage', 2019, 2022)
compare_category_between_months(expense_transactions, 'Food and Beverage', 2023, 1, 2)

# Filter income transactions
income_transactions = create_transaction_type_summary_df(df, 'Income')
st.write(income_transactions)
show_top_5_categories_donut_chart(income_transactions, 2023, 'Income')
show_top_5_categories_over_the_time_series(income_transactions, 'Income')
show_top_5_categories_of_the_month(income_transactions, 2023, 2, 'Income')
compare_category_between_years(income_transactions, 'Salary', 2019, 2022)
compare_category_between_months(income_transactions, 'Salary', 2023, 1, 2)


