---
id: how-to-test-enonic-xp-apps-jest
when_skills: [test-xp-apps]
read: section
prose: caveman-lite
---

# Jest + Mock XP

Faster, no XP server needed. Supports TypeScript natively via `ts-jest`.

### @enonic/mock-xp (optional, for richer XP API mocking)

```bash
npm install --save-dev @enonic/mock-xp
```

Provides mock classes for XP APIs:

| Class | Mocks |
|-------|-------|
| `Server` | Creates mock repositories, projects, and contexts |
| `App` | Represents an XP application with a `key` |
| `LibContent` | `/lib/xp/content` — `create()`, `createMedia()`, `get()` |
| `LibPortal` | `/lib/xp/portal` — `getContent()`, `imageUrl()`, `assetUrl()` |
| `LibNode` | `/lib/xp/node` — `connect()`, CRUD on nodes |

**Note:** `@enonic/mock-xp` does NOT mock `lib-auth`, `lib-i18n`, `lib-mail`, `lib-repo`, or others — those still require manual `jest.mock()`.

Setup pattern:

```typescript
import { jest } from '@jest/globals';
import { App, LibContent, LibPortal, Server } from '@enonic/mock-xp';

const server = new Server({ loglevel: 'debug' })
    .createProject({ projectName: 'myproject' })
    .setContext({ projectName: 'myproject' });

const app = new App({ key: 'com.example.dfs' });
const libContent = new LibContent({ server });
const libPortal = new LibPortal({ app, server });

jest.mock('/lib/xp/portal', () => ({
    assetUrl: jest.fn((params: unknown) => libPortal.assetUrl(params)),
    getContent: jest.fn(() => libPortal.getContent()),
    imageUrl: jest.fn((params: unknown) => libPortal.imageUrl(params)),
}), { virtual: true });
```

See [Testing with Jest and Mock XP](https://developer.enonic.com/docs/testing-with-jest-and-mock-xp) for full documentation.

---

## Jest Configuration (current project)

The project uses `xp/jest.config.ts` with two projects: **CLIENT** (jsdom) and **SERVER** (node). Both use `ts-jest` for TypeScript transformation.

Key config details:
- `passWithNoTests: true` — no failure on empty test suites
- `coverageProvider: 'v8'` — for correct line numbers under jsdom
- Test file patterns: `*.{spec,test}.{ts,tsx}`

## Server-Side Tests (Jest)

### Location

`xp/src/jest/server/` — mirror the `src/main/resources/` structure.

Example: to test `src/main/resources/lib/myModule/helper.ts`, create `src/jest/server/lib/myModule/helper.test.ts`.

### Setup

The `setupFile.ts` provides global mocks:

```typescript
globalThis.log = {
    debug: console.debug,
    info: console.info,
    error: console.error,
    warning: console.warn
}
```

The `global.d.ts` defines `App` and `Log` types for the test environment.

### Path Aliases (tsconfig)

The server tsconfig extends `xp/src/main/resources/tsconfig.json` and overrides `paths`.
TypeScript `paths` are **fully replaced** (not merged) when overridden, so the server tsconfig must include ALL needed mappings:

```json
{
  "paths": {
    "/lib/enonic/asset": ["../../../node_modules/@enonic-types/lib-asset"],
    "/lib/enonic/react4xp": ["../../../node_modules/@enonic-types/lib-react4xp"],
    "/lib/xp/*": ["../../../node_modules/@enonic-types/lib-*"],
    "/*": ["../../main/resources/*"]
  }
}
```

### Module Resolution (Jest vs TypeScript)

Jest uses `moduleNameMapper` (in `jest.config.ts`) for runtime module resolution, **not** TypeScript `paths`. There are two categories of absolute imports:

| Import pattern | Resolves to | Jest strategy |
|---|---|---|
| `/react4xp/*`, `/lib/app/*`, `/site/*` | Real files in `src/main/resources/` | `moduleNameMapper` catch-all: `'^/(?!lib/xp/\|lib/enonic/)(.*)$'` |
| `/lib/xp/*`, `/lib/enonic/*` | Type-only packages (`@enonic-types/*`) — no JS | `jest.mock('...', () => (...), { virtual: true })` |

**Important:** XP runtime libraries (`/lib/xp/*`, `/lib/enonic/*`) are excluded from the `moduleNameMapper` catch-all via negative lookahead. They **must** be mocked with `{ virtual: true }` because they have no JavaScript entry point.

### Example: Testing a Processor

```typescript
// xp/src/jest/server/react4xp/components/parts/hero/processor.test.ts

// ALWAYS import Jest globals explicitly — @types/jest is not installed
import { jest, describe, it, expect, beforeEach } from '@jest/globals';

// XP runtime libraries — type-only, MUST use { virtual: true }
jest.mock('/lib/enonic/react4xp', () => ({
    processHtml: jest.fn(({ value }: { value: string }) => ({ processedHtml: value })),
}), { virtual: true });

// Project-internal modules — resolve via moduleNameMapper (no { virtual: true })
jest.mock('/lib/app/extension/portal', () => ({
    myImageUrl: jest.fn(() => ({ link: 'https://example.com/image.jpg', alt: '' })),
    processTextArea: jest.fn((text: string) => text),
    myPageUrl: jest.fn((nodeId: string) => `https://example.com/page/${nodeId}`),
}));

