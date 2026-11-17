# Decision points

Technical choices the ticket does not make for you. They are engineering calls, not analyst TBD. Without this step the planner picks the model's habit (JWT, Redux, a new queue) and nobody notices.

## When a decision point exists

Harvest one when the task **introduces or changes** any of these:

- Authentication or session strategy (sessions, OAuth/OIDC, JWT, API keys)
- Authorization model (roles, ACL, per-resource rules)
- Persistence: data store, persisted schema, or migration
- Sync vs async work (request path, job, queue, scheduler)
- Caching layer or invalidation strategy
- Frontend state management or rendering strategy (SSR, CSR, static)
- API style or public contract (REST, GraphQL, webhook, event)
- File or media storage
- A new runtime dependency or external service

Not a decision point: the codebase already does this the same way and the ticket does not ask to change it. Follow the precedent and cite it.

## Resolve in this order

Stop at the first step that gives a sourced answer.

1. **Codebase precedent.** The repo, a sister part, or the platform already solves it (e.g. Enonic XP ID providers for login). Cite the path.
2. **Decision guide.** Open `~/.agents/kb/implementation/llm-index.md` and look for a `How-to-choose-*` row whose topic matches. Apply its criteria to this project's facts. Cite the guide and the scenario row that matched.
3. **Advisor.** Spawn a subagent only when no guide covers the scenario, the guide's criteria do not settle it, or the choice is gated (below) and costly to reverse. One advisor per decision point.

## Advisor brief

Run it on the `plan-review` role (`~/.agents/skills-vendor/ROLES.md`), a different model than the planner. If the harness cannot spawn a subagent, answer it inline after reading only the guide and the facts list.

Pass the facts, never your leaning. Do not write "should we use X?" or name the option you expect.

```text
Decision: <one line, neutral: "auth strategy for the editor portal">
Facts:
- <clients: same-origin browser / SPA on other domain / mobile / third-party / service>
- <existing platform or IdP, existing patterns in the repo with paths>
- <hard constraints from the PRD: compliance, revocation, scale, hosting>
- <what is out of scope>
Guide: <path of the closest How-to-choose-* guide, or "none">
Return: 2-3 options, recommended first. For each: when it fits, the criterion
that decides it for these facts, main risk. Then the facts you lacked that
would change the recommendation. Do not edit files.
```

The advisor advises. The planner decides and records.

## Record

Write each decision point under `### Technical decisions` in `tbd.md` (`write-and-validate.md` template), both modes:

- `**<decision>:** (a) <chosen>. Source: <precedent path | guide path + scenario | advisor>. Gate: yes|no. Rejected: <option> because <one line>.`

Encode the chosen option as a Constraint or in Suggested Technical Approach.

- **Gate: yes** when it hits the Operator Gate (auth or permissions, persisted schema or migration, public contract, new cost). Surface it in the planning summary for the operator to confirm. It is not an analyst TBD, in either mode. Do not phrase it with `write-analyst-message`.
- **Gate: no** is decided. Not a coding stop.
- **Guide gap:** when the advisor answered with `Guide: none`, add one line to the planning summary naming the topic. Do not write a new guide unless the operator asks.
