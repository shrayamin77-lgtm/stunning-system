import streamlit as st
import pandas as pd

rotation_df = pd.read_csv("rotation_schedule.csv")
backup_df = pd.read_csv("backup_schedule_final.csv")

backup_long_df = pd.melt(
    backup_df,
    id_vars=["block", "date"],
    value_vars=["1st Backup", "2nd Backup"],
    var_name="Backup_Type",
    value_name="Resident"
)
backup_long_df = backup_long_df.dropna(subset=["Resident"])
backup_long_df = backup_long_df[backup_long_df["Resident"] != "—"]
backup_long_df["block"] = backup_long_df["block"].astype(int)
rotation_df.columns = rotation_df.columns.astype(str)

elective_blocks = {
    r: set(rotation_df.columns[rotation_df.loc[rotation_df["Name"] == r].eq("Elective").any()].astype(int))
    for r in backup_long_df["Resident"].unique()
}

st.title("Backup Block Swap Tool")

resident_input = st.selectbox("Select your name:", sorted(backup_long_df["Resident"].unique()))
block_input = st.selectbox("Which block are you trying to swap?", sorted(backup_long_df[backup_long_df["Resident"] == resident_input]["block"].unique()))

your_blocks = backup_long_df[(backup_long_df["Resident"] == resident_input) & (backup_long_df["block"] == block_input)]
your_block = int(block_input)

swap_candidates = backup_long_df[
    (backup_long_df["block"] != your_block) &
    (backup_long_df["Resident"] != resident_input)
]

eligible_swaps = []
for _, row in swap_candidates.iterrows():
    other = row["Resident"]
    other_block = int(row["block"])
    if (
        other_block in elective_blocks.get(resident_input, set()) and
        your_block in elective_blocks.get(other, set())
    ):
        eligible_swaps.append((other, other_block, row["date"]))

if eligible_swaps:
    st.write("### Eligible swap partners:")
    for name, block, date in eligible_swaps:
        st.write(f"- {name} (Block {block}, {date})")
else:
    st.warning("No eligible swaps found.")
