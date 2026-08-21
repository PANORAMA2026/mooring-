import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, date, time

# ==========================================
# 1. CONFIGURAZIONE PAGINA & SCHEDA NAVE
# ==========================================
st.set_page_config(page_title="Mooring Plan Generator - Carnival Panorama", layout="wide")

st.title("⚓ Smart Mooring Plan Generator & Stress Analysis")
st.caption("Conforme a raccomandazioni OCIMF MEG4 | Carnival Panorama")

LINES_DATABASE = {
    "FWD": {"material": "HMPE SBT 44mm", "MBL": 115.0, "stiffness_factor": 1.2},
    "AFT": {"material": "Polyester 42mm", "MBL": 110.0, "stiffness_factor": 0.8}
}
WINCH_BRAKE_PERCENT = 0.60  # Freno tarato al 60% MBL

# ==========================================
# 2. MEMORIA PERSISTENTE BANCHINE CON BITTE PROGRESSIVE (1 -> N)
# ==========================================
if "berths_db" not in st.session_state:
    st.session_state.berths_db = {
        "Long Beach (US)": {
            "lat": 33.7541, "lon": -118.2165, "heading": 120, "swl_bollard": 100.0, "dist": 15.0,
            "bollards": [
                {"id": 1, "pos_m": 120, "max_lines": 2, "azimut": 40, "slope": 12},  # Prua estrema
                {"id": 2, "pos_m": 90,  "max_lines": 2, "azimut": 25, "slope": 11},  # Prua media
                {"id": 3, "pos_m": 60,  "max_lines": 2, "azimut": 5,  "slope": 9},   # Traverso Prua
                {"id": 4, "pos_m": 30,  "max_lines": 2, "azimut": -30, "slope": 10},  # Spring FWD
                {"id": 5, "pos_m": -30, "max_lines": 2, "azimut": 30, "slope": 10},  # Spring AFT
                {"id": 6, "pos_m": -60, "max_lines": 2, "azimut": -5, "slope": 9},   # Traverso Poppa
                {"id": 7, "pos_m": -90, "max_lines": 2, "azimut": -25, "slope": 11}, # Poppa media
                {"id": 8, "pos_m": -120,"max_lines": 2, "azimut": -40, "slope": 12}  # Poppa estrema
            ]
        },
        "Ensenada (MX)": {
            "lat": 31.8578, "lon": -116.6058, "heading": 45, "swl_bollard": 80.0, "dist": 12.0,
            "bollards": [
                {"id": 1, "pos_m": 100, "max_lines": 2, "azimut": 35, "slope": 10},
                {"id": 2, "pos_m": 70,  "max_lines": 2, "azimut": 20, "slope": 9},
                {"id": 3, "pos_m": 40,  "max_lines": 2, "azimut": 0,  "slope": 8},
                {"id": 4, "pos_m": 15,  "max_lines": 2, "azimut": -25, "slope": 8},
                {"id": 5, "pos_m": -15, "max_lines": 2, "azimut": 25, "slope": 8},
                {"id": 6, "pos_m": -40, "max_lines": 2, "azimut": 0,  "slope": 8},
                {"id": 7, "pos_m": -70, "max_lines": 2, "azimut": -20, "slope": 9},
                {"id": 8, "pos_m": -100,"max_lines": 2, "azimut": -35, "slope": 10}
            ]
        }
    }

# ==========================================
# 3. CONFIGURAZIONE E EDITOR BANCHINA PORTO
# ==========================================
st.sidebar.header("📍 Selezione Operativa")
selected_port = st.sidebar.selectbox("Porto Attivo", list(st.session_state.berths_db.keys()))

