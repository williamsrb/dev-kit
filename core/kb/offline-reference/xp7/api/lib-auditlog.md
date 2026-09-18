<!-- src:https://developer.enonic.com/docs/platform/7.x/api/lib-auditlog generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC api/lib-auditlog.md

# Auditlog API

XP 7.2.0

This API provides functions for audit log management.

## Usage

```groovy
dependencies {
  include "com.enonic.xp:lib-auditlog:${xpVersion}"
}
```

Add the `import` statement to your controller:

```typescript
import auditlogLib from '/lib/xp/auditlog';
```

## Functions

### find

This function searches for entries in the audit log.

Parameters

An object with the following keys and their values:

| Name | Type | Attributes | Default | Description |
| --- | --- | --- | --- | --- |
| start | number | <optional> | 0 | Start index (used for paging) |
| count | number | <optional> | 10 | Number of entries to fetch |
| ids | array | <optional> |  | Filter by entry ids |
| from | string | <optional> |  | Filter by entries earlier than `from` |
| to | string | <optional> |  | Filter by entries later than `to` |
| type | string | <optional> |  | Filter by type |
| source | string | <optional> |  | Filter by source |
| users | array | <optional> |  | Filter by user keys |
| objects | array | <optional> |  | Filter by object URIs |

> **Note:** All parameters are optional, but you should specify at least one of them. If no parameters are supplied, you will get an empty result.

Returns

**Object** : An array of audit log entries.

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

| Name | Kind | Details |
| --- | --- | --- |
| id | string | Id of the audit log entry. |

Returns

**Object** : Audit log entry as JSON.

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

Parameters

| Name | Type | Attributes | Description |
| --- | --- | --- | --- |
| type | string |  | Type of log entry. |
| time | string | <optional> | Log entry timestamp. Defaults to now. |
| source | string | <optional> | Log entry source. Defaults to the application ID. |
| user | string | <optional> | Log entry user. Defaults to the user of current context. |
| objects | string[] | <optional> | URIs to objects that relate to this log entry. Defaults to empty array. |
| data | object | <optional> | Custom extra data for the this log entry. Defaults to empty object. |

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
