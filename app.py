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

# --- 1. STOCK ROOM (With Delete & Low Stock Alerts) ---
if menu == "Stock Room":
    st.title(f"📦 Inventory Management: {selected_outlet}")
    
    with st.expander("➕ Add New Inventory Item"):
        with st.form("add_stock_form"):
            c1, c2, c3, c4 = st.columns(4)
            item_name = c1.text_input("Ingredient Name")
            qty = c2.number_input("Quantity", min_value=0.0)
            unit = c3.selectbox("Unit", ["Grams", "Kg", "Pieces", "Liters", "ML"])
            cost = c4.number_input("Total Purchase Cost (₹)", min_value=0.0)
            if st.form_submit_button("Add to Stock"):
                new_id = len(db["inventory"]) + 1
                new_row = pd.DataFrame([{"id": new_id, "Outlet": selected_outlet, "Item": item_name, "Qty": qty, "Unit": unit, "Total_Cost": cost}])
                st.session_state.db["inventory"] = pd.concat([db["inventory"], new_row], ignore_index=True)
                st.rerun()

    st.subheader("Current Stock")
    curr_inv = db["inventory"][db["inventory"]["Outlet"] == selected_outlet]
    
    if not curr_inv.empty:
        # Define Low Stock Thresholds (Example: < 500g or < 10 pieces)
        for idx, row in curr_inv.iterrows():
            is_low = (row['Unit'] in ['Grams', 'ML'] and row['Qty'] < 500) or \
                     (row['Unit'] in ['Pieces', 'Kg', 'Liters'] and row['Qty'] < 10)
            
            col_a, col_b, col_c = st.columns([3, 1, 1])
            
            # Highlight Logic
            label = f"**{row['Item']}**: {row['Qty']} {row['Unit']} (Cost: ₹{row['Total_Cost']})"
            if is_low:
                col_a.error(f"⚠️ LOW STOCK: {label}")
            else:
                col_a.write(label)
                
            if col_c.button("🗑️ Remove", key=f"del_{row['id']}"):
                st.session_state.db["inventory"] = db["inventory"].drop(idx)
                st.rerun()
    else:
        st.info("No items in stock.")

# --- 2. RECIPE MASTER ---
elif menu == "Recipe Master":
    st.title("👨‍🍳 Recipe Builder")
    available_items = db["inventory"][db["inventory"]["Outlet"] == selected_outlet]["Item"].unique()
    
    if len(available_items) == 0:
        st.warning("Please add items to the Stock Room first.")
    else:
        with st.form("recipe_form"):
            new_dish = st.text_input("Dish Name")
            selected_ings = st.multiselect("Select Ingredients", available_items)
            recipe_map = {}
            for ing in selected_ings:
                unit = db["inventory"][db["inventory"]["Item"] == ing]["Unit"].iloc[0]
                recipe_map[ing] = st.number_input(f"Amount of {ing} ({unit})", min_value=0.0, key=f"recipe_{ing}")
            
            if st.form_submit_button("Create Recipe"):
                if new_dish:
                    st.session_state.db["recipes"][new_dish] = recipe_map
                    st.success(f"Recipe for {new_dish} saved!")
                st.rerun()

# --- 3. MENU & PRICING ---
elif menu == "Menu & Pricing":
    st.title("💰 Menu Master")
    if not db["recipes"]:
        st.info("Create a Recipe first.")
    else:
        for dish in db["recipes"].keys():
            current_price = db["menu_prices"].get(dish, 0.0)
            db["menu_prices"][dish] = st.number_input(f"Selling Price: {dish} (₹)", value=float(current_price))
        if st.button("Save Prices"):
            st.success("Menu updated!")

# --- 4. OUTLET & PLATFORM SETTINGS ---
elif menu == "Outlet & Platform Settings":
    st.title("⚙️ Outlet & Platform Config")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Link Platforms")
        p_name = st.text_input("Platform Name")
        p_comm = st.number_input("Commission %", min_value=0.0)
        p_del = st.number_input("Delivery Fee (₹)", min_value=0.0)
        if st.button("Add Platform"):
            if selected_outlet not in db["outlet_configs"]: db["outlet_configs"][selected_outlet] = {"Platforms": {}}
            db["outlet_configs"][selected_outlet]["Platforms"][p_name] = {"comm": p_comm, "del": p_del}
            st.success("Linked!")

# --- 5. SALE ENTRY ---
elif menu == "Sale Entry":
    st.title(f"🎯 Sale Entry: {selected_outlet}")
    config = db["outlet_configs"].get(selected_outlet, {"Platforms": {"Direct": {"comm": 0.0, "del": 0.0}}})
    platforms = list(config["Platforms"].keys())
    dishes = list(db["menu_prices"].keys())
    
    if not dishes:
        st.error("No dishes in Menu.")
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
                        # Calc cost and subtract stock
                        ing_cost += (db["inventory"].at[idx, "Total_Cost"] / db["inventory"].at[idx, "Qty"]) * amt
                        st.session_state.db["inventory"].at[idx, "Qty"] -= amt
                
                p_data = config["Platforms"][platform]
                comm = (price * p_data['comm']) / 100
                profit = price - comm - p_data['del'] - ing_cost
                
                new_s = pd.DataFrame([{"Date": datetime.now(), "Outlet": selected_outlet, "Dish": dish, "Platform": platform, "Revenue": price, "Comm_Paid": comm, "Del_Cost": p_data['del'], "Ing_Cost": ing_cost, "Net_Profit": profit}])
                st.session_state.db["sales"] = pd.concat([db["sales"], new_s], ignore_index=True)
                st.success("Sale Recorded!")
                st.rerun()

# --- 6. DASHBOARD ---
elif menu == "Dashboard":
    st.title(f"📊 Analytics: {selected_outlet}")
    s_df = db["sales"][db["sales"]["Outlet"] == selected_outlet]
    if not s_df.empty:
        m1, m2 = st.columns(2)
        m1.metric("Revenue", f"₹{s_df['Revenue'].sum()}")
        m2.metric("Profit", f"₹{round(s_df['Net_Profit'].sum(), 2)}")
        st.plotly_chart(px.bar(s_df.groupby(s_df['Date'].dt.date).sum().reset_index(), x='Date', y='Net_Profit'))
