# Data Layer Specification

## Purpose

Manage data persistence, database operations, and data format compatibility. SQLite serves as the single source of truth, with text file import/export for backward compatibility.

## Requirements

### Requirement: SQLite Database Schema

The system SHALL use SQLite as the primary data store with the following tables: accounts (core), and configuration stored as key-value pairs.

#### Scenario: Initialize database

- GIVEN a fresh installation without accounts.db
- WHEN the application starts or DBManager.init_db() is called
- THEN the accounts table is created with all required columns
- AND existing text files (accounts.txt, etc.) are automatically imported

#### Scenario: Accounts table schema

- GIVEN the database is initialized
- THEN the accounts table contains columns: email (TEXT PRIMARY KEY), password, recovery_email, secret_key, link, status, message, browser_id, browser_config (JSON), created_at, updated_at

### Requirement: Account Upsert Operations

The system SHALL support upsert (insert or update) semantics for account operations.

#### Scenario: Insert new account

- GIVEN an email not in the database
- WHEN upsert_account is called
- THEN a new row is inserted with the provided fields

#### Scenario: Update existing account

- GIVEN an email already in the database
- WHEN upsert_account is called with new values
- THEN only non-null provided fields are updated
- AND existing non-null fields are preserved

### Requirement: Thread-Safe Database Access

The system SHALL provide thread-safe database access for concurrent operations.

#### Scenario: Concurrent task execution

- GIVEN multiple tasks running concurrently
- WHEN database operations are performed simultaneously
- THEN a threading lock prevents data corruption
- AND context managers ensure proper connection cleanup

### Requirement: Text File Import

The system SHALL support importing account data from text files with configurable separators.

#### Scenario: Parse accounts.txt

- GIVEN an accounts.txt file with separator configuration on the first line
- WHEN import_from_files is called
- THEN each line is parsed using the configured separator
- AND the format is: Email[sep]Password[sep]BackupEmail[sep]2FASecret
- AND lines starting with # are treated as comments and skipped

#### Scenario: Detect separator configuration

- GIVEN the first non-comment line contains separator config (e.g., 分隔符="----")
- WHEN parsing begins
- THEN the specified separator is used for all subsequent lines

### Requirement: Text File Export

The system SHALL export database content to traditional text files for compatibility.

#### Scenario: Export by status

- GIVEN accounts with various statuses in the database
- WHEN export_to_files is called
- THEN accounts are written to status-specific files:
  - sheerIDlink.txt: accounts with link_ready status and links
  - 已验证未绑卡.txt: accounts with verified status
  - 已绑卡号.txt: accounts with subscribed status
  - 无资格号.txt: accounts with ineligible status

#### Scenario: Export format

- GIVEN accounts to export
- WHEN writing to text files
- THEN each account line uses "----" separator
- AND fields are in order: Link(if any)----Email----Password----RecoveryEmail----SecretKey

### Requirement: Browser Configuration Storage

The system SHALL store browser window configurations as JSON in the database.

#### Scenario: Save browser config

- GIVEN a browser configuration object from BitBrowser API
- WHEN save_browser_config is called
- THEN the configuration is serialized as JSON
- AND stored in the browser_config column of the account row

#### Scenario: Retrieve browser config

- GIVEN an account with saved browser configuration
- WHEN get_browser_config is called
- THEN the JSON is deserialized and returned as a Python dictionary

### Requirement: Data Migration

The system SHALL support migrating data from legacy text file format to the database.

#### Scenario: First-time migration

- GIVEN existing text files (accounts.txt, etc.) and no database
- WHEN the system starts for the first time
- THEN all text file data is imported into the database
- AND the text files are preserved (not deleted)
