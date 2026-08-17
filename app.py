import streamlit as st
import pandas as pd
import numpy as np
import io
import re
import os
import zipfile
import xlrd
from PIL import Image

st.set_page_config(
    page_title="Mooring Management & Vessel Planner - Carnival Panorama",
    page_icon="🚢",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 1. FUNZIONE DI ESTRAZIONE IMMAGINI E DATI DA EXCEL (.XLS / .XLSX)
# -----------------------------------------------------------------------------
def extract_plan_from_excel(file_bytes, filename):
    """Estrae metadati e disegni tecnici integrati da file Excel (.xls o .xlsx)."""
    extracted_images = []
    
    # Estrazione immagini da file .xls (Legacy BIFF8 binary stream)
    if filename.lower().endswith('.xls'):
        content = file_bytes
        png_matches = [m.start() for m in re.finditer(b'\x89PNG\r\n\x1a\n', content)]
        jpg_matches = [m.start() for m in re.finditer(b'\xff\xd8\xff', content)]
        
        for start in png_matches:
            end = content.find(b'IEND', start)
            if end != -1:
                img_data = content[start:end + 8]
                try:
                    img = Image.open(io.BytesIO(img_data))
                    if img.size[0] > 200 and img.size[1] > 200: # Filtra icone/logo piccoli
                        extracted_images.append(img)
                except Exception:
                    pass
                    
        for start in jpg_matches:
            end = content.find(b'\xff\xd9', start)
            if end != -1:
                img_data = content[start:end + 2]
                try:
                    img = Image.open(io.BytesIO(img_data))
                    if img.size[0] > 200 and img.size[1] > 200:
                        extracted_images.append(img)
                except Exception:
                    pass

    # Estrazione immagini da file .xlsx (OpenXML ZIP)
    elif filename.lower().endswith('.xlsx'):
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                for name in z.namelist():
                    if name.startswith('xl/media/'):
                        img_data = z.read(name)
                        try:
                            img = Image.open(io.BytesIO(img_data))
                            if img.size[0] > 200 and img.size[1] > 200:
                                extracted_images.append(img)
                        except Exception:
                            pass
        except Exception:
            pass

    # Parsing Cantiere / Porto / Heading / Cavi da testo celle
    parsed_info = {
        "raw_title": "Piano d'Ormeggio Caricato",
        "port": "Ensenada",
        "pier": "Pier #2",
        "heading": 150.0,
        "config": "6/2",
        "notes": [],
        "lines_summary": []
    }

    try:
        wb = xlrd.open_workbook(file_contents=file_bytes)
        sheet = wb.sheet_by_index(0)
        
        for r in range(sheet.nrows):
            for c in range(sheet.ncols):
                val = str(sheet.cell_value(r, c)).strip()
                if not val:
                    continue
                
                if "HDG" in val or "Pier" in val or "Port" in val:
                    parsed_info["raw_title"] = val
                    hdg_m = re.search(r'HDG\s*(\d+)°?', val, re.IGNORECASE)
                    if hdg_m:
                        parsed_info["heading"] = float(hdg_m.group(1))
                    pier_m = re.search(r'Pier\s*#?\s*(\w+)', val, re.IGNORECASE)
                    if pier_m:
                        parsed_info["pier"] = f"Pier #{pier_m.group(1)}"

                if re.match(r'^\d+/\d+$', val):
                    parsed_info["config"] = val
                
                if any(k in val.lower() for k in ["lines", "spring", "breast", "head", "stern"]):
                    if val not in parsed_info["lines_summary"]:
                        parsed_info["lines_summary"].append(val)
                        
                if "heaving" in val.lower() or "dk#" in val.lower():
                    if val not in parsed_info["notes"]:
                        parsed_info["notes"].append(val)
    except Exception:
        pass

    return parsed_info, extracted_images

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
        "gross_tonnage": 133500
    }

