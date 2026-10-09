import streamlit as st
from services.study_service import StudyService

def render_card_editor(study_id: str, study_service: StudyService):
    st.subheader("Manage Study Cards / Items")
    
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
                    st.success(f"Added card: {title}")
                    st.rerun()
                else:
                    st.error("Card Title is required.")

    # CSV Batch Import
    with st.expander("Batch Import Cards via CSV", expanded=False):
        uploaded_file = st.file_uploader("Upload CSV (Columns: title, description, example, notes)", type=["csv"])
        if uploaded_file and st.button("Process CSV Import"):
            bytes_data = uploaded_file.getvalue()
            ok, msg = study_service.import_cards_csv(study_id, bytes_data)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

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