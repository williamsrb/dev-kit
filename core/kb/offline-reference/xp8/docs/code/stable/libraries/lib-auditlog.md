<!-- src:https://developer.enonic.com/docs/code/stable/libraries/lib-auditlog generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries/lib-auditlog.md

# Auditlog library

This API provides functions for audit log management.

## Usage

```groovy
dependencies {
  include xplibs.auditlog
}
```

```typescript
import auditlogLib from '/lib/xp/auditlog';
```

## Functions

### find

This function searches for entries in the audit log.

Parameters

`find()` takes a single `params` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| start | number | **Optional.** Start index (used for paging). Defaults to `0`. |
| count | number | **Optional.** Number of entries to fetch. Defaults to `10`. |
| ids | array | **Optional.** Filter by entry ids. |
| from | string | **Optional.** Filter by entries on or after `from`. |
| to | string | **Optional.** Filter by entries on or before `to`. |
| type | string | **Optional.** Filter by type. |
| source | string | **Optional.** Filter by source. |
| users | array | **Optional.** Filter by user keys. |
| objects | array | **Optional.** Filter by object URIs. |

> **Note:** All parameters are optional, but you should specify at least one of them. If no parameters are supplied, you will get an empty result.

Returns

**Object** : Audit log search results, with `total`, `count`, and an array of `hits`.

Examples

```typescript
import {find} from '/lib/xp/auditlog';

// Find first audit log by ids
const result = find({
    start: 0,
    count: 1,
    ids: [
        '90b976f7-55ab-48ef-acb8-e7c6f0744442',
        '00c4e51d-ee39-4f0e-9075-5af00b5830c4'
    ]
});
```

### get

This function fetches an audit log entry.

Parameters

`get()` takes a single `params` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| id | string | Id of the audit log entry. |

Returns

**Object** : Audit log entry as JSON, or `null` if no audit log exists with the given id.

Examples

```typescript
import {get as getAuditEntry} from '/lib/xp/auditlog';

// Gets an audit log by id.
const log = getAuditEntry({
    id: '90b976f7-55ab-48ef-acb8-e7c6f0744442'
});
```

### log

This function creates a single audit log entry.

`log()` takes a single `params` object with these properties:

| Name | Type | Description |
| --- | --- | --- |
| type | string | Type of log entry. |
| time | string | **Optional.** Log entry timestamp. Defaults to now. |
| source | string | **Optional.** Log entry source. Defaults to the application ID. |
| user | string | **Optional.** Log entry user. Defaults to the user of current context. |
| objects | string[] | **Optional.** URIs to objects that relate to this log entry. Defaults to empty array. |
| data | object | **Optional.** Custom extra data for this log entry. Defaults to empty object. |

Returns

**Object** : Created audit log entry as JSON.

Examples

```typescript
import {log as logAuditEntry} from '/lib/xp/auditlog';

// Creates an audit log.
const log1 = logAuditEntry({
    type: 'testlog'
});
```

```typescript
// Creates an audit log with more custom parameters.
const log2 = logAuditEntry({
    type: 'testlog',
    time: '2019-08-12T08:44:02.767Z',
    source: 'unittests',
    user: 'user:system:anonymous',
    objects: [
        'some:resource:uri'
    ],
    data: {
        custom: 'string',
        somevalue: 2.5
    }
});
```
