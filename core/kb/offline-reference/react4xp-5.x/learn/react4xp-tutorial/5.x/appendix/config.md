<!-- src:https://developer.enonic.com/learn/react4xp-tutorial/5.x/appendix/config generated:2026-07-30T04:16:10Z format:llm-dense react4xp-5.x -->
#DOC learn/react4xp-tutorial/5.x/appendix/config.md

# Application config

Standard configuration options for your React4XP-based application

Like any other Enonic application, you may provide a standard configuration file, and place in in the XP config folder. i.e. $XP_HOME/config/.cfg

## R4XP tuning

The React4XP starter provies a few standard configuration options (in addition to configuration options you define yourself). Here they are:

myr4xpapp.cfg

```properties
react4xp.hydrate = (true|false) (1)
react4xp.ssr = (true|false) (2)
# react4xp.ssr.maxThreads = (int) (3)
react4xp.serveGlobals = true (4)
react4xp.urlType = server|absolute (5)
```

| ****1** | Set `hydrate` to `false` to disable hydration |
| --- | --- |
| ****2** | Set `ssr` to `false` in order to disable SSR by default. This setting can be overridden on a per-component basis in your code.   @@BLOCK0@@ |
| ****3** | `maxThreads` specifies the number of ([renderers](learn/react4xp-tutorial/5.x/appendix/api.md#renderers)) used for simultaneous SSR requests. Defaults to the number of processors cores available to XP. Be careful about setting this option |
| ****4** | React4xp creates a globals bundle, which MUST contain all assets NEEDED to render server-side. By default it contains react and react-dom, but more assets can be added. By default the globals bundle is also provided to the client-side, setting `serveGlobals` to `false` will prevent globals from being delivered to the client.   @@BLOCK1@@ |
| ****5** | `urlType` may optionally be used to force generation of `absolute` URLs. The default value is `server`   @@BLOCK2@@ |
