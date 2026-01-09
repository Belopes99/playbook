from __future__ import annotations

from typing import List, Tuple, Optional
import io

import streamlit as st
import pandas as pd
from google.cloud import bigquery

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Arc

from src.ui_filters import render_sidebar_globals, get_bq_client

# =========================================
# CONFIG BQ
# =========================================

PROJECT = "playbook-database-477918"
DATASET = "brasileirao_serie_a"

EVENTS_PREFIX = "events_brasileirao_serie_a"
SCHEDULE_PREFIX = "schedule_brasileirao_serie_a"

# Fundo do PNG exportado (para não “sumir” no download)
EXPORT_BG = "#0e1117"

# =========================================
# PITCH CONFIG
# =========================================

PITCH_LENGTH = 105.0  # metros
PITCH_WIDTH = 68.0    # metros

# =========================================
# SQL HELPERS
# =========================================


def fq_table(prefix: str, year: int) -> str:
    return f"`{PROJECT}.{DATASET}.{prefix}_{int(year)}`"


def union_sql(prefix: str, years: Tuple[int, ...], select_clause: str) -> str:
    return "\nUNION ALL\n".join(
        f"{select_clause} FROM {fq_table(prefix, y)}" for y in years
    )


def run_query(sql: str, params: Optional[list] = None) -> pd.DataFrame:
    client = get_bq_client()
    cfg = bigquery.QueryJobConfig(query_parameters=params or [])
    return client.query(sql, job_config=cfg).to_dataframe()


@st.cache_data(ttl=3600)
def detect_match_id_col(prefix: str, year: int) -> str:
    client = get_bq_client()
    table_id = f"{PROJECT}.{DATASET}.{prefix}_{int(year)}"
    schema = client.get_table(table_id).schema
    cols = [f.name for f in schema]

    candidates = [
        "game_id", "gameId",
        "match_id", "matchId", "matchID",
        "fixture_id", "fixtureId",
        "id", "Id",
    ]

    for c in candidates:
        if c in cols:
            return c

    for c in cols:
        lc = c.lower()
        if "game" in lc and "id" in lc:
            return c
        if "match" in lc and "id" in lc:
            return c
        if "fixture" in lc and "id" in lc:
            return c

    raise ValueError(
        f"Não consegui detectar a coluna de ID da partida em {table_id}. Colunas: {cols}"
    )


# =========================================
# PITCH + PLOT HELPERS
# =========================================


