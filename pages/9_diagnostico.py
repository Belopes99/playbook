import streamlit as st
import pandas as pd
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.bq_io import get_bq_client
from src.queries import get_teams_match_count_query
from src.css import load_css

st.set_page_config(page_title="Diagnóstico de Dados", page_icon="🔧", layout="wide")
load_css()

st.title("🔧 Diagnóstico de Integridade de Dados")
st.markdown("""
Esta ferramenta verifica se todas as equipes possuem **38 jogos** por temporada.
Se houver menos, significa que há jogos faltando na base de dados.
""")

st.divider()

# --- CONFIG ---
PROJECT_ID = "betterbet-467621"
DATASET_ID = "betterdata"

@st.cache_data(ttl=60)
def load_audit_data():
    client = get_bq_client(project=PROJECT_ID)
    query = get_teams_match_count_query(PROJECT_ID, DATASET_ID)
    df = client.query(query).to_dataframe()
    return df

try:
    with st.spinner("Auditando base de dados..."):
        df = load_audit_data()
except Exception as e:
    st.error(f"Erro ao auditar dados: {e}")
    st.stop()

if df.empty:
    st.info("Nenhum dado encontrado.")
    st.stop()

# --- LOGIC ---
# Highlight logic
def highlight_rows(row):
    # Rule: If season is completed (<= 2024 for example), it MUST be 38.
    # If 2025 (current), it can be anything.
    # Let's assume 2024 passed.
    
    season = row['season']
    games = row['total_games']
    
    current_season = 2025 # Or dynamic
    
    if season < current_season and games != 38:
        return ['background-color: #551111'] * len(row)
    elif season < current_season and games == 38:
        return ['background-color: #113311'] * len(row)
    return [''] * len(row)

st.subheader("Relatório de Jogos por Equipe/Temporada")

# Filter options
seasons = sorted(df['season'].unique(), reverse=True)
sel_season = st.multiselect("Filtrar Temporadas", seasons, default=seasons[:1])

if sel_season:
    df_show = df[df['season'].isin(sel_season)]
else:
    df_show = df

# --- METRICS & TABS ---
c1, c2 = st.columns(2)
problems = df_show[ (df_show['season'] < 2025) & (df_show['total_games'] != 38) ]
c1.metric("Registros Analisados (Linhas)", len(df_show))
c2.metric("Inconsistências (Linhas)", len(problems), delta_color="inverse")

if not problems.empty:
    st.warning(f"⚠️ Atenção! Encontradas {len(problems)} registros com número de jogos diferente de 38 em temporadas passadas.")

tab_detail, tab_macro = st.tabs(["📋 Detalhado (Por Temporada)", "🔎 Visão Macro (Acumulado)"])

with tab_detail:
    st.dataframe(
        df_show.style.apply(highlight_rows, axis=1),
        use_container_width=True,
        height=800
    )

with tab_macro:
    st.markdown("### Total de Jogos por Equipe (Soma das Temporadas Selecionadas)")
    if not sel_season:
        st.info("Selecione temporadas acima para visualizar o acumulado.")
    else:
        # Aggregation
        df_macro = df_show.groupby("team")["total_games"].sum().reset_index()
        df_macro = df_macro.sort_values("total_games", ascending=False)
        
        # Calculate Expected Games
        # Logic: If all selected seasons are COMPLETED (assume < 2025), expected = 38 * count.
        # If 2025 is in selection, expected varies.
        # We can just show the number of seasons present for that team.
        
        # Count unique seasons per team in the selection
        seasons_per_team = df_show.groupby("team")["season"].nunique().reset_index(name="num_seasons")
        df_macro = pd.merge(df_macro, seasons_per_team, on="team")
        
        # Display
        st.dataframe(
            df_macro,
            use_container_width=True,
            column_config={
                "team": "Equipe",
                "total_games": "Total de Jogos",
                "num_seasons": "Temporadas Disputadas (na seleção)"
            },
            hide_index=True
            },
            hide_index=True
        )

# --- NEW TAB: QUALIFIERS INSPECTOR ---
# To debug why KeyPass == Assist
with st.spinner("Carregando inspetor de qualifiers..."):
    # We need a new query to fetch raw qualifiers for inspection
    # Limited to recent events to avoid huge load
    pass

st.divider()
st.subheader("🔍 Inspetor de Qualifiers (Tags)")

@st.cache_data(ttl=300)
def inspect_qualifiers_query(project_id, dataset_id, event_type="Pass", limit=1000):
    # Fetch raw qualifiers for specific event type
    # Using 2024 as default recent sample
    return f"""
    SELECT 
        game_id, 
        player, 
        team, 
        type, 
        outcome_type,
        qualifiers
    FROM `{project_id}.{dataset_id}.eventos_brasileirao_serie_a_2024`
    WHERE type = '{event_type}'
    LIMIT {limit}
    """

col_insp_1, col_insp_2 = st.columns(2)
with col_insp_1:
    insp_type = st.selectbox("Tipo de Evento para Inspeção", ["Pass", "Shot", "Foul", "Goal"], index=0)
with col_insp_2:
    insp_limit = st.number_input("Amostra (linhas)", 100, 10000, 1000)

if st.button("Carregar Amostra de Qualifiers"):
    try:
        client = get_bq_client(project=PROJECT_ID)
        q_insp = inspect_qualifiers_query(PROJECT_ID, DATASET_ID, insp_type, insp_limit)
        df_insp = client.query(q_insp).to_dataframe()
        
        st.success(f"Carregado {len(df_insp)} eventos do tipo {insp_type}.")
        
        # Analysis
        # 1. Check regex matches for Assist vs KeyPass
        re_assist = r"['\"]displayName['\"]\s*:\s*['\"]Assist['\"]"
        re_key = r"['\"]displayName['\"]\s*:\s*['\"]KeyPass['\"]"
        
        import re
        
        def has_tag(text, pattern):
            if not isinstance(text, str): return False
            return bool(re.search(pattern, text))
            
        df_insp["Has_Assist"] = df_insp["qualifiers"].apply(lambda x: has_tag(x, re_assist))
        df_insp["Has_KeyPass"] = df_insp["qualifiers"].apply(lambda x: has_tag(x, re_key))
        
        # Summary
        c1, c2, c3 = st.columns(3)
        c1.metric("Total com Assist", df_insp["Has_Assist"].sum())
        c2.metric("Total com KeyPass", df_insp["Has_KeyPass"].sum())
        c3.metric("Interseção (Ambos)", df_insp[(df_insp["Has_Assist"]) & (df_insp["Has_KeyPass"])].shape[0])
        
        st.markdown("##### Visualizar Dados Brutos (Onde existe overlap)")
        st.dataframe(
            df_insp[df_insp["Has_Assist"] | df_insp["Has_KeyPass"]].head(50),
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"Erro na inspeção: {e}")
