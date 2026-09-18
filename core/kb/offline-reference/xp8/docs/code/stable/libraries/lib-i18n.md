<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-i18n generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-i18n.md

# I18N library

This API provides functionality for localization of text phrases.

## Usage

> **Note:** This API uses standard framework functionality. Please read the [framework localization docs](docs/code/stable/fundamentals/i18n.md) before using this API.

```groovy
dependencies {
  include xplibs.i18n
}
```

```typescript
import i18nLib from '/lib/xp/i18n';
```

Then you need to create files with original phrases and their translations. These files should normally be placed in the `src/main/resources/i18n` folder of your application. There must be a file named `phrases.properties` that contains all the default phrases. Additional files with translations named `phrases_.properties` should contain the same phrases with texts localised to `` language. If a phrase is missing from the locale-specific file, the default file will be used. This is what a couple of such files could look like:

phrases.properties

```properties
action.preview=Preview
notify.process.failed=Processing failed: {0}.
```

phrases_es.properties

```properties
action.preview=Vista Previa
notify.process.failed=Error al procesar: {0}.
```

## Functions

### getPhrases

Returns an object of key/value-pairs for all phrases with the given locales in the specified bundles.

Parameters

`getPhrases()` takes two positional arguments: `locale` (`string | string[]`) — a locale string or array of locales in preferred order (pass an empty array to use the site language); and an optional `bundles` (`string[]`) — bundle names as paths relative to `src/main/resources/`.

Returns

**object** : An object whose keys are the phrase keys and whose values are the localized strings.

Example

Get all phrases for a locale

```typescript
const phrasesEs = i18nLib.getPhrases('es', ['i18n/phrases']);
```

Sample response

```typescript
{
    "action.preview": "Vista Previa",
    "notify.process.failed": "Error al procesar: {0}."
}
```

### getSupportedLocales

Returns the list of supported locale codes for the specified bundles.

Parameters

`getSupportedLocales()` takes one optional positional argument: `bundles` (`string[]`) — bundle names as paths relative to `src/main/resources/`.

Returns

**string[]** : Sorted array of supported locale codes (as language tags).

Example

Get the supported locales for a bundle

```typescript
const locales = i18nLib.getSupportedLocales(['i18n/phrases']);
```

Sample response

```typescript
["es"]
```

### localize

Localizes a phrase by searching through the list of passed-in locales in the given order to find a translation for the phrase key. If no translation is found, the default phrase will be used. Some phrases will have placeholders (`{0}`, `{1}` etc.) for values that may be inserted into the phrase. These must be provided in the function call for those phrases.

`localize()` takes a single `LocalizeParams` object with these properties:

Parameters

| Name | Type | Description |
| --- | --- | --- |
| key | string | The phrase key. |
| locale | string \| string[] | **Optional.** A locale string or array of locales in preferred order. If not set, the site language is used. |
| values | string[] | **Optional.** Placeholder values inserted into the phrase in order (`{0}`, `{1}`, etc.). |
| bundles | string[] | **Optional.** Bundle names as paths relative to `src/main/resources/`. |
| `fallbackMessage` | string | **Optional.** Returned when the phrase is not found. Defaults to `"NOT_TRANSLATED"`. |

Returns

**string** : The localized string, or the fallback message if the phrase is not found.

Example

Localize a message with a placeholder

```typescript
import {localize} from '/lib/xp/i18n';

const message = localize({
    key: 'notify.process.failed',
    locale: 'es',
    values: ['StaleConnectionException']
});
```

Sample response

```typescript
Error al procesar: StaleConnectionException.
```

Localize with a custom fallback

```typescript
import {localize} from '/lib/xp/i18n';

const message = localize({
    key: 'action.preview',
    locale: ['es', 'en'],
    fallbackMessage: '(missing translation)'
});
```
