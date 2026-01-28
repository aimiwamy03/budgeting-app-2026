import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime, date

# --- UI CONFIG ---
st.set_page_config(page_title="Cloud Budget Tracker", layout="wide")

# --- CATEGORY DEFINITIONS ---
NEEDS_CATEGORIES = ["Housing", "Utilities", "Groceries", "Transportation", "Insurance", "Healthcare", "Subscriptions"]
WANTS_CATEGORIES = ["Food/Dining", "Shopping", "Entertainment", "Travel", "Personal Care", "Misc"]
ALL_CATEGORIES = NEEDS_CATEGORIES + WANTS_CATEGORIES
PAYMENT_METHODS = ["Debit", "Credit", "Cash", "Venmo", "Zelle", "Other"]

st.markdown("""
    <style>
    .main { background-color: #E8F6EF; }
    </style>
    """, unsafe_allow_html=True)

# --- GOOGLE SHEETS CONNECTION ---
# In your secrets.toml or Streamlit Cloud, you must provide 'spreadsheet' and 'worksheet'
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    return conn.read(ttl="10m") # Cache data for 10 mins

# --- SIDEBAR ---
st.sidebar.title("☁️ Cloud Budget")
page = st.sidebar.radio("Go to", ["Log Paycheck", "Analytics Dashboard"])

current_month_name = datetime.now().strftime("%B %Y")

