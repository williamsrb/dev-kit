<!-- src:https://developer.enonic.com/docs/platform/stable/endpoints generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/platform/stable/endpoints.md

# APIs and Endpoints

Enonic XP exposes APIs and functionality through multiple HTTP endpoints, each serving specific purposes.

## Web (Port 8080)

The gateway for all client interactions, including APIs, Admin and the Site service. See [Web](docs/platform/stable/endpoints/web.md).

## Management API (Port 4848)

Programmatic access to administrative and operational functions, commonly used together with Enonic CLI. See [Management API](docs/platform/stable/endpoints/management.md).

## Statistics API (Port 2609)

Real-time metrics and monitoring data about the XP instance, used for health checks and performance monitoring. See [Statistics API](docs/platform/stable/endpoints/statistics.md).

> **Tip:** The default ports can be overridden via `com.enonic.xp.web.jetty.cfg`
