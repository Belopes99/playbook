from typing import Optional, Tuple

# YEARS_TO_QUERY = range(2015, 2026)
YEARS_TO_QUERY = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]

def _build_union_query(project_id: str, dataset_id: str, table_prefix: str) -> str:
    """
    Helper to build UNION ALL query for multiple years.
    """
    subqueries = []
    for year in YEARS_TO_QUERY:
        subqueries.append(f"SELECT * FROM `{project_id}.{dataset_id}.{table_prefix}_{year}`")
    return " UNION ALL ".join(subqueries)


def get_total_matches_query(project_id: str, dataset_id: str) -> str:
    """
    Retorna query para contar total de partidas únicas (usando schedule).
    """
    schedule_union = _build_union_query(project_id, dataset_id, "schedule_brasileirao_serie_a")
    return f"""
        WITH all_schedule AS (
            {schedule_union}
        )
        SELECT COUNT(DISTINCT game_id) as total
        FROM all_schedule
        WHERE status IS NOT NULL
    """

def get_total_events_query(project_id: str, dataset_id: str) -> str:
    """
    Retorna query para contar total de eventos.
    """
    events_union = _build_union_query(project_id, dataset_id, "eventos_brasileirao_serie_a")
    return f"""
        WITH all_events AS (
            {events_union}
        )
        SELECT COUNT(*) as total
        FROM all_events
    """

def get_recent_matches_query(project_id: str, dataset_id: str, limit: int = 5) -> str:
    """
    Retorna query para as últimas partidas processadas (usando schedule).
    """
    schedule_union = _build_union_query(project_id, dataset_id, "schedule_brasileirao_serie_a")
    return f"""
        WITH all_schedule AS (
            {schedule_union}
        )
        SELECT 
            game_id as match_id,
            start_time as match_date,
            home_team,
            away_team,
            home_score,
            away_score
        FROM all_schedule
        WHERE status = 2 -- Assuming 2 is 'Finished'
        AND home_score IS NOT NULL
        ORDER BY start_time DESC
        LIMIT {limit}
    """

def get_match_stats_query(project_id: str, dataset_id: str) -> str:
    """
    Retorna estatísticas AGREGADAS por partida e time.
    Isso serve de base para o Ranking (Geral ou Por Temporada).
    """
    schedule_union = _build_union_query(project_id, dataset_id, "schedule_brasileirao_serie_a")
    events_union = _build_union_query(project_id, dataset_id, "eventos_brasileirao_serie_a")
    
    return f"""
    WITH all_schedule AS (
        {schedule_union}
    ),
    all_events AS (
        {events_union}
    ),
    
    match_metadata AS (
        SELECT 
            game_id,
            start_time as match_date,
            home_team,
            away_team,
            home_score,
            away_score
        FROM all_schedule
        WHERE home_score IS NOT NULL 
    ),
    
    match_teams AS (
        SELECT 
            game_id,
            match_date,
            home_team as team,
            home_score as goals_for,
            away_score as goals_against,
            'Mandante' as side
        FROM match_metadata
        
        UNION ALL
        
        SELECT 
            game_id,
            match_date,
            away_team as team,
            away_score as goals_for,
            home_score as goals_against,
            'Visitante' as side
        FROM match_metadata
    ),
    
    event_stats AS (
        SELECT
            game_id as match_id,
            team,
            COUNTIF(type = 'Pass') as total_passes,
            COUNTIF(type = 'Pass' AND outcome_type = 'Successful') as successful_passes,
            COUNTIF(is_shot = true) as total_shots,
            COUNTIF(type = 'Goal') as goals_from_events,
            COUNTIF(type IN ('SavedShot', 'Goal')) as shots_on_target
        FROM all_events
        GROUP BY 1, 2
    )
    
    SELECT
        t.game_id as match_id,
        EXTRACT(YEAR FROM t.match_date) as season,
        t.team,
        t.goals_for,
        t.goals_against,
        IFNULL(e.total_passes, 0) as total_passes,
        IFNULL(e.successful_passes, 0) as successful_passes,
        IFNULL(e.total_shots, 0) as total_shots,
        IFNULL(e.shots_on_target, 0) as shots_on_target
    FROM match_teams t
    LEFT JOIN event_stats e ON t.game_id = e.match_id AND t.team = e.team
    """


