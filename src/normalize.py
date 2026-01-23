from __future__ import annotations

import re
from typing import Iterable, Optional
import pandas as pd


# -----------------------------
# Helpers gerais
# -----------------------------
def _to_snake(name: str) -> str:
    """Converte nomes para snake_case (robusto para camelCase e espaços)."""
    if name is None:
        return name
    s = str(name).strip()
    s = s.replace("%", "pct")
    s = re.sub(r"[^\w\s]", "_", s)          # pontuação -> _
    s = re.sub(r"\s+", "_", s)              # espaços -> _
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", s)  # camelCase
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s) # camelCase
    s = re.sub(r"_+", "_", s)               # múltiplos _
    return s.lower().strip("_")


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza nomes de colunas para snake_case."""
    out = df.copy()
    out.columns = [_to_snake(c) for c in out.columns]
    return out


def coerce_numeric(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
    """Converte colunas para numérico (coerção segura)."""
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def coerce_int(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
    """Converte colunas para Int64 pandas (aceita NaN)."""
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").astype("Int64")
    return out


def coerce_datetime(df: pd.DataFrame, cols: Iterable[str], utc: bool = False) -> pd.DataFrame:
    """Converte colunas para datetime (robusto)."""
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = pd.to_datetime(out[c], errors="coerce", utc=utc)
    return out


def ensure_match_id(df: pd.DataFrame, candidates: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """
    Garante uma coluna `match_id` para joins.
    Procura por nomes comuns e renomeia para `match_id`.
    """
    if candidates is None:
        candidates = ["match_id", "matchid", "game_id", "id_partida", "match", "gameid"]

    out = df.copy()
    cols = list(out.columns)
    existing = {c.lower(): c for c in cols}

    for cand in candidates:
        if cand in existing:
            real = existing[cand]
            if real != "match_id":
                out = out.rename(columns={real: "match_id"})
            break

    # força tipo Int64 se existir
    if "match_id" in out.columns:
        out["match_id"] = pd.to_numeric(out["match_id"], errors="coerce").astype("Int64")

    return out


# -----------------------------
# Normalização específica
# -----------------------------
def normalize_events(df_events: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza DF de eventos (WhoScored-like):
    - nomes em snake_case
    - garante match_id
    - coercões de tipos comuns (minute/second/x/y/end_x/end_y/player_id/team_id)
    """
    out = standardize_columns(df_events)
    out = ensure_match_id(out)

    # ids comuns
    out = coerce_int(out, ["event_id", "id", "player_id", "team_id", "opponent_team_id"])

    # tempo
    out = coerce_int(out, ["minute", "second", "expanded_minute", "period", "match_period"])

    # coordenadas (podem vir como x,y,endx,endy etc.)
    # Normaliza nomes mais comuns:
    rename_map = {}
    if "endx" in out.columns and "end_x" not in out.columns:
        rename_map["endx"] = "end_x"
    if "endy" in out.columns and "end_y" not in out.columns:
        rename_map["endy"] = "end_y"
    if "x" in out.columns and "start_x" not in out.columns:
        # mantém x/y como x/y (muita gente usa assim)
        pass
    if rename_map:
        out = out.rename(columns=rename_map)

    out = coerce_numeric(out, ["x", "y", "end_x", "end_y"])

    # flags/outcome comuns
    # (mantém como está; só tenta reduzir bagunça de strings)
    for c in ["type", "event_type", "outcome_type", "outcome", "qualifiers"]:
        if c in out.columns:
            out[c] = out[c].astype(str)

    return out


def normalize_schedule(df_schedule: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza DF de schedule:
    - nomes em snake_case
    - garante match_id
    - datas em datetime
    - scores e ids em Int64
    """
    out = standardize_columns(df_schedule)
    out = ensure_match_id(out)

    # ids comuns (home/away)
    out = coerce_int(out, ["home_team_id", "away_team_id", "season", "round", "matchday"])

    # placar
    out = coerce_int(out, ["home_score", "away_score", "ft_home_score", "ft_away_score"])

    # datas comuns
    out = coerce_datetime(out, ["date", "match_date", "start_date", "kickoff_time", "utc_date"], utc=False)

    # padroniza "date" se existir outro nome
    if "date" not in out.columns:
        for alt in ["match_date", "start_date", "utc_date", "kickoff_time"]:
            if alt in out.columns:
                out = out.rename(columns={alt: "date"})
                break

    return out


def normalize_all(df_events: pd.DataFrame, df_schedule: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Convenience: normaliza ambos e garante match_id para join."""
    e = normalize_events(df_events)
    s = normalize_schedule(df_schedule)
    return e, s
