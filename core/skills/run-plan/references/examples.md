## Examples

**Implementation plan:** user says `run PROJ-341` or `run hubspot-form-macro` or path `~/.agents/plans/<TASK-ID>.md` / folder `~/.agents/plans/<TASK-ID>/`  
→ `agentctl plan resolve <TASK-ID>`; read `entry` only; scan `~/.agents/kb/implementation`; execute coding todos. Local slugs skip the branch-equals-key assert.

**Evidence plan:** user says `run evidence PROJ-341` or `run evidence hubspot-form-macro` or a path that `plan resolve --kind evidence` returns  
→ read evidence plan only; scan `~/.agents/kb/testing`; follow **Execution** (capture / Jira comment when `mode` is `jira` / chat report when `local` / KB write-back).

**Validation-oriented plan:** steps that are review/lint/gate focused  
→ scan `~/.agents/kb/validation`; record reusable checklists there.

**Multiple plans at once:** “run PROJ-339, PROJ-341, and PROJ-343” or two+ plan paths  
→ do **not** execute here; read and follow `multitask-same-repo`.
