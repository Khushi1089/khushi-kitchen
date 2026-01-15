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
        "outlets": ["The Home Plate", "No Cap Burgers", "Hello Momos"],
        "inventory": pd.DataFrame(columns=["Outlet", "Item", "Qty", "Unit", "Total_Cost"]),
        "recipes": {}, 
        "menu_prices": {}, 
        "outlet_platforms": {
            "The Home Plate": {"Zomato": 25.0, "Swiggy": 25.0, "Direct": 0.0}
        },
        "sales": pd.DataFrame(columns=["Date", "Outlet", "Dish", "Platform", "Base_Price", "Commission", "Tax", "Delivery", "Net_Profit"]),
        "expenses": pd.DataFrame(columns=["Date", "Outlet", "Category", "Amount", "Notes"])
    }

db = st.session_state.db

# --- SIDEBAR ---
st.sidebar.title("☁️ Cloud K Command")
menu = st.sidebar.radio("Navigate", [
    "Dashboard", "Sale Entry", "Misc Expenses", "Menu & Pricing", 
    "Stock Room", "Recipe Master", "Outlet & Platform Settings"
])

selected_outlet = st.sidebar.selectbox("Active Outlet", db["outlets"])

# --- 1. OUTLET & PLATFORM SETTINGS ---
if menu == "Outlet & Platform Settings":
    st.title("🏢 Management Control")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Manage Outlets")
        new_out = st.text_input("New Outlet Name")
        if st.button("Add Outlet"):
            if new_out and new_out not in db["outlets"]:
                db["outlets"].append(new_out)
                db["outlet_platforms"][new_out] = {"Direct": 0.0}
                st.success(f"{new_out} added!")
                st.rerun()
        
        rem_out = st.selectbox("Remove Outlet", db["outlets"])
        if st.button("Delete Outlet"):
            db["outlets"].remove(rem_out)
            st.warning(f"{rem_out} removed.")
            st.rerun()

    with col2:
        st.subheader("Manage Platforms & Commissions")
        p_name = st.text_input("Platform Name (e.g., MagicPin)")
        p_comm = st.number_input("Commission %", min_value=0.0, max_value=100.0)
        if st.button(f"Add Platform to {selected_outlet}"):
            if selected_outlet not in db["outlet_platforms"]:
                db["outlet_platforms"][selected_outlet] = {}
            db["outlet_platforms"][selected_outlet][p_name] = p_comm
            st.success(f"Linked {p_name} at {p_comm}%")

# --- 2. STOCK ROOM (GRAMS & PIECES) ---
elif menu == "Stock Room":
    st.title(f"📦 Inventory: {selected_outlet}")
    with st.form("add_stock"):
        c1, c2, c3, c4 = st.columns(4)
        item = c1.text_input("Item (e.g., Flour, Patty)")
        qty = c2.number_input("Quantity", min_value=0.0)
        unit = c3.selectbox("Unit", ["Grams", "Pieces", "ML", "Kg"])
        cost = c4.number_input("Total Purchase Cost (₹)", min_value=0.0)
        if st.form_submit_button("Update Stock"):
            new_row = {"Outlet": selected_outlet, "Item": item, "Qty": qty, "Unit": unit, "Total_Cost": cost}
            st.session_state.db["inventory"] = pd.concat([db["inventory"], pd.DataFrame([new_row])], ignore_index=True)

    st.dataframe(db["inventory"][db["inventory"]["Outlet"] == selected_outlet])

# --- 3. RECIPE MASTER (PER DISH UNITS) ---
elif menu == "Recipe Master":
    st.title("👨‍🍳 Recipe & Costing")
    dish_name = st.text_input("Dish Name (e.g., Classic Burger)")
    
    available_items = db["inventory"]["Item"].unique()
    if len(available_items) == 0:
        st.error("Add items to Stock Room first!")
    else:
        selected_ingredients = st.multiselect("Select Ingredients", available_items)
        recipe_data = {}
        for ing in selected_ingredients:
            unit_type = db["inventory"][db["inventory"]["Item"] == ing]["Unit"].values[0]
            amt = st.number_input(f"Amount of {ing} (in {unit_type}) used per dish", min_value=0.0, format="%.2f")
            recipe_data[ing] = amt
        
        if st.button("Save Recipe"):
            db["recipes"][dish_name] = recipe_data
            st.success(f"Recipe for {dish_name} saved!")

# --- 4. MENU & PRICING ---
elif menu == "Menu & Pricing":
    st.title("💰 Menu Pricing")
    if not db["recipes"]:
        st.info("Create a recipe first!")
    else:
        for dish in db["recipes"].keys():
            db["menu_prices"][dish] = st.number_input(f"Selling Price for {dish} (₹)", value=float(db["menu_prices"].get(dish, 0.0)))
        st.success("Prices Updated!")

# --- 5. SALE ENTRY (CALCULATED PROFIT) ---
elif menu == "Sale Entry":
    st.title(f"🎯 Sale: {selected_outlet}")
    
    if not db["menu_prices"]:
        st.error("Setup Recipes and Prices first!")
    else:
        dish = st.selectbox("Product", list(db["menu_prices"].keys()))
        platform = st.selectbox("Platform", list(db["outlet_platforms"].get(selected_outlet, {"Direct":0}).keys()))
        
        c1, c2, c3 = st.columns(3)
        price = c1.number_input("Price", value=db["menu_prices"][dish])
        tax = c2.number_input("Tax (₹)", min_value=0.0)
        deliv = c3.number_input("Delivery Charge (₹)", min_value=0.0)
        
        if st.button("Log Sale"):
            # Calculate ingredient cost
            ing_cost = 0
            recipe = db["recipes"][dish]
            for item, amt in recipe.items():
                inv_match = db["inventory"][(db["inventory"]["Item"]==item) & (db["inventory"]["Outlet"]==selected_outlet)]
                if not inv_match.empty:
                    # Cost per unit = Total Cost / Total Qty
                    unit_cost = inv_match["Total_Cost"].values[0] / inv_match["Qty"].values[0]
                    ing_cost += (unit_cost * amt)
            
            comm_amt = (price * db["outlet_platforms"][selected_outlet].get(platform, 0)) / 100
            net_prof = price - comm_amt - ing_cost - deliv
            
            new_s = pd.DataFrame([{
                "Date": datetime.now(), "Outlet": selected_outlet, "Dish": dish, "Platform": platform,
                "Base_Price": price, "Commission": comm_amt, "Tax": tax, "Delivery": deliv, "Net_Profit": net_prof
            }])
            st.session_state.db["sales"] = pd.concat([db["sales"], new_s], ignore_index=True)
            st.success(f"Profit of ₹{round(net_prof, 2)} recorded!")

# --- 6. DASHBOARD ---
elif menu == "Dashboard":
    st.title(f"📊 {selected_outlet} Dashboard")
    s_df = db["sales"][db["sales"]["Outlet"] == selected_outlet]
    
    m1, m2 = st.columns(2)
    m1.metric("Gross Sales", f"₹{s_df['Base_Price'].sum()}")
    m2.metric("Net Profit", f"₹{round(s_df['Net_Profit'].sum(), 2)}")
    
    if not s_df.empty:
        fig = px.pie(s_df, values='Net_Profit', names='Platform', title="Profit by Platform")
        st.plotly_chart(fig)
