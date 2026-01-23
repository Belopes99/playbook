from typing import Optional, Tuple

def get_total_matches_query(project_id: str, dataset_id: str) -> str:
    """
    Retorna query para contar total de partidas únicas.
    """
    # Assumindo que a tabela de eventos é eventos_{ano} e precisamos agregar.
    # Por enquanto, vamos pegar apenas de 2025 ou fazer um UNION se tiver mais anos.
    # Para simplificar, vamos contar de 2025.
    return f"""
        SELECT COUNT(DISTINCT match_id) as total
        FROM `{project_id}.{dataset_id}.events_bra_2025`
    """

def get_total_events_query(project_id: str, dataset_id: str) -> str:
    """
    Retorna query para contar total de eventos.
    """
    return f"""
        SELECT COUNT(*) as total
        FROM `{project_id}.{dataset_id}.events_bra_2025`
    """

def get_recent_matches_query(project_id: str, dataset_id: str, limit: int = 5) -> str:
    """
    Retorna query para as últimas partidas processadas.
    """
    return f"""
        SELECT 
            DISTINCT match_id,
            match_date,
            home_team,
            away_team,
            home_score,
            away_score
        FROM `{project_id}.{dataset_id}.events_bra_2025`
        ORDER BY match_date DESC
        LIMIT {limit}
    """
