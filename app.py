import streamlit as st
import pandas as pd
import numpy as np
import json
import math
import requests
import datetime
import streamlit.components.v1 as components

# Configurazione della pagina
st.set_page_config(
    page_title="Mooring Analysis & Port Planner",
    page_icon="⚓",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 1. DATABASE BANCHINE DI DEFAULT & CARICAMENTO JSON
# -----------------------------------------------------------------------------
DEFAULT_BERTHS = {
    "Ensenada": {
        "lat": 31.8578,
        "lon": -116.6258,
        "berths": {
            "Cruise Pier North": {
                "heading": 210,
                "bollard_capacity_ton": 100,
                "bollard_spacing_m": 20,
                "max_draft_m": 10.0,
                "fender_type": "Cone Fender"
            },
            "Cruise Pier South": {
                "heading": 190,
                "bollard_capacity_ton": 100,
                "bollard_spacing_m": 20,
                "max_draft_m": 9.8,
                "fender_type": "Cone Fender"
            }
        }
    },
    "Puerto Vallarta": {
        "lat": 20.6534,
        "lon": -105.2404,
        "berths": {
            "Pier 1": {
                "heading": 180,
                "bollard_capacity_ton": 80,
                "bollard_spacing_m": 18,
                "max_draft_m": 9.5,
                "fender_type": "Cell Fender"
            },
            "Pier 2": {
                "heading": 180,
                "bollard_capacity_ton": 80,
                "bollard_spacing_m": 18,
                "max_draft_m": 9.0,
                "fender_type": "Cell Fender"
            },
            "Pier 3": {
                "heading": 180,
                "bollard_capacity_ton": 80,
                "bollard_spacing_m": 18,
                "max_draft_m": 9.2,
                "fender_type": "Cell Fender"
            }
        }
    },
    "Mazatlán": {
        "lat": 23.1983,
        "lon": -106.4214,
        "berths": {
            "Cruise Dock": {
                "heading": 340,
                "bollard_capacity_ton": 75,
                "bollard_spacing_m": 15,
                "max_draft_m": 9.2,
                "fender_type": "Arch Fender"
            }
        }
    },
    "La Paz (Pichilingue)": {
        "lat": 24.2713,
        "lon": -110.3235,
        "berths": {
            "Muelle T-Pichilingue": {
                "heading": 195,
                "bollard_capacity_ton": 80,
                "bollard_spacing_m": 15,
                "max_draft_m": 9.5,
                "fender_type": "Cell Fender"
            }
        }
    }
}

@st.cache_data
def load_berths_data():
    try:
        with open("berths.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return DEFAULT_BERTHS

berths_db = load_berths_data()

# -----------------------------------------------------------------------------
# 2. FUNZIONALITÀ DI CALCOLO E METEO
# -----------------------------------------------------------------------------
def fetch_weather_data(lat, lon, selected_date):
    """Recupera le previsioni orarie da Open-Meteo per il giorno selezionato."""
    date_str = selected_date.strftime("%Y-%m-%d")
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=kn&start_date={date_str}&end_date={date_str}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None

def calculate_mooring_forces(wind_speed_kt, wind_dir_deg, current_speed_kt, current_dir_deg, ship_heading_deg, A_front, A_side, A_wetted):
    """Calcolo semplificato delle forze del vento e della corrente in tonnellate (MEG4)."""
    V_w = wind_speed_kt * 0.514444
    V_c = current_speed_kt * 0.514444
    
    rel_wind_angle = math.radians((wind_dir_deg - ship_heading_deg) % 360)
    rel_curr_angle = math.radians((current_dir_deg - ship_heading_deg) % 360)
    
    rho_air = 1.225
    rho_water = 1025.0
    
    Cx_w = 0.8 * math.cos(rel_wind_angle)
    Cy_w = 0.9 * math.sin(rel_wind_angle)
    
    Cx_c = 0.1 * math.cos(rel_curr_angle)
    Cy_c = 0.6 * math.sin(rel_curr_angle)
    
    Fx_w = 0.5 * rho_air * (V_w ** 2) * A_front * Cx_w
    Fy_w = 0.5 * rho_air * (V_w ** 2) * A_side * Cy_w
    
    Fx_c = 0.5 * rho_water * (V_c ** 2) * (A_wetted * 0.1) * Cx_c
    Fy_c = 0.5 * rho_water * (V_c ** 2) * A_wetted * Cy_c
    
    Fx_total_t = (Fx_w + Fx_c) / 9806.65
    Fy_total_t = (Fy_w + Fy_c) / 9806.65
    
    return Fx_total_t, Fy_total_t

def recommend_lines(Fx_t, Fy_t, line_mbl_t, safety_factor=0.55):
    """Calcola la configurazione dei cavi (SWL = 55% MBL per MEG4)."""
    swl_t = line_mbl_t * safety_factor
    
    abs_Fx = abs(Fx_t)
    abs_Fy = abs(Fy_t)
    
    springs = max(2, math.ceil(abs_Fx / (2 * swl_t)))
    breasts = max(2, math.ceil(abs_Fy / (2 * swl_t)))
    head_stern = 2
    
    total_lines = (head_stern + breasts + springs) * 2
    return head_stern, breasts, springs, total_lines, swl_t

# -----------------------------------------------------------------------------
# 3. PANNELLO LATERALE (SIDEBAR)
# -----------------------------------------------------------------------------
st.sidebar.title("⚓ Parametri Ormeggio")

st.sidebar.subheader("1. Destinazione & Banchina")
selected_port = st.sidebar.selectbox("Seleziona Porto", list(berths_db.keys()))
port_info = berths_db[selected_port]
berths_map = port_info["berths"]

selected_berth = st.sidebar.selectbox("Seleziona Banchina", list(berths_map.keys()))
berth_info = berths_map[selected_berth]

st.sidebar.subheader("2. Data e Ora Arrivo")
dock_date = st.sidebar.date_input("Data ormeggio", datetime.date.today())
dock_time = st.sidebar.time_input("Ora stimata (ETA)", datetime.time(8, 0))

st.sidebar.subheader("3. Specifiche Nave & Cavi")
ship_loa = st.sidebar.number_input("LOA (m)", value=323.0)
ship_beam = st.sidebar.number_input("Larghezza / Beam (m)", value=37.2)
ship_draft = st.sidebar.number_input("Pescaggio / Draft (m)", value=8.5)
A_front = st.sidebar.number_input("Area Frontale Vento (m²)", value=1200.0)
A_side = st.sidebar.number_input("Area Laterale Vento (m²)", value=9500.0)
line_mbl = st.sidebar.number_input("MBL Cavo (Tonnellate)", value=115.0)

# -----------------------------------------------------------------------------
# 4. INTERFACCIA PRINCIPALE
# -----------------------------------------------------------------------------
st.title("🚢 Mooring Analysis & Port Planner")
st.caption(f"Analisi di ormeggio MEG4 per **{selected_port} - {selected_berth}** | Data: **{dock_date}** ore **{dock_time.strftime('%H:%M')}**")

# Tabelle Dati Banchina
st.markdown("### 📌 Specifiche Banchina Selezionata")
col_b1, col_b2, col_b3, col_b4 = st.columns(4)
col_b1.metric("Orientamento Banchina", f"{berth_info['heading']}°")
col_b2.metric("Portata Bitte", f"{berth_info['bollard_capacity_ton']} t")
col_b3.metric("Spaziatura Bitte", f"{berth_info['bollard_spacing_m']} m")
col_b4.metric("Pescaggio Max", f"{berth_info['max_draft_m']} m")

st.divider()

# Mappa Windy e Previsioni Meteo
st.markdown("### 🌤️ Previsioni Meteo & Mappa Windy")

weather_data = fetch_weather_data(port_info["lat"], port_info["lon"], dock_date)

default_wind_speed = 15.0
default_wind_dir = 270

if weather_data and "hourly" in weather_data:
    hour_idx = dock_time.hour
    default_wind_speed = float(weather_data["hourly"]["wind_speed_10m"][hour_idx])
    default_wind_dir = int(weather_data["hourly"]["wind_direction_10m"][hour_idx])
    st.success(f"Dati meteo live Open-Meteo per le {dock_time.strftime('%H:%M')}: Vento **{default_wind_speed} kt** da **{default_wind_dir}°**")
else:
    st.info("Utilizzo valori meteo manuali (seleziona la data per il forecast automatico).")

col_w1, col_w2 = st.columns([1, 1])

with col_w1:
    st.subheader("Condizioni Ambientali")
    wind_speed = st.slider("Velocità Vento (kt)", 0.0, 60.0, default_wind_speed, 1.0)
    wind_dir = st.slider("Direzione Vento (gradi °)", 0, 360, default_wind_dir, 5)
    current_speed = st.slider("Velocità Corrente (kt)", 0.0, 5.0, 0.8, 0.1)
    current_dir = st.slider("Direzione Corrente (gradi °)", 0, 360, 180, 5)
    
    ship_heading = berth_info["heading"]
    A_wetted = ship_loa * ship_draft
    Fx, Fy = calculate_mooring_forces(wind_speed, wind_dir, current_speed, current_dir, ship_heading, A_front, A_side, A_wetted)

with col_w2:
    st.subheader("Mappa Vento Interattiva (Windy)")
    windy_url = f"https://embed.windy.com/embed2.html?lat={port_info['lat']}&lon={port_info['lon']}&zoom=11&level=surface&overlay=wind&menu=&message=true&marker=true&forecast=12&type=map&location=coordinates&detail=true&metricWind=kt&metricTemp=%C2%B0C"
    components.iframe(windy_url, height=380, scrolling=False)

st.divider()

# Risultati Forze e Raccomandazione Cavi
st.markdown("### 📊 Risultati Analisi Forze & Configurazione Cavi Ottimale")

head_s, breasts, springs, total_lines, swl_t = recommend_lines(Fx, Fy, line_mbl)

col_r1, col_r2, col_r3, col_r4 = st.columns(4)
col_r1.metric("Forza Longitudinale ($F_x$)", f"{Fx:.1f} t", help="Spinta avanti/indietro lungo banchina")
col_r2.metric("Forza Trasversale ($F_y$)", f"{Fy:.1f} t", help="Spinta perpendicolare alla banchina")
col_r3.metric("SWL Cavo (55% MBL)", f"{swl_t:.1f} t")
col_r4.metric("Totale Cavi Consigliati", f"{total_lines} cavi")

st.markdown("#### ⚓ Schema di Ormeggio Raccomandato (MEG4)")
col_c1, col_c2, col_c3 = st.columns(3)

with col_c1:
    st.info(f"**Head / Stern Lines**\n\n**{head_s}** a prua / **{head_s}** a poppa\n\n*(Totale: {head_s * 2})*")

with col_c2:
    st.info(f"**Breast Lines**\n\n**{breasts}** a prua / **{breasts}** a poppa\n\n*(Totale: {breasts * 2})*")

with col_c3:
    st.info(f"**Spring Lines**\n\n**{springs}** avanti / **{springs}** indietro\n\n*(Totale: {springs * 2})*")

if abs(Fy) > (berth_info['bollard_capacity_ton'] * breasts):
    st.warning("⚠️ Attenzione: La forza trasversale calcolata supera la capacità nominale delle bitte selezionate. Si raccomanda di raddoppiare i cavi di Breast o rinforzare l'ormeggio.")
