import streamlit as st
import pandas as pd

# --- APP CONFIG ---
st.set_page_config(page_title="Cloud K", page_icon="☁️", layout="wide")

# --- CUSTOM CSS FOR THE "BURGER BHAU" LOOK ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .sidebar .sidebar-content { background-image: linear-gradient(#e66465, #9198e5); }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("☁️ Cloud K")
outlet = st.sidebar.selectbox("Select Outlet", ["Andheri West", "Bandra East", "Add New Outlet+"])
menu = st.sidebar.radio("Navigation", ["Dashboard", "Inventory", "Sales & Revenue", "Profit & Loss"])

# --- MOCK DATA (In a real app, this saves to a database) ---
if 'inventory' not in st.session_state:
    st.session_state.inventory = pd.DataFrame([
        {"Item": "Chicken Patties", "Stock": 800, "Status": "Healthy"},
        {"Item": "Red Onions", "Stock": 150, "Status": "Low Stock"}
    ])

# --- 1. DASHBOARD ---
if menu == "Dashboard":
    st.title(f"📊 {outlet} Dashboard")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Revenue", "₹341,000", "+12.5%")
    col2.metric("Total Orders", "940", "+5.2%")
    col3.metric("Low Stock Items", "2", "-2")
    col4.metric("Active Outlets", "5")

    st.markdown("### Revenue Trends")
    chart_data = pd.DataFrame({'Sales': [40000, 50000, 30000, 70000, 60000]}, index=['Mon', 'Tue', 'Wed', 'Thu', 'Fri'])
    st.bar_chart(chart_data)

# --- 2. INVENTORY ---
elif menu == "Inventory":
    st.title("📦 Inventory Management")
    
    # Add Item Section
    with st.expander("➕ Add New Stock Item"):
        new_item = st.text_input("Item Name")
        qty = st.number_input("Quantity", min_value=0)
        if st.button("Update Inventory"):
            st.success(f"Added {qty} {new_item} to {outlet}")

    st.table(st.session_state.inventory)

# --- 3. SALES & REVENUE ---
elif menu == "Sales & Revenue":
    st.title("💰 Sales Tracker")
    c1, c2 = st.columns(2)
    with c1:
        item_sold = st.selectbox("Item Sold", ["Burger", "Pizza", "Chai"])
        amt = st.number_input("Sale Amount (₹)")
    with c2:
        date = st.date_input("Transaction Date")
        if st.button("Log Sale"):
            st.success(f"Sale of ₹{amt} recorded for {outlet}")

# --- 4. PROFIT & LOSS ---
elif menu == "Profit & Loss":
    st.title("📈 Profit & Loss Statement")
    revenue = 341000
    expenses = st.number_input("Total Expenses (Rent, Salary, Raw Materials)", value=200000)
    profit = revenue - expenses
    
    st.metric("Net Profit", f"₹{profit}", delta_color="normal")
    
    if profit > 0:
        st.balloons()
        st.write("Excellent! Your outlet is in profit.")
    else:
        st.error("Loss detected. Check your inventory wastage!")
