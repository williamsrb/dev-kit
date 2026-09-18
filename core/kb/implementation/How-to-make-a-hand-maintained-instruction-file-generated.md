---
id: how-to-make-a-hand-maintained-instruction-file-generated
when_skills: [run-plan, plan-implementation]
inputs: [~/.agents/rules/AGENTS.md, ~/.agents/rules/*.mdc]
outputs: [rules/manifest.json, rules/agents.d/, bin/generate-agents-md.py]
stop_if: [the generator cannot reproduce the current file byte for byte]
read: whole
prose: caveman-lite
---

# Make a hand-maintained instruction file generated

`rules/AGENTS.md` was maintained by hand beside the Cursor `.mdc` rules, guarded
only by a "keep in sync" note. Same shape appears wherever one aggregated file
restates many small sources. Converting it safely is a measurement problem
first, an authoring problem second.

## Scope

Aggregated instruction or config file whose sections restate other files. Not
for a file whose content is genuinely original.

## Procedure

1. **Split the file into regions before anything else.** Header, embedded
   constitution, per-section body, trailer. Tool-managed blocks
   (`<!-- context7 -->`, `<!-- graft:start -->…<!-- graft:end -->`) are a
   *trailer*: extract them verbatim and never regenerate their contents.
2. **Measure duplication; do not trust the audit that sent you.** Compare each
   section against its source with the transform the aggregate actually
   applies. For AGENTS.md that is: strip frontmatter, strip the H1, demote
   remaining headings one level. Before demotion 2 of 17 sections matched;
   after, 3. The plan had recorded 8.
3. **Classify each section, do not force one mode.** `mdc` = embed the source
   verbatim. `file` = the aggregate's text is a translation or a merge of
   several sources, so it gets its own file and that file is the only source.
   Forcing every section into "embed verbatim" rewrites 14 rule bodies and is
   not the change that was asked for.
4. **Gate on byte-for-byte reproduction.** Run the generator with `--stdout`
   and `diff` against the file on disk *before* changing any content. If it is
   not identical, the region split or the transform is wrong. This is the
   whole safety net — without it a content bug hides inside a large diff.
5. **Only then** resolve the drift the comparison exposed, one commit apart
   from the mechanical split if the diff is large.
6. Give the generator `--check` (exit 1 on stale), `--apply`, `--stdout`, and a
   dry run as the bare action. Add `--layer`/`--profile` if the point was
   scoping, and assert in a test that the filter actually drops sections.
7. Rewrite the file's own "keep in sync" header to say it is generated and name
   the command. A generated file that still tells the reader to edit it will be
   edited.

## Pitfalls

- **Heading demotion must skip fenced blocks.** A `# comment` inside a ```bash
  block is not a heading; demoting it corrupts the sample.
- Diff counts do not tell you contradiction from expansion. Read the
  source-only lines. A 2-line diff was a live contradiction; a 33-line diff was
  a faithful expansion.
- Drift runs both ways. The aggregate is sometimes the correct side and the
  small source file the stale one. Decide per pair, by which one agrees with
  the skill that consumes it, not by which file is bigger.
- JSON, not YAML, for the manifest if the surrounding tooling is stdlib-only.
  PyYAML being installed on the authoring machine is not the same as it being
  available on a machine the kit bootstraps.
- Keep the layer tags in the manifest, not in the section bodies. Bodies move;
  the list is what a profile filters.
