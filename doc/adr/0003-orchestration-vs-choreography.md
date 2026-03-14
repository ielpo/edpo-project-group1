# 3. Orchestration vs Choreography

Date: 2026-03-14

## Status

Accepted

## Context

The selected application will require different services working in a coordinated manner, therefore we need to define where to use orchestration and where choreography is more suited.

## Decision

The ordering and the manufacturing processes will be implemented using orchestration. The customer process will make use of choreography.
Both ordering and manufacturing processes need to execute steps with additional logic regarding error and timeout handling.
The customer process is less critical and can have parts that fail.

## Consequences

The orchestration requires the use of a process engine, this increases the complexity of the applications.
