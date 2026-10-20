"""DEC-1122 fix round 1 (route A): build the expected tests/test_scryfall_callers.py.

Input: the head's file (git show ea4b890:tests/test_scryfall_callers.py, blob 7082ccdd).
It moves the reviewer's four kill files (/tmp/dec1122/kills/test_kill_*.py) into
ComputeTokensTests, in the class's own idiom: methods that use self.write_deck and
self.run_main, and the per-subtest reset of the head's loops. Each edit asserts its anchor.

Usage: python3 build_expected.py <head file> <out file>
"""
import sys
from pathlib import Path

src = Path(sys.argv[1]).read_text()


def insert_after(text: str, anchor: str, new: str) -> str:
    assert text.count(anchor) == 1, (anchor[:60], text.count(anchor))
    return text.replace(anchor, anchor + new)


# 1. The import for IncompleteRead.
src = insert_after(src, "import csv\n", "import http.client\n")

# 2. B1 (R1): three read failures join the failed-request case.
src = insert_after(src, '''            "not JSON": (b"<html>bad gateway</html>",
                         "JSONDecodeError: Expecting value: line 1 column 1 (char 0)"),
''', '''            # urllib wraps a failure in a URLError only while it sends the request. A
            # failure while it waits for or reads the answer reaches the script raw.
            "read timeout": (TimeoutError("The read operation timed out"),
                             "TimeoutError: The read operation timed out"),
            "connection reset": (ConnectionResetError(54, "Connection reset by peer"),
                                 "ConnectionResetError: [Errno 54] Connection reset by peer"),
            "incomplete answer": (http.client.IncompleteRead(b"{"),
                                  "IncompleteRead: IncompleteRead(1 bytes read)"),
''')

# 3. B3 (R10): a fault that is not a failed request keeps its own exception.
src = insert_after(src, '''        self.assertEqual(code, 1)
        self.assertIn("Scryfall request failed: POST", out)
        self.assertEqual(len(fake.sent), 1)
        self.assertEqual(path.read_text(), before)
''', '''
    def test_deck_entry_without_a_name_is_not_reported_as_a_failed_request(self):
        """main() prints "No file written." for a 429 or a failed request only. Any other
        fault, here a deck entry without a name, leaves main() as its own exception."""
        path = self.write_deck("one", "Sol Ring", "Arcane Signet")
        deck = json.loads(path.read_text())
        deck["decklist"].append({"quantity": 1})
        path.write_text(json.dumps(deck))
        before = path.read_text()
        fake = token_fake()

        with self.assertRaises(KeyError):
            self.run_main(fake)

        self.assertEqual(fake.sent, [])
        self.assertEqual(path.read_text(), before)
''')

# 4. B4 (R11 to R13): the batch reads its answer's fields with defaults, as main did.
src = insert_after(src, '''        self.assertIn("Retrying 1 via fuzzy named lookup...", out)
        self.assertEqual(json.loads(path.read_text())["tokens"], [])
''', '''
    # The batch reads ``data`` and ``not_found`` with defaults. Scryfall's documented answer
    # holds both fields; these cases keep the reading of an answer that lacks one.

    def run_batch_answer(self, answer: dict) -> tuple[int, str, FakeScryfall, list]:
        """Answer the batch of a one-card deck with ``answer``; return the exit code, the
        screen, the fake and the deck's tokens."""
        path = self.write_deck("one", "Goblin Maker")
        fake = token_fake()
        fake.failures[0] = json.dumps(answer).encode()
        code, out = self.run_main(fake)
        return code, out, fake, json.loads(path.read_text())["tokens"]

    def test_batch_answer_without_data_reads_as_no_card(self):
        code, _, fake, tokens = self.run_batch_answer({"object": "list", "not_found": []})
        self.assertEqual(code, 0)
        self.assertEqual([s.url for s in fake.sent], [COLLECTION_URL])
        self.assertEqual(tokens, [])

    def test_batch_answer_without_not_found_reads_as_every_card_found(self):
        goblin_maker = token_fake().by_name["Goblin Maker"]
        code, _, fake, tokens = self.run_batch_answer({"object": "list", "data": [goblin_maker]})
        self.assertEqual(code, 0)
        self.assertEqual([s.url for s in fake.sent], [COLLECTION_URL, GOBLIN_URL])
        self.assertEqual([t["name"] for t in tokens], ["Goblin"])

    def test_not_found_entry_without_a_name_costs_no_fuzzy_lookup(self):
        code, out, fake, tokens = self.run_batch_answer(
            {"object": "list", "data": [], "not_found": [{"set": "abc", "collector_number": "1"}]})
        self.assertEqual(code, 0)
        self.assertNotIn("Retrying", out)
        self.assertEqual([s.url for s in fake.sent], [COLLECTION_URL])
        self.assertEqual(tokens, [])
''')

# 5. B2 (R8 and R17): the order of the front faces in the batch.
src = insert_after(src, '''        self.assertEqual(
            [(t["name"], t["produced_by"]) for t in tokens],
            [("Human", [lovestruck]), ("Human Cleric", [westvale])])
''', '''
    def test_batch_sorts_the_front_faces_by_code_point(self):
        """The batch sorts the front faces, not the full names, and capitals come first.
        "Fire & Ice" sorts before "Fire // Ice" but after "Fire"; "Lord Windgrace" sorts
        before "Lord of the Void" only when case counts."""
        decks = {
            ("Fire // Ice", "Fire & Ice"): ["Fire", "Fire & Ice", "Sol Ring"],
            ("Lord of the Void", "Lord Windgrace"):
                ["Lord Windgrace", "Lord of the Void", "Sol Ring"],
        }
        for names, asked in decks.items():
            with self.subTest(names=names):
                shutil.rmtree(self.commanders, ignore_errors=True)
                self.write_deck("one", "Sol Ring", *names)
                fake = token_fake([
                    make_card(name, layout="adventure" if " // " in name else "normal")
                    for name in names])

                code, _ = self.run_main(fake)

                self.assertEqual(code, 0)
                self.assertEqual([s.url for s in fake.sent], [COLLECTION_URL])
                self.assertEqual(fake.asked_names(), asked)
''')

Path(sys.argv[2]).write_text(src)
print("written", sys.argv[2], len(src.splitlines()), "lines")
