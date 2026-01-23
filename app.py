import streamlit as st
from src.ui_filters import render_sidebar_globals

st.set_page_config(page_title="Playbook", layout="wide")
st.title("Playbook • Dashboard")

globals_ = render_sidebar_globals()

st.write("Selecione uma página no menu à esquerda.")
st.write("Globais:", globals_)
