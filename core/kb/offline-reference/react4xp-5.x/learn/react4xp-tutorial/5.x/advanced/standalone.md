<!-- src:https://developer.enonic.com/learn/react4xp-tutorial/5.x/advanced/standalone generated:2026-07-30T04:16:10Z format:llm-dense react4xp-5.x -->
#DOC learn/react4xp-tutorial/5.x/advanced/standalone.md

# React4XP Webapps

> **Tip:** This chapter builds on the source code from [the client side rendering chapter](learn/react4xp-tutorial/5.x/advanced/client-side.md), especially the entry and dependencies, and the assets that they’re compiled into.

If you’ve completed that lesson, nice. But that code is not in focus here and we won’t look at it much - what we’ll build in this chapter is *around* the compiled assets from entries and dependencies, just referring to them.

**What counts here are the general principles and usage patterns**. They should become pretty clear pretty soon.

## Background

### The story so far

Until now in all the previous examples, the XP controllers have still been at the center of the rendering.

Even in the [previous chapter](learn/react4xp-tutorial/5.x/advanced/client-side.md), which demonstrated how to make the frontend react components render with data fetched from an API, the response from the initial request to the page still came from an XP controller.

In that response there was a serverside-rendered initial HTML rendering of the entry, references to dependency and entry assets (in the right order), and a client-side wrapper (fetched from a referred XP service) that handles the react rendering/hydration trigger in the browser. All of this was automatically generated and included from the `React4xp.render` call in the XP controller.

### Going fully headless

But in general, when the React4xp buildtime compiles the react component source files (etc) into assets, what happens is just a **regular webpack** process that generates **regular JS (etc) assets** that can be run in the browser in pretty much any regular way - independent of the React4xp runtime.

**In other words, you can serve the React4xp-compiled assets from anywhere and use them however you want.**

Now that we’ve seen how to set up an API that serves XP content data, and that using that data to render something with react in the browser boils down to passing props and handling a component state, this opens up for **headless approaches!**

## Standalone React4xp in a nutshell

The takeaway of this chapter is this: React4xp components (entries and dependencies) can be used without any XP controller or `React4xp.render` call. To do that, the base HTML (the response of a first page request, or some script loaded by it) **must do these tasks**:

- Load React and ReactDOM from somewhere. For example a CDN,

- Load all the [dependency chunks](learn/react4xp-tutorial/5.x/appendix/chunks.md) that the entries need (before loading the entry assets!),

- Load all [entry assets](learn/react4xp-tutorial/5.x/appendix/entries.md). This will make each entry available in the browser’s JS namespace as a react-component-creating function, at `React4xp[jsxPath].default`, for each entry’s [jsxPath](learn/react4xp-tutorial/5.x/appendix/jsxpath.md).

