from __future__ import annotations

from typing import Iterable, Optional
import pandas as pd


# -----------------------------
# Helpers
# -----------------------------
def _first_existing(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    """Retorna o primeiro nome de coluna existente no df."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


# -----------------------------
# Filters - Schedule
# -----------------------------
def filter_by_season(
    df_schedule: pd.DataFrame,
    seasons: Optional[Iterable[int]] = None,
) -> pd.DataFrame:
    """
    Filtra por temporada/ano.
    Detecta automaticamente a coluna correta.
    """
    if not seasons:
        return df_schedule

    col = _first_existing(
        df_schedule,
        candidates=[
            "season",
            "season_id",
            "year",
            "competition_season",
            "tournament_season",
        ],
    )

    if col is None:
        # não quebra o pipeline
        return df_schedule

    return df_schedule[df_schedule[col].isin(seasons)].copy()


def filter_matches(
    df_schedule: pd.DataFrame,
    teams: Optional[Iterable[str]] = None,
    status: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    out = df_schedule.copy()

    if teams:
        teams = set(teams)
        if "home_team" in out.columns and "away_team" in out.columns:
            out = out[
                (out["home_team"].isin(teams)) |
                (out["away_team"].isin(teams))
            ]

    if status and "status" in out.columns:
        out = out[out["status"].isin(status)]

    return out


# -----------------------------
# Filters - Events
# -----------------------------
def filter_events_by_matches(
    df_events: pd.DataFrame,
    match_ids: Iterable[int],
) -> pd.DataFrame:
    if "match_id" not in df_events.columns:
        return df_events
    return df_events[df_events["match_id"].isin(match_ids)].copy()


def filter_events(
    df_events: pd.DataFrame,
    teams: Optional[Iterable[str]] = None,
    event_types: Optional[Iterable[str]] = None,
    minutes: Optional[tuple[int, int]] = None,
) -> pd.DataFrame:
    out = df_events.copy()

    if teams and "team" in out.columns:
        out = out[out["team"].isin(teams)]

    if event_types:
        col = _first_existing(out, ["type", "event_type"])
        if col:
            out = out[out[col].isin(event_types)]

    if minutes and "expanded_minute" in out.columns:
        m0, m1 = minutes
        out = out[
            (out["expanded_minute"] >= m0) &
            (out["expanded_minute"] <= m1)
        ]

    return out
