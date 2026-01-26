import streamlit as st
from src.bq_io import get_bq_client

# Mock secrets if needed (but running locally it should pick up if set, 
# or I rely on the user's environment if they run it via streamlit run, but I'll try to run as plain python script)
# However, src.bq_io uses st.secrets. Running as plain python might fail if secrets aren't loaded.
# I will use 'streamlit run' for this script or just rely on 'src.bq_io' logic. 
# Actually, the simplest way is to assume it works or peek at a known file.
# Let's try to query one row and print columns.

try:
    client = get_bq_client(project="betterbet-448216")
    query = """
    SELECT *
    FROM `betterbet-448216.betterdata.events_brasileirao_serie_a_2025`
    LIMIT 1
    """
    df = client.query(query).to_dataframe()
    print("COLUMNS FOUND:", df.columns.tolist())
    if 'player' in df.columns:
        print("SUCCESS: 'player' column found.")
    elif 'player_name' in df.columns:
        print("SUCCESS: 'player_name' column found.")
    else:
        print("FAILURE: No player column found.")
        
except Exception as e:
    print(f"ERROR: {e}")
