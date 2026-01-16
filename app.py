import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io

# --- APP CONFIG ---
st.set_page_config(page_title="Cloud K - Professional ERP", page_icon="☁️", layout="wide")

# --- DATABASE INITIALIZATION ---
if 'db' not in st.session_state:
    st.session_state.db = {
        "outlets": ["The Home Plate", "No Cap Burgers", "Pocket Pizzaz", "Witx Sandwitx", "Hello Momos", "Khushi Breakfast Club", "Bihar ka Swad"],
        "inventory": pd.DataFrame(columns=["id", "Outlet", "Item", "Qty", "Unit", "Total_Cost"]),
        "recipes": {}, 
        "menu_prices": {}, 
        "outlet_configs": {},
        "sales": pd.DataFrame(columns=["Date", "Outlet", "Dish", "Platform", "Revenue", "Comm_Paid", "Del_Cost", "Ing_Cost", "Net_Profit"]),
        "expenses": pd.DataFrame(columns=["id", "Date", "Outlet", "Category", "Amount", "Notes"])
    }

db = st.session_state.db

# --- SIDEBAR ---
st.sidebar.title("☁️ Cloud K Command")
menu = st.sidebar.radio("Navigate", [
    "Dashboard", "Sale Entry", "Misc Expenses", 
    "Stock Room", "Recipe Master", "Menu & Pricing", "Outlet & Platform Settings"
])

selected_outlet = st.sidebar.selectbox("Active Outlet", db["outlets"])

# --- 1. DASHBOARD (FIXED VALUEERROR) ---
if menu == "Dashboard":
    st.title(f"📊 {selected_outlet} Financials")
    
    s_df = db["sales"][db["sales"]["Outlet"] == selected_outlet].copy()
    e_df = db["expenses"][db["expenses"]["Outlet"] == selected_outlet].copy()

    if s_df.empty and e_df.empty:
        st.info("No data available for this outlet.")
    else:
        # Standardize dates to prevent plotting errors
        s_df['Date'] = pd.to_datetime(s_df['Date'])
        e_df['Date'] = pd.to_datetime(e_df['Date'])

        view_type = st.radio("Group By", ["Daily", "Monthly", "Yearly"], horizontal=True)
        
        if view_type == "Daily":
            fmt = '%Y-%m-%d'
        elif view_type == "Monthly":
            fmt = '%b %Y'
        else:
            fmt = '%Y'

        s_df['DisplayDate'] = s_df['Date'].dt.strftime(fmt)
        e_df['DisplayDate'] = e_df['Date'].dt.strftime(fmt)

        # Aggregate and Merge
        sales_sum = s_df.groupby('DisplayDate').agg({'Revenue': 'sum', 'Net_Profit': 'sum'}).reset_index()
        exp_sum = e_df.groupby('DisplayDate').agg({'Amount': 'sum'}).reset_index()
        
        stats = pd.merge(sales_sum, exp_sum, on='DisplayDate', how='outer').fillna(0)
        stats['Final_Profit'] = stats['Net_Profit'] - stats['Amount']

        # Visualization
        fig = px.bar(stats, x='DisplayDate', y=['Revenue', 'Final_Profit'], 
                     barmode='group', title=f"{view_type} Performance")
        st.plotly_chart(fig, use_container_width=True)

# --- 2. MISC EXPENSES (FIXED TYPEERROR & SORTING) ---
elif menu == "Misc Expenses":
    st.title(f"💸 Expenses: {selected_outlet}")
    
    with st.form("add_expense"):
        c1, c2, c3 = st.columns(3)
        cat = c1.selectbox("Category", ["Rent", "Salary", "Electricity", "Marketing", "Misc"])
        amt = c2.number_input("Amount (₹)", min_value=0.0)
        date_input = c3.date_input("Date", datetime.now())
        note = st.text_input("Notes")
        
        if st.form_submit_button("Record Expense"):
            # Store date as datetime to ensure sortability
            new_date = pd.to_datetime(date_input)
            new_id = datetime.now().strftime('%Y%m%d%H%M%S')
            new_e = pd.DataFrame([{"id": new_id, "Date": new_date, "Outlet": selected_outlet, "Category": cat, "Amount": amt, "Notes": note}])
            st.session_state.db["expenses"] = pd.concat([db["expenses"], new_e], ignore_index=True)
            st.rerun()

    st.subheader("History")
    exp_list = db["expenses"][db["expenses"]["Outlet"] == selected_outlet].copy()
    if not exp_list.empty:
        # Convert to datetime before sorting to prevent TypeError
        exp_list['Date'] = pd.to_datetime(exp_list['Date'])
        exp_list = exp_list.sort_values(by="Date", ascending=False)
        st.dataframe(exp_list[["Date", "Category", "Amount", "Notes"]], use_container_width=True)

# --- 3. SALE ENTRY ---
elif menu == "Sale Entry":
    st.title("🎯 Record Sales")
    # Logic from your previous version for deducting stock goes here...
    st.info("Ensure you have added Recipes and Inventory before logging sales.")
