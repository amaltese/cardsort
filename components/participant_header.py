import streamlit as st
from database.models import Study

def render_participant_header(study: Study):
    st.title(study.title)
    if study.researcher_info:
        st.caption(f"Hosted by: {study.researcher_info}")
    
    with st.expander("Study Instructions & Context", expanded=True):
        if study.description:
            st.markdown(f"**About this Study:** {study.description}")
        if study.instructions:
            st.info(f"**Instructions:** {study.instructions}")
        st.write(f"**Item Type:** {study.item_label}")
        st.write(f"**Sort Type:** {study.condition.capitalize()} Sort")