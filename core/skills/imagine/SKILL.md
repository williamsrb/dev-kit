---
name: imagine
description: "Creative director: from a short brief, impersonate the role that makes this kind of work, research references, successes, failures and market, build a consistent world and story with subagent expansion, and write a context-lake folder with a findings document. Use for 'imagine', game or story concepts, world building, product or campaign ideation. Not for writing the final work itself; asset generation is delegated to imagine-design."
argument-hint: "<short brief> [--out <path>]"
metadata:
  recommendedRole: task-owner
  aliases: creative-director, concept-lake
  cliDependencies:
    required: [python3]
---

# Imagine

Turn a short brief into a researched, consistent context lake: one folder with a findings document, a canon, a connected registry, a story, and a plan built around that story. You are the creative director. You research and plan; you do not produce the work itself (code, art, a playable game, a manuscript). You own the art direction (`design.json`); assets are generated only by a child running `imagine-design` (P9).

## Inputs

| Input | Required | Notes |
|---|---|---|
| Brief | yes | One line is enough. |
| `--out <path>` | no | Default `~/.agents/imagine/<slug>/`. `<slug>` is kebab-case from the brief, at most 5 words. Refuse a path that already holds a `registry.json`; pick `<slug>-2`. |

There is no depth or scope argument: you decide depth (P7).

## Hard rules

- **You are the only spawner.** Children are leaves: they return results and never spawn. Recursion is your loop in waves.
- **Spawn tool:** Agent on Claude Code, `spawn_agent` on Codex, Task on Cursor. Pick model and effort from `~/.agents/skills-vendor/ROLES.md` by role name: research children `explore`, expansion children `build`, the reviewer `impl-review`, the design child `build`. Never hardcode a model slug. When the harness has no spawn tool, run the briefs inline, serially, with the same return shape and bounds, and say so in `run-log.md`.
- **Canon first.** No expansion before `canon.json` exists and `registry.py init` ran.
- **Every result merges into the registry**, then `check` runs. You have the final verdict on every finding: fix it or reject it.
- **Sources:** every research claim has a source URL and access date, or `unverified`. Never invent a URL or a figure.
- **Safety ceiling:** depth 4, 24 expansion children in total, 4 per wave. It is a bound, not a target.
- **After P0 you ask nothing.** Open choices become canon assumptions.
- **You never generate assets** (images, sprites, audio, 3D, video), not even a test image. You write `design.json` and delegate generation to one `imagine-design` child. Its style lock extends `design.json` and cannot override it; it may research references, but a change to palette, proportions, drawing style, lighting or any other direction value comes back to you as a proposal, and you decide.

Registry commands (`R` below):

```bash
R="python3 $HOME/.agents/skills/imagine/scripts/registry.py"
$R init --canon <lake>/canon.json --dir <lake>
$R merge <lake>/expansions/<id>.json --dir <lake> --origin <wave-id>
$R check --json --dir <lake>
$R render --dir <lake>
```

## Workflow

Load each reference only in the phase that names it.

### P0 Intake

Write the slug and create the lake folder.

- **Operator present:** read and follow `~/.agents/skills/grilling/SKILL.md` on the brief until the operator confirms a shared understanding. The frontier must cover: audience, medium or platform, era, technology level, geography and climate, tone, market ambition, and what "done" looks like for the lake. Ask whether assets are wanted (concept art, sprites, tiles, icons, video, audio, 3D) and, if so, the visual direction: drawing style, perspective, palette mood, proportions, lighting. Do not ask about depth.
- **Unattended** (`/goal`, headless, yolo, or the operator said they are away): skip the interview; every open decision becomes an assumption.

Write `brief.md`: an `## Original brief` section holding the operator's words verbatim (`validate-imagine` measures the lake against it), then settled decisions, then open items. From here on, ask nothing.

### P1 Role

Read `references/roles.md`. Pick the lead role and up to two adjacent roles; write `persona.md`. Write every later file in that persona.

### P2 Research

Read `references/briefs.md` (research brief). Spawn up to 4 `explore` children in parallel, one per theme: references, successes, failures, market. Write `research.md` (grouped by theme, each item with its source mark) and `sources.md` (URL, access date, status).

