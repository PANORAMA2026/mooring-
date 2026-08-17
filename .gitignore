import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import requests

# Set page configuration
st.set_page_config(
    page_title="Mooring Analysis & Ship Profile - Carnival Panorama",
    page_icon="⚓",
    layout="wide"
)

# ---------------------------------------------------------
# 1. INITIALIZE SHIP PROFILE & MOORING DATA IN SESSION STATE
# ---------------------------------------------------------

default_ship_profile = {
    "ship_name": "Carnival Panorama",
    "call_sign": "H3WI",
    "imo": "9767091",
    "loa": 323.44,       # meters
    "lbp": 286.9,        # meters
    "beam": 37.20,       # meters
    "max_beam": 49.40,   # meters
    "draft": 8.55,       # meters
    "displacement": 70028, # metric tons
    "air_draft": 63.25,  # meters
    "windage_front": 1450.0, # m2 (estimated transverse projected wind area)
    "windage_side": 12022.5, # m2 (lateral sail area)
    "underwater_side": 286.9 * 8.55, # m2 approx underwater lateral area
    "bow_thrusters_kw": 7500, # 3 x 2500 kW
    "azipods_kw": 33000       # 2 x 16.5 MW
}

default_fwd_ropes = [
    {"Rope": "M1", "Winch": "Winch 4", "Type": "BEXCO-Maxiflex HMPE", "Length_m": 150, "Dia_mm": 42, "MBL_t": 135, "Function": "Spring"},
    {"Rope": "M2", "Winch": "Winch 4", "Type": "BEXCO-Maxiflex HMPE", "Length_m": 150, "Dia_mm": 42, "MBL_t": 135, "Function": "Spring"},
    {"Rope": "G1", "Winch": "Winch 4", "Type": "Gleistein Dyneema", "Length_m": 190, "Dia_mm": 54, "MBL_t": 185, "Function": "Head Line"},
    {"Rope": "G2", "Winch": "Winch 4", "Type": "Gleistein Dyneema", "Length_m": 190, "Dia_mm": 54, "MBL_t": 185, "Function": "Head Line"},
    {"Rope": "B4", "Winch": "Winch 1", "Type": "BexcoFlex Polyester/Bexcord", "Length_m": 200, "Dia_mm": 60, "MBL_t": 72, "Function": "Breast Line"},
    {"Rope": "B5", "Winch": "Winch 2", "Type": "BexcoFlex Polyester/Bexcord", "Length_m": 200, "Dia_mm": 60, "MBL_t": 72, "Function": "Breast Line"},
    {"Rope": "B6", "Winch": "Winch 2", "Type": "BexcoFlex Polyester/Bexcord", "Length_m": 200, "Dia_mm": 60, "MBL_t": 72, "Function": "Breast Line"},
    {"Rope": "G3", "Winch": "Winch 3", "Type": "Gleistein Dyneema", "Length_m": 190, "Dia_mm": 54, "MBL_t": 185, "Function": "Head Line"},
    {"Rope": "E12", "Winch": "Additional", "Type": "Lankhorst Eurofloat", "Length_m": 220, "Dia_mm": 72, "MBL_t": 85, "Function": "Reserve"},
    {"Rope": "E14", "Winch": "Additional", "Type": "Lankhorst Eurofloat", "Length_m": 220, "Dia_mm": 72, "MBL_t": 85, "Function": "Reserve"}
]

default_aft_ropes = [
    {"Rope": "L2", "Winch": "Winch 3", "Type": "Lanko Force Dyneema SK78", "Length_m": 150, "Dia_mm": 48, "MBL_t": 160, "Function": "Stern Line"},
    {"Rope": "L4", "Winch": "Winch 3", "Type": "Lanko Force Dyneema SK78", "Length_m": 150, "Dia_mm": 48, "MBL_t": 160, "Function": "Stern Line"},
    {"Rope": "B1", "Winch": "Winch 5", "Type": "BexcoFlex Polyester/Bexcord", "Length_m": 200, "Dia_mm": 60, "MBL_t": 72, "Function": "Breast Line"},
    {"Rope": "B2", "Winch": "Winch 5", "Type": "BexcoFlex Polyester/Bexcord", "Length_m": 200, "Dia_mm": 60, "MBL_t": 72, "Function": "Breast Line"},
    {"Rope": "G5", "Winch": "Winch 3", "Type": "Gleistein Dyneema", "Length_m": 190, "Dia_mm": 54, "MBL_t": 185, "Function": "Stern Line"},
    {"Rope": "G6", "Winch": "Winch 3", "Type": "Gleistein Dyneema", "Length_m": 190, "Dia_mm": 54, "MBL_t": 185, "Function": "Stern Line"},
    {"Rope": "G1", "Winch": "Winch 4", "Type": "Gleistein Dyneema", "Length_m": 190, "Dia_mm": 54, "MBL_t": 185, "Function": "Stern Line"},
    {"Rope": "G2", "Winch": "Winch 4", "Type": "Gleistein Dyneema", "Length_m": 190, "Dia_mm": 54, "MBL_t": 185, "Function": "Stern Line"},
    {"Rope": "G3", "Winch": "Winch 6", "Type": "Gleistein Dyneema", "Length_m": 190, "Dia_mm": 54, "MBL_t": 185, "Function": "Stern Line"},
    {"Rope": "G4", "Winch": "Winch 6", "Type": "Gleistein Dyneema", "Length_m": 190, "Dia_mm": 54, "MBL_t": 185, "Function": "Stern Line"}
]

