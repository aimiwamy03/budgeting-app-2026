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
PAYMENT_METHODS = ["Credit", "Debit", "Cash", "Venmo", "Zelle", "Apple Pay", "Other"]

# Category icons for visual appeal
CATEGORY_ICONS = {
    "Housing": "🏠", "Utilities": "💡", "Groceries": "🛒", "Transportation": "🚗",
    "Insurance": "🛡️", "Healthcare": "🏥", "Subscriptions": "📱",
    "Food/Dining": "🍔", "Shopping": "🛍️", "Entertainment": "🎬",
    "Travel": "✈️", "Personal Care": "💅", "Misc": "📦"
}

# --- COFFEE PALETTE ---
COLORS = {
    "bg": "#F5EDE4",
    "card": "#FFFFFF",
    "accent1": "#FAFF7F",
    "accent2": "#0C9762",
    "gray": "#D4C4B5",
    "text": "#3D2B1F",
    "text_light": "#8B7355",
    "needs": "#C17767",
    "wants": "#D4A574",
    "savings": "#7A9B76",
    "danger": "#C17767",
    "warning": "#D4A574",
    "success": "#7A9B76",
}

# --- MODERN MINIMAL STYLING ---
st.markdown(f"""
    <style>
    .stApp {{ background: {COLORS['bg']}; }}
    section[data-testid="stSidebar"] {{ background: {COLORS['card']}; }}
    .stButton > button {{
        background: {COLORS['accent1']} !important;
        color: {COLORS['text']} !important;
        border: none !important;
        border-radius: 12px !important;
    }}
    .stButton > button:hover {{ background: #E8EB6F !important; }}
    .stProgress > div > div > div {{ background: {COLORS['accent2']} !important; }}
    </style>
    """, unsafe_allow_html=True)

def get_spending_score(savings_rate):
    if savings_rate >= 25: return ("A+", "🌟", COLORS['success'], "Excellent! You're crushing it!")
    elif savings_rate >= 20: return ("A", "✨", COLORS['success'], "Great job! On track!")
    elif savings_rate >= 15: return ("B", "👍", "#7AB85C", "Good! Room to grow")
    elif savings_rate >= 10: return ("C", "😐", COLORS['warning'], "Fair. Try to save more")
    elif savings_rate >= 5: return ("D", "⚠️", COLORS['warning'], "Warning: Low savings")
    else: return ("F", "🚨", COLORS['danger'], "Critical: Overspending!")

CHART_COLORS = ['#0C9762', '#FAFF7F', '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DFE6E9', '#74B9FF', '#A29BFE']

# --- GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def get_data():
    return conn.read()

def get_fresh_data():
    """Get data without cache - use when checking before save"""
    return conn.read(ttl=0)

# --- EXPENSES: GOOGLE SHEETS FUNCTIONS ---
@st.cache_data(ttl=30)
def load_expenses_from_sheets():
    """Load expenses from Google Sheets 'Expenses' worksheet"""
    try:
        df = conn.read(worksheet="Expenses", ttl=0)
        if df is not None and not df.empty:
            # Convert to list of dicts
            expenses = df.to_dict('records')
            # Clean up the data
            for e in expenses:
                e['amount'] = float(e.get('amount', 0) or 0)
            return expenses
        return []
    except Exception:
        # Worksheet doesn't exist yet - that's ok
        return []

