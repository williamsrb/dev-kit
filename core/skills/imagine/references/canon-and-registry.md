# Canon and registry

The canon fixes the world before any expansion. The registry holds every entity and its links. `scripts/registry.py` checks structure and axis tags; the main agent judges what the script cannot see.

## Canon (`canon.json`)

Axes:

| Axis | Shape | Checked by |
|---|---|---|
| `era` | ordered `levels` + `ceiling` | script |
| `tech` | ordered `levels` + `ceiling` | script |
| geography | `regions[]`, each with allowed and forbidden `biome`, `climate`, `feature` | script |
| climate and weather | region `climate` lists; seasons and weather in `notes` | script (tags), main agent (prose) |
| physics or magic | `physics` text: what is possible, its cost, its limits | main agent |
| tone, audience, market | `tone`, `audience`, `market` text | main agent |
| deliberate mixes | `rules[]` | script honors them |
| open choices | `assumptions[]` | listed in findings |

```json
{
  "slug": "desert-farm",
  "axes": {
    "era":  {"levels": ["ancient", "medieval", "early-modern", "industrial", "modern"], "ceiling": "medieval"},
    "tech": {"levels": ["stone", "bronze", "iron", "gunpowder", "steam", "electric", "digital", "spaceflight"], "ceiling": "iron"}
  },
  "regions": [
    {
      "id": "red-waste",
      "name": "The Red Waste",
      "allowed":   {"biome": ["dune-sea", "rocky-desert"], "climate": ["arid", "hot-desert"], "feature": ["oasis", "dune", "wadi", "salt-flat", "mesa"]},
      "forbidden": {"biome": ["rainforest", "tundra"], "feature": ["lake", "jungle", "swamp", "glacier"]}
    }
  ],
  "physics": "No magic. Water is the scarce resource; wells deplete.",
  "tone": "cozy, low stakes, warm humor",
  "audience": "casual players 16+, cozy-game fans",
  "market": "indie PC + Switch, premium price",
  "rules": [
    {"id": "clockwork-pumps", "axis": "tech", "values": ["steam"], "region": "red-waste", "why": "one guild keeps pre-collapse pumps running"}
  ],
  "assumptions": ["Single continent; no ocean travel."]
}
```

Rules:

- An empty or missing `allowed` list means any value not in `forbidden`.
- A rule allows exactly its `values` on its `axis`, in its `region` or everywhere when `region` is omitted. Write the reason in `why`.
- Change the canon only in P3, or in P8 when the main agent decides a deviation is better than the canon and logs why. Rerun `check` after.

## Registry (`registry.json`)

```json
{
  "version": 1,
  "story_root": "the-dry-season",
  "concepts": [], "characters": [], "terms": [], "actors": [], "places": []
}
```

Entity:

```json
{
  "id": "palm-well",
  "type": "place",
  "name": "Palm Well",
  "aliases": ["the Well"],
  "summary": "Last sweet-water oasis on the caravan road.",
  "region": "red-waste",
  "tags": {"era": "medieval", "tech": "iron", "biome": "dune-sea", "feature": ["oasis", "dune"]},
  "links": [{"to": "well-keeper-asha", "rel": "kept-by"}],
  "origin": "P6"
}
```

- `id`: kebab-case, unique across all tables. `type`: `concept`, `character`, `term`, `actor`, `place`.
- `actor` = a role in a creation step (a producer, a playtester); `character` = a person in the story.
- Places need `region`. Every entity tags the axes it touches; an untagged feature cannot be checked.
- `story_root` is the one entity allowed to have no links. Set it in P6 by editing the file.
- Story and steps reference entities as `[[id]]` or `[[id|label]]`.

## Commands

```bash
python3 ~/.agents/skills/imagine/scripts/registry.py init --canon canon.json --dir <lake>
python3 ~/.agents/skills/imagine/scripts/registry.py merge <result.json> --dir <lake> [--origin <wave-id>]
python3 ~/.agents/skills/imagine/scripts/registry.py check --json --dir <lake>
python3 ~/.agents/skills/imagine/scripts/registry.py render --dir <lake>
```

Exit 0 clean, 1 findings (`check`), 2 bad input. `merge` adds new ids, merges known ids additively (aliases, missing tags, links), and refuses a type conflict without writing anything. It prints the result's `candidates` and `assumptions` back for the run log.

## The five check kinds

| Kind | Meaning | Usual fix |
|---|---|---|
| `dangling-link` | `links[].to` is not an entity id | add the target entity or drop the link |
| `orphan` | no inbound or outbound link (story root excepted) | link it to what it serves, or delete it |
| `duplicate` | same id twice, or two ids share a normalized name or alias | merge into one entity, keep the other name as alias |
| `axis-violation` | `era`/`tech` above the ceiling or not a level; `biome`/`climate`/`feature` forbidden or not allowed in the region; place without a canon region | change the tag and the prose, or reject the entity |
| `story-reference` | `[[id]]` in `story.md` or `steps.md` not in the registry | register it or rewrite the sentence |

Fix or reject: fix when the entity's role in the story survives the change; reject when the deviation is the point of the entity. To reject after a merge, delete the entity from `registry.json`, then rerun `check` to catch the links it leaves dangling.

## Semantic review checklist (P8, per axis)

The script trusts tags. The main agent and the reviewer read the prose against the canon:

- **Geography:** every place sits in a canon region; travel times and distances fit the map; no feature in a summary that its tags omit ("the lake behind the dunes" tagged only `dune`).
- **Climate and weather:** seasons, rain, snow, crops and animals fit the region's climate; water sources match an arid climate.
- **Era:** institutions, money, writing, social roles and vocabulary fit the era ceiling.
- **Technology:** tools, weapons, transport, medicine, communication stay at or under the tech ceiling, except canon rules.
- **Tone:** events, deaths, humor and stakes fit the tone and audience.
- **Physics or magic:** every supernatural effect follows the stated cost and limits; nothing solves a plot problem for free.

## Worked deviations

- **Spaceship in a medieval canon.** A subagent returns `star-barge` tagged `tech: spaceflight`. `check` reports `tech 'spaceflight' is above the ceiling 'iron'`. Its story role is "arrives with strangers", which a caravan also serves: reject `star-barge`, ask nothing, seed `salt-caravan` instead. If the brief wanted a fallen-star mystery, write a canon rule in P3, not in P7.
- **Lake or jungle in a desert.** `mirror-lake` in `red-waste` tagged `feature: lake` fails as forbidden. The story needs a water source where travelers meet: replace with `palm-well`, tagged `feature: oasis`. Same for a jungle: a palm grove around an oasis or a wadi with seasonal growth.
- **Deliberate mix.** A steampunk brief allows `steam` above an `iron` ceiling through a rule; `check` stays clean and the rule's `why` goes to `findings.md`.
