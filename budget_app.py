import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- UI CONFIG ---
st.set_page_config(page_title="Cloud Budget Tracker", layout="wide")

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
    st.title("📊 Log Paycheck")
    
    # --- SELECT PERIOD ---
    st.subheader("📅 Select Period")
    col_month, col_year, col_half = st.columns(3)
    
    months = ["January", "February", "March", "April", "May", "June", 
              "July", "August", "September", "October", "November", "December"]
    current_month_idx = datetime.now().month - 1
    current_year = datetime.now().year
    
    with col_month:
        selected_month = st.selectbox("Month", months, index=current_month_idx)
    with col_year:
        selected_year = st.selectbox("Year", [2025, 2026, 2027], index=[2025, 2026, 2027].index(current_year) if current_year in [2025, 2026, 2027] else 1)
    with col_half:
        pay_period = st.selectbox("Pay Period", ["1st Half (1st-15th)", "2nd Half (16th-End)"])
    
    # Build the database key
    month_num = months.index(selected_month) + 1
    period_suffix = "1" if "1st" in pay_period else "2"
    db_month_key = f"{selected_year}-{month_num:02d}-{period_suffix}"
    
    st.info(f"📝 Recording for: **{selected_month} {selected_year} ({pay_period})**")
    
    # Option to overwrite existing entry
    overwrite = st.checkbox("Overwrite if entry already exists", value=False)
    
    st.divider()
    
    # 1. Income Section
    col1, col2 = st.columns(2)
    paycheck = col1.number_input("Paycheck Amount", min_value=0.0, step=100.0)
    side_income = col2.number_input("Side Income", min_value=0.0, step=50.0)
    total_income = paycheck + side_income
    
    st.divider()

    # 2. Spending Inputs (Savings = Income - Needs - Wants)
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.subheader("🏠 Needs")
        needs_val = st.number_input("Rent, Bills, Groceries, etc.", min_value=0.0)
        st.caption(f"50% target: ${total_income * 0.5:,.2f}")
    with col_b:
        st.subheader("🛍️ Wants")
        wants_val = st.number_input("Fun, Dining, Shopping, etc.", min_value=0.0)
        st.caption(f"30% target: ${total_income * 0.3:,.2f}")
    
    # Auto-calculate savings: whatever is left stays in savings
    savings_val = total_income - needs_val - wants_val
    
    with col_c:
        st.subheader("🏦 Savings")
        st.metric("Auto-calculated", f"${savings_val:,.2f}")
        st.caption(f"20% target: ${total_income * 0.2:,.2f}")
        if savings_val < 0:
            st.error("⚠️ Overspent!")

    notes = st.text_area("Notes")

    if st.button("🚀 Save to Google Sheets"):
        # Fetch existing data to check for duplicates and append
        existing_data = get_data()
        
        # Check if sheet is empty or missing 'Month' column
        is_empty = existing_data is None or existing_data.empty or 'Month' not in existing_data.columns
        month_exists = not is_empty and db_month_key in existing_data['Month'].values
        
        new_row = pd.DataFrame([{
            "Month": db_month_key,
            "Income": total_income,
            "Needs": needs_val,
            "Wants": wants_val,
            "Savings": savings_val,
            "Notes": notes
        }])
        
        if month_exists and not overwrite:
            st.error(f"Entry for {selected_month} {selected_year} ({pay_period}) already exists! Check 'Overwrite' to update it.")
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
                st.success(f"✅ Entry for {selected_month} {selected_year} ({pay_period}) updated!")
            else:
                st.success(f"✅ Entry for {selected_month} {selected_year} ({pay_period}) saved!")
            st.balloons()

elif page == "Analytics Dashboard":
    st.title("📈 Google Sheets Analytics")
    df = get_data()

    if df is None or df.empty or 'Month' not in df.columns:
        st.info("The spreadsheet is empty. Add data to see analytics.")
    else:
        # Latest Month Stats
        latest = df.iloc[-1]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Income", f"${latest['Income']:,.2f}")
        c2.metric("Savings Rate", f"{(latest['Savings']/latest['Income'])*100:.1f}%")
        c3.metric("Needs vs Target", f"${latest['Needs'] - (latest['Income']*0.5):,.2f}", delta_color="inverse")

        # Trends Chart
        st.subheader("Historical Trends")
        fig = px.bar(df, x='Month', y=['Needs', 'Wants', 'Savings'], title="Spending Breakdown Over Time")
        st.plotly_chart(fig, use_container_width=True)

        # Show the Google Sheet link for convenience
        st.markdown(f"[🔗 Open your Google Sheet](Your_Sheet_URL_Here)")
