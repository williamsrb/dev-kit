<!-- src:https://developer.enonic.com/learn/react4xp-tutorial/5.x/appendix/entries generated:2026-07-30T04:16:10Z format:llm-dense react4xp-5.x -->
#DOC learn/react4xp-tutorial/5.x/appendix/entries.md

# Entries

## What is an entry?

React4xp is structured around *entries*.

It’s actually a webpack term, but in React4xp we use the word entry for **a React component that can be accessed by React4xp** in an XP controller. They are the *only* react files that React4xp can use directly.

Think of entries as **"bridge elements"**:

A mental model:

(Here’s a [cheat sheet](learn/react4xp-tutorial/5.x/appendix/entries_cheatsheet.md). See also chunks, for a [complete picture](learn/react4xp-tutorial/5.x/appendix/chunks.md#entries_and_chunks))

On the XP/server side, you have the controllers with their backend XP flow, logic and XP lib imports. Entries are the beginning of the frontend side (although the same code is also used for serverside-rendering): they do regular frontend-style ES6 logic and can **import** stuff from NPM/node_modules, your own logic, nested react components, whatever - even other entries.

## How to make an entry

Entries are pretty much just standard TSX/JSX files, but they must follow **two requirements** (another [cheat sheet](learn/react4xp-tutorial/5.x/appendix/entries_howto.md)):

- is located either in a folder either below ***/site/*** or below one of the **entryDirs** folders listed in *react4xp.config.js* (see also [jsxPath](learn/react4xp-tutorial/5.x/appendix/jsxpath.md)),

- and **default-exports a function**: `props?⇒reactComponent` - a function that *may* take a `props` argument (serializable JS object: no functions) and *must* return a react component.

> **Note:** **Important:**

There should be no call to `React.render` or `ReactDOM.render` in an entry (or a compiled entry or dependency bundle - keep an eye on your imports). React4xp will handle that call in the right context.

If your entry uses react hooks or it’s a react class component, read [Classes and hooks in entries](#classes-and-hooks) below.

## Entries, assets and react apps

React4xp handles them in build-time and runtime: locates entries, compiles each entry into its own **entry asset** (under */build/resources/main/r4xAssets*). React4xp’s render methods also generate page contributions that make sure these assets are served to the client.

For example, early in this tutorial we’ve seen the entries *hello-react.jsx* and *color.jsx*, they are compiled into the assets *hello-react.js* and *color.js*.

When rendered (whether it’s by using `.render` or a pair of `renderBody`/`renderPageContributions` in the [custom flow syntax](learn/react4xp-tutorial/5.x/custom-flow-syntax.md)), each entry will become not only assets of their own, but **independent root level react apps** in the browser memory! Good to know if you display more than one entry on a page - which you can, but you might also consider using just one entry for the root, and multiple imports in it.

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

In the examples above it would be equivalent to `Welcome(props);` and `HookButton(props);`. `Welcome` is not compiled to a function that can be called like this, and the pure `HookButtons` function is not really a *functional component* (before it’s called as a component, the way we do when it’s wrapped), just a regular JS function - so the straight export [breaks the rules of hooks and you get an error](https://reactjs.org/warnings/invalid-hook-call-warning.html).
