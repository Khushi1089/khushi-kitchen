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

# --- 6. DASHBOARD (STRICT DATE-BASED ANALYTICS) ---
if menu == "Dashboard":
    st.title(f"📊 {selected_outlet}: Financial Engine")
    
    # 1. Filter Data by Selected Outlet
    s_df = db["sales"][db["sales"]["Outlet"] == selected_outlet].copy()
    e_df = db["expenses"][db["expenses"]["Outlet"] == selected_outlet].copy()

    if s_df.empty and e_df.empty:
        st.info("No data found. Start by entering sales or expenses!")
    else:
        # Ensure Date columns are datetime objects
        s_df['Date'] = pd.to_datetime(s_df['Date'])
        e_df['Date'] = pd.to_datetime(e_df['Date'])

        # 2. Time View Selection
        view_type = st.radio("Switch View", ["Monthly Analytics", "Yearly Analytics"], horizontal=True)
        
        # 3. Aggregation Logic
        if view_type == "Monthly Analytics":
            s_df['Period'] = s_df['Date'].dt.strftime('%b %Y')
            e_df['Period'] = e_df['Date'].dt.strftime('%b %Y')
        else:
            s_df['Period'] = s_df['Date'].dt.strftime('%Y')
            e_df['Period'] = e_df['Date'].dt.strftime('%Y')

        # Calculate Grouped Data
        monthly_sales = s_df.groupby('Period').agg({
            'Revenue': 'sum', 'Comm_Paid': 'sum', 'Del_Cost': 'sum', 'Ing_Cost': 'sum', 'Net_Profit': 'sum'
        }).reset_index()
        
        monthly_exp = e_df.groupby('Period').agg({'Amount': 'sum'}).reset_index()
        
        # Combine Sales and Expenses for True Profit
        final_stats = pd.merge(monthly_sales, monthly_exp, on='Period', how='outer').fillna(0)
        final_stats['Final_Profit'] = final_stats['Net_Profit'] - final_stats['Amount']

        # 4. Display Key Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Revenue", f"₹{round(final_stats['Revenue'].sum(), 2)}")
        m2.metric("Inventory Costs", f"₹{round(final_stats['Ing_Cost'].sum(), 2)}")
        m3.metric("Platform & Delivery", f"₹{round(final_stats['Comm_Paid'].sum() + final_stats['Del_Cost'].sum(), 2)}")
        
        actual_profit = final_stats['Final_Profit'].sum()
        if actual_profit >= 0:
            m4.metric("Net Profit", f"₹{round(actual_profit, 2)}", delta_color="normal")
        else:
            m4.metric("Net Loss", f"₹{round(actual_profit, 2)}", delta="LOSS", delta_color="inverse")

        # 5. Visual Trend Analysis
        st.subheader(f"{view_type} Trend")
        
        fig = px.bar(final_stats, x='Period', y=['Revenue', 'Final_Profit'],
                     barmode='group', 
                     color_discrete_map={'Revenue': '#3498db', 'Final_Profit': '#2ecc71'},
                     labels={'value': 'Amount (₹)', 'variable': 'Financial Category'})
        st.plotly_chart(fig, use_container_width=True)

        # 6. Breakdown Table
        with st.expander("View Detailed Raw Data"):
            st.dataframe(final_stats.sort_values('Period', ascending=False))

# --- 7. MISC EXPENSES (UPGRADED WITH EDIT & DELETE) ---
if menu == "Misc Expenses":
    st.title(f"💸 Expense Ledger: {selected_outlet}")
    
    # Session state for tracking which expense is being edited
    if 'editing_expense_id' not in st.session_state:
        st.session_state.editing_expense_id = None

    # --- ADD NEW EXPENSE FORM ---
    with st.expander("➕ Add New Expense", expanded=st.session_state.editing_expense_id is None):
        with st.form("exp_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            cat = c1.selectbox("Category", ["Rent", "Salary", "Electricity", "Packaging", "Cleaning", "Marketing", "Maintenance", "Misc"])
            amt = c2.number_input("Amount (₹)", min_value=0.0, step=10.0)
            c3, c4 = st.columns(2)
            exp_date = c3.date_input("Date", datetime.now())
            note = c4.text_input("Notes")
            
            if st.form_submit_button("Record Expense"):
                new_id = datetime.now().strftime('%Y%m%d%H%M%S') # Unique ID based on timestamp
                new_e = pd.DataFrame([{"id": new_id, "Date": exp_date, "Outlet": selected_outlet, "Category": cat, "Amount": amt, "Notes": note}])
                st.session_state.db["expenses"] = pd.concat([db["expenses"], new_e], ignore_index=True)
                st.success("Expense Recorded!")
                st.rerun()

    st.divider()

    # --- EXPENSE HISTORY & EDITING ---
    st.subheader(f"📜 Expense History for {selected_outlet}")
    exp_list = db["expenses"][db["expenses"]["Outlet"] == selected_outlet].copy()

    if not exp_list.empty:
        exp_list = exp_list.sort_values(by="Date", ascending=False)
        
        for idx, row in exp_list.iterrows():
            # If this row is being edited, show an edit form
            if st.session_state.editing_expense_id == row['id']:
                with st.container():
                    st.warning(f"Editing Entry from {row['Date']}")
                    with st.form(key=f"edit_form_{row['id']}"):
                        ec1, ec2, ec3 = st.columns(3)
                        new_cat = ec1.selectbox("Category", ["Rent", "Salary", "Electricity", "Packaging", "Cleaning", "Marketing", "Maintenance", "Misc"], 
                                               index=["Rent", "Salary", "Electricity", "Packaging", "Cleaning", "Marketing", "Maintenance", "Misc"].index(row['Category']))
                        new_amt = ec2.number_input("Amount (₹)", value=float(row['Amount']))
                        new_date = ec3.date_input("Date", pd.to_datetime(row['Date']))
                        new_note = st.text_input("Notes", value=row['Notes'])
                        
                        eb1, eb2 = st.columns(2)
                        if eb1.form_submit_button("✅ Save Changes"):
                            db["expenses"].loc[db["expenses"]['id'] == row['id'], ["Category", "Amount", "Date", "Notes"]] = [new_cat, new_amt, new_date, new_note]
                            st.session_state.editing_expense_id = None
                            st.success("Updated Successfully!")
                            st.rerun()
                        if eb2.form_submit_button("❌ Cancel"):
                            st.session_state.editing_expense_id = None
                            st.rerun()
            else:
                # Regular view of the history
                col1, col2, col3, col4, col5 = st.columns([1.5, 2, 1.5, 3, 2])
                col1.write(f"**{row['Date']}**")
                col2.write(row['Category'])
                col3.write(f"₹{row['Amount']}")
                col4.write(f"*{row['Notes']}*")
                
                # Action Buttons
                if col5.button("✏️ Edit", key=f"edit_btn_{row['id']}"):
                    st.session_state.editing_expense_id = row['id']
                    st.rerun()
                if col5.button("🗑️ Delete", key=f"del_btn_{row['id']}"):
                    st.session_state.db["expenses"] = db["expenses"][db["expenses"]['id'] != row['id']]
                    st.rerun()
            st.write("---")
    else:
        st.info("No expenses found.")
