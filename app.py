import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import json
import math
import requests
import datetime
import folium
from streamlit_folium import st_folium

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
        "lat": 31.8528,
        "lon": -116.6226,
        "berths": {
            "Cruise Terminal": {"heading": 155, "bollard_capacity_ton": 100}
        }
    },
    "Puerto Vallarta": {
        "lat": 20.6534,
        "lon": -105.2404,
        "berths": {
            "Pier 1": {"heading": 180, "bollard_capacity_ton": 80}
        }
    },
    "Mazatlán": {
        "lat": 23.1983,
        "lon": -106.4214,
        "berths": {
            "Cruise Dock": {"heading": 340, "bollard_capacity_ton": 75}
        }
    },
    "La Paz (Pichilingue)": {
        "lat": 24.2713,
        "lon": -110.3235,
        "berths": {
            "Muelle T-Pichilingue": {"heading": 195, "bollard_capacity_ton": 80}
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
# 2. INIZIALIZZAZIONE SESSION STATE
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

if "vessel_pos" not in st.session_state:
    st.session_state["vessel_pos"] = {
        "lat": 31.8528,
        "lon": -116.6226,
        "heading": 155.0
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
# 3. FUNZIONI UTILI (POLIGONO IN SCALA METRICA REALE)
# -----------------------------------------------------------------------------
def get_ship_polygon_coords(lat, lon, loa_m, beam_m, heading_deg):
    """Calcola i vertici geografici esatti del profilo della nave in metri."""
    heading_rad = math.radians(heading_deg)
    half_l = loa_m / 2.0
    half_b = beam_m / 2.0
    
    # Vertici locali (Prua affusolata + scafo)
    local_corners = [
        (0, half_l),
        (half_b, half_l * 0.70),
        (half_b, -half_l),
        (-half_b, -half_l),
        (-half_b, half_l * 0.70),
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

# -----------------------------------------------------------------------------
# 4. ARCHITETTURA A TAB
# -----------------------------------------------------------------------------
st.title("🚢 Carnival Panorama - Integrated Mooring System")

tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Info Nave & Specifiche",
    "⚓ Stazioni di Ormeggio & Cavi",
    "🌍 Google Earth & Windy Map",
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
# TAB 2: STAZIONI DI ORMEGGIO & CAVI
# =============================================================================
with tab2:
    st.header("⚓ Configurazione Stazioni & Verricelli")
    with st.expander("📂 Carica Registro Cavi Reale (CSV / Excel)"):
        uploaded_file = st.file_uploader("Scegli un file CSV o XLSX:", type=["csv", "xlsx"])
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    st.session_state["mooring_lines"] = pd.read_csv(uploaded_file)
                else:
                    st.session_state["mooring_lines"] = pd.read_excel(uploaded_file)
                st.success("Registro cavi aggiornato!")
            except Exception as e:
                st.error(f"Errore caricamento: {e}")

    st.session_state["mooring_lines"] = st.data_editor(
        st.session_state["mooring_lines"],
        num_rows="dynamic",
        use_container_width=True
    )

# =============================================================================
# TAB 3: POSIZIONAMENTO INTERATTIVO MAPPA & WINDY
# =============================================================================
with tab3:
    st.header("🌍 Carteggio Satellitare & Posizionamento Manuale Nave")
    
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        sel_port = st.selectbox("Porto Predefinito", list(berths_db.keys()))
    with col_p2:
        sel_berth = st.selectbox("Banchina Predefinita", list(berths_db[sel_port]["berths"].keys()))
    with col_p3:
        if st.button("📍 Ripristina Coordinate Porto"):
            st.session_state["vessel_pos"]["lat"] = berths_db[sel_port]["lat"]
            st.session_state["vessel_pos"]["lon"] = berths_db[sel_port]["lon"]
            st.session_state["vessel_pos"]["heading"] = float(berths_db[sel_port]["berths"][sel_berth].get("heading", 155))

    map_provider = st.radio("Seleziona Vista Mappa:", ["Google Earth / ESRI Satellite (Posizionamento)", "Windy Live Map"], horizontal=True)

    if map_provider == "Google Earth / ESRI Satellite (Posizionamento)":
        st.info("💡 **Come posizionare la nave:** Clicca in un punto qualsiasi della mappa satellitare per spostare il centro della nave, oppure usa i controlli manuali qui sotto per rifinire la posizione e l'orientamento (°).")

        # Controlli manuali per spostamento fine ed orientamento
        ctrl_col1, ctrl_col2, ctrl_col3 = st.columns(3)
        with ctrl_col1:
            st.session_state["vessel_pos"]["lat"] = st.number_input("Latitudine Nave", value=float(st.session_state["vessel_pos"]["lat"]), format="%.6f", step=0.0001)
        with ctrl_col2:
            st.session_state["vessel_pos"]["lon"] = st.number_input("Longitudine Nave", value=float(st.session_state["vessel_pos"]["lon"]), format="%.6f", step=0.0001)
        with ctrl_col3:
            st.session_state["vessel_pos"]["heading"] = st.slider("Heading Nave (°)", min_value=0.0, max_value=360.0, value=float(st.session_state["vessel_pos"]["heading"]), step=1.0)

        # Rendering della Mappa Folium
        m = folium.Map(
            location=[st.session_state["vessel_pos"]["lat"], st.session_state["vessel_pos"]["lon"]],
            zoom_start=18,
            max_zoom=20,
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri World Imagery"
        )

        # Calcolo vertici dello scafo in metri scalati geograficamente
        ship_poly = get_ship_polygon_coords(
            st.session_state["vessel_pos"]["lat"],
            st.session_state["vessel_pos"]["lon"],
            st.session_state["ship_data"]["loa"],
            st.session_state["ship_data"]["beam"],
            st.session_state["vessel_pos"]["heading"]
        )

        # Poligono della Nave (scala al cambiare del livello di zoom)
        folium.Polygon(
            locations=ship_poly,
            color="#00EEFF",
            fill=True,
            fill_color="#0088FF",
            fill_opacity=0.6,
            weight=2,
            popup=f"<b>{st.session_state['ship_data']['name']}</b><br>LOA: {st.session_state['ship_data']['loa']}m<br>Heading: {st.session_state['vessel_pos']['heading']}°"
        ).add_to(m)

        # Marker Centro Nave
        folium.Marker(
            [st.session_state["vessel_pos"]["lat"], st.session_state["vessel_pos"]["lon"]],
            popup="Centro Nave",
            icon=folium.Icon(color="red", icon="anchor")
        ).add_to(m)

        # Cattura l'evento del click sulla mappa
        map_data = st_folium(m, width="100%", height=600, key="interactive_map")

        # Se l'utente clicca sulla mappa, aggiorna le coordinate della nave
        if map_data and map_data.get("last_clicked"):
            clicked_lat = map_data["last_clicked"]["lat"]
            clicked_lon = map_data["last_clicked"]["lng"]
            if (abs(clicked_lat - st.session_state["vessel_pos"]["lat"]) > 0.00001 or 
                abs(clicked_lon - st.session_state["vessel_pos"]["lon"]) > 0.00001):
                st.session_state["vessel_pos"]["lat"] = clicked_lat
                st.session_state["vessel_pos"]["lon"] = clicked_lon
                st.rerun()

    else:
        # Windy Live Map incentrato sulle coordinate correnti della nave
        v_lat = st.session_state["vessel_pos"]["lat"]
        v_lon = st.session_state["vessel_pos"]["lon"]
        windy_html = f"""
        <iframe width="100%" height="580" 
            src="https://embed.windy.com/embed2.html?lat={v_lat}&lon={v_lon}&detailLat={v_lat}&detailLon={v_lon}&width=100%25&height=580&zoom=11&level=surface&overlay=wind&product=ecmwf&menu=&message=&marker=true&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=kt&metricTemp=%C2%B0C&radarRange=-1" 
            frameborder="0">
        </iframe>
        """
        components.html(windy_html, height=590)

# =============================================================================
# TAB 4: USURA CAVI & MEG4
# =============================================================================
with tab4:
    st.header("📈 Usura Cavi & Line Management Plan (MEG4)")
    df_lines = st.session_state["mooring_lines"].copy()
    
    if "Hours_Used" in df_lines.columns and "Max_Tension_Ton" in df_lines.columns and "MBL_Ton" in df_lines.columns:
        df_lines["Residual_MBL_%"] = 100 - (df_lines["Hours_Used"] / 12) - ((df_lines["Max_Tension_Ton"] / df_lines["MBL_Ton"]) * 20)
        df_lines["Residual_MBL_%"] = df_lines["Residual_MBL_%"].clip(lower=40.0, upper=100.0)
        
        def get_status(row):
            if row["Residual_MBL_%"] < 75.0 or row["Hours_Used"] > 1000:
                return "🔴 CRITICO (Sostituire)"
            elif row["Residual_MBL_%"] < 85.0 or row["Hours_Used"] > 750:
                return "🟡 ATTENZIONE (Ispezionare)"
            return "🟢 OTTIMO"

        df_lines["Stato_Cavo"] = df_lines.apply(get_status, axis=1)

    st.dataframe(df_lines, use_container_width=True)
