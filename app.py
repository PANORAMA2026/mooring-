import streamlit as st
import pandas as pd
import numpy as np
import json
import math

st.set_page_config(
    page_title="Mooring Management & Vessel Planner - Carnival Panorama",
    page_icon="🚢",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 1. INIZIALIZZAZIONE SESSION STATE
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

if "active_berth" not in st.session_state:
    st.session_state["active_berth"] = {
        "info": {
            "Porto": "Ensenada",
            "Banchina": "Cruise Pier",
            "Heading_Banchina": 155.0,
            "Bordo_Affiancato": "Starboard",
            "Pescaggio_Max": 11.0,
            "Altezza_Banchina_SLM": 3.5
        },
        "bollards": pd.DataFrame([
            {"ID_Bitta": "B1", "Posizione_M": 0.0, "SWL_Tonnellate": 100, "Note": "Prua estrema"},
            {"ID_Bitta": "B2", "Posizione_M": 25.0, "SWL_Tonnellate": 100, "Note": "OK"},
            {"ID_Bitta": "B3", "Posizione_M": 50.0, "SWL_Tonnellate": 100, "Note": "OK"},
            {"ID_Bitta": "B4", "Posizione_M": 75.0, "SWL_Tonnellate": 80, "Note": "Verificare usura"},
            {"ID_Bitta": "B5", "Posizione_M": 100.0, "SWL_Tonnellate": 100, "Note": "OK"},
            {"ID_Bitta": "B6", "Posizione_M": 125.0, "SWL_Tonnellate": 100, "Note": "OK"},
            {"ID_Bitta": "B7", "Posizione_M": 150.0, "SWL_Tonnellate": 100, "Note": "OK"},
            {"ID_Bitta": "B8", "Posizione_M": 175.0, "SWL_Tonnellate": 100, "Note": "Poppa estrema"}
        ])
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
# 2. ARCHITETTURA A TAB
# -----------------------------------------------------------------------------
st.title("🚢 Carnival Panorama - Integrated Mooring System")

tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Info Nave & Specifiche",
    "⚓ Stazioni di Ormeggio & Cavi",
    "📐 Layout Banchine & Bitte (da Excel)",
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
    st.session_state["mooring_lines"] = st.data_editor(
        st.session_state["mooring_lines"],
        num_rows="dynamic",
        use_container_width=True
    )

# =============================================================================
# TAB 3: LAYOUT BANCHINE & CARICAMENTO EXCEL
# =============================================================================
with tab3:
    st.header("📐 Importazione & Registro Banchine")
    
    # Uploader file Excel per la Banchina
    uploaded_berth_file = st.file_uploader(
        "📂 Carica File Excel della Banchina (.xlsx)", 
        type=["xlsx", "xls"],
        help="Carica il file contenente le specifiche della banchina e la disposizione delle bitte."
    )

    if uploaded_berth_file is not None:
        try:
            xls = pd.ExcelFile(uploaded_berth_file)
            
            # Lettura Foglio Info Banchina
            if "Dati_Banchina" in xls.sheet_names:
                df_info = pd.read_excel(xls, "Dati_Banchina")
                st.session_state["active_berth"]["info"] = df_info.iloc[0].to_dict()
            
            # Lettura Foglio Bitte
            if "Planimetria_Bitte" in xls.sheet_names:
                df_bollards = pd.read_excel(xls, "Planimetria_Bitte")
                st.session_state["active_berth"]["bollards"] = df_bollards

            st.success(f"Banchina '{st.session_state['active_berth']['info'].get('Banchina', 'N/A')}' caricata con successo!")
        except Exception as e:
            st.error(f"Errore durante la lettura del file Excel: {e}")

    st.markdown("---")

    # Visualizzazione dati banchina attiva
    info = st.session_state["active_berth"]["info"]
    df_bollards = st.session_state["active_berth"]["bollards"]

    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
    col_b1.metric("Porto", str(info.get("Porto", "-")))
    col_b2.metric("Banchina", str(info.get("Banchina", "-")))
    col_b3.metric("Heading (°)", f"{info.get('Heading_Banchina', 0.0)}°")
    col_b4.metric("Bordo Affiancato", str(info.get("Bordo_Affiancato", "-")))

    st.subheader("📌 Registro Bitte e Capacità SWL")
    st.session_state["active_berth"]["bollards"] = st.data_editor(
        df_bollards,
        num_rows="dynamic",
        use_container_width=True
    )

    # Schema Grafico Lineare (Senza Mappe Satellitari)
    st.subheader("📐 Disposizione Lineare Bitte sulla Banchina")
    if not df_bollards.empty and "Posizione_M" in df_bollards.columns:
        chart_data = df_bollards.copy()
        chart_data = chart_data.sort_values(by="Posizione_M")
        
        st.bar_chart(
            chart_data,
            x="ID_Bitta",
            y="SWL_Tonnellate",
            color="#0088FF",
            use_container_width=True
        )

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
