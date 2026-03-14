# 3. Operaton as BPMN Engine

Date: 2026-03-14

## Status

Accepted

## Context

Camunda 7 is EOL, therefore we must choose if we use Operaton or switch to Camunda 8.

## Decision

We will implement the system using Operaton as process engine.
The execution in the context of an IoT application with physical components limits the possibilities for using cloud solutions.
Additionally, the selected use case will allow for only a very limited number of concurrent process executions.
Therefore, we would not leverage the advantages of the scalability of the cloud deployments.

## Consequences

The project needs to be set up correctly, imported code must be adapted if it was written for Camunda 7.
