## MODIFIED Requirements

### Requirement: Preset catalog and deterministic execution
The service MUST load named presets from `presets.yml`, MUST expose the available preset names, and MUST execute a requested preset deterministically. Steps without `awaitRequest` advance after `delayMs` milliseconds. Steps with `awaitRequest` advance when a matching incoming HTTP request is received or `delayMs` milliseconds elapse as a timeout — whichever comes first.

#### Scenario: Happy-path preset runs reproducibly (non-gated steps)
- **WHEN** a client requests `POST /api/presets/run` with `{ "preset": "happy-path" }`
- **AND** no steps in that preset declare `awaitRequest`
- **THEN** the service accepts the run request
- **AND** it starts the named preset advancing each step after `delayMs`
- **AND** repeating the same preset with the same configuration yields the same sequence of simulation outcomes

#### Scenario: Preset with gated steps waits for requests
- **WHEN** a client requests `POST /api/presets/run` with a preset that has steps declaring `awaitRequest`
- **THEN** the service starts the preset
- **AND** gated steps hold until a matching incoming request arrives or `delayMs` elapses
- **AND** repeating the run with the same request sequence yields the same outcome

#### Scenario: Preset list includes configured names
- **WHEN** a client requests `GET /api/presets`
- **THEN** the service returns the configured preset names, including presets loaded from `presets.yml`
