import streamlit as st
from services.study_service import StudyService


CONDITIONS = ["OPEN", "CLOSED", "HYBRID"]

CONDITION_EXPLANATIONS = {
    "OPEN": "Participants create all categories themselves. Do not add starting categories for this type of study.",
    "CLOSED": "You create the starting categories. Participants sort cards into those fixed categories only.",
    "HYBRID": "You create starting categories, and participants may add, rename, or remove categories as they work.",
}


def _questions_from_text(value: str):
    return [line.strip() for line in value.splitlines() if line.strip()]


def _condition_permissions(condition: str):
    """The sort type, rather than separate checkboxes, determines category control."""
    participant_category_control = condition in {"OPEN", "HYBRID"}
    return {
        "allow_new": participant_category_control,
        "allow_rename": participant_category_control,
        "allow_delete": participant_category_control,
    }


def _optional_settings(prefix: str, current=None):
    """Render only settings that genuinely vary independently of sort type."""
    current = current or {}
    has_nonstandard_values = (
        current.get("allow_descriptions", True) is not True
        or current.get("allow_unassigned", False) is not False
        or current.get("require_all", True) is not True
        or current.get("log_interactions", True) is not True
    )
    customize = st.toggle(
        "Customize optional participant settings",
        value=has_nonstandard_values,
        key=f"{prefix}_customize_optional",
        help="Most studies should use the recommended settings below. Turn this on only when your protocol needs an exception.",
    )

    if not customize:
        st.caption("Recommended: show category descriptions, require every card to be sorted, and record interaction events.")
        return True, False, True, True

    allow_descriptions = st.checkbox(
        "Show and allow category descriptions",
        value=current.get("allow_descriptions", True),
        key=f"{prefix}_allow_descriptions",
    )
    completion_rule = st.radio(
        "Completion rule",
        ["Every card must be sorted", "Participants may leave cards unassigned"],
        index=1 if current.get("allow_unassigned", False) else 0,
        key=f"{prefix}_completion_rule",
        help="Choose one rule. This replaces the two conflicting unassigned-card checkboxes.",
    )
    log_interactions = st.checkbox(
        "Record detailed interaction events",
        value=current.get("log_interactions", True),
        key=f"{prefix}_log_interactions",
    )
    allow_unassigned = completion_rule == "Participants may leave cards unassigned"
    return allow_descriptions, allow_unassigned, not allow_unassigned, log_interactions


def _sort_type_intro(condition: str):
    st.info(f"**{condition.title()} sort:** {CONDITION_EXPLANATIONS[condition]}")
    if condition == "CLOSED":
        st.caption("Category names are fixed by the researcher for a closed sort.")
    else:
        st.caption("Participants can create, rename, and remove their own categories for this sort type.")


def render_study_builder(study_service: StudyService):
    st.subheader("Configure New Research Study")
    st.caption("Choose the sort type first. It determines who controls categories; optional settings are separate.")

    title = st.text_input("Study Title*", placeholder="e.g., K-12 Teacher Competency Mapping", key="new_study_title")
    description = st.text_area("Study Description", placeholder="Brief description visible to participants", key="new_study_description")
    instructions = st.text_area("Participant Instructions", placeholder="Sort these capacities into meaningful categories...", key="new_study_instructions")
    researcher_info = st.text_input("Researcher / Institution", placeholder="Department of Education, University X", key="new_study_researcher")

    col1, col2 = st.columns(2)
    with col1:
        condition = st.selectbox("Sort Type*", options=CONDITIONS, key="new_study_condition")
    with col2:
        item_label = st.selectbox(
            "Item Label", ["Card", "Capacity", "Concept", "Skill", "Strategy", "Idea", "Behavior", "Attribute"],
            index=1, key="new_study_item_label",
        )

    _sort_type_intro(condition)
    st.markdown("##### Optional Settings")
    allow_descriptions, allow_unassigned, require_all, log_interactions = _optional_settings("new_study")
    questions_text = st.text_area(
        "Reflection questions (one per line)", value="Please explain your sorting logic.",
        help="Participants will see every non-empty line after completing the sort.", key="new_study_questions",
    )

    if st.button("Create Study Workspace", type="primary", key="create_study"):
        permissions = _condition_permissions(condition)
        success, message, study = study_service.create_study(
            title=title, description=description, instructions=instructions,
            researcher_info=researcher_info, condition=condition, item_label=item_label,
            allow_new_categories=permissions["allow_new"], allow_rename_categories=permissions["allow_rename"],
            allow_delete_categories=permissions["allow_delete"], allow_category_descriptions=allow_descriptions,
            allow_unassigned=allow_unassigned, require_all_placed=require_all,
            log_interactions=log_interactions, reflection_questions=_questions_from_text(questions_text),
        )
        if success:
            st.session_state["active_study_id"] = study.study_id
            st.success("Study created. Add cards and, for closed or hybrid sorts, starting categories next.")
            st.rerun()
        else:
            st.error(message)


def render_study_settings(study, study_service: StudyService):
    """Edit settings with the same unambiguous rules used during creation."""
    st.subheader("Study Settings")
    condition = study.condition if study.condition in CONDITIONS else "CLOSED"

    title = st.text_input("Study Title*", value=study.title, key=f"settings_title_{study.study_id}")
    description = st.text_area("Study Description", value=study.description, key=f"settings_description_{study.study_id}")
    instructions = st.text_area("Participant Instructions", value=study.instructions, key=f"settings_instructions_{study.study_id}")
    researcher_info = st.text_input("Researcher / Institution", value=study.researcher_info, key=f"settings_researcher_{study.study_id}")
    condition = st.selectbox("Sort Type*", CONDITIONS, index=CONDITIONS.index(condition), key=f"settings_condition_{study.study_id}")
    item_options = ["Card", "Capacity", "Concept", "Skill", "Strategy", "Idea", "Behavior", "Attribute"]
    item_label = st.selectbox(
        "Item Label", item_options, index=item_options.index(study.item_label) if study.item_label in item_options else 0,
        key=f"settings_item_label_{study.study_id}",
    )
    _sort_type_intro(condition)
    st.caption("Card colors are set in Cards / Items; category colors are set in Starting Categories.")
    st.markdown("##### Optional Settings")
    allow_descriptions, allow_unassigned, require_all, log_interactions = _optional_settings(
        f"settings_{study.study_id}",
        {
            "allow_descriptions": study.allow_category_descriptions,
            "allow_unassigned": study.allow_unassigned,
            "require_all": study.require_all_placed,
            "log_interactions": study.log_interactions,
        },
    )
    questions_text = st.text_area(
        "Reflection questions (one per line)", value="\n".join(study.reflection_questions),
        key=f"settings_questions_{study.study_id}",
    )

    if st.button("Save Study Settings", type="primary", key=f"save_study_{study.study_id}"):
        permissions = _condition_permissions(condition)
        study.title = title.strip()
        study.description = description.strip()
        study.instructions = instructions.strip()
        study.researcher_info = researcher_info.strip()
        study.condition = condition
        study.item_label = item_label
        study.allow_new_categories = permissions["allow_new"]
        study.allow_rename_categories = permissions["allow_rename"]
        study.allow_delete_categories = permissions["allow_delete"]
        study.allow_category_descriptions = allow_descriptions
        study.allow_unassigned = allow_unassigned
        study.require_all_placed = require_all
        study.log_interactions = log_interactions
        study.reflection_questions = _questions_from_text(questions_text)
        success, message = study_service.update_study(study)
        if success:
            st.success(message)
            st.rerun()
        else:
            st.error(message)
