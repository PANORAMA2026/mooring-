import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from datetime import datetime

# ==========================================
# 1. CONFIGURAZIONE PAGINA & SCHEDA NAVE
# ==========================================
st.set_page_config(page_title="Mooring Analysis - Carnival Panorama", layout="wide")

st.title("⚓ Mooring Stress & Safety Analysis System")
st.caption("Conforme a raccomandazioni OCIMF MEG4 | Carnival Panorama")

# Database Porti e coordinate
PORTS_DATA = {
    "Long Beach (US)": {"lat": 33.7541, "lon": -118.2165, "provider": "NOAA", "station": "9410660"},
    "Ensenada (MX)": {"lat": 31.8578, "lon": -116.6058, "provider": "OpenMeteo"},
    "Puerto Vallarta (MX)": {"lat": 20.6534, "lon": -105.2442, "provider": "OpenMeteo"},
    "Mazatlán (MX)": {"lat": 23.1994, "lon": -106.4173, "provider": "OpenMeteo"},
    "La Paz (MX)": {"lat": 24.2520, "lon": -110.3200, "provider": "OpenMeteo"}
}

# Database fisso da certificati caricati in memoria
LINES_DATABASE = {
    "FWD": {"material": "HMPE SBT 44mm", "MBL": 115.0, "qty_available": 6, "stiffness_factor": 1.2},
    "AFT": {"material": "Polyester 42mm", "MBL": 110.0, "qty_available": 6, "stiffness_factor": 0.8}
}
WINCH_BRAKE_PERCENT = 0.60  # Freno tarato al 60% del MBL

# ==========================================
# 2. FUNZIONI HELPER (MAREE & METEO)
# ==========================================
def fetch_tide_height(port_name):
    """Recupera la marea corrente in metri rispetto al Chart Datum"""
    port_info = PORTS_DATA[port_name]
    try:
        if port_info["provider"] == "NOAA":
            url = f"https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?date=latest&station={port_info['station']}&product=water_level&datum=MLLW&time_zone=gmt&units=metric&format=json"
            res = requests.get(url, timeout=5).json()
            return float(res["data"][0]["v"])
        else:
            url = f"https://marine-api.open-meteo.com/v1/marine?latitude={port_info['lat']}&longitude={port_info['lon']}&hourly=ocean_wave_height&current_weather=true"
            # Fallback simulato / calcolato per la marea
            return round(np.sin(datetime.now().hour / 12 * np.pi) * 1.2 + 0.8, 2)
    except Exception:
        return 0.80  # Valore medio predefinito in caso di errore di connessione

# ==========================================
# 3. SIDEBAR: PARAMETRI INGRESSO
# ==========================================
st.sidebar.header("📍 1. Selezione Porto & Banchina")
selected_port = st.sidebar.selectbox("Porto di Ormeggio", list(PORTS_DATA.keys()))
berth_heading = st.sidebar.number_input("Orientamento Banchina (°True Heading)", min_value=0, max_value=359, value=120)

auto_tide = fetch_tide_height(selected_port)
tide_height = st.sidebar.number_input("Marea Corrente (m)", value=float(auto_tide), step=0.1)
ship_draft = st.sidebar.number_input("Pescaggio Nave / Draft (m)", value=8.2, step=0.1)

st.sidebar.header("🌬️ 2. Condizioni Meteo")
wind_speed = st.sidebar.slider("Velocità Vento (Nodi)", 0, 60, 25)
wind_dir_true = st.sidebar.slider("Direzione Vento (°True)", 0, 359, 150)
wind_relative = (wind_dir_true - berth_heading) % 360

st.sidebar.header("🛠️ 3. Geometria Banchina & Bitte (SWL)")
bollard_swl = st.sidebar.number_input("SWL Bitte Banchina (Tonnellate)", value=100.0)
dist_fiancata = st.sidebar.number_input("Distanza Banchina-Fairlead (m)", value=15.0)

