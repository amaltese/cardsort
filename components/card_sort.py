import streamlit as st
from typing import List, Dict
from database.models import Study, Card
from services.sort_service import SortService

def pluralize_label(label: str) -> str:
    lbl = (label or "Card").strip()
    if lbl.lower().endswith('y') and not lbl.lower()[-2:] in ['ay', 'ey', 'iy', 'oy', 'uy']:
        return lbl[:-1] + 'ies'
    elif lbl.lower().endswith(('s', 'x', 'z', 'ch', 'sh')):
        return lbl + 'es'
    return lbl + 's'

def render_card_sort_workspace(study: Study, cards: List[Card]):
    # Custom CSS for research-grade index card styling
    st.markdown("""
    <style>
        .card-box {
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-left: 4px solid #1E88E5;
            border-radius: 8px;
            padding: 14px;
            margin-bottom: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            transition: transform 0.1s ease, box-shadow 0.1s ease;
        }
        .card-box:hover {
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        .card-title {
            font-size: 16px;
            font-weight: 700;
            color: #1A1A1A;
            margin-bottom: 4px;
        }
        .card-desc {
            font-size: 13px;
            color: #555555;
            line-height: 1.4;
            margin-bottom: 6px;
        }
        .card-example {
            font-size: 12px;
            font-style: italic;
            color: #777777;
            background-color: #F8F9FA;
            padding: 4px 8px;
            border-radius: 4px;
            display: inline-block;
        }
        .category-bucket {
            background-color: #F4F6F8;
            border: 2px dashed #CBD5E1;
            border-radius: 8px;
            padding: 12px;
            min-height: 200px;
            margin-bottom: 16px;
        }
        .bucket-header {
            font-size: 16px;
            font-weight: 600;
            color: #0F172A;
            border-bottom: 2px solid #E2E8F0;
            padding-bottom: 8px;
            margin-bottom: 12px;
        }
    </style>
    """, unsafe_allow_html=True)

    plural_label = pluralize_label(study.item_label)

    # Fetch predefined categories for Hybrid, Closed, or Proposed conditions
    db_categories = []
    if study.condition in ["CLOSED", "HYBRID", "PROPOSED"]:
        from services.study_service import StudyService
        svc = StudyService()
        db_categories = [cat.name for cat in svc.cat_repo.get_categories_for_study(study.study_id)]

    # Initialize session state for categories
    if "categories" not in st.session_state or not st.session_state["categories"]:
        st.session_state["categories"] = db_categories.copy()

    # Initialize placements
    if "placements" not in st.session_state:
        st.session_state["placements"] = {"Unassigned": [c.card_id for c in cards]}
        for cat_name in st.session_state["categories"]:
            st.session_state["placements"][cat_name] = []

    # Keep placements synced with any new categories added
    for cat_name in st.session_state["categories"]:
        if cat_name not in st.session_state["placements"]:
            st.session_state["placements"][cat_name] = []

    cards_by_id = {c.card_id: c for c in cards}

    # Top Control Bar: Category Creation
    if study.allow_new_categories:
        with st.expander("➕ Create New Category", expanded=(len(st.session_state["categories"]) == 0)):
            c_input, c_btn = st.columns([3, 1])
            with c_input:
                new_cat_name = st.text_input("Category Name", key="new_cat_input", label_visibility="collapsed", placeholder="Enter category name...")
            with c_btn:
                if st.button("Add Category", type="primary", use_container_width=True):
                    clean_name = new_cat_name.strip()
                    if clean_name and clean_name not in st.session_state["categories"] and clean_name != "Unassigned":
                        st.session_state["categories"].append(clean_name)
                        st.session_state["placements"][clean_name] = []
                        st.success(f"Added category '{clean_name}'")
                        st.rerun()

    st.markdown("---")

    # Main Card Sort Workspace (Split Columns)
    unassigned_ids = st.session_state["placements"].get("Unassigned", [])
    active_categories = st.session_state["categories"]

    # Layout: Left = Card Deck | Right = Category Columns
    deck_col, board_col = st.columns([1, 1] if active_categories else [1, 0.01])

    with deck_col:
        st.markdown(f"### 🎴 Unassigned Deck ({len(unassigned_ids)} {plural_label})")
        
        if not unassigned_ids:
            st.success(f"🎉 All {plural_label.lower()} have been placed into categories!")
        else:
            for cid in unassigned_ids:
                c_obj = cards_by_id.get(cid)
                if not c_obj:
                    continue

                with st.container():
                    st.markdown(
                        f"""
                        <div class="card-box">
                            <div class="card-title">{c_obj.title}</div>
                            {f'<div class="card-desc">{c_obj.description}</div>' if c_obj.description else ''}
                            {f'<div class="card-example">e.g. {c_obj.example}</div>' if c_obj.example else ''}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    if active_categories:
                        cols = st.columns(min(len(active_categories), 3))
                        for i, cat in enumerate(active_categories):
                            col_idx = i % min(len(active_categories), 3)
                            with cols[col_idx]:
                                if st.button(f"➡️ {cat}", key=f"move_{cid}_{cat}", use_container_width=True):
                                    st.session_state["placements"] = SortService.move_card(
                                        st.session_state["placements"], cid, cat
                                    )
                                    st.rerun()
                    else:
                        st.caption("👈 Create a category above to start placing cards.")
                    st.markdown("<br>", unsafe_allow_html=True)

    with board_col:
        if active_categories:
            st.markdown(f"### 📂 Category Buckets ({len(active_categories)})")
            
            # Display category columns
            num_cols = min(len(active_categories), 2)
            cat_columns = st.columns(num_cols)

            for idx, cat_name in enumerate(active_categories):
                col_target = cat_columns[idx % num_cols]
                with col_target:
                    placed_ids = st.session_state["placements"].get(cat_name, [])
                    
                    st.markdown(
                        f"""
                        <div class="bucket-header">
                            🏷️ {cat_name} <span style="font-weight:normal; font-size:13px; color:#64748B;">({len(placed_ids)})</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    if study.allow_delete_categories:
                        if st.button("🗑️ Delete Category", key=f"del_cat_{cat_name}", help="Move cards back to unassigned deck and remove category"):
                            st.session_state["placements"]["Unassigned"].extend(placed_ids)
                            del st.session_state["placements"][cat_name]
                            st.session_state["categories"].remove(cat_name)
                            st.rerun()

                    if not placed_ids:
                        st.caption("*Empty bucket*")
                    else:
                        for cid in placed_ids:
                            c_obj = cards_by_id.get(cid)
                            if not c_obj:
                                continue
                            
                            st.markdown(
                                f"""
                                <div style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:6px; padding:8px 12px; margin-bottom:6px;">
                                    <span style="font-weight:600; font-size:14px;">{c_obj.title}</span>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                            if st.button("↩️ Unassign", key=f"unassign_{cid}_{cat_name}", use_container_width=True):
                                st.session_state["placements"] = SortService.move_card(
                                    st.session_state["placements"], cid, "Unassigned"
                                )
                                st.rerun()
                    st.markdown("<hr style='margin: 12px 0;'>", unsafe_allow_html=True)
