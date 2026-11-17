---
id: how-to-choose-an-auth-strategy
when_skills: [plan-implementation, validate-plan, validate-impl]
topic: auth-strategy
keywords: [choose, auth, strategy, session, sessions, oauth, oidc, jwt, login, authentication]
inputs: [clients, existing platform or IdP, revocation needs, services that verify identity]
outputs: [chosen auth strategy with the scenario row that decided it]
stop_if: [the repo or platform already authenticates users and the ticket does not ask to change it]
read: section
prose: caveman-lite
---

# How to choose an auth strategy

JWT is not the default. It answers one scenario: many services verifying identity without calling back. For a single web app it adds the problems sessions do not have (no revocation, logout that does not log out, tokens in browser storage).

## Procedure

1. Check precedent first. If the repo or platform already authenticates users (Enonic XP ID providers and `lib-auth`, a framework auth module, a gateway), use it and stop. Do not add a second mechanism next to it.
2. Collect the facts:
   - Clients: same-origin browser, SPA on another domain, mobile/native, third-party apps, other services.
   - Identity source: local users, corporate IdP (Entra ID, Okta, Keycloak), social login.
   - Revocation: must an admin or logout end access at once?
   - Verifiers: one backend, or several services that each check identity.
3. Pick the first matching row below. Cite the row in the plan.
4. Record it under **Technical decisions** with `Gate: yes`. Auth is always Operator Gate.

## Scenarios

| Scenario | Choose | Why not the others |
|---|---|---|
| Server-rendered or same-origin web app, one backend | Server-side session, cookie `HttpOnly; Secure; SameSite=Lax` | Revocation and logout are one delete. JWT adds nothing here. |
| Users already live in a corporate IdP or social login | OIDC authorization code + PKCE against that IdP, then a local session (backend-for-frontend) | Do not store passwords. Do not hand IdP tokens to the browser. |
| SPA on another domain calling its own API | Backend-for-frontend with a session cookie; else OIDC code + PKCE with short access tokens in memory | Tokens in `localStorage` are readable by any XSS. |
| Mobile or native app | OIDC code + PKCE, short access token, rotating refresh token in OS secure storage | Sessions do not fit non-browser clients. |
| Third-party apps act on a user's behalf | OAuth 2 authorization server from an existing product (IdP, Keycloak) | Never hand-roll an authorization server. |
| Service to service | OAuth client credentials or mTLS; short-lived JWT access tokens are fine | No user, no session. |
| Many services or edge nodes verify identity without a call back | Short-lived JWT access tokens (minutes) issued by the IdP, plus refresh | This is the one place JWT is the answer. |
| Developers call a public API from scripts | Scoped API keys, stored hashed, rotatable | OAuth is overhead when there is no user consent step. |

## Pitfalls

- JWT as a session replacement for one web app: logout and "revoke user" do not work until expiry; a denylist turns it back into a session store.
- OAuth 2 alone is authorization, not login. Login is OIDC on top of it.
- Cookie sessions need CSRF protection: `SameSite` plus a CSRF token on state-changing forms.
- JWT verification: pin the algorithm, reject `none`, never share one HS256 secret across services.
- Do not mix strategies by accident (session for pages, a hand-made token for the same app's API). One app, one mechanism, unless a scenario row above requires two.
