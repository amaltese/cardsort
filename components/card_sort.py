import streamlit as st
import html
import random
import re
from typing import List, Dict
from database.models import Study, Card
from services.sort_service import SortService
from components.tabletop_sort import render_tabletop_component

def pluralize_label(label: str) -> str:
    lbl = (label or "Card").strip()
    if lbl.lower().endswith('y') and not lbl.lower()[-2:] in ['ay', 'ey', 'iy', 'oy', 'uy']:
        return lbl[:-1] + 'ies'
    elif lbl.lower().endswith(('s', 'x', 'z', 'ch', 'sh')):
        return lbl + 'es'
    return lbl + 's'

def _safe_color(value: str, fallback: str) -> str:
    return value if re.fullmatch(r"#[0-9a-fA-F]{6}", value or "") else fallback


def _card_location(placements, card_id):
    for category_name, card_ids in placements.items():
        if card_id in card_ids:
            return category_name
    return None


def _move_card(
    placements, card_id, category_name, participant_service, session_token, study,
    method="button", source_category=None,
):
    source_category = source_category or _card_location(placements, card_id)
    st.session_state["placements"] = SortService.move_card(placements, card_id, category_name)
    if participant_service:
        payload = {"card_id": card_id, "category": category_name}
        if source_category:
            payload["from_category"] = source_category
        if method:
            payload["method"] = method
        participant_service.record_interaction(
            session_token, study, "card_moved", payload
        )


def _component_state_value(component_key, value_name):
    component_state = st.session_state.get(component_key)
    if component_state is None:
        return None
    if isinstance(component_state, dict):
        return component_state.get(value_name)
    return getattr(component_state, value_name, None)


def _clear_tabletop_history(session_token):
    for layout_name in ("tabletop", "freeform"):
        st.session_state.pop(f"{layout_name}_history_{session_token}", None)


