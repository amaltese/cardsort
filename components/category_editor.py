import streamlit as st
import html
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
            fill = st.color_picker("Background Fill", "#E0F2FE")
        with c2:
            text_color = st.color_picker("Text Color", "#0C4A6E")
        with c3:
            border = st.color_picker("Border Color", "#0284C7")

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
            st.markdown(
                f"<div style='background:{cat.color_fill};color:{cat.color_text};border:2px solid {cat.color_border};"
                f"padding:8px 12px;border-radius:6px;'><strong>{html.escape(cat.name)}</strong></div>",
                unsafe_allow_html=True,
            )
            if cat.description:
                st.caption(cat.description)
            with st.expander("Edit category appearance", expanded=False):
                with st.form(f"edit_category_{cat.category_id}"):
                    edited_name = st.text_input("Category Name", value=cat.name)
                    edited_description = st.text_area("Category Description", value=cat.description)
                    e1, e2, e3 = st.columns(3)
                    with e1:
                        edited_fill = st.color_picker("Background Fill", cat.color_fill)
                    with e2:
                        edited_text = st.color_picker("Text Color", cat.color_text)
                    with e3:
                        edited_border = st.color_picker("Border Color", cat.color_border)
                    if st.form_submit_button("Save Category"):
                        if not edited_name.strip():
                            st.error("Category name is required.")
                        elif edited_name.strip() != cat.name and any(
                            other.name == edited_name.strip() for other in categories
                        ):
                            st.error("Category names must be unique within a study.")
                        else:
                            cat.name = edited_name.strip()
                            cat.description = edited_description.strip()
                            cat.color_fill = edited_fill
                            cat.color_text = edited_text
                            cat.color_border = edited_border
                            study_service.cat_repo.save_categories([cat])
                            st.success("Category updated.")
                            st.rerun()
        with cols[1]:
            if st.button("Delete", key=f"del_cat_{cat.category_id}"):
                study_service.cat_repo.delete_category(cat.category_id)
                st.rerun()
