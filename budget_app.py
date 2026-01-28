import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date

# --- UI CONFIG ---
st.set_page_config(page_title="Cloud Budget Tracker", layout="wide", page_icon="💰")

# --- CATEGORY DEFINITIONS ---
NEEDS_CATEGORIES = ["Housing", "Utilities", "Groceries", "Transportation", "Insurance", "Healthcare", "Subscriptions"]
WANTS_CATEGORIES = ["Food/Dining", "Shopping", "Entertainment", "Travel", "Personal Care", "Misc"]
ALL_CATEGORIES = NEEDS_CATEGORIES + WANTS_CATEGORIES
PAYMENT_METHODS = ["Credit", "Debit", "Cash", "Venmo", "Zelle", "Apple Pay", "Other"]  # Credit first (default)

# Category icons for visual appeal
CATEGORY_ICONS = {
    "Housing": "🏠", "Utilities": "💡", "Groceries": "🛒", "Transportation": "🚗",
    "Insurance": "🛡️", "Healthcare": "🏥", "Subscriptions": "📱",
    "Food/Dining": "🍔", "Shopping": "🛍️", "Entertainment": "🎬",
    "Travel": "✈️", "Personal Care": "💅", "Misc": "📦"
}

# --- COFFEE THEME COLOR PALETTE ---
COLORS = {
    "bg": "#F5F0EB",           # Soft cream/latte
    "card": "#FFFBF7",         # Warm white
    "accent1": "#8B5A2B",      # Rich coffee brown
    "accent2": "#D4A574",      # Caramel
    "accent3": "#C9B896",      # Creamy beige
    "text": "#4A3728",         # Dark roast
    "success": "#7A9B76",      # Sage green
    "warning": "#D4A574",      # Caramel
    "danger": "#C17767",       # Terracotta
    "needs": "#C17767",        # Terracotta
    "wants": "#D4A574",        # Caramel
    "savings": "#7A9B76",      # Sage green
}

# --- CUSTOM STYLING (Coffee theme - compact & cozy) ---
st.markdown(f"""
    <style>
    /* Main background */
    .stApp {{ background: linear-gradient(135deg, {COLORS['bg']} 0%, #EDE5DC 100%); }}
    
    /* Compact text sizing */
    .stApp {{ font-size: 14px; }}
    h1 {{ font-size: 1.6rem !important; color: {COLORS['text']}; }}
    h2 {{ font-size: 1.3rem !important; color: {COLORS['text']}; }}
    h3 {{ font-size: 1.1rem !important; color: {COLORS['accent1']}; }}
    p, span, label {{ font-size: 0.85rem !important; }}
    
    /* Compact metrics */
    [data-testid="stMetricValue"] {{ font-size: 1.2rem !important; color: {COLORS['accent1']}; }}
    [data-testid="stMetricLabel"] {{ font-size: 0.75rem !important; }}
    [data-testid="stMetricDelta"] {{ font-size: 0.7rem !important; }}
    
    /* Cards */
    .stMetric {{ 
        background: {COLORS['card']}; 
        padding: 10px; 
        border-radius: 10px; 
        box-shadow: 0 2px 6px rgba(74,55,40,0.1);
        border: 1px solid {COLORS['accent3']};
    }}
    
    /* Sidebar */
    [data-testid="stSidebar"] {{ background: {COLORS['card']}; }}
    [data-testid="stSidebar"] h1 {{ color: {COLORS['accent1']}; }}
    
    /* Buttons */
    .stButton > button {{
        background: {COLORS['accent1']};
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 0.85rem;
        padding: 0.4rem 1rem;
    }}
    .stButton > button:hover {{ background: {COLORS['text']}; }}
    
    /* Input fields */
    .stSelectbox, .stNumberInput, .stTextInput {{ font-size: 0.85rem; }}
    
    /* Progress bars */
    .stProgress > div > div {{ background: {COLORS['accent2']}; }}
    
    /* Expander */
    .streamlit-expanderHeader {{ font-size: 0.9rem !important; color: {COLORS['accent1']}; }}
    
    /* Dataframe */
    .stDataFrame {{ font-size: 0.8rem; }}
    
    /* Reduce spacing */
    .block-container {{ padding-top: 1rem; padding-bottom: 1rem; }}
    .element-container {{ margin-bottom: 0.5rem; }}
    
    /* Divider */
    hr {{ border-color: {COLORS['accent3']}; margin: 0.8rem 0; }}
    </style>
    """, unsafe_allow_html=True)

