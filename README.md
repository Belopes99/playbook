# Prodigy.co Scouting Platform ⚽📊

Bem-vindo à plataforma de inteligência de dados da Prodigy.co. Este projeto utiliza Streamlit para fornecer visualizações avançadas de eventos de futebol, mapas de calor, e análises táticas usando dados detalhados.

## 🚀 Funcionalidades

*   **Mapa de Eventos Interativo:** Visualize passes, chutes e ações defensivas em um campo 2D interativo (Plotly).
*   **Filtros Granulares:** Filtre por Temporada, Time, Jogador, Tipo de Evento e Qualificadores (ex: "BigChance").
*   **Design Premium:** Interface otimizada com tema escuro e elementos visuais de alta fidelidade.
*   **Personalização:** Controle total sobre cores e formas dos eventos.

## 🛠️ Configuração Local

### Pré-requisitos
*   Python 3.10+
*   Pip

### Instalação

1.  Clone o repositório:
    ```bash
    git clone https://github.com/Belopes99/prodigy.co-scouting-plataform.git
    cd prodigy.co-scouting-plataform
    ```

2.  Crie um ambiente virtual (recomendado):
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Linux/Mac
    # ou
    .\.venv\Scripts\activate   # Windows
    ```

3.  Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```

## 🔐 Configuração de Credenciais

Este projeto utiliza o Google BigQuery. Para rodar, você precisará configurar as credenciais.

1.  Crie o arquivo `.streamlit/secrets.toml`.
2.  Adicione suas credenciais do GCP no seguinte formato:

```toml
[gcp_service_account]
type = "service_account"
project_id = "seu-project-id"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----..."
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

> **Nota:** As credenciais nunca devem ser commitadas no Git. Certifique-se de que `.streamlit/secrets.toml` está no seu `.gitignore`.

## ▶️ Executando

```bash
streamlit run app.py
```

## 📄 Estrutura

*   `app.py`: Ponto de entrada da aplicação.
*   `pages/`: Páginas adicionais (Eventos, Jogadores, etc).
*   `src/`: Módulos auxiliares (Plotagem, CSS, Conexão BQ).
