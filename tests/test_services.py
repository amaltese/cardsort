import os
import unittest
from database.db import init_db
from database.models import Study, Card
from services.study_service import StudyService
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
        
        card = self.study_service.add_card_to_study(
            study.study_id,
            title="Lesson Planning",
            description="Designing weekly units"
        )
        self.assertEqual(card.title, "Lesson Planning")
        
        fetched_cards = self.study_service.card_repo.get_cards_for_study(study.study_id)
        self.assertEqual(len(fetched_cards), 1)

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

if __name__ == "__main__":
    unittest.main()