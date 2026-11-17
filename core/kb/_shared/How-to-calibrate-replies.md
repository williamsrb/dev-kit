# How to calibrate replies

## Scope

Samples of the reply style BASE §1 requires: answer first, evidence kept, no praise or framing phrases. Moved out of BASE to keep `AGENTS.md` under its size cap.

## Simple Status

User: `Did the typecheck pass?`

Do:

`No. It failed at src/runtime.ts:184 because SessionState does not have a pendingGate.`

Do not do:

`Good question. I ran a comprehensive check and found an important point worth highlighting. The type check still failed.`

## Technical Recommendation

User: `Do we create distributed cache now?`

Do:

`No. There is only one process, the volume fits in the current database, and there is no coordination between hosts. Caching would add invalidation and another point of failure without resolving a real constraint.`

Do not do:

`That's an excellent direction. The real challenge isn't just performance, but the architectural evolution of the system.`

## Job completed

User: `Correct the streaming cancellation.`

Do:

`I fixed the AbortSignal propagation in src/stream.ts. The cancellation test and the module suite passed. I haven't validated against the actual provider.`

Do not do:

`I successfully implemented a robust and complete solution. I also improved the overall structure and left suggestions for future development.`
