import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from database.db import init_db
from services.study_service import StudyService
from services.export_service import ExportService
from services.analysis_service import AnalysisService
from utils.authentication import check_researcher_auth

st.set_page_config(page_title="Study Results & Analysis", layout="wide")
init_db()

if check_researcher_auth():
    st.title("Participant Results & Card Sort Analytics")
    
    study_service = StudyService()
    export_service = ExportService()
    analysis_service = AnalysisService()

    studies = study_service.get_all_studies()
    if not studies:
        st.info("No studies have been created yet.")
    else:
        # Study Selector Dropdown
        study_options = {f"{std.title} ({std.condition})": std for std in studies}
        selected_label = st.selectbox("Select Study to Analyze:", list(study_options.keys()))
        selected_study = study_options[selected_label]

        st.markdown("---")
        
        # Fetch responses and card list
        completed_sessions = export_service.get_completed_sessions_for_study(selected_study.study_id)
        cards = study_service.card_repo.get_cards_for_study(selected_study.study_id, active_only=True)
        card_titles = [c.title for c in cards]

        # Overview Metrics Bar
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Completed Submissions", len(completed_sessions))
        with col2:
            st.metric("Study Condition", selected_study.condition)
        with col3:
            st.metric("Total Items Configured", len(card_titles))

        st.markdown("---")

        if not completed_sessions:
            st.warning("⚠️ No submitted responses found for this study yet.")
            st.info(f"Share this link with participants: `/2_Participant?st={selected_study.token}`")
        else:
            # Multi-Tab Analytics Dashboard
            tab1, tab2, tab3 = st.tabs([
                "📊 Card Agreement & Co-Occurrence", 
                "📋 Category Frequency Matrix", 
                "🎓 Individual Submissions"
            ])

            # Tab 1: Co-Occurrence Matrix & Consensus Breakdown
            with tab1:
                st.subheader("Card Consensus & Agreement Analysis")
                
                df_agreement = analysis_service.get_card_agreement_summary(selected_study.study_id, card_titles)
                st.dataframe(
                    df_agreement,
                    use_container_width=True,
                    column_config={
                        "Agreement %": st.column_config.ProgressColumn(
                            "Agreement %",
                            help="Percentage of participants who placed this card in its primary category",
                            format="%.1f%%",
                            min_value=0,
                            max_value=100
                        )
                    }
                )

                st.markdown("---")
                st.subheader("Pairwise Co-Occurrence Heatmap (%)")
                st.caption("Shows how frequently pairs of cards were grouped into the same category across all teachers.")

                df_co = analysis_service.get_co_occurrence_matrix(selected_study.study_id, card_titles)
                if not df_co.empty:
                    styled_co = df_co.style.background_gradient(cmap="Blues", axis=None).format("{:.0f}%")
                    st.dataframe(styled_co, use_container_width=True)

            # Tab 2: Card-by-Category Cross-Tabulation
            with tab2:
                st.subheader("Card Assignment Breakdown by Category (%)")
                st.caption("Percentage of total participants assigning each card to a given category name.")

                df_freq = analysis_service.get_card_category_frequency(selected_study.study_id, card_titles)
                if not df_freq.empty:
                    styled_freq = df_freq.style.background_gradient(cmap="Greens", axis=None).format("{:.1f}%")
                    st.dataframe(styled_freq, use_container_width=True)
                else:
                    st.info("No category assignments available yet.")

            # Tab 3: Raw Individual Submissions & Exports
            with tab3:
                csv_data = export_service.export_results_csv(selected_study.study_id)
                st.download_button(
                    label="📥 Export All Raw Submissions to CSV",
                    data=csv_data,
                    file_name=f"results_{selected_study.study_id}.csv",
                    mime="text/csv",
                    type="primary"
                )

                st.markdown("### Individual Participant Responses")

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
                                    for card_item in card_list:
                                        st.markdown(f"• {card_item}")
