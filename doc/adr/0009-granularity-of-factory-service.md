# 9. Granularity of Factory Service

Date: 2026-04-16

## Status

Accepted

## Context

The factory domain contains many independent services and functions, all related to manufacturing the order. This decision relates to the granularity of the BPMN process. The process engine is able to model these functions at different levels of abstraction: from the highest-level abstraction of a single service task down to individual robot or sensor actions.
The key trade-off here is between the complexity of the model and the flexibility in implementing and extending the process.

## Decision

The assembly process is encapsulated into one service task.

The logic of where to pick blocks from, how to move them around, and how to read and interpret sensors is implemented inside one service task. All additional services pertaining to the factory domain are only called by the factory service directly and not exposed to the process engine.
With this decision we forfeit flexibility for a simpler Operaton implementation, allowing us to focus on other tasks such as improving the robot service and implementing a custom color sensor.


## Consequences

The BPMN process is simplified greatly, and its purpose is limited to providing controlled execution and error handling at a high level.
Changing the process requires redeploying the factory service, this is an acceptable trade-off in the context of a physical system where the amount of concurrent operations is limited to one.
The assembly logic can be tested directly in the Java application without requiring deployment of the process definition.
The extension of the process is limited to developers, a non-technical person is not able to graphically reconfigure the system.
