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

# --- 3. RECIPE MASTER (RE-ENGINEERED FOR LIVE CALCULATION) ---
elif menu == "Recipe Master":
    st.title("👨‍🍳 Recipe Builder")
    
    inv_df = st.session_state.db["inventory"]
    outlet_stock = inv_df[inv_df["Outlet"] == selected_outlet]

    if outlet_stock.empty:
        st.warning(f"⚠️ Stock Room is empty for '{selected_outlet}'. Please add items in the 'Stock Room' first.")
    else:
        # 1. Create a lookup for cost per single piece/unit
        stock_lookup = {}
        for _, row in outlet_stock.iterrows():
            u_cost = row['Total_Cost'] / row['Qty'] if row['Qty'] > 0 else 0
            stock_lookup[row['Item']] = {
                'unit_cost': u_cost,
                'unit_type': row['Unit']
            }

        # 2. Recipe Inputs (Outside form for live updates)
        st.subheader("Create a New Dish")
        dish_name = st.text_input("Dish Name (e.g., Burger)")
        
        selected_ings = st.multiselect(
            "Select Ingredients from Stock", 
            options=list(stock_lookup.keys())
        )
        
        st.divider()
        
        recipe_map = {}
        total_production_cost = 0.0
        
        if selected_ings:
            st.write("**Specify Pieces/Amount Used per Dish:**")
            for ing in selected_ings:
                u_price = stock_lookup[ing]['unit_cost']
                u_type = stock_lookup[ing]['unit_type']
                
                c1, c2, c3 = st.columns([3, 2, 2])
                
                # These inputs now update 'total_production_cost' instantly
                qty_used = c1.number_input(f"Amount of {ing} ({u_type})", min_value=0.0, step=0.01, key=f"rec_{ing}")
                
                item_cost = qty_used * u_price
                
                c2.write(f"Cost per {u_type}: ₹{round(u_price, 2)}")
                c3.write(f"**Subtotal: ₹{round(item_cost, 2)}**")
                
                recipe_map[ing] = qty_used
                total_production_cost += item_cost
            
            st.divider()
            st.success(f"💰 **Total Ingredient Cost for this Dish: ₹{round(total_production_cost, 2)}**")

            # 3. Save Button (Inside a small form to trigger the save action)
            with st.form("save_recipe_form"):
                st.write("Confirm and Save to Menu")
                if st.form_submit_button("Save Recipe"):
                    if dish_name and recipe_map:
                        st.session_state.db["recipes"][dish_name] = recipe_map
                        st.session_state.db["menu_prices"][dish_name] = total_production_cost
                        st.success(f"✅ Recipe for {dish_name} saved!")
                        st.rerun()
                    else:
                        st.error("Please provide a name and ingredients.")

    # --- DISPLAY SAVED RECIPES ---
    if st.session_state.db["recipes"]:
        st.divider()
        st.subheader("📜 Saved Recipes & Production Costs")
        for dish, ingredients in st.session_state.db["recipes"].items():
            cost = st.session_state.db["menu_prices"].get(dish, 0)
            with st.expander(f"🍴 {dish} — Production Cost: ₹{round(cost, 2)}"):
                for item, amount in ingredients.items():
                    unit_info = outlet_stock[outlet_stock["Item"] == item]
                    unit_disp = unit_info["Unit"].iloc[0] if not unit_info.empty else "units"
                    st.write(f"- {item}: {amount} {unit_disp}")
                
                if st.button(f"Delete {dish}", key=f"rm_{dish}"):
                    del st.session_state.db["recipes"][dish]
                    if dish in st.session_state.db["menu_prices"]:
                        del st.session_state.db["menu_prices"][dish]
                    st.rerun()

