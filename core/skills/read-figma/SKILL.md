---
name: read-figma
description: "Decode local Figma .fig files: unpack, resolve a node-id from a Figma URL, extract text and component names. Use whenever a .fig or Figma node-id is mentioned — .fig is compressed binary with a GUID trap that causes false negatives. | recommendedRole: explore | aliases: figma-read, inspect-fig, decode-figma, parse-fig-file."
metadata:
  recommendedRole: explore
  aliases: figma-read, inspect-fig, decode-figma, parse-fig-file
  cliDependencies:
    required: [python3, zstd]
    optional: []
---

## Local deterministic first

Use `scripts/fig.py --json ...` for bounded output and `scripts/fig.py verify-node <scene.bin> <node-id>` for presence checks.

# Reading Figma .fig files

Figma `.fig` exports are self-contained and inspectable offline — no Figma account, no API token, no MCP. This matters when you need to check a design claim (e.g. "the Jira ticket links node X; is X really the publications card?") and the only thing you have is a file someone dropped in the repo.

The format is straightforward once you know its two traps. Both traps produce **false negatives that look like solid conclusions**, which is the real hazard: you don't get an error, you get a confident wrong answer.

## Use the bundled script

`scripts/fig.py` implements everything below. Prefer it over re-deriving the format by hand.

```bash
FIG=scripts/fig.py

python3 $FIG unpack "design.fig" /tmp/figout   # -> /tmp/figout/scene.bin (+ images/, meta.json)
python3 $FIG node  /tmp/figout/scene.bin 1340-30358   # resolve a node-id from a Figma URL
python3 $FIG grep  /tmp/figout/scene.bin "LuseKontroll"  # find literal text w/ context
python3 $FIG text  /tmp/figout/scene.bin [filter]     # dump text runs, optionally filtered
python3 $FIG names /tmp/figout/scene.bin              # ASCII component/symbol key refs
```

Read the rest of this file when the script's output needs interpreting, or when you need to work the format manually.

## Trap 1: node GUIDs are varints, not text

**This is the one that will burn you.** A Figma URL says `?node-id=1340-30358`, so searching the decoded graph for the string `1340:30358` feels natural. It returns zero hits **even when the node is present**, because node GUIDs are encoded as kiwi varint pairs, not ASCII.

```python
def varint(n):
    out = bytearray()
    while True:
        b = n & 0x7F; n >>= 7
        out.append(b | 0x80 if n else b)
        if not n: return bytes(out)

key = varint(1340) + varint(30358)   # -> bc0a96ed01
```

Confusingly, the file **does** contain ASCII `NNN:NNN` tokens — but those are component/symbol *key references*, a different field. Their presence makes the ASCII search look like it's working, which is exactly why the false negative is so convincing: you see `1337:2763` in the dump, conclude the index is textual, search for `1340:30358`, find nothing, and report the node as missing.

`fig.py node` does this correctly and prints an expected-by-chance figure alongside the hit count. A 5-byte needle in a 30MB haystack is expected ~0.00003 times, so even 1–3 hits is real signal, not coincidence. Trust that number over your intuition about "only 3 hits seems low".

**Before ever reporting a node as absent**, confirm you searched varints and not text. Absence claims about a binary format are load-bearing — someone may re-export a 140MB file because of them.

## Trap 2: text is NUL-delimited, and `strings` misleads

Text runs look like `b'Hanken Grotesk\x00Medium\x00HankenGrotesk-Medium\x00*\x01Hva gjør du...'` — font family, style, postscript name, then `\x00*`, a length/tag byte, then UTF-8. The delimiters are **NULs, not spaces**. A space-based regex matches nothing and reads as "this file has no text."

Plain `strings` is also unreliable here: it fragments UTF-8 (Norwegian `ø`/`å` split runs apart) and buries text in binary noise. Prefer `fig.py text` / `fig.py grep`, which collapse binary runs to ` | ` so the readable content survives with its surrounding structure intact.

## File format

`.fig` is a **ZIP**:

| Member | What it is |
|---|---|
| `canvas.fig` | the scene graph (kiwi container) — the part you want |
| `meta.json` | file name, canvas `render_coordinates` (bounds of the saved pages) |
| `thumbnail.png` | small preview |
| `images/` | bitmap assets, content-hash named — usually most of the file size |

`canvas.fig` is a kiwi container:

```
b'fig-kiwi' | version:uint32 | (length:uint32 | payload)*
```

Two sections in practice: a small **schema** (raw deflate, `zlib.decompress(blob, -15)`) and a large **scene graph**. The scene graph is commonly **zstd** (magic `28 b5 2f fd`), not deflate — assuming deflate throws `zlib.error` and tempts you into thinking the section is encrypted. Sniff the magic instead of assuming, since this varies by version.

Note `zstandard` (Python) is frequently missing while `/usr/bin/zstd` is present; `fig.py` tries the module then falls back to the CLI.

## Interpreting what you find

- **`meta.json` → `render_coordinates`** gives the saved canvas extent. Two exports with identical extents and identical node sets are the same content — useful for proving a re-export added nothing but images.
- **"Partial file saved" in the filename** means Figma only wrote the pages that had been loaded in that session. It's a real phenomenon, but don't jump to it as the explanation for a missing node until you've ruled out Trap 1 — it costs the user a large re-export and usually isn't the cause.
- **Frame/component names sit near their nodes.** Once `fig.py node` locates a GUID, read the surrounding context for names (`varsling`, `Frame 1315`, `report`) and text. That adjacency is what lets you say what a node *is*.
- **Compare against the codebase.** Sampling a PNG export's colours and matching them to SCSS tokens (`#59CD8B` = `$primary-green`) is often the fastest way to identify which existing component a design is, and whether it's already implemented.

## What this is good for

The high-value use isn't extracting pixels — it's **checking a claim**. A ticket links a node and asserts it's the design for some feature; this skill tells you what the node actually is. Answers worth reporting look like:

- "Node `1340-30358` resolves to a frame named `varsling` containing *'Hva gjør du hvis du finner døde eller syke dyr?'* — it's the `help-card` dark variant, not the publications card the ticket describes."

When the design contradicts the ticket, say so and stop — that's a spec bug for the reporter, and no amount of further decoding fixes it. Guessing the intended design from adjacent frames is how wrong components get built. Separate what's actually blocked from what isn't: a blocked visual design rarely blocks the logic work in the same ticket.

Report what you verified and how, so the next reader can re-run it. If you hit a genuinely new wrinkle in the format, add it here.

`references/worked-example.md` walks through a real case (VET-1143) where both traps fired and the varint one produced a confident wrong answer that cost a 142MB re-export. Worth reading if you're about to report a node as missing, or if a design claim isn't lining up.