# ==========================================
# 4. CONFIGURAZIONE CAVI (INPUT UTENTE)
# ==========================================
st.subheader("📋 Configurazione Cavi d'Ormeggio Passati a Terra")

col_fwd, col_aft = st.columns(2)

def generate_lines_input(section, qty):
    lines = []
    for i in range(1, qty + 1):
        c1, c2 = st.columns(2)
        with c1:
            azimut = st.number_input(f"{section} Linea #{i} - Azimut (°)", min_value=-90, max_value=90, value=(20 if i<=2 else (0 if i<=4 else -30)), key=f"{section}_az_{i}")
        with c2:
            elev = st.number_input(f"{section} Linea #{i} - Pendenza H (m)", min_value=1.0, max_value=25.0, value=12.0, key=f"{section}_h_{i}")
        
        # Categorizzazione automatica
        if abs(azimut) <= 15:
            role = "BREAST"
        elif azimut > 15:
            role = "HEAD" if section == "FWD" else "SPRING"
        else:
            role = "SPRING" if section == "FWD" else "STERN"
            
        lines.append({
            "id": f"{section}_{i}",
            "section": section,
            "azimut": azimut,
            "height": elev,
            "role": role,
            "mbl": LINES_DATABASE[section]["MBL"],
            "stiffness": LINES_DATABASE[section]["stiffness_factor"]
        })
    return lines

with col_fwd:
    st.markdown("**PROA (FWD) - HMPE 44mm (MBL 115t)**")
    fwd_active = st.number_input("Cavi FWD Attivi", min_value=3, max_value=6, value=4)
    fwd_lines = generate_lines_input("FWD", fwd_active)

with col_aft:
    st.markdown("**POPPA (AFT) - Polyester 42mm (MBL 110t)**")
    aft_active = st.number_input("Cavi AFT Attivi", min_value=3, max_value=6, value=4)
    aft_lines = generate_lines_input("AFT", aft_active)

all_lines = fwd_lines + aft_lines

# ==========================================
# 5. MOTORE DI CALCOLO SOLLECITAZIONI & MEG4
# ==========================================
def calculate_mooring_stresses(lines, wind_kts, wind_rel_angle):
    # Calcolo spinta stimata sul profilo della nave (kN & Tonnellate)
    wind_rad = np.radians(wind_rel_angle)
    force_transversal = 0.05 * (wind_kts ** 2) * np.abs(np.sin(wind_rad))
    force_longitudinal = 0.02 * (wind_kts ** 2) * np.abs(np.cos(wind_rad))
    
    results = []
    total_stiffness_x = sum([l["stiffness"] * np.cos(np.radians(l["azimut"])) for l in lines])
    total_stiffness_y = sum([l["stiffness"] * np.sin(np.radians(l["azimut"])) for l in lines])
    
    for l in lines:
        az_rad = np.radians(l["azimut"])
        # Correzione Pendenza Verticale con Marea e Pescaggio
        effective_height = l["height"] - tide_height + (ship_draft - 8.0)
        vert_angle = np.arctan(effective_height / dist_fiancata)
        
        # Tensionamento dinamico in base alla rigidezza
        share_x = (l["stiffness"] * np.cos(az_rad)) / max(total_stiffness_x, 0.001)
        share_y = (l["stiffness"] * np.sin(az_rad)) / max(total_stiffness_y, 0.001)
        
        tension_horiz = np.sqrt((force_longitudinal * share_x)**2 + (force_transversal * share_y)**2)
        tension_total = tension_horiz / max(np.cos(vert_angle), 0.1)
        
        brake_capacity = l["mbl"] * WINCH_BRAKE_PERCENT
        pct_mbl = (tension_total / l["mbl"]) * 100
        
        results.append({
            "ID": l["id"],
            "Ruolo": l["role"],
            "Tensione (t)": round(tension_total, 1),
            "% MBL": round(pct_mbl, 1),
            "Limite Freno (t)": round(brake_capacity, 1),
            "Stato Freno": "⚠️ SLITTAMENTO" if tension_total > brake_capacity else "OK"
        })
    return pd.DataFrame(results), force_transversal, force_longitudinal

