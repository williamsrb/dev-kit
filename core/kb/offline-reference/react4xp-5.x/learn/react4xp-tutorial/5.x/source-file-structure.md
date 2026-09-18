<!-- src:https://developer.enonic.com/learn/react4xp-tutorial/5.x/source-file-structure generated:2026-07-30T04:16:10Z format:llm-dense react4xp-5.x -->
#DOC learn/react4xp-tutorial/5.x/source-file-structure.md

# Defining your own source structure

## Lesson overview

So far, every time we’ve referenced a *.tsx* react component from React4xp in a controller, we’ve used a `component` object in the *entry* argument of `render`. This is just a shortcut, and it depends on an "XP-conventional" naming regime to work: the *.tsx* source file must be in the same folder as the controller, and have the same name.

It doesn’t have to be that way. In this example, we’ll take a look at which react components are available to `render` - called **entries** in React4xp - and how to reference them, whatever they’re called, and wherever they’re located.

## Entries and locations

For react components to be available to React4xp the way we’ve seen so far, their **TSX/JSX source files must be located in certain folders** where React4xp is looking for them and auto-compiles them.

When they are located where they should be (and export a `props⇒component` function), those react components are called **entries** ([full reference](learn/react4xp-tutorial/5.x/appendix/entries.md)).

### 1: Below *site/*

Below the folder *src/main/resources/site/*, all source files with the extension *.jsx* are detected at compile-time and available as entries to React4xp. If you take the **path relative to *resources/*** and the file name without the extension, you get a string that can be used to point React4xp to that react component:

- `"site/parts/hello-react/hello-react"` → *src/main/resources/site/parts/hello-react/hello-react.tsx*

- `"site/parts/color/color"` → *src/main/resources/site/parts/color/color.tsx*

- `"site/parts/color/differentEntry"` → *src/main/resources/site/parts/color/differentEntry.tsx*

…​etc.

These strings are called **jsxPaths** in React4xp, and they can be used directly in controllers as the *entry* argument. For example in the [*color* Part controller](learn/react4xp-tutorial/5.x/pages-parts-and-regions.md#color_part_controller) from before:

site/parts/color/color.ts

```typescript
render(
    component,
    props,
    request,
    options
);
```

…​is equivalent to:

```typescript
render(
    "site/parts/color/color",
    props,
    request,
    options
);
```

And so on. Calling the *.tsx* source file something else, or having it in a different folder, is fine as long as you refer to it correctly like this.

> **Warning:** *jsxPaths* are name strings, not relative paths! You can’t refer to *color.tsx* from *color.ts* as `"color"` or `"./color"` etc.

> **Tip:** If you look at the rendered HTML output in the page source, you can see React4xp using the jsxPaths to refer to the compiled assets from the client - even if you used the `component` object in the *entry* argument.

> **Tip:** All the *entries* in your project are listed with their *jsxPath* after compilation, in *build/resources/main/r4xAssets/entries.json*.

### 2: Below *react4xp/*

If you just want to keep your react components out of the regular XP file structure in *site/* and be independent of the structure of Parts, Pages, etc, the folder *src/main/resources/react4xp/* is meant for that. Here’s how (assuming you’re using [the starter](https://market.enonic.com/starters/react4xp-starter) or generally following [the recommended react4xp setup pattern](https://github.com/enonic/lib-react4xp/blob/master/README.adoc#setup-option-2-using-react4xp-in-an-existing-project)):

Open *react4xp.config.js* in the project root, and look for the property `entryDirs`. This is a (comma-separated) list of folder names **relative to the *react4xp/* folder**. React4xp comes with a built-in suggestion here: `entryDirs: ['entries']`. This means that all *.tsx* source files below *src/main/resources/react4xp/entries* will become entries: react components available to React4xp.

They will get a ***jsxPath* relative to the closest *entryDirs* folder**.

So for example if `entryDirs = entries`, then the closest *entryDirs* folder is *src/main/resources/react4xp/entries*, and any XP controller can render *src/main/resources/react4xp/entries/subFolder/myEntry.tsx* like this:

```typescript
React4xp.render(
    "subFolder/myEntry",
    props,
    request,
    options
);
```

> **Tip:** **Under the *site/* folder, entry source files must have the extension *.tsx***. This is because regular XP source files can have *.ts* extension, and must be separated since the compilation and handling is very different. However, **under the *entryDirs* folder(s), entries can have *.ts* and *.js* extensions too!**

> **Note:** React4xp doesn’t currently separate between different *entryDirs*, they behave as one. So if `entryDirs = entries,moreEntries` then *react4xp/entries/foo/bar.tsx* and *react4xp/moreEntries/foo/bar.tsx* will get the same *jsxPath*: `"foo/bar"`. Beware of **namespace collisions**; you won’t be able to refer to both.

### 3: Anywhere else

The *entryDirs* are paths relative to *src/main/resources/react4xp/*, so just use relative *entryDirs* if you need entries outside of that.

For example, say you’ve added an NPM package *externalComponents* with react components in a *comps* subfolder, and you want to use them as entries. Simply add it to *entryDirs*:

react4xp.config.js

```js
entryDirs:['entries','../../../../../node_modules/externalComponents/comps']
```

(Or replace *entries* if you’re not using it, of course)

## Further reading

If you want a deeper dive into details before moving on, here’s more about [entries](#appendix/) and the [jsxPaths](learn/react4xp-tutorial/5.x/appendix/jsxpath.md) that point React4xp to them.

Okay, next example lessons!
