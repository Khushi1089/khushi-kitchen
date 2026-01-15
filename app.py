import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- APP CONFIG ---
st.set_page_config(page_title="Cloud K - Global ERP", page_icon="☁️", layout="wide")

# --- DATABASE INITIALIZATION ---
if 'db' not in st.session_state:
    st.session_state.db = {
        "outlets": ["The Home Plate", "No Cap Burgers", "Hello Momos"],
        "inventory": pd.DataFrame(columns=["Outlet", "Item", "Qty", "Unit", "Total_Cost", "Weight_Per_Piece"]),
        "recipes": {}, 
        "menu_prices": {}, 
        # Matrix: { "OutletName": {"Platform": Commission%} }
        "outlet_platforms": {
            "The Home Plate": {"Zomato": 25.0, "Swiggy": 25.0, "Direct": 0.0},
            "Hello Momos": {"Direct": 0.0}
        },
        "sales": pd.DataFrame(columns=["Date", "Outlet", "Dish", "Platform", "Base_Price", "Commission", "Tax", "Delivery", "Net_Profit"])
    }

db = st.session_state.db

# --- SIDEBAR ---
st.sidebar.title("☁️ Cloud K Command")
menu = st.sidebar.radio("Navigate", ["Dashboard", "Menu & Pricing", "Sale Entry", "Stock Room", "Recipe Master", "Outlet & Platforms", "Unit Converter"])

# --- 1. OUTLET & PLATFORM MANAGER ---
if menu == "Outlet & Platforms":
    st.title("🏢 Multi-Outlet & Platform Manager")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Add New Outlet")
        new_out = st.text_input("Outlet Name")
        if st.button("Register Outlet"):
            if new_out and new_out not in db["outlets"]:
                db["outlets"].append(new_out)
                db["outlet_platforms"][new_out] = {"Direct": 0.0}
                st.success(f"{new_out} added!")
                st.rerun()
    
    with col2:
        st.subheader("Manage Platforms for Outlet")
        target_out = st.selectbox("Select Outlet", db["outlets"])
        p_name = st.text_input("Platform Name (e.g., Zomato)")
        p_comm = st.number_input("Commission %", min_value=0.0, max_value=100.0)
        
        if st.button(f"Link {p_name} to {target_out}"):
            if target_out not in db["outlet_platforms"]:
                db["outlet_platforms"][target_out] = {}
            db["outlet_platforms"][target_out][p_name] = p_comm
            st.success(f"Linked {p_name} to {target_out} at {p_comm}%")

    st.write("### Current Outlet Setup")
    st.json(db["outlet_platforms"])

# --- SELECT ACTIVE OUTLET ---
if menu not in ["Outlet & Platforms", "Unit Converter"]:
    selected_outlet = st.sidebar.selectbox("Active Outlet", db["outlets"])
    outlet_inv = db["inventory"][db["inventory"]["Outlet"] == selected_outlet]

# --- 2. MENU & PRICING ---
elif menu == "Menu & Pricing":
    st.title("💰 Menu Pricing Master")
    all_dishes = list(db["recipes"].keys())
    if not all_dishes:
        st.warning("Please create recipes first in the Recipe Master!")
    else:
        for dish in all_dishes:
            current_p = db["menu_prices"].get(dish, 0.0)
            new_p = st.number_input(f"Standard Price for {dish} (₹)", value=float(current_p), key=dish)
            db["menu_prices"][dish] = new_p
        st.success("Menu Prices Saved!")

