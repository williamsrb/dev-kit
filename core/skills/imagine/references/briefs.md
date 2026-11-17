# Subagent briefs

Four child kinds. Each brief is self-contained: the child knows only what the brief says. Every brief ends with the never-spawn rule.

> You are a leaf. Do not spawn subagents, do not delegate, do not ask the operator anything. Return the result in the shape below and stop.

Pick model and effort for each child from `~/.agents/skills-vendor/ROLES.md` by role name. Never write a model slug into a brief.

## Research brief (role `explore`, P2)

One theme per child, up to four in parallel: **references** (modern and classical works), **successes**, **failures**, **market** (hype versus trend, niche versus broad appeal, market versus money waste).

```text
Role: you research for a <persona role> planning <one-line brief>.
Theme: <one theme>.
Settled brief: <brief.md, verbatim>.
Find: 5–10 items on this theme. For each: name, year, what happened, why it matters for this brief, and the lesson.
Source rule: each item carries a source URL and the access date (YYYY-MM-DD). If you cannot open a source, mark the item `unverified`. Never invent a URL, a number or a sales figure.
Return: one fenced JSON block, then nothing else.
<never-spawn rule>
```

Return:

```json
{
  "theme": "failures",
  "items": [
    {"name": "…", "year": 2019, "summary": "…", "lesson": "…", "source": "https://…", "accessed": "2026-10-30", "status": "verified"},
    {"name": "…", "year": 2014, "summary": "…", "lesson": "…", "source": null, "accessed": null, "status": "unverified"}
  ]
}
```

No web tool in the harness: the child answers from knowledge and marks every item `unverified`.

## Expansion brief (role `build`, P7)

```text
Role: you are a <persona role> deepening one part of <world name>.
Target: <one entity or gap, one sentence>.
Context:
  canon.json (in full): <…>
  registry slice (target + entities within one link): <…>
  story outline: <3–6 lines from story.md>
Delimitation:
  Must not change: <axes, entities, facts that are fixed>.
  May add: <entity types>, at most <N> new entities.
  Out of scope: <what another child or a later wave owns>.
  Tag every entity with the axes it touches (era, tech, biome, climate, feature); every place carries a top-level `region` field holding a canon region id (not a tag).
Return: one fenced JSON block (shape below), then prose for expansions/<target-id>.md under a `## Prose` heading.
<never-spawn rule>
```

Return:

```json
{
  "entities": [
    {"id": "salt-caravan", "type": "concept", "name": "Salt Caravan", "aliases": [], "summary": "…",
     "tags": {"era": "medieval", "tech": "iron"}, "links": [{"to": "palm-well", "rel": "stops-at"}]}
  ],
  "links": [{"from": "palm-well", "to": "salt-caravan", "rel": "supplied-by"}],
  "candidates": [{"id": "caravan-master", "why": "drives the act-two conflict", "priority": "high"}],
  "assumptions": ["Caravans cross in winter only."],
  "sources": []
}
```

- `links` holds links from existing entities to new ones; links from a new entity go on that entity.
- `candidates` are expansion proposals. The child does not expand them.
- Save the JSON to `expansions/<target-id>.json` and the prose to `expansions/<target-id>.md`, then `$R merge <lake>/expansions/<target-id>.json --dir <lake> --origin <wave-id>` (`$R` as in `SKILL.md`).

## Reviewer brief (role `impl-review`, P8)

One child, on a different model than the `build` children. Read-only.

```text
Role: you review a world for consistency. You do not edit files.
Inputs: canon.json, registry.json, story.md, steps.md (paths or content).
Check each entity and each story section against the canon, axis by axis:
  geography, climate and weather, era, technology, tone, physics or magic.
  (Checklist: ~/.agents/skills/imagine/references/canon-and-registry.md, "Semantic review checklist".)
Also flag: contradictions between entities, story beats that use an entity against its summary, characters with no role in the story.
Return: one fenced JSON block, then nothing else. Return an empty list if you find nothing; do not invent findings.
<never-spawn rule>
```

Return:

```json
{
  "findings": [
    {"id": "mirror-lake", "axis": "geography", "problem": "summary describes a lake in red-waste", "fix": "replace with an oasis pool at palm-well", "severity": "high"}
  ]
}
```

The main agent answers every finding with `applied` or `rejected: <reason>` in `run-log.md`.

## Design brief (role `build`, P9)

One child. It is the only producer of assets in a run.

```text
Role: you are the art lead for <world name>, working under the creative director's art direction.
Skill: read and follow ~/.agents/skills/imagine-design/SKILL.md.
Lake: <absolute lake path>. Write only under <lake>/assets/.
Art direction (binding): <lake>/design.json. Your style lock extends it and may add fields, never change one.
You may research visual references on the web; record each in assets/references.md. A reference that argues for a different palette, proportion, drawing style, lighting or any other design.json value becomes a proposal, not a change.
Context: canon.json, registry.json (subjects by id), story.md outline: <paths>.
Assets: the asset list in design.json. <"all" | the ids to redo after an accepted proposal>.
Return: one fenced JSON block (shape below), then nothing else.
<never-spawn rule>
```

Return:

```json
{
  "provider": "pixellab",
  "passed": 14,
  "failed": [{"id": "hero-walk", "reason": "pixel-scale check failed after 3 attempts"}],
  "pending": [],
  "additions": [{"path": "direction.dithering", "value": "none", "why": "design.json left it open"}],
  "proposals": [
    {"path": "palette.colors", "current": ["#1a1c2c", "…"], "proposed": ["#1a1c2c", "…", "#3b5dc9"],
     "why": "night scenes need a cold shadow tone", "evidence": "assets/sheets/night-test.png"}
  ],
  "manifest": "assets/manifest.json"
}
```

`pending` lists assets that waited for a provider key; the child names the `~/.agents/.auth/` placeholder to fill.

## No spawn tool

When the harness exposes no spawn tool, run each brief inline, one after another, and hold yourself to the same return shape, the same per-wave limit and the same ceiling. Say so in `run-log.md`.
