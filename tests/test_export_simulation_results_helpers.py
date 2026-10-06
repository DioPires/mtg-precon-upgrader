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

    def _run_hatch(self, forests_in_hand: int):
        """Pinned hatch-engine game; returns (hatch turns, casts by turn)."""
        metadata = self._hatch_metadata()
        two_drops = [f"Two Drop {i}" for i in range(10)]
        bears = [f"Bear {i}" for i in range(20)]
        decklist = (["Forest"] * 12 + ["Ashnod's Altar"] + two_drops + bears)
        deck_data = {"decklist": [{"name": name} for name in decklist]}
        context = exporter.build_goldfish_context(
            decklist, deck_data, metadata, self.HATCH_COMMANDER, ["G"],
            self.HATCH_DECK_ID)
        hand = (["Forest"] * forests_in_hand + ["Ashnod's Altar"]
                + two_drops[:2])
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

        class SerialPool:
            def __init__(self, *_args, **_kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *_exc):
                return False

            @staticmethod
            def map(fn, iterable):
                return [fn(item) for item in iterable]

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
