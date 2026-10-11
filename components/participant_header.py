import streamlit as st
from database.models import Study

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
            f"You will organize **{study.item_label.lower()}s** into categories, review your organization, and record a short voice memo before submitting."
        )
