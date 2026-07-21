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

# --- DATA LOADING ---
@st.cache_data
def load_data():
    backup_df = pd.read_csv("backup_schedule_final.csv")
    backup_df["Resident"] = backup_df["Resident"].astype(str).str.strip()
    backup_df["Date_Range"] = backup_df["Date_Range"].astype(str).str.strip()
    
    matrix_df = pd.read_csv("clean_schedule_matrix.csv")
    matrix_df["Resident"] = matrix_df["Resident"].astype(str).str.strip()
    
    weekend_df = pd.read_csv("weekend_coverage_schedule.csv")
    weekend_df["Date"] = weekend_df["Date"].astype(str).str.strip()
    weekend_df["Scheduled_Coverage"] = weekend_df["Scheduled_Coverage"].astype(str).str.strip()
    
    return backup_df, matrix_df, weekend_df

backup_df, matrix_df, weekend_df = load_data()

# Parse Block Intervals from Clean Schedule Matrix
block_intervals = []
for col in matrix_df.columns:
    if col == "Resident": continue
    try:
        start_str, end_str = col.split("-")
        s_m, s_d = map(int, start_str.strip().split("/"))
        e_m, e_d = map(int, end_str.strip().split("/"))
        s_yr = 2026 if s_m >= 7 else 2027
        e_yr = 2026 if e_m >= 7 else 2027
        block_intervals.append({"column": col, "start": datetime(s_yr, s_m, s_d), "end": datetime(e_yr, e_m, e_d)})
    except Exception: continue

def get_matrix_col_for_date_range(range_str):
    try:
        start_date_str = range_str.split("-")[0].strip()
        target_dt = pd.to_datetime(start_date_str)
        for interval in block_intervals:
            if interval["start"] <= target_dt <= interval["end"]:
                return interval["column"]
    except: return None
    return None

def is_on_elective(resident_name, range_str):
    matrix_col = get_matrix_col_for_date_range(range_str)
    if not matrix_col: return True
    
    res_row = matrix_df[matrix_df["Resident"].str.lower() == resident_name.lower()]
    if res_row.empty: return False
    
    val = str(res_row.iloc[0][matrix_col]).strip()
    return val.lower() == "elective"

def get_weekend_shifts_in_range(resident_name, range_str):
    """Finds any weekend floor shifts assigned to resident within a date range."""
    try:
        s_str, e_str = range_str.split("-")
        s_dt = pd.to_datetime(s_str.strip())
        e_dt = pd.to_datetime(e_str.strip())
    except:
        return []
    
    working_dates = []
    for _, row in weekend_df.iterrows():
        shift_dt = pd.to_datetime(row["Date"])
        if s_dt <= shift_dt <= e_dt:
            names = [n.strip().lower() for n in str(row["Scheduled_Coverage"]).split(",")]
            if resident_name.lower() in names:
                working_dates.append(row["Date"])
    return working_dates

# --- UI ---
st.set_page_config(page_title="Backup Block Swap Tool", page_icon="🔄")
st.title("🔄 Backup Block Swap Tool")
st.write("Find residents to swap **backup blocks** with. Swaps require both residents to be on **Elective** during their respective backup periods.")

resident_list = sorted(backup_df["Resident"].unique())
selected_resident = st.selectbox("Select Your Last Name:", resident_list)

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
                
            # Mutual elective check
            other_on_elective_for_me = is_on_elective(other_resident, selected_range)
            i_on_elective_for_them = is_on_elective(selected_resident, other_range)
            
            if other_on_elective_for_me and i_on_elective_for_them:
                # Check for weekend floor conflicts
                their_conflicts = get_weekend_shifts_in_range(other_resident, selected_range)
                my_conflicts = get_weekend_shifts_in_range(selected_resident, other_range)
                
                if spouse_conflict := (their_conflicts or my_conflicts):
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
            
            # Convert to DataFrame
            df_swaps = pd.DataFrame(eligible_swaps)
            
            # Display legend
            st.caption("🟢 **Green Dot:** Clear of weekend floor shifts. | 🔴 **Red Dot:** Elective verified, but has an assigned floor weekend during the block.")
            st.table(df_swaps)
        else:
            st.warning("No eligible reciprocal backup swaps found for this period.")
else:
    st.info(f"No backup blocks currently assigned to **{selected_resident}**.")
