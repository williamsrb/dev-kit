<!-- src:https://developer.enonic.com/learn/react4xp-tutorial/stable/setup generated:2026-07-30T04:17:59Z format:llm-dense react4xp-7.x -->
#DOC learn/react4xp-tutorial/stable/setup.md

# Setting up the developer environment

Set up the developer environment, create, build, and deploy and application.

## Install Enonic CLI

The Enonic CLI (Command Line Interface) is an essential tool for developing with Enonic.

If you have `npm` on your device, run this command:

```
npm install -g @enonic/cli
```

If not, here are some [alternative ways to install Enonic CLI](https://developer.enonic.com/start)

To verify that the CLI has been installed, run `enonic -v`. This should output the version of your installed CLI. To see all available options, simply run `enonic`.

> **Tip:** To upgrade, use `enonic latest`. If there are new versions you will see instructions on how to upgrade.

## Create a sandbox

We’re going to need a sandbox for this tutorial:

**Create a sandbox** called `r4xptutorial` by running this command in your terminal:

```
enonic sandbox create r4xptutorial -t hmdb -f
```

This will create and start a sandbox containing relevant applications, including the Headless Movie DB sample dataset.

## Create application

From a **new terminal window**, run the following command to create the application that will contain the React4XP front-end.

```
enonic project create my.first.r4xp -r starter-react4xp -s r4xptutorial -f
```

> **Note:** This command creates an app named `my.first.r4xp`. It uses the [React4xp starter Github repo](https://github.com/enonic/starter-react4xp) as a starter, and links it to the `r4xptutorial` sandbox.

## Project structure

You will now get a typical Enonic app file structure. Below we’re highlighting some of the most interesting files and folders:

```files
package.json
react4xp.config.js (1)
src/
  main/
    resources/
      react4xp/ (2)
        dataFetcher.ts (3)
        componentRegistry.tsx (4)
        components/
        entries/
          App.tsx (5)
      cms/ (6)
        app.ts (7)
      types/ (8)
```

| ****1** | React4XP settings |
| --- | --- |
| ****2** | React components must be placed within this folder |
| ****3** | Fetches props for CMS components |
| ****4** | Mapping React components to CMS component |
| ****5** | Main React component |
| ****6** | Optionally place CMS schemas here |
| ****7** | Bootstrapping controller |
| ****8** | TypeScript types (optional) |

## Dev mode

Assuming you did not change any of the default values when creating the app, run the following commands:

```
cd r4xp
enonic dev
```

This will perform an initial build, and deploy the application to the sandbox.

Once you see the following lines, the application has been built and deployed to the sandbox:

```
BUILD SUCCESSFUL in 1m 27s
8 actionable tasks: 7 executed, 1 up-to-date
```

> **Tip:** In the sandbox log, this shows that app is running:

2019-04-09 13:40:40,765 INFO ... Application [my.first.r4xp] installed successfully

Because the sandbox is running in dev mode, any changes to the code within your app will instantly be picked up.

> **Tip:** Dive deeper by learning more about React4XP’s [build system](docs/react4xp/stable/build.md).

In the next chapter, you’ll get familiar with [basic React4XP rendering](learn/react4xp-tutorial/stable/hello.md).
