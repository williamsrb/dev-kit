<!-- src:https://developer.enonic.com/learn/react4xp-tutorial/5.x/setup generated:2026-07-30T04:16:10Z format:llm-dense react4xp-5.x -->
#DOC learn/react4xp-tutorial/5.x/setup.md

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
enonic sandbox create r4xptutorial -t essentials -f
```

This will create and start a sandbox containg `essential` applications.

## Create the app

From a **new terminal window**, run the following command to create the application.

```
enonic project create my.first.r4xp -r starter-react4xp -b 5.x -s r4xptutorial -f
```

> **Note:** This command creates an app named `my.first.r4xp`. It uses the [React4xp starter Github repo](https://github.com/enonic/starter-react4xp) as a starter, and links it to the `r4xptutorial` sandbox.

## Project structure

You will not get a typical Enonic project structure. The biggest news are `react4xp.config.js` and the folder `src/main/resources/react4xp/`.

```files
build.gradle (1)
package.json
react4xp.config.js (2)
src/
  main/
    resources/
      react4xp/ (3)
        entries/
        shared/
      site/ (4)
```

| ****1** | Core build files, will contain references to `lib-react4xp` library and the `@enonic/react4xp` npm package. |
| --- | --- |
| ****2** | React4xp [build configuration](learn/react4xp-tutorial/5.x/appendix/build.md), here you may add additional globals and tune common React4xp properties. |
| ****3** | Optionally place React components in these folders. They will be covered in detail throughout the tutorial. |
| ****4** | Standard site/ folder |

> **Tip:** The short takeaqay is that you can put your TSX/JSX source files in `react4xp/entries/` or witin the `site/` structure directly.

## Start building

Assuming you did not change any of the values when creating the app, run the following commmands:

```
cd r4xp
enonic dev
```

This will build and deploy the application to your sandbox.

> **Note:** Look for a line like this in the sandbox log to verify that the app has started:

2019-04-09 13:40:40,765 INFO ... Application [my.first.r4xp] installed successfully

Because the sandbox is running in dev mode, any changes to the code wihin your app will instantly be picked up.

Now you’re ready to get started with the first lesson: [Hello React](learn/react4xp-tutorial/5.x/hello-react.md).
