import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- DATABASE SETUP ---
# This creates a little notebook where the app writes down your sales.
conn = sqlite3.connect('khushi_kitchen.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS sales 
             (customer TEXT, item TEXT, qty INTEGER, total REAL, date TEXT)''')
conn.commit()

# --- APP INTERFACE ---
st.set_page_config(page_title="Khushi Kitchen App", page_icon="🍳")

st.title("🍳 Khushi Breakfast Club")
st.subheader("Cloud Kitchen Manager")

# 1. NEW ORDER SECTION
st.markdown("### 📝 Take New Order")
menu = {
    "Masala Omelette": 80,
    "Aloo Paratha": 60,
    "Paneer Toast": 90,
    "Chai": 20,
    "Coffee": 30
}

col1, col2, col3 = st.columns(3)
with col1:
    cust_name = st.text_input("Customer Name")
with col2:
    selected_item = st.selectbox("Select Breakfast", list(menu.keys()))
with col3:
    quantity = st.number_input("How many?", min_value=1, value=1)

if st.button("🔥 Place Order & Save"):
    if cust_name:
        price = menu[selected_item] * quantity
        today = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Save to our notebook (Database)
        c.execute("INSERT INTO sales VALUES (?, ?, ?, ?, ?)", 
                  (cust_name, selected_item, quantity, price, today))
        conn.commit()
        st.success(f"Done! Saved ₹{price} for {cust_name}")
    else:
        st.error("Please type the customer's name!")

# 2. REVENUE TRACKER SECTION
st.markdown("---")
st.markdown("### 📊 Today's Earnings")

# Pull data from the notebook to show on screen
df = pd.read_sql_query("SELECT * FROM sales", conn)

if not df.empty:
    total_money = df['total'].sum()
    st.metric("Total Revenue", f"₹{total_money}")
    st.dataframe(df) # Shows the list of all orders
else:
    st.write("No orders yet today. Let's get cooking!")
