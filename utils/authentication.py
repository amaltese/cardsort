import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def _attempt_researcher_login():
    expected_password = os.getenv("RESEARCHER_PASSWORD", "admin")
    entered_password = st.session_state.get("researcher_password", "")
    if entered_password == expected_password:
        st.session_state["authenticated"] = True
        st.session_state.pop("researcher_login_error", None)
    else:
        st.session_state["researcher_login_error"] = "Invalid password."


def check_researcher_auth() -> bool:
    if st.session_state.get("authenticated", False):
        return True
        
    st.title("Researcher Login")
    st.text_input(
        "Enter Researcher Password",
        type="password",
        key="researcher_password",
        on_change=_attempt_researcher_login,
        help="Press Enter to log in, or use the Login button.",
    )
    st.button("Login", type="primary", on_click=_attempt_researcher_login)
    if st.session_state.get("researcher_login_error"):
        st.error(st.session_state["researcher_login_error"])
    return False
