<!-- src:https://developer.enonic.com/docs/platform/7.x/framework/templating generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC framework/templating.md

# Templating

Templates engines may be used to simplify output generation from controllers.

## Introduction

Enonic XP does ship with a standard templating engine, but supports use of 3rd party engines. In this section we give examples of how you may use templating engines with your controllers.

> **Note:** A range of integrated templating engines are available as [libraries on Enonic Market](https://market.enonic.com/libraries).

## React / JSX

Enonic offers a solution for server-side rendering with JSX React templates. Details are available in a [separate tutorial called React4XP](https://developer.enonic.com/docs/react4xp).

## Thymeleaf

Here we will demonstrate templating using the [Thymeleaf](https://www.thymeleaf.org/documentation.html) templating engine. Thymeleaf is available as an [Enonic library](https://market.enonic.com/vendors/enonic/thymeleaf-lib).

> **Tip:** For a more extensive tutorial using Thymeleaf, visit the [My first site tutorial](https://developer.enonic.com/docs/my-first-site)

Start by including the library in your app:

build.gradle

```gradle
dependencies {
   include 'com.enonic.lib:lib-thymeleaf:<version>'
}
```

> **Note:** Replace <version> with the version of the library you want to use.

Add a template file to your project:

src/main/resources/views/sample-view.html

```html
<!DOCTYPE html>
<html>
  <head>
  </head>
  <body>
    <h1>My first page, with a view!</h1>
    <h2>Hello <span data-th-text="${name}">World</span></h2>
  </body>
</html>
```

Your controller must then be updated to use the template:

Example controller using Thymeleaf

```javascript
var thymeleaf = require('/lib/thymeleaf');

exports.get = function(req) {

  // Resolve the view
  var view = resolve('/view/my-template.html');

  // Define a model
  var model = {
    name: "John Doe"
  };

  // Render a thymeleaf template
  var body = thymeleaf.render(view, model);

  // Return the result
  return {
    body: body,
    contentType: 'text/html'
  };

};
```

Unlike some controller files, templates may reside anywhere within the `src/main/resources` structure of your project.

If the view file is in the same folder as your controller, it can be resolved with only the file name `resolve('my-template.html')`. Otherwise, the full or relative path should be used.