if "ship_profile" not in st.session_state:
    st.session_state["ship_profile"] = default_ship_profile.copy()

if "fwd_ropes" not in st.session_state:
    st.session_state["fwd_ropes"] = pd.DataFrame(default_fwd_ropes)

if "aft_ropes" not in st.session_state:
    st.session_state["aft_ropes"] = pd.DataFrame(default_aft_ropes)

# ---------------------------------------------------------
# 2. HELPER FUNCTIONS FOR CALCULATIONS & WEATHER API
# ---------------------------------------------------------

def fetch_weather(lat, lon):
    """Fetch live wind & weather data from Open-Meteo API"""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        res = requests.get(url, timeout=5).json()
        if "current_weather" in res:
            cw = res["current_weather"]
            return {
                "wind_speed_kts": round(cw["windspeed"] * 0.539957, 1), # km/h to knots
                "wind_dir_deg": cw["winddirection"],
                "temp_c": cw.get("temperature", 20.0)
            }
    except Exception as e:
        st.error(f"Errore recupero meteo: {e}")
    return None

def calculate_environmental_forces(profile, wind_spd_kts, wind_dir_rel, curr_spd_kts, curr_dir_rel):
    """
    OCIMF MEG4 simplified aerodynamic and hydrodynamic force estimation
    Forces in Metric Tons (tonne)
    """
    # Density of air (1.225 kg/m3) and sea water (1025 kg/m3)
    rho_air = 1.225
    rho_water = 1025.0
    
    # Conversions
    V_w = wind_spd_kts * 0.514444 # kts to m/s
    V_c = curr_spd_kts * 0.514444 # kts to m/s
    
    rad_w = np.radians(wind_dir_rel)
    rad_c = np.radians(curr_dir_rel)
    
    # Wind Force Coefficients (approximate OCIMF for cruise ships)
    Cx_w = -0.6 * np.cos(rad_w) # Longitudinal
    Cy_w = 0.95 * np.sin(rad_w) # Transverse
    
    # Wind Forces (N -> Tonnes)
    F_wind_x = 0.5 * rho_air * (V_w**2) * profile["windage_front"] * Cx_w / 9806.65
    F_wind_y = 0.5 * rho_air * (V_w**2) * profile["windage_side"] * Cy_w / 9806.65
    
    # Current Force Coefficients
    Cx_c = -0.1 * np.cos(rad_c)
    Cy_c = 0.8 * np.sin(rad_c)
    
    # Current Forces (N -> Tonnes)
    F_curr_x = 0.5 * rho_water * (V_c**2) * (profile["beam"] * profile["draft"]) * Cx_c / 9806.65
    F_curr_y = 0.5 * rho_water * (V_c**2) * profile["underwater_side"] * Cy_c / 9806.65
    
    # Total Forces
    F_total_x = F_wind_x + F_curr_x
    F_total_y = F_wind_y + F_curr_y
    F_total_mag = np.hypot(F_total_x, F_total_y)
    
    return {
        "F_wind_x": F_wind_x, "F_wind_y": F_wind_y,
        "F_curr_x": F_curr_x, "F_curr_y": F_curr_y,
        "F_total_x": F_total_x, "F_total_y": F_total_y,
        "F_total_mag": F_total_mag
    }

# ---------------------------------------------------------
# 3. STREAMLIT NAVIGATION & TABS
# ---------------------------------------------------------

st.title("⚓ Mooring Analysis & Operational System")
st.caption(f"Vessel: **{st.session_state['ship_profile']['ship_name']}** | Call Sign: {st.session_state['ship_profile']['call_sign']} | IMO: {st.session_state['ship_profile']['imo']}")

tabs = st.tabs(["📊 Mooring & Forces Analysis", "🚢 Ship Profile & Edit", "🧵 Cable Inventory (FWD & AFT)", "🌤️ Weather & Port Data"])

