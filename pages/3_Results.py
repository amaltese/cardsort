import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from database.db import init_db
from services.study_service import StudyService
from services.export_service import ExportService
from utils.authentication import check_researcher_auth

st.set_page_config(page_title="Study Results", layout="wide")
init_db()

if check_researcher_auth():
    st.title("Participant Results & Submissions")
    
    study_service = StudyService()
    export_service = ExportService()

    studies = study_service.get_all_studies()
    if not studies:
        st.info("No studies have been created yet.")
    else:
        # Study Selector Dropdown
        study_options = {f"{std.title} ({std.condition})": std for std in studies}
        selected_label = st.selectbox("Select Study to View Results:", list(study_options.keys()))
        selected_study = study_options[selected_label]

        st.markdown("---")
        
        # Fetch completed responses from DB
        completed_sessions = export_service.get_completed_sessions_for_study(selected_study.study_id)

        # Overview Metrics Bar
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Completed Responses", len(completed_sessions))
        with col2:
            st.metric("Study Condition", selected_study.condition)
        with col3:
            st.metric("Item Type", selected_study.item_label)

        st.markdown("---")

        if not completed_sessions:
            st.warning("⚠️ No submitted responses found for this study yet.")
            st.info(f"Share this link with participants: `/2_Participant?st={selected_study.token}`")
        else:
            # Export to CSV Button
            csv_data = export_service.export_results_csv(selected_study.study_id)
            st.download_button(
                label="📥 Export All Submissions to CSV",
                data=csv_data,
                file_name=f"results_{selected_study.study_id}.csv",
                mime="text/csv",
                type="primary"
            )

            st.markdown("### Individual Participant Submissions")

            # Render each participant response
            for idx, sess in enumerate(completed_sessions):
                code = sess["completion_code"]
                completed_at = sess["completed_at"]
                refl = sess["reflection"]
                placements = sess["placements"]

                with st.expander(f"🎓 Submission #{len(completed_sessions) - idx} — Code: {code} ({completed_at})", expanded=(idx == 0)):
                    if refl:
                        st.info(f"💬 **Teacher Reflection:** {refl}")

                    st.markdown("**Category Assignments:**")
                    
                    if placements:
                        cat_cols = st.columns(min(len(placements), 3))
                        for cat_idx, (cat_name, card_list) in enumerate(placements.items()):
                            col_target = cat_cols[cat_idx % len(cat_cols)]
                            with col_target:
                                st.markdown(f"##### 🏷️ {cat_name} ({len(card_list)})")
                                for card_title in card_list:
                                    st.markdown(f"• {card_title}")
