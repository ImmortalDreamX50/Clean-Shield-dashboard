import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta
import plotly.graph_objs as go

# --- Page Configuration ---
st.set_page_config(page_title="Clean Shield Dashboard", layout="wide")

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
    .card h3 {
        margin: 0;
        font-size: 24px;
        font-weight: 600;
    }
    .metric-value {
        font-size: 40px;
        font-weight: bold;
    }
    .risk-high {
        color: red;
        font-size: 32px;
        font-weight: bold;
    }
    .risk-moderate {
        color: orange;
        font-size: 28px;
        font-weight: bold;
    }
    .risk-low {
        color: lightgreen;
        font-size: 28px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- API & Config ---
API_KEY = "3adadd6215176f2e11467321ee0784ad"
LAT, LON = -29.9, 30.9

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
    st.error("Failed to load data.")
    st.stop()

# --- Extract Values ---
temp = weather_data['main']['temp']
humidity = weather_data['main']['humidity']
wind = weather_data['wind']['speed'] * 3.6  # m/s to km/h
pm25 = pollution_data['list'][0]['components']['pm2_5']
dt = datetime.fromtimestamp(pollution_data['list'][0]['dt'])

# --- Determine Risk ---
risk = "Low"
if pm25 > 25:
    risk = "High"
elif pm25 > 10:
    risk = "Moderate"

# --- Simulated PM2.5 Data ---
dates = [datetime.now() - timedelta(days=i) for i in reversed(range(10))]
bc_values = [max(5, pm25 + (i - 5)) for i in range(10)]

# 📍 Create a base map centered on your location
m = folium.Map(location=[-29.9, 30.9], zoom_start=7, tiles="CartoDB dark_matter")

# 🔴 Add High Risk Zone
folium.CircleMarker(
    location=[-29.9, 30.9],
    radius=10,
    color="red",
    fill=True,
    fill_opacity=0.7,
    popup="High Risk Zone (Black Carbon > 25 µg/m³)"
).add_to(m)

# 🟠 Add Moderate Risk Zone
folium.CircleMarker(
    location=[-30.2, 30.7],
    radius=10,
    color="orange",
    fill=True,
    fill_opacity=0.6,
    popup="Moderate Risk Zone (Black Carbon 10–25 µg/m³)"
).add_to(m)

# 🟢 Add Low Risk Zone
folium.CircleMarker(
    location=[-30.5, 30.5],
    radius=10,
    color="green",
    fill=True,
    fill_opacity=0.5,
    popup="Low Risk Zone (Black Carbon < 10 µg/m³)"
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
        st.markdown(f"<div class='risk-high'>High</div>", unsafe_allow_html=True)
        st.markdown("⚠️ WARNING")
    elif risk == "Moderate":
        st.markdown(f"<div class='risk-moderate'>Moderate</div>", unsafe_allow_html=True)
        st.markdown("⚠️ Be cautious")
    else:
        st.markdown(f"<div class='risk-low'>Low</div>", unsafe_allow_html=True)
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
fig.add_trace(go.Scatter(x=dates, y=bc_values, mode='lines+markers', line=dict(color="orange", width=3)))
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
# 🗺️ Display it in Streamlit
with col4:
    st.subheader("📍 RISK ZONE MAP")
    st_folium(m, width=700, height=400)


with col5:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🚨 ALERTS")
    st.markdown(f"🔴 **High glacier melt risk** — {dt.strftime('%I:%M %p')}")
    if pm25 > 10:
        st.markdown(f"🟠 Moderate black carbon levels — {dt.strftime('%b %d, %I:%M %p')}")
    st.markdown('</div>', unsafe_allow_html=True)
