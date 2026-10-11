import streamlit as st
from database.models import Study
from components.card_sort import pluralize_label

def render_participant_header(study: Study):
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
