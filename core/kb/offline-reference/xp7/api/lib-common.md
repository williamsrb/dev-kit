<!-- src:https://developer.enonic.com/docs/platform/7.x/api/lib-common generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC api/lib-common.md

# Common API

This API provides helper functions.

## Usage

```groovy
dependencies {
  include "com.enonic.xp:lib-common:${xpVersion}"
}
```

Add the `import` statement to your controller:

```typescript
import commonLib from '/lib/xp/common';
```

## Functions

### sanitize

Transforms a text string so that it can be safely used in cases where the range of accepted characters is restricted.

Some usage examples for sanitizing are: content or node name, principal name, URL or a file system path etc.

The following changes will be applied to the input text:

- Convert characters to lowercase (according to the rules of the default locale)

- Replace punctuation symbols and blank spaces with the hyphen character ('-')

- Remove some unsafe and invisible Unicode characters

- Strip duplicated hyphen characters

- Remove diacritic characters

- Map letters to the English alphabet (ASCII encoding)

Parameters

| Name | Kind | Details |
| --- | --- | --- |
| text | string | Text to sanitize |

Returns

**string** : The sanitized text

Example

Sanitize string

```typescript
import {sanitize} from '/lib/xp/common';

const sanitizedText = sanitize("Piña CØLADÆ <script>alert('hi!');</script>");
```

Sample response

```typescript
"pina-coladae-script-alerthi-script"
```