def _scale_series_to_0_100(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    vv = s.dropna()
    if len(vv) > 0 and (vv.between(0, 1).mean() > 0.95):
        return s * 100.0
    return s


def draw_pitch(ax, style: dict):
    line_color = style.get("pitch_line_color", "#9aa0a6")
    lw = style.get("pitch_line_width", 1.15)

    L = PITCH_LENGTH
    W = PITCH_WIDTH

    ax.set_xlim(0, L)
    ax.set_ylim(0, W)
    ax.set_aspect("equal", adjustable="box")

    ax.add_patch(Rectangle((0, 0), L, W, fill=False, edgecolor=line_color, lw=lw))
    ax.plot([L / 2, L / 2], [0, W], color=line_color, lw=lw)

    center_circle_r = 9.15
    ax.add_patch(
        Arc(
            (L / 2, W / 2),
            2 * center_circle_r,
            2 * center_circle_r,
            theta1=0,
            theta2=360,
            color=line_color,
            lw=lw,
        )
    )

    pa_depth = 16.5
    pa_width = 40.32
    pa_y0 = (W - pa_width) / 2
    ax.add_patch(Rectangle((0, pa_y0), pa_depth, pa_width, fill=False, edgecolor=line_color, lw=lw))
    ax.add_patch(Rectangle((L - pa_depth, pa_y0), pa_depth, pa_width, fill=False, edgecolor=line_color, lw=lw))

    ga_depth = 5.5
    ga_width = 18.32
    ga_y0 = (W - ga_width) / 2
    ax.add_patch(Rectangle((0, ga_y0), ga_depth, ga_width, fill=False, edgecolor=line_color, lw=lw))
    ax.add_patch(Rectangle((L - ga_depth, ga_y0), ga_depth, ga_width, fill=False, edgecolor=line_color, lw=lw))

    ax.axis("off")


def add_attack_direction(ax, style: dict):
    text_color = style.get("text_color", "#c9cdd1")
    arrow_color = style.get("arrow_color", "#c9cdd1")

    y = 1.03
    ax.annotate(
        "",
        xy=(0.72, y),
        xytext=(0.28, y),
        xycoords="axes fraction",
        textcoords="axes fraction",
        arrowprops=dict(arrowstyle="->", color=arrow_color, lw=2.0),
        annotation_clip=False,
    )
    ax.text(
        0.5, y + 0.02, "Sentido do ataque →",
        transform=ax.transAxes,
        ha="center", va="bottom",
        color=text_color, fontsize=11,
        clip_on=False,
    )


def apply_attack_orientation(
    df: pd.DataFrame,
    focus_teams: Tuple[str, ...],
    x_col: str = "x_plot",
    y_col: str = "y_plot",
    endx_col: str = "end_x_plot",
    endy_col: str = "end_y_plot",
) -> pd.DataFrame:
    out = df.copy()

    if "team" not in out.columns:
        return out

    L = PITCH_LENGTH
    W = PITCH_WIDTH

    teams_set = set(map(str, focus_teams))
    mask_opp = ~out["team"].astype(str).isin(teams_set)

    if x_col in out.columns:
        out.loc[mask_opp, x_col] = L - out.loc[mask_opp, x_col]
    if y_col in out.columns:
        out.loc[mask_opp, y_col] = W - out.loc[mask_opp, y_col]

    if endx_col in out.columns and endy_col in out.columns:
        out.loc[mask_opp, endx_col] = L - out.loc[mask_opp, endx_col]
        out.loc[mask_opp, endy_col] = W - out.loc[mask_opp, endy_col]

    return out


def plot_events_pitch(
    df_events_plot: pd.DataFrame,
    draw_arrows: bool,
    color_by_outcome: bool,
    style: dict,
):
    fig_w = 14.5
    fig_h = fig_w * (PITCH_WIDTH / PITCH_LENGTH)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    fig_bg = style.get("fig_bg", "none")
    ax_bg = style.get("ax_bg", "none")
    fig.patch.set_facecolor(fig_bg)
    ax.set_facecolor(ax_bg)

    draw_pitch(ax, style)
    add_attack_direction(ax, style)

    has_end = ("end_x_plot" in df_events_plot.columns and "end_y_plot" in df_events_plot.columns)

    ok_color = style.get("ok_color", "#7CFC98")
    bad_color = style.get("bad_color", "#FF6B6B")

    event_color = style.get("event_color", "#c9cdd1")
    event_alpha = float(style.get("event_alpha", 0.88))
    event_size = int(style.get("event_size", 26))

    arrow_alpha = float(style.get("arrow_alpha", 0.65))
    arrow_width = float(style.get("arrow_width", 0.0022))

    legend_text_color = style.get("legend_text_color", style.get("text_color", "#c9cdd1"))

    def plot_group(g: pd.DataFrame, color: str, label: Optional[str] = None):
        ax.scatter(
            g["x_plot"], g["y_plot"],
            s=event_size,
            alpha=event_alpha,
            color=color,
            label=label,
            zorder=3,
        )

        if draw_arrows and has_end:
            gg = g.dropna(subset=["end_x_plot", "end_y_plot"])
            if not gg.empty:
                ax.quiver(
                    gg["x_plot"], gg["y_plot"],
                    gg["end_x_plot"] - gg["x_plot"],
                    gg["end_y_plot"] - gg["y_plot"],
                    angles="xy",
                    scale_units="xy",
                    scale=1,
                    width=arrow_width,
                    alpha=arrow_alpha,
                    color=color,
                    zorder=2,
                )

    if color_by_outcome and "outcome_type" in df_events_plot.columns:
        succ = df_events_plot[df_events_plot["outcome_type"] == "Successful"]
        fail = df_events_plot[df_events_plot["outcome_type"] != "Successful"]

        if not succ.empty:
            plot_group(succ, ok_color, "Successful")
        if not fail.empty:
            plot_group(fail, bad_color, "Unsuccessful")

        leg = ax.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.06),
            ncol=2,
            frameon=False,
        )
        if leg is not None:
            plt.setp(leg.get_texts(), color=legend_text_color)
    else:
        ax.scatter(
            df_events_plot["x_plot"], df_events_plot["y_plot"],
            s=event_size,
            alpha=event_alpha,
            color=event_color,
            zorder=3,
        )

        if draw_arrows and has_end:
            gg = df_events_plot.dropna(subset=["end_x_plot", "end_y_plot"])
            ax.quiver(
                gg["x_plot"], gg["y_plot"],
                gg["end_x_plot"] - gg["x_plot"],
                gg["end_y_plot"] - gg["y_plot"],
                angles="xy",
                scale_units="xy",
                scale=1,
                width=arrow_width,
                alpha=arrow_alpha,
                color=event_color,
                zorder=2,
            )

    fig.subplots_adjust(top=0.90, right=0.98, left=0.05, bottom=0.14)
    return fig


