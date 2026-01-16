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

# --- 1. DASHBOARD (STRICT DATE-BASED ANALYTICS) ---
if menu == "Dashboard":
    st.title(f"📊 {selected_outlet}: Financial Engine")
    
    # 1. Filter Data by Selected Outlet
    s_df = db["sales"][db["sales"]["Outlet"] == selected_outlet].copy()
    e_df = db["expenses"][db["expenses"]["Outlet"] == selected_outlet].copy()

    if s_df.empty and e_df.empty:
        st.info("No data found. Start by entering sales or expenses!")
    else:
        # Ensure Date columns are datetime objects
        s_df['Date'] = pd.to_datetime(s_df['Date'])
        e_df['Date'] = pd.to_datetime(e_df['Date'])

        # 2. Time View Selection
        view_type = st.radio("Switch View", ["Monthly Analytics", "Yearly Analytics"], horizontal=True)
        
        # 3. Aggregation Logic
        if view_type == "Monthly Analytics":
            s_df['Period'] = s_df['Date'].dt.strftime('%b %Y')
            e_df['Period'] = e_df['Date'].dt.strftime('%b %Y')
        else:
            s_df['Period'] = s_df['Date'].dt.strftime('%Y')
            e_df['Period'] = e_df['Date'].dt.strftime('%Y')

        # Calculate Grouped Data
        monthly_sales = s_df.groupby('Period').agg({
            'Revenue': 'sum', 'Comm_Paid': 'sum', 'Del_Cost': 'sum', 'Ing_Cost': 'sum', 'Net_Profit': 'sum'
        }).reset_index()
        
        monthly_exp = e_df.groupby('Period').agg({'Amount': 'sum'}).reset_index()
        
        # Combine Sales and Expenses for True Profit
        final_stats = pd.merge(monthly_sales, monthly_exp, on='Period', how='outer').fillna(0)
        final_stats['Final_Profit'] = final_stats['Net_Profit'] - final_stats['Amount']

        # 4. Display Key Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Revenue", f"₹{round(final_stats['Revenue'].sum(), 2)}")
        m2.metric("Inventory Costs", f"₹{round(final_stats['Ing_Cost'].sum(), 2)}")
        m3.metric("Platform & Delivery", f"₹{round(final_stats['Comm_Paid'].sum() + final_stats['Del_Cost'].sum(), 2)}")
        
        actual_profit = final_stats['Final_Profit'].sum()
        if actual_profit >= 0:
            m4.metric("Net Profit", f"₹{round(actual_profit, 2)}", delta_color="normal")
        else:
            m4.metric("Net Loss", f"₹{round(actual_profit, 2)}", delta="LOSS", delta_color="inverse")

        # 5. Visual Trend Analysis
        st.subheader(f"{view_type} Trend")
        
        fig = px.bar(final_stats, x='Period', y=['Revenue', 'Final_Profit'],
                     barmode='group', 
                     color_discrete_map={'Revenue': '#3498db', 'Final_Profit': '#2ecc71'},
                     labels={'value': 'Amount (₹)', 'variable': 'Financial Category'})
        st.plotly_chart(fig, use_container_width=True)

        # 6. Breakdown Table
        with st.expander("View Detailed Raw Data"):
            st.dataframe(final_stats.sort_values('Period', ascending=False))

# --- 2. MISC EXPENSES (UPDATED WORKING DELETE) ---
elif menu == "Misc Expenses":
    st.title(f"💸 Expenses: {selected_outlet}")
    
    # 1. Entry Form
    with st.form("add_expense", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        cat = c1.selectbox("Category", ["Rent", "Salary", "Electricity", "Marketing", "Misc"])
        amt = c2.number_input("Amount (₹)", min_value=0.0)
        date_input = c3.date_input("Date", datetime.now())
        note = st.text_input("Notes")
        
        if st.form_submit_button("Record Expense"):
            # Create a unique ID and ensure date is a timestamp
            new_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
            new_date = pd.to_datetime(date_input)
            
            new_e = pd.DataFrame([{
                "id": new_id, 
                "Date": new_date, 
                "Outlet": selected_outlet, 
                "Category": cat, 
                "Amount": amt, 
                "Notes": note
            }])
            
            # Update the main database
            st.session_state.db["expenses"] = pd.concat([st.session_state.db["expenses"], new_e], ignore_index=True)
            st.success("Expense Recorded Successfully!")
            st.rerun()

    st.divider()
    st.subheader("📜 Expense History")

    # 2. History & Functional Delete
    # We get the full dataframe and keep the index so we know exactly what to delete
    exp_df = st.session_state.db["expenses"]
    
    # Filter for the current outlet
    outlet_exp = exp_df[exp_df["Outlet"] == selected_outlet]

    if not outlet_exp.empty:
        # Sort by date (newest first)
        outlet_exp = outlet_exp.sort_values(by="Date", ascending=False)

        # Create table headers
        h1, h2, h3, h4, h5 = st.columns([2, 2, 1.5, 3, 1])
        h1.write("**Date**")
        h2.write("**Category**")
        h3.write("**Amount**")
        h4.write("**Notes**")
        h5.write("**Action**")

        for idx, row in outlet_exp.iterrows():
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 2, 1.5, 3, 1])
                
                # Format date for display
                disp_date = row['Date'].strftime('%d-%m-%Y') if isinstance(row['Date'], datetime) else str(row['Date'])
                
                col1.write(disp_date)
                col2.write(row['Category'])
                col3.write(f"₹{row['Amount']}")
                col4.write(row['Notes'])
                
                # The Actual Delete Button
                # We use the unique index 'idx' from the original dataframe
                if col5.button("🗑️", key=f"del_{row['id']}"):
                    st.session_state.db["expenses"] = st.session_state.db["expenses"].drop(idx)
                    st.toast(f"Deleted {row['Category']} expense")
                    st.rerun()
    else:
        st.info("No expenses found for this outlet.")

# --- 3. SALE ENTRY ---
elif menu == "Sale Entry":
    st.title("🎯 Record Sales")
    # Logic from your previous version for deducting stock goes here...
    st.info("Ensure you have added Recipes and Inventory before logging sales.")
