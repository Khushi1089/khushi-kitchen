import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io

# --- APP CONFIG ---
st.set_page_config(page_title="Cloud K - Global ERP", page_icon="☁️", layout="wide")

# --- DATABASE INITIALIZATION ---
if 'db' not in st.session_state:
    st.session_state.db = {
        "outlets": ["The Home Plate", "Hello Momos", "Burger Bhau"],
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

# --- SIDEBAR NAVIGATION ---
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
        new_out = st.text_input("Outlet Name")
        if st.button("Register Outlet"):
            if new_out and new_out not in db["outlets"]:
                db["outlets"].append(new_out)
                db["outlet_platforms"][new_out] = {"Direct": 0.0}
                st.success(f"{new_out} Registered!")
                st.rerun()
    with col2:
        st.subheader("Configure Platforms")
        target_out = st.selectbox("Select Outlet", db["outlets"])
        p_name = st.text_input("Platform Name (Zomato/Swiggy/etc)")
        p_comm = st.number_input("Commission %", min_value=0.0, max_value=100.0)
        if st.button(f"Link to {target_out}"):
            db["outlet_platforms"][target_out][p_name] = p_comm
            st.success("Linked!")

# --- ACTIVE OUTLET SELECTOR ---
if menu not in ["Outlet & Platforms", "Unit Converter"]:
    selected_outlet = st.sidebar.selectbox("Active Outlet", db["outlets"])
    outlet_inv = db["inventory"][db["inventory"]["Outlet"] == selected_outlet]

# --- 2. MENU & PRICING ---
elif menu == "Menu & Pricing":
    st.title("💰 Preset Menu Prices")
    all_dishes = list(db["recipes"].keys())
    if not all_dishes:
        st.warning("Create recipes first!")
    else:
        for dish in all_dishes:
            current_p = db["menu_prices"].get(dish, 0.0)
            db["menu_prices"][dish] = st.number_input(f"Price for {dish} (₹)", value=float(current_p))
        st.success("Prices Saved!")

# --- 3. SALE ENTRY ---
elif menu == "Sale Entry":
    st.title(f"🎯 New Sale: {selected_outlet}")
    platforms = list(db["outlet_platforms"].get(selected_outlet, {"Direct": 0.0}).keys())
    if not db["menu_prices"]: st.error("Set Menu Prices first!")
    else:
        c1, c2 = st.columns(2)
        dish = c1.selectbox("Dish", list(db["menu_prices"].keys()))
        platform = c2.selectbox("Platform", platforms)
        col1, col2, col3 = st.columns(3)
        base_p = col1.number_input("Base Price", value=db["menu_prices"][dish])
        tax = col2.number_input("Tax (₹)", min_value=0.0)
        deliv = col3.number_input("Delivery (₹)", min_value=0.0)
        
        comm_amt = (base_p * db["outlet_platforms"][selected_outlet].get(platform, 0.0)) / 100
        if st.button("Confirm Sale"):
            # Stock Deduction
            recipe = db["recipes"].get(dish, {})
            cost = 0
            for item, req in recipe.items():
                row = outlet_inv[outlet_inv["Item"] == item]
                if not row.empty:
                    u_cost = row["Total_Cost"].values[0] / max(1, row["Qty"].values[0])
                    cost += (u_cost * req)
                    st.session_state.db["inventory"].loc[(db["inventory"]["Outlet"]==selected_outlet)&(db["inventory"]["Item"]==item), "Qty"] -= req
            
            new_s = pd.DataFrame([{
                "Date": datetime.now(), "Outlet": selected_outlet, "Dish": dish, "Platform": platform, 
                "Base_Price": base_p, "Commission": comm_amt, "Tax": tax, "Delivery": deliv, "Net_Profit": base_p - comm_amt - cost
            }])
            st.session_state.db["sales"] = pd.concat([db["sales"], new_s], ignore_index=True)
            st.balloons()

# --- 4. MISC EXPENSES ---
elif menu == "Misc Expenses":
    st.title(f"💸 Expenses: {selected_outlet}")
    with st.form("exp"):
        cat = st.selectbox("Category", ["Rent", "Salary", "Electricity", "Packaging", "Marketing", "Misc"])
        amt = st.number_input("Amount (₹)", min_value=0.0)
        note = st.text_input("Notes")
        if st.form_submit_button("Save Expense"):
            new_e = pd.DataFrame([{"Date": datetime.now(), "Outlet": selected_outlet, "Category": cat, "Amount": amt, "Notes": note}])
            st.session_state.db["expenses"] = pd.concat([db["expenses"], new_e], ignore_index=True)

# --- 5. DASHBOARD & DOWNLOAD ---
elif menu == "Dashboard":
    st.title(f"📊 {selected_outlet} Analytics")
    sales_df = db["sales"][db["sales"]["Outlet"] == selected_outlet]
    exp_df = db["expenses"][db["expenses"]["Outlet"] == selected_outlet]
    
    m1, m2, m3 = st.columns(3)
    rev = sales_df["Base_Price"].sum() if not sales_df.empty else 0
    exps = exp_df["Amount"].sum() if not exp_df.empty else 0
    prof = (sales_df["Net_Profit"].sum() if not sales_df.empty else 0) - exps
    
    m1.metric("Total Revenue", f"₹{rev}")
    m2.metric("Total Expenses", f"₹{exps}")
    m3.metric("Net Profit (Rokda)", f"₹{round(prof, 2)}")

    if not sales_df.empty:
        fig = px.line(sales_df, x='Date', y='Net_Profit', title="Profit Trend")
        st.plotly_chart(fig, use_container_width=True)
        
        # EXCEL DOWNLOAD FEATURE
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            sales_df.to_excel(writer, sheet_name='Sales')
            exp_df.to_excel(writer, sheet_name='Expenses')
        st.download_button(label="📥 Download Excel Report", data=buffer, file_name=f"{selected_outlet}_Report.xlsx")
    else:
        st.info("No data yet!")

# --- STOCK & RECIPE (Core Logic) ---
elif menu == "Stock Room":
    st.title(f"📦 {selected_outlet} Stock")
    with st.expander("Add Stock"):
        n = st.text_input("Item")
        q = st.number_input("Qty", min_value=0.0)
        p = st.number_input("Total Cost", min_value=0.0)
        if st.button("Save"):
            new_r = {"Outlet": selected_outlet, "Item": n, "Qty": q, "Unit": "Units", "Total_Cost": p}
            st.session_state.db["inventory"] = pd.concat([db["inventory"], pd.DataFrame([new_r])], ignore_index=True)
    st.dataframe(db["inventory"][db["inventory"]["Outlet"] == selected_outlet])

elif menu == "Recipe Master":
    st.title("👨‍🍳 Master Recipes")
    dish_n = st.text_input("New Dish Name")
    items = db["inventory"]["Item"].unique()
    if len(items) > 0:
        sel = st.multiselect("Ingredients", items)
        if st.button("Save Recipe"):
            db["recipes"][dish_n] = {i: 1.0 for i in sel}
            st.success("Dish Created!")
