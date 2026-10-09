import sys
from pathlib import Path

# Explicitly add the app's root folder to Python's module path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from database.db import init_db

st.set_page_config(
    page_title="Card Sorting Research Platform",
    page_icon="🗂️",
    layout="wide"
)

# Initialize SQLite tables on app startup
init_db()

st.title("Virtual Card-Sorting Research Platform")
st.markdown("""
Welcome to the asynchronous virtual card-sorting platform designed for educational and professional research studies.

### Routing Navigation
* **For Researchers**: Access **1_Researcher** in the sidebar menu to build studies, configure cards, and set sort conditions.
* **For Participants**: Open the unique study URL provided by your research team or enter a Study Token in **2_Participant**.
* **For Results**: Access **3_Results** to view incoming participant sorting data.
""")
