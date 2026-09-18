<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-common generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-common.md

# Common library

This API provides helper functions.

## Usage

```groovy
dependencies {
  include xplibs.common
}
```

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

`sanitize()` takes a single positional argument: `text` (string) — the text to sanitize.

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