def fig_to_png_bytes(fig, style: dict, bg_key: str = "fig_bg") -> bytes:
    buf = io.BytesIO()

    fig_bg = style.get(bg_key, "none")
    transparent = (str(fig_bg).lower() == "none")

    # Mantém o padrão: PNG sempre com fundo sólido (EXPORT_BG)
    if transparent:
        face = EXPORT_BG
        edge = EXPORT_BG
        transparent_flag = False
    else:
        face = fig_bg if fig_bg else EXPORT_BG
        edge = face
        transparent_flag = False

    fig.savefig(
        buf,
        format="png",
        dpi=200,
        bbox_inches="tight",
        facecolor=face,
        edgecolor=edge,
        transparent=transparent_flag,
    )

    buf.seek(0)
    return buf.read()


# =========================================
# FILTER HELPERS
# =========================================


def match_label(row: pd.Series) -> str:
    dt = row.get("start_time", None)
    try:
        dt = pd.to_datetime(dt, errors="coerce", utc=True)
        dt_str = dt.tz_convert("America/Sao_Paulo").strftime("%Y-%m-%d %H:%M") if pd.notna(dt) else "sem data"
    except Exception:
        dt_str = "sem data"
    return f"{dt_str} • {row.get('home_team','?')} vs {row.get('away_team','?')} • match_id={int(row['match_id'])}"


def infer_opponents(df_matches: pd.DataFrame, teams: Tuple[str, ...]) -> List[str]:
    if df_matches.empty:
        return []

    teams_set = set(teams)
    opps = set()

    for r in df_matches.itertuples(index=False):
        if getattr(r, "home_team", None) in teams_set and pd.notna(getattr(r, "away_team", None)):
            opps.add(str(r.away_team))
        if getattr(r, "away_team", None) in teams_set and pd.notna(getattr(r, "home_team", None)):
            opps.add(str(r.home_team))

    return sorted(opps)


# =========================================
# LOADERS (cached)
# =========================================


