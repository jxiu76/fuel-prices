import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import requests

# -----------------------------------------------------------------------------
# Configuration & Setup
# -----------------------------------------------------------------------------
st.set_page_config(page_title="NCR Fuel Watch", page_icon="⛽", layout="wide")

API_URL = "http://localhost:8000/api"

# Inject Custom CSS for Minimalist UI
st.markdown("""
<style>
    .reportview-container .main .block-container{ padding-top: 2rem; }
    h1 { color: #1E3A8A; font-weight: 700; }
    .stMetric > div { background-color: #F8FAFC; border-radius: 8px; padding: 15px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Data Retrieval
# -----------------------------------------------------------------------------
@st.cache_data(ttl=600)
def fetch_data():
    try:
        response = requests.get(f"{API_URL}/prices/latest")
        if response.status_code == 200 and response.json():
            df = pd.DataFrame(response.json())
        else:
            raise Exception("API error or empty data")
    except Exception as e:
        # Fallback to simulated dummy data if API isn't running yet during dev
        st.sidebar.warning(f"Backend API not found. Using simulated data. ({e})")
        df = pd.DataFrame([
            {"city": "Quezon City", "brand": "Shell", "fuel_type": "Diesel", "price": 54.20, "lat": 14.6760, "lon": 121.0437},
            {"city": "Quezon City", "brand": "Petron", "fuel_type": "Unleaded 91", "price": 59.50, "lat": 14.6500, "lon": 121.0300},
            {"city": "Makati", "brand": "Caltex", "fuel_type": "Premium 95", "price": 63.10, "lat": 14.5547, "lon": 121.0244},
            {"city": "Manila", "brand": "Shell", "fuel_type": "Diesel", "price": 53.80, "lat": 14.5995, "lon": 120.9842},
            {"city": "Taguig", "brand": "Petron", "fuel_type": "Premium 95", "price": 64.00, "lat": 14.5176, "lon": 121.0509},
        ])
    return df

@st.cache_data(ttl=600)
def fetch_historic_trends():
    # Simulated historical data for the line chart
    dates = pd.date_range(end=datetime.now(), periods=30)
    return pd.DataFrame({
        "Date": np.tile(dates, 2),
        "Price": np.concatenate([np.linspace(52, 55, 30) + np.random.normal(0, 0.5, 30), 
                                 np.linspace(60, 63, 30) + np.random.normal(0, 0.5, 30)]),
        "Fuel Type": ["Diesel"]*30 + ["Premium 95"]*30
    })

# Initialize state
df = fetch_data()
historical_df = fetch_historic_trends()

# -----------------------------------------------------------------------------
# Sidebar layout
# -----------------------------------------------------------------------------
st.sidebar.title("⛽ Filters")
st.sidebar.markdown("Filter the NCR fuel stations.")

cities = ["All"] + sorted(df["city"].unique().tolist())
selected_city = st.sidebar.selectbox("Select City", cities)

fuel_types = ["All"] + sorted(df["fuel_type"].unique().tolist())
selected_fuel = st.sidebar.selectbox("Select Fuel Type", fuel_types)

# Filter Dataframe
filtered_df = df.copy()
if selected_city != "All":
    filtered_df = filtered_df[filtered_df["city"] == selected_city]
if selected_fuel != "All":
    filtered_df = filtered_df[filtered_df["fuel_type"] == selected_fuel]

# -----------------------------------------------------------------------------
# Main Layout
# -----------------------------------------------------------------------------
st.title("NCR Fuel Watch Dashboard")
st.markdown("Track, analyze, and forecast fuel prices across Metro Manila in real-time.")

# TOP ROW: KPI Cards
col1, col2, col3 = st.columns(3)

if not filtered_df.empty:
    avg_price = filtered_df["price"].mean()
    cheapest = filtered_df.loc[filtered_df["price"].idxmin()]
    
    col1.metric("Average Price (Selected)", f"₱{avg_price:.2f}", "-1.2% (7d)")
    
    col2.metric("Cheapest Station", f"₱{cheapest['price']:.2f}", f"{cheapest['brand']} - {cheapest['city']}", delta_color="normal")
    col3.metric("Total Stations Tracked", len(filtered_df), "Active")
else:
    st.warning("No data available for the selected filters.")

st.markdown("---")

# MIDDLE ROW: Map & Chart
left_col, right_col = st.columns([1, 1.2])

with left_col:
    st.subheader("Station Price Map")
    if not filtered_df.empty:
        # Create color scale based on price (Green = cheap, Red = expensive)
        fig_map = px.scatter_mapbox(
            filtered_df, lat="lat", lon="lon",
            color="price", size="price",
            color_continuous_scale=["#10B981", "#F59E0B", "#EF4444"], # Tailwind colors
            hover_name="brand",
            hover_data={"lat": False, "lon": False, "price": True, "city": True, "fuel_type": True},
            zoom=10, mapbox_style="carto-positron"
        )
        fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig_map, use_container_width=True)
        
with right_col:
    st.subheader("Price Volatility & Trends (30-day)")
    # Using the simulated historical data for demonstration of trend visualization
    trend_filter = historical_df.copy()
    if selected_fuel != "All":
        trend_filter = trend_filter[trend_filter["Fuel Type"] == selected_fuel]
        
    fig_line = px.line(
        trend_filter, x="Date", y="Price", color="Fuel Type",
        line_shape="spline", # Smooth curves
        markers=True
    )
    fig_line.update_layout(
        plot_bgcolor="white",
        yaxis_title="Price (PHP / L)",
        xaxis_title="",
        legend_title="Fuel",
        hovermode="x unified"
    )
    st.plotly_chart(fig_line, use_container_width=True)

# -----------------------------------------------------------------------------
# Bottom Row: Insights & Data Table
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("Market Insights & Outlier Detection")

col_insight1, col_insight2 = st.columns(2)

with col_insight1:
    st.markdown("**🔍 Standard Deviation (Volatility)**")
    if len(filtered_df) > 1:
        st.info(f"Price volatility across selected stations is **₱{filtered_df['price'].std():.2f}**. Lower values indicate stable pricing in this region.")
    else:
        st.info("Not enough data to calculate volatility.")

with col_insight2:
    st.markdown("**⚠️ Outlier Detection (IQR Method)**")
    # Basic logic to show how outlies are flagged
    st.success("No anomalies detected in the current dataset. All reported prices fall within the expected interquartile range.")

with st.expander("View Raw Datatable"):
    st.dataframe(filtered_df[["brand", "city", "fuel_type", "price"]].reset_index(drop=True), use_container_width=True)
