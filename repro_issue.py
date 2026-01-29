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
TEAM = "Cruzeiro"

def check_goals():
    client = get_bq_client(project=PROJECT_ID)
    
    # 1. Get Game IDs for Cruzeiro in 2025
    schedule_query = f"""
        SELECT game_id, home_team, away_team
        FROM `{PROJECT_ID}.{DATASET_ID}.schedule_brasileirao_serie_a_{YEAR}`
        WHERE home_team = '{TEAM}' OR away_team = '{TEAM}'
    """
    
    games = client.query(schedule_query).to_dataframe()
    game_ids = games["game_id"].tolist()
    
    if not game_ids:
        print(f"No games found for {TEAM} in {YEAR}")
        return

    print(f"Found {len(game_ids)} games for {TEAM} in {YEAR}")
    
    games_list = ", ".join(map(str, game_ids))
    
    # 2. Get All Goals in these games
    # We want to see who scored and if it was an own goal
    events_query = f"""
        SELECT 
            game_id, 
            team, 
            player, 
            type, 
            qualifiers, 
            period, 
            minute, 
            second
        FROM `{PROJECT_ID}.{DATASET_ID}.eventos_brasileirao_serie_a_{YEAR}`
        WHERE game_id IN ({games_list})
        AND type = 'Goal'
    """
    
    goals = client.query(events_query).to_dataframe()
    
    print(f"Total Goals in Cruzeiro games: {len(goals)}")
    
    # Analyze attribution
    cruzeiro_goals_direct = 0
    cruzeiro_benefited_og = 0
    opponent_goals = 0
    
    print("\n--- GOAL ANALYSIS ---")
    for _, row in goals.iterrows():
        is_cruzeiro_action = (row['team'] == TEAM)
        is_own_goal = "OwnGoal" in row['qualifiers']
        
        # Logic:
        # 1. Action by Cruzeiro, NOT Own Goal -> Goal FOR Cruzeiro
        # 2. Action by Cruzeiro, IS Own Goal -> Goal AGAINST Cruzeiro (For Opponent)
        # 3. Action by Opponent, NOT Own Goal -> Goal AGAINST Cruzeiro (For Opponent)
        # 4. Action by Opponent, IS Own Goal -> Goal FOR Cruzeiro
        
        if is_cruzeiro_action:
            if not is_own_goal:
                cruzeiro_goals_direct += 1
                # print(f"Goal FOR Cruzeiro (Direct): {row['player']} ({row['minute']}')")
            else:
                opponent_goals += 1
                print(f"Own Goal BY Cruzeiro (Benefits Opponent): {row['player']} ({row['minute']}') - Team: {row['team']}")
        else:
            if not is_own_goal:
                opponent_goals += 1
            else:
                cruzeiro_benefited_og += 1
                print(f"Own Goal BY Opponent (Benefits Cruzeiro): {row['player']} ({row['minute']}') - Team: {row['team']}")

    print(f"\nSummary for {TEAM} {YEAR}:")
    print(f"Direct Goals by {TEAM}: {cruzeiro_goals_direct}")
    print(f"Own Goals favoring {TEAM}: {cruzeiro_benefited_og}")
    print(f"Total Goals FOR {TEAM}: {cruzeiro_goals_direct + cruzeiro_benefited_og}")
    print(f"Current System Likely Counts: {cruzeiro_goals_direct}") 
    # Current system queries `team = 'Cruzeiro'`, so it counts:
    # Goals by Cruzeiro (Direct) + Own Goals by Cruzeiro (Wrongly attributed as For?)
    
    # Actually current query: `team = 'Cruzeiro' AND type = 'Goal'`.
    # This includes Own Goals BY Cruzeiro (bad) and excludes Own Goals BY Opponent (good but missing).
    
    curr_sys_count = goals[goals['team'] == TEAM].shape[0]
    print(f"Rows with team='{TEAM}' and type='Goal': {curr_sys_count}")
    
    real_total = cruzeiro_goals_direct + cruzeiro_benefited_og
    print(f"REAL Total Goals For: {real_total}")
    
    difference = real_total - curr_sys_count
    print(f"Difference: {difference}")

if __name__ == "__main__":
    try:
        check_goals()
    except Exception as e:
        print(f"Error: {e}")
