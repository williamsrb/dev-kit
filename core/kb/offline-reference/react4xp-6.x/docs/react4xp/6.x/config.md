<!-- src:https://developer.enonic.com/docs/react4xp/6.x/config generated:2026-07-30T04:18:15Z format:llm-dense react4xp-6.x -->
#DOC docs/react4xp/6.x/config.md

# Application config

Standard configuration options for your React4XP-based application

Like any other Enonic application, you may provide a standard configuration file, and place it in the XP config folder. i.e. $XP_HOME/config/.cfg

## R4XP tuning

The React4XP starter provides a few standard configuration options (in addition to the configuration options you define yourself). Here they are:

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
| ****2** | Set `ssr` to `false` in order to disable SSR by default. This setting can be overridden on a per-component basis in your code. |
| ****3** | `maxThreads` caps how many [server-side renderings](docs/react4xp/6.x/ssr.md) React4XP performs at the same time. Each rendering runs on a single thread, so this sets concurrency, not the speed of an individual rendering. Defaults to the number of processor cores available to XP. Be careful about setting this option: each concurrent worker keeps its own copy of the compiled assets in memory, so a high value costs memory and adds [warmup](docs/react4xp/6.x/ssr.md#warmup) work. |
| ****4** | React4xp creates a globals bundle, which MUST contain all assets NEEDED to render server-side. By default it contains react and react-dom, but more assets can be added. By default the globals bundle is also provided to the client-side, setting `serveGlobals` to `false` will prevent globals from being delivered to the client.   @@BLOCK0@@ |
| ****5** | `urlType` may optionally be used to force generation of `absolute` URLs. The default value is `server`   @@BLOCK1@@ |
