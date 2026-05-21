# Preset Step Visualizer

Version: v1

## ADDED Requirements

### Requirement: Step pipeline rendered on active preset card
When a preset is running, its card in the presets panel SHALL display a horizontal step pipeline showing all steps of that preset as labelled block nodes.

Steps SHALL be visually differentiated by state:
- **Completed**: steps with index less than `currentStep`
- **Active**: the step at index `currentStep`
- **Pending**: steps with index greater than `currentStep`

The pipeline SHALL NOT be rendered on cards for presets that are not currently running.

#### Scenario: Running preset shows step pipeline
- **WHEN** a preset run is started via `POST /api/presets/run`
- **THEN** the presets fragment returned by `GET /fragments/presets` (and pushed via SSE OOB) SHALL include a step pipeline inside the card for that preset
- **AND** the pipeline SHALL contain one node per step defined in the preset's YAML
- **AND** steps with index less than `currentStep` SHALL carry the CSS class `step--done`
- **AND** the step at index equal to `currentStep` SHALL carry the CSS class `step--active`
- **AND** steps with index greater than `currentStep` SHALL carry the CSS class `step--pending`

#### Scenario: Idle presets show no pipeline
- **WHEN** no preset is running (status is `idle` or `stopped`)
- **THEN** the presets fragment SHALL NOT render any step pipeline on any card

#### Scenario: Pipeline advances with each step
- **WHEN** the engine advances from step N to step N+1
- **THEN** the SSE stream emits an updated presets fragment
- **AND** the node at index N transitions from `step--active` to `step--done`
- **AND** the node at index N+1 becomes `step--active`

#### Scenario: Pipeline disappears after preset completes
- **WHEN** the preset run finishes and status returns to `idle` or `stopped`
- **THEN** the presets fragment SHALL NOT render a step pipeline on any card

### Requirement: Preset list includes step metadata
The `list_presets()` engine method SHALL include a `steps` array for each preset, containing at least the `name` of each step.

#### Scenario: Presets API response includes steps
- **WHEN** a client calls `GET /api/presets`
- **THEN** each item in the `items` array SHALL contain a `steps` field
- **AND** each entry in `steps` SHALL include at minimum a `name` string

### Requirement: Presets fragment receives simulation state
The `/fragments/presets` endpoint and the SSE OOB renderer SHALL pass the current `SimulationState` to the presets template so step-level active state can be computed server-side.

#### Scenario: Fragment endpoint provides state context
- **WHEN** a client calls `GET /fragments/presets`
- **THEN** the rendered HTML SHALL reflect the current `currentPreset` and `currentStep` values from the engine state at render time

#### Scenario: SSE OOB update reflects new step
- **WHEN** the engine advances to a new step and the SSE stream emits an update
- **THEN** the OOB presets fragment in the SSE payload SHALL show the updated active step on the running preset card
