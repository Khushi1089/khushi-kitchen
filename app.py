import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- APP CONFIG ---
st.set_page_config(page_title="Cloud K - Global ERP", page_icon="☁️", layout="wide")

# --- DATABASE INITIALIZATION ---
if 'db' not in st.session_state:
    st.session_state.db = {
        "outlets": ["The Home Plate", "No Cap Burgers", "Pocket Pizzaz", "Witx Sandwitx", "Hello Momos", "Khushi Breakfast Club", "Bihar ka Swad"],
        "inventory": pd.DataFrame(columns=["Outlet", "Item", "Qty", "Unit", "Total_Cost", "Weight_Per_Piece"]),
        "recipes": {}, 
        "menu_prices": {}, # Format: {"Dish": 250.0}
        "platforms": ["Zomato", "Swiggy", "MagicPin", "Direct Sale"],
        "commissions": {"Zomato": 25.0, "Swiggy": 25.0, "MagicPin": 15.0, "Direct Sale": 0.0},
        "sales": pd.DataFrame(columns=["Date", "Outlet", "Dish", "Platform", "Gross_Revenue", "Commission", "Tax", "Delivery", "Net_Profit"])
    }

db = st.session_state.db

# --- SIDEBAR ---
st.sidebar.title("☁️ Cloud K Command")
menu = st.sidebar.radio("Navigate", ["Dashboard", "Menu & Pricing", "Sale Entry", "Stock Room", "Recipe Master", "Outlet & Platforms", "Unit Converter"])

# --- 1. OUTLET & PLATFORMS (Add/Remove) ---
if menu == "Outlet & Platforms":
    st.title("🏢 Settings")
    c1, c2 = st.columns(2)
    with c1:
        new_out = st.text_input("New Outlet Name")
        if st.button("Add Outlet"):
            if new_out and new_out not in db["outlets"]: db["outlets"].append(new_out); st.rerun()
    with c2:
        p_name = st.text_input("Platform Name (e.g., UberEats)")
        p_comm = st.number_input("Commission %", min_value=0.0)
        if st.button("Add Platform"):
            db["platforms"].append(p_name)
            db["commissions"][p_name] = p_comm; st.rerun()

# --- SELECT ACTIVE OUTLET ---
if menu not in ["Outlet & Platforms", "Unit Converter"]:
    selected_outlet = st.sidebar.selectbox("Active Outlet", db["outlets"])
    outlet_inv = db["inventory"][db["inventory"]["Outlet"] == selected_outlet]

# --- 2. MENU & PRICING (New Request) ---
elif menu == "Menu & Pricing":
    st.title("💰 Menu Pricing Master")
    st.write("Set your standard selling prices here.")
    all_dishes = list(db["recipes"].keys())
    if not all_dishes:
        st.warning("Please create recipes first!")
    else:
        for dish in all_dishes:
            current_p = db["menu_prices"].get(dish, 0.0)
            new_p = st.number_input(f"Selling Price for {dish} (₹)", value=float(current_p), key=dish)
            db["menu_prices"][dish] = new_p
        st.success("Prices updated!")

