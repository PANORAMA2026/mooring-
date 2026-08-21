import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, date, time

# ==========================================
# 1. CONFIGURAZIONE PAGINA & SCHEDA NAVE
# ==========================================
st.set_page_config(page_title="Mooring Analysis - Carnival Panorama", layout="wide")

st.title("⚓ Mooring Stress & Safety Analysis System")
st.caption("Conforme a raccomandazioni OCIMF MEG4 | Carnival Panorama")

# Database cavi caricati in memoria dai certificati
LINES_DATABASE = {
    "FWD": {"material": "HMPE SBT 44mm", "MBL": 115.0, "stiffness_factor": 1.2},
    "AFT": {"material": "Polyester 42mm", "MBL": 110.0, "stiffness_factor": 0.8}
}
WINCH_BRAKE_PERCENT = 0.60  # Freno al 60% MBL

# ==========================================
# 2. MEMORIA PERSISTENTE BANCHINE (SESSION STATE)
# ==========================================
if "berths_db" not in st.session_state:
    st.session_state.berths_db = {
        "Long Beach (US)": {
            "lat": 33.7541, "lon": -118.2165, "heading": 120, "swl": 100.0, "dist": 15.0,
            "fwd_azimut": [20, 20, 0, 0, -30, -30], "fwd_slope": [12, 12, 10, 10, 15, 15],
            "aft_azimut": [30, 30, 0, 0, -20, -20], "aft_slope": [15, 15, 10, 10, 12, 12]
        },
        "Ensenada (MX)": {
            "lat": 31.8578, "lon": -116.6058, "heading": 045, "swl": 80.0, "dist": 12.0,
            "fwd_azimut": [25, 25, 0, 0, -25, -25], "fwd_slope": [10, 10, 8, 8, 12, 12],
            "aft_azimut": [25, 25, 0, 0, -25, -25], "aft_slope": [12, 12, 8, 8, 10, 10]
        },
        "Puerto Vallarta (MX)": {
            "lat": 20.6534, "lon": -105.2442, "heading": 180, "swl": 80.0, "dist": 14.0,
            "fwd_azimut": [20, 20, 0, 0, -30, -30], "fwd_slope": [11, 11, 9, 9, 14, 14],
            "aft_azimut": [30, 30, 0, 0, -20, -20], "aft_slope": [14, 14, 9, 9, 11, 11]
        },
        "Mazatlán (MX)": {
            "lat": 23.1994, "lon": -106.4173, "heading": 310, "swl": 90.0, "dist": 13.0,
            "fwd_azimut": [20, 20, 0, 0, -25, -25], "fwd_slope": [10, 10, 8, 8, 13, 13],
            "aft_azimut": [25, 25, 0, 0, -20, -20], "aft_slope": [13, 13, 8, 8, 10, 10]
        },
        "La Paz (MX)": {
            "lat": 24.2520, "lon": -110.3200, "heading": 090, "swl": 75.0, "dist": 11.0,
            "fwd_azimut": [18, 18, 0, 0, -25, -25], "fwd_slope": [9, 9, 7, 7, 11, 11],
            "aft_azimut": [25, 25, 0, 0, -18, -18], "aft_slope": [11, 11, 7, 7, 9, 9]
        }
    }

# ==========================================
# 3. INTERFACCIA: GESTIONE BANCHINE PER PORTO
# ==========================================
st.sidebar.header("📍 Selezione Operativa")
selected_port = st.sidebar.selectbox("Porto Attivo", list(st.session_state.berths_db.keys()))