# --- 3. SALE ENTRY ---
elif menu == "Sale Entry":
    st.title(f"🎯 Sale Entry: {selected_outlet}")
    # Load platforms only for the selected outlet
    platforms_available = list(db["outlet_platforms"].get(selected_outlet, {"Direct": 0.0}).keys())
    
    if not db["menu_prices"]: st.error("Set Menu Prices first!")
    else:
        c1, c2 = st.columns(2)
        dish = c1.selectbox("Product", list(db["menu_prices"].keys()))
        platform = c2.selectbox("Order Source", platforms_available)
        
        col1, col2, col3 = st.columns(3)
        base_price = col1.number_input("Base Dish Price", value=db["menu_prices"][dish])
        tax_val = col2.number_input("GST/Tax (₹)", min_value=0.0)
        del_charge = col3.number_input("Delivery Fee (₹)", min_value=0.0)
        
        comm_pct = db["outlet_platforms"][selected_outlet].get(platform, 0.0)
        comm_amt = (base_price * comm_pct) / 100
        
        st.info(f"**Financial Breakdown:** {platform} Commission (₹{comm_amt}) | Customer Pays (₹{base_price + tax_val + del_charge})")

        if st.button("Record Sale"):
            # Deducting Stock
            recipe = db["recipes"].get(dish, {})
            cost = 0
            for item, req in recipe.items():
                row = outlet_inv[outlet_inv["Item"] == item]
                if not row.empty:
                    u_cost = row["Total_Cost"].values[0] / max(1, row["Qty"].values[0])
                    cost += (u_cost * req)
                    st.session_state.db["inventory"].loc[(db["inventory"]["Outlet"]==selected_outlet)&(db["inventory"]["Item"]==item), "Qty"] -= req
            
            # Profit = Base Price - Platform Fee - Ingredients
            net_p = base_price - comm_amt - cost
            
            new_s = pd.DataFrame([{
                "Date": datetime.now(), "Outlet": selected_outlet, "Dish": dish, 
                "Platform": platform, "Base_Price": base_price, 
                "Commission": comm_amt, "Tax": tax_val, "Delivery": del_charge, "Net_Profit": net_p
            }])
            st.session_state.db["sales"] = pd.concat([db["sales"], new_s], ignore_index=True)
            st.balloons()
            st.success("Sale Recorded Successfully!")

# --- 4. DASHBOARD (Fixed ValueError) ---
elif menu == "Dashboard":
    st.title(f"📊 {selected_outlet} Dashboard")
    df = db["sales"][db["sales"]["Outlet"] == selected_outlet].copy()
    
    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])
        view = st.radio("Time View", ["Daily", "Monthly"], horizontal=True)
        df['DisplayDate'] = df['Date'].dt.date if view == "Daily" else df['Date'].dt.strftime('%b %Y')

        stats = df.groupby('DisplayDate').agg({'Base_Price':'sum', 'Net_Profit':'sum'}).reset_index()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Gross Sales", f"₹{df['Base_Price'].sum()}")
        m2.metric("Net Profit", f"₹{round(df['Net_Profit'].sum(), 2)}")
        m3.metric("Tax Tracked", f"₹{df['Tax'].sum()}")

        # Fixed chart logic to prevent empty data errors
        if not stats.empty:
            fig = px.bar(stats, x='DisplayDate', y=['Base_Price', 'Net_Profit'], 
                         barmode='group', title="Revenue vs Real Profit")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Start logging sales to see your growth analytics!")

# (Stock Room, Recipe Master, and Unit Converter logic continues below...)
elif menu == "Stock Room":
    st.title(f"📦 {selected_outlet} Stock")
    with st.expander("Add Raw Material"):
        c1, c2, c3, c4 = st.columns(4)
        name = c1.text_input("Item Name")
        qty = c2.number_input("Quantity", min_value=0.0)
        unit = c3.selectbox("Unit", ["Pieces", "Kg", "Liters"])
        price = c4.number_input("Purchase Price (₹)", min_value=0.0)
        if st.button("Add to Stock"):
            new_row = {"Outlet": selected_outlet, "Item": name, "Qty": qty, "Unit": unit, "Total_Cost": price, "Weight_Per_Piece": 0}
            st.session_state.db["inventory"] = pd.concat([db["inventory"], pd.DataFrame([new_row])], ignore_index=True)
            st.success("Stock updated!")
    st.dataframe(outlet_inv)

elif menu == "Recipe Master":
    st.title("👨‍🍳 Master Recipe Book")
    dish = st.text_input("Dish Name (e.g. Paneer Pizza)")
    all_items = db["inventory"]["Item"].unique()
    if len(all_items) > 0:
        ingredients = st.multiselect("Select Ingredients", all_items)
        recipe_map = {}
        if ingredients:
            cols = st.columns(len(ingredients))
            for i, item in enumerate(ingredients):
                recipe_map[item] = cols[i].number_input(f"Amt of {item}", min_value=0.001, format="%.3f")
            if st.button("Link Recipe"):
                st.session_state.db["recipes"][dish] = recipe_map
                st.success("Recipe and Stock Deduction linked!")
