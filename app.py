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
        "expenses": pd.DataFrame(columns=["id", "Date", "Outlet", "Category", "Amount", "Notes"])
    }

db = st.session_state.db

# --- SIDEBAR ---
st.sidebar.title("☁️ Cloud K Command")
menu = st.sidebar.radio("Navigate", [
    "Dashboard", "Sale Entry", "Misc Expenses", 
    "Stock Room", "Recipe Master", "Menu & Pricing", "Outlet & Platform Settings"
])

selected_outlet = st.sidebar.selectbox("Active Outlet", db["outlets"])

# --- 1. DASHBOARD (FIXED DATE TYPES) ---
if menu == "Dashboard":
    st.title(f"📊 {selected_outlet}: Financial Engine")
    
    s_df = db["sales"][db["sales"]["Outlet"] == selected_outlet].copy()
    e_df = db["expenses"][db["expenses"]["Outlet"] == selected_outlet].copy()

    if s_df.empty and e_df.empty:
        st.info("No data found. Start by entering sales or expenses!")
    else:
        # CRITICAL FIX: Ensure uniform datetime types before grouping
        s_df['Date'] = pd.to_datetime(s_df['Date'])
        e_df['Date'] = pd.to_datetime(e_df['Date'])

        view_type = st.radio("Switch View", ["Monthly Analytics", "Yearly Analytics"], horizontal=True)
        
        fmt = '%b %Y' if view_type == "Monthly Analytics" else '%Y'
        s_df['Period'] = s_df['Date'].dt.strftime(fmt)
        e_df['Period'] = e_df['Date'].dt.strftime(fmt)

        monthly_sales = s_df.groupby('Period').agg({
            'Revenue': 'sum', 'Comm_Paid': 'sum', 'Del_Cost': 'sum', 'Ing_Cost': 'sum', 'Net_Profit': 'sum'
        }).reset_index()
        
        monthly_exp = e_df.groupby('Period').agg({'Amount': 'sum'}).reset_index()
        
        final_stats = pd.merge(monthly_sales, monthly_exp, on='Period', how='outer').fillna(0)
        final_stats['Final_Profit'] = final_stats['Net_Profit'] - final_stats['Amount']

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Revenue", f"₹{round(final_stats['Revenue'].sum(), 2)}")
        m2.metric("Inventory Costs", f"₹{round(final_stats['Ing_Cost'].sum(), 2)}")
        m3.metric("Platform & Delivery", f"₹{round(final_stats['Comm_Paid'].sum() + final_stats['Del_Cost'].sum(), 2)}")
        
        actual_profit = final_stats['Final_Profit'].sum()
        m4.metric("Net Profit", f"₹{round(actual_profit, 2)}", delta=f"{round(actual_profit, 2)}")

        fig = px.bar(final_stats, x='Period', y=['Revenue', 'Final_Profit'], barmode='group',
                     color_discrete_map={'Revenue': '#3498db', 'Final_Profit': '#2ecc71'})
        st.plotly_chart(fig, use_container_width=True)

