
---

## 13. After the slice: the engine verdict, the owner's words, and the design proposal (2026-10-12)

Revision 11. §12 stays as written. This section records what the slice settled, what the owner asked for on 2026-10-12, and a design proposal with three directions for the owner's choice. Nothing is built on the new direction until the owner picks, the PRD is amended, and the amended PRD and this plan pass Codex (the owner's standing instruction of 2026-10-10 15:58Z).

### 13.1 What the slice settled

PR #115 is on `main` at `e79a195` (DEC-953; reviews DEC-976 and DEC-977, both APPROVE, the camera fix of DEC-975 included). The matrix of `prd_v4.md` 9.5, as the reviewer drew it at `237c8aa` and re-read at `3d41c7a`:

| Row | Result | Figures and basis |
|---|---|---|
| D | Pass | The scope shipped in the week. Owner editor time: 13 minutes of the 2 days; the owner handed the editor parts to the engineer on 2026-10-11 at 16:50Z. |
| R1 | Miss, on p90 alone | HDRP high, warm, native: p90 28.18 ms against 20 ms. p99 30.83 ms, longest 49.76 ms and GPU 3.79 GB pass. The volumetric fog at its medium tier, which the owner kept, is 12 to 13 ms of the frame. |
| R2 | Pass: degraded pass 1 | HDRP medium, warm, native: p90 16.00 ms, p99 17.55 ms, longest 49.45 ms, GPU 3.01 GB. |
| L | Not run | The owner has no MacBook Air (2026-10-12 10:09Z). Treated as the matrix treats a miss: the light Mac is suspended as a gating target pending Wave 5. |
| C | Recorded | Cold p90 within 0.1 ms of warm at both levels. 301 images from Scryfall in each cold run, none failed. |
| I | Pass | The six image-path tests pass with the exhibit-camera design. |
| A | **Artistic miss** | Question 3 is a no (13.2). Questions 2 and 5 are yes. Question 4 is partly: movement, card view and the river's sound yes; the camera was fixed on DEC-975; the water is "okish". |

Consequences in force:

- **Degraded pass 1** (9.5 row R2): Wave 5 makes HDRP medium the reference machine's ceiling setting and HDRP high a target; 7.2's first three rows are relabelled in the next amendment. The engine is not in question. At HDRP medium there is 4.0 ms of room at p90; the trial of photographic CC0 props (DEC-953, 2026-10-11 21:20Z) cost 1.0 ms of it.
- **The light Mac is unmeasured.** Wave 5 decides between a URP build variant and dropping the target (11.5).
- **Row A:** change the design, not the engine; record what failed. This section is that record.

### 13.2 What the owner said

Question 3 on the finished slice (DEC-953, 2026-10-12 10:09Z):

> it's still a radial chart. I mean, the card stands are all together in circles going from the center until almost the end of the map. it's like I'm moving through a radial museum of card stands, it's not like I'm in a world discovering cards as I journey to discover this amazing world (plane) I'm in. I wanted this to be more like an experience in knowing the planes history. I venture into the plane's world, it's modelled as the plane is described in the MTG lore and then I go through its history and can read about it and see the cards that are related to that part of the plane's history. it should be a historical experience kind of "game" with amazing visuals and lighting and sounds and music

Question 4 on the same card: "the river and the lake are okish but I would like them to be translucent water with sea life (fishes, corals, algae, etc)".

The two earlier cards. What makes it a chart (2026-10-11 20:21Z): the rings, the rows, the straight paths, the empty outer bands, the plaza. The trial pictures (2026-10-12 08:52Z): the photographic models are "partly" the look and go in after the slice; still wrong on them: the same tree repeated, pale, the rocks, the bushes, the colour, too sparse; and "missing more environment features, leaves flowing in the wind, trees moving with the wind, birds flying, fish in the water, those types of details. details that actually make me believe I'm in a world".

### 13.3 What that means against PRD v4

Four asks, each with a different weight against the contract:

