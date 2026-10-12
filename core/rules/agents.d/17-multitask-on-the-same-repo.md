When the user wants **multiple PRD tasks on the same repo at once** (same Epic/Release or local slugs; batch implement, parallel worktrees, several PRD→plan→impl flows), read and follow the `multitask-same-repo` skill immediately. The alias `mult` does **not** activate it (`mult` = `orchestrate`, ordinary prompt-splitting). Single task/branch: ignore this.

Hard constraints:

1. **Isolation = `git worktree`**: one parent checkout, one worktree + branch per task key. No full copies; never triplicate `node_modules`/build trees.
2. **Subagents share only via disk** (PRDs, plans, a short `DECISIONS.md`). Briefs are self-contained and thin: cite those files, forbid re-deriving shared conventions.
3. **Phase-split into fresh sessions**: never plan-validation and implementation (or QA) in one transcript. `/model` does **not** reset context.
4. **Shared work once, before fan-out** (helpers, path rules, cross-cutting ports). Never an identical port into each worktree from parallel agents.
5. **One implementer per worktree**, confined to its path, asserting `git branch --show-current` matches the task key before edits. Orchestrator stays thin and never holds every plan's research dump.
6. **QA / lint / evidence = fresh session(s)**, preferably one per branch.
