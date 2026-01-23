from __future__ import annotations

from typing import List, Dict, Tuple
import streamlit as st
from google.cloud import bigquery
import pandas as pd

PROJECT = "betterbet-467621"
DATASET = "betterdata"
SCHEDULE_PREFIX = "schedule_brasileirao_serie_a"


# get_bq_client removido daqui, importado de src.bq_io


def fq_table(prefix: str, year: int) -> str:
    return f"`{PROJECT}.{DATASET}.{prefix}_{int(year)}`"


def _years_from_ui(years: List[int] | None) -> List[int]:
    ys = sorted({int(y) for y in (years or [])})
    return ys if ys else [2025]


def _union_schedule_years(years: List[int]) -> str:
    parts = []
    for y in years:
        parts.append(f"SELECT home_team, away_team FROM {fq_table(SCHEDULE_PREFIX, y)}")
    return "\nUNION ALL\n".join(parts)


@st.cache_data(ttl=3600)
def load_teams_for_years(years: Tuple[int, ...]) -> List[str]:
    years_list = list(years)
    sql = f"""
    WITH s AS (
      {_union_schedule_years(years_list)}
    )
    SELECT DISTINCT team
    FROM (
      SELECT home_team AS team FROM s
      UNION DISTINCT
      SELECT away_team AS team FROM s
    )
    WHERE team IS NOT NULL
    ORDER BY team
    """
    from src.bq_io import get_bq_client
    df = get_bq_client().query(sql).to_dataframe()
    return df["team"].dropna().astype(str).tolist()


def render_sidebar_globals() -> Dict:
    st.sidebar.header("Filtros globais")

    years = st.sidebar.multiselect("Temporada(s)", list(range(2015, 2026)), default=[2025])
    years = _years_from_ui(years)
    years_t = tuple(years)

    teams_all = load_teams_for_years(years_t)
    teams = st.sidebar.multiselect("Time(s)", teams_all, default=teams_all[:1] if teams_all else [])

    globals_ = {"years": years, "teams": teams}

    st.session_state["years"] = years
    st.session_state["teams"] = teams

    return globals_