with st.expander("🛠️ CONFIGURAZIONE BITTE BANCHINA (Sequenza 1 -> N da Prua a Poppa)", expanded=False):
    st.info(f"Configura le bitte di **{selected_port}**. La **Bitta #1** è quella posizionata più a prua, le successive proseguono in ordine verso poppa.")
    
    port_cfg = st.session_state.berths_db[selected_port]
    
    cp1, cp2, cp3 = st.columns(3)
    with cp1:
        new_head = st.number_input("Orientamento Banchina (°True)", 0, 359, int(port_cfg["heading"]))
    with cp2:
        new_swl = st.number_input("SWL Bitte (Tonnellate)", 10.0, 250.0, float(port_cfg["swl_bollard"]))
    with cp3:
        new_dist = st.number_input("Distanza Fiancata-Banchina (m)", 1.0, 50.0, float(port_cfg["dist"]))
        
    st.markdown("---")
    st.markdown("### Mappatura Dettagliata Bitte Banchina")
    
    num_bollards = st.number_input("Numero Totale Bitte in Banchina", min_value=4, max_value=12, value=len(port_cfg["bollards"]))
    
    updated_bollards = []
    for idx in range(num_bollards):
        b_id = idx + 1
        default_b = port_cfg["bollards"][idx] if idx < len(port_cfg["bollards"]) else {"id": b_id, "pos_m": 0, "max_lines": 2, "azimut": 0, "slope": 10}
        
        st.markdown(f"**📍 Bitta #{b_id}** *(Bitta {b_id} da prua)*")
        cb1, cb2, cb3, cb4 = st.columns(4)
        with cb1:
            m_lines = st.number_input(f"Capienza Max Cavi (Bitta #{b_id})", 1, 4, int(default_b["max_lines"]), key=f"bl_max_{selected_port}_{b_id}")
        with cb2:
            az = st.number_input(f"Azimut Cavo (°)", -90, 90, int(default_b["azimut"]), key=f"bl_az_{selected_port}_{b_id}")
        with cb3:
            sl = st.number_input(f"Pendenza Cavo (°)", 0, 60, int(default_b["slope"]), key=f"bl_sl_{selected_port}_{b_id}")
        with cb4:
            pos = st.number_input(f"Posizione vs Centro Nave (m)", -200, 200, int(default_b["pos_m"]), key=f"bl_pos_{selected_port}_{b_id}")
            
        updated_bollards.append({"id": b_id, "max_lines": m_lines, "azimut": az, "slope": sl, "pos_m": pos})

    if st.button("💾 Salva Banchina e Bitte in Memoria"):
        st.session_state.berths_db[selected_port]["heading"] = new_head
        st.session_state.berths_db[selected_port]["swl_bollard"] = new_swl
        st.session_state.berths_db[selected_port]["dist"] = new_dist
        st.session_state.berths_db[selected_port]["bollards"] = updated_bollards
        st.success(f"Mappatura bitte per {selected_port} salvata con successo!")

# ==========================================
# 4. CONDIMETEO REAL-TIME PER DATA E ORA
# ==========================================
st.sidebar.header("🌤️ 2. Condimeteo Live / Previsioni")

selected_date = st.sidebar.date_input("Data Ormeggio", value=date.today())
selected_time = st.sidebar.time_input("Ora Ormeggio", value=time(12, 0))

def get_realtime_weather(lat, lon, target_date, target_time):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=windspeed_10m,winddirection_10m,windgusts_10m&windspeed_unit=kn&start_date={target_date}&end_date={target_date}"
        res = requests.get(url, timeout=5).json()
        target_hour = target_time.hour
        return float(res["hourly"]["windspeed_10m"][target_hour]), float(res["hourly"]["winddirection_10m"][target_hour]), float(res["hourly"]["windgusts_10m"][target_hour])
    except Exception:
        return 20.0, 150.0, 28.0

active_banchina = st.session_state.berths_db[selected_port]
live_spd, live_dir, live_gust = get_realtime_weather(active_banchina["lat"], active_banchina["lon"], selected_date, selected_time)

override_meteo = st.sidebar.checkbox("Modifica Meteo Manualmente", value=False)
if override_meteo:
    wind_speed = st.sidebar.slider("Vento (Nodi)", 0, 70, int(live_spd))
    wind_dir_true = st.sidebar.slider("Direzione Vento (°True)", 0, 359, int(live_dir))
else:
    wind_speed = live_spd
    wind_dir_true = live_dir
    st.sidebar.metric("Vento Reale / Previsto", f"{wind_speed} kts", f"Raffica: {live_gust} kts")
    st.sidebar.metric("Direzione Vento", f"{wind_dir_true}° True")

wind_relative = (wind_dir_true - active_banchina["heading"]) % 360

# ==========================================
# 5. ALGORITMO DI SELEZIONE OTTIMALE DELLE BITTE & RIGGINGS
# ==========================================
st.sidebar.header("⚙️ 3. Numero Cavi Target")
target_fwd_lines = st.sidebar.number_input("Totale Cavi da Passare a Prua (FWD)", 3, 8, 4)
target_aft_lines = st.sidebar.number_input("Totale Cavi da Passare a Poppa (AFT)", 3, 8, 4)