# --- 4. MENU & PRICING (UPDATED WITH ADVANCED COSTING TABLE) ---
elif menu == "Menu & Pricing":
    st.title("💰 Menu Master & advanced Costing")
    
    if not st.session_state.db["recipes"]:
        st.info("⚠️ No recipes found. Please create a recipe in 'Recipe Master' first to see it here.")
    else:
        st.subheader(f"Costing Analysis for {selected_outlet}")
        
        # Prepare lists to build the final display table
        table_data = []

        for dish_name in st.session_state.db["recipes"].keys():
            # 1. Pull Production Cost from Recipe Master
            prod_cost = st.session_state.db["menu_prices"].get(dish_name, 0.0)
            
            st.markdown(f"### 🍴 {dish_name}")
            col_in1, col_in2, col_in3 = st.columns(3)
            
            # 2. Manual Inputs
            comm = col_in1.number_input(f"Platform Commission (₹)", min_value=0.0, step=1.0, key=f"comm_{dish_name}")
            adv = col_in2.number_input(f"Advertisement Cost (₹)", min_value=0.0, step=1.0, key=f"adv_{dish_name}")
            misc = col_in3.number_input(f"Misc Expenses (₹)", min_value=0.0, step=1.0, key=f"misc_{dish_name}")
            
            # 3. Real-time Calculations
            total_spent = prod_cost + comm + adv + misc
            labour = total_spent * 0.10  # 10% of total spent
            profit = (total_spent + labour) * 0.10 # 10% of (total spent + labour)
            grand_total = total_spent + labour + profit
            
            # 4. Add to table list
            table_data.append({
                "Dish Name": dish_name,
                "Production Cost": f"₹{round(prod_cost, 2)}",
                "Platform Commission": f"₹{round(comm, 2)}",
                "Advertisement Cost": f"₹{round(adv, 2)}",
                "Misc": f"₹{round(misc, 2)}",
                "Total Spent": f"₹{round(total_spent, 2)}",
                "Labour (10%)": f"₹{round(labour, 2)}",
                "Profit (10%)": f"₹{round(profit, 2)}",
                "Grand Total": f"₹{round(grand_total, 2)}"
            })
            st.divider()

        # 5. Display the Final Table
        if table_data:
            st.subheader("📊 Final Pricing Summary Table")
            summary_df = pd.DataFrame(table_data)
            st.table(summary_df)
            
            # Optional: Button to export this data
            csv = summary_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Pricing Table",
                csv,
                f"Pricing_Analysis_{selected_outlet}.csv",
                "text/csv",
                key='download-csv'
            )

