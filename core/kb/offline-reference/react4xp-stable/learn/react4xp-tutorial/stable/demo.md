<!-- src:https://developer.enonic.com/learn/react4xp-tutorial/stable/demo generated:2026-07-30T04:17:59Z format:llm-dense react4xp-7.x -->
#DOC learn/react4xp-tutorial/stable/demo.md

# React4XP Demo

Spin up your own React4XP personal demo in the cloud, or on your local machine.

Below: Choose to run the demo in Enonic Cloud, or on your local machine.

> **Tip:** To learn the details behind how this front-end was built, head on to the [first chapter](learn/react4xp-tutorial/stable/setup.md) of the tutorial instead.

## Alternative 1 - Enonic Cloud

Follow these steps to get the demo up and running on our Free plan:

- **Sign up** for [Enonic cloud](https://console.enonic.com/)

Verify your e-mail and create the account

- **Create a new solution**

Use the template called `Headless Movie DB`, and complete the setup.

- **Link the front-end to your content**

Once the solution is ready, launch `XP Admin` → `Content Studio`.

Edit the `Headless Movie DB` site, add the `React4XP Demo` application and press **Save**

You should now see the new front-end in Content Studio.

- Publish the changes

**Optionally expose the site on a public URL** by following the steps below:

- Select `Ingresses` from the main menu and click **Create**

- Give it a suitable name, i.e. `moviedb`

- Set the target to `/site/hmdb/master/hmdb`

- Accept creating a new domain, and set the path to `/`

- Leave IDprovider empty and click **Create** on the final step

- Visit the Ingress link to see the live site.

> **Tip:** If the live site is showing the default preview of Headless Movie DB, you have not published your changes to the site.

Congratulations, you just deployed a live a React site powered by Enonic! 🚀

## Alternative 2 - Local instance

Follow the steps below to build and run the demo on a local Enonic developer environment:

- **Install Enonic CLI** if you have not already done this

```
npm install -g @enonic/cli
```

- **Create a new sandbox and start it** by running this command in your terminal:

```
enonic sandbox create r4xpdemo -t hmdb -f
```

- **Link the front-end with your content**

Launch `XP admin` → `Content Studio`.

Edit the `Headless Movie DB` site, add the `React4XP Demo` application and press **Save**

> **Tip:** The live version of the site can be found on [http://localhost:8080/site/hmdb/master/hmdb](http://localhost:8080/site/hmdb/master/hmdb)

Congratulations, you just built a React site powered by Enonic! 🚀
