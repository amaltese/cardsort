import streamlit as st
from typing import List, Dict
from database.models import Study, Card
from services.sort_service import SortService

def render_card_sort_workspace(study: Study, cards: List[Card]):
    st.subheader("Card Sorting Workspace")

    # Session State Initialization
    if "categories" not in st.session_state:
        st.session_state["categories"] = []
    if "placements" not in st.session_state:
        # Initialize all cards in Unassigned
        st.session_state["placements"] = {
            "Unassigned": [c.card_id for c in cards]
        }
        for cat_name in st.session_state["categories"]:
            st.session_state["placements"][cat_name] = []

    cards_by_id = {c.card_id: c for c in cards}

    # Category Creation (if permitted)
    if study.allow_new_categories:
        with st.expander("Create New Category", expanded=True):
            cols = st.columns([3, 1])
            with cols[0]:
                new_cat_name = st.text_input("New Category Name", key="new_cat_input", label_visibility="collapsed", placeholder="Enter new category name...")
            with cols[1]:
                if st.button("Add Category", use_container_width=True):
                    clean_name = new_cat_name.strip()
                    if clean_name and clean_name not in st.session_state["categories"] and clean_name != "Unassigned":
                        st.session_state["categories"].append(clean_name)
                        st.session_state["placements"][clean_name] = []
                        st.success(f"Category '{clean_name}' created.")
                        st.rerun()

    st.markdown("---")

    # Display Current Categories & Cards Matrix
    available_categories = ["Unassigned"] + st.session_state["categories"]
    
    # Unassigned Cards Pool
    unassigned_ids = st.session_state["placements"].get("Unassigned", [])
    st.markdown(f"### Unassigned {study.item_label}s ({len(unassigned_ids)})")
    
    if not unassigned_ids:
        st.success(f"All {study.item_label.lower()}s have been assigned to categories!")
    else:
        for cid in unassigned_ids:
            c_obj = cards_by_id.get(cid)
            if not c_obj:
                continue
            
            with st.container():
                st.markdown(
                    f"""
                    <div style="border: 1px solid #CCCCCC; background-color: #FFFFFF; padding: 12px; border-radius: 6px; margin-bottom: 8px;">
                        <span style="font-weight: bold; color: #000000;">{c_obj.title}</span>
                        <p style="margin: 4px 0 0 0; color: #555555; font-size: 14px;">{c_obj.description}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # Category Assignment Selector
                target = st.selectbox(
                    f"Assign '{c_obj.title}' to category:",
                    options=available_categories,
                    index=0,
                    key=f"select_{cid}"
                )
                if target != "Unassigned":
                    st.session_state["placements"] = SortService.move_card(
                        st.session_state["placements"], cid, target
                    )
                    st.rerun()

    # Active Categories Columns
    if st.session_state["categories"]:
        st.markdown("---")
        st.markdown("### Your Formed Categories")
        cat_cols = st.columns(len(st.session_state["categories"]))
        
        for idx, cat_name in enumerate(st.session_state["categories"]):
            with cat_cols[idx]:
                placed_ids = st.session_state["placements"].get(cat_name, [])
                st.markdown(f"#### {cat_name} ({len(placed_ids)})")
                
                if study.allow_delete_categories:
                    if st.button("Delete Category", key=f"del_cat_btn_{cat_name}"):
                        # Reassign cards back to Unassigned
                        st.session_state["placements"]["Unassigned"].extend(placed_ids)
                        del st.session_state["placements"][cat_name]
                        st.session_state["categories"].remove(cat_name)
                        st.rerun()

                for cid in placed_ids:
                    c_obj = cards_by_id.get(cid)
                    if not c_obj:
                        continue
                    st.markdown(
                        f"""
                        <div style="border: 1px solid #000000; background-color: #FAFAFA; padding: 8px; border-radius: 4px; margin-bottom: 6px;">
                            <span style="font-weight: 500;">{c_obj.title}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    if st.button("Move to Unassigned", key=f"unassign_{cid}"):
                        st.session_state["placements"] = SortService.move_card(
                            st.session_state["placements"], cid, "Unassigned"
                        )
                        st.rerun()