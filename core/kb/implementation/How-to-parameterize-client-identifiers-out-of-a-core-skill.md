---
id: how-to-parameterize-client-identifiers-out-of-a-core-skill
when_skills: [run-plan, plan-implementation, validate-impl]
inputs: [~/.agents/skills/<skill>, ~/.agents/config/client-overlay.json]
outputs: [neutral core skill, client-overlay.json, client-overlay.example.json]
stop_if: [the identifier is load-bearing and no overlay key can carry it]
read: whole
prose: caveman-lite
---

# Parameterize client identifiers out of a core skill

A skill that is core to the harness must not name a client, a client's hosts, or
a client-specific KB folder — otherwise it cannot ship to anyone else, and a
second client silently inherits the first one's URLs. Applies before exporting
or sharing skills.

## Procedure

1. `grep -rn "<client>\|<client-domain>" <skill>` per skill. Sort the hits into
   three kinds, because each takes a different fix:
   - **Illustrative** (an example URL, an example path). Replace with a
     placeholder shape: `https://review.<project>.<env-domain>/`,
     `~/Workspace/Projects/<project>`. Keep the shape — a placeholder that
     drops the path structure loses the instruction.
   - **Routing** ("open `<client>/How-to-…`"). Make the route generic and let
     the project folder supply the specifics:
     "open `<project>/How-to-…`; it names where that project's pages live".
     The skill keeps the workflow, the KB keeps the client.
   - **Behavioural, in code**. Move the value into a config file. This is the
     only kind that needs a code change.
2. For the code kind, add `config/client-overlay.json` with an
   `AGENTS_CLIENT_OVERLAY` env override, plus a committed
   `client-overlay.example.json`. Core ships the example; the client overlay
   profile ships the real file.
3. **Absent config must disable the check, not guess.** A fallback heuristic
   ("any bare host URL is a defect") fires on legitimate links. Return `None`
   and skip.
4. Prove the replacement matches the original on a case table before trusting
   it. Include a negative case per pattern and one host that must *not* match.
5. `grep` again and expect zero hits in the skill.

## Pitfalls

- Deleting the client specifics instead of parameterizing them breaks the
  workflow that depends on them. The plan's wording matters: "parameterize
  rather than delete".
- A hand-written regex over hosts is where the bug hides. Rebuilding
  `check-evidence-comment.py`'s pattern from config revealed the original
  required `[^/\s"'<>]+` before its alternatives, so `https://web02-stg3…`
  never matched — the staging half of the rule had never fired. Diff old
  against new on a case table; a silent improvement is still a behaviour
  change to report.
- Build the pattern from globs with `re.escape` on the literal parts. Do not
  interpolate config values into a regex raw.
- A `-multitask` suffix or similar layout convention is not a client
  identifier. Do not neutralize structure that is generic.

## Sample data

```json
{
  "env_root_host_patterns": ["*k8s.example.com", "web02-stg*.example.com"],
  "git_host": "git.example.com",
  "example_project": "acme-group"
}
```
