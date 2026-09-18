<!-- src:https://developer.enonic.com/docs/cms/stable/pages/indexing generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/cms/stable/pages/indexing.md

# Component indexing

## Introduction

Like other schemas, component form values are automatically indexed, including adding text values to the `_alltext` field. Additionally, fields like the component name also get indexed.

## Usage

To provide a predictable way of searching components, they are persisted and indexed as a flat list. Below is an example of how the components of a page may be persisted:

Sample persisted component structure

```JSON
"components": [
  {
    "type": "page",
    "path": "/",
    "page": {
      "descriptor": "com.enonic.app.superhero:default",
      "customized": true
    }
  },
  {
    "type": "part",
    "path": "/main/0",
    "part": {
      "descriptor": "com.enonic.app.superhero:featured"
    }
  },
  {
    "type": "fragment",
    "path": "/main/1",
    "fragment": {
      "id": "5499dfd8-67c2-4712-a0d9-554b9817b4ad"
    }
  },
  {
    "type": "layout",
    "path": "/main/2",
    "layout": {
      "descriptor": "com.enonic.app.superhero:two-column"
    }
  },
  {
    "type": "part",
    "path": "/main/2/left/0",
    "part": {
      "descriptor": "com.enonic.app.superhero:posts-list"
    }
  },
  {
    "type": "part",
    "path": "/main/2/right/0",
    "part": {
      "descriptor": "com.enonic.app.superhero:search-form",
      "config": {
        "com-enonic-app-superhero": {
          "search-form": {
          }
        }
      }
    }
  },
  {
    "type": "part",
    "path": "/main/2/right/1",
    "part": {
      "descriptor": "com.enonic.app.superhero:recent-posts",
      "config": {
        "com-enonic-app-superhero": {
          "recent-posts": {
          }
        }
      }
    }
  },
  {
    "type": "part",
    "path": "/main/2/right/2",
    "part": {
      "descriptor": "com.enonic.app.superhero:categories",
      "config": {
        "com-enonic-app-superhero": {
          "categories": {
            "showPostCount": false,
            "showHierarchy": false
          }
        }
      }
    }
  }
]
```

Thanks to this persistence model, it is possible to predictably query for the presence of specific component types i.e. via `components.part.descriptor` or for component form values i.e. via `components.part.config...`.

## Query examples

### Find pages using a specific part

```graphql
{
  guillotine {
    queryDsl(
      query: {
        term: {
          field: "components.part.descriptor",
          value: { string: "com.enonic.app.superhero:featured" }
        }
      },
      first: 20
    ) {
      _id
      _path
      displayName
    }
  }
}
```

### Find pages using a specific fragment

```graphql
{
  guillotine {
    queryDsl(
      query: {
        term: {
          field: "components.fragment.id",
          value: { string: "5499dfd8-67c2-4712-a0d9-554b9817b4ad" }
        }
      }
    ) {
      _id
      _path
      displayName
    }
  }
}
```

### Find pages with a specific part config value

Component configs are addressable by the same flat path, with dots replaced for special characters. For example, the `showPostCount` flag on the `categories` part from `com.enonic.app.superhero`:

```graphql
{
  guillotine {
    queryDsl(
      query: {
        term: {
          field: "components.part.config.com-enonic-app-superhero.categories.showPostCount",
          value: { boolean: true }
        }
      }
    ) {
      _id
      _path
      displayName
    }
  }
}
```

> **Tip:** When excluding fragments from customer-facing search results, filter out the `portal:fragment` content type as well — fragment contents are indexed on the fragment itself, not on the pages that reference them.