def _render_tabletop_sorter(
    cards_by_id, unassigned_ids, active_categories, category_styles,
    default_category_style, study, participant_service, session_token, mode="TABLETOP",
):
    is_freeform = mode == "FREEFORM"
    heading = "Freeform sorting workspace" if is_freeform else "Interactive tabletop"
    st.markdown(f"### 2. {heading} ({len(unassigned_ids)} remaining)")
    item_label = (study.item_label or "Item").strip().lower()
    plural_label = pluralize_label(study.item_label).lower()
    if is_freeform:
        st.caption(
            f"Drag a {item_label} into the workspace to start a new named pile, then move {plural_label} "
            f"between piles. You can also select a {item_label}, then choose a pile or create a new one."
        )
    else:
        st.caption(
            f"Drag {plural_label} between the tray and category bins, or select a {item_label} and then "
            f"click Place here. Select any placed {item_label} to move it again."
        )
    if not active_categories and not (is_freeform and study.allow_new_categories):
        st.info("Create a category above before you start sorting.")
        return

    prefix = mode.lower()
    component_key = f"{prefix}_workspace_{session_token}"
    history_key = f"{prefix}_history_{session_token}"
    move_seen_key = f"{prefix}_move_seen_{session_token}"
    undo_seen_key = f"{prefix}_undo_seen_{session_token}"
    create_seen_key = f"{prefix}_create_seen_{session_token}"
    announcement_key = f"{prefix}_announcement_{session_token}"
    focus_key = f"{prefix}_focus_target_{session_token}"

    def handle_move():
        move = _component_state_value(component_key, "move")
        if not isinstance(move, dict):
            return
        event_id = str(move.get("event_id") or "")
        if not event_id or st.session_state.get(move_seen_key) == event_id:
            return
        st.session_state[move_seen_key] = event_id

        card_id = str(move.get("card_id") or "")
        target = str(move.get("target_category") or "")
        placements = st.session_state.get("placements", {})
        source = _card_location(placements, card_id)
        if card_id not in cards_by_id or target not in {"Unassigned", *active_categories}:
            return
        if not source or source == target:
            return

        history = st.session_state.setdefault(history_key, [])
        history.append({"card_id": card_id, "source": source, "target": target})
        if len(history) > 100:
            del history[:-100]
        method = str(move.get("method") or "tabletop")
        if method not in {"click", "drag", "keyboard"}:
            method = "tabletop"
        _move_card(
            placements, card_id, target, participant_service, session_token, study,
            method=method, source_category=source,
        )
        if method == "keyboard":
            remaining_ids = st.session_state["placements"].get("Unassigned", [])
            if source == "Unassigned" and remaining_ids:
                st.session_state[focus_key] = {"kind": "card", "card_id": remaining_ids[0]}
            elif source != "Unassigned":
                st.session_state[focus_key] = {"kind": "card", "card_id": card_id}
            else:
                st.session_state[focus_key] = {"kind": "undo"}
        st.session_state[announcement_key] = f"{cards_by_id[card_id].title} moved to {target}."

    def handle_create():
        create = _component_state_value(component_key, "create")
        if not isinstance(create, dict) or not (is_freeform and study.allow_new_categories):
            return
        event_id = str(create.get("event_id") or "")
        if not event_id or st.session_state.get(create_seen_key) == event_id:
            return
        st.session_state[create_seen_key] = event_id

        card_id = str(create.get("card_id") or "")
        clean_name = str(create.get("category_name") or "").strip()
        placements = st.session_state.get("placements", {})
        source = _card_location(placements, card_id)
        existing_names = {category.casefold() for category in st.session_state["categories"]}
        if card_id not in cards_by_id or not source:
            return
        if not clean_name:
            st.session_state[announcement_key] = "Enter a name for the new pile."
            return
        if clean_name.casefold() == "unassigned" or clean_name.casefold() in existing_names:
            st.session_state[announcement_key] = "Choose a unique name for the new pile."
            return

        st.session_state["categories"].append(clean_name)
        st.session_state["placements"][clean_name] = []
        st.session_state["category_descriptions"][clean_name] = ""
        history = st.session_state.setdefault(history_key, [])
        history.append(
            {"card_id": card_id, "source": source, "target": clean_name, "created_category": clean_name}
        )
        if len(history) > 100:
            del history[:-100]
        method = str(create.get("method") or "tabletop")
        _move_card(
            placements, card_id, clean_name, participant_service, session_token, study,
            method="new_pile", source_category=source,
        )
        if participant_service:
            participant_service.record_interaction(
                session_token, study, "category_created", {"category": clean_name, "method": method}
            )
        if method == "keyboard":
            st.session_state[focus_key] = {"kind": "card", "card_id": card_id}
        st.session_state[announcement_key] = f"Created {clean_name} and moved {cards_by_id[card_id].title} there."

    def handle_undo():
        undo = _component_state_value(component_key, "undo")
        if not isinstance(undo, dict):
            return
        event_id = str(undo.get("event_id") or "")
        if not event_id or st.session_state.get(undo_seen_key) == event_id:
            return
        st.session_state[undo_seen_key] = event_id

        history = st.session_state.setdefault(history_key, [])
        placements = st.session_state.get("placements", {})
        if not history:
            return
        last_move = history.pop()
        card_id = last_move.get("card_id")
        source = last_move.get("source")
        target = last_move.get("target")
        if (
            card_id not in cards_by_id
            or source not in placements
            or _card_location(placements, card_id) != target
        ):
            history.clear()
            st.session_state[announcement_key] = "Undo history was reset because the categories changed."
            return
        _move_card(
            placements, card_id, source, participant_service, session_token, study,
            method="undo", source_category=target,
        )
        created_category = last_move.get("created_category")
        if (
            created_category
            and created_category in st.session_state["categories"]
            and not st.session_state["placements"].get(created_category)
        ):
            del st.session_state["placements"][created_category]
            st.session_state["categories"].remove(created_category)
            st.session_state["category_descriptions"].pop(created_category, None)
            st.session_state[announcement_key] = f"Last move undone and empty pile “{created_category}” removed."
        else:
            st.session_state[announcement_key] = f"Last move undone. {cards_by_id[card_id].title} returned to {source}."
        if str(undo.get("method") or "") == "keyboard":
            st.session_state[focus_key] = {"kind": "card", "card_id": card_id}

    card_data = [
        {
            "id": card.card_id,
            "title": card.title,
            "description": card.description,
            "example": card.example,
            "fill": _safe_color(card.color_fill, "#EFF6FF"),
            "text": _safe_color(card.color_text, "#0F172A"),
            "border": _safe_color(card.color_border, "#2563EB"),
        }
        for card in cards_by_id.values()
    ]
    category_data = []
    for category_name in active_categories:
        style = category_styles.get(category_name, default_category_style)
        category_data.append(
            {
                "name": category_name,
                "description": (
                    st.session_state.get("category_descriptions", {}).get(
                        category_name, style.get("description", "")
                    )
                    if study.allow_category_descriptions
                    else ""
                ),
                "fill": style["fill"],
                "text": style["text"],
                "border": style["border"],
            }
        )

    mounted = render_tabletop_component(
        {
            "cards": card_data,
            "categories": category_data,
            "placements": {
                category: list(card_ids)
                for category, card_ids in st.session_state["placements"].items()
            },
            "can_undo": bool(st.session_state.get(history_key)),
            "announcement": st.session_state.pop(announcement_key, ""),
            "focus_target": st.session_state.pop(focus_key, None),
            "item_label": item_label,
            "plural_label": plural_label,
            "mode": mode,
            "can_create": is_freeform and study.allow_new_categories,
        },
        key=component_key,
        on_move=handle_move,
        on_undo=handle_undo,
        on_create=handle_create,
    )
    if not mounted:
        st.error("The interactive tabletop needs Streamlit 1.65 or newer. The app is still loading the required update.")


