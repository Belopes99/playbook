import sys
import os
import pandas as pd
from google.cloud import bigquery

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.bq_io import get_bq_client

PROJECT_ID = "betterbet-467621"
DATASET_ID = "betterdata"
YEAR = 2025

def check_event_types():
    client = get_bq_client(project=PROJECT_ID)
    
    query = f"""
        SELECT type, COUNT(*) as count
        FROM `{PROJECT_ID}.{DATASET_ID}.eventos_brasileirao_serie_a_{YEAR}`
        GROUP BY 1
        ORDER BY 2 DESC
    """
    
    print(f"Querying distinct event types for {YEAR}...")
    df = client.query(query).to_dataframe()
    
    print("\n--- ACTUAL DB EVENT TYPES ---")
    print(df.to_string(index=False))
    
    # Expected types from pages/2_rankings.py (hardcoded for comparison)
    EXPECTED_TYPES = [
        "Pass", 
        "Goal", 
        "SavedShot", 
        "MissedShots", 
        "ShotOnPost", 
        "BallRecovery", 
        "Tackle", 
        "Interception", 
        "Foul", 
        "Save", 
        "Clearance", 
        "TakeOn", 
        "Aerial", 
        "Error", 
        "Challenge", 
        "Dispossessed",
        "BlockedPass",
        "Smother",
        "KeeperPickup"
    ]
    
    actual_types = df['type'].tolist()
    
    print("\n--- COMPARISON ---")
    missing_in_db = [t for t in EXPECTED_TYPES if t not in actual_types]
    if missing_in_db:
        print(f"WARNING: The following configured types DO NOT EXIST in DB:")
        for t in missing_in_db:
            print(f" - {t}")
    else:
        print("All configured types exist in DB.")
        
    missing_in_config = [t for t in actual_types if t not in EXPECTED_TYPES]
    if missing_in_config:
        print(f"INFO: The following valid DB types are NOT in config:")
        for t in missing_in_config:
            print(f" - {t}")

if __name__ == "__main__":
    check_event_types()
