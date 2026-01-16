import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io

# --- APP CONFIG ---
st.set_page_config(page_title="Cloud K - Global Analytics", page_icon="☁️", layout="wide")

# --- DATABASE INITIALIZATION ---
if 'db' not in st.session_state:
    st.session_state.db = {
        "outlets": ["The Home Plate", "No Cap Burgers", "Pocket Pizzaz", "Witx Sandwitx", "Hello Momos", "Khushi Breakfast Club", "Bihar ka Swad"],
        "inventory": pd.DataFrame(columns=["id", "Outlet", "Item", "Qty", "Unit", "Total_Cost"]),
        "recipes": {}, 
        "menu_prices": {}, 
        "outlet_configs": {},
        "sales": pd.DataFrame(columns=["Date", "Outlet", "Dish", "Platform", "Revenue", "Comm_Paid", "Del_Cost", "Ing_Cost", "Net_Profit"]),
        "expenses": pd.DataFrame(columns=["Date", "Outlet", "Category", "Amount", "Notes"])
    }

db = st.session_state.db

# --- SIDEBAR ---
st.sidebar.title("☁️ Cloud K Master Control")
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

# --- 2. SALE ENTRY (CALCULATES PROFIT ON THE FLY) ---
elif menu == "Sale Entry":
    st.title(f"🎯 Log Sale: {selected_outlet}")
    
    # Get Platform Configs
    config = db["outlet_configs"].get(selected_outlet, {"Platforms": {"Direct": {"comm": 0.0, "del": 0.0}}})
    platforms = list(config["Platforms"].keys())
    dishes = list(db["menu_prices"].keys())

    if not dishes:
        st.warning("Please set your Menu Prices first!")
    else:
        with st.form("sale_form"):
            dish = st.selectbox("Select Dish", dishes)
            plat = st.selectbox("Order Platform", platforms)
            price = st.number_input("Selling Price (₹)", value=float(db["menu_prices"].get(dish, 0.0)))
            sale_date = st.date_input("Date of Sale", datetime.now())
            
            if st.form_submit_button("Submit Sale"):
                # Calculate Costs from Recipe
                ing_cost = 0
                recipe = db["recipes"].get(dish, {})
                for item, amt in recipe.items():
                    inv_match = db["inventory"][(db["inventory"]["Item"]==item) & (db["inventory"]["Outlet"]==selected_outlet)]
                    if not inv_match.empty:
                        idx = inv_match.index[0]
                        unit_cost = db["inventory"].at[idx, "Total_Cost"] / db["inventory"].at[idx, "Qty"]
                        ing_cost += (unit_cost * amt)
                        st.session_state.db["inventory"].at[idx, "Qty"] -= amt # Deduct Stock
                
                # Platform calculations
                p_data = config["Platforms"][plat]
                comm = (price * p_data['comm']) / 100
                delivery = p_data['del']
                net_profit = price - comm - delivery - ing_cost

                new_row = pd.DataFrame([{
                    "Date": sale_date, "Outlet": selected_outlet, "Dish": dish, "Platform": plat,
                    "Revenue": price, "Comm_Paid": comm, "Del_Cost": delivery, "Ing_Cost": ing_cost, "Net_Profit": net_profit
                }])
                st.session_state.db["sales"] = pd.concat([db["sales"], new_row], ignore_index=True)
                st.success(f"Profit of ₹{round(net_profit, 2)} recorded.")

# --- 3import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io

# --- APP CONFIG ---
st.set_page_config(page_title="Cloud K - Global Analytics", page_icon="☁️", layout="wide")

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
st.sidebar.title("☁️ Cloud K Master Control")
menu = st.sidebar.radio("Navigate", [
    "Dashboard", "Sale Entry", "Misc Expenses", 
    "Stock Room", "Recipe Master", "Menu & Pricing", "Outlet & Platform Settings"
])

selected_outlet = st.sidebar.selectbox("Active Outlet", db["outlets"])

