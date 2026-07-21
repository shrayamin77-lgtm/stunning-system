import streamlit as st
import pandas as pd
from datetime import datetime
import re

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

# --- APP HEADER & ROLE SELECTION ---
st.set_page_config(page_title="Backup Block Swap Tool", page_icon="🔄")
st.title("🔄 Backup Block Swap Tool")

role = st.radio("Select Your PGY Level:", ["Intern (PGY-1)", "Senior (PGY-2 / PGY-3)"], horizontal=True)

# Assign files based on selected role
if role == "Intern (PGY-1)":
    matrix_file = "clean_schedule_matrix.csv"
    weekend_file = "weekend_coverage_schedule.csv"
    backup_file = "backup_schedule_final.csv"
else:
    matrix_file = "senior_schedule_matrix.csv"
    weekend_file = "senior_weekend_coverage_schedule.csv"
    backup_file = "senior_backup_schedule_final.csv"

# --- DATA LOADING & HARDENING ---
@st.cache_data
def load_data(m_file, w_file, b_file):
    try:
        backup_df = pd.read_csv(b_file)
        backup_df["Resident"] = backup_df["Resident"].astype(str).str.strip()
        backup_df["Date_Range"] = backup_df["Date_Range"].astype(str).str.strip()
        
        matrix_df = pd.read_csv(m_file)
        matrix_df["Resident"] = matrix_df["Resident"].astype(str).str.strip()
        matrix_df.columns = [str(c).strip() for c in matrix_df.columns]
        
        # Custom reader for weekend coverage to handle any comma formatting issues
        weekend_rows = []
        with open(w_file, 'r', encoding='utf-8-sig') as f:
            header = f.readline()
            for line in f:
                line = line.strip()
                if not line: continue
                parts = line.split(',', 1) # Split into date and remainder
                if len(parts) == 2:
                    d_val = parts[0].strip()
                    cov_val = parts[1].strip()
                    # If multiple comma-separated names exist on one line, explode them
                    names = [n.strip() for n in cov_val.split(',')]
                    for name in names:
                        if name:
                            weekend_rows.append({"Date": d_val, "Scheduled_Coverage": name})
                            
        weekend_df = pd.DataFrame(weekend_rows)
        
        return backup_df, matrix_df, weekend_df
    except Exception as e:
        st.error(f"⚠️ Error loading CSV files for {role}. Please ensure all required CSVs are uploaded to GitHub.")
        st.stop()

backup_df, matrix_df, weekend_df = load_data(matrix_file, weekend_file, backup_file)

# --- DATE PARSING HELPERS ---
def parse_academic_date(date_str):
    """Safely converts date strings (with or without years) into accurate academic year dates."""
    try:
        clean_s = str(date_str).strip()
        parts = clean_s.split("/")
        month = int(parts[0])
        day = int(parts[1])
        
        if len(parts) == 3:
            year = int(parts[2])
            if year < 100:
                year += 2000
        else:
            year = 2026 if month >= 7 else 2027
            
        return datetime(year, month, day).date()
    except Exception:
        return None

def is_on_elective(resident_name, range_str):
    """Checks if a resident is on Elective during a specific block date range."""
    try:
        s_str = range_str.split("-")[0].strip()
        target_start = parse_academic_date(s_str)
    except Exception:
        return False
        
    if not target_start:
        return False

    matching_col = None
    
    # Match matrix column header by comparing normalized start dates
    for col in matrix_df.columns:
        if col == "Resident": 
            continue
        try:
            col_start_str = col.split("-")[0].strip()
            col_start = parse_academic_date(col_start_str)
            if col_start and col_start == target_start:
                matching_col = col
                break
        except Exception:
            continue

    if not matching_col:
        return False

    res_row = matrix_df[matrix_df["Resident"].str.lower() == resident_name.strip().lower()]
    if res_row.empty:
        return False

    rotation_val = str(res_row.iloc[0][matching_col]).strip()
    return rotation_val.lower() == "elective"

