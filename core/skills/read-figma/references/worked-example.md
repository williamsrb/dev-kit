# Worked example: verifying a ticket's Figma link (VET-1143, 2026-07-17)

A real case, kept because both traps in SKILL.md fired here and the second one
produced a confident, wrong, user-visible answer.

## The question

Jira VET-1143 said: implement the research-publications card per Figma
`?node-id=1340-30358`. The spec claimed the card shows project title, intro,
project period (start–end year), and research areas. Was that node really that
card?

## What happened

The design was delivered as three PNG exports plus a `.fig`. Colour-sampling the
PNGs against the SCSS tokens identified them immediately:

| PNG | card bg | token | component |
|---|---|---|---|
| kurs.png | `#59CD8B` | `$primary-green` | `help-card--green` |
| varsling.png | `#1C4FB9` | `$primary-dark-blue` | `help-card--blue` |
| varsling-1.png | `#091A3E` | `$primary-black` | `help-card--dark` |

None showed a period, research areas, or tags — so none matched the spec's card.
That part held up.

Then the mistake: searching the decoded scene graph for the ASCII string
`1340:30358` returned nothing, while ASCII tokens like `1337:2763` *were*
present. Conclusion drawn: "the node is absent, this is a Figma partial save,
the page was never loaded." Reported to the user with a remediation plan.

The user re-exported the whole file — 142MB — which of course changed nothing.
Its scene graph was byte-identical to the first export (same 2215 ASCII tokens,
15 bytes of session metadata apart); only bundled images differed (218 vs 124).
That identity was itself worth reporting, but it was answering the wrong
question.

The user then supplied `1340-30358.png`, which was `varsling-1.png` renamed.
Treating the rename as a claim to test rather than a shortcut to dismiss is what
broke it open: searching the **varint** GUID `bc0a96ed01` found the node in 3
places, in both exports, all along — adjacent to a frame named `varsling` and
the text *"Hva gjør du hvis du finner døde eller syke dyr?"*.

## The finding

Node `1340-30358` **is** the dark `help-card` — already implemented at
`prototype/src/modules/cards/help-card-dark.php`. The ticket's design link points
at the wrong component. That is a spec bug for the reporter; no further decoding
resolves it.

The same file contains a component named `report` (`221:3074`) with real research
content (*"LuseKontroll: Statistisk modellering av kontrollstrategier for
lakselus"* + intro), which is suggestive of the intended design — but its tags
read `Publikasjon: 1-2024` and a species tag, i.e. the report-listing usage, not
period + research areas. Suggestive is not conclusive; building on it would have
meant guessing at a component.

## Lessons worth carrying

1. **An absence claim about a binary format is a strong claim.** "The node isn't
   there" cost the user a 142MB export. Before asserting absence, prove the
   search method finds a node you *know* exists — `fig.py node` on a known-good
   GUID is a two-second control.
2. **Partial evidence that looks like a working method is the trap.** Seeing
   ASCII `1337:2763` made the ASCII search feel validated. It was a different
   field entirely.
3. **Test the user's claim before discounting it.** The renamed PNG looked like
   a shortcut and was in fact correct. The mtime showed it was a rename; that
   made it *unverified*, not *wrong*.
4. **A design that contradicts the ticket is the finding.** Stop and route it to
   the reporter rather than inferring intent from neighbouring frames.
5. **Separate what's blocked from what isn't.** In VET-1143 the JS fixes (null
   guards, query restructuring) were design-independent and could land while the
   design question went back to the reporter.
