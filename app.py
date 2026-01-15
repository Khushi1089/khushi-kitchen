import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io

# --- APP CONFIG ---
st.set_page_config(page_title="Cloud K - Global Analytics", page_icon="☁️", layout="wide")

# --- DATA PERSISTENCE ---
if 'db' not in st.session_state:
    st.session_state.db = {
        "outlets": ["The Home Plate", "No Cap Burgers", "Pocket Pizzaz", "Witx Sandwitx", "Hello Momos", "Khushi Breakfast Club", "Bihar ka Swad"],
        "inventory": pd.DataFrame(columns=["Outlet", "Item", "Qty", "Unit", "Total_Cost"]),
        "recipes": {}, 
        "menu_prices": {}, 
        "outlet_configs": {
            "The Home Plate": {"Platforms": {"Direct": {"comm": 0.0, "del": 0.0}}}
        },
        "sales": pd.DataFrame(columns=["Date", "Outlet", "Dish", "Platform", "Revenue", "Comm_Paid", "Del_Cost", "Ing_Cost", "Net_Profit"]),
        "expenses": pd.DataFrame(columns=["Date", "Outlet", "Category", "Amount", "Notes"])
    }

db = st.session_state.db

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("☁️ Cloud K Master")
menu = st.sidebar.radio("Navigation", [
    "Dashboard & Analytics", "Sale Entry", "Misc Expenses", 
    "Menu & Pricing", "Stock Room", "Recipe Master", "Outlet & Platform Settings"
])

# --- 1. SETTINGS: OUTLETS & PLATFORMS ---
if menu == "Outlet & Platform Settings":
    st.title("🏢 Outlet & Platform Management")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Manage Outlets")
        new_out = st.text_input("New Outlet Name")
        if st.button("Add Outlet"):
            if new_out and new_out not in db["outlets"]:
                db["outlets"].append(new_out)
                db["outlet_configs"][new_out] = {"Platforms": {"Direct": {"comm": 0.0, "del": 0.0}}}
                st.rerun()
        
        rem_out = st.selectbox("Remove Outlet", db["outlets"])
        if st.button("Delete Outlet"):
            db["outlets"].remove(rem_out)
            st.rerun()

    with c2:
        st.subheader("Platform Config per Outlet")
        target_out = st.selectbox("Select Outlet", db["outlets"])
        p_name = st.text_input("Platform Name (e.g., Zomato)")
        p_comm = st.number_input("Commission %", min_value=0.0)
        p_del = st.number_input("Platform Delivery Charge (₹)", min_value=0.0)
        
        if st.button(f"Link Platform to {target_out}"):
            if target_out not in db["outlet_configs"]: db["outlet_configs"][target_out] = {"Platforms": {}}
            db["outlet_configs"][target_out]["Platforms"][p_name] = {"comm": p_comm, "del": p_del}
            st.success(f"Linked {p_name} to {target_out}")

# --- ACTIVE OUTLET ---
selected_outlet = st.sidebar.selectbox("Active Outlet", db["outlets"])

# --- 2. STOCK ROOM ---
if menu == "Stock Room":
    st.title(f"📦 Inventory: {selected_outlet}")
    with st.form("stock"):
        c1, c2, c3, c4 = st.columns(4)
        item = c1.text_input("Item Name")
        qty = c2.number_input("Quantity")
        unit = c3.selectbox("Unit", ["Grams", "Pieces", "Kg", "Liters"])
        cost = c4.number_input("Total Purchase Cost (₹)")
        if st.form_submit_button("Update Inventory"):
            new_row = {"Outlet": selected_outlet, "Item": item, "Qty": qty, "Unit": unit, "Total_Cost": cost}
            st.session_state.db["inventory"] = pd.concat([db["inventory"], pd.DataFrame([new_row])], ignore_index=True)
    st.dataframe(db["inventory"][db["inventory"]["Outlet"] == selected_outlet])

# --- 3. RECIPE MASTER ---
elif menu == "Recipe Master":
    st.title("👨‍🍳 Recipe & Per-Dish Units")
    dish_name = st.text_input("Dish Name")
    items = db["inventory"]["Item"].unique()
    if len(items) > 0:
        sel_items = st.multiselect("Select Ingredients", items)
        recipe_data = {}
        for i in sel_items:
            u = db["inventory"][db["inventory"]["Item"] == i]["Unit"].values[0]
            recipe_data[i] = st.number_input(f"{i} used ({u})", min_value=0.0, format="%.2f")
        if st.button("Save Recipe"):
            db["recipes"][dish_name] = recipe_data
            st.success("Recipe Linked!")

