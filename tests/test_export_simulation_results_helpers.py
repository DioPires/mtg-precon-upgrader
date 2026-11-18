import importlib
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
            [], [], {name: profile}, {name: meta}, ["U", "B", "R"])
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
            exporter.simulate_goldfish_game(decklist, CARDS, context, 6)
        return sizes + [len(library)]

    def _engine_card_sizes(self, card, deck_id):
        return self._library_sizes(deck_id, [card] + ["Island"] * 6, ["Island"] * 92)

    def test_jace_draws_three_at_the_start_of_each_later_turn(self):
        # Turns 2-4 draw 1 (draw step); Jace adds nothing on turn 4, his cast
        # turn; turns 5-10 draw 1 + 3.
        for deck_id in ("tidal-legion", "gathering-shadow"):
            with self.subTest(deck=deck_id):
                self.assertEqual(
                    self._engine_card_sizes("The Theorist, Jace Beleren", deck_id),
                    [92, 91, 90, 89, 85, 81, 77, 73, 69, 65, 65])

    def test_one_ring_sequence_is_unchanged(self):
        # Cast on turn 4 and draws 1 then (89 -> 88); turns 5, 6, 7 draw the
        # draw step plus activations 2, 3, 4; then the draw step alone.
        self.assertEqual(
            self._engine_card_sizes("The One Ring", "gandalf-party-guest"),
            [92, 91, 90, 89, 85, 81, 76, 75, 74, 73, 73])

    def test_jace_cards_arrive_before_the_upkeep_tempt(self):
        # gathering-shadow: Call of the Ring tempts at upkeep while the
        # commander is out, and the tempt converts to discard-hand-draw-four
        # only at hand size 2 or less. Hand: Jace, Call of the Ring, a Swamp
        # and four Islands; library: 40 Zero Trinkets ({0}, cast the turn they
        # are drawn, so the hand empties every turn); commander: Probe
        # Commander ({5}). Swamp turn 1, an Island each turn 2-5; Call of the
        # Ring turn 2, Jace turn 4, the commander turn 5.
        # Turn 5 (commander not out yet, no tempt): 37 - 3 - 1 = 33.
        # Turn 6: the hand is empty after turn 5; Jace's 3 cards make it 3, so
        # the upkeep tempt does not convert, and the draw step adds 1:
        # 33 - 3 - 1 = 29. Were the tempt read before Jace's cards, it would
        # convert on the empty hand (draw 4), then Jace 3 and the draw step 1:
        # 25.
        sizes = self._library_sizes(
            "gathering-shadow",
            hand=["The Theorist, Jace Beleren", "Call of the Ring", "Swamp",
                  "Island", "Island", "Island", "Island"],
            library=["Zero Trinket"] * 40,
            commander="Probe Commander", colors=("U", "B"))
        self.assertEqual(sizes[:6], [40, 39, 38, 37, 33, 29])

    def test_the_upkeep_tempt_reads_the_hand_before_the_draw_step(self):
        # gathering-shadow, no Jace. Hand: Call of the Ring, a Swamp and five
        # Islands; library: 39 Zero Trinkets with an Island on top;
        # commander: Probe Commander ({5}). Swamp turn 1; turn 2 draws the
        # Island, plays an Island and casts Call of the Ring; turns 3-5 each
        # draw a Trinket, play an Island and cast the Trinket; turn 5's five
        # lands cast the commander. Turn 6 upkeep: two Islands in hand, so the
        # tempt converts (discard 2, draw 4) and then the draw step draws 1:
        # 36 - 4 - 1 = 31, and the hand holds 4 + 1 = 5 at the land choice.
        # Were the draw step first, the tempt would read 3 cards and not
        # convert: 35 and a hand of 3. Were the discard-and-draw done after
        # the draw step, the library would also read 31 but the hand 4.
        # Hand at each land choice: 7, 7 (the Island drawn), 6, 5, 4, then 5.
        hand_sizes = []
        sizes = self._library_sizes(
            "gathering-shadow",
            hand=["Call of the Ring", "Swamp"] + ["Island"] * 5,
            library=["Zero Trinket"] * 39 + ["Island"],
            commander="Probe Commander", colors=("U", "B"), hand_sizes=hand_sizes)
        self.assertEqual(sizes[:6], [40, 39, 38, 37, 36, 31])
        self.assertEqual(hand_sizes[:6], [7, 7, 6, 5, 4, 5])

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
            by_turn, _ = exporter.simulate_goldfish_game(decklist, CARDS, context, 6)
        return by_turn, sizes + [len(library)]

    @staticmethod
    def _library_with(card, turn, land):
        """92 cards: `card` is drawn on `turn` (2-10), lands everywhere else."""
        return [land] * (92 - (turn - 1)) + [card] + [land] * (turn - 2)

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
        # takes one card from turn 2. The first of the eight is Stonecoil
        # Serpent ({X}): Mathemagics paid 2 + 2 x 3 = 8, all eight Islands, so
        # the Serpent gets X = 0 and waits for turn 9, where nine Islands make
        # X = 9 (combat min(8, 9) = 8, from turn 10).
        library = ["Island"] * 84 + ["Stonecoil Serpent", "Mathemagics"] + ["Island"] * 6
        by_turn, sizes = self._run(["Island"] * 7, library, colors=("U",))
        self.assertEqual(sizes, [92, 91, 90, 89, 88, 87, 86, 85, 76, 75, 75])
        self.assertEqual(self._damage(by_turn), [0] * 9 + [8])

    # (card, turn it is drawn and cast with that many Command Towers,
    #  commander, cards it draws). Command Tower taps for either colour.
    DRAW_CASES = [
        # {X}{G}{U} with five lands: X = 3, "Draw X cards."
        ("Mind into Matter", 5, "The Ur-Dragon", 3),
        # {X}{U}{U}, five lands: X = 3, "Draw X cards, then discard a card."
        ("Pull from Tomorrow", 5, "The Ur-Dragon", 3),
        # {X}{U}{U}{U}{U}, six lands: X = 2, "Draw X cards."
        ("Transcendent Message", 6, "The Ur-Dragon", 2),
        # {X}{G}{U}, seven lands: X = 5, "draw half X cards. Round down".
        ("Hydroid Krasis", 7, "The Ur-Dragon", 2),
        # {X}{U}{U}, seven lands: X = 5, "draw half X cards, rounded down".
        ("Wan Shi Tong, Librarian", 7, "The Ur-Dragon", 2),
        # {X}{U}{U}{U}, six lands: X = 3, plus one per commander cast; The
        # Ur-Dragon is never cast here.
        ("Commander's Insight", 6, "The Ur-Dragon", 3),
        # Probe Commander ({5}) is cast on turn 5, so X = 3 plus one.
        ("Commander's Insight", 6, "Probe Commander", 4),
        # {X}{G}, five lands: X = 4, below "If X is 5 or more, you draw".
        ("Kinetic Ooze", 5, "The Ur-Dragon", 0),
        # Six lands: X = 5.
        ("Kinetic Ooze", 6, "The Ur-Dragon", 1),
    ]

    def test_draw_spells_draw_at_the_paid_x(self):
        for card, turn, commander, drawn in self.DRAW_CASES:
            with self.subTest(card=card, turn=turn, commander=commander):
                _, sizes = self._run(
                    ["Command Tower"] * 7,
                    self._library_with(card, turn, "Command Tower"),
                    commander=commander)
                # One card per draw step from turn 2; the spell's cards leave
                # the library after its turn's land choice.
                expected = [92 - (t - 1) - (drawn if t > turn else 0)
                            for t in range(1, 11)] + [83 - drawn]
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
        # and its copy draws 4 more.
        with patch.dict(exporter.COMMANDER_COPY_ENGINE,
                        {"synthetic-copy": {"mode": "tap_gate", "tapCost": 1}}):
            _, sizes = self._run(
                ["Command Tower"] * 7,
                self._library_with("Mind into Matter", 6, "Command Tower"),
                commander="Probe Commander", deck_id="synthetic-copy")
        self.assertEqual(sizes, [92, 91, 90, 89, 88, 87, 78, 77, 76, 75, 75])

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
                decklist, metadata, context, 6)
        return by_turn, casts

    def test_an_x_spell_pays_x_only_out_of_mana_the_gate_does_not_need(self):
        # Turn 2 casts the permanent piece. Turn 3 draws Stonecoil Serpent
        # with three Forests: the gate still needs {2} for the instant piece,
        # so the Serpent takes X = 1 (combat 1), not 3, and the gate fires.
        by_turn, casts = self._run_line(
            ["Piece Permanent", "Piece Instant"],
            ["Forest"] * 3 + ["Piece Permanent", "Piece Instant"],
            ["Forest"] * 16 + ["Stonecoil Serpent", "Forest"])
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
            by_turn, _ = exporter.simulate_goldfish_game(decklist, CARDS, context, 6)
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
            by_turn, _ = exporter.simulate_goldfish_game(decklist, CARDS, context, 6)
        return ([by_turn[turn]["cumulativeDamage"] for turn in range(1, 11)],
                sizes + [len(library)])

    @staticmethod
    def _library_with(card, turn, land="Command Tower"):
        """92 cards: `card` is drawn on `turn` (2-10), lands everywhere else."""
        return [land] * (92 - (turn - 1)) + [card] + [land] * (turn - 2)

    @staticmethod
    def _sizes_with_extra_draws(extra):
        """Library sizes when only the draw step and `extra` {turn: cards
        drawn before that turn's land choice} take cards."""
        drawn = 0
        sizes = []
        for turn in range(1, 11):
            drawn += (1 if turn > 1 else 0) + extra.get(turn, 0)
            sizes.append(92 - drawn)
        return sizes + [sizes[-1]]

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
        _, sizes = self._run(
            ["Peregrin Took", "Anointed Procession"] + ["Command Tower"] * 5,
            self._library_with("Frontline Rush", 6), commander="Baylen, the Haymaker")
        self.assertEqual(sizes, self._sizes_with_extra_draws({7: 2}))

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
        cases = {
            "no doubler": (["Adeline, Resplendent Cathar", "Peregrin Took"],
                           {9: 1, 10: 1}),
            "a doubler": (["Adeline, Resplendent Cathar", "Peregrin Took",
                           "Anointed Procession"], {8: 1, 9: 1, 10: 2}),
        }
        for label, (spells, extra) in cases.items():
            with self.subTest(label):
                _, sizes = self._run(
                    spells + ["Command Tower"] * (7 - len(spells)),
                    ["Command Tower"] * 92, commander="Baylen, the Haymaker")
                self.assertEqual(sizes, self._sizes_with_extra_draws(extra))

    def test_draconic_visitor_stops_new_food_and_keeps_the_old(self):
        # Commander Baylen on turn 3. New Food: Peregrin Took on turn 4,
        # Draconic Visitor ({3}{R}{R}) on turn 5; Frontline Rush, drawn on turn
        # 6, makes two Goblins, and Peregrin's Food would be a Dragon the engine
        # does not credit: two untapped tokens, no card (three, one card, if
        # the Food counted). Old Food: Rosie Cotton on turn 4 makes a Food;
        # Visitor is drawn and cast on turn 5 and Rush on turn 6: the Food and
        # two Goblins are untapped at the end of turn 6, one card before turn 7.
        tower = "Command Tower"
        cases = {
            "new Food": (["Peregrin Took", "Draconic Visitor"],
                         self._library_with("Frontline Rush", 6), {}),
            "old Food": (["Rosie Cotton of South Lane"],
                         [tower] * 87 + ["Frontline Rush", "Draconic Visitor"] + [tower] * 3,
                         {7: 1}),
        }
        for label, (spells, library, extra) in cases.items():
            with self.subTest(label):
                _, sizes = self._run(spells + [tower] * (7 - len(spells)), library,
                                     commander="Baylen, the Haymaker")
                self.assertEqual(sizes, self._sizes_with_extra_draws(extra))

    def test_baylen_draws_per_three_tokens_that_did_not_attack_while_he_is_out(self):
        # Secure the Wastes drawn on turn 7 with seven towers: X = 6, six
        # Warriors. With Baylen cast on turn 3 they are untapped at the end of
        # turn 7: 6 // 3 = 2 cards before turn 8; from turn 8 they attack and
        # draw nothing. With a commander that is never cast, no cards.
        library = self._library_with("Secure the Wastes", 7)
        for commander, extra in (("Baylen, the Haymaker", {8: 2}), ("The Ur-Dragon", {})):
            with self.subTest(commander=commander):
                _, sizes = self._run(["Command Tower"] * 7, list(library),
                                     commander=commander)
                self.assertEqual(sizes, self._sizes_with_extra_draws(extra))

    def test_baylen_draws_in_the_turn_cycle_he_is_cast(self):
        # The towers make only red or white here, so Baylen ({R}{G}{W}) waits
        # for the Forest drawn on turn 2, which is played only once the seven
        # towers are down, on turn 8 (a tower adds two of the commander's
        # colours, the Forest none). Turn 8: Baylen, then Secure the Wastes
        # (drawn that turn) with the five mana left: X = 4, four Warriors. They
        # are untapped at the end of turn 8, so Baylen draws 4 // 3 = 1 card
        # before turn 9. Zero Trinkets fill the library.
        library = (["Zero Trinket"] * 85 + ["Secure the Wastes"] + ["Zero Trinket"] * 5
                   + ["Forest"])
        _, sizes = self._run(["Command Tower"] * 7, library,
                             commander="Baylen, the Haymaker", colors=("R", "W"))
        self.assertEqual(sizes, self._sizes_with_extra_draws({9: 1}))

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
        # Castle Ardenvale: "{2}{W}{W}, {T}" with its own {T} charged as a
        # third {W}. Zero Trinkets ({0}, no combat) are drawn on turns 2-3
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
                           ["Forest"] * 90 + ["Zero Trinket"] * 2, ("W", "G"),
                           [0, 0, 0, 0, 0, 1, 3, 6, 10, 15]),
            "one Plains": (["Plains", "Castle Ardenvale"] + ["Zero Trinket"] * 5,
                           ["Forest"] * 91 + ["Zero Trinket"], ("W", "G"), [0] * 10),
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
        "the turn's casts left: Castle Ardenvale (2 generic + 3 W), Halo "
        "Fountain (1 W; only on a turn something attacked, so a creature is "
        "tapped); Food as a card resolves or enters: Rosie Cotton of South Lane "
        "1. A land among the activated makers must be untapped, and its own "
        "{T} is charged as one more mana of its colour: the pool does not "
        "record which land paid for what. Peregrin Took adds one Food to each "
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
        "mana and +1/+1 counter abilities, Halo Fountain's untap, Treasure and "
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
                "oracle_text": "{T}: Add {R}.", "mana_cost": "", "cmc": 0,
                "colors": [], "color_identity": ["R"], "produced_mana": ["R"],
            },
            self.COMMANDER: {
                "name": self.COMMANDER,
                "type_line": "Legendary Creature — Human Shaman",
                "oracle_text": "", "mana_cost": "{60}", "cmc": 60,
                "colors": [], "color_identity": ["G"], "power": "2",
                "toughness": "3",
            },
        }
        for name, (type_line, power) in self.COMBAT_CARDS.items():
            metadata[name] = {
                "name": name, "type_line": type_line, "oracle_text": "",
                "mana_cost": "", "cmc": 0, "colors": [], "color_identity": [],
                "power": power, "toughness": power,
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
                    + list(self.COMBAT_CARDS) + self.FILLERS)
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
                decklist, metadata, context, 6)
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
                "oracle_text": "", "mana_cost": "", "cmc": 0,
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
            exporter.simulate_goldfish_game(decklist, metadata, context, 6)
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
                decklist, metadata, context, 6)
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
                "oracle_text": "{T}: Add {G}{G}{G}.", "mana_cost": "", "cmc": 0,
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
                "oracle_text": "Draw a card.", "mana_cost": "", "cmc": 0,
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
                decklist, metadata, context, 6)
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
        # The partner is not in hand, so the start piece is cast; the cantrip
        # then draws the partner, which is cast the same turn. The start piece
        # entered before its partner, so the loop waits a turn although {1} is
        # left over, and starts on turn 2 by paying the start piece again.
        by_turn, casts = self._run_start_piece_combo(
            ["Forest", "Triple Rock", "Start Top", "Cantrip"], ["Partner Forge"])
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
                context["profiles"], self._metadata(), ["G"])
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