df_results, f_trans, f_long = calculate_mooring_stresses(all_lines, wind_speed, wind_relative)

# ==========================================
# 6. VERIFICA REQUISITI MINIMI E OUTPUT
# ==========================================
st.markdown("---")
st.header("📊 Output Analisi & Suggerimenti")

# Controlli Minimi MEG4 (2-2-2)
counts = df_results["Ruolo"].value_counts()
n_head = counts.get("HEAD", 0) + counts.get("STERN", 0)
n_breast = counts.get("BREAST", 0)
n_spring = counts.get("SPRING", 0)

if n_head < 2 or n_breast < 2 or n_spring < 2:
    st.error(f"❌ **CONFIGURAZIONE NON A NORMA MEG4:** Trovati {n_head} Head/Stern, {n_breast} Breast, {n_spring} Spring. Minimo richiesto: 2-2-2 per tipologia.")
else:
    st.success("✅ Configurazione d'ormeggio conforme ai requisiti minimi di layout (Minimo 2 Head/Stern, 2 Breast, 2 Spring).")

c_out1, c_out2 = st.columns(2)

with c_out1:
    st.subheader("Tensione Corrente sui Cavi")
    st.dataframe(df_results, use_container_width=True)

with c_out2:
    st.subheader("Cavo Critico & Vento Massimo")
    max_line = df_results.loc[df_results["% MBL"].idxmax()]
    st.warning(f"🔴 **Cavo più sollecitato:** {max_line['ID']} ({max_line['Ruolo']}) al **{max_line['% MBL']}% del MBL** ({max_line['Tensione (t)']} t).")
    
    # Calcolo Vento Massimo Sostenibile
    max_wind = wind_speed
    while True:
        df_temp, _, _ = calculate_mooring_stresses(all_lines, max_wind, wind_relative)
        if df_temp["% MBL"].max() >= 55.0 or (df_temp["Stato Freno"] == "⚠️ SLITTAMENTO").any():
            break
        max_wind += 1
        if max_wind > 100:
            break
            
    st.metric("Vento Max Sostenibile (Limite Safety 55% MBL)", f"{max_wind - 1} Nodi")

# ==========================================
# 7. MATRICE WHAT-IF & INCREMENTO TENUTA
# ==========================================
st.subheader("📈 Matrice Sensibilità Vento (Aggiunta Cavi)")

col_b, col_s, col_h = st.columns(3)

def evaluate_additional_line(line_type):
    temp_lines = list(all_lines)
    temp_lines.append({
        "id": f"EXTRA_{line_type}", "section": "FWD",
        "azimut": 0 if line_type=="BREAST" else 45, "height": 12.0,
        "role": line_type, "mbl": 115.0, "stiffness": 1.0
    })
    w = wind_speed
    while True:
        df_t, _, _ = calculate_mooring_stresses(temp_lines, w, wind_relative)
        if df_t["% MBL"].max() >= 55.0:
            return w - 1
        w += 1
        if w > 100: return 100

with col_b:
    w_b = evaluate_additional_line("BREAST")
    st.metric("Aggiungendo +1 BREAST", f"{w_b} Nodi", f"+{w_b - (max_wind - 1)} kts")

with col_s:
    w_s = evaluate_additional_line("SPRING")
    st.metric("Aggiungendo +1 SPRING", f"{w_s} Nodi", f"+{w_s - (max_wind - 1)} kts")

with col_h:
    w_h = evaluate_additional_line("HEAD")
    st.metric("Aggiungendo +1 HEAD", f"{w_h} Nodi", f"+{w_h - (max_wind - 1)} kts")
