import streamlit as st
import pandas as pd
import numpy as np
import json
import math
import requests
import datetime
import folium
from streamlit_folium import st_folium

# Configurazione della pagina
st.set_page_config(
    page_title="Mooring Management & Vessel Planner - Carnival Panorama",
    page_icon="🚢",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 1. DATABASE PORTI & BANCHINE
# -----------------------------------------------------------------------------
DEFAULT_BERTHS = {
    "Ensenada": {
        "lat": 31.8578,
        "lon": -116.6258,
        "berths": {
            "Cruise Pier North": {"heading": 210, "bollard_capacity_ton": 100, "bollard_spacing_m": 20, "max_draft_m": 10.0},
            "Cruise Pier South": {"heading": 190, "bollard_capacity_ton": 100, "bollard_spacing_m": 20, "max_draft_m": 9.8}
        }
    },
    "Puerto Vallarta": {
        "lat": 20.6534,
        "lon": -105.2404,
        "berths": {
            "Pier 1": {"heading": 180, "bollard_capacity_ton": 80, "bollard_spacing_m": 18, "max_draft_m": 9.5},
            "Pier 2": {"heading": 180, "bollard_capacity_ton": 80, "bollard_spacing_m": 18, "max_draft_m": 9.0},
            "Pier 3": {"heading": 180, "bollard_capacity_ton": 80, "bollard_spacing_m": 18, "max_draft_m": 9.2}
        }
    },
    "Mazatlán": {
        "lat": 23.1983,
        "lon": -106.4214,
        "berths": {
            "Cruise Dock": {"heading": 340, "bollard_capacity_ton": 75, "bollard_spacing_m": 15, "max_draft_m": 9.2}
        }
    },
    "La Paz (Pichilingue)": {
        "lat": 24.2713,
        "lon": -110.3235,
        "berths": {
            "Muelle T-Pichilingue": {"heading": 195, "bollard_capacity_ton": 80, "bollard_spacing_m": 15, "max_draft_m": 9.5}
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
# 2. INIZIALIZZAZIONE SESSION STATE (MOORING STATIONS & CAVI)
# -----------------------------------------------------------------------------
if "ship_data" not in st.session_state:
    st.session_state["ship_data"] = {
        "name": "Carnival Panorama",
        "loa": 323.0,
        "beam": 37.2,
        "draft": 8.5,
        "air_draft": 62.0,
        "gross_tonnage": 133500,
        "wind_front": 1200.0,
        "wind_side": 9500.0
    }

if "mooring_lines" not in st.session_state:
    st.session_state["mooring_lines"] = pd.DataFrame([
        {"ID": "FWD-L1", "Station": "Forecastle (Prua)", "Type": "HMPE High Tech", "Winch": "Winch 1 (Port)", "Role": "Head Line", "MBL_Ton": 115, "Hours_Used": 450, "Max_Tension_Ton": 42.0, "Cert_Date": "2024-01-15"},
        {"ID": "FWD-L2", "Station": "Forecastle (Prua)", "Type": "HMPE High Tech", "Winch": "Winch 2 (Stbd)", "Role": "Head Line", "MBL_Ton": 115, "Hours_Used": 450, "Max_Tension_Ton": 40.5, "Cert_Date": "2024-01-15"},
        {"ID": "FWD-L3", "Station": "Forecastle (Prua)", "Type": "HMPE High Tech", "Winch": "Winch 3 (Port)", "Role": "Breast Line", "MBL_Ton": 115, "Hours_Used": 820, "Max_Tension_Ton": 68.0, "Cert_Date": "2023-06-10"},
        {"ID": "FWD-L4", "Station": "Forecastle (Prua)", "Type": "HMPE High Tech", "Winch": "Winch 4 (Stbd)", "Role": "Spring Line", "MBL_Ton": 115, "Hours_Used": 300, "Max_Tension_Ton": 35.0, "Cert_Date": "2024-03-01"},
        {"ID": "AFT-L1", "Station": "Poppa (Aft Station)", "Type": "Polyester Blend", "Winch": "Winch 5 (Port)", "Role": "Stern Line", "MBL_Ton": 110, "Hours_Used": 980, "Max_Tension_Ton": 72.0, "Cert_Date": "2022-11-20"},
        {"ID": "AFT-L2", "Station": "Poppa (Aft Station)", "Type": "Polyester Blend", "Winch": "Winch 6 (Stbd)", "Role": "Stern Line", "MBL_Ton": 110, "Hours_Used": 980, "Max_Tension_Ton": 70.0, "Cert_Date": "2022-11-20"},
        {"ID": "AFT-L3", "Station": "Poppa (Aft Station)", "Type": "Polyester Blend", "Winch": "Winch 7 (Port)", "Role": "Breast Line", "MBL_Ton": 110, "Hours_Used": 1120, "Max_Tension_Ton": 82.0, "Cert_Date": "2022-05-15"},
        {"ID": "AFT-L4", "Station": "Poppa (Aft Station)", "Type": "Polyester Blend", "Winch": "Winch 8 (Stbd)", "Role": "Spring Line", "MBL_Ton": 110, "Hours_Used": 400, "Max_Tension_Ton": 38.0, "Cert_Date": "2024-02-10"},
    ])

# -----------------------------------------------------------------------------
# 3. FUNZIONI UTILI
# -----------------------------------------------------------------------------
def get_ship_polygon_coords(lat, lon, loa_m, beam_m, heading_deg):
    """Calcola i vertici della nave in scala reale."""
    heading_rad = math.radians(heading_deg)
    half_l = loa_m / 2.0
    half_b = beam_m / 2.0
    
    local_corners = [
        (0, half_l),
        (half_b, half_l * 0.75),
        (half_b, -half_l),
        (-half_b, -half_l),
        (-half_b, half_l * 0.75),
        (0, half_l)
    ]
    
    coords = []
    m_per_deg_lat = 111139.0
    m_per_deg_lon = 111139.0 * math.cos(math.radians(lat))
    
    for dx, dy in local_corners:
        rot_x = dx * math.cos(heading_rad) + dy * math.sin(heading_rad)
        rot_y = -dx * math.sin(heading_rad) + dy * math.cos(heading_rad)
        coords.append([lat + (rot_y / m_per_deg_lat), lon + (rot_x / m_per_deg_lon)])
        
    return coords

def fetch_weather(lat, lon, selected_date):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=kn&start_date={selected_date}&end_date={selected_date}"
    try:
        r = requests.get(url, timeout=4).json()
        return r
    except Exception:
        return None

# -----------------------------------------------------------------------------
# 4. ARCHITETTURA A TAB (PAGINE)
# -----------------------------------------------------------------------------
st.title("🚢 Carnival Panorama - Integrated Mooring System")

tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Info Nave & Specifiche",
    "⚓ Stazioni di Ormeggio & Cavi",
    "🌍 Google Earth & Banchina",
    "📈 Usura Cavi & Line Management"
])

# =============================================================================
# TAB 1: INFO NAVE
# =============================================================================
with tab1:
    st.header("🚢 Profilo Tecnico Nave")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Dati Generali")
        st.session_state["ship_data"]["loa"] = st.number_input("LOA (Lunghezza Fuori Tutto) [m]", value=st.session_state["ship_data"]["loa"])
        st.session_state["ship_data"]["beam"] = st.number_input("Beam (Larghezza) [m]", value=st.session_state["ship_data"]["beam"])
        st.session_state["ship_data"]["draft"] = st.number_input("Draft (Pescaggio) [m]", value=st.session_state["ship_data"]["draft"])
        st.session_state["ship_data"]["gross_tonnage"] = st.number_input("Gross Tonnage (GT)", value=st.session_state["ship_data"]["gross_tonnage"])

    with col2:
        st.subheader("Superfici Esposte al Vento (MEG4)")
        st.session_state["ship_data"]["wind_front"] = st.number_input("Area Vento Frontale [m²]", value=st.session_state["ship_data"]["wind_front"])
        st.session_state["ship_data"]["wind_side"] = st.number_input("Area Vento Laterale [m²]", value=st.session_state["ship_data"]["wind_side"])
        st.session_state["ship_data"]["air_draft"] = st.number_input("Air Draft [m]", value=st.session_state["ship_data"]["air_draft"])

# =============================================================================
# TAB 2: STAZIONI DI ORMEGGIO & CAVI INTERATTIVI
# =============================================================================
with tab2:
    st.header("⚓ Configurazione Stazioni & Verricelli (Winch)")
    st.caption("Modifica le posizioni dei cavi, i verricelli assegnati e il tipo di fibra. I cambiamenti aggiorneranno l'analisi in tempo reale.")
    
    edited_df = st.data_editor(
        st.session_state["mooring_lines"],
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Station": st.column_config.SelectboxColumn("Stazione", options=["Forecastle (Prua)", "Poppa (Aft Station)"]),
            "Type": st.column_config.SelectboxColumn("Tipo Cavo", options=["HMPE High Tech", "Polyester Blend", "Polypropylene", "Steel Wire"]),
            "Role": st.column_config.SelectboxColumn("Ruolo Cavo", options=["Head Line", "Stern Line", "Breast Line", "Spring Line"]),
            "MBL_Ton": st.column_config.NumberColumn("MBL (Tonnellate)", min_value=50, max_value=250),
            "Hours_Used": st.column_config.NumberColumn("Ore di Servizio", min_value=0),
            "Max_Tension_Ton": st.column_config.NumberColumn("Picco Tensione Registrata (t)")
        }
    )
    st.session_state["mooring_lines"] = edited_df

# =============================================================================
# TAB 3: GOOGLE EARTH & NAVE IN SCALA
# =============================================================================
with tab3:
    st.header("🌍 Mappa Satellitare Banchina (Google Earth Style)")
    
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        sel_port = st.selectbox("Porto", list(berths_db.keys()))
    with col_p2:
        sel_berth = st.selectbox("Banchina", list(berths_db[sel_port]["berths"].keys()))
    with col_p3:
        dock_date = st.date_input("Data Arrivo", datetime.date.today())
        
    port_data = berths_db[sel_port]
    berth_data = port_data["berths"][sel_berth]
    
    # Recupero flessibile parametri banchina
    bollard_cap = berth_data.get("bollard_capacity_ton", berth_data.get("bollard_cap", 80))
    heading = berth_data.get("heading", 180)

    # Previsioni Meteo
    w_json = fetch_weather(port_data["lat"], port_data["lon"], dock_date.strftime("%Y-%m-%d"))
    if w_json and "hourly" in w_json:
        wind_sp = float(w_json["hourly"]["wind_speed_10m"][8])
        wind_dir = int(w_json["hourly"]["wind_direction_10m"][8])
        st.success(f"Meteo previsto per il {dock_date}: Vento **{wind_sp} kt** da **{wind_dir}°**")

    # Mappa Folium con layer satellitare ESRI World Imagery
    m = folium.Map(
        location=[port_data["lat"], port_data["lon"]],
        zoom_start=17,
        max_zoom=20,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery"
    )

    # Calcolo coordinate nave in scala
    ship_poly = get_ship_polygon_coords(
        port_data["lat"],
        port_data["lon"],
        st.session_state["ship_data"]["loa"],
        st.session_state["ship_data"]["beam"],
        heading
    )

    # Rendering Poligono Nave
    folium.Polygon(
        locations=ship_poly,
        color="#00EEFF",
        fill=True,
        fill_color="#0088FF",
        fill_opacity=0.6,
        weight=2,
        popup=f"<b>{st.session_state['ship_data']['name']}</b><br>LOA: {st.session_state['ship_data']['loa']}m<br>Heading: {heading}°"
    ).add_to(m)

    # Marker Banchina
    folium.Marker(
        [port_data["lat"], port_data["lon"]],
        popup=f"<b>{sel_berth}</b><br>Capacità Bitte: {bollard_cap} t",
        icon=folium.Icon(color="red", icon="anchor")
    ).add_to(m)

    st_folium(m, width="100%", height=500)

# =============================================================================
# TAB 4: USURA CAVI & LINE MANAGEMENT PLAN (MEG4)
# =============================================================================
with tab4:
    st.header("📈 Usura Cavi & Line Management Plan (MEG4)")
    st.caption("Monitoraggio dello stato di salute, tensione massima registrata e calcolo della resistenza residua del cavo.")
    
    df_lines = st.session_state["mooring_lines"].copy()
    
    # Calcolo Indice di Usura
    df_lines["Residual_MBL_%"] = 100 - (df_lines["Hours_Used"] / 12) - ((df_lines["Max_Tension_Ton"] / df_lines["MBL_Ton"]) * 20)
    df_lines["Residual_MBL_%"] = df_lines["Residual_MBL_%"].clip(lower=40.0, upper=100.0)
    
    def get_status(row):
        if row["Residual_MBL_%"] < 75.0 or row["Hours_Used"] > 1000:
            return "🔴 CRITICO (Sostituire)"
        elif row["Residual_MBL_%"] < 85.0 or row["Hours_Used"] > 750:
            return "🟡 ATTENZIONE (Ispezionare)"
        return "🟢 OTTIMO"

    df_lines["Stato_Cavo"] = df_lines.apply(get_status, axis=1)

    st.dataframe(
        df_lines[["ID", "Station", "Winch", "Type", "Hours_Used", "Max_Tension_Ton", "Residual_MBL_%", "Stato_Cavo"]],
        use_container_width=True
    )
    
    critical_lines = df_lines[df_lines["Stato_Cavo"].str.contains("CRITICO")]
    if not critical_lines.empty:
        st.error(f"🚨 **Attenzione Sicurezza MEG4:** Risultano {len(critical_lines)} cavi che hanno superato il limite di usura o ore di servizio consigliate. Si raccomanda la sostituzione immediata.")
