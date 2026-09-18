<!-- src:https://developer.enonic.com/learn/react4xp-tutorial/5.x/appendix/upgrade generated:2026-07-30T04:16:10Z format:llm-dense react4xp-5.x -->
#DOC learn/react4xp-tutorial/5.x/appendix/upgrade.md

# Upgrading to v5

## Important changes

### Import restrictions

It turns out importing from React4xp entries causes "intermittent" SSR errors. "When" it happens depends upon which page is visited first, after starting the React4xp application.

"Why" it happens is slightly complex. Entries and dependencies are transpiled with different optimizations. When an entry is imported somewhere: the imported entry’s source code is duplicated into multiple bundles. Each bundle pushes it’s "version" of the code onto the global chunk object using a chunk id. All duplications use the same chunk id, but have different optimizations. When the original entry "wins", everything works as expected, but when a imported chunk with wrong optimization wins, the error occurs.

To avoid this we have introduced import restrictions on the site folder and entryDirs. Trying to import from any restricted path, will cause a compilation error with a helpful error message.

### Entry Extension Whitelist

We have also introduced a configurable `entryExtensionWhitelist`.

This is a list of file extensions that are allowed to be imported from under site and entryDirs. There is a default list, but you can override it in react4xp.config.js.

### @enonic/react-components

If you are using @enonic/react-components, you might run into some compiletime resolve issues. The new version of this package fixes that.

## Upgrade steps

Upgrade @enonic/react4xp in package.json, and also the lib-react4xp in build.gradle.

### package.json

```console
npm install --save-dev @enonic/react4xp@^5
```

### build.gradle

build.gradle

```gradle
dependencies {
    include "com.enonic.lib:lib-react4xp:5.x.x"
}
```

### react4xp.config.js

react4xp.config.js

```gradle
entryExtensionWhitelist: [
    'css',
    'd', (1)
    'png',
    'sass',
    'scss',
    'styl'
],
```

| ****1** | TypeScript declaration files |
| --- | --- |

### Build

Try to compile and see if you get the compilation error mentioned in the what section at the top.

### Move code

If you get a compilation error, move any imported entry code outside site and entryDirs. For example into the src/main/resources/react4xp folder.

## Side notes

### @enonic/react-components

```console
npm install --save-dev @enonic/react-components@^4
```
