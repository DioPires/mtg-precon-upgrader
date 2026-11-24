import gc
import importlib
import itertools
import json
import random
import re
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
        # Surrak and Goreclaw hastes creatures only as they enter (DEC-935
        # round 5), so it is entry-gated like riot.
        self.assertFalse(exporter.static_haste_active(
            self.HASTE, self._board("Surrak and Goreclaw")))
        # The static-name path is tested on a local copy of the config: the
        # live broodfire config has no static anthem since DEC-935 round 6.
        haste = dict(self.HASTE, staticNames={"Rising of the Day"})
        self.assertTrue(exporter.static_haste_active(
            haste, self._board("Rising of the Day")))
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
        no_mana = {"landRamp": None, "manaAtoms": [], "manaOnce": [], "manaBoard": [],
                   "manaOnCast": [], "manaSourceDelay": None, "immediateDraw": 0,
                   "landFetch": None, "imprint": None, "manaOneColour": False,
                   "landGrant": None, "landCrack": None, "manaTurns": None}
        profiles = {
            "Rock": {"typeLine": "Artifact", "isPermanent": True, **no_mana,
                     "impact": 1, "combat": 0, "isThreat": False},
            "Wastes": {"typeLine": "Land", "isPermanent": True, **no_mana,
                       "impact": 0, "combat": 0, "isThreat": False},
            "Bear": {"typeLine": "Creature — Bear", "isPermanent": True, **no_mana,
                     "impact": 2, "combat": 2, "isThreat": True},
        }
        # Library bottom -> top; the two cards above the Bear are bottomed.
        library = ["Deep", "Bear", "Wastes", "Rock"]
        permanents, hand, lands = [], [], []
        hatched = exporter.hatch_from_library(
            3, exporter.GoldfishManaPool([]), library, hand, permanents, lands,
            profiles, [])
        self.assertEqual(hatched, "Bear")
        self.assertEqual([p["name"] for p in permanents], ["Bear"])
        self.assertEqual(permanents[0]["combatReadyTurn"], 4)
        self.assertEqual(library, ["Rock", "Wastes", "Deep"])

        # ready_turn pulls the hatch into the current combat (Raph & Mikey).
        library = ["Bear"]
        permanents = []
        exporter.hatch_from_library(
            3, exporter.GoldfishManaPool([]), library, hand, permanents, lands,
            profiles, [], ready_turn=3)
        self.assertEqual(permanents[0]["combatReadyTurn"], 3)

        # A creature-less library hatches nothing and is left intact.
        library = ["Rock", "Wastes"]
        permanents = []
        self.assertIsNone(exporter.hatch_from_library(
            3, exporter.GoldfishManaPool([]), library, hand, permanents, lands,
            profiles, []))
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
        # DEC-940 — extra combat phase, for the per-combat hatch trigger test.
        "Aurelia, the Warleader": "Legendary Creature — Angel",
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
                "oracle_text": "{T}: Add {C}.", "mana_cost": "{0}", "cmc": 0,
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
                "mana_cost": "" if "Land" in type_line else "{0}", "cmc": 0, "colors": [],
                "color_identity": [],
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
                decklist, context, 6)
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
        # so it readies her even though the goldfish casts her first. The live
        # broodfire config has no static anthem since DEC-935 round 6, so the
        # static path is tested on a local copy of the config.
        haste = dict(exporter.COMMANDER_HASTE_SOURCES[self.DECK_ID],
                     staticNames={"Rising of the Day"})
        with patch.dict(exporter.COMMANDER_HASTE_SOURCES, {self.DECK_ID: haste}):
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

    def test_raph_and_mikey_hatch_again_in_each_extra_combat(self):
        """DEC-940 — the per-combat hatch trigger fires at every combat phase."""
        base, _ = self._run(["Raph & Mikey, Troublemakers"])
        self.assertEqual(self._per_turn(base)[2], 1)
        # Aurelia adds a second combat phase, so the attack trigger fires twice.
        extra, _ = self._run(["Raph & Mikey, Troublemakers",
                              "Aurelia, the Warleader"])
        self.assertEqual(self._per_turn(extra)[2], 2)


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
                    decklist, context, 6)
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


class CombatPhaseDamageTests(unittest.TestCase):
    """DEC-940 — the power multipliers inside one combat phase."""

    MODS = exporter.COMBAT_MODIFIERS["broodfire-hatchery"]
    ZOPANDREL = "Zopandrel, Hunger Dominus"
    XENAGOS = "Xenagos, God of Revels"
    RAPHAEL = "Raphael, the Nightwatcher"

    @staticmethod
    def _att(name, combat, entry_phase=None):
        record = {"name": name, "combat": combat, "combatReadyTurn": 1}
        if entry_phase is not None:
            record["combatEntryPhase"] = entry_phase
        return record

    def test_unconfigured_deck_gets_the_plain_sum(self):
        attackers = [self._att("A", 3), self._att("B", 5)]
        self.assertEqual(
            exporter.combat_phase_damage(attackers, None, set(), 0), 8)
        # Configured deck, none of the modifier permanents on the battlefield.
        self.assertEqual(
            exporter.combat_phase_damage(attackers, self.MODS, {"Forest"}, 0), 8)
        self.assertEqual(
            exporter.combat_phase_damage([], self.MODS, {self.RAPHAEL}, 0), 0)

    def test_zopandrel_compounds_once_per_beginning_of_combat(self):
        attackers = [self._att("A", 3), self._att("B", 5)]
        board = {self.ZOPANDREL}
        self.assertEqual(
            exporter.combat_phase_damage(attackers, self.MODS, board, 0), 16)
        self.assertEqual(
            exporter.combat_phase_damage(attackers, self.MODS, board, 1), 32)
        self.assertEqual(
            exporter.combat_phase_damage(attackers, self.MODS, board, 2), 64)

    def test_zopandrel_only_doubles_triggers_a_creature_was_present_for(self):
        # Hatched during the second combat phase: no doubling that phase, one
        # doubling at the next beginning of combat.
        attackers = [self._att("A", 3), self._att("Hatched", 4, entry_phase=1)]
        board = {self.ZOPANDREL}
        self.assertEqual(
            exporter.combat_phase_damage(attackers, self.MODS, board, 1),
            3 * 4 + 4)
        self.assertEqual(
            exporter.combat_phase_damage(attackers, self.MODS, board, 2),
            3 * 8 + 4 * 2)

    def test_xenagos_doubles_only_the_single_largest_attacker(self):
        attackers = [self._att("A", 3), self._att("B", 5), self._att("C", 2)]
        self.assertEqual(
            exporter.combat_phase_damage(attackers, self.MODS, {self.XENAGOS}, 0),
            3 + 10 + 2)

    def test_xenagos_cannot_target_itself(self):
        # "another target creature you control" — the God is the biggest body
        # on the board but pumps the next-largest attacker instead.
        attackers = [self._att(self.XENAGOS, 9), self._att("A", 3),
                     self._att("B", 2)]
        self.assertEqual(
            exporter.combat_phase_damage(attackers, self.MODS, {self.XENAGOS}, 0),
            9 + 6 + 2)

    def test_xenagos_cannot_target_a_creature_hatched_in_response(self):
        # The hatch resolves after the beginning-of-combat trigger is already on
        # the stack, so the fresh body is not a legal target this phase.
        attackers = [self._att("A", 3), self._att("Hatched", 9, entry_phase=1)]
        board = {self.XENAGOS}
        self.assertEqual(
            exporter.combat_phase_damage(attackers, self.MODS, board, 1),
            3 * 2 + 9)
        # From the next combat phase it is a legal target again.
        self.assertEqual(
            exporter.combat_phase_damage(attackers, self.MODS, board, 2),
            3 + 9 * 2)

    def test_raphael_doubles_the_whole_phase(self):
        attackers = [self._att("A", 3), self._att("B", 5)]
        self.assertEqual(
            exporter.combat_phase_damage(attackers, self.MODS, {self.RAPHAEL}, 0),
            16)

    def test_multipliers_stack_in_zopandrel_xenagos_raphael_order(self):
        attackers = [self._att("A", 2), self._att("B", 3)]
        board = {self.ZOPANDREL, self.XENAGOS, self.RAPHAEL}
        # Zopandrel -> [4, 6]; Xenagos doubles the 6 -> [4, 12]; Raphael x2.
        self.assertEqual(
            exporter.combat_phase_damage(attackers, self.MODS, board, 0), 32)


class PrintedPowerProfileTests(unittest.TestCase):
    """DEC-940 — printed power reaches the profile without touching the proxy."""

    def _profile(self, **meta):
        base = {"type_line": "Creature — Bear", "oracle_text": "",
                "mana_cost": "{3}", "cmc": 3, "colors": ["G"]}
        base.update(meta)
        return exporter.build_goldfish_profile(
            name="Bear", meta=base, category_names=set(),
            commander_colors=["G"], commander_name="Other")

    def test_printed_power_is_parsed_and_defaults_to_zero(self):
        self.assertEqual(self._profile(power="7")["printedPower"], 7)
        self.assertEqual(self._profile(power="0")["printedPower"], 0)
        # No printed power (non-creature) and unfixed power both read 0.
        self.assertEqual(self._profile()["printedPower"], 0)
        self.assertEqual(self._profile(power=None)["printedPower"], 0)
        self.assertEqual(self._profile(power="*")["printedPower"], 0)
        self.assertEqual(self._profile(power="1+*")["printedPower"], 0)

    def test_printed_power_does_not_change_the_combat_proxy(self):
        # The proxy stays min(8, MV) + keyword bonus whatever the printed power.
        for power in (None, "0", "7", "15"):
            with self.subTest(power=power):
                self.assertEqual(self._profile(power=power)["combat"], 3)


# Card data for CastTimeDrawTests, DrawEngineGoldfishTests, XSpellGoldfishTests,
# ArmyReadinessGoldfishTests and TokenMakerGoldfishTests: type line, mana
# cost, mana value and oracle text as data/card-metadata.json held them on
# 2026-11-18, pasted so these
# tests stay put when that file is refreshed or a deck drops a card. "−" in
# loyalty costs is U+2212, as Scryfall prints it. "Zero Trinket" and "Probe
# Commander" are made-up cards for the engine fixture.
CARDS = {
    "Island": {
        "type_line": "Basic Land — Island",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": "({T}: Add {U}.)",
        "colors": [],
    },
    "Swamp": {
        "type_line": "Basic Land — Swamp",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": "({T}: Add {B}.)",
        "colors": [],
    },
    "Forest": {
        "type_line": "Basic Land — Forest",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": "({T}: Add {G}.)",
        "colors": [],
    },
    "Mountain": {
        "type_line": "Basic Land — Mountain",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": "({T}: Add {R}.)",
        "colors": [],
    },
    "Command Tower": {
        "type_line": "Land",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": (
            "{T}: Add one mana of any color in your commander's color "
            "identity."),
        "colors": [],
    },
    "The Ur-Dragon": {
        "type_line": "Legendary Creature — Dragon Avatar",
        "mana_cost": "{4}{W}{U}{B}{R}{G}",
        "cmc": 9.0,
        "oracle_text": (
            "Eminence — As long as The Ur-Dragon is in the command zone or on "
            "the battlefield, other Dragon spells you cast cost {1} less to "
            "cast.\n"
            "Flying\n"
            "Whenever one or more Dragons you control attack, draw that many "
            "cards, then you may put a permanent card from your hand onto the "
            "battlefield."),
        "colors": ["B", "G", "R", "U", "W"],
        "power": "10",
    },
    "The Theorist, Jace Beleren": {
        "type_line": "Legendary Planeswalker — Jace",
        "mana_cost": "{2}{U}{U}",
        "cmc": 4.0,
        "oracle_text": (
            "At the beginning of each opponent's draw step, you draw a card.\n"
            "+1: Create a 1/1 blue Illusion creature token.\n"
            "−2: For each opponent, return up to one target artifact or "
            "creature that player controls to its owner's hand.\n"
            "−6: Draw three cards. Then put X +1/+1 counters on each creature "
            "you control, where X is the number of cards in your hand."),
        "colors": ["U"],
    },
    "The One Ring": {
        "type_line": "Legendary Artifact",
        "mana_cost": "{4}",
        "cmc": 4.0,
        "oracle_text": (
            "Indestructible\n"
            "When The One Ring enters, if you cast it, you gain protection "
            "from everything until your next turn.\n"
            "At the beginning of your upkeep, you lose 1 life for each burden "
            "counter on The One Ring.\n"
            "{T}: Put a burden counter on The One Ring, then draw a card for "
            "each burden counter on The One Ring."),
        "colors": [],
    },
    "Azami, Lady of Scrolls": {
        "type_line": "Legendary Creature — Human Wizard",
        "mana_cost": "{2}{U}{U}{U}",
        "cmc": 5.0,
        "oracle_text": "Tap an untapped Wizard you control: Draw a card.",
        "colors": ["U"],
        "power": "0",
    },
    "Call of the Ring": {
        "type_line": "Enchantment",
        "mana_cost": "{1}{B}",
        "cmc": 2.0,
        "oracle_text": (
            "At the beginning of your upkeep, the Ring tempts you.\n"
            "Whenever you choose a creature as your Ring-bearer, you may pay "
            "2 life. If you do, draw a card."),
        "colors": ["B"],
    },
    "Long River's Pull": {
        "type_line": "Instant",
        "mana_cost": "{U}{U}",
        "cmc": 2.0,
        "oracle_text": (
            "Gift a card (You may promise an opponent a gift as you cast this "
            "spell. If you do, they draw a card before its other effects.)\n"
            "Counter target creature spell. If the gift was promised, instead "
            "counter target spell."),
        "colors": ["U"],
    },
    "Mind Stone": {
        "type_line": "Artifact",
        "mana_cost": "{2}",
        "cmc": 2.0,
        "oracle_text": (
            "{T}: Add {C}.\n"
            "{1}, {T}, Sacrifice this artifact: Draw a card."),
        "colors": [],
    },
    "Hedron Archive": {
        "type_line": "Artifact",
        "mana_cost": "{4}",
        "cmc": 4.0,
        "oracle_text": (
            "{T}: Add {C}{C}.\n"
            "{2}, {T}, Sacrifice this artifact: Draw two cards."),
        "colors": [],
    },
    "Commander's Sphere": {
        "type_line": "Artifact",
        "mana_cost": "{3}",
        "cmc": 3.0,
        "oracle_text": (
            "{T}: Add one mana of any color in your commander's color "
            "identity.\n"
            "Sacrifice this artifact: Draw a card."),
        "colors": [],
    },
    "Ozolith, the Shattered Spire": {
        "type_line": "Legendary Artifact",
        "mana_cost": "{1}{G}",
        "cmc": 2.0,
        "oracle_text": (
            "If one or more +1/+1 counters would be put on an artifact or "
            "creature you control, that many plus one +1/+1 counters are put "
            "on it instead.\n"
            "{1}{G}, {T}: Put a +1/+1 counter on target artifact or creature "
            "you control. Activate only as a sorcery.\n"
            "Cycling {2} ({2}, Discard this card: Draw a card.)"),
        "colors": ["G"],
    },
    "Sauron, the Dark Lord": {
        "type_line": "Legendary Creature — Avatar Horror",
        "mana_cost": "{3}{U}{B}{R}",
        "cmc": 6.0,
        "oracle_text": (
            "Ward—Sacrifice a legendary artifact or legendary creature.\n"
            "Whenever an opponent casts a spell, amass Orcs 1.\n"
            "Whenever an Army you control deals combat damage to a player, "
            "the Ring tempts you.\n"
            "Whenever the Ring tempts you, you may discard your hand. If you "
            "do, draw four cards."),
        "colors": ["B", "R", "U"],
        "power": "7",
    },
    "Belladonna Took": {
        "type_line": "Legendary Creature — Halfling Citizen",
        "mana_cost": "{1}{W}",
        "cmc": 2.0,
        "oracle_text": (
            "Whenever a token you control enters, you gain 1 life if this is "
            "the first time this ability has resolved this turn. If it's the "
            "second time, draw a card. If it's the third time, put a +1/+1 "
            "counter on each creature you control."),
        "colors": ["W"],
        "power": "2",
    },
    "Braids, Arisen Nightmare": {
        "type_line": "Legendary Creature — Nightmare",
        "mana_cost": "{1}{B}{B}",
        "cmc": 3.0,
        "oracle_text": (
            "At the beginning of your end step, you may sacrifice an "
            "artifact, creature, enchantment, land, or planeswalker. If you "
            "do, each opponent may sacrifice a permanent of their choice that "
            "shares a card type with it. For each opponent who doesn't, that "
            "player loses 2 life and you draw a card."),
        "colors": ["B"],
        "power": "3",
    },
    "The Queen of Dale": {
        "type_line": "Legendary Creature — Human Noble",
        "mana_cost": "{1}{W}",
        "cmc": 2.0,
        "oracle_text": (
            "Whenever an opponent casts their first noncreature spell each "
            "turn, you recruit. (Draw a card, then discard a card. If you "
            "discarded a nonland card, create a 1/1 white Human Soldier "
            "creature token.)"),
        "colors": ["W"],
        "power": "2",
    },
    "Summon: Bahamut": {
        "type_line": "Enchantment Creature — Saga Dragon",
        "mana_cost": "{9}",
        "cmc": 9.0,
        "oracle_text": (
            "(As this Saga enters and after your draw step, add a lore "
            "counter. Sacrifice after IV.)\n"
            "I, II — Destroy up to one target nonland permanent.\n"
            "III — Draw two cards.\n"
            "IV — Mega Flare — This creature deals damage equal to the total "
            "mana value of other permanents you control to each opponent.\n"
            "Flying"),
        "colors": [],
        "power": "9",
    },
    "Black Market Connections": {
        "type_line": "Enchantment",
        "mana_cost": "{2}{B}",
        "cmc": 3.0,
        "oracle_text": (
            "At the beginning of your first main phase, choose one or more —\n"
            "• Sell Contraband — Create a Treasure token. You lose 1 life.\n"
            "• Buy Information — Draw a card. You lose 2 life.\n"
            "• Hire a Mercenary — Create a 3/2 colorless Shapeshifter "
            "creature token with changeling. You lose 3 life. (It is every "
            "creature type.)"),
        "colors": ["B"],
    },
    "Teval's Judgment": {
        "type_line": "Enchantment",
        "mana_cost": "{2}{B}",
        "cmc": 3.0,
        "oracle_text": (
            "Whenever one or more cards leave your graveyard, choose one that "
            "hasn't been chosen this turn —\n"
            "• Draw a card.\n"
            "• Create a Treasure token.\n"
            "• Create a 2/2 black Zombie Druid creature token."),
        "colors": ["B"],
    },
    "Archon of Cruelty": {
        "type_line": "Creature — Archon",
        "mana_cost": "{6}{B}{B}",
        "cmc": 8.0,
        "oracle_text": (
            "Flying\n"
            "Whenever this creature enters or attacks, target opponent "
            "sacrifices a creature or planeswalker of their choice, discards "
            "a card, and loses 3 life. You draw a card and gain 3 life."),
        "colors": ["B"],
        "power": "6",
    },
    "Sephiroth, Fabled SOLDIER": {
        "type_line": "Legendary Creature — Human Avatar Soldier // Legendary Creature — Angel Nightmare Avatar",
        "mana_cost": "{2}{B}",
        "cmc": 3.0,
        "oracle_text": (
            "Whenever Sephiroth enters or attacks, you may sacrifice another "
            "creature. If you do, draw a card.\n"
            "Whenever another creature dies, target opponent loses 1 life and "
            "you gain 1 life. If this is the fourth time this ability has "
            "resolved this turn, transform Sephiroth."),
        "colors": ["B"],
        "power": "3",
    },
    "The Sackville-Bagginses": {
        "type_line": "Legendary Creature — Halfling Citizen",
        "mana_cost": "{1}{B}",
        "cmc": 2.0,
        "oracle_text": (
            "When The Sackville-Bagginses enter, you may sacrifice another "
            "creature or artifact. If you do, draw a card and create a "
            "Treasure token.\n"
            "Whenever you sacrifice a token, target opponent loses 1 life."),
        "colors": ["B"],
        "power": "2",
    },
    "Kozilek, the Broken Reality": {
        "type_line": "Legendary Creature — Eldrazi",
        "mana_cost": "{9}",
        "cmc": 9.0,
        "oracle_text": (
            "When you cast this spell, up to two target players each manifest "
            "two cards from their hands. For each card manifested this way, "
            "you draw a card. (To manifest a card, put it onto the "
            "battlefield face down as a 2/2 creature. Turn it face up any "
            "time for its mana cost if it's a creature card.)\n"
            "Other colorless creatures you control get +3/+2."),
        "colors": [],
        "power": "9",
    },
    "Thought Monitor": {
        "type_line": "Artifact Creature — Construct",
        "mana_cost": "{6}{U}",
        "cmc": 7.0,
        "oracle_text": (
            "Affinity for artifacts (This spell costs {1} less to cast for "
            "each artifact you control.)\n"
            "Flying\n"
            "When this creature enters, draw two cards."),
        "colors": ["U"],
        "power": "2",
    },
    "Tataru Taru": {
        "type_line": "Legendary Creature — Dwarf Advisor",
        "mana_cost": "{1}{W}",
        "cmc": 2.0,
        "oracle_text": (
            "When Tataru Taru enters, you draw a card and target opponent may "
            "draw a card.\n"
            "Scions' Secretary — Whenever an opponent draws a card, if it "
            "isn't that player's turn, create a tapped Treasure token. This "
            "ability triggers only once each turn."),
        "colors": ["W"],
        "power": "0",
    },
    "Cryptic Command": {
        "type_line": "Instant",
        "mana_cost": "{1}{U}{U}{U}",
        "cmc": 4.0,
        "oracle_text": (
            "Choose two —\n"
            "• Counter target spell.\n"
            "• Return target permanent to its owner's hand.\n"
            "• Tap all creatures your opponents control.\n"
            "• Draw a card."),
        "colors": ["U"],
    },
    "Kozilek, Butcher of Truth": {
        "type_line": "Legendary Creature — Eldrazi",
        "mana_cost": "{10}",
        "cmc": 10.0,
        "oracle_text": (
            "When you cast this spell, draw four cards.\n"
            "Annihilator 4 (Whenever this creature attacks, defending player "
            "sacrifices four permanents of their choice.)\n"
            "When Kozilek is put into a graveyard from anywhere, its owner "
            "shuffles their graveyard into their library."),
        "colors": [],
        "power": "12",
    },
    "Vaultborn Tyrant": {
        "type_line": "Creature — Dinosaur",
        "mana_cost": "{5}{G}{G}",
        "cmc": 7.0,
        "oracle_text": (
            "Trample\n"
            "Whenever this creature or another creature you control with power "
            "4 or greater enters, you gain 3 life and draw a card.\n"
            "When this creature dies, if it's not a token, create a token "
            "that's a copy of it, except it's an artifact in addition to its "
            "other types."),
        "colors": ["G"],
        "power": "6",
    },
    "Sign in Blood": {
        "type_line": "Sorcery",
        "mana_cost": "{B}{B}",
        "cmc": 2.0,
        "oracle_text": "Target player draws two cards and loses 2 life.",
        "colors": ["B"],
    },
    # X spells (XSpellGoldfishTests).
    "Primordial Hydra": {
        "type_line": "Creature — Hydra",
        "mana_cost": "{X}{G}{G}",
        "cmc": 2.0,
        "oracle_text": (
            "This creature enters with X +1/+1 counters on it.\n"
            "At the beginning of your upkeep, double the number of +1/+1 "
            "counters on this creature.\n"
            "This creature has trample as long as it has ten or more +1/+1 "
            "counters on it."),
        "colors": ["G"],
        "power": "0",
    },
    "Stonecoil Serpent": {
        "type_line": "Artifact Creature — Snake",
        "mana_cost": "{X}",
        "cmc": 0.0,
        "oracle_text": (
            "Reach, trample, protection from multicolored\n"
            "This creature enters with X +1/+1 counters on it."),
        "colors": [],
        "power": "0",
    },
    # data/card-metadata.json, 2026-11-21. Its ping reads as interaction, so
    # the cast loop never casts it.
    "Walking Ballista": {
        "type_line": "Artifact Creature — Construct",
        "mana_cost": "{X}{X}",
        "cmc": 0.0,
        "oracle_text": (
            "This creature enters with X +1/+1 counters on it.\n"
            "{4}: Put a +1/+1 counter on this creature.\n"
            "Remove a +1/+1 counter from this creature: It deals 1 damage to any target."),
        "colors": [],
        "power": "0",
    },
    "Hydroid Krasis": {
        "type_line": "Creature — Jellyfish Hydra Beast",
        "mana_cost": "{X}{G}{U}",
        "cmc": 2.0,
        "oracle_text": (
            "When you cast this spell, you gain half X life and draw half X "
            "cards. Round down each time.\n"
            "Flying, trample\n"
            "This creature enters with X +1/+1 counters on it."),
        "colors": ["G", "U"],
        "power": "0",
    },
    "Wan Shi Tong, Librarian": {
        "type_line": "Legendary Creature — Bird Spirit",
        "mana_cost": "{X}{U}{U}",
        "cmc": 2.0,
        "oracle_text": (
            "Flash\n"
            "Flying, vigilance\n"
            "When Wan Shi Tong enters, put X +1/+1 counters on him. Then draw "
            "half X cards, rounded down.\n"
            "Whenever an opponent searches their library, put a +1/+1 counter "
            "on Wan Shi Tong and draw a card."),
        "colors": ["U"],
        "power": "1",
    },
    "Kinetic Ooze": {
        "type_line": "Creature — Ooze",
        "mana_cost": "{X}{G}",
        "cmc": 1.0,
        "oracle_text": (
            "This creature enters with X +1/+1 counters on it.\n"
            "When this creature enters, destroy up to one target artifact or "
            "enchantment with mana value X or less. If X is 5 or more, you draw"
            " a card. If X is 10 or more, double the number of +1/+1 counters "
            "on any number of other target creatures."),
        "colors": ["G"],
        "power": "0",
    },
    "Mind into Matter": {
        "type_line": "Sorcery",
        "mana_cost": "{X}{G}{U}",
        "cmc": 2.0,
        "oracle_text": (
            "Draw X cards. Then you may put a permanent card with mana value X "
            "or less from your hand onto the battlefield tapped."),
        "colors": ["G", "U"],
    },
    "Pull from Tomorrow": {
        "type_line": "Instant",
        "mana_cost": "{X}{U}{U}",
        "cmc": 2.0,
        "oracle_text": "Draw X cards, then discard a card.",
        "colors": ["U"],
    },
    "Transcendent Message": {
        "type_line": "Instant",
        "mana_cost": "{X}{U}{U}{U}{U}",
        "cmc": 4.0,
        "oracle_text": (
            "Convoke (Your creatures can help cast this spell. Each creature "
            "you tap while casting this spell pays for {1} or one mana of that "
            "creature's color.)\n"
            "Draw X cards."),
        "colors": ["U"],
    },
    "Commander's Insight": {
        "type_line": "Instant",
        "mana_cost": "{X}{U}{U}{U}",
        "cmc": 3.0,
        "oracle_text": (
            "Target player draws X cards plus an additional card for each time "
            "they've cast a commander from the command zone this game."),
        "colors": ["U"],
    },
    "Mathemagics": {
        "type_line": "Sorcery",
        "mana_cost": "{X}{X}{U}{U}",
        "cmc": 2.0,
        "oracle_text": (
            "Target player draws 2ˣ cards. (2⁰ = 1, 2¹ = 2, 2² = 4, 2³ = 8, 2⁴ "
            "= 16, 2⁵ = 32, and so on.)"),
        "colors": ["U"],
    },
    "Springleaf Parade": {
        "type_line": "Enchantment",
        "mana_cost": "{X}{G}{G}",
        "cmc": 2.0,
        "oracle_text": (
            "When this enchantment enters, create X 1/1 colorless Shapeshifter "
            "creature tokens with changeling. (They're every creature type.)\n"
            "Creature tokens you control have \"{T}: Add one mana of any "
            "color.\""),
        "colors": ["G"],
    },
    "Summons of Saruman": {
        "type_line": "Sorcery",
        "mana_cost": "{X}{U}{R}",
        "cmc": 2.0,
        "oracle_text": (
            "Amass Orcs X. Mill X cards. You may cast an instant or sorcery "
            "spell with mana value X or less from among them without paying its"
            " mana cost. (To amass Orcs X, put X +1/+1 counters on an Army you "
            "control. It's also an Orc. If you don't control an Army, create a "
            "0/0 black Orc Army creature token first.)\n"
            "Flashback—{3}{U}{R}, Exile X cards from your graveyard."),
        "colors": ["R", "U"],
    },
    "Assault on Osgiliath": {
        "type_line": "Sorcery",
        "mana_cost": "{X}{R}{R}{R}",
        "cmc": 3.0,
        "oracle_text": (
            "Amass Orcs X, then Goblins and Orcs you control gain double strike"
            " and haste until end of turn. (To amass Orcs X, put X +1/+1 "
            "counters on an Army you control. It's also an Orc. If you don't "
            "control an Army, create a 0/0 black Orc Army creature token "
            "first.)"),
        "colors": ["R"],
    },
    "Saruman, the White Hand": {
        "type_line": "Legendary Creature — Avatar Wizard",
        "mana_cost": "{1}{U}{B}{R}",
        "cmc": 4.0,
        "oracle_text": (
            "Whenever you cast a noncreature spell, amass Orcs X, where X is "
            "that spell's mana value. (Put X +1/+1 counters on an Army you "
            "control. It's also an Orc. If you don't control an Army, create a "
            "0/0 black Orc Army creature token first.)\n"
            "Goblins and Orcs you control have ward {2}."),
        "colors": ["B", "R", "U"],
        "power": "2",
    },
    "Swarming of Moria": {
        "type_line": "Sorcery",
        "mana_cost": "{2}{R}",
        "cmc": 3.0,
        "oracle_text": (
            "Create a Treasure token. (It's an artifact with \"{T}, Sacrifice "
            "this token: Add one mana of any color.\")\n"
            "Amass Orcs 2. (Put two +1/+1 counters on an Army you control. It's"
            " also an Orc. If you don't control an Army, create a 0/0 black Orc"
            " Army creature token first.)"),
        "colors": ["R"],
    },
    "Syncopate": {
        "type_line": "Instant",
        "mana_cost": "{X}{U}",
        "cmc": 1.0,
        "oracle_text": (
            "Counter target spell unless its controller pays {X}. If that spell"
            " is countered this way, exile it instead of putting it into its "
            "owner's graveyard."),
        "colors": ["U"],
    },
    "Whir of Invention": {
        "type_line": "Instant",
        "mana_cost": "{X}{U}{U}{U}",
        "cmc": 3.0,
        "oracle_text": (
            "Improvise (Your artifacts can help cast this spell. Each artifact "
            "you tap after you're done activating mana abilities pays for {1}.)"
            "\n"
            "Search your library for an artifact card with mana value X or "
            "less, put it onto the battlefield, then shuffle."),
        "colors": ["U"],
    },
    "Divergent Equation": {
        "type_line": "Instant",
        "mana_cost": "{X}{X}{U}",
        "cmc": 1.0,
        "oracle_text": (
            "Return up to X target instant and/or sorcery cards from your "
            "graveyard to your hand.\n"
            "Exile Divergent Equation."),
        "colors": ["U"],
    },
    # Token makers (TokenMakerGoldfishTests).
    "Plains": {
        "type_line": "Basic Land — Plains",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": "({T}: Add {W}.)",
        "colors": [],
    },
    "Baylen, the Haymaker": {
        "type_line": "Legendary Creature — Rabbit Warrior",
        "mana_cost": "{R}{G}{W}",
        "cmc": 3.0,
        "oracle_text": (
            "Tap two untapped tokens you control: Add one mana of any color.\n"
            "Tap three untapped tokens you control: Draw a card.\n"
            "Tap four untapped tokens you control: Put three +1/+1 counters on "
            "Baylen. It gains trample until end of turn."),
        "colors": ["G", "R", "W"],
        "power": "4",
    },
    "Frontline Rush": {
        "type_line": "Instant",
        "mana_cost": "{R}{W}",
        "cmc": 2.0,
        "oracle_text": (
            "Choose one —\n"
            "• Create two 1/1 red Goblin creature tokens.\n"
            "• Target creature gets +X/+X until end of turn, where X is the "
            "number of creatures you control."),
        "colors": ["R", "W"],
    },
    "Warleader's Call": {
        "type_line": "Enchantment",
        "mana_cost": "{1}{R}{W}",
        "cmc": 3.0,
        "oracle_text": (
            "Creatures you control get +1/+1.\n"
            "Whenever a creature you control enters, this enchantment deals 1 "
            "damage to each opponent."),
        "colors": ["R", "W"],
    },
    "Secure the Wastes": {
        "type_line": "Instant",
        "mana_cost": "{X}{W}",
        "cmc": 1.0,
        "oracle_text": "Create X 1/1 white Warrior creature tokens.",
        "colors": ["W"],
    },
    "Pest Infestation": {
        "type_line": "Sorcery",
        "mana_cost": "{X}{X}{G}",
        "cmc": 1.0,
        "oracle_text": (
            "Destroy up to X target artifacts and/or enchantments. Create twice "
            "X 1/1 black and green Pest creature tokens with \"When this token "
            "dies, you gain 1 life.\""),
        "colors": ["G"],
    },
    "Adeline, Resplendent Cathar": {
        "type_line": "Legendary Creature — Human Knight",
        "mana_cost": "{1}{W}{W}",
        "cmc": 3.0,
        "oracle_text": (
            "Vigilance\n"
            "Adeline's power is equal to the number of creatures you control.\n"
            "Whenever you attack, for each opponent, create a 1/1 white Human "
            "creature token that's tapped and attacking that player or a "
            "planeswalker they control."),
        "colors": ["W"],
        "power": "*",
    },
    "Anim Pakal, Thousandth Moon": {
        "type_line": "Legendary Creature — Human Soldier",
        "mana_cost": "{1}{R}{W}",
        "cmc": 3.0,
        "oracle_text": (
            "Whenever you attack with one or more non-Gnome creatures, put a "
            "+1/+1 counter on Anim Pakal, then create X 1/1 colorless Gnome "
            "artifact creature tokens that are tapped and attacking, where X is "
            "the number of +1/+1 counters on Anim Pakal."),
        "colors": ["R", "W"],
        "power": "1",
    },
    "Scute Swarm": {
        "type_line": "Creature — Insect",
        "mana_cost": "{2}{G}",
        "cmc": 3.0,
        "oracle_text": (
            "Landfall — Whenever a land you control enters, create a 1/1 green "
            "Insect creature token. If you control six or more lands, create a "
            "token that's a copy of this creature instead."),
        "colors": ["G"],
        "power": "1",
    },
    "Nature's Lore": {
        "type_line": "Sorcery",
        "mana_cost": "{1}{G}",
        "cmc": 2.0,
        "oracle_text": (
            "Search your library for a Forest card, put that card onto the "
            "battlefield, then shuffle."),
        "colors": ["G"],
    },
    "Anointed Procession": {
        "type_line": "Enchantment",
        "mana_cost": "{3}{W}",
        "cmc": 4.0,
        "oracle_text": (
            "If an effect would create one or more tokens under your control, it "
            "creates twice that many of those tokens instead."),
        "colors": ["W"],
    },
    "Peregrin Took": {
        "type_line": "Legendary Creature — Halfling Citizen",
        "mana_cost": "{2}{G}",
        "cmc": 3.0,
        "oracle_text": (
            "If one or more tokens would be created under your control, those "
            "tokens plus an additional Food token are created instead. (It's an "
            "artifact with \"{2}, {T}, Sacrifice this token: You gain 3 life.\")\n"
            "Sacrifice three Foods: Draw a card."),
        "colors": ["G"],
        "power": "2",
    },
    "Halo Fountain": {
        "type_line": "Artifact",
        "mana_cost": "{2}{W}",
        "cmc": 3.0,
        "oracle_text": (
            "{W}, {T}, Untap a tapped creature you control: Create a 1/1 green "
            "and white Citizen creature token.\n"
            "{W}{W}, {T}, Untap two tapped creatures you control: Draw a card.\n"
            "{W}{W}{W}{W}{W}, {T}, Untap fifteen tapped creatures you control: "
            "You win the game."),
        "colors": ["W"],
    },
    "Castle Ardenvale": {
        "type_line": "Land",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": (
            "This land enters tapped unless you control a Plains.\n"
            "{T}: Add {W}.\n"
            "{2}{W}{W}, {T}: Create a 1/1 white Human creature token."),
        "colors": [],
    },
    "Prosperous Partnership": {
        "type_line": "Enchantment",
        "mana_cost": "{1}{R}{W}",
        "cmc": 3.0,
        "oracle_text": (
            "When this enchantment enters, create two 1/1 green and white "
            "Citizen creature tokens.\n"
            "Tap three untapped creatures you control: Create a Treasure token."),
        "colors": ["R", "W"],
    },
    "Staff of the Storyteller": {
        "type_line": "Artifact",
        "mana_cost": "{1}{W}",
        "cmc": 2.0,
        "oracle_text": (
            "When this artifact enters, create a 1/1 white Spirit creature token "
            "with flying.\n"
            "Whenever you create one or more creature tokens, put a story counter "
            "on this artifact.\n"
            "{W}, {T}, Remove a story counter from this artifact: Draw a card."),
        "colors": ["W"],
    },
    "Rosie Cotton of South Lane": {
        "type_line": "Legendary Creature — Halfling Peasant",
        "mana_cost": "{2}{W}",
        "cmc": 3.0,
        "oracle_text": (
            "When Rosie Cotton enters, create a Food token. (It's an artifact "
            "with \"{2}, {T}, Sacrifice this token: You gain 3 life.\")\n"
            "Whenever you create a token, put a +1/+1 counter on target creature "
            "you control other than Rosie Cotton."),
        "colors": ["W"],
        "power": "1",
    },
    "Mondrak, Glory Dominus": {
        "type_line": "Legendary Creature — Phyrexian Horror",
        "mana_cost": "{2}{W}{W}",
        "cmc": 4.0,
        "oracle_text": (
            "If one or more tokens would be created under your control, twice "
            "that many of those tokens are created instead.\n"
            "{1}{W/P}{W/P}, Sacrifice two other artifacts and/or creatures: Put "
            "an indestructible counter on Mondrak. ({W/P} can be paid with "
            "either {W} or 2 life.)"),
        "colors": ["W"],
        "power": "4",
    },
    "Draconic Visitor": {
        "type_line": "Creature — Dragon",
        "mana_cost": "{3}{R}{R}",
        "cmc": 5.0,
        "oracle_text": (
            "Flying\n"
            "If one or more artifact tokens would be created under your control, "
            "that many 5/5 red Dragon creature tokens with flying are created "
            "instead."),
        "colors": ["R"],
        "power": "5",
    },
    "Zero Trinket": {
        "type_line": "Artifact",
        "mana_cost": "{0}",
        "cmc": 0.0,
        "oracle_text": "",
        "colors": [],
    },
    "Probe Commander": {
        "type_line": "Legendary Creature — Test",
        "mana_cost": "{5}",
        "cmc": 5.0,
        "oracle_text": "",
        "colors": [],
        "power": "5",
    },
    # ManaModelGoldfishTests (2026-11-19): data/card-metadata.json as it held
    # them that day, back_face included. "Probe Five", "Probe Two", "Probe BB"
    # and "Probe Nine" are made-up creatures with no text.
    "Wastes": {
        "type_line": "Basic Land",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": "{T}: Add {C}.",
        "colors": [],
    },
    "Mana Vault": {
        "type_line": "Artifact",
        "mana_cost": "{1}",
        "cmc": 1.0,
        "oracle_text": (
            "This artifact doesn't untap during your untap step.\n"
            "At the beginning of your upkeep, you may pay {4}. If you do, untap "
            "this artifact.\n"
            "At the beginning of your draw step, if this artifact is tapped, it "
            "deals 1 damage to you.\n"
            "{T}: Add {C}{C}{C}."),
        "colors": [],
    },
    "Lotus Petal": {
        "type_line": "Artifact",
        "mana_cost": "{0}",
        "cmc": 0.0,
        "oracle_text": "{T}, Sacrifice this artifact: Add one mana of any color.",
        "colors": [],
    },
    "Krark-Clan Ironworks": {
        "type_line": "Artifact",
        "mana_cost": "{4}",
        "cmc": 4.0,
        "oracle_text": "Sacrifice an artifact: Add {C}{C}.",
        "colors": [],
    },
    "Tainted Wood": {
        "type_line": "Land",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": (
            "{T}: Add {C}.\n"
            "{T}: Add {B} or {G}. Activate only if you control a Swamp."),
        "colors": [],
    },
    "Hagra Mauling // Hagra Broodpit": {
        "type_line": "Instant // Land",
        "mana_cost": "{2}{B}{B}",
        "cmc": 4.0,
        "oracle_text": (
            "This spell costs {1} less to cast if an opponent controls no basic "
            "lands.\n"
            "Destroy target creature."),
        "colors": ["B"],
        "layout": "modal_dfc",
        "back_face": {"type_line": "Land",
                      "oracle_text": "This land enters tapped.\n{T}: Add {B}."},
    },
    "Brightclimb Pathway": {
        "type_line": "Land // Land",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": "{T}: Add {W}.",
        "colors": [],
        "layout": "modal_dfc",
        "back_face": {"type_line": "Land", "oracle_text": "{T}: Add {B}."},
    },
    "Fabled Passage": {
        "type_line": "Land",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": (
            "{T}, Sacrifice this land: Search your library for a basic land "
            "card, put it onto the battlefield tapped, then shuffle. Then if you "
            "control four or more lands, untap that land."),
        "colors": [],
    },
    "Scorched Ruins": {
        "type_line": "Land",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": (
            "If this land would enter, sacrifice two untapped lands instead. If "
            "you do, put this land onto the battlefield. If you don't, put it "
            "into its owner's graveyard.\n"
            "{T}: Add {C}{C}{C}{C}."),
        "colors": [],
    },
    "Cultivate": {
        "type_line": "Sorcery",
        "mana_cost": "{2}{G}",
        "cmc": 3.0,
        "oracle_text": (
            "Search your library for up to two basic land cards, reveal those "
            "cards, put one onto the battlefield tapped and the other into your "
            "hand, then shuffle."),
        "colors": ["G"],
    },
    "Wayfarer's Bauble": {
        "type_line": "Artifact",
        "mana_cost": "{1}",
        "cmc": 1.0,
        "oracle_text": (
            "{2}, {T}, Sacrifice this artifact: Search your library for a basic "
            "land card, put that card onto the battlefield tapped, then shuffle."),
        "colors": [],
    },
    "Birgi, God of Storytelling // Harnfel, Horn of Bounty": {
        "type_line": "Legendary Creature — God // Legendary Artifact",
        "mana_cost": "{2}{R}",
        "cmc": 3.0,
        "oracle_text": (
            "Whenever you cast a spell, add {R}. Until end of turn, you don't "
            "lose this mana as steps and phases end.\n"
            "Creatures you control can boast twice during each of your turns "
            "rather than once."),
        "colors": ["R"],
        "layout": "modal_dfc",
        "power": "3",
    },
    "Probe Five": {
        "type_line": "Creature — Test",
        "mana_cost": "{5}",
        "cmc": 5.0,
        "oracle_text": "",
        "colors": [],
    },
    "Probe Two": {
        "type_line": "Creature — Test",
        "mana_cost": "{2}",
        "cmc": 2.0,
        "oracle_text": "",
        "colors": [],
    },
    "Probe BB": {
        "type_line": "Creature — Test",
        "mana_cost": "{B}{B}",
        "cmc": 2.0,
        "oracle_text": "",
        "colors": ["B"],
    },
    "Probe Nine": {
        "type_line": "Creature — Test",
        "mana_cost": "{9}",
        "cmc": 9.0,
        "oracle_text": "",
        "colors": [],
    },
    # Fix pass (2026-11-19): data/card-metadata.json as it held them that day.
    # "Probe Three", "Probe Petal Four", "Probe Slow Land" and "Probe Kill"
    # are made up: a creature with no text, a self-sacrificing {4} artifact,
    # a land that reads the other lands, and interaction (no goldfish target).
    "Llanowar Elves": {
        "type_line": "Creature — Elf Druid",
        "mana_cost": "{G}",
        "cmc": 1.0,
        "oracle_text": "{T}: Add {G}.",
        "colors": ["G"],
        "power": "1",
    },
    "Lotus Field": {
        "type_line": "Land",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": (
            "Hexproof\nThis land enters tapped.\nWhen this land enters, sacrifice two "
            "lands.\n{T}: Add three mana of any one color."),
        "colors": [],
    },
    "Simic Growth Chamber": {
        "type_line": "Land",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": (
            "This land enters tapped.\nWhen this land enters, return a land you "
            "control to its owner's hand.\n{T}: Add {G}{U}."),
        "colors": [],
    },
    "Ugin's Labyrinth": {
        "type_line": "Land",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": (
            "Imprint — When this land enters, you may exile a colorless card with "
            "mana value 7 or greater from your hand.\n{T}: Add {C}. If a card is "
            "exiled with this land, add {C}{C} instead.\n{T}: Return the exiled "
            "card to its owner's hand."),
        "colors": [],
    },
    "Chrome Mox": {
        "type_line": "Artifact",
        "mana_cost": "{0}",
        "cmc": 0.0,
        "oracle_text": (
            "Imprint — When this artifact enters, you may exile a nonartifact, "
            "nonland card from your hand.\n{T}: Add one mana of any of the exiled "
            "card's colors."),
        "colors": [],
    },
    "Basalt Monolith": {
        "type_line": "Artifact",
        "mana_cost": "{3}",
        "cmc": 3.0,
        "oracle_text": (
            "This artifact doesn't untap during your untap step.\n{T}: Add "
            "{C}{C}{C}.\n{3}: Untap this artifact."),
        "colors": [],
    },
    "Sakura-Tribe Elder": {
        "type_line": "Creature — Snake Shaman",
        "mana_cost": "{1}{G}",
        "cmc": 2.0,
        "oracle_text": (
            "Sacrifice this creature: Search your library for a basic land card, "
            "put that card onto the battlefield tapped, then shuffle."),
        "colors": ["G"],
        "power": "1",
    },
    "Urza, Lord High Artificer": {
        "type_line": "Legendary Creature — Human Artificer",
        "mana_cost": "{2}{U}{U}",
        "cmc": 4.0,
        "oracle_text": (
            "When Urza enters, create a 0/0 colorless Construct artifact creature "
            "token with \"This token gets +1/+1 for each artifact you control.\"\n"
            "Tap an untapped artifact you control: Add {U}.\n{5}: Shuffle your "
            "library, then exile the top card. Until end of turn, you may play that "
            "card without paying its mana cost."),
        "colors": ["U"],
        "power": "1",
    },
    "Xander's Lounge": {
        "type_line": "Land — Island Swamp Mountain",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": (
            "({T}: Add {U}, {B}, or {R}.)\nThis land enters tapped.\nCycling {3} "
            "({3}, Discard this card: Draw a card.)"),
        "colors": [],
    },
    "Polluted Delta": {
        "type_line": "Land",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": (
            "{T}, Pay 1 life, Sacrifice this land: Search your library for an "
            "Island or Swamp card, put it onto the battlefield, then shuffle."),
        "colors": [],
    },
    "Probe Three": {
        "type_line": "Creature — Test",
        "mana_cost": "{3}",
        "cmc": 3.0,
        "oracle_text": "",
        "colors": [],
    },
    "Probe Petal Four": {
        "type_line": "Artifact",
        "mana_cost": "{4}",
        "cmc": 4.0,
        "oracle_text": "{T}, Sacrifice this artifact: Add {C}{C}.",
        "colors": [],
    },
    "Probe Slow Land": {
        "type_line": "Land",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": (
            "This land enters tapped unless you control two or more other lands.\n"
            "{T}: Add {C}."),
        "colors": [],
    },
    "Probe Kill": {
        "type_line": "Instant",
        "mana_cost": "{1}{B}",
        "cmc": 2.0,
        "oracle_text": "Destroy target creature.",
        "colors": ["B"],
    },
    # Review round 1 (2026-11-20): data/card-metadata.json as it held them
    # that day. "Probe Vigilant Elf", "Probe Combo A" and "Probe Combo B" are
    # made up: a vigilant mana Elf and two instants a combo line names.
    "Shineshadow Snarl": {
        "type_line": "Land",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": (
            "As this land enters, you may reveal a Plains or Swamp card from your "
            "hand. If you don't, this land enters tapped.\n{T}: Add {W} or {B}."),
        "colors": [],
    },
    "Ancient Tomb": {
        "type_line": "Land",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": "{T}: Add {C}{C}. This land deals 2 damage to you.",
        "colors": [],
    },
    "Three Visits": {
        "type_line": "Sorcery",
        "mana_cost": "{1}{G}",
        "cmc": 2.0,
        "oracle_text": (
            "Search your library for a Forest card, put it onto the battlefield, then "
            "shuffle."),
        "colors": ["G"],
    },
    "Drowned Catacomb": {
        "type_line": "Land",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": (
            "This land enters tapped unless you control an Island or a Swamp.\n{T}: Add "
            "{U} or {B}."),
        "colors": [],
    },
    "Elvish Archdruid": {
        "type_line": "Creature — Elf Druid",
        "mana_cost": "{1}{G}{G}",
        "cmc": 3.0,
        "oracle_text": "Other Elf creatures you control get +1/+1.\n{T}: Add {G} for each Elf you control.",
        "colors": ["G"],
        "power": "2",
    },
    "Forsaken Monument": {
        "type_line": "Legendary Artifact",
        "mana_cost": "{5}",
        "cmc": 5.0,
        "oracle_text": (
            "Colorless creatures you control get +2/+2.\nWhenever you tap a permanent "
            "for {C}, add an additional {C}.\nWhenever you cast a colorless spell, you "
            "gain 2 life."),
        "colors": [],
    },
    "Urza's Saga": {
        "type_line": "Enchantment Land — Urza's Saga",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": (
            "(As this Saga enters and after your draw step, add a lore counter. "
            "Sacrifice after III.)\nI — This Saga gains \"{T}: Add {C}.\"\nII — This "
            "Saga gains \"{2}, {T}: Create a 0/0 colorless Construct artifact creature "
            "token with 'This token gets +1/+1 for each artifact you control.'\"\nIII — "
            "Search your library for an artifact card with mana cost {0} or {1}, put it "
            "onto the battlefield, then shuffle."),
        "colors": [],
    },
    "Probe Vigilant Elf": {
        "type_line": "Creature — Elf",
        "mana_cost": "{G}",
        "cmc": 1.0,
        "oracle_text": "Vigilance\n{T}: Add {G}.",
        "colors": ["G"],
        "power": "1",
    },
    "Probe Combo A": {
        "type_line": "Instant",
        "mana_cost": "{1}{G}",
        "cmc": 2.0,
        "oracle_text": "",
        "colors": ["G"],
    },
    "Probe Combo B": {
        "type_line": "Instant",
        "mana_cost": "{G}",
        "cmc": 1.0,
        "oracle_text": "",
        "colors": ["G"],
    },
    # Review round 2 (2026-11-20): data/card-metadata.json or the local
    # Scryfall mirror as they held them that day. "Probe CCC", "Probe WWW",
    # "Probe GG" and "Probe Metal Rock" are made up: creatures with no text,
    # and an artifact whose mana needs a second artifact.
    "Sol Ring": {
        "type_line": "Artifact",
        "mana_cost": "{1}",
        "cmc": 1.0,
        "oracle_text": "{T}: Add {C}{C}.",
        "colors": [],
    },
    "Chromatic Lantern": {
        "type_line": "Artifact",
        "mana_cost": "{3}",
        "cmc": 3.0,
        "oracle_text": (
            "Lands you control have \"{T}: Add one mana of any color.\"\n{T}: Add one mana "
            "of any color."),
        "colors": [],
    },
    "Reflecting Pool": {
        "type_line": "Land",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": "{T}: Add one mana of any type that a land you control could produce.",
        "colors": [],
    },
    "Nykthos, Shrine to Nyx": {
        "type_line": "Legendary Land",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": (
            "{T}: Add {C}.\n{2}, {T}: Choose a color. Add an amount of mana of that color equal "
            "to your devotion to that color. (Your devotion to a color is the number of mana "
            "symbols of that color in the mana costs of permanents you control.)"),
        "colors": [],
    },
    "Myriad Landscape": {
        "type_line": "Land",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": (
            "This land enters tapped.\n{T}: Add {C}.\n{2}, {T}, Sacrifice this land: Search your "
            "library for up to two basic land cards that share a land type, put them onto the "
            "battlefield tapped, then shuffle."),
        "colors": [],
    },
    "High Market": {
        "type_line": "Land",
        "mana_cost": "",
        "cmc": 0.0,
        "oracle_text": "{T}: Add {C}.\n{T}, Sacrifice a creature: You gain 1 life.",
        "colors": [],
    },
    "Probe CCC": {
        "type_line": "Creature — Test",
        "mana_cost": "{C}{C}{C}",
        "cmc": 3.0,
        "oracle_text": "",
        "colors": [],
    },
    "Probe WWW": {
        "type_line": "Creature — Test",
        "mana_cost": "{W}{W}{W}",
        "cmc": 3.0,
        "oracle_text": "",
        "colors": ["W"],
    },
    "Probe GG": {
        "type_line": "Creature — Test",
        "mana_cost": "{G}{G}",
        "cmc": 2.0,
        "oracle_text": "",
        "colors": ["G"],
    },
    "Probe WW": {
        "type_line": "Creature — Test",
        "mana_cost": "{W}{W}",
        "cmc": 2.0,
        "oracle_text": "",
        "colors": ["W"],
    },
    "Probe Metal Rock": {
        "type_line": "Artifact",
        "mana_cost": "{0}",
        "cmc": 0.0,
        "oracle_text": "{T}: Add {C}{C}. Activate only if you control two or more artifacts.",
        "colors": [],
    },
}


class CastTimeDrawTests(unittest.TestCase):
    """Cards the goldfish draws when it casts a card, from the card's oracle text.

    Each case builds the profile from the oracle text (build_goldfish_profile)
    and casts it through resolve_cast_effects, the path the main-phase and
    cascade casts share. Oracle text is copied from Scryfall; "−" in loyalty
    costs is U+2212, as Scryfall prints it.
    """

    def _cards_drawn_on_cast(self, name, type_line, mana_cost, cmc, oracle_text):
        meta = {"name": name, "type_line": type_line, "mana_cost": mana_cost,
                "cmc": cmc, "oracle_text": oracle_text}
        profile = exporter.build_goldfish_profile(
            name=name, meta=meta, category_names=set(),
            commander_colors=["U", "B", "R"], commander_name="Other")
        library = [f"Library {i}" for i in range(10)]
        hand = []
        exporter.resolve_cast_effects(
            name, profile, 1, exporter.GoldfishManaPool([]), library, hand,
            [], [], {name: profile}, ["U", "B", "R"])
        return len(hand)

    def test_an_unaffordable_minus_loyalty_draw_is_not_drawn_on_cast(self):
        # Enters with 3 loyalty, so −6 cannot be activated on entry; its other
        # draw is an opponent's-draw-step trigger. Neither happens on cast.
        drawn = self._cards_drawn_on_cast(
            "The Theorist, Jace Beleren", "Legendary Planeswalker — Jace",
            "{2}{U}{U}", 4,
            "At the beginning of each opponent's draw step, you draw a card.\n"
            "+1: Create a 1/1 blue Illusion creature token.\n"
            "−2: For each opponent, return up to one target artifact or creature "
            "that player controls to its owner's hand.\n"
            "−6: Draw three cards. Then put X +1/+1 counters on each creature you "
            "control, where X is the number of cards in your hand.")
        self.assertEqual(drawn, 0)

    def test_a_plus_loyalty_draw_keeps_its_count(self):
        # Enters with 7 loyalty; +2 can be activated the turn it is cast.
        drawn = self._cards_drawn_on_cast(
            "Ugin, Eye of the Storms", "Legendary Planeswalker — Ugin", "{7}", 7,
            "When you cast this spell, exile up to one target permanent that's one "
            "or more colors.\n"
            "Whenever you cast a colorless spell, exile up to one target permanent "
            "that's one or more colors.\n"
            "+2: You gain 3 life and draw a card.\n"
            "0: Add {C}{C}{C}.\n"
            "−11: Search your library for any number of colorless nonland cards, "
            "exile them, then shuffle. Until end of turn, you may cast those cards "
            "without paying their mana costs.")
        self.assertEqual(drawn, 1)

    def test_a_zero_loyalty_draw_keeps_its_count(self):
        # Enters with 6 loyalty; 0 can be activated the turn it is cast.
        drawn = self._cards_drawn_on_cast(
            "Vraska, Betrayal's Sting", "Legendary Planeswalker — Vraska",
            "{4}{B}{B/P}", 6,
            "Compleated ({B/P} can be paid with {B} or 2 life. If life was paid, "
            "this planeswalker enters with two fewer loyalty counters.)\n"
            "0: You draw a card and lose 1 life. Proliferate.\n"
            "−2: Target creature becomes a Treasure artifact with \"{T}, Sacrifice "
            "this artifact: Add one mana of any color\" and loses all other card "
            "types and abilities.\n"
            "−9: If target player has fewer than nine poison counters, they get a "
            "number of poison counters equal to the difference.")
        self.assertEqual(drawn, 1)

    def test_floor_a_minus_loyalty_draw_counts_zero_even_when_affordable(self):
        # Documents the floor: the card metadata carries no starting loyalty, so
        # a minus ability is never counted, even one the walker could afford on
        # entry (any starting loyalty of 1 or more pays this −1).
        drawn = self._cards_drawn_on_cast(
            "Synthetic Walker", "Legendary Planeswalker — Test", "{2}{U}", 3,
            "−1: Draw a card.")
        self.assertEqual(drawn, 0)

    def test_a_hyphen_typed_in_place_of_the_minus_sign_is_a_minus_cost(self):
        # Oracle text prints U+2212; a hyphen-minus in its place is the same cost.
        drawn = self._cards_drawn_on_cast(
            "Synthetic Walker", "Legendary Planeswalker — Test", "{2}{U}", 3,
            "-2: Draw two cards.")
        self.assertEqual(drawn, 0)

    def test_floor_a_minus_x_loyalty_draw_counts_zero(self):
        # Documents the floor: −X can be paid with X = 0 at any loyalty, so the
        # walker can draw the turn it is cast, but a minus ability is never
        # counted.
        drawn = self._cards_drawn_on_cast(
            "Synthetic Walker", "Legendary Planeswalker — Test", "{2}{U}", 3,
            "−X: Draw a card.")
        self.assertEqual(drawn, 0)

    def test_a_draw_spell_draws_on_cast(self):
        drawn = self._cards_drawn_on_cast(
            "Night's Whisper", "Sorcery", "{1}{B}", 2,
            "You draw two cards and lose 2 life.")
        self.assertEqual(drawn, 2)

    def test_an_enters_draw_keeps_its_count(self):
        # "draw two cards, then discard two cards": the goldfish credits the two
        # draws and models no discard; this pins that count.
        drawn = self._cards_drawn_on_cast(
            "Seasoned Cryomancer", "Creature — Human Wizard", "{1}{U}{U}", 3,
            "When this creature enters, draw two cards, then discard two cards. "
            "When you discard one or more nonland cards this way, tap up to that "
            "many target creatures and put a stun counter on each of them.\n"
            "{3}{U}{U}, Exile this card from your graveyard: Draw two cards.")
        self.assertEqual(drawn, 2)

    def _drawn(self, name):
        card = CARDS[name]
        return self._cards_drawn_on_cast(
            name, card["type_line"], card["mana_cost"], card["cmc"], card["oracle_text"])

    # Fleet cards (text in CARDS). Expected values are what each card draws
    # as it is cast or enters, read off that text.
    FLEET_CASES = {
        # Reminder text: the gift reminder's draw is the opponent's.
        "Long River's Pull": 0,
        # Activated abilities.
        "Mind Stone": 0,
        "Hedron Archive": 0,
        "Commander's Sphere": 0,
        # Cycling: reminder text and an activated ability.
        "Ozolith, the Shattered Spire": 0,
        # Triggers other than the card's own entering or casting, follow-on
        # sentences included.
        "Sauron, the Dark Lord": 0,
        "Belladonna Took": 0,
        "Braids, Arisen Nightmare": 0,
        "The Queen of Dale": 0,
        # Saga: the draw is chapter III.
        "Summon: Bahamut": 0,
        # Mode lines under a recurring trigger.
        "Black Market Connections": 0,
        "Teval's Judgment": 0,
        # Own entering, worded "Whenever this creature enters"; the draw is
        # the next sentence.
        "Archon of Cruelty": 1,
        # Own entering by short name ("Whenever Sephiroth enters").
        "Sephiroth, Fabled SOLDIER": 1,
        # Own entering by full name, plural verb ("enter").
        "The Sackville-Bagginses": 1,
        # Own entering, the draw in the trigger sentence itself.
        "Thought Monitor": 2,
        "Tataru Taru": 1,
        # Own entering worded "Whenever this creature or another creature
        # ... enters": the trigger sentence's draw is credited once, for its
        # own entry.
        "Vaultborn Tyrant": 1,
        # Own casting, the draw in the trigger sentence itself.
        "Kozilek, Butcher of Truth": 4,
        # "Target player draws": the pilot targets themself.
        "Sign in Blood": 2,
        # A mode line under "Choose two —".
        "Cryptic Command": 1,
    }

    def test_fleet_cards_draw_what_they_draw_on_cast(self):
        for name, expected in self.FLEET_CASES.items():
            with self.subTest(card=name):
                self.assertEqual(self._drawn(name), expected)

    def test_floor_a_variable_cast_trigger_draw_counts_one(self):
        # Kozilek draws one card per card manifested, up to four. The cast
        # trigger is the card's own casting, so the line is kept, and the next
        # sentence's "you draw a card" is credited as 1.
        self.assertEqual(self._drawn("Kozilek, the Broken Reality"), 1)

    def test_an_enters_trigger_by_a_full_name_with_a_comma_keeps_its_count(self):
        drawn = self._cards_drawn_on_cast(
            "Example, the Sage", "Legendary Creature — Test", "{2}{U}", 3,
            "When Example, the Sage enters, draw a card.")
        self.assertEqual(drawn, 1)

    def test_a_token_entering_after_an_attack_is_not_own_entering(self):
        # "enters" after the trigger clause's comma belongs to the token.
        drawn = self._cards_drawn_on_cast(
            "Synthetic Raider", "Creature — Test", "{2}{R}", 3,
            "Whenever this creature attacks, create a token that enters tapped. "
            "Draw a card.")
        self.assertEqual(drawn, 0)

    # Literal synthetic texts below (not fleet cards), expected values read off
    # the text: what the caster draws as the card is cast or enters.

    def test_an_own_entering_draw_with_a_plural_verb_in_the_trigger_sentence(self):
        # "enter", not "enters": the trigger sentence itself holds the draw.
        drawn = self._cards_drawn_on_cast(
            "Synthetic Twins & Triplets", "Legendary Creature — Test", "{2}{B}", 3,
            "When Synthetic Twins & Triplets enter, draw a card.")
        self.assertEqual(drawn, 1)

    def test_an_own_entering_or_attacking_trigger_draws_once_on_entry(self):
        drawn = self._cards_drawn_on_cast(
            "Synthetic Raider", "Creature — Test", "{2}{U}", 3,
            "Whenever this creature enters or attacks, draw a card.")
        self.assertEqual(drawn, 1)

    def test_another_creature_entering_after_an_attack_is_not_own_entering(self):
        # The card's own entry does not trigger this; only "this creature or
        # another ... enters" names its own entering.
        drawn = self._cards_drawn_on_cast(
            "Synthetic Raider", "Creature — Test", "{2}{U}", 3,
            "Whenever this creature attacks or another creature you control "
            "enters, draw a card.")
        self.assertEqual(drawn, 0)

    def test_a_delayed_draw_in_the_entering_trigger_is_not_drawn_on_cast(self):
        drawn = self._cards_drawn_on_cast(
            "Synthetic Raider", "Creature — Test", "{2}{U}", 3,
            "When this creature enters, draw a card at the beginning of the "
            "next turn's upkeep.")
        self.assertEqual(drawn, 0)

    def test_a_draw_by_another_subject_counts_zero(self):
        for text in ("Target opponent draws two cards.", "Each opponent draws a card."):
            with self.subTest(text=text):
                drawn = self._cards_drawn_on_cast(
                    "Synthetic Gift", "Sorcery", "{1}{U}", 2, text)
                self.assertEqual(drawn, 0)

    def test_floor_each_player_draws_counts_zero(self):
        # Documents the floor: the pilot is one of the players and draws two,
        # but of the third-person draws only "target player draws" is counted.
        drawn = self._cards_drawn_on_cast(
            "Synthetic Gift", "Sorcery", "{1}{U}", 2, "Each player draws two cards.")
        self.assertEqual(drawn, 0)

    def test_an_attack_trigger_draw_is_not_drawn_on_cast(self):
        drawn = self._cards_drawn_on_cast(
            "Synthetic Raider", "Creature — Test", "{2}{U}", 3,
            "Whenever this creature attacks, draw a card.")
        self.assertEqual(drawn, 0)

    def test_a_later_trigger_sentence_on_an_own_entering_line_is_not_drawn(self):
        # One line, two sentences: only the first is the entering trigger.
        drawn = self._cards_drawn_on_cast(
            "Synthetic Raider", "Creature — Test", "{2}{U}", 3,
            "When this creature enters, create a token. Whenever it attacks, "
            "draw a card.")
        self.assertEqual(drawn, 0)

    def test_a_chapter_one_saga_draw_is_drawn_on_cast(self):
        # No saga in the fleet draws at chapter I; literal text. The chapter
        # list includes I, so the draw happens as the saga enters.
        drawn = self._cards_drawn_on_cast(
            "Synthetic Saga", "Enchantment — Saga", "{2}{U}", 3,
            "(As this Saga enters and after your draw step, add a lore counter. "
            "Sacrifice after III.)\n"
            "I, II — Draw a card.\n"
            "III — Scry 2.")
        self.assertEqual(drawn, 1)

    def test_an_enters_trigger_by_front_face_name_keeps_its_count(self):
        # Literal text: a double-faced card's front face names itself.
        drawn = self._cards_drawn_on_cast(
            "Front Walker // Back Walker", "Creature — Test // Creature — Test",
            "{2}{U}", 3,
            "When Front Walker enters, draw a card.")
        self.assertEqual(drawn, 1)

    def test_cast_turn_activations_are_credited_by_name_only(self):
        # The oracle parse skips both activated draws; CAST_TURN_ACTIVATION_DRAW
        # credits the first activation on the cast turn.
        for name in ("The One Ring", "Azami, Lady of Scrolls"):
            with self.subTest(card=name):
                self.assertEqual(exporter.immediate_draw_count(name, CARDS[name]), 0)
                self.assertEqual(self._drawn(name), 1)


class SerialPool:
    """multiprocessing.Pool stand-in that maps in this process."""

    def __init__(self, *_args, **_kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    @staticmethod
    def map(fn, iterable):
        return [fn(item) for item in iterable]


class DrawEngineGoldfishTests(unittest.TestCase):
    """PERMANENT_DRAW_ENGINE through the goldfish turn loop.

    One simulate_goldfish_game run with the opening fixed instead of shuffled
    (the mulligan's shuffle is replaced by a given hand and library), under a
    deck id whose shipped config holds the engine; card data from CARDS. The
    library size is read at each turn's land choice, after that turn's draws,
    and once after turn 10; each drop is what was drawn in between. The
    default fixture: the engine card and six Islands in hand, 92 Islands in
    the library and a commander the Islands cannot cast, so the engine card
    is cast on turn 4, the first turn with four lands.
    """

    def _library_sizes(self, deck_id, hand, library, commander="The Ur-Dragon",
                       colors=("U",), hand_sizes=None):
        """Library sizes at each land choice; `hand_sizes`, if given, gets the
        hand size at each land choice (choose_land_to_play's first argument)."""
        decklist = hand + library
        context = exporter.build_goldfish_context(
            decklist, {"decklist": []}, CARDS, commander, list(colors), deck_id)
        sizes = []
        choose_land = exporter.choose_land_to_play

        def record_then_choose(*args, **kwargs):
            sizes.append(len(library))
            if hand_sizes is not None:
                hand_sizes.append(len(args[0]))
            return choose_land(*args, **kwargs)

        with patch.object(exporter, "commander_mulligan_goldfish",
                          return_value=(library, hand)), \
                patch.object(exporter, "choose_land_to_play",
                             side_effect=record_then_choose):
            exporter.simulate_goldfish_game(decklist, context, 6)
        return sizes + [len(library)]

    def _engine_card_sizes(self, card, deck_id):
        return self._library_sizes(deck_id, [card] + ["Island"] * 6, ["Island"] * 92)

    def test_jace_draws_three_at_the_start_of_each_later_turn(self):
        # Turns 1-4 draw 1 (the draw step, turn 1 included: CR 103.8c); Jace
        # adds nothing on turn 4, his cast turn; turns 5-10 draw 1 + 3.
        for deck_id in ("tidal-legion", "gathering-shadow"):
            with self.subTest(deck=deck_id):
                self.assertEqual(
                    self._engine_card_sizes("The Theorist, Jace Beleren", deck_id),
                    [91, 90, 89, 88, 84, 80, 76, 72, 68, 64, 64])

    def test_one_ring_sequence_is_unchanged(self):
        # Turns 1-4 draw 1 (the draw step). Cast on turn 4 and draws 1 then
        # (88 -> 87); turns 5, 6, 7 draw the draw step plus activations 2, 3,
        # 4; then the draw step alone.
        self.assertEqual(
            self._engine_card_sizes("The One Ring", "gandalf-party-guest"),
            [91, 90, 89, 88, 84, 80, 75, 74, 73, 72, 72])

    def test_jace_cards_arrive_before_the_upkeep_tempt(self):
        # gathering-shadow: Call of the Ring tempts at upkeep while the
        # commander is out, and the tempt converts to discard-hand-draw-four
        # only at hand size 2 or less. Hand: Jace, Call of the Ring, a Swamp
        # and four Islands; library: 40 Zero Trinkets ({0}, cast the turn they
        # are drawn, so the hand empties every turn); commander: Probe
        # Commander ({5}). Swamp turn 1, an Island each turn 2-5; Call of the
        # Ring turn 2, Jace turn 4, the commander turn 5. Turns 1-4 each draw
        # a Trinket in the draw step: 39, 38, 37, 36.
        # Turn 5 (commander not out yet, no tempt): 36 - 3 - 1 = 32.
        # Turn 6: the hand is empty after turn 5; Jace's 3 cards make it 3, so
        # the upkeep tempt does not convert, and the draw step adds 1:
        # 32 - 3 - 1 = 28. Were the tempt read before Jace's cards, it would
        # convert on the empty hand (draw 4), then Jace 3 and the draw step 1:
        # 24.
        sizes = self._library_sizes(
            "gathering-shadow",
            hand=["The Theorist, Jace Beleren", "Call of the Ring", "Swamp",
                  "Island", "Island", "Island", "Island"],
            library=["Zero Trinket"] * 40,
            commander="Probe Commander", colors=("U", "B"))
        self.assertEqual(sizes[:6], [39, 38, 37, 36, 32, 28])

    def test_the_upkeep_tempt_reads_the_hand_before_the_draw_step(self):
        # gathering-shadow, no Jace. Hand: Call of the Ring, a Swamp and five
        # Islands; library: 39 Zero Trinkets with an Island on top;
        # commander: Probe Commander ({5}). Turn 1 draws the Island and plays
        # the Swamp; turn 2 draws a Trinket, plays an Island and casts Call of
        # the Ring and the Trinket; turns 3-5 each draw a Trinket, play an
        # Island and cast the Trinket; turn 5's five lands cast the
        # commander. Turn 6 upkeep: two Islands in hand, so the tempt converts
        # (discard 2, draw 4) and then the draw step draws 1: 35 - 4 - 1 = 30,
        # and the hand holds 4 + 1 = 5 at the land choice. Were the draw step
        # first, the tempt would read 3 cards and not convert: 34 and a hand
        # of 3. Were the discard-and-draw done after the draw step, the
        # library would also read 30 but the hand 4.
        # Hand at each land choice: 8 (the Island drawn), 8, 6, 5, 4, then 5.
        hand_sizes = []
        sizes = self._library_sizes(
            "gathering-shadow",
            hand=["Call of the Ring", "Swamp"] + ["Island"] * 5,
            library=["Zero Trinket"] * 39 + ["Island"],
            commander="Probe Commander", colors=("U", "B"), hand_sizes=hand_sizes)
        self.assertEqual(sizes[:6], [39, 38, 37, 36, 35, 30])
        self.assertEqual(hand_sizes[:6], [8, 8, 6, 5, 4, 5])

    # The draw-engine paragraphs of the goldfish methodology, whole.
    ACTIVATED_PARAGRAPH = (
        " Activated draw engines modeled (DEC-472): The One Ring (max 4 "
        "activations). Each turn on the battlefield the engine activates once — "
        "its counter total grows by one and that many cards are drawn (the "
        "cast-turn draw stays on the immediateDraw path). maxActivations is the "
        "stopping rule standing in for The One Ring's upkeep life loss, which the "
        "goldfish does not track. Floors: the on-cast protection turn and "
        "opponent-dependent draw taxes (Rhystic Study / Mystic Remora class) are "
        "not modeled.")
    RECURRING_PARAGRAPH = (
        " Recurring draw triggers modeled (owner-approved 2026-11-17): The "
        "Theorist, Jace Beleren (3 per turn). These stand in for draws on "
        "opponents' turns (The Theorist, Jace Beleren: one card at the beginning "
        "of each opponent's draw step), so the cards are drawn at the start of "
        "each of your turns from the turn after the permanent is cast. Assumes "
        "all three opponents stay in the game and the permanent survives; there "
        "is no stopping rule.")

    def _methodology(self, deck_id):
        decklist = ["The Theorist, Jace Beleren"] + ["Island"] * 98
        with patch.object(exporter, "GOLDFISH_GAMES", 16), \
                patch("multiprocessing.Pool", SerialPool):
            goldfish, _ = exporter.compute_goldfish_section(
                decklist=decklist, deck_data={"decklist": []}, metadata=CARDS,
                commander_name="The Ur-Dragon", commander_colors=["U"],
                deck_id=deck_id)
        return goldfish["methodology"]

    def test_methodology_names_a_recurring_trigger_on_its_own(self):
        # tidal-legion has a drawsPerTurn engine and no maxActivations one.
        methodology = self._methodology("tidal-legion")
        self.assertIn(self.RECURRING_PARAGRAPH, methodology)
        self.assertNotIn("Activated draw engines", methodology)

    def test_methodology_names_both_draw_engine_kinds(self):
        # gathering-shadow has The One Ring and Jace.
        methodology = self._methodology("gathering-shadow")
        self.assertIn(self.ACTIVATED_PARAGRAPH, methodology)
        self.assertIn(self.RECURRING_PARAGRAPH, methodology)


class TurnOneDrawTests(unittest.TestCase):
    """Turn 1 has a draw step (owner-approved 2026-11-23). The simulators
    model a four-player free-for-all Commander game, in which no player skips
    the draw step of their first turn (CR 103.8c). So the goldfish and every
    mana simulation draw a card on turn 1, and the hypergeometric curves
    count the opening seven plus one card a turn from turn 1."""

    # A made-up {9} sorcery: no fixture in this class reaches nine mana.
    FILLER = "Probe Filler"
    FILLER_CARD = {"type_line": "Sorcery", "mana_cost": "{9}", "cmc": 9.0,
                   "oracle_text": "", "colors": []}
    BASIC = {"W": "Plains", "U": "Island", "B": "Swamp", "R": "Mountain",
             "G": "Forest", "C": "Wastes"}
    TAPPED_FOREST = {"type_line": "Land", "mana_cost": "", "cmc": 0.0,
                     "oracle_text": "This land enters tapped.\n{T}: Add {G}.", "colors": []}

    def test_the_goldfish_plays_the_land_its_turn_1_draw_took(self):
        # simulate_goldfish_game with only the shuffle pinned: it deals the
        # library as given, and draws pop its end. The seven: three Probe
        # Tapped Forests (lands that enter tapped) and four Probe Nines, a
        # keep (three lands). Under them, on top of the library, a Forest.
        # The turn-1 draw takes the Forest and the land drop takes a land
        # usable this turn over a tapped one: one land, one mana on turn 1.
        # With a Probe Nine on top and the Forest under it (the control),
        # the one turn-1 draw takes the Probe Nine and turn 1 plays a tapped
        # land: one land, no mana. So would skipping the turn-1 draw or
        # drawing after the land drop; drawing two on turn 1 would reach the
        # Forest and read one mana.
        cards = dict(CARDS, **{"Probe Tapped Forest": self.TAPPED_FOREST})
        seven = ["Probe Tapped Forest"] * 3 + ["Probe Nine"] * 4
        turn_one = {}
        for top, under in (("Forest", "Probe Nine"), ("Probe Nine", "Forest")):
            order = ["Probe Nine"] * 90 + [under, top] + list(reversed(seven))
            decklist = sorted(order)
            context = exporter.build_goldfish_context(
                decklist, {"decklist": [{"name": name} for name in decklist]}, cards,
                "Probe Commander", ["G"], "synthetic-draw")

            def deal(library, order=order):
                library[:] = order

            with patch.object(exporter.random, "shuffle", deal):
                by_turn, _ = exporter.simulate_goldfish_game(decklist, context, 6)
            turn_one[top] = (by_turn[1]["lands"], by_turn[1]["availableMana"])
        self.assertEqual(turn_one, {"Forest": (1, 1), "Probe Nine": (1, 0)})

    def test_the_goldfish_methodology_states_the_turn_1_draw(self):
        decklist = ["Island"] * 99
        with patch.object(exporter, "GOLDFISH_GAMES", 16), \
                patch("multiprocessing.Pool", SerialPool):
            goldfish, _ = exporter.compute_goldfish_section(
                decklist=decklist, deck_data={"decklist": []}, metadata=CARDS,
                commander_name="The Ur-Dragon", commander_colors=["U"],
                deck_id="synthetic-draw")
        self.assertIn(
            "16-game solitaire heuristic. Every turn draws a card, turn 1 included: the "
            "simulation models a four-player free-for-all Commander game, in which no player "
            "skips the draw step of their first turn (CR 103.8c). Sequencing:",
            goldfish["methodology"])

    def test_cards_seen_are_the_opening_seven_and_one_a_turn_from_turn_1(self):
        self.assertEqual([exporter.cards_seen_by_turn(turn) for turn in range(1, 11)],
                         [8, 9, 10, 11, 12, 13, 14, 15, 16, 17])
        # The whole 99 is seen by turn 92, and never more than 99.
        self.assertEqual([exporter.cards_seen_by_turn(turn) for turn in (91, 92, 93)],
                         [98, 99, 99])

    def test_one_card_is_seen_by_turn_1_eight_times_in_99(self):
        # One copy in 99 cards is among the first n with probability n / 99;
        # n = 7 + turn: 8/99 = 8.1%, ..., 15/99 = 15.2%, ..., 17/99 = 17.2%.
        self.assertEqual(
            exporter.compute_probability_curve([self.FILLER]),
            {"1": 8.1, "2": 9.1, "3": 10.1, "4": 11.1, "5": 12.1,
             "6": 13.1, "7": 14.1, "8": 15.2, "9": 16.2, "10": 17.2})

    @staticmethod
    def _rock_cost(rock: dict) -> int:
        """A ROCK_DEFS entry's mana value (armory-protocol names it cast_generic)."""
        return rock.get("cmc", rock.get("cast_generic"))

    def test_every_mana_simulation_plays_the_land_its_turn_1_draw_took(self):
        # Each deck's mana simulation through run_simulation, one game with
        # the shuffle pinned (library order = list order; draws pop the end).
        # Opening seven: two copies of the deck's dearest rock (two mana
        # sources: the hand is kept) and five fillers, no land. On top of the
        # library: the deck's first-colour basic. The turn-1 draw takes it,
        # the land drop plays it, and a rock of mana value 2 or more cannot be
        # cast from one land: one mana on turn 1. zada-hedron-grinder's only
        # rock is Sol Ring ({1}): the land casts one (its rock loop tries each
        # rock once) and that simulation counts untapped lands and rocks on
        # the battlefield: 1 + 2 = 3. With a filler on top and the basic under
        # it (the control), the one turn-1 draw takes the filler and turn 1
        # has no land: 0. Skipping the turn-1 draw, drawing it after the land
        # drop or drawing two on turn 2 would leave turn 1 at 0 too; drawing
        # two on turn 1 would reach the basic in the control.
        root = Path(__file__).resolve().parent.parent
        colors = {deck["id"]: deck["colors"] for deck in json.loads(
            (root / "data" / "index.json").read_text())["commanders"]}
        self.assertTrue(exporter.DECKS)
        for deck_id, _name, _export in exporter.DECKS:
            with self.subTest(deck=deck_id):
                module = importlib.import_module(
                    "mana_simulation_" + deck_id.replace("-", "_"))
                rock = max(sorted(module.ROCK_DEFS),
                           key=lambda name: self._rock_cost(module.ROCK_DEFS[name]))
                cost = self._rock_cost(module.ROCK_DEFS[rock])
                land = self.BASIC[colors[deck_id][0]]
                metadata = {land: CARDS[land], self.FILLER: self.FILLER_CARD,
                            rock: {"type_line": "Artifact", "mana_cost": "{%d}" % cost,
                                   "cmc": float(cost), "oracle_text": "", "colors": []}}
                turn_one = {}
                for top, under in ((land, self.FILLER), (self.FILLER, land)):
                    decklist = ([self.FILLER] * 19 + [under, top] + [self.FILLER] * 5
                                + [rock] * 2)
                    args = (decklist, metadata)
                    if deck_id == "hidden-legion":
                        args += (set(), set(), set())  # no changelings, Dragons or Elves
                    with patch("random.shuffle"):
                        stats = module.run_simulation(*args, num_games=1)
                    turn_one[top] = stats["mana_by_turn"][1]
                expected = [3] if deck_id == "zada-hedron-grinder" else [1]
                self.assertEqual(turn_one, {land: expected, self.FILLER: [0]})


class ManaSimMulliganBottomTests(unittest.TestCase):
    """A paid mulligan in each mana simulation puts its card on the bottom of
    the library, so it is drawn after every other card (owner-approved
    2026-11-23). The position is the one the goldfish has used since
    92254668. Which card is bottomed is unchanged: each mana simulation keeps
    its own existing selector, which differs from the goldfish's (the
    goldfish keeps the cards its combo checks take from the hand until last,
    prefers interaction, and bottoms a land from a seven of five or more
    lands)."""

    BASIC = TurnOneDrawTests.BASIC
    # Made up: a sorcery with no mana cost (mana value 0), which no mana
    # simulation counts as castable, and a {9} sorcery, castable with nine
    # lands.
    BLANK = "Probe Blank"
    BLANK_CARD = {"type_line": "Sorcery", "mana_cost": "", "cmc": 0.0,
                  "oracle_text": "", "colors": []}
    NINE = "Probe Nine Sorcery"
    NINE_CARD = {"type_line": "Sorcery", "mana_cost": "{9}", "cmc": 9.0,
                 "oracle_text": "", "colors": []}

    def test_every_mana_simulation_draws_the_bottomed_card_last(self):
        # Each deck's mana simulation through run_simulation, one game with
        # the shuffle pinned (library order = list order; draws pop the end).
        # The deck: nine of its first-colour basic under a seven of six
        # Probe Blanks and the {9} sorcery. The seven has no mana source, so
        # it is mulliganed twice (the pinned shuffle deals it again each
        # time) and kept on the paid mulligan, which bottoms the most
        # expensive spell: the {9} sorcery, under the nine basics. The
        # library is then ten cards and the game draws one a turn from turn
        # 1: the basics on turns 1-9 (one land a turn, one mana each), the
        # {9} sorcery on turn 10, the last card. Mana on turns 1-10: 1, 2,
        # ..., 9, 9. Castable spells: none on turns 1-9 (the Blanks never
        # count, and the sorcery is still in the library on turn 9, the
        # first turn with nine mana), the sorcery on turn 10.
        # On the top of the library instead it would be drawn on turn 1:
        # mana 0, 1, ..., 9. Lost instead of bottomed, turn 10 would have
        # nothing castable; kept in hand as well, turn 9 would.
        root = Path(__file__).resolve().parent.parent
        colors = {deck["id"]: deck["colors"] for deck in json.loads(
            (root / "data" / "index.json").read_text())["commanders"]}
        self.assertTrue(exporter.DECKS)
        for deck_id, _name, _export in exporter.DECKS:
            with self.subTest(deck=deck_id):
                module = importlib.import_module(
                    "mana_simulation_" + deck_id.replace("-", "_"))
                land = self.BASIC[colors[deck_id][0]]
                metadata = {land: CARDS[land], self.BLANK: self.BLANK_CARD,
                            self.NINE: self.NINE_CARD}
                args = ([land] * 9 + [self.NINE] + [self.BLANK] * 6, metadata)
                if deck_id == "hidden-legion":
                    args += (set(), set(), set())  # no changelings, Dragons or Elves
                with patch("random.shuffle"):
                    stats = module.run_simulation(*args, num_games=1)
                self.assertEqual(
                    (dict(stats["mulligan_attempts"]),
                     [stats["mana_by_turn"][turn] for turn in range(1, 11)],
                     [stats["castable_spell_by_turn"][turn] for turn in range(1, 11)]),
                    ({2: 1}, [[1], [2], [3], [4], [5], [6], [7], [8], [9], [9]],
                     [0, 0, 0, 0, 0, 0, 0, 0, 0, 1]))


class XSpellGoldfishTests(unittest.TestCase):
    """X spells through the goldfish turn loop (owner-approved 2026-11-18).

    One simulate_goldfish_game run per case with the opening fixed instead of
    shuffled, as in DrawEngineGoldfishTests; card data from CARDS. Unless a
    case says otherwise the commander is The Ur-Dragon, which the lands here
    can never cast, the deck has no engine config and every land enters
    untapped. library.pop() draws from the end, so `_library_with(card, turn)`
    puts `card` where the draw step of `turn` finds it. Combat: a creature
    scores min(8, mana value) plus one for a listed keyword ("Flying"; the
    lower-case "trample" of Primordial Hydra and Stonecoil Serpent is not
    one), from the turn after it is cast.
    """

    def _run(self, hand, library, commander="The Ur-Dragon", colors=("G", "U"),
             deck_id="synthetic-x", threats=()):
        """One pinned game: (by_turn, library size at each land choice and
        after turn 10). `threats` go in a guide category, which makes them
        threats as a deck's categories do."""
        decklist = hand + library
        deck_data = {"decklist": [], "guideContent": {"deckCategories": [
            {"name": "Big Creatures", "cards": list(threats)}]}}
        context = exporter.build_goldfish_context(
            decklist, deck_data, CARDS, commander, list(colors), deck_id)
        sizes = []
        choose_land = exporter.choose_land_to_play

        def record_then_choose(*args, **kwargs):
            sizes.append(len(library))
            return choose_land(*args, **kwargs)

        with patch.object(exporter, "commander_mulligan_goldfish",
                          return_value=(library, hand)), \
                patch.object(exporter, "choose_land_to_play",
                             side_effect=record_then_choose):
            by_turn, _ = exporter.simulate_goldfish_game(decklist, context, 6)
        return by_turn, sizes + [len(library)]

    @staticmethod
    def _library_with(card, turn, land):
        """92 cards: `card` is drawn on `turn` (1-10; one draw step a turn
        from turn 1), lands everywhere else."""
        return [land] * (92 - turn) + [card] + [land] * (turn - 1)

    @staticmethod
    def _damage(by_turn):
        return [by_turn[turn]["cumulativeDamage"] for turn in range(1, 11)]

    def test_an_x_spell_below_x_one_stays_in_hand(self):
        # Forests only. Turn 2's {G}{G} pays the pips but leaves X = 0, so the
        # Hydra stays in hand; turn 3 casts it with X = 1: combat and impact
        # (a threat's impact is max(2, min(8, mana value)), nothing else on
        # this card adds to it) read mana value 2 + 1 = 3.
        by_turn, _ = self._run(["Primordial Hydra"] + ["Forest"] * 6,
                               ["Forest"] * 92, threats=["Primordial Hydra"])
        self.assertEqual(self._damage(by_turn), [0, 0, 0, 3, 6, 9, 12, 15, 18, 21])
        self.assertEqual(by_turn[3]["pressure"], 3)

    def test_x_is_the_mana_left_where_the_spell_sits_in_the_cast_order(self):
        # Turn 3 draws Stonecoil Serpent with three Forests out. Neither is a
        # threat here (mana value below 3, no category); both sort as
        # permanents of impact 0 and the Hydra (mana value 2) goes first: it
        # takes all three Forests (X = 1, combat 3) and leaves the Serpent
        # X = 0, so it waits for turn 4 and four Forests (X = 4, combat 4).
        # Damage: Hydra from turn 4, Serpent from turn 5.
        by_turn, _ = self._run(["Primordial Hydra"] + ["Forest"] * 6,
                               self._library_with("Stonecoil Serpent", 3, "Forest"))
        self.assertEqual(self._damage(by_turn), [0, 0, 0, 3, 10, 17, 24, 31, 38, 45])

    def test_pips_need_their_colour_and_x_takes_any_source(self):
        # Hand lands: two Forests and four Islands; the library holds only
        # Zero Trinkets ({0}, no combat), so the hand's six lands are all the
        # lands. Land choice: Island turn 1 (a tie broken by name), Forest
        # turn 2 (new colour), Islands turns 3-5, the second Forest turn 6.
        # The {G}{G} is payable only on turn 6, and X takes the four Islands:
        # X = 4, combat min(8, 2 + 4) = 6 from turn 7.
        by_turn, _ = self._run(
            ["Primordial Hydra", "Forest", "Forest", "Island", "Island",
             "Island", "Island"],
            ["Zero Trinket"] * 92)
        self.assertEqual(self._damage(by_turn), [0, 0, 0, 0, 0, 0, 6, 12, 18, 24])

    def test_xx_costs_two_per_x_and_mathemagics_draws_two_to_the_x(self):
        # Mathemagics ({X}{X}{U}{U}) is drawn on turn 8 with eight Islands:
        # X = (8 - 2) / 2 = 3, so it draws 2^3 = 8. Each turn's draw step
        # takes one card from turn 1. The first of the eight is Stonecoil
        # Serpent ({X}): Mathemagics paid 2 + 2 x 3 = 8, all eight Islands, so
        # the Serpent gets X = 0 and waits for turn 9, where nine Islands make
        # X = 9 (combat min(8, 9) = 8, from turn 10).
        library = ["Island"] * 83 + ["Stonecoil Serpent", "Mathemagics"] + ["Island"] * 7
        by_turn, sizes = self._run(["Island"] * 7, library, colors=("U",))
        self.assertEqual(sizes, [91, 90, 89, 88, 87, 86, 85, 84, 75, 74, 74])
        self.assertEqual(self._damage(by_turn), [0] * 9 + [8])

    # (card, turn it is drawn and cast with that many Command Towers,
    #  commander, library size at each land choice and after turn 10).
    # Command Tower taps for either colour. The library holds 92 and the draw
    # step takes one card a turn from turn 1 (91 at turn 1, 82 at turn 10);
    # the spell's N cards leave it after its turn's land choice, so each
    # later reading is N lower.
    DRAW_CASES = [
        # {X}{G}{U} with five lands: X = 3, "Draw X cards.": 3 cards.
        ("Mind into Matter", 5, "The Ur-Dragon",
         [91, 90, 89, 88, 87, 83, 82, 81, 80, 79, 79]),
        # {X}{U}{U}, five lands: X = 3, "Draw X cards, then discard a card.": 3.
        ("Pull from Tomorrow", 5, "The Ur-Dragon",
         [91, 90, 89, 88, 87, 83, 82, 81, 80, 79, 79]),
        # {X}{U}{U}{U}{U}, six lands: X = 2, "Draw X cards.": 2.
        ("Transcendent Message", 6, "The Ur-Dragon",
         [91, 90, 89, 88, 87, 86, 83, 82, 81, 80, 80]),
        # {X}{G}{U}, seven lands: X = 5, "draw half X cards. Round down": 2.
        ("Hydroid Krasis", 7, "The Ur-Dragon",
         [91, 90, 89, 88, 87, 86, 85, 82, 81, 80, 80]),
        # {X}{U}{U}, seven lands: X = 5, "draw half X cards, rounded down": 2.
        ("Wan Shi Tong, Librarian", 7, "The Ur-Dragon",
         [91, 90, 89, 88, 87, 86, 85, 82, 81, 80, 80]),
        # {X}{U}{U}{U}, six lands: X = 3, plus one per commander cast; The
        # Ur-Dragon is never cast here: 3.
        ("Commander's Insight", 6, "The Ur-Dragon",
         [91, 90, 89, 88, 87, 86, 82, 81, 80, 79, 79]),
        # Probe Commander ({5}) is cast on turn 5, so X = 3 plus one: 4.
        ("Commander's Insight", 6, "Probe Commander",
         [91, 90, 89, 88, 87, 86, 81, 80, 79, 78, 78]),
        # {X}{G}, five lands: X = 4, below "If X is 5 or more, you draw": 0.
        ("Kinetic Ooze", 5, "The Ur-Dragon",
         [91, 90, 89, 88, 87, 86, 85, 84, 83, 82, 82]),
        # Six lands: X = 5: 1.
        ("Kinetic Ooze", 6, "The Ur-Dragon",
         [91, 90, 89, 88, 87, 86, 84, 83, 82, 81, 81]),
    ]

    def test_draw_spells_draw_at_the_paid_x(self):
        for card, turn, commander, expected in self.DRAW_CASES:
            with self.subTest(card=card, turn=turn, commander=commander):
                _, sizes = self._run(
                    ["Command Tower"] * 7,
                    self._library_with(card, turn, "Command Tower"),
                    commander=commander)
                self.assertEqual(sizes, expected)

    def test_creature_combat_is_capped_at_eight_plus_the_keyword(self):
        # Hydroid Krasis drawn on turn 9 with nine Command Towers: X = 7,
        # mana value 2 + 7 = 9, capped at 8, plus one for Flying = 9 on turn 10.
        by_turn, _ = self._run(["Command Tower"] * 7,
                               self._library_with("Hydroid Krasis", 9, "Command Tower"))
        self.assertEqual(self._damage(by_turn), [0] * 9 + [9])

    def test_amass_x_spells_amass_the_x_paid(self):
        # gathering-shadow's amass engine; the commander is never cast, so no
        # opponent-cast amass. Summons of Saruman ({X}{U}{R}) on turn 5 with
        # five towers: X = 3. Assault on Osgiliath ({X}{R}{R}{R}) on turn 6
        # with six: X = 3. The Army attacks for 3 from the next turn.
        for card, turn, damage in (
                ("Summons of Saruman", 5, [0, 0, 0, 0, 0, 3, 6, 9, 12, 15]),
                ("Assault on Osgiliath", 6, [0, 0, 0, 0, 0, 0, 3, 6, 9, 12])):
            with self.subTest(card=card):
                by_turn, _ = self._run(
                    ["Command Tower"] * 7,
                    self._library_with(card, turn, "Command Tower"),
                    colors=("U", "R"), deck_id="gathering-shadow")
                self.assertEqual(self._damage(by_turn), damage)

    def test_saruman_amasses_the_mana_value_with_x(self):
        # Saruman, the White Hand ({1}{U}{B}{R}, combat 4) is cast on turn 4.
        # Summons of Saruman is drawn on turn 6 with six towers: X = 4. It
        # amasses 4, and Saruman's trigger amasses its mana value on the
        # stack, 2 + 4 = 6: an Army of 10 that attacks from turn 7.
        # Damage: 4 on turns 5-6, then 4 + 10 a turn.
        by_turn, _ = self._run(
            ["Saruman, the White Hand"] + ["Command Tower"] * 6,
            self._library_with("Summons of Saruman", 6, "Command Tower"),
            colors=("U", "B", "R"), deck_id="gathering-shadow")
        self.assertEqual(self._damage(by_turn), [0, 0, 0, 0, 4, 8, 22, 36, 50, 64])

    # Springleaf Parade's text grants "{T}: Add" to creature tokens, which
    # would read as a mana source; as an X spell it is none.

    def _parade_game(self):
        """(by_turn, [(turn, card, total mana paid) for each resolution]).

        Springleaf Parade is drawn on turn 5 with five Forests and Probe
        Commander ({5}) in the command zone. Turn 5 casts the commander and
        leaves no mana; turn 6 casts the Parade with six Forests: {G}{G} and
        X = 4, 6 mana in all."""
        casts = []
        original_resolve = exporter.resolve_cast_effects

        def recording_resolve(name, profile, turn, *args, **kwargs):
            casts.append((turn, name, profile["manaCost"]["total"]))
            return original_resolve(name, profile, turn, *args, **kwargs)

        with patch.object(exporter, "resolve_cast_effects", recording_resolve):
            by_turn, _ = self._run(
                ["Forest"] * 7, self._library_with("Springleaf Parade", 5, "Forest"),
                commander="Probe Commander", colors=("G",))
        return by_turn, casts

    def test_an_x_spell_with_a_mana_ability_does_not_sort_ahead_of_the_commander(self):
        # The commander is cast on turn 5 (combat 5 from turn 6) and the
        # Parade waits for turn 6. Sorted as ramp it would take the turn-5
        # mana as X = 3 and push the commander to turn 6.
        by_turn, _ = self._parade_game()
        self.assertEqual(self._damage(by_turn), [0, 0, 0, 0, 0, 5, 10, 15, 20, 25])

    def test_an_x_spell_with_a_mana_ability_is_not_a_ramp_permanent(self):
        # The Parade resolves once, on turn 6, for 6 mana, and is on the
        # battlefield from then on; the ramp count stays 0.
        by_turn, casts = self._parade_game()
        self.assertEqual(
            ([(turn, paid) for turn, name, paid in casts if name == "Springleaf Parade"],
             [by_turn[turn]["ramp"] for turn in range(1, 11)]),
            ([(6, 6)], [0] * 10))

    def test_an_x_spell_with_a_mana_ability_is_not_cheap_ramp_for_the_mulligan(self):
        # The mulligan rule: two lands and no cheap ramp (a mana source or
        # land-ramp spell of mana value 2 or less) is a mulligan. With Mind
        # Stone ({2}, "{T}: Add {C}.") as the third card the hand is kept;
        # with Springleaf Parade in its place it is not.
        hands = {
            "Mind Stone": ["Forest", "Forest", "Mind Stone"] + ["Zero Trinket"] * 4,
            "Springleaf Parade": ["Forest", "Forest", "Springleaf Parade"]
            + ["Zero Trinket"] * 4,
        }
        context = exporter.build_goldfish_context(
            hands["Mind Stone"] + hands["Springleaf Parade"], {"decklist": []},
            CARDS, "Probe Commander", ["G"], "synthetic-x")
        decisions = {card: exporter.should_goldfish_mulligan(hand, context["profiles"])
                     for card, hand in hands.items()}
        self.assertEqual(decisions, {"Mind Stone": False, "Springleaf Parade": True})

    def test_a_copy_of_an_x_spell_keeps_the_x_paid(self):
        # A tap_gate copy engine (one copy of each instant or sorcery while one
        # untapped creature remains; local config, as no fleet deck has one).
        # Probe Commander ({5}) is cast on turn 5 with five Command Towers.
        # Mind into Matter is drawn on turn 6: X = 6 - 2 = 4, so it draws 4
        # and its copy draws 4 more. One card per draw step from turn 1.
        with patch.dict(exporter.COMMANDER_COPY_ENGINE,
                        {"synthetic-copy": {"mode": "tap_gate", "tapCost": 1}}):
            _, sizes = self._run(
                ["Command Tower"] * 7,
                self._library_with("Mind into Matter", 6, "Command Tower"),
                commander="Probe Commander", deck_id="synthetic-copy")
        self.assertEqual(sizes, [91, 90, 89, 88, 87, 86, 77, 76, 75, 74, 74])

    # --- the DEC-944 gate and combo-line pieces ------------------------------

    COMBO_DECK_ID = "synthetic-combo"

    @staticmethod
    def _combo_metadata() -> dict:
        def card(name, type_line, mana_cost, cmc):
            return {"name": name, "type_line": type_line, "oracle_text": "",
                    "mana_cost": mana_cost, "cmc": cmc, "colors": [],
                    "color_identity": []}

        metadata = {
            "Forest": CARDS["Forest"],
            "Stonecoil Serpent": CARDS["Stonecoil Serpent"],
            "Synthetic Commander": card("Synthetic Commander",
                                        "Legendary Creature — Human", "{9}", 9),
            "Piece Permanent": card("Piece Permanent", "Artifact", "{2}", 2),
            "Piece Instant": card("Piece Instant", "Instant", "{2}", 2),
            "X Piece Permanent": card("X Piece Permanent", "Artifact", "{X}{2}", 2),
            "X Piece Instant": card("X Piece Instant", "Instant", "{X}{2}", 2),
            "Bear": card("Bear", "Creature — Bear", "{2}", 2),
        }
        return metadata

    def _run_line(self, pieces, hand, library):
        """Pinned game with one combo win condition; (by_turn, casts by turn)."""
        metadata = self._combo_metadata()
        decklist = hand + library
        deck_data = {
            "decklist": [{"name": name} for name in decklist],
            "winConditions": [{"kind": "combo", "pieces": list(pieces)}],
        }
        context = exporter.build_goldfish_context(
            decklist, deck_data, metadata, "Synthetic Commander", ["G"],
            self.COMBO_DECK_ID)
        casts = defaultdict(list)
        original_resolve = exporter.resolve_cast_effects

        def recording_resolve(name, profile, turn, *args, **kwargs):
            casts[turn].append(name)
            return original_resolve(name, profile, turn, *args, **kwargs)

        with patch.object(exporter, "commander_mulligan_goldfish",
                          lambda *_: (list(library), list(hand))), \
                patch.object(exporter, "resolve_cast_effects", recording_resolve):
            by_turn, _ = exporter.simulate_goldfish_game(
                decklist, context, 6)
        return by_turn, casts

    def test_an_x_spell_pays_x_only_out_of_mana_the_gate_does_not_need(self):
        # Turn 2 casts the permanent piece. Turn 3 draws Stonecoil Serpent
        # with three Forests: the gate still needs {2} for the instant piece,
        # so the Serpent takes X = 1 (combat 1), not 3, and the gate fires.
        by_turn, casts = self._run_line(
            ["Piece Permanent", "Piece Instant"],
            ["Forest"] * 3 + ["Piece Permanent", "Piece Instant"],
            ["Forest"] * 16 + ["Stonecoil Serpent", "Forest", "Forest"])
        self.assertEqual(casts[3], ["Stonecoil Serpent"])
        self.assertEqual(by_turn[3]["comboLethal"], 1)
        self.assertEqual(by_turn[4]["combat"], 1)

    def test_a_combo_line_piece_with_x_is_cast_at_x_zero(self):
        # The line's permanent piece costs {X}{2}. Line pieces are cast freely
        # at X = 0, so it lands on turn 2 out of two Forests; under the X rule
        # it would need a third mana.
        by_turn, casts = self._run_line(
            ["X Piece Permanent", "Piece Instant"],
            ["Forest"] * 3 + ["X Piece Permanent", "Piece Instant"],
            ["Forest"] * 18)
        # Cast on turn 2, and the gate fires on turn 3 with {2} for the
        # instant piece.
        self.assertEqual((casts[2], by_turn[3]["comboLethal"]),
                         (["X Piece Permanent"], 1))

    def test_the_gate_prices_a_combo_line_piece_with_x_at_x_zero(self):
        # Two Forests in all (the library holds Bears). Turn 2 casts the
        # permanent piece; on turn 3 the {X}{2} instant piece is priced at
        # {2}, which the two Forests pay, so the Bear is held and the gate
        # fires.
        by_turn, casts = self._run_line(
            ["Piece Permanent", "X Piece Instant"],
            ["Forest"] * 2 + ["Piece Permanent", "X Piece Instant"],
            ["Bear"] * 20)
        self.assertEqual((casts[3], by_turn[3]["comboLethal"]), ([], 1))

    # --- methodology ---------------------------------------------------------

    # The X paragraph: the policy, then this deck's own credits, then the
    # floors. Every deck gets the policy and the creature sentence; only a
    # deck with X_SPELL_DRAW cards names them, only the amass deck gets the
    # amass sentence.
    X_POLICY = (
        " X spells modeled (owner-approved 2026-11-18): a spell with {X} in its "
        "mana cost keeps its place in the cast order (never the ramp tier) and, "
        "when reached, is cast with X = the largest value the mana left pays "
        "after its coloured pips and the holds above, with no mana-source "
        "exemption; {X}{X} costs two per X. Below X = 1 it stays in hand and the "
        "next spell is tried. Combo-line pieces and KEY_COMBOS assembly members "
        "are still cast at X = 0, and the combo gate prices its pieces at X = 0. "
        "Credited at the paid X: a creature's combat, and a threat creature's "
        "pressure score, read mana value + X (capped at 8, keyword bonus as "
        "before)")
    X_FLOORS = (
        ". Every other X effect (tokens, life loss, damage, tutoring, pumps, "
        "proliferate, recursion, manifest) is not credited: those spells are only "
        "re-timed. Floors: convoke, improvise and cost reducers are not "
        "modeled.")
    X_DRAWS = "; cards drawn: Mathemagics 2^X, Mind into Matter X"
    X_AMASS = ("; amass X spells amass X, and Saruman, the White Hand's amass "
               "counts the X paid")

    def _methodology(self, decklist, win_conditions=(), roles=None,
                     deck_id="synthetic-x"):
        roles = roles or {}
        deck_data = {"decklist": [dict({"name": name}, **roles.get(name, {}))
                                  for name in decklist],
                     "winConditions": list(win_conditions)}
        with patch.object(exporter, "GOLDFISH_GAMES", 16), \
                patch("multiprocessing.Pool", SerialPool):
            goldfish, _ = exporter.compute_goldfish_section(
                decklist=decklist, deck_data=deck_data, metadata=CARDS,
                commander_name="The Ur-Dragon", commander_colors=["G", "U"],
                deck_id=deck_id)
        return goldfish["methodology"]

    def test_methodology_names_only_the_decks_own_x_credits(self):
        cases = {
            # Stonecoil Serpent is in no table: the policy alone.
            "no draw card": (["Stonecoil Serpent"] + ["Forest"] * 98,
                             "synthetic-x", self.X_POLICY + self.X_FLOORS),
            # Two X_SPELL_DRAW cards, named in the table's words, by name.
            "draw cards": (["Mind into Matter", "Mathemagics", "Stonecoil Serpent"]
                           + ["Forest"] * 96, "synthetic-x",
                           self.X_POLICY + self.X_DRAWS + self.X_FLOORS),
            # gathering-shadow's amass engine.
            "amass deck": (["Summons of Saruman"] + ["Forest"] * 98,
                           "gathering-shadow",
                           self.X_POLICY + self.X_AMASS + self.X_FLOORS),
        }
        for label, (decklist, deck_id, paragraph) in cases.items():
            with self.subTest(label):
                self.assertIn(paragraph, self._methodology(decklist, deck_id=deck_id))

    def test_methodology_scores_x_creatures_with_x_only_where_x_spells_are_cast(self):
        with_x = self._methodology(["Stonecoil Serpent"] + ["Forest"] * 98)
        without_x = self._methodology(["Forest"] * 99)
        self.assertEqual(
            ("plus one for a listed combat keyword, MV + X for an X creature cast "
             "with X paid) so the curve" in with_x,
             "plus one for a listed combat keyword) so the curve" in without_x),
            (True, True))

    # A combo line of two non-X permanents, so the deck builds its tutor and
    # reanimation tables.
    PLAIN_COMBO = [{"kind": "combo", "pieces": ["Zero Trinket", "Mind Stone"]}]

    def test_methodology_leaves_the_x_rule_out_when_no_x_spell_is_cast(self):
        cases = {
            "no X card": (["Forest"] * 99, (), None),
            "X cards that are combo-line pieces": (
                ["Stonecoil Serpent", "Primordial Hydra"] + ["Forest"] * 97,
                [{"kind": "combo",
                  "pieces": ["Stonecoil Serpent", "Primordial Hydra"]}], None),
            # "Counter target spell": interaction, never cast.
            "an interaction X card": (["Syncopate"] + ["Forest"] * 98, (), None),
            "a reserved X tutor": (
                ["Whir of Invention", "Zero Trinket", "Mind Stone"] + ["Forest"] * 96,
                self.PLAIN_COMBO,
                {"Whir of Invention": {"primary_role": "tutor"}}),
            "a reserved X reanimation spell": (
                ["Divergent Equation", "Zero Trinket", "Mind Stone"] + ["Forest"] * 96,
                self.PLAIN_COMBO,
                {"Divergent Equation": {"primary_role": "recursion"}}),
        }
        for label, (decklist, win_conditions, roles) in cases.items():
            with self.subTest(label):
                self.assertNotIn("X spells modeled", self._methodology(
                    decklist, win_conditions, roles))

    def test_methodology_states_a_combo_lines_min_x(self):
        # Stonecoil Serpent is cast under the X rule; Walking Ballista, which
        # the cast loop never casts (its ping reads as interaction), is a line
        # piece priced at X = 2 by the line's minX.
        decklist = ["Stonecoil Serpent", "Walking Ballista", "Mind Stone"] + ["Forest"] * 96
        line = {"kind": "combo", "pieces": ["Walking Ballista", "Mind Stone"]}
        min_x_sentence = (
            " A combo line's X piece (winConditions[].minX, owner-approved 2026-11-19) is priced at the "
            "X of the cheapest direct cast with which the line's listed pieces work: Walking Ballista at "
            "X = 2 (each {X} in its cost is X mana). It is supplied from the hand or by a tutor the tags "
            "read as to-hand (a bargain tutor by its paid route to the hand); a card with the recursion "
            "role, a tutor to the graveyard and a bargain free cast do not supply it. Known limits: "
            "recursion that returns the card to the hand is excluded with the rest (an under-read), a "
            "tutor the tags read as to-hand whose text does not put a castable copy into the hand that turn "
            "(it puts the card onto the battlefield, on top of the library, or cannot find it) still "
            "supplies it (an over-read), and an X piece already on the battlefield counts whatever X it "
            "entered with.")
        priced = self._methodology(decklist, [dict(line, minX={"Walking Ballista": 2})])
        plain = self._methodology(decklist, [line])
        self.assertEqual(
            (min_x_sentence in priced,
             self.X_POLICY.replace("pieces at X = 0. ", "pieces at X = 0 except the X pieces above. ") in priced,
             "A combo line's X piece" in plain, self.X_POLICY in plain),
            (True, True, False, True))


class ArmyReadinessGoldfishTests(unittest.TestCase):
    """DEC-533 Army readiness: an Army made by the start-of-turn opponent-cast
    amass attacks that turn; any other amass source's Army waits a turn.

    gathering-shadow's amass engine (3 opponent batches of 1 a turn while the
    commander is out), the opening fixed as in DrawEngineGoldfishTests, card
    data from CARDS. Probe Commander ({5}, combat 5) is cast on turn 5 and
    attacks from turn 6. The hand never drops to 2 cards, so no Ring tempt
    converts.
    """

    def _damage(self, hand, library, colors):
        decklist = hand + library
        context = exporter.build_goldfish_context(
            decklist, {"decklist": []}, CARDS, "Probe Commander", list(colors),
            "gathering-shadow")
        with patch.object(exporter, "commander_mulligan_goldfish",
                          return_value=(library, hand)):
            by_turn, _ = exporter.simulate_goldfish_game(decklist, context, 6)
        return [by_turn[turn]["cumulativeDamage"] for turn in range(1, 11)]

    def test_an_army_from_opponent_casts_attacks_the_turn_it_is_made(self):
        # Turn 6 starts with the commander out: three batches make an Army of
        # 3 that swings with the commander (5 + 3); each later turn adds 3.
        self.assertEqual(
            self._damage(["Island"] * 7, ["Island"] * 92, ("U", "B")),
            [0, 0, 0, 0, 0, 8, 19, 33, 50, 70])

    def test_an_army_from_an_own_cast_still_waits_a_turn(self):
        # Swarming of Moria ({2}{R}) is cast on turn 3 and amasses 2: the
        # Army is made during turn 3 and first attacks on turn 4. From turn 6
        # the opponent batches add 3 a turn and the commander swings for 5.
        self.assertEqual(
            self._damage(["Swarming of Moria"] + ["Mountain"] * 6,
                         ["Mountain"] * 92, ("B", "R")),
            [0, 0, 0, 2, 4, 14, 27, 43, 62, 84])


class TokenMakerGoldfishTests(unittest.TestCase):
    """TOKEN_MAKER_ENGINE (owner-approved 2026-11-18) through the goldfish loop.

    stampede-acres' shipped config. One simulate_goldfish_game run per case
    with the opening fixed instead of shuffled, as in DrawEngineGoldfishTests;
    card data from CARDS. Unless a case says otherwise the lands are Command
    Towers (any of red, green and white), one played each turn, and the
    commander is The Ur-Dragon, which they never cast. library.pop() draws
    from the end. Combat: a creature card scores min(8, mana value) from the
    turn after it is cast; a creature token deals 1, plus one per anthem, from
    the turn after it is made, or from the turn it is made when it enters
    tapped and attacking. Baylen, the Haymaker's cards are seen as drops in
    the library size, read at each turn's land choice (after that turn's
    draws) and once after turn 10.
    """

    DECK_ID = "stampede-acres"

    def _run(self, hand, library, commander="The Ur-Dragon", colors=("R", "G", "W")):
        """(cumulative damage on turns 1-10, library sizes)."""
        decklist = hand + library
        context = exporter.build_goldfish_context(
            decklist, {"decklist": []}, CARDS, commander, list(colors), self.DECK_ID)
        sizes = []
        choose_land = exporter.choose_land_to_play

        def record_then_choose(*args, **kwargs):
            sizes.append(len(library))
            return choose_land(*args, **kwargs)

        with patch.object(exporter, "commander_mulligan_goldfish",
                          return_value=(library, hand)), \
                patch.object(exporter, "choose_land_to_play",
                             side_effect=record_then_choose):
            by_turn, _ = exporter.simulate_goldfish_game(decklist, context, 6)
        return ([by_turn[turn]["cumulativeDamage"] for turn in range(1, 11)],
                sizes + [len(library)])

    @staticmethod
    def _library_with(card, turn, land="Command Tower"):
        """92 cards: `card` is drawn on `turn` (1-10; one draw step a turn
        from turn 1), lands everywhere else."""
        return [land] * (92 - turn) + [card] + [land] * (turn - 1)

    def test_a_fixed_makers_tokens_attack_from_the_next_turn_with_the_anthem(self):
        # Frontline Rush ({R}{W}) on turn 2 makes two Goblins; Warleader's
        # Call ({1}{R}{W}, "Creatures you control get +1/+1.") on turn 3.
        # From turn 3 the Goblins deal 2 x (1 + 1) = 4 a turn.
        damage, _ = self._run(["Frontline Rush", "Warleader's Call"]
                              + ["Command Tower"] * 5, ["Command Tower"] * 92)
        self.assertEqual(damage, [0, 0, 4, 8, 12, 16, 20, 24, 28, 32])

    def test_each_fixed_maker_makes_its_tokens_and_food_never_attacks(self):
        # Prosperous Partnership ({1}{R}{W}) on turn 3: two Citizens, 2 a turn
        # from turn 4. Staff of the Storyteller ({1}{W}) on turn 2: one
        # Spirit, 1 a turn from turn 3. Frontline Rush on turn 2 (two Goblins)
        # and Rosie Cotton ({2}{W}, combat 3) on turn 3, whose Food never
        # attacks: 2 on turn 3, then 2 + 3 a turn.
        cases = {
            "Prosperous Partnership": (["Prosperous Partnership"],
                                       [0, 0, 0, 2, 4, 6, 8, 10, 12, 14]),
            "Staff of the Storyteller": (["Staff of the Storyteller"],
                                         [0, 0, 1, 2, 3, 4, 5, 6, 7, 8]),
            "Rosie Cotton's Food": (["Rosie Cotton of South Lane", "Frontline Rush"],
                                    [0, 0, 2, 7, 12, 17, 22, 27, 32, 37]),
        }
        for label, (spells, damage) in cases.items():
            with self.subTest(label):
                hand = spells + ["Command Tower"] * (7 - len(spells))
                self.assertEqual(self._run(hand, ["Command Tower"] * 92)[0], damage)

    def test_x_token_spells_make_x_and_twice_x(self):
        # Secure the Wastes ({X}{W}) drawn on turn 4 with four towers: X = 3,
        # three Warriors. Pest Infestation ({X}{X}{G}) drawn on turn 5 with
        # five: X = 2, twice X = four Pests. Each attacks from the next turn.
        for card, turn, damage in (
                ("Secure the Wastes", 4, [0, 0, 0, 0, 3, 6, 9, 12, 15, 18]),
                ("Pest Infestation", 5, [0, 0, 0, 0, 0, 4, 8, 12, 16, 20])):
            with self.subTest(card=card):
                self.assertEqual(self._run(["Command Tower"] * 7,
                                           self._library_with(card, turn))[0], damage)

    def test_adelines_tokens_attack_the_turn_they_are_made_and_keep_attacking(self):
        # Adeline ({1}{W}{W}, combat 3) is cast on turn 3 and attacks from
        # turn 4; each attack makes three Humans tapped and attacking. Turn t
        # (t >= 4) deals 3 + 3 x (t - 3): 6, 9, 12, 15, 18, 21, 24.
        damage, _ = self._run(["Adeline, Resplendent Cathar"] + ["Command Tower"] * 6,
                              ["Command Tower"] * 92)
        self.assertEqual(damage, [0, 0, 0, 6, 15, 27, 42, 60, 81, 105])

    def test_anim_pakal_makes_one_more_gnome_each_attack(self):
        # Anim Pakal ({1}{R}{W}, combat 3) is cast on turn 3; his k-th attack
        # (turn 3 + k) makes k Gnomes tapped and attacking, which keep
        # attacking: turn t deals 3 + (1 + 2 + ... + (t - 3)): 4, 6, 9, 13, 18,
        # 24, 31.
        damage, _ = self._run(["Anim Pakal, Thousandth Moon"] + ["Command Tower"] * 6,
                              ["Command Tower"] * 92)
        self.assertEqual(damage, [0, 0, 0, 4, 10, 19, 32, 50, 74, 105])

    def test_landfall_counts_only_the_natural_land_drop_after_the_cast(self):
        # Forests only. Scute Swarm ({2}{G}, combat 3) is cast on turn 3,
        # after that turn's land drop. Turn 4 draws Nature's Lore: the land
        # drop makes an Insect, and the Forest the Lore puts onto the
        # battlefield makes none. One Insect per drop from then on, each
        # attacking from the next turn: turn t (t >= 4) deals 3 + (t - 4).
        damage, _ = self._run(["Scute Swarm"] + ["Forest"] * 6,
                              self._library_with("Nature's Lore", 4, "Forest"),
                              colors=("G",))
        self.assertEqual(damage, [0, 0, 0, 3, 7, 12, 18, 25, 33, 42])

    def test_each_doubler_doubles_the_tokens(self):
        # One doubler: Anointed Procession ({3}{W}) on turn 4; Frontline Rush,
        # drawn on turn 5, makes 2 x 2 = four Goblins, attacking from turn 6.
        # Two: Mondrak ({2}{W}{W}, combat 4 from turn 5) on turn 4, Anointed
        # Procession on turn 5; Rush, drawn on turn 6, makes 2 x 2 x 2 = eight
        # Goblins: 4 a turn, then 4 + 8 from turn 7.
        cases = {
            "one doubler": (["Anointed Procession"], 5,
                            [0, 0, 0, 0, 0, 4, 8, 12, 16, 20]),
            "two doublers": (["Anointed Procession", "Mondrak, Glory Dominus"], 6,
                             [0, 0, 0, 0, 4, 8, 20, 32, 44, 56]),
        }
        for label, (doublers, turn, damage) in cases.items():
            with self.subTest(label):
                hand = doublers + ["Command Tower"] * (7 - len(doublers))
                self.assertEqual(
                    self._run(hand, self._library_with("Frontline Rush", turn))[0], damage)

    def test_peregrin_adds_one_food_and_then_the_doubler_doubles_it(self):
        # Commander Baylen. Turn 3 Baylen, turn 4 Peregrin Took, turn 5
        # Anointed Procession; Frontline Rush, drawn on turn 6, is one event:
        # two Goblins plus Peregrin's Food, then doubled: four Goblins and two
        # Food. None attacked on turn 6, so Baylen draws 6 // 3 = 2 before
        # turn 7. From turn 7 the Goblins attack and the two Food alone draw
        # nothing. Doubling before the Food (four Goblins, one Food), no Food,
        # or no doubling would each leave five tokens or fewer: one card.
        # Library of 92, one draw step a turn from turn 1: 91 at turn 1's land
        # choice, ..., 86 at turn 6's; turn 7 takes Baylen's 2 and its draw
        # step: 86 - 3 = 83; then 82, 81, 80, and 80 after turn 10.
        _, sizes = self._run(
            ["Peregrin Took", "Anointed Procession"] + ["Command Tower"] * 5,
            self._library_with("Frontline Rush", 6), commander="Baylen, the Haymaker")
        self.assertEqual(sizes, [91, 90, 89, 88, 87, 86, 83, 82, 81, 80, 80])

    def test_food_made_with_attacking_tokens_enters_tapped(self):
        # Commander Baylen on turn 3, Adeline on turn 4 (she sorts ahead of
        # Peregrin Took by name), Peregrin on turn 5. From turn 5 each attack
        # makes three Humans, tapped and attacking, and one Food, which enters
        # tapped. Untapped tokens at the end of turns 5-9: 0, 1, 2, 3, 4 Food
        # (the Humans attacked), so Baylen draws one card before turn 9 and
        # one before turn 10. Counting the tapped Food would draw before
        # turns 8, 9 and 10.
        # With Anointed Procession too (turn 6): from turn 6 each attack makes
        # six Humans and two Food, both tapped. Food at the end of turns 5-9:
        # 1, 3, 5, 7, 9, of which 1, 2, 2, 2, 2 entered tapped that turn, so
        # 0, 1, 3, 5, 7 untapped: one card before turns 8 and 9, two before
        # turn 10. Counting one tapped Food per event would give 0, 2, 4, 6, 8:
        # one before turn 8, two before turns 9 and 10.
        # Library sizes at each land choice and after turn 10: 92 less one
        # draw step a turn from turn 1 (91 at turn 1) and Baylen's cards. No
        # doubler: 91 ... 84 at turn 8; turn 9: 84 - 1 - 1 = 82; turn 10:
        # 82 - 1 - 1 = 80. A doubler: 91 ... 85 at turn 7; turn 8: 85 - 1 - 1
        # = 83; turn 9: 83 - 1 - 1 = 81; turn 10: 81 - 2 - 1 = 78.
        cases = {
            "no doubler": (["Adeline, Resplendent Cathar", "Peregrin Took"],
                           [91, 90, 89, 88, 87, 86, 85, 84, 82, 80, 80]),
            "a doubler": (["Adeline, Resplendent Cathar", "Peregrin Took",
                           "Anointed Procession"], [91, 90, 89, 88, 87, 86, 85, 83, 81, 78, 78]),
        }
        for label, (spells, expected) in cases.items():
            with self.subTest(label):
                _, sizes = self._run(
                    spells + ["Command Tower"] * (7 - len(spells)),
                    ["Command Tower"] * 92, commander="Baylen, the Haymaker")
                self.assertEqual(sizes, expected)

    def test_draconic_visitor_stops_new_food_and_keeps_the_old(self):
        # Commander Baylen on turn 3. New Food: Peregrin Took on turn 4,
        # Draconic Visitor ({3}{R}{R}) on turn 5; Frontline Rush, drawn on turn
        # 6, makes two Goblins, and Peregrin's Food would be a Dragon the engine
        # does not credit: two untapped tokens, no card (three, one card, if
        # the Food counted). Old Food: Rosie Cotton on turn 4 makes a Food;
        # Visitor is drawn and cast on turn 5 and Rush on turn 6: the Food and
        # two Goblins are untapped at the end of turn 6, one card before turn 7.
        # Library sizes: 92 less one draw step a turn from turn 1 (91 at turn
        # 1, 82 at turn 10); with the old Food, turn 7 also takes Baylen's
        # card: 86 - 1 - 1 = 84, then 83, 82, 81.
        tower = "Command Tower"
        cases = {
            "new Food": (["Peregrin Took", "Draconic Visitor"],
                         self._library_with("Frontline Rush", 6),
                         [91, 90, 89, 88, 87, 86, 85, 84, 83, 82, 82]),
            "old Food": (["Rosie Cotton of South Lane"],
                         [tower] * 86 + ["Frontline Rush", "Draconic Visitor"] + [tower] * 4,
                         [91, 90, 89, 88, 87, 86, 84, 83, 82, 81, 81]),
        }
        for label, (spells, library, expected) in cases.items():
            with self.subTest(label):
                _, sizes = self._run(spells + [tower] * (7 - len(spells)), library,
                                     commander="Baylen, the Haymaker")
                self.assertEqual(sizes, expected)

    def test_baylen_draws_per_three_tokens_that_did_not_attack_while_he_is_out(self):
        # Secure the Wastes drawn on turn 7 with seven towers: X = 6, six
        # Warriors. With Baylen cast on turn 3 they are untapped at the end of
        # turn 7: 6 // 3 = 2 cards before turn 8; from turn 8 they attack and
        # draw nothing. With a commander that is never cast, no cards.
        # Library sizes: 92 less one draw step a turn from turn 1 (91 at turn
        # 1, 82 at turn 10); with Baylen, turn 8 also takes his 2: 85 - 2 - 1
        # = 82, then 81, 80.
        library = self._library_with("Secure the Wastes", 7)
        for commander, expected in (
                ("Baylen, the Haymaker", [91, 90, 89, 88, 87, 86, 85, 82, 81, 80, 80]),
                ("The Ur-Dragon", [91, 90, 89, 88, 87, 86, 85, 84, 83, 82, 82])):
            with self.subTest(commander=commander):
                _, sizes = self._run(["Command Tower"] * 7, list(library),
                                     commander=commander)
                self.assertEqual(sizes, expected)

    def test_baylen_draws_in_the_turn_cycle_he_is_cast(self):
        # The towers make only red or white here, so Baylen ({R}{G}{W}) waits
        # for the Forest drawn on turn 2, which is played only once the seven
        # towers are down, on turn 8 (a tower adds two of the commander's
        # colours, the Forest none). Turn 8: Baylen, then Secure the Wastes
        # (drawn that turn) with the five mana left: X = 4, four Warriors. They
        # are untapped at the end of turn 8, so Baylen draws 4 // 3 = 1 card
        # before turn 9. Zero Trinkets fill the library; turn 1 draws one.
        # Library sizes: 92 less one draw step a turn from turn 1 (91 at turn
        # 1, 84 at turn 8); turn 9 also takes Baylen's card: 84 - 1 - 1 = 82,
        # then 81.
        library = (["Zero Trinket"] * 84 + ["Secure the Wastes"] + ["Zero Trinket"] * 5
                   + ["Forest", "Zero Trinket"])
        _, sizes = self._run(["Command Tower"] * 7, library,
                             commander="Baylen, the Haymaker", colors=("R", "W"))
        self.assertEqual(sizes, [91, 90, 89, 88, 87, 86, 85, 84, 82, 81, 81])

    def test_anim_pakals_gnomes_stay_1_1_attackers_under_draconic_visitor(self):
        # Anim Pakal (combat 3) on turn 3, Draconic Visitor ({3}{R}{R}, combat
        # 5 + 1 for Flying = 6 from turn 6) on turn 5. The Gnomes are artifact
        # creature tokens: under Visitor they would be 5/5 flying Dragons, and
        # the engine keeps crediting them as 1/1 attackers (a floor). Gnomes
        # made on turns 4-10: 1, 2, ..., 7, all attacking from the turn made.
        # Turn 4: 3 + 1 = 4; turn 5: 3 + 3 = 6; turn 6: 3 + 6 + 6 = 15; turn 7:
        # 3 + 6 + 10 = 19; then 24, 30, 37.
        damage, _ = self._run(
            ["Anim Pakal, Thousandth Moon", "Draconic Visitor"] + ["Command Tower"] * 5,
            ["Command Tower"] * 92)
        self.assertEqual(damage, [0, 0, 0, 4, 10, 25, 44, 68, 98, 135])

    def test_the_commanders_mana_ability_adds_no_mana(self):
        # Baylen's "Tap two untapped tokens you control: Add one mana of any
        # color." is not modelled. Three towers and Baylen on turn 3, then
        # Castle Ardenvale on turn 4, tapped (no Plains); Zero Trinkets after.
        # From turn 5 four lands make four mana, one short of the Castle's
        # five, so it never makes a Human: Baylen alone deals 3 a turn from
        # turn 4. Mana from Baylen with no tokens would pay it every turn from
        # turn 5.
        damage, _ = self._run(
            ["Command Tower"] * 3 + ["Castle Ardenvale"] + ["Zero Trinket"] * 3,
            ["Zero Trinket"] * 92, commander="Baylen, the Haymaker")
        self.assertEqual(damage, [0, 0, 0, 3, 6, 9, 12, 15, 18, 21])

    def test_halo_fountain_uses_only_unspent_mana_after_an_attack(self):
        # Frontline Rush on turn 2 (two Goblins, attacking from turn 3); Halo
        # Fountain ({2}{W}) on turn 3 takes all three towers, so its {W}
        # activation first comes on turn 4, then every turn: one Citizen a
        # turn, attacking from the next. Damage 2, 2, 3, 4, 5, 6, 7, 8 on
        # turns 3-10. With no creature to attack (Halo alone) nothing is ever
        # tapped and it makes nothing.
        cases = {
            "after an attack": (["Halo Fountain", "Frontline Rush"],
                                [0, 0, 2, 4, 7, 11, 16, 22, 29, 37]),
            "no attack": (["Halo Fountain"], [0] * 10),
        }
        for label, (spells, damage) in cases.items():
            with self.subTest(label):
                hand = spells + ["Command Tower"] * (7 - len(spells))
                self.assertEqual(self._run(hand, ["Command Tower"] * 92)[0], damage)

    def test_castle_ardenvale_needs_three_white_sources_and_to_be_untapped(self):
        # Castle Ardenvale: "{2}{W}{W}, {T}": the Castle itself untapped and
        # {2}{W}{W} from the other lands (white needs two white sources
        # besides the Castle). Zero Trinkets ({0}, no combat) are drawn on turns 1-3
        # where a land would get in the way.
        # Two Plains: Plains turns 1-2 (the Castle loses the name tie-break),
        # the Castle turn 3, Forests after. Turn 5 has five lands, three of
        # them white: one Human a turn from turn 5, attacking from the next.
        # One Plains: the Castle turn 2, Forests after; only two white
        # sources ever, so nothing (charging the {T} as generic mana would
        # make a Human a turn from turn 5).
        # Five towers first: the Castle comes turn 6 and enters tapped (no
        # Plains), so its first Human comes turn 7, though the towers alone
        # could pay on turn 6.
        cases = {
            "two Plains": (["Plains", "Plains", "Castle Ardenvale"] + ["Zero Trinket"] * 4,
                           ["Forest"] * 89 + ["Zero Trinket"] * 3, ("W", "G"),
                           [0, 0, 0, 0, 0, 1, 3, 6, 10, 15]),
            "one Plains": (["Plains", "Castle Ardenvale"] + ["Zero Trinket"] * 5,
                           ["Forest"] * 90 + ["Zero Trinket"] * 2, ("W", "G"), [0] * 10),
            "enters tapped": (["Command Tower"] * 5 + ["Castle Ardenvale", "Zero Trinket"],
                              ["Zero Trinket"] * 92, ("R", "G", "W"),
                              [0, 0, 0, 0, 0, 0, 0, 1, 3, 6]),
        }
        for label, (hand, library, colors, damage) in cases.items():
            with self.subTest(label):
                self.assertEqual(self._run(hand, library, colors=colors)[0], damage)

    # The token paragraph of stampede-acres' goldfish methodology, whole.
    TOKEN_PARAGRAPH = (
        " Token makers modeled (owner-approved 2026-11-18): this deck's token "
        "makers feed the DEC-404 token ledger, one creation event per "
        "resolution, trigger or activation. Credited: creature tokens as a card "
        "resolves or enters: Frontline Rush 2, Prosperous Partnership 2, Staff "
        "of the Storyteller 1; X spells at the X paid: Grand Crescendo X, March "
        "of the Multitudes X, Pest Infestation 2X, Secure the Wastes X; "
        "whenever you attack, tapped and attacking, from the turn after the "
        "maker is cast: Adeline, Resplendent Cathar 3, Anim Pakal, Thousandth "
        "Moon one more each attack (1, 2, 3 ...); one per natural land drop "
        "while on the battlefield: Scute Swarm, Springheart Nantuko; at most "
        "once per turn each, after combat, in this order, paid out of the mana "
        "the turn's casts left: Castle Ardenvale (2 generic + 2 W), Halo "
        "Fountain (1 W; only with a tapped creature, one that attacked or was "
        "tapped for mana, which it untaps); Food as a card resolves or enters: Rosie Cotton of South Lane "
        "1. An activated maker must be untapped and is tapped for its ability "
        "(its {T}, not in the costs above); a land's own mana then leaves the "
        "pool. Peregrin Took adds one Food to each "
        "event before any doubler (the controller orders replacement effects, "
        "so the Food is doubled too); Food made with tokens that enter tapped "
        "enters tapped. Anointed Procession and Mondrak, Glory Dominus each "
        "double every token of an event. While Draconic Visitor is on the "
        "battlefield no new Food is credited: it would be a creature token the "
        "engine does not credit. Combat, the DEC-404 convention: each "
        "creature token deals 1 plus one per anthem on the battlefield "
        "(Warleader's Call) every turn from the turn after it is made, tokens "
        "made tapped and attacking deal damage the turn they are made, every "
        "creature token able to attack attacks, and no token is ever removed or "
        "spent. Commander draw: Baylen, the Haymaker taps 3 untapped tokens to "
        "draw a card. The cost has no {T} symbol, so summoning-sick tokens can "
        "pay, and a token that attacked stays tapped until your untap step; so "
        "at the last opponent's end step before each of your turns, while it is "
        "on the battlefield, the commander draws one card per 3 untapped "
        "tokens: every Food except any that entered tapped on your last turn, "
        "and the creature tokens made on your last turn. The cards arrive "
        "before your upkeep. The maker list is a floor; not credited: "
        "Smothering Tithe, The Queen of Dale (their tokens depend on opponents' "
        "choices); Gleaming Splendor (its Treasure needs an opponent's second "
        "draw in a turn: the goldfish models no opponent draws and never "
        "activates its {2}{W}); Elspeth, Storm Slayer, Voice of "
        "Victory, Artifact Mutation, The Battle of Bywater (never cast: read as "
        "interaction); Aligned Heart, Cori-Steel Cutter (tokens only on the "
        "second spell in a turn); Caretaker's Talent, Idol of Oblivion "
        "(one-shot activations); Scurry Oak (Squirrels from +1/+1 counters: "
        "with Rosie Cotton of South Lane they are the infinite the combo gate "
        "scores); Draconic Visitor (its 5/5 flying Dragons are not credited: "
        "while it is on the battlefield no new Food is credited, and Anim "
        "Pakal's Gnomes count as 1/1s); nor token copies' own landfall, "
        "landfall from lands a fetch land or ramp spell puts onto the "
        "battlefield, the makers' other abilities (Prosperous Partnership's "
        "Treasure), an attack maker's trigger on the turn it is cast (another "
        "creature attacking would trigger it). Not modeled: the commander's "
        "mana and +1/+1 counter abilities, Halo Fountain's draw and win abilities, Treasure and "
        "Food being spent, untaps on opponents' turns (Seedborn Muse, "
        "Drumbellower), Caretaker's Talent's level 3 anthem (\"Creature tokens "
        "you control get +2/+2.\"), noncombat token payoffs (Impact Tremors, "
        "Purphoros, Warleader's Call's ping), token-draw payoffs (Caretaker's Talent, "
        "Bennie Bracks, Belladonna Took, Staff of the Storyteller's story "
        "counters, Idol of Oblivion, Peregrin Took's Foods).")
    # Its X paragraph names the token X spells' credit and drops "tokens"
    # from the effects it does not credit.
    X_TOKEN_SENTENCE = (
        "; X token spells make their tokens at the X paid (token makers below). "
        "Every other X effect (life loss, damage, tutoring, pumps, proliferate, "
        "recursion, manifest) is not credited")

    def _methodology(self, deck_id):
        decklist = ["Secure the Wastes"] + ["Command Tower"] * 98
        with patch.object(exporter, "GOLDFISH_GAMES", 16), \
                patch("multiprocessing.Pool", SerialPool):
            goldfish, _ = exporter.compute_goldfish_section(
                decklist=decklist, deck_data={"decklist": []}, metadata=CARDS,
                commander_name="Baylen, the Haymaker",
                commander_colors=["R", "G", "W"], deck_id=deck_id)
        return goldfish["methodology"]

    def test_methodology_leaves_out_the_sentences_of_empty_keys(self):
        # The shipped config with every optional key emptied but one X maker:
        # the paragraph keeps only the ledger, the X maker, combat and the
        # commander draw, with no anthem list.
        emptied = dict(exporter.TOKEN_MAKER_ENGINE[self.DECK_ID],
                       onResolve={}, perX={"Secure the Wastes": 1}, attackMakers={},
                       growingAttackMakers=set(), landfallMakers=set(),
                       activatedMakers={}, needsTappedCreature=set(), doublerNames=set(),
                       extraFoodName="", artifactTokensReplacedBy="", anthemNames=set(),
                       excluded=(), notCredited=(), notModeled=())
        with patch.dict(exporter.TOKEN_MAKER_ENGINE, {self.DECK_ID: emptied}):
            methodology = self._methodology(self.DECK_ID)
        self.assertEqual(methodology[methodology.find(" Token makers modeled"):], (
            " Token makers modeled (owner-approved 2026-11-18): this deck's token "
            "makers feed the DEC-404 token ledger, one creation event per "
            "resolution, trigger or activation. Credited: X spells at the X paid: "
            "Secure the Wastes X. Combat, the DEC-404 convention: each creature "
            "token deals 1 plus one per anthem on the battlefield every turn from "
            "the turn after it is made, tokens made tapped and attacking deal "
            "damage the turn they are made, every creature token able to attack "
            "attacks, and no token is ever removed or spent. Commander draw: "
            "Baylen, the Haymaker taps 3 untapped tokens to draw a card. The cost "
            "has no {T} symbol, so summoning-sick tokens can pay, and a token that "
            "attacked stays tapped until your untap step; so at the last "
            "opponent's end step before each of your turns, while it is on the "
            "battlefield, the commander draws one card per 3 untapped tokens: "
            "every Food except any that entered tapped on your last turn, and the "
            "creature tokens made on your last turn. The cards arrive before your "
            "upkeep."))

    def test_methodology_states_the_token_makers_only_for_this_deck(self):
        methodology = self._methodology(self.DECK_ID)
        other = self._methodology("synthetic-x")
        self.assertEqual(
            (self.TOKEN_PARAGRAPH in methodology, self.X_TOKEN_SENTENCE in methodology,
             "Token makers modeled" in other, self.X_TOKEN_SENTENCE in other,
             "Every other X effect (tokens, life loss" in other),
            (True, True, False, False, True))


class TokenMakerTableGuardTests(unittest.TestCase):
    """TOKEN_MAKER_ENGINE["stampede-acres"] against the deck as it stands.

    The one token-engine test that reads data/: the live
    data/commanders/stampede-acres/deck.json and data/card-metadata.json, so a
    swap that adds or cuts a token card fails here until the engine's table
    or its exclusion list follows. A card makes or replaces tokens when a line
    of its oracle text says "create(s) ... token(s)" or "token(s) ... would be
    created" within one sentence, or when it is a `produced_by` name of a
    deck.json `tokens[]` entry whose type line starts with "Token"
    (compute_tokens.py writes those from Scryfall's related cards; its "Card"
    markers and "Emblem" entries are skipped). The oracle text here is the
    front face's, so makers on a back face or an adventure face, and keyword
    makers without reminder text (a bare "investigate"), are seen only
    through `tokens[]`: after a swap, run `uv run python
    scripts/compute_tokens.py --deck stampede-acres` before this test. A
    `produced_by` name no longer in the deck is reported on its own: tokens[]
    is stale. Through the deck's goldfish context, the exclusions whose
    reason is that the goldfish never casts the card are never cast, and
    every credited card that is not a land can be cast.
    """

    DECK_ID = "stampede-acres"
    TOKEN_TEXT = re.compile(
        r"\bcreates?\b[^.\n]*\btokens?\b|\btokens?\b[^.\n]*\bwould be created\b",
        re.IGNORECASE)

    @classmethod
    def problems(cls, deck, metadata, token_engines, swarm_engines) -> tuple:
        """(token cards in neither list, listed cards no longer in the deck,
        cards both credited and excluded, "never cast" exclusions the goldfish
        casts, credited non-land cards it never casts, deck ids in both
        TOKEN_MAKER_ENGINE and COMMANDER_TOKEN_ENGINE, tokens[] producers no
        longer in the deck: tokens[] is stale, re-run compute_tokens)."""
        config = token_engines[cls.DECK_ID]
        in_deck = {deck["commander"]} | {card["name"] for card in deck["decklist"]}
        credited = (set(config["onResolve"]) | set(config["perX"])
                    | set(config["attackMakers"]) | config["growingAttackMakers"]
                    | config["landfallMakers"] | set(config["activatedMakers"])
                    | config["doublerNames"] | {config["extraFoodName"]}
                    | config["anthemNames"])
        excluded = {name for _, names in config["excluded"] for name in names}
        never_cast = {name for reason, names in config["excluded"]
                      if reason.startswith("never cast") for name in names}
        token_cards = {name for name in in_deck
                       if cls.TOKEN_TEXT.search(metadata[name].get("oracle_text", ""))}
        producers = {name for entry in deck.get("tokens") or []
                     if entry["type_line"].startswith("Token")
                     for name in entry["produced_by"]}
        token_cards |= producers & in_deck
        decklist = [card["name"] for card in deck["decklist"]
                    for _ in range(card.get("quantity", 1))]
        context = exporter.build_goldfish_context(
            decklist, deck, metadata, deck["commander"],
            metadata[deck["commander"]]["colors"], cls.DECK_ID)
        profiles = context["profiles"]
        return (sorted(token_cards - credited - excluded),
                sorted((credited | excluded | {config["artifactTokensReplacedBy"]})
                       - in_deck),
                sorted(credited & excluded),
                sorted(name for name in never_cast & in_deck
                       if not exporter.goldfish_never_casts(name, profiles[name], context)),
                sorted(name for name in credited & in_deck
                       if not profiles[name]["isLand"]
                       and exporter.goldfish_never_casts(name, profiles[name], context)),
                sorted(set(token_engines) & set(swarm_engines)),
                sorted(producers - in_deck))

    def test_every_token_card_in_the_deck_is_credited_or_excluded(self):
        root = Path(__file__).resolve().parent.parent
        deck = json.loads(
            (root / "data" / "commanders" / self.DECK_ID / "deck.json").read_text())
        metadata = json.loads(Path(exporter.METADATA_FILE).read_text())
        self.assertEqual(
            self.problems(deck, metadata, exporter.TOKEN_MAKER_ENGINE,
                          exporter.COMMANDER_TOKEN_ENGINE),
            ([], [], [], [], [], [], []))


def mana_letters(atoms) -> list[str]:
    """Mana atoms as sorted WUBRGC letter strings, for comparisons."""
    return sorted("".join(c for c in "WUBRGC" if c in atom) for atom in atoms)


class ManaModelRuleTests(unittest.TestCase):
    """The mana model's rules (owner-approved 2026-11-19), one table per rule.

    Card texts are copied from data/card-metadata.json (2026-11-19); each
    expected value is read off the text: the mana a pilot gets from the card
    on a normal turn using only itself and the goldfish's own battlefield.
    """

    @staticmethod
    def model(type_line, text, colors=(), power=None, cmd=("B", "G"), back=None, name="Card"):
        meta = {"type_line": type_line, "oracle_text": text, "colors": list(colors),
                "power": power, "mana_cost": "" if "Land" in type_line else "{0}", "cmc": 0}
        if back:
            meta["back_face"] = {"type_line": back[0], "oracle_text": back[1]}
        return exporter.card_mana_model(name, meta, list(cmd))

    # (name, type line, text, colors, power, commander colours, expected fields)
    CASES = [
        # M1: the face on the battlefield, reminder and quoted text removed.
        ("Hagra Mauling // Hagra Broodpit", "Instant // Land",
         "This spell costs {1} less to cast if an opponent controls no basic lands.\nDestroy target creature.",
         ("B",), None, ("B", "G"), {"isLand": True, "mana": ["B"], "landEntry": ("tapped",)}),
        ("Growing Rites of Itlimoc", "Legendary Enchantment // Legendary Land",
         "When Growing Rites of Itlimoc enters, look at the top four cards of your library.\n"
         "At the beginning of your end step, if you control four or more creatures, transform "
         "Growing Rites of Itlimoc.", ("G",), None, ("G",),
         {"isLand": False, "mana": [], "manaSourceDelay": None}),
        ("Dryad Arbor", "Land Creature — Forest Dryad",
         "(This land isn't a spell, it's affected by summoning sickness, and it has \"{T}: Add {G}.\")",
         ("G",), "1", ("G",), {"mana": ["G"], "landEntry": ("untapped",)}),
        ("Urborg, Tomb of Yawgmoth", "Legendary Land",
         "Each land is a Swamp in addition to its other land types.", (), None, ("B",),
         {"mana": ["B"], "eachLandIs": "Swamp"}),
        ("Big Score", "Instant",
         "As an additional cost to cast this spell, discard a card.\nDraw two cards and create two "
         "Treasure tokens. (They're artifacts with \"{T}, Sacrifice this token: Add one mana of any "
         "color.\")", ("R",), None, ("B", "R"), {"mana": [], "manaSourceDelay": None}),
        ("Enduring Vitality", "Enchantment Creature — Elk Glimmer",
         "Vigilance\nCreatures you control have \"{T}: Add one mana of any color.\"\nWhen Enduring "
         "Vitality dies, if it was a creature, return it to the battlefield under its owner's "
         "control. It's an enchantment. (It's not a creature.)", ("G",), "3", ("B", "G"),
         {"mana": ["BG"], "manaSourceDelay": 1}),
        ("Cryptolith Rite", "Enchantment",
         "Creatures you control have \"{T}: Add one mana of any color.\"", ("G",), None, ("B", "G"),
         {"mana": [], "manaSourceDelay": None}),
        ("Urza's Saga", "Enchantment Land — Urza's Saga",
         "(As this Saga enters and after your draw step, add a lore counter. Sacrifice after III.)\n"
         "I — This Saga gains \"{T}: Add {C}.\"\nII — This Saga gains \"{2}, {T}: Create a 0/0 "
         "colorless Construct artifact creature token with 'This token gets +1/+1 for each artifact "
         "you control.'\"\nIII — Search your library for an artifact card with mana cost {0} or {1}, "
         "put it onto the battlefield, then shuffle.", (), None, ("W",),
         {"mana": ["C"], "manaTurns": 3}),
        # M2: activated and plus or zero loyalty abilities; evaluated triggers.
        ("Birgi, God of Storytelling", "Legendary Creature — God // Legendary Artifact",
         "Whenever you cast a spell, add {R}. Until end of turn, you don't lose this mana as steps "
         "and phases end.\nCreatures you control can boast twice during each of your turns rather "
         "than once.", ("R",), "3", ("R",), {"mana": [], "onCast": ["R"]}),
        ("Crime Novelist", "Creature — Goblin Bard",
         "Whenever you sacrifice an artifact, put a +1/+1 counter on this creature and add {R}.",
         ("R",), "1", ("B", "R"), {"mana": [], "manaSourceDelay": None}),
        ("Ugin, Eye of the Storms", "Legendary Planeswalker — Ugin",
         "When you cast this spell, exile up to one target permanent that's one or more colors.\n"
         "+2: You gain 3 life and draw a card.\n0: Add {C}{C}{C}.\n−11: Search your library for "
         "any number of colorless nonland cards, exile them, then shuffle.", (), None, ("C",),
         {"mana": ["C", "C", "C"], "manaSourceDelay": 0}),
        # M3: costs.
        ("Izzet Signet", "Artifact", "{1}, {T}: Add {U}{R}.", (), None, ("U", "R"),
         {"mana": ["UR"], "manaSourceDelay": 1}),
        ("Overflowing Basin", "Land", "{1}, {T}: Add {G}{U}.", (), None, ("U", "G"), {"mana": ["UG"]}),
        ("Hall of Oracles", "Land",
         "{T}: Add {C}.\n{1}, {T}: Add one mana of any color.\n{T}: Put a +1/+1 counter on target "
         "creature. Activate only as a sorcery and only if you've cast an instant or sorcery spell "
         "this turn.", (), None, ("U", "G"), {"mana": ["C"]}),
        ("Ashnod's Altar", "Artifact", "Sacrifice a creature: Add {C}{C}.", (), None, ("B", "G"),
         {"mana": [], "once": [], "manaSourceDelay": None}),
        ("Phyrexian Tower", "Legendary Land",
         "{T}: Add {C}.\n{T}, Sacrifice a creature: Add {B}{B}.", (), None, ("B", "G"), {"mana": ["C"]}),
        # Fix 6: a cost that sacrifices "a"/"an" permanent of a type is fed
        # other permanents: nothing, even when the card is of that type.
        ("Krark-Clan Ironworks", "Artifact", "Sacrifice an artifact: Add {C}{C}.", (), None, ("C",),
         {"mana": [], "once": [], "manaSourceDelay": None}),
        ("Lotus Petal", "Artifact", "{T}, Sacrifice this artifact: Add one mana of any color.",
         (), None, ("B", "R"), {"mana": [], "once": ["BR"], "onceLeaves": True}),
        ("Mana Vault", "Artifact",
         "This artifact doesn't untap during your untap step.\nAt the beginning of your upkeep, you "
         "may pay {4}. If you do, untap this artifact.\n{T}: Add {C}{C}{C}.", (), None, ("C",),
         {"mana": [], "once": ["C", "C", "C"], "onceLeaves": False, "manaSourceDelay": 0}),
        ("Skirk Prospector", "Creature — Goblin", "Sacrifice a Goblin: Add {R}.", ("R",), "1", ("R",),
         {"mana": [], "once": [], "manaSourceDelay": None}),
        ("Baylen, the Haymaker", "Legendary Creature — Rabbit Warrior",
         "Tap two untapped tokens you control: Add one mana of any color.\nTap three untapped tokens "
         "you control: Draw a card.", ("G", "R", "W"), "4", ("R", "G", "W"),
         {"mana": [], "manaSourceDelay": None}),
        ("Three Tree Mascot", "Artifact Creature — Shapeshifter",
         "Changeling\n{1}: Add one mana of any color. Activate only once each turn.", (), "2",
         ("W", "U", "B", "R", "G"), {"mana": [], "manaSourceDelay": None}),
        ("Arena of Glory", "Land",
         "This land enters tapped unless you control a Mountain.\n{T}: Add {R}.\n{R}, {T}, Exert this "
         "land: Add {R}{R}. If any of that mana is spent on a creature spell, it gains haste until end "
         "of turn.", (), None, ("R",), {"mana": ["R"], "landEntry": ("anyType", frozenset({"Mountain"}))}),
        # M4: one activation a turn.
        ("Karplusan Forest", "Land",
         "{T}: Add {C}.\n{T}: Add {R} or {G}. This land deals 1 damage to you.", (), None, ("R", "G"),
         {"mana": ["RGC"]}),
        ("Cascade Bluffs", "Land", "{T}: Add {C}.\n{U/R}, {T}: Add {U}{U}, {U}{R}, or {R}{R}.",
         (), None, ("U", "R"), {"mana": ["URC"]}),
        ("Talisman of Creativity", "Artifact",
         "{T}: Add {C}.\n{T}: Add {U} or {R}. This artifact deals 1 damage to you.", (), None,
         ("U", "R"), {"mana": ["URC"], "manaSourceDelay": 0}),
        ("Eldrazi Temple", "Land",
         "{T}: Add {C}.\n{T}: Add {C}{C}. Spend this mana only to cast colorless Eldrazi spells or "
         "activate abilities of colorless Eldrazi.", (), None, ("C",), {"mana": ["C", "C"]}),
        ("Relic of Sauron", "Artifact",
         "{T}: Add two mana in any combination of {U}, {B}, and/or {R}.\n{3}, {T}: Draw two cards, "
         "then discard a card.", (), None, ("U", "B", "R"), {"mana": ["UBR", "UBR"]}),
        ("Delighted Halfling", "Creature — Halfling Citizen",
         "{T}: Add {C}.\n{T}: Add one mana of any color. Spend this mana only to cast a legendary "
         "spell, and that spell can't be countered.", ("G",), "1", ("R", "G", "W"),
         {"mana": ["WRGC"], "manaSourceDelay": 1}),
        # M5: conditions, restricted mana, variable amounts.
        ("Tainted Wood", "Land", "{T}: Add {C}.\n{T}: Add {B} or {G}. Activate only if you control a Swamp.",
         (), None, ("B", "G"),
         {"mana": ["C"], "board": [("gate", ("anyType", frozenset({"Swamp"})), (frozenset("BG"),))]}),
        ("Gemstone Caverns", "Legendary Land",
         "If this card is in your opening hand and you're not the starting player, you may begin the "
         "game with Gemstone Caverns on the battlefield with a luck counter on it. If you do, exile a "
         "card from your hand.\n{T}: Add {C}. If Gemstone Caverns has a luck counter on it, instead "
         "add one mana of any color.", (), None, ("C",), {"mana": ["C"], "board": []}),
        ("Shrine of the Forsaken Gods", "Land",
         "{T}: Add {C}.\n{T}: Add {C}{C}. Spend this mana only to cast colorless spells. Activate only "
         "if you control seven or more lands.", (), None, ("C",),
         {"mana": ["C"], "board": [("gate", ("atLeast", "Land", 7), (frozenset("C"),) * 2)]}),
        ("Urza's Tower", "Land — Urza's Tower",
         "{T}: Add {C}. If you control an Urza's Mine and an Urza's Power-Plant, add {C}{C}{C} instead.",
         (), None, ("C",),
         {"mana": ["C"], "board": [("gate", ("landTypes", frozenset({"Mine", "Power-Plant"})),
                                    (frozenset("C"),) * 3)]}),
        ("Urza's Workshop", "Land — Urza's",
         "{T}: Add {C}.\nMetalcraft — {T}: Add {C} for each Urza's land you control. Activate only if "
         "you control three or more artifacts.", (), None, ("C",),
         {"mana": ["C"], "board": [("count", ("type", "Urza's"), frozenset("C"), 0,
                                    ("atLeast", "Artifact", 3))]}),
        ("Cabal Coffers", "Land", "{2}, {T}: Add {B} for each Swamp you control.", (), None, ("B", "R"),
         {"mana": [], "board": [("count", ("type", "Swamp"), frozenset("B"), 2, None)]}),
        ("Elvish Archdruid", "Creature — Elf Druid",
         "Other Elf creatures you control get +1/+1.\n{T}: Add {G} for each Elf you control.",
         ("G",), "2", ("G",),
         {"mana": ["G"], "board": [("count", ("type", "Elf"), frozenset("G"), 0, None)],
          "manaSourceDelay": 1}),
        ("Kami of Whispered Hopes", "Creature — Spirit",
         "{T}: Add X mana of any one color, where X is this creature's power.", ("G",), "1",
         ("U", "G"), {"mana": ["UG"]}),
        ("Vivi Ornitier", "Legendary Creature — Wizard",
         "{0}: Add X mana in any combination of {U} and/or {R}, where X is Vivi Ornitier's power. "
         "Activate only during your turn and only once each turn.", ("R", "U"), "0", ("U", "R", "W"),
         {"mana": [], "manaSourceDelay": None}),
        ("Chrome Mox", "Artifact",
         "Imprint — When this artifact enters, you may exile a nonartifact, nonland card from your "
         "hand.\n{T}: Add one mana of any of the exiled card's colors.", (), None, ("U", "B", "R"),
         {"mana": [], "manaSourceDelay": 0,
          "imprint": {"atoms": None, "colorless": False, "nonartifact": True, "nonland": True,
                      "minValue": 0}}),
        ("Ugin's Labyrinth", "Land",
         "Imprint — When this land enters, you may exile a colorless card with mana value 7 or greater "
         "from your hand.\n{T}: Add {C}. If a card is exiled with this land, add {C}{C} instead.\n"
         "{T}: Return the exiled card to its owner's hand.", (), None, ("C",),
         {"mana": ["C"], "imprint": {"atoms": (frozenset("C"), frozenset("C")), "colorless": True,
                                     "nonartifact": False, "nonland": False, "minValue": 7}}),
        ("Basalt Monolith", "Artifact",
         "This artifact doesn't untap during your untap step.\n{T}: Add {C}{C}{C}.\n{3}: Untap this "
         "artifact.", (), None, ("C",),
         {"mana": [], "once": ["C", "C", "C"], "onceLeaves": False, "manaSourceDelay": 0,
          "onceRearm": {"W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "C": 0, "generic": 3, "X": 0,
                        "total": 3}}),
        # Fix 4: Urza taps his own Construct token from the turn he is cast.
        ("Urza, Lord High Artificer", "Legendary Creature — Human Artificer",
         "When Urza enters, create a 0/0 colorless Construct artifact creature token with \"This "
         "token gets +1/+1 for each artifact you control.\"\nTap an untapped artifact you control: "
         "Add {U}.\n{5}: Shuffle your library, then exile the top card. Until end of turn, you may "
         "play that card without paying its mana cost.", ("U",), "1", ("U",),
         {"mana": ["U"], "board": [("count", ("idleArtifacts", 1), frozenset("U"), 0, None)],
          "manaSourceDelay": 0, "manaTapsSelf": False}),
        ("Crypt of Agadeem", "Land",
         "This land enters tapped.\n{T}: Add {B}.\n{2}, {T}: Add {B} for each black creature card "
         "in your graveyard.", (), None, ("B", "G"), {"mana": ["B"], "board": []}),
        ("Howlsquad Heavy", "Creature — Goblin Mercenary",
         "Start your engines!\nOther Goblins you control have haste.\nMax speed — {T}: Add {R} for "
         "each Goblin you control.", ("R",), "2", ("R",), {"mana": [], "manaSourceDelay": None}),
        ("Three Tree City", "Legendary Land",
         "As Three Tree City enters, choose a creature type.\n{T}: Add {C}.\n{2}, {T}: Choose a color. "
         "Add an amount of mana of that color equal to the number of creatures you control of the "
         "chosen type.", (), None, ("U",), {"mana": ["C"], "board": []}),
        ("Nykthos, Shrine to Nyx", "Legendary Land",
         "{T}: Add {C}.\n{2}, {T}: Choose a color. Add an amount of mana of that color equal to your "
         "devotion to that color.", (), None, ("G",),
         {"mana": ["C"], "board": [("count", ("devotion",), frozenset("G"), 2, None)]}),
        ("Bloom Tender", "Creature — Elf Druid",
         "Vivid — {T}: For each color among permanents you control, add one mana of that color.",
         ("G",), "1", ("B", "G"), {"mana": ["G"], "board": [("vivid",)]}),
        ("Mox Amber", "Legendary Artifact",
         "{T}: Add one mana of any color among legendary creatures and planeswalkers you control.",
         (), None, ("U", "R", "W"),
         {"mana": [], "board": [("legendColors", ("Creature", "Planeswalker"))], "manaSourceDelay": 0}),
        ("Crypt Ghast", "Creature — Spirit",
         "Extort\nWhenever you tap a Swamp for mana, add an additional {B}.", ("B",), "2", ("B", "R"),
         {"mana": [], "board": [("extra", "swampsTapped", frozenset("B"), 0)]}),
        ("Badgermole Cub", "Creature — Badger Mole",
         "When this creature enters, earthbend 1. (Target land you control becomes a 0/0 creature "
         "with haste that's still a land.)\nWhenever you tap a creature for mana, add an additional "
         "{G}.", ("G",), "2", ("B", "G"),
         {"mana": [], "board": [("extra", "creatureSources", frozenset("G"), 1)]}),
        # M6: lands.
        ("Lotus Field", "Land",
         "Hexproof\nThis land enters tapped.\nWhen this land enters, sacrifice two lands.\n{T}: Add "
         "three mana of any one color.", (), None, ("W",),
         {"mana": ["W", "W", "W"], "landEntry": ("tapped",),
          "landEntryCost": {"count": 2, "now": False, "toHand": False}}),
        ("Scorched Ruins", "Land", CARDS["Scorched Ruins"]["oracle_text"], (), None, ("C",),
         {"mana": ["C", "C", "C", "C"], "landEntry": ("untapped",),
          "landEntryCost": {"count": 2, "now": True, "toHand": False}}),
        ("Simic Growth Chamber", "Land",
         "This land enters tapped.\nWhen this land enters, return a land you control to its owner's "
         "hand.\n{T}: Add {G}{U}.", (), None, ("U", "G"),
         {"mana": ["G", "U"], "landEntry": ("tapped",),
          "landEntryCost": {"count": 1, "now": False, "toHand": True}}),
        # R3: a fetch land makes no mana of its own; it is cracked as it is
        # played for a land its search finds, which enters as the search says.
        ("Fabled Passage", "Land", CARDS["Fabled Passage"]["oracle_text"], (), None, ("U", "G"),
         {"mana": [], "landEntry": ("untapped",),
          "landCrack": {"count": 1, "toHand": 0, "basicOnly": True, "allowedSubtypes": set(),
                        "perType": [], "sharedType": False, "entersTapped": True,
                        "untapIf": ("landsAtLeast", 4)}}),
        ("Polluted Delta", "Land",
         "{T}, Pay 1 life, Sacrifice this land: Search your library for an Island or Swamp card, put "
         "it onto the battlefield, then shuffle.", (), None, ("U", "B", "R"),
         {"mana": [], "landEntry": ("untapped",),
          "landCrack": {"count": 1, "toHand": 0, "basicOnly": False,
                        "allowedSubtypes": {"Island", "Swamp"}, "perType": [], "sharedType": False,
                        "entersTapped": False, "untapIf": None}}),
        ("Elven Passage", "Land",
         "{T}, Pay 1 life, Sacrifice this land: Search your library for a basic land card, put it onto "
         "the battlefield tapped, then shuffle. You may behold an Elf. If you do, untap that land.",
         (), None, ("U", "G"),
         {"mana": [], "landEntry": ("untapped",),
          "landCrack": {"count": 1, "toHand": 0, "basicOnly": True, "allowedSubtypes": set(),
                        "perType": [], "sharedType": False, "entersTapped": True,
                        "untapIf": ("elf",)}}),
        # R4: wording no rule reads is refused, not credited by accident.
        ("Probe Other Grant", "Creature — Elf",
         "Other creatures you control have \"{T}: Add {G}.\"", ("G",), "1", ("G",),
         {"mana": [], "manaSourceDelay": None}),
        ("Probe Timeless", "Artifact", "Probe Timeless enters tapped.\n{T}: Add {C}.", (), None, ("C",),
         {"mana": ["C"], "manaSourceDelay": 1}),
        ("Probe Pool", "Land", "{T}: Add one mana of any type that a land you control could produce.",
         (), None, ("U", "G"), {"mana": [], "board": [("landColors",)]}),
        ("Lotus Field (one colour)", "Land", "{T}: Add three mana of any one color.", (), None,
         ("W", "U"), {"mana": ["WU", "WU", "WU"], "manaOneColour": True}),
        ("Chromatic Lantern", "Artifact",
         "Lands you control have \"{T}: Add one mana of any color.\"\n{T}: Add one mana of any color.",
         (), None, ("B", "G"), {"mana": ["BG"], "landGrant": frozenset("BG")}),
    ]
    # (text, reason) — each must leave an "unread" verdict.
    UNREAD_CASES = [
        ("{T}: If you control a Dragon, add {C}{C}.", "a condition no rule reads"),
        ("{T}: Add {C}.\nLandfall — Whenever a land you control enters, add {G}.", "a landfall trigger"),
        ("Remove a charge counter from this artifact: Add {C}.", "its own counters"),
        ("Some creatures you control have \"{T}: Add {G}.\"", "a grant subject no rule reads"),
        ("{T}: Add {C}.\n{1}{G}: Level 2\n{T}: Add {G}{G}.", "a level ability"),
    ]

    def test_triggered_mana_is_a_named_floor_or_unread(self):
        # Extraplanar Lens's "its controller adds" and Crime Novelist's
        # sacrifice trigger are named floors; any other trigger is unread.
        cases = [
            ("Imprint — When this artifact enters, you may exile target land you control.\nWhenever "
             "a land with the same name as the exiled card is tapped for mana, its controller adds "
             "one mana of any type that land produced.", "trigger floor"),
            ("Whenever you sacrifice an artifact, put a +1/+1 counter on this creature and add {R}.",
             "trigger floor"),
            ("Whenever a land you control enters, its controller adds {G}.", "unread"),
        ]
        for text, verdict in cases:
            with self.subTest(text=text[:40]):
                got = self.model("Artifact", text, name="Probe Card")
                self.assertEqual([v for _, v in got["verdicts"]], [verdict])

    def test_wording_no_rule_reads_is_unread(self):
        for text, reason in self.UNREAD_CASES:
            with self.subTest(reason=reason):
                got = self.model("Artifact", text, name="Probe Card")
                self.assertIn("unread", [verdict for _, verdict in got["verdicts"]])
                meta = {"type_line": "Artifact", "oracle_text": text, "mana_cost": "{0}", "cmc": 0}
                with self.assertRaises(ValueError):
                    exporter.build_goldfish_profile("Probe Card", meta, set(), ["G"], "Other")

    def test_each_rule_reads_the_card_text(self):
        keys = {"mana": "manaAtoms", "once": "manaOnce", "onCast": "manaOnCast", "board": "manaBoard"}
        for name, type_line, text, colors, power, cmd, expected in self.CASES:
            with self.subTest(card=name):
                back = None
                if name == "Hagra Mauling // Hagra Broodpit":
                    back = ("Land", "This land enters tapped.\n{T}: Add {B}.")
                got = self.model(type_line, text, colors, power, cmd, back=back, name=name)
                for key, want in expected.items():
                    value = got[keys.get(key, key)]
                    if key in ("mana", "once", "onCast"):
                        value = mana_letters(value)
                    self.assertEqual(value, want, key)
                self.assertNotIn("unread", [verdict for _, verdict in got["verdicts"]])

    def test_a_pathway_keeps_both_land_faces(self):
        got = self.model("Land // Land", "{T}: Add {W}.", cmd=("W", "B"),
                         back=("Land", "{T}: Add {B}."), name="Brightclimb Pathway")
        self.assertEqual([mana_letters(face) for face in got["landFaces"]], [["W"], ["B"]])

    def test_planar_nexus_is_every_nonbasic_land_type(self):
        got = self.model("Land", "This land is every nonbasic land type. (Nonbasic land types include "
                         "Cave, Desert, Gate, Lair, Locus, Mine, Power-Plant, Sphere, Tower, and "
                         "Urza's.)\n{T}: Add {C}.\n{1}, {T}: Add one mana of any color.", cmd=("C",))
        self.assertLessEqual({"Mine", "Power-Plant", "Tower", "Urza's"}, got["landTypes"])
        self.assertEqual(mana_letters(got["manaAtoms"]), ["C"])

    # (text, expected rule) for parse_land_entry
    ENTRY_CASES = [
        ("This land enters tapped unless you control two or fewer other lands.\n{T}: Add {B} or {R}.",
         ("otherLandsAtMost", 2)),
        ("This land enters tapped unless you control two or more other lands.\n{T}: Add {B} or {G}.",
         ("otherLandsAtLeast", 2)),
        ("This land enters tapped unless you control a Swamp or a Mountain.\n{T}: Add {B} or {R}.",
         ("anyType", frozenset({"Swamp", "Mountain"}))),
        ("({T}: Add {B} or {R}.)\nThis land enters tapped unless you control two or more basic lands.",
         ("basicsAtLeast", 2)),
        ("Barad-dûr enters tapped unless you control a legendary creature.\n{T}: Add {B}.",
         ("legendaryCreature",)),
        ("({T}: Add {U}.)\nThis land enters tapped unless you control three or more other Islands.",
         ("otherTypeAtLeast", "Island", 3)),
        ("If you control two or more other lands, this land enters tapped.\n{T}: Add {R}.",
         ("otherLandsAtMost", 1)),
        ("({T}: Add {B} or {R}.)\nAs this land enters, you may pay 2 life. If you don't, it enters tapped.",
         ("untapped",)),
        ("As this land enters, you may pay 3 life. If you don't, it enters tapped.\n{T}: Add {B}.",
         ("untapped",)),
        ("This land enters tapped unless you have two or more opponents.\n{T}: Add {B} or {R}.",
         ("untapped",)),
        # DEC-688 / DEC-929: untapped from the fourth land drop.
        ("({T}: Add {B} or {R}.)\nThis land enters tapped unless your opponents control eight or more lands.",
         ("otherLandsAtLeast", 3)),
        ("As this land enters, you may reveal a Plains or Swamp card from your hand. If you don't, this "
         "land enters tapped.\n{T}: Add {W} or {B}.", ("reveal", frozenset({"Plains", "Swamp"}))),
        ("This land enters tapped unless you control a creature with power 4 or greater.", "unread"),
    ]

    def test_land_entry_rules(self):
        for text, expected in self.ENTRY_CASES:
            with self.subTest(text=text[:50]):
                self.assertEqual(exporter.parse_land_entry(text), expected)

    @staticmethod
    def entry_tapped(rule, lands, others=()):
        """land_enters_tapped with lands (name, land types, basic, each-land-is) and
        other permanents (name, type words, changeling) on the battlefield."""
        profiles, battlefield, permanents = {}, [], []
        for name, types, basic, each in lands:
            profiles[name] = {"landTypes": frozenset(types), "eachLandIs": each}
            battlefield.append({"name": name, "colors": set(), "subtypes": set(types), "isBasic": basic})
        for name, words, changeling in others:
            profiles[name] = {"typeWords": frozenset(words), "changeling": changeling}
            permanents.append({"name": name, "kind": "spell"})
        return exporter.land_enters_tapped(rule, battlefield, permanents, profiles, [])

    def test_land_entry_rules_read_the_battlefield(self):
        forest = ("Forest", {"Forest"}, True, None)
        swamp = ("Swamp", {"Swamp"}, True, None)
        island = ("Island", {"Island"}, True, None)
        urborg = ("Urborg", set(), False, "Swamp")
        tower = ("Tower", set(), False, None)
        cases = [
            (("otherLandsAtMost", 2), [forest, swamp], (), False),
            (("otherLandsAtMost", 2), [forest, swamp, island], (), True),
            (("otherLandsAtLeast", 2), [forest], (), True),
            (("otherLandsAtLeast", 2), [forest, swamp], (), False),
            (("basicsAtLeast", 2), [forest, tower], (), True),
            (("basicsAtLeast", 2), [forest, swamp], (), False),
            (("anyType", frozenset({"Swamp"})), [forest], (), True),
            # Urborg makes every land a Swamp, itself included.
            (("anyType", frozenset({"Swamp"})), [forest, urborg], (), False),
            (("otherTypeAtLeast", "Island", 3), [island, island], (), True),
            (("otherTypeAtLeast", "Island", 3), [island, island, island], (), False),
            (("legendaryCreature",), [forest], [("Bear", {"Creature", "Bear"}, False)], True),
            (("legendaryCreature",), [forest],
             [("Commander", {"Legendary", "Creature", "Elf", "Warrior"}, False)], False),
            # A changeling is an Elf to behold.
            (("elf",), [forest], [("Shapeshifter", {"Creature", "Shapeshifter"}, True)], False),
            (("elf",), [forest], [("Bear", {"Creature", "Bear"}, False)], True),
        ]
        for rule, lands, others, tapped in cases:
            with self.subTest(rule=rule, lands=[land[0] for land in lands]):
                self.assertEqual(self.entry_tapped(rule, lands, others), tapped)

    # (name, type line, text, expected landRamp fields or None)
    RAMP_CASES = [
        ("Cultivate", "Sorcery", CARDS["Cultivate"]["oracle_text"],
         {"count": 1, "toHand": 1, "entersTapped": True, "basicOnly": True}),
        ("Skyshroud Claim", "Sorcery",
         "Search your library for up to two Forest cards, put them onto the battlefield, then shuffle.",
         {"count": 2, "toHand": 0, "entersTapped": False, "allowedSubtypes": {"Forest"}}),
        ("Farseek", "Sorcery",
         "Search your library for a Plains, Island, Swamp, or Mountain card, put it onto the "
         "battlefield tapped, then shuffle.",
         {"count": 1, "entersTapped": True, "basicOnly": False,
          "allowedSubtypes": {"Plains", "Island", "Swamp", "Mountain"}}),
        ("Solemn Simulacrum", "Artifact Creature — Golem",
         "When this creature enters, you may search your library for a basic land card, put that card "
         "onto the battlefield tapped, then shuffle.\nWhen this creature dies, you may draw a card.",
         {"count": 1, "toHand": 0, "entersTapped": True, "basicOnly": True}),
        ("Stoic Farmer", "Creature — Dwarf Peasant",
         "When this creature enters, search your library for a basic Plains card and reveal it. If an "
         "opponent controls more lands than you, put it onto the battlefield tapped. Otherwise, put it "
         "into your hand. Then shuffle.", {"count": 0, "toHand": 1, "allowedSubtypes": {"Plains"}}),
        ("Archaeomancer's Map", "Artifact",
         "When this artifact enters, search your library for up to two basic Plains cards, reveal "
         "them, put them into your hand, then shuffle.\nWhenever a land an opponent controls enters, "
         "if that player controls more lands than you, you may put a land card from your hand onto "
         "the battlefield.", {"count": 0, "toHand": 2}),
        ("Land Tax", "Enchantment",
         "At the beginning of your upkeep, if an opponent controls more lands than you, you may search "
         "your library for up to three basic land cards, reveal them, put them into your hand, then "
         "shuffle.", None),
        ("Eye of Ugin", "Legendary Land",
         "Colorless Eldrazi spells you cast cost {2} less to cast.\n{7}, {T}: Search your library for a "
         "colorless creature card, reveal it, put it into your hand, then shuffle.", None),
    ]

    def test_ramp_spells_move_the_lands_their_text_says(self):
        for name, type_line, text, expected in self.RAMP_CASES:
            with self.subTest(card=name):
                got = exporter.parse_land_ramp_profile({"type_line": type_line, "oracle_text": text})
                if expected is None:
                    self.assertIsNone(got)
                    continue
                for key, want in expected.items():
                    self.assertEqual(got[key], want, key)

    def test_land_fetching_permanents(self):
        verge = self.model("Land", "This land enters tapped.\n{T}: Add {C}.\n{2}, {T}, Sacrifice this "
                           "land: Search your library for a Forest card and a Plains card, put them "
                           "onto the battlefield tapped, then shuffle.")
        self.assertEqual((verge["landFetch"]["count"], verge["landFetch"]["perType"],
                          verge["landFetch"]["cost"]["total"]), (2, ["Forest", "Plains"], 2))
        myriad = self.model("Land", "This land enters tapped.\n{T}: Add {C}.\n{2}, {T}, Sacrifice this "
                            "land: Search your library for up to two basic land cards that share a land "
                            "type, put them onto the battlefield tapped, then shuffle.")
        self.assertEqual((myriad["landFetch"]["count"], myriad["landFetch"]["sharedType"]), (2, True))
        elder = self.model("Creature — Snake Shaman", "Sacrifice this creature: Search your library "
                           "for a basic land card, put that card onto the battlefield tapped, then "
                           "shuffle.", colors=("G",), power="1")
        self.assertEqual((elder["landFetch"]["count"], elder["landFetch"]["cost"]["total"],
                          elder["manaAtoms"]), (1, 0, []))
        bauble = self.model("Artifact", CARDS["Wayfarer's Bauble"]["oracle_text"])
        self.assertEqual(bauble["landFetch"]["cost"]["total"], 2)

    def test_only_lasting_mana_and_land_ramp_are_mana_sources(self):
        cases = {"Sol Ring": True, "Elvish Archdruid": True, "Cultivate": True,
                 "Krark-Clan Ironworks": False, "Mana Vault": False, "Lotus Petal": False,
                 "Archaeomancer's Map": False, "Mox Amber": False, "Big Score": False}
        texts = {name: text for name, _, text, *_ in self.CASES}
        types = {name: type_line for name, type_line, *_ in self.CASES}
        texts.update({"Sol Ring": "{T}: Add {C}{C}.", "Cultivate": CARDS["Cultivate"]["oracle_text"],
                      "Archaeomancer's Map": self.RAMP_CASES[5][2]})
        types.update({"Sol Ring": "Artifact", "Cultivate": "Sorcery", "Archaeomancer's Map": "Artifact"})
        for name, expected in cases.items():
            with self.subTest(card=name):
                meta = {"type_line": types[name], "oracle_text": texts[name], "mana_cost": "{3}",
                        "cmc": 3, "colors": [], "power": "2"}
                profile = exporter.build_goldfish_profile(
                    name=name, meta=meta, category_names=set(), commander_colors=["G"],
                    commander_name="Other")
                self.assertEqual(exporter.is_mana_source(profile), expected)


class ManaBoardTests(unittest.TestCase):
    """Board terms read on the goldfish's own battlefield (M5): every card is
    put onto the battlefield on turn 1 and the turn-3 sources are read, so
    each counts. Card texts copied from data/card-metadata.json (2026-11-19).
    """

    TEXTS = {
        "Forest": ("Basic Land — Forest", "({T}: Add {G}.)", ()),
        "Swamp": ("Basic Land — Swamp", "({T}: Add {B}.)", ()),
        "Wastes": ("Basic Land", "{T}: Add {C}.", ()),
        "Tainted Wood": ("Land", CARDS["Tainted Wood"]["oracle_text"], ()),
        "Urborg, Tomb of Yawgmoth": ("Legendary Land", "Each land is a Swamp in addition to its other land types.", ()),
        "Urza's Mine": ("Land — Urza's Mine", "{T}: Add {C}. If you control an Urza's Power-Plant and an Urza's Tower, add {C}{C} instead.", ()),
        "Urza's Tower": ("Land — Urza's Tower", "{T}: Add {C}. If you control an Urza's Mine and an Urza's Power-Plant, add {C}{C}{C} instead.", ()),
        "Planar Nexus": ("Land", "This land is every nonbasic land type.\n{T}: Add {C}.\n{1}, {T}: Add one mana of any color.", ()),
        "Urza's Workshop": ("Land — Urza's", "{T}: Add {C}.\nMetalcraft — {T}: Add {C} for each Urza's land you control. Activate only if you control three or more artifacts.", ()),
        "Mind Stone": ("Artifact", "{T}: Add {C}.\n{1}, {T}, Sacrifice this artifact: Draw a card.", ()),
        "Elvish Archdruid": ("Creature — Elf Druid", "Other Elf creatures you control get +1/+1.\n{T}: Add {G} for each Elf you control.", ("G",)),
        "Llanowar Elves": ("Creature — Elf Druid", "{T}: Add {G}.", ("G",)),
        "Three Tree Mascot": ("Artifact Creature — Shapeshifter", "Changeling\n{1}: Add one mana of any color. Activate only once each turn.", ()),
        "Cabal Coffers": ("Land", "{2}, {T}: Add {B} for each Swamp you control.", ()),
        "Bloom Tender": ("Creature — Elf Druid", "Vivid — {T}: For each color among permanents you control, add one mana of that color.", ("G",)),
        "Probe BB": ("Creature — Test", "", ("B",)),
        "Mox Amber": ("Legendary Artifact", "{T}: Add one mana of any color among legendary creatures and planeswalkers you control.", ()),
        "Legend": ("Legendary Creature — Human", "", ("U", "R")),
        "Crypt Ghast": ("Creature — Spirit", "Extort\nWhenever you tap a Swamp for mana, add an additional {B}.", ("B",)),
        "Badgermole Cub": ("Creature — Badger Mole", "When this creature enters, earthbend 1.\nWhenever you tap a creature for mana, add an additional {G}.", ("G",)),
        "Forsaken Monument": ("Legendary Artifact", "Colorless creatures you control get +2/+2.\nWhenever you tap a permanent for {C}, add an additional {C}.", ()),
        "Sol Ring": ("Artifact", "{T}: Add {C}{C}.", ()),
        "Nykthos, Shrine to Nyx": ("Legendary Land", "{T}: Add {C}.\n{2}, {T}: Choose a color. Add an amount of mana of that color equal to your devotion to that color.", ()),
        "Llanowar Tribe": ("Creature — Elf Druid", "{T}: Add {G}{G}{G}.", ("G",)),
        "Shrine of the Forsaken Gods": ("Land", "{T}: Add {C}.\n{T}: Add {C}{C}. Spend this mana only to cast colorless spells. Activate only if you control seven or more lands.", ()),
        "Urza, Lord High Artificer": ("Legendary Creature — Human Artificer", CARDS["Urza, Lord High Artificer"]["oracle_text"], ("U",)),
        "Reflecting Pool": ("Land", "{T}: Add one mana of any type that a land you control could produce.", ()),
        "Chromatic Lantern": ("Artifact", "Lands you control have \"{T}: Add one mana of any color.\"\n{T}: Add one mana of any color.", ()),
        "Basalt Monolith": ("Artifact", CARDS["Basalt Monolith"]["oracle_text"], ()),
        "Zero Trinket": ("Artifact", "", ()),
        "Urza's Saga": ("Enchantment Land — Urza's Saga", CARDS.get("Urza's Saga", {}).get("oracle_text") or "I — This Saga gains \"{T}: Add {C}.\"\nII — This Saga gains \"{2}, {T}: Create a token.\"\nIII — Search your library for an artifact card with mana cost {0} or {1}, put it onto the battlefield, then shuffle.", ()),
    }
    TEXTS["Disciple of Freyalise // Garden of Freyalise"] = (
        "Creature — Elf Druid // Land",
        "When this creature enters, you may sacrifice another creature. If you do, you gain X life "
        "and draw X cards, where X is that creature's power.", ("G",))
    BACKS = {"Disciple of Freyalise // Garden of Freyalise": {
        "type_line": "Land",
        "oracle_text": "As this land enters, you may pay 3 life. If you don't, it enters tapped.\n{T}: Add {G}."}}
    COSTS = {"Llanowar Tribe": "{G}{G}{G}", "Elvish Archdruid": "{1}{G}{G}", "Llanowar Elves": "{G}",
             "Bloom Tender": "{1}{G}", "Probe BB": "{B}{B}",
             "Disciple of Freyalise // Garden of Freyalise": "{3}{G}{G}{G}"}

    def board(self, names, colours=("B", "G"), read_turn=3):
        metadata = {name: {"type_line": self.TEXTS[name][0], "oracle_text": self.TEXTS[name][1],
                           "colors": list(self.TEXTS[name][2]),
                           "mana_cost": self.COSTS.get(name, "" if "Land" in self.TEXTS[name][0].split(" // ")[0]
                                                       else "{0}"),
                           "cmc": 0, "power": "1"} for name in names}
        for name in names:
            if name in self.BACKS:
                metadata[name]["back_face"] = self.BACKS[name]
        context = exporter.build_goldfish_context(
            list(names), {"decklist": []}, metadata, "Legend" if "Legend" in names else names[0],
            list(colours), "synthetic-board")
        profiles = context["profiles"]
        permanents, lands = [], []
        for name in names:
            if profiles[name]["isLand"]:
                exporter.put_land_onto_battlefield(name, 1, False, permanents, lands, profiles, list(colours))
            else:
                exporter.resolve_cast_effects(name, profiles[name], 1, exporter.GoldfishManaPool([]),
                                              [], [], permanents, lands, profiles, list(colours))
        return mana_letters(exporter.board_mana(permanents, read_turn, profiles))

    def test_board_terms(self):
        cases = [
            # Tainted Wood's B/G needs a Swamp.
            (["Tainted Wood", "Forest"], ["C", "G"]),
            (["Tainted Wood", "Swamp"], ["B", "BGC"]),
            # Urborg makes every land a Swamp.
            # and every land can tap for {B} (F2: colour only, one mana).
            (["Tainted Wood", "Forest", "Urborg, Tomb of Yawgmoth"], ["B", "BG", "BGC"]),
            # Tron: Planar Nexus is a Power-Plant.
            (["Urza's Mine", "Urza's Tower"], ["C", "C"]),
            (["Urza's Mine", "Urza's Tower", "Planar Nexus"], ["C"] * 6),
            # Metalcraft: one {C} per Urza's land with three artifacts out.
            (["Urza's Workshop", "Urza's Mine", "Mind Stone", "Mind Stone"], ["C"] * 4),
            (["Urza's Workshop", "Urza's Mine", "Mind Stone", "Mind Stone", "Mind Stone"], ["C"] * 6),
            # Archdruid counts itself, Llanowar Elves and the changeling: three.
            (["Elvish Archdruid", "Llanowar Elves", "Three Tree Mascot"], ["G"] * 4),
            # Coffers: three Swamps less its {2}.
            (["Cabal Coffers", "Swamp", "Swamp", "Swamp"], ["B"] * 4),
            # Vivid: green (itself) and black (Probe BB).
            (["Bloom Tender", "Probe BB"], ["B", "G"]),
            # Mox Amber: the legendary creature's colours.
            (["Mox Amber"], []),
            (["Mox Amber", "Legend"], ["UR"]),
            # Crypt Ghast: one more {B} per Swamp.
            (["Crypt Ghast", "Swamp", "Swamp"], ["B"] * 4),
            # Badgermole Cub: one more {G} for Llanowar Elves and its earthbent land.
            (["Badgermole Cub", "Llanowar Elves", "Forest"], ["G"] * 4),
            # ... and for a count creature tapped for mana (Elvish Archdruid).
            (["Badgermole Cub", "Elvish Archdruid", "Forest"], ["G"] * 4),
            # Reflecting Pool: what the other lands could make; nothing alone.
            (["Reflecting Pool"], []),
            (["Reflecting Pool", "Forest", "Swamp"], ["B", "BG", "G"]),
            # Chromatic Lantern: every land makes any colour (one mana each).
            (["Chromatic Lantern", "Forest"], ["BG", "BG"]),
            # Forsaken Monument: one more {C} on Basalt Monolith's one-shot {C}{C}{C}.
            (["Forsaken Monument", "Basalt Monolith"], ["C"] * 4),
            # Forsaken Monument: one more {C} per permanent tapped for {C}.
            (["Forsaken Monument", "Sol Ring", "Wastes"], ["C"] * 5),
            # Nykthos in a green deck: devotion 3 + 2 = 5, less its {2}: three,
            # beside Llanowar Tribe's three and the Archdruid's two Elves.
            (["Nykthos, Shrine to Nyx", "Llanowar Tribe", "Elvish Archdruid"], ["G"] * 8),
            # Devotion 3 nets one: one mana, {C} or {G}.
            (["Nykthos, Shrine to Nyx", "Llanowar Tribe"], ["G", "G", "G", "GC"]),
            # An MDFC played as its land face has no mana cost: no devotion.
            (["Nykthos, Shrine to Nyx", "Llanowar Tribe", "Disciple of Freyalise // Garden of Freyalise"],
             ["G", "G", "G", "G", "GC"]),
            # Shrine of the Forsaken Gods: {C}{C} from seven lands.
            (["Shrine of the Forsaken Gods"] + ["Wastes"] * 5, ["C"] * 6),
            (["Shrine of the Forsaken Gods"] + ["Wastes"] * 6, ["C"] * 8),
        ]
        for names, expected in cases:
            colours = (("C",) if "Wastes" in names or "Urza's Mine" in names
                       else ("G",) if "Nykthos, Shrine to Nyx" in names else ("B", "G"))
            with self.subTest(board=names):
                self.assertEqual(self.board(names, colours), expected)

    def test_a_saga_makes_mana_until_its_last_chapter(self):
        # Urza's Saga enters on turn 1 with chapter I ("gains {T}: Add {C}").
        # Chapter III triggers on turn 3 and it is tapped for {C} before it
        # resolves and the Saga is sacrificed: {C} on turns 1 to 3.
        self.assertEqual(self.board(["Urza's Saga"], ("W",), read_turn=3), ["C"])
        self.assertEqual(self.board(["Urza's Saga"], ("W",), read_turn=4), [])

    def test_urza_taps_his_construct_and_idle_artifacts(self):
        # Urza alone: his Construct token pays one {U}. An artifact with no
        # mana of its own (Zero Trinket) pays another; Mind Stone taps for
        # its own {C} instead.
        self.assertEqual(self.board(["Urza, Lord High Artificer"], ("U",), read_turn=1), ["U"])
        self.assertEqual(self.board(["Urza, Lord High Artificer", "Zero Trinket"], ("U",),
                                    read_turn=1), ["U", "U"])
        self.assertEqual(self.board(["Urza, Lord High Artificer", "Mind Stone"], ("U",),
                                    read_turn=1), ["C", "U"])

    def test_a_pathway_enters_as_the_face_of_a_missing_colour(self):
        metadata = {"Brightclimb Pathway": CARDS["Brightclimb Pathway"]}
        context = exporter.build_goldfish_context(
            ["Brightclimb Pathway"], {"decklist": []}, metadata, "Brightclimb Pathway", ["W", "B"], "x")
        profiles = dict(context["profiles"], Plains={"landTypes": frozenset({"Plains"}), "eachLandIs": None})
        # No land out: a tie, the front face (W).
        record = exporter.put_land_onto_battlefield(
            "Brightclimb Pathway", 1, False, [], [], profiles, ["W", "B"])
        self.assertEqual(mana_letters(record["manaAtoms"]), ["W"])
        # A Plains out: the back face (B) adds the missing colour.
        record = exporter.put_land_onto_battlefield(
            "Brightclimb Pathway", 1, False, [],
            [{"name": "Plains", "colors": {"W"}, "subtypes": {"Plains"}, "isBasic": True}],
            profiles, ["W", "B"])
        self.assertEqual(mana_letters(record["manaAtoms"]), ["B"])


class ManaModelGoldfishTests(unittest.TestCase):
    """The mana model through the goldfish turn loop, with the opening fixed
    (the mulligan's shuffle replaced by a given hand and library, as in
    DrawEngineGoldfishTests); card data from CARDS. The commander is The
    Ur-Dragon, which these lands never cast, unless a case names another.
    library.pop() draws from the end, and turn 1 draws too (CR 103.8c), so a
    library whose card for turn 2 is the second from the end has, at the end,
    a card that changes nothing in the turns the case reads (Probe Nine,
    castable only with nine mana; Probe BB, which a deck without black never
    casts).
    """

    def _run(self, hand, library, colors=("C",), commander="The Ur-Dragon", deck_id="synthetic-mana"):
        decklist = hand + library
        context = exporter.build_goldfish_context(decklist, {"decklist": []}, CARDS, commander,
                                                  list(colors), deck_id)
        with patch.object(exporter, "commander_mulligan_goldfish", return_value=(library, hand)):
            by_turn, _ = exporter.simulate_goldfish_game(decklist, context, 6)
        return by_turn

    @staticmethod
    def _series(by_turn, key, turns=6):
        return [by_turn[turn][key] for turn in range(1, turns + 1)]

    def test_one_shot_mana_waits_for_the_turn_that_spends_it(self):
        # Turn 1: Wastes pays Mana Vault; its {C}{C}{C} is not needed, so it is
        # kept (available 1 + 3). Turn 2 draws Probe Five: two Wastes and the
        # Vault pay {5} (available 5), spending the Vault. Turn 3 on: Wastes
        # only. Forced onto turn 1, the Vault's mana would be gone and Probe
        # Five would wait for turn 5. Probe Five deals 5 from turn 3.
        library = ["Probe Nine"] * 91 + ["Probe Five", "Probe Nine"]
        by_turn = self._run(["Mana Vault"] + ["Wastes"] * 6, library)
        self.assertEqual(self._series(by_turn, "availableMana"), [4, 5, 3, 4, 5, 6])
        self.assertEqual(self._series(by_turn, "cumulativeDamage"), [0, 0, 5, 10, 15, 20])

    def test_a_spent_self_sacrificing_source_leaves(self):
        # Turn 1: Wastes and Lotus Petal pay Probe Two; the Petal is sacrificed
        # as its mana is spent, so it is gone from every later reading of turn
        # 1 (its mana counts for the turn). Probe Two deals 2 from turn 2.
        boards = []
        original = exporter.metrics_from_board

        def recording(**kwargs):  # call-through spy
            boards.append(sorted(p["name"] for p in kwargs["permanents"] if p["kind"] != "land"))
            return original(**kwargs)

        with patch.object(exporter, "metrics_from_board", recording):
            by_turn = self._run(["Lotus Petal", "Probe Two"] + ["Wastes"] * 5, ["Probe Nine"] * 92)
        self.assertEqual(self._series(by_turn, "availableMana"), [2, 2, 3, 4, 5, 5])
        self.assertEqual(self._series(by_turn, "cumulativeDamage"), [0, 2, 4, 6, 8, 10])
        self.assertEqual(boards[:2], [["Probe Two"], ["Probe Two"]])

    def test_a_cast_trigger_adds_mana_for_the_next_spell(self):
        # Birgi ({2}{R}) is cast on turn 3 with the three Mountains. Turn 4
        # draws the second Probe Two: the first costs two of the three
        # Mountains and Birgi adds {R}, which with the third Mountain pays the
        # second. Combat: Birgi 3 from turn 4, each Probe Two 2 from turn 5.
        # Turn 4's available mana counts Birgi's two {R}: 3 + 2. Birgi's
        # trigger does not tap her: she attacks.
        library = ["Probe Nine"] * 89 + ["Probe Two", "Probe Two", "Probe Nine", "Probe Nine"]
        by_turn = self._run(["Birgi, God of Storytelling // Harnfel, Horn of Bounty"]
                            + ["Mountain"] * 3 + ["Probe Nine"] * 3, library, colors=("R",))
        self.assertEqual(self._series(by_turn, "cumulativeDamage"), [0, 0, 0, 3, 10, 17])
        self.assertEqual(self._series(by_turn, "availableMana"), [1, 2, 3, 5, 3, 3])

    def test_a_conditional_land_turns_on_with_its_condition(self):
        # Turn 1 Tainted Wood (two new colours beat the Swamp's one): {C} only.
        # Turn 2 Swamp: Tainted Wood now adds {B}, so {B}{B} pays Probe BB,
        # which deals 2 from turn 3. Without the Swamp check it never could.
        by_turn = self._run(["Tainted Wood", "Swamp", "Probe BB"] + ["Probe Nine"] * 4,
                            ["Probe Nine"] * 92, colors=("B", "G"))
        self.assertEqual(self._series(by_turn, "cumulativeDamage"), [0, 0, 2, 4, 6, 8])

    def test_a_land_face_is_played_and_enters_tapped(self):
        # Hagra Mauling is the only land in hand: played as Hagra Broodpit,
        # which enters tapped (turn 1: 0) and makes {B} from turn 2; Swamps
        # follow from the library (turn 1 draws a Probe Nine).
        by_turn = self._run(["Hagra Mauling // Hagra Broodpit"] + ["Probe Nine"] * 6,
                            ["Swamp"] * 91 + ["Probe Nine"], colors=("B",))
        self.assertEqual(self._series(by_turn, "availableMana"), [0, 2, 3, 4, 5, 6])

    def test_a_basic_fetch_enters_untapped_with_three_other_lands(self):
        # Fabled Passage is cracked as it is played: the Forest it finds enters
        # tapped and untaps with four lands. Below three other lands it would
        # stay tapped, so the hand's Forests go first; on turn 4 the Forest
        # from the library enters untapped and the Passage is gone. With no
        # basic left in the library it finds nothing and makes nothing.
        hand = ["Fabled Passage", "Forest", "Forest", "Forest"] + ["Probe Nine"] * 3
        by_turn = self._run(list(hand), ["Forest"] + ["Probe Nine"] * 91, colors=("G",))
        self.assertEqual(self._series(by_turn, "availableMana"), [1, 2, 3, 4, 4, 4])
        self.assertEqual(self._series(by_turn, "lands"), [1, 2, 3, 4, 4, 4])
        by_turn = self._run(list(hand), ["Probe Nine"] * 92, colors=("G",))
        self.assertEqual(self._series(by_turn, "availableMana"), [1, 2, 3, 3, 3, 3])

    def test_a_typed_fetch_puts_a_land_of_its_types_onto_the_battlefield(self):
        # Turn 1 Polluted Delta is cracked for the Swamp in the library. Turn 2
        # Drowned Catacomb ("enters tapped unless you control an Island or a
        # Swamp") sees that Swamp and enters untapped: Probe BB on turn 2.
        # With the Delta kept as a stand-in the Catacomb would enter tapped.
        by_turn = self._run(["Polluted Delta", "Drowned Catacomb", "Probe BB"] + ["Probe Nine"] * 4,
                            ["Swamp"] + ["Probe Nine"] * 91, colors=("U", "B"))
        self.assertEqual(self._series(by_turn, "availableMana"), [1, 2, 2, 2, 2, 2])
        self.assertEqual(self._series(by_turn, "cumulativeDamage"), [0, 0, 2, 4, 6, 8])

    def test_cultivate_puts_one_land_onto_the_battlefield_and_one_in_hand(self):
        # Turn 3: Cultivate fetches a tapped Forest and puts the other in hand
        # (lands 4); turn 4 plays it (lands 5). Two Forests sit at the bottom
        # of the library for the search.
        library = ["Forest", "Forest"] + ["Probe Nine"] * 90
        by_turn = self._run(["Cultivate", "Forest", "Forest", "Forest"] + ["Probe Nine"] * 3,
                            library, colors=("G",))
        self.assertEqual(self._series(by_turn, "lands"), [1, 2, 4, 5, 5, 5])
        self.assertEqual(self._series(by_turn, "availableMana"), [1, 2, 3, 5, 5, 5])

    def test_a_one_shot_source_is_not_cast_ahead_of_the_commander(self):
        # Turn 5 draws Probe Petal Four ({4}; "{T}, Sacrifice this artifact:
        # Add {C}{C}") with five Wastes out, the first turn Probe Commander
        # ({5}) is castable. The Petal's one-shot {C}{C} is not a mana source
        # for the cast order, so the commander comes first. Sorted as ramp,
        # the Petal would go first and leave 1 + 2 mana: the commander would
        # wait for turn 6.
        library = ["Probe Nine"] * 88 + ["Probe Petal Four"] + ["Probe Nine"] * 4
        by_turn = self._run(["Wastes"] * 6 + ["Probe Nine"], library, commander="Probe Commander")
        self.assertEqual(self._series(by_turn, "commanderCast"), [0, 0, 0, 0, 1, 1])

    def test_a_land_fetching_permanent_is_activated_with_spare_mana(self):
        # Turn 1: Wastes casts Wayfarer's Bauble. Turn 2: two Wastes pay its
        # {2} at the end of the turn and a Wastes from the library enters
        # tapped: the board, read after that, has three lands; the turn had two
        # mana. Turn 3 has four lands, all untapped.
        library = ["Wastes"] + ["Probe Nine"] * 91
        by_turn = self._run(["Wayfarer's Bauble"] + ["Wastes"] * 6, library)
        self.assertEqual(self._series(by_turn, "lands"), [1, 3, 4, 5, 6, 7])
        self.assertEqual(self._series(by_turn, "availableMana"), [1, 2, 4, 5, 6, 7])

    def test_a_land_fetch_that_gains_no_land_is_not_activated(self):
        # Krosan Verge: "{2}, {T}, Sacrifice this land: Search your library for
        # a Forest card and a Plains card, put them onto the battlefield
        # tapped". With only Forests in the library it would trade itself for
        # one land: kept. With a Plains too it nets a land: activated.
        verge = {"type_line": "Land", "mana_cost": "", "cmc": 0, "colors": [], "oracle_text": (
            "This land enters tapped.\n{T}: Add {C}.\n{2}, {T}, Sacrifice this land: Search your "
            "library for a Forest card and a Plains card, put them onto the battlefield tapped, then "
            "shuffle.")}
        plains = {"type_line": "Basic Land — Plains", "mana_cost": "", "cmc": 0, "colors": [],
                  "oracle_text": "({T}: Add {W}.)"}
        metadata = {"Krosan Verge": verge, "Forest": CARDS["Forest"], "Plains": plains}
        for library, expected in ((["Forest", "Forest"], ["Forest", "Forest", "Krosan Verge"]),
                                  (["Forest", "Plains"], ["Forest", "Forest", "Forest", "Plains"])):
            with self.subTest(library=library):
                context = exporter.build_goldfish_context(
                    ["Krosan Verge", "Forest", "Plains"], {"decklist": []}, metadata, "Forest",
                    ["G", "W"], "synthetic-fetch")
                profiles = context["profiles"]
                permanents, lands = [], []
                for name in ("Krosan Verge", "Forest", "Forest"):
                    exporter.put_land_onto_battlefield(name, 1, False, permanents, lands, profiles,
                                                       ["G", "W"])
                exporter.activate_land_fetches(
                    2, exporter.GoldfishManaPool([frozenset("C"), frozenset("G"), frozenset("G")]),
                    list(library), [], permanents, lands, profiles, ["G", "W"])
                self.assertEqual(sorted(p["name"] for p in permanents), expected)

    def test_a_land_that_sacrifices_two_lands_waits_for_them(self):
        # Scorched Ruins needs two other lands. In a colourless deck its {C}
        # outscores a Mountain, so it would be played first; it waits:
        # Mountains on turns 1 and 2, then Ruins on turn 3 for its net {C}{C}.
        by_turn = self._run(["Scorched Ruins", "Mountain", "Mountain"] + ["Probe Nine"] * 4,
                            ["Probe Nine"] * 92)
        self.assertEqual(self._series(by_turn, "availableMana"), [1, 2, 4, 4, 4, 4])
        # The two Mountains are gone: one land from turn 3.
        self.assertEqual(self._series(by_turn, "lands"), [1, 2, 1, 1, 1, 1])

    def test_lands_given_up_no_longer_count_for_later_lands(self):
        # Turn 3 Scorched Ruins sacrifices both Mountains. On turn 4 Probe
        # Slow Land ("enters tapped unless you control two or more other
        # lands") sees one other land and enters tapped: 4 mana, 5 from
        # turn 5. Counting the sacrificed Mountains it would enter untapped.
        by_turn = self._run(["Scorched Ruins", "Mountain", "Mountain", "Probe Slow Land"]
                            + ["Probe Nine"] * 3, ["Probe Nine"] * 92)
        self.assertEqual(self._series(by_turn, "lands"), [1, 2, 1, 2, 2, 2])
        self.assertEqual(self._series(by_turn, "availableMana"), [1, 2, 4, 4, 5, 5])

    def test_lands_an_entering_trigger_takes_are_tapped_first(self):
        # Turn 3 draws Probe Two; Lotus Field enters tapped and its trigger
        # sacrifices both Wastes, tapped for {C}{C} in response, which casts
        # Probe Two that turn (2 damage from turn 4). From turn 4 Lotus Field
        # alone makes 3.
        by_turn = self._run(["Lotus Field", "Wastes", "Wastes"] + ["Probe Nine"] * 4,
                            ["Probe Nine"] * 90 + ["Probe Two", "Probe Nine", "Probe Nine"])
        self.assertEqual(self._series(by_turn, "lands"), [1, 2, 1, 1, 1, 1])
        self.assertEqual(self._series(by_turn, "availableMana"), [1, 2, 2, 3, 3, 3])
        self.assertEqual(self._series(by_turn, "cumulativeDamage"), [0, 0, 0, 2, 4, 6])

    def test_a_land_returned_to_the_hand_is_played_again(self):
        # Turn 2 Simic Growth Chamber returns the Forest (tapped for {G}
        # first) and enters tapped; turn 3 plays the Forest again.
        by_turn = self._run(["Simic Growth Chamber", "Forest"] + ["Probe Nine"] * 5,
                            ["Probe Nine"] * 92, colors=("U", "G"))
        self.assertEqual(self._series(by_turn, "lands"), [1, 1, 2, 2, 2, 2])
        self.assertEqual(self._series(by_turn, "availableMana"), [1, 1, 3, 3, 3, 3])

    def test_a_mana_creature_attacks_when_the_lands_pay(self):
        # Turn 1 Forest and Llanowar Elves. Turn 2 the two Forests pay Probe
        # Two, so the Elves attack (1). Turn 3 the Elves and Probe Two attack.
        by_turn = self._run(["Llanowar Elves", "Forest", "Forest", "Probe Two"] + ["Probe Nine"] * 3,
                            ["Probe Nine"] * 92, colors=("G",))
        self.assertEqual(self._series(by_turn, "cumulativeDamage"), [0, 1, 4, 7, 10, 13])

    def test_a_mana_creature_tapped_for_a_spell_does_not_attack(self):
        # Turn 2 Probe Three needs the two Forests and the Elves: the Elves are
        # tapped and do not attack. Turn 3 nothing is cast: Elves 1 + Probe 3.
        by_turn = self._run(["Llanowar Elves", "Forest", "Forest", "Probe Three"] + ["Probe Nine"] * 3,
                            ["Probe Nine"] * 92, colors=("G",))
        self.assertEqual(self._series(by_turn, "cumulativeDamage"), [0, 0, 4, 8, 12, 16])

    def test_a_mana_creature_that_attacked_has_no_mana_after_combat(self):
        # Turn 2 a Forest casts Wayfarer's Bauble; the Elves attack, so the
        # one Forest left cannot pay the Bauble's {2} at the end of the turn.
        # Turn 3 nothing is cast: the Elves attack again and the two Forests
        # pay it; the Forest from the library enters tapped (the board is read
        # after it).
        library = ["Forest"] + ["Probe Nine"] * 91
        by_turn = self._run(["Llanowar Elves", "Forest", "Forest", "Wayfarer's Bauble"]
                            + ["Probe Nine"] * 3, library, colors=("G",))
        self.assertEqual(self._series(by_turn, "lands"), [1, 2, 3, 3, 3, 3])
        self.assertEqual(self._series(by_turn, "cumulativeDamage"), [0, 1, 2, 3, 4, 5])

    def test_ugins_labyrinth_imprints_a_big_colorless_card(self):
        # With Probe Nine (colourless, mana value 9) in hand Ugin's Labyrinth
        # exiles it and makes {C}{C} from turn 1: Probe Two is cast on turn 1
        # and attacks from turn 2. With no such card it makes {C}: Probe Two
        # waits for turn 2 (the Wastes drawn; turn 1 draws a Probe BB, which
        # a colourless deck never casts).
        library = ["Wastes"] * 91 + ["Probe BB"]
        by_turn = self._run(["Ugin's Labyrinth", "Probe Two", "Probe Nine"] + ["Probe BB"] * 4, list(library))
        self.assertEqual(self._series(by_turn, "availableMana"), [2, 3, 4, 5, 6, 7])
        self.assertEqual(self._series(by_turn, "cumulativeDamage"), [0, 2, 4, 6, 8, 10])
        by_turn = self._run(["Ugin's Labyrinth", "Probe Two"] + ["Probe BB"] * 5, list(library))
        self.assertEqual(self._series(by_turn, "availableMana"), [1, 2, 3, 4, 5, 6])
        self.assertEqual(self._series(by_turn, "cumulativeDamage"), [0, 0, 2, 4, 6, 8])

    def test_chrome_mox_imprints_a_coloured_card(self):
        # Turn 1 Chrome Mox exiles Probe Kill (black interaction the goldfish
        # never casts) and taps for {B}: with the Swamp it casts Probe BB on
        # turn 1. With only colourless cards to exile the Mox makes nothing
        # and Probe Two waits for turn 2.
        library = ["Swamp"] * 92
        by_turn = self._run(["Chrome Mox", "Swamp", "Probe BB", "Probe Kill"] + ["Probe Nine"] * 3,
                            library, colors=("B",))
        self.assertEqual(self._series(by_turn, "availableMana"), [2, 3, 4, 5, 6, 7])
        self.assertEqual(self._series(by_turn, "cumulativeDamage"), [0, 2, 4, 6, 8, 10])
        by_turn = self._run(["Chrome Mox", "Swamp", "Probe Two"] + ["Probe Nine"] * 4,
                            library, colors=("B",))
        self.assertEqual(self._series(by_turn, "availableMana"), [1, 2, 3, 4, 5, 6])
        self.assertEqual(self._series(by_turn, "cumulativeDamage"), [0, 0, 2, 4, 6, 8])


class ManaRoundOneGoldfishTests(unittest.TestCase):
    """Review round 1 (2026-11-20): one tapped state per permanent, exact
    payment, fetch lands that fetch, Sagas and self-sacrificing sources that
    leave, mana added during the turn. The ManaModelGoldfishTests harness."""

    _run = ManaModelGoldfishTests._run
    _series = staticmethod(ManaModelGoldfishTests._series)

    def test_one_shot_mana_is_spent_after_the_lands(self):
        # Turn 2 draws Probe Two: the two Wastes pay it and Mana Vault's
        # {C}{C}{C} is kept: 3 + 3 on turn 3, until Probe Nine takes it on
        # turn 6. Spending the Vault with the lands, turn 3 would have 3.
        library = ["Probe Nine"] * 91 + ["Probe Two", "Probe Nine"]
        by_turn = self._run(["Mana Vault"] + ["Wastes"] * 6, library)
        self.assertEqual(self._series(by_turn, "availableMana"), [4, 5, 6, 7, 8, 9])

    def test_basalt_monolith_untaps_on_a_later_turn_with_three_mana_left(self):
        # Turn 3 Basalt Monolith (kept, 3 + 3); turn 4 Probe Five takes four
        # Wastes and one of its {C}: spent, with no mana left to untap it.
        # Turn 5 its five Wastes are unspent, so it untaps at the end of the
        # turn: turn 6 has 6 + 3.
        library = ["Probe Nine"] * 89 + ["Probe Five", "Probe Nine", "Probe Nine"]
        by_turn = self._run(["Basalt Monolith"] + ["Wastes"] * 6, library)
        self.assertEqual(self._series(by_turn, "availableMana"), [1, 2, 6, 7, 5, 9])

    def test_a_snarl_reveals_from_the_hand_at_the_land_drop(self):
        # Turn 1 Shineshadow Snarl reveals the Swamp in hand and enters
        # untapped; turn 2 the Swamp. Not reading the hand, the Swamp would go
        # first and the Snarl would enter tapped on turn 2.
        by_turn = self._run(["Shineshadow Snarl", "Swamp"] + ["Probe Nine"] * 5,
                            ["Probe Nine"] * 92, colors=("W", "B"))
        self.assertEqual(self._series(by_turn, "availableMana"), [1, 2, 2, 2, 2, 2])

    def test_a_saga_leaves_after_its_last_chapter(self):
        # Wastes turns 1-2 (the Saga loses the name tie-break), Urza's Saga
        # turn 3 ({C} turns 3-5). On turn 5 it is tapped as chapter III
        # resolves and leaves before the land drop: two lands from turn 5,
        # its {C} still in turn 5's mana.
        by_turn = self._run(["Urza's Saga", "Wastes", "Wastes"] + ["Probe Nine"] * 4,
                            ["Probe Nine"] * 92)
        self.assertEqual(self._series(by_turn, "lands"), [1, 2, 3, 3, 2, 2])
        self.assertEqual(self._series(by_turn, "availableMana"), [1, 2, 3, 3, 3, 2])

    def test_a_vigilant_attacker_keeps_its_mana(self):
        # Turn 2 a Forest casts Wayfarer's Bauble; Probe Vigilant Elf attacks
        # untapped, so the other Forest and its {G} pay the Bauble at the end
        # of turn 2 (three lands read). Losing its mana in the attack, the
        # Bauble would wait for turn 3.
        library = ["Forest"] + ["Probe Nine"] * 91
        by_turn = self._run(["Probe Vigilant Elf", "Forest", "Forest", "Wayfarer's Bauble"]
                            + ["Probe Nine"] * 3, library, colors=("G",))
        self.assertEqual(self._series(by_turn, "lands"), [1, 3, 3, 3, 3, 3])
        self.assertEqual(self._series(by_turn, "cumulativeDamage"), [0, 1, 2, 3, 4, 5])

    def test_a_count_mana_creature_tapped_for_mana_does_not_attack(self):
        # Elvish Archdruid ({T}: Add {G} for each Elf) on turn 3; turn 4 draws
        # Probe Five: four Forests and the Archdruid's {G} pay it, so the
        # Archdruid does not attack on turn 4 (3 from turn 5, Probe Five 5
        # from turn 5). Read as a land's mana it would attack on turn 4.
        library = ["Probe Nine"] * 89 + ["Probe Five", "Probe Nine", "Probe Nine", "Probe Nine"]
        by_turn = self._run(["Elvish Archdruid"] + ["Forest"] * 4 + ["Probe Nine"] * 2,
                            library, colors=("G",))
        self.assertEqual(self._series(by_turn, "cumulativeDamage"), [0, 0, 0, 0, 8, 16])

    def test_an_untapped_land_from_a_ramp_spell_joins_the_turns_mana(self):
        # Turn 2 two Forests cast Three Visits, which puts a Forest onto the
        # battlefield untapped: its {G} is the turn's third mana.
        by_turn = self._run(["Three Visits", "Forest", "Forest"] + ["Probe Nine"] * 4,
                            ["Forest"] + ["Probe Nine"] * 91, colors=("G",))
        self.assertEqual(self._series(by_turn, "availableMana"), [1, 3, 3, 3, 3, 3])

    def test_lands_given_up_are_the_ones_with_the_least_mana(self):
        # Ancient Tomb ({C}{C}) turn 1, Wastes turns 2-3, Scorched Ruins turn
        # 4: it sacrifices the two Wastes and keeps the Tomb: 2 + 4 from turn
        # 4. Giving up the Tomb would leave 1 + 4.
        library = ["Probe Nine"] * 89 + ["Scorched Ruins", "Wastes", "Wastes", "Probe Nine"]
        by_turn = self._run(["Ancient Tomb"] + ["Probe Nine"] * 6, library)
        self.assertEqual(self._series(by_turn, "availableMana"), [2, 3, 4, 6, 6, 6])

    def test_a_land_fetch_is_paid_without_the_lands_own_mana(self):
        # Forest turn 1, Myriad Landscape turn 2 (tapped). Turn 3 has no land
        # drop: the Forest alone cannot pay {2} with the Landscape tapped for
        # the ability, so it is kept (two lands). Paying with its own {C} it
        # would fetch the two Forests on turn 3 (three lands read).
        myriad = {"type_line": "Land", "mana_cost": "", "cmc": 0, "colors": [], "oracle_text": (
            "This land enters tapped.\n{T}: Add {C}.\n{2}, {T}, Sacrifice this land: Search your "
            "library for up to two basic land cards that share a land type, put them onto the "
            "battlefield tapped, then shuffle.")}
        with patch.dict(CARDS, {"Myriad Landscape": myriad}):
            by_turn = self._run(["Forest", "Myriad Landscape"] + ["Probe Nine"] * 5,
                                ["Forest", "Forest"] + ["Probe Nine"] * 90, colors=("G",))
        self.assertEqual(self._series(by_turn, "lands"), [1, 2, 2, 2, 2, 2])

    def test_chrome_mox_is_not_cast_with_nothing_to_exile(self):
        # Only colourless cards in hand: the Mox stays in hand (no ramp
        # permanent on the battlefield). With Probe Kill to exile it is cast.
        by_turn = self._run(["Chrome Mox", "Swamp", "Probe Two"] + ["Probe Nine"] * 4,
                            ["Swamp"] * 92, colors=("B",))
        self.assertEqual(self._series(by_turn, "ramp"), [0] * 6)
        by_turn = self._run(["Chrome Mox", "Swamp", "Probe Kill"] + ["Probe Nine"] * 4,
                            ["Swamp"] * 92, colors=("B",))
        self.assertEqual(self._series(by_turn, "ramp"), [1] * 6)

    def test_urza_makes_his_mana_the_turn_he_enters(self):
        # Turn 1 Island and Zero Trinket (an artifact with no mana). Turn 4
        # four Islands cast Urza: his Construct and the Trinket pay {U}{U} at
        # once, which casts Probe Two that turn (2 from turn 5).
        library = ["Probe Nine"] * 89 + ["Probe Two", "Island", "Island", "Probe Nine"]
        by_turn = self._run(["Urza, Lord High Artificer", "Island", "Island", "Zero Trinket"]
                            + ["Probe Nine"] * 3, library, colors=("U",))
        self.assertEqual(self._series(by_turn, "availableMana"), [1, 2, 3, 6, 6, 6])
        # Urza 4 and Probe Two 2 from turn 5.
        self.assertEqual(self._series(by_turn, "cumulativeDamage"), [0, 0, 0, 0, 6, 12])

    def test_a_reachable_combo_line_keeps_its_mana_creature_home(self):
        # Probe Combo A ({1}{G}) and Probe Combo B ({G}) are a combo line.
        # Turn 2: two Forests and Llanowar Elves pay both, so the line is
        # ready (comboLethal) and the Elves do not attack. Turn 3 on the line
        # has fired: the Elves attack.
        decklist_hand = ["Llanowar Elves", "Forest", "Forest", "Probe Combo A", "Probe Combo B",
                         "Probe Nine", "Probe Nine"]
        library = ["Probe Nine"] * 92
        deck_data = {"decklist": [], "winConditions": [
            {"title": "Probe line", "kind": "combo", "pieces": ["Probe Combo A", "Probe Combo B"],
             "cards": ["Probe Combo A", "Probe Combo B"], "description": ""}]}
        context = exporter.build_goldfish_context(decklist_hand + library, deck_data, CARDS,
                                                  "The Ur-Dragon", ["G"], "synthetic-line")
        with patch.object(exporter, "commander_mulligan_goldfish",
                          return_value=(list(library), list(decklist_hand))):
            by_turn, _ = exporter.simulate_goldfish_game(decklist_hand + library, context, 6)
        self.assertEqual(self._series(by_turn, "comboLethal"), [0, 1, 1, 1, 1, 1])
        self.assertEqual(self._series(by_turn, "cumulativeDamage"), [0, 0, 1, 2, 3, 4])


class ManaLegalityReplayTests(unittest.TestCase):
    """An independent limit on the mana the goldfish spends (review rounds 4
    and 5, after review10r5/legal5.py): seeded games of every fleet deck, and
    after every committed payment each mana it used is checked against what
    the reviewed card table (tests/fixtures/goldfish_mana.json, with the
    cards' type lines, mana costs and oracle text from data/card-metadata.json;
    never the exporter's profiles) says that card can make on that board:

    A  the mana each source pays in a turn is within its cap, a gated or
       counted ability's condition read on the board at that payment, an
       extra trigger's bonus only while its source is on the battlefield and
       its condition holds, an imprint's mana as its entry names it (Chrome
       Mox: one);
    B  each mana's colours are colours that card can make, a gated
       ability's only while its condition holds on that board (Spire of
       Industry), a counted ability's only while it counts one or more
       (Cabal Coffers), a Pathway's those of the face it entered as, an
       imprint's those of the card it exiled (Chrome Mox), both as the game
       chose them (Reflecting Pool: what the other lands' abilities could
       make, costs ignored);
    C  a source tapped before the payment, and not already used this turn,
       does not pay with mana that taps it;
    D  a non-land the table says makes mana from the next turn, a land that
       entered tapped (or that the table says enters tapped) and a land
       creature do not pay the turn they entered;
    E  a permanent's own {T} ability and its {T} mana are not both used in a
       turn;
    F  mana with no source is not spent beyond what was added;
    G  a payment uses exactly as many mana as the cost;
    I  one-shot mana is used at most once per arming (its own mana, plus a
       Monument extra on the {C} while Monument is out), counted per arming;
    J  a creature whose {T} mana paid does not attack that turn, and one
       that attacked does not then pay with it (vigilance excepted, read
       from the card's own text);
    K  whether a mana taps its source agrees with the table (a land's and
       Urza's grant to an artifact do)."""

    DECKS = {"titan-convergence": "sim_titan", "eternal-agony": "sim_rakdos", "gathering-shadow": "sim_grixis",
             "eternal-harvest": "sim_golgari", "witherbloom-the-balancer": "sim_witherbloom",
             "the-white-forge": "sim_mono_white", "verdant-tide": "sim_mono_green",
             "creeping-corruption": "sim_wubg_poison", "grave-dividends": "sim_grave_dividends",
             "hidden-legion": "sim_hidden_legion", "zada-hedron-grinder": "sim_zada",
             "exponential-growth": "sim_exponential_growth", "slivers": "sim_slivers",
             "stampede-acres": "sim_stampede_acres", "tidal-legion": "sim_tidal_legion",
             "armory-protocol": "sim_armory_protocol", "shield-doctrine": "sim_shield_doctrine",
             "gandalf-party-guest": "sim_gandalf", "hoard-and-bleed": "sim_hoard_and_bleed",
             "broodfire-hatchery": "sim_broodfire_hatchery", "anvil-chorus": "sim_anvil_chorus"}
    GAMES = 30
    # Enough games for the rarer boards a control mutant needs (review round
    # 5): armory-protocol's artifact creatures beside Urza.
    GAMES_BY_DECK = {"armory-protocol": 100}
    ROOT = Path(__file__).resolve().parent.parent
    BASIC_TYPES = {"Plains", "Island", "Swamp", "Mountain", "Forest"}
    LAND_COLOURS = {"Plains": "W", "Island": "U", "Swamp": "B", "Mountain": "R", "Forest": "G"}

    @classmethod
    def setUpClass(cls):
        cls.table = json.loads((cls.ROOT / "tests" / "fixtures" / "goldfish_mana.json").read_text())
        cls.meta = json.loads((cls.ROOT / "data" / "card-metadata.json").read_text())

    # ---- what a card is, read from the metadata and the table
    def type_line(self, name):
        return (self.meta.get(name, {}).get("type_line", "") or "").split(" // ")[0]

    def land_type_line(self, name):
        """The type line of the face a land is played as (a modal DFC's back)."""
        meta = self.meta.get(name, {})
        if "Land" not in self.type_line(name) and meta.get("back_face"):
            return meta["back_face"].get("type_line", "")
        return self.type_line(name)

    def has_type(self, permanent, word, permanents):
        if permanent.get("kind") == "land":
            words = set(re.findall(r"[A-Za-z'-]+", self.land_type_line(permanent["name"])))
            if word == "Swamp" and any(p["name"] == "Urborg, Tomb of Yawgmoth" for p in permanents):
                return True
            return word in words or bool(self.table.get(permanent["name"], {}).get("everyNonbasicType")
                                         and word not in self.BASIC_TYPES)
        words = set(re.findall(r"[A-Za-z'-]+", self.type_line(permanent["name"])))
        oracle = self.meta.get(permanent["name"], {}).get("oracle_text", "") or ""
        return word in words or ("Changeling" in oracle and word not in self.BASIC_TYPES
                                 and word not in {"Creature", "Artifact", "Land", "Enchantment"})

    def devotion(self, permanents, colour):
        total = 0
        for p in permanents:
            if p.get("kind") != "land":
                cost = (self.meta.get(p["name"], {}).get("mana_cost", "") or "").split(" // ")[0]
                total += sum(1 for sym in re.findall(r"\{([^}]+)\}", cost) if colour in sym.split("/"))
        return total

    def condition(self, parts, permanents):
        """A table gate ("landTypes:A|B", "atLeast:Type:N", "anyType:A|B")
        read on the board."""
        kind = parts[0]
        if kind == "landTypes":
            return all(any(p.get("kind") == "land" and self.has_type(p, t, permanents) for p in permanents)
                       for t in parts[1].split("|"))
        if kind == "atLeast":
            return sum(1 for p in permanents if self.has_type(p, parts[1], permanents)) >= int(parts[2])
        return any(p.get("kind") == "land" and self.has_type(p, t, permanents)
                   for p in permanents for t in parts[1].split("|"))

    @staticmethod
    def expand(atom, cmd):
        if atom == "cmd":
            return set(cmd) or {"C"}
        if atom == "C+cmd":
            return {"C"} | set(cmd)
        return set(atom)

    def lasting_cap(self, name, permanents, cmd):
        entry = self.table.get(name, {})
        # An imprint makes the mana its table entry names: its atoms, or one
        # mana of the exiled card's colours ("colors": Chrome Mox).
        imprint = entry.get("imprint")
        imprint_cap = 0 if not imprint else 1 if imprint["atoms"] == "colors" else len(imprint["atoms"])
        cap = max(len(entry.get("mana", [])), 1 if entry.get("faces") else 0, imprint_cap)
        for term in entry.get("board", []):
            parts = term.split(":")
            if parts[0] == "gate":
                if self.condition(parts[1:-1], permanents):
                    cap = max(cap, len(parts[-1].split(",")))
            elif parts[0] == "count" and parts[1] == "type":
                if len(parts) > 5 and not self.condition(parts[5:], permanents):
                    continue
                cap = max(cap, sum(1 for p in permanents if self.has_type(p, parts[2], permanents)) - int(parts[4]))
            elif parts[0] == "count" and parts[1] == "devotion":
                colours = cmd if parts[2] == "cmd" else list(parts[2])
                cap = max([cap] + [self.devotion(permanents, c) - int(parts[3]) for c in colours])
            elif parts[0] == "count" and parts[1] == "idleArtifacts":
                cap = max(cap, int(parts[2]))
            elif parts[0] == "vivid":
                cap = max(cap, len(set().union(*(set(self.meta.get(p["name"], {}).get("colors") or [])
                                                  for p in permanents))))
            elif parts[0] in ("legendColors", "landColors"):
                cap = max(cap, 1)
        return cap

    def urza_eligible(self, record, permanents):
        entry = self.table.get(record["name"], {})
        type_line = self.type_line(record["name"])
        return (any(p["name"] == "Urza, Lord High Artificer" for p in permanents) and "Artifact" in type_line
                and "Creature" not in type_line and record.get("kind") != "land"
                and not (entry.get("mana") or entry.get("once") or entry.get("board")))

    def extras(self, permanents):
        """The table's "extra" terms of the permanents on the battlefield."""
        return [term.split(":") for p in permanents for term in self.table.get(p["name"], {}).get("board", [])
                if term.startswith("extra")]

    def caps(self, record, permanents, cmd):
        """(lasting, one-shot) mana one record can make on this board."""
        name = record["name"]
        if name.endswith("(earthbent land)"):
            return 1, 0
        entry = self.table.get(name, {})
        lasting, once = self.lasting_cap(name, permanents, cmd), len(entry.get("once", []))
        if record.get("kind") == "land" and lasting == 0 and any(
                self.table.get(p["name"], {}).get("landGrant") for p in permanents):
            lasting = 1
        if self.urza_eligible(record, permanents):
            lasting += 1
        type_line = self.type_line(name)
        for _, source, _, _ in self.extras(permanents):
            if source == "colorlessSources":
                if lasting and any("C" in self.expand(a, cmd) for a in entry.get("mana", [])
                                   + (["C"] if any(t.startswith(("count", "gate")) for t in entry.get("board", []))
                                      else [])):
                    lasting += 1
                if once and any("C" in self.expand(a, cmd) for a in entry.get("once", [])):
                    once += 1
            elif source == "swampsTapped":
                if record.get("kind") == "land" and self.has_type(record, "Swamp", permanents) and lasting:
                    lasting += 1
            elif source == "creatureSources" and "Creature" in type_line and entry.get("taps") and lasting:
                lasting += 1
        return lasting, once

    def oracle_outputs(self, name, cmd):
        """Colours any of a land's add abilities could make (CR 106.7, costs
        ignored), and its basic land types'."""
        colours = set()
        meta = self.meta.get(name, {})
        text = meta.get("oracle_text", "") or ""
        if "Land" not in self.type_line(name) and meta.get("back_face"):
            text = meta["back_face"].get("oracle_text", "") or ""
        for clause in re.findall(r"[Aa]dd ([^.]*)", re.sub(r"\([^)]*\)", "", text)):
            colours |= set(re.findall(r"\{([WUBRGC])\}", clause))
            if re.search(r"any (?:one )?colou?r|any combination of colors", clause):
                colours |= self.expand("cmd", cmd)
        for word, colour in self.LAND_COLOURS.items():
            if word in self.land_type_line(name):
                colours.add(colour)
        return colours

    def counted(self, parts, permanents, cmd):
        """The mana a "count" term makes on this board before its cost (Cabal
        Coffers: a Swamp each), 0 while its own condition fails."""
        if parts[1] == "type":
            if len(parts) > 5 and not self.condition(parts[5:], permanents):
                return 0
            return sum(1 for p in permanents if self.has_type(p, parts[2], permanents))
        if parts[1] == "devotion":
            return max(self.devotion(permanents, c) for c in (cmd if parts[2] == "cmd" else list(parts[2])))
        return int(parts[2])  # idleArtifacts

    def allowed_colours(self, record, permanents, cmd, depth=0):
        name = record["name"]
        if name.endswith("(earthbent land)"):
            return {"G"}
        entry = self.table.get(name, {})
        colours = set()
        # A Pathway makes the colours of the face it entered as (observed as
        # it entered: self.observed["face"]); with no face observed (its mana
        # matched neither face, or it was never seen entering) it makes no face
        # colours. Every land enters through put_land_onto_battlefield.
        faces = [face for i, face in enumerate(entry.get("faces", []))
                 if i == self.observed["face"].get(id(record))]
        for atom in entry.get("mana", []) + entry.get("once", []) + [a for face in faces for a in face]:
            colours |= self.expand(atom, cmd)
        imprint = entry.get("imprint")
        if imprint and imprint.get("atoms") == "colors":
            # One mana of the colours of the card it exiled (observed as it
            # was exiled: self.observed["imprint"]); nothing exiled, none.
            card = self.observed["imprint"].get(id(record))
            colours |= set(self.meta.get(card, {}).get("colors") or []) if card else set()
        elif imprint:
            colours |= set().union(*(self.expand(a, cmd) for a in imprint["atoms"]))
        for term in entry.get("board", []):
            parts = term.split(":")
            if parts[0] == "count":
                # Counted mana's colours only while it counts one or more
                # (Cabal Coffers with no Swamp makes no black).
                if self.counted(parts, permanents, cmd) >= 1:
                    colours |= self.expand(parts[2] if parts[1] == "devotion" else parts[3], cmd)
            elif parts[0] == "gate" and self.condition(parts[1:-1], permanents):
                # A gated ability's colours only while its condition holds on
                # the board at the payment (Spire of Industry: an artifact).
                for atom in parts[-1].split(","):
                    colours |= self.expand(atom, cmd)
            elif parts[0] in ("legendColors", "vivid"):
                colours |= set("WUBRG")
            elif parts[0] == "landColors" and depth == 0:
                for p in permanents:
                    other = self.table.get(p["name"], {})
                    if (p is not record and p.get("kind") == "land"
                            and "landColors" not in other.get("board", [])):
                        colours |= self.allowed_colours(p, permanents, cmd, 1)
                        # The text's add abilities, costs ignored, except a
                        # Pathway's other face and counted mana, read on the
                        # board above.
                        if not (other.get("faces") or any(t.startswith("count") for t in other.get("board", []))):
                            colours |= self.oracle_outputs(p["name"], cmd)
        if record.get("kind") == "land":
            for p in permanents:
                grant = self.table.get(p["name"], {}).get("landGrant")
                if grant:
                    colours |= self.expand(grant, cmd)
        if self.urza_eligible(record, permanents):
            colours.add("U")
        for _, _, colour, _ in self.extras(permanents):
            colours |= self.expand(colour, cmd)
        return colours

    def table_taps(self, atom):
        """Whether the table says spending this mana taps its source: lands
        and Urza's grant to an artifact do; a non-land by its `taps`."""
        record = atom.source
        entry = self.table.get(record["name"])
        if record["name"].endswith("(earthbent land)") or record.get("kind") == "land" or entry is None:
            return True
        if not (entry.get("mana") or entry.get("once") or entry.get("board")):
            return True  # Urza's grant
        return bool(entry.get("taps"))

    # ---- the replay
    def run_deck(self, deck_id: str, games: int | None = None) -> tuple:
        """(violations by rule, mana spent) over the deck's seeded games."""
        deck = json.loads((self.ROOT / "data" / "commanders" / deck_id / "deck.json").read_text())
        index = {e["id"]: e for e in json.loads((self.ROOT / "data" / "index.json").read_text())["commanders"]}
        decklist = getattr(exporter, self.DECKS[deck_id]).build_decklist(deck)
        context = exporter.build_goldfish_context(decklist, deck, self.meta, deck["commander"],
                                                  list(index[deck_id]["colors"]) or ["C"], deck_id)
        cmd = [c for c in context["commanderColors"] if c in "WUBRG"]
        violations = defaultdict(list)
        st = {"spent": 0}

        def vigilant(record):
            """Vigilance as a keyword of the creature's own text, read from
            the card data (not the exporter's profile)."""
            text = re.sub(r"\([^)]*\)", "", self.meta.get(record["name"], {}).get("oracle_text", "") or "")
            keywords = {word.strip().lower() for line in text.split("\n") for word in line.split(",")}
            return "vigilance" in keywords and "Creature" in self.type_line(record["name"])

        after, add, floated = exporter.GoldfishManaPool._after, exporter.GoldfishManaPool.add, exporter.floated
        spend, combat, rearm = exporter.spend_mana, exporter.combat_phase_damage, exporter.rearm_once_sources
        metrics, put = exporter.metrics_from_board, exporter.put_land_onto_battlefield
        imprint = exporter.imprint_from_hand
        # What the game chose, read as it happens: the face each Pathway
        # entered as (the table's face whose colours its mana has; None when
        # none matches) and the card each imprint exiled (allowed_colours).
        self.observed = {"face": {}, "imprint": {}}

        def recording_imprint(record, *args, **kwargs):
            card = imprint(record, *args, **kwargs)
            self.observed["imprint"][id(record)] = card
            return card

        def recording_after(pool, used, pinned):
            out = after(pool, used, pinned)
            out.used_atoms = [pool.sources[i] for i in used]
            return out

        def counting_add(pool, atoms):
            atoms = list(atoms)
            if pool.turn is not None:
                st["free_in"][pool.turn] += len(atoms)
            return add(pool, atoms)

        def counting_floated(atom):
            st["floated"] += 1
            return floated(atom)

        def recording_put(land_name, turn, tapped, permanents, *args, **kwargs):
            record = put(land_name, turn, tapped, permanents, *args, **kwargs)
            st["entered"][id(record)] = (turn, bool(tapped))
            st["alive"].append(record)
            faces = self.table.get(land_name, {}).get("faces")
            if faces:
                made = set().union(*record["manaAtoms"]) if record["manaAtoms"] else set()
                self.observed["face"][id(record)] = next(
                    (i for i, face in enumerate(faces) if set().union(*(self.expand(a, cmd) for a in face)) == made),
                    None)
            return record

        def checked_spend(pool, cost, permanents, battlefield_lands, profiles_, keep=(), strict=True,
                          taps=None, paid=None):
            turn = pool.turn
            st["free_in"][turn] += st["floated"]
            st["floated"] = 0
            tapped_before = {id(p): bool(p.get("tapped")) for p in permanents}
            used_before, board = set(pool.tapped), list(permanents)
            left = spend(pool, cost, permanents, battlefield_lands, profiles_, keep, strict, taps, paid)
            if left is None:
                return left
            used = getattr(left, "used_atoms", [])
            st["spent"] += len(used)
            if len(used) != cost.get("generic", 0) + sum(cost.get(c, 0) for c in "WUBRGC"):
                violations["G mana used differs from the cost"].append((turn, len(used), dict(cost)))
            for atom in used:
                record = atom.source
                if record is None:
                    st["free_out"][turn] += 1
                    continue
                st["alive"].append(record)  # its id stays unique for the game
                key, name = (turn, id(record)), record["name"]
                st["names"][key] = name
                here = board if any(p is record for p in board) else board + [record]
                lasting, once = self.caps(record, here, cmd)
                st["cap"][key] = (max(st["cap"].get(key, (0, 0))[0], lasting),
                                  max(st["cap"].get(key, (0, 0))[1], once))
                st["once" if atom.once else "lasting"][key] += 1
                if atom.once:
                    st["arming"][id(record)] += 1
                    if st["arming"][id(record)] > once:
                        violations["I one-shot mana over one arming"].append((turn, name, st["arming"][id(record)]))
                if not set(atom) <= self.allowed_colours(record, here, cmd):
                    violations["B a colour the card cannot make"].append((turn, name, "".join(sorted(atom))))
                if atom.taps and tapped_before.get(id(record)) and id(record) not in used_before:
                    violations["C a tapped source paid with mana that taps it"].append((turn, name))
                entry = self.table.get(name, {})
                entered = st["entered"].get(id(record))
                if record.get("kind") != "land" and record.get("enteredTurn") == turn and entry.get("from") == "next":
                    violations["D paid the turn it entered (from the next turn)"].append((turn, name))
                if entered and entered[0] == turn and (entered[1] or entry.get("entry") == "tapped"):
                    violations["D a land that entered tapped paid that turn"].append((turn, name))
                if entered and entered[0] == turn and "Creature" in self.land_type_line(name):
                    violations["D a land creature paid the turn it entered"].append((turn, name))
                if name in self.table and bool(atom.taps) != self.table_taps(atom):
                    violations["K taps flag differs from the table"].append((turn, name))
                if atom.taps and id(record) in st["attacked"].get(turn, set()) and not vigilant(record):
                    violations["J attacked, then paid with its {T} mana"].append((turn, name))
                if atom.taps and id(record) in st["ability"].get(turn, set()):
                    violations["E {T} ability used, then {T} mana"].append((turn, name))
                if atom.taps:
                    st["tapped_for_mana"].setdefault(turn, set()).add(id(record))
            if taps is not None:
                st["alive"].append(taps)
                if id(taps) in st["tapped_for_mana"].get(turn, set()):
                    violations["E {T} mana spent, then {T} ability"].append((turn, taps["name"]))
                st["ability"].setdefault(turn, set()).add(id(taps))
            for kind, index_ in (("lasting", 0), ("once", 1)):
                for key, n in st[kind].items():
                    if key[0] == turn and n > st["cap"][key][index_]:
                        violations[f"A {kind} mana over the card's cap"].append(
                            (turn, st["names"][key], n, st["cap"][key][index_]))
                        st[kind][key] = -999
            if st["free_out"][turn] > st["free_in"][turn]:
                violations["F mana with no source spent beyond what was added"].append(
                    (turn, st["free_out"][turn], st["free_in"][turn]))
                st["free_out"][turn] = -999
            return left

        def checked_combat(attackers, modifiers, board, phase_index):
            turn = st["turn"]
            st["alive"].extend(attackers)
            for record in attackers:
                st["attacked"].setdefault(turn, set()).add(id(record))
                if (phase_index == 0 and not vigilant(record)
                        and id(record) in st["tapped_for_mana"].get(turn, set())):
                    violations["J paid with its {T} mana, then attacked"].append((turn, record["name"]))
            return combat(attackers, modifiers, board, phase_index)

        def counting_rearm(permanents, pool, battlefield_lands, profiles_):
            spent = {id(p) for p in permanents if p.get("onceSpent")}
            out = rearm(permanents, pool, battlefield_lands, profiles_)
            for p in permanents:
                if id(p) in spent and not p.get("onceSpent"):
                    st["arming"][id(p)] = 0  # a new arming
            return out

        def turn_end(**kwargs):
            st["turn"] = kwargs["turn"] + 1
            return metrics(**kwargs)

        random.seed(exporter.GOLDFISH_SEED)
        with patch.object(exporter.GoldfishManaPool, "_after", recording_after), \
                patch.object(exporter.GoldfishManaPool, "add", counting_add), \
                patch.multiple(exporter, floated=counting_floated, spend_mana=checked_spend,
                               combat_phase_damage=checked_combat, rearm_once_sources=counting_rearm,
                               metrics_from_board=turn_end, put_land_onto_battlefield=recording_put,
                               imprint_from_hand=recording_imprint):
            for _ in range(games or self.GAMES_BY_DECK.get(deck_id, self.GAMES)):
                st.update(turn=1, floated=0, free_in=Counter(), free_out=Counter(), lasting=Counter(),
                          once=Counter(), cap={}, names={}, attacked={}, tapped_for_mana={}, ability={},
                          arming=Counter(), entered={}, alive=[])
                exporter.simulate_goldfish_game(decklist, context, 6)
        return violations, st["spent"]

    def test_no_seeded_game_spends_mana_the_table_does_not_give(self):
        for deck_id in self.DECKS:
            with self.subTest(deck=deck_id):
                violations, spent = self.run_deck(deck_id)
                self.assertGreater(spent, 200)
                self.assertEqual({kind: found[:3] for kind, found in violations.items()}, {})

    def test_reflecting_pool_reads_counted_mana_on_the_payment_board(self):
        # The seeded games never reach this board (hoard-and-bleed: 0 of
        # 1,000 games with the break), so the check is read on it directly.
        # Cabal Coffers makes black only with a Swamp out: Reflecting Pool
        # beside Coffers and a Mountain cannot make black; beside Coffers and
        # a Swamp it can.
        self.observed = {"face": {}, "imprint": {}}
        pool, coffers = {"name": "Reflecting Pool", "kind": "land"}, {"name": "Cabal Coffers", "kind": "land"}
        made = {other: self.allowed_colours(pool, [pool, coffers, {"name": other, "kind": "land"}], ["B", "R"])
                for other in ("Mountain", "Swamp")}
        self.assertEqual(made, {"Mountain": {"R"}, "Swamp": {"B"}})


class ManaOnOfferInvariantTests(unittest.TestCase):
    """I1 (review round 3): the mana on offer always equals what the board
    gives. Seeded games of seven fleet decks (data/commanders, the exporter's
    own seed); after every resolution (a cast or a put, an imprint, a
    cascade, a land search) and before every read of the pool (each payment
    and payment search, the combo and assembly gates, the end of the turn's
    untaps and land fetches) its unspent mana must be the mana already
    floating (no source, or a source this turn has used) plus board_mana for
    the battlefield as it stands."""

    DECKS = {"titan-convergence": "sim_titan", "the-white-forge": "sim_mono_white", "slivers": "sim_slivers",
             "armory-protocol": "sim_armory_protocol", "verdant-tide": "sim_mono_green",
             # Chrome Mox; the hatch engine with High Market.
             "gathering-shadow": "sim_grixis", "broodfire-hatchery": "sim_broodfire_hatchery"}
    GAMES = 12

    @staticmethod
    def canon(atoms) -> Counter:
        return Counter((frozenset(a), exporter.atom_source_id(a), a.once, a.group is not None, a.order,
                        a.reserve, a.taps) for a in atoms)

    def run_deck(self, deck_id: str) -> int:
        root = Path(__file__).resolve().parent.parent
        deck = json.loads((root / "data" / "commanders" / deck_id / "deck.json").read_text())
        metadata = json.loads((root / "data" / "card-metadata.json").read_text())
        index = {e["id"]: e for e in json.loads((root / "data" / "index.json").read_text())["commanders"]}
        decklist = getattr(exporter, self.DECKS[deck_id]).build_decklist(deck)
        context = exporter.build_goldfish_context(decklist, deck, metadata, deck["commander"],
                                                  list(index[deck_id]["colors"]) or ["C"], deck_id)
        profiles = context["profiles"]
        board = {"permanents": None}
        checks = []
        put_land = exporter.put_land_onto_battlefield

        def record_board(land_name, turn, tapped, permanents, *args, **kwargs):
            board["permanents"] = permanents
            return put_land(land_name, turn, tapped, permanents, *args, **kwargs)

        def check(pool, where):
            permanents = board["permanents"]
            if permanents is None or pool.turn is None:
                return
            unspent = [a for a in pool.sources
                       if exporter.atom_source_id(a) is not None and exporter.atom_source_id(a) not in pool.tapped]
            fresh = [a for a in exporter.board_mana(permanents, pool.turn, profiles, pool.tapped)
                     if not (pool.lasting_only and a.once)]
            checks.append(where)
            self.assertEqual(self.canon(unspent), self.canon(fresh), f"{deck_id} T{pool.turn} {where}")

        def checked(name, pool_at, after):
            """Call-through: the pool (argument ``pool_at``: a position, or
            the keyword "pool") checked before the call or after it."""
            original = getattr(exporter, name)

            def call(*args, **kwargs):
                pool = kwargs["pool"] if pool_at == "pool" else args[pool_at]
                if not after:
                    check(pool, name)
                result = original(*args, **kwargs)
                if after:
                    check(pool, name)
                return result
            return name, call

        refresh = exporter.refresh_pool

        def floating_kept(pool, permanents, profiles_, turn):
            """refresh_pool keeps every mana already floating (no source, or a
            source this turn has used)."""
            def floating(p):
                return Counter((frozenset(a), exporter.atom_source_id(a)) for a in p.sources
                               if exporter.atom_source_id(a) is None or exporter.atom_source_id(a) in p.tapped)
            before = floating(pool)
            out = refresh(pool, permanents, profiles_, turn)
            self.assertEqual(floating(out), before, f"{deck_id} T{turn} refresh_pool")
            checks.append("refresh_pool")
            return out

        hooks = [checked("find_payment", 0, False), checked("spend_mana", 0, False),
                 checked("combo_ready_this_turn", "pool", False),
                 checked("combo_assembled_this_turn", "pool", False),
                 checked("rearm_once_sources", 1, False), checked("activate_land_fetches", 1, False),
                 checked("resolve_cast_effects", 3, True), checked("imprint_on_entry", 3, True),
                 checked("resolve_cascade_triggers", 3, True), checked("fetch_lands", 3, True),
                 ("refresh_pool", floating_kept)]
        random.seed(exporter.GOLDFISH_SEED)
        with patch.object(exporter, "put_land_onto_battlefield", record_board), \
                patch.multiple(exporter, **dict(hooks)):
            for _ in range(self.GAMES):
                board["permanents"] = None
                exporter.simulate_goldfish_game(decklist, context, 6)
        self.assertLessEqual({"find_payment", "spend_mana", "resolve_cast_effects", "rearm_once_sources",
                              "activate_land_fetches", "refresh_pool"}, set(checks), deck_id)
        return len(checks)

    def test_the_pool_is_what_the_board_gives_at_every_payment(self):
        for deck_id in self.DECKS:
            with self.subTest(deck=deck_id):
                self.assertGreater(self.run_deck(deck_id), 100)


PAY_ONE = {"W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "C": 0, "generic": 1, "X": 0, "total": 1}


class PayTruth:
    """A brute force over every legal payment, independent of the exporter's
    allocator (I2). A plain mana makes one of its colours; a one-colour
    activation (``group``) that pays is made as one colour c: it makes as
    many mana as its atoms that contain c, all c, and its unspent mana stays
    that colour; an activation left unused keeps its atoms. A requirement (a
    list of costs) is kept when the pool left pays any one of them."""

    COLOURS = "WUBRGC"

    @classmethod
    def cost(cls, **pips) -> dict:
        out = {c: 0 for c in cls.COLOURS}
        out.update(generic=0, X=0)
        out.update(pips)
        out["total"] = sum(out[c] for c in cls.COLOURS) + out["generic"]
        return out

    @classmethod
    def payable_plain(cls, mana: list, cost: dict) -> bool:
        pips = [c for c in cls.COLOURS for _ in range(cost[c])]
        if len(mana) < len(pips) + cost["generic"]:
            return False
        match: dict = {}

        def augment(p, seen):
            for j, colours in enumerate(mana):
                if pips[p] in colours and j not in seen:
                    seen.add(j)
                    if j not in match or augment(match[j], seen):
                        match[j] = p
                        return True
            return False

        return all(augment(p, set()) for p in range(len(pips)))

    @classmethod
    def pays(cls, left: list, cost: dict) -> bool:
        """``left``: (colours, group or None) pairs."""
        plain = [colours for colours, group in left if group is None]
        groups: dict = {}
        for colours, group in left:
            if group is not None:
                groups.setdefault(group, []).append(colours)
        ids = list(groups)
        for choice in itertools.product(*[[None] + sorted(set().union(*groups[g])) for g in ids]):
            mana = list(plain)
            for group, colour in zip(ids, choice):
                if colour is not None:
                    mana += [frozenset({colour})] * sum(1 for s in groups[group] if colour in s)
            if cls.payable_plain(mana, cost):
                return True
        return False

    @classmethod
    def lefts(cls, atoms: list, cost: dict):
        """Every pool a payment of ``cost`` leaves, as sorted keys of
        (colours, unused one-colour activation) and as (colours, group)
        lists."""
        need = sum(cost[c] for c in cls.COLOURS) + cost["generic"]
        groups: dict = {}
        for i, atom in enumerate(atoms):
            if getattr(atom, "group", None) is not None:
                groups.setdefault(atom.group, []).append(i)
        plain = [i for i, atom in enumerate(atoms) if getattr(atom, "group", None) is None]
        ids = list(groups)
        seen = {}
        for choice in itertools.product(*[[None] + sorted(set().union(*(atoms[i] for i in groups[g])))
                                          for g in ids]):
            mana = [(frozenset(atoms[i]), None) for i in plain]
            open_atoms = []
            for group, colour in zip(ids, choice):
                if colour is None:
                    open_atoms += [(frozenset(atoms[i]), group) for i in groups[group]]
                else:
                    mana += [(frozenset({colour}), None)] * sum(1 for i in groups[group] if colour in atoms[i])
            for used in itertools.combinations(range(len(mana)), need):
                if not cls.payable_plain([mana[j][0] for j in used], cost):
                    continue
                left = [mana[j] for j in range(len(mana)) if j not in used] + open_atoms
                seen.setdefault(cls.key(left), left)
        return seen

    @staticmethod
    def key(left: list) -> tuple:
        return tuple(sorted((tuple(sorted(colours)), group is not None and len(colours) > 1)
                            for colours, group in left))

    @classmethod
    def pool_left(cls, pool) -> list:
        return [(frozenset(atom), getattr(atom, "group", None)) for atom in pool.sources]

    SETS = ["W", "U", "B", "R", "G", "C", "WU", "UB", "BG", "GW", "RG", "WUBRG", "BGR", "CRG", "CW"]

    @classmethod
    def pool(cls, rng) -> list:
        atoms = []
        tapped = set()
        for s in range(rng.randint(1, 5)):
            record = {"name": f"S{s}"}
            kind = rng.choice(["land", "land", "land", "rock", "once", "creature", "creature", "group",
                               "devotion", "reserve"])
            colours = frozenset(rng.choice(cls.SETS))
            if kind == "devotion":
                devotion = {c: rng.randint(0, 3) for c in rng.sample("WUBRG", 2)}
                sets = [frozenset(c for c, n in devotion.items() if n >= k)
                        for k in range(1, max(devotion.values()) + 1)]
                atoms += exporter.tag_atoms(sets, record, 0, group=id(record), taps=True)
            elif kind == "group":
                colours = frozenset(rng.choice(["WU", "WUBRG", "BG"]))
                atoms += exporter.tag_atoms([colours] * rng.randint(2, 3), record, 0, group=id(record),
                                            taps=True)
            elif kind == "once":
                atoms += exporter.tag_atoms([colours] * rng.randint(1, 3), record, 1, once=True, taps=True)
            elif kind == "creature":
                atoms += exporter.tag_atoms([colours] * rng.randint(1, 2), record, rng.randint(2, 6),
                                            taps=True)
            else:
                atoms += exporter.tag_atoms([colours] * (rng.randint(1, 2) if kind == "rock" else 1), record,
                                            0, reserve=kind == "reserve", taps=True)
            if rng.random() < 0.1:
                tapped.add(id(record))
        rng.shuffle(atoms)
        return atoms, tapped

    @classmethod
    def random_cost(cls, rng, most: int, least: int = 0) -> dict:
        pips = {}
        for _ in range(rng.randint(least, max(least, min(most, 5)))):
            colour = "generic" if rng.random() < 0.4 else rng.choice(cls.COLOURS)
            pips[colour] = pips.get(colour, 0) + 1
        return cls.cost(**pips)


def check_pay(exporter_module, seed: int, trials: int, verbose: bool = False) -> list:
    """Run ``trials`` random pools; return the cases where pay() disagrees with
    the brute force (I2): it refuses a payable case, accepts an unpayable one,
    or returns a pool no real payment leaves or that does not keep the
    requirements."""
    rng = random.Random(seed)
    bad = []
    for _ in range(trials):
        atoms, tapped = PayTruth.pool(rng)
        if len(atoms) > 8:
            continue
        cost = PayTruth.random_cost(rng, len(atoms))
        keep = [[PayTruth.random_cost(rng, len(atoms), 1) for _ in range(rng.choice([1, 1, 2]))]
                for _ in range(rng.choice([0, 1, 1, 2]))]
        lefts = PayTruth.lefts(atoms, cost)
        keeping = {key: left for key, left in lefts.items()
                   if all(any(PayTruth.pays(left, c) for c in costs) for costs in keep)}
        got = exporter_module.GoldfishManaPool(atoms, tapped).pay(cost, keep)
        if (got is None) != (not keeping):
            bad.append(("refused" if keeping else "accepted", atoms, cost, keep))
        elif got is not None and PayTruth.key(PayTruth.pool_left(got)) not in keeping:
            bad.append(("not a keeping payment", atoms, cost, keep))
        if verbose and bad and len(bad) <= 5 and bad[-1][1] is atoms:
            print(bad[-1][0], [("".join(sorted(a)), a.source["name"], a.order, a.group is not None)
                               for a in atoms], cost, keep)
    return bad


class ManaPaymentPropertyTests(unittest.TestCase):
    """I2 (review round 3): GoldfishManaPool.pay is exact, holds included,
    against PayTruth's brute force over random pools (lands, rocks, one-shot
    mana, creatures, mana of sources already used, one-colour activations
    uniform and Nykthos-shaped) with costs of pips and generic and zero to
    two requirements: a payment whenever the cost and the requirements can
    be paid together, never otherwise, and the pool returned is one a real
    payment leaves that keeps them."""

    def test_pay_agrees_with_the_brute_force(self):
        # 10,000 random pools (25 seeds of 400): about a second.
        bad = [case for seed in range(20261120, 20261145) for case in check_pay(exporter, seed, 400)]
        self.assertEqual([(kind, cost, keep) for kind, _atoms, cost, keep in bad], [])

    def test_the_cases_review_round_3_found(self):
        pay = PayTruth.cost
        # (a) Lotus Field ({W} or {U}, three of one colour) and a Bird (any
        # colour, could attack): {W}{U}{1} keeping {W} is paid with the Field
        # made white ({W}, {1}, one {W} left) and the Bird's {U}.
        field, bird = {"name": "Lotus Field"}, {"name": "Bird"}
        atoms = (exporter.tag_atoms([frozenset("WU")] * 3, field, 0, group=id(field), taps=True)
                 + exporter.tag_atoms([frozenset("WUBRG")], bird, 3, taps=True))
        got = exporter.GoldfishManaPool(atoms).pay(pay(W=1, U=1, generic=1), [[pay(W=1)]])
        self.assertEqual(sorted(mana_letters(got.sources)), ["W"])
        # (b) Lotus Field (any colour) and a Mountain: {1} cannot keep both
        # {G} and {B}{R} (the Field makes one colour).
        field, mountain = {"name": "Lotus Field"}, {"name": "Mountain"}
        atoms = (exporter.tag_atoms([frozenset("WUBRG")] * 3, field, 0, group=id(field), taps=True)
                 + exporter.tag_atoms([frozenset("R")], mountain, 0, taps=True))
        self.assertIsNone(exporter.GoldfishManaPool(atoms).pay(pay(generic=1), [[pay(G=1)], [pay(B=1, R=1)]]))
        # (c) Nykthos with devotion green 3, white 1 ({W/G}, {G}, {G}) and a
        # Forest: paying {1}{G} leaves no mana of a colour Nykthos did not make.
        nykthos, forest = {"name": "Nykthos"}, {"name": "Forest"}
        atoms = (exporter.tag_atoms([frozenset("WG"), frozenset("G"), frozenset("G")], nykthos, 0,
                                    group=id(nykthos), taps=True)
                 + exporter.tag_atoms([frozenset("G")], forest, 0, taps=True))
        got = exporter.GoldfishManaPool(atoms).pay(pay(G=1, generic=1), [[pay(G=2)]])
        self.assertFalse(got.can_cast(pay(W=1, G=1)))
        # The same Nykthos alone pays {W} made white: its green mana is not
        # made (nothing left).
        got = exporter.GoldfishManaPool(atoms[:3]).pay(pay(W=1))
        self.assertEqual(got.total, 0)
        # Thirteen single-mana sources, {6} keeping {B} (no cap on the search).
        sets = ["B", "G", "U", "R", "W", "C", "GU", "GR", "GW", "RU", "UW", "RW", "CG"]
        atoms = [exporter.tag_atoms([frozenset(s)], {"name": f"L{i}"}, 0, taps=True)[0]
                 for i, s in enumerate(sets)]
        got = exporter.GoldfishManaPool(atoms).pay(pay(generic=6), [[pay(B=1)]])
        self.assertTrue(got is not None and got.can_cast(pay(B=1)))
        # Leaf Gilder ({G}, combat 2) listed first, Priest of Titania ({G}{G},
        # combat 2) and Lotus Petal: {G}{G} takes the Priest alone, not the
        # Gilder and the Petal (equal combat: the fewest one-shot sources).
        gilder, priest, petal = {"name": "Leaf Gilder"}, {"name": "Priest"}, {"name": "Lotus Petal"}
        atoms = (exporter.tag_atoms([frozenset("G")], gilder, 4, taps=True)
                 + exporter.tag_atoms([frozenset("G")] * 2, priest, 4, taps=True)
                 + exporter.tag_atoms([frozenset("WUBRG")], petal, 1, once=True, taps=True))
        got = exporter.GoldfishManaPool(atoms).pay(pay(G=2))
        self.assertEqual(sorted(a.source["name"] for a in got.sources), ["Leaf Gilder", "Lotus Petal"])

    def test_a_keeping_payment_is_the_most_preferred_keeper(self):
        pay = PayTruth.cost
        # {2} keeping {G}: the preferred payment (the Forest and Swamp A, the
        # first of the lands) breaks the hold; of the payments that keep it,
        # two lands come before a land and the one-shot Petal ({W}).
        forest, swamp_a, swamp_b = {"name": "Forest"}, {"name": "Swamp A"}, {"name": "Swamp B"}
        plains, petal = {"name": "Plains"}, {"name": "Lotus Petal"}
        atoms = (exporter.tag_atoms([frozenset("G")], forest, 0, taps=True)
                 + exporter.tag_atoms([frozenset("B")], swamp_a, 0, taps=True)
                 + exporter.tag_atoms([frozenset("W")], petal, 1, once=True, taps=True)
                 + exporter.tag_atoms([frozenset("W")], plains, 0, taps=True)
                 + exporter.tag_atoms([frozenset("B")], swamp_b, 0, taps=True))
        pool = exporter.GoldfishManaPool(atoms)
        self.assertEqual(sorted(a.source["name"] for a in pool.pay(pay(generic=2)).sources),
                         ["Lotus Petal", "Plains", "Swamp B"])
        got = pool.pay(pay(generic=2), [[pay(G=1)]])
        self.assertEqual(sorted(a.source["name"] for a in got.sources), ["Forest", "Lotus Petal", "Plains"])
        # Every requirement is kept, not only the first: keeping {G} and {B},
        # the Forest and a Swamp stay.
        got = pool.pay(pay(generic=2), [[pay(G=1)], [pay(B=1)]])
        self.assertTrue(got.can_cast(pay(G=1)) and got.can_cast(pay(B=1)))
        self.assertEqual(sorted(a.source["name"] for a in got.sources), ["Forest", "Lotus Petal", "Swamp B"])
        # {2} keeping {W}: the preferred payment (Savannah and Elf Y) breaks
        # it. Of the keepers the fewest creatures that could attack come
        # first: Big Elf's {G}{G} (combat 5), not Elves Y and Z (combat 1
        # each), although those come first in the search.
        savannah, big, elf_y, elf_z = ({"name": n} for n in ("Savannah", "Big Elf", "Elf Y", "Elf Z"))
        atoms = (exporter.tag_atoms([frozenset("GW")], savannah, 0, taps=True)
                 + exporter.tag_atoms([frozenset("G")], elf_y, 3, taps=True)
                 + exporter.tag_atoms([frozenset("G")], elf_z, 3, taps=True)
                 + exporter.tag_atoms([frozenset("G")] * 2, big, 7, taps=True))
        pool = exporter.GoldfishManaPool(atoms)
        self.assertEqual(sorted(a.source["name"] for a in pool.pay(pay(generic=2)).sources),
                         ["Big Elf", "Big Elf", "Elf Z"])
        got = pool.pay(pay(generic=2), [[pay(W=1)]])
        self.assertEqual(sorted(a.source["name"] for a in got.sources), ["Elf Y", "Elf Z", "Savannah"])


class ManaRoundTwoPaymentTests(unittest.TestCase):
    """Review round 2 (2026-11-20): one payment path. The spend preference
    (GoldfishManaPool's docstring), payments checked jointly with what the
    turn holds, and each payment settled before the next."""

    ONE = {"W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "C": 0, "generic": 1, "X": 0, "total": 1}

    @staticmethod
    def mana(colours, record, order=0, **kwargs):
        return exporter.tag_atoms([frozenset(colours)], record, order, **kwargs)[0]

    def test_floating_mana_pays_before_a_fresh_land(self):
        # Sol Ring was used for one {C}: its other {C} is floating and pays
        # {1} before Castle Ardenvale's {W} (listed first).
        sol, castle = {"name": "Sol Ring"}, {"name": "Castle Ardenvale"}
        pool = exporter.GoldfishManaPool([self.mana("W", castle), self.mana("C", sol)], tapped={id(sol)})
        self.assertEqual([a.source["name"] for a in pool.pay(self.ONE).sources], ["Castle Ardenvale"])

    def test_a_land_whose_tap_ability_the_turn_uses_pays_last_among_lands(self):
        # Castle Ardenvale (listed first) and a Plains: {1} takes the Plains.
        castle, plains = {"name": "Castle Ardenvale"}, {"name": "Plains"}
        pool = exporter.GoldfishManaPool([self.mana("W", castle, reserve=True), self.mana("W", plains)])
        self.assertEqual([a.source["name"] for a in pool.pay(self.ONE).sources], ["Castle Ardenvale"])
        # It still pays before one-shot mana and creatures that could attack.
        petal, elf = {"name": "Lotus Petal"}, {"name": "Elf"}
        pool = exporter.GoldfishManaPool([self.mana("W", petal, 1, once=True), self.mana("W", elf, 3),
                                          self.mana("W", castle, reserve=True)])
        self.assertEqual(sorted(a.source["name"] for a in pool.pay(self.ONE).sources), ["Elf", "Lotus Petal"])

    def test_a_creature_that_could_attack_costs_its_attack_until_combat_is_over(self):
        # {G} from a G/W land or a vigilant Elf ({G}, could attack): before
        # combat the land pays; after combat the Elf, the narrower mana.
        elf, dual = {"name": "Vigilant Elf"}, {"name": "Dual"}
        atoms = [self.mana("GW", dual), self.mana("G", elf, 3)]
        g = dict(self.ONE, generic=0, G=1)
        self.assertEqual([a.source["name"] for a in exporter.GoldfishManaPool(atoms).pay(g).sources],
                         ["Vigilant Elf"])
        after = exporter.GoldfishManaPool(atoms).after_combat()
        self.assertEqual([a.source["name"] for a in after.pay(g).sources], ["Dual"])

    def test_a_payment_that_keeps_the_hold_is_taken_when_the_preferred_one_breaks_it(self):
        # {W}{2} with {G} held (Worldly Tutor): Command Tower pays the {W};
        # the preferred generic (Forest, then a Mountain, the narrowest, listed
        # first) leaves only a Mountain. The two Mountains keep the Forest's
        # {G}: that payment is taken. With nothing held the preferred one is.
        tower, forest = {"name": "Command Tower"}, {"name": "Forest"}
        mountains = [{"name": "Mountain A"}, {"name": "Mountain B"}]
        atoms = ([self.mana("RGW", tower), self.mana("G", forest)]
                 + [self.mana("R", m) for m in mountains])
        cost = dict(self.ONE, generic=2, W=1, total=3)
        held = dict(self.ONE, generic=0, G=1)
        pool = exporter.GoldfishManaPool(atoms)
        self.assertEqual([a.source["name"] for a in pool.pay(cost).sources], ["Mountain B"])
        kept = pool.pay(cost, keep=[[held]])
        self.assertEqual([a.source["name"] for a in kept.sources], ["Forest"])
        # A requirement no payment keeps refuses the spend; a cast that is
        # never held back (strict False) then takes the preferred payment.
        both = dict(self.ONE, generic=0, G=2)
        self.assertIsNone(pool.pay(cost, keep=[[both]]))
        self.assertIsNone(exporter.find_payment(pool, cost, [[both]]))
        self.assertEqual([a.source["name"] for a in
                          exporter.find_payment(pool, cost, [[both]], strict=False).sources], ["Mountain B"])
        # A gate kept by any one of its lines: {G} or {B}.
        self.assertEqual([a.source["name"] for a in
                          pool.pay(cost, keep=[[dict(self.ONE, generic=0, B=1), held]]).sources], ["Forest"])

    def test_each_payment_taps_only_the_permanents_whose_own_tap_paid(self):
        context = exporter.build_goldfish_context(
            ["Urza, Lord High Artificer", "Llanowar Elves", "Wastes"], {"decklist": []}, CARDS,
            "Probe Commander", ["U", "G"], "synthetic-pay")
        profiles = context["profiles"]
        urza = {"name": "Urza, Lord High Artificer", "manaAtoms": [], "kind": "ramp"}
        elves = {"name": "Llanowar Elves", "manaAtoms": [frozenset("G")], "kind": "ramp"}
        wastes = {"name": "Wastes", "manaAtoms": [frozenset("C")], "kind": "land"}
        permanents = [urza, elves, wastes]
        # Urza's {U} (his Construct's) does not tap him; the Elves' and the
        # Wastes' {T} abilities tap them.
        pool = exporter.GoldfishManaPool([self.mana("U", urza), self.mana("G", elves, taps=True),
                                          self.mana("C", wastes, taps=True)])
        three = dict(self.ONE, generic=3, total=3)
        left = exporter.spend_mana(pool, three, permanents, [], profiles)
        self.assertEqual(left.total, 0)
        self.assertEqual([p.get("tapped", False) for p in permanents], [False, True, True])
        # A permanent tapped for its own ability: it must be untapped, its
        # own mana cannot pay, and it is tapped for it.
        castle = {"name": "Wastes", "manaAtoms": [frozenset("C")], "kind": "land"}
        pool = exporter.GoldfishManaPool([self.mana("C", castle, taps=True), self.mana("U", urza)])
        self.assertIsNone(exporter.spend_mana(pool, dict(self.ONE, generic=2, total=2), [castle, urza],
                                              [], profiles, taps=castle))
        left = exporter.spend_mana(pool, self.ONE, [castle, urza], [], profiles, taps=castle)
        self.assertEqual((left.total, castle["tapped"]), (0, True))
        self.assertIsNone(exporter.spend_mana(exporter.GoldfishManaPool([self.mana("U", urza)]), self.ONE,
                                              [castle, urza], [], profiles, taps=castle))

    def test_end_of_turn_payments_are_settled_one_by_one(self):
        # Wayfarer's Bauble ({2}, {T}, sacrifice) comes first and its {2} is
        # paid with Myriad Landscape's {C} (listed first, not reserved here)
        # and a Forest: the Landscape is tapped and cannot pay its own {T}.
        context = exporter.build_goldfish_context(
            ["Wayfarer's Bauble", "Myriad Landscape", "Forest"], {"decklist": []}, CARDS,
            "Probe Commander", ["G"], "synthetic-fetch")
        profiles = dict(context["profiles"])
        profiles["Myriad Landscape"] = dict(profiles["Myriad Landscape"], manaReserve=False)
        permanents, lands = [], []
        bauble = {"name": "Wayfarer's Bauble", "kind": "ramp", "manaAtoms": [], "manaActiveTurn": 1,
                  "combat": 0, "combatReadyTurn": 99}
        permanents.append(bauble)
        myriad = exporter.put_land_onto_battlefield("Myriad Landscape", 1, False, permanents, lands, profiles,
                                                    ["G"])
        forests = [exporter.put_land_onto_battlefield("Forest", 1, False, permanents, lands, profiles, ["G"])
                   for _ in range(3)]
        pool = exporter.GoldfishManaPool(turn=2)
        library = ["Forest"] * 4
        exporter.activate_land_fetches(2, pool, library, [], permanents, lands, profiles, ["G"])
        names = sorted(p["name"] for p in permanents)
        self.assertEqual(names, ["Forest"] * 4 + ["Myriad Landscape"])
        self.assertTrue(myriad["tapped"])

    def test_nykthos_makes_each_colour_its_own_devotion(self):
        # Devotion: green 6 (three {G}{G} permanents), white 0. Nykthos
        # ({2}, {T}) makes four green, never white.
        profiles = {"Probe GG": {"manaCost": {"W": 0, "U": 0, "B": 0, "R": 0, "G": 2, "C": 0}},
                    "Nykthos": {"manaCost": {"W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "C": 0}}}
        permanents = [{"name": "Probe GG", "kind": "spell"}] * 3
        term = ("count", ("devotion",), frozenset("GW"), 2, None)
        atoms = exporter.board_term_atoms(term, [frozenset("C")], permanents, profiles, 3)
        self.assertEqual(mana_letters(atoms), ["G"] * 4)
        # Four green and two white: the activation is one colour.
        profiles["Probe WW"] = {"manaCost": {"W": 2, "U": 0, "B": 0, "R": 0, "G": 0, "C": 0}}
        permanents = permanents + [{"name": "Probe WW", "kind": "spell"}] * 2
        nykthos = {"name": "Nykthos"}
        atoms = exporter.tag_atoms(exporter.board_term_atoms(term, [frozenset("C")], permanents, profiles, 3),
                                   nykthos, 0, group=id(nykthos))
        pool = exporter.GoldfishManaPool(atoms)
        self.assertEqual(pool.total, 4)
        self.assertTrue(pool.can_cast(dict(self.ONE, generic=0, G=4, total=4)))
        self.assertTrue(pool.can_cast(dict(self.ONE, generic=0, W=2, total=2)))
        self.assertFalse(pool.can_cast(dict(self.ONE, generic=1, W=2, total=3)))
        self.assertEqual(mana_letters(pool.pay(dict(self.ONE, generic=0, W=1, total=1)).sources), ["W"])


class ManaRoundTwoBoardTests(unittest.TestCase):
    """Review round 2 (2026-11-20): board readings, CARDS texts."""

    def test_reflecting_pool_reads_the_face_a_pathway_was_played_as(self):
        # Brightclimb Pathway played as its black face beside an Island:
        # Reflecting Pool makes {U} or {B}, not the Pathway's other face's {W}.
        context = exporter.build_goldfish_context(
            ["Reflecting Pool", "Brightclimb Pathway", "Island"], {"decklist": []}, CARDS,
            "Probe Commander", ["W", "U", "B"], "synthetic-pool")
        profiles = context["profiles"]
        permanents, lands = [], []
        exporter.put_land_onto_battlefield("Island", 1, False, permanents, lands, profiles, ["U", "B"])
        exporter.put_land_onto_battlefield("Brightclimb Pathway", 1, False, permanents, lands, profiles,
                                           ["U", "B"])
        pool_land = exporter.put_land_onto_battlefield("Reflecting Pool", 1, False, permanents, lands,
                                                       profiles, ["U", "B"])
        self.assertEqual(mana_letters(permanents[1]["manaAtoms"]), ["B"])
        self.assertEqual(mana_letters(exporter.record_atoms(pool_land, permanents, profiles, 2)), ["UB"])

    def test_urborg_fetched_during_the_turn_widens_the_lands_not_yet_tapped(self):
        # A Forest's {G} is in the pool; a search puts Urborg onto the
        # battlefield untapped: the Forest (untapped) now makes {B} too, and
        # Urborg's own mana joins with its {B}. A Forest already tapped stays.
        urborg = {"type_line": "Legendary Land", "mana_cost": "", "cmc": 0, "colors": [],
                  "oracle_text": "Each land is a Swamp in addition to its other land types."}
        metadata = {"Urborg, Tomb of Yawgmoth": urborg, "Forest": CARDS["Forest"]}
        context = exporter.build_goldfish_context(["Urborg, Tomb of Yawgmoth", "Forest"], {"decklist": []},
                                                  metadata, "Forest", ["B", "G"], "synthetic-urborg")
        profiles = context["profiles"]
        permanents, lands = [], []
        forests = [exporter.put_land_onto_battlefield("Forest", 1, False, permanents, lands, profiles,
                                                      ["B", "G"]) for _ in range(2)]
        pool = exporter.GoldfishManaPool(exporter.board_mana(permanents, 2, profiles))
        pool = exporter.spend_mana(pool, {"G": 1, "W": 0, "U": 0, "B": 0, "R": 0, "C": 0, "generic": 0,
                                          "X": 0, "total": 1}, permanents, lands, profiles)
        search = {"count": 1, "toHand": 0, "basicOnly": False, "allowedSubtypes": set(), "perType": [],
                  "sharedType": False, "entersTapped": False}
        exporter.fetch_lands(search, 1, 2, pool, ["Urborg, Tomb of Yawgmoth"], [], permanents, lands, profiles,
                             ["B", "G"])
        self.assertEqual(sorted(mana_letters(pool.sources)), ["B", "BG"])
        self.assertEqual(sum(1 for f in forests if f.get("tapped")), 1)

    def test_forsaken_monument_fires_only_for_a_colourless_activation(self):
        # Beside Forsaken Monument, Sol Ring always makes {C}{C} and the extra
        # {C}. Nykthos: with no devotion it taps for {C} (and the extra);
        # with devotion to white 4 for {W}{W} (no extra); with devotion 3 it
        # makes {C} or {W}: one activation, whose extra {C} comes only with
        # the {C} ({C}{C} or {W}, never {W}{C}).
        context = exporter.build_goldfish_context(
            ["Nykthos, Shrine to Nyx", "Forsaken Monument", "Probe WW", "Probe WWW", "Sol Ring"],
            {"decklist": []}, CARDS, "Probe Commander", ["W"], "synthetic-monument")
        profiles = context["profiles"]
        cases = [((), ["C", "C"]), (("Probe WW", "Probe WW"), ["W", "W"]), (("Probe WWW",), ["C", "WC"])]
        for devotion, nykthos in cases:
            with self.subTest(devotion=devotion):
                permanents, lands = [], []
                exporter.put_land_onto_battlefield("Nykthos, Shrine to Nyx", 1, False, permanents, lands,
                                                   profiles, ["W"])
                for name in ("Forsaken Monument", "Sol Ring") + devotion:
                    exporter.resolve_cast_effects(name, profiles[name], 1, exporter.GoldfishManaPool([]),
                                                  [], [], permanents, lands, profiles, ["W"])
                got = exporter.board_mana(permanents, 2, profiles)
                by = {name: sorted(mana_letters(a for a in got if a.source["name"] == name))
                      for name in ("Sol Ring", "Nykthos, Shrine to Nyx")}
                self.assertEqual(by, {"Sol Ring": ["C", "C", "C"], "Nykthos, Shrine to Nyx": nykthos})
                if devotion == ("Probe WWW",):
                    only = exporter.GoldfishManaPool([a for a in got if a.source["name"] != "Sol Ring"])
                    pips = dict(PAY_ONE, generic=0)
                    self.assertEqual([only.can_cast(dict(pips, C=2, total=2)), only.can_cast(dict(pips, W=1, total=1)),
                                      only.can_cast(dict(pips, W=1, C=1, total=2))], [True, True, False])

    def test_a_cascaded_chrome_mox_needs_a_card_to_imprint(self):
        # Cascade off a {4} spell finds Chrome Mox. With an empty hand it is
        # declined and bottomed (no ramp); with Probe Kill in hand it is cast,
        # exiles it, and its {B} joins the turn's pool.
        context = exporter.build_goldfish_context(
            ["Chrome Mox", "Probe Kill", "Swamp"], {"decklist": []}, CARDS, "Probe Commander", ["B"],
            "synthetic-cascade")
        profiles = context["profiles"]
        cascade = {"triggers": 1, "minValue": 0, "fromHandOnly": True}
        spell = dict(profiles["Probe Kill"], cmc=4)
        for hand, cast in (([], False), (["Probe Kill"], True)):
            with self.subTest(hand=hand):
                library, permanents, pool = ["Swamp", "Chrome Mox"], [], exporter.GoldfishManaPool([])
                hand = list(hand)
                exporter.resolve_cascade_triggers(spell, cascade, 3, pool, library, hand, permanents, [],
                                                  profiles, ["B"], set(), context, True)
                self.assertEqual([p["name"] for p in permanents], ["Chrome Mox"] if cast else [])
                self.assertEqual(library, ["Swamp"] if cast else ["Chrome Mox", "Swamp"])
                self.assertEqual((hand, mana_letters(pool.sources)), ([], ["B"]) if cast else ([], []))


class ManaRoundTwoGoldfishTests(unittest.TestCase):
    """Review round 2 (2026-11-20) through the goldfish turn loop: the
    ManaModelGoldfishTests harness unless a case builds its own."""

    _run = ManaModelGoldfishTests._run
    _series = staticmethod(ManaModelGoldfishTests._series)

    def test_urza_still_attacks_after_his_mana_pays(self):
        # Turn 4 four Islands cast Urza; his Construct and Zero Trinket give
        # {U}{U}. Turn 5 Probe Five takes the four Islands and one {U} of
        # his: Urza taps an artifact, not himself, and attacks for 4.
        library = ["Probe Nine"] * 88 + ["Probe Five", "Island", "Island", "Probe Nine"]
        by_turn = self._run(["Urza, Lord High Artificer", "Island", "Island", "Zero Trinket"]
                            + ["Probe Nine"] * 3, library, colors=("U",))
        self.assertEqual(self._series(by_turn, "availableMana"), [1, 2, 3, 6, 6, 6])
        self.assertEqual(self._series(by_turn, "cumulativeDamage"), [0, 0, 0, 0, 4, 13])

    def test_a_vigilant_mana_creature_is_not_tapped_while_lands_pay(self):
        # Turn 2: two Forests and Probe Vigilant Elf; Probe Two takes the two
        # Forests and the Elf attacks (witherbloom game 47: the lands pay
        # before the vigilant creature). Priced as free before combat, the
        # Elf (listed before the second Forest) would pay and not attack.
        by_turn = self._run(["Probe Vigilant Elf", "Forest", "Forest", "Probe Two"] + ["Probe Nine"] * 3,
                            ["Probe Nine"] * 92, colors=("G",))
        self.assertEqual(self._series(by_turn, "cumulativeDamage"), [0, 1, 4, 7, 10, 13])

    def test_a_lotus_petal_leaves_as_its_mana_is_spent(self):
        # Turn 1: Lotus Petal, then Probe Two from the Wastes and the Petal
        # (sacrificed at once), then Probe Metal Rock ({0}; {C}{C} only with
        # two or more artifacts): alone, it makes nothing (turn 1: 2 mana).
        # The Petal still there, the Rock would add {C}{C} that turn.
        by_turn = self._run(["Lotus Petal", "Wastes", "Probe Two", "Probe Metal Rock"] + ["Probe Nine"] * 3,
                            ["Probe Nine"] * 92)
        self.assertEqual(self._series(by_turn, "availableMana"), [2, 1, 1, 1, 1, 1])

    def test_a_land_grant_entering_widens_the_lands_not_yet_tapped(self):
        # Turn 4 draws Chromatic Lantern: three Swamps cast it; the fourth
        # Swamp, untapped, now makes any colour, which with the Lantern's own
        # mana casts Probe GG that turn (2 from turn 5).
        library = ["Probe Nine"] * 89 + ["Chromatic Lantern", "Swamp", "Swamp", "Probe Nine"]
        by_turn = self._run(["Probe GG", "Swamp", "Swamp"] + ["Probe Nine"] * 4, library, colors=("B", "G"))
        self.assertEqual(self._series(by_turn, "cumulativeDamage"), [0, 0, 0, 0, 2, 4])

    def test_forsaken_monument_adds_for_mana_that_comes_online_during_the_turn(self):
        # Five Wastes cast Forsaken Monument on turn 5. Turn 6: each Wastes
        # adds an extra {C} (10); Basalt Monolith enters with {C}{C}{C} and the
        # Monument's {C} for it: 14. The other cards are Probe BB, which a
        # colourless deck never casts.
        library = ["Probe BB"] * 87 + ["Basalt Monolith"] + ["Probe BB"] * 4
        by_turn = self._run(["Forsaken Monument"] + ["Wastes"] * 5 + ["Probe BB"], library)
        self.assertEqual(self._series(by_turn, "availableMana"), [1, 2, 3, 4, 5, 14])
        # Urza's Saga (turns 5-7) and Forsaken Monument (turn 5): on turn 7
        # the Saga is tapped as chapter III resolves; its {C} and the
        # Monument's {C} for it float: four Wastes, four extras, two.
        by_turn = self._run(["Forsaken Monument", "Urza's Saga"] + ["Wastes"] * 4 + ["Probe BB"],
                            ["Probe BB"] * 92)
        self.assertEqual(self._series(by_turn, "availableMana", 7), [1, 2, 3, 4, 5, 10, 10])

    def test_monuments_extra_on_one_shot_mana_is_one_shot(self):
        # Plains turns 1-5; Basalt Monolith turn 3; Forsaken Monument turn 4
        # (four Plains and one of Basalt's {C}); turn 5 untaps Basalt with
        # three of its five Plains. Turn 6: Probe CCC takes Basalt's {C}{C}{C}
        # and Probe WWW three Plains; the Monument's {C} for Basalt is left,
        # one-shot, so the two Plains left cannot untap Basalt: turn 7 has
        # five. Counted as lasting it would untap it: turn 7 would have nine.
        # Probe CCC is drawn on turn 5 (no {C} then), Probe WWW on turn 6; the
        # other cards are Probe BB, which a white deck never casts.
        library = ["Probe BB"] * 87 + ["Probe WWW", "Probe CCC"] + ["Probe BB"] * 4
        by_turn = self._run(["Basalt Monolith", "Forsaken Monument"] + ["Plains"] * 5, library,
                            colors=("W",))
        self.assertEqual(self._series(by_turn, "availableMana", 7), [1, 2, 6, 7, 5, 9, 5])

    def test_myriad_landscape_tapped_for_mana_does_not_fetch(self):
        # Forest turn 1 (and a vigilant Elf), Myriad Landscape turn 2 (tapped;
        # the second Elf), Forest turn 3: Probe Three takes the two Forests
        # and the Landscape's {C} (before the Elves, which attack). The
        # Elves' {G}{G} is left after combat, but the Landscape is tapped: no
        # fetch on turn 3. Turn 4 it fetches the two Forests.
        library = ["Forest", "Forest"] + ["Probe Nine"] * 88 + ["Forest", "Probe Nine", "Probe Nine"]
        by_turn = self._run(["Forest", "Myriad Landscape", "Probe Vigilant Elf", "Probe Vigilant Elf",
                             "Probe Three", "Probe Nine", "Probe Nine"], library, colors=("G",))
        self.assertEqual(self._series(by_turn, "lands", 4), [1, 2, 3, 4])

    def test_a_reachable_assembly_keeps_its_mana_creature_home(self):
        # Probe Combo A in hand fills one slot; Probe Tutor ({1}{G}, a tutor)
        # can fetch Probe Combo B for the other. Turn 2: the Forest and
        # Llanowar Elves pay the tutor, so the Elves stay home and the combo
        # is assembled on turn 2.
        hand = ["Llanowar Elves", "Forest", "Probe Combo A", "Probe Tutor"] + ["Probe Nine"] * 3
        library = ["Probe Combo B", "Forest"] + ["Probe Nine"] * 90
        cards = dict(CARDS, **{"Probe Tutor": {"type_line": "Instant", "mana_cost": "{1}{G}", "cmc": 2.0,
                                                "oracle_text": "", "colors": ["G"]}})
        deck_data = {"decklist": [{"name": "Probe Tutor", "primary_role": "tutor"}]}
        combos = {"synthetic-assembly": [{"name": "Probe line", "pieces": ["Probe Combo A", "Probe Combo B"]}]}
        with patch.dict(exporter.KEY_COMBOS, combos):
            context = exporter.build_goldfish_context(hand + library, deck_data, cards, "The Ur-Dragon", ["G"],
                                                      "synthetic-assembly")
        self.assertEqual(len(context["assemblyLines"]), 1)
        with patch.object(exporter, "commander_mulligan_goldfish", return_value=(list(library), list(hand))):
            by_turn, assembly = exporter.simulate_goldfish_game(hand + library, context, 6)
        self.assertEqual(assembly, [2])
        self.assertEqual(self._series(by_turn, "cumulativeDamage", 3), [0, 0, 1])


class ManaRoundTwoEngineTests(unittest.TestCase):
    """Review round 2 (2026-11-20): {T} abilities of the hatch engine and the
    token makers, through the goldfish turn loop."""

    def _hatch(self, hand_extra, library_extra=(), lands=("Forest", "Forest"), commander_cost="{1}"):
        """The CastPriorityHoldTests hatch deck (broodfire-hatchery's config;
        the commander a vanilla 1-power Shaman costing `commander_cost`):
        (by_turn, the turns of each hatch)."""
        metadata = CastPriorityHoldTests()._hatch_metadata()
        commander = CastPriorityHoldTests.HATCH_COMMANDER
        metadata[commander] = dict(metadata[commander], mana_cost=commander_cost,
                                   cmc=float(commander_cost.strip("{}")))
        metadata["High Market"] = CARDS["High Market"]
        metadata["Thornbite Staff"] = {"type_line": "Kindred Artifact — Shaman Equipment",
                                       "mana_cost": "{2}", "cmc": 2.0, "oracle_text": "", "colors": []}
        bears = [f"Bear {i}" for i in range(20)]
        hand = list(lands) + list(hand_extra)
        library = ["Forest"] * 6 + bears + list(library_extra)
        decklist = hand + library
        context = exporter.build_goldfish_context(
            decklist, {"decklist": [{"name": n} for n in decklist]}, metadata,
            CastPriorityHoldTests.HATCH_COMMANDER, ["G"], CastPriorityHoldTests.HATCH_DECK_ID)
        hatched = []
        original = exporter.hatch_from_library

        def recording(turn, *args, **kwargs):
            hatched.append(turn)
            return original(turn, *args, **kwargs)

        with patch.object(exporter, "commander_mulligan_goldfish", lambda *_: (list(library), list(hand))), \
                patch.object(exporter, "hatch_from_library", recording):
            by_turn, _ = exporter.simulate_goldfish_game(decklist, context, 6)
        return by_turn, hatched

    def test_the_commander_is_tapped_by_her_egg_activation(self):
        # Turn 1: Forest, Ashnod's Altar, the commander ({1}, combat 1).
        # Turn 2: two Forests pay {2}, {T}: an Egg, eaten by the Altar, hatches
        # a Bear. She is tapped and does not attack on turn 2; the Bear (8)
        # attacks from turn 3 while she makes an Egg each turn.
        by_turn, hatched = self._hatch(["Ashnod's Altar"])
        self.assertEqual(hatched[:2], [2, 3])
        self.assertEqual([by_turn[t]["cumulativeDamage"] for t in (1, 2, 3)], [0, 0, 8])

    def test_thornbite_staff_untaps_her_after_the_egg_dies(self):
        # Ashnod's Altar turn 1, Thornbite Staff ({2}) turn 2, the commander
        # ({3}, combat 3) turn 3 with the Staff already out. Turn 4: her Eggs
        # die to the Altar and the Staff untaps her each time, so she attacks
        # (3); the Bears they hatch attack from turn 5.
        by_turn, hatched = self._hatch(["Ashnod's Altar", "Thornbite Staff"],
                                       lands=("Forest", "Forest", "Forest"), commander_cost="{3}")
        self.assertEqual(hatched[0], 4)
        self.assertEqual([by_turn[t]["cumulativeDamage"] for t in (3, 4)], [0, 3])

    def test_high_market_tapped_for_mana_cannot_sacrifice(self):
        # Turn 1 Forest and the commander; turn 2 High Market: its {C} and the
        # Forest pay the Egg activation, so High Market is tapped and the Egg
        # waits. Turn 3 two Forests pay the next one and the untapped High
        # Market sacrifices an Egg: the first hatch is on turn 3.
        by_turn, hatched = self._hatch(["High Market"], lands=("Forest",),
                                       library_extra=("Forest", "Bear 0", "Bear 1"))
        self.assertEqual(hatched[:1], [3])

    def test_castle_ardenvale_tapped_for_mana_makes_no_token(self):
        # Plains and Sol Ring turn 1 (with two Lotus Petals kept); turn 2 the
        # Castle enters untapped and Probe WW takes the Plains and the
        # Castle ({W}{W}), not the one-shot Petals. After combat Sol Ring's
        # {C}{C} and the Petals' {W}{W} would pay {2}{W}{W}, but the Castle
        # is tapped: no Human on turn 2. Damage: Probe WW 2 from turn 3, a
        # Human from turn 3's activation attacks from turn 4.
        damage, _ = TokenMakerGoldfishTests()._run(
            ["Plains", "Castle Ardenvale", "Sol Ring", "Lotus Petal", "Lotus Petal", "Zero Trinket",
             "Zero Trinket"],
            ["Zero Trinket"] * 91 + ["Probe WW", "Zero Trinket"], colors=("W",))
        self.assertEqual(damage[:4], [0, 0, 2, 5])


R3_PROBES = {
    # Made up for review round 3 (2026-11-20): a {1} creature, a {1} rock, a
    # {2}{B} tutor, a {1} artifact, instants of {B}, {1}, {2} and {4}{U}{U}
    # that a combo line names, a {G} creature and a {1} basic-land search.
    "Probe One": {"type_line": "Creature — Test", "mana_cost": "{1}", "cmc": 1.0, "oracle_text": "",
                  "colors": []},
    "Probe Rock": {"type_line": "Artifact", "mana_cost": "{1}", "cmc": 1.0, "oracle_text": "{T}: Add {C}.",
                   "colors": []},
    "Probe Tutor B": {"type_line": "Instant", "mana_cost": "{2}{B}", "cmc": 3.0, "oracle_text": "",
                      "colors": ["B"]},
    "Probe Piece": {"type_line": "Artifact", "mana_cost": "{1}", "cmc": 1.0, "oracle_text": "", "colors": []},
    "Probe Finisher": {"type_line": "Instant", "mana_cost": "{B}", "cmc": 1.0, "oracle_text": "",
                       "colors": ["B"]},
    "Probe Finisher One": {"type_line": "Instant", "mana_cost": "{1}", "cmc": 1.0, "oracle_text": "",
                           "colors": []},
    "Probe Finisher Two": {"type_line": "Instant", "mana_cost": "{2}", "cmc": 2.0, "oracle_text": "",
                           "colors": []},
    "Probe Finisher Six": {"type_line": "Instant", "mana_cost": "{4}{U}{U}", "cmc": 6.0, "oracle_text": "",
                           "colors": ["U"]},
    "Probe G": {"type_line": "Creature — Test", "mana_cost": "{G}", "cmc": 1.0, "oracle_text": "",
                "colors": ["G"]},
    "Probe Basic Search": {"type_line": "Sorcery", "mana_cost": "{1}", "cmc": 1.0, "oracle_text": (
        "Search your library for a basic land card, put it onto the battlefield, then shuffle."),
        "colors": []},
    # The local Scryfall mirror (2026-11-20).
    "Dryad Arbor": {"type_line": "Land Creature — Forest Dryad", "mana_cost": "", "cmc": 0.0, "oracle_text": (
        "(This land isn't a spell, it's affected by summoning sickness, and it has \"{T}: Add {G}.\")"),
        "colors": ["G"], "power": "1"},
    "Spire of Industry": {"type_line": "Land", "mana_cost": "", "cmc": 0.0, "oracle_text": (
        "{T}: Add {C}.\n{T}, Pay 1 life: Add one mana of any color. Activate only if you control an "
        "artifact."), "colors": []},
    "Adarkar Wastes": {"type_line": "Land", "mana_cost": "", "cmc": 0.0, "oracle_text": (
        "{T}: Add {C}.\n{T}: Add {W} or {U}. This land deals 1 damage to you."), "colors": []},
    "Crypt Ghast": {"type_line": "Creature — Spirit", "mana_cost": "{3}{B}", "cmc": 4.0, "oracle_text": (
        "Extort (Whenever you cast a spell, you may pay {W/B}. If you do, each opponent loses 1 life and you "
        "gain that much life.)\nWhenever you tap a Swamp for mana, add an additional {B}."), "colors": ["B"],
        "power": "2"},
    "Urborg, Tomb of Yawgmoth": {"type_line": "Legendary Land", "mana_cost": "", "cmc": 0.0,
                                 "oracle_text": "Each land is a Swamp in addition to its other land types.",
                                 "colors": []},
}


class ManaRoundThreeGoldfishTests(unittest.TestCase):
    """Review round 3 (2026-11-20) through the goldfish turn loop: the
    ManaModelGoldfishTests harness unless a case builds its own; CARDS plus
    R3_PROBES."""

    _series = staticmethod(ManaModelGoldfishTests._series)

    def _run(self, hand, library, colors=("C",), deck_data=None, combos=None):
        """(by_turn, assembly turns) of one game with the opening fixed."""
        cards = dict(CARDS, **R3_PROBES)
        decklist = hand + library
        deck_id = "synthetic-assembly" if combos else "synthetic-mana"
        with patch.dict(exporter.KEY_COMBOS, {deck_id: combos} if combos else {}):
            context = exporter.build_goldfish_context(decklist, deck_data or {"decklist": []}, cards,
                                                      "The Ur-Dragon", list(colors), deck_id)
        with patch.object(exporter, "commander_mulligan_goldfish", return_value=(list(library), list(hand))):
            return exporter.simulate_goldfish_game(decklist, context, 6)

    TUTOR_LINE = {"decklist": [{"name": "Probe Tutor B", "primary_role": "tutor"}]}
    ASSEMBLY = [{"name": "Probe line", "pieces": ["Probe Combo A", "Probe Combo B"]}]

    def test_a_filler_pays_with_the_payment_that_keeps_the_gate(self):
        # Probe Combo A is in hand and Probe Tutor B ({2}{B}) can fetch Probe
        # Combo B: the assembly gate is {2}{B}. Turn 1 the Swamp (the name
        # tie-break) casts Sol Ring. Turn 2 draws Probe One ({1}) and plays
        # the Forest: the preferred payment (the Swamp, listed first) breaks
        # the gate; the payment that keeps it (Sol Ring's {C}) is the one
        # committed, so the gate is read on turn 2 with {B}, {C} and {G}
        # left. Paying again with the preferred payment it would wait for
        # turn 3.
        hand = ["Swamp", "Forest", "Sol Ring", "Probe Combo A", "Probe Tutor B", "Probe Nine", "Probe Nine"]
        library = ["Probe Combo B"] + ["Probe Nine"] * 89 + ["Probe One", "Probe Nine"]
        by_turn, assembly = self._run(hand, library, ("B", "G"), self.TUTOR_LINE, self.ASSEMBLY)
        self.assertEqual(assembly, [2])
        self.assertEqual(self._series(by_turn, "cumulativeDamage", 3), [0, 0, 1])

    def test_a_cast_never_held_back_still_keeps_the_gate_when_it_can(self):
        # As above with Probe Rock ({1}, a mana source, never held back)
        # drawn on turn 2: it takes Sol Ring's {C}, not the Swamp, and the
        # gate is read on turn 2. Taking the preferred payment regardless of
        # the gate, it would wait for turn 3.
        hand = ["Swamp", "Forest", "Sol Ring", "Probe Combo A", "Probe Tutor B", "Probe Nine", "Probe Nine"]
        library = ["Probe Combo B"] + ["Probe Nine"] * 89 + ["Probe Rock", "Probe Nine"]
        _, assembly = self._run(hand, library, ("B", "G"), self.TUTOR_LINE, self.ASSEMBLY)
        self.assertEqual(assembly, [2])

    def test_a_line_piece_keeps_the_rest_of_its_line(self):
        # G1. Combo line: Probe Piece ({1}, drawn on turn 2) and Probe
        # Finisher ({B}, in hand). Turn 2: the Swamp (turn 1) and the Forest.
        # Casting the Piece keeps the rest of the line ({B}, the Piece on the
        # battlefield), so the Forest pays and the line is ready on turn 2.
        # Holding the Piece's own cost again ({1}{B} beside the {1}), no
        # payment keeps it and the Swamp pays: ready on turn 3.
        deck_data = {"decklist": [], "winConditions": [
            {"title": "Probe line", "kind": "combo", "pieces": ["Probe Piece", "Probe Finisher"],
             "cards": ["Probe Piece", "Probe Finisher"], "description": ""}]}
        hand = ["Swamp", "Forest", "Probe Finisher"] + ["Probe Nine"] * 4
        library = ["Probe Nine"] * 91 + ["Probe Piece", "Probe Nine"]
        by_turn, _ = self._run(hand, library, ("B", "G"), deck_data)
        self.assertEqual(self._series(by_turn, "comboLethal"), [0, 1, 1, 1, 1, 1])

    def test_a_land_that_enters_tapped_cannot_use_its_tap_ability_that_turn(self):
        # G3. Forests on turns 1-2, Myriad Landscape on turn 3 (it enters
        # tapped): its fetch ({2}, {T}) waits for turn 4 although the two
        # Forests are unspent on turn 3. Read as untapped it would fetch the
        # two Forests on turn 3 (four lands then).
        by_turn, _ = self._run(["Forest", "Forest", "Myriad Landscape"] + ["Probe Nine"] * 4,
                               ["Forest"] * 4 + ["Probe Nine"] * 88, ("G",))
        self.assertEqual(self._series(by_turn, "lands"), [1, 2, 3, 4, 4, 4])

    def test_urza_keeps_his_own_mana_after_he_attacks(self):
        # Urza ({2}{U}{U}) on turn 4 with four Islands; Zero Trinket out from
        # turn 1. Turn 5 draws Probe Finisher Six ({4}{U}{U}), a one-piece
        # combo line: four Islands, his {U} (his Construct is tapped, not
        # him) and the Trinket's {U} pay it. Urza attacks (4) and the line
        # is read after combat with his {U} still there: ready on turn 5.
        deck_data = {"decklist": [], "winConditions": [
            {"title": "Probe line", "kind": "combo", "pieces": ["Probe Finisher Six"],
             "cards": ["Probe Finisher Six"], "description": ""}]}
        hand = ["Urza, Lord High Artificer", "Island", "Island", "Island", "Zero Trinket", "Probe Nine",
                "Probe Nine"]
        library = ["Probe Nine"] * 88 + ["Probe Finisher Six", "Probe Nine", "Probe Nine", "Island", "Probe Nine"]
        by_turn, _ = self._run(hand, library, ("U",), deck_data)
        self.assertEqual(self._series(by_turn, "comboLethal"), [0, 0, 0, 0, 1, 1])
        self.assertEqual(self._series(by_turn, "cumulativeDamage"), [0, 0, 0, 0, 4, 8])

    def test_a_vigilant_mana_creature_pays_and_attacks(self):
        # G6 (M9). Probe Vigilant Elf on turn 1; turn 2 Probe Three takes both
        # Forests and the Elf's {G}: the Elf is not tapped by it and attacks
        # (1). Damage from turn 3: Probe Three 3 and the Elf 1 a turn.
        by_turn, _ = self._run(["Probe Vigilant Elf", "Forest", "Forest", "Probe Three"] + ["Probe Nine"] * 3,
                               ["Probe Nine"] * 92, ("G",))
        self.assertEqual(self._series(by_turn, "cumulativeDamage"), [0, 1, 5, 9, 13, 17])

    def test_forsaken_monument_adds_for_a_land_a_search_puts_onto_the_battlefield(self):
        # Five Wastes cast Forsaken Monument on turn 5. Turn 6 draws Probe
        # Basic Search ({1}): a Wastes pays it and the Wastes it finds enters
        # untapped with its {C} and the Monument's {C} for it: 10 + 2.
        library = ["Wastes"] + ["Probe BB"] * 86 + ["Probe Basic Search"] + ["Probe BB"] * 5
        by_turn, _ = self._run(["Forsaken Monument"] + ["Wastes"] * 5 + ["Probe BB"], library)
        self.assertEqual(self._series(by_turn, "availableMana"), [1, 2, 3, 4, 5, 12])


class ManaRoundThreeEngineTests(unittest.TestCase):
    """Review round 3 (2026-11-20): the hatch engine's holds, High Market
    and Thornbite Staff, and Halo Fountain, through the goldfish turn loop
    (the CastPriorityHoldTests hatch deck: broodfire-hatchery's config, the
    commander a vanilla Shaman of the given cost)."""

    def _hatch(self, hand, library_extra=(), commander_cost="{1}", win_conditions=(), spy=False):
        """(by_turn, turns of each hatch, casts by turn, High Market's tapped
        state at each turn's end, whether its mana was in the end of each
        turn's pool)."""
        metadata = CastPriorityHoldTests()._hatch_metadata()
        commander = CastPriorityHoldTests.HATCH_COMMANDER
        metadata[commander] = dict(metadata[commander], mana_cost=commander_cost,
                                   cmc=float(commander_cost.strip("{}")))
        metadata["High Market"] = CARDS["High Market"]
        metadata["Thornbite Staff"] = {"type_line": "Kindred Artifact — Shaman Equipment", "mana_cost": "{2}",
                                       "cmc": 2.0, "oracle_text": "", "colors": []}
        metadata.update(R3_PROBES)
        library = ["Forest"] * 6 + [f"Bear {i}" for i in range(20)] + list(library_extra)
        decklist = list(hand) + library
        deck_data = {"decklist": [{"name": n} for n in decklist], "winConditions": list(win_conditions)}
        context = exporter.build_goldfish_context(decklist, deck_data, metadata, commander, ["G"],
                                                  CastPriorityHoldTests.HATCH_DECK_ID)
        hatched, casts, market_tapped, market_mana = [], defaultdict(list), [], []
        hatch, resolve = exporter.hatch_from_library, exporter.resolve_cast_effects
        metrics, rearm = exporter.metrics_from_board, exporter.rearm_once_sources

        def recording_hatch(turn, *args, **kwargs):  # call-through spies
            hatched.append(turn)
            return hatch(turn, *args, **kwargs)

        def recording_resolve(name, profile, turn, *args, **kwargs):
            casts[turn].append(name)
            return resolve(name, profile, turn, *args, **kwargs)

        def recording_metrics(**kwargs):
            market_tapped.append(any(p.get("tapped") for p in kwargs["permanents"] if p["name"] == "High Market"))
            return metrics(**kwargs)

        def recording_rearm(permanents, pool, *args):
            market_mana.append(any(a.source is not None and a.source["name"] == "High Market"
                                   for a in pool.sources))
            return rearm(permanents, pool, *args)

        with patch.object(exporter, "commander_mulligan_goldfish", lambda *_: (list(library), list(hand))), \
                patch.object(exporter, "hatch_from_library", recording_hatch), \
                patch.object(exporter, "resolve_cast_effects", recording_resolve), \
                patch.object(exporter, "metrics_from_board", recording_metrics), \
                patch.object(exporter, "rearm_once_sources", recording_rearm):
            by_turn, _ = exporter.simulate_goldfish_game(decklist, context, 6)
        return by_turn, hatched, casts, market_tapped, market_mana

    LINE = {"title": "Probe line", "kind": "combo", "description": ""}

    def test_the_held_activation_and_a_gate_are_kept_together(self):
        # G2. Turn 1: Forest, the commander ({1}), Ashnod's Altar. Turns 2-3
        # an Egg is made and hatched each turn (the Two Drops wait: {2} plus
        # the held {2} is more than the turn has). Turn 4 draws Probe
        # Finisher Two ({2}), a one-piece combo line, and has four Forests:
        # the Egg activation and the line are kept together ({4}), so the
        # Two Drop waits again, the Egg is made and hatched, and the line is
        # ready with the {2} left. Kept apart, the Two Drop would keep each
        # ({2} left) and the activation would then break the gate: no hatch
        # on turn 4.
        line = dict(self.LINE, pieces=["Probe Finisher Two"], cards=["Probe Finisher Two"])
        by_turn, hatched, casts, _, _ = self._hatch(
            ["Forest"] * 4 + ["Ashnod's Altar", "Two Drop 0", "Two Drop 1"],
            library_extra=("Probe Finisher Two", "Bear 0", "Bear 1", "Bear 2", "Bear 3", "Bear 4"),
            win_conditions=[line])
        self.assertEqual(hatched[:3], [2, 3, 4])
        self.assertNotIn("Two Drop 0", casts[4])
        self.assertEqual(by_turn[4]["comboLethal"], 1)

    def test_high_market_sacrifices_only_when_its_tap_keeps_the_gate(self):
        # G3. Turn 1 Forest and the commander ({1}); turn 2 Forest; turn 3
        # High Market and Probe Finisher One ({1}, a one-piece line). Two
        # Forests pay the Egg activation; High Market's {T} would take the
        # {C} the line needs, so it sacrifices nothing on turn 3 and the line
        # is ready. Turn 4 (no gate left) it sacrifices the Eggs' first.
        line = dict(self.LINE, pieces=["Probe Finisher One"], cards=["Probe Finisher One"])
        by_turn, hatched, _, _, _ = self._hatch(
            ["Forest", "Forest", "High Market"] + ["Bear 16", "Bear 17", "Bear 18", "Bear 19"],
            library_extra=("Probe Finisher One", "Bear 15", "Bear 14"), win_conditions=[line])
        self.assertEqual(self._series(by_turn, "comboLethal", 4), [0, 0, 1, 1])
        self.assertEqual(hatched[:1], [4])

    _series = staticmethod(ManaModelGoldfishTests._series)

    def test_high_markets_sacrifice_taps_it_and_thornbite_staff_untaps_her(self):
        # G3, G7. Thornbite Staff turn 2, the commander ({3}) turn 3, High
        # Market turn 4: two Forests pay the Egg activation (she is tapped),
        # High Market sacrifices the Egg (tapped, its {C} gone from the
        # turn's mana) and the Staff untaps her as the Egg dies: she attacks
        # (3) on turn 4.
        by_turn, hatched, casts, market_tapped, market_mana = self._hatch(
            ["Forest", "Forest", "Forest", "High Market", "Thornbite Staff", "Bear 18", "Bear 19"],
            commander_cost="{3}")
        self.assertEqual((casts[2], casts[3][:1]), (["Thornbite Staff"], [CastPriorityHoldTests.HATCH_COMMANDER]))
        self.assertEqual(hatched[:1], [4])
        self.assertEqual((market_tapped[3], market_mana[3]), (True, False))
        self.assertEqual(self._series(by_turn, "cumulativeDamage", 4), [0, 0, 0, 3])

    def test_halo_fountain_untaps_a_creature_tapped_for_mana(self):
        # G7. stampede-acres' config. Plains turns 1-2, Dryad Arbor turn 3 (a
        # land creature that never attacks; summoning sick, it enters
        # tapped, so it loses the land choice to the second Plains). Turn 4
        # Halo Fountain takes all three; Probe G ({G}), drawn on turn 4,
        # waits. Turn 5 the Arbor pays Probe G and is tapped, so Halo's {W}
        # (a Plains) untaps it: a Citizen, attacking from turn 6, then one a
        # turn (Probe G attacks from turn 6). Counting only creatures that
        # attacked, the first Citizen would come on turn 6.
        library = ["Zero Trinket"] * 89 + ["Probe G", "Zero Trinket", "Zero Trinket", "Zero Trinket"]
        with patch.dict(CARDS, R3_PROBES):
            damage, _ = TokenMakerGoldfishTests()._run(
                ["Halo Fountain", "Dryad Arbor", "Plains", "Plains"] + ["Zero Trinket"] * 3, library,
                colors=("W", "G"))
        self.assertEqual(damage, [0, 0, 0, 0, 0, 2, 5, 9, 14, 20])


class ManaRoundThreeUnitTests(unittest.TestCase):
    """Review round 3 (2026-11-20): the payment committed, the sources a
    payment settles, Urza's grant and Reflecting Pool, CARDS plus R3_PROBES."""

    ONE = PAY_ONE

    @staticmethod
    def mana(colours, record, order=0, **kwargs):
        return exporter.tag_atoms([frozenset(colours)], record, order, **kwargs)[0]

    def test_spend_mana_commits_the_payment_it_was_given(self):
        # {1} keeping {G}: the payment found takes the Swamp; spend_mana
        # commits that one (the Forest, listed first, stays untapped).
        context = exporter.build_goldfish_context(["Forest", "Swamp"], {"decklist": []}, CARDS,
                                                  "Probe Commander", ["B", "G"], "synthetic-commit")
        profiles = context["profiles"]
        permanents, lands = [], []
        forest = exporter.put_land_onto_battlefield("Forest", 1, False, permanents, lands, profiles, ["B", "G"])
        swamp = exporter.put_land_onto_battlefield("Swamp", 1, False, permanents, lands, profiles, ["B", "G"])
        pool = exporter.GoldfishManaPool(turn=2)
        exporter.refresh_pool(pool, permanents, profiles, 2)
        keep = [[dict(self.ONE, generic=0, G=1)]]
        paid = exporter.find_payment(pool, self.ONE, keep)
        left = exporter.spend_mana(pool, self.ONE, permanents, lands, profiles, paid=paid)
        self.assertIs(left, paid)
        self.assertEqual((forest.get("tapped"), swamp.get("tapped")), (False, True))

    def test_a_payment_settles_only_the_sources_it_newly_used(self):
        # End of a turn that spent Basalt Monolith (it is among the sources
        # the turn used and tapped): five Wastes re-arm it with three, then
        # crack Wayfarer's Bauble with two. The Bauble's payment neither
        # spends nor taps Basalt again: it stays untapped with its mana for
        # the next turn.
        context = exporter.build_goldfish_context(["Basalt Monolith", "Wayfarer's Bauble", "Wastes"],
                                                  {"decklist": []}, CARDS, "Probe Commander", ["C"],
                                                  "synthetic-settle")
        profiles = context["profiles"]
        permanents, lands = [], []
        for name in ("Basalt Monolith", "Wayfarer's Bauble"):
            exporter.resolve_cast_effects(name, profiles[name], 1, exporter.GoldfishManaPool([]), [], [],
                                          permanents, lands, profiles, ["C"])
        basalt = permanents[0]
        basalt.update(onceSpent=True, tapped=True)
        for _ in range(5):
            exporter.put_land_onto_battlefield("Wastes", 1, False, permanents, lands, profiles, ["C"])
        pool = exporter.GoldfishManaPool(tapped={id(basalt)}, tapping={id(basalt)}, turn=2, lasting_only=True)
        exporter.refresh_pool(pool, permanents, profiles, 2)
        left = exporter.rearm_once_sources(permanents, pool, lands, profiles)
        self.assertEqual((basalt["onceSpent"], basalt["tapped"]), (False, False))
        exporter.activate_land_fetches(2, left, ["Wastes"] * 3, [], permanents, lands, profiles, ["C"])
        self.assertNotIn("Wayfarer's Bauble", [p["name"] for p in permanents])
        self.assertEqual((basalt["onceSpent"], basalt["tapped"]), (False, False))

    def test_urza_grants_each_idle_artifact_its_own_tap_for_blue(self):
        # G5. Urza with Zero Trinket, Wayfarer's Bauble and an Island: Urza's
        # own {U} (his Construct's) does not tap him; the Trinket's and the
        # Bauble's {U} tap them.
        context = exporter.build_goldfish_context(
            ["Urza, Lord High Artificer", "Zero Trinket", "Wayfarer's Bauble", "Island"], {"decklist": []},
            CARDS, "Probe Commander", ["U"], "synthetic-urza")
        profiles = context["profiles"]
        permanents, lands = [], []
        for name in ("Urza, Lord High Artificer", "Zero Trinket", "Wayfarer's Bauble"):
            exporter.resolve_cast_effects(name, profiles[name], 1, exporter.GoldfishManaPool([]), [], [],
                                          permanents, lands, profiles, ["U"])
        urza, trinket, bauble = permanents
        exporter.put_land_onto_battlefield("Island", 1, False, permanents, lands, profiles, ["U"])
        atoms = exporter.board_mana(permanents, 2, profiles)
        self.assertEqual(sorted((a.source["name"], "".join(sorted(a)), a.taps) for a in atoms),
                         [("Island", "U", True), ("Urza, Lord High Artificer", "U", False),
                          ("Wayfarer's Bauble", "U", True), ("Zero Trinket", "U", True)])
        # The Bauble's own {U} cannot pay the {2} of its {T} ability.
        two = dict(self.ONE, generic=2, total=2)
        bauble_and_island = exporter.GoldfishManaPool([a for a in atoms if a.source in (bauble, permanents[3])])
        self.assertIsNone(exporter.find_payment(bauble_and_island, two, taps=bauble))
        self.assertIsNotNone(exporter.find_payment(exporter.GoldfishManaPool(atoms), two, taps=bauble))
        # Spending every {U}: the Trinket, the Bauble and the Island are
        # tapped, not Urza; tapped, the Trinket offers nothing more.
        pool = exporter.GoldfishManaPool(atoms, turn=2)
        exporter.spend_mana(pool, dict(self.ONE, generic=4, total=4), permanents, lands, profiles)
        self.assertEqual([p.get("tapped", False) for p in permanents], [False, True, True, True])
        # Urza tapped (he attacked): his own {U} is still offered; the
        # Trinket, tapped, offers nothing.
        for record in permanents:
            record["tapped"] = record is not bauble
        self.assertEqual(sorted(a.source["name"] for a in exporter.board_mana(permanents, 2, profiles)),
                         ["Urza, Lord High Artificer", "Wayfarer's Bauble"])

    def test_reflecting_pool_reads_every_colour_another_land_could_produce(self):
        # G4. Spire of Industry with no artifact out makes only {C}, but it
        # could produce any colour (its second ability's condition and life
        # cost do not matter): Reflecting Pool makes {C} or any colour.
        cards = dict(CARDS, **R3_PROBES)
        context = exporter.build_goldfish_context(["Reflecting Pool", "Spire of Industry"], {"decklist": []},
                                                  cards, "Probe Commander", ["U", "B"], "synthetic-pool")
        profiles = context["profiles"]
        permanents, lands = [], []
        spire = exporter.put_land_onto_battlefield("Spire of Industry", 1, False, permanents, lands, profiles,
                                                   ["U", "B"])
        reflecting = exporter.put_land_onto_battlefield("Reflecting Pool", 1, False, permanents, lands,
                                                        profiles, ["U", "B"])
        # "Any color" reads as the commander's colours ({U}, {B}).
        self.assertEqual(mana_letters(exporter.record_atoms(spire, permanents, profiles, 2)), ["C"])
        self.assertEqual(mana_letters(exporter.record_atoms(reflecting, permanents, profiles, 2)), ["UBC"])

    def test_mana_read_again_carries_the_triggers_and_grants_out(self):
        # I1, the cases review round 3 found. Crypt Ghast out, a Forest's
        # {G} spent, Urborg put onto the battlefield untapped by a search:
        # the untapped Forest makes {G} or {B} and, a Swamp now, Ghast's
        # extra {B}; Urborg makes {B} and the extra {B}.
        cards = dict(CARDS, **R3_PROBES)
        context = exporter.build_goldfish_context(
            ["Crypt Ghast", "Urborg, Tomb of Yawgmoth", "Forest", "Wastes", "Chromatic Lantern",
             "Forsaken Monument"], {"decklist": []}, cards, "Probe Commander", ["B", "G"], "synthetic-reread")
        profiles = context["profiles"]
        permanents, lands = [], []
        for _ in range(2):
            exporter.put_land_onto_battlefield("Forest", 1, False, permanents, lands, profiles, ["B", "G"])
        exporter.resolve_cast_effects("Crypt Ghast", profiles["Crypt Ghast"], 1, exporter.GoldfishManaPool([]),
                                      [], [], permanents, lands, profiles, ["B", "G"])
        pool = exporter.GoldfishManaPool(turn=2)
        exporter.refresh_pool(pool, permanents, profiles, 2)
        pool = exporter.spend_mana(pool, dict(self.ONE, generic=0, G=1), permanents, lands, profiles)
        search = {"count": 1, "toHand": 0, "basicOnly": False, "allowedSubtypes": set(), "perType": [],
                  "sharedType": False, "entersTapped": False}
        exporter.fetch_lands(search, 1, 2, pool, ["Urborg, Tomb of Yawgmoth"], [], permanents, lands, profiles,
                             ["B", "G"])
        self.assertEqual(sorted(mana_letters(a for a in pool.sources if a.source is not None
                                             and exporter.atom_source_id(a) not in pool.tapped)),
                         ["B", "B", "B", "BG"])
        # Forsaken Monument out, Chromatic Lantern cast: a Wastes makes {C}
        # and the Monument's {C}, or any one colour, never a colour and the
        # extra {C}.
        permanents, lands = [], []
        exporter.put_land_onto_battlefield("Wastes", 1, False, permanents, lands, profiles, ["B", "G"])
        pool = exporter.GoldfishManaPool(turn=2)
        for name in ("Forsaken Monument", "Chromatic Lantern"):
            exporter.resolve_cast_effects(name, profiles[name], 2, pool, [], [], permanents, lands, profiles,
                                          ["B", "G"])
        wastes = exporter.GoldfishManaPool([a for a in pool.sources if a.source["name"] == "Wastes"])
        pips = dict(self.ONE, generic=0)
        self.assertEqual([wastes.can_cast(dict(pips, C=2, total=2)), wastes.can_cast(dict(pips, G=1, total=1)),
                          wastes.can_cast(dict(pips, G=1, C=1, total=2))], [True, True, False])

    def test_forsaken_monument_adds_only_with_a_pain_lands_colourless_mana(self):
        # Adarkar Wastes taps for {C}, or for {W} or {U}: beside Forsaken
        # Monument it makes {C}{C} (the extra comes with the {C}) or {W},
        # never {W} and the extra {C}.
        cards = dict(CARDS, **R3_PROBES)
        context = exporter.build_goldfish_context(["Adarkar Wastes", "Forsaken Monument"], {"decklist": []},
                                                  cards, "Probe Commander", ["W", "U"], "synthetic-pain")
        profiles = context["profiles"]
        permanents, lands = [], []
        exporter.put_land_onto_battlefield("Adarkar Wastes", 1, False, permanents, lands, profiles, ["W", "U"])
        exporter.resolve_cast_effects("Forsaken Monument", profiles["Forsaken Monument"], 1,
                                      exporter.GoldfishManaPool([]), [], [], permanents, lands, profiles,
                                      ["W", "U"])
        pool = exporter.GoldfishManaPool(exporter.board_mana(permanents, 2, profiles))
        pips = dict(self.ONE, generic=0)
        self.assertEqual([pool.can_cast(dict(pips, C=2, total=2)), pool.can_cast(dict(pips, W=1, total=1)),
                          pool.can_cast(dict(pips, W=1, C=1, total=2))], [True, True, False])


R4_PROBES = {
    # The local Scryfall mirror (2026-11-20).
    "The Mycosynth Gardens": {"type_line": "Land — Sphere", "mana_cost": "", "cmc": 0.0, "oracle_text": (
        "{T}: Add {C}.\n{1}, {T}: Add one mana of any color.\n{X}, {T}: This land becomes a copy of target "
        "nontoken artifact you control with mana value X."), "colors": []},
    "Cabal Coffers": {"type_line": "Land", "mana_cost": "", "cmc": 0.0,
                      "oracle_text": "{2}, {T}: Add {B} for each Swamp you control.", "colors": []},
    "Maze of Ith": {"type_line": "Land", "mana_cost": "", "cmc": 0.0, "oracle_text": (
        "{T}: Untap target attacking creature. Prevent all combat damage that would be dealt to and dealt by "
        "that creature this turn."), "colors": []},
    "Nevinyrral's Disk": {"type_line": "Artifact", "mana_cost": "{4}", "cmc": 4.0, "oracle_text": (
        "This artifact enters tapped.\n{1}, {T}: Destroy all artifacts, creatures, and enchantments."),
        "colors": []},
    "Yasharn, Implacable Earth": {"type_line": "Legendary Creature — Elemental Boar", "mana_cost": "{2}{G}{W}",
                                  "cmc": 4.0, "colors": ["G", "W"], "power": "4", "oracle_text": (
        "When Yasharn enters, search your library for a basic Forest card and a basic Plains card, reveal "
        "those cards, put them into your hand, then shuffle.\nPlayers can't pay life or sacrifice nonland "
        "permanents to cast spells or activate abilities.")},
    # Made up: a G/W land, an artifact with a {T} ability a combo line names, an artifact
    # creature, a {G} rock, a {1} land-fetching artifact whose land enters
    # untapped, a {1} tutor, and instants two assembly lines name.
    "Probe Dual GW": {"type_line": "Land", "mana_cost": "", "cmc": 0.0, "oracle_text": "{T}: Add {G} or {W}.",
                      "colors": []},
    "Probe Scepter": {"type_line": "Artifact", "mana_cost": "{2}", "cmc": 2.0,
                      "oracle_text": "{2}, {T}: Draw a card.", "colors": []},
    "Probe Golem": {"type_line": "Artifact Creature — Golem", "mana_cost": "{3}", "cmc": 3.0, "oracle_text": "",
                    "colors": [], "power": "3"},
    "Viridian Crystal": {"type_line": "Artifact", "mana_cost": "{0}", "cmc": 0.0, "oracle_text": "{T}: Add {G}.",
                         "colors": []},
    "Probe Untapped Fetcher": {"type_line": "Artifact", "mana_cost": "{1}", "cmc": 1.0, "oracle_text": (
        "{1}, {T}, Sacrifice this artifact: Search your library for a basic land card, put it onto the "
        "battlefield, then shuffle."), "colors": []},
    "Probe Tutor One": {"type_line": "Instant", "mana_cost": "{1}", "cmc": 1.0, "oracle_text": "", "colors": []},
    "Probe Line A1": {"type_line": "Instant", "mana_cost": "{9}", "cmc": 9.0, "oracle_text": "", "colors": []},
    "Probe Line B1": {"type_line": "Instant", "mana_cost": "{9}", "cmc": 9.0, "oracle_text": "", "colors": []},
    "Probe Line A2": {"type_line": "Instant", "mana_cost": "{9}", "cmc": 9.0, "oracle_text": "", "colors": []},
    "Probe Line B2": {"type_line": "Instant", "mana_cost": "{9}", "cmc": 9.0, "oracle_text": "", "colors": []},
}


class ManaRoundFourGoldfishTests(unittest.TestCase):
    """Review round 4 (2026-11-20) through the goldfish turn loop; CARDS,
    R3_PROBES and R4_PROBES."""

    _series = staticmethod(ManaModelGoldfishTests._series)

    @staticmethod
    def cards() -> dict:
        return dict(CARDS, **R3_PROBES, **R4_PROBES)

    def _run(self, hand, library, colors, deck_data=None, deck_id="synthetic-mana", spy=None):
        """(by_turn, assembly turns); ``spy(name, **kwargs)`` sees each
        metrics_from_board call's permanents."""
        decklist = hand + library
        context = exporter.build_goldfish_context(decklist, deck_data or {"decklist": []}, self.cards(),
                                                  "The Ur-Dragon", list(colors), deck_id)
        metrics = exporter.metrics_from_board

        def recording(**kwargs):
            if spy is not None:
                spy(kwargs["turn"], kwargs["permanents"])
            return metrics(**kwargs)

        with patch.object(exporter, "commander_mulligan_goldfish", return_value=(list(library), list(hand))), \
                patch.object(exporter, "metrics_from_board", recording):
            return exporter.simulate_goldfish_game(decklist, context, 6)

    def test_hatch_payments_keep_a_held_aggravated_assault(self):
        # Fix 1. broodfire-hatchery's config with the CombatModifierGoldfishTests
        # cards (Atla costs {1}). Turn 1: a Forest, two Ruby Crystals ({R}),
        # three Viridian Crystals ({G}; they sort after the Rubies), Atla,
        # Ashnod's Altar, Aggravated Assault and Attacker A. Turn 2: seven
        # mana, two red. Atla's {2} paid the preferred way (the first Forest and
        # the first Ruby Crystal) leaves one red and Assault's {3}{R}{R} fails;
        # the payment that keeps Assault is taken, so turn 2 has two combats:
        # Attacker A deals 1 in the first, Attacker A and Atla (tapped by her
        # Egg, untapped by Assault) 1 each in the second: 3. Spending the
        # Assault mana, turn 2 would deal 1.
        metadata = CombatModifierGoldfishTests()._metadata()
        commander = CombatModifierGoldfishTests.COMMANDER
        metadata[commander] = dict(metadata[commander], mana_cost="{1}", cmc=1)
        metadata["Ashnod's Altar"] = CastPriorityHoldTests()._hatch_metadata()["Ashnod's Altar"]
        metadata["Viridian Crystal"] = dict(R4_PROBES["Viridian Crystal"], name="Viridian Crystal")
        hand = (["Forest", "Forest", "Ruby Crystal", "Ruby Crystal"] + ["Viridian Crystal"] * 3
                + ["Ashnod's Altar", "Aggravated Assault", "Attacker A"])
        library = list(CombatModifierGoldfishTests.FILLERS)
        decklist = hand + library
        context = exporter.build_goldfish_context(decklist, {"decklist": [{"name": n} for n in decklist]},
                                                  metadata, commander, ["G"], CombatModifierGoldfishTests.DECK_ID)
        eggs = []
        hatch = exporter.hatch_from_library

        def recording(turn, *args, **kwargs):  # an Egg died: one was made
            eggs.append(turn)
            return hatch(turn, *args, **kwargs)

        with patch.object(exporter, "commander_mulligan_goldfish", lambda *_: (list(library), list(hand))), \
                patch.object(exporter, "hatch_from_library", recording):
            by_turn, _ = exporter.simulate_goldfish_game(decklist, context, 6)
        self.assertEqual(eggs[:1], [2])
        self.assertEqual(by_turn[2]["combat"], 3)

    def test_a_line_piece_keeps_the_rest_of_its_line_whatever_the_order(self):
        # G1, not by board order. Combo line: Probe Piece ({1}, drawn on turn
        # 2) and Probe Finisher ({B}). Turn 1 Probe Dual GW (two new colours),
        # turn 2 the Swamp. The preferred payment of {1} takes the Swamp (the
        # narrowest colours first, though listed second); the Piece keeps the
        # rest of its line ({B}), so the Dual pays and the line is ready on
        # turn 2. Holding the Piece's cost again, it would be ready on turn 3.
        deck_data = {"decklist": [], "winConditions": [
            {"title": "Probe line", "kind": "combo", "pieces": ["Probe Piece", "Probe Finisher"],
             "cards": ["Probe Piece", "Probe Finisher"], "description": ""}]}
        by_turn, _ = self._run(["Swamp", "Probe Dual GW", "Probe Finisher"] + ["Probe Nine"] * 4,
                               ["Probe Nine"] * 91 + ["Probe Piece", "Probe Nine"], ("B", "G", "W"), deck_data)
        self.assertEqual(self._series(by_turn, "comboLethal"), [0, 1, 1, 1, 1, 1])

    def test_the_held_activation_is_joined_with_each_gate_on_its_own(self):
        # G2 with two gates. Two assembly lines, each with a piece in hand and
        # the other in the library; Probe Tutor One ({1}) can fetch either, so
        # drawn on turn 4 it makes both gates {1}. Turn 4 has four Forests and
        # the Egg activation ({2}) held: each gate is kept together with the
        # activation ({3} each), not the two summed ({4}); Two Drop 0 ({2})
        # waits, the Egg is made and hatched, and both lines are assembled.
        metadata = CastPriorityHoldTests()._hatch_metadata()
        commander = CastPriorityHoldTests.HATCH_COMMANDER
        metadata.update({name: R4_PROBES[name] for name in R4_PROBES if name.startswith("Probe")})
        hand = ["Forest"] * 4 + ["Ashnod's Altar", "Two Drop 0", "Probe Line A1", "Probe Line A2"]
        library = (["Probe Line B1", "Probe Line B2"] + ["Forest"] * 6 + [f"Bear {i}" for i in range(5, 20)]
                   + ["Probe Tutor One", "Bear 0", "Bear 1", "Bear 2", "Bear 3", "Bear 4"])
        decklist = hand + library
        deck_data = {"decklist": [{"name": n, "primary_role": "tutor" if n == "Probe Tutor One" else "other"}
                                  for n in decklist]}
        combos = {CastPriorityHoldTests.HATCH_DECK_ID: [
            {"name": "Probe line 1", "pieces": ["Probe Line A1", "Probe Line B1"]},
            {"name": "Probe line 2", "pieces": ["Probe Line A2", "Probe Line B2"]}]}
        with patch.dict(exporter.KEY_COMBOS, combos):
            context = exporter.build_goldfish_context(decklist, deck_data, metadata, commander, ["G"],
                                                      CastPriorityHoldTests.HATCH_DECK_ID)
        self.assertEqual(len(context["assemblyLines"]), 2)
        keeps, hatched = [], []
        find, hatch = exporter.find_payment, exporter.hatch_from_library

        def amount(cost):
            return cost.get("generic", 0) + sum(cost.get(c, 0) for c in "WUBRGC")

        def recording_find(pool, cost, keep=(), *args, **kwargs):
            if pool.turn == 4 and amount(cost) == 2:
                keeps.append(sorted(sorted(amount(c) for c in costs) for costs in keep))
            return find(pool, cost, keep, *args, **kwargs)

        def recording_hatch(turn, *args, **kwargs):
            hatched.append(turn)
            return hatch(turn, *args, **kwargs)

        with patch.object(exporter, "commander_mulligan_goldfish", lambda *_: (list(library), list(hand))), \
                patch.object(exporter, "find_payment", recording_find), \
                patch.object(exporter, "hatch_from_library", recording_hatch):
            _, assembly = exporter.simulate_goldfish_game(decklist, context, 6)
        self.assertEqual(keeps[:1], [[[3], [3]]])
        self.assertIn(4, hatched)
        self.assertEqual(assembly, [4, 4])

    def test_high_market_sacrifices_when_other_mana_keeps_the_gate(self):
        # G3, the other side. Three Forests by turn 3, High Market turn 4 with
        # Probe Finisher One ({1}, a one-piece line) drawn: two Forests pay
        # the Egg activation; the third Forest keeps the line, so High Market
        # sacrifices the Egg (a hatch on turn 4) and the line is ready.
        line = dict(ManaRoundThreeEngineTests.LINE, pieces=["Probe Finisher One"], cards=["Probe Finisher One"])
        by_turn, hatched, _, _, _ = ManaRoundThreeEngineTests()._hatch(
            ["Forest", "Forest", "High Market", "Bear 16", "Bear 17", "Bear 18", "Bear 19"],
            library_extra=("Probe Finisher One", "Bear 15", "Forest", "Bear 14"), win_conditions=[line])
        self.assertEqual(hatched[:1], [4])
        self.assertEqual(self._series(by_turn, "comboLethal", 4), [0, 0, 0, 1])

    def test_halo_fountain_needs_a_tapped_creature_not_one_that_just_entered(self):
        # Fix 5. stampede-acres' config. Plains turns 1-3 (Halo Fountain turn
        # 3), Dryad Arbor turn 4: it enters untapped (summoning sick) and is
        # never tapped, so Halo has no tapped creature to untap: no Citizen.
        with patch.dict(CARDS, R3_PROBES):
            damage, _ = TokenMakerGoldfishTests()._run(
                ["Halo Fountain", "Plains", "Plains", "Plains", "Dryad Arbor", "Zero Trinket", "Zero Trinket"],
                ["Zero Trinket"] * 92, colors=("W", "G"))
        self.assertEqual(damage, [0] * 10)

    def test_halo_fountain_untaps_the_creature_it_pays_with(self):
        # Fix 5. The round-3 Halo game: on turn 5 Dryad Arbor pays Probe G and
        # Halo's cost untaps it: untapped at the end of turn 5.
        arbor = []
        metrics = exporter.metrics_from_board

        def recording(**kwargs):
            arbor.append(next((p.get("tapped") for p in kwargs["permanents"] if p["name"] == "Dryad Arbor"), None))
            return metrics(**kwargs)

        library = ["Zero Trinket"] * 89 + ["Probe G", "Zero Trinket", "Zero Trinket", "Zero Trinket"]
        with patch.dict(CARDS, R3_PROBES), patch.object(exporter, "metrics_from_board", recording):
            TokenMakerGoldfishTests()._run(["Halo Fountain", "Dryad Arbor", "Plains", "Plains"]
                                           + ["Zero Trinket"] * 3, library, colors=("W", "G"))
        # Turn 3 the Arbor entered; turn 4 it paid for Halo and stays tapped
        # (nothing untapped it); turn 5 it paid for Probe G and Halo untapped it.
        self.assertEqual(arbor[2:5], [False, True, False])

    def test_available_mana_counts_a_land_an_end_of_turn_fetch_puts_untapped(self):
        # Fix 9. Probe Untapped Fetcher ({1}; {1}, {T}, sacrifice: a basic
        # land onto the battlefield untapped) is cast on turn 1. Turn 2 a
        # Forest pays its fetch at the end of the turn, and the Forest it finds
        # enters untapped: its {G} is turn 2's third mana.
        by_turn, _ = self._run(["Forest", "Forest", "Probe Untapped Fetcher"] + ["Probe Nine"] * 4,
                               ["Forest"] * 3 + ["Probe Nine"] * 89, ("G",))
        self.assertEqual(self._series(by_turn, "availableMana"), [1, 3, 3, 3, 3, 3])
        self.assertEqual(self._series(by_turn, "lands"), [1, 3, 3, 3, 3, 3])

    def test_the_one_ring_is_tapped_by_its_draw(self):
        # Fix 2. gandalf-party-guest's draw engine: The One Ring ({4}) on turn
        # 4 draws as it is cast and on turns 5-7 (four activations); each taps
        # it, so Urza could not tap it for {U} those turns. Turn 8 it rests.
        tapped = {}
        by_turn, _ = self._run(["The One Ring"] + ["Island"] * 4 + ["Probe Nine"] * 2, ["Probe Nine"] * 92,
                               ("U",), deck_id="gandalf-party-guest",
                               spy=lambda turn, permanents: tapped.update({turn: next(
                                   (p.get("tapped") for p in permanents if p["name"] == "The One Ring"), None)}))
        self.assertEqual([tapped[t] for t in range(4, 9)], [True, True, True, True, False])


class ManaRoundFourUnitTests(unittest.TestCase):
    """Review round 4 (2026-11-20): Urza's grant, Reflecting Pool, grants to
    lands, records kept for the turn, the reserve, and the payment search;
    CARDS, R3_PROBES and R4_PROBES."""

    ONE = PAY_ONE

    @staticmethod
    def context(names, colours, deck_data=None, deck_id="synthetic-r4"):
        return exporter.build_goldfish_context(names, deck_data or {"decklist": []},
                                               ManaRoundFourGoldfishTests.cards(), "Probe Commander",
                                               list(colours), deck_id)

    def test_urza_grants_no_blue_to_a_line_member_an_artifact_creature_or_a_tapped_artifact(self):
        # Fix 2. Urza, Zero Trinket, Probe Scepter (a combo line names it),
        # Nevinyrral's Disk (enters tapped), Probe Golem (an artifact
        # creature) and The One Ring (its draw taps it as it is cast). The
        # turn they enter: Urza's {U} and the Trinket's only. Next turn, all
        # untapped: the Disk and the Ring too, never the Scepter or the Golem.
        names = ["Urza, Lord High Artificer", "Zero Trinket", "Probe Scepter", "Nevinyrral's Disk", "Probe Golem",
                 "The One Ring"]
        deck_data = {"decklist": [], "winConditions": [
            {"title": "Probe line", "kind": "combo", "pieces": ["Probe Scepter", "Probe Finisher"],
             "cards": ["Probe Scepter", "Probe Finisher"], "description": ""}]}
        context = self.context(names + ["Probe Finisher"], ["U"], deck_data)
        profiles = context["profiles"]
        permanents, lands = [], []
        for name in names:
            exporter.resolve_cast_effects(name, profiles[name], 1, exporter.GoldfishManaPool([]), [], [],
                                          permanents, lands, profiles, ["U"])
        self.assertEqual(sorted(a.source["name"] for a in exporter.board_mana(permanents, 1, profiles)),
                         ["Urza, Lord High Artificer", "Zero Trinket"])
        for record in permanents:
            record["tapped"] = False  # the next untap step
        self.assertEqual(sorted(a.source["name"] for a in exporter.board_mana(permanents, 2, profiles)),
                         ["Nevinyrral's Disk", "The One Ring", "Urza, Lord High Artificer", "Zero Trinket"])

    def test_reflecting_pool_reads_what_each_ability_would_make_on_this_board(self):
        # Fix 3. The Mycosynth Gardens' "{1}, {T}: Add one mana of any color"
        # counts before its {1} is netted: Reflecting Pool makes {C} or the
        # commander's colours. Cabal Coffers ("{2}, {T}: Add {B} for each
        # Swamp") could produce black only with a Swamp out.
        context = self.context(["Reflecting Pool", "The Mycosynth Gardens", "Cabal Coffers", "Swamp"], ["B", "R"])
        profiles = context["profiles"]
        permanents, lands = [], []
        exporter.put_land_onto_battlefield("The Mycosynth Gardens", 1, False, permanents, lands, profiles, ["B", "R"])
        pool_land = exporter.put_land_onto_battlefield("Reflecting Pool", 1, False, permanents, lands, profiles,
                                                       ["B", "R"])
        self.assertEqual(mana_letters(exporter.record_atoms(pool_land, permanents, profiles, 2)), ["BRC"])
        permanents, lands = [], []
        coffers = exporter.put_land_onto_battlefield("Cabal Coffers", 1, False, permanents, lands, profiles,
                                                     ["B", "R"])
        self.assertEqual(exporter.land_could_produce(coffers, permanents, profiles, 2), frozenset())
        exporter.put_land_onto_battlefield("Swamp", 1, False, permanents, lands, profiles, ["B", "R"])
        self.assertEqual(exporter.land_could_produce(coffers, permanents, profiles, 2), frozenset("B"))

    def test_a_land_grant_reaches_a_land_with_no_mana_ability(self):
        # Fix 4. Maze of Ith has no mana ability: beside Urborg it makes {B}
        # (tapping it), beside Chromatic Lantern any colour (the commander's:
        # {B} or {G}).
        context = self.context(["Maze of Ith", "Urborg, Tomb of Yawgmoth", "Chromatic Lantern"], ["B", "G"])
        profiles = context["profiles"]
        for grant in ("Urborg, Tomb of Yawgmoth", "Chromatic Lantern"):
            with self.subTest(grant=grant):
                permanents, lands = [], []
                exporter.put_land_onto_battlefield("Maze of Ith", 1, False, permanents, lands, profiles, ["B", "G"])
                if grant == "Chromatic Lantern":
                    exporter.resolve_cast_effects(grant, profiles[grant], 1, exporter.GoldfishManaPool([]), [], [],
                                                  permanents, lands, profiles, ["B", "G"])
                else:
                    exporter.put_land_onto_battlefield(grant, 1, False, permanents, lands, profiles, ["B", "G"])
                maze = [(mana_letters([a]), a.taps) for a in exporter.board_mana(permanents, 2, profiles)
                        if a.source["name"] == "Maze of Ith"]
                self.assertEqual(maze, [(["B"], True)] if grant.startswith("Urborg") else [(["BG"], True)])

    def test_a_record_that_leaves_keeps_its_id_for_the_turn(self):
        # Fix 7. Lotus Petal pays and is sacrificed; with every other reference
        # to it gone, the pool the payment left still holds the record its
        # tapped set names, so no record made later that turn reuses its id.
        context = self.context(["Lotus Petal", "Wastes"], ["C"])
        profiles = context["profiles"]
        permanents, lands = [], []
        exporter.resolve_cast_effects("Lotus Petal", profiles["Lotus Petal"], 1, exporter.GoldfishManaPool([]),
                                      [], [], permanents, lands, profiles, ["C"])
        pool = exporter.GoldfishManaPool(turn=1)
        exporter.refresh_pool(pool, permanents, profiles, 1)
        left = exporter.spend_mana(pool, self.ONE, permanents, lands, profiles)
        self.assertEqual(permanents, [])
        stale = set(left.tapped)
        del pool
        gc.collect()  # the payment search's closures hold the pool's mana in cycles
        self.assertEqual({sid: left.records.get(sid, {}).get("name") for sid in stale},
                         {sid: "Lotus Petal" for sid in stale})
        later = [{"name": f"Probe {i}", "kind": "spell", "manaAtoms": []} for i in range(5000)]
        self.assertEqual([r["name"] for r in later if id(r) in stale], [])

    def test_a_fetch_reserves_its_mana_only_when_it_can_net_a_land(self):
        # Fix 8. Myriad Landscape fetches two basics that share a type: with
        # one Forest in the deck it would only swap itself for it, so its mana
        # is not held back for the fetch; with two it is.
        for forests, reserved in ((1, False), (2, True)):
            with self.subTest(forests=forests):
                profiles = self.context(["Myriad Landscape"] + ["Forest"] * forests, ["G"])["profiles"]
                self.assertEqual(bool(profiles["Myriad Landscape"].get("manaReserve")), reserved)

    def test_the_payment_search_has_no_cap(self):
        # Review round 4: one colourless source and fourteen two-colour ones
        # (all ten pairs of WUBRG, and a second W/U, W/B and W/R). {7} keeping
        # {C}: every payment with the colourless source (the narrowest) comes
        # first; the first one that keeps {C} is past the 600th.
        pairs = ["".join(p) for p in itertools.combinations("WUBRG", 2)] + ["WU", "WB", "WR"]
        atoms = [exporter.tag_atoms([frozenset("C")], {"name": "Wastes"}, 0, taps=True)[0]]
        atoms += [exporter.tag_atoms([frozenset(p)], {"name": f"Dual {i}"}, 0, taps=True)[0]
                  for i, p in enumerate(pairs)]
        got = exporter.GoldfishManaPool(atoms).pay(PayTruth.cost(generic=7), [[PayTruth.cost(C=1)]])
        self.assertIsNotNone(got)
        self.assertEqual((got.total, got.can_cast(PayTruth.cost(C=1))), (7, True))

    def test_interchangeable_mana_taps_the_fewest_permanents(self):
        # {1} keeping {G}: the preferred payment (the Forest, listed first)
        # breaks it; of the {U} that keep it, Urza's (his Construct is tapped,
        # not a permanent the turn reads) is taken before the Island's, which
        # would tap the Island.
        forest, island, urza = {"name": "Forest"}, {"name": "Island"}, {"name": "Urza"}
        atoms = (exporter.tag_atoms([frozenset("G")], forest, 0, taps=True)
                 + exporter.tag_atoms([frozenset("U")], island, 0, taps=True)
                 + exporter.tag_atoms([frozenset("U")], urza, 0, taps=False))
        got = exporter.GoldfishManaPool(atoms).pay(self.ONE, [[PayTruth.cost(G=1)]])
        self.assertEqual((sorted(a.source["name"] for a in got.sources), got.tapping), (["Forest", "Island"], set()))


class ManaRoundFourParserTests(unittest.TestCase):
    """Review round 4 (2026-11-20): land searches read as a whole clause or
    refused, and a cost that gives up five lands. Texts from the local
    Scryfall mirror (2026-11-20) unless made up."""

    REFUSED = [
        ("Slimefoot's Survey", "Sorcery", "Domain — Search your library for up to two land cards that each have a "
         "basic land type, put them onto the battlefield tapped, then shuffle.", "{4}{G}", "its land search"),
        ("Reach the Horizon", "Sorcery", "Search your library for up to two basic land cards and/or Town cards "
         "with different names, put them onto the battlefield tapped, then shuffle.", "{3}{G}", "its land search"),
        ("Gaea's Balance", "Sorcery", "As an additional cost to cast this spell, sacrifice five lands.\nSearch "
         "your library for a land card of each basic land type, put those cards onto the battlefield, then "
         "shuffle.", "{3}{G}", "its land search"),
        ("Genesis Device", "Legendary Artifact", "When Genesis Device enters, search your library for a basic land "
         "card or Planet card, put it onto the battlefield tapped, then shuffle.", "{2}{G}", "its land search"),
        # Made up: a plain search behind a cost of five lands.
        ("Probe Five Land Ramp", "Sorcery", "As an additional cost to cast this spell, sacrifice five lands.\n"
         "Search your library for a basic land card, put it onto the battlefield, then shuffle.", "{1}{G}",
         "the land it gives up"),
    ]

    def test_wordings_no_rule_reads_stop_the_export_with_their_reason(self):
        for name, type_line, text, cost, reason in self.REFUSED:
            with self.subTest(card=name):
                with self.assertRaisesRegex(ValueError, re.escape(reason)):
                    exporter.build_goldfish_profile(name, ManaRoundThreeParserTests.card(type_line, text, cost),
                                                    set(), ["R", "G", "W"], "Other")

    def test_two_named_basic_types_are_read_as_two_lands(self):
        # Yasharn: "a basic Forest card and a basic Plains card", to the hand.
        meta = dict(R4_PROBES["Yasharn, Implacable Earth"])
        profile = exporter.build_goldfish_profile("Yasharn, Implacable Earth", meta, set(), ["G", "W"], "Other")
        ramp = profile["landRamp"]
        self.assertEqual((ramp["count"], ramp["toHand"], ramp["perType"], ramp["basicOnly"]),
                         (0, 2, ["Forest", "Plains"], True))


R5_PROBES = {
    # The local Scryfall mirror (2026-11-20).
    "Noble's Purse": {"type_line": "Artifact", "mana_cost": "{2}", "cmc": 2.0, "colors": [], "oracle_text": (
        "This artifact enters tapped and with three coin counters on it.\n{T}, Remove a coin counter from this "
        "artifact: Create a Treasure token. (It's an artifact with \"{T}, Sacrifice this token: Add one mana of "
        "any color.\")")},
    "Embodiment of Spring": {"type_line": "Creature — Elemental", "mana_cost": "{U}", "cmc": 1.0, "colors": ["U"],
                             "power": "0", "oracle_text": (
        "{1}{G}, {T}, Sacrifice this creature: Search your library for a basic land card, put it onto the "
        "battlefield tapped, then shuffle.")},
    "Viewpoint Synchronization": {"type_line": "Sorcery", "mana_cost": "{4}{G}", "cmc": 5.0, "colors": ["G"],
                                  "oracle_text": (
        "Freerunning {2}{G} (You may cast this spell for its freerunning cost if you dealt combat damage to a "
        "player this turn with an Assassin or commander.)\nSearch your library for up to three basic land cards "
        "and reveal them. Put two of them onto the battlefield tapped and the other into your hand, then "
        "shuffle.")},
    "Shard Convergence": {"type_line": "Sorcery", "mana_cost": "{3}{G}", "cmc": 4.0, "colors": ["G"],
                          "oracle_text": (
        "Search your library for a Plains card, an Island card, a Swamp card, and a Mountain card. Reveal those "
        "cards, put them into your hand, then shuffle.")},
    "Embermouth Sentinel": {"type_line": "Artifact Creature — Chimera", "mana_cost": "{2}", "cmc": 2.0,
                            "colors": [], "power": "2", "oracle_text": (
        "When this creature enters, you may search your library for a basic land card, reveal it, then shuffle "
        "and put that card on top. If you control a Dragon, put that card onto the battlefield tapped "
        "instead.")},
    "Bojuka Bog": {"type_line": "Land", "mana_cost": "", "cmc": 0.0, "colors": [], "oracle_text": (
        "This land enters tapped.\nWhen this land enters, exile target player's graveyard.\n{T}: Add {B}.")},
    "Hour of Promise": {"type_line": "Sorcery", "mana_cost": "{4}{G}", "cmc": 5.0, "colors": ["G"], "oracle_text": (
        "Search your library for up to two land cards, put them onto the battlefield tapped, then shuffle. Then "
        "if you control three or more Deserts, create two 2/2 black Zombie creature tokens.")},
    "Skullclamp": {"type_line": "Artifact — Equipment", "mana_cost": "{1}", "cmc": 1.0, "colors": [],
                   "oracle_text": ("Equipped creature gets +1/-1.\nWhenever equipped creature dies, draw two "
                                   "cards.\nEquip {1}")},
    # Made up: a rock that enters tapped with a rider, an Equipment a combo
    # line names (no {T} ability), a land creature Forest, a land that makes
    # {W}{W}, three tutors (an instant-only and two sorcery-only ones by their
    # deck entries, one of them blue), an instant and a sorcery two assembly
    # lines name, and a {U} sorcery with no effect.
    "Probe Purse Rock": {"type_line": "Artifact", "mana_cost": "{2}", "cmc": 2.0, "colors": [], "oracle_text": (
        "This artifact enters tapped and with a charge counter on it.\n{T}: Add {C}.")},
    "Probe Sword": {"type_line": "Artifact — Equipment", "mana_cost": "{3}", "cmc": 3.0, "colors": [],
                    "oracle_text": "Equipped creature gets +2/+2.\nEquip {2}"},
    "Probe Treefolk Land": {"type_line": "Land Creature — Forest Treefolk", "mana_cost": "", "cmc": 0.0,
                            "colors": ["G"], "power": "1", "oracle_text": ""},
    "Probe Plains Pair": {"type_line": "Land", "mana_cost": "", "cmc": 0.0, "colors": [],
                          "oracle_text": "{T}: Add {W}{W}."},
    "Probe Tutor W": {"type_line": "Instant", "mana_cost": "{W}", "cmc": 1.0, "oracle_text": "", "colors": ["W"]},
    "Probe Tutor 1W": {"type_line": "Instant", "mana_cost": "{1}{W}", "cmc": 2.0, "oracle_text": "",
                       "colors": ["W"]},
    "Probe Tutor 1U": {"type_line": "Instant", "mana_cost": "{1}{U}", "cmc": 2.0, "oracle_text": "",
                       "colors": ["U"]},
    "Probe Line Sorcery": {"type_line": "Sorcery", "mana_cost": "{9}", "cmc": 9.0, "oracle_text": "", "colors": []},
    "Probe U Drop": {"type_line": "Sorcery", "mana_cost": "{U}", "cmc": 1.0, "oracle_text": "", "colors": ["U"]},
    # The local Scryfall mirror (2026-11-17 snapshot), read 2026-11-21.
    "Sylvan Scrying": {"type_line": "Sorcery", "mana_cost": "{1}{G}", "cmc": 2.0, "colors": ["G"], "oracle_text": (
        "Search your library for a land card, reveal it, put it into your hand, then shuffle.")},
    "Tempt with Discovery": {"type_line": "Sorcery", "mana_cost": "{3}{G}", "cmc": 4.0, "colors": ["G"],
                             "oracle_text": (
        "Tempting offer — Search your library for a land card and put it onto the battlefield. Each opponent "
        "may search their library for a land card and put it onto the battlefield. For each opponent who searches "
        "a library this way, search your library for a land card and put it onto the battlefield. Then each "
        "player who searched a library this way shuffles.")},
    # Made up: Embodiment of Spring's fetch on a creature with vigilance.
    "Probe Vigilant Fetcher": {"type_line": "Creature — Elemental", "mana_cost": "{U}", "cmc": 1.0, "colors": ["U"],
                               "power": "0", "oracle_text": (
        "Vigilance\n{1}{G}, {T}, Sacrifice this creature: Search your library for a basic land card, put it onto "
        "the battlefield tapped, then shuffle.")},
    # Made up: a Pathway whose front face is a Swamp, so a fetch land finds it.
    "Probe Swamp Pathway": {"type_line": "Land — Swamp // Land", "mana_cost": "", "cmc": 0.0, "colors": [],
                            "oracle_text": "({T}: Add {B}.)", "layout": "modal_dfc",
                            "back_face": {"type_line": "Land", "oracle_text": "{T}: Add {W}."}},
}


class ManaRoundFiveGoldfishTests(unittest.TestCase):
    """Review round 5 (2026-11-20) through the goldfish turn loop; CARDS and
    the R3, R4 and R5 probes."""

    _series = staticmethod(ManaModelGoldfishTests._series)

    @staticmethod
    def cards() -> dict:
        return dict(CARDS, **R3_PROBES, **R4_PROBES, **R5_PROBES)

    def assault_game(self, hand):
        """broodfire-hatchery's config with the CombatModifierGoldfishTests
        cards (Atla costs {1}), Ashnod's Altar, Skullclamp and High Market:
        (by_turn, the turns of each hatch)."""
        metadata = CombatModifierGoldfishTests()._metadata()
        commander = CombatModifierGoldfishTests.COMMANDER
        metadata[commander] = dict(metadata[commander], mana_cost="{1}", cmc=1)
        metadata["Ashnod's Altar"] = CastPriorityHoldTests()._hatch_metadata()["Ashnod's Altar"]
        metadata["High Market"] = CARDS["High Market"]
        for name in ("Viridian Crystal",):
            metadata[name] = dict(R4_PROBES[name], name=name)
        metadata["Skullclamp"] = dict(R5_PROBES["Skullclamp"], name="Skullclamp")
        library = list(CombatModifierGoldfishTests.FILLERS)
        decklist = list(hand) + library
        context = exporter.build_goldfish_context(decklist, {"decklist": [{"name": n} for n in decklist]},
                                                  metadata, commander, ["G"], CombatModifierGoldfishTests.DECK_ID)
        hatched = []
        hatch = exporter.hatch_from_library

        def recording(turn, *args, **kwargs):  # an Egg died: one was made
            hatched.append(turn)
            return hatch(turn, *args, **kwargs)

        with patch.object(exporter, "commander_mulligan_goldfish", lambda *_: (list(library), list(hand))), \
                patch.object(exporter, "hatch_from_library", recording):
            by_turn, _ = exporter.simulate_goldfish_game(decklist, context, 6)
        return by_turn, hatched

    BASE = ["Ruby Crystal", "Ruby Crystal", "Aggravated Assault", "Attacker A"]

    def test_skullclamps_equip_keeps_a_held_assault(self):
        # Item 3. Turn 2: seven mana, two red (two Forests, two Ruby
        # Crystals, three Viridian Crystals). The Egg activation keeps
        # Assault's {3}{R}{R}; Skullclamp's {1} equip would take its last
        # mana, so it waits and Ashnod's Altar eats the Egg; Assault is paid:
        # two combats, 3 damage (Attacker A, then Attacker A and Atla).
        by_turn, hatched = self.assault_game(["Forest", "Forest"] + self.BASE + ["Viridian Crystal"] * 3
                                             + ["Ashnod's Altar", "Skullclamp"])
        self.assertEqual((hatched[:1], by_turn[2]["combat"]), ([2], 3))

    def test_high_markets_tap_keeps_a_held_assault(self):
        # Item 3. High Market the only land; turn 2: its {C}, two red, four
        # green. The Egg activation keeps Assault; High Market's {T} would take
        # the {C} Assault needs, so it sacrifices nothing; Assault is paid:
        # 3 damage, no hatch on turn 2.
        by_turn, hatched = self.assault_game(["High Market"] + self.BASE + ["Viridian Crystal"] * 4)
        self.assertEqual((2 in hatched, by_turn[2]["combat"]), (False, 3))

    def test_an_unaffordable_assault_holds_nothing(self):
        # Item 3. Assault out but no red mana: the Egg activation is made on
        # turn 2 (two Forests) and hatched. Keeping an Assault the pool cannot
        # pay, no Egg would ever be made.
        _, hatched = self.assault_game(["Forest", "Forest", "Aggravated Assault", "Attacker A", "Ashnod's Altar"])
        self.assertEqual(hatched[:1], [2])

    def _two_gate_game(self, hand: list, library: list, roles: dict) -> tuple:
        """Two assembly lines on the hatch engine's deck: Probe Line A1 + B1
        and Probe Line A2 + Probe Line Sorcery, the tutors in ``roles`` (name
        -> tutor_targets) to fill them. Returns (casts by turn, hatch turns,
        assembly turns)."""
        metadata = CastPriorityHoldTests()._hatch_metadata()
        commander = CastPriorityHoldTests.HATCH_COMMANDER
        metadata.update({name: R4_PROBES[name] for name in ("Probe Line A1", "Probe Line B1", "Probe Line A2")})
        metadata.update({name: R5_PROBES[name] for name in ("Probe Tutor W", "Probe Tutor 1W", "Probe Tutor 1U",
                                                           "Probe Plains Pair", "Probe Line Sorcery", "Probe U Drop")})
        metadata["Island"] = CARDS["Island"]
        decklist = hand + library
        deck_data = {"decklist": [dict({"name": n, "primary_role": "tutor", "tutor_targets": roles[n]}
                                       if n in roles else {"name": n}) for n in decklist]}
        combos = {CastPriorityHoldTests.HATCH_DECK_ID: [
            {"name": "Probe line 1", "pieces": ["Probe Line A1", "Probe Line B1"]},
            {"name": "Probe line 2", "pieces": ["Probe Line A2", "Probe Line Sorcery"]}]}
        with patch.dict(exporter.KEY_COMBOS, combos):
            context = exporter.build_goldfish_context(decklist, deck_data, metadata, commander, ["G"],
                                                      CastPriorityHoldTests.HATCH_DECK_ID)
        casts, hatched = defaultdict(list), []
        resolve, hatch = exporter.resolve_cast_effects, exporter.hatch_from_library

        def recording_resolve(name, profile, turn, *args, **kwargs):
            casts[turn].append(name)
            return resolve(name, profile, turn, *args, **kwargs)

        def recording_hatch(turn, *args, **kwargs):
            hatched.append(turn)
            return hatch(turn, *args, **kwargs)

        with patch.object(exporter, "commander_mulligan_goldfish", lambda *_: (list(library), list(hand))), \
                patch.object(exporter, "resolve_cast_effects", recording_resolve), \
                patch.object(exporter, "hatch_from_library", recording_hatch):
            _, assembly = exporter.simulate_goldfish_game(decklist, context, 6)
        return casts, hatched, assembly

    def test_each_gate_is_kept_with_the_activation_by_its_own_colours(self):
        # Item 4. Two assembly lines: Probe Tutor W ({W}, instants only) can
        # fill the first, Probe Tutor 1W ({1}{W}, sorceries only) the second.
        # No white until Probe Plains Pair ({W}{W}) on turn 4: five mana
        # (three Forests and {W}{W}), the Egg activation ({2}) held: the
        # gates are kept as {2}{W} and {3}{W}. Two Drop 0 ({2}) would leave
        # three, which keeps the first but not the second: it waits; the Egg
        # is made and hatched, and both lines are assembled on turn 4.
        hand = ["Forest"] * 3 + ["Probe Plains Pair", "Ashnod's Altar", "Two Drop 0", "Probe Line A1",
                                 "Probe Line A2", "Probe Tutor W", "Probe Tutor 1W"]
        library = (["Probe Line B1", "Probe Line Sorcery"] + ["Forest"] * 6 + [f"Bear {i}" for i in range(20)])
        casts, hatched, assembly = self._two_gate_game(
            hand, library, {"Probe Tutor W": ["instant"], "Probe Tutor 1W": ["sorcery"]})
        self.assertNotIn("Two Drop 0", casts[4])
        self.assertIn(4, hatched)
        self.assertEqual(assembly, [4, 4])

    def test_each_gate_keeps_its_own_coloured_pips(self):
        # Review round 6, item c. The first line's tutor is Probe Tutor W
        # ({W}, instants only), the second's Probe Tutor 1U ({1}{U},
        # sorceries only). Lands: Forest, Forest, Probe Plains Pair ({W}{W}),
        # Island (the only blue source) on turns 1-4; Probe Tutor W is drawn
        # on turn 4, so no gate is reachable before. Turn 4: five mana (G, G,
        # W, W, U), the Egg activation ({2}) held: the gates are kept as
        # {2}{W} and {3}{U}. Probe U Drop ({U}) would take the only blue: it
        # waits (the second gate read with the first gate's pips, {3}{W},
        # would let it be cast); the Egg is made and hatched, both lines are
        # assembled on turn 4, and the U Drop is cast on turn 5.
        hand = ["Forest"] * 2 + ["Probe Plains Pair", "Island", "Ashnod's Altar", "Probe U Drop", "Probe Line A1",
                                 "Probe Line A2", "Probe Tutor 1U"]
        # Draws and hatches take the library's top: turn 1 draws a Bear, turns
        # 2 and 3 each draw a Bear and hatch one, so Probe Tutor W is turn 4's
        # draw.
        library = (["Probe Line B1", "Probe Line Sorcery"] + ["Forest"] * 6 + [f"Bear {i}" for i in range(15)]
                   + ["Probe Tutor W"] + [f"Bear {i}" for i in range(15, 20)])
        casts, hatched, assembly = self._two_gate_game(
            hand, library, {"Probe Tutor W": ["instant"], "Probe Tutor 1U": ["sorcery"]})
        self.assertEqual(("Probe U Drop" in casts[4], "Probe U Drop" in casts[5]), (False, True))
        self.assertIn(4, hatched)
        self.assertEqual(assembly, [4, 4])

    def _run(self, hand, library, colors):
        decklist = hand + library
        context = exporter.build_goldfish_context(decklist, {"decklist": []}, self.cards(), "The Ur-Dragon",
                                                  list(colors), "synthetic-mana")
        with patch.object(exporter, "commander_mulligan_goldfish", return_value=(list(library), list(hand))):
            return exporter.simulate_goldfish_game(decklist, context, 6)

    def test_a_creatures_own_tap_ability_waits_out_the_turn_it_enters(self):
        # Item 6 (round 5) and item d (round 6). Island, Forest, Forest on
        # turns 1-3; turn 3 draws the creature and casts it with the Island,
        # leaving the two Forests. Embodiment of Spring's fetch ({1}{G}, {T})
        # is summoning sick on turn 3 (three lands); on turn 4 the three lands
        # pay it, so it stays out of combat and fetches a Forest (four).
        # Sakura-Tribe Elder's (no {T}) is used on turn 3 (four). No land is
        # drawn after turn 3.
        for creature, lands in (("Embodiment of Spring", [1, 2, 3, 4]), ("Sakura-Tribe Elder", [1, 2, 4, 4])):
            with self.subTest(creature=creature):
                library = ["Forest"] * 3 + ["Probe Nine"] * 87 + [creature, "Probe Nine", "Probe Nine"]
                by_turn, _ = self._run(["Island", "Forest", "Forest"] + ["Probe Nine"] * 4, library, ("G", "U"))
                self.assertEqual(self._series(by_turn, "lands", 4), lands)

    # A fetch creature stays home only when the end of the turn will activate
    # its fetch (X fix round 1, item 6). Each case is (combat, lands) on turn
    # 4 or turn 2: the creature's combat is 1 (mana value 1, no keyword).
    def test_a_fetch_creature_whose_fetch_the_lands_cannot_pay_attacks(self):
        # Three Islands: Embodiment of Spring is cast on turn 3; on turn 4 no
        # green pays {1}{G}, so it attacks and nothing is fetched.
        library = ["Forest"] * 3 + ["Probe Nine"] * 87 + ["Embodiment of Spring", "Probe Nine", "Probe Nine"]
        by_turn, _ = self._run(["Island"] * 3 + ["Probe Nine"] * 4, library, ("G", "U"))
        self.assertEqual((by_turn[4]["combat"], by_turn[4]["lands"]), (1, 3))

    def test_one_shot_mana_does_not_keep_a_fetch_creature_home(self):
        # Turn 1: Forest; a Lotus Petal pays Embodiment of Spring's {U}. Turn
        # 2 draws a second Petal: Forest and Petal would pay {1}{G} now, but
        # the end of the turn pays from lasting mana (the Forest alone), so
        # Embodiment attacks.
        library = ["Forest"] * 3 + ["Probe Nine"] * 87 + ["Lotus Petal", "Probe Nine"]
        by_turn, _ = self._run(["Forest", "Lotus Petal", "Embodiment of Spring"] + ["Probe Nine"] * 4, library,
                               ("G", "U"))
        self.assertEqual((by_turn[2]["combat"], by_turn[2]["lands"]), (1, 1))

    def test_a_vigilant_fetch_creature_attacks_and_fetches(self):
        # Probe Vigilant Fetcher (Embodiment of Spring's fetch with
        # vigilance), cast on turn 3 with the Island: on turn 4 it attacks
        # untapped, then the Forests pay its fetch.
        library = ["Forest"] * 3 + ["Probe Nine"] * 87 + ["Probe Vigilant Fetcher", "Probe Nine", "Probe Nine"]
        by_turn, _ = self._run(["Island", "Forest", "Forest"] + ["Probe Nine"] * 4, library, ("G", "U"))
        self.assertEqual((by_turn[4]["combat"], by_turn[4]["lands"]), (1, 4))

    def test_a_fetch_creature_attacks_when_a_held_gate_needs_the_mana(self):
        # Island, Forest, Forest; Embodiment of Spring cast on turn 3. Turn 4
        # draws Probe Gate Instant ({2}), the one piece of a combo line: the
        # three lands pay the gate or the {1}{G} fetch, not both, so the
        # gate's mana is held, Embodiment attacks, and the gate fires.
        hand = ["Island", "Forest", "Forest"] + ["Probe Nine"] * 4
        library = ["Forest"] * 3 + ["Probe Nine"] * 86 + ["Probe Gate Instant", "Embodiment of Spring",
                                                           "Probe Nine", "Probe Nine"]
        decklist = hand + library
        cards = dict(self.cards(), **{"Probe Gate Instant": {
            "type_line": "Instant", "mana_cost": "{2}", "cmc": 2.0, "oracle_text": "", "colors": []}})
        deck_data = {"decklist": [], "winConditions": [
            {"title": "Probe gate", "kind": "combo", "pieces": ["Probe Gate Instant"]}]}
        context = exporter.build_goldfish_context(decklist, deck_data, cards, "The Ur-Dragon", ["G", "U"],
                                                  "synthetic-mana")
        with patch.object(exporter, "commander_mulligan_goldfish", return_value=(list(library), list(hand))):
            by_turn, _ = exporter.simulate_goldfish_game(decklist, context, 6)
        self.assertEqual((by_turn[3]["comboLethal"], by_turn[4]["comboLethal"], by_turn[4]["combat"],
                          by_turn[4]["lands"]), (0, 1, 1, 3))

    def test_a_mana_creature_the_fetch_needs_stays_home_with_the_fetcher(self):
        # Turn 1: Island; a Lotus Petal pays Llanowar Elves' {G}, the Island
        # Embodiment of Spring's {U}. Turn 2, no land: the Island and the
        # Elves pay {1}{G}, so Embodiment stays home; the Elves would take
        # the only lasting green to combat, so they stay home too, and the
        # fetch finds a Forest (two lands, no combat). A second Lotus Petal
        # drawn on turn 2 changes nothing: its one-shot mana is not what the
        # end of the turn pays the fetch with.
        for drawn in ("Probe Nine", "Lotus Petal"):
            with self.subTest(drawn=drawn):
                library = ["Forest"] * 3 + ["Probe Nine"] * 87 + [drawn, "Probe Nine"]
                by_turn, _ = self._run(["Island", "Lotus Petal", "Llanowar Elves", "Embodiment of Spring"]
                                       + ["Probe Nine"] * 3, library, ("G", "U"))
                self.assertEqual((by_turn[2]["combat"], by_turn[2]["lands"]), (0, 2))


class ManaRoundFiveUnitTests(unittest.TestCase):
    """Review round 5 (2026-11-20): entering tapped with a rider, Urza and
    line members, land searches (library faces, entry costs, the land chosen);
    CARDS and the R3, R4 and R5 probes."""

    @staticmethod
    def context(names, colours, deck_data=None):
        return exporter.build_goldfish_context(names, deck_data or {"decklist": []},
                                               ManaRoundFiveGoldfishTests.cards(), "Probe Commander",
                                               list(colours), "synthetic-r5")

    def test_entering_tapped_with_a_rider_is_entering_tapped(self):
        # Item 5. Noble's Purse ("enters tapped and with three coin
        # counters"): tapped as it enters, so Urza's grant passes it by; Probe
        # Purse Rock (the same rider, {T}: Add {C}) makes its mana from the
        # next turn.
        context = self.context(["Urza, Lord High Artificer", "Noble's Purse", "Probe Purse Rock"], ["U"])
        profiles = context["profiles"]
        self.assertEqual((profiles["Noble's Purse"]["entersTapped"], profiles["Probe Purse Rock"]["entersTapped"],
                          profiles["Probe Purse Rock"]["manaSourceDelay"]), (True, True, 1))
        permanents = []
        for name in ("Urza, Lord High Artificer", "Noble's Purse"):
            exporter.resolve_cast_effects(name, profiles[name], 1, exporter.GoldfishManaPool([]), [], [],
                                          permanents, [], profiles, ["U"])
        self.assertEqual([a.source["name"] for a in exporter.board_mana(permanents, 1, profiles)],
                         ["Urza, Lord High Artificer"])

    def test_urza_taps_a_line_member_its_line_does_not_need_untapped(self):
        # Item 10. A combo line names Probe Scepter ({2}, {T}: an ability of
        # its own with {T}) and Probe Sword (an Equipment, no {T} ability):
        # Urza never taps the Scepter for {U}; the Sword he does.
        deck_data = {"decklist": [], "winConditions": [
            {"title": "Probe line", "kind": "combo", "pieces": ["Probe Scepter", "Probe Sword", "Probe Finisher"],
             "cards": ["Probe Scepter", "Probe Sword", "Probe Finisher"], "description": ""}]}
        names = ["Urza, Lord High Artificer", "Probe Scepter", "Probe Sword"]
        profiles = self.context(names + ["Probe Finisher"], ["U"], deck_data)["profiles"]
        permanents = []
        for name in names:
            exporter.resolve_cast_effects(name, profiles[name], 1, exporter.GoldfishManaPool([]), [], [],
                                          permanents, [], profiles, ["U"])
        self.assertEqual(sorted(a.source["name"] for a in exporter.board_mana(permanents, 1, profiles)),
                         ["Probe Sword", "Urza, Lord High Artificer"])

    def test_a_search_reads_a_card_as_it_is_in_the_library(self):
        # Item 8. "Search your library for a land card": Hagra Mauling // Hagra
        # Broodpit is an instant in the library, so Bojuka Bog is found.
        profiles = self.context(["Hagra Mauling // Hagra Broodpit", "Bojuka Bog"], ["B", "G"])["profiles"]
        search = {"count": 1, "toHand": 0, "basicOnly": False, "allowedSubtypes": set(), "perType": [],
                  "sharedType": False, "entersTapped": False}
        found = exporter.select_ramp_targets(["Hagra Mauling // Hagra Broodpit", "Bojuka Bog"], profiles,
                                             ["B", "G"], [], [], search, 1, to_hand=False)
        self.assertEqual(found, ["Bojuka Bog"])

    def test_a_searched_land_pays_its_own_entry_cost(self):
        # Item 9. Five Forests out; Hour of Promise finds a Forest and Simic
        # Growth Chamber, which returns a land to the hand as it enters: six
        # lands on the battlefield and one in the hand.
        names = ["Hour of Promise", "Forest", "Simic Growth Chamber"]
        profiles = self.context(names, ["G", "U"])["profiles"]
        permanents, lands, hand = [], [], []
        for _ in range(5):
            exporter.put_land_onto_battlefield("Forest", 1, False, permanents, lands, profiles, ["G", "U"])
        pool = exporter.GoldfishManaPool(turn=2)
        exporter.refresh_pool(pool, permanents, profiles, 2)
        exporter.resolve_cast_effects("Hour of Promise", profiles["Hour of Promise"], 2, pool,
                                      ["Forest", "Simic Growth Chamber"], hand, permanents, lands, profiles,
                                      ["G", "U"])
        self.assertEqual((sum(1 for p in permanents if p["kind"] == "land"), hand), (6, ["Forest"]))

    # Searched lands (mana-model review round 6, X fix round 1). Tempt with
    # Discovery puts one land card onto the battlefield untapped (the
    # opponents' offer is not modelled); Sylvan Scrying puts one into the
    # hand; Hour of Promise puts lands in tapped.
    def search_game(self, names, colours, lands_out=()):
        """(profiles, permanents, battlefield lands) with ``lands_out`` played."""
        profiles = self.context(list(names) + ["Tempt with Discovery", "Sylvan Scrying", "Hour of Promise"],
                                colours)["profiles"]
        permanents, lands = [], []
        for land in lands_out:
            exporter.put_land_onto_battlefield(land, 1, False, permanents, lands, profiles, list(colours))
        return profiles, permanents, lands

    def test_a_land_a_search_puts_onto_the_battlefield_enters_front_face_up(self):
        # A Plains out, commander W and B: played, Brightclimb Pathway would
        # enter as its back face ({B}, the missing colour); Tempt with
        # Discovery puts it onto the battlefield front face up, {W}.
        profiles, permanents, lands = self.search_game(["Brightclimb Pathway", "Plains"], ["W", "B"], ["Plains"])
        exporter.fetch_lands(profiles["Tempt with Discovery"]["landRamp"], 1, 2, exporter.GoldfishManaPool(turn=2),
                             ["Brightclimb Pathway"], [], permanents, lands, profiles, ["W", "B"])
        self.assertEqual((permanents[-1]["name"], mana_letters(permanents[-1]["manaAtoms"])),
                         ("Brightclimb Pathway", ["W"]))

    def test_a_searched_snarl_reveals_from_the_hand(self):
        # Shineshadow Snarl enters untapped when the hand holds a Plains or
        # Swamp card: a Swamp in hand, untapped; an Island, tapped.
        for hand, tapped in ((["Swamp"], False), (["Island"], True)):
            with self.subTest(hand=hand):
                profiles, permanents, lands = self.search_game(["Shineshadow Snarl", "Swamp", "Island"], ["W", "B"])
                exporter.fetch_lands(profiles["Tempt with Discovery"]["landRamp"], 1, 2,
                                     exporter.GoldfishManaPool(turn=2), ["Shineshadow Snarl"], list(hand),
                                     permanents, lands, profiles, ["W", "B"])
                self.assertEqual((permanents[-1]["name"], permanents[-1]["tapped"]), ("Shineshadow Snarl", tapped))

    def test_a_search_onto_the_battlefield_ranks_a_land_as_it_will_enter(self):
        # Tempt with Discovery, commander W and B, a Plains out. Wastes or
        # Shineshadow Snarl: with a Swamp in hand the Snarl enters untapped
        # and adds B, so it is found; with nothing to reveal it would enter
        # tapped, so the untapped Wastes is. Swamp or Brightclimb Pathway:
        # put onto the battlefield, the Pathway is its front face {W}, which
        # the Plains already makes, so the Swamp, which adds B, is found.
        names = ["Wastes", "Shineshadow Snarl", "Swamp", "Brightclimb Pathway", "Plains"]
        for library, hand, found in ((["Wastes", "Shineshadow Snarl"], ["Swamp"], "Shineshadow Snarl"),
                                     (["Wastes", "Shineshadow Snarl"], [], "Wastes"),
                                     (["Swamp", "Brightclimb Pathway"], [], "Swamp")):
            with self.subTest(library=library, hand=hand):
                profiles, permanents, lands = self.search_game(names, ["W", "B"], ["Plains"])
                exporter.fetch_lands(profiles["Tempt with Discovery"]["landRamp"], 1, 2,
                                     exporter.GoldfishManaPool(turn=2), list(library), list(hand), permanents,
                                     lands, profiles, ["W", "B"])
                self.assertEqual(permanents[-1]["name"], found)

    def test_a_search_into_the_hand_ranks_a_pathway_by_either_face(self):
        # Sylvan Scrying, commander W and B, a Plains out; Swamp or
        # Brightclimb Pathway. The land goes to the hand and is played later,
        # when the Pathway can enter as its {B} face: it adds B and makes both
        # commander colours, so it is found over the Swamp.
        profiles, permanents, lands = self.search_game(["Swamp", "Brightclimb Pathway", "Plains"], ["W", "B"],
                                                       ["Plains"])
        hand = []
        exporter.resolve_cast_effects("Sylvan Scrying", profiles["Sylvan Scrying"], 2,
                                      exporter.GoldfishManaPool(turn=2), ["Swamp", "Brightclimb Pathway"], hand,
                                      permanents, lands, profiles, ["W", "B"])
        self.assertEqual(hand, ["Brightclimb Pathway"])

    def test_a_search_that_puts_lands_in_tapped_ranks_them_as_tapped(self):
        # Hour of Promise (lands put in tapped), one land, commander B and G,
        # a Forest out; Wastes (untapped by its own text) or Bojuka Bog
        # (tapped by its own, {B}). Both enter tapped, so the Bog, which adds
        # the missing B, is found.
        profiles, permanents, lands = self.search_game(["Wastes", "Bojuka Bog", "Forest"], ["B", "G"], ["Forest"])
        exporter.fetch_lands(profiles["Hour of Promise"]["landRamp"], 1, 2, exporter.GoldfishManaPool(turn=2),
                             ["Wastes", "Bojuka Bog"], [], permanents, lands, profiles, ["B", "G"])
        self.assertEqual((permanents[-1]["name"], permanents[-1]["tapped"]), ("Bojuka Bog", True))

    def test_a_fetch_land_puts_a_pathway_onto_the_battlefield_front_face_up(self):
        # Polluted Delta finds Probe Swamp Pathway (a Swamp // Land Pathway:
        # {B} // {W}); commander W and B, a Swamp out. Played, it would enter
        # as its {W} face, the missing colour; found by the crack it enters
        # front face up, {B}, and the land drop scores the Delta by that face.
        profiles, permanents, lands = self.search_game(["Polluted Delta", "Probe Swamp Pathway", "Swamp"],
                                                       ["W", "B"], ["Swamp"])
        score = exporter.land_play_score("Polluted Delta", ["Polluted Delta"], profiles, lands, permanents,
                                         ["W", "B"], ["Probe Swamp Pathway"])
        # (usable this turn, new commander colours, commander colours, colours)
        self.assertEqual(score[:4], (10, 0, 1, 1))
        record = exporter.crack_fetch_land("Polluted Delta", 1, ["Probe Swamp Pathway"], [], permanents, lands,
                                           profiles, ["W", "B"])
        self.assertEqual((record["name"], mana_letters(record["manaAtoms"])), ("Probe Swamp Pathway", ["B"]))

    def test_a_search_chooses_a_land_usable_this_turn_as_a_land_drop_does(self):
        # Item 9. Nature's Lore (a Forest card, onto the battlefield
        # untapped): a plain Forest, not Probe Treefolk Land (a land creature:
        # summoning sick), whose name would win the tie.
        profiles = self.context(["Nature's Lore", "Forest", "Probe Treefolk Land"], ["G"])["profiles"]
        found = exporter.select_ramp_targets(["Probe Treefolk Land", "Forest"], profiles, ["G"], [], [],
                                             profiles["Nature's Lore"]["landRamp"], 1, to_hand=False)
        self.assertEqual(found, ["Forest"])


class ManaRoundFiveParserTests(unittest.TestCase):
    """Review round 5 (2026-11-20): every destination of a land search read,
    or the search refused. Texts from the local Scryfall mirror (2026-11-20)."""

    def test_a_split_between_the_battlefield_and_the_hand_is_read(self):
        profile = exporter.build_goldfish_profile("Viewpoint Synchronization",
                                                  R5_PROBES["Viewpoint Synchronization"], set(), ["G"], "Other")
        ramp = profile["landRamp"]
        self.assertEqual((ramp["count"], ramp["toHand"], ramp["entersTapped"]), (2, 1, True))

    def test_a_list_of_cards_and_a_later_instead_are_refused(self):
        # And a split between the battlefield and the hand in other words
        # (made up: the land put untapped).
        split = {"type_line": "Sorcery", "mana_cost": "{2}{G}", "cmc": 3.0, "colors": ["G"], "oracle_text": (
            "Search your library for up to two basic land cards, put one onto the battlefield and the other into "
            "your hand, then shuffle.")}
        for name, meta in (("Shard Convergence", R5_PROBES["Shard Convergence"]),
                           ("Embermouth Sentinel", R5_PROBES["Embermouth Sentinel"]), ("Probe Split Search", split)):
            with self.subTest(card=name):
                with self.assertRaisesRegex(ValueError, re.escape("its land search")):
                    exporter.build_goldfish_profile(name, meta, set(), ["G"], "Other")


class ManaRoundTwoParserTests(unittest.TestCase):
    """Review round 2 (2026-11-20): wordings the parser refuses rather than
    guess, and the readings that replaced a guess. Texts from the local
    Scryfall mirror (2026-11-20)."""

    REFUSED = [
        ("Harrow", "Instant", "As an additional cost to cast this spell, sacrifice a land.\nSearch your "
         "library for up to two basic land cards, put them onto the battlefield, then shuffle."),
        ("Roiling Regrowth", "Instant", "Sacrifice a land. Search your library for up to two basic land "
         "cards, put them onto the battlefield tapped, then shuffle."),
        ("Crop Rotation", "Instant", "As an additional cost to cast this spell, sacrifice a land.\nSearch "
         "your library for a land card, put that card onto the battlefield, then shuffle."),
        ("Mox Diamond", "Artifact", "If this artifact would enter, you may discard a land card instead. If "
         "you do, put this artifact onto the battlefield. If you don't, put it into its owner's "
         "graveyard.\n{T}: Add one mana of any color."),
        ("Coral Atoll", "Land", "This land enters tapped.\nWhen this land enters, sacrifice it unless you "
         "return an untapped Island you control to its owner's hand.\n{T}: Add {C}{U}."),
        ("Dormant Volcano", "Land", "This land enters tapped.\nWhen this land enters, sacrifice it unless "
         "you return an untapped Mountain you control to its owner's hand.\n{T}: Add {C}{R}."),
        ("Brokers Hideout", "Land", "When this land enters, sacrifice it. When you do, search your library "
         "for a basic Forest, Plains, or Island card, put it onto the battlefield tapped, then shuffle "
         "and you gain 1 life."),
        ("Grasslands", "Land", "This land enters tapped.\n{T}, Sacrifice this land: Search your library "
         "for a Forest or Plains card, put it onto the battlefield, then shuffle."),
        ("Multiversal Passage", "Land", "As this land enters, choose a basic land type. Then you may pay 2 "
         "life. If you don't, it enters tapped.\nThis land is the chosen type."),
        ("Thran Portal", "Land — Gate", "This land enters tapped unless you control two or fewer other "
         "lands.\nAs this land enters, choose a basic land type.\nThis land is the chosen type in addition "
         "to its other types.\nMana abilities of this land cost an additional 1 life to activate."),
        ("Vesuva", "Land", "You may have this land enter tapped as a copy of any land on the battlefield."),
        ("Prismatic Omen", "Enchantment", "Lands you control are every basic land type in addition to their "
         "other types."),
        ("Dryad of the Ilysian Grove", "Enchantment Creature — Nymph Dryad", "You may play an additional "
         "land on each of your turns.\nLands you control are every basic land type in addition to their "
         "other types."),
        ("Crystal Vein", "Land", "{T}: Add {C}.\n{T}, Sacrifice this land: Add {C}{C}."),
        ("Rose, Cutthroat Raider", "Legendary Artifact Creature — Robot", "First strike\nRaid — At end of "
         "combat on your turn, if you attacked this turn, create a Junk token for each opponent you "
         "attacked.\nWhenever you sacrifice a Junk, add {R}."),
        ("Resonating Lute", "Artifact", "Lands you control have \"{T}: Add two mana of any one color. Spend "
         "this mana only to cast instant and sorcery spells.\"\n{T}: Draw a card. Activate only if you "
         "have seven or more cards in your hand."),
        ("Probe Exhaust Rock", "Artifact", "Exhaust — {T}: Add {C}{C}{C}."),
        # A grant to every land of anything but "{T}: Add" one mana.
        ("Probe Double Grant", "Artifact", "Lands you control have \"{T}: Add {C}{C}.\""),
        ("Probe Restricted Grant", "Artifact", "Lands you control have \"{T}: Add one mana of any color. "
         "Spend this mana only to cast creature spells.\""),
        ("Probe Conditional Grant", "Artifact", "Lands you control have \"{T}: Add {G}.\" as long as you "
         "control a Forest."),
        ("Probe Costed Grant", "Artifact", "Lands you control have \"{1}, {T}: Add {G}.\""),
        # R4 refusal paths.
        ("Probe Search Lead", "Creature — Elf", "When this creature enters, if you control a Forest, search "
         "your library for a basic land card, put it onto the battlefield tapped, then shuffle."),
        ("Probe Entry Rule", "Land", "This land enters tapped unless you control a Dragon.\n{T}: Add {R}."),
        ("Probe Land Search", "Land", "{T}, Sacrifice this land: If you control a Forest, search your "
         "library for a basic land card, put it onto the battlefield, then shuffle."),
        ("Probe Lands Taken", "Land", "When this land enters, sacrifice a Forest.\n{T}: Add {G}{G}."),
    ]

    @staticmethod
    def meta(type_line, text, colors=()):
        return {"type_line": type_line, "oracle_text": text, "colors": list(colors),
                "mana_cost": "" if "Land" in type_line.split(" // ")[0] else "{0}",
                "cmc": 0, "power": "1"}

    # The reason each refusal names (review round 4: the refusal, not only
    # that it raised).
    REASONS = {'Harrow': 'the land it gives up', 'Roiling Regrowth': 'the land it gives up', 'Crop Rotation': 'the land it gives up', 'Mox Diamond': 'gives up a land', 'Coral Atoll': 'lands taken as it enters', 'Dormant Volcano': 'lands taken as it enters', 'Brokers Hideout': 'lands taken as it enters', 'Grasslands': "a fetch land's own entry rule", 'Multiversal Passage': 'a type or copy chosen as it enters', 'Thran Portal': 'a type or copy chosen as it enters', 'Vesuva': 'a type or copy chosen as it enters', 'Prismatic Omen': 'Lands you control are every basic land type', 'Dryad of the Ilysian Grove': 'Lands you control are every basic land type', 'Crystal Vein': 'lasting mana or sacrificing it for more', 'Rose, Cutthroat Raider': 'Whenever you sacrifice a Junk, add {R}.', 'Resonating Lute': '{T}: Add two mana of any one color. Spend this mana only', 'Probe Exhaust Rock': 'Exhaust — {T}: Add {C}{C}{C}.', 'Probe Double Grant': '{T}: Add {C}{C}.', 'Probe Restricted Grant': 'Spend this mana only to cast creature spells.', 'Probe Conditional Grant': '{T}: Add {G}.', 'Probe Costed Grant': '{1}, {T}: Add {G}.', 'Probe Search Lead': 'its land search', 'Probe Entry Rule': 'how it enters', 'Probe Land Search': "'search'", 'Probe Lands Taken': 'lands taken as it enters'}

    def test_wordings_no_rule_reads_stop_the_export(self):
        self.assertEqual(sorted(self.REASONS), sorted(name for name, _, _ in self.REFUSED))
        for name, type_line, text in self.REFUSED:
            with self.subTest(card=name):
                with self.assertRaisesRegex(ValueError, re.escape(self.REASONS[name])):
                    exporter.build_goldfish_profile(name, self.meta(type_line, text), set(), ["R", "G", "W"],
                                                    "Other")

    def test_an_opponent_condition_inside_an_ability_is_a_floor(self):
        profile = exporter.build_goldfish_profile(
            "Probe Opponent Rock", self.meta("Artifact", "{T}: If an opponent controls more lands than you, "
                                             "add {C}{C}."), set(), ["G"], "Other")
        self.assertEqual((profile["manaAtoms"], [v for _, v in profile["manaVerdicts"]]),
                         ([], ["condition floor"]))

    def test_an_unknown_land_entry_rule_raises(self):
        with self.assertRaises(ValueError):
            exporter.land_enters_tapped(("probe",), [], [], {}, [])

    def test_readings_that_replaced_a_guess(self):
        # "Two mana in any combination of colors": two mana, each the
        # commander's colours (as "one mana of any color").
        model = exporter.card_mana_model("Probe Combination", self.meta(
            "Artifact", "{T}: Add two mana in any combination of colors."), ["B", "G"])
        self.assertEqual(mana_letters(model["manaAtoms"]), ["BG", "BG"])
        model = exporter.card_mana_model("Probe Named Combination", self.meta(
            "Artifact", "{T}: Add two mana in any combination of {R} and/or {G}."), ["B", "G"])
        self.assertEqual(mana_letters(model["manaAtoms"]), ["RG", "RG"])
        # Nissa's Pilgrimage: one Forest onto the battlefield tapped, the
        # other to the hand (spell mastery's third is a floor).
        ramp = exporter.parse_land_ramp_profile(self.meta(
            "Sorcery", "Search your library for up to two basic Forest cards, reveal those cards, and put "
            "one onto the battlefield tapped and the rest into your hand. Then shuffle.\nSpell mastery — "
            "If there are two or more instant and/or sorcery cards in your graveyard, search your library "
            "for up to three basic Forest cards instead of two."))
        self.assertEqual((ramp["count"], ramp["toHand"], ramp["entersTapped"]), (1, 1, True))
        # Harbinger of the Seas: its type-setting is a named floor, not
        # refused and not applied.
        profile = exporter.build_goldfish_profile("Harbinger of the Seas", self.meta(
            "Creature — Merfolk Wizard", "Nonbasic lands are Islands."), set(), ["U"], "Other")
        self.assertEqual([v for _, v in profile["manaVerdicts"]], ["land types set, not applied"])
        # A count creature's {T} is recorded: it does not attack when tapped.
        self.assertTrue(exporter.card_mana_model("Elvish Archdruid", CARDS["Elvish Archdruid"],
                                                 ["G"])["manaTapsSelf"])


class ManaRoundThreeParserTests(unittest.TestCase):
    """Review round 3 (2026-11-20): more wordings the parser refuses, and
    readings that replaced a refusal. Texts from the local Scryfall mirror
    (2026-11-20)."""

    meta = staticmethod(ManaRoundTwoParserTests.meta)

    REFUSED = [
        # No mana cost: suspend (read as free it would be cast at once).
        ("Ancestral Vision", "Sorcery", "Suspend 4—{U} (Rather than cast this card from your hand, pay {U} "
         "and exile it with four time counters on it.)\nTarget player draws three cards.", ""),
        # A land's own mandatory self-sacrifice trigger.
        ("City of Traitors", "Land", "When you play another land, sacrifice this land.\n{T}: Add {C}{C}.", ""),
        # Land searches whose count or filter no rule places.
        ("Boundless Realms", "Sorcery", "Search your library for up to X basic land cards, where X is the "
         "number of lands you control, put them onto the battlefield tapped, then shuffle.", "{6}{G}"),
        ("Probe Four Lands", "Sorcery", "Search your library for four basic land cards, put them onto the "
         "battlefield tapped, then shuffle.", "{4}"),
        ("Scapeshift", "Sorcery", "Sacrifice any number of lands. Search your library for up to that many land "
         "cards, put them onto the battlefield tapped, then shuffle.", "{2}{G}{G}"),
        ("Into the North", "Sorcery", "Search your library for a snow land card, put it onto the battlefield "
         "tapped, then shuffle.", "{1}{G}"),
        # A land search behind a cost that keeps the land.
        ("Thawing Glaciers", "Land", "This land enters tapped.\n{1}, {T}: Search your library for a basic land "
         "card, put that card onto the battlefield tapped, then shuffle. Return this land to its owner's hand "
         "at the beginning of the next cleanup step.", ""),
        # "Lands you control are the chosen type".
        ("Realmwright", "Creature — Vedalken Wizard", "As this creature enters, choose a basic land type.\n"
         "Lands you control are the chosen type in addition to their other types.", "{U}"),
        # Setting nonbasic lands' type beside other colours (commander R/G/W).
        ("Blood Moon", "Enchantment", "Nonbasic lands are Mountains.", "{2}{R}"),
        ("Magus of the Moon", "Creature — Human Wizard", "Nonbasic lands are Mountains.", "{2}{R}"),
    ]

    @classmethod
    def card(cls, type_line, text, cost):
        return dict(cls.meta(type_line, text), mana_cost=cost)

    # The reason each refusal names (review round 4).
    REASONS = {'Ancestral Vision': 'how it is cast (no mana cost)', 'City of Traitors': 'When you play another land, sacrifice this land.', 'Boundless Realms': 'its land search', 'Probe Four Lands': 'its land search', 'Scapeshift': 'its land search', 'Into the North': 'its land search', 'Thawing Glaciers': '{1}, {T}: Search your library', 'Realmwright': 'Lands you control are the chosen type', 'Blood Moon': 'Nonbasic lands are Mountains.', 'Magus of the Moon': 'Nonbasic lands are Mountains.'}

    def test_wordings_no_rule_reads_stop_the_export(self):
        self.assertEqual(sorted(self.REASONS), sorted(name for name, _, _, _ in self.REFUSED))
        for name, type_line, text, cost in self.REFUSED:
            with self.subTest(card=name):
                with self.assertRaisesRegex(ValueError, re.escape(self.REASONS[name])):
                    exporter.build_goldfish_profile(name, self.card(type_line, text, cost), set(),
                                                    ["R", "G", "W"], "Other")

    def test_a_card_that_gives_up_a_land_is_named_in_the_refusal(self):
        with self.assertRaisesRegex(ValueError, "the land it gives up"):
            exporter.build_goldfish_profile("Harrow", self.card(
                "Instant", "As an additional cost to cast this spell, sacrifice a land.\nSearch your library "
                "for up to two basic land cards, put them onto the battlefield, then shuffle.", "{2}{G}"),
                set(), ["G"], "Other")

    def test_readings_that_replaced_a_refusal(self):
        # Harbinger of the Seas in a mono-blue deck: a named floor; Blood Moon
        # in a mono-red deck likewise.
        for name, colours in (("Harbinger of the Seas", ["U"]), ("Blood Moon", ["R"])):
            text = "Nonbasic lands are Islands." if name.startswith("Harbinger") else "Nonbasic lands are Mountains."
            profile = exporter.build_goldfish_profile(name, self.card("Creature — Merfolk Wizard", text, "{U}"),
                                                      set(), colours, "Other")
            self.assertEqual([v for _, v in profile["manaVerdicts"]], ["land types set, not applied"])
        # An Aura that makes another permanent a colourless land: a floor.
        profile = exporter.build_goldfish_profile("Imprisoned in the Moon", self.card(
            "Enchantment — Aura", "Enchant creature, land, or planeswalker\nEnchanted permanent is a colorless "
            "land with \"{T}: Add {C}\" and loses all other card types and abilities.", "{2}{U}"),
            set(), ["U"], "Other")
        self.assertEqual(([v for _, v in profile["manaVerdicts"]], profile["manaAtoms"]), (["grant floor"], []))
        # "Add five mana in any combination of colors" for {5}: nets nothing.
        profile = exporter.build_goldfish_profile("Cascading Cataracts", self.card(
            "Land", "Indestructible\n{T}: Add {C}.\n{5}, {T}: Add five mana in any combination of colors.", ""),
            set(), ["U", "G"], "Other")
        self.assertEqual(mana_letters(profile["manaAtoms"]), ["C"])
        # An entering trigger worded with the card's short name.
        profile = exporter.build_goldfish_profile("Sutina, Speaker of the Tajuru", self.card(
            "Legendary Creature — Elf Scout", "When Sutina enters, search your library for a basic land card, "
            "put it onto the battlefield tapped, then shuffle.\nWhenever Sutina attacks, you may return a land "
            "you control to its owner's hand. When you do, put a +1/+1 counter on target creature.", "{2}{G}"),
            set(), ["G"], "Other")
        self.assertEqual((profile["landRamp"]["count"], profile["landRamp"]["entersTapped"]), (1, True))
        # A land sacrificed for a search (Elvish Reclaimer) nets nothing: no
        # land fetch, not refused.
        profile = exporter.build_goldfish_profile("Elvish Reclaimer", self.card(
            "Creature — Elf Warrior", "This creature gets +2/+2 as long as there are three or more land cards in "
            "your graveyard.\n{2}, {T}, Sacrifice a land: Search your library for a land card, put it onto the "
            "battlefield tapped, then shuffle.", "{G}"), set(), ["G"], "Other")
        self.assertIsNone(profile["landFetch"])


class ManaPilotHelperTests(unittest.TestCase):
    """The pilot's mana choices (fix pass 2026-11-19), at their helpers: what
    an imprint exiles, which mana is spent first, the colours a fetch finds,
    a Snarl's reveal, a Basalt Monolith's untap. Card data from CARDS."""

    @staticmethod
    def context(names, colors):
        return exporter.build_goldfish_context(list(names), {"decklist": []}, CARDS, "Probe Commander",
                                               list(colors), "synthetic-pilot")

    def test_an_imprint_exiles_the_card_the_goldfish_gets_least_from(self):
        context = self.context(["Chrome Mox", "Ugin's Labyrinth", "Probe BB", "Probe Kill", "Probe Two",
                                "Probe Nine", "Wastes"], ("B",))
        profiles = context["profiles"]
        # (permanent, hand, card exiled, hand after, mana after)
        cases = [
            # Interaction the goldfish never casts goes first.
            ("Chrome Mox", ["Probe BB", "Probe Kill", "Probe Two"], "Probe Kill",
             ["Probe BB", "Probe Two"], ["B"]),
            # Else the castable card last in the cast order: the only coloured one.
            ("Chrome Mox", ["Probe BB", "Probe Two"], "Probe BB", ["Probe Two"], ["B"]),
            # Colourless cards give the Mox nothing: none is exiled.
            ("Chrome Mox", ["Probe Two", "Probe Nine"], None, ["Probe Two", "Probe Nine"], []),
            # The Labyrinth takes a colourless card of mana value 7 or more.
            ("Ugin's Labyrinth", ["Probe Two", "Probe Nine", "Wastes"], "Probe Nine",
             ["Probe Two", "Wastes"], ["C", "C"]),
            ("Ugin's Labyrinth", ["Probe Two", "Probe BB"], None, ["Probe Two", "Probe BB"], ["C"]),
        ]
        for name, hand, exiled, hand_after, mana in cases:
            with self.subTest(permanent=name, hand=hand):
                record = {"manaAtoms": list(profiles[name]["manaAtoms"])}
                hand = list(hand)
                got = exporter.imprint_from_hand(record, profiles[name], hand, profiles, context, False)
                self.assertEqual((got, hand, mana_letters(record["manaAtoms"])),
                                 (exiled, hand_after, mana))

    def test_an_imprint_never_exiles_a_line_member_tutor_or_reanimation_spell(self):
        # With Probe BB in a combo line and Probe Kill a tutor (by its role),
        # in a deck with no gate configured for them to matter, Chrome Mox
        # exiles nothing; in a deck without those roles it takes Probe Kill
        # (interaction it never casts).
        names = ["Chrome Mox", "Probe BB", "Probe Kill", "Swamp"]
        tutor = {"name": "Probe Kill", "primary_role": "tutor"}
        line = {"title": "line", "kind": "combo", "description": "",
                "pieces": ["Probe BB", "Swamp"], "cards": ["Probe BB", "Swamp"]}
        hand = ["Probe BB", "Probe Kill"]
        for deck_data, exiled in (({"decklist": []}, "Probe Kill"),
                                  ({"decklist": [tutor]}, "Probe BB"),
                                  ({"decklist": [tutor], "winConditions": [line]}, None)):
            with self.subTest(deck=deck_data):
                context = exporter.build_goldfish_context(names, deck_data, CARDS, "Probe Commander",
                                                          ["B"], "synthetic-keep")
                self.assertEqual(exporter.imprint_choice(context["profiles"]["Chrome Mox"], hand,
                                                         context["profiles"], context, False), exiled)

    def test_lands_and_noncreatures_are_spent_before_creatures(self):
        def record(name, combat, ready=1):
            return {"name": name, "combat": combat, "combatReadyTurn": ready}

        profiles = {
            "Forest": {"typeWords": frozenset({"Basic", "Land", "Forest"}), "manaTapsSelf": True,
                       "vigilance": False},
            "Elf": {"typeWords": frozenset({"Creature", "Elf"}), "manaTapsSelf": True, "vigilance": False},
            "Vigilant Elf": {"typeWords": frozenset({"Creature", "Elf"}), "manaTapsSelf": True,
                             "vigilance": True},
            "Urza": {"typeWords": frozenset({"Creature", "Human"}), "manaTapsSelf": False,
                     "vigilance": False},
        }
        cases = [
            (record("Forest", 0), 0),
            # A creature that taps for mana instead of attacking: 2 + its combat.
            (record("Elf", 1), 3),
            (record("Elf", 4), 6),
            # Summoning sick: it could not attack anyway.
            (record("Elf", 1, ready=2), 0),
            # Vigilance (M9): it attacks first and taps for mana after combat.
            (record("Vigilant Elf", 1), 0),
            # Its mana does not tap it (Urza taps another artifact).
            (record("Urza", 1), 0),
        ]
        for rec, order in cases:
            with self.subTest(record=rec):
                self.assertEqual(exporter.spend_order(rec, profiles, 1), order)
        # One generic mana: the land pays, then the least combat.
        land, small, big = (exporter.tag_atoms([frozenset("G")], {"name": n}, o)[0]
                            for n, o in (("Forest", 0), ("Elf", 3), ("Big Elf", 6)))
        one = {"generic": 1, "W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "C": 0, "X": 0, "total": 1}
        left = exporter.GoldfishManaPool([big, small, land]).pay(one).sources
        self.assertEqual(sorted(a.source["name"] for a in left), ["Big Elf", "Elf"])
        left = exporter.GoldfishManaPool([big, small]).pay(one).sources
        self.assertEqual([a.source["name"] for a in left], ["Big Elf"])

    def test_a_fetch_land_finds_a_legal_land_of_the_library(self):
        # Polluted Delta finds an Island or a Swamp card. With a Plains and
        # Xander's Lounge (an Island Swamp Mountain that enters tapped) left,
        # the Lounge is the only legal land; with an Island too the Island
        # (untapped) wins; with a Plains alone nothing is found. Only a take
        # removes the land from the library.
        context = self.context(["Polluted Delta", "Island", "Plains", "Xander's Lounge"], ("U", "B", "R"))
        profiles = context["profiles"]
        for library, found in ((["Plains", "Xander's Lounge"], ("Xander's Lounge", True)),
                               (["Xander's Lounge", "Island"], ("Island", False)),
                               (["Plains"], (None, True))):
            with self.subTest(library=library):
                kept = list(library)
                self.assertEqual(exporter.crack_target("Polluted Delta", kept, profiles, ["U", "B", "R"],
                                                       [], [], [], take=False), found)
                self.assertEqual(kept, library)
                exporter.crack_target("Polluted Delta", kept, profiles, ["U", "B", "R"], [], [], [],
                                      take=True)
                self.assertEqual(len(kept), len(library) - (found[0] is not None))

    def test_a_search_for_lands_that_share_a_type_takes_a_legal_set(self):
        # Myriad Landscape: "up to two basic land cards that share a land
        # type". From Forest, Forest, Swamp: the two Forests, not the Swamp
        # alone. "A Forest card and a Plains card" takes at most `count`.
        context = self.context(["Forest", "Swamp", "Plains"], ("B", "G", "W"))
        profiles = context["profiles"]
        shared = {"count": 2, "toHand": 0, "basicOnly": True, "allowedSubtypes": set(), "perType": [],
                  "sharedType": True, "entersTapped": True}
        library = ["Forest", "Forest", "Swamp"]
        self.assertEqual(sorted(exporter.select_ramp_targets(library, profiles, ["B", "G", "W"], [], [],
                                                             shared, 2, to_hand=False)), ["Forest", "Forest"])
        per_type = dict(shared, sharedType=False, basicOnly=False, perType=["Forest", "Plains"])
        for count, taken in ((0, 0), (1, 1), (2, 2)):
            with self.subTest(count=count):
                self.assertEqual(len(exporter.select_ramp_targets(
                    ["Forest", "Plains"], profiles, ["B", "G", "W"], [], [], per_type, count, to_hand=False)), taken)

    def test_an_exact_payment_is_found_and_prefers_lands(self):
        def mana(colours, name, order):
            return exporter.tag_atoms([frozenset(colours)], {"name": name}, order)[0]

        # Atraxa ({W}{U}{B}{G}) from Hallowed Fountain (W/U), a U/B land,
        # Elves of Deep Shadow (B) and Noble Hierarch (G/W/U): only one
        # matching pays it, and greedy land-first spending misses it.
        atraxa = {"W": 1, "U": 1, "B": 1, "G": 1, "R": 0, "C": 0, "generic": 0, "X": 0, "total": 4}
        pool = exporter.GoldfishManaPool([mana("WU", "Fountain", 0), mana("UB", "Delta land", 0),
                                          mana("B", "Elves", 3), mana("GWU", "Hierarch", 3)])
        self.assertTrue(pool.can_cast(atraxa))
        # A wider land pays a {G} before a narrower creature that could attack.
        g = dict(atraxa, W=0, U=0, B=0, total=1)
        left = exporter.GoldfishManaPool([mana("GU", "Dual", 0), mana("G", "Elf", 3)]).pay(g)
        self.assertEqual([a.source["name"] for a in left.sources], ["Elf"])
        # Two generic: one creature that makes two before two that make one.
        two = dict(g, G=0, generic=2, total=2)
        priest = exporter.tag_atoms([frozenset("G")] * 2, {"name": "Priest"}, 5)
        left = exporter.GoldfishManaPool(priest + [mana("G", "Elf A", 3), mana("G", "Elf B", 3)]
                                         ).pay(two)
        self.assertEqual(sorted(a.source["name"] for a in left.sources), ["Elf A", "Elf B"])
        # One-shot mana after the lands: {1} from a Wastes keeps the Vault.
        one = dict(two, generic=1, total=1)
        vault = exporter.tag_atoms([frozenset("C")] * 3, {"name": "Vault"}, 1, once=True)
        left = exporter.GoldfishManaPool(vault + [mana("C", "Wastes", 0)]).pay(one)
        self.assertEqual([a.source["name"] for a in left.sources], ["Vault"] * 3)

    def test_mana_of_any_one_color_pays_one_colour(self):
        # Lotus Field's three mana of one colour (here W or U): {W}{U} cannot be
        # paid from it alone, {W}{W} can, and after a {W} the rest is white.
        field = {"name": "Lotus Field"}
        atoms = exporter.tag_atoms([frozenset("WU")] * 3, field, 0, group=id(field))
        pips = {"W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "C": 0, "generic": 0, "X": 0, "total": 2}
        self.assertFalse(exporter.GoldfishManaPool(atoms).can_cast(dict(pips, W=1, U=1)))
        self.assertTrue(exporter.GoldfishManaPool(atoms).can_cast(dict(pips, W=2)))
        left = exporter.GoldfishManaPool(atoms).pay(dict(pips, W=1, total=1))
        self.assertEqual(mana_letters(left.sources), ["W", "W"])

    def test_a_snarl_reads_the_hand(self):
        rule = exporter.parse_land_entry(
            "As this land enters, you may reveal a Plains or Swamp card from your hand. If you don't, "
            "this land enters tapped.\n{T}: Add {W} or {B}.")
        profiles = {"Swamp": {"subtypes": {"Swamp"}}, "Forest": {"subtypes": {"Forest"}},
                    "Probe BB": {"subtypes": set()}}
        for hand, tapped in ((["Swamp"], False), (["Forest", "Probe BB"], True), ([], True)):
            with self.subTest(hand=hand):
                self.assertEqual(exporter.land_enters_tapped(rule, [], [], profiles, hand), tapped)
        # Urborg makes every land a Swamp on the battlefield only: in the hand
        # it is no Swamp card to reveal.
        urborg = {"type_line": "Legendary Land", "mana_cost": "", "cmc": 0, "colors": [],
                  "oracle_text": "Each land is a Swamp in addition to its other land types."}
        profiles = exporter.build_goldfish_context(
            ["Urborg, Tomb of Yawgmoth"], {"decklist": []}, {"Urborg, Tomb of Yawgmoth": urborg},
            "Urborg, Tomb of Yawgmoth", ["B"], "x")["profiles"]
        self.assertTrue(exporter.land_enters_tapped(rule, [], [], profiles, ["Urborg, Tomb of Yawgmoth"]))

    def test_a_spent_basalt_monolith_untaps_with_three_mana_left(self):
        context = self.context(["Basalt Monolith", "Wastes"], ("C",))
        profiles = context["profiles"]
        for left, rearmed in ((3, True), (2, False)):
            with self.subTest(mana_left=left):
                monolith = {"name": "Basalt Monolith", "onceSpent": True, "tapped": True}
                pool = exporter.rearm_once_sources(
                    [monolith], exporter.GoldfishManaPool([frozenset("C")] * left), [], profiles)
                self.assertEqual((not monolith["onceSpent"], pool.total), (rearmed, 0 if rearmed else left))

    def test_the_methodology_names_the_decks_own_mana_cards(self):
        decklist = ["Mana Vault", "Basalt Monolith", "Chrome Mox", "Lotus Field", "Wayfarer's Bauble",
                    "Llanowar Elves", "Tainted Wood", "Krark-Clan Ironworks",
                    "Birgi, God of Storytelling // Harnfel, Horn of Bounty"] + ["Wastes"] * 90
        deck_data = {"decklist": [{"name": name} for name in decklist], "winConditions": []}
        with patch.object(exporter, "GOLDFISH_GAMES", 16), patch("multiprocessing.Pool", SerialPool):
            goldfish, _ = exporter.compute_goldfish_section(
                decklist=decklist, deck_data=deck_data, metadata=CARDS,
                commander_name="Probe Commander", commander_colors=["B", "G"], deck_id="synthetic-pilot")
        methodology = goldfish["methodology"]
        for sentence in (
                " Mana model (owner-approved 2026-11-19, review rounds 1 to 5 2026-11-20): a "
                "permanent gives the mana its own text gives a pilot on a normal turn, using only "
                "itself and what the goldfish has on its own battlefield; a wording the parser is "
                "known not to read stops the export.",
                "a tapped creature does not attack, and one that attacked pays for nothing afterwards",
                "Spend order: mana already made (floating) first; then lands, noncreature mana and "
                "creatures that could not attack",
                "The combo and assembly gates' reachability is checked before attackers are declared, "
                "and the gates are read after combat on the mana kept for them",
                "Convention: Exotic Orchard and Fellwar Stone make the commander's colours",
                "\"your opponents control eight or more lands\" is met from the fourth land drop, "
                "DEC-688 / DEC-929",
                "a fetch land is cracked as it is played for the best legal land left in the library",
                "with nothing to find it stays and makes no mana of its own",
                "a non-land ability with mana in its cost (a Signet) also from the next turn, a floor",
                "availableMana is the mana the pilot could have spent that turn",
                "Dryad Arbor is a land and never attacks.",
                "Named floors (not credited): Treasure and other mana tokens; rituals",
                "After every resolution (a cast, a land put onto the battlefield, a permanent leaving, "
                "a grant or trigger source entering) the turn's unspent mana is read from the board again",
                "a payment is found whenever the cost and what the turn holds can be paid together, "
                "never otherwise, and of the payments that keep the holds the most preferred is taken",
                "a vigilant creature is not: M9, the pilot attacks first and casts after combat, so a "
                "vigilant mana creature both attacks and pays",
                "Forsaken Monument's extra belongs to the colourless choice of an activation"):
            with self.subTest(sentence=sentence[:40]):
                self.assertIn(sentence, methodology)
        self.assertIn(
            " In this deck, one-shot mana: Basalt Monolith, Mana Vault; untapped with mana left: "
            "Basalt Monolith; imprint: Chrome Mox; lands that take lands as they enter: Lotus Field; "
            "land-fetching permanents: Wayfarer's Bauble; mana read on the battlefield: Tainted Wood; "
            "all of one activation's mana one colour: Lotus Field; mana as spells are cast: Birgi, "
            "God of Storytelling // Harnfel, Horn of Bounty; mana creatures that tap instead of "
            "attacking: Llanowar Elves; abilities not credited: Krark-Clan Ironworks (needs another "
            "resource).", methodology)
        # A count creature is a mana creature too (Elvish Archdruid).
        decklist = ["Elvish Archdruid"] + ["Forest"] * 98
        with patch.object(exporter, "GOLDFISH_GAMES", 16), patch("multiprocessing.Pool", SerialPool):
            goldfish, _ = exporter.compute_goldfish_section(
                decklist=decklist, deck_data={"decklist": [{"name": n} for n in decklist]},
                metadata=CARDS, commander_name="Probe Commander", commander_colors=["G"],
                deck_id="synthetic-pilot")
        self.assertIn("mana creatures that tap instead of attacking: Elvish Archdruid.",
                      goldfish["methodology"])

    def test_land_fetching_permanents_are_ramp_for_the_cast_order_and_the_mulligan(self):
        context = self.context(["Sakura-Tribe Elder", "Chrome Mox", "Forest"], ("G",))
        profiles = context["profiles"]
        self.assertTrue(exporter.is_mana_source(profiles["Sakura-Tribe Elder"]))
        self.assertEqual(exporter.proactive_cast_priority(
            "Sakura-Tribe Elder", profiles["Sakura-Tribe Elder"], "Probe Commander", False)[0], 0)
        self.assertTrue(exporter.is_mana_source(profiles["Chrome Mox"]))
        hand = ["Forest", "Forest", "Sakura-Tribe Elder", "Probe Nine", "Probe Nine", "Probe Nine",
                "Probe Nine"]
        profiles = dict(profiles, **self.context(["Probe Nine"], ("G",))["profiles"])
        self.assertFalse(exporter.should_goldfish_mulligan(hand, profiles))
        self.assertTrue(exporter.should_goldfish_mulligan(
            ["Forest", "Forest"] + ["Probe Nine"] * 5, profiles))


class GoldfishMulliganTests(unittest.TestCase):
    """The goldfish's Commander mulligan, through commander_mulligan_goldfish
    with only the shuffle scripted: each random.shuffle call records the
    cards it receives and deals a given seven on top of the library (draws
    pop its end), the given cards under it, then the rest of the deck in deck
    order. The first mulligan is free; the second is paid: the third seven is
    kept and one card goes to the bottom. Card data from CARDS; made up:
    "Probe Big Kill" (interaction of mana value 5), "Probe Wipe" (a board
    wipe of mana value 7), "Probe Raise" (a reanimation spell of mana value
    4, interaction by its "return target" text), "Probe Seek" (a tutor of
    mana value 7), "Probe Entomb" (a tutor of mana value 1 that puts its card
    into the graveyard), "Probe Blade" (an Equipment of mana value 4) and
    "Probe Tapped Forest" (a land that enters tapped and makes {G}).

    The deck data gives Probe Raise, Probe Seek and Probe Entomb their roles.
    The gate decides what the mulligan keeps (mulliganKeep): "combo" is a
    combo line of Probe Combo A and Probe Combo B (both pieces, both tutors,
    the reanimation spell); "assembly" is the same pair as the deck's only
    assembly line (both members and Probe Seek, the to_hand tutor); "none"
    has no gate (nothing); "deploy" has no gate and a deploy engine whose
    Equipment is Probe Blade (Probe Blade)."""

    METADATA = dict(CARDS, **{
        "Probe Big Kill": {"type_line": "Sorcery", "mana_cost": "{4}{B}", "cmc": 5.0,
                           "oracle_text": "Destroy target creature.", "colors": ["B"]},
        "Probe Wipe": {"type_line": "Sorcery", "mana_cost": "{5}{B}{B}", "cmc": 7.0,
                       "oracle_text": "Destroy all creatures.", "colors": ["B"]},
        "Probe Raise": {"type_line": "Sorcery", "mana_cost": "{2}{B}{B}", "cmc": 4.0,
                        "oracle_text": "Return target creature card from your graveyard to the battlefield.",
                        "colors": ["B"]},
        "Probe Seek": {"type_line": "Sorcery", "mana_cost": "{6}{B}", "cmc": 7.0,
                       "oracle_text": "Search your library for a card, put that card into your hand, then shuffle.",
                       "colors": ["B"]},
        "Probe Entomb": {"type_line": "Instant", "mana_cost": "{B}", "cmc": 1.0,
                         "oracle_text": "Search your library for a card, put that card into your graveyard, "
                                        "then shuffle.",
                         "colors": ["B"]},
        "Probe Blade": {"type_line": "Artifact — Equipment", "mana_cost": "{4}", "cmc": 4.0,
                        "oracle_text": "Equipped creature gets +4/+0.\nEquip {4}", "colors": []},
        "Probe Tapped Forest": {"type_line": "Land", "mana_cost": "", "cmc": 0.0,
                                "oracle_text": "This land enters tapped.\n{T}: Add {G}.", "colors": []},
    })
    ROLES = [{"name": "Probe Raise", "primary_role": "recursion"},
             {"name": "Probe Seek", "primary_role": "tutor"},
             {"name": "Probe Entomb", "primary_role": "tutor", "tutor_mode": "to_graveyard"}]
    PAIR = ["Probe Combo A", "Probe Combo B"]
    GATES = {
        "combo": ({"decklist": ROLES, "winConditions": [
            {"title": "Probe line", "kind": "combo", "description": "", "pieces": PAIR, "cards": PAIR}]}, {}, {}),
        "assembly": ({"decklist": ROLES}, {"synthetic-mulligan": [{"name": "Probe line", "pieces": PAIR}]}, {}),
        "none": ({"decklist": ROLES}, {}, {}),
        "deploy": ({"decklist": ROLES}, {}, {"synthetic-mulligan": {
            "transformCost": {"generic": 4}, "reducedTransformCost": {"generic": 2}, "reducerName": "",
            "transformedPower": 5, "equipmentPower": {"Probe Blade": 4}, "doubleStrikeNames": set()}}),
    }
    DECK = (["Forest"] * 29 + ["Probe Tapped Forest", "Polluted Delta"] + ["Swamp"] * 6
            + ["Probe Slow Land"] * 2 + ["Probe Kill", "Probe Big Kill", "Probe Wipe", "Probe Seek"]
            + ["Probe Raise"] * 2 + PAIR + ["Probe Entomb", "Probe Blade"] + ["Probe Two"] * 14
            + ["Probe Three"] * 14 + ["Probe Five"] * 14 + ["Probe Nine"] * 8)
    # One land: a mulligan (should_goldfish_mulligan).
    BAD = ["Forest", "Probe Two", "Probe Three", "Probe Five", "Probe Nine", "Probe Two", "Probe Three"]

    def deal(self, seven, under=()):
        rest = list(self.DECK)
        for card in list(seven) + list(under):
            rest.remove(card)
        return rest + list(reversed(under)) + list(reversed(seven))

    def context(self, colors, gate="combo"):
        deck_data, combos, deploy = self.GATES[gate]
        with patch.dict(exporter.KEY_COMBOS, combos), patch.dict(exporter.COMMANDER_DEPLOY_ENGINE, deploy):
            return exporter.build_goldfish_context(list(self.DECK), deck_data, self.METADATA,
                                                   "Probe Commander", list(colors), "synthetic-mulligan")

    @staticmethod
    def scripted(orders, received):
        orders = iter(orders)

        def shuffle(library):
            received.append(Counter(library))
            library[:] = next(orders)

        return shuffle

    def mulligan(self, sevens, colors=("B", "G"), gate="combo"):
        received = []
        context = self.context(colors, gate)
        with patch.object(exporter.random, "shuffle", self.scripted([self.deal(s) for s in sevens], received)):
            library, hand = exporter.commander_mulligan_goldfish(list(self.DECK), context["profiles"],
                                                                 list(colors), context["mulliganKeep"])
        return library, hand, received

    def test_a_bottomed_card_is_drawn_after_the_rest_of_the_library(self):
        seven = ["Forest", "Forest", "Swamp", "Probe Big Kill", "Probe Two", "Probe Three", "Probe Five"]
        library, hand, _ = self.mulligan([self.BAD, self.BAD, seven])
        draws = [library.pop() for _ in range(len(library))]
        self.assertEqual((len(hand), len(draws), draws.index("Probe Big Kill")), (6, 93, 92))

    def test_the_game_draws_the_card_under_the_kept_seven_not_the_bottomed_one(self):
        # simulate_goldfish_game, read only through its own per-turn data: a
        # landless third seven (Probe Big Kill bottomed, interaction first)
        # dealt over Probe Tapped Forest, the deck's only copy. The goldfish
        # draws from turn 1 (CR 103.8c), so its first draw is that land,
        # played on turn 1; turn 2 draws a Probe Nine (the rest of the deck,
        # in deck order, ends with them): one land on turns 1 and 2. Drawing
        # the bottomed Probe Big Kill first, turn 1 would have no land.
        seven = ["Probe Two", "Probe Three", "Probe Five", "Probe Nine", "Probe Big Kill", "Probe Two",
                 "Probe Three"]
        orders = [self.deal(self.BAD), self.deal(self.BAD), self.deal(seven, under=["Probe Tapped Forest"])]
        with patch.object(exporter.random, "shuffle", self.scripted(orders, [])):
            by_turn, _ = exporter.simulate_goldfish_game(list(self.DECK), self.context(("B", "G")), 6)
        self.assertEqual((by_turn[1]["lands"], by_turn[2]["lands"]), (1, 1))

    def test_the_game_keeps_the_decks_mulligan_set(self):
        # simulate_goldfish_game, read through its own per-turn combat: a
        # third seven of four Forests, Probe Two, Probe Three and one dearer
        # card, dealt over Probe Nines. A Forest a turn and a Probe Nine drawn
        # each turn from turn 1; the commander ({5}) is not cast by turn 4.
        # Probe Two is cast on turn 2 and attacks from turn 3, Probe Three, if
        # kept, is cast on turn 3 and attacks from turn 4. (case, gate, dearer
        # card, combat on turns 3 and 4)
        cases = [
            # Nothing kept: Probe Seek, the dearest spell, goes; 2, then 2 + 3.
            ("no gate", "none", "Probe Seek", (2, 5)),
            # Probe Seek kept (a tutor, the deck has a combo line): Probe
            # Three goes. Probe Seek is never cast (reserved), and the line
            # is not reachable (one tutor, both pieces in the library), so
            # nothing holds Probe Two back: 2, then 2.
            ("combo gate", "combo", "Probe Seek", (2, 2)),
            # Probe Blade kept (the deploy engine's Equipment): Probe Three
            # goes. Probe Blade is never cast, and is deployed only once the
            # commander has transformed, which needs it in play: 2, then 2.
            ("deploy engine", "deploy", "Probe Blade", (2, 2)),
        ]
        for case, gate, dearer, combat in cases:
            with self.subTest(case=case):
                seven = ["Forest"] * 4 + [dearer, "Probe Two", "Probe Three"]
                orders = [self.deal(self.BAD), self.deal(self.BAD),
                          self.deal(seven, under=["Probe Nine"] * 3)]
                context = self.context(("B", "G"), gate)
                with patch.object(exporter.random, "shuffle", self.scripted(orders, [])):
                    by_turn, _ = exporter.simulate_goldfish_game(list(self.DECK), context, 6)
                self.assertEqual((by_turn[3]["combat"], by_turn[4]["combat"]), combat)

    def test_the_paid_mulligan_bottoms_interaction_then_the_dearest_spell_and_a_land_from_five(self):
        # (case, kept seven, commander colours, card bottomed, six kept)
        cases = [
            ("interaction first, the most expensive first, before a 9-drop",
             ["Forest", "Forest", "Swamp", "Probe Kill", "Probe Big Kill", "Probe Nine", "Probe Two"],
             ("B", "G"), "Probe Big Kill",
             ["Forest", "Forest", "Swamp", "Probe Kill", "Probe Nine", "Probe Two"]),
            ("the dearer interaction even with the later name",
             ["Forest", "Forest", "Swamp", "Probe Kill", "Probe Wipe", "Probe Two", "Probe Three"],
             ("B", "G"), "Probe Wipe",
             ["Forest", "Forest", "Swamp", "Probe Kill", "Probe Two", "Probe Three"]),
            ("no interaction: the most expensive spell",
             ["Forest", "Forest", "Swamp", "Probe Two", "Probe Three", "Probe Nine", "Probe Five"],
             ("B", "G"), "Probe Nine",
             ["Forest", "Forest", "Swamp", "Probe Two", "Probe Three", "Probe Five"]),
            ("a kept reanimation spell stays though it reads as dearer interaction",
             ["Forest", "Forest", "Swamp", "Probe Raise", "Probe Kill", "Probe Nine", "Probe Two"],
             ("B", "G"), "Probe Kill",
             ["Forest", "Forest", "Swamp", "Probe Raise", "Probe Nine", "Probe Two"]),
            ("kept before interaction: the 9-drop goes, not the kept reanimation spell",
             ["Forest", "Forest", "Swamp", "Probe Raise", "Probe Two", "Probe Three", "Probe Nine"],
             ("B", "G"), "Probe Nine",
             ["Forest", "Forest", "Swamp", "Probe Raise", "Probe Two", "Probe Three"]),
            ("every spell kept: still a spell, interaction first",
             ["Forest", "Forest", "Swamp", "Swamp", "Probe Raise", "Probe Seek", "Probe Raise"],
             ("B", "G"), "Probe Raise",
             ["Forest", "Forest", "Swamp", "Swamp", "Probe Seek", "Probe Raise"]),
            ("four lands: still a spell",
             ["Forest", "Forest", "Swamp", "Probe Slow Land", "Probe Two", "Probe Three", "Probe Five"],
             ("B", "G"), "Probe Five",
             ["Forest", "Forest", "Swamp", "Probe Slow Land", "Probe Two", "Probe Three"]),
            ("five lands: a land, the one entering tapped on an empty battlefield",
             ["Forest", "Forest", "Swamp", "Swamp", "Probe Slow Land", "Probe Two", "Probe Nine"],
             ("B", "G"), "Probe Slow Land",
             ["Forest", "Forest", "Swamp", "Swamp", "Probe Two", "Probe Nine"]),
            ("five lands, two making only {G}: the tapped one, though Forest comes first by name",
             ["Forest", "Forest", "Swamp", "Swamp", "Probe Tapped Forest", "Probe Two", "Probe Nine"],
             ("B", "G"), "Probe Tapped Forest",
             ["Forest", "Forest", "Swamp", "Swamp", "Probe Two", "Probe Nine"]),
            ("six lands: a land too",
             ["Forest", "Forest", "Forest", "Swamp", "Swamp", "Probe Slow Land", "Probe Two"],
             ("B", "G"), "Probe Slow Land",
             ["Forest", "Forest", "Forest", "Swamp", "Swamp", "Probe Two"]),
            ("five lands: Polluted Delta scores as the untapped Swamp the library holds for it",
             ["Polluted Delta", "Forest", "Forest", "Swamp", "Probe Slow Land", "Probe Two", "Probe Nine"],
             ("B", "G"), "Probe Slow Land",
             ["Polluted Delta", "Forest", "Forest", "Swamp", "Probe Two", "Probe Nine"]),
            ("five untapped lands: the one making no commander colour",
             ["Forest", "Forest", "Forest", "Swamp", "Forest", "Probe Two", "Probe Nine"],
             ("G",), "Swamp",
             ["Forest", "Forest", "Forest", "Forest", "Probe Two", "Probe Nine"]),
            ("seven lands: the one ranked lowest, not the first in hand",
             ["Forest", "Swamp", "Forest", "Probe Slow Land", "Swamp", "Forest", "Forest"],
             ("B", "G"), "Probe Slow Land",
             ["Forest", "Swamp", "Forest", "Swamp", "Forest", "Forest"]),
        ]
        for case, seven, colors, bottomed, kept in cases:
            with self.subTest(case=case):
                library, hand, received = self.mulligan([self.BAD, self.BAD, seven], colors)
                self.assertEqual((hand, library, received),
                                 (kept, [bottomed] + self.deal(seven)[:-7], [Counter(self.DECK)] * 3))

    def test_what_the_mulligan_keeps_follows_the_decks_gates(self):
        # (case, gate, kept seven, card bottomed, six kept)
        cases = [
            ("no gate: the reanimation spell is dearer interaction and goes", "none",
             ["Forest", "Forest", "Swamp", "Probe Raise", "Probe Kill", "Probe Nine", "Probe Two"],
             "Probe Raise", ["Forest", "Forest", "Swamp", "Probe Kill", "Probe Nine", "Probe Two"]),
            ("no gate: the tutor is the dearest spell and goes", "none",
             ["Forest", "Forest", "Swamp", "Probe Seek", "Probe Two", "Probe Three", "Probe Five"],
             "Probe Seek", ["Forest", "Forest", "Swamp", "Probe Two", "Probe Three", "Probe Five"]),
            ("assembly only: the reanimation spell is not kept", "assembly",
             ["Forest", "Forest", "Swamp", "Probe Raise", "Probe Seek", "Probe Two", "Probe Three"],
             "Probe Raise", ["Forest", "Forest", "Swamp", "Probe Seek", "Probe Two", "Probe Three"]),
            ("assembly only: the to_hand tutor and the member stay, a Probe Two goes", "assembly",
             ["Forest", "Forest", "Swamp", "Probe Combo A", "Probe Seek", "Probe Two", "Probe Two"],
             "Probe Two", ["Forest", "Forest", "Swamp", "Probe Combo A", "Probe Seek", "Probe Two"]),
            ("assembly only: the to_graveyard tutor is not kept", "assembly",
             ["Forest", "Forest", "Swamp", "Probe Entomb", "Probe Seek", "Probe Combo A", "Probe Combo B"],
             "Probe Entomb", ["Forest", "Forest", "Swamp", "Probe Seek", "Probe Combo A", "Probe Combo B"]),
            ("combo: both pieces and the graveyard tutor stay, the dearest kept spell goes", "combo",
             ["Forest", "Forest", "Swamp", "Probe Entomb", "Probe Seek", "Probe Combo A", "Probe Combo B"],
             "Probe Seek", ["Forest", "Forest", "Swamp", "Probe Entomb", "Probe Combo A", "Probe Combo B"]),
            ("deploy engine: its Equipment stays, the dearer other spell goes", "deploy",
             ["Forest", "Forest", "Swamp", "Probe Blade", "Probe Two", "Probe Three", "Probe Two"],
             "Probe Three", ["Forest", "Forest", "Swamp", "Probe Blade", "Probe Two", "Probe Two"]),
        ]
        for case, gate, seven, bottomed, kept in cases:
            with self.subTest(case=case):
                library, hand, _ = self.mulligan([self.BAD, self.BAD, seven], gate=gate)
                self.assertEqual((hand, library[0]), (kept, bottomed))

    def test_the_third_seven_is_kept_whatever_it_holds(self):
        # Two mulligans at most: a third one-land seven is kept with its
        # most expensive spell bottomed, and no fourth seven is dealt.
        good = ["Forest", "Forest", "Swamp", "Probe Two", "Probe Three", "Probe Five", "Probe Nine"]
        library, hand, received = self.mulligan([self.BAD, self.BAD, self.BAD, good])
        self.assertEqual((hand, library[0], received),
                         (["Forest", "Probe Two", "Probe Three", "Probe Five", "Probe Two", "Probe Three"],
                          "Probe Nine", [Counter(self.DECK)] * 3))

    def test_a_keep_and_a_free_mulligan_bottom_nothing(self):
        good = ["Forest", "Forest", "Swamp", "Probe Two", "Probe Three", "Probe Five", "Probe Nine"]
        for sevens, shuffles in (([good, self.BAD, self.BAD], 1), ([self.BAD, good, self.BAD], 2)):
            with self.subTest(shuffles=shuffles):
                library, hand, received = self.mulligan(sevens)
                self.assertEqual((hand, library, received),
                                 (good, self.deal(good)[:-7], [Counter(self.DECK)] * shuffles))


class GoldfishManaTableGuardTests(unittest.TestCase):
    """Every fleet card's goldfish mana against a reviewed table.

    tests/fixtures/goldfish_mana.json holds, for every card in the 21 decks
    that is a land or has mana text ("add", "adds", "produces", a land
    search), the mana read off its text by hand (owner-approved mana model,
    2026-11-19). The test reads the live decks (data/commanders/*/deck.json,
    data/card-metadata.json) and fails when such a card is missing from the
    table, when a table name is in no deck, when the exporter refuses a card
    (a line of its text no rule reads), or when the exporter's reading
    differs from the table: the mana, whether its ability taps the permanent
    ("taps"), how a land enters, what a fetch land finds ("crack"). A card
    with no mana text may hold a note-only entry (a named floor: mana tokens,
    untappers, cost reducers); the exporter must credit it nothing. After a
    swap, read each new card's text and add its entry; never copy the
    parser's output into it.
    """

    FIXTURE = Path(__file__).resolve().parent / "fixtures" / "goldfish_mana.json"
    # Mana text: "add", "adds", "produces", a land search, or a change to the
    # land types of lands (Urborg, Prismatic Omen, "Nonbasic lands are
    # Islands"), which changes every land's mana.
    MANA_TEXT = re.compile(r"\b(?:adds?|produces?)\b"
                           r"|search your library for [^.]*(land|plains|island|swamp|mountain|forest) cards?"
                           r"|\b(?:each land|lands you control|all lands|nonbasic lands|lands)\b[^.\"]*\b(?:is|are)\b"
                           r"[^.\"]*\b(?:land types?|the chosen type|plains|islands?|swamps?|mountains?|forests?)\b",
                           re.IGNORECASE)

    @staticmethod
    def letters(atom) -> str:
        return "".join(colour for colour in "WUBRGC" if colour in atom)

    @classmethod
    def resolve(cls, text: str, cmd: frozenset) -> str:
        """A table atom ('cmd', 'C+cmd', 'WUC') as WUBRGC letters."""
        colours = set()
        for part in text.split("+"):
            colours |= cmd if part == "cmd" else set(part)
        return cls.letters(colours)

    @staticmethod
    def sorted_bars(text: str) -> str:
        """Order-free comparison of the "A|B" lists inside a term."""
        return ":".join("|".join(sorted(part.split("|"))) for part in text.split(":"))

    @classmethod
    def render(cls, profile: dict) -> dict:
        """The exporter's reading of one card, in the table's words."""
        def atoms(xs):
            return sorted(cls.letters(a) for a in xs)

        def test_text(test):
            if test[0] == "atLeast":
                return f"atLeast:{test[1]}:{test[2]}"
            return f"{test[0]}:" + "|".join(sorted(test[1]))

        def term_text(term):
            if term[0] == "gate":
                return f"gate:{test_text(term[1])}:" + ",".join(cls.letters(a) for a in term[2])
            if term[0] == "count":
                key = ("devotion" if term[1][0] == "devotion"
                       else f"idleArtifacts:{term[1][1]}" if term[1][0] == "idleArtifacts"
                       else f"type:{term[1][1]}")
                gate = f":{test_text(term[4])}" if term[4] else ""
                return f"count:{key}:{cls.letters(term[2])}:{term[3]}{gate}"
            if term[0] == "legendColors":
                return "legendColors:" + ("|".join(term[1]) or "any")
            if term[0] == "extra":
                return f"extra:{term[1]}:{cls.letters(term[2])}:{term[3]}"
            return term[0]

        def search(found, cost=None):
            out = {"count": found["count"], "toHand": found["toHand"], "tapped": found["entersTapped"],
                   "basic": found["basicOnly"], "types": "|".join(sorted(found["allowedSubtypes"])),
                   "perType": "|".join(sorted(found["perType"])), "shared": found["sharedType"]}
            if cost is not None:
                out["cost"] = cost["total"]
            return out

        out = {"mana": atoms(profile["manaAtoms"]), "once": atoms(profile["manaOnce"]),
               "board": sorted(cls.sorted_bars(term_text(t)) for t in profile["manaBoard"]),
               "onCast": atoms(profile["manaOnCast"])}
        if profile["manaOnce"]:
            out["leaves"] = profile["onceLeaves"]
        if profile["onceRearm"]:
            out["rearm"] = profile["onceRearm"]["total"]
        if profile["manaOneColour"]:
            out["oneColour"] = True
        if profile["landGrant"]:
            out["landGrant"] = cls.letters(profile["landGrant"])
        if profile["imprint"]:
            rule = profile["imprint"]
            out["imprint"] = {key: rule[key] for key in ("colorless", "nonartifact", "nonland", "minValue")
                              if rule.get(key)}
            out["imprint"]["atoms"] = "colors" if rule["atoms"] is None else atoms(rule["atoms"])
        if profile["isLand"]:
            entry = profile["landEntry"]
            out["entry"] = entry if isinstance(entry, str) else ":".join(
                "|".join(sorted(part)) if isinstance(part, frozenset) else str(part) for part in entry)
        elif profile["manaAtoms"] or profile["manaOnce"] or profile["manaBoard"] or profile["imprint"]:
            out["from"] = {0: "now", 1: "next"}.get(profile["manaSourceDelay"])
            # Whether the ability it is tapped for mana by has {T} (R1: a
            # creature tapped for mana does not attack).
            out["taps"] = profile["manaTapsSelf"]
        for key, value in (("entryCost", profile["landEntryCost"]), ("turns", profile["manaTurns"]),
                           ("eachLandIs", profile["eachLandIs"])):
            if value:
                out[key] = value
        if profile["landFaces"]:
            out["faces"] = [atoms(face) for face in profile["landFaces"]]
        if profile["landRamp"]:
            out["ramp"] = search(profile["landRamp"])
        if profile["landFetch"]:
            out["fetch"] = dict(search(profile["landFetch"], profile["landFetch"]["cost"]),
                                tapsSelf=profile["landFetch"]["tapsSelf"])
        if profile["landCrack"]:
            crack = profile["landCrack"]
            out["crack"] = {"types": "|".join(sorted(crack["allowedSubtypes"])), "basic": crack["basicOnly"],
                            "tapped": crack["entersTapped"],
                            "untapIf": ":".join(map(str, crack["untapIf"])) if crack["untapIf"] else None}
        if profile["landTypes"] == exporter.NONBASIC_LAND_TYPES:
            out["everyNonbasicType"] = True
        return out

    @classmethod
    def expected(cls, spec: dict, is_land: bool, cmd: frozenset) -> dict:
        """One table entry, with 'cmd' read for this deck."""
        def atoms(xs):
            return sorted(cls.resolve(x, cmd) for x in xs)

        board = [re.sub(r"\bcmd\b", cls.letters(cmd), term) for term in spec.get("board", [])]
        out = {"mana": atoms(spec.get("mana", [])), "once": atoms(spec.get("once", [])),
               "board": sorted(cls.sorted_bars(term) for term in board),
               "onCast": atoms(spec.get("onCast", []))}
        if spec.get("once"):
            out["leaves"] = spec["leaves"]
        for key in ("rearm", "oneColour"):
            if key in spec:
                out[key] = spec[key]
        if "landGrant" in spec:
            out["landGrant"] = cls.resolve(spec["landGrant"], cmd)
        if "imprint" in spec:
            out["imprint"] = dict(spec["imprint"])
            if out["imprint"]["atoms"] != "colors":
                out["imprint"]["atoms"] = atoms(out["imprint"]["atoms"])
        if is_land:
            out["entry"] = cls.sorted_bars(spec.get("entry", "untapped"))
        elif "from" in spec:
            out["from"] = spec["from"]
            out["taps"] = spec["taps"]
        for key in ("entryCost", "turns", "eachLandIs", "everyNonbasicType", "crack"):
            if key in spec:
                out[key] = spec[key]
        if "crack" in spec:
            out["crack"] = dict(spec["crack"], types=cls.sorted_bars(spec["crack"]["types"]))
        if "faces" in spec:
            out["faces"] = [atoms(face) for face in spec["faces"]]
        for key in ("ramp", "fetch"):
            if key in spec:
                out[key] = dict(spec[key], types=cls.sorted_bars(spec[key]["types"]),
                                perType=cls.sorted_bars(spec[key]["perType"]))
        return out

    @classmethod
    def problems(cls, root: Path, exporter_module, metadata: dict | None = None) -> list[str]:
        table = json.loads(cls.FIXTURE.read_text())
        table.pop("_about")
        if metadata is None:
            metadata = json.loads((root / "data" / "card-metadata.json").read_text())
        index = json.loads((root / "data" / "index.json").read_text())
        colours = {entry["id"]: entry["colors"] for entry in index["commanders"]}
        problems, in_decks = [], set()
        for deck_id, _, _ in exporter_module.DECKS:
            deck = json.loads((root / "data" / "commanders" / deck_id / "deck.json").read_text())
            decklist = [card["name"] for card in deck["decklist"]]
            cmd = frozenset(colours[deck_id])
            for name in sorted(set(decklist) | {deck["commander"]}):
                in_decks.add(name)
                meta = metadata[name]
                try:
                    profile = exporter_module.build_goldfish_profile(
                        name, meta, set(), sorted(cmd), deck["commander"])
                except ValueError as error:
                    problems.append(f"{name} ({deck_id}): {error}")
                    continue
                text = meta.get("oracle_text", "") + "\n" + (meta.get("back_face") or {}).get("oracle_text", "")
                got = cls.render(profile)
                if "Land" not in meta["type_line"] and not cls.MANA_TEXT.search(text):
                    # A card with no mana text may hold a note-only entry (an
                    # untapper, a cost reducer: a named floor); it gives nothing.
                    if name in table and got != cls.expected(table[name], False, cmd):
                        problems.append(f"{name} ({deck_id}): note-only entry but the exporter credits {got}")
                    continue
                if name not in table:
                    problems.append(f"{name} ({deck_id}): not in {cls.FIXTURE.name}: read its mana "
                                    "off its text and add an entry")
                    continue
                want = cls.expected(table[name], profile["isLand"], cmd)
                if want != got:
                    problems.append(f"{name} ({deck_id}): table {want} but exporter {got}")
        problems += [f"{name}: in {cls.FIXTURE.name} but in no deck: remove it"
                     for name in sorted(set(table) - in_decks)]
        pairs = cls.deck_cards(root, exporter_module)
        problems += [f"{name}: findsByDeck names {deck_id}, which does not hold it"
                     for name in sorted(table) for deck_id in table[name].get("findsByDeck", {})
                     if (name, deck_id) not in pairs]
        return problems

    @staticmethod
    def deck_cards(root: Path, exporter_module) -> set:
        """(card, deck id) for every card of the 21 decks."""
        pairs = set()
        for deck_id, _, _ in exporter_module.DECKS:
            deck = json.loads((root / "data" / "commanders" / deck_id / "deck.json").read_text())
            pairs |= {(card["name"], deck_id) for card in deck["decklist"]}
        return pairs

    def test_every_fleet_mana_card_matches_the_reviewed_table(self):
        root = Path(__file__).resolve().parent.parent
        problems = self.problems(root, exporter)
        self.assertEqual(problems, [], "\n".join(problems))

    def test_the_guard_sees_changes_to_land_types(self):
        # A permanent that changes land types changes every land's mana: the
        # guard asks for its entry like a card that adds mana.
        for text in ("Nonbasic lands are Islands.",
                     "Lands you control are every basic land type in addition to their other types.",
                     "Each land is a Swamp in addition to its other land types.",
                     "Lands you control are the chosen type in addition to their other types."):
            with self.subTest(text=text[:30]):
                self.assertTrue(self.MANA_TEXT.search(text))
        self.assertFalse(self.MANA_TEXT.search("Creatures you control get +1/+1."))

    def test_the_guard_fails_on_mana_text_no_rule_reads(self):
        # Sol Ring ("{T}: Add {C}{C}.") with a landfall mana trigger, or with a
        # condition inside its ability, is refused: the guard names it.
        root = Path(__file__).resolve().parent.parent
        metadata = json.loads((root / "data" / "card-metadata.json").read_text())
        for added in ("{T}: Add {C}{C}.\nLandfall — Whenever a land you control enters, add {G}.",
                      "{T}: If you control a Dragon, add {C}{C}."):
            with self.subTest(text=added):
                changed = dict(metadata, **{"Sol Ring": dict(metadata["Sol Ring"], oracle_text=added)})
                problems = self.problems(root, exporter, changed)
                self.assertTrue(problems and all(p.startswith("Sol Ring") for p in problems), problems)


class CombatModifierGoldfishTests(unittest.TestCase):
    """DEC-940 — extra combat phases inside a deterministic goldfish turn loop.

    Synthetic ``broodfire-hatchery`` deck built like the DEC-938 harness: the
    combat permanents cost nothing so the whole opening hand lands on turn 1 and
    every attacker is combat-ready on turn 2 (no haste source is ever in play).
    Free creatures all score combat 1 (``max(1, min(8, MV))``), which makes the
    per-turn ``combat`` field a direct count of phases x attackers. The commander
    costs {60} and every Filler {30}, so neither is ever cast: the hatch engine
    stays closed and the whole mana pool is available to Aggravated Assault.
    """

    DECK_ID = "broodfire-hatchery"
    COMMANDER = "Atla Palani, Nest Tender"
    # name -> (type_line, printed power)
    COMBAT_CARDS = {
        "Aurelia, the Warleader": ("Legendary Creature — Angel", "3"),
        "Combat Celebrant": ("Creature — Human Warrior", "4"),
        "Tifa, Martial Artist": ("Legendary Creature — Human Monk", "4"),
        "Zopandrel, Hunger Dominus": ("Legendary Creature — Phyrexian Horror", "9"),
        "Xenagos, God of Revels": ("Legendary Enchantment Creature — God", "6"),
        "Raphael, the Nightwatcher": ("Legendary Creature — Mutant Ninja Turtle", "4"),
        "Aggravated Assault": ("Enchantment", None),
        "Annie Joins Up": ("Legendary Enchantment", None),
        "Attacker A": ("Creature — Bear", "2"),
        "Attacker B": ("Creature — Bear", "2"),
        "Big Attacker": ("Creature — Giant", "7"),
    }
    FILLERS = [f"Filler {i}" for i in range(30)]

    def _metadata(self) -> dict:
        metadata = {
            "Forest": {
                "name": "Forest", "type_line": "Basic Land — Forest",
                "oracle_text": "({T}: Add {G}.)", "mana_cost": "", "cmc": 0,
                "colors": [], "color_identity": ["G"], "produced_mana": ["G"],
            },
            "Ruby Crystal": {
                "name": "Ruby Crystal", "type_line": "Artifact",
                "oracle_text": "{T}: Add {R}.", "mana_cost": "{0}", "cmc": 0,
                "colors": [], "color_identity": ["R"], "produced_mana": ["R"],
            },
            self.COMMANDER: {
                "name": self.COMMANDER,
                "type_line": "Legendary Creature — Human Shaman",
                "oracle_text": "", "mana_cost": "{60}", "cmc": 60,
                "colors": [], "color_identity": ["G"], "power": "2",
                "toughness": "3",
            },
            # A made-up free mana creature (round 1, 2026-11-20).
            "Probe Red Dork": {
                "name": "Probe Red Dork", "type_line": "Creature — Goblin",
                "oracle_text": "{T}: Add {R}.", "mana_cost": "{0}", "cmc": 0,
                "colors": [], "color_identity": ["R"], "power": "1", "toughness": "1",
            },
        }
        for name, (type_line, power) in self.COMBAT_CARDS.items():
            metadata[name] = {
                "name": name, "type_line": type_line, "oracle_text": "",
                "mana_cost": "" if "Land" in type_line else "{0}", "cmc": 0, "colors": [],
                "color_identity": [], "power": power, "toughness": power,
            }
        for name in self.FILLERS:
            metadata[name] = {
                "name": name, "type_line": "Sorcery", "oracle_text": "",
                "mana_cost": "{30}", "cmc": 30, "colors": [],
                "color_identity": [],
            }
        return metadata

    def _run(self, hand_cards, crystals=0, forests=8, deck_id=None):
        """Run one pinned game; return {turn: combat damage dealt that turn}."""
        metadata = self._metadata()
        decklist = (["Forest"] * forests + ["Ruby Crystal"] * max(crystals, 1)
                    + list(self.COMBAT_CARDS) + ["Probe Red Dork"] + self.FILLERS)
        deck_data = {"decklist": [{"name": name} for name in decklist]}
        context = exporter.build_goldfish_context(
            decklist, deck_data, metadata, self.COMMANDER, ["G"],
            self.DECK_ID if deck_id is None else deck_id)
        hand = (["Forest"] * forests + ["Ruby Crystal"] * crystals
                + list(hand_cards))
        library = list(self.FILLERS)
        with patch.object(exporter, "commander_mulligan_goldfish",
                          lambda *_: (list(library), list(hand))):
            by_turn, _ = exporter.simulate_goldfish_game(
                decklist, context, 6)
        return {turn: by_turn[turn]["combat"] for turn in by_turn}

    def test_unconfigured_deck_runs_one_unmodified_combat(self):
        hand = ["Aurelia, the Warleader", "Attacker A", "Attacker B"]
        combat = self._run(hand, deck_id="not-configured")
        self.assertEqual(combat[2], 3)
        # Same hand on the configured deck takes Aurelia's extra combat.
        self.assertEqual(self._run(hand)[2], 6)

    def test_aurelia_adds_one_extra_combat_per_turn(self):
        self.assertEqual(self._run(["Attacker A", "Attacker B"])[2], 2)
        combat = self._run(["Aurelia, the Warleader", "Attacker A", "Attacker B"])
        # Three attackers x two phases — "the first time each turn" is one extra
        # combat, not one per phase, so it does not reach the 4-phase cap.
        self.assertEqual(combat[2], 6)
        self.assertEqual(combat[3], 6)

    def test_combat_celebrant_exerts_every_other_turn_and_sits_out(self):
        # Combat Celebrant left the broodfire config at DEC-935 round 5; the
        # exert mechanism is kept under test on a local copy of the config.
        mods = dict(exporter.COMBAT_MODIFIERS[self.DECK_ID],
                    exertCombatNames={"Combat Celebrant"})
        with patch.dict(exporter.COMBAT_MODIFIERS, {self.DECK_ID: mods}):
            combat = self._run(["Combat Celebrant", "Attacker A", "Attacker B"])
        # Turn 2: 3 attackers, then an extra combat without the exerted
        # Celebrant (it untaps all *other* creatures) = 3 + 2.
        self.assertEqual(combat[2], 5)
        # Turn 3: exerted, so it does not untap and cannot attack at all.
        self.assertEqual(combat[3], 2)
        self.assertEqual(combat[4], 5)
        self.assertEqual(combat[5], 2)

    def test_tifa_needs_a_printed_power_seven_attacker(self):
        # Tifa 4 / Attacker 2 / Attacker 2 — nothing reaches power 7.
        self.assertEqual(
            self._run(["Tifa, Martial Artist", "Attacker A", "Attacker B"])[2], 3)
        # Big Attacker is printed 7/7, so the trigger's gate is met.
        self.assertEqual(
            self._run(["Tifa, Martial Artist", "Big Attacker", "Attacker A"])[2],
            6)

    def test_tifa_only_triggers_from_the_first_combat_phase(self):
        combat = self._run(["Tifa, Martial Artist", "Big Attacker",
                            "Aurelia, the Warleader"])
        # One extra combat each from Aurelia and Tifa = 3 phases x 3 attackers.
        # A Tifa that re-triggered in the extra combats would hit the 4 cap (12).
        self.assertEqual(combat[2], 9)

    def test_annie_doubles_the_aurelia_and_tifa_triggers(self):
        self.assertEqual(
            self._run(["Aurelia, the Warleader", "Attacker A"])[2], 4)
        self.assertEqual(
            self._run(["Aurelia, the Warleader", "Attacker A",
                       "Annie Joins Up"])[2], 6)
        self.assertEqual(
            self._run(["Tifa, Martial Artist", "Big Attacker"])[2], 4)
        self.assertEqual(
            self._run(["Tifa, Martial Artist", "Big Attacker",
                       "Annie Joins Up"])[2], 6)

    def test_four_combat_phases_is_the_cap(self):
        # Aurelia + Tifa under Annie queue four extra combats; only three fit.
        combat = self._run(["Aurelia, the Warleader", "Tifa, Martial Artist",
                            "Big Attacker", "Annie Joins Up"])
        self.assertEqual(combat[2], 12)

    def test_a_mana_creature_aggravated_assault_needs_stays_home_for_it(self):
        # Turn 2: two Forests, two Ruby Crystals and Probe Red Dork's {R} are
        # exactly {3}{R}{R}. The Dork stays home in the first combat (Attacker
        # A alone: 1), pays for Aggravated Assault, which untaps the
        # creatures: both attack in the second combat (2). Attacking first,
        # the Dork could not pay: one combat of 2; paying after attacking, 4.
        combat = self._run(["Aggravated Assault", "Attacker A", "Probe Red Dork"], crystals=2)
        self.assertEqual(combat[2], 3)

    def test_aggravated_assault_is_paid_from_the_remaining_pool(self):
        # {3}{R}{R} per extra combat. Turn 2 the pool is two Forests plus the
        # Ruby Crystals that landed on turn 1.
        self.assertEqual(
            self._run(["Aggravated Assault", "Attacker A", "Attacker B"],
                      crystals=2)[2], 2)
        self.assertEqual(
            self._run(["Aggravated Assault", "Attacker A", "Attacker B"],
                      crystals=3)[2], 4)

    def test_aggravated_assault_repeats_while_the_pool_allows(self):
        self.assertEqual(
            self._run(["Aggravated Assault", "Attacker A", "Attacker B"],
                      crystals=8)[2], 6)
        # Pool for four more activations, but the phase cap stops it at four.
        self.assertEqual(
            self._run(["Aggravated Assault", "Attacker A", "Attacker B"],
                      crystals=20)[2], 8)

    def test_zopandrel_compounds_across_the_turns_combat_phases(self):
        # Three attackers at combat 1: phase 0 doubles to 2 each (6), phase 1
        # doubles again to 4 each (12) = 18 for the turn.
        combat = self._run(["Zopandrel, Hunger Dominus",
                            "Aurelia, the Warleader", "Attacker A"])
        self.assertEqual(combat[2], 18)
        # Without the extra combat it is one doubling: 3 attackers x 2.
        self.assertEqual(
            self._run(["Zopandrel, Hunger Dominus", "Attacker A",
                       "Attacker B"])[2], 6)

    def test_raphael_doubles_every_phase(self):
        self.assertEqual(
            self._run(["Raphael, the Nightwatcher", "Attacker A",
                       "Attacker B"])[2], 6)
        # Three attackers doubled in each of Aurelia's two phases.
        self.assertEqual(
            self._run(["Raphael, the Nightwatcher", "Aurelia, the Warleader",
                       "Attacker A"])[2], 12)

    def test_xenagos_doubles_one_attacker_per_phase(self):
        # Four equal attackers (Xenagos included): one of the other three is
        # doubled each phase, so 4 + 1 = 5.
        self.assertEqual(
            self._run(["Xenagos, God of Revels", "Attacker A", "Attacker B",
                       "Big Attacker"])[2], 5)


class CastPriorityHoldTests(unittest.TestCase):
    """DEC-944 — the goldfish holds mana for the turn's line.

    Two pinned synthetic decks, built like the DEC-938/940 harnesses: the
    opening hand and library are fixed by patching the mulligan, so each run is
    deterministic and every assertion is about one sequencing decision.
    """

    HATCH_DECK_ID = "broodfire-hatchery"
    HATCH_COMMANDER = "Atla Palani, Nest Tender"

    @staticmethod
    def _forest() -> dict:
        return {
            "name": "Forest", "type_line": "Basic Land — Forest",
            "oracle_text": "({T}: Add {G}.)", "mana_cost": "", "cmc": 0,
            "colors": [], "color_identity": ["G"], "produced_mana": ["G"],
        }

    # --- (c) engine activations: holding {2} beats casting a two-drop --------

    def _hatch_metadata(self) -> dict:
        metadata = {
            "Forest": self._forest(),
            self.HATCH_COMMANDER: {
                "name": self.HATCH_COMMANDER,
                "type_line": "Legendary Creature — Human Shaman",
                "oracle_text": "", "mana_cost": "{1}", "cmc": 1,
                "colors": [], "color_identity": ["G"],
            },
            "Ashnod's Altar": {
                "name": "Ashnod's Altar", "type_line": "Artifact",
                "oracle_text": "", "mana_cost": "{0}", "cmc": 0,
                "colors": [], "color_identity": [],
            },
        }
        # The filler the hold has to beat: a plain {2} sorcery, no mana, no
        # combat, so the only reason to cast it is "the mana was there".
        for i in range(10):
            metadata[f"Two Drop {i}"] = {
                "name": f"Two Drop {i}", "type_line": "Sorcery",
                "oracle_text": "", "mana_cost": "{2}", "cmc": 2,
                "colors": [], "color_identity": [],
            }
        for i in range(20):
            metadata[f"Bear {i}"] = {
                "name": f"Bear {i}", "type_line": "Creature — Bear",
                "oracle_text": "", "mana_cost": "{9}", "cmc": 9,
                "colors": [], "color_identity": [],
            }
        return metadata

    def _run_hatch(self, forests_in_hand: int, extra_hand: tuple = ()):
        """Pinned hatch-engine game; returns (hatch turns, casts by turn).

        `extra_hand` names CARDS entries added to the deck and the hand."""
        metadata = self._hatch_metadata()
        metadata.update({name: CARDS[name] for name in extra_hand})
        two_drops = [f"Two Drop {i}" for i in range(10)]
        bears = [f"Bear {i}" for i in range(20)]
        decklist = (["Forest"] * 12 + ["Ashnod's Altar"] + two_drops + bears
                    + list(extra_hand))
        deck_data = {"decklist": [{"name": name} for name in decklist]}
        context = exporter.build_goldfish_context(
            decklist, deck_data, metadata, self.HATCH_COMMANDER, ["G"],
            self.HATCH_DECK_ID)
        hand = (["Forest"] * forests_in_hand + ["Ashnod's Altar"]
                + two_drops[:2] + list(extra_hand))
        # library.pop() draws from the end: Bears sit on top so a hatch finds one.
        library = ["Forest"] * (12 - forests_in_hand) + bears

        hatch_turns = []
        casts = defaultdict(list)
        original_hatch = exporter.hatch_from_library
        original_resolve = exporter.resolve_cast_effects

        def recording_hatch(turn, *args, **kwargs):
            hatch_turns.append(turn)
            return original_hatch(turn, *args, **kwargs)

        def recording_resolve(name, profile, turn, *args, **kwargs):
            casts[turn].append(name)
            return original_resolve(name, profile, turn, *args, **kwargs)

        with patch.object(exporter, "commander_mulligan_goldfish",
                          lambda *_: (list(library), list(hand))), \
                patch.object(exporter, "hatch_from_library", recording_hatch), \
                patch.object(exporter, "resolve_cast_effects", recording_resolve):
            exporter.simulate_goldfish_game(decklist, context, 6)
        return hatch_turns, casts

    def test_two_mana_is_held_for_the_egg_activation(self):
        # Turn 1: Forest, free Altar, {1} commander. Turn 2: second Forest, so
        # exactly {2} is available and the engine is online. The pilot makes an
        # Egg instead of casting the two-drop.
        hatch_turns, casts = self._run_hatch(forests_in_hand=2)
        self.assertEqual(casts[1], [self.HATCH_COMMANDER, "Ashnod's Altar"])
        self.assertNotIn("Two Drop 0", casts[2],
                         "the two-drop ate the activation's mana")
        self.assertIn(2, hatch_turns, "no Egg hatched on the two-mana turn")

    def test_the_hold_is_one_activation_not_a_ban_on_casting(self):
        # Four Forests in hand: turn 4 has {4}, enough for the activation and a
        # two-drop, so both happen. Only one activation is held, not a budget.
        hatch_turns, casts = self._run_hatch(forests_in_hand=4)
        self.assertIn("Two Drop 0", casts[4])
        self.assertIn(4, hatch_turns)

    def test_an_x_spell_pays_x_only_out_of_mana_the_activation_does_not_need(self):
        # Stonecoil Serpent ({X}) joins the hand. Turn 1's Forest casts the
        # commander, so the Serpent gets X = 0 and waits. Turn 2: {2}, all of
        # it held for the Egg activation, so X = 1 or 2 would break the hold
        # and the Serpent waits again while the Egg is made. Turn 3: {3} pays
        # X = 1 and keeps {2} for the activation.
        hatch_turns, casts = self._run_hatch(
            forests_in_hand=4, extra_hand=("Stonecoil Serpent",))
        self.assertEqual(
            ("Stonecoil Serpent" in casts[1] + casts[2], 2 in hatch_turns),
            (False, True))
        self.assertIn("Stonecoil Serpent", casts[3])

    # --- (b) the combo gate -------------------------------------------------

    COMBO_DECK_ID = "synthetic-combo"
    COMBO_COMMANDER = "Synthetic Commander"

    def _combo_metadata(self) -> dict:
        metadata = {
            "Forest": self._forest(),
            self.COMBO_COMMANDER: {
                "name": self.COMBO_COMMANDER,
                "type_line": "Legendary Creature — Human",
                "oracle_text": "", "mana_cost": "{9}", "cmc": 9,
                "colors": [], "color_identity": ["G"],
            },
            # Permanent piece: cast normally, then it waits on the battlefield.
            "Piece Permanent": {
                "name": "Piece Permanent", "type_line": "Artifact",
                "oracle_text": "", "mana_cost": "{2}", "cmc": 2,
                "colors": [], "color_identity": [],
            },
            # Non-permanent piece: reserved from filler casting, so the gate is
            # purely a question of whether {2} is still in the pool.
            "Piece Instant": {
                "name": "Piece Instant", "type_line": "Instant",
                "oracle_text": "", "mana_cost": "{2}", "cmc": 2,
                "colors": [], "color_identity": [],
            },
        }
        for i in range(20):
            metadata[f"Bear {i}"] = {
                "name": f"Bear {i}", "type_line": "Creature — Bear",
                "oracle_text": "", "mana_cost": "{2}", "cmc": 2,
                "colors": [], "color_identity": [],
                "power": "2", "toughness": "2",
            }
        return metadata

    def _run_combo(self, forests_in_hand: int = 3):
        """Pinned combo game; returns (by_turn, casts by turn)."""
        metadata = self._combo_metadata()
        bears = [f"Bear {i}" for i in range(20)]
        decklist = (["Forest"] * 20 + ["Piece Permanent", "Piece Instant"]
                    + bears)
        deck_data = {
            "decklist": [{"name": name} for name in decklist],
            "winConditions": [{
                "kind": "combo",
                "pieces": ["Piece Permanent", "Piece Instant"],
            }],
        }
        context = exporter.build_goldfish_context(
            decklist, deck_data, metadata, self.COMBO_COMMANDER, ["G"],
            self.COMBO_DECK_ID)
        self.assertEqual(len(context["comboLines"]), 1)
        hand = (["Forest"] * forests_in_hand
                + ["Piece Permanent", "Piece Instant"] + bears[:2])
        library = ["Forest"] * (20 - forests_in_hand) + bears[2:]

        casts = defaultdict(list)
        original_resolve = exporter.resolve_cast_effects

        def recording_resolve(name, profile, turn, *args, **kwargs):
            casts[turn].append(name)
            return original_resolve(name, profile, turn, *args, **kwargs)

        with patch.object(exporter, "commander_mulligan_goldfish",
                          lambda *_: (list(library), list(hand))), \
                patch.object(exporter, "resolve_cast_effects", recording_resolve):
            by_turn, _ = exporter.simulate_goldfish_game(
                decklist, context, 6)
        return by_turn, casts

    def test_the_gate_fires_on_the_turn_the_pieces_are_castable(self):
        by_turn, casts = self._run_combo()
        # Turn 2 casts the permanent piece ({2} out of two Forests); the gate
        # still needs {2} for the instant, which turn 2 no longer has.
        self.assertEqual(casts[2], ["Piece Permanent"])
        self.assertEqual(by_turn[2]["comboLethal"], 0)
        # Turn 3 brings the pool to {3}. A Bear is affordable and would leave
        # {1}, so it is held back and the gate fires instead.
        self.assertEqual(casts[3], [])
        self.assertEqual(by_turn[3]["comboLethal"], 1)

    def test_filler_resumes_once_the_gate_has_fired(self):
        # comboLethal is sticky, so from turn 4 on there is nothing left to
        # protect and the Bears get cast again.
        _, casts = self._run_combo()
        self.assertEqual(casts[4], ["Bear 0"])

    # --- the combo gate with a startPiece ------------------------------------

    def _run_start_piece_combo(self, hand: list, library_top: list):
        """Pinned game for a start piece and its partner on turn 1.

        A free rock that adds {G}{G}{G} makes turn 1 a four-mana turn: the {1}
        start piece and the {2} partner both fit with {1} left over. A free
        cantrip can draw the partner mid-turn. Every other spell costs {9}, so
        nothing else competes for the mana. ``library_top`` is drawn first.
        """
        metadata = {
            "Forest": self._forest(),
            self.COMBO_COMMANDER: {
                "name": self.COMBO_COMMANDER,
                "type_line": "Legendary Creature — Human",
                "oracle_text": "", "mana_cost": "{9}", "cmc": 9,
                "colors": [], "color_identity": ["G"],
            },
            "Triple Rock": {
                "name": "Triple Rock", "type_line": "Artifact",
                "oracle_text": "{T}: Add {G}{G}{G}.", "mana_cost": "{0}", "cmc": 0,
                "colors": [], "color_identity": ["G"],
            },
            "Start Top": {
                "name": "Start Top", "type_line": "Artifact",
                "oracle_text": "", "mana_cost": "{1}", "cmc": 1,
                "colors": [], "color_identity": [],
            },
            "Partner Forge": {
                "name": "Partner Forge", "type_line": "Artifact",
                "oracle_text": "", "mana_cost": "{2}", "cmc": 2,
                "colors": [], "color_identity": [],
            },
            "Cantrip": {
                "name": "Cantrip", "type_line": "Sorcery",
                "oracle_text": "Draw a card.", "mana_cost": "{0}", "cmc": 0,
                "colors": [], "color_identity": [],
            },
        }
        fillers = [f"Filler {i}" for i in range(10)]
        for name in fillers:
            metadata[name] = {
                "name": name, "type_line": "Sorcery", "oracle_text": "",
                "mana_cost": "{9}", "cmc": 9, "colors": [], "color_identity": [],
            }
        decklist = (["Forest"] * 11
                    + ["Triple Rock", "Start Top", "Partner Forge", "Cantrip"]
                    + fillers)
        deck_data = {
            "decklist": [{"name": name} for name in decklist],
            "winConditions": [{
                "title": "Start Loop",
                "kind": "combo",
                "pieces": ["Start Top", "Partner Forge"],
                "startPiece": "Start Top",
            }],
        }
        context = exporter.build_goldfish_context(
            decklist, deck_data, metadata, self.COMBO_COMMANDER, ["G"],
            self.COMBO_DECK_ID)
        # library.pop() draws from the end: library_top first, then a Forest
        # every turn.
        library = fillers + ["Forest"] * 10 + list(reversed(library_top))

        casts = defaultdict(list)
        original_resolve = exporter.resolve_cast_effects

        def recording_resolve(name, profile, turn, *args, **kwargs):
            casts[turn].append(name)
            return original_resolve(name, profile, turn, *args, **kwargs)

        with patch.object(exporter, "commander_mulligan_goldfish",
                          lambda *_: (list(library), list(hand))), \
                patch.object(exporter, "resolve_cast_effects", recording_resolve):
            by_turn, _ = exporter.simulate_goldfish_game(
                decklist, context, 6)
        return by_turn, casts

    def test_start_piece_cast_before_its_partner_waits_a_turn(self):
        by_turn, casts = self._run_start_piece_combo(
            ["Forest", "Triple Rock", "Start Top", "Partner Forge"], [])
        # Cheapest line member first: the start piece lands before its partner.
        self.assertEqual(casts[1], ["Triple Rock", "Start Top", "Partner Forge"])
        # {1} is left over, but the start piece entered before its partner, so
        # the loop cannot be started this turn.
        self.assertEqual(by_turn[1]["comboLethal"], 0)
        # Turn 2: nothing else is cast and the start piece's {1} is available.
        self.assertEqual(casts[2], [])
        self.assertEqual(by_turn[2]["comboLethal"], 1)

    def test_partner_drawn_after_the_start_piece_waits_a_turn(self):
        # The turn-1 draw step takes a Forest, so the partner is not in hand
        # and the start piece is cast; the cantrip then draws the partner,
        # which is cast the same turn. The start piece entered before its
        # partner, so the loop waits a turn although {1} is left over, and
        # starts on turn 2 by paying the start piece again.
        by_turn, casts = self._run_start_piece_combo(
            ["Forest", "Triple Rock", "Start Top", "Cantrip"], ["Forest", "Partner Forge"])
        self.assertEqual(casts[1],
                         ["Triple Rock", "Start Top", "Cantrip", "Partner Forge"])
        self.assertEqual(by_turn[1]["comboLethal"], 0)
        self.assertEqual(casts[2], [])
        self.assertEqual(by_turn[2]["comboLethal"], 1)


class ComboStartPieceTests(unittest.TestCase):
    """A combo line's ``startPiece`` is cast to start the loop.

    Shaped on titan-convergence's Sensei's Divining Top loops (Commander
    Spellbook 985-5078-5705 and 5078-5642-5705, both ``manaNeeded`` {1}): the
    loop starts with a Top cast while the other pieces are out. A Top on the
    battlefield is free only when it was the last of the line's pieces to enter
    and it entered this turn; one out since an earlier turn pays its cost
    again; one that entered this turn before a partner cannot restart the loop
    that turn, and neither can a Top that only reanimation could deliver.
    Synthetic pieces: {1} start piece, {4} and {2} partners, a {3} unrelated
    artifact, a {2} reanimation spell, a {1} to-graveyard tutor and a {2}
    to-hand tutor. Every board is built through ``resolve_cast_effects``, the
    path the goldfish uses to put a cast permanent on the battlefield, in the
    order listed.
    """

    TURN = 5
    COMMANDER = "Synthetic Commander"
    DECKLIST = [
        {"name": "Top Piece"},
        {"name": "Forge Piece"},
        {"name": "Raker Piece"},
        {"name": "Other Artifact"},
        {"name": "Reanimate Piece", "primary_role": "recursion"},
        {"name": "Entomb Piece", "primary_role": "tutor",
         "tutor_mode": "to_graveyard"},
        {"name": "Tutor Piece", "primary_role": "tutor"},
    ]
    WINCON = {
        "title": "Top Loop",
        "kind": "combo",
        "pieces": ["Top Piece", "Forge Piece", "Raker Piece"],
        "startPiece": "Top Piece",
    }
    PLAIN = {"title": "Top Loop", "kind": "combo",
             "pieces": ["Top Piece", "Forge Piece", "Raker Piece"]}
    # A second line that is never ready: nothing can supply Other Artifact.
    OTHER = {"title": "Other Loop", "kind": "combo",
             "pieces": ["Other Artifact", "Forge Piece"]}
    # A second start-piece line sharing the start piece.
    SECOND = {"title": "Second Loop", "kind": "combo",
              "pieces": ["Top Piece", "Other Artifact", "Raker Piece"],
              "startPiece": "Top Piece"}

    @staticmethod
    def _metadata() -> dict:
        def card(name, type_line, mana_cost, cmc):
            return {
                "name": name, "type_line": type_line, "oracle_text": "",
                "mana_cost": mana_cost, "cmc": cmc, "colors": [],
                "color_identity": [],
            }

        return {
            "Synthetic Commander": card("Synthetic Commander",
                                        "Legendary Creature — Eldrazi",
                                        "{9}", 9),
            "Top Piece": card("Top Piece", "Artifact", "{1}", 1),
            "Forge Piece": card("Forge Piece", "Artifact", "{4}", 4),
            "Raker Piece": card("Raker Piece", "Artifact", "{2}", 2),
            "Other Artifact": card("Other Artifact", "Artifact", "{3}", 3),
            "Reanimate Piece": card("Reanimate Piece", "Sorcery", "{2}", 2),
            "Entomb Piece": card("Entomb Piece", "Instant", "{1}", 1),
            "Tutor Piece": card("Tutor Piece", "Sorcery", "{2}", 2),
        }

    def _context(self, wincons: list) -> dict:
        deck_data = {
            "decklist": [dict(entry) for entry in self.DECKLIST],
            "winConditions": [dict(wincon) for wincon in wincons],
        }
        return exporter.build_goldfish_context(
            [entry["name"] for entry in self.DECKLIST], deck_data,
            self._metadata(), self.COMMANDER, ["G"], "synthetic-start-piece")

    def _board(self, context: dict, entries: list) -> list[dict]:
        """Resolve each (name, cast turn) onto the battlefield, in order."""
        permanents = []
        for name, cast_turn in entries:
            exporter.resolve_cast_effects(
                name, context["profiles"][name], cast_turn,
                exporter.GoldfishManaPool([]), [], [], permanents, [],
                context["profiles"], ["G"])
        return permanents

    EARLIER_BOARD = [("Top Piece", 3), ("Forge Piece", 4), ("Raker Piece", 4)]
    PARTNERS_OUT = [("Forge Piece", 4), ("Raker Piece", 4)]
    RAKER_MISSING = [("Top Piece", 3), ("Forge Piece", 3)]
    TOP_LAST_LAST_TURN = [("Forge Piece", 3), ("Raker Piece", 3), ("Top Piece", 4)]
    TOP_BEFORE_PARTNER = [("Raker Piece", 3), ("Top Piece", 5), ("Forge Piece", 5)]
    SPARE = 9

    # (label, win conditions, hand, battlefield [(name, cast turn)] in entry
    #  order, mana in the pool, ready). TURN is 5.
    READY_CASES = [
        ("start piece out since turn 3, empty pool",
         [WINCON], [], EARLIER_BOARD, 0, False),
        ("start piece out since turn 3, pool holds its {1}",
         [WINCON], [], EARLIER_BOARD, 1, True),
        ("start piece last to enter but on turn 4, empty pool",
         [WINCON], [], TOP_LAST_LAST_TURN, 0, False),
        ("start piece last to enter but on turn 4, pool holds its {1}",
         [WINCON], [], TOP_LAST_LAST_TURN, 1, True),
        ("start piece out since turn 3, a partner cast this turn, empty pool",
         [WINCON], [], [("Top Piece", 3), ("Raker Piece", 3), ("Forge Piece", 5)],
         0, False),
        ("start piece last to enter on turn 4, unrelated permanent cast this "
         "turn, empty pool",
         [WINCON], [], TOP_LAST_LAST_TURN + [("Other Artifact", 5)], 0, False),
        ("start piece cast this turn before a partner cast this turn, spare mana",
         [WINCON], [], TOP_BEFORE_PARTNER, SPARE, False),
        ("start piece cast this turn after both partners from turn 3, empty pool",
         [WINCON], [], [("Forge Piece", 3), ("Raker Piece", 3), ("Top Piece", 5)],
         0, True),
        ("start piece cast this turn after both partners cast this turn, "
         "empty pool",
         [WINCON], [], [("Forge Piece", 5), ("Raker Piece", 5), ("Top Piece", 5)],
         0, True),
        ("start piece cast this turn last, then an unrelated permanent cast "
         "this turn, empty pool",
         [WINCON], [], [("Forge Piece", 3), ("Raker Piece", 3), ("Top Piece", 5),
                        ("Other Artifact", 5)], 0, True),
        ("start piece cast this turn, {4} partner still in hand, spare mana",
         [WINCON], ["Forge Piece"], [("Raker Piece", 3), ("Top Piece", 5)],
         SPARE, False),
        ("start piece out since turn 3, {4} piece in hand, pool {4}",
         [WINCON], ["Forge Piece"], [("Top Piece", 3), ("Raker Piece", 4)], 4,
         False),
        ("start piece out since turn 3, {4} piece in hand, pool {5}",
         [WINCON], ["Forge Piece"], [("Top Piece", 3), ("Raker Piece", 4)], 5,
         True),
        ("start piece only reachable by reanimation, spare mana",
         [WINCON], ["Reanimate Piece"], PARTNERS_OUT, SPARE, False),
        ("start piece only reachable by to_graveyard tutor + reanimation, "
         "spare mana",
         [WINCON], ["Entomb Piece", "Reanimate Piece"], PARTNERS_OUT, SPARE,
         False),
        ("start piece by to_hand tutor, to_graveyard tutor also in hand, "
         "pool {2} + its {1}",
         [WINCON], ["Entomb Piece", "Reanimate Piece", "Tutor Piece"],
         PARTNERS_OUT, 3, True),
        ("start piece by to_hand tutor, to_graveyard tutor also in hand, "
         "pool holds only the {2} tutor",
         [WINCON], ["Entomb Piece", "Reanimate Piece", "Tutor Piece"],
         PARTNERS_OUT, 2, False),
        ("start piece out since turn 3, partner reanimated, pool {2} + its {1}",
         [WINCON], ["Reanimate Piece"], RAKER_MISSING, 3, True),
        ("start piece in hand, pool holds its {1}",
         [WINCON], ["Top Piece"], PARTNERS_OUT, 1, True),
        ("start piece in hand, empty pool",
         [WINCON], ["Top Piece"], PARTNERS_OUT, 0, False),
        ("start line plus a line without startPiece, start piece out since "
         "turn 3, empty pool",
         [WINCON, OTHER], [], EARLIER_BOARD, 0, False),
        ("start line plus a line without startPiece, start piece cast this "
         "turn last, empty pool",
         [WINCON, OTHER], [], [("Forge Piece", 3), ("Raker Piece", 3),
                               ("Top Piece", 5)], 0, True),
        ("first line refused, second line's start piece entered last, "
         "empty pool",
         [WINCON, SECOND], [], [("Raker Piece", 3), ("Other Artifact", 3),
                                ("Top Piece", 5), ("Forge Piece", 5)], 0, True),
        ("no startPiece, all pieces out since an earlier turn, empty pool",
         [PLAIN], [], EARLIER_BOARD, 0, True),
        ("no startPiece, Top cast this turn before a partner, empty pool",
         [PLAIN], [], TOP_BEFORE_PARTNER, 0, True),
        ("no startPiece, partner reanimated, pool holds exactly its {2}",
         [PLAIN], ["Reanimate Piece"], RAKER_MISSING, 2, True),
        ("no startPiece, partner entombed and reanimated, pool exactly {1} + {2}",
         [PLAIN], ["Entomb Piece", "Reanimate Piece"], RAKER_MISSING, 3, True),
    ]

    def test_combo_ready_charges_a_start_piece_already_on_the_battlefield(self):
        for label, wincons, hand, board, mana, expected in self.READY_CASES:
            with self.subTest(label):
                context = self._context(wincons)
                ready = exporter.combo_ready_this_turn(
                    turn=self.TURN, hand=list(hand),
                    permanents=self._board(context, board),
                    combo_lines=context["comboLines"],
                    profiles=context["profiles"],
                    tutor_meta=context["tutorMeta"],
                    reanim_names=context["reanimationNames"],
                    commander_in_play=False, commander_play_turn=None,
                    pool=exporter.GoldfishManaPool([frozenset({"G"})] * mana),
                    commander_name=self.COMMANDER)
                self.assertEqual(ready, expected)

    def test_extract_combo_lines_carries_the_start_piece(self):
        lines = self._context([self.WINCON])["comboLines"]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["startPiece"], "Top Piece")

    def test_extract_combo_lines_line_without_start_piece_has_none(self):
        lines = self._context([self.PLAIN])["comboLines"]
        self.assertEqual(len(lines), 1)
        self.assertIsNone(lines[0]["startPiece"])

    def test_extract_combo_lines_rejects_a_start_piece_outside_pieces(self):
        profiles = self._context([self.WINCON])["profiles"]
        deck_data = {"winConditions": [
            dict(self.WINCON, startPiece="Sensei's Divining Top")]}
        with self.assertRaisesRegex(ValueError, "'Top Loop'"):
            exporter.extract_combo_lines(deck_data, profiles)


class ComboLineMinXTests(unittest.TestCase):
    """A combo line's ``minX`` (owner-approved 2026-11-19): the X a piece with
    {X} in its cost is priced at, the cheapest direct cast with which the
    line's listed pieces work.

    Shaped on the-white-forge's Heliod, Sun-Crowned + Walking Ballista
    (priced at X = 2) and eternal-harvest's Walking Ballista + Mikaeus, the
    Unhallowed (X = 1). X Piece carries Walking Ballista's cost and text
    ({X}{X}: X = 2 costs 4 mana, X = 1 costs 2); the text reads as
    interaction, so the cast loop never casts it, as with Ballista. Partner
    Piece {3}, an unrelated {1} enchantment (it makes the bargain path live),
    a {2} to-hand tutor, a {1} to-graveyard tutor, a {2} reanimation spell
    and a {1} bargain tutor. The piece is priced at minX in hand, through a
    to-hand tutor and through the bargain tutor's paid route to the hand;
    reanimation, the to-graveyard tutor and the bargain free cast do not
    supply it. Every board is built through ``resolve_cast_effects``.
    """

    TURN = 5
    COMMANDER = "Synthetic Commander"
    BALLISTA_TEXT = ("This creature enters with X +1/+1 counters on it.\n{4}: Put a +1/+1 counter on "
                     "this creature.\nRemove a +1/+1 counter from this creature: It deals 1 damage "
                     "to any target.")
    DECKLIST = [
        {"name": "X Piece"},
        {"name": "Partner Piece"},
        {"name": "Other Enchantment"},
        {"name": "Tutor Piece", "primary_role": "tutor"},
        {"name": "Entomb Piece", "primary_role": "tutor", "tutor_mode": "to_graveyard"},
        {"name": "Reanimate Piece", "primary_role": "recursion"},
        {"name": "Beseech Piece", "primary_role": "tutor", "tutor_free_cast_via_bargain": True},
    ]
    MINX = {"title": "X Loop", "kind": "combo", "pieces": ["Partner Piece", "X Piece"],
            "minX": {"X Piece": 2}}
    MINX_1 = dict(MINX, minX={"X Piece": 1})
    PLAIN = {"title": "X Loop", "kind": "combo", "pieces": ["Partner Piece", "X Piece"]}
    # The X piece as the start piece: out since turn 4, its cost is paid again.
    START = dict(MINX, startPiece="X Piece")

    @classmethod
    def _metadata(cls) -> dict:
        def card(name, type_line, mana_cost, cmc, text=""):
            return {"name": name, "type_line": type_line, "oracle_text": text, "mana_cost": mana_cost,
                    "cmc": cmc, "colors": [], "color_identity": []}

        return {
            cls.COMMANDER: card(cls.COMMANDER, "Legendary Creature — Eldrazi", "{9}", 9),
            "X Piece": card("X Piece", "Artifact Creature — Construct", "{X}{X}", 0, cls.BALLISTA_TEXT),
            "Partner Piece": card("Partner Piece", "Artifact", "{3}", 3),
            "Other Enchantment": card("Other Enchantment", "Enchantment", "{1}", 1),
            "Tutor Piece": card("Tutor Piece", "Sorcery", "{2}", 2),
            "Entomb Piece": card("Entomb Piece", "Instant", "{1}", 1),
            "Reanimate Piece": card("Reanimate Piece", "Sorcery", "{2}", 2),
            "Beseech Piece": card("Beseech Piece", "Sorcery", "{1}", 1),
        }

    def _context(self, wincons: list) -> dict:
        deck_data = {"decklist": [dict(entry) for entry in self.DECKLIST],
                     "winConditions": [dict(wincon) for wincon in wincons]}
        return exporter.build_goldfish_context(
            [entry["name"] for entry in self.DECKLIST], deck_data, self._metadata(), self.COMMANDER,
            ["G"], "synthetic-min-x")

    def _board(self, context: dict, entries: list) -> list[dict]:
        permanents = []
        for name, cast_turn in entries:
            exporter.resolve_cast_effects(name, context["profiles"][name], cast_turn,
                                          exporter.GoldfishManaPool([]), [], [], permanents, [],
                                          context["profiles"], ["G"])
        return permanents

    PARTNER_OUT = [("Partner Piece", 3)]
    BARGAIN_BOARD = [("Partner Piece", 3), ("Other Enchantment", 3)]
    SPARE = 9

    # (label, win condition, hand, battlefield [(name, cast turn)], mana in
    #  the pool, ready). TURN is 5. Costs by hand: X Piece at X = 2 is 4 mana,
    # at X = 1 is 2 mana, at X = 0 nothing.
    READY_CASES = [
        ("minX 2, X piece in hand, pool 3", MINX, ["X Piece"], PARTNER_OUT, 3, False),
        ("minX 2, X piece in hand, pool 4", MINX, ["X Piece"], PARTNER_OUT, 4, True),
        ("minX 1, X piece in hand, pool 1", MINX_1, ["X Piece"], PARTNER_OUT, 1, False),
        ("minX 1, X piece in hand, pool 2", MINX_1, ["X Piece"], PARTNER_OUT, 2, True),
        ("minX 2, both pieces in hand, pool {3} + 4 - 1", MINX, ["X Piece", "Partner Piece"], [], 6, False),
        ("minX 2, both pieces in hand, pool {3} + 4", MINX, ["X Piece", "Partner Piece"], [], 7, True),
        ("minX 2, to-hand tutor, pool {2} + 4 - 1", MINX, ["Tutor Piece"], PARTNER_OUT, 5, False),
        ("minX 2, to-hand tutor, pool {2} + 4", MINX, ["Tutor Piece"], PARTNER_OUT, 6, True),
        ("minX 2, reanimation only, spare mana", MINX, ["Reanimate Piece"], PARTNER_OUT, SPARE, False),
        ("minX 2, to-graveyard tutor and reanimation, spare mana", MINX, ["Entomb Piece", "Reanimate Piece"],
         PARTNER_OUT, SPARE, False),
        # The bargain tutor's free cast (X = 0) does not supply the piece; its
        # paid route to the hand does, bargained or not: {1} + 4.
        ("minX 2, bargain tutor with an enchantment out, pool {1} + 4 - 1", MINX, ["Beseech Piece"],
         BARGAIN_BOARD, 4, False),
        ("minX 2, bargain tutor with an enchantment out, pool {1} + 4", MINX, ["Beseech Piece"],
         BARGAIN_BOARD, 5, True),
        ("minX 2, bargain tutor with nothing to bargain, pool {1} + 4", MINX, ["Beseech Piece"],
         PARTNER_OUT, 5, True),
        ("minX 2 start piece out since turn 4, pool 3", START, [], PARTNER_OUT + [("X Piece", 4)], 3, False),
        ("minX 2 start piece out since turn 4, pool 4", START, [], PARTNER_OUT + [("X Piece", 4)], 4, True),
        ("no minX, X piece in hand, empty pool", PLAIN, ["X Piece"], PARTNER_OUT, 0, True),
        ("no minX, to-hand tutor, pool {2}", PLAIN, ["Tutor Piece"], PARTNER_OUT, 2, True),
        ("no minX, reanimation, pool {2}", PLAIN, ["Reanimate Piece"], PARTNER_OUT, 2, True),
        ("no minX, to-graveyard tutor and reanimation, pool {1} + {2}", PLAIN,
         ["Entomb Piece", "Reanimate Piece"], PARTNER_OUT, 3, True),
        ("no minX, bargain tutor with an enchantment out, pool {1}", PLAIN, ["Beseech Piece"], BARGAIN_BOARD,
         1, True),
    ]

    def test_the_gate_prices_an_x_piece_at_its_lines_min_x(self):
        for label, wincon, hand, board, mana, expected in self.READY_CASES:
            with self.subTest(label):
                context = self._context([wincon])
                ready = exporter.combo_ready_this_turn(
                    turn=self.TURN, hand=list(hand), permanents=self._board(context, board),
                    combo_lines=context["comboLines"], profiles=context["profiles"],
                    tutor_meta=context["tutorMeta"], reanim_names=context["reanimationNames"],
                    commander_in_play=False, commander_play_turn=None,
                    pool=exporter.GoldfishManaPool([frozenset({"G"})] * mana),
                    commander_name=self.COMMANDER)
                self.assertEqual(ready, expected)

    def test_extract_combo_lines_carries_min_x_and_the_priced_cost(self):
        line = self._context([self.MINX])["comboLines"][0]
        self.assertEqual(line["minX"], {"X Piece": 2})
        self.assertEqual([(cost["generic"], cost["total"]) for cost in line["costs"]], [(3, 3), (4, 4)])
        plain = self._context([self.PLAIN])["comboLines"][0]
        self.assertEqual((plain["minX"], [cost["total"] for cost in plain["costs"]]), ({}, [3, 0]))

    # (label, the win condition's changes, accepted). The deck holds Walking
    # Ballista ({X}{X}), Heliod, Sun-Crowned ({2}{W}), Endless One ({X}) and
    # Agadeem's Awakening // Agadeem, the Undercrypt ({X}{B}{B}{B} front),
    # listed by its full name; Hangarback Walker ({X}{X}) is a real card
    # outside the deck.
    AGADEEM = "Agadeem's Awakening // Agadeem, the Undercrypt"
    AGREEMENT_CASES = [
        ("pieces as a string", {"pieces": "Walking Ballista", "minX": {"Walking Ballista": 2}}, False),
        ("pieces as a number, with a startPiece and an empty map",
         {"pieces": 1, "startPiece": "Walking Ballista", "minX": {}}, False),
        ("the full name of a double-faced card with {X}",
         {"pieces": [AGADEEM, "Heliod, Sun-Crowned"], "minX": {AGADEEM: 1}}, True),
        ("a face name of a card the deck lists by its full name",
         {"pieces": ["Agadeem's Awakening", "Heliod, Sun-Crowned"], "minX": {"Agadeem's Awakening": 1}}, False),
        ("a valid map", {"minX": {"Walking Ballista": 2}}, True),
        ("an empty map", {"minX": {}}, True),
        ("an empty list", {"minX": []}, False),
        ("a list of names", {"minX": ["Walking Ballista"]}, False),
        ("a number", {"minX": 2}, False),
        ("on an entry with no kind", {"kind": None, "minX": {"Walking Ballista": 2}}, False),
        ("an {X} card in the deck, not one of the line's pieces", {"minX": {"Endless One": 1}}, False),
        ("a piece that is not in the deck", {"pieces": ["Walking Ballista", "Hangarback Walker"],
                                              "minX": {"Hangarback Walker": 1}}, False),
        ("a piece with no {X}", {"minX": {"Heliod, Sun-Crowned": 1}}, False),
        ("zero", {"minX": {"Walking Ballista": 0}}, False),
        ("negative", {"minX": {"Walking Ballista": -1}}, False),
        ("a string", {"minX": {"Walking Ballista": "2"}}, False),
        ("a boolean", {"minX": {"Walking Ballista": True}}, False),
        ("a float", {"minX": {"Walking Ballista": 2.0}}, False),
    ]

    def test_the_validator_and_the_exporter_accept_the_same_min_x(self):
        validator = importlib.import_module("scripts.validate_deck_json")
        costs = {"Walking Ballista": "{X}{X}", "Heliod, Sun-Crowned": "{2}{W}", "Endless One": "{X}",
                 "Hangarback Walker": "{X}{X}", "Synthetic Commander": "{9}"}
        types = {"Walking Ballista": "Artifact Creature — Construct",
                 "Heliod, Sun-Crowned": "Legendary Enchantment Creature — God",
                 "Endless One": "Creature — Eldrazi", "Hangarback Walker": "Artifact Creature — Construct",
                 "Synthetic Commander": "Legendary Creature — Eldrazi"}
        agadeem = self.AGADEEM
        index = validator.ScryfallNameIndex(
            dict({name: name for name in costs}, **{agadeem: agadeem, "Agadeem's Awakening": agadeem}),
            dict(costs, **{agadeem: "{X}{B}{B}{B}"}))
        # Both readers get the same deck: the exporter's profiles are every
        # card the deck lists, Agadeem's Awakening by its full name.
        decklist = ["Walking Ballista", "Heliod, Sun-Crowned", "Endless One", agadeem]
        metas = {name: {"type_line": types[name], "mana_cost": costs[name], "oracle_text": "", "colors": [],
                        "cmc": 0} for name in decklist[:3] + [self.COMMANDER]}
        metas[agadeem] = {"type_line": "Sorcery // Land", "mana_cost": "{X}{B}{B}{B} // ", "oracle_text": "",
                          "colors": ["B"], "cmc": 3, "layout": "modal_dfc",
                          "back_face": {"type_line": "Land", "oracle_text": "{T}: Add {B}."}}
        profiles = {name: exporter.build_goldfish_profile(name, meta, set(), ["W", "B"], self.COMMANDER)
                    for name, meta in metas.items()}
        for label, changes, accepted in self.AGREEMENT_CASES:
            with self.subTest(label):
                wincon = {"title": "Loop", "kind": "combo", "cards": ["Walking Ballista", "Heliod, Sun-Crowned"],
                          "pieces": ["Walking Ballista", "Heliod, Sun-Crowned"]}
                wincon.update(changes)
                deck = {"id": "test-deck", "commander": self.COMMANDER, "winConditions": [wincon],
                        "decklist": [{"name": name} for name in decklist]}
                with tempfile.TemporaryDirectory() as tmpdir:
                    deck_file = Path(tmpdir) / "deck.json"
                    deck_file.write_text(json.dumps(deck))
                    issues = validator.validate_deck_json([deck_file], index)
                try:
                    exporter.extract_combo_lines(deck, profiles)
                    exported = True
                except ValueError as error:
                    self.assertIn("'Loop'", str(error))
                    exported = False
                self.assertEqual(([issue.issue_type for issue in issues], exported),
                                 ([] if accepted else ["invalid_min_x"], accepted))

    def test_the_cast_loop_holds_the_x_piece_cost_for_the_gate(self):
        """Pinned game. Turn 1-2: Forests and {1} fillers (the gate needs {3}
        + 4, out of reach). Turn 3: Partner Piece takes the three Forests; the
        gate is the X piece at X = 2, 4 mana, not payable. Turn 4: four
        Forests, a {1} filler in hand: casting it would leave 3, so it is held
        and the gate fires. Turn 5: the gate has fired; the filler is cast."""
        metadata = dict(self._metadata(), Forest=CastPriorityHoldTests._forest())
        fillers = [f"Filler {i}" for i in range(4)]
        bears = [f"Bear {i}" for i in range(10)]
        for name in fillers:
            metadata[name] = {"name": name, "type_line": "Sorcery", "oracle_text": "", "mana_cost": "{1}",
                              "cmc": 1, "colors": [], "color_identity": []}
        for name in bears:
            metadata[name] = {"name": name, "type_line": "Sorcery", "oracle_text": "", "mana_cost": "{9}",
                              "cmc": 9, "colors": [], "color_identity": []}
        hand = ["Forest", "X Piece", "Partner Piece"] + fillers
        library = bears + ["Forest"] * 8
        decklist = hand + library
        deck_data = {"decklist": [{"name": name} for name in decklist], "winConditions": [dict(self.MINX)]}
        context = exporter.build_goldfish_context(decklist, deck_data, metadata, self.COMMANDER, ["G"],
                                                  "synthetic-min-x")
        self.assertTrue(context["profiles"]["X Piece"]["isInteraction"])
        casts = defaultdict(list)
        original_resolve = exporter.resolve_cast_effects

        def recording_resolve(name, profile, turn, *args, **kwargs):
            casts[turn].append(name)
            return original_resolve(name, profile, turn, *args, **kwargs)

        with patch.object(exporter, "commander_mulligan_goldfish", lambda *_: (list(library), list(hand))), \
                patch.object(exporter, "resolve_cast_effects", recording_resolve):
            by_turn, _ = exporter.simulate_goldfish_game(decklist, context, 6)
        self.assertEqual([casts[turn] for turn in (1, 2, 3, 4, 5)],
                         [["Filler 0"], ["Filler 1", "Filler 2"], ["Partner Piece"], [], ["Filler 3"]])
        self.assertEqual([by_turn[turn]["comboLethal"] for turn in (3, 4)], [0, 1])


class ControlDeckGoldfishEqualityTests(unittest.TestCase):
    """DEC-944 — a deck with no combo and no engine config is untouched.

    ``gathering-shadow`` has no ``winConditions[] kind:'combo'`` entry, no
    KEY_COMBOS line and no hatch/combat-modifier config, so it has no gates to
    protect and no activations to hold: every DEC-944 branch is inert and the
    whole goldfish section must still reproduce the checked-in numbers. The
    goldfish run is seeded per chunk, so this is an exact comparison; the pool
    is mapped serially here to keep the test single-process.
    """

    DECK_ID = "gathering-shadow"
    COLORS = ["U", "B", "R"]

    def test_control_deck_goldfish_section_is_unchanged(self):
        root = Path(__file__).resolve().parent.parent
        deck_data = json.loads(
            (root / "data" / "commanders" / self.DECK_ID / "deck.json").read_text())
        decklist = [card["name"]
                    for card in deck_data["decklist"]
                    for _ in range(card.get("quantity", 1))]
        metadata = json.loads(Path(exporter.METADATA_FILE).read_text())
        context = exporter.build_goldfish_context(
            decklist, deck_data, metadata, deck_data["commander"],
            self.COLORS, self.DECK_ID)
        self.assertEqual(context["comboLines"], [])
        self.assertEqual(context["assemblyLines"], [])
        self.assertIsNone(context["hatchEngine"])
        self.assertIsNone(context["combatModifiers"])
        self.assertIsNone(context["tokenMakers"])

        with patch("multiprocessing.Pool", SerialPool):
            goldfish, _ = exporter.compute_goldfish_section(
                decklist=decklist, deck_data=deck_data, metadata=metadata,
                commander_name=deck_data["commander"],
                commander_colors=self.COLORS, deck_id=self.DECK_ID)

        checked_in = json.loads(
            (root / "data" / "commanders" / self.DECK_ID
             / "simulation.json").read_text())["goldfish"]
        for key in ("byTurn", "speed", "commanderCurve", "numGames"):
            if key in checked_in:
                with self.subTest(key=key):
                    self.assertEqual(goldfish[key], checked_in[key])
