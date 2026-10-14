"""DEC-1112: kill cases for the survivors of items 9 b and 9 c that stand.

Each case passes on the head (872a14d) and fails on its mutant. No case sends a live request.
"""

import contextlib
import json

import tests.test_fetch_other_printings as other_printings
from tests.test_fetch_other_printings import SEARCH_URL, PrintsScryfall, printing
from tests.test_scryfall_fetch import DeckDirCase, FakeScryfall, make_card


class Dec1112KillCases(DeckDirCase):
    run_pass = other_printings.FirstPageProofCases.run_pass

    def test_s1_page_with_an_inversion_of_one_cent_proves_nothing(self):
        """S1 (line 167): 0.49 after 0.50 is out of order, so the page proves nothing."""
        price, out = self.run_pass("Forest", raw_page=[
            printing("Forest", "a", usd="0.50"), printing("Forest", "b", usd="0.49")])
        self.assertIsNone(price)
        self.assertIn(
            "    Forest: the first page does not prove the lowest usd price: no price taken\n", out)

    def test_s4_non_foil_price_of_zero_counts(self):
        """S4 (line 230): a non-foil price of 0.00 is a price, as 0.00 is a key (line 167)."""
        price, out = self.run_pass("Thought Vessel", has_more=False, raw_page=[
            printing("Thought Vessel", "a", usd="0.00"), printing("Thought Vessel", "b", usd="0.05")])
        self.assertEqual(price, 0.0)
        self.assertIn("    Thought Vessel: usd 0.0 from another printing\n", out)

    def test_r1_search_is_a_get_without_a_body(self):
        """R1 (line 189): /cards/search goes out as a GET."""
        self.write_deck("one", "Blood Crypt")
        batch = make_card("Blood Crypt", usd=None, eur=None)
        fake = PrintsScryfall([batch], {batch["oracle_id"]: [
            printing("Blood Crypt", "rna", usd="9.00", eur="7.50")]})

        code, _ = self.run_metadata(fake)

        self.assertEqual(code, 0)
        search = fake.sent[1]
        self.assertTrue(search.url.startswith(SEARCH_URL + "?"))
        self.assertIsNone(search.body)
        self.assertNotIn("content-type", search.headers)

    def test_r4_card_without_top_level_oracle_id_sends_no_oracleid_none_search(self):
        """R4 (line 374): a reversible_card carries its oracle_id on each face only.

        The head ends the run with KeyError: 'oracle_id' before any search; the
        mutant sends ``oracleid:None``. A fix that reads the face's oracle id
        also passes this case."""
        self.write_deck("one", "Blood Crypt")
        card = make_card("Blood Crypt // Blood Crypt", layout="reversible_card", usd=None, eur=None)
        oracle_id = card.pop("oracle_id")
        card["card_faces"] = [{"name": "Blood Crypt", "oracle_id": oracle_id},
                              {"name": "Blood Crypt", "oracle_id": oracle_id}]
        fake = PrintsScryfall([card], {oracle_id: [
            printing("Blood Crypt", "rna", usd="9.00", eur="7.50")]})

        with contextlib.suppress(KeyError):
            self.run_metadata(fake)

        self.assertFalse([s.url for s in fake.sent if "oracleid%3ANone" in s.url])

    def test_r10_two_returned_spellings_join_with_a_semicolon(self):
        """R10 (line 400): card names hold commas, so the names join with "; "."""
        self.write_deck("one", "sol ring", "Lorien Revealed", "Aether Vial")
        fake = FakeScryfall()
        fake.failures[0] = json.dumps({"object": "list", "not_found": [], "data": [
            make_card("Æther Vial"), make_card("Lórien Revealed"), make_card("Sol Ring")]}).encode()

        code, out = self.run_metadata(fake)

        self.assertNotEqual(code, 0)
        self.assertIn(
            "  Scryfall also returned names that match no name asked: "
            "Æther Vial; Lórien Revealed\n", out)
        self.assert_no_file_written()

    def test_r14_non_ascii_name_is_written_as_an_escape(self):
        """R14 (line 437): card-metadata.json keeps json.dump's ASCII escapes, as on main."""
        self.write_deck("one", "Lórien Revealed")
        fake = FakeScryfall([make_card("Lórien Revealed")])

        code, _ = self.run_metadata(fake)

        self.assertEqual(code, 0)
        text = self.output.read_text()
        self.assertIn('"L\\u00f3rien Revealed": {', text)
        self.assertEqual(text, json.dumps(json.loads(text), indent=2, sort_keys=True))