def get_players_by_team_query(project_id: str, dataset_id: str, team: str) -> str:
    """
    Lista jogadores que atuaram pelo time.
    """
    events_union = _build_union_query(project_id, dataset_id, "eventos_brasileirao_serie_a")
    return f"""
    WITH all_events AS (
        {events_union}
    )
    SELECT DISTINCT player
    FROM all_events
    WHERE team = '{team}' AND player IS NOT NULL
    ORDER BY player
    """


def get_player_stats_query(project_id: str, dataset_id: str, year: int = 2025) -> str:
    """
    Retorna estatísticas AGREGADAS por jogador para radar charts.
    """
    # NOTE: For individual player stats, we might want to respect the 'year' param IF passed?
    # But currently the UI flow doesn't strongly bind year selection to this, usually it's "Select Player".
    # Assuming we want stats for the SPECIFIC year passed or filtered.
    # If the user selects a player from a team list which is typically "current", maybe we just want 2025?
    # BUT, the prompt implies "Expanding Data".
    # Let's keep it simple: Use dynamic table if year provided, OR use union. 
    # Let's stick to the specific year requested for the RADAR chart context usually
    # BUT we are refactoring globally.
    
    # Actually, for the Radar Chart on Page 3, it's nice to verify if we want career stats or season stats.
    # The signature has `year: int = 2025`. Let's create a specific single-year query if needed, or union.
    # Given the complexity, let's just target the requested year for now to be safe/fast for Radar.
    
    return f"""
    SELECT
        player,
        team,
        COUNT(*) as total_actions,
        COUNTIF(type = 'Pass') as total_passes,
        COUNTIF(type = 'Pass' AND outcome_type = 'Successful') as successful_passes,
        SAFE_DIVIDE(COUNTIF(type = 'Pass' AND outcome_type = 'Successful'), COUNTIF(type = 'Pass')) as pass_accuracy,
        
        COUNTIF(is_shot = true) as total_shots,
        COUNTIF(type = 'Goal') as goals,
        
        COUNTIF(type = 'Ball Recovery') as recoveries,
        COUNTIF(type = 'Interception') as interceptions,
        COUNTIF(type = 'Tackle') as tackles
        
    FROM `{project_id}.{dataset_id}.eventos_brasileirao_serie_a_{year}`
    WHERE player IS NOT NULL
    GROUP BY 1, 2
    """


def get_player_events_query(project_id: str, dataset_id: str, player: str) -> str:
    """
    Retorna eventos brutos de um jogador para plotagem de mapa.
    Aqui idealmente pegariamos todos os anos.
    """
    events_union = _build_union_query(project_id, dataset_id, "eventos_brasileirao_serie_a")
    return f"""
    WITH all_events AS (
        {events_union}
    )
    SELECT 
        game_id as match_id,
        team,
        player,
        type,
        outcome_type,
        x as x_start,
        y as y_start,
        end_x as x_end,
        end_y as y_end,
        period,
        minute,
        second
    FROM all_events
    WHERE player = '{player}'
    """


def get_player_rankings_query(project_id: str, dataset_id: str) -> str:
    """
    Retorna estatísticas de jogadores AGRUPADAS por Temporada (via Join com Schedule).
    Permite ranking 'Por Temporada' ou 'Agregado' (realizado no Pandas).
    UNION ALL YEARS.
    """
    schedule_union = _build_union_query(project_id, dataset_id, "schedule_brasileirao_serie_a")
    events_union = _build_union_query(project_id, dataset_id, "eventos_brasileirao_serie_a")

    return f"""
    WITH all_schedule AS (
        {schedule_union}
    ),
    all_events AS (
        {events_union}
    ),
    
    match_dates AS (
        SELECT game_id, start_time 
        FROM all_schedule
    ),
    
    player_stats AS (
        SELECT
            game_id,
            player,
            team,
            COUNTIF(is_shot = true) as shots,
            COUNTIF(type = 'Goal') as goals,
            COUNTIF(type = 'Pass' AND outcome_type = 'Successful') as successful_passes,
            COUNTIF(type = 'Pass') as total_passes
        FROM all_events
        WHERE player IS NOT NULL
        GROUP BY 1, 2, 3
    )
    
    SELECT
        p.player,
        p.team,
        EXTRACT(YEAR FROM m.start_time) as season,
        COUNT(DISTINCT p.game_id) as matches,
        SUM(p.goals) as goals,
        SUM(p.shots) as shots,
        SUM(p.successful_passes) as successful_passes,
        SUM(p.total_passes) as total_passes
    FROM player_stats p
    JOIN match_dates m ON p.game_id = m.game_id
    GROUP BY 1, 2, 3
    """
