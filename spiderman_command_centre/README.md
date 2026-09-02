# Team Spade — Spider-Man Command Centre

A terminal-based control room through which Spider-Man's response system
is operated. Pure Python, no database, no APIs, no web framework —
everything lives in memory for the duration of the run, as required.

## Running it

```
python3 main.py
```

## Running the tests

```
python3 -m unittest discover -s tests -v
```
27 tests, all passing — covering every service, every status transition
(valid and invalid), empty-state edge cases, and the mission-scoring
formula against the worked example from the spec.

## Architecture

The brief asks for interface/orchestration to be kept separate from the
underlying incident, priority and mission logic. That's the whole
structure here:

| File                     | Responsibility                                            |
|---------------------------|------------------------------------------------------------|
| `models.py`               | Data shapes only — `Severity`, `Status`, `Incident`         |
| `locations.py`            | HQ + location coordinates, distance calculation             |
| `incident_service.py`     | Create/store/query incidents, enforce status transitions    |
| `priority_service.py`     | Priority scoring and ordering                                |
| `mission_service.py`      | Mission scoring, "next mission" recommendation               |
| `dashboard_service.py`    | Aggregate counts for the dashboard                            |
| `cli_utils.py`            | **Only** input reading/validation — never crashes; `prompt_choice` is the single reusable "pick a number from a menu" primitive everything else is built on |
| `display.py`              | **Only** terminal formatting/printing — no raw objects dumped |
| `main.py`                 | Menu loop — orchestration only, contains zero business rules  |
| `tests/test_services.py`  | Unit tests against the service layer directly (no I/O)        |

`main.py` never computes a score or decides whether a status change is
legal — it just reads a choice, calls a service, and hands the result to
`display.py`. That's what "stay in your lane" means here.

## Menu-driven, not free-typed

Every choice in this app is a numbered decision, not a typed field,
wherever that's genuinely possible:

* **Incident type** — pick from a menu (Fire, Robbery, Assault, Hostage
  Situation, Bombing Threat, Vehicle Collision, Chemical Spill, or
  "Other" to type a custom one).
* **Location** — pick from the known-locations menu, or "Other" to type
  a new one.
* **Severity** and **description** — menu of presets ("Custom" for
  description).
* **Which incident to update** — picked from a numbered list of
  currently-updatable incidents, never typed by ID. This also removes
  the whole class of "typo'd an incident ID" errors.
* **What status to move an incident to** — the menu only ever shows the
  status(es) that incident is actually allowed to move to next (e.g. a
  `REPORTED` incident only offers `IN_PROGRESS`; a `RESOLVED` incident
  offers nothing, and the operator is told why). An invalid transition
  literally can't be selected — `incident_service.update_status` still
  re-validates it as a safety net in case the two ever drift apart.
* **Reporting an incident** ends with a review screen and an explicit
  Confirm/Cancel choice before anything is saved.
* **Exiting** asks for confirmation (Yes/No) rather than quitting
  immediately on "7".

The only remaining free-text entry points are the ones a fixed menu
genuinely can't cover: an "Other" incident type/location, a "Custom"
description, and the exact headcount for people affected (a menu of
number ranges would lose the precision the priority formula needs).
Every one of those is still validated (non-empty text, non-negative
whole number) and re-prompts on bad input instead of crashing.

## Design decisions the spec left open (and why)

**Priority score** — `severity_weight + min(people_affected, 20)`, where
severity weights are LOW=10, MEDIUM=20, HIGH=30, CRITICAL=40. Severity
dominates, but a mass-casualty incident can still push a lower-severity
report up. The 20-point cap stops one huge number from swamping severity
entirely. This exactly reproduces the worked example in the spec
(HIGH + 17 people → 30 + 17 = 47).

**Mission score** — `max(0, priority_score - distance_km)`. Closer, more
severe incidents rank highest; the score can't go negative. This exactly
matches the spec's worked example: priority 47, distance 6 km → score 41.

**Distance/routes** — since no maps API or database is allowed, HQ
("Queens Street") sits at the origin of a small in-memory coordinate
system. A handful of known locations (City Hospital, Central Park, etc.)
have fixed coordinates; any other location typed in gets a coordinate
deterministically derived from its own name (via hash), so the same
location always yields the same distance for the rest of that run,
without ever touching disk or network. Route is simply HQ → incident
location.

**"Next mission" candidate pool** — only `REPORTED` (undispatched)
incidents are considered. An `IN_PROGRESS` incident is already being
handled, so it wouldn't make sense to recommend it as the *next* thing
to respond to; it still shows up in Active Incidents and the Dashboard.

**Status transitions** — strictly `REPORTED → IN_PROGRESS → RESOLVED`.
No skipping steps, no going backwards, and `RESOLVED` is final. Any other
requested change is rejected with a clear message and the incident is
left untouched.

## Crash-proofing

* Every `input()` call goes through `cli_utils`, which rejects empty
  input, non-numeric input, out-of-range menu choices, and negative
  numbers by re-prompting — never by throwing.
* A genuine end-of-input (EOF) or Ctrl+C is treated as "shut down
  cleanly", not as "loop forever asking for input that will never come."
* `main.py` wraps every menu handler in a final `except Exception` as a
  last line of defence, so even an unanticipated error is reported and
  the app returns to the main menu instead of dying.
* Looking up a missing incident ID, viewing an empty incident list,
  asking for a mission with none available, and building an empty
  dashboard are all explicitly handled — verified by both the automated
  tests and manual end-to-end runs.