@st.cache_data(ttl=900)
def load_matches(
    years: Tuple[int, ...],
    teams: Tuple[str, ...],
    home_away: Tuple[str, ...],
    sched_match_id_col: str,
) -> pd.DataFrame:
    schedule_union = union_sql(
        SCHEDULE_PREFIX,
        years,
        f"SELECT {sched_match_id_col} AS match_id, start_time, home_team, away_team",
    )

    where = ["(home_team IN UNNEST(@teams) OR away_team IN UNNEST(@teams))"]
    params = [bigquery.ArrayQueryParameter("teams", "STRING", list(teams))]

    if home_away:
        clauses = []
        if "Home" in home_away:
            clauses.append("(home_team IN UNNEST(@teams))")
        if "Away" in home_away:
            clauses.append("(away_team IN UNNEST(@teams))")
        if clauses:
            where.append("(" + " OR ".join(clauses) + ")")

    sql = f"""
    WITH s AS (
      {schedule_union}
    )
    SELECT match_id, start_time, home_team, away_team
    FROM s
    WHERE {" AND ".join(where)}
    ORDER BY start_time DESC
    """

    df = run_query(sql, params)

    if "start_time" in df.columns:
        df["start_time"] = pd.to_datetime(df["start_time"], errors="coerce", utc=True)

    df["match_id"] = pd.to_numeric(df["match_id"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["match_id"])
    df["match_id"] = df["match_id"].astype("int64")

    return df


@st.cache_data(ttl=900)
def load_event_types(
    years: Tuple[int, ...],
    teams: Tuple[str, ...],
    match_ids: Tuple[int, ...],
    events_match_id_col: str,
) -> List[str]:
    events_union = union_sql(
        EVENTS_PREFIX,
        years,
        f"SELECT {events_match_id_col} AS match_id, team, type",
    )

    where = ["type IS NOT NULL", "team IN UNNEST(@teams)"]
    params = [bigquery.ArrayQueryParameter("teams", "STRING", list(teams))]

    if match_ids:
        where.append("match_id IN UNNEST(@match_ids)")
        params.append(bigquery.ArrayQueryParameter("match_ids", "INT64", [int(x) for x in match_ids]))

    sql = f"""
    WITH e AS ({events_union})
    SELECT DISTINCT type
    FROM e
    WHERE {" AND ".join(where)}
    ORDER BY type
    """

    df = run_query(sql, params)
    return df["type"].dropna().astype(str).tolist()


@st.cache_data(ttl=900)
def load_outcomes(
    years: Tuple[int, ...],
    teams: Tuple[str, ...],
    match_ids: Tuple[int, ...],
    event_types: Tuple[str, ...],
    events_match_id_col: str,
) -> List[str]:
    events_union = union_sql(
        EVENTS_PREFIX,
        years,
        f"SELECT {events_match_id_col} AS match_id, team, type, outcome_type",
    )

    where = ["outcome_type IS NOT NULL", "team IN UNNEST(@teams)"]
    params = [bigquery.ArrayQueryParameter("teams", "STRING", list(teams))]

    if match_ids:
        where.append("match_id IN UNNEST(@match_ids)")
        params.append(bigquery.ArrayQueryParameter("match_ids", "INT64", [int(x) for x in match_ids]))

    if event_types:
        where.append("type IN UNNEST(@types)")
        params.append(bigquery.ArrayQueryParameter("types", "STRING", list(event_types)))

    sql = f"""
    WITH e AS ({events_union})
    SELECT DISTINCT outcome_type
    FROM e
    WHERE {" AND ".join(where)}
    ORDER BY outcome_type
    """

    df = run_query(sql, params)
    return df["outcome_type"].dropna().astype(str).tolist()


@st.cache_data(ttl=900)
def load_players(
    years: Tuple[int, ...],
    teams: Tuple[str, ...],
    match_ids: Tuple[int, ...],
    event_types: Tuple[str, ...],
    events_match_id_col: str,
) -> pd.DataFrame:
    events_union = union_sql(
        EVENTS_PREFIX,
        years,
        f"""
        SELECT
          {events_match_id_col} AS match_id,
          team,
          type,
          CAST(player_id AS INT64) AS player_id,
          CAST(player AS STRING) AS player_name
        """,
    )

    where = ["player_id IS NOT NULL", "team IN UNNEST(@teams)"]
    params = [bigquery.ArrayQueryParameter("teams", "STRING", list(teams))]

    if match_ids:
        where.append("match_id IN UNNEST(@match_ids)")
        params.append(bigquery.ArrayQueryParameter("match_ids", "INT64", [int(x) for x in match_ids]))

    if event_types:
        where.append("type IN UNNEST(@types)")
        params.append(bigquery.ArrayQueryParameter("types", "STRING", list(event_types)))

    sql = f"""
    WITH e AS ({events_union})
    SELECT
      player_id,
      ANY_VALUE(player_name) AS player_name
    FROM e
    WHERE {" AND ".join(where)}
    GROUP BY player_id
    ORDER BY player_name, player_id
    """

    df = run_query(sql, params)
    if df.empty:
        return df

    df["player_id"] = pd.to_numeric(df["player_id"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["player_id"]).copy()
    df["player_id"] = df["player_id"].astype("int64")
    df["player_name"] = df["player_name"].fillna("").astype(str).str.strip()

    return df


@st.cache_data(ttl=300)
def load_events_filtered(
    years: Tuple[int, ...],
    teams: Tuple[str, ...],
    match_ids: Tuple[int, ...],
    minute_range: Tuple[int, int],
    event_types: Tuple[str, ...],
    outcomes: Tuple[str, ...],
    player_ids: Tuple[int, ...],
    limit_rows: int,
    events_match_id_col: str,
) -> pd.DataFrame:
    events_union = union_sql(
        EVENTS_PREFIX,
        years,
        f"""
        SELECT
          {events_match_id_col} AS match_id,
          expanded_minute,
          type,
          outcome_type,
          team,
          CAST(player_id AS INT64) AS player_id,
          CAST(player AS STRING) AS player,
          x, y, end_x, end_y
        """,
    )

    where = [
        "team IN UNNEST(@teams)",
        "expanded_minute BETWEEN @m0 AND @m1",
    ]

    params: list = [
        bigquery.ArrayQueryParameter("teams", "STRING", list(teams)),
        bigquery.ScalarQueryParameter("m0", "INT64", int(minute_range[0])),
        bigquery.ScalarQueryParameter("m1", "INT64", int(minute_range[1])),
        bigquery.ScalarQueryParameter("lim", "INT64", int(limit_rows)),
    ]

    if match_ids:
        where.append("match_id IN UNNEST(@match_ids)")
        params.append(bigquery.ArrayQueryParameter("match_ids", "INT64", [int(x) for x in match_ids]))

    if event_types:
        where.append("type IN UNNEST(@types)")
        params.append(bigquery.ArrayQueryParameter("types", "STRING", list(event_types)))

    if outcomes:
        where.append("outcome_type IN UNNEST(@outs)")
        params.append(bigquery.ArrayQueryParameter("outs", "STRING", list(outcomes)))

    if player_ids:
        where.append("player_id IN UNNEST(@pids)")
        params.append(bigquery.ArrayQueryParameter("pids", "INT64", [int(x) for x in player_ids]))

    sql = f"""
    WITH e AS ({events_union})
    SELECT *
    FROM e
    WHERE {" AND ".join(where)}
    LIMIT @lim
    """

    return run_query(sql, params)


# =========================================
# PAGE
# =========================================

st.set_page_config(page_title="Eventos", layout="wide")
st.title("Eventos • Análise Interativa")

globals_ = render_sidebar_globals()
years: List[int] = globals_.get("years", [])
teams: List[str] = globals_.get("teams", [])

if not years or not teams:
    st.warning("Selecione pelo menos uma temporada e um time na sidebar.")
    st.stop()

years_t = tuple(sorted(set(int(y) for y in years)))
teams_t = tuple(sorted(set(str(t) for t in teams)))

try:
    SCHED_MATCH_ID_COL = detect_match_id_col(SCHEDULE_PREFIX, years_t[0])
    EVENTS_MATCH_ID_COL = detect_match_id_col(EVENTS_PREFIX, years_t[0])
except Exception as e:
    st.error(str(e))
    st.stop()

st.subheader("Filtros da página")

c1, c2, c3, c4 = st.columns([1.2, 1.2, 1.2, 1.0])

with c1:
    minute_range = st.slider("Minutos", 0, 120, (0, 120))

with c2:
    home_away = st.multiselect("Home/Away", ["Home", "Away"], default=["Home", "Away"])

with c3:
    match_mode = st.radio("Partidas", ["Todas", "Escolher (multi)"], horizontal=True)

with c4:
    limit_rows = st.number_input("Limite de eventos", 10_000, 500_000, 200_000, 10_000)

df_matches = load_matches(years_t, teams_t, tuple(home_away), SCHED_MATCH_ID_COL)

if df_matches.empty:
    st.warning("Nenhuma partida encontrada com esses filtros globais + Home/Away.")
    st.stop()

opponents_all = infer_opponents(df_matches, teams_t)
opponents = st.multiselect("Time adversário (opcional)", opponents_all, default=[])

if opponents:
    teams_set = set(teams_t)
    opp_set = set(opponents)

    def ok(r: pd.Series) -> bool:
        ht, at = r["home_team"], r["away_team"]
        return ((ht in teams_set and at in opp_set) or (at in teams_set and ht in opp_set))

    df_matches_eff = df_matches[df_matches.apply(ok, axis=1)].copy()
else:
    df_matches_eff = df_matches.copy()

df_matches_eff["label"] = df_matches_eff.apply(match_label, axis=1)
label_map = dict(zip(df_matches_eff["match_id"].astype("int64"), df_matches_eff["label"]))

match_universe = df_matches_eff["match_id"].dropna().astype("int64").tolist()
match_ids_selected: List[int] = []

if match_mode.startswith("Escolher"):
    match_ids_selected = st.multiselect(
        "Selecione match_id(s)",
        options=match_universe,
        default=match_universe[:1] if match_universe else [],
        format_func=lambda mid: label_map.get(int(mid), str(mid)),
    )

match_ids_effective = tuple(match_ids_selected) if match_ids_selected else tuple(match_universe)

event_types_all = load_event_types(years_t, teams_t, match_ids_effective, EVENTS_MATCH_ID_COL)
default_types = ["Pass"] if "Pass" in event_types_all else (event_types_all[:1] if event_types_all else [])
event_types = st.multiselect("Tipo(s) de evento", event_types_all, default=default_types)

outcomes_all = load_outcomes(years_t, teams_t, match_ids_effective, tuple(event_types), EVENTS_MATCH_ID_COL)
outcomes = st.multiselect("Outcome (opcional)", outcomes_all, default=[])

df_players = load_players(years_t, teams_t, match_ids_effective, tuple(event_types), EVENTS_MATCH_ID_COL)
player_options = [
    f"{r.player_name} ({r.player_id})" if r.player_name else f"({r.player_id})"
    for r in df_players.itertuples(index=False)
]
selected_players = st.multiselect("Jogador(es) (opcional)", options=player_options, default=[])

player_ids_sel: List[int] = []
for lab in selected_players:
    try:
        player_ids_sel.append(int(lab.split("(")[-1].split(")")[0]))
    except Exception:
        pass

df_events = load_events_filtered(
    years=years_t,
    teams=teams_t,
    match_ids=match_ids_effective,
    minute_range=(int(minute_range[0]), int(minute_range[1])),
    event_types=tuple(event_types),
    outcomes=tuple(outcomes),
    player_ids=tuple(player_ids_sel),
    limit_rows=int(limit_rows),
    events_match_id_col=EVENTS_MATCH_ID_COL,
)

st.divider()
st.subheader("Resultados")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Temporadas", ", ".join(map(str, years_t)))
k2.metric("Times", ", ".join(teams_t))
k3.metric("Partidas (universo)", str(len(match_ids_effective)))
k4.metric("Eventos retornados", f"{len(df_events):,}".replace(",", "."))

if df_events.empty:
    st.warning("Nenhum evento retornado. Ajuste filtros.")
    st.stop()

cols_pref = ["match_id", "expanded_minute", "type", "outcome_type", "team", "player_id", "player", "x", "y", "end_x", "end_y"]
cols_show = [c for c in cols_pref if c in df_events.columns] + [c for c in df_events.columns if c not in cols_pref]
st.dataframe(df_events[cols_show].head(500), use_container_width=True)

st.divider()
st.subheader("Mapa de eventos (campo)")

g1, g2, g3 = st.columns([1.2, 1.2, 1.0])

with g1:
    draw_arrows = st.checkbox(
        "Desenhar Setas (Ponto Final do Evento)",
        value=("end_x" in df_events.columns and "end_y" in df_events.columns),
    )

with g2:
    color_by_outcome = st.checkbox(
        "Colorir por Sucesso do Evento",
        value=("outcome_type" in df_events.columns),
    )

with g3:
    sample_n = st.number_input("Amostra p/ plot", min_value=200, max_value=20000, value=3000, step=200)

with st.expander("Estilo do mapa (campo)", expanded=False):
    c1s, c2s, c3s = st.columns(3)

    with c1s:
        pitch_line_color = st.color_picker("Cor das linhas do campo", "#9aa0a6")
        pitch_line_width = st.slider("Espessura das linhas", 0.5, 3.0, 1.15, 0.05)

    with c2s:
        text_color = st.color_picker("Cor do texto (sentido do ataque)", "#c9cdd1")
        arrow_color = st.color_picker("Cor da seta (sentido do ataque)", "#c9cdd1")
        legend_text_color = st.color_picker("Cor do texto da legenda", "#c9cdd1")

    with c3s:
        transparent_bg = st.checkbox("Fundo transparente", value=True)
        if transparent_bg:
            fig_bg = "none"
            ax_bg = "none"
        else:
            fig_bg = st.color_picker("Cor de fundo (figura)", "#0e1117")
            ax_bg = st.color_picker("Cor de fundo (eixos)", "#0e1117")

    st.divider()

    c4s, c5s = st.columns(2)

    with c4s:
        event_color = st.color_picker("Cor dos eventos (geral)", "#c9cdd1")
        event_alpha = st.slider("Opacidade dos eventos", 0.1, 1.0, 0.88, 0.01)
        event_size = st.slider("Tamanho dos pontos", 5, 80, 26, 1)

    with c5s:
        ok_color = st.color_picker("Cor Successful", "#7CFC98")
        bad_color = st.color_picker("Cor Unsuccessful", "#FF6B6B")
        arrow_alpha = st.slider("Opacidade das setas", 0.1, 1.0, 0.65, 0.01)
        arrow_width = st.slider("Largura das setas", 0.0005, 0.01, 0.0022, 0.0001)

style = {
    "pitch_line_color": pitch_line_color,
    "pitch_line_width": float(pitch_line_width),
    "text_color": text_color,
    "arrow_color": arrow_color,
    "legend_text_color": legend_text_color,
    "fig_bg": fig_bg,
    "ax_bg": ax_bg,
    "event_color": event_color,
    "event_alpha": float(event_alpha),
    "event_size": int(event_size),
    "ok_color": ok_color,
    "bad_color": bad_color,
    "arrow_alpha": float(arrow_alpha),
    "arrow_width": float(arrow_width),
}

needed = {"x", "y"}
if not needed.issubset(df_events.columns):
    st.warning("Este dataset não tem colunas x/y para desenhar o mapa.")
    st.stop()

plot_df = df_events.copy()

for c in ["x", "y", "end_x", "end_y"]:
    if c in plot_df.columns:
        plot_df[c] = pd.to_numeric(plot_df[c], errors="coerce")

plot_df = plot_df.dropna(subset=["x", "y"])

if len(plot_df) > int(sample_n):
    plot_df = plot_df.sample(int(sample_n), random_state=42)

# Converte coords do dataset (0..100) para o campo real (105x68)
plot_df["x_plot"] = _scale_series_to_0_100(plot_df["x"]) * (PITCH_LENGTH / 100.0)
plot_df["y_plot"] = _scale_series_to_0_100(plot_df["y"]) * (PITCH_WIDTH / 100.0)

if "end_x" in plot_df.columns and "end_y" in plot_df.columns:
    plot_df["end_x_plot"] = _scale_series_to_0_100(plot_df["end_x"]) * (PITCH_LENGTH / 100.0)
    plot_df["end_y_plot"] = _scale_series_to_0_100(plot_df["end_y"]) * (PITCH_WIDTH / 100.0)

plot_df = apply_attack_orientation(plot_df, focus_teams=teams_t)

fig_pitch = plot_events_pitch(
    df_events_plot=plot_df,
    draw_arrows=bool(draw_arrows),
    color_by_outcome=bool(color_by_outcome),
    style=style,
)

png_pitch = fig_to_png_bytes(fig_pitch, style, bg_key="fig_bg")

st.pyplot(fig_pitch, clear_figure=False)

fname_pitch = f"event_map_{'_'.join(map(str, years_t))}_{'_'.join(teams_t)}.png".replace(" ", "_")
st.download_button(
    label="⬇️ Baixar imagem do campo (PNG)",
    data=png_pitch,
    file_name=fname_pitch,
    mime="image/png",
)