# --- 2. MISC EXPENSES (FIXED TYPE ERROR & WORKING DELETE) ---
elif menu == "Misc Expenses":
    st.title(f"💸 Expenses: {selected_outlet}")
    
    with st.form("add_expense", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        cat = c1.selectbox("Category", ["Rent", "Salary", "Electricity", "Marketing", "Misc"])
        amt = c2.number_input("Amount (₹)", min_value=0.0)
        date_input = c3.date_input("Date", datetime.now())
        note = st.text_input("Notes")
        
        if st.form_submit_button("Record Expense"):
            # Ensure unique ID with microsecond precision
            new_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
            # CRITICAL FIX: Always convert input date to pandas datetime
            new_date = pd.to_datetime(date_input)
            
            new_e = pd.DataFrame([{
                "id": new_id, "Date": new_date, "Outlet": selected_outlet, 
                "Category": cat, "Amount": amt, "Notes": note
            }])
            
            st.session_state.db["expenses"] = pd.concat([st.session_state.db["expenses"], new_e], ignore_index=True)
            st.success("Expense Recorded!")
            st.rerun()

    st.divider()
    st.subheader("📜 Expense History")

    # Get a fresh reference and force datetime conversion to prevent sort errors
    exp_df = st.session_state.db["expenses"].copy()
    exp_df['Date'] = pd.to_datetime(exp_df['Date'])
    
    outlet_exp = exp_df[exp_df["Outlet"] == selected_outlet]

    if not outlet_exp.empty:
        # Sorting now works because all values in 'Date' are uniform
        outlet_exp = outlet_exp.sort_values(by="Date", ascending=False)

        h1, h2, h3, h4, h5 = st.columns([2, 2, 1.5, 3, 1])
        h1.write("**Date**")
        h2.write("**Category**")
        h3.write("**Amount**")
        h4.write("**Notes**")
        h5.write("**Action**")

        for idx, row in outlet_exp.iterrows():
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 2, 1.5, 3, 1])
                col1.write(row['Date'].strftime('%d-%b-%Y'))
                col2.write(row['Category'])
                col3.write(f"₹{row['Amount']}")
                col4.write(row['Notes'])
                
                # Use the ID for the button key but the index (idx) for the drop command
                if col5.button("🗑️", key=f"del_{row['id']}"):
                    st.session_state.db["expenses"] = st.session_state.db["expenses"].drop(idx)
                    st.rerun()
    else:
        st.info("No expenses found.")

# --- 3. RECIPE MASTER & MENU CREATOR ---
elif menu == "Recipe Master":
    st.title("👨‍🍳 Recipe & Menu Builder")
    
    # Check if there is anything in stock to build a recipe with
    inv_df = st.session_state.db["inventory"]
    outlet_inventory = inv_df[inv_df["Outlet"] == selected_outlet]
    
    if outlet_inventory.empty:
        st.warning("Your Stock Room is empty! Please add ingredients in the 'Stock Room' first to create recipes.")
    else:
        with st.form("recipe_builder_form", clear_on_submit=True):
            st.subheader("Create a New Dish")
            c1, c2 = st.columns(2)
            new_dish = c1.text_input("Dish Name (e.g., Veg Burger)")
            
            # Multi-select ingredients directly from Stock Room for the active outlet
            selected_ings = st.multiselect(
                "Select Ingredients for this Dish", 
                options=outlet_inventory["Item"].unique()
            )
            
            st.divider()
            
            recipe_map = {}
            total_dish_cost = 0.0
            
            if selected_ings:
                st.write("**Define Ingredient Quantities:**")
                # Create input rows for each selected ingredient
                for ing in selected_ings:
                    # Get unit and cost data from inventory
                    ing_data = outlet_inventory[outlet_inventory["Item"] == ing].iloc[0]
                    unit = ing_data["Unit"]
                    
                    # Calculate cost per single unit (e.g., cost per 1kg or 1pcs)
                    # Calculation: $Cost_{unit} = \frac{Total Cost}{Total Quantity}$
                    cost_per_unit = ing_data["Total_Cost"] / ing_data["Qty"] if ing_data["Qty"] > 0 else 0
                    
                    col_a, col_b, col_c = st.columns([2, 2, 2])
                    qty_needed = col_a.number_input(f"Amount of {ing} ({unit})", min_value=0.0, step=0.01, key=f"qty_{ing}")
                    col_b.write(f"Unit Cost: ₹{round(cost_per_unit, 2)}")
                    
                    # Track cost and mapping
                    item_total_cost = qty_needed * cost_per_unit
                    col_c.write(f"Subtotal: ₹{round(item_total_cost, 2)}")
                    
                    recipe_map[ing] = qty_needed
                    total_dish_cost += item_total_cost
                
                st.info(f"💡 Total Ingredient Cost for one {new_dish if new_dish else 'dish'}: **₹{round(total_dish_cost, 2)}**")
                
                # Directly set Selling Price here to update Menu & Pricing
                selling_price = st.number_input("Set Selling Price (₹)", min_value=0.0, step=1.0, help="This will update your Menu Pricing.")
            
            if st.form_submit_button("Save to Menu & Recipes"):
                if new_dish and recipe_map:
                    # Save Recipe
                    st.session_state.db["recipes"][new_dish] = recipe_map
                    # Save Price to Menu Pricing
                    st.session_state.db["menu_prices"][new_dish] = selling_price
                    st.success(f"✅ {new_dish} has been added to your Menu and Recipes!")
                    st.rerun()
                else:
                    st.error("Please provide a Dish Name and select at least one ingredient.")

    # --- LIST EXISTING RECIPES ---
    if st.session_state.db["recipes"]:
        st.divider()
        st.subheader("📜 Current Menu & Recipes")
        for dish, ings in st.session_state.db["recipes"].items():
            price = st.session_state.db['menu_prices'].get(dish, 0)
            with st.expander(f"🍴 {dish} — Selling Price: ₹{price}"):
                st.write("**Ingredients:**")
                for ing, amt in ings.items():
                    # Get unit from inventory for display
                    unit_search = outlet_inventory[outlet_inventory["Item"] == ing]
                    unit = unit_search["Unit"].iloc[0] if not unit_search.empty else ""
                    st.write(f"- {ing}: {amt} {unit}")
                
                if st.button(f"Delete {dish}", key=f"del_dish_{dish}"):
                    del st.session_state.db["recipes"][dish]
                    if dish in st.session_state.db["menu_prices"]:
                        del st.session_state.db["menu_prices"][dish]
                    st.rerun()