# ---------------------------------------------------------
# TAB 1: MOORING & FORCES ANALYSIS
# ---------------------------------------------------------
with tabs[0]:
    st.header("Analisi delle Forze di Ormeggio (OCIMF MEG4)")
    
    col_meteo, col_results = st.columns([1, 2])
    
    with col_meteo:
        st.subheader("⚙️ Condizioni Operative")
        
        wind_spd = st.slider("Velocità Vento (Nodi)", 0.0, 60.0, 25.0, 0.5)
        wind_dir = st.slider("Direzione Vento Relativa (° rispetto alla prua)", 0, 360, 45, 5)
        
        st.divider()
        curr_spd = st.slider("Velocità Corrente (Nodi)", 0.0, 5.0, 0.8, 0.1)
        curr_dir = st.slider("Direzione Corrente Relativa (° rispetto alla prua)", 0, 360, 90, 5)
        
        active_fwd_ropes = st.number_input("Cavi attivi a Prua (FWD)", min_value=1, max_value=12, value=4)
        active_aft_ropes = st.number_input("Cavi attivi a Poppa (AFT)", min_value=1, max_value=12, value=4)
        
    with col_results:
        forces = calculate_environmental_forces(
            st.session_state["ship_profile"], 
            wind_spd, wind_dir, 
            curr_spd, curr_dir
        )
        
        st.subheader("📈 Risultati del Calcolo Forze")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Spinta Trasversale Vento (Lateral)", f"{abs(forces['F_wind_y']):.1f} t")
        m2.metric("Spinta Trasversale Corrente", f"{abs(forces['F_curr_y']):.1f} t")
        m3.metric("Forza Totale Trasversale", f"{abs(forces['F_total_y']):.1f} t")
        
        m4, m5, m6 = st.columns(3)
        m4.metric("Spinta Longitudinale Vento", f"{abs(forces['F_wind_x']):.1f} t")
        m5.metric("Spinta Longitudinale Corrente", f"{abs(forces['F_curr_x']):.1f} t")
        m6.metric("Forza Totale Risultante", f"{forces['F_total_mag']:.1f} t")
        
        st.divider()
        st.subheader("🛡️ Carico Medio per Cavo & Safety Verification")
        
        total_active_lines = active_fwd_ropes + active_aft_ropes
        load_per_line = forces["F_total_mag"] / total_active_lines if total_active_lines > 0 else 0
        
        # Reference MBL (using standard Dyneema 185t or BexcoFlex 72t average)
        avg_mbl = 130.0 # metric tons
        load_percentage = (load_per_line / avg_mbl) * 100 if avg_mbl > 0 else 0
        
        c1, c2 = st.columns(2)
        c1.metric("Carico medio stimato per cavo", f"{load_per_line:.1f} t")
        c2.metric("% di MBL Stimato", f"{load_percentage:.1f}%")
        
        if load_percentage > 55.0:
            st.error("⚠️ ATTENZIONE: Il carico per cavo supera il 55% del MBL (Limite di Sicurezza OCIMF MEG4)! Rinforzare l'ormeggio o attivare verricelli aggiuntivi.")
        elif load_percentage > 40.0:
            st.warning("⚠️ AVVISO: Carico elevato (> 40% MBL). Monitorare con attenzione le stazioni d'ormeggio.")
        else:
            st.success("✅ Condizioni d'ormeggio nei limiti di sicurezza standard (< 50% MBL).")
            
        # Diagram Plot
        st.subheader("🎯 Diagramma Polare della Direzione Forze")
        fig, ax = plt.subplots(subplot_kw={'projection': 'polar'}, figsize=(4, 4))
        
        # Wind vector
        ax.annotate('', xy=(np.radians(wind_dir), wind_spd), xytext=(0,0),
                    arrowprops=dict(facecolor='blue', edgecolor='blue', arrowstyle='->', lw=2),
                    label='Vento')
        
        # Current vector (scaled up for visualization)
        ax.annotate('', xy=(np.radians(curr_dir), curr_spd * 10), xytext=(0,0),
                    arrowprops=dict(facecolor='green', edgecolor='green', arrowstyle='->', lw=2),
                    label='Corrente x10')
        
        ax.set_theta_zero_location('N')
        ax.set_theta_direction(-1)
        ax.set_title("Vento & Corrente (Relativi alla Prua 0°)", fontsize=10)
        st.pyplot(fig)

