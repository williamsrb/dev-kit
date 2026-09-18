<!-- src:https://developer.enonic.com/docs/platform/7.x/framework/events generated:2026-07-24T21:10:20Z format:llm-dense xp:7.x -->
#DOC framework/events.md

# Events

Send and listen to local or cluster wide events

## Introduction

The XP framework enable developers to create and/or listen to events. Events may be local (within a single server) or cluster wide (distributed to all servers within a cluster). In addition to application specific events, XP itself produces a range of standard events.

## Use cases

The use cases for events are limitless, but the most common are:

- Cache invalidation

- Notifications (i.e. notify clients connected to any server in the cluster via Websocket)

- Job triggering

## Implementation

For implementation details, please visit the [event library](/docs/platform/7.x/api/lib-event) documentation.
