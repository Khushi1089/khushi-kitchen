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

# --- SIDEBAR ---
st.sidebar.title("☁️ Cloud K Command")
menu = st.sidebar.radio("Navigate", [
    "Dashboard", "Sale Entry", "Misc Expenses", "Menu & Pricing", 
    "Stock Room", "Recipe Master", "Outlet & Platforms"
])

# --- ACTIVE OUTLET ---
selected_outlet = st.sidebar.selectbox("Active Outlet", db["outlets"])
outlet_inv = db["inventory"][db["inventory"]["Outlet"] == selected_outlet]

# --- 1. SALE ENTRY (FIXED FOR VISIBILITY) ---
if menu == "Sale Entry":
    st.title(f"🎯 New Sale: {selected_outlet}")
    
    # Check if we have platforms and prices
    platforms = list(db["outlet_platforms"].get(selected_outlet, {"Direct": 0.0}).keys())
    dishes = list(db["menu_prices"].keys())

    if not dishes:
        st.error("⚠️ No Dishes Found!")
        st.info("To make an entry, you must first: 1. Add Stock -> 2. Create a Recipe -> 3. Set a Price.")
        if st.button("Go to Recipe Master"):
            st.session_state.menu = "Recipe Master" # Attempt to redirect
    else:
        with st.form("sale_form"):
            c1, c2 = st.columns(2)
            dish = c1.selectbox("Select Product", dishes)
            platform = c2.selectbox("Sold Via", platforms)
            
            col1, col2, col3 = st.columns(3)
            base_p = col1.number_input("Selling Price (₹)", value=float(db["menu_prices"].get(dish, 0)))
            tax = col2.number_input("GST/Tax (₹)", min_value=0.0)
            deliv = col3.number_input("Delivery Fee (₹)", min_value=0.0)
            
            submitted = st.form_submit_button("Confirm & Log Sale")
            
            if submitted:
                comm_pct = db["outlet_platforms"][selected_outlet].get(platform, 0.0)
                comm_amt = (base_p * comm_pct) / 100
                
                # Logic to deduct stock...
                new_s = pd.DataFrame([{
                    "Date": datetime.now(), "Outlet": selected_outlet, "Dish": dish, "Platform": platform, 
                    "Base_Price": base_p, "Commission": comm_amt, "Tax": tax, "Delivery": deliv, "Net_Profit": base_p - comm_amt
                }])
                st.session_state.db["sales"] = pd.concat([db["sales"], new_s], ignore_index=True)
                st.success(f"Sale recorded for {dish} via {platform}!")
                st.balloons()

# --- 2. MISC EXPENSES ---
elif menu == "Misc Expenses":
    st.title(f"💸 Expenses: {selected_outlet}")
    with st.form("exp_form"):
        cat = st.selectbox("Category", ["Rent", "Salary", "Electricity", "Packaging", "Marketing", "Other"])
        amt = st.number_input("Amount (₹)", min_value=0.0)
        note = st.text_input("Notes")
        if st.form_submit_button("Save Expense"):
            new_e = pd.DataFrame([{"Date": datetime.now(), "Outlet": selected_outlet, "Category": cat, "Amount": amt, "Notes": note}])
            st.session_state.db["expenses"] = pd.concat([db["expenses"], new_e], ignore_index=True)
            st.success("Expense Recorded!")

# --- 3. DASHBOARD & DOWNLOAD ---
elif menu == "Dashboard":
    st.title(f"📊 {selected_outlet} Overview")
    s_df = db["sales"][db["sales"]["Outlet"] == selected_outlet]
    e_df = db["expenses"][db["expenses"]["Outlet"] == selected_outlet]
    
    m1, m2, m3 = st.columns(3)
    rev = s_df["Base_Price"].sum() if not s_df.empty else 0
    exps = e_df["Amount"].sum() if not e_df.empty else 0
    m1.metric("Revenue", f"₹{rev}")
    m2.metric("Expenses", f"₹{exps}")
    m3.metric("Profit", f"₹{round(rev - exps, 2)}")

    if not s_df.empty:
        # Excel Download
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            s_df.to_excel(writer, sheet_name='Sales')
            e_df.to_excel(writer, sheet_name='Expenses')
        st.download_button("📥 Download Monthly Report", buffer, f"{selected_outlet}_Report.xlsx")

# --- OTHER MENUS (Same logic as before) ---
elif menu == "Menu & Pricing":
    st.title("💰 Set Menu Prices")
    for dish in db["recipes"].keys():
        db["menu_prices"][dish] = st.number_input(f"Price for {dish}", value=float(db["menu_prices"].get(dish, 0.0)))

elif menu == "Stock Room":
    st.title("📦 Inventory")
    with st.expander("Add New Item"):
        n = st.text_input("Item Name")
        q = st.number_input("Qty", min_value=0.0)
        p = st.number_input("Cost", min_value=0.0)
        if st.button("Add"):
            new_r = {"Outlet": selected_outlet, "Item": n, "Qty": q, "Total_Cost": p}
            st.session_state.db["inventory"] = pd.concat([db["inventory"], pd.DataFrame([new_r])], ignore_index=True)

elif menu == "Recipe Master":
    st.title("👨‍🍳 Recipe Master")
    d_name = st.text_input("Dish Name")
    items = db["inventory"]["Item"].unique()
    sel = st.multiselect("Select Ingredients", items)
    if st.button("Save Recipe"):
        db["recipes"][d_name] = {i: 1.0 for i in sel}
        st.success(f"Recipe for {d_name} saved!")

elif menu == "Outlet & Platforms":
    st.title("🏢 Management")
    st.write("Manage your Outlets and their specific Platform Commission rates here.")
