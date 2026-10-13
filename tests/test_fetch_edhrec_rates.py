import importlib
import unittest


fetch_rates = importlib.import_module("scripts.fetch_edhrec_rates")


class EdhrecSlugTests(unittest.TestCase):
    def test_simple_commander(self):
        self.assertEqual(fetch_rates.edhrec_slug("Zada, Hedron Grinder"), "zada-hedron-grinder-NEGATIVE-CONTROL")

    def test_dfc_uses_front_face(self):
        self.assertEqual(
            fetch_rates.edhrec_slug("Tony Stark // The Invincible Iron Man"), "tony-stark"
        )

    def test_accents_and_apostrophes_stripped(self):
        self.assertEqual(fetch_rates.edhrec_slug("Ghired's Belligerence"), "ghireds-belligerence")
        self.assertEqual(fetch_rates.edhrec_slug("Jhoira, Weatherlight Captain"), "jhoira-weatherlight-captain")

    def test_slug_candidates_dfc_fallback(self):
        cands = fetch_rates.slug_candidates("Tony Stark // The Invincible Iron Man")
        self.assertEqual(cands[0], "tony-stark")
        self.assertEqual(cands[1], "tony-stark-the-invincible-iron-man")

    def test_slug_candidates_single_face(self):
        self.assertEqual(fetch_rates.slug_candidates("Sol Ring"), ["sol-ring"])


class ExtractRatesTests(unittest.TestCase):
    def _page(self, cardviews):
        return {"container": {"json_dict": {"cardlists": [{"header": "x", "cardviews": cardviews}]}}}

    def test_rate_from_num_and_potential(self):
        page = self._page([{"name": "Buster Sword", "num_decks": 431, "potential_decks": 1000}])
        self.assertEqual(fetch_rates.extract_rates(page), {"Buster Sword": 43.1})

    def test_rate_falls_back_to_inclusion_field_then_label(self):
        page = self._page(
            [
                {"name": "A", "inclusion": 50, "potential_decks": 200},
                {"name": "B", "label": "17% of 900 decks"},
            ]
        )
        self.assertEqual(fetch_rates.extract_rates(page), {"A": 25.0, "B": 17.0})

    def test_dfc_names_collapse_to_front_face_max(self):
        page = self._page(
            [
                {"name": "Card // Back", "num_decks": 10, "potential_decks": 100},
                {"name": "Card", "num_decks": 30, "potential_decks": 100},
            ]
        )
        self.assertEqual(fetch_rates.extract_rates(page), {"Card": 30.0})

    def test_unparseable_entries_skipped_and_rates_clamped(self):
        page = self._page(
            [
                {"name": "NoData"},
                {"num_decks": 5, "potential_decks": 10},
                {"name": "Over", "num_decks": 150, "potential_decks": 100},
            ]
        )
        self.assertEqual(fetch_rates.extract_rates(page), {"Over": 100.0})


if __name__ == "__main__":
    unittest.main()
