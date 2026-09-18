<!-- src:https://developer.enonic.com/docs/platform/7.x/framework/globals generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC framework/globals.md

# Global objects and functions

The following global functions and objects are available in the Enonic XP framework.

## App

The globally available `app` object holds information about the contextual app. It has the following properties:

app.name

The name of the application.

app.version

Version of the application.

app.config

Values from the application’s configuration file. This can be set using `$XP_HOME/config/.cfg`. Every time the configuration is changed the app is restarted.

Examples:

```javascript
// Get application name
var name = app.name;  // com.enonic.app.superhero

// Get application version
var version = app.version;  // 1.2.0

// Get some config from the <app.name>.cfg file
var myKey = app.config.secretkey; // Reads the string stored in the "secretkey" property
```

## Log

This globally available `log` object holds the logging methods. It’s one method for each log level and takes the same number of parameters.

```javascript
  log.debug(message, [args]) (1) (2)
```

| ****1** | **string message** Message to log as a debug-level message. |
| --- | --- |
| ****2** | **array args** Optional arguments used in message format. When the last argument is an exception/error instance, its stack trace will be logged. |

```javascript
  log.info(message, [args]) (1) (2)
```

| ****1** | **string message** Message to log as a info-level message. |
| --- | --- |
| ****2** | **array args** Optional arguments used in message format. When the last argument is an exception/error instance, its stack trace will be logged. |

```javascript
  log.warning(message, [args]) (1) (2)
```

| ****1** | **string message** Message to log as a warning-level message. |
| --- | --- |
| ****2** | **array args** Optional arguments used in message format. When the last argument is an exception/error instance, its stack trace will be logged. |

```javascript
  log.error(message, [args]) (1) (2)
```

| ****1** | **string message** Message to log as a error-level message. |
| --- | --- |
| ****2** | **array args** Optional arguments used in message format. When the last argument is an exception/error instance, its stack trace will be logged. |

Examples:

```javascript
// Log a simple message
log.debug('Hello World');

// Log a formatting message
log.info('Hello %s', 'World');

// Log a formatting message
log.warning('%s %s', 'Hello', 'World');

// Log using the built-in JSON converter
log.error('My JSON %s', object );

// Log an exception with stack trace
try {
  thisWillFail();
} catch (e) {
  log.error('An error occurred', e);
}

// Log a formatting message with exception stack trace
try {
  bean.run();
} catch (e) {
  log.error('Error in %s', 'myFunction', e);
}
```

## Resolve()

This globally available function resolves a fully qualified path to a local resource based on the current location. It does not check if a resource exists at the specified path. This function supports both relative (with dot-references) and absolute paths.

```javascript
  resolve(path) (1) (2)
```

| ****1** | **string path** Path to resolve using current location. |
| --- | --- |
| ****2** | **returns** the fully qualified resource path of the location. |

Examples:

```javascript
// Absolute path
var path1 = resolve('/views/myview.html');

// Relative path - in this case, the resource must be in the same folder
var path2 = resolve('myview.html');

// Relative path (same as above)
var path3 = resolve('./myview.html');

// Relative path - resource is one level up
var path4 = resolve('../myview.html');
```

## Require()

This globally available function will load a JavaScript file and return the exports as objects. The function implements parts of the `CommonJS Modules Specification`_.

```javascript
  require(path) (1) (2)
```

| ****1** | **string path** Path to the JavaScript to load. |
| --- | --- |
| ****2** | **returns** The loaded JavaScript object exports. |

Examples:

```javascript
// Absolute path
var lib1 = require('/lib/mylib.js');

// Relative path
var lib2 = require('mylib');

// Relative path (same as above)
var lib3 = require('./mylib.js');

// Relative path
var lib4 = require('../mylib');
```

If the path is relative then it will start looking for the file from the local directory. The file extension .js is not required.

## Exports

The globally available `exports` keyword is used to expose functionality from a given JavaScript file (controllers, libraries etc). This is part of the require.js spec.

Simply use the `exports` keyword to expose functionality from any JavaScript file.

## Double underscore __

The double underscore is available in any server-side JavaScript code and is used for wrapping Java objects in a JavaScript object. Read more about the [Java bridge](/docs/platform/7.x/framework/java-bridge).
