import streamlit as st
import pandas as pd

# Load backup and rotation schedules
backup_df = pd.read_csv("backup_schedule_final.csv")
rotation_df = pd.read_csv("rotation_schedule.csv")

# Melt backup schedule into long format
backup_long = pd.melt(
    backup_df,
    id_vars=["Block"],
    value_vars=["1st Backup", "2nd Backup"],
    var_name="Backup Type",
    value_name="Resident"
)

# Create a map of elective blocks per resident
elective_blocks_by_resident = {
    r: {
        int(col)
        for col in rotation_df.columns[1:]  # Skip "Name"
        if col.isdigit() and rotation_df.loc[rotation_df["Name"] == r, col].values[0] == "Elective"
    }
    for r in rotation_df["Name"]
}

# Streamlit UI
st.title("Backup Swap Finder")
resident_input = st.selectbox("Select your name", backup_long["Resident"].unique())
block_input = st.selectbox("Select the block you're trying to swap out of", backup_long[backup_long["Resident"] == resident_input]["Block"].unique())

# Find matching swap candidates
eligible_swaps = []
for _, row in backup_long.iterrows():
    other_resident = row["Resident"]
    other_block = row["Block"]
    
    if (
        other_resident != resident_input and
        other_block in elective_blocks_by_resident.get(resident_input, set()) and
        block_input in elective_blocks_by_resident.get(other_resident, set())
    ):
        eligible_swaps.append((other_resident, other_block))

# Display results
if eligible_swaps:
    st.subheader("Eligible Swap Options:")
    for res, blk in eligible_swaps:
        st.write(f"- {res} (Block {blk})")
else:
    st.warning("No eligible swaps found.")
