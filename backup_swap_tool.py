import streamlit as st
import pandas as pd

# Load files
backup_df = pd.read_csv("backup_schedule_final.csv")
rotation_df = pd.read_csv("rotation_schedule.csv", index_col=0)

# Clean rotation headers (e.g., "Block 1", ..., "Block 26")
rotation_df.columns = [col.strip().lower() for col in rotation_df.columns]
rotation_df.index = rotation_df.index.str.strip()
rotation_df = rotation_df.applymap(lambda x: x.strip().lower() if isinstance(x, str) else x)

# Melt the backup schedule
backup_long = pd.melt(
    backup_df,
    id_vars=["block", "date"],
    value_vars=["1st Backup", "2nd Backup"],
    var_name="Backup_Type",
    value_name="Resident"
)
backup_long["Resident"] = backup_long["Resident"].str.strip()
backup_long["block"] = backup_long["block"].astype(str)

# Define elective checker
def is_on_elective(resident, block):
    block_col = f"block {block}"
    if resident in rotation_df.index and block_col in rotation_df.columns:
        return rotation_df.loc[resident, block_col] == "elective"
    return False

backup_long["On_Elective"] = backup_long.apply(
    lambda row: is_on_elective(row["Resident"], row["block"]), axis=1
)

# App UI
st.title("🟢 Backup Coverage Swap Tool")
st.write("Use this tool to find eligible backup block swaps among residents.")

resident_list = sorted(backup_long["Resident"].unique())
selected_resident = st.selectbox("Select your name:", resident_list)

# Filter for selected resident’s blocks
resident_blocks = backup_long[backup_long["Resident"] == selected_resident]

# Show current backup assignments
st.subheader("📅 Your Current Backup Assignments")
st.dataframe(resident_blocks[["block", "date"]].reset_index(drop=True))

# Show eligible swap candidates per block
st.subheader("🔁 Eligible Swap Opportunities")

for _, row in resident_blocks.iterrows():
    block = row["block"]
    date = row["date"]

    # Find other backups who are also on elective during that block
    candidates = backup_long[
        (backup_long["block"] == block) &
        (backup_long["Resident"] != selected_resident) &
        (backup_long["On_Elective"])
    ][["Resident", "Backup_Type"]].drop_duplicates()

    st.markdown(f"**Block {block} ({date})**")
    if candidates.empty:
        st.write("No eligible swaps for this block.")
    else:
        st.dataframe(candidates.reset_index(drop=True))

