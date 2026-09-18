<!-- src:https://developer.enonic.com/docs/platform/7.x/framework/idprovider generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC framework/idprovider.md

# ID Providers

The XP framework offers a solution for pluggable authentication called ID providers

## Introduction

As part of the XP [IAM](/docs/platform/7.x/iam) (Identity and Access management), apps and sites may be loosely associated with an ID provider. The ID provider is responsible for providing user authentication, independent of the source identity system.

ID providers are wired tightly into the [common HTTP execution pipeline](/docs/platform/7.x/runtime/engines#_common_request_pipeline). They participate both in pipeline execution steps, and through the [ID provider service endpoint](/docs/platform/7.x/runtime/engines/idprovider-service)

This section describes how to implement an ID provider application.

## Descriptor

An IDprovider application requires a descriptor file. The descriptor should be placed in your project as `src/main/resources/idprovider/idprovider.xml`.

Sample idprovider.xml

```XML
<id-provider>
  <mode>LOCAL</mode>  (1)
  <form>  (2)
    <input name="title" type="TextLine">
      <label>Title</label>
      <occurrences minimum="0" maximum="1"/>
      <default>User Login</default>
    </input>
  </form>
</id-provider>
```

| ****1** | **mode** specifies how users and groups are process and stored in XP. Allowed values are:        **LOCAL** - Users and groups are fully managed by the IDprovider (i.e. no integrations or external ID systems).      **EXTERNAL** - Users and groups exist in a remote system. The IDprovider acts as a "broker" between XP and the remote Identity system.      **MIXED** - Users exist in a remote system, but the groups are created and managed locally in XP. |
| --- | --- |
| ****2** | **form** defines config options that can be defined from the UI when setting up ID providers. Forms are based on the [schema system](/docs/platform/7.x/cms/schemas)   @@BLOCK0@@ |

## idprovider.js

You must add a specific idprovier JavaScript controller `src/main/resources/idprovider/idprovider.js` to the application. An application may only implement a single ID provider.

To implement your ID provider, export one or more of the following functions:

### handle401

Perhaps the most common use of ID providers is handling 401 errors (Unauthorized). When a user attempts to access a resource or service that requires authentication, the pipeline will produce an HTTP 401 response. The IDprovider may intercept the response before this is sent to the client (browser) and perform an action that enables the user to authenticate, hopefully giving access to the resource.

### login

Clients may request a login directly through a pre-defined endpoint, available for all ID providers. This provides a deterministic endpoint for accessing the login page of any ID provider.

The URL to the endpoint can be generated using the [loginUrl() function in the portal library](/docs/platform/7.x/api/lib-portal#_loginurl)

> **Note:** If the "login" endpoint is called with a "redirect" parameter, a validation of the origin is performed. The result of this validation is then passed to the ID Provider as a request property "validTicket".

### logout

Clients may request a logout directly through a pre-defined endpoint, available for all ID providers. This provides a deterministic endpoint for logging out of any ID provider.

The URL for this endpoint can be generated using the [logoutUrl() function in the portal library](/docs/platform/7.x/api/lib-portal#_logouturl)

> **Note:** If the "logout" endpoint is called with a "redirect" parameter, a validation of the origin is performed. The result of this validation is then passed to the ID Provider as a request property "validTicket".

### autoLogin

An ID provider may optionally include an AutoLogin filter. The purpose of this filter is to automatically sign in users, before they may access other parts of the execution pipeline. This effectively blocks all unauthorised access attempts for the protected service.

If no user already exists in the context, the autoLogin filter is executed early in the HTTP engine’s pipeline.

> **Note:** `autoLogin` works only for identity providers that are configured as `default` in the virtual host mapping. Visit the [vhost configuration](/docs/platform/7.x/deployment/config#vhost) section for more details.

### GET/POST etc

Additinoally, an ID provider may aso act as a regular [controller](/docs/platform/7.x/framework/controllers) - supporting any interaction as desired. Communication with the controller is handled via the [ID provider endpoint](/docs/platform/7.x/runtime/engines/idprovider-service).

The URL to this endpoint can be generated using the [idProviderUrl() function in the portal library](/docs/platform/7.x/api/lib-portal#_idproviderurl)

## Sample

The code below demonstrates how an ID provider may be implemented

Sample idprovider.js

```javascript
var authLib = require('/lib/xp/auth');

// Filter every reqeust
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
