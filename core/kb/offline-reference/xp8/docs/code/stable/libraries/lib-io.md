<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-io generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-io.md

# IO library

IO related functions.

## Usage

```groovy
dependencies {
  include xplibs.io
}
```

```typescript
import ioLib from '/lib/xp/io';
```

## Functions

### getMimeType

Returns the mime-type from a file name or extension.

Parameters

Takes a single `name` string — the file name or extension to look up.

Returns

**string** : The mime-type for the given name or extension.

Example

```typescript
import {getMimeType} from '/lib/xp/io';

// Returns mime-type for a file name.
const type = getMimeType('myfile.txt');
log.info('Mime type is %s', type);
```

### getResource

Looks up a resource on the classpath.

Parameters

Takes a single `key` argument — a string path or a [ResourceKey](docs/code/stable/fundamentals/types.md#resource-key) identifying the resource.

Returns

**object** : ([`Resource`](docs/code/stable/fundamentals/types.md#resource)) A resource handle exposing `exists()`, `getSize()`, `getTimestamp()`, and `getStream()`.

Examples

```typescript
import {getResource} from '/lib/xp/io';

// Returns a file by name.
const res1 = getResource('/lib/xp/examples/io/sample.txt');
const exists = res1.exists();
const size = res1.getSize();
const timestamp = res1.getTimestamp();
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

Returns the size of a stream in bytes.

Parameters

Takes a single `stream` argument — a [ByteSource](docs/code/stable/fundamentals/types.md#byte-source) to measure.

Returns

**number** : Size of the stream in bytes.

Example

```typescript
import {getSize} from '/lib/xp/io';

// Returns the size of a stream.
const size = getSize(stream);
log.info('Stream size is %s bytes', size);
```

### newStream

Creates a new stream from a string.

Parameters

Takes a single `text` string — the text to encode as a UTF-8 byte stream.

Returns

**object** : ([`ByteSource`](docs/code/stable/fundamentals/types.md#byte-source)) A new stream containing the UTF-8 bytes of the input string.

Example

```typescript
import {newStream} from '/lib/xp/io';

// Creates a new stream from a string.
const stream = newStream('Hello World');
```

### processLines

Reads a stream line by line, invoking a callback for each line.

Parameters

Takes two positional arguments: a `stream` ([ByteSource](docs/code/stable/fundamentals/types.md#byte-source)) to read from, and a `func` callback `(line: string) ⇒ void` called once per line.

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

Reads all lines from a stream and returns them as an array.

Parameters

Takes a single `stream` argument — a [ByteSource](docs/code/stable/fundamentals/types.md#byte-source) to read from.

Returns

**string[]** : Lines read from the stream.

Example

```typescript
import {readLines} from '/lib/xp/io';

// Reads lines from stream.
const lines = readLines(stream);
log.info('Num lines: %s', lines.length);
```

### readText

Reads the full text content of a stream.

Parameters

Takes a single `stream` argument — a [ByteSource](docs/code/stable/fundamentals/types.md#byte-source) to read from.

Returns

**string** : Text read from the stream.

Example

```typescript
import {readText} from '/lib/xp/io';

// Reads text from stream.
const text = readText(stream);
log.info('Text: %s', text);
```
