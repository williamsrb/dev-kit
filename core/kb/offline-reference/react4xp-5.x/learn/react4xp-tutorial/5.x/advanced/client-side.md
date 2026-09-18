<!-- src:https://developer.enonic.com/learn/react4xp-tutorial/5.x/advanced/client-side generated:2026-07-30T04:16:10Z format:llm-dense react4xp-5.x -->
#DOC learn/react4xp-tutorial/5.x/advanced/client-side.md

# Client side rendering

We will now look at how to use React4xp in combination with XP’s graphQL api.

> **Warning:** This chapter is currently based on the deprecated Guillotine library. We are working on updating it.

## Lesson overview

This chapter will focus on setting up the API and the first usages:

- set up a content type and react visualization for single movie items,

- making **a graphQL query** for content data in a regular XP controller,

- using React4xp to **visualize that data**,

- letting the rendered components make **the same query from the frontend**,

- and use react to dynamically render a visualization of the returned data, and this way fill in more content as we scroll down the page: an **"infinite scroller"** page.

> **Note:** The [next chapter](learn/react4xp-tutorial/5.x/advanced/standalone.md) will expand on this lesson. It demonstrates more decoupled (and less XP-centric) ways to use these same React4xp components in a *standalone webapp*, to render content data from a guillotine API.

### Source files

Files involved (src/main/resources/…​):

```files
react4xp/
    myEntries/                  (1)
        Movie.tsx
        MovieList.tsx
        MovieList.scss
    shared/
        Movie.tsx
        Movie.scss

site/
    content-types
        /movie/
            movie.xml           (2)
    parts/
        movie-list/
            movie-list.ts       (3)
            movie-list.xml
    site.xml                    (4)

controllers/
    previewMovie.ts             (5)

headless/                       (6)
    helpers/
        movieListRequests.ts
    guillotineApi.ts
    guillotineRequest.ts
```

| ****1** | We’re going to build a site which is a list of movies, each displayed with a poster and a bit of info. The **entries** *Movie* and *MovieList* both import a *shared/Movie* component. The *Movie* entry uses it to preview a single movie item inside Content Studio, while the *MovieList* entry displays the actual movie list site, by iterating over multiple *movie* data items and using the *shared/Movie* component for visualizing each item (both in a serverside-rendered and headless context). |
| --- | --- |
| ****2** | A content type for a single *movie*, |
| ****3** | A part with a controller that fetches child content items of the *movie* content type, and renders them into MovieList, |
| ****4** | In *site.xml* we will set up controller mappings for both the guillotine API and…​ |
| ****5** | …​the single-movie preview controller: displays a single movie without needing to set up a template and a part. |
| ****6** | *guillotineApi.ts* is the actual API to guillotine. It can run graphQL queries both from XP controllers and through received HTTP requests. And *guillotineRequest.ts* simplifies making such a request from the browser. Both of these are general-purpose and come with the starter (since version 1.1.0). But *helpers/movieListRequests.ts* contains helper functions specific to the lesson site we’re building here: it helps with building a query for fetching movie-list data, and parsing the returned data into the `props` format that the *Movie* component needs. These helpers are also used on both frontend and backend. |

## Groundwork: movie items

