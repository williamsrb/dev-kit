---
id: how-to-test-enonic-xp-apps-junit
when_skills: [test-xp-apps]
read: section
prose: caveman-lite
---

# XP Test Framework (JUnit + JavaScript)

Runs in the XP runtime; best for services, controllers, and XP API usage. Requires the `com.enonic.xp:testing` dependency.

### Gradle

```groovy
repositories {
    mavenCentral()
    maven { url 'https://repo.enonic.com/public' }  // required — not on Maven Central
}

dependencies {
    testImplementation "com.enonic.xp:testing:${xpVersion}"
}
```

The artifact version should match your `xpVersion` property (e.g., `7.16.1`).

### Layout

- JS tests: `xp/src/test/resources/` (mirror main layout, e.g. `lib/foo-test.js`)
- Java bootstrap: `xp/src/test/java/` — class extending `ScriptRunnerSupport`, returns path to JS test

### Java Bootstrap

Each JavaScript test file needs a Java class that extends `ScriptRunnerSupport`:

```java
package io.x99.dfs;

import com.enonic.xp.testing.ScriptRunnerSupport;

public class MyModuleTest extends ScriptRunnerSupport {
    @Override
    public String getScriptTestFile() {
        return "/lib/my-module-test.js";  // path under src/test/resources/
    }
}
```

**Important:** The class is `ScriptRunnerSupport`, not `ScriptTestSupport`.

### Example

```javascript
// xp/src/test/resources/lib/example-test.js
var lib = require('./example');
var t = require('/lib/xp/testing');

exports.testHappyPath = function () {
    var result = lib.myFunction({ input: 'value' });
    t.assertJson({ expected: 'output' }, result);
};

exports.testFailurePath = function () {
    var result = lib.myFunction({ input: '' });
    t.assertEquals(null, result);
};
```

Every exported function prefixed with `test` is executed as a separate test. Optional `exports.before` and `exports.after` hooks run around each test function.

### Mocking

`t.mock('/lib/some-module', { fn: function () { return 'fixed'; } })` before requiring the module under test. Reuse the mock object when varying return values:

```javascript
var t = require('/lib/xp/testing');
var mockedFuncs = {};
t.mock('/lib/valueCreator', mockedFuncs);
var service = require('./myModule');  // now uses the mock

exports.testScenario1 = function () {
    mockedFuncs.getValue = function () { return 0; };
    t.mock('/lib/valueCreator', mockedFuncs);  // re-apply
    t.assertEquals("Low", service.get());
};
```

### Run

```bash
./gradlew test   # from xp/
```

**Note:** XP Test Framework tests are written in plain JavaScript (CommonJS `require`), not TypeScript.

---

