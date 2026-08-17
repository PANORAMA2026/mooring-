import streamlit as st
import pandas as pd
import numpy as np
import io
import re
import os
import zipfile
import requests
from PIL import Image

try:
    import xlrd
except ImportError:
    xlrd = None

st.set_page_config(
    page_title="Mooring Analysis & Decision Support - Carnival Panorama",
    page_icon="🚢",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 1. ESTETICA & STILE
# -----------------------------------------------------------------------------
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #faafa8; }
    .metric-card {
        background-color: #1e222b;
        border: 1px solid #2e3644;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. INIZIALIZZAZIONE SESSION STATE
# -----------------------------------------------------------------------------
if "ship_specs" not in st.session_state:
    st.session_state["ship_specs"] = {
        "name": "Carnival Panorama",
        "loa": 323.6,
        "beam": 37.2,
        "draft": 8.5,
        "air_draft": 54.0,
        "displacement": 69200, # Tonnellate
        "wind_area_front": 1250, # m2
        "wind_area_side": 8400,  # m2
        "current_area_front": 180, # m2
        "current_area_side": 1200 # m2
    }

if "mooring_lines_db" not in st.session_state:
    st.session_state["mooring_lines_db"] = pd.DataFrame([
        {"ID": "FWD-1", "Posizione": "Prua", "Ruolo": "Head Line", "MBL_Design_Ton": 115, "Ore_Uso": 320, "Diametro_mm": 44, "Materiale": "SBT HMPE", "Bitta_Rif": "29", "Stato": "🟢 Buono"},
        {"ID": "FWD-2", "Posizione": "Prua", "Ruolo": "Head Line", "MBL_Design_Ton": 115, "Ore_Uso": 320, "Diametro_mm": 44, "Materiale": "SBT HMPE", "Bitta_Rif": "29", "Stato": "🟢 Buono"},
        {"ID": "FWD-3", "Posizione": "Prua", "Ruolo": "Breast Line", "MBL_Design_Ton": 115, "Ore_Uso": 890, "Diametro_mm": 44, "Materiale": "SBT HMPE", "Bitta_Rif": "28", "Stato": "🟡 Monitorare"},
        {"ID": "FWD-4", "Posizione": "Prua", "Ruolo": "Breast Line", "MBL_Design_Ton": 115, "Ore_Uso": 890, "Diametro_mm": 44, "Materiale": "SBT HMPE", "Bitta_Rif": "27", "Stato": "🟡 Monitorare"},
        {"ID": "FWD-5", "Posizione": "Prua", "Ruolo": "Spring Line", "MBL_Design_Ton": 115, "Ore_Uso": 410, "Diametro_mm": 44, "Materiale": "SBT HMPE", "Bitta_Rif": "25", "Stato": "🟢 Buono"},
        {"ID": "FWD-6", "Posizione": "Prua", "Ruolo": "Spring Line", "MBL_Design_Ton": 115, "Ore_Uso": 410, "Diametro_mm": 44, "Materiale": "SBT HMPE", "Bitta_Rif": "25", "Stato": "🟢 Buono"},
        {"ID": "AFT-1", "Posizione": "Poppa", "Ruolo": "Stern Line", "MBL_Design_Ton": 110, "Ore_Uso": 1120, "Diametro_mm": 42, "Materiale": "Polyester", "Bitta_Rif": "14", "Stato": "🔴 Da Sostituire"},
        {"ID": "AFT-2", "Posizione": "Poppa", "Ruolo": "Stern Line", "MBL_Design_Ton": 110, "Ore_Uso": 1120, "Diametro_mm": 42, "Materiale": "Polyester", "Bitta_Rif": "14", "Stato": "🔴 Da Sostituire"},
        {"ID": "AFT-3", "Posizione": "Poppa", "Ruolo": "Breast Line", "MBL_Design_Ton": 110, "Ore_Uso": 650, "Diametro_mm": 42, "Materiale": "Polyester", "Bitta_Rif": "16", "Stato": "🟢 Buono"},
        {"ID": "AFT-4", "Posizione": "Poppa", "Ruolo": "Breast Line", "MBL_Design_Ton": 110, "Ore_Uso": 650, "Diametro_mm": 42, "Materiale": "Polyester", "Bitta_Rif": "16", "Stato": "🟢 Buono"},
        {"ID": "AFT-5", "Posizione": "Poppa", "Ruolo": "Spring Line", "MBL_Design_Ton": 110, "Ore_Uso": 310, "Diametro_mm": 42, "Materiale": "Polyester", "Bitta_Rif": "19", "Stato": "🟢 Buono"},
        {"ID": "AFT-6", "Posizione": "Poppa", "Ruolo": "Spring Line", "MBL_Design_Ton": 110, "Ore_Uso": 310, "Diametro_mm": 42, "Materiale": "Polyester", "Bitta_Rif": "19", "Stato": "🟢 Buono"},
    ])

if "mooring_history" not in st.session_state:
    st.session_state["mooring_history"] = pd.DataFrame([
        {"Data": "2026-08-10", "Porto": "Ensenada", "Banchina": "Pier #1", "Vento Max (kt)": 32, "Corrente (kt)": 1.2, "Config": "6/2 FWD - 7/2 AFT", "Note": "Tensione massima su Spring 68%"},
        {"Data": "2026-08-03", "Porto": "Ensenada", "Banchina": "Pier #2", "Vento Max (kt)": 22, "Corrente (kt)": 0.8, "Config": "6/2 FWD - 6/2 AFT", "Note": "Nessuna anomalia"},
        {"Data": "2026-07-27", "Porto": "Cabo San Lucas", "Banchina": "Tender Bay", "Vento Max (kt)": 18, "Corrente (kt)": 0.5, "Config": "Rada", "Note": "Operazione Tender ok"},
    ])

# -----------------------------------------------------------------------------
# 3. UTILITY FUNZIONE ESTRAZIONE EXCEL
# -----------------------------------------------------------------------------
def parse_excel_mooring(file_bytes, filename):
    imgs = []
    if filename.lower().endswith('.xls'):
        pngs = [m.start() for m in re.finditer(b'\x89PNG\r\n\x1a\n', file_bytes)]
        for s in pngs:
            e = file_bytes.find(b'IEND', s)
            if e != -1:
                try:
                    im = Image.open(io.BytesIO(file_bytes[s:e+8]))
                    if im.size[0] > 180 and im.size[1] > 180: imgs.append(im)
                except: pass
    elif filename.lower().endswith('.xlsx'):
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                for name in z.namelist():
                    if name.startswith('xl/media/'):
                        try:
                            im = Image.open(io.BytesIO(z.read(name)))
                            if im.size[0] > 180 and im.size[1] > 180: imgs.append(im)
                        except: pass
        except: pass
    return imgs

# -----------------------------------------------------------------------------
# 4. BARRA DI NAVIGAZIONE TAB PRINCIPALI
# -----------------------------------------------------------------------------
st.sidebar.title("🚢 Navigation & Control")
st.sidebar.markdown(f"**Vessel:** {st.session_state['ship_specs']['name']}")
st.sidebar.markdown("**Officer:** Second Deck Navigational Officer")

page = st.sidebar.radio(
    "Seleziona Modulo:",
    [
        "🎛️ Live Simulation & Dynamic Forces",
        "🌀 Live Weather & Windy Integration",
        "📐 Import & Parsing Schemi Banchina (Excel)",
        "⚙️ Specifiche Nave & Pilot Card",
        "📉 Usura Cavi, MBL & Ispezioni",
        "📜 Storico Ormeggi & Logbook"
    ]
)

# =============================================================================
# PAGINA 1: LIVE SIMULATION & DYNAMIC FORCES (MEG4 CALCULATION)
# =============================================================================
if page == "🎛️ Live Simulation & Dynamic Forces":
    st.title("🎛️ Simulated Mooring Forces & Recommended Arrangement")
    st.caption("Calcolo delle forze di vento e corrente in tempo reale basato sulle linee guida OCIMF MEG4")

    col_env1, col_env2, col_env3 = st.columns(3)
    
    with col_env1:
        st.subheader("💨 Vento Reale / Simulato")
        wind_speed = st.slider("Velocità Vento (Nodi / Knots)", 0, 60, 28)
        wind_dir = st.slider("Direzione Vento relativa alla nave (°)", 0, 360, 45)
        
    with col_env2:
        st.subheader("🌊 Corrente")
        curr_speed = st.slider("Velocità Corrente (Knots)", 0.0, 4.0, 1.1, step=0.1)
        curr_dir = st.slider("Direzione Corrente relativa (°)", 0, 360, 30)

    with col_env3:
        st.subheader("⚓ Banchina & Assetto")
        dock_side = st.selectbox("Fianco all'Ormeggio", ["Sinistra (Port Side)", "Dritta (Starboard Side)"])
        tide_variation = st.number_input("Variazione Marea [m]", -2.0, 5.0, 1.2)

    # ALGORITMO MEG4 per Forze Trasversali e Longitudinali
    rho_air = 1.225 # kg/m3
    wind_ms = wind_speed * 0.514444
    rad_wind = np.radians(wind_dir)
    
    # Forze Vento (Tonnellate)
    front_wind_force = 0.5 * rho_air * (wind_ms**2) * st.session_state["ship_specs"]["wind_area_front"] * np.cos(rad_wind) * 0.000101972
    side_wind_force = 0.5 * rho_air * (wind_ms**2) * st.session_state["ship_specs"]["wind_area_side"] * np.sin(rad_wind) * 0.000101972
    
    # Forze Corrente
    curr_ms = curr_speed * 0.514444
    rad_curr = np.radians(curr_dir)
    side_curr_force = 0.5 * 1025 * (curr_ms**2) * st.session_state["ship_specs"]["current_area_side"] * np.sin(rad_curr) * 0.000101972

    total_transverse_force = abs(side_wind_force) + abs(side_curr_force)
    total_longitudinal_force = abs(front_wind_force)

    st.markdown("---")
    st.subheader("📊 Tonnellate di Forza Risultanti sugli Ormeggi")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Spinta Trasversale Totale", f"{total_transverse_force:.1f} Ton", delta=f"{'⚠️ Alta' if total_transverse_force > 150 else 'OK'}")
    c2.metric("Spinta Longitudinale Totale", f"{total_longitudinal_force:.1f} Ton")
    c3.metric("Carico Stimato su Cavo Singolo", f"{(total_transverse_force/6):.1f} Ton / cavo")
    
    mbl_limit = 115 * 0.55 # Limit 55% MBL
    status_limit = "🟢 Sicuro (<55% MBL)" if (total_transverse_force/6) < mbl_limit else "🚨 Rischio Sovraccarico"
    c4.metric("Limite Sicurezza MEG4", f"{mbl_limit:.1f} Ton", delta=status_limit)

    st.markdown("---")
    st.subheader("💡 Ormeggio Consigliato in Base alle Condizioni Meteo")
    
    if total_transverse_force > 180:
        st.error("🚨 **RACCOMANDAZIONE:** Configurazione Rinforzata richiesta! Utilizzare almeno **4 Head Lines, 4 Breast Lines, 2 Springs AFT/FWD**. Considerare l'uso di un rimorchiatore in assistenza se il vento supera i 35 kt.")
    elif total_transverse_force > 100:
        st.warning("🟡 **RACCOMANDAZIONE:** Configurazione standard **6/2** o **7/2** (3 Head Lines, 3 Breast Lines, 2 Springs FWD e AFT). Verificare il pretensionamento automatico dei verricelli.")
    else:
        st.success("🟢 **RACCOMANDAZIONE:** Configurazione Standard Banchina **6/2** sufficiente. Tensione bilanciata su tutti i cavi in fibra.")

# =============================================================================
# PAGINA 2: LIVE WEATHER & WINDY INTEGRATION
# =============================================================================
elif page == "🌀 Live Weather & Windy Integration":
    st.title("🌀 Live Weather & Windy Radar Integration")
    
    col_w1, col_w2 = st.columns([1, 2])
    with col_w1:
        st.subheader("📍 Selezione Porto / Banchina")
        lat = st.number_input("Latitudine", value=31.8578)
        lon = st.number_input("Longitudine", value=-116.6258)
        zoom = st.slider("Zoom Mappa", 3, 15, 11)
        overlay = st.selectbox("Layer Meteo", ["wind", "waves", "currents", "clouds", "pressure"])

    with col_w2:
        windy_html = f"""
        <iframe width="100%" height="450" src="https://embed.windy.com/embed2.html?lat={lat}&lon={lon}&detailLat={lat}&detailLon={lon}&width=650&height=450&zoom={zoom}&level=surface&overlay={overlay}&product=ecmwf&menu=&message=&marker=true&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=kt&metricTemp=%C2%B0C&radarRange=-1" frameborder="0"></iframe>
        """
        st.components.v1.html(windy_html, height=470)

# =============================================================================
# PAGINA 3: IMPORT SCHEMI BANCHINA EXCEL
# =============================================================================
elif page == "📐 Import & Parsing Schemi Banchina (Excel)":
    st.title("📐 Importatore Schemi Grafici Banchina da Excel")
    uploaded_file = st.file_uploader("Carica il file del piano d'ormeggio (.xls / .xlsx)", type=["xls", "xlsx"])
    
    if uploaded_file:
        bytes_data = uploaded_file.read()
        imgs = parse_excel_mooring(bytes_data, uploaded_file.name)
        st.success(f"File caricato! Estratti {len(imgs)} diagrammi ad alta risoluzione.")
        if imgs:
            c1, c2 = st.columns(2)
            for idx, img in enumerate(imgs):
                with (c1 if idx % 2 == 0 else c2):
                    st.image(img, caption=f"Layout Dettaglio Banchina #{idx+1}", use_column_width=True)

# =============================================================================
# PAGINA 4: SPECIFICHE NAVE & PILOT CARD (INTERFACCIA RIDISEGNATA)
# =============================================================================
elif page == "⚙️ Specifiche Nave & Pilot Card":
    st.title("⚙️ Carnival Panorama - Particulars & Pilot Card")
    st.caption("Specifiche tecniche principali e dati di manovrabilità della nave")

    specs = st.session_state["ship_specs"]
    
    st.subheader("📐 Dimensioni & Carenamento")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Lunghezza (LOA)", f"{specs['loa']} m")
    col2.metric("Larghezza (Beam)", f"{specs['beam']} m")
    col3.metric("Pescaggio (Draft)", f"{specs['draft']} m")
    col4.metric("Altezza Max (Air Draft)", f"{specs['air_draft']} m")
    col5.metric("Dislocamento", f"{specs['displacement']:,} T".replace(",", "."))

    st.markdown("---")

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("🌬️ Superfici Esposte (Wind & Current Areas)")
        st.markdown(f"""
        <div style="background-color: #1e222b; padding: 20px; border-radius: 8px; border: 1px solid #2e3644; font-size: 15px;">
            <p>💨 <b>Superficie Vento Frontale:</b> {specs['wind_area_front']} m²</p>
            <p>💨 <b>Superficie Vento Laterale:</b> {specs['wind_area_side']} m²</p>
            <hr style="border-color: #2e3644;">
            <p>🌊 <b>Superficie Corrente Frontale:</b> {specs['current_area_front']} m²</p>
            <p>🌊 <b>Superficie Corrente Laterale:</b> {specs['current_area_side']} m²</p>
        </div>
        """, unsafe_allow_html=True)

    with col_b:
        st.subheader("🚤 Propulsione & Manovrabilità")
        st.markdown("""
        <div style="background-color: #1e222b; padding: 20px; border-radius: 8px; border: 1px solid #2e3644; font-size: 15px;">
            <p>⚡ <b>Propulsione Principale:</b> 2x Azipod ABB V2100 (Totale 37,000 kW)</p>
            <p>🔄 <b>Bow Thrusters:</b> 3x Brunvoll Transverse Thrusters (3x 2,200 kW)</p>
            <p>🚀 <b>Velocità Max:</b> 22.6 Nodi</p>
            <p>⚓ <b>Ancore:</b> 2x Spek Anchors (11.5 Ton ciascuna) - 14 Lunghezze Catena</p>
        </div>
        """, unsafe_allow_html=True)

# =============================================================================
# PAGINA 5: USURA CAVI, MBL & ISPEEZIONI
# =============================================================================
elif page == "📉 Usura Cavi, MBL & Ispezioni":
    st.title("📉 Stato Usura Cavi, MBL & Certificati Linee")
    
    st.dataframe(st.session_state["mooring_lines_db"], use_container_width=True)
    
    st.markdown("---")
    st.subheader("⚠️ Allarmi Manutenzione Cavi")
    for idx, row in st.session_state["mooring_lines_db"].iterrows():
        if "🔴" in row["Stato"]:
            st.error(f"**Cavo {row['ID']} ({row['Ruolo']} - {row['Posizione']})**: Raggiunto il limite ore uso ({row['Ore_Uso']} hrs). Sostituzione raccomandata.")

# =============================================================================
# PAGINA 6: STORICO ORMEGGI & LOGBOOK
# =============================================================================
elif page == "📜 Storico Ormeggi & Logbook":
    st.title("📜 Storico Operazioni di Ormeggio")
    st.dataframe(st.session_state["mooring_history"], use_container_width=True)
