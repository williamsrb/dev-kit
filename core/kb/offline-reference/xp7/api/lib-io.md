<!-- src:https://developer.enonic.com/docs/platform/7.x/api/lib-io generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC api/lib-io.md

# IO API

IO related functions.

## Usage

```groovy
dependencies {
  include "com.enonic.xp:lib-io:${xpVersion}"
}
```

Add the `import` statement to your controller:

```typescript
import ioLib from '/lib/xp/io';
```

## Functions

### getMimeType

Returns the mime-type from a name or extension.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| name | string | Name of file or extension |

Returns

**string** : mime-type from a name or extension.

Example

```typescript
import {getMimeType} from '/lib/xp/io';

// Returns mime-type for a file name.
const type = getMimeType('myfile.txt');
log.info('Mime type is %s', type);
```

### getResource

Looks up a resource.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| key | string | Resource key to look up |

Returns

**Resource** : Resource reference.

Examples

```typescript
import {getResource} from '/lib/xp/io';

// Returns a file by name.
const res1 = getResource('/lib/xp/examples/io/sample.txt');
const exists = res1.exists();
const size = res1.getSize();
const stream = res1.getStream();
```

```typescript
import {getResource} from '/lib/xp/io';

// Returns a file by reference.
const res2 = getResource(resolve('./sample.txt'));
if (res2.exists()) {
    log.info('Resource exists');
}
```

### getSize

Returns the size of a stream.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| stream |  | Stream to get size of |

Returns

**number** : Returns the size of a stream.

Example

```typescript
import {getSize} from '/lib/xp/io';

// Returns the size of a stream.
const size = getSize(stream);
log.info('Stream size is %s bytes', size);
```

### newStream

Returns a new stream from a string.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| text | string | String to create a stream of |

Returns

*** : A new stream.

Example

```typescript
import {newStream} from '/lib/xp/io';

// Creates a new stream from a string.
const stream = newStream('Hello World');
```

### processLines

Process lines from a stream.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| stream |  | Stream to read lines from |
| func | function | Callback function to be called for each line |

Example

```typescript
import {processLines} from '/lib/xp/io';

let num = 0;

// Process lines from stream.
processLines(stream, (line) => {
    num++;
    log.info('Line %s: %s', num, line);
});
```

### readLines

Reads lines from a stream.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| stream |  | A stream to read lines from |

Returns

**string[]** : Lines as an array.

Example

```typescript
import {readLines} from '/lib/xp/io';

// Reads lines from stream.
const lines = readLines(stream);
log.info('Num lines: %s', lines.length);
```

### readText

Reads text from a stream.

Parameters

| Name | Type | Description |
| --- | --- | --- |
| stream |  | A stream to read text from |

Returns

**string** : Text read from a stream or a string.

Example

```typescript
import {readText} from '/lib/xp/io';

// Reads text from stream.
const text = readText(stream);
log.info('Text: %s', text);
```
