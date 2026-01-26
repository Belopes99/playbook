import streamlit as st
import pandas as pd
import plotly.express as px

from src.css import load_css
from src.bq_io import get_bq_client
from src.queries import get_match_stats_query, get_player_rankings_query

st.set_page_config(page_title="Rankings Gerais", page_icon="📊", layout="wide")
load_css()

st.title("📊 Rankings Gerais")

# --- 1. CONFIGURATION & SIDEBAR ---
# Since we moved filters to main page as per user request
st.divider()

# --- 2. MAIN FILTERS ---
col_filter_1, col_filter_2 = st.columns(2)

with col_filter_1:
    subject = st.radio(
        "Analisar:",
        ["Equipes", "Jogadores"],
        index=0,
        horizontal=True
    )

with col_filter_2:
    aggregation_mode = st.radio(
        "Agrupamento:",
        ["Por Temporada (Ex: 2025)", "Histórico (Agregado)"],
        index=0,
        horizontal=True
    )

# --- 3. DATA LOADING ---
PROJECT_ID = "betterbet-467621"
DATASET_ID = "betterdata"

@st.cache_data(ttl=3600)
def load_team_data():
    client = get_bq_client(project=PROJECT_ID)
    query = get_match_stats_query(PROJECT_ID, DATASET_ID)
    return client.query(query).to_dataframe()

@st.cache_data(ttl=3600)
def load_player_data():
    client = get_bq_client(project=PROJECT_ID)
    query = get_player_rankings_query(PROJECT_ID, DATASET_ID)
    return client.query(query).to_dataframe()

try:
    if subject == "Equipes":
        df_raw = load_team_data()
    else:
        df_raw = load_player_data()
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

# --- 4. DATA PROCESSING (Aggregation) ---

if subject == "Equipes":
    # TEAM LOGIC
    if aggregation_mode.startswith("Por Temporada"):
        groupby_cols = ["team", "season"]
        df_raw["display_name"] = df_raw["team"] + " (" + df_raw["season"].astype(str) + ")"
        
        # Aggregation
        df_agg = df_raw.groupby(groupby_cols)[
            ["goals_for", "goals_against", "total_passes", "successful_passes", "total_shots", "shots_on_target"]
        ].sum().reset_index()
        
        # Restore display_name
        df_agg["display_name"] = df_agg["team"] + " (" + df_agg["season"].astype(str) + ")"
        
        # Match counts
        matches = df_raw.groupby(groupby_cols)["match_id"].nunique().reset_index(name="matches")
        df_agg = pd.merge(df_agg, matches, on=groupby_cols)
        
    else: # Historico/Agregado
        groupby_cols = ["team"]
        df_raw["display_name"] = df_raw["team"]
        
        df_agg = df_raw.groupby(groupby_cols)[
            ["goals_for", "goals_against", "total_passes", "successful_passes", "total_shots", "shots_on_target"]
        ].sum().reset_index()
        
        # Restore display_name
        df_agg["display_name"] = df_agg["team"]
        
        matches = df_raw.groupby(groupby_cols)["match_id"].nunique().reset_index(name="matches")
        df_agg = pd.merge(df_agg, matches, on=groupby_cols)

    # Metrics
    df_agg["goals_p90"] = df_agg["goals_for"] / df_agg["matches"]
    df_agg["shots_p90"] = df_agg["total_shots"] / df_agg["matches"]
    df_agg["pass_pct"] = (df_agg["successful_passes"] / df_agg["total_passes"]).fillna(0) * 100

elif subject == "Jogadores":
    # PLAYER LOGIC
    # df_raw cols from query: player, team, season, matches, goals, shots, successful_passes, total_passes
    
    if aggregation_mode.startswith("Por Temporada"):
        groupby_cols = ["player", "team", "season"]
        df_raw["display_name"] = df_raw["player"] + " (" + df_raw["team"] + " " + df_raw["season"].astype(str) + ")"
        
        # Already vaguely aggregated by query, but let's ensure uniqueness
        df_agg = df_raw.groupby(groupby_cols)[
            ["matches", "goals", "shots", "successful_passes", "total_passes"]
        ].sum().reset_index()
        
        # Restore display_name
        df_agg["display_name"] = df_agg["player"] + " (" + df_agg["team"] + " " + df_agg["season"].astype(str) + ")"
        
    else: # Historico/Agregado
        # Ignore team? Or include "Last Team"?
        # Usually for player rankings, aggregating across teams in same league is fine.
        groupby_cols = ["player"]
        df_raw["display_name"] = df_raw["player"]
        
        df_agg = df_raw.groupby(groupby_cols)[
            ["matches", "goals", "shots", "successful_passes", "total_passes"]
        ].sum().reset_index()
        
        # Restore display_name
        df_agg["display_name"] = df_agg["player"]
        
        # Determine "Team" for display (Latest or 'Multiple')
        # Simple approach: Join with list of teams
        # ignoring for now to keep simple

    # Metrics
    df_agg["goals_p90"] = (df_agg["goals"] / df_agg["matches"]).fillna(0)
    df_agg["shots_p90"] = (df_agg["shots"] / df_agg["matches"]).fillna(0)
    df_agg["pass_pct"] = (df_agg["successful_passes"] / df_agg["total_passes"]).fillna(0) * 100
    
    # Aliasing for consistency with Team logic for Charts
    df_agg["goals_for"] = df_agg["goals"] 
    df_agg["total_shots"] = df_agg["shots"]


# --- 5. VISUALIZATION ---

tab1, tab2 = st.tabs(["📊 Rankings (Gols)", "📋 Dados Detalhados"])

with tab1:
    st.subheader(f"Top {subject} por Gols")
    
    # Filter Top N
    top_n = st.slider("Quantidade de itens:", 5, 50, 20)
    
    df_chart = df_agg.sort_values("goals_for", ascending=False).head(top_n)
    
    fig = px.bar(
        df_chart,
        x="goals_for",
        y="display_name",
        orientation='h',
        color="goals_p90", # Color by efficiency
        color_continuous_scale="Viridis",
        text="goals_for",
        labels={
            "goals_for": "Total de Gols",
            "display_name": subject[:-1], # Singularish
            "goals_p90": "Gols/Jogo"
        }
    )
    
    fig.update_layout(yaxis={'categoryorder':'total ascending'}, template="plotly_dark", height=600)
    fig.update_traces(textposition='outside')
    
    st.plotly_chart(fig, use_container_width=True)


with tab2:
    st.dataframe(
        df_agg.sort_values("goals_for", ascending=False),
        use_container_width=True,
        hide_index=True
    )
