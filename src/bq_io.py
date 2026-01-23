from __future__ import annotations

from typing import Optional
import pandas as pd
import streamlit as st
from google.cloud import bigquery


@st.cache_resource(ttl=3600)
def get_bq_client(project: Optional[str] = None) -> bigquery.Client:
    """
    Cria cliente do BigQuery.
    Usa 'gcp_service_account' dos secrets do Streamlit se disponível.
    Caso contrário, tenta credenciais padrão (ambiente).
    """
    # 1. Tenta pegar do dicionário 'gcp_service_account' (Estrutura Recomendada)
    if "gcp_service_account" in st.secrets:
        from google.oauth2 import service_account
        info = st.secrets["gcp_service_account"]
        credentials = service_account.Credentials.from_service_account_info(info)
        project = project or info.get("project_id")
        return bigquery.Client(credentials=credentials, project=project)

    # 2. Tenta pegar da raiz (Caso o usuário tenha colado apenas o conteúdo sem o header)
    elif "private_key" in st.secrets and "project_id" in st.secrets:
        from google.oauth2 import service_account
        # Converter st.secrets (que pode ser um proxy) para dict
        info = dict(st.secrets)
        credentials = service_account.Credentials.from_service_account_info(info)
        project = project or info.get("project_id")
        return bigquery.Client(credentials=credentials, project=project)

    # 3. Fallback: Tenta credenciais do ambiente (local com gcloud auth login)
    try:
        return bigquery.Client(project=project) if project else bigquery.Client()
    except Exception as e:
        st.error(
            "Erro de Autenticação do Google Cloud. "
            "Não foi possível encontrar as credenciais no 'st.secrets' nem no ambiente. "
            "Verifique se você configurou o Secret 'gcp_service_account' no Streamlit Cloud."
        )
        raise e


def load_table(
    client: bigquery.Client,
    table_fqdn: str,
    where: Optional[str] = None,
    limit: Optional[int] = None,
) -> pd.DataFrame:
    """
    Carrega uma tabela do BigQuery em um DataFrame.
    table_fqdn: `projeto.dataset.tabela`
    where: condição SQL sem o 'WHERE' (ex: "season = 2025 AND team = 'Cruzeiro'")
    """
    query = f"SELECT * FROM `{table_fqdn}`"
    if where:
        query += f" WHERE {where}"
    if limit is not None:
        query += f" LIMIT {int(limit)}"

    return client.query(query).to_dataframe()


def load_events(
    client: bigquery.Client,
    project: str,
    dataset: str,
    table_prefix: str,
    year: int,
    where: Optional[str] = None,
    limit: Optional[int] = None,
) -> pd.DataFrame:
    """
    Carrega events de um ano.
    Exemplo de tabela: {table_prefix}_{year} -> events_bra_2025
    """
    table = f"{project}.{dataset}.{table_prefix}_{int(year)}"
    return load_table(client, table, where=where, limit=limit)


def load_schedule(
    client: bigquery.Client,
    project: str,
    dataset: str,
    table_prefix: str,
    year: int,
    where: Optional[str] = None,
    limit: Optional[int] = None,
) -> pd.DataFrame:
    """
    Carrega schedule de um ano.
    """
    table = f"{project}.{dataset}.{table_prefix}_{int(year)}"
    return load_table(client, table, where=where, limit=limit)
