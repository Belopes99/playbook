import sys
import os
import pandas as pd
from google.cloud import bigquery

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.bq_io import get_bq_client
from src.queries import get_conversion_ranking_query

PROJECT_ID = "betterbet-467621"
DATASET_ID = "betterdata"
YEAR = 2025
TEAM = "Cruzeiro"

def verify_conversion():
    print("Generating Conversion Ranking Query for Cruzeiro 2025 Goal Conversion...")
    
    # Numerator: Goal
    num_types = ["Goal"]
    
    # Denominator: All Shots (Approx)
    den_types = ["Goal", "SavedShot", "MissedShots", "ShotOnPost", "BlockedPass"]
    
    query = get_conversion_ranking_query(
        project_id=PROJECT_ID,
        dataset_id=DATASET_ID,
        subject="Equipes",
        
        # Num
        num_event_types=num_types,
        num_outcomes="Todos",
        num_qualifiers="Todos (Qualquer)",
        
        # Den
        den_event_types=den_types,
        den_outcomes="Todos",
        den_qualifiers="Todos (Qualquer)",
        
        teams=[TEAM],
        players=None
    )
    
    client = get_bq_client(project=PROJECT_ID)
    df = client.query(query).to_dataframe()
    
    # Filter for 2025
    df = df[df['season'] == YEAR]
    
    if df.empty:
        print("No data returned.")
        return

    row = df.iloc[0]
    
    print("\n--- RESULTS ---")
    print(f"Team: {row['team']}")
    print(f"Example Match ID: {row['game_id']}")
    print(f"Values check (First Row): Num={row['numerator']}, Den={row['denominator']}, Ratio={row['ratio']}")
    
    # Aggregate for season
    total_num = df['numerator'].sum()
    total_den = df['denominator'].sum()
    
    ratio = (total_num / total_den) if total_den > 0 else 0
    pct = ratio * 100
    
    print(f"\nSEASON TOTALS ({YEAR}):")
    print(f"Total Goals (Num): {total_num}")
    print(f"Total Shots (Den): {total_den}")
    print(f"Conversion Rate: {pct:.2f}%")
    
    if total_num == 55:
        print("Numerator matches expected Goal Count (55). OK.")
    else:
        print(f"WARNING: Numerator {total_num} != 55")

if __name__ == "__main__":
    verify_conversion()
