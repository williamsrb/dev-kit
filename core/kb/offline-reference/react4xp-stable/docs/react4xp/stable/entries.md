<!-- src:https://developer.enonic.com/docs/react4xp/stable/entries generated:2026-07-30T04:17:59Z format:llm-dense react4xp-7.x -->
#DOC docs/react4xp/stable/entries.md

# Entries

## What is an entry?

React4xp is not limited to a single "React app", it may actually support multiple React instances on a single page.

In. React4XP we call these `entries`. It’s actually a webpack term, but in React4xp we use the word entry for **a React component that can be called by React4xp** from an XP script file. They are the only react files that React4xp can use directly.

Think of entries as **"bridge elements"**:

A mental model:

(Here’s a [cheat sheet](docs/react4xp/stable/entries/cheatsheet.md). See also chunks, for a [complete picture](docs/react4xp/stable/chunks.md#entries_and_chunks))

On the XP/server side, you have the server-side functions with their backend XP flow, logic and XP lib imports. Entries are the beginning of the frontend side (although the same code is also used for serverside-rendering): they do regular frontend-style ES6 logic and can **import** stuff from NPM/node_modules, your own logic, nested react components, whatever - even other entries.

## How to make an entry

Entries are pretty much just standard TSX/JSX files, but they must follow **two requirements** (another [cheat sheet](docs/react4xp/stable/entries/howto.md)):

- is located in a folder below one of the **entryDirs** folders listed in *react4xp.config.js* - the starter uses ***react4xp/entries/*** (see also [jsxPath](#jsxPath)). In legacy XP 7 apps, entries could also be placed below ***/site/*** - XP 8 apps no longer have this folder (it was renamed to `cms/`, which is not scanned for entries),

- and **default-exports a function**: `props?⇒reactComponent` - a function that *may* take a `props` argument (serializable JS object: no functions) and *must* return a react component.

> **Note:** **Important:**

There should be no call to `React.render` or `ReactDOM.render` in an entry (or a compiled entry or dependency bundle - keep an eye on your imports). React4xp will handle that call in the right context.

If your entry uses react hooks or it’s a react class component, read [Classes and hooks in entries](#classes-and-hooks) below.

## Entries, assets and react apps

React4xp handles them in build-time and runtime: locates entries, compiles each entry into its own **entry asset** (under */build/resources/main/r4xAssets*). React4xp’s render methods also generate page contributions that make sure these assets are served to the client.

For example, the starter’s entry *react4xp/entries/App.tsx* is compiled into the entry asset *App.js*. Add a second entry *react4xp/entries/shop/Cart.tsx*, and it becomes *shop/Cart.js*: each entry gets its own asset, named from its path below the [entryDirs](docs/react4xp/stable/build.md#entryDirs) folder - see [jsxPath](#jsxPath).

When rendered (whether it’s by using `.render` or a pair of `renderBody`/`renderPageContributions` in the [custom flow](docs/react4xp/stable/library.md#react4xp_object)), each entry will become not only assets of their own, but **independent root level react apps** in the browser memory! Good to know if you display more than one entry on a page - which you can, but you might also consider using just one entry for the root, and multiple imports in it.

## Classes and hooks in entries

If your entry is a [react class component](https://reactjs.org/docs/react-component.html) or a functional component that uses [react hooks](https://reactjs.org/docs/hooks-intro.html) (and possibly other specific react features?), the default-export must be correctly wrapped.

### JSX entry examples

- **Straight functional component entry:** straight export is okay.

Header.jsx

```javascript
function Header(props) {
    return <h1>{props.text}</h1>;
};

// This is fine:
export default Header;

// An extra wrapped layer would work too. But it's usually not necessary:
//
// export default (props) => <Header {...props} />;
```

- **Class component entry:** needs a JSX-wrapped export.

Welcome.jsx

```javascript
class Welcome extends React.Component {
  render() {
    return <p>Hello, {this.props.name}</p>;
  }
}

// Bad:
// export default Welcome;

// Good:
export default props => <Welcome {...props} />;
```

- **Functional component that uses hooks:** needs a JSX-wrapped export.

HookButton.jsx

```javascript
function HookButton() {
  const [count, setCount] = useState(0);

  return (
      <button onClick={() => setCount(count + 1)}>
        You clicked {count} times
      </button>
  );
}

// Bad:
// export default HookButton;

// Good:
export default props => <HookButton {...props} />;
```

### Why?

The reason for this has to do with how the components are compiled, and that the runtime-client trigger call in the browser *uses the default-export directly, in vanilla JS* - so everything that’s exported from an entry must be ready and compiled for vanilla-JS usage.

In the examples above it would be equivalent to `Welcome(props);` and `HookButton(props);`. `Welcome` is not compiled to a function that can be called like this, and the pure `HookButton` function is not really a *functional component* (before it’s called as a component, the way we do when it’s wrapped), just a regular JS function - so the straight export [breaks the rules of hooks and you get an error](https://reactjs.org/warnings/invalid-hook-call-warning.html).

## What is the jsxPath?

Each entry is identified by its own *jsxPath*.

Short and brutal: the jsxPath is a name string generated from the path and filename of the compiled asset after building, relative to */build/resources/main/r4xAssets/* - without file extension.

## From source file location to jsxPath

During development though, these 3 rules are probably easier:

- If you use `portal.getComponent()` to insert a component object (like `entry` in the [React4XP tutorial](https://developer.enonic.com/learn/react4xp-tutorial)), you can ignore the jsxPath and let the component object do the job: `React4xp.render` will use it to look for an entry with **the same name, in the same folder**, as a part/page/layout implementation.

But if you need to access an entry with a particular name or from a different folder (from anywhere in the compiled JAR, actually), here’s **how to find the jsxPath of an entry**:

- Using the setup from the starter, put your entries under *src/main/resources/* ***react4xp/entries***. Then the jsxPath (and compiled-asset path) will be relative to */entries/*.

Actually, you can control this with the `entryDirs` property in your local [*react4xp.config.js*](https://github.com/enonic/enonic-react4xp/blob/master/examples/react4xp.config.js). The starter has added `entryDirs:['entries']` here, but this is a comma-separated list of folder names relative to *src/main/resources/react4xp/*. Remember, if you add more entryDirs or replace `entries`, the jsxPaths will always be relative to those new entryDirs, so beware of name collisions.

- **For example:** add `../myComponents` to entryDirs: `entryDirs:['entries','../myComponents']`. Since entryDirs and `../` are relative to *src/main/resources/react4xp/*, the new entry source folder is *src/main/resources/myComponents/*. Now new TSX/JSX files can be put there, and get a jsxPath relative to that. So the entry *src/main/resources/myComponents/* ***app/myEntry.jsx*** will get the jsxPath `"app/myEntry"`, and will be compiled to this entry asset: */build/resources/main/r4xAssets/app/myEntry.js*.

- In legacy XP 7 apps only: if an entry’s source file is a TSX/JSX under */src/main/resources/* ***site/***, the jsxPath is the source file’s path relative to */src/main/resources/* - unix-style and without file extension.

So the jsxPath will start with `site/…​` etc (and the asset will be compiled into a folder below */build/resources/main/r4xAssets/* ***site/***, and so on). XP 8 apps have no *site/* folder, so this rule no longer applies to them.

## Overview in entries.json

If you’re ever unsure: after building, the **jsxPaths of all the available entries** are stored in *build/resources/main/r4xAssets/entries.json*.

This file is generated by webpack during build. It’s also used by the runtime, so it **should not be deleted or edited**!

## Name, not path

JsxPaths are not actually file system paths, but **static name strings**. So avoid shortcuts and relative references like `../`, etc.

See also: [chunks](docs/react4xp/stable/chunks.md).