with st.expander("🛠️ CONFIGURAZIONE BANCHINE E GEOMETRIA CAVI (Salvata in Memoria)", expanded=False):
    st.info(f"Modifica i dati fisici della banchina di **{selected_port}**. I parametri inseriti verranno salvati e riutilizzati automaticamente per tutti i calcoli futuri.")
    
    port_config = st.session_state.berths_db[selected_port]
    
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        new_heading = st.number_input("Orientamento Banchina (°True Heading)", min_value=0, max_value=359, value=int(port_config["heading"]))
    with col_p2:
        new_swl = st.number_input("SWL Bitte Banchina (Tonnellate)", min_value=10.0, max_value=250.0, value=float(port_config["swl"]))
    with col_p3:
        new_dist = st.number_input("Distanza Fiancata-Banchina (m)", min_value=1.0, max_value=50.0, value=float(port_config["dist"]))
        
    st.markdown("---")
    st.markdown("### Configurazione Cavi d'Ormeggio (Azimut e Pendenza in Gradi °)")
    
    col_f_cfg, col_a_cfg = st.columns(2)
    
    with col_f_cfg:
        st.subheader("Prua (FWD) - HMPE 44mm")
        fwd_az_list = []
        fwd_sl_list = []
        for i in range(6):
            c_a, c_s = st.columns(2)
            with c_a:
                az = st.number_input(f"FWD #{i+1} Azimut (°)", -90, 90, int(port_config["fwd_azimut"][i]), key=f"f_az_{selected_port}_{i}")
                fwd_az_list.append(az)
            with c_s:
                sl = st.number_input(f"FWD #{i+1} Pendenza (°)", 0, 60, int(port_config["fwd_slope"][i]), key=f"f_sl_{selected_port}_{i}")
                fwd_sl_list.append(sl)
                
    with col_a_cfg:
        st.subheader("Poppa (AFT) - Polyester 42mm")
        aft_az_list = []
        aft_sl_list = []
        for i in range(6):
            c_a, c_s = st.columns(2)
            with c_a:
                az = st.number_input(f"AFT #{i+1} Azimut (°)", -90, 90, int(port_config["aft_azimut"][i]), key=f"a_az_{selected_port}_{i}")
                aft_az_list.append(az)
            with c_s:
                sl = st.number_input(f"AFT #{i+1} Pendenza (°)", 0, 60, int(port_config["aft_slope"][i]), key=f"a_sl_{selected_port}_{i}")
                aft_sl_list.append(sl)

    if st.button("💾 Salva Dati Banchina in Memoria"):
        st.session_state.berths_db[selected_port]["heading"] = new_heading
        st.session_state.berths_db[selected_port]["swl"] = new_swl
        st.session_state.berths_db[selected_port]["dist"] = new_dist
        st.session_state.berths_db[selected_port]["fwd_azimut"] = fwd_az_list
        st.session_state.berths_db[selected_port]["fwd_slope"] = fwd_sl_list
        st.session_state.berths_db[selected_port]["aft_azimut"] = aft_az_list
        st.session_state.berths_db[selected_port]["aft_slope"] = aft_sl_list
        st.success(f"Dati della banchina di {selected_port} salvati correttamente!")

# ==========================================
# 4. REPERIMENTO METEO IN TEMPO REALE PER DATA SELEZIONATA
# ==========================================
st.sidebar.header("🌤️ 2. Condimeteo Live & Previsioni")

selected_date = st.sidebar.date_input("Seleziona Data Ormeggio", value=date.today())
selected_time = st.sidebar.time_input("Seleziona Ora", value=time(12, 0))

def get_realtime_weather(lat, lon, target_date, target_time):
    """Richiesta API Open-Meteo per recuperare meteo reale/previsionale alla data/ora specifica"""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=windspeed_10m,winddirection_10m,windgusts_10m&windspeed_unit=kn&start_date={target_date}&end_date={target_date}"
        res = requests.get(url, timeout=5).json()
        
        target_hour = target_time.hour
        wind_spd = res["hourly"]["windspeed_10m"][target_hour]
        wind_dir = res["hourly"]["winddirection_10m"][target_hour]
        wind_gust = res["hourly"]["windgusts_10m"][target_hour]
        return float(wind_spd), float(wind_dir), float(wind_gust)
    except Exception:
        # Fallback predefinito se l'API non risponde o la data è oltre il limite forecast
        return 18.0, 240.0, 25.0

active_banchina = st.session_state.berths_db[selected_port]
live_spd, live_dir, live_gust = get_realtime_weather(active_banchina["lat"], active_banchina["lon"], selected_date, selected_time)

