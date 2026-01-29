import sys
import os
import pandas as pd
from google.cloud import bigquery

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.bq_io import get_bq_client
from src.queries import get_dynamic_ranking_query

PROJECT_ID = "betterbet-467621"
DATASET_ID = "betterdata"
YEAR = 2025
TEAM = "Cruzeiro"

def verify_fix():
    print("Generating Dynamic Ranking Query for Cruzeiro 2025 Goals...")
    
    # We simulate the exact call made by the app
    # Subject="Equipes", EventTypes=["Goal"], Outcomes=["Todos"], Quals=["Todos"], Teams=["Cruzeiro"]
    
    query = get_dynamic_ranking_query(
        project_id=PROJECT_ID,
        dataset_id=DATASET_ID,
        subject="Equipes",
        event_types=["Goal"],
        outcomes="Todos",
        qualifiers="Todos (Qualquer)",
        use_related_player=False,
        teams=[TEAM],
        players=None
    )
    
    # print(query) # Debug if needed
    
    client = get_bq_client(project=PROJECT_ID)
    df = client.query(query).to_dataframe()
    
    # Filter for 2025
    df_2025 = df[df['season'] == YEAR]
    
    total_goals = df_2025['metric_count'].sum()
    
    print(f"\nTotal Goals (metric_count) for {TEAM} in {YEAR}: {total_goals}")
    
    if total_goals == 55:
        print("SUCCESS: Goal count is 55 as expected.")
    else:
        print(f"FAILURE: Goal count is {total_goals}, expected 55.")

if __name__ == "__main__":
    verify_fix()