- Construct a props object for each entry that uses props. This is where we’ll contact the [graphQL endpoint](learn/react4xp-tutorial/5.x/advanced/client-side.md#expose_api) in this lesson, for fetching the data from XP.

- Use the props with each entry’s component-creating function to create a react-renderable component:

```typescript
const component = React4xp[jsxPath].default(props);
```

- Finally, render the component into your DOM as a react app:

```typescript
ReactDOM.render(component, document.getElementById("my-target-container-id"));
```

If you’ve used React before, this is the same flow.

> **Note:** **This approach does NOT include server-side react rendering!** At least not out of the box. But since the React4xp build processes are pretty regular webpack, using regular react, it should be perfectly possible to tweak things and engineer your own solutions.

## Lesson overview

We’ll take a look at **two variations** of how to use React4xp-compiled components without rendering them from XP controllers. Both of them do [the same steps above](#nutshell), in slightly different ways:

- **Completely standalone:** this first variation is the manual, hardcoded, vanilla-js-and-react webapp approach. The HTML and script do everything explicitly: asset URLs and initial values are **handled and organized manually in the HTML itself**, and the script at the end fetches data from guillotine, organizes them into props and makes a **regular `ReactDOM.render` call**. In this approach, XP’s role is mainly to serve content data through the guillotine API. Pretty independent but there are no helpers; so getting things right is up to you.

- **Webapp with XP helpers:** this second variation is "slightly standalone": we use XP to wrap a little boilerplate for convenience: **XP and thymeleaf provides some initial values**. The script at the end is still loaded and used to fetch data and create props, but instead of having the HTML load all the entry and dependency assets and call `React4xp.render`, the React4xp client wrapper is loaded in order to use a **React4xp helper function:** `.renderWithDependencies`. This is an all-in-one rendering trigger that takes one or more [entry jsxPaths](learn/react4xp-tutorial/5.x/appendix/jsxpath.md) with props and target container ID’s, and uses **XP services** for auto-tracking and loading all the assets needed (including dependency chunks) before rendering them.

Keep in mind that except for the XP services in the second variation, **no running XP is strictly necessary for this to work**. The data-serving endpoint could be any API (e.g. REST) instead of guillotine, and the initial HTML and JS/CSS assets are static and could be served from anywhere. Use whatever approach suits your project.

But we’ll use XP anyway in this chapter: we already have it up and running from the previous chapters. So we’ll use [the XP webapp functionality](https://developer.enonic.com/guides/my-first-webapp) (see [here](https://developer.enonic.com/docs/xp/stable/runtime/engines/webapp-engine) for more documentation) to serve the initial HTML, and the [regular XP asset functionality](https://developer.enonic.com/docs/xp/stable/runtime/engines/asset-service) for serving the assets for the entries and dependencies.

### Source files

Files involved (src/main/resources/…​) - in addition to the ones from chapter 8:

```files
webapp/
    webapp.ts
    standalone.ts
    standalone.html

assets/webapp/
    script.js
```

XP uses *standalone.ts* and *standalone.html* to generate an initial HTML that directly makes the browser run most of [the steps above](#nutshell), fetching assets and setting up initial values, and then calling the final *script.js* asset, which handles the rest.

## 1. Completely standalone

In this first of the two approaches, we’ll minimize the use of runtime XP: all values and asset URLs are hardcoded. XP is used to serve the initial HTML and the assets, as well as providing a guillotine endpoint where the browser can fetch data, but this functionality can easily be replaced with any other file- and data-serving solution and still work just fine.

### HTML base

The webapp begins with some basic HTML, setting it all up in the browser.

standalone.html:

```html
<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8">
        <title>Completely standalone</title>

        <!-- <1> -->
        <script crossorigin src="https://unpkg.com/react@16/umd/react.production.min.js"></script>
        <script crossorigin src="https://unpkg.com/react-dom@16/umd/react-dom.production.min.js"></script>

        <!-- <2> -->
        [(${assetsHtml})]

        <style>
            body { margin: 0; padding: 0; }
            h1, p, .faux-spinner { padding: 30px; margin: 0 auto; font-family: 'DejaVu Sans', Arial, Helvetica, sans-serif; }
        </style>
    </head>

    <body>
        <h1>Top 3 movies to put in a list</h1>
        <p>#4 will blow your mind!</p>

        <!-- <3> -->
        <div id="movieListContainer">
            <div class="faux-spinner">Loading movies...</div>
        </div>

        <!-- <4> -->
        <script>
          var MOVIE_LIST_PARAMS = {
              parentPath: '/[[${SITE_NAME}]]',
              apiUrl: '[[${apiUrl}]]',
              movieType: '[[${APP_NAME}]]:movie',
              movieCount: 3,
              sortExpression: 'data.year ASC',
          };
        </script>

        <!-- <5> -->
        <script defer th:src="${assetRoot + '/webapp/script.js'}"></script>
    </body>
</html>
```

| ****1** | We start by running React and ReactDOM from a CDN. |
| --- | --- |
| ****2** | All the required css and js assets are linked. See controller below. |
| ****3** | The target container for the react app. The not-really-a-spinner (*"Loading movies…​"*) will be replaced when the actual *MovieList* is rendered into the container. |
| ****4** | Variables used by our particular script later, just wrapped in a `MOVIE_LIST_PARAMS` object to encapsulate them in the global namespace. These are the same values as in in the previous chapter, and the script at the end will use these in a `props` object, to create the renderable react app from the *MovieList* entry. Also note that we just hardcoded the values of `parentPath`, `apiUrl` and `movieType` here - they may be different in your setup. As [before](learn/react4xp-tutorial/5.x/advanced/client-side.md): `parentPath` is the content path of the site item under which the movie items will be found, `apiUrl` is the full path to `/api/headless` *below that site* (recall that the URL to the guillotine API depends on the URL of a site item like this, because of the way we set the API up with a controller mapping [earlier](learn/react4xp-tutorial/5.x/advanced/client-side.md#expose_api)), and `movietype` is the full, appname-dependent content type of the movie items to look for. |
| ****5** | Finally, loading the compiled script from *script.ts*, see [below](#script). |

> **Note:** The asset paths above have one or two components that depend on details in your setup: `{hash}` and `(…​my.asset.url)`.

`{hash}` stands for the content hashed part of the compiled-asset filename (where webpack is set up to do this - React4xp uses this for cache busting). These change on every recompilation of changed source code in React4xp dependency chunks - in the last chapter: everything below *src/main/resources/* ***react4xp/shared***.

`(…​my.asset.url)` stands for the root path to your particular source for the compiled assets.

For example, on my local machine where I’m using XP to fetch assets, the asset path `"(…​my.asset.url) /react4xp/shared.{hash}.js"` looks like this:

`"/_/asset/com.enonic.app.react4xp:1604314030/react4xp/shared.d366a6c1b.js"`

**How to find your particular URLs for hardcoding this example?** Again, this depends on your setup, but based on the previous chapter lesson: you can use the page/preview that’s produced from the Content Studio version of the movie list page, and just copy the asset paths from the produced page source HTML. Or if you know the asset root path but need the hash, you can run `gradlew clean build` and look at the file names below *build/resources/main/r4xAssets*.

Okay, moving on, a **webapp controller** is needed for XP to serve this HTML, and it’s about as minimal as an XP controller can be:

webapp.ts:

```typescript
// export {get} from './standalone';
export {get} from './withHelpers';
```

standalone.ts:

```typescript
import {
  // getAssetUrls
  getComponentChunkUrls
} from '/lib/enonic/react4xp';
// @ts-expect-error No types for /lib/thymeleaf yet.
import thymeleaf from '/lib/thymeleaf';
import {
  assetUrl as getAssetUrl,
  serviceUrl as getServiceUrl
} from '/lib/xp/portal';

const VIEW = resolve('standalone.html');
const PROJECT = 'default';
const BRANCH = 'master';
const SITE_NAME = 'sample-site';
const SITE_ROOT = `/site/${PROJECT}/${BRANCH}/${SITE_NAME}`;

export function get() {
  const assetUrls = getComponentChunkUrls('MovieList');

  const assetsArray = [];
  for (let i = 0; i < assetUrls.length; i++) {
    const assetUrl = assetUrls[i];
    const ext = assetUrl.split('.').pop();
    if (ext === 'css') {
      assetsArray.push(`<link rel="stylesheet" type="text/css" href="${assetUrl}" />`);
    } else if (ext === 'js') {
      assetsArray.push(`<script src="${assetUrl}"></script>`);
    }
  }

  return {
    contentType: 'text/html',
    body: thymeleaf.render(VIEW, {
      apiUrl: `${SITE_ROOT}/api/headless`,
      APP_NAME: app.name,
      assetRoot: getAssetUrl({path: ''}),
      assetsHtml: assetsArray.join('\n'),
      serviceRoot: getServiceUrl({service: ''}),
      SITE_NAME
    })
  };
}
```

### The script

Finally, the script that’s called at the end of the HTML.

> **Tip:** If you’ve been through the lesson in the previous chapter, you might recognize that **the logic in is script is the same** - the functions here are just copied or slightly modified from [*movieListRequests.ts*](learn/react4xp-tutorial/5.x/advanced/client-side.md#movielistrequests) and [*guillotineRequest.ts*](learn/react4xp-tutorial/5.x/advanced/client-side.md#guillotine_request_helper) - see those for more reference.

#### Quick overview of the script:

- The main function is `requestAndRenderMovies`.

It gets its input values from the `MOVIE_LIST_PARAMS` object we defined in the global namespace in the HTML earlier.

- It uses these values to request data about *3* (`movieCount`) *movies* (`movieType`) under the *movielist* site (`parentPath`), from the guillotine API.

Just like in the previous chapter, the guillotine query string for fetching movies is built with a function, `buildQueryListMovies` (but compared to the previous chapter, it now uses parameters instead of hardcoding the content type and parentPath).

- The returned data is parsed into a JSON array of movie objects (`extractToMovieArray`)…​

- …​and passed to the `renderMovie` function, where it’s used in a `props` object alongside other values from `MOVIE_LIST_PARAMS`.

- Along with the `props`, the *MovieList* entry (`React4xp['MovieList]`) is used to create a renderable react component…​

- …​that is rendered into the target `movieListContainer` element in the DOM with `ReactDOM.render`, now as a top-level react app.

#### Script code

script.js:

```javascript
const buildQueryListMovies = (movieType, parentPath) => {
  // verify content type names like "com.enonic.app.react4xp:movie" and match up groups before and after the colon:
  const matched = movieType.match(/(\w+(\.\w+)*):(\w+)/i);
  if (!matched) {
      throw Error(`movieType '${movieType}' is not a valid format.` +
          "Expecting <appName>:<XP content type>, for example: 'com.enonic.app.react4xp:movie' etc");
  }

  // e.g. "com.enonic.app.react4xp" --> "com_enonic_app_react4xp:
  const appNameUnderscored = matched[1].replace(/\./g, '_');

  // e.g. "movie" --> "Movie"
  const ctyCapitalized = matched[3][0].toUpperCase() + matched[3].substr(1);

  return `
query($first:Int!, $offset:Int!, $sort:String!) {
guillotine {
  query(contentTypes: ["${movieType}"], query: "_path LIKE '/content${parentPath}/*'", first: $first, offset: $offset, sort: $sort) {
    ... on ${appNameUnderscored}_${ctyCapitalized} {
      _id
      displayName
      data {
        year
        description
        actor
        image {
          ... on media_Image {
            imageUrl(type: absolute, scale: "width(300)")
          }
        }
      }
    }
  }
}
}`;
};

// Returns arrays unchanged.
// If the maybeArray arg is a non-array value, wraps it in a single-item array.
// If arg is falsy, returns an empty array.
const forceArray = maybeArray => {
  if (Array.isArray(maybeArray)) {
      return maybeArray;
  }
  return (maybeArray) ? [maybeArray] : [];
};

// Adapts the output from the guillotine query to the MovieList props signature
const extractMovieArray = responseData => responseData.data.guillotine.query
  .filter( movieItem => movieItem && typeof movieItem === 'object' && Object.keys(movieItem).indexOf('data') !== -1)
  .map(
      movieItem => ({
          id: movieItem._id,
          title: movieItem.displayName.trim(),
          imageUrl: movieItem.data.image.imageUrl,
          year: movieItem.data.year,
          description: movieItem.data.description,
          actors: forceArray(movieItem.data.actor)
              .map( actor => (actor || '').trim())
              .filter(actor => !!actor)
      })
  );

// ---------------------------------------------------------

// Makes a (guillotine) request for data with these search parameters and passes updateDOMWithNewMovies as the callback
// function to use on the returned list of movie data
const requestAndRenderMovies = () => {
  fetch(
      MOVIE_LIST_PARAMS.apiUrl,
      {
          method: "POST",
          body: JSON.stringify({
              query: buildQueryListMovies(
                  MOVIE_LIST_PARAMS.movieType,
                  MOVIE_LIST_PARAMS.parentPath
              ),
              variables: {
                  first: MOVIE_LIST_PARAMS.movieCount,
                  offset: 0,
                  sort: MOVIE_LIST_PARAMS.sortExpression
              }}
          ),
      }
  )
      .then(response => {
          if (!(response.status < 300)) {
              throw Error(`Guillotine API response:\n
              \n${response.status} - ${response.statusText}.\n
              \nAPI url: ${response.url}\n
              \nInspect the request and/or the server log.`);
          }
          return response;
      })

      .then(response => response.json())
      .then(extractMovieArray)
      .then(renderMovies)
      .catch( error => {console.error(error);})
};

const renderMovies = (movies) => {
  console.log("Rendering initial movies:", movies);

  // When compiled, all React4xp entries are exported as functions,
  // as "default" under the entryName (jsxPath), inside the global object `sanitized(app.name)React4xp`:
  const componentFunc = ComEnonicAppSamples_react4xpReact4xp['MovieList'].default;

  // Run the componentFunc with the props as argument, to build a renderable react component:
  const props = {
      movies: movies,
      apiUrl: MOVIE_LIST_PARAMS.apiUrl,
      parentPath: MOVIE_LIST_PARAMS.parentPath,
      movieCount: MOVIE_LIST_PARAMS.movieCount,
      movieType: MOVIE_LIST_PARAMS.movieType,
      sortExpression: MOVIE_LIST_PARAMS.sortExpression
  };
  const component = componentFunc(props);

  // Get the DOM element where the movie list should be rendered:
  const targetElement = document.getElementById("movieListContainer");

  // Straight call to ReactDOM (loaded from CDN):
  ReactDOM.render(component, targetElement);
};

// Finally, calling the entry function and running it all:
requestAndRenderMovies();
```

### Output

Assuming you’ve been through the [client-side lesson](learn/react4xp-tutorial/5.x/advanced/client-side.md), you can now rebuild the project. But instead of opening Content Studio, open the XP main menu in the top right corner, choose *Applications*, and in the Applications viewer, select your app:

At the bottom of the app info panel, you’ll see a URL where you can preview the webapp we just built:

Clicking this link should now show you the working webapp - listing 3 initial movies and filling in more as you scroll down, just like in the preview at the end of the previous chapter.

## 2. Webapp with XP helpers

This is all nice and well, but a cumbersome part is that it requires you to supply values and asset URLs yourself, or ways to figure them out. Hashes in file names is a neat way of content-based cache busting, but keeping track of the resulting file names can be a chore. Even if that’s not an issue, it could be handy to have a way to just supply the name (jsxPath) of the entry (or entries) you want to render, and let the system itself figure out what dependency chunk(s) are needed to load alongside the entry asset(s). Not to mention prevent them from being downloaded twice.

If you have XP running but still want to make things work headlessly and outside of Content Studio, React4xp provides a couple of helpers for this. The client wrapper comes with the function `.renderWithDependencies`, which uses an XP service to track the sum set of dependency chunks required to render a set of jsxPaths, loads them and the entry assets, and renders them.

### HTML base

The HTML base is very similar to the one in [the previous example](#html1), only this time since we’re using XP anyway, it’s a more traditional [thymeleaf template](https://developer.enonic.com/docs/thymeleaf-library). This means we can get rid of most of the hardcoded stuff in the HTML.

Just like before, we get react/react-dom from a CDN, provide a pinch of styling and a ready container to render into (with a "spinner". Whatever). But the differences are these:

withHelpers.html:

```html
<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8">
        <title>All headless</title>

        <script crossorigin src="https://unpkg.com/react@16/umd/react.production.min.js"></script>
        <script crossorigin src="https://unpkg.com/react-dom@16/umd/react-dom.production.min.js"></script>

        <!-- <1> -->
        [(${clientAssetHtml})]

        <style>
            body { margin: 0; padding: 0; }
            h1, p, .faux-spinner { padding: 30px; margin: 0 auto; font-family: 'DejaVu Sans', Arial, Helvetica, sans-serif; }
        </style>
    </head>

    <body>
        <h1>Top 3 movies to put in a list</h1>
        <p>#4 will blow your mind!</p>

        <div id="movieListContainer">
            <div class="faux-spinner">Loading movies...</div>
        </div>

        <!-- <2> -->
        <script data-th-utext="|
        var MOVIE_LIST_PARAMS= {
            serviceUrlRoot: '${portal.serviceUrl({'_service='})}',
            parentPath: '/${SITE_NAME}',
            apiUrl: '/site/${PROJECT}/${BRANCH}/${SITE_NAME}/api/headless',
            movieType: '${movieType}',
            movieCount: 3,
            sortExpression: 'data.year ASC',
        }|"></script>

        <!-- <3> -->
        <script defer data-th-src="${portal.assetUrl({'_path=webapp/script2.js'})}"></script>
    </body>
</html>
```

| ****1** | This is where we [previously](#html1) put URLs to each specific dependency chunk and entry asset we want to use. Here, we only load the React4xp client-wrapper, and make it available in the browser’s namespace as `React4xp.CLIENT`. |
| --- | --- |
| ****2** | As before, we set a few initial values for the final script to use. Two things are different here, though: first, we let the XP controller (right below) supply the appname-dependent content type and the content path to the site with the movies below it. And second: `serviceUrlRoot`. This value is the URL root of the XP services, and lets the script know where to look for the service that tracks the entries' assets and dependencies. |
| ****3** | The final script asset ([below](#script2)), also loaded by using the `portal.assetUrl` function with thymeleaf instead of hardcoded. |

The **webapp controller** needs to provide that extra little info to the values in `MOVIE_LIST_PARAMS`, in the thymeleaf `model` now:

withHelpers.ts:

```typescript
import {getClientUrl} from '/lib/enonic/react4xp';
// @ts-expect-error No types for '/lib/thymeleaf' yet.
import thymeleaf from '/lib/thymeleaf';

const VIEW = resolve('withHelpers.html');
const PROJECT = 'default';
const BRANCH = 'master';
const SITE_NAME = 'sample-site';

export function get(req) {
  const clientUrl = getClientUrl();

  const model = {
    clientAssetHtml: `<script src="${clientUrl}"></script>`,
    BRANCH,
    movieType: `${app.name}:movie`,
    PROJECT,
    SITE_NAME
  };

  return {
    contentType: 'text/html',
    body: thymeleaf.render(VIEW, model)
  };
}
```

### The script asset

The script asset is almost identical to before. All that’s changed is in `renderMovies` at the end:

script2.js:

```javascript
const buildQueryListMovies = (movieType, parentPath) => {
  // verify content type names like "com.enonic.app.react4xp:movie" and match up groups before and after the colon:
  const matched = movieType.match(/(\w+(\.\w+)*):(\w+)/i);
  if (!matched) {
      throw Error(`movieType '${movieType}' is not a valid format. Expecting <appName>:<XP content type>, for example: 'com.enonic.app.react4xp:movie' etc`);
  }

  // e.g. "com.enonic.app.react4xp" --> "com_enonic_app_react4xp
  const appNameUnderscored = matched[1].replace(/\./g, '_');

  // e.g. "movie" --> "Movie"
  const ctyCapitalized = matched[3][0].toUpperCase() + matched[3].substr(1);

  return `
query($first:Int!, $offset:Int!, $sort:String!) {
guillotine {
  query(contentTypes: ["${movieType}"], query: "_path LIKE '/content${parentPath}/*'", first: $first, offset: $offset, sort: $sort) {
    ... on ${appNameUnderscored}_${ctyCapitalized} {
      _id
      displayName
      data {
        year
        description
        actor
        image {
          ... on media_Image {
            imageUrl(type: absolute, scale: "width(300)")
          }
        }
      }
    }
  }
}
}`;
};

// Returns arrays unchanged.
// If the maybeArray arg is a non-array value, wraps it in a single-item array.
// If arg is falsy, returns an empty array.
const forceArray = maybeArray => {
  if (Array.isArray(maybeArray)) {
      return maybeArray;
  }
  return (maybeArray) ? [maybeArray] : [];
};

// Adapt the output from the guillotine query to the MovieList props signature
const extractMovieArray = responseData => responseData.data.guillotine.query
  .filter( movieItem => movieItem && typeof movieItem === 'object' && Object.keys(movieItem).indexOf('data') !== -1)
  .map(
      movieItem => ({
          id: movieItem._id,
          title: movieItem.displayName.trim(),
          imageUrl: movieItem.data.image.imageUrl,
          year: movieItem.data.year,
          description: movieItem.data.description,
          actors: forceArray(movieItem.data.actor)
              .map( actor => (actor || '').trim())
              .filter(actor => !!actor)
      })
  );

// ---------------------------------------------------------

// Makes a (guillotine) request for data with these search parameters and passes updateDOMWithNewMovies as the callback
// function to use on the returned list of movie data
const requestAndRenderMovies = () => {
  fetch(
      MOVIE_LIST_PARAMS.apiUrl,
      {
          method: "POST",
          body: JSON.stringify({
              query: buildQueryListMovies(
                  MOVIE_LIST_PARAMS.movieType,
                  MOVIE_LIST_PARAMS.parentPath
              ),
              variables: {
                  first: MOVIE_LIST_PARAMS.movieCount,
                  offset: 0,
                  sort: MOVIE_LIST_PARAMS.sortExpression
              }}
          ),
      }
  )
      .then(response => {
          if (!(response.status < 300)) {
              throw Error(`Guillotine API response:\n
              \n${response.status} - ${response.statusText}.\n
              \nAPI url: ${response.url}\n
              \nInspect the request and/or the server log.`);
          }
          return response;
      })

      .then(response => response.json())
      .then(extractMovieArray)
      .then(renderMovies)
      .catch( error => {console.error(error);})
};

const renderMovies = (movies) => {
  console.log("Rendering movies:", movies);

  const props = {
      movies: movies,
      apiUrl: MOVIE_LIST_PARAMS.apiUrl,
      parentPath: MOVIE_LIST_PARAMS.parentPath,
      movieCount: MOVIE_LIST_PARAMS.movieCount,
      movieType: MOVIE_LIST_PARAMS.movieType,
      sortExpression: MOVIE_LIST_PARAMS.sortExpression
  };

  (1)
  ComEnonicAppSamples_react4xpReact4xpClient.renderWithDependencies(
      {
          'MovieList': {
              targetId: 'movieListContainer',
              props: props
          }
      },
      null,
      MOVIE_LIST_PARAMS.serviceUrlRoot
  );
};

// Finally, calling the entry function and running it all:
requestAndRenderMovies();
```

| ****1** | No need to create the react components explicitly. As soon as the `props` are created, everything from there is handled by the `React4xp.CLIENT.renderWithDependencies` wrapper function.    Also, this is where the `serviceUrlRoot` value is used - .renderWithDependencies` will not work without it! |
| --- | --- |

### Output

The output when you preview it should be the same as [the previous example](#output1).

**That concludes the last of these lessons.**

You are now a legit React4xp knight! If you have improvement suggestions, questions, bug reports - welcome to talk with us about it:

- [Future improvements, requested features](https://github.com/enonic/lib-react4xp/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement)

- [The Enonic Forums](https://discuss.enonic.com)

- [Known bugs we’re working on](https://github.com/enonic/lib-react4xp/issues?q=is%3Aissue+is%3Aopen+label%3Abug) - and a few workarounds
