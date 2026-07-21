import streamlit as st
import pandas as pd
from datetime import datetime

# --- SECURITY ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
            
    if "password_correct" not in st.session_state:
        st.text_input("Enter residency password to access the tool:", type="password", on_change=password_entered, key="password")
        return False
    return st.session_state["password_correct"]

if not check_password():
    st.stop()

# --- ROLE SELECTION ---
st.set_page_config(page_title="Residency Swap Tool", page_icon="🏥")
st.title("🏥 Residency Swap Tool")

# Radio button to pick PGY level
role = st.radio("Select Your Role:", ["Intern (PGY-1)", "Senior (PGY-2 / PGY-3)"], horizontal=True)

# Dynamically set file paths based on role
if role == "Intern (PGY-1)":
    matrix_file = "clean_schedule_matrix.csv"
    weekend_file = "weekend_coverage_schedule.csv"
    backup_file = "backup_schedule_final.csv"
else:
    matrix_file = "senior_schedule_matrix.csv"
    weekend_file = "senior_weekend_coverage_schedule.csv"
    backup_file = "senior_backup_schedule_final.csv"

# --- DATA LOADING ---
@st.cache_data
def load_data(m_file, w_file, b_file):
    try:
        matrix_df = pd.read_csv(m_file)
        matrix_df["Resident"] = matrix_df["Resident"].astype(str).str.strip()
        
        weekend_df = pd.read_csv(w_file)
        weekend_df["Date"] = weekend_df["Date"].astype(str).str.strip()
        weekend_df["Scheduled_Coverage"] = weekend_df["Scheduled_Coverage"].astype(str).str.strip()
        
        backup_df = pd.read_csv(b_file)
        backup_df["Resident"] = backup_df["Resident"].astype(str).str.strip()
        backup_df["Date_Range"] = backup_df["Date_Range"].astype(str).str.strip()
        
        return matrix_df, weekend_df, backup_df
    except FileNotFoundError as e:
        st.error(f"⚠️ Could not load data files for {role}. Please make sure senior CSV files are uploaded to GitHub.")
        st.stop()

matrix_df, weekend_df, backup_df = load_data(matrix_file, weekend_file, backup_file)

# Dropdown automatically populates with residents from the selected role!
resident_list = sorted(matrix_df["Resident"].unique())
selected_resident = st.selectbox(f"Select Your Last Name ({role}):", resident_list)

st.success(f"Loaded schedule data for **{selected_resident}** ({role}). Ready to search swaps!")
