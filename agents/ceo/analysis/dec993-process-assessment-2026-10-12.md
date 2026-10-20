# DEC-993: what to take from the "cozy fishing game" post (2026-10-12)

> **Erratum (2026-10-12 18:3xZ).** The adversarial review of this assessment (Codex and a fresh Claude agent, `dec993-adversarial-review-codex.md`, `dec993-adversarial-review-claude.md`) read its reasoning as UNSOUND. Eleven merged findings, all accepted, are triaged in `dec993-triage-2026-10-12.md`, which supersedes this file on: the Tripo trial (deferred; it contradicts PRD 8.12.1 and the owner's props decision of 2026-10-12 15:07Z); step 3 "mostly ours" (no prop prefab exists, `Generate.cs` loads FBX files as-is, the materials are written from a colour table); step 7's chronology (about 23 hours, not 29; no greybox walk ever happened); item 1's "no engineer cost, no PRD change" (withdrawn); the citations of 5.8.4, 8.12.3, 8.12.6, §14.4 and Appendix D.3; and every Tripo fact (unverified). Read this file as the record of what was claimed, not as the recommendation.

Tier 0, CEO-executed assessment. No implementation. A copy of the DEC-993 comment of 2026-10-12.

## Outcome

Little of the post's process is new to us. Five of its seven steps are already ours, were taken on
2026-10-10 (DEC-950 plan §12.11 and §12.12), or were ruled out today (DEC-960, no-go on the editor
bridge and `blender-mcp`). One thing is genuinely new: **AI mesh generation as a content source**
for the props and stones the CC0 libraries fail on. I recommend a bounded, owner-run trial of it
inside the temperate kit's photographic asset pass, after Amendment 4 is confirmed. Two smaller
takes cost almost nothing: a written conditioning rule for kit props (step 3 of the post, done in
text in our stack) and an owner walk after every merged pull request that changes how a world
looks (step 7, tighter than the two walks the second slice schedules).

## What the post and the video show

The post is a solo workflow: Tripo generates every model, Claude Code drives Blender through MCP to
set scale, pivots and materials and to animate, Unity 6 holds the world, systems go in one at a time,
and the author plays after every step.

The video (`~/Downloads/claude_unity_game.mov`, 32 s, 582 × 326, a screen recording of a web player
showing a 27 s clip) shows a small island you cross in under half a minute: a forest clearing with
rocks, a river, a waterfall into a pool, a beach, a pier with a boat, a hut. The camera is top-down
at three quarters, not third-person. Every model is in one stylised low-polygon style with soft
colours, so the island reads as one place. The water is translucent with fish shadows under it, foam
on the shoreline, flowers in the grass. The interface shows a bait choice (worm, bread, shrimp), a
creel count ("Creel 3 / 8"), a time of day ("Afternoon") and a catch label ("Garfish"). It is a game
by its own description: an objective, a counter, a choice that changes the outcome. The video shows
no frame times, no world larger than the island, and nothing of the build process itself.

Two things in the video match what the owner asked for on 2026-10-12 and are already in the plan:
life in the water (fish, translucent water: plan §13.7, a stretch item of the second slice) and a
world where every prop belongs to the same style (the owner's six corrections of 08:52Z are variety
and coherence complaints, and PRD 8.12.6 in Amendment 4 is the answer so far).

## Step by step against what we have

| Post step | Ours today | Verdict |
|---|---|---|
| 1. Generate every model with Tripo (Smart Mesh, their P2.0 model, launched 2026-09-21 after an August preview; quad meshes up to 25,000 faces; FBX out) | PRD 8.12.1: kit assets are CC0 or owner-made (Poly Haven, Kenney, Quaternius, ambientCG, Freesound). Appendix D.3 already names "AI mesh generation followed by clean-up" for the avatar. The first slice's trial (DEC-953, 2026-10-11 21:20Z) found seven Poly Haven models hold the frame at 1.0 ms; the owner found them "better, but not there yet": one tree repeated, pale far trees, the rocks, the bushes, the colour, see-through trees. | **New for props and stones.** A trial is worth it. Details below. |
| 2. Claude Code drives Blender through MCP | DEC-960 (today, 15:14Z): no-go now on any editor bridge. `blender-mcp` is off: it runs arbitrary Python as the owner's user on a port with no token, beside the runner. It may be turned on only by the owner, for the owner's own modelling, under four conditions (runner stopped, safe mode on, the owner's client only, a `CREDITS.md` row for every download). An engineer's use needs a PRD 7.6.4 amendment first. | **Ruled.** Nothing changes. |
| 3. The model sets up each model in Blender: scale, pivots, materials, clean export | In our stack this step is text, and engineers already do it: the import settings in each prop's `.meta` file, materials as YAML, prefabs that put the pivot at the base, and `KitMaskImport.cs`, which repacks the mask textures on import so the binary stays as `sources.yaml` pins it. The FBX is never edited. What we lack is a written rule and a check: the slice engineer judged scale "from pictures" and made nine plain materials by hand. No defect is on record. | **Mostly ours.** Small take: a conditioning rule with an EditMode test, about half an engineer-day, text only. The value is repeatability across twelve kits, not a fix. |
| 4. The model animates in Blender (walk, cast, rod, boat) | PRD 8.1.2, 8.5.3, Appendix D.3: the shared Mixamo set retargeted onto one humanoid rig; the mannequin for the slices; Teferi is not commissioned before 11.1. | **Not now.** When Teferi is commissioned, Appendix D.3's generation path is already the post's steps 1 and 4. |
| 5. Build the world by hand in Unity 6 | PRD 8.2.5 and goal 4: worlds are generated from data by the allocator through the scene generation entry point; hero set-pieces are the owner's. Plan §13.6 ruled out hand-placed stands. The post's island is a few hundred metres across at most; Dominaria is about 1,120 m across under the journey law (plan §14.4) with 6,271 stands. | **Not transferable at our scale.** The hero set-pieces are where the owner hand-builds, as planned. |
| 6. Add the systems one at a time | PRD 9.6: leg A (tooling), leg 1 (allocator and greybox), leg 2 (dressing, reading layer, travel), each a reviewed pull request. | **Already ours in shape.** |
| 7. Play it after every step and fix one thing at a time | The first slice had one greybox walk and one judging walk. The walk was offered on 2026-10-10 at 23:17Z; the owner's "it's a chart" answer came on 2026-10-11 at 20:21Z, 29 hours into the week, when the full scope was already built. PRD 9.6 schedules the same two walks across about five weeks for the second slice. | **Take, tighter.** One owner walk after every merged pull request that changes how a world looks, on the player the bench job builds. About ten minutes each, three to five walks over the second slice, owner time only. Not a gate: the merge stays on the reviewer's verdict. |

"One tool, one job" is ours already, with a different roster: the Python pipeline owns data and
layout; Unity owns the runtime; CC0 libraries own the kit assets; the owner and Blender own the
hero set-pieces and the avatar. The post fills one slot we leave empty: a model source that makes
variety on demand in one style. That is the slot the trial tests.

## The trial, if the owner wants it

**What.** The owner generates about six models in Tripo Studio: two more tree species, one bush,
two rocks of the temperate biome, and one of the bespoke stones nobody owns yet (plan §12.11
finding 4: the plinth, the waystone and the marker stone have no named owner; Amendment 4 adds the
reading stone and the chapter stone). No card art and no character goes into any prompt or input
image (PRD 5.8.4, Appendix E). An engineer places them in the view the 2026-10-11 trial used and
produces the same paired pictures with the frame time beside each, measured the same way. The owner
judges on the six corrections. Expectation, stated honestly: good odds on rocks, stones and
structures; uncertain on trees, because mesh generators are weakest on foliage, and "photographic"
vegetation usually means leaf cards from photogrammetry.

**Licence, unverified.** Tripo's site returned 403 to every fetch I tried, so I have only search
summaries of its own help page: rights to models made by free users stay with Tripo (their Terms of
Service section 5.2.1 as cited), paid users get full rights to use, modify and distribute, and no
rights to the input image are granted either way. One Tripo blog post says the free tier is CC BY
4.0, which contradicts the help page. Step one of the trial is the owner reading the current Terms
of Service in a browser and recording what they say. Until then: paid plan only (third-party
listings say about US$20 a month; the pricing page decides), the owner's own account, nothing
generated on the free tier enters the repository.

**PRD change if a generated model is kept.** 8.12.1 gains a source class "generated under the
owner's paid account", and 8.12.2's row gains the service, the plan, the prompt and the date. CC0
has no question over who owns the copyright; a generated model may, in some jurisdictions. Keep
the generated set small and replaceable, and never a card's likeness.

**Cost.** Owner: about two hours plus one month of a paid plan. Engineer: about half a day, inside
the temperate kit's photographic asset pass (a leg-2 prerequisite of PRD 9.6, opened beside leg A
at plan §14.4 step 3), as its first half day. Nothing else moves.

**Who.** The owner generates (binary authoring is the owner's, PRD 8.12.3). The engineer places
and measures (a content task, 8.12.1). The reviewer is not the engineer. No MCP, no Blender by an
engineer, no change to 7.6.4.

## What not to take

- Blender through MCP, by anyone but the owner, under the DEC-960 conditions. Ruled today.
- A hand-built world. Ruled on plan §13.6; the picture stays the data.
- Any game system. Bait choice and a creel count fail the museum test (goal 1).
- The top-down camera. Third-person with a following camera is decided (PRD 5.8) and the owner
  accepted the camera on DEC-975.

## Recommendation, with costs

1. **Owner walks after every merged look pull request** in the second slice: owner time only, about
   ten minutes each, no engineer cost, no PRD change (walks on a built player are not editor time).
   Take now; it starts with leg 1's second pull request.
2. **A prop conditioning rule with a test:** about half an engineer-day, text only, rides with the
   photographic asset pass or the next tooling leg. Take with the asset pass.
3. **The Tripo trial:** the asset pass's first half day, after Amendment 4 is confirmed, paid plan,
   owner-run generation, Terms of Service read first. Take as a trial, decide on pictures.
4. An adversarial review of this assessment first, as on 2026-10-10 (Codex plus a fresh Claude
   agent, about fifteen minutes of model time, no engineer time), is the owner's call. The
   2026-10-10 review corrected four of my claims; every "ours already" claim above cites its PRD
   section or its record so the same check is cheap.

Nothing here gates Amendment 4, Codex round 8, DEC-984's fix or the open merges.

## Sources

- Tripo P2.0 launch and preview: PR Newswire via Webull (2026-09-21), Fabbaloo (2026-08-28), 3D AI
  Studio's model listing. Licence summaries: Tripo's help page "How to use Tripo models
  commercially" and Tripo's blog, as summarised by search; the pages themselves returned 403.
- Our record: `prd_v4.md` on `main` (7.6.4, 8.1.2, 8.2.5, 8.5.3, 8.12, 9.5, Appendix D.3), Amendment
  4 draft 4 (8.12.1, 8.12.6, 9.6), DEC-950 plan §12.11, §12.12, §13.6, §13.7, §14.4, DEC-960's
  `docs/mcp-evaluation.md` section 5, DEC-953's comments of 2026-10-11 (17:06Z, 21:20Z) and
  2026-10-12 (09:09Z), `unity/Eternities/Assets/Kits/temperate/CREDITS.md`.
