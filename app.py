import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io

# --- APP CONFIG ---
st.set_page_config(page_title="Cloud K - Financial Analytics", page_icon="☁️", layout="wide")

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
st.sidebar.title("☁️ Cloud K Command")
menu = st.sidebar.radio("Navigate", [
    "Dashboard", "Sale Entry", "Misc Expenses", 
    "Stock Room", "Recipe Master", "Menu & Pricing", "Outlet & Platform Settings"
])

selected_outlet = st.sidebar.selectbox("Active Outlet", db["outlets"])

# --- 1. DASHBOARD (REBUILT FOR PROFIT & LOSS) ---
if menu == "Dashboard":
    st.title(f"📊 Financial Performance: {selected_outlet}")
    
    # Filtering Data
    s_df = db["sales"][db["sales"]["Outlet"] == selected_outlet].copy()
    e_df = db["expenses"][db["expenses"]["Outlet"] == selected_outlet].copy()
    
    # Time View Selection
    view = st.radio("View Analytics By", ["Monthly", "Yearly"], horizontal=True)
    
    if not s_df.empty or not e_df.empty:
        # Convert dates
        if not s_df.empty: s_df['Date'] = pd.to_datetime(s_df['Date'])
        if not e_df.empty: e_df['Date'] = pd.to_datetime(e_df['Date'])
        
        # Calculate Metrics
        total_rev = s_df['Revenue'].sum() if not s_df.empty else 0
        total_comm = s_df['Comm_Paid'].sum() if not s_df.empty else 0
        total_del = s_df['Del_Cost'].sum() if not s_df.empty else 0
        total_ing_cost = s_df['Ing_Cost'].sum() if not s_df.empty else 0
        total_misc_exp = e_df['Amount'].sum() if not e_df.empty else 0
        
        # Final Profit Calculation
        # Revenue - (Platform Fees + Delivery + Ingredients + Misc Expenses)
        final_profit = total_rev - (total_comm + total_del + total_ing_cost + total_misc_exp)

        # Display Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Gross Revenue", f"₹{total_rev}")
        c2.metric("Total COGS (Ingredients)", f"₹{round(total_ing_cost, 2)}")
        c3.metric("Operating Expenses", f"₹{total_misc_exp}")
        
        if final_profit >= 0:
            c4.metric("Net Profit", f"₹{round(final_profit, 2)}", delta_color="normal")
        else:
            c4.metric("Net Loss", f"₹{round(final_profit, 2)}", delta="-Loss", delta_color="inverse")

        st.divider()

        # Graph Logic
        if not s_df.empty:
            format_str = '%b %Y' if view == "Monthly" else '%Y'
            s_df['Period'] = s_df['Date'].dt.strftime(format_str)
            
            # Grouping for Chart
            chart_data = s_df.groupby('Period').agg({
                'Revenue': 'sum', 
                'Net_Profit': 'sum'
            }).reset_index()
            
            # Subtracting monthly misc expenses from net profit in chart
            if not e_df.empty:
                e_df['Period'] = e_df['Date'].dt.strftime(format_str)
                e_monthly = e_df.groupby('Period')['Amount'].sum()
                chart_data['Actual_Profit'] = chart_data.apply(
                    lambda x: x['Net_Profit'] - e_monthly.get(x['Period'], 0), axis=1
                )
            else:
                chart_data['Actual_Profit'] = chart_data['Net_Profit']

            fig = px.bar(chart_data, x='Period', y=['Revenue', 'Actual_Profit'],
                         title=f"{view} Revenue vs Actual Profit",
                         labels={'value': 'Amount (₹)', 'variable': 'Category'},
                         barmode='group',
                         color_discrete_map={'Revenue': '#3498db', 'Actual_Profit': '#2ecc71'})
            st.plotly_chart(fig, use_container_width=True)
            
            

    else:
        st.info("No data available to generate a report.")

# --- 2. SALE ENTRY (Stock Deduction + Profit Calc) ---
elif menu == "Sale Entry":
    st.title(f"🎯 Sale Entry: {selected_outlet}")
    config = db["outlet_configs"].get(selected_outlet, {"Platforms": {"Direct": {"comm": 0.0, "del": 0.0}}})
    platforms = list(config["Platforms"].keys())
    dishes = list(db["menu_prices"].keys())
    
    if not dishes:
        st.error("No dishes in Menu. Create Recipe and set Pricing first.")
    else:
        with st.form("sale_entry"):
            dish = st.selectbox("Dish", dishes)
            platform = st.selectbox("Platform", platforms)
            price = st.number_input("Price (₹)", value=db["menu_prices"][dish])
            
            if st.form_submit_button("Log Sale"):
                ing_cost = 0
                recipe = db["recipes"].get(dish, {})
                for item, amt in recipe.items():
                    inv_idx = db["inventory"][(db["inventory"]["Item"]==item) & (db["inventory"]["Outlet"]==selected_outlet)].index
                    if not inv_idx.empty:
                        idx = inv_idx[0]
                        ing_cost += (db["inventory"].at[idx, "Total_Cost"] / db["inventory"].at[idx, "Qty"]) * amt
                        st.session_state.db["inventory"].at[idx, "Qty"] -= amt
                
                p_data = config["Platforms"][platform]
                comm = (price * p_data['comm']) / 100
                d_fee = p_data['del']
                profit = price - comm - d_fee - ing_cost
                
                new_s = pd.DataFrame([{
                    "Date": datetime.now(), "Outlet": selected_outlet, "Dish": dish, "Platform": platform,
                    "Revenue": price, "Comm_Paid": comm, "Del_Cost": d_fee, "Ing_Cost": ing_cost, "Net_Profit": profit
                }])
                st.session_state.db["sales"] = pd.concat([db["sales"], new_s], ignore_index=True)
                st.success("Sale Recorded and Stock Deducted!")

