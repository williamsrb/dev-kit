<!-- src:https://developer.enonic.com/docs/code/stable/web/id-providers generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/web/id-providers.md

# Building ID Providers

The XP framework offers a solution for pluggable authentication called ID providers

## Introduction

As part of the XP’s Identity and Access Management (IAM) system, services may be loosely associated with an ID provider via vhost configuration.

The ID provider is responsible for providing user authentication, independent of the source identity system.

ID providers are wired tightly into the [common HTTP request pipeline](docs/code/stable/web.md#common_request_pipeline). They participate both in pipeline execution steps, and through the contextually mounted ID provider API.

This section describes how to implement an ID provider application.

> **Tip:** Two ready-made ID providers are published on [Enonic Market](https://market.enonic.com) and cover most common needs without writing code: **OIDC ID Provider** — for any OpenID Connect-compliant identity system (Auth0, Okta, Microsoft Entra, Keycloak, etc.) — and **Simple ID Provider** — a turn-key local identity store with a built-in login form. Reach for those first; implement a custom ID provider only when neither fits.

## Endpoints and mounting

Unlike the four [services](docs/code/stable/web.md), an ID provider has no URL prefix of its own. Instead, every ID provider is reachable through a single fixed mountpoint:

`/_/idprovider/`

This mountpoint is **contextual** — the same `/_/idprovider/` space resolves within the site, webapp, and admin services (the flat `/api` endpoint has no `/_/` space), so an ID provider can serve its login flow and custom requests regardless of which service the user is interacting with. `` is the name given to the ID provider when it is configured — it is unrelated to the key of the application that implements it.

Three behaviours are reachable under the mountpoint, each invoking the matching [implementation](#idproviderts) function:

> **Note:** This diagram covers the ID provider’s **endpoint** surfaces. Its two **pipeline hooks** — `autoLogin` (the autologin filter) and `handle401` — are triggered by the request pipeline rather than the endpoint, and appear in the [common pipeline](docs/code/stable/web.md#common_request_pipeline) diagram.

/_/idprovider/<name>/login

Invokes `login` — a deterministic login endpoint, available for every provider.

/_/idprovider/<name>/logout

Invokes `logout`.

/_/idprovider/<name>

The base endpoint dispatches to the provider’s `GET`/`POST`/… HTTP functions.

Rather than hardcoding these paths, generate them with the portal library helpers — [loginUrl()](docs/code/stable/libraries/lib-portal.md#_loginurl), [logoutUrl()](docs/code/stable/libraries/lib-portal.md#_logouturl) and [idProviderUrl()](docs/code/stable/libraries/lib-portal.md#_idproviderurl) — which resolve the correct contextual URL for the current request.

> **Note:** The endpoint is **mounted** everywhere, but an ID provider only **activates** for a request when it is bound to the request’s virtual host. The vhost mapping declares which ID provider(s) apply, and the one marked `default` is the provider whose `autoLogin` filter runs. See the [vhost configuration](https://developer.enonic.com/docs/platform/xp8/config/vhosts) for the binding rules.

## Descriptor

An IDprovider application requires a descriptor file. The descriptor should be placed in your project as `src/main/resources/idprovider/idprovider.yaml`.

Sample idprovider.yaml

```yaml
kind: "IdProvider"
mode: "LOCAL" (1)
form:         (2)
- type: "TextLine"
  name: "title"
  label: "Title"
  default: "User Login"
  occurrences:
    min: 0
    max: 1
```

| ****1** | **mode** specifies how users and groups are process and stored in XP. Allowed values are:        **LOCAL** - Users and groups are fully managed by the IDprovider (i.e. no integrations or external ID systems).      **EXTERNAL** - Users and groups exist in a remote system. The IDprovider acts as a "broker" between XP and the remote Identity system.      **MIXED** - Users exist in a remote system, but the groups are created and managed locally in XP. |
| --- | --- |
| ****2** | **form** defines config options that can be defined from the UI when setting up ID providers. Forms are based on the [schema system](https://developer.enonic.com/docs/cms/xp8/schemas)   @@BLOCK3@@ |

## idprovider.ts

Add an ID provider implementation at `src/main/resources/idprovider/idprovider.ts`. An application may only implement a single ID provider.

To implement your ID provider, export one or more of the following functions:

> **Note:** To serve static assets (CSS, JS, images — e.g. for a login page), use the [`lib-static`](https://developer.enonic.com/docs/lib-static) library, **not** `lib-asset`. Like admin extensions, an ID provider runs in a context where `lib-asset` does not fit; `lib-static` (typically paired with `lib-router`) is designed for serving static files from here.

### handle401

Perhaps the most common use of ID providers is handling 401 errors (Unauthorized). When a user attempts to access a resource or service that requires authentication, the pipeline will produce an HTTP 401 response. The IDprovider may intercept the response before this is sent to the client (browser) and perform an action that enables the user to authenticate, hopefully giving access to the resource.

### login

Clients may request a login directly through a pre-defined endpoint, available for all ID providers. This provides a deterministic endpoint for accessing the login page of any ID provider.

The URL to the endpoint can be generated using the [loginUrl() function in the portal library](docs/code/stable/libraries/lib-portal.md#_loginurl)

> **Note:** If the "login" endpoint is called with a "redirect" parameter, a validation of the origin is performed. The result of this validation is then passed to the ID Provider as a request property "validTicket".

### logout

Clients may request a logout directly through a pre-defined endpoint, available for all ID providers. This provides a deterministic endpoint for logging out of any ID provider.

The URL for this endpoint can be generated using the [logoutUrl() function in the portal library](docs/code/stable/libraries/lib-portal.md#_logouturl)

> **Note:** If the "logout" endpoint is called with a "redirect" parameter, a validation of the origin is performed. The result of this validation is then passed to the ID Provider as a request property "validTicket".

### autoLogin

An ID provider may optionally include an AutoLogin filter. The purpose of this filter is to automatically sign in users, before they may access other parts of the execution pipeline. This effectively blocks all unauthorised access attempts for the protected service.

If no user already exists in the context, the autoLogin filter is executed early in the request pipeline.

> **Note:** `autoLogin` works only for identity providers that are configured as `default` in the virtual host mapping. Visit the [vhost configuration](https://developer.enonic.com/docs/platform/xp8/config/vhosts) section for more details.

### GET/POST etc

Additionally, an ID provider may also act as a regular [HTTP function](docs/code/stable/web/request-response.md) — supporting any interaction as desired. Communication with the implementation is handled via the ID provider endpoint.

The URL to this endpoint can be generated using the [idProviderUrl() function in the portal library](docs/code/stable/libraries/lib-portal.md#_idproviderurl)

## Sample

The code below demonstrates how an ID provider may be implemented

Sample idprovider.js

```javascript
var authLib = require('/lib/xp/auth');

// Filter every request
exports.autoLogin = function (req) {
    log.info('Invoked only unless user is already authenticated');
};

// Override error handler when authentication is required
exports.handle401 = function (req) {
    var body = generateLoginPage();
    return {
        status: 401,
        contentType: 'text/html',
        body: body
    };
};

// Triggered when user visits the ID providers login endpoint
exports.login = function (req) {

    var redirectUrl = req.validTicket ? req.params.redirect : undefined;

    var body = generateLoginPage(redirectUrl);
    return {
        contentType: 'text/html',
        body: body
    };
};

// Triggered when user visits the ID providers logout endpoint
exports.logout = function (req) {

    // Sign user out of XP
    authLib.logout();

    var redirectUrl = req.validTicket ? req.params.redirect : undefined;

    if (redirectUrl) {
        return {
            redirect: redirectUrl
        };
    } else {
        var body = generateLoginPage();
        return {
            contentType: 'text/html',
            body: body
        };
    }
};
```