def get_spending_score(savings_rate):
    """Calculate a financial health score"""
    if savings_rate >= 25: return ("A+", "🌟", COLORS['success'], "Excellent! You're crushing it!")
    elif savings_rate >= 20: return ("A", "✨", COLORS['success'], "Great job! On track!")
    elif savings_rate >= 15: return ("B", "👍", "#A8C69F", "Good! Room to grow")
    elif savings_rate >= 10: return ("C", "😐", COLORS['warning'], "Fair. Try to save more")
    elif savings_rate >= 5: return ("D", "⚠️", COLORS['warning'], "Warning: Low savings")
    else: return ("F", "🚨", COLORS['danger'], "Critical: Overspending!")

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
    # --- SUPER COMPACT HEADER: Month/Year + Income all in one row ---
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    current_month_idx = datetime.now().month - 1
    current_year = datetime.now().year
    
    c1, c2, c3, c4, c5, c6 = st.columns([1, 0.7, 1.2, 1.2, 1, 1])
    with c1:
        selected_month = st.selectbox("📅", months, index=current_month_idx, label_visibility="collapsed")
    with c2:
        selected_year = st.selectbox("Year", [2025, 2026, 2027], index=[2025, 2026, 2027].index(current_year) if current_year in [2025, 2026, 2027] else 1, label_visibility="collapsed")
    with c3:
        paycheck_1 = st.number_input("💵 Pay 1", min_value=0.0, step=100.0, format="%.0f")
    with c4:
        paycheck_2 = st.number_input("💵 Pay 2", min_value=0.0, step=100.0, format="%.0f")
    with c5:
        side_income = st.number_input("💸 Side", min_value=0.0, step=50.0, format="%.0f")
    with c6:
        total_income = paycheck_1 + paycheck_2 + side_income
        st.metric("Total", f"${total_income:,.0f}", label_visibility="visible")
    
    # Build the database key
    full_months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    month_num = months.index(selected_month) + 1
    db_month_key = f"{selected_year}-{month_num:02d}"
    
    overwrite = st.checkbox("Overwrite existing", value=False)
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
    
    # --- SPENDING INSIGHTS (Rocket Money style) ---
    if not expenses_df.empty and total_income > 0:
        st.subheader("📊 Spending Insights")
        
        # Category breakdown pie chart
        col_chart, col_top = st.columns([2, 1])
        
        with col_chart:
            category_totals = expenses_df.groupby('Category')['Amount'].sum().reset_index()
            category_totals['Icon'] = category_totals['Category'].map(lambda x: CATEGORY_ICONS.get(x, "📦") + " " + x)
            fig_pie = px.pie(category_totals, values='Amount', names='Icon', 
                           title="Where Your Money Went",
                           color_discrete_sequence=['#8B5A2B', '#D4A574', '#C9B896', '#C17767', '#7A9B76', '#A67B5B', '#DEB887', '#BC8F8F', '#D2B48C', '#C4A484', '#BDB76B', '#8FBC8F', '#CD853F'])
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col_top:
            st.markdown("### 🔥 Top Spending")
            top_categories = category_totals.nlargest(5, 'Amount')
            for _, row in top_categories.iterrows():
                icon = CATEGORY_ICONS.get(row['Category'], "📦")
                st.markdown(f"{icon} **{row['Category']}**: ${row['Amount']:,.2f}")
    
    st.divider()

    # --- BUDGET PROGRESS BARS (Rocket Money style) ---
    st.subheader("📈 Budget Progress")
    
    needs_val = needs_expenses
    wants_val = wants_expenses
    savings_val = total_income - needs_val - wants_val
    
    if total_income > 0:
        needs_target = total_income * 0.5
        wants_target = total_income * 0.3
        savings_target = total_income * 0.2
        
        needs_pct = min((needs_val / needs_target) * 100, 150) if needs_target > 0 else 0
        wants_pct = min((wants_val / wants_target) * 100, 150) if wants_target > 0 else 0
        savings_pct = min((savings_val / savings_target) * 100, 150) if savings_target > 0 else 0
        
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            st.markdown("### 🏠 Needs (50%)")
            color = "normal" if needs_pct <= 100 else "inverse"
            st.metric("Spent", f"${needs_val:,.2f}", f"{needs_pct:.0f}% of budget", delta_color=color)
            st.progress(min(needs_pct / 100, 1.0))
            if needs_pct > 100:
                st.error(f"⚠️ Over budget by ${needs_val - needs_target:,.2f}")
            elif needs_pct > 80:
                st.warning("⚡ Getting close to limit")
        
        with col_b:
            st.markdown("### 🛍️ Wants (30%)")
            color = "normal" if wants_pct <= 100 else "inverse"
            st.metric("Spent", f"${wants_val:,.2f}", f"{wants_pct:.0f}% of budget", delta_color=color)
            st.progress(min(wants_pct / 100, 1.0))
            if wants_pct > 100:
                st.error(f"⚠️ Over budget by ${wants_val - wants_target:,.2f}")
            elif wants_pct > 80:
                st.warning("⚡ Getting close to limit")
        
        with col_c:
            st.markdown("### 🏦 Savings (20%)")
            color = "normal" if savings_val >= 0 else "inverse"
            st.metric("Remaining", f"${savings_val:,.2f}", f"{savings_pct:.0f}% of target", delta_color=color)
            st.progress(min(max(savings_pct / 100, 0), 1.0))
            if savings_val < 0:
                st.error("🚨 Overspent! Dipping into savings")
            elif savings_pct >= 100:
                st.success("✅ Savings goal met!")
        
        # --- FINANCIAL HEALTH SCORE (Rocket Money style) ---
        st.divider()
        savings_rate = (savings_val / total_income) * 100 if total_income > 0 else 0
        grade, emoji, color, message = get_spending_score(savings_rate)
        
        score_col1, score_col2 = st.columns([1, 3])
        with score_col1:
            st.markdown(f"<h1 style='text-align: center; color: {color}; font-size: 72px;'>{grade}</h1>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; font-size: 24px;'>{emoji}</p>", unsafe_allow_html=True)
        with score_col2:
            st.markdown(f"### Your Money Score")
            st.markdown(f"**{message}**")
            st.markdown(f"Savings Rate: **{savings_rate:.1f}%** of income")
            if savings_rate < 20:
                st.markdown(f"💡 *Tip: Try to save ${(total_income * 0.2) - savings_val:,.2f} more to hit 20%*")
    else:
        st.info("Enter your income above to see budget progress")

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
    st.title("📈 Financial Dashboard")
    df = get_data()

    if df is None or df.empty or 'Month' not in df.columns:
        st.info("The spreadsheet is empty. Add data to see analytics.")
    else:
        # Handle both old 'Income' column and new 'TotalIncome' column
        income_col = 'TotalIncome' if 'TotalIncome' in df.columns else 'Income'
        latest = df.iloc[-1]
        
        # --- MONTH OVER MONTH COMPARISON (Rocket Money style) ---
        st.subheader("📊 This Month at a Glance")
        
        c1, c2, c3, c4 = st.columns(4)
        
        # Calculate month-over-month changes
        if len(df) >= 2:
            prev = df.iloc[-2]
            income_change = latest[income_col] - prev[income_col]
            needs_change = latest['Needs'] - prev['Needs']
            wants_change = latest['Wants'] - prev['Wants']
            savings_change = latest['Savings'] - prev['Savings']
        else:
            income_change = needs_change = wants_change = savings_change = 0
        
        with c1:
            st.metric("💰 Income", f"${latest[income_col]:,.2f}", 
                     f"${income_change:+,.0f}" if income_change != 0 else None)
        with c2:
            st.metric("🏠 Needs", f"${latest['Needs']:,.2f}", 
                     f"${needs_change:+,.0f}" if needs_change != 0 else None, delta_color="inverse")
        with c3:
            st.metric("🛍️ Wants", f"${latest['Wants']:,.2f}", 
                     f"${wants_change:+,.0f}" if wants_change != 0 else None, delta_color="inverse")
        with c4:
            savings_rate = (latest['Savings']/latest[income_col])*100 if latest[income_col] > 0 else 0
            st.metric("🏦 Savings", f"${latest['Savings']:,.2f}", 
                     f"${savings_change:+,.0f}" if savings_change != 0 else None)
        
        # Financial Health Score
        grade, emoji, color, message = get_spending_score(savings_rate)
        st.markdown(f"### {emoji} Financial Health: **{grade}** - {message}")
        
        st.divider()
        
        # --- SPENDING TRENDS (Rocket Money style) ---
        st.subheader("📈 Spending Trends")
        
        col_line, col_pie = st.columns(2)
        
        with col_line:
            # Stacked area chart for spending over time
            fig_area = go.Figure()
            fig_area.add_trace(go.Scatter(x=df['Month'], y=df['Needs'], name='Needs', 
                                         fill='tonexty', mode='lines', line=dict(color=COLORS['needs'])))
            fig_area.add_trace(go.Scatter(x=df['Month'], y=df['Needs'] + df['Wants'], name='Wants', 
                                         fill='tonexty', mode='lines', line=dict(color=COLORS['wants'])))
            fig_area.add_trace(go.Scatter(x=df['Month'], y=df[income_col], name='Income', 
                                         mode='lines+markers', line=dict(color=COLORS['accent1'], width=3)))
            fig_area.update_layout(title="Income vs Spending Over Time", 
                                  xaxis_title="Month", yaxis_title="Amount ($)")
            st.plotly_chart(fig_area, use_container_width=True)
        
        with col_pie:
            # Latest month breakdown
            breakdown = pd.DataFrame({
            'Category': ['Needs', 'Wants', 'Savings'],
                'Amount': [latest['Needs'], latest['Wants'], max(latest['Savings'], 0)]
            })
            fig_donut = px.pie(breakdown, values='Amount', names='Category', hole=0.5,
                              title=f"Latest Month Breakdown ({latest['Month']})",
                              color_discrete_map={'Needs': COLORS['needs'], 'Wants': COLORS['wants'], 'Savings': COLORS['savings']})
            st.plotly_chart(fig_donut, use_container_width=True)
        
        st.divider()
        
        # --- SAVINGS PROGRESS (Rocket Money style) ---
        st.subheader("🎯 Savings Journey")
        
        total_saved = df['Savings'].sum()
        avg_savings = df['Savings'].mean()
        months_tracked = len(df)
        
        s1, s2, s3 = st.columns(3)
        s1.metric("💎 Total Saved", f"${total_saved:,.2f}")
        s2.metric("📊 Avg Monthly Savings", f"${avg_savings:,.2f}")
        s3.metric("📅 Months Tracked", months_tracked)
        
        # Savings over time line chart
        fig_savings = px.line(df, x='Month', y='Savings', title="Savings Over Time",
                             markers=True, line_shape='spline')
        fig_savings.update_traces(line_color=COLORS['savings'], line_width=3)
        fig_savings.add_hline(y=avg_savings, line_dash="dash", line_color=COLORS['accent1'],
                             annotation_text=f"Average: ${avg_savings:,.0f}")
        st.plotly_chart(fig_savings, use_container_width=True)
        
        st.divider()
        
        # --- DATA TABLE ---
        with st.expander("📋 View All Data"):
            st.dataframe(df.sort_values('Month', ascending=False), use_container_width=True)
