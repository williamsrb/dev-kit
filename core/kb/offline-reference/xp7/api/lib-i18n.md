<!-- src:https://developer.enonic.com/docs/platform/7.x/api/lib-i18n generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC api/lib-i18n.md

# I18N API

This API provides functionality for localization of text phrases.

## Usage

> **Note:** This API uses standard framework functionality. Please read the [framework localization docs](/docs/platform/7.x/framework/i18n) before using this API.

```groovy
dependencies {
  include "com.enonic.xp:lib-i18n:${xpVersion}"
}
```

Add the `import` statement to your controller:

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

| Name | Kind | Details |
| --- | --- | --- |
| locale | string \| string[] | A string-representation of a locale, or an array of locales in preferred order. Pass in an empty array for default locale. |
| bundles | string[] | Required list of bundle names. Bundle names are specified as paths, relative to the `src/main/resources/` folder. |

Returns

An object with all phrases

Example

Getting the current context

```typescript
const phrasesEs = i18nLib.getPhrases('es', ['i18n/phrases'])
```

Sample response

```typescript
{
  action.preview:"Vista Previa",
  notify.process.failed:"Error al procesar: {0}."
}
```

### getSupportedLocales

Returns the list of supported locale codes for the specified bundles.

Parameters

| Name | Kind | Details |
| --- | --- | --- |
| bundles | string[] | Required list of bundle names. Bundle names are specified as paths, relative to the `src/main/resources` folder. |

Returns

An array with all locales

Example

Getting the current context

```typescript
const locales = i18nLib.getSupportedLocales(['i18n/phrases'])
```

Sample response

```typescript
["es"]
```

### localize

Localizes a phrase by searching through the list of passed in locales in the given order, to find a translation for the phrase-key. If no translation is found, the default phrase will be used. Some phrases will have placeholders (`{0}`, `{1}` etc) for values that may be inserted into the phrase. These must be provided in the function call for those phrases.

Parameters

| Name | Kind | Details |
| --- | --- | --- |
| key | string | The phrase key |
| locale | string \| string[] | A string-representation of a locale, or an array of locales in preferred order. If the locale is not set, the site language is used. |
| values | string[] | Optional placeholder values |
| bundles | string[] | Optional list of bundle names |
| application | string | Application key where to find resource bundles. Defaults to current application |

Returns

The localized string

Example

Localize a message with a placeholder.

```typescript
import {localize} from '/lib/xp/i18n';

const message2 = localize({
    key: 'notify.process.failed',
    locale: 'es',
    values: ["StaleConnectionException"]
});
```

Sample response

```typescript
Error al procesar: "StaleConnectionException".
```
