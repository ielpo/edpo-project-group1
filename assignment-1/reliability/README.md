# Assignment 1 - Fault Tolerance and Reliability

## Test 1

### Goal
Observe failure of one broker in a triple redundant setup with one producer and one consumer.

### Setup
 - 1 controller
 - 3 brokers
 - 1 producers
 - 1 consumers

### Procedure
1. Normal startup of all components
2. Kill leader broker
3. Observe effects

### Expectations
The producer needs to wait for a new leader to be available.
The consumer does not receive events for a certain amount of time.


## Test 2

### Goal
Observe behaviour when follower 
