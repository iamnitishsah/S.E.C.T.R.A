import numpy as np
import pandas as pd
import streamlit as st

# Page configuration
st.set_page_config(page_title="Streamlit Demo App", layout="wide")

st.title("Interactive Sales Dashboard Demo")
st.write("Adjust the controls in the sidebar to update the metrics and charts.")

# --- Sidebar Controls ---
st.sidebar.header("Filter Options")
num_days = st.sidebar.slider("Number of days", min_value=7, max_value=90, value=30)
category = st.sidebar.selectbox("Select Category", ["Electronics", "Clothing", "Home & Garden"])
show_raw_data = st.sidebar.checkbox("Show raw data table", value=True)

# --- Generate Sample Data ---
np.random.seed(42)
dates = pd.date_range(end=pd.Timestamp.today(), periods=num_days)
base_sales = {"Electronics": 500, "Clothing": 300, "Home & Garden": 200}[category]

df = pd.DataFrame({
    "Date": dates,
    "Revenue ($)": np.random.randint(base_sales - 100, base_sales + 250, size=num_days),
    "Orders": np.random.randint(10, 60, size=num_days),
}).set_index("Date")

# --- Key Metrics ---
col1, col2, col3 = st.columns(3)
col1.metric("Total Revenue", f"${df['Revenue ($)'].sum():,}")
col2.metric("Total Orders", f"{df['Orders'].sum():,}")
col3.metric("Avg Daily Revenue", f"${df['Revenue ($)'].mean():.2f}")

st.divider()

# --- Interactive Chart ---
st.subheader(f"{category} Revenue Trend")
st.line_chart(df["Revenue ($)"])

# --- Conditional Raw Data View ---
if show_raw_data:
    st.subheader("Raw Data")
    st.dataframe(df, use_container_width=True)