# ---------------------------------------------------------
# TAB 2: SHIP PROFILE & EDIT
# ---------------------------------------------------------
with tabs[1]:
    st.header("🚢 Profilo Nave & Dimensioni (Salvato in Memoria)")
    st.info("I parametri della nave sono pre-caricati con i dati della Carnival Panorama. È possibile modificarli e salvarli per questa sessione.")
    
    prof = st.session_state["ship_profile"]
    
    with st.form("ship_profile_form"):
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            ship_name = st.text_input("Nome Nave", prof["ship_name"])
            call_sign = st.text_input("Call Sign", prof["call_sign"])
            imo = st.text_input("IMO Number", prof["imo"])
            loa = st.number_input("Lunghezza Fuori Tutto - LOA (m)", value=float(prof["loa"]))
            
        with col_b:
            lbp = st.number_input("Lunghezza tra le Perpendicolari - LBP (m)", value=float(prof["lbp"]))
            beam = st.number_input("Larghezza - Beam (m)", value=float(prof["beam"]))
            max_beam = st.number_input("Larghezza Massima (m)", value=float(prof["max_beam"]))
            draft = st.number_input("Pescaggio - Draft (m)", value=float(prof["draft"]))
            
        with col_c:
            displacement = st.number_input("Dislocamento (tonnellate)", value=float(prof["displacement"]))
            windage_side = st.number_input("Area Velica Laterale (m²)", value=float(prof["windage_side"]))
            windage_front = st.number_input("Area Frontale (m²)", value=float(prof["windage_front"]))
            thrusters = st.number_input("Potenza Bow Thrusters (kW)", value=int(prof["bow_thrusters_kw"]))
            
        submit_btn = st.form_submit_button("💾 Salva Modifiche Profilo Nave")
        
        if submit_btn:
            st.session_state["ship_profile"].update({
                "ship_name": ship_name,
                "call_sign": call_sign,
                "imo": imo,
                "loa": loa,
                "lbp": lbp,
                "beam": beam,
                "max_beam": max_beam,
                "draft": draft,
                "displacement": displacement,
                "windage_side": windage_side,
                "windage_front": windage_front,
                "underwater_side": lbp * draft,
                "bow_thrusters_kw": thrusters
            })
            st.success("Profilo Nave aggiornato con successo!")

# ---------------------------------------------------------
# TAB 3: CABLE INVENTORY (FWD & AFT)
# ---------------------------------------------------------
with tabs[2]:
    st.header("🧵 Gestione Distribuzione Cavi d'Ormeggio")
    st.write("Configurazione estorta dal file Excel *Mooring Rope Summary*. Puoi aggiungere o modificare le caratteristiche dei cavi.")
    
    subtab1, subtab2 = st.tabs(["Prua (FWD MOORING)", "Poppa (AFT MOORING)"])
    
    with subtab1:
        st.subheader("Inventario Cavi Prua (FWD)")
        edited_fwd = st.data_editor(
            st.session_state["fwd_ropes"], 
            num_rows="dynamic", 
            key="fwd_editor"
        )
        st.session_state["fwd_ropes"] = edited_fwd
        
    with subtab2:
        st.subheader("Inventario Cavi Poppa (AFT)")
        edited_aft = st.data_editor(
            st.session_state["aft_ropes"], 
            num_rows="dynamic", 
            key="aft_editor"
        )
        st.session_state["aft_ropes"] = edited_aft

# ---------------------------------------------------------
# TAB 4: WEATHER & PORT DATA
# ---------------------------------------------------------
with tabs[3]:
    st.header("🌤️ Integrazione Meteo Live & Dati Porto")
    
    st.write("Seleziona una destinazione/porto o inserisci le coordinate geografiche per recuperare i dati meteo in tempo reale tramite Open-Meteo API.")
    
    ports = {
        "Long Beach, CA (USA)": {"lat": 33.7701, "lon": -118.1937},
        "Cabo San Lucas (Mexico)": {"lat": 22.8905, "lon": -109.9167},
        "Puerto Vallarta (Mexico)": {"lat": 20.6534, "lon": -105.2253},
        "Ensenada (Mexico)": {"lat": 31.8667, "lon": -116.5964},
        "Mazatlán (Mexico)": {"lat": 23.2167, "lon": -106.4167}
    }
    
    selected_port = st.selectbox("Seleziona Porto predefinito:", list(ports.keys()))
    
    col_lat, col_lon = st.columns(2)
    lat_val = col_lat.number_input("Latitudine", value=ports[selected_port]["lat"], format="%.4f")
    lon_val = col_lon.number_input("Longitudine", value=ports[selected_port]["lon"], format="%.4f")
    
    if st.button("📡 Recupera Meteo Live"):
        data = fetch_weather(lat_val, lon_val)
        if data:
            st.success("Dati Meteo aggiornati con successo!")
            w1, w2, w3 = st.columns(3)
            w1.metric("Velocità Vento", f"{data['wind_speed_kts']} kts")
            w2.metric("Direzione Vento", f"{data['wind_dir_deg']}°")
            w3.metric("Temperatura", f"{data['temp_c']} °C")
