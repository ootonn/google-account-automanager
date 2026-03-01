# Web UI Specification

## Purpose

Provide a web-based management interface for Google account operations, including account CRUD, browser window management, task execution with real-time feedback, and system configuration. Built with Vue 3 + Vite frontend and FastAPI backend.

## Requirements

### Requirement: Account Management View

The system SHALL provide a web interface for managing Google accounts.

#### Scenario: View all accounts

- GIVEN the user navigates to the accounts page
- WHEN the page loads
- THEN all accounts are displayed in a table with columns: email, status, password (masked), recovery_email, 2FA status, browser status

#### Scenario: Search and filter accounts

- GIVEN multiple accounts in the system
- WHEN the user enters a search term or selects a status filter
- THEN only matching accounts are displayed

#### Scenario: Import accounts via web UI

- GIVEN the user is on the accounts page
- WHEN the user submits account data in the import form (text area or file)
- THEN accounts are parsed and imported into the database
- AND the accounts list refreshes to show new entries

#### Scenario: Export accounts

- GIVEN accounts exist in the database
- WHEN the user triggers export
- THEN account data is exported to the appropriate text files

#### Scenario: Batch delete by status

- GIVEN accounts with various statuses
- WHEN the user selects a status and triggers batch delete
- THEN all accounts matching the selected status are deleted

### Requirement: Browser Window Management View

The system SHALL provide a web interface for managing BitBrowser windows.

#### Scenario: Create windows for accounts

- GIVEN selected accounts without browser windows
- WHEN the user triggers window creation
- THEN browser windows are created for the selected accounts
- AND progress is displayed in real-time

#### Scenario: Restore windows

- GIVEN accounts with saved browser configurations but no active windows
- WHEN the user triggers window restoration
- THEN windows are restored from saved configurations

#### Scenario: Sync windows

- GIVEN existing BitBrowser windows
- WHEN the user triggers sync
- THEN all windows are synchronized with the database

### Requirement: Task Execution Interface

The system SHALL provide a web interface for executing and monitoring automation tasks.

#### Scenario: Start a task

- GIVEN the user selects accounts and a task type
- WHEN the user clicks "Start Task"
- THEN the task begins execution
- AND real-time logs and progress are displayed via WebSocket

#### Scenario: View task progress

- GIVEN a running task
- WHEN the user is on the tasks page
- THEN a progress bar shows current/total completion
- AND live log output scrolls automatically
- AND the current account being processed is highlighted

#### Scenario: Cancel a running task

- GIVEN a task in progress
- WHEN the user clicks "Cancel"
- THEN the task stops after the current account completes

### Requirement: Configuration Page

The system SHALL provide a web-based configuration interface.

#### Scenario: Configure SheerID API Key

- GIVEN the user navigates to the configuration page
- WHEN the user enters and saves a SheerID API Key
- THEN the API key is stored in the database for use in automation tasks

#### Scenario: Configure virtual card information

- GIVEN the user navigates to the configuration page
- WHEN the user enters card details (number, month, year, CVV)
- THEN the card info is stored in the database
- AND card info from the database takes priority over cards.txt

### Requirement: Real-time Feedback

The system SHALL provide real-time feedback for all long-running operations.

#### Scenario: WebSocket connection for live updates

- GIVEN the user is on a page with active tasks
- WHEN a WebSocket connection is established
- THEN task progress, logs, and status changes are pushed in real-time

#### Scenario: Auto-reconnect on disconnection

- GIVEN a WebSocket connection drops
- WHEN the client detects disconnection
- THEN it SHOULD automatically attempt reconnection

### Requirement: Responsive Layout

The system SHOULD provide a responsive layout that works on desktop browsers.

#### Scenario: Desktop browser view

- GIVEN the user accesses the UI from a desktop browser
- WHEN the page loads
- THEN the layout uses the full available width
- AND navigation is accessible via sidebar or top navigation

### Requirement: REST API

The system SHALL expose RESTful API endpoints for all operations.

#### Scenario: API documentation

- GIVEN the backend is running
- WHEN the user navigates to /docs
- THEN the FastAPI auto-generated Swagger documentation is displayed
- AND all endpoints are documented with request/response schemas
