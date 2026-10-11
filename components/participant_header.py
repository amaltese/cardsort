import streamlit as st
from typing import List, Optional
from database.models import Study
from database.models import Category
from components.card_sort import pluralize_label

def render_participant_header(study: Study, starting_categories: Optional[List[Category]] = None):
    st.title(study.title)
    if study.researcher_info:
        st.caption(f"Hosted by: {study.researcher_info}")

    with st.container(border=True):
        st.markdown("#### Before you begin")
        if study.description:
            st.markdown(f"**About this study:** {study.description}")
        if study.instructions:
            st.markdown(f"**Your task:** {study.instructions}")
        st.markdown(
            f"You will organize **{pluralize_label(study.item_label).lower()}** into categories, review your organization, and record a short voice memo before submitting."
        )

    if study.condition in {"CLOSED", "HYBRID"} and starting_categories:
        st.markdown("#### You will begin with these categories")
        st.caption(
            "You can sort into these categories first."
            + (" You may also create or change categories as you work." if study.condition == "HYBRID" else "")
        )
        columns = st.columns(min(len(starting_categories), 3))
        for index, category in enumerate(starting_categories):
            with columns[index % len(columns)]:
                with st.container(border=True):
                    st.markdown(f"**{category.name}**")
                    if category.description:
                        st.caption(category.description)
    elif study.condition == "OPEN":
        st.info("You will create the categories that best fit your organization of these items.")
