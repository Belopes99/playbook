import streamlit as st

def load_css():
    st.markdown("""
        <style>
        /* Hide Hamburger Menu and Footer */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Remove top padding */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
        }
        
        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: #161b22;
        }
        
        /* Custom Card for Metrics */
        div[data-testid="stMetric"] {
            background-color: #21262d;
            border: 1px solid #30363d;
            padding: 10px;
            border-radius: 8px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        div[data-testid="stMetric"] > div {
            color: #c9d1d9;
        }
        div[data-testid="stMetric"] label {
            color: #8b949e;
        }
        
        /* Primary Button Upgrade */
        div.stButton > button:first-child {
            background-color: #238636;
            color: white;
            border: none;
            border-radius: 6px;
            font-weight: 600;
        }
        div.stButton > button:first-child:hover {
            background-color: #2ea043;
        }
        
        /* Expander Styling */
        .streamlit-expanderHeader {
            background-color: #0d1117;
            border-radius: 6px;
        }
        
        /* DataFrame Styling */
        div[data-testid="stDataFrame"] {
            border: 1px solid #30363d;
            border-radius: 6px;
        }

        /* Navigation Card Styling */
        .nav-card {
            background-color: #21262d;
            border: 1px solid #30363d;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            text-decoration: none;
            color: #c9d1d9;
            transition: transform 0.2s, background-color 0.2s;
            display: block;
        }
        .nav-card:hover {
            transform: translateY(-2px);
            background-color: #30363d;
            border-color: #8b949e;
            text-decoration: none;
        }
        .nav-card h3 {
            margin-top: 0;
            color: #58a6ff;
        }
        .nav-card p {
            color: #8b949e;
            font-size: 0.9em;
        }
        </style>
    """, unsafe_allow_html=True)