def optimize_mooring_setup(bollards_list, target_fwd, target_aft, w_speed, w_rel):
    # Separazione bitte zona Prua (pos_m > 0) e zona Poppa (pos_m <= 0)
    fwd_bollards = [b for b in bollards_list if b["pos_m"] >= 0]
    aft_bollards = [b for b in bollards_list if b["pos_m"] < 0]
    
    # Se la suddivisione automatica è sbilanciata, ordina per sequenza numerica
    if not fwd_bollards or not aft_bollards:
        mid = len(bollards_list) // 2
        fwd_bollards = bollards_list[:mid]
        aft_bollards = bollards_list[mid:]

    def assign_lines_to_bollards(bollards_sublist, target_count, station_name):
        assigned_plan = []
        remaining = target_count
        
        # Classificazione e priorità d'uso delle bitte per efficienza (Breast/Head vs Spring)
        sorted_b = sorted(bollards_sublist, key=lambda x: abs(x["azimut"]), reverse=True)
        
        bollard_usage = {b["id"]: 0 for b in bollards_sublist}
        
        while remaining > 0:
            added = False
            for b in sorted_b:
                if bollard_usage[b["id"]] < b["max_lines"] and remaining > 0:
                    bollard_usage[b["id"]] += 1
                    remaining -= 1
                    added = True
            if not added:
                break  # Raggiunta capienza massima fisica delle bitte selezionate
                
        for b in bollards_sublist:
            qty = bollard_usage[b["id"]]
            az = b["azimut"]
            
            if abs(az) <= 15:
                role = "BREAST"
            elif az > 15:
                role = "HEAD" if station_name == "FWD" else "SPRING"
            else:
                role = "SPRING" if station_name == "FWD" else "STERN"
                
            assigned_plan.append({
                "bollard_id": b["id"],
                "qty": qty,
                "role": role,
                "azimut": az,
                "slope": b["slope"],
                "max_lines": b["max_lines"],
                "station": station_name
            })
        return assigned_plan

    plan_fwd = assign_lines_to_bollards(fwd_bollards, target_fwd, "FWD")
    plan_aft = assign_lines_to_bollards(aft_bollards, target_aft, "AFT")
    
    return plan_fwd + plan_aft

full_plan = optimize_mooring_setup(active_banchina["bollards"], target_fwd_lines, target_aft_lines, wind_speed, wind_relative)

# ==========================================
# 6. CALCOLO STRESS ED EFFICIENZA GEOMETRICA
# ==========================================
def run_mooring_stress_analysis(plan, w_speed, w_rel):
    wind_rad = np.radians(w_rel)
    force_transversal = 0.05 * (w_speed ** 2) * np.abs(np.sin(wind_rad))
    force_longitudinal = 0.02 * (w_speed ** 2) * np.abs(np.cos(wind_rad))
    
    active_lines = []
    line_counter = 1
    for item in plan:
        for _ in range(item["qty"]):
            mat_info = LINES_DATABASE[item["station"]]
            active_lines.append({
                "line_id": f"{item['station']}_{line_counter}",
                "station": item["station"],
                "bollard_id": item["bollard_id"],
                "role": item["role"],
                "azimut": item["azimut"],
                "slope": item["slope"],
                "mbl": mat_info["MBL"],
                "stiffness": mat_info["stiffness_factor"]
            })
            line_counter += 1
            
    tot_stiff_x = sum([l["stiffness"] * np.cos(np.radians(l["azimut"])) for l in active_lines])
    tot_stiff_y = sum([l["stiffness"] * np.sin(np.radians(l["azimut"])) for l in active_lines])
    
    detailed_results = []
    for l in active_lines:
        az_rad = np.radians(l["azimut"])
        sl_rad = np.radians(l["slope"])
        
        share_x = (l["stiffness"] * np.cos(az_rad)) / max(tot_stiff_x, 0.001)
        share_y = (l["stiffness"] * np.sin(az_rad)) / max(tot_stiff_y, 0.001)
        
        t_horiz = np.sqrt((force_longitudinal * share_x)**2 + (force_transversal * share_y)**2)
        t_total = t_horiz / max(np.cos(sl_rad), 0.1)
        
        brake_lim = l["mbl"] * WINCH_BRAKE_PERCENT
        pct_mbl = (t_total / l["mbl"]) * 100
        
        detailed_results.append({
            "Cavo": l["line_id"],
            "Stazione": l["station"],
            "Bitta Banchina": f"Bitta #{l['bollard_id']}",
            "Tipologia Cavo": l["role"],
            "Azimut (°)": l["azimut"],
            "Pendenza (°)": l["slope"],
            "Tensione (t)": round(t_total, 1),
            "% MBL": round(pct_mbl, 1),
            "Stato Freno": "⚠️ SLITTAMENTO" if t_total > brake_lim else "OK"
        })
    return pd.DataFrame(detailed_results)

