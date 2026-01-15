import streamlit as st
import pandas as pd

# --- APP CONFIG ---
st.set_page_config(page_title="Cloud K", page_icon="☁️", layout="wide")

# --- INITIALIZING DATA ---
# This part makes the app "remember" your changes while you use it
if 'outlets' not in st.session_state:
    st.session_state.outlets = {
        "The Home Plate": {"revenue": 0, "expenses": 0, "stock": 100},
        "No Cap Burgers": {"revenue": 0, "expenses": 0, "stock": 100},
        "Pocket Pizzaz": {"revenue": 0, "expenses": 0, "stock": 100},
        "Witx Sandwitx": {"revenue": 0, "expenses": 0, "stock": 100},
        "Hello Momos": {"revenue": 0, "expenses": 0, "stock": 100}
    }

# --- SIDEBAR ---
st.sidebar.title("☁️ Cloud K Management")
selected_outlet = st.sidebar.selectbox("Select Outlet", list(st.session_state.outlets.keys()))
menu = st.sidebar.radio("Go To", ["Live Dashboard", "Manage Inventory", "Log Sales & Expenses"])

# --- DATA SHORTCUTS ---
data = st.session_state.outlets[selected_outlet]

# --- 1. LIVE DASHBOARD (Calculates automatically) ---
if menu == "Live Dashboard":
    st.title(f"📊 {selected_outlet} Overview")
    
    # Automatic Math
    profit = data['revenue'] - data['expenses']
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Revenue", f"₹{data['revenue']}")
    col2.metric("Total Expenses", f"₹{data['expenses']}")
    col3.metric("Net Profit/Loss", f"₹{profit}", delta=profit)

    st.progress(max(0, min(data['stock']/100, 1.0)), text=f"Inventory Level: {data['stock']}%")

# --- 2. MANAGE INVENTORY ---
elif menu == "Manage Inventory":
    st.title("📦 Inventory Control")
    st.write(f"Current Stock for {selected_outlet}: **{data['stock']} units**")
    
    add_stock = st.number_input("Refill Stock (Units)", min_value=0)
    if st.button("Update Stock"):
        st.session_state.outlets[selected_outlet]['stock'] += add_stock
        st.success("Inventory updated!")
        st.rerun()

# --- 3. LOG SALES & EXPENSES ---
elif menu == "Log Sales & Expenses":
    st.title("📝 Data Entry")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Add Sale")
        sale_amt = st.number_input("Sale Amount (₹)", min_value=0)
        stock_used = st.number_input("Stock Units Used", min_value=0)
        if st.button("Save Sale"):
            st.session_state.outlets[selected_outlet]['revenue'] += sale_amt
            st.session_state.outlets[selected_outlet]['stock'] -= stock_used
            st.success("Sale Recorded!")
            st.rerun()
            
    with col2:
        st.subheader("Add Expense")
        exp_amt = st.number_input("Expense (Rent/Salary/Raw Materials) (₹)", min_value=0)
        if st.button("Save Expense"):
            st.session_state.outlets[selected_outlet]['expenses'] += exp_amt
            st.success("Expense Recorded!")
            st.rerun()