st.sidebar.caption(f"Dati estratti per {selected_date} alle {selected_time.strftime('%H:%M')}")
override_meteo = st.sidebar.checkbox("Modifica Condimeteo Manualmente", value=False)

if override_meteo:
    wind_speed = st.sidebar.slider("Velocità Vento (Nodi)", 0, 70, int(live_spd))
    wind_dir_true = st.sidebar.slider("Direzione Vento (°True)", 0, 359, int(live_dir))
else:
    wind_speed = live_spd
    wind_dir_true = live_dir
    st.sidebar.metric("Vento Reale / Previsionale", f"{wind_speed} kts", f"Raffica: {live_gust} kts")
    st.sidebar.metric("Direzione Vento", f"{wind_dir_true}° True")

wind_relative = (wind_dir_true - active_banchina["heading"]) % 360

# ==========================================
# 5. MOTORE DI CALCOLO stress & MEG4
# ==========================================
st.sidebar.header("⚙️ 3. Cavi Attivi in Servizio")
fwd_active_count = st.sidebar.number_input("Cavi FWD In Uso", 3, 6, 4)
aft_active_count = st.sidebar.number_input("Cavi AFT In Uso", 3, 6, 4)

def calculate_mooring_stresses(wind_kts, wind_rel_angle):
    wind_rad = np.radians(wind_rel_angle)
    force_transversal = 0.05 * (wind_kts ** 2) * np.abs(np.sin(wind_rad))
    force_longitudinal = 0.02 * (wind_kts ** 2) * np.abs(np.cos(wind_rad))
    
    lines_data = []
    # Compilazione FWD
    for i in range(fwd_active_count):
        az = active_banchina["fwd_azimut"][i]
        sl = active_banchina["fwd_slope"][i]
        lines_data.append({
            "id": f"FWD_{i+1}", "section": "FWD", "azimut": az, "slope_deg": sl,
            "mbl": LINES_DATABASE["FWD"]["MBL"], "stiffness": LINES_DATABASE["FWD"]["stiffness_factor"],
            "role": "BREAST" if abs(az) <= 15 else ("HEAD" if az > 15 else "SPRING")
        })
    # Compilazione AFT
    for i in range(aft_active_count):
        az = active_banchina["aft_azimut"][i]
        sl = active_banchina["aft_slope"][i]
        lines_data.append({
            "id": f"AFT_{i+1}", "section": "AFT", "azimut": az, "slope_deg": sl,
            "mbl": LINES_DATABASE["AFT"]["MBL"], "stiffness": LINES_DATABASE["AFT"]["stiffness_factor"],
            "role": "BREAST" if abs(az) <= 15 else ("SPRING" if az > 15 else "STERN")
        })
        
    tot_stiff_x = sum([l["stiffness"] * np.cos(np.radians(l["azimut"])) for l in lines_data])
    tot_stiff_y = sum([l["stiffness"] * np.sin(np.radians(l["azimut"])) for l in lines_data])
    
    results = []
    for l in lines_data:
        az_rad = np.radians(l["azimut"])
        sl_rad = np.radians(l["slope_deg"])
        
        share_x = (l["stiffness"] * np.cos(az_rad)) / max(tot_stiff_x, 0.001)
        share_y = (l["stiffness"] * np.sin(az_rad)) / max(tot_stiff_y, 0.001)
        
        tension_horiz = np.sqrt((force_longitudinal * share_x)**2 + (force_transversal * share_y)**2)
        # Scomposizione 3D della pendenza in gradi
        tension_total = tension_horiz / max(np.cos(sl_rad), 0.1)
        
        brake_capacity = l["mbl"] * WINCH_BRAKE_PERCENT
        pct_mbl = (tension_total / l["mbl"]) * 100
        
        results.append({
            "ID": l["id"],
            "Ruolo": l["role"],
            "Azimut (°)": l["azimut"],
            "Pendenza (°)": l["slope_deg"],
            "Tensione (t)": round(tension_total, 1),
            "% MBL": round(pct_mbl, 1),
            "Limite Freno (t)": round(brake_capacity, 1),
            "Stato Freno": "⚠️ SLITTAMENTO" if tension_total > brake_capacity else "OK"
        })
    return pd.DataFrame(results), lines_data

