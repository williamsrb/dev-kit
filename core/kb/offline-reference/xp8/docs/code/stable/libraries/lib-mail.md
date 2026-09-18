<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-mail generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-mail.md

# Mail library

This API provides functions that are used for sending emails.

## Usage

```groovy
dependencies {
  include xplibs.mail
}
```

```typescript
import mailLib from '/lib/xp/mail';
```

> **Note:** You also need to configure your smtp-server before you can send out email. For details, see [the configuration page](https://developer.enonic.com/docs/platform/xp8/config/system#mail)

## Functions

### send

Sends an email message using the mail server configured.

The address values can be either a simple email address (e.g. `name@domain.org` ) or an address with a display name. In the latter case the email will be enclosed with angle brackets (e.g. `Some Name `).

The `from` parameter supports the [default *from* email](#getDefaultFromEmail) substitution. If the email address is not specified in angle brackets (e.g., `Some Name <>` or `<>`), the default *from* email address is used. However, an error is thrown if the default *from* email is not set.

The parameters `from`, `to`, `cc`, `bcc` and `replyTo` can be passed as a single string or as an array of strings, if there are multiple addresses to specify.

The content-type of the email can be specified by using the `contentType` parameter. See example below for sending a message with an HTML body.

Parameters

`send()` takes a single `SendMessageParams` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| from | string \| string[] | E-mail address(es) and optionally name(s) of the message sender. |
| to | string \| string[] | E-mail address(es) and optionally name(s) of the message’s recipient(s). |
| subject | string | Subject line of the message. |
| body | string | Text content of the message. |
| cc | string \| string[] | **Optional.** List of carbon copy e-mail address(es). |
| bcc | string \| string[] | **Optional.** List of blind carbon copy e-mail address(es). |
| replyTo | string \| string[] | **Optional.** Alternative e-mail address(es) for replies. |
| contentType | string | **Optional.** Content type of the message body. |
| headers | object | **Optional.** Custom headers in the form of name-value pairs. |
| attachments | [Attachment](#attachment)[] | **Optional.** Attachments to include in the e-mail. |

Returns

**boolean** : `true` if the message was successfully sent, `false` otherwise.

Example

Send a simple HTML e-mail

```typescript
import {send} from '/lib/xp/mail';

const flag1 = send({
    from: 'me@enonic.com',
    to: 'user@somewhere.org',
    subject: 'HTML email test',
    body: '<h1>HTML Email!</h1><p>You can use the contentType parameter for HTML messages.</p>',
    contentType: 'text/html; charset="UTF-8"'
});
```

Send an e-mail with attachments

```typescript
import {send} from '/lib/xp/mail';

const flag2 = send({
    from: 'Sales Department <sales@enonic.com>',
    to: 'user@somewhere.org',
    subject: 'Email Test from Enonic XP',
    cc: 'other@example.org',
    bcc: ['support@enonic.com', 'other@enonic.com'],
    replyTo: 'support@enonic.com',
    body: 'Welcome to Enonic XP!' + '\r\n\r\n' + '- The Dev Team',
    headers: {
        'Disposition-Notification-To': 'me@enonic.com'
    },
    attachments: [
        {
            fileName: 'logo.png',
            mimeType: 'image/png',
            data: stream1,
            headers: {
                'Content-ID': 'logo-img'
            }
        },
        {
            fileName: 'text.txt',
            data: stream2
        }
    ]
});
```

### getDefaultFromEmail

Returns the default *from* email address configured in the [XP mail configuration](https://developer.enonic.com/docs/platform/xp8/config/system#mail).

Returns

**string** : The default *from* email address, or `null` if none is configured.

Example

Get a defaultFromEmail

```typescript
import {getDefaultFromEmail} from '/lib/xp/mail';

const defaultFromEmail = getDefaultFromEmail();
```

## Type Definitions

### Attachment

A single attachment to include in an e-mail.

Properties

| Name | Type | Description |
| --- | --- | --- |
| fileName | string | Attachment file name. |
| data | [ByteSource](docs/code/stable/fundamentals/types.md#byte-source) | Attachment stream. |
| mimeType | string | **Optional.** Attachment content type. If not specified, it is inferred from the filename. |
| headers | object | **Optional.** Attachment headers in the form of name-value pairs. |