def is_same_resident(target, candidate):
    """Flexible check for last names and initials (e.g. 'G. Singh' vs 'g singh')."""
    t = re.sub(r'\s+', ' ', str(target).lower().replace(".", " ")).strip()
    c = re.sub(r'\s+', ' ', str(candidate).lower().replace(".", " ")).strip()
    return t == c

def get_weekend_shifts_in_range(resident_name, range_str):
    """Checks if a resident has assigned weekend floor coverage during a date range."""
    try:
        s_str, e_str = range_str.split("-")
        s_dt = parse_academic_date(s_str)
        e_dt = parse_academic_date(e_str)
    except Exception:
        return []
        
    if not s_dt or not e_dt:
        return []
    
    working_dates = []

    for _, row in weekend_df.iterrows():
        try:
            date_val = str(row["Date"]).strip()
            if not date_val or date_val.lower() == "nan":
                continue
            
            shift_dt = parse_academic_date(date_val)
            if shift_dt and (s_dt <= shift_dt <= e_dt):
                scheduled_resident = str(row["Scheduled_Coverage"]).strip()
                if is_same_resident(resident_name, scheduled_resident):
                    working_dates.append(date_val)
        except Exception:
            continue
            
    return working_dates

# --- USER INTERFACE & SEARCH LOGIC ---
st.write("Find residents to swap **backup blocks** with. Both residents must be on **Elective** during their respective backup periods.")

resident_list = sorted(backup_df["Resident"].unique())
selected_resident = st.selectbox(f"Select Your Last Name ({role}):", resident_list)

user_assignments = backup_df[backup_df["Resident"] == selected_resident]
user_ranges = sorted(user_assignments["Date_Range"].unique())

if user_ranges:
    selected_range = st.selectbox("Select the Backup Period You Need to Swap Out Of:", user_ranges)
    
    if not is_on_elective(selected_resident, selected_range):
        st.error(f"⚠️ You are not on Elective during {selected_range}. Swaps must involve Elective blocks.")
        st.stop()
        
    if st.button("🔎 Search Backup Swaps"):
        eligible_swaps = []
        
        for _, row in backup_df.iterrows():
            other_resident = row["Resident"]
            other_range = row["Date_Range"]
            other_role = row["Backup_Role"]
            
            if other_resident == selected_resident or other_range == selected_range:
                continue
                
            # Check reciprocal Elective status
            other_on_elective_for_me = is_on_elective(other_resident, selected_range)
            i_on_elective_for_them = is_on_elective(selected_resident, other_range)
            
            if other_on_elective_for_me and i_on_elective_for_them:
                their_conflicts = get_weekend_shifts_in_range(other_resident, selected_range)
                my_conflicts = get_weekend_shifts_in_range(selected_resident, other_range)
                
                if their_conflicts or my_conflicts:
                    status = "🔴 Weekend Coverage Conflict"
                    notes_list = []
                    if their_conflicts:
                        notes_list.append(f"{other_resident} works weekend: {', '.join(their_conflicts)}")
                    if my_conflicts:
                        notes_list.append(f"You work weekend: {', '.join(my_conflicts)}")
                    notes = " | ".join(notes_list)
                else:
                    status = "🟢 Completely Free"
                    notes = "No weekend floor shifts"

                eligible_swaps.append({
                    "Status": status,
                    "Swap With": other_resident,
                    "Their Backup Dates": other_range,
                    "Their Role": other_role,
                    "Conflict Details": notes
                })
                
        if eligible_swaps:
            st.success(f"✅ Found {len(eligible_swaps)} reciprocal backup swap options for {selected_range}:")
            df_swaps = pd.DataFrame(eligible_swaps)
            st.caption("🟢 **Green Dot:** Clear of weekend floor shifts. | 🔴 **Red Dot:** Elective verified, but has an assigned floor weekend during the block.")
            st.table(df_swaps)
        else:
            st.warning("No eligible reciprocal backup swaps found for this period.")
else:
    st.info(f"No backup blocks currently assigned to **{selected_resident}**.")
