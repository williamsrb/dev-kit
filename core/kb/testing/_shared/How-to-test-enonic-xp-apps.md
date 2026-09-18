---
id: how-to-test-enonic-xp-apps
when_skills: [test-xp-apps]
read: section
prose: caveman-lite
---

# How to test Enonic XP apps

Open one recipe. Do not load both JUnit and Jest files.

| Recipe | File |
|--------|------|
| XP Test Framework (JUnit + JS) | [How-to-test-enonic-xp-apps-junit.md](How-to-test-enonic-xp-apps-junit.md) |
| Jest + Mock XP | [How-to-test-enonic-xp-apps-jest.md](How-to-test-enonic-xp-apps-jest.md) |

## Choosing a Framework (full table)

| Scenario | Recommended |
|----------|-------------|
| Tests use XP APIs with runtime fidelity | XP Test Framework |
| XP APIs without booting XP | Jest + @enonic/mock-xp |
| Pure logic | Jest |
| Fast iteration | Jest |
| Integration-style XP behavior | XP Test Framework |
| DOM needed | Jest + jsdom |

## Choosing What to Test

| Change type | Test project / framework | What to verify |
|-------------|--------------------------|----------------|
| Processor (data fetching) | Jest SERVER | Props output, image resolution, HTML processing, CTA logic |
| Lib module | Jest SERVER | Input/output, edge cases, error handling |
| Service / controller | Jest SERVER or XP Test Framework | Response shape, status codes, auth |
| React component (prototype) | Jest CLIENT | Rendering, props, conditional UI |
| React component (XP-native) | Jest CLIENT | Rendering, variation switching |
| XML descriptor only | N/A | Manual test plan (Content Studio) |
| i18n only | N/A | Manual test plan (verify labels) |

## Manual Test Plan Template

When automated testing is not feasible:

- Affected endpoints, services, or modules
- Happy path steps and expected outcomes
- Failure path and error handling
- Auth/permissions behavior
- Data side effects (repo/content)
- Rollback or safety notes for production-sensitive code

## Verification Checklist (Full)

| Area | Checks |
|------|--------|
| Processors | Props output matches expected shape, image URLs resolved, HTML processed |
| Endpoints/Services | Request/response shape, status codes, content-type |
| Auth/Permissions | Logged-in vs anonymous, role-based access |
| Data effects | Content create/update/delete, repo changes |
| Edge cases | Empty input, invalid IDs, missing config, null fields |
| High-risk areas | Negative cases, timeout/error handling, idempotency where relevant |