# --- 4. MENU & PRICING ---
elif menu == "Menu & Pricing":
    st.title("💰 Menu Pricing")
    for dish in db["recipes"].keys():
        db["menu_prices"][dish] = st.number_input(f"Price for {dish}", value=float(db["menu_prices"].get(dish, 0.0)))

# --- 5. SALE ENTRY ---
elif menu == "Sale Entry":
    st.title(f"🎯 Sale: {selected_outlet}")
    config = db["outlet_configs"].get(selected_outlet, {"Platforms": {"Direct": {"comm": 0.0, "del": 0.0}}})
    platforms = list(config["Platforms"].keys())
    
    dish = st.selectbox("Product", list(db["menu_prices"].keys()))
    plat = st.selectbox("Platform", platforms)
    
    price = st.number_input("Base Price", value=db["menu_prices"].get(dish, 0.0))
    
    if st.button("Confirm Sale"):
        # Calc Costs
        ing_cost = 0
        recipe = db["recipes"].get(dish, {})
        for item, amt in recipe.items():
            match = db["inventory"][(db["inventory"]["Item"]==item) & (db["inventory"]["Outlet"]==selected_outlet)]
            if not match.empty:
                ing_cost += (match["Total_Cost"].values[0] / match["Qty"].values[0]) * amt
        
        plat_data = config["Platforms"][plat]
        comm_amt = (price * plat_data['comm']) / 100
        del_fee = plat_data['del']
        net_prof = price - comm_amt - del_fee - ing_cost
        
        new_sale = pd.DataFrame([{
            "Date": datetime.now(), "Outlet": selected_outlet, "Dish": dish, "Platform": plat,
            "Revenue": price, "Comm_Paid": comm_amt, "Del_Cost": del_fee, "Ing_Cost": ing_cost, "Net_Profit": net_prof
        }])
        st.session_state.db["sales"] = pd.concat([db["sales"], new_sale], ignore_index=True)
        st.balloons()

# --- 6. MISC EXPENSES ---
elif menu == "Misc Expenses":
    st.title(f"💸 Expenses: {selected_outlet}")
    with st.form("exp"):
        cat = st.selectbox("Category", ["Rent", "Salary", "Electricity", "Other"])
        amt = st.number_input("Amount")
        if st.form_submit_button("Log Expense"):
            new_exp = pd.DataFrame([{"Date": datetime.now(), "Outlet": selected_outlet, "Category": cat, "Amount": amt}])
            st.session_state.db["expenses"] = pd.concat([db["expenses"], new_exp], ignore_index=True)

# --- 7. DASHBOARD & ANALYTICS ---
elif menu == "Dashboard & Analytics":
    st.title(f"📊 {selected_outlet} Financial Engine")
    
    view = st.radio("Analytics Period", ["Monthly", "Yearly"], horizontal=True)
    s_df = db["sales"][db["sales"]["Outlet"] == selected_outlet].copy()
    e_df = db["expenses"][db["expenses"]["Outlet"] == selected_outlet].copy()
    
    if not s_df.empty:
        s_df['Date'] = pd.to_datetime(s_df['Date'])
        format_str = '%Y-%m' if view == "Monthly" else '%Y'
        s_df['Period'] = s_df['Date'].dt.strftime(format_str)
        
        stats = s_df.groupby('Period').agg({
            'Revenue': 'sum', 'Comm_Paid': 'sum', 'Del_Cost': 'sum', 'Ing_Cost': 'sum', 'Net_Profit': 'sum'
        }).reset_index()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Revenue", f"₹{stats['Revenue'].sum()}")
        m2.metric("Total Profit", f"₹{round(stats['Net_Profit'].sum() - e_df['Amount'].sum(), 2)}")
        m3.metric("Platform Fees", f"₹{stats['Comm_Paid'].sum() + stats['Del_Cost'].sum()}")
        m4.metric("Expenses", f"₹{e_df['Amount'].sum()}")

        st.plotly_chart(px.bar(stats, x='Period', y=['Revenue', 'Net_Profit'], barmode='group', title=f"{view} Sales vs Profit"))
        
        # EXCEL DOWNLOAD
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            s_df.to_excel(writer, sheet_name='Sales')
            e_df.to_excel(writer, sheet_name='Expenses')
        st.download_button("📥 Export Yearly Report", buf, f"{selected_outlet}_Report.xlsx")
    else:
        st.info("Log your first sale to see analytics!")
