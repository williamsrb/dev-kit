---
id: how-to-give-an-argparse-cli-the-bare-equals-help-contract
when_skills: [run-plan, plan-implementation]
inputs: [a python argparse CLI with subparser groups]
outputs: [bare invocation == --help, exit 0, at every level]
stop_if: []
read: whole
prose: caveman-lite
---

# Give an argparse CLI the bare-equals-help contract

Contract: bare invocation and `--help` write identical text to stdout and exit
0, recursively for every group. Only a genuine mistake — unknown subcommand or
bad flag — writes usage to stderr and exits 2. Argparse does not do this by
default: `required=True` subparsers make bare invocation an error.

## Procedure

1. Set `required=False` on every `add_subparsers(...)`, top level and per group.
2. Give each group parser its own default action that prints that group's help:

```python
def _help_action(parser):
    def run(_args):
        parser.print_help()
        return 0
    return run

group_parser.set_defaults(func=_help_action(group_parser))
```

   A subcommand's own `set_defaults(func=…)` overrides the group's, so a real
   command still runs.
3. In `main`, the no-`func` case becomes exit 0 instead of exit 2.
4. **Check unknown arguments before the no-`func` branch**, or a bad flag on
   bare invocation exits 0:

```python
args, unknown = parser.parse_known_args()
if not hasattr(args, "func"):
    if unknown:
        parser.error("unrecognized arguments: " + " ".join(unknown))
    parser.print_help()
    return 0
```

5. Verify every group in one loop rather than spot-checking; compare output and
   both exit codes.

```bash
for g in $(cli --help | awk '/^    [a-z]/ {print $1}'); do
  diff <(cli "$g" 2>&1) <(cli "$g" --help 2>&1) >/dev/null \
    && echo "OK   $g" || echo "FAIL $g"
done
```

## Pitfalls

- Ordering the unknown-argument check after the help branch is the one bug this
  change introduces. It passes every positive test.
- `parse_known_args` plus `nargs=REMAINDER` subcommands (a passthrough group)
  need their extras merged before the unknown check, not after.
- Changing bare exit 2 to 0 changes any caller that used the exit code to mean
  "no arguments given". Grep for callers before shipping.
