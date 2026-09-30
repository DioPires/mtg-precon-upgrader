import importlib
import json
import random
import tempfile
import unittest
from collections import Counter, defaultdict
from pathlib import Path
from unittest.mock import patch


exporter = importlib.import_module("scripts.export_simulation_results")


class ExportSimulationResultsHelperTests(unittest.TestCase):
    def test_resolve_decks_defaults_to_all(self):
        resolved = exporter.resolve_decks(None)
        self.assertEqual([deck_id for deck_id, _, _ in resolved],
                         [deck_id for deck_id, _, _ in exporter.DECKS])

    def test_resolve_decks_preserves_canonical_order(self):
        resolved = exporter.resolve_decks(["gathering-shadow", "titan-convergence"])
        self.assertEqual([deck_id for deck_id, _, _ in resolved],
                         ["titan-convergence", "gathering-shadow"])

    def test_output_path_for_default_location(self):
        path = exporter.output_path_for("gathering-shadow", None)
        expected = exporter.PROJECT_ROOT / "data" / "commanders" / "gathering-shadow" / "simulation.json"
        self.assertEqual(path, expected)

    def test_output_path_for_custom_directory(self):
        base = Path("/tmp/sim-exports")
        path = exporter.output_path_for("gathering-shadow", base)
        self.assertEqual(path, base / "gathering-shadow" / "simulation.json")

    def test_export_selected_decks_writes_output_on_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            result = {"metadata": {"ok": True}}
            selected = [("gathering-shadow", "Gathering Shadow", lambda _: result)]

            with patch("builtins.print"), patch.object(exporter, "validate_output", return_value=True):
                failures = exporter.export_selected_decks({}, selected, output_dir)

            self.assertEqual(failures, 0)
            path = output_dir / "gathering-shadow" / "simulation.json"
            self.assertTrue(path.exists())
            self.assertEqual(json.loads(path.read_text()), result)

    def test_export_selected_decks_counts_validation_failures(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            selected = [("gathering-shadow", "Gathering Shadow", lambda _: {"metadata": {"ok": True}})]

            with patch("builtins.print"), patch.object(exporter, "validate_output", return_value=False):
                failures = exporter.export_selected_decks({}, selected, output_dir)

            self.assertEqual(failures, 1)
            self.assertFalse((output_dir / "gathering-shadow" / "simulation.json").exists())

    def test_export_selected_decks_counts_exceptions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            def boom(_):
                raise RuntimeError("broken export")

            selected = [("gathering-shadow", "Gathering Shadow", boom)]
            with patch("builtins.print"), patch.object(exporter.traceback, "print_exc"):
                failures = exporter.export_selected_decks({}, selected, output_dir)

            self.assertEqual(failures, 1)


class CopyEngineHelperTests(unittest.TestCase):
    """DEC-393 — commander copy-trigger engine helpers."""

    def test_targets_only_creatures_accepts_single_creature_target(self):
        self.assertTrue(exporter.targets_only_creatures(
            {"oracle_text": "Target creature gains haste until end of turn.\nDraw a card."}))
        self.assertTrue(exporter.targets_only_creatures(
            {"oracle_text": "Create a Role token attached to up to one target creature you control."}))

    def test_targets_only_creatures_rejects_other_target_types(self):
        for oracle in (
            "Copy target instant or sorcery spell. You may choose new targets for the copy.",
            "Grapeshot deals 1 damage to any target.",
            "Choose target opponent.",
            "The owner of target permanent shuffles it into their library.",
            "Create two 1/1 red Goblin creature tokens.",  # no target at all
            "Up to two target creatures each get +2/+0.",  # plural targeting
        ):
            self.assertFalse(exporter.targets_only_creatures({"oracle_text": oracle}), oracle)

    def test_creature_token_count_fixed_counts(self):
        self.assertEqual(exporter.creature_token_count(
            {"oracle_text": "Create two 1/1 red Goblin creature tokens."}), 2)
        self.assertEqual(exporter.creature_token_count(
            {"oracle_text": "When this artifact enters, create a 1/1 white Spirit creature token with flying."}), 1)
        # Granted-ability quote must not hide the create clause.
        self.assertEqual(exporter.creature_token_count(
            {"oracle_text": 'Create a 0/1 black Wizard creature token with "Whenever you cast a noncreature spell, this token deals 1 damage to each opponent."'}), 1)

    def test_creature_token_count_skips_variable_triggered_and_activated(self):
        for oracle in (
            "Create X 1/1 white Warrior creature tokens.",
            "Then create a 1/1 white Monk creature token with prowess for each rally counter on it.",
            "Whenever a Goblin you control dies, create a 1/1 red Goblin creature token.",
            "{3}{R}, Sacrifice a Goblin: Create two 1/1 red Goblin creature tokens.",
            "Create a Treasure token.",  # not a creature token
        ):
            self.assertEqual(exporter.creature_token_count({"oracle_text": oracle}), 0, oracle)

    def test_copy_engine_per_other_creature_counts_others(self):
        engine = exporter.COMMANDER_COPY_ENGINE["zada-hedron-grinder"]
        profile = {"targetsOnlyCreature": True}
        # 5 creatures incl. the commander -> 4 copies.
        self.assertEqual(exporter.copy_engine_copy_count(engine, profile, 5, 0), 4)
        # Commander alone -> no copies; non-qualifying spell -> no copies.
        self.assertEqual(exporter.copy_engine_copy_count(engine, profile, 1, 0), 0)
        self.assertEqual(exporter.copy_engine_copy_count(
            engine, {"targetsOnlyCreature": False}, 5, 0), 0)

    def test_copy_engine_tap_gate_throttles_per_turn(self):
        engine = {"mode": "tap_gate", "tapCost": 3}
        profile = {"targetsOnlyCreature": False}
        # 7 creatures: first two casts copy (3+3 tapped), third finds only 1 untapped.
        self.assertEqual(exporter.copy_engine_copy_count(engine, profile, 7, 0), 1)
        self.assertEqual(exporter.copy_engine_copy_count(engine, profile, 7, 1), 1)
        self.assertEqual(exporter.copy_engine_copy_count(engine, profile, 7, 2), 0)
        # Below the gate entirely.
        self.assertEqual(exporter.copy_engine_copy_count(engine, profile, 2, 0), 0)


class HatchEngineHelperTests(unittest.TestCase):
    """DEC-938 — pure helpers behind the hatch engine and team-haste rule."""

    ENGINE = exporter.COMMANDER_HATCH_ENGINE["broodfire-hatchery"]
    HASTE = exporter.COMMANDER_HASTE_SOURCES["broodfire-hatchery"]

    @staticmethod
    def _board(*names):
        return [{"name": name, "combat": 0, "combatReadyTurn": 99} for name in names]

    def test_egg_multiplier_doubles_per_token_doubler(self):
        self.assertEqual(exporter.hatch_egg_multiplier(self.ENGINE, self._board()), 1)
        self.assertEqual(exporter.hatch_egg_multiplier(
            self.ENGINE, self._board("Mondrak, Glory Dominus")), 2)
        self.assertEqual(exporter.hatch_egg_multiplier(
            self.ENGINE, self._board("Mondrak, Glory Dominus",
                                     "Elspeth, Storm Slayer")), 4)

    def test_entry_eggs_double_on_elesh_norn_then_on_token_doublers(self):
        hatcher = "Palani's Hatcher"
        self.assertEqual(exporter.hatch_entry_eggs(
            self.ENGINE, hatcher, self._board(hatcher)), 2)
        # Elesh Norn doubles the ETB trigger itself: two triggers, two Eggs each.
        self.assertEqual(exporter.hatch_entry_eggs(
            self.ENGINE, hatcher,
            self._board(hatcher, "Elesh Norn, Mother of Machines")), 4)
        # ...and the token doublers then multiply the tokens created.
        self.assertEqual(exporter.hatch_entry_eggs(
            self.ENGINE, hatcher,
            self._board(hatcher, "Elesh Norn, Mother of Machines",
                        "Mondrak, Glory Dominus")), 8)
        self.assertEqual(exporter.hatch_entry_eggs(
            self.ENGINE, "Nesting Dragon", self._board("Nesting Dragon")), 0)

    def test_team_haste_needs_a_source_or_a_complete_pair(self):
        self.assertFalse(exporter.team_haste_active(self.HASTE, self._board()))
        self.assertTrue(exporter.team_haste_active(
            self.HASTE, self._board("Rhythm of the Wild")))
        # Palani's Hatcher only hastes other Dinosaurs — Maskwood Nexus is the
        # other half of the pair.
        self.assertFalse(exporter.team_haste_active(
            self.HASTE, self._board("Palani's Hatcher")))
        self.assertFalse(exporter.team_haste_active(
            self.HASTE, self._board("Maskwood Nexus")))
        self.assertTrue(exporter.team_haste_active(
            self.HASTE, self._board("Palani's Hatcher", "Maskwood Nexus")))

    def test_static_haste_excludes_entry_gated_riot(self):
        # Rhythm's riot applies only as a creature enters, so it is not a
        # continuous grant a permanent already on the battlefield can read.
        self.assertFalse(exporter.static_haste_active(
            self.HASTE, self._board("Rhythm of the Wild")))
        for name in ("Samut, Hazoret's Champion", "Rising of the Day"):
            self.assertTrue(exporter.static_haste_active(
                self.HASTE, self._board(name)), name)
        self.assertTrue(exporter.static_haste_active(
            self.HASTE, self._board("Palani's Hatcher", "Maskwood Nexus")))

    def test_set_entry_ready_turn_only_pulls_readiness_forward(self):
        permanents = [{"name": "Bear", "combat": 3, "combatReadyTurn": 5}]
        exporter.set_entry_ready_turn(permanents, "Bear", 4)
        self.assertEqual(permanents[0]["combatReadyTurn"], 4)
        exporter.set_entry_ready_turn(permanents, "Bear", 7)
        self.assertEqual(permanents[0]["combatReadyTurn"], 4)
        # Non-combat permanents are untouched.
        rock = [{"name": "Rock", "combat": 0, "combatReadyTurn": 99}]
        exporter.set_entry_ready_turn(rock, "Rock", 3)
        self.assertEqual(rock[0]["combatReadyTurn"], 99)

    def test_hatch_puts_one_creature_and_bottoms_the_rest(self):
        profiles = {
            "Rock": {"typeLine": "Artifact", "isPermanent": True, "landRamp": None,
                     "manaAtoms": [], "manaSourceDelay": None, "immediateDraw": 0,
                     "impact": 1, "combat": 0, "isThreat": False},
            "Wastes": {"typeLine": "Land", "isPermanent": True, "landRamp": None,
                       "manaAtoms": [], "manaSourceDelay": 0, "immediateDraw": 0,
                       "impact": 0, "combat": 0, "isThreat": False},
            "Bear": {"typeLine": "Creature — Bear", "isPermanent": True,
                     "landRamp": None, "manaAtoms": [], "manaSourceDelay": None,
                     "immediateDraw": 0, "impact": 2, "combat": 2, "isThreat": True},
        }
        # Library bottom -> top; the two cards above the Bear are bottomed.
        library = ["Deep", "Bear", "Wastes", "Rock"]
        permanents, hand, lands = [], [], []
        hatched = exporter.hatch_from_library(
            3, exporter.GoldfishManaPool([]), library, hand, permanents, lands,
            profiles, {}, [])
        self.assertEqual(hatched, "Bear")
        self.assertEqual([p["name"] for p in permanents], ["Bear"])
        self.assertEqual(permanents[0]["combatReadyTurn"], 4)
        self.assertEqual(library, ["Rock", "Wastes", "Deep"])

        # ready_turn pulls the hatch into the current combat (Raph & Mikey).
        library = ["Bear"]
        permanents = []
        exporter.hatch_from_library(
            3, exporter.GoldfishManaPool([]), library, hand, permanents, lands,
            profiles, {}, [], ready_turn=3)
        self.assertEqual(permanents[0]["combatReadyTurn"], 3)

        # A creature-less library hatches nothing and is left intact.
        library = ["Rock", "Wastes"]
        permanents = []
        self.assertIsNone(exporter.hatch_from_library(
            3, exporter.GoldfishManaPool([]), library, hand, permanents, lands,
            profiles, {}, []))
        self.assertEqual(permanents, [])
        self.assertEqual(sorted(library), ["Rock", "Wastes"])


class HatchEngineGoldfishTests(unittest.TestCase):
    """DEC-938 — the hatch engine inside a deterministic goldfish turn loop.

    Synthetic ``broodfire-hatchery`` deck: the engine permanents cost nothing so
    the whole opening hand lands on turn 1, every Bear and Filler costs {9} so
    the goldfish never casts one (Bears exist only to be hatched), and the
    opening hand/library are pinned by patching the mulligan — the only source
    of randomness in ``simulate_goldfish_game``. Each test asserts on the
    ``(turn, ready_turn)`` pairs recorded from every ``hatch_from_library`` call.
    """

    DECK_ID = "broodfire-hatchery"
    COMMANDER = "Atla Palani, Nest Tender"
    FREE_PERMANENTS = {
        "Ashnod's Altar": "Artifact",
        "Goblin Bombardment": "Enchantment",
        "High Market": "Land",
        "Skullclamp": "Artifact — Equipment",
        "Thornbite Staff": "Kindred Artifact — Shaman Equipment",
        "Mondrak, Glory Dominus": "Legendary Creature — Phyrexian Horror",
        "Elspeth, Storm Slayer": "Planeswalker — Elspeth",
        "Annie Joins Up": "Legendary Enchantment",
        "Roaming Throne": "Artifact Creature — Golem",
        "Seedborn Muse": "Creature — Spirit",
        "Palani's Hatcher": "Creature — Dinosaur",
        "Nesting Dragon": "Creature — Dragon",
        "Elesh Norn, Mother of Machines": "Legendary Creature — Phyrexian Praetor",
        "Raph & Mikey, Troublemakers": "Legendary Creature — Mutant Ninja Turtle",
        "Rhythm of the Wild": "Enchantment",
        "Rising of the Day": "Enchantment",
        "Samut, Hazoret's Champion": "Legendary Creature — Human Warrior Cleric",
        "Maskwood Nexus": "Artifact",
    }
    BEARS = [f"Bear {i}" for i in range(40)]
    FILLERS = [f"Filler {i}" for i in range(30)]

    def _metadata(self, commander_cmc: int, pre_commander=()) -> dict:
        metadata = {
            "Forest": {
                "name": "Forest", "type_line": "Basic Land — Forest",
                "oracle_text": "({T}: Add {G}.)", "mana_cost": "", "cmc": 0,
                "colors": [], "color_identity": ["G"], "produced_mana": ["G"],
            },
            "Mana Crystal": {
                "name": "Mana Crystal", "type_line": "Artifact",
                "oracle_text": "{T}: Add {C}.", "mana_cost": "", "cmc": 0,
                "colors": [], "color_identity": [], "produced_mana": ["C"],
            },
            self.COMMANDER: {
                "name": self.COMMANDER,
                "type_line": "Legendary Creature — Human Shaman",
                "oracle_text": "", "mana_cost": "{%d}" % commander_cmc,
                "cmc": commander_cmc, "colors": [], "color_identity": ["G"],
            },
        }
        for name, type_line in self.FREE_PERMANENTS.items():
            metadata[name] = {
                "name": name, "type_line": type_line, "oracle_text": "",
                "mana_cost": "", "cmc": 0, "colors": [], "color_identity": [],
            }
        # High Market must not be a castable spell — it is the land outlet.
        metadata["High Market"]["oracle_text"] = "{T}: Add {C}."
        metadata["High Market"]["produced_mana"] = ["C"]
        # `proactive_cast_priority` casts mana sources before the commander, so
        # naming a card here is the harness knob for "this permanent is already
        # on the battlefield when the commander enters".
        for name in pre_commander:
            metadata[name]["oracle_text"] = "{T}: Add {C}."
            metadata[name]["produced_mana"] = ["C"]
        for name in self.BEARS:
            metadata[name] = {
                "name": name, "type_line": "Creature — Bear", "oracle_text": "",
                "mana_cost": "{9}", "cmc": 9, "colors": [], "color_identity": [],
            }
        for name in self.FILLERS:
            metadata[name] = {
                "name": name, "type_line": "Sorcery", "oracle_text": "",
                "mana_cost": "{9}", "cmc": 9, "colors": [], "color_identity": [],
            }
        return metadata

    def _run(self, engine_cards, commander_cmc=1, crystals=3, forests=6,
             pre_commander=(), extra_lands=()):
        """Run one pinned game; return (hatch calls, by_turn)."""
        metadata = self._metadata(commander_cmc, pre_commander)
        lands = ["Forest"] * forests + list(extra_lands)
        decklist = (lands + ["Mana Crystal"] * crystals
                    + list(self.FREE_PERMANENTS) + self.BEARS + self.FILLERS)
        deck_data = {"decklist": [{"name": name} for name in decklist]}
        context = exporter.build_goldfish_context(
            decklist, deck_data, metadata, self.COMMANDER, ["G"], self.DECK_ID)
        hand = lands + ["Mana Crystal"] * crystals + list(engine_cards)
        # library.pop() draws from the end, so Bears sit on top of the Fillers.
        library = list(self.FILLERS) + list(self.BEARS)

        calls = []
        original = exporter.hatch_from_library

        def recording_hatch(turn, *args, ready_turn=None, **kwargs):
            calls.append((turn, ready_turn))
            return original(turn, *args, ready_turn=ready_turn, **kwargs)

        with patch.object(exporter, "commander_mulligan_goldfish",
                          lambda *_: (list(library), list(hand))), \
                patch.object(exporter, "hatch_from_library", recording_hatch):
            by_turn, _ = exporter.simulate_goldfish_game(
                decklist, metadata, context, 6)
        return calls, by_turn

    @staticmethod
    def _per_turn(calls):
        counts = Counter(turn for turn, _ in calls)
        return {turn: counts[turn] for turn in sorted(counts)}

    def test_no_hatch_without_the_commander(self):
        # Commander at {30} is never affordable inside the 10-turn window.
        calls, _ = self._run(["Ashnod's Altar"], commander_cmc=30)
        self.assertEqual(calls, [])

    def test_no_hatch_without_an_outlet(self):
        calls, _ = self._run([])
        self.assertEqual(calls, [])
        # Skullclamp alone does not open the engine (board scope, DEC-938).
        calls, _ = self._run(["Skullclamp"])
        self.assertEqual(calls, [])

    def test_no_own_turn_hatch_on_the_commanders_cast_turn(self):
        calls, _ = self._run(["Ashnod's Altar"])
        self.assertEqual(min(turn for turn, _ in calls), 2)
        self.assertEqual(self._per_turn(calls)[2], 1)

    def test_static_haste_source_covers_the_commander_retroactively(self):
        # Rising of the Day is continuous ("Creatures you control have haste"),
        # so it readies her even though the goldfish casts her first.
        calls, _ = self._run(["Ashnod's Altar", "Rising of the Day"])
        self.assertEqual(self._per_turn(calls)[1], 1)
        # With haste the hatched creature is combat-ready the turn it entered.
        self.assertEqual(calls[0], (1, 1))

    def test_riot_does_not_ready_the_commander_when_it_enters_after_her(self):
        # Rhythm of the Wild is a replacement effect on entry, so a commander
        # already on the battlefield never gets haste from it.
        calls, _ = self._run(["Ashnod's Altar", "Rhythm of the Wild"])
        self.assertEqual(min(turn for turn, _ in calls), 2)
        # It still hastes creatures that enter later, hatched ones included.
        self.assertEqual(calls[0], (2, 2))

    def test_riot_readies_the_commander_when_it_enters_before_her(self):
        calls, _ = self._run(["Ashnod's Altar", "Rhythm of the Wild"],
                             pre_commander=["Rhythm of the Wild"])
        self.assertEqual(self._per_turn(calls)[1], 1)
        self.assertEqual(calls[0], (1, 1))

    def test_one_egg_per_turn_without_thornbite_and_four_with_it(self):
        base, _ = self._run(["Ashnod's Altar"])
        self.assertEqual(self._per_turn(base)[3], 1)
        # Commander at {4} lands on turn 2, after the Staff — the free attach
        # trigger ("whenever a Shaman enters") is the sim's only equip path.
        staffed, _ = self._run(["Ashnod's Altar", "Thornbite Staff"],
                               commander_cmc=4, crystals=2)
        self.assertEqual(self._per_turn(staffed)[3], 4)
        # Thornbite without Ashnod's Altar has nothing to pay the next
        # activation ({C}{C} off the Egg it just ate), so even with a free
        # unlimited outlet the commander untaps once: one Egg per turn.
        no_altar, _ = self._run(["Goblin Bombardment", "Thornbite Staff"],
                                commander_cmc=4, crystals=2)
        self.assertEqual(self._per_turn(no_altar)[3], 1)

    def test_high_market_is_a_once_per_untap_outlet(self):
        # Only land in the deck, so it is the turn-1 land drop.
        calls, _ = self._run(["High Market", "Mondrak, Glory Dominus"], forests=0)
        # Two Eggs from the doubled activation, but High Market eats one.
        self.assertEqual(self._per_turn(calls)[2], 1)

    def test_token_doublers_multiply_the_eggs(self):
        one, _ = self._run(["Ashnod's Altar"])
        two, _ = self._run(["Ashnod's Altar", "Mondrak, Glory Dominus"])
        four, _ = self._run(["Ashnod's Altar", "Mondrak, Glory Dominus",
                             "Elspeth, Storm Slayer"])
        self.assertEqual(self._per_turn(one)[3], 1)
        self.assertEqual(self._per_turn(two)[3], 2)
        self.assertEqual(self._per_turn(four)[3], 4)

    def test_trigger_doublers_add_one_hatch_per_egg_each(self):
        annie, _ = self._run(["Ashnod's Altar", "Annie Joins Up"])
        both, _ = self._run(["Ashnod's Altar", "Annie Joins Up", "Roaming Throne"])
        self.assertEqual(self._per_turn(annie)[3], 2)
        self.assertEqual(self._per_turn(both)[3], 3)

    def test_hatch_cap_holds_at_eight_per_turn(self):
        calls, _ = self._run(
            ["Ashnod's Altar", "Thornbite Staff", "Mondrak, Glory Dominus",
             "Elspeth, Storm Slayer", "Annie Joins Up", "Roaming Throne",
             "Seedborn Muse"],
            commander_cmc=4, crystals=2)
        per_turn = self._per_turn(calls)
        self.assertTrue(per_turn, "no hatches observed")
        self.assertEqual(max(per_turn.values()), 8)

    def test_seedborn_hatches_are_ready_next_turn_even_under_haste(self):
        calls, _ = self._run(["Ashnod's Altar", "Seedborn Muse",
                              "Rhythm of the Wild"])
        turn_three = [ready for turn, ready in calls if turn == 3]
        # One own-turn Egg (hasted: ready this turn) + three Seedborn Eggs on
        # the opponents' untap steps (ready next turn regardless of haste).
        self.assertEqual(turn_three, [3, None, None, None])

    def test_palanis_hatcher_entry_eggs_and_nesting_dragon_landfall(self):
        hatcher, _ = self._run(["Ashnod's Altar", "Palani's Hatcher"],
                               commander_cmc=4, crystals=2)
        # Turn 2 the commander lands; the Hatcher's two entry Eggs from turn 1
        # are still on the board and her dies-trigger converts them at once.
        self.assertEqual(self._per_turn(hatcher)[2], 2)
        dragon, _ = self._run(["Ashnod's Altar", "Nesting Dragon"])
        # Nesting Dragon lands turn 1; its landfall Egg starts turn 2 and adds
        # one Egg per land drop on top of the commander's activation.
        self.assertEqual(self._per_turn(dragon)[3], 2)

    def test_skullclamp_cannot_eat_nesting_dragons_0_2_eggs(self):
        # High Market is the whole land base so every land drop is an outlet
        # land; Mondrak doubles both Egg streams so supply outruns capacity.
        calls, _ = self._run(
            ["Nesting Dragon", "Skullclamp", "Mondrak, Glory Dominus"],
            forests=0, extra_lands=["High Market"] * 4)
        # Turn 2: two 0/1 Eggs from the doubled activation and two 0/2 Dragon
        # Eggs from landfall. Skullclamp's +1/-1 kills only the 0/1s (two
        # equips at {1}), then High Market eats one 0/2 — three hatches, not
        # the four the Clamp would reach if it could equip a 0/2.
        self.assertEqual(self._per_turn(calls)[2], 3)

    def test_raph_and_mikey_hatch_at_combat_ready_to_attack(self):
        calls, _ = self._run(["Raph & Mikey, Troublemakers"])
        # No commander gate and no outlet needed — the attack trigger stands
        # alone, and printed haste makes them ready the turn they enter.
        self.assertEqual(calls[0], (1, 1))
        self.assertEqual(self._per_turn(calls)[1], 1)
        annie, _ = self._run(["Raph & Mikey, Troublemakers", "Annie Joins Up"])
        self.assertEqual(self._per_turn(annie)[1], 2)


class GoldfishManaSpendTests(unittest.TestCase):
    """DEC-937 — mana is spent once per turn, not rebuilt per cast.

    Synthetic deck: 40 Forest + 59 identical {1}{G} two-drops (one of which is
    the commander). No ramp, so end-of-turn ``availableMana`` equals the size of
    the pool the casts were paid from, which makes the ceiling exact:
    ``2 * casts <= availableMana``. Before the fix the turn pool was rebuilt
    from every active source on each pass of the cast loop, so two lands on
    turn 2 paid for as many two-drops as the hand held.
    """

    GAMES = 120
    SEED = 11

    @staticmethod
    def _synthetic_deck():
        forest = {
            "name": "Forest", "type_line": "Basic Land — Forest",
            "oracle_text": "({T}: Add {G}.)", "mana_cost": "", "cmc": 0,
            "colors": [], "color_identity": ["G"], "produced_mana": ["G"],
        }
        decklist = ["Forest"] * 40 + [f"Bear {i}" for i in range(1, 60)]
        metadata = {"Forest": forest}
        for i in range(1, 60):
            metadata[f"Bear {i}"] = {
                "name": f"Bear {i}", "type_line": "Creature — Bear",
                "oracle_text": "", "mana_cost": "{1}{G}", "cmc": 2,
                "colors": ["G"], "color_identity": ["G"],
            }
        deck_data = {"decklist": [{"name": name} for name in decklist]}
        context = exporter.build_goldfish_context(
            decklist, deck_data, metadata, "Bear 1", ["G"], "synthetic-two-drops")
        return decklist, metadata, context

    def _casts_by_mana(self):
        """Run GAMES goldfish games; return {availableMana: [casts that turn]}."""
        decklist, metadata, context = self._synthetic_deck()
        casts_this_turn = Counter()
        original = exporter.resolve_cast_effects

        def counting_resolve(name, profile, turn, pool, *args, **kwargs):
            casts_this_turn[turn] += 1
            return original(name, profile, turn, pool, *args, **kwargs)

        by_mana = defaultdict(list)
        with patch.object(exporter, "resolve_cast_effects", counting_resolve):
            random.seed(self.SEED)
            for _ in range(self.GAMES):
                casts_this_turn.clear()
                by_turn, _ = exporter.simulate_goldfish_game(
                    decklist, metadata, context, 6)
                for turn in range(1, exporter.NUM_TURNS + 1):
                    by_mana[by_turn[turn]["availableMana"]].append(casts_this_turn[turn])
        return by_mana

    def test_casts_never_exceed_the_turn_pool(self):
        by_mana = self._casts_by_mana()
        self.assertTrue(by_mana, "no goldfish turns observed")
        for mana, casts in sorted(by_mana.items()):
            self.assertLessEqual(
                2 * max(casts), mana,
                f"{max(casts)} two-drops cast on a turn with {mana} mana available")

    def test_two_lands_cast_one_two_drop_and_four_lands_cast_two(self):
        by_mana = self._casts_by_mana()
        self.assertIn(2, by_mana, "no two-mana turn observed")
        self.assertIn(4, by_mana, "no four-mana turn observed")
        self.assertEqual(max(by_mana[2]), 1)
        self.assertEqual(max(by_mana[4]), 2)