def save_expenses_to_sheets(expenses_list):
    """Save all expenses to Google Sheets 'Expenses' worksheet"""
    if not expenses_list:
        # Create empty DataFrame with columns
        df = pd.DataFrame(columns=['month', 'date', 'category', 'description', 'amount', 'payment'])
    else:
        df = pd.DataFrame(expenses_list)
    
    try:
        conn.update(worksheet="Expenses", data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        error_msg = str(e).lower()
        if "worksheet not found" in error_msg or "worksheetnotfound" in error_msg:
            st.error("⚠️ **Setup Required:** Please create a new worksheet/tab named **'Expenses'** in your Google Sheet, then try again.")
            st.info("💡 In Google Sheets: Click the **+** button at the bottom to add a new sheet, then rename it to **Expenses**")
        else:
            st.error(f"Error saving expenses: {e}")
        return False

# --- SESSION STATE: EXPENSES (loaded from Google Sheets) ---
if 'expenses' not in st.session_state:
    st.session_state.expenses = load_expenses_from_sheets()

if 'selected_month' not in st.session_state:
    st.session_state.selected_month = datetime.now().strftime("%B")

if 'selected_year' not in st.session_state:
    st.session_state.selected_year = datetime.now().year

def get_month_key():
    return f"{st.session_state.selected_month} {st.session_state.selected_year}"

def get_month_expenses():
    """Get expenses for the currently selected month"""
    month_key = get_month_key()
    return [e for e in st.session_state.expenses if e.get('month') == month_key]

def calc_expense_totals():
    """Calculate Needs and Wants totals from expenses"""
    month_expenses = get_month_expenses()
    needs = sum(e['amount'] for e in month_expenses if e['category'] in NEEDS_CATEGORIES)
    wants = sum(e['amount'] for e in month_expenses if e['category'] in WANTS_CATEGORIES)
    return needs, wants

# --- SIDEBAR ---
st.sidebar.title("☁️ Cloud Budget")
page = st.sidebar.radio("Go to", ["📊 Budget", "📝 Expenses", "📈 Analytics"])

# Month/Year selector (shared across pages)
st.sidebar.divider()
st.sidebar.subheader("📅 Period")
months = ["January", "February", "March", "April", "May", "June", 
          "July", "August", "September", "October", "November", "December"]
current_month_idx = months.index(st.session_state.selected_month)

selected_month = st.sidebar.selectbox("Month", months, index=current_month_idx, key="month_select")
selected_year = st.sidebar.selectbox("Year", [2025, 2026, 2027], 
                                     index=[2025, 2026, 2027].index(st.session_state.selected_year), 
                                     key="year_select")

# Update session state when changed
if selected_month != st.session_state.selected_month:
    st.session_state.selected_month = selected_month
if selected_year != st.session_state.selected_year:
    st.session_state.selected_year = selected_year

db_month_key = get_month_key()

# Show expense count in sidebar
month_expenses = get_month_expenses()
st.sidebar.metric("📝 Expenses This Month", len(month_expenses))

# ============================================================
# PAGE 1: BUDGET
# ============================================================
if page == "📊 Budget":
    st.header("📊 Monthly Budget")
    st.caption(f"Tracking: **{db_month_key}**")
    
    # --- LOAD EXISTING DATA FOR THIS MONTH ---
    existing_budget = get_data()
    month_data = None
    if existing_budget is not None and not existing_budget.empty and 'Month' in existing_budget.columns:
        month_row = existing_budget[existing_budget['Month'] == db_month_key]
        if not month_row.empty:
            month_data = month_row.iloc[0]
    
    # Get default values from saved data (or 0 if no data)
    default_paycheck1 = float(month_data['Paycheck1']) if month_data is not None and 'Paycheck1' in month_data else 0.0
    default_paycheck2 = float(month_data['Paycheck2']) if month_data is not None and 'Paycheck2' in month_data else 0.0
    default_side_income = float(month_data['SideIncome']) if month_data is not None and 'SideIncome' in month_data else 0.0
    default_notes = str(month_data['Notes']) if month_data is not None and 'Notes' in month_data and pd.notna(month_data['Notes']) else ""
    
    # Show status
    if month_data is not None:
        st.success(f"✅ Loaded saved data for {db_month_key}")
    else:
        st.info(f"📝 No saved data for {db_month_key} yet")
    
    # --- INCOME SECTION ---
    st.subheader("💵 Income")
    col3, col4, col5 = st.columns(3)
    with col3:
        paycheck_1 = st.number_input("1st Paycheck", min_value=0.0, step=100.0, value=default_paycheck1)
    with col4:
        paycheck_2 = st.number_input("2nd Paycheck", min_value=0.0, step=100.0, value=default_paycheck2)
    with col5:
        side_income = st.number_input("Side Income", min_value=0.0, step=100.0, value=default_side_income)
    
    total_income = paycheck_1 + paycheck_2 + side_income
    
    col_metric, col_save = st.columns([3, 1])
    with col_metric:
        st.metric("💰 Total Monthly Income", f"${total_income:,.2f}")
    with col_save:
        overwrite = st.checkbox("Overwrite existing", value=True if month_data is not None else False)
        save_top = st.button("💾 Quick Save", use_container_width=True, key="save_top")
    
    st.divider()
    
    # --- GET EXPENSE TOTALS FROM SESSION STATE ---
    needs_val, wants_val = calc_expense_totals()
    total_expenses = needs_val + wants_val
    savings_val = total_income - needs_val - wants_val
    
    # --- BUDGET PROGRESS ---
    st.subheader("📈 Budget Progress")
    
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
            st.caption(f"Budget: **${needs_target:,.2f}**")
            color = "normal" if needs_pct <= 100 else "inverse"
            st.metric("Spent", f"${needs_val:,.2f}", f"{needs_pct:.0f}% of budget", delta_color=color)
            st.progress(min(needs_pct / 100, 1.0))
            remaining_needs = needs_target - needs_val
            if remaining_needs > 0:
                st.caption(f"💰 ${remaining_needs:,.2f} left to spend")
            elif needs_pct > 100:
                st.error(f"⚠️ Over by ${needs_val - needs_target:,.2f}")
        
        with col_b:
            st.markdown("### 🛍️ Wants (30%)")
            st.caption(f"Budget: **${wants_target:,.2f}**")
            color = "normal" if wants_pct <= 100 else "inverse"
            st.metric("Spent", f"${wants_val:,.2f}", f"{wants_pct:.0f}% of budget", delta_color=color)
            st.progress(min(wants_pct / 100, 1.0))
            remaining_wants = wants_target - wants_val
            if remaining_wants > 0:
                st.caption(f"💰 ${remaining_wants:,.2f} left to spend")
            elif wants_pct > 100:
                st.error(f"⚠️ Over by ${wants_val - wants_target:,.2f}")
        
        with col_c:
            st.markdown("### 🏦 Savings (20%)")
            st.caption(f"Goal: **${savings_target:,.2f}**")
            color = "normal" if savings_val >= 0 else "inverse"
            savings_rate_pct = (savings_val / total_income) * 100 if total_income > 0 else 0
            st.metric("Remaining", f"${savings_val:,.2f}", f"{savings_rate_pct:.0f}% of income", delta_color=color)
            st.progress(min(max(savings_rate_pct / 100, 0), 1.0))
            if savings_val < 0:
                st.error("🚨 Overspent!")
            elif savings_rate_pct >= 20:
                st.success("✅ Goal met!")
        
        # --- FINANCIAL HEALTH SCORE ---
        st.divider()
        savings_rate = (savings_val / total_income) * 100 if total_income > 0 else 0
        grade, emoji, color, message = get_spending_score(savings_rate)
        
        score_col1, score_col2 = st.columns([1, 3])
        with score_col1:
            st.markdown(f"<h1 style='text-align: center; color: {color}; font-size: 72px;'>{grade}</h1>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; font-size: 24px;'>{emoji}</p>", unsafe_allow_html=True)
        with score_col2:
            st.markdown("### Your Money Score")
            st.markdown(f"**{message}**")
            st.markdown(f"Savings Rate: **{savings_rate:.1f}%** of income")
            if savings_rate < 20:
                st.markdown(f"💡 *Tip: Try to save ${(total_income * 0.2) - savings_val:,.2f} more to hit 20%*")
    else:
        st.info("Enter your income above to see budget progress")
    
    st.divider()
    
    # --- EXPENSE SUMMARY (link to expenses page) ---
    if len(month_expenses) > 0:
        st.subheader("📝 Expense Summary")
        st.caption(f"You have **{len(month_expenses)} expenses** logged for {db_month_key}")
        
        # Quick category breakdown
        expense_df = pd.DataFrame(month_expenses)
        category_totals = expense_df.groupby('category')['amount'].sum().sort_values(ascending=False)
        
        for cat, amt in category_totals.head(5).items():
            icon = CATEGORY_ICONS.get(cat, "📦")
            st.markdown(f"{icon} **{cat}**: ${amt:,.2f}")
        
        st.info("💡 Go to **📝 Expenses** page to add or edit expenses")
    else:
        st.info("💡 No expenses logged yet. Go to **📝 Expenses** page to add some!")
    
    st.divider()
    
    notes = st.text_area("Notes", value=default_notes)
    save_bottom = st.button("🚀 Save to Google Sheets", key="save_bottom")
    
    # Handle save
    if save_top or save_bottom:
        # Get fresh data (no cache) to ensure accurate duplicate check
        existing_data = get_fresh_data()
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
            st.error(f"Entry for {db_month_key} already exists! Check 'Overwrite' to update it.")
        else:
            if is_empty:
                updated_df = new_row
            elif month_exists and overwrite:
                # Remove ALL existing rows for this month (handles duplicates too)
                existing_data = existing_data[existing_data['Month'] != db_month_key]
                updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                updated_df = updated_df.sort_values('Month').reset_index(drop=True)
            else:
                updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                updated_df = updated_df.sort_values('Month').reset_index(drop=True)
            
            conn.update(data=updated_df)
            st.cache_data.clear()  # Clear cache after saving
            if month_exists and overwrite:
                st.success(f"✅ Entry for {db_month_key} updated!")
            else:
                st.success(f"✅ Entry for {db_month_key} saved!")
            st.balloons()

# ============================================================
# PAGE 2: EXPENSES
# ============================================================
elif page == "📝 Expenses":
    st.header("📝 Expense Tracker")
    st.caption(f"Logging expenses for: **{db_month_key}**")
    
    # --- ADD NEW EXPENSE ---
    st.subheader("➕ Add New Expense")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        exp_date = st.date_input("Date", value=date.today())
    with col2:
        exp_category = st.selectbox("Category", ALL_CATEGORIES)
    with col3:
        exp_payment = st.selectbox("Payment Method", PAYMENT_METHODS)
    
    col4, col5, col6 = st.columns([2, 1, 1])
    with col4:
        exp_description = st.text_input("Description")
    with col5:
        exp_amount = st.number_input("Amount", min_value=0.0, step=1.0, format="%.2f")
    with col6:
        st.write("")
        st.write("")
        if st.button("➕ Add Expense", use_container_width=True):
            if exp_amount > 0:
                new_expense = {
                    "month": db_month_key,
                    "date": exp_date.strftime("%m/%d/%y"),
                    "category": exp_category,
                    "description": exp_description,
                    "amount": exp_amount,
                    "payment": exp_payment
                }
                st.session_state.expenses.append(new_expense)
                # Save to Google Sheets immediately
                if save_expenses_to_sheets(st.session_state.expenses):
                    st.success(f"✅ Added & saved: {exp_description} - ${exp_amount:.2f}")
                else:
                    st.warning(f"Added locally but failed to sync to Google Sheets")
                st.rerun()
            else:
                st.warning("Please enter an amount greater than 0")
    
    st.divider()
    
    # --- EXPENSE TABLE ---
    month_expenses = get_month_expenses()
    
    if len(month_expenses) > 0:
        st.subheader(f"📋 Expenses for {db_month_key}")
        
        # Convert to DataFrame for display
        expense_df = pd.DataFrame(month_expenses)
        display_cols = ['date', 'category', 'description', 'amount', 'payment']
        display_df = expense_df[display_cols].copy()
        display_df.columns = ['Date', 'Category', 'Description', 'Amount', 'Payment']
        
        # Use data_editor for editing
        edited_df = st.data_editor(
            display_df,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "Category": st.column_config.SelectboxColumn(options=ALL_CATEGORIES),
                "Payment": st.column_config.SelectboxColumn(options=PAYMENT_METHODS),
                "Amount": st.column_config.NumberColumn(format="%.2f"),
            },
            key="expense_editor"
        )
        
        # Update session state when edited
        if st.button("💾 Save Changes to Google Sheets", use_container_width=True):
            # Remove old expenses for this month
            st.session_state.expenses = [e for e in st.session_state.expenses if e.get('month') != db_month_key]
            
            # Add edited expenses back
            for _, row in edited_df.iterrows():
                if pd.notna(row['Amount']) and row['Amount'] > 0:
                    st.session_state.expenses.append({
                        "month": db_month_key,
                        "date": row['Date'],
                        "category": row['Category'],
                        "description": row['Description'],
                        "amount": float(row['Amount']),
                        "payment": row['Payment']
                    })
            
            # Save to Google Sheets
            if save_expenses_to_sheets(st.session_state.expenses):
                st.success("✅ Changes saved to Google Sheets!")
            else:
                st.warning("Saved locally but failed to sync to Google Sheets")
            st.rerun()
        
        st.divider()
        
        # --- CATEGORY BREAKDOWN ---
        st.subheader("📊 Category Breakdown")
        
        category_totals = expense_df.groupby('category')['amount'].sum().reset_index()
        category_totals['icon'] = category_totals['category'].map(lambda x: CATEGORY_ICONS.get(x, "📦") + " " + x)
        
        col_chart, col_list = st.columns([2, 1])
        
        with col_chart:
            fig_pie = px.pie(category_totals, values='amount', names='icon',
                           title="Spending by Category",
                           color_discrete_sequence=CHART_COLORS)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col_list:
            st.markdown("### 🔥 Top Spending")
            for _, row in category_totals.nlargest(5, 'amount').iterrows():
                icon = CATEGORY_ICONS.get(row['category'], "📦")
                cat_type = "Needs" if row['category'] in NEEDS_CATEGORIES else "Wants"
                st.markdown(f"{icon} **{row['category']}**: ${row['amount']:,.2f} ({cat_type})")
        
        st.divider()
        
        # --- TOTALS ---
        needs_total, wants_total = calc_expense_totals()
        total_spent = needs_total + wants_total
        
        col_t1, col_t2, col_t3 = st.columns(3)
        col_t1.metric("🏠 Needs Total", f"${needs_total:,.2f}")
        col_t2.metric("🛍️ Wants Total", f"${wants_total:,.2f}")
        col_t3.metric("💸 Total Spent", f"${total_spent:,.2f}")
        
        st.info("💡 These totals automatically sync to the **📊 Budget** page!")
    else:
        st.info("No expenses logged for this month yet. Add some above!")
        
        # Quick add suggestions
        st.markdown("### 💡 Quick Add Ideas")
        quick_cats = ["Housing", "Groceries", "Food/Dining", "Transportation"]
        cols = st.columns(4)
        for i, cat in enumerate(quick_cats):
            with cols[i]:
                icon = CATEGORY_ICONS.get(cat, "📦")
                if st.button(f"{icon} {cat}", key=f"quick_{cat}"):
                    st.session_state.quick_category = cat
                    st.rerun()

