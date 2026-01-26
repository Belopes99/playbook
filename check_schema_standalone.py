import tomllib
from google.cloud import bigquery
from google.oauth2 import service_account

try:
    # 1. Read Secrets
    with open(".streamlit/secrets.toml", "rb") as f:
        secrets = tomllib.load(f)
    
    info = secrets["gcp_service_account"]
    
    print(f"Info Project ID (from secrets): '{info.get('project_id')}'")
    
    # Use the project from secrets to see if data is THERE
    project_id = info.get("project_id")
    print(f"Using Project ID from secrets: {project_id}")

    # 2. Create Credentials
    credentials = service_account.Credentials.from_service_account_info(info)
    
    # 3. Create Client
    client = bigquery.Client(credentials=credentials, project=project_id)
    
    print(f"Client Project: '{client.project}'")
    
    # 4. Get Table
    table_id = f"{project_id}.betterdata.eventos_brasileirao_serie_a_2025"
    print(f"Getting table: {table_id}")
    table = client.get_table(table_id)
    
    print("COLUMNS FOUND:", [f.name for f in table.schema])
    
    cols = [f.name for f in table.schema]
    if 'player' in cols:
        print("SUCCESS: 'player' column found.")
    elif 'player_name' in cols:
        print("SUCCESS: 'player_name' column found.")
    else:
        # Check for similar columns
        print("Candidates for player:", [c for c in cols if 'player' in c.lower() or 'name' in c.lower()])
        
except Exception as e:
    print(f"ERROR: {e}")
