import streamlit as st
from services.study_service import StudyService

def render_category_editor(study_id: str, study_service: StudyService):
    st.subheader("Manage Starting Categories")
    
    study = study_service.get_study(study_id)
    if study and study.condition == "OPEN":
        st.info("This is an OPEN sort study. Starting categories are disabled by default for participants.")

    with st.form("add_category_form"):
        name = st.text_input("Category Name*")
        desc = st.text_area("Category Description")
        c1, c2, c3 = st.columns(3)
        with c1:
            fill = st.color_picker("Background Fill", "#FFFFFF")
        with c2:
            text_color = st.color_picker("Text Color", "#000000")
        with c3:
            border = st.color_picker("Border Color", "#CCCCCC")

        if st.form_submit_button("Add Category"):
            if name.strip():
                study_service.add_category_to_study(study_id, name, desc, fill, text_color, border)
                st.success(f"Added category: {name}")
                st.rerun()
            else:
                st.error("Category name is required.")

    categories = study_service.cat_repo.get_categories_for_study(study_id)
    st.write(f"**Predefined Categories Count:** {len(categories)}")
    for cat in categories:
        cols = st.columns([4, 1])
        with cols[0]:
            st.markdown(f"**{cat.name}**")
            if cat.description:
                st.caption(cat.description)
        with cols[1]:
            if st.button("Delete", key=f"del_cat_{cat.category_id}"):
                study_service.cat_repo.delete_category(cat.category_id)
                st.rerun()