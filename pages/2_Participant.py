import streamlit as st
from database.db import init_db
from services.study_service import StudyService
from services.participant_service import ParticipantService
from components.participant_header import render_participant_header
from components.card_sort import render_card_sort_workspace

st.set_page_config(page_title="Participant Workspace", layout="wide")
init_db()

query_params = st.query_params
study_token = query_params.get("st", None)

study_service = StudyService()
participant_service = ParticipantService()

if not study_token:
    st.title("Participant Portal")
    study_token = st.text_input("Enter your Study Token to begin:")

if study_token:
    study = study_service.get_study_by_token(study_token)
    if not study:
        st.error("Invalid study token. Please check your participant link.")
    else:
        render_participant_header(study)
        cards = study_service.card_repo.get_cards_for_study(study.study_id, active_only=True)
        categories = study_service.cat_repo.get_categories_for_study(study.study_id)
        
        if not cards:
            st.warning("This study currently has no cards configured.")
        else:
            render_card_sort_workspace(study, cards)