# ============================================================
# PAGE 3: ANALYTICS
# ============================================================
elif page == "📈 Analytics":
    st.title("📈 Financial Dashboard")
    df = get_data()

    if df is None or df.empty or 'Month' not in df.columns:
        st.info("The spreadsheet is empty. Add data to see analytics.")
    else:
        income_col = 'TotalIncome' if 'TotalIncome' in df.columns else 'Income'
        latest = df.iloc[-1]
        
        # --- MONTH OVERVIEW ---
        st.subheader("📊 This Month at a Glance")
        
        c1, c2, c3, c4 = st.columns(4)
        
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
        
        grade, emoji, color, message = get_spending_score(savings_rate)
        st.markdown(f"### {emoji} Financial Health: **{grade}** - {message}")
        
        st.divider()
        
        # --- SPENDING TRENDS ---
        st.subheader("📈 Spending Trends")
        
        col_line, col_pie = st.columns(2)
        
        with col_line:
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
            breakdown = pd.DataFrame({
                'Category': ['Needs', 'Wants', 'Savings'],
                'Amount': [latest['Needs'], latest['Wants'], max(latest['Savings'], 0)]
            })
            fig_donut = px.pie(breakdown, values='Amount', names='Category', hole=0.5,
                              title=f"Latest Month Breakdown ({latest['Month']})",
                              color_discrete_map={'Needs': COLORS['needs'], 'Wants': COLORS['wants'], 'Savings': COLORS['savings']})
            st.plotly_chart(fig_donut, use_container_width=True)
        
        st.divider()
        
        # --- SAVINGS PROGRESS ---
        st.subheader("🎯 Savings Journey")
        
        total_saved = df['Savings'].sum()
        avg_savings = df['Savings'].mean()
        months_tracked = len(df)
        
        s1, s2, s3 = st.columns(3)
        s1.metric("💎 Total Saved", f"${total_saved:,.2f}")
        s2.metric("📊 Avg Monthly Savings", f"${avg_savings:,.2f}")
        s3.metric("📅 Months Tracked", months_tracked)
        
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
