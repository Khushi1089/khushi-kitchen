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

# --- 1. DASHBOARD (FIXED DATE TYPES) ---
if menu == "Dashboard":
    st.title(f"📊 {selected_outlet}: Financial Engine")
    
    s_df = db["sales"][db["sales"]["Outlet"] == selected_outlet].copy()
    e_df = db["expenses"][db["expenses"]["Outlet"] == selected_outlet].copy()

    if s_df.empty and e_df.empty:
        st.info("No data found. Start by entering sales or expenses!")
    else:
        # CRITICAL FIX: Ensure uniform datetime types before grouping
        s_df['Date'] = pd.to_datetime(s_df['Date'])
        e_df['Date'] = pd.to_datetime(e_df['Date'])

        view_type = st.radio("Switch View", ["Monthly Analytics", "Yearly Analytics"], horizontal=True)
        
        fmt = '%b %Y' if view_type == "Monthly Analytics" else '%Y'
        s_df['Period'] = s_df['Date'].dt.strftime(fmt)
        e_df['Period'] = e_df['Date'].dt.strftime(fmt)

        monthly_sales = s_df.groupby('Period').agg({
            'Revenue': 'sum', 'Comm_Paid': 'sum', 'Del_Cost': 'sum', 'Ing_Cost': 'sum', 'Net_Profit': 'sum'
        }).reset_index()
        
        monthly_exp = e_df.groupby('Period').agg({'Amount': 'sum'}).reset_index()
        
        final_stats = pd.merge(monthly_sales, monthly_exp, on='Period', how='outer').fillna(0)
        final_stats['Final_Profit'] = final_stats['Net_Profit'] - final_stats['Amount']

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Revenue", f"₹{round(final_stats['Revenue'].sum(), 2)}")
        m2.metric("Inventory Costs", f"₹{round(final_stats['Ing_Cost'].sum(), 2)}")
        m3.metric("Platform & Delivery", f"₹{round(final_stats['Comm_Paid'].sum() + final_stats['Del_Cost'].sum(), 2)}")
        
        actual_profit = final_stats['Final_Profit'].sum()
        m4.metric("Net Profit", f"₹{round(actual_profit, 2)}", delta=f"{round(actual_profit, 2)}")

        fig = px.bar(final_stats, x='Period', y=['Revenue', 'Final_Profit'], barmode='group',
                     color_discrete_map={'Revenue': '#3498db', 'Final_Profit': '#2ecc71'})
        st.plotly_chart(fig, use_container_width=True)

# --- 2. MISC EXPENSES (FIXED TYPE ERROR & WORKING DELETE) ---
elif menu == "Misc Expenses":
    st.title(f"💸 Expenses: {selected_outlet}")
    
    with st.form("add_expense", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        cat = c1.selectbox("Category", ["Rent", "Salary", "Electricity", "Marketing", "Misc"])
        amt = c2.number_input("Amount (₹)", min_value=0.0)
        date_input = c3.date_input("Date", datetime.now())
        note = st.text_input("Notes")
        
        if st.form_submit_button("Record Expense"):
            # Ensure unique ID with microsecond precision
            new_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
            # CRITICAL FIX: Always convert input date to pandas datetime
            new_date = pd.to_datetime(date_input)
            
            new_e = pd.DataFrame([{
                "id": new_id, "Date": new_date, "Outlet": selected_outlet, 
                "Category": cat, "Amount": amt, "Notes": note
            }])
            
            st.session_state.db["expenses"] = pd.concat([st.session_state.db["expenses"], new_e], ignore_index=True)
            st.success("Expense Recorded!")
            st.rerun()

    st.divider()
    st.subheader("📜 Expense History")

    # Get a fresh reference and force datetime conversion to prevent sort errors
    exp_df = st.session_state.db["expenses"].copy()
    exp_df['Date'] = pd.to_datetime(exp_df['Date'])
    
    outlet_exp = exp_df[exp_df["Outlet"] == selected_outlet]

    if not outlet_exp.empty:
        # Sorting now works because all values in 'Date' are uniform
        outlet_exp = outlet_exp.sort_values(by="Date", ascending=False)

        h1, h2, h3, h4, h5 = st.columns([2, 2, 1.5, 3, 1])
        h1.write("**Date**")
        h2.write("**Category**")
        h3.write("**Amount**")
        h4.write("**Notes**")
        h5.write("**Action**")

        for idx, row in outlet_exp.iterrows():
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 2, 1.5, 3, 1])
                col1.write(row['Date'].strftime('%d-%b-%Y'))
                col2.write(row['Category'])
                col3.write(f"₹{row['Amount']}")
                col4.write(row['Notes'])
                
                # Use the ID for the button key but the index (idx) for the drop command
                if col5.button("🗑️", key=f"del_{row['id']}"):
                    st.session_state.db["expenses"] = st.session_state.db["expenses"].drop(idx)
                    st.rerun()
    else:
        st.info("No expenses found.")

# --- 3. SALE ENTRY ---
elif menu == "Sale Entry":
    st.title("🎯 Record Sales")
    st.info("Ensure you have added Recipes and Inventory before logging sales.")