# --- 3. SALE ENTRY (Upgraded with Commission/Tax/Delivery) ---
elif menu == "Sale Entry":
    st.title(f"🎯 Sale Entry: {selected_outlet}")
    if not db["menu_prices"]: st.error("Set Menu Prices first!")
    else:
        dish = st.selectbox("Product", list(db["menu_prices"].keys()))
        platform = st.selectbox("Sold Via", db["platforms"])
        
        col1, col2, col3 = st.columns(3)
        base_price = col1.number_input("Base Price", value=db["menu_prices"][dish])
        tax_val = col2.number_input("Tax (₹)", min_value=0.0)
        del_charge = col3.number_input("Delivery Charge (₹)", min_value=0.0)
        
        comm_pct = db["commissions"].get(platform, 0.0)
        comm_amt = (base_price * comm_pct) / 100
        total_customer_pays = base_price + tax_val + del_charge
        
        st.info(f"Platform Commission ({comm_pct}%): ₹{comm_amt}")

        if st.button("Confirm Sale"):
            # Deduct Stock logic
            recipe = db["recipes"].get(dish, {})
            cost = 0
            for item, req in recipe.items():
                row = outlet_inv[outlet_inv["Item"] == item]
                if not row.empty:
                    u_cost = row["Total_Cost"].values[0] / max(1, row["Qty"].values[0])
                    cost += (u_cost * req)
                    st.session_state.db["inventory"].loc[(db["inventory"]["Outlet"]==selected_outlet)&(db["inventory"]["Item"]==item), "Qty"] -= req
            
            # Net Profit = (Base Price - Commission - Ingredient Cost)
            net_p = base_price - comm_amt - cost
            
            new_s = pd.DataFrame([{
                "Date": datetime.now(), "Outlet": selected_outlet, "Dish": dish, 
                "Platform": platform, "Gross_Revenue": total_customer_pays, 
                "Commission": comm_amt, "Tax": tax_val, "Delivery": del_charge, "Net_Profit": net_p
            }])
            st.session_state.db["sales"] = pd.concat([db["sales"], new_s], ignore_index=True)
            st.balloons()

# --- 4. DASHBOARD (Fixed ValueError) ---
elif menu == "Dashboard":
    st.title(f"📊 {selected_outlet} Analytics")
    df = db["sales"][db["sales"]["Outlet"] == selected_outlet].copy()
    
    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])
        view = st.radio("Group By", ["Daily", "Monthly"], horizontal=True)
        df['DisplayDate'] = df['Date'].dt.date if view == "Daily" else df['Date'].dt.strftime('%b %Y')

        stats = df.groupby('DisplayDate').agg({'Gross_Revenue':'sum', 'Net_Profit':'sum'}).reset_index()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Gross Revenue", f"₹{df['Gross_Revenue'].sum()}")
        m2.metric("Total Commissions Paid", f"₹{df['Commission'].sum()}")
        m3.metric("Net Profit", f"₹{round(df['Net_Profit'].sum(), 2)}")

        # Fixed Chart Logic
        fig = px.bar(stats, x='DisplayDate', y=['Gross_Revenue', 'Net_Profit'], barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data yet.")

# (Remaining sections for Stock Room, Recipe, Unit Converter stay the same as previous version)
elif menu == "Stock Room":
    st.title(f"📦 {selected_outlet} Inventory")
    with st.expander("➕ Add Stock"):
        c1, c2, c3, c4 = st.columns(4)
        name = c1.text_input("Item Name")
        qty = c2.number_input("Qty", min_value=0.0)
        unit = c3.selectbox("Unit", ["Pieces", "Kg", "Liters"])
        price = c4.number_input("Total Cost", min_value=0.0)
        if st.button("Save"):
            new_row = {"Outlet": selected_outlet, "Item": name, "Qty": qty, "Unit": unit, "Total_Cost": price, "Weight_Per_Piece": 0}
            st.session_state.db["inventory"] = pd.concat([db["inventory"], pd.DataFrame([new_row])], ignore_index=True)
    st.dataframe(outlet_inv)

elif menu == "Recipe Master":
    st.title("👨‍🍳 Recipe Master")
    dish = st.text_input("New Dish Name")
    all_items = db["inventory"]["Item"].unique()
    if len(all_items) > 0:
        ingredients = st.multiselect("Select Items", all_items)
        recipe_map = {}
        if ingredients:
            cols = st.columns(len(ingredients))
            for i, item in enumerate(ingredients):
                recipe_map[item] = cols[i].number_input(f"Qty {item}", min_value=0.001, format="%.3f")
            if st.button("Save Recipe"):
                st.session_state.db["recipes"][dish] = recipe_map
                st.success("Recipe Linked!")

elif menu == "Unit Converter":
    st.title("⚖️ Unit Converter")
    val = st.number_input("Enter Quantity", min_value=0.0)
    w_one = st.number_input("Grams per Piece", min_value=0.0)
    if w_one > 0:
        st.write(f"Total Weight: {(val * w_one)/1000} Kg")
