import streamlit as st
import pandas as pd

# --- APP CONFIG ---
st.set_page_config(page_title="Cloud K - Ultimate", page_icon="☁️", layout="wide")

# --- INITIALIZE DATABASE ---
# This holds data for all 5 outlets separately
if 'db' not in st.session_state:
    st.session_state.db = {
        "outlets": ["The Home Plate", "No Cap Burgers", "Pocket Pizzaz", "Witx Sandwitx", "Hello Momos"],
        "inventory": pd.DataFrame(columns=["Outlet", "Item", "Qty", "Unit", "Total_Cost"]),
        "recipes": {}, # Format: {"Dish": {"Ingredient": Qty}}
        "sales": pd.DataFrame(columns=["Outlet", "Dish", "Revenue", "Cost", "Profit"])
    }

db = st.session_state.db

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("☁️ Cloud K Master")
selected_outlet = st.sidebar.selectbox("Current Outlet", db["outlets"])
menu = st.sidebar.radio("Navigation", ["Dashboard", "Stock Room", "Recipe Master", "Sale Entry"])

# Filter inventory for the selected outlet
outlet_inv = db["inventory"][db["inventory"]["Outlet"] == selected_outlet]

# --- 1. STOCK ROOM (Add Ingredients & Packaging) ---
if menu == "Stock Room":
    st.title(f"📦 {selected_outlet} Inventory")
    with st.expander("➕ Add Raw Material / Packaging"):
        c1, c2, c3, c4 = st.columns(4)
        name = c1.text_input("Item Name")
        q = c2.number_input("Total Quantity", min_value=0.0)
        u = c3.selectbox("Unit", ["Kg", "Grams", "Units", "Packets"])
        p = c4.number_input("Purchase Price (₹)", min_value=0.0)
        
        if st.button("Save to Stock"):
            new_item = pd.DataFrame([{"Outlet": selected_outlet, "Item": name, "Qty": q, "Unit": u, "Total_Cost": p}])
            st.session_state.db["inventory"] = pd.concat([db["inventory"], new_item], ignore_index=True)
            st.rerun()
    st.dataframe(outlet_inv, use_container_width=True)

# --- 2. RECIPE MASTER (Define once) ---
elif menu == "Recipe Master":
    st.title("👨‍🍳 Recipe & Packaging Master")
    st.info("Define what 1 dish uses. This applies to all outlets!")
    
    dish_name = st.text_input("Dish Name (e.g., Momos Full Plate)")
    
    # Get all unique items across all outlets to build a recipe
    all_items = db["inventory"]["Item"].unique()
    
    if len(all_items) > 0:
        items_needed = st.multiselect("Select Ingredients & Packaging", all_items)
        recipe_details = {}
        
        cols = st.columns(len(items_needed) if items_needed else 1)
        for i, item in enumerate(items_needed):
            unit = db["inventory"][db["inventory"]["Item"] == item]["Unit"].iloc[0]
            recipe_details[item] = cols[i].number_input(f"Qty of {item} ({unit})", min_value=0.001, format="%.3f")
            
        if st.button("Save Recipe"):
            st.session_state.db["recipes"][dish_name] = recipe_details
            st.success(f"Recipe for {dish_name} is now active!")
    else:
        st.warning("Go to Stock Room and add ingredients first!")

# --- 3. SALE ENTRY (The Magic Button) ---
elif menu == "Sale Entry":
    st.title(f"🎯 {selected_outlet} - Sales")
    if not db["recipes"]:
        st.warning("Please define a Recipe first!")
    else:
        dish = st.selectbox("Product Sold", list(db["recipes"].keys()))
        price = st.number_input("Selling Price (₹)", min_value=0)
        
        if st.button("Confirm Sale"):
            recipe = db["recipes"][dish]
            can_sell = True
            cost_of_dish = 0
            
            # Check stock and calculate cost
            for item, used_qty in recipe.items():
                item_row = outlet_inv[outlet_inv["Item"] == item]
                if item_row.empty or item_row["Qty"].values[0] < used_qty:
                    st.error(f"Low Stock: {item}!")
                    can_sell = False
                else:
                    # Calculate cost (Price / Total Qty * Used Qty)
                    unit_cost = item_row["Total_Cost"].values[0] / max(1, item_row["Qty"].values[0])
                    cost_of_dish += (unit_cost * used_qty)

            if can_sell:
                # Deduct Stock
                for item, used_qty in recipe.items():
                    st.session_state.db["inventory"].loc[(db["inventory"]["Outlet"] == selected_outlet) & (db["inventory"]["Item"] == item), "Qty"] -= used_qty
                
                # Log Sale
                new_sale = pd.DataFrame([{"Outlet": selected_outlet, "Dish": dish, "Revenue": price, "Cost": round(cost_of_dish, 2), "Profit": price - round(cost_of_dish, 2)}])
                st.session_state.db["sales"] = pd.concat([db["sales"], new_sale], ignore_index=True)
                st.balloons()
                st.success("Sale recorded and stock deducted!")

# --- 4. DASHBOARD ---
elif menu == "Dashboard":
    st.title(f"📊 {selected_outlet} Dashboard")
    my_sales = db["sales"][db["sales"]["Outlet"] == selected_outlet]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Revenue", f"₹{my_sales['Revenue'].sum()}")
    c2.metric("Total Cost", f"₹{my_sales['Cost'].sum()}")
    c3.metric("Net Profit", f"₹{my_sales['Profit'].sum()}")
    
    st.subheader("Inventory Levels")
    st.dataframe(outlet_inv)
