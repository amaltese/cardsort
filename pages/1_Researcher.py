import sys
import os
from urllib.parse import quote
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from dotenv import load_dotenv
from database.db import init_db
from services.study_service import StudyService
from utils.authentication import check_researcher_auth
from components.study_builder import render_study_builder, render_study_settings
from components.card_editor import render_card_editor
from components.category_editor import render_category_editor

st.set_page_config(page_title="Researcher Portal", layout="wide")
load_dotenv()
init_db()

if check_researcher_auth():
    st.title("Researcher Dashboard")
    study_service = StudyService()

    tab1, tab2 = st.columns([1, 2])
    studies = study_service.get_all_studies()

    with tab1:
        st.subheader("Existing Studies")
        if not studies:
            st.info("No studies created yet.")
        for std in studies:
            if st.button(f"📌 {std.title} ({std.condition})", key=f"std_sel_{std.study_id}", use_container_width=True):
                st.session_state["active_study_id"] = std.study_id

        if st.button("➕ Create New Study", use_container_width=True, type="primary"):
            st.session_state["active_study_id"] = "NEW"

    with tab2:
        if "study_created_confirmation" in st.session_state:
            info = st.session_state.pop("study_created_confirmation")
            st.success(f"🎉 **Study '{info['title']}' created successfully!** ({info['condition']} mode)")
            st.toast("Study created successfully!", icon="✅")

        active_id = st.session_state.get("active_study_id", "NEW")
        if active_id == "NEW":
            render_study_builder(study_service)
        else:
            selected_study = study_service.get_study(active_id)
            if selected_study:
                heading, delete_action = st.columns([4, 1])
                with heading:
                    st.header(f"Editing: {selected_study.title}")
                with delete_action:
                    if st.button("🗑️ Delete Study", key=f"delete_top_{selected_study.study_id}", use_container_width=True):
                        st.session_state["delete_study_confirmation"] = selected_study.study_id

                if st.session_state.get("delete_study_confirmation") == selected_study.study_id:
                    st.error("Deleting a study permanently removes its cards, categories, and participant responses.")
                    confirm_delete = st.checkbox(
                        "I understand this cannot be undone.", key=f"confirm_delete_top_{selected_study.study_id}"
                    )
                    if st.button("Permanently Delete This Study", type="primary", disabled=not confirm_delete):
                        study_service.delete_study(selected_study.study_id)
                        st.session_state["active_study_id"] = "NEW"
                        st.session_state.pop("delete_study_confirmation", None)
                        st.rerun()
                
                # A relative link always works in this running app.  Set
                # APP_BASE_URL when deploying so the copyable link works from
                # email and outside the current browser.
                participant_path = f"/Participant?st={quote(selected_study.token)}"
                base_url = os.getenv("APP_BASE_URL", "").rstrip("/")
                participant_url = f"{base_url}{participant_path}" if base_url else participant_path
                st.markdown("##### 🔗 Participant Link")
                st.link_button("Open participant study", participant_url, type="primary")
                st.code(participant_url, language=None)
                if not base_url:
                    st.caption("This works within this app. To email a full link, set APP_BASE_URL in your .env file (for example, https://your-app.example).")
                
                t1, t2, t3 = st.tabs(["Study Settings", "Cards / Items", "Starting Categories"])
                with t1:
                    render_study_settings(selected_study, study_service)
                with t2:
                    render_card_editor(selected_study.study_id, study_service)
                with t3:
                    render_category_editor(selected_study.study_id, study_service)