if page == "Log Paycheck":
    st.title("📊 Monthly Budget Entry")
    
    # --- SELECT MONTH ---
    col_month, col_year = st.columns(2)
    
    months = ["January", "February", "March", "April", "May", "June", 
              "July", "August", "September", "October", "November", "December"]
    current_month_idx = datetime.now().month - 1
    current_year = datetime.now().year
    
    with col_month:
        selected_month = st.selectbox("Month", months, index=current_month_idx)
    with col_year:
        selected_year = st.selectbox("Year", [2025, 2026, 2027], index=[2025, 2026, 2027].index(current_year) if current_year in [2025, 2026, 2027] else 1)
    
    # Build the database key (monthly, no half-month suffix)
    month_num = months.index(selected_month) + 1
    db_month_key = f"{selected_year}-{month_num:02d}"
    
    # Option to overwrite existing entry
    overwrite = st.checkbox("Overwrite if entry already exists", value=False)
    
    st.divider()
    
    # 1. Income Section - TWO PAYCHECKS
    st.subheader("💵 Income (2 Paychecks per Month)")
    col1, col2, col3 = st.columns(3)
    paycheck_1 = col1.number_input("1st Paycheck (1st-15th)", min_value=0.0, step=100.0)
    paycheck_2 = col2.number_input("2nd Paycheck (16th-End)", min_value=0.0, step=100.0)
    side_income = col3.number_input("Side Income", min_value=0.0, step=50.0)
    total_income = paycheck_1 + paycheck_2 + side_income
    
    st.metric("💰 Total Monthly Income", f"${total_income:,.2f}")
    
    st.divider()
    
    # --- EXPENSE TRACKER ---
    st.subheader("📝 Expense Tracker")
    st.caption("Add your expenses below. They'll auto-sum into Needs & Wants.")
    
    # Initialize session state for expenses if not exists
    expense_key = f"expenses_{db_month_key}"
    if expense_key not in st.session_state:
        st.session_state[expense_key] = pd.DataFrame(columns=["Date", "Category", "Description", "Amount", "Payment"])
    
    # --- ADD NEW EXPENSE ---
    with st.expander("➕ Add New Expense", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            exp_date = st.date_input("Date", value=date.today())
            exp_category = st.selectbox("Category", ALL_CATEGORIES)
        with col2:
            exp_description = st.text_input("Description")
            exp_amount = st.number_input("Amount", min_value=0.0, step=1.0, format="%.2f")
        with col3:
            exp_payment = st.selectbox("Payment Method", PAYMENT_METHODS)
            if st.button("➕ Add Expense"):
                if exp_amount > 0:
                    new_expense = pd.DataFrame([{
                        "Date": exp_date.strftime("%m/%d/%y"),
                        "Category": exp_category,
                        "Description": exp_description,
                        "Amount": exp_amount,
                        "Payment": exp_payment
                    }])
                    st.session_state[expense_key] = pd.concat([st.session_state[expense_key], new_expense], ignore_index=True)
                    st.success(f"Added: {exp_description} - ${exp_amount:.2f}")
                    st.rerun()
    
    # --- EXPENSE TABLE ---
    expenses_df = st.session_state[expense_key]
    
    if not expenses_df.empty:
        st.dataframe(expenses_df, use_container_width=True, hide_index=True)
        
        # Calculate totals by category type
        expenses_df['Amount'] = pd.to_numeric(expenses_df['Amount'], errors='coerce').fillna(0)
        needs_expenses = expenses_df[expenses_df['Category'].isin(NEEDS_CATEGORIES)]['Amount'].sum()
        wants_expenses = expenses_df[expenses_df['Category'].isin(WANTS_CATEGORIES)]['Amount'].sum()
        total_expenses = expenses_df['Amount'].sum()
        
        # Clear expenses button
        if st.button("🗑️ Clear All Expenses"):
            st.session_state[expense_key] = pd.DataFrame(columns=["Date", "Category", "Description", "Amount", "Payment"])
            st.rerun()
    else:
        st.info("No expenses added yet. Add some above!")
        needs_expenses = 0.0
        wants_expenses = 0.0
        total_expenses = 0.0
    
    st.divider()
    
    # --- SUMMARY: Needs / Wants / Savings ---
    st.subheader("📊 Monthly Summary")
    
    # Use expense totals as default, but allow manual override
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("### 🏠 Needs")
        st.metric("From Expenses", f"${needs_expenses:,.2f}")
        needs_val = st.number_input("Manual Adjustment", value=needs_expenses, min_value=0.0, key="needs_input")
        st.caption(f"50% target: ${total_income * 0.5:,.2f}")
    with col_b:
        st.markdown("### 🛍️ Wants")
        st.metric("From Expenses", f"${wants_expenses:,.2f}")
        wants_val = st.number_input("Manual Adjustment", value=wants_expenses, min_value=0.0, key="wants_input")
        st.caption(f"30% target: ${total_income * 0.3:,.2f}")
    
    # Auto-calculate savings
    savings_val = total_income - needs_val - wants_val
    
    with col_c:
        st.markdown("### 🏦 Savings")
        st.metric("Auto-calculated", f"${savings_val:,.2f}")
        st.caption(f"20% target: ${total_income * 0.2:,.2f}")
        if savings_val < 0:
            st.error("⚠️ Overspent!")
        elif savings_val >= total_income * 0.2:
            st.success("✅ On track!")

    notes = st.text_area("Notes")

    if st.button("🚀 Save to Google Sheets"):
        # Fetch existing data to check for duplicates and append
        existing_data = get_data()
        
        # Check if sheet is empty or missing 'Month' column
        is_empty = existing_data is None or existing_data.empty or 'Month' not in existing_data.columns
        month_exists = not is_empty and db_month_key in existing_data['Month'].values
        
        new_row = pd.DataFrame([{
            "Month": db_month_key,
            "Paycheck1": paycheck_1,
            "Paycheck2": paycheck_2,
            "SideIncome": side_income,
            "TotalIncome": total_income,
            "Needs": needs_val,
            "Wants": wants_val,
            "Savings": savings_val,
            "Notes": notes
        }])
        
        if month_exists and not overwrite:
            st.error(f"Entry for {selected_month} {selected_year} already exists! Check 'Overwrite' to update it.")
        else:
            if is_empty:
                updated_df = new_row
            elif month_exists and overwrite:
                # Remove old entry and add new one
                existing_data = existing_data[existing_data['Month'] != db_month_key]
                updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                updated_df = updated_df.sort_values('Month').reset_index(drop=True)
            else:
                updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                updated_df = updated_df.sort_values('Month').reset_index(drop=True)
            
            conn.update(data=updated_df)
            if month_exists and overwrite:
                st.success(f"✅ Entry for {selected_month} {selected_year} updated!")
            else:
                st.success(f"✅ Entry for {selected_month} {selected_year} saved!")
            st.balloons()

elif page == "Analytics Dashboard":
    st.title("📈 Google Sheets Analytics")
    df = get_data()

    if df is None or df.empty or 'Month' not in df.columns:
        st.info("The spreadsheet is empty. Add data to see analytics.")
    else:
        # Latest Month Stats
        latest = df.iloc[-1]
        
        # Handle both old 'Income' column and new 'TotalIncome' column
        income_col = 'TotalIncome' if 'TotalIncome' in df.columns else 'Income'
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Income", f"${latest[income_col]:,.2f}")
        c2.metric("Savings Rate", f"{(latest['Savings']/latest[income_col])*100:.1f}%")
        c3.metric("Needs vs Target", f"${latest['Needs'] - (latest[income_col]*0.5):,.2f}", delta_color="inverse")

        # Trends Chart
        st.subheader("Historical Trends")
        fig = px.bar(df, x='Month', y=['Needs', 'Wants', 'Savings'], title="Spending Breakdown Over Time")
        st.plotly_chart(fig, use_container_width=True)

        # Show the Google Sheet link for convenience
        st.markdown(f"[🔗 Open your Google Sheet](Your_Sheet_URL_Here)")
