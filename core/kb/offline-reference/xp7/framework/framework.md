<!-- src:https://developer.enonic.com/docs/platform/7.x/framework generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC framework/framework.md

# Enonic Framework

Enonic applications are built using Enonic’s server-side JavaScript controller framework. Applications are executed by the [XP runtime](/docs/platform/7.x/runtime), which means it can take advantage of it’s modular architecture and get access to all platform [APIs](/docs/platform/7.x/api) as well as access management and IDprovider features.

Here are some highlights:

- **Integrated** with the Enonic applications runtime. Ship and execute server-side TypeScript/JavaScript.

- **Compatible** across all releases of XP within a major version i.e. 7.x.x

- **Supports** HTTP request-response, clustered events and and background task execution

- **Multithreaded** for ease of development and effective use of multi-core CPU arcitectures

- **Fast and performant** as JavaScripts are compiled and adapted to the underlying architecture.

- **Based on the [CommonJS module specification](https://wiki.commonjs.org/wiki/Modules/1.1)**

- **Powered by the GraalVM** Unlike most JavaScript frameworks, this is not powered by Node.js, but uses the Nashorn scripting engine. Next major release of XP is expected to be using GraalJS.