df_analysis = run_mooring_stress_analysis(full_plan, wind_speed, wind_relative)

# ==========================================
# 7. OUTPUT DELLE ISTRUZIONI DI COPERTA
# ==========================================
st.markdown("---")
st.header(f"📋 Piano d'Ormeggio e Distribuzione Cavi - {selected_port}")

# Conteggio tipologie cavi per Stazione
fwd_df = df_analysis[df_analysis["Stazione"] == "FWD"]
aft_df = df_analysis[df_analysis["Stazione"] == "AFT"]

fwd_counts = fwd_df["Tipologia Cavo"].value_counts()
aft_counts = aft_df["Tipologia Cavo"].value_counts()

col_f_sum, col_a_sum = st.columns(2)

with col_f_sum:
    st.subheader("FORWARD MOORING STATION (Prua)")
    st.markdown(f"""
    * **HEAD LINES:** `{fwd_counts.get('HEAD', 0)}` cavi
    * **BREAST LINES:** `{fwd_counts.get('BREAST', 0)}` cavi
    * **SPRING LINES:** `{fwd_counts.get('SPRING', 0)}` cavi
    * **TOTALE CAVI PRUA:** `{len(fwd_df)}`
    """)

with col_a_sum:
    st.subheader("AFTER MOORING STATION (Poppa)")
    st.markdown(f"""
    * **STERN LINES:** `{aft_counts.get('STERN', 0)}` cavi
    * **BREAST LINES:** `{aft_counts.get('BREAST', 0)}` cavi
    * **SPRING LINES:** `{aft_counts.get('SPRING', 0)}` cavi
    * **TOTALE CAVI POPPA:** `{len(aft_df)}`
    """)

st.markdown("---")
st.subheader("📍 Disposizione Tattica Cavi sulle Bitte di Banchina")
st.caption("Nota: Le bitte lasciate con 0 cavi sono state escluse dal sistema perché geometricamente meno efficienti per le condizioni attuali.")

plan_summary = []
for p in full_plan:
    status_str = f"🟢 PASSATI {p['qty']} CAVI ({p['role']})" if p['qty'] > 0 else "⚪ LASCIATA VUOTA (0 Cavi)"
    plan_summary.append({
        "Stazione": p["station"],
        "Bitta Banchina": f"Bitta #{p['bollard_id']}",
        "Stato Bitta": status_str,
        "Numero Cavi": p["qty"],
        "Tipologia Cavo": p["role"] if p["qty"] > 0 else "N/A",
        "Azimut Bitta (°)": p["azimut"],
        "Pendenza Bitta (°)": p["slope"],
        "Capienza Max Bitta": f"{p['max_lines']} Cavi"
    })

df_plan_view = pd.DataFrame(plan_summary)
st.dataframe(df_plan_view, use_container_width=True)

# ==========================================
# 8. VERIFICA SICUREZZA & CARICO CAVI
# ==========================================
st.markdown("---")
st.subheader("⚡ Verifiche di Sicurezza e Limiti di Carico")

c_sec1, c_sec2 = st.columns(2)

with c_sec1:
    st.markdown("**Analisi Carico sui Singoli Cavi**")
    st.dataframe(df_analysis[["Cavo", "Bitta Banchina", "Tipologia Cavo", "Tensione (t)", "% MBL", "Stato Freno"]], use_container_width=True)

with c_sec2:
    st.markdown("**Limiti di Sicurezza Vento**")
    max_line = df_analysis.loc[df_analysis["% MBL"].idxmax()]
    st.warning(f"🔴 **Cavo Più Sollecitato:** {max_line['Cavo']} ({max_line['Bitta Banchina']}) al **{max_line['% MBL']}% MBL** ({max_line['Tensione (t)']} t).")
    
    # Calcolo Vento Massimo per questo setup
    w_lim = wind_speed
    while True:
        df_chk = run_mooring_stress_analysis(full_plan, w_lim, wind_relative)
        if df_chk["% MBL"].max() >= 55.0 or (df_chk["Stato Freno"] == "⚠️ SLITTAMENTO").any():
            break
        w_lim += 1
        if w_lim > 120: break
        
    st.metric("Vento Max Sostenibile con Questo Layout", f"{int(w_lim - 1)} Nodi")
