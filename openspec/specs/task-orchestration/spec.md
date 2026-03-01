# Task Orchestration Specification

## Purpose

Manage and execute automation tasks with configurable concurrency, real-time progress updates via WebSocket, and ordered execution. The task system is the central execution engine that coordinates all automation operations.

## Requirements

### Requirement: Task Types

The system SHALL support the following task types: setup_2fa, reset_2fa, check_eligibility, age_verification, bind_card, change_password, set_language, create_window, delete_window, restore_window, and sync_windows.

#### Scenario: Execute a supported task type

- GIVEN a valid task type and selected accounts
- WHEN the task is submitted via the API
- THEN the corresponding automation function is executed for each account
- AND progress is reported in real-time

#### Scenario: Reject unsupported task type

- GIVEN an invalid or unknown task type
- WHEN the task is submitted
- THEN the API returns an error indicating the task type is not supported

### Requirement: Configurable Concurrency

The system SHALL support configurable concurrency for task execution, defaulting to sequential (one at a time) execution.

#### Scenario: Sequential execution

- GIVEN a task with default concurrency settings
- WHEN the task is executing
- THEN accounts are processed one at a time in order

#### Scenario: Parallel execution

- GIVEN a task with concurrency set to N (N > 1)
- WHEN the task is executing
- THEN up to N accounts are processed simultaneously

### Requirement: Real-time Progress Updates

The system SHALL provide real-time task progress via WebSocket connections.

#### Scenario: Progress during execution

- GIVEN a running task with WebSocket clients connected
- WHEN an account completes processing
- THEN a progress update is broadcast to all connected clients
- AND the update includes: current count, total count, current account, status, and log message

#### Scenario: Task completion notification

- GIVEN a running task
- WHEN all accounts have been processed
- THEN a completion event is broadcast to all WebSocket clients
- AND the final summary includes success/failure counts

### Requirement: Task Cancellation

The system SHOULD support cancelling running tasks.

#### Scenario: Cancel a running task

- GIVEN a task currently in execution
- WHEN a cancellation request is received
- THEN the current account finishes processing
- AND no further accounts are started
- AND a cancellation event is broadcast

### Requirement: Task Logging

The system SHALL capture and stream execution logs for each task.

#### Scenario: Log capture during automation

- GIVEN a running automation task
- WHEN the automation script produces output
- THEN the log is captured and forwarded to WebSocket clients
- AND logs are associated with the specific account being processed

### Requirement: Account Selection for Tasks

The system SHALL support selecting accounts for task execution by explicit list or by status filter.

#### Scenario: Select accounts by email list

- GIVEN a list of specific email addresses
- WHEN a task is created
- THEN only the specified accounts are included in the task

#### Scenario: Select accounts by status

- GIVEN a status filter (e.g., "verified")
- WHEN a task is created
- THEN all accounts matching the status are included