# --- 4. MENU & PRICING ---
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

# --- 5. OUTLET & PLATFORM SETTINGS ---
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

# --- 6. STOCK ROOM (INVENTORY MANAGEMENT) ---
elif menu == "Stock Room":
    st.title(f"📦 Stock Room: {selected_outlet}")
    
    # 1. Add New Item Form
    with st.expander("➕ Add New Inventory Item", expanded=False):
        with st.form("add_inventory_form", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            item_name = c1.text_input("Item Name (e.g., Flour, Oil)")
            qty = c2.number_input("Quantity", min_value=0.0, step=0.1)
            unit = c3.selectbox("Unit", ["kg", "ltr", "gm", "ml", "pcs", "box"])
            cost = c4.number_input("Total Cost (₹)", min_value=0.0, step=1.0)
            
            if st.form_submit_button("Add to Stock"):
                if item_name:
                    new_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
                    new_item = pd.DataFrame([{
                        "id": new_id,
                        "Outlet": selected_outlet,
                        "Item": item_name,
                        "Qty": qty,
                        "Unit": unit,
                        "Total_Cost": cost
                    }])
                    st.session_state.db["inventory"] = pd.concat([st.session_state.db["inventory"], new_item], ignore_index=True)
                    st.success(f"Added {item_name} to inventory!")
                    st.rerun()
                else:
                    st.error("Please enter an item name.")

    st.divider()

    # 2. Display and Manage Inventory
    st.subheader("📋 Current Stock Levels")
    
    # Filter inventory for the selected outlet
    inv_df = st.session_state.db["inventory"]
    outlet_inv = inv_df[inv_df["Outlet"] == selected_outlet].copy()

    if not outlet_inv.empty:
        # Create Table Headers
        h1, h2, h3, h4, h5 = st.columns([3, 2, 2, 2, 1])
        h1.write("**Item Name**")
        h2.write("**Quantity**")
        h3.write("**Unit**")
        h4.write("**Total Cost**")
        h5.write("**Action**")

        for idx, row in outlet_inv.iterrows():
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
                
                col1.write(row["Item"])
                col2.write(f"{row['Qty']}")
                col3.write(row["Unit"])
                col4.write(f"₹{row['Total_Cost']}")
                
                # Delete Button for each item
                if col5.button("🗑️", key=f"inv_del_{row['id']}"):
                    st.session_state.db["inventory"] = st.session_state.db["inventory"].drop(idx).reset_index(drop=True)
                    st.toast(f"Removed {row['Item']} from stock")
                    st.rerun()
                    
        # Optional: Low Stock Warning (Example: less than 2 units)
        low_stock = outlet_inv[outlet_inv["Qty"] < 2]
        if not low_stock.empty:
            st.warning(f"⚠️ Low Stock Alert for: {', '.join(low_stock['Item'].tolist())}")
    else:
        st.info("Your stock room is empty. Add items above to get started.")

# --- 7. SALE ENTRY ---
elif menu == "Sale Entry":
    st.title("🎯 Record Sales")
    st.info("Ensure you have added Recipes and Inventory before logging sales.")
