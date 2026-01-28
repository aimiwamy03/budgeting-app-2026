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
page = st.sidebar.radio("Go to", ["Fill New Month", "Analytics Dashboard"])

db_month_key = datetime.now().strftime("%Y-%m")
current_month_name = datetime.now().strftime("%B %Y")

if page == "Fill New Month":
    st.title(f"📊 Budget Entry: {current_month_name}")
    
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
        
        if db_month_key in existing_data['Month'].values:
            st.error(f"Data for {db_month_key} already exists in Google Sheets!")
        else:
            new_row = pd.DataFrame([{
                "Month": db_month_key,
                "Income": total_income,
                "Needs": needs_val,
                "Wants": wants_val,
                "Savings": savings_val,
                "Notes": notes
            }])
            
            # Combine and update the spreadsheet
            updated_df = pd.concat([existing_data, new_row], ignore_index=True)
            conn.update(data=updated_df)
            st.success("Data synced to Google Sheets!")
            st.balloons()

elif page == "Analytics Dashboard":
    st.title("📈 Google Sheets Analytics")
    df = get_data()

    if df.empty:
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