1. **The layout.** The law of 5.4 (colour is the wedge, time is the radius, each set is a site) produced what it says: a wheel. The slice's figures on Dominaria: 824 m across; 36 bands with a width, 28 of them at the 6 m minimum; a plaza of 20.6 m radius; 5,955 of 6,271 stands facing a ring path; 610 stands with no neighbour within 8 m; from 103 m outward the bands are 6 m rows. 5.4.16 named the risk and gave the slice the question; the answer is no. This changes goal 4, 5.1.4, the 3.1 entities and 5.4. It is the main item.
2. **History.** "Go through its history and read about it" reverses non-goal 9 ("no plane descriptions, no story text") and adds a content type the product has never had: authored text. A museum has placards, so this is not a policy problem by itself. It is a maintenance, accuracy and licence question (13.5).
3. **Lore-modelled worlds.** "Modelled as the plane is described in the MTG lore" takes goal 3's hero set-piece further: not a landmark in a kit world but a world whose geography follows the lore. For twenty hero planes that is owner authoring at a scale 8.12.3 already put at 20 to 40 owner-weeks for set-pieces alone. The data can carry part of it (13.4).
4. **Life in the world.** Wind in trees and grass, drifting clouds and particles are already 5.1.3; the slice's kit subset had none of them, and they were Wave 5 leg 3 work, not slice scope. Birds, fish, corals and algae, and translucent water, are new content. Photographic props are a budget change (7.2's kit row and 8.12.1's model cap).

Not changed: goal 1. A road through a plane's history with reading stones is a museum trail. No objective, no completion, no score. The word "game" in the owner's quote stays out of authored text (9.1.6). Scryfall's "create new games" clause (`docs/scryfall-policy.md` §11.9) bears exactly as before. The 11.1 classification stays the owner's gate before any distribution.

### 13.4 What the data can carry

Checked on Scryfall on 2026-10-12 against Dominaria's 35 sets in Appendix B (6,576 non-basic cards by Scryfall's count; the dataset has 6,271 after the v3 exclusion rules):