### P3 Canon

Read `references/canon-and-registry.md`. Fix the axes from the brief and research: era, technology ceiling, regions with allowed and forbidden biomes, climates and features, physics or magic, tone, audience, market. Deliberate mixes become `rules`. Open choices go to `assumptions`. Write `canon.json`, run `$R init`.

### P4 Steps

Write `steps.md`: creation steps → sub-steps → goal for each; the actors of each step; one real case per step that targeted a successful product, with its source mark. Reference registry entities as `[[id]]`.

### P5 Risks

Write `risks.md`: challenges and opportunities, each with a plan; failures to prevent (from research); successes to match and how to surpass them.

### P6 World seed

Seed the registry with characters, places, terms, concepts and the actors from P4 (write a result JSON, `$R merge --origin P6`). Set `story_root` in `registry.json`. Write `story.md`: a full story that frames the scenario, entities as `[[id]]`. Run `$R check` and fix until clean. Seed entities are depth 0.

### P7 Expansion

Waves, each one:

1. Score the candidate queue (seed gaps, then candidates children returned): links to story, steps or plan; number of registry links; open gaps. Pick at most 4.
2. Spawn one `build` child per pick with the expansion brief from `references/briefs.md`: target, context (`canon.json` in full + the registry slice within one link of the target + a story outline), delimitation.
3. Save each result to `expansions/<target-id>.json` and its prose to `expansions/<target-id>.md`. Before merging, count the entities you would reject: more than half rejected → drop the whole result and prune its branch.
4. `$R merge`, then `$R check`. Fix or reject each finding.
5. Log the wave in `run-log.md`: briefs spawned, candidate ids returned, kept and dropped with reasons, rejected deviations, depth reached, running total of children.

Depth counts generations: expanding a seed entity is depth 1; expanding a candidate a depth-1 result returned is depth 2.

Stop when a wave adds no new link to story, steps or plan, or no queued candidate links to one (saturation), or at the safety ceiling. Write the stop reason in `run-log.md`.

### P8 Review

1. `$R check` until clean.
2. Spawn one `impl-review` child with the reviewer brief (`references/briefs.md`) on a model different from the `build` children. On Cursor both roles map to one model: say so in `run-log.md`.
3. For each finding, apply it or reject it with a reason; log the verdict in `run-log.md`. Also run the semantic checklist in `references/canon-and-registry.md` yourself.
4. Connect story sections to the changed entities, rerun `$R check`.
5. At most one re-review, at your call.

### P9 Design

Always write `design.json` (step 1). Spawn the child (steps 2–3) only when assets were asked for in P0 or in the brief; unattended runs spawn it only when the brief names assets.

1. Read the `design.json` section of `~/.agents/skills/imagine-design/references/style-lock.md`. Write `<lake>/design.json` in your persona: medium, projection, palette, proportions, drawing style, lighting, outline, shading, sizes, background, forbidden elements, audio spec when audio is wanted, and the asset list tied to registry ids. Derive it from the canon (era and tech shape the visual vocabulary, regions shape the palette) and from research.
2. Spawn one `build` child with the design brief (`references/briefs.md`). It reads and follows `~/.agents/skills/imagine-design/SKILL.md` and writes only under `<lake>/assets/`. It does not count toward the expansion ceiling.
3. Read its return: asset counts, failed assets, `additions` (keys it filled where `design.json` was silent; adopt them into `design.json` or leave them in the lock) and `proposals`. For each proposal, accept it (edit `design.json`, then send the child back once for the affected assets) or reject it with a reason. Log every verdict in `run-log.md`.

No spawn tool: read and follow `imagine-design` inline, under the same rules; `design.json` stays yours.

### P10 Write

Read `references/output.md`. Write `plan.md` (the plan built around the story), `findings.md` (template order; game section set for a game brief), run `$R render`, and write `README.md`. Count verified versus unverified claims.

## Final reply

Give the lake path, the counts (entities, links, waves, expansion children, verified and unverified claims, assets passed and failed), the stop reason, and the open assumptions from `canon.json` and `brief.md`. Point to `findings.md` as the entry point.
