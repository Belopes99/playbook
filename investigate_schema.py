
import toml
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
import os

if os.path.exists(".streamlit/secrets.toml"):
    SECRETS_PATH = ".streamlit/secrets.toml"
elif os.path.exists("Scouting/Streamlit/.streamlit/secrets.toml"):
    SECRETS_PATH = "Scouting/Streamlit/.streamlit/secrets.toml"
else:
    SECRETS_PATH = r"c:\Users\belop\OneDrive\Área de Trabalho\Prodigy.co\Scouting\Streamlit\.streamlit\secrets.toml"

PROJECT_ID = "betterbet-467621"
DATASET_ID = "betterdata"

def get_client():
    try:
        if os.path.exists(SECRETS_PATH):
            secrets = toml.load(SECRETS_PATH)
            if "gcp_service_account" in secrets:
                info = secrets["gcp_service_account"]
                credentials = service_account.Credentials.from_service_account_info(info)
                return bigquery.Client(credentials=credentials, project=PROJECT_ID)
    except Exception:
        pass
    return bigquery.Client(project=PROJECT_ID)

def check_optimizations():
    client = get_client()
    
    print("--- Goal Analysis: Assisted Qualifier vs Related Player ---")
    # Check if there are Goals with 'Assisted' qualifier but NO related_player_id (orphaned assist?)
    # Or Goals with related_player_id but NO 'Assisted' flag (maybe rebound?)
    query_goal = f"""
    SELECT 
        COUNTIF(qualifiers LIKE '%Assisted%') as has_assisted_tag,
        COUNTIF(related_player_id IS NOT NULL) as has_related_player,
        COUNTIF(qualifiers LIKE '%Assisted%' AND related_player_id IS NULL) as assisted_but_no_player,
        COUNTIF(related_player_id IS NOT NULL AND qualifiers NOT LIKE '%Assisted%') as player_but_not_assisted
    FROM `{PROJECT_ID}.{DATASET_ID}.eventos_brasileirao_serie_a_2024`
    WHERE type = 'Goal'
    """
    df_goal = client.query(query_goal).to_dataframe()
    print(df_goal.transpose())
    
    print("\n--- Big Chances ---")
    # Check distinct tags for Big Chance
    # Usually 'BigChanceCreated' on Pass?
    query_bc = f"""
    SELECT 
        type,
        COUNT(*) as cnt
    FROM `{PROJECT_ID}.{DATASET_ID}.eventos_brasileirao_serie_a_2024`
    WHERE qualifiers LIKE '%BigChanceCreated%'
    GROUP BY 1
    ORDER BY 2 DESC
    """
    df_bc = client.query(query_bc).to_dataframe()
    print(df_bc)
    
    print("\n--- Errors ---")
    # 'Error' type
    query_err = f"""
    SELECT 
        qualifiers,
        COUNT(*) as cnt
    FROM `{PROJECT_ID}.{DATASET_ID}.eventos_brasileirao_serie_a_2024`
    WHERE type = 'Error'
    GROUP BY 1
    ORDER BY 2 DESC
    LIMIT 10
    """
    df_err = client.query(query_err).to_dataframe()
    for q in df_err['qualifiers']:
        print(q)

if __name__ == "__main__":
    check_optimizations()