# --- 3. MISC EXPENSES ---
elif menu == "Misc Expenses":
    st.title(f"💸 Log Expenses: {selected_outlet}")
    with st.form("exp_form"):
        cat = st.selectbox("Category", ["Rent", "Salary", "Electricity", "Packaging", "Marketing", "Other"])
        amt = st.number_input("Amount (₹)", min_value=0.0)
        note = st.text_input("Notes")
        if st.form_submit_button("Save"):
            new_e = pd.DataFrame([{"Date": datetime.now(), "Outlet": selected_outlet, "Category": cat, "Amount": amt, "Notes": note}])
            st.session_state.db["expenses"] = pd.concat([db["expenses"], new_e], ignore_index=True)
            st.success("Expense added to P&L calculation.")

# --- (STOCK ROOM, RECIPE MASTER, MENU & OUTLET SETTINGS REMAIN UNCHANGED FOR STABILITY) ---
elif menu == "Stock Room":
    st.title(f"📦 Inventory: {selected_outlet}")
    with st.expander("➕ Add Stock Item"):
        with st.form("add_stock"):
            c1, c2, c3, c4 = st.columns(4)
            item_name = c1.text_input("Item Name")
            qty = c2.number_input("Quantity", min_value=0.01)
            unit = c3.selectbox("Unit", ["Grams", "Kg", "Pieces", "ML", "Liters"])
            cost = c4.number_input("Total Purchase Cost (₹)", min_value=0.0)
            if st.form_submit_button("Add"):
                new_row = pd.DataFrame([{"id": len(db["inventory"])+1, "Outlet": selected_outlet, "Item": item_name, "Qty": qty, "Unit": unit, "Total_Cost": cost}])
                st.session_state.db["inventory"] = pd.concat([db["inventory"], new_row], ignore_index=True)
                st.rerun()

    curr_inv = db["inventory"][db["inventory"]["Outlet"] == selected_outlet]
    for idx, row in curr_inv.iterrows():
        is_low = (row['Unit'] in ['Grams', 'ML'] and row['Qty'] < 500) or (row['Unit'] in ['Pieces', 'Kg', 'Liters'] and row['Qty'] < 10)
        c_a, c_b = st.columns([4, 1])
        if is_low: c_a.error(f"⚠️ {row['Item']}: {row['Qty']} {row['Unit']} (LOW)")
        else: c_a.info(f"{row['Item']}: {row['Qty']} {row['Unit']}")
        if c_b.button("🗑️", key=f"del_{row['id']}"):
            st.session_state.db["inventory"] = db["inventory"].drop(idx); st.rerun()

elif menu == "Recipe Master":
    st.title("👨‍🍳 Recipe Master")
    items = db["inventory"][db["inventory"]["Outlet"] == selected_outlet]["Item"].unique()
    if len(items) == 0: st.warning("Add stock first.")
    else:
        with st.form("recipe"):
            dish = st.text_input("Dish Name")
            sel = st.multiselect("Select Ingredients", items)
            recipe_map = {}
            for i in sel:
                u = db["inventory"][db["inventory"]["Item"] == i]["Unit"].iloc[0]
                recipe_map[i] = st.number_input(f"{i} ({u}) used", min_value=0.0)
            if st.form_submit_button("Save"):
                db["recipes"][dish] = recipe_map; st.success("Recipe Saved!")

elif menu == "Menu & Pricing":
    st.title("💰 Menu Pricing")
    for dish in db["recipes"].keys():
        db["menu_prices"][dish] = st.number_input(f"Price: {dish}", value=float(db["menu_prices"].get(dish, 0.0)))
    if st.button("Lock Prices"): st.success("Pricing Updated!")

elif menu == "Outlet & Platform Settings":
    st.title("⚙️ Config")
    p_name = st.text_input("Platform")
    p_comm = st.number_input("Commission %")
    p_del = st.number_input("Delivery Charge")
    if st.button("Add"):
        if selected_outlet not in db["outlet_configs"]: db["outlet_configs"][selected_outlet] = {"Platforms": {}}
        db["outlet_configs"][selected_outlet]["Platforms"][p_name] = {"comm": p_comm, "del": p_del}
        st.success("Linked!")