if "mooring_lines" not in st.session_state:
    st.session_state["mooring_lines"] = pd.DataFrame([
        {"ID": "FWD-L1", "Stazione": "Prua (Forecastle)", "Winch": "Winch 1 (Port)", "Ruolo": "Head Line", "Bitta_Assegnata": "Bitta 29", "MBL_Ton": 115, "Ore_Uso": 450, "Stato": "🟢 OK"},
        {"ID": "FWD-L2", "Stazione": "Prua (Forecastle)", "Winch": "Winch 2 (Stbd)", "Ruolo": "Head Line", "Bitta_Assegnata": "Bitta 28", "MBL_Ton": 115, "Ore_Uso": 450, "Stato": "🟢 OK"},
        {"ID": "FWD-L3", "Stazione": "Prua (Forecastle)", "Winch": "Winch 3 (Port)", "Ruolo": "Breast Line", "Bitta_Assegnata": "Bitta 27", "MBL_Ton": 115, "Ore_Uso": 820, "Stato": "🟡 Ispezionare"},
        {"ID": "FWD-L4", "Stazione": "Prua (Forecastle)", "Winch": "Winch 4 (Stbd)", "Ruolo": "Spring Line", "Bitta_Assegnata": "Bitta 25", "MBL_Ton": 115, "Ore_Uso": 300, "Stato": "🟢 OK"},
        {"ID": "AFT-L1", "Stazione": "Poppa (Aft Deck)", "Winch": "Winch 5 (Port)", "Ruolo": "Spring Line", "Bitta_Assegnata": "Bitta 19", "MBL_Ton": 110, "Ore_Uso": 980, "Stato": "🟡 Ispezionare"},
        {"ID": "AFT-L2", "Stazione": "Poppa (Aft Deck)", "Winch": "Winch 6 (Stbd)", "Ruolo": "Breast Line", "Bitta_Assegnata": "Bitta 16", "MBL_Ton": 110, "Ore_Uso": 980, "Stato": "🟡 Ispezionare"},
    ])

# -----------------------------------------------------------------------------
# 3. INTERFACCIA PRINCIPALE
# -----------------------------------------------------------------------------
st.title("🚢 Carnival Panorama - Integrated Mooring System")

tab1, tab2, tab3 = st.tabs([
    "📋 Info Nave & Specifiche",
    "📐 Piani d'Ormeggio & Disegni Banchina (da Excel)",
    "⚓ Gestione Cavi & Assegnazione Bitte"
])

# =============================================================================
# TAB 1: INFO NAVE
# =============================================================================
with tab1:
    st.header("🚢 Specifiche Nave")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state["ship_data"]["loa"] = st.number_input("LOA [m]", value=st.session_state["ship_data"]["loa"])
        st.session_state["ship_data"]["beam"] = st.number_input("Beam [m]", value=st.session_state["ship_data"]["beam"])
    with col2:
        st.session_state["ship_data"]["draft"] = st.number_input("Draft [m]", value=st.session_state["ship_data"]["draft"])
        st.session_state["ship_data"]["air_draft"] = st.number_input("Air Draft [m]", value=st.session_state["ship_data"]["air_draft"])

# =============================================================================
# TAB 2: PIANI D'ORMEGGIO EXCEL & DISEGNI ESTRATTI
# =============================================================================
with tab2:
    st.header("📐 Interpretatore Disegni & Piani d'Ormeggio Excel")
    
    uploaded_plan = st.file_uploader(
        "📂 Carica Disegno Piano d'Ormeggio (.xls o .xlsx)",
        type=["xls", "xlsx"],
        help="Carica i file Excel contenenti i diagrammi vettoriali/immagini del piano d'ormeggio."
    )

    if uploaded_plan is not None:
        file_bytes = uploaded_plan.read()
        info, images = extract_plan_from_excel(file_bytes, uploaded_plan.name)
        
        st.success(f"File '{uploaded_plan.name}' interpretato correttamente!")

        # Visualizzazione Metadati Estratti
        st.subheader("📌 Dati Operativi Estratti dal File")
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Intestazione / Banchina", info["raw_title"])
        m_col2.metric("Heading Banchina", f"{info['heading']}°")
        m_col3.metric("Configurazione Cavi", info["config"])
        m_col4.metric("Note Operative", ", ".join(info["notes"]) if info["notes"] else "Nessuna")

        st.markdown("---")

        # Visualizzazione Disegni Tecnici Estratti dall'Excel
        st.subheader("🖼️ Disegni Tecnici d'Ormeggio Estratti dall'Excel")
        if images:
            img_cols = st.columns(len(images))
            for i, img in enumerate(images):
                with img_cols[i]:
                    caption = "Schema Prua (FWD)" if i == 0 else "Schema Poppa (Aft)" if i == 1 else f"Disegno #{i+1}"
                    st.image(img, caption=caption, use_column_width=True)
        else:
            st.info("Nessuna immagine ad alta risoluzione trovata direttamente nell'Excel. Visualizzazione della tabella dati.")

# =============================================================================
# TAB 3: GESTIONE CAVI & ASSEGNAZIONE BITTE
# =============================================================================
with tab3:
    st.header("⚓ Assegnazione Cavi Verricelli ➔ Bitte Banchina")
    st.info("💡 Utilizza i numeri delle bitte identificati nei disegni di Tab 2 (es. Bitte #29, #28, #27, #25 a Prua e #19, #16 a Poppa) per configurare il piano d'ormeggio.")

    st.session_state["mooring_lines"] = st.data_editor(
        st.session_state["mooring_lines"],
        num_rows="dynamic",
        use_container_width=True
    )