def _render_large_card(card: Card):
    card_fill = _safe_color(card.color_fill, "#EFF6FF")
    if card_fill == "#FFFFFF":
        card_fill = "#EFF6FF"
    card_text = _safe_color(card.color_text, "#0F172A")
    card_border = _safe_color(card.color_border, "#2563EB")
    st.markdown(
        f"""
        <div style="background:{card_fill}; color:{card_text}; border:3px solid {card_border}; border-radius:16px;
                    padding:32px; margin:14px auto 20px; max-width:900px; box-shadow:0 5px 14px rgba(15, 23, 42, .10);">
            <div style="font-size:24px; font-weight:700; line-height:1.4;">{html.escape(card.title)}</div>
            {f'<div style="font-size:16px; line-height:1.5; margin-top:14px;">{html.escape(card.description)}</div>' if card.description else ''}
            {f'<div style="font-size:14px; font-style:italic; margin-top:14px;">Example: {html.escape(card.example)}</div>' if card.example else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _focused_card_id(unassigned_ids: List[str], session_token: str) -> str:
    focus_key = f"focused_card_{session_token}"
    if st.session_state.get(focus_key) not in unassigned_ids:
        st.session_state[focus_key] = unassigned_ids[0]
    return st.session_state[focus_key]


def _render_focused_carousel(cards_by_id, unassigned_ids, active_categories, study, participant_service, session_token):
    st.markdown(f"### 2. Focused sorter ({len(unassigned_ids)} remaining)")
    st.caption("Review one item at a time, then choose the category that fits it best. You can revisit placed items below.")
    if not unassigned_ids:
        st.success("All items have been placed. Review your categories below before submitting.")
        return
    if not active_categories:
        st.info("Create a category above before you start sorting.")
        return

    card_id = _focused_card_id(unassigned_ids, session_token)
    card_index = unassigned_ids.index(card_id)
    previous, position, following = st.columns([1, 4, 1])
    with previous:
        if st.button("← Previous", disabled=len(unassigned_ids) == 1, key="focused_previous"):
            st.session_state[f"focused_card_{session_token}"] = unassigned_ids[(card_index - 1) % len(unassigned_ids)]
            st.rerun()
    with position:
        st.markdown(f"<div style='text-align:center; padding-top:8px; font-weight:600;'>Item {card_index + 1} of {len(unassigned_ids)} remaining</div>", unsafe_allow_html=True)
    with following:
        if st.button("Next →", disabled=len(unassigned_ids) == 1, key="focused_next"):
            st.session_state[f"focused_card_{session_token}"] = unassigned_ids[(card_index + 1) % len(unassigned_ids)]
            st.rerun()

    card = cards_by_id[card_id]
    _render_large_card(card)
    st.markdown("##### Choose a category")
    columns = st.columns(min(len(active_categories), 3))
    for index, category in enumerate(active_categories):
        with columns[index % len(columns)]:
            if st.button(category, key=f"focused_move_{card_id}_{category}", use_container_width=True, type="primary"):
                _move_card(st.session_state["placements"], card_id, category, participant_service, session_token, study)
                remaining = st.session_state["placements"]["Unassigned"]
                if remaining:
                    st.session_state[f"focused_card_{session_token}"] = remaining[min(card_index, len(remaining) - 1)]
                st.rerun()


def _render_board_sorter(cards_by_id, unassigned_ids, active_categories, category_styles, default_category_style, study, participant_service, session_token):
    st.markdown(f"### 2. Board-style sorter ({len(unassigned_ids)} remaining)")
    st.caption("Choose an item, then click the category bin where it belongs. This is a board-style alternative to drag-and-drop; review the full bins below.")
    if not unassigned_ids:
        st.success("All items have been placed. Review your categories below before submitting.")
        return
    if not active_categories:
        st.info("Create a category above before you start sorting.")
        return

    card_id = _focused_card_id(unassigned_ids, session_token)
    card_index = unassigned_ids.index(card_id)
    navigation_left, navigation_right = st.columns(2)
    with navigation_left:
        if st.button("← Previous item", disabled=len(unassigned_ids) == 1, key="board_previous"):
            st.session_state[f"focused_card_{session_token}"] = unassigned_ids[(card_index - 1) % len(unassigned_ids)]
            st.rerun()
    with navigation_right:
        if st.button("Next item →", disabled=len(unassigned_ids) == 1, key="board_next"):
            st.session_state[f"focused_card_{session_token}"] = unassigned_ids[(card_index + 1) % len(unassigned_ids)]
            st.rerun()

    _render_large_card(cards_by_id[card_id])
    st.markdown("##### Place this item in a category bin")
    columns = st.columns(min(len(active_categories), 3))
    for index, category in enumerate(active_categories):
        with columns[index % len(columns)]:
            style = category_styles.get(category, default_category_style)
            count = len(st.session_state["placements"].get(category, []))
            with st.container(border=True):
                st.markdown(f"<div style='font-weight:700; color:{style['text']};'>{html.escape(category)}</div>", unsafe_allow_html=True)
                st.caption(f"{count} item{'s' if count != 1 else ''} currently here")
                if st.button("Place here", key=f"board_move_{card_id}_{category}", use_container_width=True):
                    _move_card(st.session_state["placements"], card_id, category, participant_service, session_token, study)
                    remaining = st.session_state["placements"]["Unassigned"]
                    if remaining:
                        st.session_state[f"focused_card_{session_token}"] = remaining[min(card_index, len(remaining) - 1)]
                    st.rerun()


def render_card_sort_workspace(study: Study, cards: List[Card], participant_service=None, session_token: str = ""):
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

    item_label = (study.item_label or "Item").strip() or "Item"
    plural_label = pluralize_label(item_label)

    # Fetch DB starting categories
    db_categories = []
    if study.condition in ["CLOSED", "HYBRID"]:
        from services.study_service import StudyService
        svc = StudyService()
        db_category_objects = svc.get_categories_for_participants(study.study_id)
        db_categories = [category.name for category in db_category_objects]
    else:
        db_category_objects = []
    default_category_style = {"fill": "#E0F2FE", "text": "#0C4A6E", "border": "#0284C7"}
    category_styles = {}
    for category in db_category_objects:
        style = {
            "fill": _safe_color(category.color_fill, default_category_style["fill"]),
            "text": _safe_color(category.color_text, default_category_style["text"]),
            "border": _safe_color(category.color_border, default_category_style["border"]),
            "description": category.description,
        }
        # Earlier versions created categories with a white-on-white default.
        # Show those legacy defaults as a calm blue until the researcher picks
        # a different color in the category editor.
        if (style["fill"], style["text"], style["border"]) == ("#FFFFFF", "#000000", "#CCCCCC"):
            style.update(default_category_style)
        category_styles[category.name] = style

    if "categories" not in st.session_state or not st.session_state["categories"]:
        presented_categories = db_categories.copy()
        if study.category_order == "RANDOM":
            # Keep the order stable within one participant's session, but vary
            # it across participants to avoid a display-order effect.
            random.Random(f"{study.study_id}:{session_token}").shuffle(presented_categories)
        st.session_state["categories"] = presented_categories
    if "category_descriptions" not in st.session_state:
        st.session_state["category_descriptions"] = {
            category.name: category.description for category in db_category_objects
        }

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
    layout = getattr(study, "participant_layout", "STANDARD")

    st.markdown("### 1. Categories")
    if study.condition == "CLOSED":
        st.caption("The research team provided fixed categories. You can review them below while you sort.")
    elif study.condition == "HYBRID":
        st.caption("Start with the provided categories, or add your own if one would better fit your organization.")
    else:
        st.caption("Create the categories that best represent how you would organize these items.")

    # Category Creation Header
    if study.allow_new_categories and layout != "FREEFORM":
        with st.expander("Add a category", expanded=(len(st.session_state["categories"]) == 0)):
            c_input, c_btn = st.columns([3, 1])
            with c_input:
                new_cat_name = st.text_input("Category Name", key="new_cat_input", label_visibility="collapsed", placeholder="Enter new category name...")
            with c_btn:
                if st.button("Add Category", type="primary", use_container_width=True):
                    clean_name = new_cat_name.strip()
                    existing_category_names = {
                        category_name.casefold() for category_name in st.session_state["categories"]
                    }
                    if not clean_name:
                        st.error("Enter a category name.")
                    elif clean_name.casefold() == "unassigned":
                        st.error("“Unassigned” is reserved for items that have not been placed yet.")
                    elif clean_name.casefold() in existing_category_names:
                        st.error("Choose a unique category name.")
                    else:
                        placed_card_count = sum(
                            len(card_ids)
                            for category, card_ids in st.session_state["placements"].items()
                            if category != "Unassigned"
                        )
                        st.session_state["categories"].append(clean_name)
                        st.session_state["placements"][clean_name] = []
                        st.session_state["category_descriptions"][clean_name] = ""
                        if placed_card_count:
                            st.session_state["category_review_notice"] = (
                                f"You added “{clean_name}” after placing {placed_card_count} item"
                                f"{'s' if placed_card_count != 1 else ''}. Review your existing categories in case any items belong here."
                            )
                        if participant_service:
                            participant_service.record_interaction(
                                session_token, study, "category_created", {"category": clean_name}
                            )
                        st.success(f"Added category '{clean_name}'")
                        st.rerun()

    if st.session_state.get("category_review_notice"):
        st.warning(st.session_state["category_review_notice"])
        if st.button("I have reviewed my categories", key="dismiss_category_review_notice"):
            st.session_state.pop("category_review_notice", None)
            st.rerun()

    st.markdown("---")

    unassigned_ids = st.session_state["placements"].get("Unassigned", [])
    active_categories = st.session_state["categories"]

    layout_state_key = f"tabletop_layout_{session_token}"
    if st.session_state.get(layout_state_key) != layout:
        _clear_tabletop_history(session_token)
        st.session_state[layout_state_key] = layout
    if layout == "FOCUSED":
        _render_focused_carousel(cards_by_id, unassigned_ids, active_categories, study, participant_service, session_token)
    elif layout == "BOARD":
        _render_board_sorter(
            cards_by_id, unassigned_ids, active_categories, category_styles, default_category_style,
            study, participant_service, session_token,
        )
    elif layout == "TABLETOP":
        _render_tabletop_sorter(
            cards_by_id, unassigned_ids, active_categories, category_styles, default_category_style,
            study, participant_service, session_token,
        )
    elif layout == "FREEFORM":
        _render_tabletop_sorter(
            cards_by_id, unassigned_ids, active_categories, category_styles, default_category_style,
            study, participant_service, session_token, mode="FREEFORM",
        )
    else:
        # The original deck remains available as the standard layout.
        st.markdown(f"### 2. Sort the unassigned deck ({len(unassigned_ids)} {plural_label})")
        st.caption("For each item, choose the category that fits best. You can unassign an item later if you change your mind.")
        if not unassigned_ids:
            st.success(f"🎉 All {plural_label.lower()} have been placed into categories!")
        else:
            search_query = ""
            if len(unassigned_ids) > 10:
                search_query = st.text_input("Search unassigned items", placeholder="Type to filter...", key="deck_search").strip().lower()
            filtered_unassigned = [
                card_id for card_id in unassigned_ids
                if card_id in cards_by_id and (
                    not search_query
                    or search_query in cards_by_id[card_id].title.lower()
                    or search_query in cards_by_id[card_id].description.lower()
                )
            ]
            items_per_page = 10
            if len(filtered_unassigned) > items_per_page:
                total_pages = (len(filtered_unassigned) + items_per_page - 1) // items_per_page
                page = st.number_input("Deck page", min_value=1, max_value=total_pages, value=1, step=1, key="deck_page_num")
                page_ids = filtered_unassigned[(page - 1) * items_per_page: page * items_per_page]
                st.caption(f"Showing page {page} of {total_pages}")
            else:
                page_ids = filtered_unassigned
            for card_id in page_ids:
                card = cards_by_id[card_id]
                with st.container():
                    card_fill = _safe_color(card.color_fill, "#EFF6FF")
                    if card_fill == "#FFFFFF":
                        card_fill = "#EFF6FF"
                    card_text = _safe_color(card.color_text, "#0F172A")
                    card_border = _safe_color(card.color_border, "#2563EB")
                    description_html = (
                        f'<div class="card-desc">{html.escape(card.description)}</div>'
                        if card.description else ""
                    )
                    example_html = (
                        f'<div class="card-example">e.g. {html.escape(card.example)}</div>'
                        if card.example else ""
                    )
                    st.markdown(
                        f'<div class="card-box" style="background:{card_fill}; color:{card_text}; border-left-color:{card_border};">'
                        f'<div class="card-title">{html.escape(card.title)}</div>'
                        f'{description_html}'
                        f'{example_html}'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                    if active_categories and len(active_categories) <= 6:
                        columns = st.columns(min(len(active_categories), 3))
                        for index, category in enumerate(active_categories):
                            with columns[index % len(columns)]:
                                if st.button(f"Place in {category}", key=f"deck_move_{card_id}_{category}", use_container_width=True):
                                    _move_card(st.session_state["placements"], card_id, category, participant_service, session_token, study)
                                    st.rerun()
                    elif active_categories:
                        category = st.selectbox("Move to category", ["Choose a category..."] + active_categories, key=f"deck_category_{card_id}")
                        if category != "Choose a category...":
                            _move_card(st.session_state["placements"], card_id, category, participant_service, session_token, study)
                            st.rerun()
                    else:
                        st.caption("Create a category above to start placing items.")

    category_controls_enabled = any(
        [study.allow_delete_categories, study.allow_rename_categories, study.allow_category_descriptions]
    )
    if active_categories and (layout not in {"TABLETOP", "FREEFORM"} or category_controls_enabled):
        st.markdown("---")
        if layout in {"TABLETOP", "FREEFORM"}:
            review_area = st.expander(
                f"3. Optional category settings ({len(active_categories)})",
                expanded=False,
            )
        else:
            review_area = st.container()

        with review_area:
            if layout in {"TABLETOP", "FREEFORM"}:
                st.caption(
                    "Your full arrangement is visible in the sorting workspace above. Open this section only "
                    "to rename, describe, or remove a category."
                )
            else:
                st.markdown(f"### 3. Review your categories ({len(active_categories)})")
                st.caption(
                    "Review items already placed in each category. You can rename, describe, or "
                    "remove categories when your study allows it."
                )

            num_cols = min(len(active_categories), 3)
            cat_columns = st.columns(num_cols)

            for idx, cat_name in enumerate(active_categories):
                col_target = cat_columns[idx % num_cols]
                with col_target:
                    placed_ids = st.session_state["placements"].get(cat_name, [])
                    style = category_styles.get(cat_name, default_category_style)

                    st.markdown(
                        f"""
                        <div class="bucket-header" style="background:{style['fill']}; color:{style['text']}; border:2px solid {style['border']}; border-radius:6px; padding:8px;">
                            🏷️ {html.escape(cat_name)} <span style="font-weight:normal; font-size:13px;">({len(placed_ids)})</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if study.allow_delete_categories:
                        if st.button(
                            "🗑️ Delete",
                            key=f"del_cat_{cat_name}",
                            help="Move items back to the unassigned tray and remove this category",
                        ):
                            st.session_state["placements"]["Unassigned"].extend(placed_ids)
                            del st.session_state["placements"][cat_name]
                            st.session_state["categories"].remove(cat_name)
                            st.session_state["category_descriptions"].pop(cat_name, None)
                            if layout in {"TABLETOP", "FREEFORM"}:
                                _clear_tabletop_history(session_token)
                            if participant_service:
                                participant_service.record_interaction(
                                    session_token, study, "category_deleted", {"category": cat_name}
                                )
                            st.rerun()

                    if study.allow_rename_categories:
                        renamed = st.text_input("Rename category", value=cat_name, key=f"rename_{cat_name}")
                        if st.button("Rename", key=f"rename_button_{cat_name}"):
                            clean_name = renamed.strip()
                            other_names = {
                                name.casefold()
                                for name in st.session_state["categories"]
                                if name != cat_name
                            }
                            if not clean_name:
                                st.error("Enter a category name.")
                            elif clean_name.casefold() == "unassigned":
                                st.error("“Unassigned” is reserved for items that have not been placed yet.")
                            elif clean_name.casefold() in other_names:
                                st.error("Choose a unique category name.")
                            elif clean_name != cat_name:
                                st.session_state["placements"][clean_name] = st.session_state["placements"].pop(cat_name)
                                st.session_state["categories"][st.session_state["categories"].index(cat_name)] = clean_name
                                description = st.session_state["category_descriptions"].pop(cat_name, "")
                                st.session_state["category_descriptions"][clean_name] = description
                                if layout in {"TABLETOP", "FREEFORM"}:
                                    _clear_tabletop_history(session_token)
                                if participant_service:
                                    participant_service.record_interaction(
                                        session_token, study, "category_renamed", {"from": cat_name, "to": clean_name}
                                    )
                                st.rerun()

                    if study.allow_category_descriptions:
                        current_description = st.session_state["category_descriptions"].get(cat_name, "")
                        st.session_state["category_descriptions"][cat_name] = st.text_input(
                            "Category description", value=current_description, key=f"desc_{cat_name}"
                        )

                    if layout in {"TABLETOP", "FREEFORM"}:
                        st.caption(
                            f"{len(placed_ids)} {item_label.lower() if len(placed_ids) == 1 else plural_label.lower()} "
                            "currently in this category."
                        )
                    elif not placed_ids:
                        st.caption("*Empty bucket*")
                    else:
                        for cid in placed_ids:
                            c_obj = cards_by_id.get(cid)
                            if not c_obj:
                                continue

                            st.markdown(
                                f"""
                                <div style="background:{_safe_color(c_obj.color_fill, '#FFFFFF')}; color:{_safe_color(c_obj.color_text, '#0F172A')}; border:1px solid {_safe_color(c_obj.color_border, '#CBD5E1')}; border-radius:6px; padding:8px 12px; margin-bottom:6px;">
                                    <span style="font-weight:600; font-size:14px;">{html.escape(c_obj.title)}</span>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                            if st.button("↩️ Unassign", key=f"unassign_{cid}_{cat_name}", use_container_width=True):
                                _move_card(
                                    st.session_state["placements"], cid, "Unassigned",
                                    participant_service, session_token, study,
                                )
                                st.rerun()
                    st.markdown("<hr style='margin: 12px 0;'>", unsafe_allow_html=True)
