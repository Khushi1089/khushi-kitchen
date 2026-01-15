import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- APP CONFIG ---
st.set_page_config(page_title="Cloud K - Global ERP", page_icon="☁️", layout="wide")

# --- DATABASE INITIALIZATION ---
# This holds all your data while the app is running
if 'db' not in st.session_state:
    st.session_state.db = {
        "outlets": ["The Home Plate", "Hello Momos"],
        "inventory": pd.DataFrame(columns=["Outlet", "Item", "Qty", "Unit", "Total_Cost"]),
        "recipes": {}, 
        "menu_prices": {}, 
        "outlet_platforms": {
            "The Home Plate": {"Zomato": 25.0, "Swiggy": 25.0, "Direct": 0.0},
            "Hello Momos": {"Direct": 0.0}
        },
        "sales": pd.DataFrame(columns=["Date", "Outlet", "Dish", "Platform", "Base_Price", "Commission", "Tax", "Delivery", "Net_Profit"]),
        "expenses": pd.DataFrame(columns=["Date", "Outlet", "Category", "Amount", "Notes"])
    }

db = st.session_state.db

# --- SIDEBAR NAV ---
st.sidebar.title("☁️ Cloud K Command")
menu = st.sidebar.radio("Navigate", [
    "Dashboard", 
    "Sale Entry", 
    "Misc Expenses", 
    "Menu & Pricing", 
    "Stock Room", 
    "Recipe Master", 
    "Outlet & Platforms", 
    "Unit Converter"
])

# --- 1. OUTLET & PLATFORM SETTINGS ---
if menu == "Outlet & Platforms":
    st.title("🏢 Outlet & Platform Management")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Add New Outlet")
        new_out = st.text_input("Outlet Name", placeholder="e.g., Burger Bhau")
        if st.button("Register Outlet"):
            if new_out and new_out not in db["outlets"]:
                db["outlets"].append(new_out)
                db["outlet_platforms"][new_out] = {"Direct": 0.0}
                st.success(f"{new_out} is now active!")
                st.rerun()
    
    with col2:
        st.subheader("Configure Platforms")
        target_out = st.selectbox("Select Outlet to Edit", db["outlets"])
        p_name = st.text_input("Platform Name", placeholder="e.g., Zomato")
        p_comm = st.number_input("Commission % for this Platform", min_value=0.0, max_value=100.0, step=1.0)
        
        if st.button(f"Link {p_name} to {target_out}"):
            db["outlet_platforms"][target_out][p_name] = p_comm
            st.success(f"Linked {p_name} at {p_comm}% commission.")

# --- ACTIVE OUTLET SELECTION ---
if menu not in ["Outlet & Platforms", "Unit Converter"]:
    selected_outlet = st.sidebar.selectbox("Active Outlet", db["outlets"])
    outlet_inv = db["inventory"][db["inventory"]["Outlet"] == selected_outlet]

# --- 2. MENU & PRICING ---
elif menu == "Menu & Pricing":
    st.title("💰 Preset Menu Prices")
    st.info("Set your dish prices here so you don't have to type them during every sale.")
    all_dishes = list(db["recipes"].keys())
    if not all_dishes:
        st.warning("Please create your recipes first!")
    else:
        for dish in all_dishes:
            current_p = db["menu_prices"].get(dish, 0.0)
            new_p = st.number_input(f"Selling Price: {dish} (₹)", value=float(current_p), key=dish)
            db["menu_prices"][dish] = new_p
        if st.button("Save All Prices"):
            st.success("All prices locked in!")

