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
    st.markdown("""
    <style>
        .card-box {
            background-color: #FFFFFF;
            border: 1px solid #CBD5E1;
            border-left: 5px solid #2563EB;
            border-radius: 8px;
            padding: 12px 14px;
            margin-bottom: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        }
        .card-title {
            font-size: 15px;
            font-weight: 700;
            color: #0F172A;
            margin-bottom: 4px;
        }
        .card-desc {
            font-size: 13px;
            color: #475569;
            line-height: 1.4;
            margin-bottom: 4px;
        }
        .card-example {
            font-size: 11px;
            font-style: italic;
            color: #64748B;
            background-color: #F8FAFC;
            padding: 3px 6px;
            border-radius: 4px;
            display: inline-block;
        }
        .bucket-header {
            font-size: 15px;
            font-weight: 700;
            color: #0F172A;
            border-bottom: 2px solid #E2E8F0;
            padding-bottom: 6px;
            margin-bottom: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

    plural_label = pluralize_label(study.item_label)

    # Fetch DB starting categories
    db_categories = []
    if study.condition in ["CLOSED", "HYBRID", "PROPOSED"]:
        from services.study_service import StudyService
        svc = StudyService()
        db_categories = [cat.name for cat in svc.cat_repo.get_categories_for_study(study.study_id)]

    if "categories" not in st.session_state or not st.session_state["categories"]:
        st.session_state["categories"] = db_categories.copy()

    # State Sync with DB cards
    current_card_ids = set(c.card_id for c in cards)
    
    if "placements" not in st.session_state:
        st.session_state["placements"] = {"Unassigned": [c.card_id for c in cards]}
        for cat_name in st.session_state["categories"]:
            st.session_state["placements"][cat_name] = []
    else:
        for cat in list(st.session_state["placements"].keys()):
            st.session_state["placements"][cat] = [
                cid for cid in st.session_state["placements"][cat] if cid in current_card_ids
            ]
        placed_ids = set(cid for cids in st.session_state["placements"].values() for cid in cids)
        missing_ids = [c.card_id for c in cards if c.card_id not in placed_ids]
        if "Unassigned" not in st.session_state["placements"]:
            st.session_state["placements"]["Unassigned"] = []
        st.session_state["placements"]["Unassigned"].extend(missing_ids)

    for cat_name in st.session_state["categories"]:
        if cat_name not in st.session_state["placements"]:
            st.session_state["placements"][cat_name] = []

    cards_by_id = {c.card_id: c for c in cards}

    # Category Creation Header
    if study.allow_new_categories:
        with st.expander("➕ Create New Category", expanded=(len(st.session_state["categories"]) == 0)):
            c_input, c_btn = st.columns([3, 1])
            with c_input:
                new_cat_name = st.text_input("Category Name", key="new_cat_input", label_visibility="collapsed", placeholder="Enter new category name...")
            with c_btn:
                if st.button("Add Category", type="primary", use_container_width=True):
                    clean_name = new_cat_name.strip()
                    if clean_name and clean_name not in st.session_state["categories"] and clean_name != "Unassigned":
                        st.session_state["categories"].append(clean_name)
                        st.session_state["placements"][clean_name] = []
                        st.success(f"Added category '{clean_name}'")
                        st.rerun()

    st.markdown("---")

    unassigned_ids = st.session_state["placements"].get("Unassigned", [])
    active_categories = st.session_state["categories"]

    deck_col, board_col = st.columns([1, 1] if active_categories else [1, 0.01])

    with deck_col:
        st.markdown(f"### 🎴 Unassigned Deck ({len(unassigned_ids)} {plural_label})")
        
        if not unassigned_ids:
            st.success(f"🎉 All {plural_label.lower()} have been placed into categories!")
        else:
            # Search filter for large decks
            search_query = ""
            if len(unassigned_ids) > 10:
                search_query = st.text_input("🔍 Search unassigned cards:", placeholder="Type to filter...", key="deck_search").strip().lower()

            filtered_unassigned = []
            for cid in unassigned_ids:
                c_obj = cards_by_id.get(cid)
                if c_obj:
                    if search_query:
                        if search_query in c_obj.title.lower() or search_query in c_obj.description.lower():
                            filtered_unassigned.append(cid)
                    else:
                        filtered_unassigned.append(cid)

            # Pagination
            items_per_page = 10
            total_items = len(filtered_unassigned)
            
            if total_items > items_per_page:
                total_pages = (total_items + items_per_page - 1) // items_per_page
                page = st.number_input(f"Page (1 of {total_pages})", min_value=1, max_value=total_pages, value=1, step=1, key="deck_page_num")
                start_idx = (page - 1) * items_per_page
                end_idx = min(start_idx + items_per_page, total_items)
                page_ids = filtered_unassigned[start_idx:end_idx]
                st.caption(f"Showing items {start_idx + 1}–{end_idx} of {total_items}")
            else:
                page_ids = filtered_unassigned

            for cid in page_ids:
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
                        # Direct Clickable Buttons if <= 6 categories
                        if len(active_categories) <= 6:
                            btn_cols = st.columns(min(len(active_categories), 3))
                            for idx, cat_name in enumerate(active_categories):
                                col_target = btn_cols[idx % min(len(active_categories), 3)]
                                with col_target:
                                    if st.button(f"➡️ {cat_name}", key=f"btn_move_{cid}_{cat_name}", use_container_width=True):
                                        st.session_state["placements"] = SortService.move_card(
                                            st.session_state["placements"], cid, cat_name
                                        )
                                        st.rerun()
                        # Dropdown selector fallback if > 6 categories
                        else:
                            cat_options = ["Move to category..."] + active_categories
                            selected_cat = st.selectbox(
                                f"Assign '{c_obj.title}'",
                                options=cat_options,
                                key=f"sel_cat_{cid}",
                                label_visibility="collapsed"
                            )
                            if selected_cat != "Move to category...":
                                st.session_state["placements"] = SortService.move_card(
                                    st.session_state["placements"], cid, selected_cat
                                )
                                st.rerun()
                    else:
                        st.caption("👈 Create a category above to start placing cards.")
                    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

    with board_col:
        if active_categories:
            st.markdown(f"### 📂 Category Buckets ({len(active_categories)})")
            
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
                        if st.button("🗑️ Delete", key=f"del_cat_{cat_name}", help="Move cards back to unassigned deck and remove category"):
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
