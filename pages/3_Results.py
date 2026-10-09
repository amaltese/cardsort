import streamlit as st
from database.db import init_db
from utils.authentication import check_researcher_auth

st.set_page_config(page_title="Study Results", layout="wide")
init_db()

if check_researcher_auth():
    st.title("Participant Results & Submissions")
    st.info("Stage 2 Results viewer ready. Data collections active in database layer.")