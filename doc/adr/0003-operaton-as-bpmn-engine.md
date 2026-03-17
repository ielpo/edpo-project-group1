# 3. Operaton as BPMN Engine

Date: 2026-03-14

## Status

Accepted

## Context

Camunda 7 is EOL, therefore we must choose if we use Operaton or switch to Camunda 8.

## Decision

We will implement the system using Operaton as the BPMN process engine.

The system is developed in the context of an IoT application involving physical components, which limits the suitability of cloud-based solutions. 
Additionally, the selected use case involves only a small number of concurrent process executions. 
As a result, the scalability benefits offered by cloud-native platforms such as Camunda 8 would not be fully utilized.

## Consequences

- The project must be properly configured to use Operaton as the process engine.
- Existing code written for Camunda 7 may require adaptation to ensure compatibility with Operaton.