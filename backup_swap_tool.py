import streamlit as st
import pandas as pd

backup_df = pd.read_csv("backup_schedule_final.csv")
rotation_df = pd.read_csv("rotation_schedule.csv", index_col=0)

rotation_df.columns = [col.strip().lower() for col in rotation_df.columns]
rotation_df.index = rotation_df.index.str.strip()
rotation_df = rotation_df.applymap(lambda x: x.strip().lower() if isinstance(x, str) else x)

backup_df["Resident"] = backup_df["Resident"].str.strip()
backup_df["block"] = backup_df["block"].astype(str)

st.title("🟢 Backup Coverage Swap Tool")
st.write("Use this tool to find eligible backup block swaps among residents.")

resident_list = sorted(backup_df["Resident"].unique())
selected_resident = st.selectbox("Select your name:", resident_list)

resident_blocks = backup_df[backup_df["Resident"] == selected_resident]

st.subheader("📅 Your Current Backup Assignments")
st.dataframe(resident_blocks[["block", "date", "Backup_Type"]].reset_index(drop=True))

st.subheader("🔁 Eligible Swap Opportunities")

for _, row in resident_blocks.iterrows():
    block = row["block"]
    date = row["date"]

    candidates = backup_df[
        (backup_df["block"] == block) &
        (backup_df["Resident"] != selected_resident) &
        (backup_df["On_Elective"])
    ][["Resident", "Backup_Type"]].drop_duplicates()

    st.markdown(f"**Block {block} ({date})**")
    if candidates.empty:
        st.write("No eligible swaps for this block.")
    else:
        st.dataframe(candidates.reset_index(drop=True))
