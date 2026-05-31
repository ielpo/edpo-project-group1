# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root — full system context: all services, communication patterns, key decisions.
- **`doc/adr/`** — read ADRs that touch the area you're about to work in.

If any of these files don't exist, proceed silently. Don't flag their absence; don't suggest creating them upfront.

## File structure: Single-context

```
/
├── CONTEXT.md
├── doc/adr/
│   ├── 0001-record-architecture-decisions.md
│   └── ...
└── services/
```

There is no `CONTEXT-MAP.md` and no per-service context files.

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/grill-with-docs`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-XXXX — but worth reopening because…_

Key ADRs for this repo:

- ADR-3: Why Operaton (not Camunda 8) as the BPMN engine
- ADR-4: Why commands & events (not pure events or RPC)
- ADR-9: Why assembly is one service task (not a subprocess)

## When to update these files

Update `CONTEXT.md` when a new service is added or removed, communication patterns change, data structures change significantly, or the development setup changes.

Create a new ADR in `doc/adr/` when making a major architectural decision (not for routine bug fixes or minor tweaks).