| Signal | Count | Use |
|---|---|---|
| Sets in release order | 35 sets, 1993-08 to 2022-11 | Today's time axis. It is not the lore's order: The Brothers' War (2022-11) depicts the same war as Antiquities (1994-03), thousands of years before Dominaria United (2022-09). An era table has to be curated; sets then map to eras by rule. |
| Story Spotlight cards (Scryfall `story_spotlight`) | 54 on Dominaria; 384 across Magic. The flag exists since 2017, so only `dom`, `dmu` and `bro` carry it | The headline exhibits of an era, chosen by Wizards, no curation. Old eras have none. |
| Cards whose name carries a region word (24 words: Tolarian, Shivan, Urborg, Benalish, Llanowar, Keldon, Yavimaya, Phyrexian, Otaria, Vesuva, Zhalfir, Jamuraa, Thran, Argoth, Koilos, Serra, Academy, Femeref, Kjeldor, Balduvia, Suq'Ata, Sarpadia, Icatia, Ice Age) | 326 of 6,576, about 5 percent | A keyword table places these in their region. The other 95 percent go where their era or set goes. |
| Legendary creatures | 368 | The people of the plane; candidates for an era's "who was here" group. |
| Planechase cards typed `Plane — Dominaria` | 9; 185 across Magic | Wizards' own pictures of the plane's places (Academy at Tolaria West, Isle of Vesuva, Krosa, Llanowar, Otaria, Shiv and others). Whether they are in the dataset depends on the v3 set-type rules; a pipeline leg checks. As exhibits they are card images: flat, credited, compliant. |
| Flavour text | On the card image | Already shown. No extra text is needed for it. |

So eras and regions are curated tables, text, one set per hero plane; the cards' assignment to them is derived by rule (set to era, keyword to region, Story Spotlight to headline). The picture stays mostly the data; goal 4 gains two curated tables beside Appendix C.

### 13.5 The reading layer: form, words, accuracy, policy, scale

- **Form.** A reading stone at each era's site: the era's name and its place in the plane's history, one to three short paragraphs, the sets that depict it, the headline cards. Text only, no voice. The map draws the trail. No counter of stones read; the recently-visited list stays as it is.
- **Words.** Every paragraph is written by us in our own words. Each era row names its sources: the cards themselves, Wizards' published story index, the MTG Wiki. The MTG Wiki's text is CC BY-NC-SA 4.0 (read at mtg.wiki on 2026-10-12); copying it would put our text under the same licence, so no sentence is copied. Facts carry no licence.
- **Accuracy.** An engineer drafts from the named sources; the reviewer checks every sentence against a source and rejects any sentence without one; the owner accepts the text under 9.3. A model's own knowledge without a source is not a source.
- **Policy.** Appendix E gains one item: lore text is our own words, names its sources, and quotes no Wizards story text. Non-goal 9 is reversed by owner decision only.
- **Scale.** Dominaria: about 10 eras, about 20 paragraphs. Twenty hero planes: about 150 eras. Kit planes: no prose; their trail is the sets in release order with names and years.

### 13.6 Three directions

**Direction A: lore-shaped hero worlds with an era trail (the owner's ask in full).** Per hero plane, three curated tables: regions (6 to 12 named places from the lore, each with a biome, a rough position and a size weight), eras (in lore order, each with its sets, its region, its paragraphs and its sources), keywords (word to region). The pipeline builds the terrain from the region table (biome per region, water on borders, roads between regions), places each card in its region or in its era's region, then in natural clusters (a grove, a ruin, a camp) with stands in groups of three to eight facing a winding path. A road runs through the regions in lore order with a reading stone at each era. Kit planes get the same cluster placement on one biome with a data-derived trail (sets in release order) and no prose. Pockets are unchanged.
Cost, engineer-days on top of Wave 5's uncut 40 to 60: allocator v2 with its checker and fixtures, 10 to 15; terrain from a region table, 5 to 8; the reading layer (stone, map trail, text in the pack), 5; pipeline tables, validation and the Scryfall flags, 5. Owner: 2 to 3 days of tables per hero plane, or 1 day of review per plane if an engineer drafts, plus the set-piece time 8.12.3 already counts. One-way doors: non-goal 9 reversed; goal 4 becomes "the data plus three curated tables"; colour leaves the map and becomes a cue on the stand, in the HUD and on the map; a hero plane without its tables reads as a kit world.

**Direction B: an organic layout, no lore.** The same data law (colour class, set), new geometry: no plaza wheel, no rings. Sites are clearings scattered over the terrain, with district blobs for colour and a soft chronology (older sets near the arrival, newer ones farther, along winding roads). Stands stand in groups of three to eight facing a path; density varies, dense by the roads and sparse at the edges; the world is sized by its content, not by its busiest band. Non-goal 9 stands; no text.
Cost: allocator v2 with checker and fixtures, 8 to 10 engineer-days; no owner tables. What it does not do: it gives the owner no history, and it may still read as a museum in a field. It is the base layer Direction A needs in any case.

**Direction C, recommended: staged. B as the law for every world; A on hero planes in Appendix C.1 order, Dominaria first.** Wave 5 leg 1 builds the organic allocator. Dominaria gets its three tables and the era trail, and the reading layer ships with Dominaria. Each later hero plane gets its tables when its set-piece is built, in C.1 order. Kit planes read as B. The first judge is a second one-week Dominaria slice on the new law, with the photographic props, wind on the vegetation and the reading stone, before Wave 5 is cut. Question 3 is restated: "from the avatar's height, does Dominaria read as a place with a history?"
Cost: B now; A's Dominaria parts in the second slice; about 25 to 33 engineer-days in all (allocator v2 10 to 15, terrain from regions 5 to 8, reading layer 5, tables and pipeline 5), of which the second slice takes the first week. The other nineteen heroes follow over the staged releases. One-way doors as A, taken one plane at a time.

What I would not do: author every hero plane's tables before the first distribution (twenty table sets before anyone walks one world is the plan that never ships); drop the data law for hand-placed stands (the picture stops being the data, and every refresh becomes owner work); keep 5.4 and dress it harder (the owner's five reasons are geometry, not dressing).

### 13.7 The content asks beside the layout

- **Photographic props.** The trial's answer stands: better, 1.0 ms at HDRP medium, "partly" the look. The next step is a per-kit asset pass with the owner's six corrections (more than one tree species, colour, rocks, bushes, density, paleness) under an amended 7.2 kit budget. Proposal: kit at most 250 MB cooked; first release is core plus the temperate kit plus Dominaria; the other kits follow in staged releases, as hero set-pieces already do. The archive ceiling is kept by staging, not by raising it.
- **Wind, clouds, particles.** 5.1.3 as written; Wave 5 leg 3 kit work. No decision needed.
- **Birds, fish, corals, algae, translucent water.** New content: HDRP water's absorption and refraction settings for translucency; underwater props; a simple flocking and schooling behaviour for birds and fish. 3 to 5 engineer-days plus assets for each kit that has water or sky life. Proposal: a stretch item in the second Dominaria slice, dropped first.

### 13.8 Sequence

1. The owner picks a direction and answers the three design questions on the card of 2026-10-12.
2. The CEO writes the PRD amendment (Amendment 4, or a v5 if the law is replaced; the content matters, not the name): goal 4, 5.1.4, the 3.1 entities (region, era, trail, reading stone, cluster), 5.4 replaced, 5.6 and Appendix C fields, non-goal 9, 7.2 budgets and the degraded-pass relabelling, 9.3 criteria, the Appendix E item, section 11.
3. Codex review of the amended PRD and this plan, as the owner's standing instruction requires; triage in this document; owner confirmation on the plan revision.
4. A second Dominaria slice, one engineer, one week, with its own acceptance matrix.
5. Wave 5 is cut after it.

Nothing is built on the new direction before step 3 is passed. DEC-978, DEC-979, DEC-960 and DEC-972 continue as housekeeping on the shipped slice.
