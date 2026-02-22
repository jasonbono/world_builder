# API Redesign

## Motivation

Cleanly separate three primitives: **control** (act), **evolve** (advance), **measure** (observe). No endpoint does double duty. The only way to gain information from the world is `/observe`, making observation count the natural metric for discovery difficulty.

## New API

### POST /reset
Resets state to initial conditions. Returns nothing.

### POST /act
Sets the action. Does NOT advance time. Returns nothing.
Body: `{"action": "A", "value": <float>}`

Calling act multiple times before advancing overwrites — only the last value matters.

### POST /advance
Advances time by N steps. Returns nothing.
Body: `{"steps": <int>}`

### GET /observe
Reads current state. Does NOT advance time. Returns:
`{"x": <float>, "t": <int>}`

### Removed
- `/history` — removed. Agent must track its own data.
- `/observe` no longer takes a steps parameter or advances time.

## Changes from old API

| Behavior | Old | New |
|----------|-----|-----|
| `/reset` return | `{x, t}` | nothing |
| `/act` return | `{before, after}` | nothing |
| `/act` side effect | sets action + advances 1 tick | sets action only |
| `/advance` return | `{x, t}` | nothing |
| `/observe` | advances N ticks, returns N states | reads current state, no time change |
| `/history` | full log | removed |

## Metric

**Observation count** = number of `/observe` calls the agent makes. This is the measure of how much information the agent needed from the world.