import { heroPartProcessor } from '/react4xp/components/parts/hero/processor';

describe('heroPartProcessor', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('should resolve image URL and process intro text', () => {
        const component = {
            type: 'part' as const,
            path: '/main/0',
            descriptor: 'com.example.dfs:hero',
            config: {
                title: 'Welcome',
                intro: 'Hello world',
                image: 'image-ref-123',
                variation: 'large',
            },
        };

        const result = heroPartProcessor({
            component,
            dataFetcher: {} as never,
        } as Parameters<typeof heroPartProcessor>[0]);

        const props = result.componentProps as Record<string, unknown>;
        expect(props.title).toBe('Welcome');
    });
});
```

### Mocking XP Libraries (manual jest.mock)

XP runtime libraries are type-only packages. Always use `{ virtual: true }`. Remember to import `jest` from `@jest/globals`:

```typescript
import { jest } from '@jest/globals';

// Mock lib-portal — { virtual: true } required
jest.mock('/lib/xp/portal', () => ({
    pageUrl: jest.fn(({ id }: { id: string }) => `/page/${id}`),
    imageUrl: jest.fn(({ id }: { id: string }) => `/image/${id}`),
}), { virtual: true });

// Mock lib-content — { virtual: true } required
jest.mock('/lib/xp/content', () => ({
    get: jest.fn(({ key }: { key: string }) => ({ _id: key, displayName: 'Test' })),
    exists: jest.fn(() => true),
}), { virtual: true });
```

## Client-Side Tests (React Components)

### Location

`xp/src/jest/client/` — organize by component type.

### Import Paths

Always import from the copied prototype location:

```typescript
// CORRECT — imports from copied prototype inside xp/
import { Header } from '../../../../main/resources/react4xp/components/prototype/Header/index';

// WRONG — breaks in Docker/CI
import { Header } from '../../../../../../prototype/src/components/Header/index';
```

### React 19 + act() Setup

React 19 requires this at the top of every client test file:

```typescript
import React from 'react';
import { createRoot, Root } from 'react-dom/client';
import { act } from 'react';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
```

Without this flag, React 19 throws: `The current testing environment is not configured to support act(...)`.

### SCSS / CSS Handling

Copied prototype files have rewritten SCSS imports. The jest config stubs these:

```typescript
moduleNameMapper: {
    '/assets/(.*)': '<rootDir>/src/main/resources/assets/$1',
}
```

### Path Aliases (tsconfig)

```json
{
  "paths": {
    "/assets/*": ["../../main/resources/assets/*"]
  }
}
```

## Running Tests

```bash
# All tests (also triggered by ./gradlew test via npmTest task)
npm test

# Specific projects
npx jest --selectProjects CLIENT
npx jest --selectProjects SERVER

# Single test file
npx jest --selectProjects SERVER path/to/test.test.ts
```

Do **not** use `npx jest --projects <path>` — it overrides project isolation.

