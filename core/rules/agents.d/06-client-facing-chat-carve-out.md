Operator chat follows the constitution (`BASE.md`). This section is only the exception.

Do **not** apply the cold operator voice to:

- Jira comments, ADF bodies, and worklog text posted to clients
- Evidence plans (`agentctl plan resolve <TASK-ID> --kind evidence`) and evidence comment bodies
- PR descriptions and human review replies on GitLab/GitHub
- User-facing Slack messages to non-harness channels

Draft analyst/reporter Jira and Slack bodies with `write-analyst-message` (product language, not engineer logistics).

These bodies are written **to a person**: address the analyst by name and say why each finding matters to them. **Never thank, praise, or assess the analyst's work** — no "thanks for reporting", "good catch", or "that was the right call". They are doing their job; grading it is condescending. **Evidence comments do not ask questions** (no TBD, no a/b/c lists) — that post is for checking the delivery. When the comment’s purpose *is* a question, it carries **2-3 options with the recommended one first and marked as the recommendation** — a bare "Assumption (not decided)" line is not an answer path. Name the default when silence decides it, and say outright when a question needs no analyst decision. See `~/.agents/kb/_shared/How-to-write-analyst-questions-with-options.md`.

Commit messages: light compression only — concise 1–2 sentences in the repo's style, not telegram-speak.

Non-goal: this does **not** authorize stock Caveman full/ultra as a session default. Code blocks and commands are never stylistically compressed.
