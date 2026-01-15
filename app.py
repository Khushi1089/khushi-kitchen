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
        "sales": pd.DataFrame(columns=["Date", "Outlet", "Dish", "Revenue", "Cost", "Profit"])
    }

db = st.session_state.db

# --- SIDEBAR ---
st.sidebar.title("☁️ Cloud K Command")
menu = st.sidebar.radio("Navigate System", ["Dashboard", "Stock Room", "Recipe Master", "Sale Entry", "Outlet Settings", "Unit Converter"])

# --- 1. UNIT CONVERTER (New Feature) ---
if menu == "Unit Converter":
    st.title("⚖️ Smart Unit Converter")
    st.write("Convert Pieces to Weight for Inventory Accuracy.")
    c1, c2, c3 = st.columns(3)
    val = c1.number_input("Enter Quantity", min_value=0.0)
    u_from = c2.selectbox("From", ["Pieces", "Kg", "Grams"])
    weight_of_one = c3.number_input("Weight of 1 piece (Grams)", min_value=0.0)
    
    if weight_of_one > 0:
        if u_from == "Pieces":
            st.success(f"Total Weight: {(val * weight_of_one)/1000} Kg")
        else:
            st.success(f"Total Pieces: {(val * 1000) / weight_of_one}")

# --- 2. OUTLET SETTINGS ---
elif menu == "Outlet Settings":
    st.title("🏢 Outlet Management")
    col1, col2 = st.columns(2)
    with col1:
        new_out = st.text_input("New Outlet Name")
        if st.button("Add Outlet"):
            if new_out and new_out not in db["outlets"]:
                st.session_state.db["outlets"].append(new_out)
                st.rerun()
    with col2:
        rem_out = st.selectbox("Remove Outlet", db["outlets"])
        if st.button("Delete Outlet"):
            st.session_state.db["outlets"].remove(rem_out)
            st.rerun()

# --- SELECT ACTIVE OUTLET ---
if menu not in ["Outlet Settings", "Unit Converter"]:
    selected_outlet = st.sidebar.selectbox("Active Outlet", db["outlets"])
    outlet_inv = db["inventory"][db["inventory"]["Outlet"] == selected_outlet]

# --- 3. STOCK ROOM (With Piece-to-Weight logic) ---
if menu == "Stock Room":
    st.title(f"📦 {selected_outlet} Inventory")
    with st.expander("➕ Add Stock (Ingredients/Packaging)"):
        c1, c2, c3, c4 = st.columns(4)
        name = c1.text_input("Item Name")
        qty = c2.number_input("Qty", min_value=0.0)
        unit = c3.selectbox("Unit", ["Units/Pieces", "Kg", "Liters"])
        price = c4.number_input("Total Price (₹)", min_value=0.0)
        w_per_p = st.number_input("Weight per Piece (Grams) - If applicable", min_value=0.0)
        
        if st.button("Save Stock"):
            new_row = {"Outlet": selected_outlet, "Item": name, "Qty": qty, "Unit": unit, "Total_Cost": price, "Weight_Per_Piece": w_per_p}
            st.session_state.db["inventory"] = pd.concat([db["inventory"], pd.DataFrame([new_row])], ignore_index=True)
            st.rerun()
    st.table(outlet_inv)

# --- 4. RECIPE MASTER ---
elif menu == "Recipe Master":
    st.title("👨‍Chef Recipe Master")
    dish = st.text_input("Dish Name")
    all_items = db["inventory"]["Item"].unique()
    if len(all_items) > 0:
        ingredients = st.multiselect("Select Ingredients", all_items)
        recipe_map = {}
        if ingredients:
            cols = st.columns(len(ingredients))
            for i, item in enumerate(ingredients):
                recipe_map[item] = cols[i].number_input(f"Qty of {item}", min_value=0.001, format="%.3f")
            if st.button("Save Recipe"):
                st.session_state.db["recipes"][dish] = recipe_map
                st.success("Recipe Saved!")

# --- 5. SALE ENTRY ---
elif menu == "Sale Entry":
    st.title(f"🎯 Sale Entry: {selected_outlet}")
    if not db["recipes"]: st.warning("Add Recipes first!")
    else:
        dish = st.selectbox("Product", list(db["recipes"].keys()))
        rev = st.number_input("Sale Price (₹)", min_value=0)
        sale_date = st.date_input("Date of Sale", datetime.now())
        
        if st.button("Confirm Sale"):
            recipe = db["recipes"][dish]
            cost = 0
            # Logic for cost and stock deduction
            for item, req in recipe.items():
                row = outlet_inv[outlet_inv["Item"] == item]
                if not row.empty:
                    u_cost = row["Total_Cost"].values[0] / max(1, row["Qty"].values[0])
                    cost += (u_cost * req)
                    st.session_state.db["inventory"].loc[(db["inventory"]["Outlet"]==selected_outlet)&(db["inventory"]["Item"]==item), "Qty"] -= req
            
            new_s = pd.DataFrame([{"Date": pd.to_datetime(sale_date), "Outlet": selected_outlet, "Dish": dish, "Revenue": rev, "Cost": round(cost,2), "Profit": rev-cost}])
            st.session_state.db["sales"] = pd.concat([db["sales"], new_s], ignore_index=True)
            st.balloons()

# --- 6. DASHBOARD (Visuals & Monthly/Yearly) ---
elif menu == "Dashboard":
    st.title(f"📊 Analytics: {selected_outlet}")
    df = db["sales"][db["sales"]["Outlet"] == selected_outlet].copy()
    
    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])
        view = st.radio("View Level", ["Daily", "Monthly", "Yearly"], horizontal=True)
        
        if view == "Monthly":
            df['DisplayDate'] = df['Date'].dt.strftime('%Y-%m')
        elif view == "Yearly":
            df['DisplayDate'] = df['Date'].dt.strftime('%Y')
        else:
            df['DisplayDate'] = df['Date'].dt.date

        stats = df.groupby('DisplayDate').agg({'Revenue':'sum', 'Profit':'sum'}).reset_index()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Revenue", f"₹{stats['Revenue'].sum()}")
        c2.metric("Total Profit", f"₹{stats['Profit'].sum()}")
        c3.metric("Avg Profit/Period", f"₹{round(stats['Profit'].mean(),2)}")

        st.plotly_chart(px.bar(stats, x='DisplayDate', y=['Revenue', 'Profit'], barmode='group', title="Financial Growth"))
        st.write("### Inventory Health")
        st.dataframe(outlet_inv)
    else:
        st.info("No sales data yet. Start selling!")
