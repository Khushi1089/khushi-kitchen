import streamlit as st
import pandas as pd

# --- APP CONFIG ---
st.set_page_config(page_title="Cloud K - AutoCalc", page_icon="☁️", layout="wide")

# --- INITIALIZE DATABASE ---
if 'db' not in st.session_state:
    st.session_state.db = {
        "inventory": pd.DataFrame(columns=["Item", "Qty", "Unit", "Price"]),
        "recipes": {},  # Format: {"Pizza": {"Flour": 0.2, "Box": 1}}
        "sales": pd.DataFrame(columns=["Product", "Revenue", "Cost", "Profit"])
    }

db = st.session_state.db

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("☁️ Cloud K")
menu = st.sidebar.radio("Navigation", ["Dashboard", "Stock Room", "Recipe Master", "Quick Sale Entry"])

# --- 1. STOCK ROOM (Fill your ingredients first) ---
if menu == "Stock Room":
    st.title("📦 Inventory & Packaging Stock")
    with st.form("stock_form"):
        col1, col2, col3, col4 = st.columns(4)
        name = col1.text_input("Item Name")
        q = col2.number_input("Quantity", min_value=0.0)
        u = col3.selectbox("Unit", ["Kg", "Grams", "Units", "Liters"])
        p = col4.number_input("Purchase Price (Total)", min_value=0.0)
        if st.form_submit_button("Add Stock"):
            new_item = pd.DataFrame([{"Item": name, "Qty": q, "Unit": u, "Price": p}])
            st.session_state.db["inventory"] = pd.concat([db["inventory"], new_item], ignore_index=True)
            st.rerun()
    st.dataframe(db["inventory"], use_container_width=True)

# --- 2. RECIPE MASTER (Define what 1 dish uses) ---
elif menu == "Recipe Master":
    st.title("👨‍🍳 Recipe & Packaging Master")
    st.write("Define how much stock is used for **1 unit** of a dish.")
    
    dish_name = st.text_input("Dish Name (e.g., Margherita Pizza)")
    
    if not db["inventory"].empty:
        items = st.multiselect("Select Ingredients/Packaging for this dish", db["inventory"]["Item"].unique())
        recipe_details = {}
        
        cols = st.columns(len(items) if items else 1)
        for i, item in enumerate(items):
            unit = db["inventory"][db["inventory"]["Item"] == item]["Unit"].values[0]
            recipe_details[item] = cols[i].number_input(f"Qty of {item} ({unit})", min_value=0.01, step=0.01)
        
        if st.button("Save Recipe"):
            st.session_state.db["recipes"][dish_name] = recipe_details
            st.success(f"Recipe for {dish_name} saved!")
    else:
        st.warning("Please add items to the Stock Room first!")

# --- 3. QUICK SALE ENTRY (The "One-Click" Sale) ---
elif menu == "Quick Sale Entry":
    st.title("🎯 One-Click Sale Entry")
    if not db["recipes"]:
        st.warning("Define your Recipes first!")
    else:
        dish_to_sell = st.selectbox("What did you sell?", list(db["recipes"].keys()))
        price_sold = st.number_input("Selling Price (₹)", min_value=0)
        
        if st.button("Confirm Sale"):
            recipe = db["recipes"][dish_to_sell]
            can_sell = True
            
            # Check if we have enough stock
            for item, used_qty in recipe.items():
                current_qty = db["inventory"].loc[db["inventory"]["Item"] == item, "Qty"].values[0]
                if current_qty < used_qty:
                    st.error(f"Not enough {item}! Need {used_qty}, have {current_qty}")
                    can_sell = False
            
            if can_sell:
                # 1. Subtract Stock
                for item, used_qty in recipe.items():
                    st.session_state.db["inventory"].loc[db["inventory"]["Item"] == item, "Qty"] -= used_qty
                
                # 2. Log Sale
                new_sale = pd.DataFrame([{"Product": dish_to_sell, "Revenue": price_sold}])
                st.session_state.db["sales"] = pd.concat([db["sales"], new_sale], ignore_index=True)
                st.balloons()
                st.success(f"Sold 1 {dish_to_sell}! Inventory updated automatically.")

# --- 4. DASHBOARD ---
elif menu == "Dashboard":
    st.title("📊 Cloud K Live Analytics")
    rev = db["sales"]["Revenue"].sum()
    st.metric("Total Revenue", f"₹{rev}")
    
    st.subheader("Inventory Status")
    st.dataframe(db["inventory"])