# --- 5. OUTLET & PLATFORM SETTINGS ---
elif menu == "Outlet & Platform Settings":
    st.title("⚙️ Outlet & Platform Config")
    
    # --- OUTLET MANAGEMENT SECTION ---
    st.subheader("🏢 Outlet Management")
    c1, c2 = st.columns(2)
    
    with c1:
        # Add New Outlet
        with st.expander("➕ Add New Outlet"):
            new_outlet_name = st.text_input("New Outlet Name")
            if st.button("Create Outlet"):
                if new_outlet_name and new_outlet_name not in st.session_state.db["outlets"]:
                    st.session_state.db["outlets"].append(new_outlet_name)
                    st.success(f"Outlet '{new_outlet_name}' added!")
                    st.rerun()
                else:
                    st.error("Invalid name or outlet already exists.")

    with c2:
        # Rename Current Outlet
        with st.expander("📝 Rename Current Outlet"):
            rename_val = st.text_input("New name for " + selected_outlet)
            if st.button("Update Name"):
                if rename_val:
                    # Update the list
                    idx = st.session_state.db["outlets"].index(selected_outlet)
                    st.session_state.db["outlets"][idx] = rename_val
                    
                    # Update references in dataframes
                    st.session_state.db["inventory"].loc[st.session_state.db["inventory"]["Outlet"] == selected_outlet, "Outlet"] = rename_val
                    st.session_state.db["expenses"].loc[st.session_state.db["expenses"]["Outlet"] == selected_outlet, "Outlet"] = rename_val
                    st.session_state.db["sales"].loc[st.session_state.db["sales"]["Outlet"] == selected_outlet, "Outlet"] = rename_val
                    
                    st.success("Outlet renamed!")
                    st.rerun()

    # Delete Outlet
    with st.expander("🗑️ Danger Zone: Delete Outlet"):
        st.warning(f"This will remove '{selected_outlet}' from the list. (Data in logs will remain but won't be accessible via this outlet name)")
        if st.button(f"Permanently Delete {selected_outlet}"):
            if len(st.session_state.db["outlets"]) > 1:
                st.session_state.db["outlets"].remove(selected_outlet)
                st.success("Outlet deleted.")
                st.rerun()
            else:
                st.error("You must have at least one outlet.")

    st.divider()

    # --- PLATFORM MANAGEMENT SECTION ---
    st.subheader("🌐 Platform Settings")
    p1, p2 = st.columns(2)
    with p1:
        st.markdown("#### Link New Platform")
        p_name = st.text_input("Platform Name (e.g., Zomato, Swiggy)")
        p_comm = st.number_input("Commission %", min_value=0.0, step=0.1)
        p_del = st.number_input("Delivery Fee (₹)", min_value=0.0, step=1.0)
        if st.button("Add Platform"):
            if selected_outlet not in db["outlet_configs"]: 
                db["outlet_configs"][selected_outlet] = {"Platforms": {}}
            db["outlet_configs"][selected_outlet]["Platforms"][p_name] = {"comm": p_comm, "del": p_del}
            st.success(f"Linked {p_name} to {selected_outlet}!")

    with p2:
        st.markdown("#### Active Platforms")
        if selected_outlet in db["outlet_configs"] and db["outlet_configs"][selected_outlet]["Platforms"]:
            for plat, details in db["outlet_configs"][selected_outlet]["Platforms"].items():
                col_p, col_b = st.columns([3, 1])
                col_p.write(f"**{plat}**: {details['comm']}% comm | ₹{details['del']} fee")
                if col_b.button("🗑️", key=f"del_plat_{plat}"):
                    del db["outlet_configs"][selected_outlet]["Platforms"][plat]
                    st.rerun()
        else:
            st.info("No platforms linked to this outlet.")

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
    st.title(f"🎯 Sale Entry: {selected_outlet}")
    
    # 1. Verification: Ensure recipes exist
    if not st.session_state.db["recipes"]:
        st.warning("⚠️ No recipes found. Please create recipes in 'Recipe Master' first.")
    else:
        # 2. Sale Entry Form
        with st.form("sale_entry_form", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            sale_date = c1.date_input("Sale Date", datetime.now())
            selected_dish = c2.selectbox("Select Dish", list(st.session_state.db["recipes"].keys()))
            
            # Fetch active platforms for the selected outlet
            platform_options = ["Direct"]
            if selected_outlet in st.session_state.db["outlet_configs"]:
                platform_options = list(st.session_state.db["outlet_configs"][selected_outlet].get("Platforms", {"Direct": 0}).keys())
            
            selected_plat = c3.selectbox("Platform", platform_options)
            qty_sold = c4.number_input("Quantity Sold", min_value=1, step=1)
            
            submit_sale = st.form_submit_button("🔨 Record Sale & Deduct Stock")

            if submit_sale:
                # --- AUTO-CALCULATION LOGIC (Matching Menu & Pricing Table) ---
                # 1. Get Production Cost (Ingredient Cost) from Recipe Master
                ing_cost_per_unit = st.session_state.db["menu_prices"].get(selected_dish, 0.0)
                
                # 2. Get Platform/Misc costs (Assuming these are retrieved from your existing inputs or platform settings)
                # If these values are platform-specific, we pull from config; otherwise default to 0
                comm_val = 0.0
                del_cost_val = 0.0
                if selected_outlet in st.session_state.db["outlet_configs"] and selected_plat in st.session_state.db["outlet_configs"][selected_outlet]["Platforms"]:
                    p_cfg = st.session_state.db["outlet_configs"][selected_outlet]["Platforms"][selected_plat]
                    comm_val = (p_cfg['comm'] / 100) * 0 # Placeholder if revenue isn't known yet
                    del_cost_val = p_cfg['del']

                # 3. Calculate Grand Total as per Menu Master logic
                # Grand Total = (Total Spent + Labour 10%) + Profit 10%
                total_spent = ing_cost_per_unit + comm_val # Based on your table columns
                labour = total_spent * 0.10
                profit = (total_spent + labour) * 0.10
                grand_total_per_unit = total_spent + labour + profit
                
                total_revenue = grand_total_per_unit * qty_sold
                total_ing_cost = ing_cost_per_unit * qty_sold

                # --- STOCK DEDUCTION LOGIC ---
                recipe = st.session_state.db["recipes"][selected_dish]
                stock_available = True
                
                # Check stock levels
                for item, amt_per_dish in recipe.items():
                    total_needed = amt_per_dish * qty_sold
                    current_stock = st.session_state.db["inventory"][
                        (st.session_state.db["inventory"]["Outlet"] == selected_outlet) & 
                        (st.session_state.db["inventory"]["Item"] == item)
                    ]["Qty"].sum()
                    
                    if current_stock < total_needed:
                        st.error(f"❌ Insufficient {item}. Need {total_needed}, have {current_stock}")
                        stock_available = False
                        break
                
                if stock_available:
                    # Deduct from Inventory
                    for item, amt_per_dish in recipe.items():
                        idx = st.session_state.db["inventory"][
                            (st.session_state.db["inventory"]["Outlet"] == selected_outlet) & 
                            (st.session_state.db["inventory"]["Item"] == item)
                        ].index
                        if not idx.empty:
                            st.session_state.db["inventory"].at[idx[0], "Qty"] -= (amt_per_dish * qty_sold)
                    
                    # Log the Sale Entry
                    new_sale = pd.DataFrame([{
                        "id": datetime.now().strftime('%Y%m%d%H%M%S%f'),
                        "Date": pd.to_datetime(sale_date),
                        "Outlet": selected_outlet,
                        "Dish": selected_dish,
                        "Platform": selected_plat,
                        "Qty": qty_sold,
                        "Revenue": total_revenue, # Auto-calculated Grand Total
                        "Ing_Cost": total_ing_cost,
                        "Net_Profit": total_revenue - total_ing_cost
                    }])
                    
                    st.session_state.db["sales"] = pd.concat([st.session_state.db["sales"], new_sale], ignore_index=True)
                    st.success(f"✅ Recorded {qty_sold} {selected_dish}. Total Revenue: ₹{round(total_revenue, 2)}")
                    st.rerun()

    # 3. Recent Sales History & Delete Section
    st.divider()
    st.subheader("📜 Recent Sales Logs")
    s_df = st.session_state.db["sales"]
    outlet_sales = s_df[s_df["Outlet"] == selected_outlet].sort_values(by="Date", ascending=False)

    if not outlet_sales.empty:
        h1, h2, h3, h4, h5 = st.columns([2, 3, 1, 2, 1])
        h1.write("**Date**")
        h2.write("**Dish (Platform)**")
        h3.write("**Qty**")
        h4.write("**Grand Total (Revenue)**")
        h5.write("**Action**")

        for idx, row in outlet_sales.iterrows():
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 3, 1, 2, 1])
                col1.write(pd.to_datetime(row['Date']).strftime('%d-%b-%Y'))
                col2.write(f"{row['Dish']} ({row['Platform']})")
                col3.write(str(row['Qty']))
                col4.write(f"₹{round(row['Revenue'], 2)}")
                
                if col5.button("🗑️", key=f"del_sale_{row['id']}"):
                    st.session_state.db["sales"] = st.session_state.db["sales"].drop(idx)
                    st.rerun()
    else:
        st.info("No sales recorded for this outlet yet.")
