## Context

The simulated factory service exposes `PUT /api/config/sensors/{sensorId}` for both the HTMX operator UI and programmatic JSON callers. Currently:

1. The handler contains 60+ lines of ad-hoc coercion logic (CSV→list, string→bool, string→number) because `htmx-ext-json-enc` sends form data with inconsistent types.
2. The handler branches on `HX-Request` header: returns empty HTML for HTMX callers, JSON for others.
3. The HTMX frontend already uses `hx-swap="none"` — it ignores the response body and relies on SSE OOB refresh.
4. README, OpenSpec specs, and DEVELOPER.md still describe a per-sensor HTML fragment response that no longer exists.

This creates a shallow module where callers must know response format rules that the implementation doesn't actually leverage.

## Goals / Non-Goals

**Goals:**

- Move input normalization into Pydantic field validators on `SensorUpdateRequest` so the handler receives clean typed data.
- Remove the `HX-Request` branch; always return JSON from the PUT endpoint.
- Update specs, README, and DEVELOPER.md to document the actual contract.
- Keep the existing test assertions green (update them to expect JSON uniformly).

**Non-Goals:**

- Changing the SSE OOB refresh mechanism (it works correctly today).
- Reworking the twin.html sensor form templates (they already use `hx-swap="none"`).
- Introducing a separate validation module or library beyond Pydantic's built-in validators.
- Refactoring the engine's `update_sensor` method signature.

## Decisions

### 1. Coercion lives in Pydantic field validators

**Choice**: Add `@field_validator` / `@model_validator` methods on `SensorUpdateRequest` that handle:
- `raw_color`: CSV string → `list[int]`, or list-of-strings → `list[int]`
- `scripted_values`: CSV string → `list[int|float]`, or list coercion
- `value`: string "true"/"false" → bool, numeric strings → int/float

**Why over alternatives**:
- Keeps normalization co-located with the schema definition (locality).
- Pydantic validators run before the handler, so the handler never touches raw strings.
- Alternative (separate coercion module) adds a module for single-use logic — fails the deletion test.

### 2. Always return JSON from PUT /api/config/sensors/{id}

**Choice**: Remove the `if request.headers.get("HX-Request") == "true"` branch. Return `JSONResponse(jsonable_encoder(sensor))` unconditionally.

**Why**: The frontend already declares `hx-swap="none"` on sensor forms and the SSE OOB stream refreshes the twin panel. The HTML branch returns an empty body anyway — no caller uses the response content. Removing the branch shrinks the interface.

### 3. Accept `raw_color` as either array or `raw_color[]` form field

**Choice**: The Pydantic validator coerces both `"0,1,0"` (CSV string) and `[0, 1, 0]` (array) into `list[int] | None`. The `json-enc` htmx extension sends arrays for `name[]` fields, so the validator handles both shapes transparently.

**Why**: This avoids breaking the HTMX form contract while keeping programmatic callers simple.

### 4. Spec updates are delta-only

**Choice**: Issue MODIFIED delta specs for the three affected capabilities rather than rewriting the full spec files.

**Why**: Only the sensor update response contract changes. Other requirements in each spec are unaffected.

## Risks / Trade-offs

- **[Breaking change for HX-Request callers]** → Mitigation: The only known consumer (the HTMX twin form) uses `hx-swap="none"` and ignores the response body. External tools scripting with `HX-Request: true` will now receive JSON instead of empty HTML — this is documented as BREAKING in the proposal.
- **[Pydantic validator complexity]** → Mitigation: Validators are simple type coercion (parse int, split comma). Test each validator in isolation with parametrized test cases.
- **[Stale spec references in other archived changes]** → Mitigation: Archived changes are immutable historical records; only the live specs under `openspec/specs/` are updated.
