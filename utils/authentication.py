import os
import streamlit as st

def check_researcher_auth() -> bool:
    if st.session_state.get("authenticated", False):
        return True
        
    st.title("Researcher Login")
    password_input = st.text_input("Enter Researcher Password", type="password")
    
    expected_password = os.getenv("RESEARCHER_PASSWORD", "admin")
    if st.button("Login"):
        if password_input == expected_password:
            st.session_state["authenticated"] = True
            st.success("Authenticated successfully.")
            st.rerun()
        else:
            st.error("Invalid password.")
    return False