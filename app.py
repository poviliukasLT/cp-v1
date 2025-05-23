
import streamlit as st
import pandas as pd
import pytz
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="Pasiūlymų generatorius", layout="wide")

st.title("📦 Pasiūlymų kūrimo įrankis v1")

# Atmintis tarp seansų
if 'pasirinktos_eilutes' not in st.session_state:
    st.session_state.pasirinktos_eilutes = pd.DataFrame()

rename_rules = {
    "Sweets": ["", "Product code", "Product name", "Purchasing price", "Label",
               "Price with costs", "Target Margin", "Target offer", "VAT",
               "Offer with VAT", "RSP MIN", "RSP MAX", "Margin RSP MIN", "Margin RSP MAX",
               "", "Target Margin", "Target offer"],
    "Snacks_": ["", "Product code", "Product name", "Purchasing price", "Label",
                "Price with costs", "Target Margin", "Target offer", "VAT",
                "Offer with VAT", "RSP MIN", "RSP MAX", "Margin RSP MIN", "Margin RSP MAX",
                "", "Target Margin", "Target offer"],
    "Groceries": ["", "Product code", "Product name", "Purchasing price", "Label",
                  "Price with costs", "Target Margin", "Target offer", "VAT",
                  "Offer with VAT", "RSP MIN", "RSP MAX", "Margin RSP MIN", "Margin RSP MAX",
                  "", "Target Margin", "Target offer"],
    "beverages": ["Country", "Product code", "Product name", "Purchasing price", "Label",
                  "Deposit (if needed)", "Sugar Tax", "Price with costs", "Target Margin",
                  "Target offer", "VAT", "Offer with VAT", "RSP MIN", "RSP MAX",
                  "Margins RSP MIN", "Margins RSP MAX", "Target Margin", "Target offer",
                  "", "AS OF 2025", "CAN up to 0,33l", "CAN over 0,33",
                  "PET up to 0,75l", "PET over 0,75l", "GLASS up to 0,5l", "GLASS over 0,5l"]
}

@st.cache_data
def load_excel(file):
    excel = pd.ExcelFile(file)
    return {sheet: excel.parse(sheet).dropna(how="all").reset_index(drop=True) for sheet in excel.sheet_names}

# 1. Įkelti failus
uploaded_files = st.file_uploader("📁 Įkelkite Excel failus:", type="xlsx", accept_multiple_files=True)

if uploaded_files:
    all_sheets = {}
    for file in uploaded_files:
        sheet_data = load_excel(file)
        for sheet, df in sheet_data.items():
            key = f"{file.name} -> {sheet}"
            all_sheets[key] = {
                "data": df,
                "filename": file.name.split(".")[0]
            }

    pasirinkimas = st.selectbox("Pasirinkite failą ir lapą:", list(all_sheets.keys()))
    df = all_sheets[pasirinkimas]["data"]
    filename = all_sheets[pasirinkimas]["filename"]

    st.dataframe(df.head(100))  # parodyti tik pirmas 100 eilučių

    pasirinktos_eilutes = st.multiselect("✅ Pasirinkite eilučių numerius:", df.index)
    if st.button("➕ Pridėti pažymėtas"):
        pasirinktos = df.loc[pasirinktos_eilutes].copy()
        pasirinktos["Failas"] = filename
        st.session_state.pasirinktos_eilutes = pd.concat(
            [st.session_state.pasirinktos_eilutes, pasirinktos],
            ignore_index=True
        )

# 2. Atminties peržiūra
st.subheader("🧠 Atmintis")
df_memory = st.session_state.pasirinktos_eilutes
if df_memory.empty:
    st.info("Nėra pasirinkimų.")
else:
    st.dataframe(df_memory)
    pasirinkti_salinimui = st.multiselect("🗑️ Pažymėkite eilutes pašalinimui:", df_memory.index)
    col1, col2 = st.columns(2)
    if col1.button("❌ Pašalinti pažymėtas"):
        st.session_state.pasirinktos_eilutes = df_memory.drop(index=pasirinkti_salinimui).reset_index(drop=True)
    if col2.button("🧹 Išvalyti viską"):
        st.session_state.pasirinktos_eilutes = pd.DataFrame(); st.rerun()

# 3. Eksportas
if not st.session_state.pasirinktos_eilutes.empty:
    df_final = pd.DataFrame()
    pasirinktos_unikalios = st.session_state.pasirinktos_eilutes.drop_duplicates()

    for failas, grupė in pasirinktos_unikalios.groupby("Failas"):
        failo_pav = grupė["Failas"].iloc[0]
        df = grupė.drop(columns="Failas").copy()

        matching_key = None
        for key in rename_rules:
            if failo_pav.lower().startswith(key.lower()):
                matching_key = key
                break

        raw_names = rename_rules.get(matching_key, [f"Column {i}" for i in range(df.shape[1])])
        num_cols = df.shape[1]
        header_names = raw_names[:num_cols] + [""] * (num_cols - len(raw_names[:num_cols]))

        header_df = pd.DataFrame([header_names])
        df.columns = list(range(num_cols))
        header_df.columns = df.columns
        tarpas = pd.DataFrame([[pd.NA]*num_cols], columns=df.columns)
        blokas = pd.concat([header_df, df, tarpas], ignore_index=True)
        df_final = pd.concat([df_final, blokas], ignore_index=True)

    lt_tz = pytz.timezone("Europe/Vilnius")
    now_str = datetime.now(lt_tz).strftime("%Y-%m-%d_%H-%M")
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_final.to_excel(writer, index=False, header=False)
        st.session_state.export_ready = True
    st.session_state.export_data = output.getvalue()
    st.session_state.export_name = f"pasiulymas_{now_str}.xlsx"

if 'export_ready' in st.session_state and st.session_state.export_ready:
    st.download_button(
        label=f"📥 Atsisiųsti pasiūlymą ({now_str})",
        data=output.getvalue(),
        file_name=f"pasiulymas_{now_str}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
