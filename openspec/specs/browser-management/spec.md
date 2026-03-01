# Browser Management Specification

## Purpose

Manage BitBrowser fingerprint browser windows for Google account automation. Each account can be associated with a browser window that maintains a unique fingerprint profile, enabling batch operations without detection.

## Requirements

### Requirement: Browser Window Creation

The system SHALL create BitBrowser fingerprint browser windows via the BitBrowser local API (default 127.0.0.1:54345).

#### Scenario: Create window for an account

- GIVEN a valid account with email and password
- WHEN a browser window creation is requested
- THEN a new BitBrowser window is created via the API
- AND the window is configured with username matching the account email
- AND the browser_id is stored in the database

#### Scenario: Create window with device type

- GIVEN a window creation request with device type "pc" or "android"
- WHEN the window is created
- THEN the appropriate OS fingerprint is applied based on device type

### Requirement: Browser Window Restoration

The system SHALL restore previously deleted browser windows using saved configuration.

#### Scenario: Restore from saved config

- GIVEN an account with saved browser_config but no active browser_id
- WHEN a restore operation is requested
- THEN a new browser window is created using the saved configuration
- AND the new browser_id is stored in the database

#### Scenario: Detect existing window on restore

- GIVEN an account requesting window restoration
- WHEN a window with matching username already exists in BitBrowser
- THEN the existing window is rebound to the account
- AND no duplicate window is created

#### Scenario: Restore with stale browser_id

- GIVEN an account with a browser_id that no longer exists in BitBrowser
- WHEN a restore operation is requested
- THEN the stale browser_id is cleared
- AND a new window is created from saved config

### Requirement: Browser Configuration Persistence

The system SHALL save and retrieve browser window configurations in the database.

#### Scenario: Save browser config

- GIVEN an active browser window
- WHEN save_browser_to_db is called
- THEN the full browser configuration is fetched from BitBrowser API
- AND stored as JSON in the account's browser_config field

### Requirement: Browser Window Deletion

The system SHALL delete browser windows while preserving configuration for future restoration.

#### Scenario: Delete window keep config

- GIVEN an active browser window for an account
- WHEN deletion is requested
- THEN the latest configuration is saved before deletion
- AND the BitBrowser window is deleted via API
- AND the browser_id is cleared but browser_config is preserved

### Requirement: Browser Sync

The system SHALL synchronize all existing BitBrowser windows with the database.

#### Scenario: Sync existing browsers

- GIVEN multiple browser windows exist in BitBrowser
- WHEN sync is triggered
- THEN each window's username is matched to database accounts
- AND configurations are saved for matching accounts
- AND stale browser_ids in the database are cleaned up

#### Scenario: Skip unknown accounts during sync

- GIVEN a browser window with a username not in the database
- WHEN sync is executed
- THEN the window is skipped with a log message