# --- 3. SALE ENTRY ---
elif menu == "Sale Entry":
    st.title(f"🎯 New Sale: {selected_outlet}")
    platforms = list(db["outlet_platforms"].get(selected_outlet, {"Direct": 0.0}).keys())
    
    if not db["menu_prices"]: 
        st.error("Go to 'Menu & Pricing' to set prices first!")
    else:
        c1, c2 = st.columns(2)
        dish = c1.selectbox("What was sold?", list(db["menu_prices"].keys()))
        platform = c2.selectbox("Order Platform", platforms)
        
        col1, col2, col3 = st.columns(3)
        base_price = col1.number_input("Dish Price", value=db["menu_prices"][dish])
        tax_val = col2.number_input("GST / Tax (₹)", min_value=0.0)
        del_charge = col3.number_input("Delivery Fee (₹)", min_value=0.0)
        
        comm_pct = db["outlet_platforms"][selected_outlet].get(platform, 0.0)
        comm_amt = (base_price * comm_pct) / 100
        
        st.divider()
        st.write(f"**Platform Fee:** ₹{comm_amt} | **Customer Pays:** ₹{base_price + tax_val + del_charge}")

        if st.button("Confirm & Deduct Stock"):
            # Stock deduction logic
            recipe = db["recipes"].get(dish, {})
            cost = 0
            for item, req in recipe.items():
                row = outlet_inv[outlet_inv["Item"] == item]
                if not row.empty:
                    u_cost = row["Total_Cost"].values[0] / max(1, row["Qty"].values[0])
                    cost += (u_cost * req)
                    st.session_state.db["inventory"].loc[(db["inventory"]["Outlet"]==selected_outlet)&(db["inventory"]["Item"]==item), "Qty"] -= req
            
            net_p = base_price - comm_amt - cost
            new_s = pd.DataFrame([{
                "Date": datetime.now(), "Outlet": selected_outlet, "Dish": dish, 
                "Platform": platform, "Base_Price": base_price, 
                "Commission": comm_amt, "Tax": tax_val, "Delivery": del_charge, "Net_Profit": net_p
            }])
            st.session_state.db["sales"] = pd.concat([db["sales"], new_s], ignore_index=True)
            st.balloons()

# --- 4. MISC EXPENSES (New Request) ---
elif menu == "Misc Expenses":
    st.title(f"💸 Outlet Expenses: {selected_outlet}")
    with st.form("exp_form"):
        cat = st.selectbox("Category", ["Rent", "Electricity", "Staff Salary", "Packaging", "Marketing", "Other"])
        amt = st.number_input("Amount (₹)", min_value=0.0)
        note = st.text_input("Notes")
        if st.form_submit_button("Log Expense"):
            new_e = pd.DataFrame([{"Date": datetime.now(), "Outlet": selected_outlet, "Category": cat, "Amount": amt, "Notes": note}])
            st.session_state.db["expenses"] = pd.concat([db["expenses"], new_e], ignore_index=True)
            st.success("Expense added to books.")
    
    st.subheader("Recent Expenses")
    st.dataframe(db["expenses"][db["expenses"]["Outlet"] == selected_outlet])

# --- 5. DASHBOARD ---
elif menu == "Dashboard":
    st.title(f"📊 {selected_outlet} Insights")
    df = db["sales"][db["sales"]["Outlet"] == selected_outlet].copy()
    ex_df = db["expenses"][db["expenses"]["Outlet"] == selected_outlet].copy()
    
    m1, m2, m3 = st.columns(3)
    total_rev = df['Base_Price'].sum() if not df.empty else 0
    total_exp = ex_df['Amount'].sum() if not ex_df.empty else 0
    
    m1.metric("Gross Sales", f"₹{total_rev}")
    m2.metric("Total Expenses", f"₹{total_exp}")
    m3.metric("Final Profit", f"₹{round(df['Net_Profit'].sum() - total_exp, 2) if not df.empty else -total_exp}")

    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])
        fig = px.bar(df.groupby(df['Date'].dt.date).sum().reset_index(), x='Date', y='Net_Profit', title="Daily Profit Trend")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Log your first sale to see the chart!")

# (Stock Room and Recipe Master sections omitted for brevity but included in the same logic)
elif menu == "Stock Room":
    st.title(f"📦 {selected_outlet} Stock")
    with st.expander("Add Raw Material"):
        c1, c2, c3 = st.columns(3)
        n = c1.text_input("Item Name")
        q = c2.number_input("Qty", min_value=0.0)
        p = c3.number_input("Total Purchase Cost", min_value=0.0)
        if st.button("Add"):
            new_r = {"Outlet": selected_outlet, "Item": n, "Qty": q, "Unit": "Units", "Total_Cost": p}
            st.session_state.db["inventory"] = pd.concat([db["inventory"], pd.DataFrame([new_r])], ignore_index=True)
    st.dataframe(db["inventory"][db["inventory"]["Outlet"] == selected_outlet])

elif menu == "Recipe Master":
    st.title("👨‍🍳 Master Recipes")
    dish_n = st.text_input("New Dish Name")
    items = db["inventory"]["Item"].unique()
    if len(items) > 0:
        sel = st.multiselect("Select Ingredients", items)
        if st.button("Save Dish"):
            db["recipes"][dish_n] = {i: 1.0 for i in sel} # Simplified for now
            st.success("Dish Created!")
