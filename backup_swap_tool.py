import streamlit as st
import pandas as pd

@st.cache_data
def load_backup_schedule():
    df = pd.read_csv("backup_schedule_final.csv")
    df.columns = df.columns.str.strip()
    df["block"] = df["block"].astype(int)
    df["Resident"] = df["Resident"].str.strip()
    return df

df = load_backup_schedule()

st.title("🔄 Backup Block Swap Tool")
st.write("Find residents to swap **backup blocks** with. Swaps must be between elective blocks only.")

resident_list = df["Resident"].unique()
selected_resident = st.sidebar.selectbox("Your Name", sorted(resident_list))

resident_blocks = df[df["Resident"] == selected_resident]["block"].unique()
selected_block = st.sidebar.selectbox("Block You Want to Swap Out", sorted(resident_blocks))

on_elective = df[(df["Resident"] == selected_resident) & (df["block"] == selected_block)]["On_Elective"].iloc[0]
if not on_elective:
    st.error(f"⚠️ You are not on elective during Block {selected_block}. Swaps must involve elective blocks.")
    st.stop()

eligible_swaps = []

for _, row in df.iterrows():
    other_resident = row["Resident"]
    other_block = row["block"]
    other_date = row["date"]
    other_on_elective = row["On_Elective"]

    if other_resident == selected_resident:
        continue
    if other_block == selected_block:
        continue

    is_current_elective = row["On_Elective"]
    is_other_block_elective_for_user = df[
        (df["Resident"] == selected_resident) & (df["block"] == other_block)
    ]["On_Elective"]

    if not is_current_elective or is_other_block_elective_for_user.empty or not is_other_block_elective_for_user.iloc[0]:
        continue

    eligible_swaps.append({
        "Swap With": other_resident,
        "Their Block": other_block,
        "Their Block Dates": other_date
    })

if eligible_swaps:
    st.success(f"Found {len(eligible_swaps)} eligible swaps for Block {selected_block}:")
    st.dataframe(pd.DataFrame(eligible_swaps))
else:
    st.warning("No eligible swaps found for your selected block.")
