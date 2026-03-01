# Account Management Specification

## Purpose

Manage Google account lifecycle including CRUD operations, status tracking, batch import/export, and credential management. Accounts are the central entity of the system, linking to browser windows, automation tasks, and verification statuses.

## Requirements

### Requirement: Account Data Model

The system SHALL store accounts with the following fields: email (primary key), password, recovery_email, secret_key (2FA TOTP), link (verification link), status, message, browser_id, and browser_config.

#### Scenario: Create account with full information

- GIVEN a valid email address and credentials
- WHEN the account is created via import or API
- THEN all provided fields are stored in the SQLite database
- AND the account status defaults to "pending"

#### Scenario: Create account with minimal information

- GIVEN only an email and password
- WHEN the account is created
- THEN recovery_email, secret_key, and link fields are NULL
- AND the account is still functional for basic operations

### Requirement: Account Status Lifecycle

The system SHALL track account status through a defined lifecycle: pending → link_ready → verified → subscribed, with alternative terminal states of "ineligible" and "error".

#### Scenario: Status transitions to link_ready

- GIVEN an account in "pending" status
- WHEN a SheerID verification link is successfully extracted
- THEN the account status changes to "link_ready"
- AND the extracted link is stored

#### Scenario: Status transitions to verified

- GIVEN an account in "link_ready" status
- WHEN SheerID eligibility verification succeeds
- THEN the account status changes to "verified"

#### Scenario: Status transitions to subscribed

- GIVEN an account in "verified" status
- WHEN card binding and subscription are completed successfully
- THEN the account status changes to "subscribed"

#### Scenario: Status transitions to ineligible

- GIVEN an account undergoing eligibility check
- WHEN the account is determined to be ineligible
- THEN the account status changes to "ineligible"

#### Scenario: Status transitions to error

- GIVEN an account during any automation task
- WHEN an unrecoverable error or timeout occurs
- THEN the account status changes to "error"
- AND the error message is stored in the "message" field

### Requirement: Batch Account Import

The system SHALL support importing accounts from text files using a configurable separator format.

#### Scenario: Import with default separator

- GIVEN an accounts.txt file with "----" as separator
- WHEN the import is triggered
- THEN each line is parsed as: Email[separator]Password[separator]BackupEmail[separator]2FASecret
- AND accounts are upserted (inserted or updated) in the database

#### Scenario: Import with custom separator

- GIVEN a separator configuration on the first line (e.g., 分隔符="|")
- WHEN the import is triggered
- THEN the specified separator is used for parsing

#### Scenario: Import preserves existing data

- GIVEN an account already exists in the database
- WHEN the same email is imported with new data
- THEN only non-null imported fields overwrite existing values

### Requirement: Account Export

The system SHALL export account data to both structured text files and the database.

#### Scenario: Export to status-based text files

- GIVEN accounts in the database with various statuses
- WHEN export is triggered
- THEN separate text files are generated per status category
- AND the files include: sheerIDlink.txt, 已验证未绑卡.txt, 已绑卡号.txt, 无资格号.txt

### Requirement: Batch Account Deletion

The system SHALL support bulk deletion of accounts filtered by status.

#### Scenario: Delete accounts by status

- GIVEN multiple accounts with status "error"
- WHEN batch delete by status "error" is requested
- THEN all matching accounts are removed from the database
- AND associated browser windows are cleaned up

### Requirement: Batch Password Change

The system SHALL support automated batch password modification for Google accounts.

#### Scenario: Change password for multiple accounts

- GIVEN a list of accounts selected for password change
- WHEN the batch password change task is executed
- THEN each account's Google password is changed via browser automation
- AND the new password is updated in the database

### Requirement: 2FAGuard Export

The system SHALL export 2FA secrets in 2FAGuard-compatible format.

#### Scenario: Export 2FA secrets

- GIVEN accounts with stored 2FA secret keys
- WHEN 2FAGuard export is triggered
- THEN a file is generated with secrets in 2FAGuard-compatible format
