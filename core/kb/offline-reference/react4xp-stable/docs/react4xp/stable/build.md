<!-- src:https://developer.enonic.com/docs/react4xp/stable/build generated:2026-07-30T04:17:59Z format:llm-dense react4xp-7.x -->
#DOC docs/react4xp/stable/build.md

# Build configuration

React4XP build setup and configuration options

## Development build

The development build continuously compiles your changes, and avoids minifying of assets to make debugging easier:

```bash
enonic dev
```

## Production build

A standard build will produce a production optimized version of the applicaiton, including minified assets and source maps. Simply run the following command:

```bash
enonic project build
```

> **Tip:** For more verbose output you may specify -i or --info. However, this requires that you use the full build command: `enonic project gradle build -i`

### Server simulation

You may test how your application will perform on a server by launching your sandbox in production mode. In this mode, assets will be served with optimized cached headers:

```bash
enonic sandbox start --prod
```

## react4xp.config.js

Several aspects of React4xp can be configured with a file *react4xp.config.js*. When using the React4XP starter this should automatically be available in your project.

### entryDirs

react4xp.config.js:

```js
entryDirs: ['myComponents', '../otherComponents']
```

React4xp will look for (ie. sets up webpack to look for) .TSX/.JSX files to turn into [entries](docs/react4xp/stable/entries.md) below the folders listed in `entryDirs` (relative to *src/main/resources/react4xp/*). The starter sets `entryDirs: ['entries']`, so entries are picked up from *src/main/resources/react4xp/entries/*.

Adding comma separated values under `entryDirs` adds *more* folder names/paths where TSX/JSX files will also become entries.

> **Note:** In legacy XP 7 apps, React4xp also scanned *src/main/resources/site/* for entries by default. XP 8 apps no longer have this folder (it was renamed to `cms/`, which is not scanned for entries).

### chunkDirs

By default, React4xp will look for (ie. sets up webpack to look for) resources *imported by* the entries. These are [bundled](https://webpack.js.org/concepts/) into separate assets that React4xp automatically loads at both server- and clientside rendering: [chunks](docs/react4xp/stable/chunks.md), by this pattern:

- If they are react and reactDOM, they are bundled separately into `globals.*.js` (where the * is a content-dependent hash).

- *node_modules/@enonic/react-components/* is bundled into `templates.*.js`

- Other packages under *node_modules* are bundled into `vendors.*.js`

- And everything else that’s *not under a `chunkDir` marked here* is bundled into `react4xp.*.js`

(Of course, non-JS bundles split out by webpack will have different extensions, such as .css)

The idea is to use `chunkDirs` to add a comma-separated list of names/paths of directories (relative to *src/main/resources/react4xp/*) that will be bundled into chunks of their own. The chunk name will be the name of the last directory in the path:

react4xp.config.js:

```js
chunkDirs: ['chunk1', 'bundle2', 'other/stuff']
```

This example adds these folders as chunkDirs, and anything the entries import from below them is bundled separately into:

- *src/main/resources/react4xp/chunk1/* ➔ `chunk1.*.js`

- *src/main/resources/react4xp/bundle2/* ➔ `bundle2.*.js`

- *src/main/resources/react4xp/other/stuff/* ➔ `stuff.*.js`

## webpack.config.react4xp.js

React4xp uses RSpack/Webpack to build. The starter comes with a minimal set of webpack rules built-in, for compiling react components in TSX/JSX files into vanilla JS.

If you need to change/expand this setup, simply place a custom `webpack.config.react4xp.js` in your project folder.

Possible reasons to change the webpack config:

- Most commonly, the built-in webpack setup is pretty minimal, only adding [loaders](https://webpack.js.org/loaders/) for compiling react from TSX/JSX. It’s likely you will need to add loaders of your own, maybe use additional plugins etc

- You may want to adjust other aspects of the compilation rules, or even replace the built-in rules entirely

- The assets that are built during the compilation are the same ones that are run on the server and in the browser. It’s possible you may need adjustments here to account for corner cases - if the problem is missing feature support in the server, perhaps you can polyfill them.

> **Note:** **Config file shape: syntax variation!**

Usually, *webpack.config.js* files tend to have a certain shape, something like:

`module.exports = function(env) {
var config = {
entry: (...)
output: (...)
resolve: (...)
module: {
rules: (...)
}
};

return config;
};
// ...etc, etc`

`webpack.config.react4xp.js` can follow the same shape, but the exported function can also take **a second `config` argument:**

`module.exports = function(env, config) {
// ...
};`

The extra incoming `config` object contains the built-in rules from React4xp. This enables you to both manipulate those rules and/or add your own, or entirely replace them by returning a different object.
