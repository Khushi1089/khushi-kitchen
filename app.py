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

# --- 1. UNIT CONVERTER ---
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
            st.success(f"Total Pieces: {int((val * 1000) / weight_of_one)}")

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
            if rem_out in st.session_state.db["outlets"]:
                st.session_state.db["outlets"].remove(rem_out)
                st.rerun()

# --- SELECT ACTIVE OUTLET ---
if menu not in ["Outlet Settings", "Unit Converter"]:
    selected_outlet = st.sidebar.selectbox("Active Outlet", db["outlets"])
    outlet_inv = db["inventory"][db["inventory"]["Outlet"] == selected_outlet]

# --- 3. STOCK ROOM ---
if menu == "Stock Room":
    st.title(f"📦 {selected_outlet} Inventory")
    with st.expander("➕ Add Stock (Ingredients/Packaging)"):
        c1, c2, c3, c4 = st.columns(4)
        name = c1.text_input("Item Name")
        qty = c2.number_input("Qty", min_value=0.0)
        unit = c3.selectbox("Unit", ["Units/Pieces", "Kg", "Liters"])
        price = c4.number_input("Total Purchase Price (₹)", min_value=0.0)
        w_per_p = st.number_input("Weight per Piece (Grams) - Optional", min_value=0.0)
        
        if st.button("Save Stock"):
            new_row = {"Outlet": selected_outlet, "Item": name, "Qty": qty, "Unit": unit, "Total_Cost": price, "Weight_Per_Piece": w_per_p}
            st.session_state.db["inventory"] = pd.concat([db["inventory"], pd.DataFrame([new_row])], ignore_index=True)
            st.rerun()
    st.dataframe(outlet_inv, use_container_width=True)

# --- 4. RECIPE MASTER ---
elif menu == "Recipe Master":
    st.title("👨‍🍳 Chef Recipe Master")
    dish = st.text_input("Dish Name (e.g., Veg Burger)")
    all_items = db["inventory"]["Item"].unique()
    if len(all_items) > 0:
        ingredients = st.multiselect("Select Ingredients/Packaging for 1 Unit", all_items)
        recipe_map = {}
        if ingredients:
            cols = st.columns(len(ingredients))
            for i, item in enumerate(ingredients):
                recipe_map[item] = cols[i].number_input(f"Qty of {item}", min_value=0.001, format="%.3f")
            if st.button("Save Recipe"):
                st.session_state.db["recipes"][dish] = recipe_map
                st.success(f"Recipe for {dish} Saved!")
    else:
        st.warning("Add items to Stock Room first!")

# --- 5. SALE ENTRY ---
elif menu == "Sale Entry":
    st.title(f"🎯 Sale Entry: {selected_outlet}")
    if not db["recipes"]: st.warning("Define Recipes first!")
    else:
        dish = st.selectbox("Product", list(db["recipes"].keys()))
        rev = st.number_input("Sale Price (₹)", min_value=0)
        sale_date = st.date_input("Date of Sale", datetime.now())
        
        if st.button("Confirm Sale & Deduct Stock"):
            recipe = db["recipes"][dish]
            cost = 0
            can_sell = True
            
            # Stock Check
            for item, req in recipe.items():
                row = outlet_inv[outlet_inv["Item"] == item]
                if row.empty or row["Qty"].values[0] < req:
                    st.error(f"Insufficient stock for {item}")
                    can_sell = False
            
            if can_sell:
                for item, req in recipe.items():
                    row = outlet_inv[outlet_inv["Item"] == item]
                    u_cost = row["Total_Cost"].values[0] / max(1, row["Qty"].values[0])
                    cost += (u_cost * req)
                    st.session_state.db["inventory"].loc[(db["inventory"]["Outlet"]==selected_outlet)&(db["inventory"]["Item"]==item), "Qty"] -= req
                
                new_s = pd.DataFrame([{"Date": pd.to_datetime(sale_date), "Outlet": selected_outlet, "Dish": dish, "Revenue": rev, "Cost": round(cost,2), "Profit": rev-cost}])
                st.session_state.db["sales"] = pd.concat([db["sales"], new_s], ignore_index=True)
                st.balloons()
                st.success("Sale Recorded!")

# --- 6. DASHBOARD (Analytics & Graphs) ---
elif menu == "Dashboard":
    st.title(f"📊 {selected_outlet} Performance")
    df = db["sales"][db["sales"]["Outlet"] == selected_outlet].copy()
    
    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])
        view = st.radio("Group By", ["Daily", "Monthly", "Yearly"], horizontal=True)
        
        if view == "Monthly":
            df['DisplayDate'] = df['Date'].dt.strftime('%b %Y')
        elif view == "Yearly":
            df['DisplayDate'] = df['Date'].dt.strftime('%Y')
        else:
            df['DisplayDate'] = df['Date'].dt.date

        stats = df.groupby('DisplayDate').agg({'Revenue':'sum', 'Profit':'sum'}).reset_index()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Revenue", f"₹{df['Revenue'].sum()}")
        m2.metric("Total Profit", f"₹{round(df['Profit'].sum(), 2)}")
        m3.metric("Profit Margin", f"{round((df['Profit'].sum()/df['Revenue'].sum())*100, 1)}%" if df['Revenue'].sum() > 0 else "0%")

        fig = px.bar(stats, x='DisplayDate', y=['Revenue', 'Profit'], barmode='group', title=f"{view} Financials")
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Current Stock Levels")
        st.dataframe(outlet_inv)
    else:
        st.info("No sales data available. Log a sale to see analytics!")
