import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from database.db import init_db
from services.study_service import StudyService
from utils.authentication import check_researcher_auth
from components.study_builder import render_study_builder
from components.card_editor import render_card_editor
from components.category_editor import render_category_editor

st.set_page_config(page_title="Researcher Portal", layout="wide")
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
                st.header(f"Editing: {selected_study.title}")
                
                # Display Reusable Shareable Link
                st.markdown("##### 🔗 Shareable Participant Link (Unlimited Responses)")
                st.info(f"Send this single link to all participants:  \n`.../2_Participant?st={selected_study.token}`")
                
                t1, t2 = st.tabs(["Cards / Items", "Starting Categories"])
                with t1:
                    render_card_editor(selected_study.study_id, study_service)
                with t2:
                    render_category_editor(selected_study.study_id, study_service)