This first stage should be easy enough, almost entirely repeating steps you’ve been through in previous chapters. We’ll make a *movie* content type, set up React4xp to preview-render it with react components (but with [a little twist](#controller_mapping)), and add some movie items that will be listed when the site is done.

> **Note:** This entire chapter builds on the [config setup from the previous lesson](learn/react4xp-tutorial/5.x/imports-and-dependency-chunks.md#webpack_config): *react4xp.config.js*, *webpack.config.react4xp.js* and the extra NPM packages should be set up like that.

If you haven’t completed that section already, better take a couple of minutes and do that before proceeding.

### Movie content type

When the setup is ready, we’ll start by adding a *movie* **content type**, with an ImageSelector for a poster `image`, a simple TextArea with a movie `description`, a numeral Long field for adding the release `year` and an array of `actor` names:

site/content-types/movie/movie.xml:

```xml
<content-type>
  <display-name>Movie</display-name>
  <description>Moving images often reflecting culture</description>
  <super-type>base:structured</super-type>

  <form>
    <input name="image" type="ImageSelector">
        <label>Movie poster</label>
        <occurrences minimum="1" maximum="1"/>
    </input>

    <input name="description" type="TextArea">
        <label>Description</label>
    </input>

    <input name="year" type="Long">
        <label>Release year</label>
        <occurrences minimum="1" maximum="1"/>
    </input>

    <input name="actor" type="TextLine">
        <label>Actor</label>
        <occurrences minimum="0" maximum="0"/>
    </input>
  </form>
</content-type>
```

### React components

Next, we’ll set up a few react components for visualizing each movie item.

The **entry**, *Movie.tsx*, will take care of rendering a preview of each movie content item in content studio later:

react4xp/myEntries/Movie.tsx:

```typescript
import React from 'react'

import Movie from '../shared/Movie';

export default (props) => <Movie {...props} />;
```

This is a pure entry wrapper that just imports the next react component from *react4xp/shared*.

Why import code from *shared* instead of keeping it all in the entry? Firstly, it’s a good rule of thumb to keep entries slim, for better optimization. And secondly, in addition to a Content Studio preview for single movies, we’re going to use the **imported components** in the actual movie list too, for each single movie in the list. This way, the preview in Content Studio will always directly reflect what’s displayed on the final page, because it’s the same code that’s used everywhere:

react4xp/shared/Movie.tsx:

```typescript
import React from 'react'

import './Movie.scss';

const Cast = ({actors}) => (
    <ul className="cast">
        { actors.map( actor => <li key={actor} className="actor">{actor}</li> ) }
    </ul>
);

const Info = ({heading, children}) => (
    <div className="info">
        {heading ? <h3>{heading}</h3> : null}
        {children}
    </div>
);

const InfoContainer = ({title, year, description, actors}) => (
    <div className="infoContainer">
        <h2 className="title">{title}</h2>

        <Info heading="Released">
            <p className="year">{year}</p>
        </Info>

        <Info heading="Description">
            <div className="description">{description}</div>
        </Info>

        { (actors && actors.length > 0) ?
            <Info heading="Cast">
                <Cast actors={actors} />
            </Info> :
            null
        }
    </div>
);

const Movie = ({imageUrl, title, description, year, actors}) => (
    <div className="movie">
        <img className="poster"
             src={imageUrl}
             alt={`Movie poster: ${title}`}
             title={`Movie poster: ${title}`}/>

        <InfoContainer title={title}
                       year={year}
                       description={description}
                       actors={actors}
        />
    </div>
);

export default Movie;
```

Not a lot of functionality here, just a TSX file that contains some structural units nested inside each other: the exported root level in the component, `Movie`, contains a movie poster image, and nests an `InfoContainer` component that displays the rest of the movie data. There, each movie data section is wrapped in an `Info` component (which just displays a header), and finally each actor name is mapped out in a list in the `Cast` component.

Take a moment to note the **props signature** of *Movie.tsx*. `Movie` clearly expects the `imageUrl` prop to be a URL, so we’ll need to handle the `image` field from the content type. The props `description`, `title` and `year` are expected to be simple strings, but `actors` should be handled as a string array. As you’ll see, we’ll make sure that each data readout of a movie item is adapted to this signature.

Moving on, *Movie.tsx* also imports some **styling** that’ll be handled by webpack the same way as in [the previous chapter](learn/react4xp-tutorial/5.x/imports-and-dependency-chunks.md#webpack_rules):

react4xp/shared/Movie.scss:

```sass
html, body {
  margin: 0; padding: 0;
}

.infoContainer {
  flex-grow: 1; flex-basis: content; padding: 0; margin: 0;

  * {
    font-family: 'DejaVu Sans', Arial, Helvetica, sans-serif; color: #444;
  }

  h2, h3 {
    padding: 0; margin: 0; color: #0c0c0c;
  }

  h2 {
    font-size: 34px;
  }

  p {
    padding: 0; margin: 10px 0 0 0;
  }
}

.info {
  margin: 0; padding: 30px 0 0 0;
}

.movie {
  margin: 0; padding: 30px; box-sizing: border-box; width: 100%; display: flex; flex-flow: row nowrap; justify-content: flex-start; align-items: flex-start;
}

.poster {
  width: 300px; max-width: 30%; margin-right: 30px; flex: 0 1 auto;
}

.cast {
  list-style-type: none; margin: 0; padding: 0;

  .actor {
    width: 100%; padding: 0; margin: 10px 0 0 0;
  }
}
```

### Controller mapping

Here comes a little variation: in this example, we want to connect a movie content item to with the rendering of the *Movie.tsx* entry. But we don’t want to mess around with setting up a [template with a part](learn/react4xp-tutorial/5.x/pages-parts-and-regions.md#page_template_setup) the way we’ve done so far. Instead, we can use a [controller mapping](https://developer.enonic.com/docs/xp/stable/framework/mappings) to make that connection in code.

Let’s open *site.xml* and add a mapping:

site/site.xml:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<site>
  <form/>
  <mappings>

    <!-- Add this... -->
    <mapping controller="/controllers/previewMovie.js" order="50">
        <match>type:'com.enonic.app.react4xp:movie'</match>
    </mapping>
    <!-- ...and that's it. -->

  </mappings>
</site>
```

Now, every *movie* content item in Content Studio is always rendered with a particular controller: */controllers/previewMovie.js*.

Two important points when using a controller mapping like this:

> **Note:** First, the controller reference in a mapping in *site.xml* must always refer to **the runtime name of the controller**. In our case, the source file of our controller is */controllers/previewMovie* ***.ts***, but at compile time, this is compiled into ***.js*** which is used at XP runtime.

Second, controller mappings use qualified content type names that have **the name of the app** in it: `com.enonic.app.react4xp`. If/when you use a different name for your app, make sure to update content type references like this, e.g. `<match>type:'my.awesome.app:movie'</match>`

Now, with that mapping set up, we can add the *previewMovie* controller:

controllers/previewMovie.ts:

```typescript
const portal = require('/lib/xp/portal');
const React4xp = require('/lib/enonic/react4xp');

const forceArray = maybeArray => {
    if (Array.isArray(maybeArray)) {
        return maybeArray;
    }
    return (maybeArray) ? [maybeArray] : [];
};

export function get(request) {
    const content = portal.getContent();            (1)

    const props = {
        imageUrl: content.data.image ?
            portal.imageUrl({                       (2)
                id: content.data.image,
                scale: 'width(300)'
            }) :
            undefined,
        title: content.displayName,
        description: content.data.description,
        year: content.data.year,
        actors: forceArray( content.data.actor )   (3)
            .map( actor => (actor || '').trim())
            .filter(actor => !!actor)
    };

    const id = content._id;                         (4)

    const output = React4xp.render(
        'Movie',                                    (5)
        props,
        request,
        {
            id,
                                                    (6)
            body: `
                <html>
                    <head>
                        <meta charset="UTF-8" />
                        <title>${content.displayName}</title>
                    </head>
                    <body class="xp-page">
                        <div id="${id}"></div>
                    </body>
                </html>
            `
        }
    );

    output.body = '<!DOCTYPE html>' + output.body;  (7)

    return output;
};
```

After the previous chapters, not much in this controller should come as a surprise, but a quick overview anyway:

| ****1** | We use `getContent` to fetch the movie item data as usual (later, we’ll use guillotine in a similar fashion. This doesn’t matter as long as the props are constructed according to the signature of *Movie.tsx*). |
| --- | --- |
| ****2** | `image` comes from an ImageSelector and is just an image item ID, so we use `imageUrl` to get the URL that the prop signature expects. |
| ****3** | Normalizing the `actor` data to guarantee that it’s an array. |
| ****4** | `React4xp.render` needs a unique ID to target a container in the surrounding `body`. |
| ****5** | `"Movie"` is of course the [jsxPath](learn/react4xp-tutorial/5.x/appendix/jsxpath.md) reference to the entry, *react4xp/myEntries/Movie.tsx*. |
| ****6** | This controller is the only one triggered for rendering *movie* items. That means that the `body` that the rendering is inserted into, has to be a **full root HTML document** including a `<head>` section (or otherwise React4xp won’t know where to put the rendered page contributions, and the component won’t work properly). |
| ****7** | Workaround for a current [inconvenient bug](https://github.com/enonic/lib-react4xp/issues/107). |

### Make some Movies

With all this in place, we’re about to finish the groundwork stage: let’s add some *movie* content items to list.

[Build the project as usual and start XP](learn/react4xp-tutorial/5.x/hello-react.md#first_setup_render).

Create a site content item and connect it to your app. Create some new Movie items:

It’s important that **the new movies are inside/under *one common container item* in the content hierarchy**. It’s easiest for this lesson if the movie items are just directly under the site itself:

When you mark/preview the site itself, you’ll see no visualization yet. But previewing each movie item should now work as in the image above.

Now we’re ready to move on to more interesting stuff, using the content and code we just made.

## Static movie list

Next, we’ll make a page controller for a site item that displays a static list of the *movie* items below it. The controller will use a configurable guillotine query to fetch an array of movie data items.

### Guillotine helpers and usage

First off, an introduction to the guillotine helpers at we’ll be using. Two of them - *headless/guillotineApi.ts* and *headless/guillotineRequests.ts* - are general-purpose helpers **included in the React4xp starter**, and the third one we’ll write next.

### Included helper: guillotineApi.ts

The most central of the helpers and the first one we’ll use, is ***headless/guillotineApi.ts***. If we strip away a little boilerplate, the bare essence of it looks like this:

headless/guillotineApi.ts:

```typescript
// @ts-expect-error No types for /lib/guillotine yet.
import {createSchema, execute} from '/lib/guillotine';

const SCHEMA = createSchema();

// ----------------------------------------------  FOR USE IN CONTROLLERS:    ------------------------------------

export const executeQuery = (query, variables) => execute({
  query: query,
  variables: variables,
  schema: SCHEMA
});

// Expose and use in POST requests from frontend:
export const post = req => {                             (3)
  const {
    query,
    variables
  } = JSON.parse(req.body);

  return {
    contentType: 'application/json',
    body: executeQuery(query, variables),
    status: 200
  };
};
```

| ****1** | At the core is the function `executeQuery`. Here, a guillotine `SCHEMA` definition is combined with a graphQL `query` string and an optional `variables` object. These are used with XP’s graphQL library to `execute` the query. The result, a JSON object, is returned. |
| --- | --- |
| ****2** | `executeQuery` is exposed and directly usable from an XP controller. That’s what we’ll do next. |
| ****3** | a `post` function is also included for receiving POST requests from outside, e.g. a browser. If these requests contain a query string, it’s executed with `executeQuery` above, and the result is returned in a response: basically a complete guillotine API endpoint for your webapp. |

> **Note:** This endpoint is **disabled by default** in the starter, to encourage developers to consider security aspects before using it. We’ll get back to that, and activate it, [later](#expose_api).

The second included helper, [guillotineRequest.ts](#guillotine_request_helper), is a `fetch` wrapper to simplify guillotine requests at the frontend. We’ll take a look at that later.

### Domain-specific helper for listing movies

In order to make requests for a list of movies below a container item in the content hierarchy, we’ll need a specific guillotine query string, as well as functionality to adapt the resulting data into the proper props structure for the react components.

And by using the same code on the frontend and backend, for this too, we gain a bit of isomorphism (the predictability of a single source of truth, in short). So we’ll make **a module with custom helper functionality** for our use case, and import from it in both places.

Let’s go ahead an write this:

headless/helpers/movieListRequests.ts:

```typescript
// Used by both backend and frontend (the movie-list part controller, and react4xp/entries/MovieList.jsx)

(1)
export const buildQueryListMovies = () => `
query(
    $first:Int!,
    $offset:Int!,
    $sort:String!,
    $parentPathQuery:String!
) {
  guillotine {
    query(
        contentTypes: ["com.enonic.app.samples_react4xp:movie"],
        query: $parentPathQuery,
        first: $first,
        offset: $offset,
        sort: $sort
    ) {
      ... on com_enonic_app_samples_react4xp_Movie {
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

(2)
export const buildParentPathQuery = (parentPath) => `_parentPath = '/content${parentPath}'`;

// Returns arrays unchanged.
// If the maybeArray arg is a non-array value, wraps it in a single-item array.
// If arg is falsy, returns an empty array.
const forceArray = maybeArray => {
    if (Array.isArray(maybeArray)) {
        return maybeArray;
    }
    return (maybeArray) ? [maybeArray] : [];
};

(3)
// Adapts the output from the guillotine query to the MovieList props signature
export const extractMovieArray = responseData => responseData.data.guillotine.query
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

export default {};
```

| ****1** | The function `buildQueryListMovies` returns a string: a **guillotine query** ready to use in the API. Colloquially, you can read this query in 3 parts:        The parenthesis after the first `query` declares some parameters that are required (hence the `!`) as values in a `variables` object together with the query.      In the parenthesis after the second `query`, those `variables` values are used: this query will list a certain number (`$first`) of movie items (`contentTypes: ["com.enonic.app.react4xp:movie"]`), starting at index number `$offset`, and sort them using the sort expression string `$sort`. It narrows down the search by nesting a second and specifying query expression `$parentPathQuery`, that tells guillotine to only look below a certain parent path in the content hierarchy - see below (2.).      The last major block, `…​ on com_enonic_app_react4xp_Movie {`, asks for a selection of sub-data from each found movie item: `_id`, `displayName`, `data.year`, etc. Note the second `…​ on media_Image` block nested inside it: instead of returning the ID value in the `data.image` field, we pass that through an `imageUrl` function that gives us a finished `data.imageUrl` field instead - directly and in one single query.    For more about guillotine queries, see the [guillotine API documentation](https://developer.enonic.com/docs/guillotine/stable/api). |
| --- | --- |
| ****2** | The function `buildParentPathQuery` returns a **sub-query string** needed to only search below the content path of a container item: the parameter `$parentPathQuery` in the main query string (1.), inserted through the `variables` object.    In [the example above](#movies_in_container_site), the site *MovieSite* is the item that contains the movies, and the content hierarchy in Content Studio shows us that *MovieSite* has the content path `/moviesite`. So the sub-query that directs guillotine to only search for movies below that parent item, can be made like this: `buildParentPathQuery('/moviesite')`. |
| ****3** | The function `extractMovieArray` takes the data object of a full guillotine search result and adapts it to the data structure that matches the props structure of our react components: an array of objects, where each object is a movie item. |

> **Note:** Remember that this query hardcodes qualified names to a content type, that contain the name of the app: `com.enonic.app.react4xp:movie` and `com_enonic_app_react4xp_Movie`. If your app name is not `com.enonic.app.react4xp`, you’ll need to change these.

### Part controller

Armed with these helpers, we can build an XP part controller that runs a guillotine query, extracts movie props from it, and renders a list of movies. We can even let the part’s config control how the movies are listed:

site/parts/movie-list/movie-list.xml

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<part>
    <display-name>Movie List</display-name>
    <description>View a list of movies</description>
    <form>

        <input name="movieCount" type="Long">
            <label>Number of movies to display</label>
            <occurrences minimum="1" maximum="1"/>
            <config/>
            <default>5</default>
        </input>

        <input name="sortBy" type="RadioButton">
            <label>Sort movies by...</label>
            <occurrences minimum="1" maximum="1"/>
            <config>
                <option value="displayName">Title</option>
                <option value="data.year">Release year</option>
                <option value="createdTime">Date added to this db</option>
            </config>
            <default>createdTime</default>
        </input>

        <input  name="descending" type="CheckBox">
            <label>... in descending (reversed) order</label>
        </input>
    </form>
</part>
```

The actual controller:

site/parts/movie-list/movie-list.ts:

```typescript
import type {PartComponent} from '@enonic-types/core';

import {toStr} from '@enonic/js-utils/value/toStr';
import {
  getComponent,
  getContent,
  getSite
} from '/lib/xp/portal';
import {render} from '/lib/enonic/react4xp';
import {executeQuery} from '/headless/guillotineApi';      (1)
import {
  buildQueryListMovies,
  buildParentPathQuery,
  extractMovieArray
} from '/headless/helpers/movieListRequests';

declare global {
  interface XpPartMap {
    ['com.enonic.app.samples-react4xp:movie-list']: {
      descending?: boolean
      movieCount: number
      sortBy?: 'displayName'|'data.year'|'createdTime'
    }
  }
}

type MovieListComponent = PartComponent<'com.enonic.app.samples-react4xp:movie-list'>

const ENTRY = 'MovieList';
// const ENTRY = 'MovieList2';
// const ENTRY = 'MovieList3';
// const ENTRY = 'MovieList4';

export function get(request) {
  const content = getContent();
  const component = getComponent<MovieListComponent>();
  const {
    descending = false,
    movieCount = 0,
    sortBy = 'createdTime'
  } = component.config;

  const sortExpression = `${sortBy} ${                     (2)
      descending ? 'DESC' : 'ASC'
  }`;

  const query = buildQueryListMovies();                    (3)

  const variables = {                                      (4)
    first: movieCount,
    offset: 0,
    sort: sortExpression,
    parentPathQuery: buildParentPathQuery(content._path)
  };

  const guillotineResult = executeQuery(query, variables); (5)
  log.info('guillotineResult: %s', toStr(guillotineResult));

  const movies = extractMovieArray(guillotineResult);      (6)

  return render(
    ENTRY,
    {                                                      (7)
      movies,
      apiUrl: `./${getSite()._path}/api/headless`,
      parentPath: content._path,
      movieCount: component.config.movieCount,
      sortExpression
    },
    request
  );
};
```

| ****1** | Import the functionality from the helpers that were [just described](#guillotine_helpers), |
| --- | --- |
| ****2** | Use the part’s config to build a sort expression for the query, |
| ****3** | Get the query string, |
| ****4** | Build the `variables` object with the query’s parameters (what’s up with a variable called `variables`, you ask? This is for consistencty - the guillotine lib and its docs refer to the encapsulated object of values for the various variables in the query, as an argument called `variables`. Now we have *that* clarified), |
| ****5** | Execute the query string with the variables in the guillotine API, |
| ****6** | Extract `movies` props (an array of objects with the same signature as the props for *Movie.tsx*) from the result of the query, |
| ****7** | Render a *MovieList* entry with the `movies` props (as well as some additional props that we will need later for making the same guillotine query from the frontend. Especially note the `apiUrl` prop: this is basically just the URL to the site itself, with `/api/headless` appended to it. When we later [expose the guillotine API](#expose_api) to the frontend, this is the URL to the API - specifically, the POST method in *guillotineApi.ts*). |

### React components

We’re still missing that ***MovieList* entry** that will display the list of movie items:

react4xp/myEntries/MovieList.tsx:

```typescript
import React from 'react'

import './MovieList.scss';

import Movie from "../shared/Movie";

const MovieList = ({movies, apiUrl, parentPath, movieCount, sortExpression}) => {

    return (
        <div className="movieList">
            {movies
                ? movies.map(movie =>
                        <Movie key={movie.id} {...movie} />
                    )
                : null
            }
        </div>
    );
};

// MUST use this export line wrapping, because of a useState hook later.
export default (props) => <MovieList {...props} />;
```

The only notable things here:

- A lot of the props aren’t used yet, just the `movies` array. The rest of the props are a preparation for later.

- Each item object in the array in `movies` is just mapped onto an imported *shared/Movie.tsx* component: the same react component that’s used to render the movie previews in Content Studio.

Most of the styling is already handled at the single-movie level, so just a minimum of extra **list styling** is needed:

react4xp/myEntries/MovieList.scss:

```sass
.movieList {
  margin: 0 auto; width: 1024px; max-width: 100%;

  .movie {
    border-bottom: 1px dotted #ccc;
  }
}
```

### Render the list

We can now set up the parent site with the movies, with a *movie-list* part. Rebuild the app, enter/refresh Content Studio, and make the *movie-list* part handle the visualization of the *MovieSite* item.

> **Tip:** You can either do that [with a template as before](learn/react4xp-tutorial/5.x/pages-parts-and-regions.md#adding_parts_to_new_content) to render *all* sites with this part controller. Or better, edit *MovieSite* directly and add the *movie-list* part to the region there, the same way as when adding a part to the region of a template. With this last direct-edit approach, only *MovieSite* will be rendered like this; other sites won’t.

Correctly set up, you can now select the list in the edit panel, and a part config panel will appear on the right. **Edit the config fields to control the guillotine query**: how many movies should be rendered, and in what order?

> **Tip:** As usual, click Preview to see the rendering in a tab of its own. A preview browser tab, with the page inspector and server log open on the side, is also the best starting point to hunt down bugs in the visualization.

## Making the list dynamic

In this next section we’ll expose the API to the frontend and let the client send a request to it. The returned data will be merged into the component state of the *MovieList* entry, and used to render the new movies into the page DOM. Finally, we’ll add a scroll listener to trigger the process.

### Exposing the guillotine API

The `post` method in the included *guillotineApi.ts* is nearly ready to use. All it needs to be activated for API requests from outside, is a controller mapping. We’ll add that next to the mapping [we’ve already added](#controller_mapping).

But first, a word of caution about doing this in other projects:

> **Note:** In the included form from the React4xp starter, *guillotineAPI.ts* is as bare-bone as it gets, and primarily meant as a stepping stone for developers to expand from.

Guillotine is a read-only interface, but still: after adding the controller mapping to an unchanged *guillotineAPI.ts*, it’s opened to receiving and **executing any guillotine query** from the frontend, technically exposing any data from the content repo to being read.

Before using it in production, **it’s highly recommended to implement your own security measures** in/around *guillotineAPI.ts*. For example authorization/permissions-checking/filtering what data is available/keeping the actual query string on the backend and only exposing the `variables` object, etc - depending on your environment and use case.

For the purpose of running this lesson on your localhost, though, it should be perfectly fine. Enter *site.xml* again to add the controller mapping:

site/site.xml:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<site>
  <form/>
    <mappings>
        <mapping controller="/controllers/previewMovie.js" order="50">
            <match>type:'com.enonic.app.react4xp:movie'</match>
        </mapping>

        <!-- Add this... -->
        <mapping controller="/headless/guillotineApi.js" order="50">
            <pattern>/api/headless</pattern>
        </mapping>
        <!-- ...to expose the API.  -->

    </mappings>
</site>
```

After rebuilding, the API is now up and running at `/api/headless` (e.g. `[http://localhost:8080/admin/site/preview/default/draft/moviesite/api/headless](http://localhost:8080/admin/site/preview/default/draft/moviesite/api/headless)`).

### Included helper: guillotineRequest.ts

Time to add some code to the existing *MovieList.tsx* so it can fetch data from the guillotine endpoint. To easily get started with that, we’ll use the second helper module **included in the react4xp starter**: *headless/guillotineRequest.ts* (the first of the two helpers is of course [guillotineApi.ts](#guillotine_helpers)).

This too has some convenience error handling and boilerplate like default parameter values/functions, but if we skip that, the bare essence is a `fetch` wrapper:

headless/guillotineRequest.ts:

```typescript
const doGuillotineRequest = ({
  url,                        (1)
  query,                      (2)
  variables,                  (3)
  handleResponseErrorFunc,    (4)
  extractDataFunc,            (5)
  handleDataFunc,             (6)
  catchErrorsFunc             (7)
}) => {

  fetch(
      url,
      {
          method: "POST",
          body: JSON.stringify({
              query,
              variables}
          ),
          credentials: "same-origin",
      }
  )
      .then(handleResponseErrorFunc)
      .then(response => response.json())
      .then(extractDataFunc)
      .then(handleDataFunc)
      .catch(catchErrorsFunc)
};

export default doGuillotineRequest;
```

In short, run `doGuillotineRequest(params)` where `params` is an object that has at least a `.url` and a `.query` attribute (and optional `.variables`), and it will send the query to the guillotine API and handle the returned data (or errors). How that’s handled is up to callbacks in `params`.

**Full `params` specs are:**

| ****1** | `url` (string, mandatory): URL to the API endpoint, i.e. to the controller mapping of `headless/guillotineApi.ts`: `<site-url>/api/headless`. |
| --- | --- |
| ****2** | `query` (string, mandatory): Must be a valid Guillotine query. |
| ****3** | `variables` (object, optional): corresponds to the guillotine `variables` object: key-value pairs where the keys correspond to parameters in the `query` string. E.g. the value of `variables.first` will be inserted into the query string as `$first`. |
| ****4** | `handleResponseErrorFunc` (function, optional): callback function that takes a response object and returns it, usually after having checked the response for errors and handled that. Default: just checks `response.status` for HTTP codes other than OK and throws any problems as `Error`. |
| ****5** | `extractDataFunc` (function, optional): callback function that takes a data object and returns another. After the response body has been parsed from JSON string to actual data, the data are run through this function, before being handled by `handleDataFunc`. Default: data is returned unchanged. |
| ****6** | `handleDataFunc` (function, optional but makes little sense to omit): callback function that takes a data object (curated data from guillotine) and does something with it - **this callback is pretty much what `doGuillotineRequest` is all about**. Default: do-nothing. |
| ****7** | `catchErrorsFunc` (function, optional): callback function that takes an error object and handles it. Default: console-error-logs the error message. |

### Frontend guillotine request

Now we’re ready to **add a guillotine call from the frontend**, specifically to *MovieList.tsx*. Here’s what we’ll do:

- Focus on the guillotine request and just add a click listener that asks for the *next X movie items* in the list after the ones that are displayed

- …​where X is the number of movies rendered to begin with. So if the *movie-list* part is configured to do the first rendering from the controller with X=3 movies, the guillotine request in *MovieList.tsx* will ask for data about the movies 4 through 6. Or in the language of our guillotine query: `first: 3, offset: 3`.

- It should also keep counting so that if we click one more time, it should ask for the next X movies *after* the ones it previously found

- …​so that in the next query, `first:3, offset:6`, and then `first:3, offset:9`, etc.

- It should do this by keeping the `query` string stable and updating `variables` for each request.

react4xp/myEntries/MovieList2.tsx:

```javascript
import React, { useState, useEffect } from 'react';     (1)

import './MovieList.scss';

import Movie from "../shared/Movie";

                                                        (2)
import doGuillotineRequest from "../../headless/guillotineRequest";
import { buildQueryListMovies, buildParentPathQuery, extractMovieArray } from "../../headless/helpers/movieListRequests";

                                                        (3)
// State values that don't need re-rendering capability, but need to be synchronously read/writable across closures.
let nextOffset = 0;             // Index for what will be the next movie to search for in a guillotine request

const MovieList = ({movies, apiUrl, parentPath, movieCount, sortExpression}) => {

                                                        (4)
    // UseEffect with these arguments ( function, [] ) corresponds to componentDidMount in the old-school class-based react components, and only happens after the first time the component is rendered into the DOM.
    useEffect(
        ()=>{
            console.log("Initializing...");
            nextOffset = movieCount;
        },
        []
    );

    // ------------------------------------------------------
    // Set up action methods, triggered by listener:

                                                                    (5)
    // Makes a (guillotine) request for data with these search parameters and passes an anonymous callback function as
    // handleDataFunc (used on the returned list of movie data).
    const makeRequest = () => {
        console.log("Requesting", movieCount, "movies, starting from index", nextOffset);
        doGuillotineRequest({
            url: apiUrl,                                            (6)

            query: buildQueryListMovies(),                          (7)

            variables: {
                first: movieCount,
                offset: nextOffset,                                 (8)
                sort: sortExpression,
                parentPathQuery: buildParentPathQuery(parentPath)   // (9)
            },

            extractDataFunc: extractMovieArray,                     (10)

            handleDataFunc: (newMovieItems) => {                    (11)
                console.log("Received data:", newMovieItems);
                nextOffset += movieCount;
            }
        });
    };

    // ------------------------------------------------------------------------------------
    // Actual rendering:

    return (
        <div className="movieList" onClick={makeRequest}>           {/* <12> */}
            {movies
                ? movies.map(movie =>
                        <Movie key={movie.id} {...movie} />
                    )
                : null
            }
        </div>
    );
};

// MUST use this export line wrapping, because of the hooks we'll add later.
export default (props) => <MovieList {...props} />;
```

The changes are:

| ****1** | Import some [react hooks](https://reactjs.org/docs/hooks-overview.html) to help us handle some component state and lifecycle events |
| --- | --- |
| ****2** | Import `doGuillotineRequest` described moments ago, and also the same helpers from *headless/helpers/movieListRequests.ts* that we’re already using [in the part controller](#movie-list-part-controller). |
| ****3** | `nextOffset` keeps track of how far the guillotine requests have counted, or rather: what the first movie in the next request should be (the next `variables.offset`) |
| ****4** | We pass a callback function to `useEffect`, a react hook that (in this case, since the array after is empty) only calls the callback after the first time the component has been rendered. This way, `nextOffset` gets an initial value, only once. |
| ****5** | `makeRequest` is the function that triggers the behavior: |
| ****6** | `doGuillotineRequest` sends a request to the API at the prop `apiUrl`. |
| ****7** | `buildQueryListMovies` gives ut the same query string as in the part controller, |
| ****8** | The rest of the `props` from the controller are now used to build the `variables` object which are inserted as the parameters in the query. Except the `offset` parameter, which uses the *current value* of the counting `nextOffset`, |
| ****9** | Just like in the controller, `buildParentPathQuery` uses the path of the movies' parent content to build a subquery variable, |
| ****10** | And also like in the controller, we use `extractMovieArray` to convert guillotine results to a data format that corresponds to an array of *Movie.tsx* props - just by passing the function into `doGuillotineRequest` as the `extractDataFunc` parameter, |
| ****11** | And finally, when we the data has passed through `extractMovieArray` and we get some `newMovieItems`, we do a temporary action for now: console-log the data, and increase `nextOffset` with the initial number of movies, so it’s ready for the next request. |
| ****12** | We add `onClick={makeRequest}` to the movie list DOM container element. Now, when we click the list, `makeRequest` is triggered, and the resulting data from the guillotine API is displayed in the browser log. |

Rebuilding this and running the moviesite in a preview window and with a console open, and the clicking somewhere on the list, say 3 times, the result might look something like this (note the console messages, how the returned movie IDs are not the same between responses, and that “starting from index…​” keeps counting):

### Dynamic DOM updates

With the request and the data flow in place, we’re just a small step away from **rendering the returned movies** at the bottom of the page, effectively filling in new movies on the page for each click.

React is *very* eager to do this whenever a component state is updated, so we’ll let it **render from the state** instead of directly from the `movie` prop:

react4xp/myEntries/MovieList3.tsx:

```typescript
import React, { useState, useEffect } from 'react'

import './MovieList.scss';

import Movie from "../shared/Movie";

import doGuillotineRequest from "../../headless/guillotineRequest";
import { buildQueryListMovies, buildParentPathQuery, extractMovieArray } from "../../headless/helpers/movieListRequests";

// State values that don't need re-rendering capability, but need to be synchronously read/writable across closures.
let nextOffset = 0;             // Index for what will be the next movie to search for in a guillotine request

const MovieList = ({movies, apiUrl, parentPath, movieCount, sortExpression}) => {

                                                                    (1)
    // Setup asynchronous component state that triggers re-render on change.
    const [state, setState] = useState({ movies });

    // UseEffect with these arguments ( function, [] ) corresponds to componentDidMount in the old-school class-based react components.
    useEffect(
        ()=>{
            console.log("Initializing...");

            nextOffset = movieCount;
        },
        []
    );

    // ------------------------------------------------------
    // Set up action methods, triggered by listener:

    // Makes a (guillotine) request for data with these search parameters and passes an anonymous callback function as
    // handleDataFunc (used on the returned list of movie data).
    const makeRequest = () => {
        console.log("Requesting", movieCount, "movies, starting from index", nextOffset);
        doGuillotineRequest({
            url: apiUrl,

            query: buildQueryListMovies(),

            variables: {
                first: movieCount,
                offset: nextOffset,
                sort: sortExpression,
                parentPathQuery: buildParentPathQuery(parentPath)
            },

            extractDataFunc: extractMovieArray,

            handleDataFunc: updateDOMWithNewMovies                  (2)
        });
    };

    // When a movie data array is returned from the guillotine data request, this method is called.
    const updateDOMWithNewMovies = (newMovieItems) => {
        console.log("Received data:", newMovieItems);
        if (newMovieItems.length > 0) {
            console.log("Adding movies to state:", newMovieItems.map(movie => movie.title));

            nextOffset += movieCount;                               (3)

            // Use a function, not just a new direct object/array, for mutating state object/array instead of replacing it:
            setState(oldState => ({                                 (4)
                movies: [
                    ...oldState.movies,
                    ...newMovieItems
                ]
            }));

            console.log("Added new movies to state / DOM.");
        }
    };

    // ------------------------------------------------------------------------------------
    // Actual rendering:

    return (
        <div className="movieList" onClick={makeRequest}>
            {state.movies
                ? state.movies.map(movie =>                         (5)
                        <Movie key={movie.id} {...movie} />
                    )
                : null
            }
        </div>
    );
};

// MUST use this export line wrapping, because of the useState hook.
export default (props) => <MovieList {...props} />;
```

Changes:

| ****1** | The `useState` react hook defines the component state: we pass the `movies` prop into it to set the initial state content. In return we get an array containing `state` - a handle for the *current* state - and `setState` - a function that updates the state. |
| --- | --- |
| ****2** | We now want `doGuillotineRequest` to trigger the new function `updateDOMWithNewMovies` when the guillotine data is returned and curated. |
| ****3** | In `updateDOMWithNewMovies` we only keep counting the `nextOffset` if any movies were actually added. |
| ****4** | We call `setState` to update the state, so that the incoming items from guillotine are added after the old ones. |
| ****5** | Use `state.movies` instead of just the `movies` props: now react will watch the state and automatically re-render the component as soon as the state is updated. |

> **Tip:** It’s possible to use `setState` with a new object instead of a function:

`setState( { movies: […​state.movies, …​newMovieItems]});`

But `setState` is an asynchronous function, and calling it with an object argument ("the current state of things" at the time setState is called, which is not when the update actually happens) runs the risk of introducing race conditions: we’d lose control of timing when the DOM updates, especially since we’re going to combine that length-of-DOM with a continuously scrolling and quickly updating trigger.

So in the example, we use a callback function argument to work around this. Something like *"Hey, React: whenever you’re ready to actually do the state update, do it based on what things are like at **that** time"*.

Rebuild the app, update the moviesite preview tab and try clicking on the list. New movies should appear below the existing one, expanding the movie list as you click:

### Scroll listener

We have arrived! The final step in this chapter:

We’ll finish *MovieList.tsx* by replacing the click listener with a scroll listener. The scroll listener will check if the page has been scrolled almost all the way to the bottom (i.e. the bottom of the movie-list container is just a little bit below the bottom of the screen) and triggers the same procedure if it has.

With one additional change to the procedure: the trigger should disable the scroll listener temporarily, only re-enabling it when we get some data back (or after a delay). This is to avoid flooding *guillotineApi.ts* with requests - since scroll events are fast and numerous.

react4xp/myEntries/MovieList4.tsx:

```typescript
import React, { useState, useEffect } from 'react'

import './MovieList.scss';

import Movie from "../shared/Movie";

import doGuillotineRequest from "../../headless/guillotineRequest";
import { buildQueryListMovies, buildParentPathQuery, extractMovieArray } from "../../headless/helpers/movieListRequests";

// State values that don't need re-rendering capability, but need to be synchronously read/writable across closures.
let nextOffset = 0;             // Index for what will be the next movie to search for in a guillotine request

let listenForScroll = true;                                         (1)
const TRIGGER_OFFSET_PX_FROM_BOTTOM = 200;                          (2)

const MovieList = ({movies, apiUrl, parentPath, movieCount, sortExpression}) => {

    // Setup asynchronous component state that triggers re-render on change.
    const [state, setState] = useState({ movies });

    const listContainerId = `movieListContainer_${parentPath}`;     (3)

    // UseEffect with these arguments ( function, [] ) corresponds to componentDidMount in the old-school class-based react components.
    useEffect(
        ()=>{
            console.log("Initializing...");

            nextOffset = movieCount;
                                                                    (4)
            // Browser-specific functionality, so this is prevented from running on the SSR
            if (typeof window.navigator !== 'undefined') {
                initScrollListener();
            }
        },
        []
    );

    // Set up scroll listener, when the component is first mounted.
    // Causes a trigger func function to be called when the bottom of the visible window is scrolled down to less
    // than TRIGGER_OFFSET_PX_FROM_BOTTOM of the movie list element.
    const initScrollListener = () => {
        console.log("Init scroll listener");
                                                                    (5)
        var movieListElem = document.getElementById(listContainerId);

        // ACTUAL SCROLL LISTENER:
        window.addEventListener("scroll", () => {
            if (listenForScroll) {                                  (6)

                                                                    (7)
                var movieBounds = movieListElem.getBoundingClientRect();
                if (movieBounds.bottom < window.innerHeight + TRIGGER_OFFSET_PX_FROM_BOTTOM) {
                    console.log("!!! SCROLL TRIGGER !!!");

                    listenForScroll = false;

                    makeRequest();

                }
            }
        });
    };

    // ------------------------------------------------------
    // Set up action methods, triggered by listener:

    // Makes a (guillotine) request for data with these search parameters and passes an anonymous callback function as
    // handleDataFunc (used on the returned list of movie data).
    const makeRequest = () => {
        console.log("Requesting", movieCount, "movies, starting from index", nextOffset);
        doGuillotineRequest({
            url: apiUrl,

            query: buildQueryListMovies(),

            variables: {
                first: movieCount,
                offset: nextOffset,
                sort: sortExpression,
                parentPathQuery: buildParentPathQuery(parentPath)
            },

            extractDataFunc: extractMovieArray,

            handleDataFunc: updateDOMWithNewMovies
        });
    };

    // When a movie data array is returned from the guillotine data request, this method is called.
    const updateDOMWithNewMovies = (newMovieItems) => {
        console.log("Received data:", newMovieItems);
        if (newMovieItems.length > 0) {
            console.log("Adding movies to state:", newMovieItems.map(movie => movie.title));

            nextOffset += movieCount;

            // Use a function, not just a new direct object/array, for mutating state object/array instead of replacing it:
            setState(oldState => ({
                movies: [
                    ...oldState.movies,
                    ...newMovieItems
                ]
            }));

            console.log("Added new movies to state / DOM.");

            listenForScroll = true;                                 (8)

        } else {
            setTimeout(
                () => {  listenForScroll = true; },
                500
            )

        }
    };

    // ------------------------------------------------------------------------------------
    // Actual rendering:

    return (
        <div id={listContainerId} className="movieList">            {/* <9> */}
            {state.movies
                ? state.movies.map(movie =>
                        <Movie key={movie.id} {...movie} />
                    )
                : null
            }
        </div>
    );
};

// MUST use this export line wrapping, because of the useState hook.
export default (props) => <MovieList {...props} />;
```

| ****1** | `listenForScroll` is the scroll-listener’s enabled-switch. |
| --- | --- |
| ****2** | Threshold value: if the distance between the bottom of the screen and the bottom of the movielist DOM container is less than this number of pixels, `makeRequest` should be triggered. |
| ****3** | We store a string to uniquely identify the movie-list container element in the DOM. |
| ****4** | In the component-initializing function (remember `useEffect`), we want to call `initScrollListener`. It’s a one-time function that sets up a scroll listener that will last for the lifespan of the component. However, remember that *MovieList.tsx* is also server-side rendered from the controller, so this very same script will run serverSide by React4xp! We check for `window.navigator` here because **we only want this scroll listener setup to run in a browser context**, not during SSR. Not only because a scroll listener makes no sense during server-side rendering, but to prevent errors that break the rendering (see the [note below](#serverbrowserbreakage)). |
| ****5** | During `initScrollListener`, we start by storing a handle to the movie-list container element in the DOM. |
| ****6** | The scroll event listener will be prevented from doing anything as long as `listenForScroll` is false. |
| ****7** | Here the distance between the bottom of the screen and the bottom of the movie-list container element is calculated. If that’s smaller than the threshold `TRIGGER_OFFSET_PX_FROM_BOTTOM`, disable the listener and trigger `makeRequest`, which performs the same duties as before: request movie data from the guillotine API, and insert that into the state to trigger rendering…​ |
| ****8** | …​with one thing added: switch the scroll listener back on when data has been received and handled, OR after 500 ms after receiving empty data. |
| ****9** | Removing the click listener and adding the unique ID `listContainerId` to the container element. |

> **Note:** The server-side rendering engine lacks most browser-specific JS functionality (except for the things React4xp has specifically polyfilled).

**Referring to browser-specific functionality during server-side rendering will usually throw an error in the server log** and break the rendering.

This is easily prevented by checking the global namespace for functionality that only exists in a browser, such as `window.navigator`.

And there we have it: **our infinite scroller**!

Rebuild, refresh the preview of *MovieSite*, and instead of clicking, just scroll down - the page should auto-refresh to add new content until the very end of time or the end of your added movies, whichever comes first.

## Other resources and tools

> **Tip:** This section is not a vital part of the rest of this or the next chapter. Feel free to skip it and miss out.

To dive deeper into Guillotine and graphQL, you can always check out the [Intro](https://developer.enonic.com/docs/intro), or our [Developer 101 tutorial](https://developer.enonic.com/docs/developer-101).