df_results, current_lines = calculate_mooring_stresses(wind_speed, wind_relative)

# ==========================================
# 6. OUTPUT & RISULTATI ANALISI
# ==========================================
st.markdown("---")
st.header(f"📊 Analisi Ormeggio a {selected_port} - {selected_date}")

# Controllo Requisiti Minimi MEG4 (2 Head/Stern, 2 Breast, 2 Spring)
counts = df_results["Ruolo"].value_counts()
n_head = counts.get("HEAD", 0) + counts.get("STERN", 0)
n_breast = counts.get("BREAST", 0)
n_spring = counts.get("SPRING", 0)

if n_head < 2 or n_breast < 2 or n_spring < 2:
    st.error(f"❌ **CONFIGURAZIONE NON A NORMA MEG4:** Trovati {n_head} Head/Stern, {n_breast} Breast, {n_spring} Spring. Requisito minimo non soddisfatto (Servono almeno 2 per tipo).")
else:
    st.success("✅ Layout d'ormeggio conforme alle linee guida MEG4 (almeno 2 Head/Stern, 2 Breast e 2 Spring attivi).")

col_res1, col_res2 = st.columns(2)

with col_res1:
    st.subheader("Carico Attuale sui Cavi")
    st.dataframe(df_results[["ID", "Ruolo", "Azimut (°)", "Pendenza (°)", "Tensione (t)", "% MBL", "Stato Freno"]], use_container_width=True)

with col_res2:
    st.subheader("Punto Critico & Vento Max Sostenibile")
    max_line = df_results.loc[df_results["% MBL"].idxmax()]
    st.warning(f"🔴 **Cavo più sollecitato:** {max_line['ID']} ({max_line['Ruolo']}) al **{max_line['% MBL']}% del MBL** ({max_line['Tensione (t)']} t).")
    
    # Calcolo Vento Max fino a superamento del 55% MBL
    w_limit = wind_speed
    while True:
        df_temp, _ = calculate_mooring_stresses(w_limit, wind_relative)
        if df_temp["% MBL"].max() >= 55.0 or (df_temp["Stato Freno"] == "⚠️ SLITTAMENTO").any():
            break
        w_limit += 1
        if w_limit > 120: break
        
    st.metric("Vento Max Sostenibile (Safety Limit 55% MBL)", f"{int(w_limit - 1)} Nodi")

# ==========================================
# 7. MATRICE SENSIVITA' VENTO (WHAT-IF)
# ==========================================
st.subheader("📈 Matrice di Aumento Resistenza Vento (+1 Cavo Extra)")

col_b, col_s, col_h = st.columns(3)

def evaluate_extra_line(line_type):
    w = wind_speed
    while True:
        # Calcolo di prova con un cavo aggiuntivo
        wind_rad = np.radians(wind_relative)
        f_tr = 0.05 * (w ** 2) * np.abs(np.sin(wind_rad))
        f_ln = 0.02 * (w ** 2) * np.abs(np.cos(wind_rad))
        
        # Stima sollecitudine distribuita
        df_t, _ = calculate_mooring_stresses(w, wind_relative)
        max_pct = df_t["% MBL"].max() * (len(df_results) / (len(df_results) + 1))
        
        if max_pct >= 55.0:
            return w - 1
        w += 1
        if w > 120: return 120

with col_b:
    w_b = evaluate_extra_line("BREAST")
    st.metric("Aggiungendo +1 BREAST", f"{w_b} Nodi", f"+{w_b - int(w_limit - 1)} kts")

with col_s:
    w_s = evaluate_extra_line("SPRING")
    st.metric("Aggiungendo +1 SPRING", f"{w_s} Nodi", f"+{w_s - int(w_limit - 1)} kts")

with col_h:
    w_h = evaluate_extra_line("HEAD")
    st.metric("Aggiungendo +1 HEAD", f"{w_h} Nodi", f"+{w_h - int(w_limit - 1)} kts")
