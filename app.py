import streamlit as st
import pandas as pd

# --- APP CONFIG ---
st.set_page_config(page_title="Cloud K - World Class ERP", page_icon="☁️", layout="wide")

# --- DATABASE INITIALIZATION ---
if 'db' not in st.session_state:
    st.session_state.db = {
        "outlets": [
            "The Home Plate", "No Cap Burgers", "Pocket Pizzaz", 
            "Witx Sandwitx", "Hello Momos", "Khushi Breakfast Club", "Bihar ka Swad"
        ],
        "inventory": pd.DataFrame(columns=["Outlet", "Item", "Qty", "Unit", "Total_Purchase_Price"]),
        "recipes": {}, # Format: {"Dish": {"Ingredient": Qty}}
        "sales": pd.DataFrame(columns=["Outlet", "Dish", "Revenue", "Cost", "Profit"])
    }

db = st.session_state.db

# --- SIDEBAR: GLOBAL CONTROLS ---
st.sidebar.title("☁️ Cloud K Control Center")
menu = st.sidebar.radio("Navigate System", ["Dashboard", "Outlet Settings", "Stock Room", "Recipe Master", "Sale Entry"])

# --- 1. OUTLET SETTINGS (Add/Remove Outlets) ---
if menu == "Outlet Settings":
    st.title("🏢 Outlet Management")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Add New Outlet")
        new_out = st.text_input("Outlet Name")
        if st.button("Add Outlet"):
            if new_out and new_out not in db["outlets"]:
                st.session_state.db["outlets"].append(new_out)
                st.success(f"Added {new_out}!")
                st.rerun()

    with col2:
        st.subheader("Remove Outlet")
        rem_out = st.selectbox("Select Outlet to Delete", db["outlets"])
        if st.button("Confirm Delete", help="This will remove the outlet from the list"):
            st.session_state.db["outlets"].remove(rem_out)
            st.warning(f"Removed {rem_out}")
            st.rerun()

# --- SELECT ACTIVE OUTLET FOR OTHER SCREENS ---
if menu != "Outlet Settings":
    selected_outlet = st.sidebar.selectbox("Active Outlet", db["outlets"])
    outlet_inv = db["inventory"][db["inventory"]["Outlet"] == selected_outlet]

# --- 2. STOCK ROOM ---
if menu == "Stock Room":
    st.title(f"📦 {selected_outlet} Inventory")
    st.info("Add ingredients and packaging material here first.")
    
    with st.expander("➕ Add Stock Item (Ingredients / Packaging)"):
        c1, c2, c3, c4 = st.columns(4)
        name = c1.text_input("Item Name (e.g., Flour, Box, Oil)")
        q = c2.number_input("Purchase Quantity", min_value=0.0, step=0.1)
        u = c3.selectbox("Unit", ["Kg", "Grams", "Units", "Liters", "Packets"])
        p = c4.number_input("Purchase Price (₹)", min_value=0.0)
        
        if st.button("Save to Inventory"):
            new_item = pd.DataFrame([{"Outlet": selected_outlet, "Item": name, "Qty": q, "Unit": u, "Total_Purchase_Price": p}])
            st.session_state.db["inventory"] = pd.concat([db["inventory"], new_item], ignore_index=True)
            st.success(f"Stocked {name} in {selected_outlet}")
            st.rerun()
    
    st.table(outlet_inv)

# --- 3. RECIPE MASTER ---
elif menu == "Recipe Master":
    st.title("👨‍🍳 Recipe & Packaging Linker")
    st.write("Define the 'Recipe' for your dishes once. It will be used for all outlets.")
    
    dish_name = st.text_input("Dish Name (e.g., Aloo Paratha, Burger)")
    all_unique_items = db["inventory"]["Item"].unique()
    
    if len(all_unique_items) > 0:
        ingredients = st.multiselect("Select Ingredients & Packaging used in 1 unit of this dish", all_unique_items)
        recipe_map = {}
        
        if ingredients:
            cols = st.columns(len(ingredients))
            for i, item in enumerate(ingredients):
                unit = db["inventory"][db["inventory"]["Item"] == item]["Unit"].iloc[0]
                recipe_map[item] = cols[i].number_input(f"Qty of {item} ({unit})", min_value=0.001, format="%.3f")
            
            if st.button("Save Product Recipe"):
                st.session_state.db["recipes"][dish_name] = recipe_map
                st.success(f"Recipe for {dish_name} saved successfully!")
    else:
        st.warning("Go to Stock Room and add items first!")

# --- 4. SALE ENTRY ---
elif menu == "Sale Entry":
    st.title(f"🎯 Sales: {selected_outlet}")
    
    if not db["recipes"]:
        st.error("No recipes found! Define them in Recipe Master first.")
    else:
        dish_to_sell = st.selectbox("Select Dish Sold", list(db["recipes"].keys()))
        sell_price = st.number_input("Sale Price (₹)", min_value=0)
        
        if st.button("Finalize Sale"):
            recipe = db["recipes"][dish_to_sell]
            can_process = True
            calculated_cost = 0
            
            # Validation & Costing
            for item, req_qty in recipe.items():
                stock_row = outlet_inv[outlet_inv["Item"] == item]
                if stock_row.empty or stock_row["Qty"].values[0] < req_qty:
                    st.error(f"Insufficient Stock: {item} (Needed: {req_qty})")
                    can_process = False
                else:
                    # Cost = (Total Price / Total Qty) * Used Qty
                    item_unit_cost = stock_row["Total_Purchase_Price"].values[0] / max(1, stock_row["Qty"].values[0])
                    calculated_cost += (item_unit_cost * req_qty)

            if can_process:
                # Deduct Stock
                for item, req_qty in recipe.items():
                    st.session_state.db["inventory"].loc[
                        (db["inventory"]["Outlet"] == selected_outlet) & 
                        (db["inventory"]["Item"] == item), "Qty"
                    ] -= req_qty
                
                # Record Sale
                profit = sell_price - calculated_cost
                new_sale = pd.DataFrame([{
                    "Outlet": selected_outlet, "Dish": dish_to_sell, 
                    "Revenue": sell_price, "Cost": round(calculated_cost, 2), "Profit": round(profit, 2)
                }])
                st.session_state.db["sales"] = pd.concat([db["sales"], new_sale], ignore_index=True)
                st.balloons()
                st.success(f"Sold {dish_to_sell}! Stock adjusted.")

# --- 5. DASHBOARD ---
elif menu == "Dashboard":
    st.title(f"📊 Financial Summary: {selected_outlet}")
    
    out_sales = db["sales"][db["sales"]["Outlet"] == selected_outlet]
    
    m1, m2, m3 = st.columns(3)
    total_rev = out_sales["Revenue"].sum()
    total_cost = out_sales["Cost"].sum()
    net_profit = out_sales["Profit"].sum()
    
    m1.metric("Total Revenue", f"₹{total_rev}")
    m2.metric("Cost of Goods (COGS)", f"₹{total_cost}")
    m3.metric("Net Profit", f"₹{net_profit}", delta=float(net_profit))
    
    st.subheader("Inventory Status")
    # Highlight low stock
    def highlight_low(s):
        return ['background-color: #ffcccc' if v < 5 else '' for v in s]
    
    if not outlet_inv.empty:
        st.dataframe(outlet_inv.style.apply(highlight_low, subset=['Qty']))
    else:
        st.write("No stock data available.")
