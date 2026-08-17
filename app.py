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
# 1. DATABASE PORTI & BANCHINE CON SALVATAGGIO SU FILE JSON
# -----------------------------------------------------------------------------
DEFAULT_BERTHS = {
    "Ensenada": {
        "lat": 31.85195,
        "lon": -116.62145,
        "berths": {
            "Cruise Terminal (Main Pier)": {
                "heading": 155.0,
                "bollard_capacity_ton": 100,
                "bollard_count": 10,
                "bollard_spacing_m": 20.0
            }
        }
    },
    "Puerto Vallarta": {
        "lat": 20.6534,
        "lon": -105.2404,
        "berths": {
            "Pier 1": {
                "heading": 180.0,
                "bollard_capacity_ton": 80,
                "bollard_count": 8,
                "bollard_spacing_m": 18.0
            }
        }
    },
    "Mazatlán": {
        "lat": 23.1983,
        "lon": -106.4214,
        "berths": {
            "Cruise Dock": {
                "heading": 340.0,
                "bollard_capacity_ton": 75,
                "bollard_count": 8,
                "bollard_spacing_m": 15.0
            }
        }
    }
}

def load_berths_data():
    try:
        with open("berths.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        with open("berths.json", "w", encoding="utf-8") as f:
            json.dump(DEFAULT_BERTHS, f, indent=4)
        return DEFAULT_BERTHS

def save_berths_data(data):
    with open("berths.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

if "berths_db" not in st.session_state:
    st.session_state["berths_db"] = load_berths_data()

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
        "lat": 31.85195,
        "lon": -116.62145,
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
# 3. FUNZIONI DI CALCOLO GEOMETRICO (NAVE & BITTE)
# -----------------------------------------------------------------------------
def get_ship_polygon_coords(lat, lon, loa_m, beam_m, heading_deg):
    heading_rad = math.radians(heading_deg)
    half_l = loa_m / 2.0
    half_b = beam_m / 2.0
    
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

def generate_bollard_positions(start_lat, start_lon, heading_deg, count, spacing_m):
    """Genera le coordinate geografiche di ogni bitta lungo l'asse della banchina."""
    heading_rad = math.radians(heading_deg)
    m_per_deg_lat = 111139.0
    m_per_deg_lon = 111139.0 * math.cos(math.radians(start_lat))
    
    bollards = []
    for i in range(count):
        dist_m = i * spacing_m
        dy = dist_m * math.cos(heading_rad)
        dx = dist_m * math.sin(heading_rad)
        b_lat = start_lat + (dy / m_per_deg_lat)
        b_lon = start_lon + (dx / m_per_deg_lon)
        bollards.append({"id": f"Bitta #{i+1}", "lat": b_lat, "lon": b_lon})
    return bollards

# -----------------------------------------------------------------------------
# 4. ARCHITETTURA A TAB
# -----------------------------------------------------------------------------
st.title("🚢 Carnival Panorama - Integrated Mooring System")

tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Info Nave & Specifiche",
    "⚓ Stazioni di Ormeggio & Cavi",
    "🌍 Google Earth, Bitte & Windy",
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
# TAB 3: POSIZIONAMENTO INTERATTIVO, SALVATAGGIO BANCHINE & BITTE
# =============================================================================
with tab3:
    st.header("🌍 Carteggio Satellitare & Layout Banchine")
    
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        sel_port = st.selectbox("Seleziona Porto", list(st.session_state["berths_db"].keys()))
    with col_p2:
        berth_options = list(st.session_state["berths_db"][sel_port]["berths"].keys())
        sel_berth = st.selectbox("Seleziona Banchina", berth_options)
    with col_p3:
        if st.button("📍 Carica Posizione Banchina Selezionata"):
            b_data = st.session_state["berths_db"][sel_port]["berths"][sel_berth]
            st.session_state["vessel_pos"]["lat"] = st.session_state["berths_db"][sel_port]["lat"]
            st.session_state["vessel_pos"]["lon"] = st.session_state["berths_db"][sel_port]["lon"]
            st.session_state["vessel_pos"]["heading"] = float(b_data.get("heading", 155.0))
            st.rerun()

    map_provider = st.radio("Seleziona Vista Mappa:", ["Google Earth / ESRI Satellite (Posizionamento)", "Windy Live Map"], horizontal=True)

    if map_provider == "Google Earth / ESRI Satellite (Posizionamento)":
        st.info("💡 **Clicca sulla mappa** per spostare il centro della nave, oppure usa i parametri sottostanti. Una volta posizionata la nave e impostate le bitte, clicca su **'Salva Banchina in Memoria'** per non doverla più riposizionare.")

        current_berth_info = st.session_state["berths_db"][sel_port]["berths"][sel_berth]

        # Form di configurazione fine e salvataggio permanente
        with st.expander("💾 Gestione & Salvataggio Permanente Banchina / Bitte", expanded=True):
            col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
            with col_cfg1:
                st.session_state["vessel_pos"]["lat"] = st.number_input("Latitudine Nave/Banchina", value=float(st.session_state["vessel_pos"]["lat"]), format="%.6f", step=0.0001)
                st.session_state["vessel_pos"]["lon"] = st.number_input("Longitudine Nave/Banchina", value=float(st.session_state["vessel_pos"]["lon"]), format="%.6f", step=0.0001)
            with col_cfg2:
                st.session_state["vessel_pos"]["heading"] = st.slider("Heading Banchina/Nave (°)", min_value=0.0, max_value=360.0, value=float(st.session_state["vessel_pos"]["heading"]), step=0.5)
                bollard_cap = st.number_input("Capacità Bitte (Tonnellate)", value=int(current_berth_info.get("bollard_capacity_ton", 100)))
            with col_cfg3:
                bollard_count = st.number_input("Numero di Bitte sulla Banchina", min_value=2, max_value=30, value=int(current_berth_info.get("bollard_count", 10)))
                bollard_spacing = st.number_input("Spaziatura tra Bitte (metri)", min_value=5.0, max_value=50.0, value=float(current_berth_info.get("bollard_spacing_m", 20.0)))

            save_col1, save_col2 = st.columns(2)
            with save_col1:
                new_berth_name = st.text_input("Nome Banchina da Salvare/Aggiornare", value=sel_berth)
            with save_col2:
                st.write("")
                st.write("")
                if st.button("💾 Salva / Aggiorna Banchina in Memoria"):
                    # Aggiorna il database locale e scrive su berths.json
                    st.session_state["berths_db"][sel_port]["lat"] = st.session_state["vessel_pos"]["lat"]
                    st.session_state["berths_db"][sel_port]["lon"] = st.session_state["vessel_pos"]["lon"]
                    st.session_state["berths_db"][sel_port]["berths"][new_berth_name] = {
                        "heading": st.session_state["vessel_pos"]["heading"],
                        "bollard_capacity_ton": bollard_cap,
                        "bollard_count": bollard_count,
                        "bollard_spacing_m": bollard_spacing
                    }
                    save_berths_data(st.session_state["berths_db"])
                    st.success(f"Banchina '{new_berth_name}' salvata con successo nel file berths.json!")

        # Mappa Folium
        m = folium.Map(
            location=[st.session_state["vessel_pos"]["lat"], st.session_state["vessel_pos"]["lon"]],
            zoom_start=18,
            max_zoom=20,
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri World Imagery"
        )

        # 1. Rendering Poligono Nave (In scala reale)
        ship_poly = get_ship_polygon_coords(
            st.session_state["vessel_pos"]["lat"],
            st.session_state["vessel_pos"]["lon"],
            st.session_state["ship_data"]["loa"],
            st.session_state["ship_data"]["beam"],
            st.session_state["vessel_pos"]["heading"]
        )

        folium.Polygon(
            locations=ship_poly,
            color="#00EEFF",
            fill=True,
            fill_color="#0088FF",
            fill_opacity=0.5,
            weight=2,
            popup=f"<b>{st.session_state['ship_data']['name']}</b><br>LOA: {st.session_state['ship_data']['loa']}m"
        ).add_to(m)

        # 2. Rendering Bitte Calcolate lungo la linea di banchina
        bollards = generate_bollard_positions(
            st.session_state["vessel_pos"]["lat"],
            st.session_state["vessel_pos"]["lon"],
            st.session_state["vessel_pos"]["heading"],
            bollard_count,
            bollard_spacing
        )

        for b in bollards:
            folium.CircleMarker(
                location=[b["lat"], b["lon"]],
                radius=5,
                color="#FF0055",
                fill=True,
                fill_color="#FFD700",
                fill_opacity=0.9,
                popup=f"<b>{b['id']}</b><br>Capacità: {bollard_cap} t"
            ).add_to(m)

        map_data = st_folium(m, width="100%", height=600, key="interactive_map")

        if map_data and map_data.get("last_clicked"):
            clicked_lat = map_data["last_clicked"]["lat"]
            clicked_lon = map_data["last_clicked"]["lng"]
            if (abs(clicked_lat - st.session_state["vessel_pos"]["lat"]) > 0.00001 or 
                abs(clicked_lon - st.session_state["vessel_pos"]["lon"]) > 0.00001):
                st.session_state["vessel_pos"]["lat"] = clicked_lat
                st.session_state["vessel_pos"]["lon"] = clicked_lon
                st.rerun()

    else:
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
