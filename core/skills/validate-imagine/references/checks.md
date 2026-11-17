# Checks

The audit script catches what is mechanical. Everything below is judgment: you read, compare and rule. Every finding names the file and section, the two things in conflict (or the missing thing), the layer that wins, and the fix.

## Deviation: concept trace

Atoms come from layers 1-3 of the authority table: every named audience, platform, era, technology level, geography, climate, tone, mechanic, scale, market ambition, definition of "done", exclusion, and every noun the brief itself uses ("cozy", "farming", "desert continent").

| Atom kind | Where it must show | Deviation looks like |
|---|---|---|
| Audience, age band | canon `audience`; tone of story events; findings Market | Stakes, violence, humor or complexity for another audience |
| Medium, platform | canon `market`; plan; design `medium`; mechanics (game) | A console-only mechanic in a mobile brief; film beats in a game |
| Era, tech | canon axes; registry tags; story props; design visual vocabulary | A tool, weapon, institution or vocabulary above the ceiling the canon rules do not cover |
| Geography, climate | canon regions; places; story travel; design palette and `forbidden` | A lake in a desert region; snow with no cold climate tag |
| Tone | canon `tone`; story; risks; plan | Grimdark turn in a cozy brief; jokes in a tragedy |
| Core activity or mechanic | steps; plan; game sections (mechanics, quests, skills) | The named activity is a side feature; a different loop leads |
| Scale, ambition | plan; steps; findings Pros and cons | Plan needs a team or budget the brief ruled out |
| Exclusion | everywhere | Any trace of the excluded thing, including inherited ones (an excluded mechanic reappearing as a quest reward) |
| "Done" for the lake | findings; plan | Deliverable the brief never asked for; a requested one missing |

Then the reverse scan, scope creep: list major elements of the output (systems, factions, regions, features, deliverables) and mark each as licensed by an atom or not. An unlicensed element is a deviation unless it is needed by a licensed one (then it stays and the dependency is noted).

Use `rg -i` over the lake for each exclusion and each canon-forbidden value; skip hits inside the file that states the exclusion. Judge every hit: a character saying "there is no lake here" is fine, a place described beside a lake is not.

Default fix: narrow or rewrite the derived artifact to fit the atom; delete the unlicensed element when nothing licensed depends on it.

## Contradiction: fact table

Build the table from `story.md` and the registry, then check every other artifact against it. Kinds of facts:

| Kind | Compare across |
|---|---|
| Identity: names, aliases, roles, ages, species | registry vs story vs steps vs plan vs findings |
| Relations: kin, allegiance, who knows whom | registry links vs story beats |
| Place: region, distances, travel time, what is where | registry tags and summaries vs story vs plan |
| Time: season, order of events, durations, ages against the timeline | story vs plan acts vs steps |
| Quantities: populations, prices, counts, levels | registry vs story vs plan vs findings |
| Rules: physics or magic costs, economy, progression | canon `physics` vs story vs mechanics |
| Canon vs design | `design.json` `forbidden`, palette mood and visual vocabulary vs canon regions, era and tech ceiling |
| Steps vs plan vs story | plan acts cover the story's beats in order; steps' actors exist in the registry; a step's "real case" matches its source mark in research |
| Findings vs the rest | findings summarizes what the files say, not a different version; Claims and README counts match the marks |
| Research vs sources | every URL used is in `sources.md`; the lesson drawn matches what the item says |
| Persona | the lake stays in the persona's role and biases; flag a file written as a different author only when the content, not the style, changed |

Rules of thumb:

- A summary that omits what the tags say, or tags that omit what the summary says ("the lake behind the dunes" tagged `dune`), is a contradiction between two fields of one entity.
- A story beat that uses an entity against its summary is a contradiction; fix the beat when the summary is canonical, fix the summary when five other places agree with the beat.
- A character with two incompatible ages, loyalties or locations: find every mention with `rg` before ruling.
- Do not call a deliberate canon `rule` a contradiction; check the rule's `why` is in findings.

Default fix: per the fix policy direction; edit all sites in one pass.

## Incomplete: per artifact

| Artifact | Incomplete when |
|---|---|
| `brief.md` | No verbatim original brief; open items that no canon assumption covers |
| `persona.md` | Missing any of Role, Expertise, Success measure, Usual deliverables, Biases, Voice |
| `research.md` | A theme (references, successes, failures, market) has no items, or fewer than the brief's weight warrants; an item with no mark |
| `sources.md` | A URL used in research is missing; a row without access date or status |
| `canon.json` | An axis the brief constrains is absent; a region has neither `allowed` nor `forbidden`; `physics`, `tone`, `audience`, `market` empty |
| `steps.md` | A step without sub-steps, goal, actors, or one real case with its source mark |
| `risks.md` | A challenge or opportunity without a plan; no failures to prevent; no successes to match and surpass |
| `registry.json` | Entity with empty summary, no tags on an axis it touches, or no link; story root unset; characters, places and actors that no story, step or plan uses |
| `story.md` | Does not frame the scenario; skips an entity the plan depends on; no ending or open thread named; a character with no role |
| `plan.md` | Does not follow the story's order; no scope, milestones or "done" definition |
| `findings.md` | Template section missing, empty, or out of order; game section set missing for a game brief; art direction section empty when `design.json` exists |
| `design.json` | An `image` block without `medium`, `projection`, `palette.mode`, `direction.drawing_style`, `direction.proportions` or `direction.lighting`; asset list with no registry entity |
| `assets/` | Asset in the design list without a manifest entry; failed or pending asset; manifest file absent on disk; missing contact sheet |
| `run-log.md` | No stop reason; a dropped expansion result or rejected entity with no reason; a reviewer or design finding with no `applied` or `rejected` verdict |
| `README.md` | Counts or file table out of date |

Default fix: fill from lake material; new entities only as the fix policy allows; otherwise record the gap as `open`.

## Asset pass notes

- Compare against `design.json`, not against your taste. Deviations: drawing style, palette, proportions, lighting, projection, outline, shading, grid and scale, canon (a forbidden thing depicted).
- Look at `assets/sheets/*.png`, not at each file. Sheets are already capped at 1280 px on the long edge; send them as they are.
- A palette or direction change you would like is a proposal, never an edit.
- Audio timbre, video motion and 3D mesh quality you cannot judge here: write "not reviewed" for them.

## Recording a finding

One finding per root cause. Fields: id (`F1`, `F2`...), class, severity, file and section, evidence (the two conflicting quotes or the missing item), winner layer, fix applied or `open`, and any re-checked sites. Do not report taste, voice, or anything the lake's `run-log.md` already adjudicated.
