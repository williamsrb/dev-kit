<!-- src:https://developer.enonic.com/learn/react4xp-tutorial/5.x/appendix/chunks generated:2026-07-30T04:16:10Z format:llm-dense react4xp-5.x -->
#DOC learn/react4xp-tutorial/5.x/appendix/chunks.md

# Dependency chunks

## What is a chunk?

A dependency chunk is **a compiled asset that can contain multiple components** that are used at runtime.

Think of it as a **library** of secondary resources that can be used by [entries](learn/react4xp-tutorial/5.x/appendix/entries.md) (or by other chunks).

Dependency chunks are served by React4xp to the client and used there. They may contain JS, or other types of code.

## Importing

Entries and other chunks can import resources from chunks, as long as the necessary webpack rules are added. Compilation rules for regular TSX, JSX, TS, JS and ES6 are included with React4xp. Other rules (loaders etc) you must add yourself - see [lesson 6](learn/react4xp-tutorial/5.x/imports-and-dependency-chunks.md#_adding_webpack_rules).

Entries and chunks - the full picture:

See also: [entries](learn/react4xp-tutorial/5.x/appendix/entries.md) and [jsxPath](learn/react4xp-tutorial/5.x/appendix/jsxpath.md).

## Standard chunks

In the standard React4xp setup, two chunks are likely to appear without any further setup: **globals and vendors**. That is, their names are hashed and will appear as `globals..js` and `vendors..js`.

- Globals usually contains react and react-dom, ensuring that the same react version is used when rendering on the client and server.

- Vendors is the chunk for anything else imported from *node_modules*.

## Defining chunk structure

You can also **define your own dependency chunk structure**. Additional folders (relative to *src/main/resources/react4xp/*) can be defined with `chunkDirs` in *react4xp.config.js*. This will cause all source files under each chunkDir to be compiled into one common dependency chunk (or to be precise: one chunk for each codetype defined by webpack rules, e.g. separate JS and CSS chunks).

- The asset’s name will be the name of the parent folder, with a content hash: ...

- For example, adding `chunkDirs: ['foo/bar']` under *react4xp.config.js*, adding *hey.js* and *baz/ho.js* and importing stuff from *hey* and *ho* in an entry, will create the dependency chunk *bar..js* - which contains both *hey* and *ho*.

## Importing from outside of chunkDirs

What happens if an entry imports something from folders **not marked as chunkDirs**?

- Imported JS (react components etc) from non-entry folders will be **compiled into the entry asset** itself. Try to avoid this, since the entries can become bloated, and code can become repeated if it’s imported into more than entry. The entry assets are also less performance optimized.

- Non-JS imports (CSS etc), are compiled to separate assets under their own name, the same way as entries (but are not given a *jsxPath*, of course).

> **Warning:** Do not import from entries! It causes random SSR errors. Place shared code in separate React components.

## Entries vs chunks

Dependency chunks never contain [entries](learn/react4xp-tutorial/5.x/appendix/entries.md); each entry is an asset file of its own. Consequently, nothing inside a dependency chunk will have a jsxPath.

This is why entries are used as a separate word from react components: all entries are react components, but all react components are not necessarily entries: react components can also be secondary imports from chunks / chunkDirs.

Only entries are runtime-available to React4xp.

## Why? For optimization!

Why use chunks?

They are handy for collecting related secondary resources (that may be frequently used together in one part of a site but not others, for instance - making it possible to minimize the necessary client downloads).

But most importantly, they are **automatically optimized for performance**:

- They are both cached on the server side as well as in the client - preventing repeated generation and minimizing downloads, speeding up the site.

- The hash is updated by content, for effective cache busting.

- Even if the resources in a chunk are used more than once on a page, the chunk is only downloaded once.

**Recommended usage:** chunks are made to be **fire-and-forget**. Define the chunkDir, some webpack rules if necessary, and import it from your entry (or your secondary components inside chunks) - the React4xp build setup and runtime will handle the rest. Dependencies are tracked, so `React4xp.render` (and `.renderPageContributions`) automatically adds extra client-side links to necessary chunks.

Since chunks are most optimized for repeated usage, it’s best to put your heavy components and resources in chunks, and **let the entries stay slim and lightweight**.
