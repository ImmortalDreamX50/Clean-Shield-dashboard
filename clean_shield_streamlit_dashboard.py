import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta
import plotly.graph_objs as go
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import os
import json

# --- Page Configuration ---
st.set_page_config(page_title="Clean Shield Dashboard", layout="wide")

# --- Auto-refresh ---
refresh_interval = st.sidebar.selectbox(
    "🔄 Auto-refresh interval",
    options=[10000, 60000, 300000, 600000],
    format_func=lambda x: f"{x//1000} seconds" if x < 60000 else f"{x//60000} minutes",
    index=2
)
st_autorefresh(interval=refresh_interval, key="refresh")

# --- Custom CSS Styling ---
st.markdown("""
    <style>
    html, body, [class*="css"] {
        background-color: #121926;
        color: #ffffff;
        font-family: 'Segoe UI', sans-serif;
    }
    .card {
        background-color: #1e293b;
        padding: 1.2rem;
        border-radius: 12px;
        box-shadow: 0 0 10px #00000040;
    }
    .metric-value { font-size: 40px; font-weight: bold; }
    .risk-high { color: red; font-size: 32px; font-weight: bold; }
    .risk-moderate { color: orange; font-size: 28px; font-weight: bold; }
    .risk-low { color: lightgreen; font-size: 28px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- API & Config ---
API_KEY = "3adadd6215176f2e11467321ee0784ad"

# Sidebar: location input
st.sidebar.header("🌍 Location Settings")
city_name = st.sidebar.text_input("Enter city name", "Durban")

# Geocode API to get lat/lon
geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name},ZA&limit=1&appid={API_KEY}"
geo_data = requests.get(geo_url).json()

if geo_data:
    LAT, LON = geo_data[0]['lat'], geo_data[0]['lon']
else:
    st.error("⚠️ Location not found in South Africa. Please enter a valid city.")
    st.stop()

# ✅ IoT Data Upload Endpoint
if "data" not in st.session_state:
    st.session_state["data"] = []

def add_sensor_data():
    try:
        params = st.query_params
        if "payload" in params:
            payload = json.loads(params["payload"][0])
            st.session_state["data"].append(payload)
    except Exception as e:
        st.write("Upload error:", e)

add_sensor_data()

@st.cache_data(ttl=600)
def fetch_data(url):
    try:
        r = requests.get(url)
        r.raise_for_status()
        return r.json()
    except:
        return None

weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={API_KEY}&units=metric"
pollution_url = f"https://api.openweathermap.org/data/2.5/air_pollution?lat={LAT}&lon={LON}&appid={API_KEY}"

weather_data = fetch_data(weather_url)
pollution_data = fetch_data(pollution_url)

if not weather_data or not pollution_data:
    st.error("❌ Failed to load weather/pollution data.")
    st.stop()

# --- Extract Values ---
temp = weather_data['main']['temp']
humidity = weather_data['main']['humidity']
wind = weather_data['wind']['speed'] * 3.6
pm25 = pollution_data['list'][0]['components']['pm2_5']
dt = datetime.fromtimestamp(pollution_data['list'][0]['dt'])

# --- Determine Risk ---
risk = "Low"
if pm25 > 25:
    risk = "High"
elif pm25 > 10:
    risk = "Moderate"

# --- Save data to CSV (auto-logging) ---
log_file = "sensor_log.csv"
new_entry = pd.DataFrame([{
    "timestamp": dt,
    "city": city_name,
    "lat": LAT,
    "lon": LON,
    "temp_C": temp,
    "humidity_%": humidity,
    "wind_kmh": wind,
    "pm25_µg/m³": pm25,
    "risk": risk
}])

if os.path.exists(log_file):
    df_log = pd.read_csv(log_file)
    df_log = pd.concat([df_log, new_entry], ignore_index=True)
else:
    df_log = new_entry

df_log.to_csv(log_file, index=False)

# --- Historical PM2.5 Data ---
def fetch_historical_pm25(lat, lon, start_date, end_date, api_key):
    historical_data = []
    current_date = start_date
    while current_date <= end_date:
        timestamp = int(current_date.timestamp())
        url = f"http://api.openweathermap.org/data/2.5/air_pollution/history?lat={lat}&lon={lon}&start={timestamp}&end={timestamp+3600}&appid={api_key}"
        data = fetch_data(url)
        if data:
            pm25_value = data['list'][0]['components']['pm2_5'] if 'list' in data else None
            if pm25_value is not None:
                historical_data.append((current_date, pm25_value))
        current_date += timedelta(days=1)
    return historical_data

# Fetch historical PM2.5 data for past week
end_date = datetime.now()
start_date = end_date - timedelta(days=7)
historical_pm25 = fetch_historical_pm25(LAT, LON, start_date, end_date, API_KEY)

# Prepare data for plotting
dates = [entry[0] for entry in historical_pm25]
pm25_values = [entry[1] for entry in historical_pm25]

# 📍 Map
m = folium.Map(location=[LAT, LON], zoom_start=7, tiles="CartoDB dark_matter")
folium.CircleMarker(
    location=[LAT, LON],
    radius=10,
    color="red" if risk == "High" else "orange" if risk == "Moderate" else "green",
    fill=True, fill_opacity=0.7,
    popup=f"{risk} Risk Zone"
).add_to(m)

# --- Dashboard Layout ---
st.markdown("## 🌍 CLEAN SHIELD")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### BLACK CARBON")
    st.markdown(f"<div class='metric-value'>{pm25:.1f} µg/m³</div>", unsafe_allow_html=True)
    st.progress(min(int(pm25), 50), text="Moderate" if pm25 <= 25 else "High")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### GLACIER MELT RISK")
    if risk == "High":
        st.markdown("<div class='risk-high'>High</div>", unsafe_allow_html=True)
        st.markdown("⚠️ WARNING")
    elif risk == "Moderate":
        st.markdown("<div class='risk-moderate'>Moderate</div>", unsafe_allow_html=True)
        st.markdown("⚠️ Be cautious")
    else:
        st.markdown("<div class='risk-low'>Low</div>", unsafe_allow_html=True)
        st.markdown("✅ Stable")
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### WEATHER")
    st.markdown(f"<div class='metric-value'>{temp:.1f}°C</div>", unsafe_allow_html=True)
    st.markdown(f"💧 {humidity}%   🌬 {wind:.1f} km/h")
    st.markdown('</div>', unsafe_allow_html=True)

# --- Trend Graph ---
st.markdown("### 📊 Black Carbon Concentration (µg/m³)")

fig = go.Figure()
fig.add_trace(go.Scatter(x=dates, y=pm25_values, mode='lines+markers', line=dict(color="orange", width=3)))
fig.update_layout(
    plot_bgcolor='#1e293b',
    paper_bgcolor='#121926',
    font_color='white',
    xaxis=dict(title='Date', tickformat='%b %d', color='white'),
    yaxis=dict(title='PM2.5 (µg/m³)', color='white'),
    height=300
)
st.plotly_chart(fig, use_container_width=True)

# --- Risk Zone Map and Alerts ---
col4, col5 = st.columns(2)
with col4:
    st.subheader("📍 RISK ZONE MAP")
    st_folium(m, width=700, height=400)

with col5:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🚨 ALERTS")
    st.markdown(f"🔴 **{risk} glacier melt risk** — {dt.strftime('%I:%M %p')}")
    if pm25 > 10:
        st.markdown(f"🟠 Moderate black carbon levels — {dt.strftime('%b %d, %I:%M %p')}")
    st.markdown('</div>', unsafe_allow_html=True)


# --- Show log preview ---
st.markdown("### 📑 Logged Data (last 5 entries)")
st.dataframe(df_log.tail(5))


# =============================
# ✅ SENSOR DATA SECTION (NEW)
# =============================
st.markdown("---")
st.markdown("## 🧪 IoT SENSOR DATA")

if "data" not in st.session_state or len(st.session_state["data"]) == 0:
    st.info("Waiting for IoT sensor data... (Connect Raspberry Pi)")
else:
    latest = st.session_state["data"][-1]

    colA, colB, colC = st.columns(3)

    with colA:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### MQ-7 (CO)")
        st.markdown(f"<div class='metric-value'>{latest.get('mq7', 'N/A')}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with colB:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### MQ-6 (LPG)")
        st.markdown(f"<div class='metric-value'>{latest.get('mq6', 'N/A')}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with colC:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### MQ-136 (H₂S)")
        st.markdown(f"<div class='metric-value'>{latest.get('mq136', 'N/A')}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Temperature & Humidity
    if latest.get("temp") is not None or latest.get("humidity") is not None:
        st.markdown("### 🌡️ Environmental Data (Sense HAT)")
        st.write(f"**Temperature:** {latest.get('temp', 'N/A')} °C")
        st.write(f"**Humidity:** {latest.get('humidity', 'N/A')} %")

    # Soil Moisture
    if latest.get("soil") is not None:
        st.markdown("### 🌱 Soil Moisture")
        st.write(f"Moisture Level: {latest.get('soil')}")

    # Timestamp
    if latest.get("timestamp"):
        st.markdown(f"📌 Last Update: **{latest.get('timestamp')}**")
    #KYO15
    if latest.get("temp_kyo15") is not None:
    st.markdown("### 🌡️ KYO15 Temperature & Humidity")
    st.write(f"Temperature: {latest.get('temp_kyo15')} °C")
    st.write(f"Humidity: {latest.get('humidity_kyo15')} %")

