<!-- src:https://developer.enonic.com/docs/code/stable/libraries generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/code/stable/libraries.md

# Platform libraries

## Introduction

When building Enonic apps you may access a broad set of platform capabilities by requiring these libraries. Each library is pulled into your app as a `build.gradle` dependency and loaded at runtime via `require('/lib/xp/')`.

A library can be loaded two ways — both fully typed once the `@enonic-types` packages are installed (see [TypeScript](docs/code/stable/fundamentals/typescript.md)):

require — CommonJS, the standard form

```typescript
const authLib = require('/lib/xp/auth');
const user = authLib.getUser();
```

ES6 import — also needs a paths mapping in tsconfig.json

```typescript
import { getUser } from '/lib/xp/auth';
const user = getUser();
```

## Headless APIs

Visit the [CMS documentation](https://developer.enonic.com/docs/cms/xp8) for details regarding the content schemas and our headless GraphQL API

## JavaDoc

Java developers or anyone interested in a Platform deep dive may check out our JavaDoc ([zipfile download](https://repo.enonic.com/public/com/enonic/xp/docs/8.0.3/docs-8.0.3-javadoc.zip)).
