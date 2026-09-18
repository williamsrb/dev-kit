<!-- src:https://developer.enonic.com/learn/react4xp-tutorial/5.x/appendix/build generated:2026-07-30T04:16:10Z format:llm-dense react4xp-5.x -->
#DOC learn/react4xp-tutorial/5.x/appendix/build.md

# Build configuration

## Build arguments

### Development mode

Use the gradle commandline flag `-Pdev` or `-Pdevelopment` to enable building in development mode.

```bash
enonic project gradle build deploy -Pdev
```

This switches between React4xp **build** modes (not to be confused with XP’s [run modes](https://developer.enonic.com/docs/enonic-cli/stable/dev#start)).

- `production`: assets are compiled more compact (and faster), with source maps

- `development`: assets are compiled for more human-readability, without minification, making errors easier to track down.

Default value is `production`.

### Verbosity

Use the gradle commandline flag -i or --info to enable a more verbose output when compiling React4xp components and globals.

## react4xp.config.js

Several aspects of React4xp can be configured with a file *react4xp.config.js*. When using the React4XP starter this should automatically be available in your project.

### Adding react4xp.config.js

> **Note:** If you’re using the [React4XP starter](https://market.enonic.com/starters/react4xp-starter) or your project is based on it, you may skip this section:

Put *react4xp.config.js* at the root of your XP project. A template can be copied from [here](https://github.com/enonic/enonic-react4xp/blob/master/examples/react4xp.config.js), or from *node_modules/@enonic/react4xp/examples/react4xp.config.js* after installing the React4xp NPM package.

**In order to take effect, it must be handled by gradle during the build:**

- Add this to your *build.gradle*:

```groovy
task react4xp(type: NpmTask, dependsOn: npmInstall) {
  args = [
    'run',
    'build:react4xp' // This script must exist in the package.json file
  ]
  description 'Compile react4xp resources'
  environment = [
    'R4X_APP_NAME': "${appName}",
    'R4X_BUILD_LOG_LEVEL': gradle.startParameter.logLevel.toString(),
    'R4X_DIR_PATH_ABSOLUTE_PROJECT': project.projectDir.toString(),
    'NODE_ENV': project.hasProperty('dev') || project.hasProperty('development') ? 'development' : 'production'
  ]
  group 'react4xp'
  // It also watches package.json and package-lock.json :)
  inputs.dir 'node_modules/@enonic/react4xp'
  inputs.dir 'src/main/resources'
  outputs.dir 'build/resources/main'
}
jar.dependsOn 'react4xp'
```

This will not only make sure *react4xp.config.js* is handled, but also give a full react4xp build setup.

- Add this to your *package.json*:

```json
{
  "scripts": {
    "build:react4xp": "npm explore @enonic/react4xp -- npm run build:react4xp",
  }
}
```

### entryDirs

react4xp.config.js:

```js
entryDirs: ['myComponents', '../otherComponents']
```

By default, React4xp will look for (ie. sets up webpack to look for) .TSX/.JSX files to turn into [entries](learn/react4xp-tutorial/5.x/appendix/entries.md) below *src/main/resources/site/*.

Adding comma separated values under `entryDirs` adds *more* folder names/paths (relative to *src/main/resources/react4xp/*) where TSX/JSX files will also become entries.

### chunkDirs

By default, React4xp will look for (ie. sets up webpack to look for) resources *imported by* the entries. These are [bundled](https://webpack.js.org/concepts/) into separate assets that React4xp automatically loads at both server- and clientside rendering: [chunks](learn/react4xp-tutorial/5.x/appendix/chunks.md), by this pattern:

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

React4xp uses Webpack to build. The starter comes with a minimal set of webpack rules built-in, for compiling react components in TSX/JSX files into vanilla JS.

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

### Webpack caching

To improve the speed of incremental builds, you may also enable webpack caching.

webpack.config.react4xp.js

```javascript
module.exports = function(env, config) {
		if (process.env.NODE_ENV === 'development') {
		config.cache = {
			type: 'filesystem'
		}
	}
  return config;
}
```

Read more [https://webpack.js.org/configuration/cache/](https://webpack.js.org/configuration/cache/)
