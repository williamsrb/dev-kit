# devkit

An AI-tooling development kit that installs on a fresh machine in two steps,
with profile isolation so several agent harnesses (for example an Enonic one
and a PHP one) run side by side on a single box without colliding.

1. `bootstrap.sh` installs dependencies and writes no configuration.
2. `install.py` writes settings and materializes profiles.

Neither step assumes the other has network access, and neither escalates
privilege for configuration.

## Status

Phase A0 of the implementation plan. The export source (`~/.agents`) has been
committed and its pre-export blockers fixed; nothing is exported into this
repository yet.

The plan lives outside this repository while it is being executed, at
`~/.agents/plans/devkit/` (start with `plan.md`). A8 restates its design
sections as `docs/`, with the rationale under `docs/maintainer/`; this README
becomes the documentation index at that point.

## Layout

| Path | Contents |
|------|----------|
| `devkit.yaml` | fork topology: `lineage_id`, `fork_id`, `upstream` |
| `examples/` | GUI-in-Docker sketches from the isolation assessment; see below |

## About `examples/`

Three Dockerfiles and their run scripts, kept as the evidence behind the
decision *not* to containerize the harness for profile isolation. They are IDE
launcher sketches, not harness images: none install python, node, tesseract or
Playwright browsers, and `Dockerfile.x11` carries a real bug
(`apt-get install -p -y`). Read them as a record of what was rejected and why,
not as something to run.
