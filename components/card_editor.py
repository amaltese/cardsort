import streamlit as st
import pandas as pd
from services.study_service import StudyService
from utils.validation import validate_card_csv

SAMPLE_CSV_TEMPLATE = """title,description,example,notes
Differentiated Instruction,Adapting teaching strategies to varied student learning needs,Grouping students by readiness,Pedagogy
Formative Assessment,Ongoing check for understanding during instruction,Exit tickets and quick polls,Assessment
Classroom Management,Establishing proactive routines and positive behavioral support,Proactive rule setting,Operational
"""

def render_card_editor(study_id: str, study_service: StudyService):
    st.subheader("Manage Study Cards / Items")
    
    if "card_import_success_msg" in st.session_state:
        st.success(st.session_state.pop("card_import_success_msg"))
        st.toast("Cards imported successfully!", icon="✅")

    # Add Single Card
    with st.expander("Add Individual Card", expanded=False):
        with st.form("add_card_form"):
            title = st.text_input("Card Title*")
            desc = st.text_area("Description")
            example = st.text_input("Example (Optional)")
            notes = st.text_input("Researcher Notes (Internal)")
            if st.form_submit_button("Add Card"):
                if title.strip():
                    study_service.add_card_to_study(study_id, title, desc, example, notes)
                    st.success(f"Added card: '{title}'")
                    st.rerun()
                else:
                    st.error("Card Title is required.")

    # CSV Batch Import with Template Download
    with st.expander("Batch Import Cards via CSV", expanded=True):
        st.markdown("Download our sample template, edit it with your own data in Excel or Google Sheets, and re-upload it below:")
        
        st.download_button(
            label="📥 Download Sample CSV Template",
            data=SAMPLE_CSV_TEMPLATE,
            file_name="card_sort_sample_template.csv",
            mime="text/csv",
            help="Download a formatted CSV template you can fill in with your study items."
        )
        
        st.markdown("---")
        uploaded_file = st.file_uploader("Upload Your CSV File", type=["csv"], key="csv_file_uploader")
        
        if uploaded_file:
            bytes_data = uploaded_file.getvalue()
            valid, msg, parsed_cards = validate_card_csv(bytes_data)
            
            if not valid:
                st.error(f"❌ {msg}")
            else:
                st.success(f"✅ {msg}")
                st.markdown("**Preview of items to import:**")
                st.dataframe(pd.DataFrame(parsed_cards), use_container_width=True)
                
                if st.button("Confirm & Import All Cards", type="primary"):
                    ok, import_msg = study_service.import_cards_csv(study_id, bytes_data)
                    if ok:
                        st.session_state["card_import_success_msg"] = import_msg
                        st.rerun()
                    else:
                        st.error(import_msg)

    # View & Export Existing Cards
    cards = study_service.card_repo.get_cards_for_study(study_id, active_only=False)
    st.write(f"**Total Cards Configured:** {len(cards)}")
    
    if cards:
        csv_data = study_service.export_cards_csv(study_id)
        st.download_button("Export Cards to CSV", data=csv_data, file_name=f"study_{study_id}_cards.csv", mime="text/csv")
        
        for c in cards:
            cols = st.columns([4, 1])
            with cols[0]:
                st.markdown(f"**{c.display_order}. {c.title}**")
                if c.description:
                    st.caption(c.description)
            with cols[1]:
                if st.button("Delete", key=f"del_crd_{c.card_id}"):
                    study_service.card_repo.delete_card(c.card_id)
                    st.rerun()
