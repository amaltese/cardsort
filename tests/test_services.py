import os
import unittest
from database.db import get_connection, init_db, _restore_state
from database.models import Study, Card, Category
from services.study_service import StudyService
from services.participant_service import ParticipantService
from services.analysis_service import AnalysisService
from services.sort_service import SortService
from utils.validation import validate_study_meta, validate_card_csv

class TestCardSortPlatform(unittest.TestCase):
    def setUp(self):
        self.test_db = "test_card_sort.db"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        init_db(self.test_db)
        self.study_service = StudyService(self.test_db)

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_create_study_and_card(self):
        ok, msg, study = self.study_service.create_study(
            title="Teacher Competency Study",
            description="Testing sorting behaviors",
            instructions="Sort all items",
            researcher_info="Lab A",
            condition="HYBRID"
        )
        self.assertTrue(ok)
        self.assertIsNotNone(study)
        self.assertEqual(study.category_order, "RANDOM")
        
        card = self.study_service.add_card_to_study(
            study.study_id,
            title="Lesson Planning",
            description="Designing weekly units"
        )
        self.assertEqual(card.title, "Lesson Planning")
        
        fetched_cards = self.study_service.card_repo.get_cards_for_study(study.study_id)
        self.assertEqual(len(fetched_cards), 1)

    def test_researcher_can_preserve_category_order(self):
        ok, message, study = self.study_service.create_study(
            "Ordered Categories", "", "", "", "CLOSED", category_order="RESEARCHER"
        )
        self.assertTrue(ok, message)
        restored = self.study_service.get_study(study.study_id)
        self.assertEqual(restored.category_order, "RESEARCHER")

    def test_researcher_can_choose_participant_layout(self):
        ok, message, study = self.study_service.create_study(
            "Tabletop Layout", "", "", "", "CLOSED", participant_layout="TABLETOP"
        )
        self.assertTrue(ok, message)
        restored = self.study_service.get_study(study.study_id)
        self.assertEqual(restored.participant_layout, "TABLETOP")

    def test_category_names_are_unique_and_cannot_use_unassigned(self):
        _, _, study = self.study_service.create_study(
            "Safe Categories", "", "", "", "HYBRID"
        )
        theme = self.study_service.add_category_to_study(study.study_id, "Theme")
        other = self.study_service.add_category_to_study(study.study_id, "Other")

        with self.assertRaisesRegex(ValueError, "unique"):
            self.study_service.add_category_to_study(study.study_id, " theme ")
        with self.assertRaisesRegex(ValueError, "reserved"):
            self.study_service.add_category_to_study(study.study_id, "UNASSIGNED")
        with self.assertRaisesRegex(ValueError, "unique"):
            self.study_service.update_category(other, "THEME")
        with self.assertRaisesRegex(ValueError, "reserved"):
            self.study_service.update_category(theme, "unassigned")

    def test_legacy_category_name_is_preserved_for_closed_sort_submission(self):
        _, _, study = self.study_service.create_study(
            "Legacy Categories", "", "", "", "CLOSED"
        )
        legacy_category = Category(
            category_id="cat_legacy",
            study_id=study.study_id,
            name=" Theme ",
            display_order=1,
        )
        self.study_service.cat_repo.save_categories([legacy_category])
        visible_categories = self.study_service.get_categories_for_participants(study.study_id)
        self.assertEqual([category.name for category in visible_categories], [" Theme "])

        card = self.study_service.add_card_to_study(study.study_id, "Legacy Card")
        participant_service = ParticipantService(self.test_db)
        session = participant_service.create_fresh_session(study.study_id)
        code = participant_service.submit_sort(
            session["session_token"],
            study,
            [card],
            {"Unassigned": [], " Theme ": [card.card_id]},
            voice_memo_url="https://drive.example.test/private-memo.wav",
        )
        self.assertRegex(code, r"^[0-9A-F]{4}-[0-9A-F]{4}$")

    def test_restore_skips_duplicate_remote_rows_without_failing(self):
        connection = get_connection(self.test_db)
        state = {
            "tables": {
                "studies": [
                    {
                        "study_id": "std_restore", "token": "duplicate-token", "title": "First",
                        "condition": "CLOSED", "category_order": "RANDOM",
                    },
                    {
                        "study_id": "std_conflict", "token": "duplicate-token", "title": "Second",
                        "condition": "CLOSED", "category_order": "RANDOM",
                    },
                ]
            }
        }
        restored_rows, skipped_rows = _restore_state(connection, state)
        connection.close()

        self.assertEqual(restored_rows, 1)
        self.assertEqual(skipped_rows, 1)
        restored = self.study_service.get_study("std_restore")
        self.assertEqual(restored.title, "First")

    def test_sort_service_movement(self):
        placements = {"Unassigned": ["crd_1", "crd_2"], "Group A": []}
        updated = SortService.move_card(placements, "crd_1", "Group A")
        self.assertIn("crd_1", updated["Group A"])
        self.assertNotIn("crd_1", updated["Unassigned"])

    def test_validation_helpers(self):
        valid, msg = validate_study_meta("A", "HYBRID")
        self.assertFalse(valid)
        
        valid, msg = validate_study_meta("Valid Title", "INVALID_COND")
        self.assertFalse(valid)

    def test_quoted_csv_with_commas_imports_without_rewriting(self):
        valid, message, cards = validate_card_csv(
            b'title,description,example,notes\n"Card A","A description, with a comma",Example,Internal\n'
        )
        self.assertTrue(valid, message)
        self.assertEqual(cards[0]["description"], "A description, with a comma")

    def test_session_cannot_submit_to_a_different_study(self):
        _, _, first_study = self.study_service.create_study(
            "First Study", "", "", "", "HYBRID"
        )
        _, _, second_study = self.study_service.create_study(
            "Second Study", "", "", "", "HYBRID"
        )
        second_card = self.study_service.add_card_to_study(second_study.study_id, "Second Card")
        participant_service = ParticipantService(self.test_db)
        first_session = participant_service.create_fresh_session(first_study.study_id)

        with self.assertRaises(ValueError):
            participant_service.submit_sort(
                first_session["session_token"], second_study, [second_card], {"Unassigned": [second_card.card_id]}
            )

    def test_deleting_study_removes_related_records(self):
        _, _, study = self.study_service.create_study("Delete Me", "", "", "", "HYBRID")
        self.study_service.add_card_to_study(study.study_id, "Temporary Card")
        self.study_service.delete_study(study.study_id)
        self.assertIsNone(self.study_service.get_study(study.study_id))
        self.assertEqual(self.study_service.card_repo.get_cards_for_study(study.study_id), [])

    def test_analysis_uses_stable_card_ids_from_new_submissions(self):
        _, _, study = self.study_service.create_study("Analysis Study", "", "", "", "HYBRID")
        first = self.study_service.add_card_to_study(study.study_id, "First Card")
        second = self.study_service.add_card_to_study(study.study_id, "Second Card")
        participant_service = ParticipantService(self.test_db)
        session = participant_service.create_fresh_session(study.study_id)
        participant_service.submit_sort(
            session["session_token"], study, [first, second], {"Group": [first.card_id, second.card_id]},
            voice_memo_url="https://drive.example.test/private-memo.wav",
        )

        matrix = AnalysisService(self.test_db).get_co_occurrence_matrix(study.study_id, [first, second])
        self.assertEqual(matrix.loc["First Card", "Second Card"], 100.0)

if __name__ == "__main__":
    unittest.main()
