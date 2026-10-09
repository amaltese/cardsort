import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import json
import streamlit as st
from database.db import init_db
from services.study_service import StudyService
from services.participant_service import ParticipantService
from components.participant_header import render_participant_header
from components.card_sort import render_card_sort_workspace, pluralize_label

st.set_page_config(page_title="Participant Workspace", layout="wide")
init_db()

query_params = st.query_params
study_token = query_params.get("st", None)

study_service = StudyService()
participant_service = ParticipantService()

def clear_participant_state():
    for key in ["session_token", "categories", "placements", "completed_code"]:
        if key in st.session_state:
            del st.session_state[key]

if not study_token:
    st.title("Participant Portal")
    study_token = st.text_input("Enter your Study Token to begin:")

if study_token:
    study = study_service.get_study_by_token(study_token)
    if not study:
        st.error("Invalid study token. Please check your participant link.")
    else:
        # Initialize fresh session if not present
        if "session_token" not in st.session_state:
            sess = participant_service.create_fresh_session(study.study_id)
            st.session_state["session_token"] = sess["session_token"]

        sess_token = st.session_state["session_token"]
        session_data = participant_service.get_session(sess_token)

        # Completion View
        if session_data and session_data.get("status") == "completed":
            st.balloons()
            st.success("🎉 **Card Sort Submitted Successfully!**")
            
            code = session_data.get("completion_code", "N/A")
            st.markdown(
                f"""
                <div style="background-color: #F0FDF4; border: 2px solid #22C55E; border-radius: 12px; padding: 24px; text-align: center; margin: 20px 0;">
                    <h3 style="color: #15803D; margin-bottom: 8px;">Your Verification Code</h3>
                    <div style="font-size: 32px; font-weight: 800; letter-spacing: 3px; color: #0E7490; font-family: monospace;">{code}</div>
                    <p style="color: #374151; margin-top: 12px; font-size: 14px;">
                        Please copy this code and provide it to your research administrator to confirm your completion.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

            if session_data.get("snapshot_json"):
                snapshot = json.loads(session_data["snapshot_json"])
                st.subheader("Summary of Submitted Organization")
                for cat, items in snapshot.get("placements", {}).items():
                    with st.expander(f"📁 {cat} ({len(items)} items)", expanded=True):
                        for item in items:
                            st.markdown(f"• {item}")
                            
                if snapshot.get("reflection"):
                    st.info(f"**Your Reflection:** {snapshot['reflection']}")

            st.markdown("---")
            if st.button("🔄 Start New Submission (Testing)", type="secondary"):
                clear_participant_state()
                st.rerun()

        else:
            # Active Sort View
            render_participant_header(study)
            cards = study_service.card_repo.get_cards_for_study(study.study_id, active_only=True)
            
            if not cards:
                st.warning("This study currently has no cards configured.")
            else:
                render_card_sort_workspace(study, cards)
                
                st.markdown("---")
                st.subheader("Submit Your Card Organization")

                unassigned_ids = st.session_state.get("placements", {}).get("Unassigned", [])
                plural_lbl = pluralize_label(study.item_label)

                reflection_q = study.reflection_questions[0] if study.reflection_questions else "Please briefly explain your sorting logic:"
                reflection_input = st.text_area(f"💬 {reflection_q}", placeholder="Explain why you grouped these items together...", height=100)

                if study.require_all_placed and len(unassigned_ids) > 0:
                    st.warning(f"⚠️ Please move the remaining **{len(unassigned_ids)} unassigned {plural_lbl.lower()}** into categories before submitting.")
                    st.button("Submit Card Sort", disabled=True, use_container_width=True)
                else:
                    if st.button("🚀 Submit Final Card Sort", type="primary", use_container_width=True):
                        code = participant_service.submit_sort(
                            session_token=st.session_state["session_token"],
                            study=study,
                            cards=cards,
                            placements=st.session_state["placements"],
                            reflection_text=reflection_input
                        )
                        st.session_state["completed_code"] = code
                        st.rerun()
