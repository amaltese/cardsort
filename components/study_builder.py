import streamlit as st
from services.study_service import StudyService

def render_study_builder(study_service: StudyService):
    st.subheader("Configure New Research Study")
    
    with st.form("create_study_form"):
        title = st.text_input("Study Title*", placeholder="e.g., K-12 Teacher Competency Mapping")
        description = st.text_area("Study Description", placeholder="Brief description visible to teachers")
        instructions = st.text_area("Participant Instructions", placeholder="Sort these capacities into meaningful categories...")
        researcher_info = st.text_input("Researcher / Institution", placeholder="Department of Education, University X")
        
        col1, col2 = st.columns(2)
        with col1:
            condition = st.selectbox(
                "Study Condition*",
                options=["OPEN", "CLOSED", "HYBRID", "PROPOSED"],
                help="OPEN: Participant creates all categories. CLOSED: Predefined categories only. HYBRID: Predefined + Participant creation. PROPOSED: Evaluate existing model."
            )
        with col2:
            item_label = st.selectbox(
                "Item Label (Domain Specific)",
                options=["Card", "Capacity", "Concept", "Skill", "Strategy", "Idea", "Behavior", "Attribute"],
                index=1
            )

        st.markdown("---")
        st.write("##### Participant Permissions & Constraints")
        c1, c2 = st.columns(2)
        with c1:
            allow_new = st.checkbox("Allow participants to create new categories", value=(condition in ["OPEN", "HYBRID"]))
            allow_rename = st.checkbox("Allow participants to rename categories", value=(condition in ["OPEN", "HYBRID"]))
            allow_delete = st.checkbox("Allow participants to delete categories", value=(condition in ["OPEN", "HYBRID"]))
        with c2:
            allow_unassigned = st.checkbox("Allow cards to remain unassigned", value=False)
            require_all = st.checkbox("Require all cards to be placed before submitting", value=True)
            log_interactions = st.checkbox("Enable detailed interaction logging", value=True)

        submitted = st.form_submit_button("Create Study Workspace")
        if submitted:
            success, msg, study = study_service.create_study(
                title=title, description=description, instructions=instructions,
                researcher_info=researcher_info, condition=condition, item_label=item_label,
                allow_new_categories=allow_new, allow_rename_categories=allow_rename,
                allow_delete_categories=allow_delete, allow_unassigned=allow_unassigned,
                require_all_placed=require_all, log_interactions=log_interactions
            )
            if success:
                st.success(f"Study created! Study Token: `{study.token}`")
                st.rerun()
            else:
                st.error(msg)